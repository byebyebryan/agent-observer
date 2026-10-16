"""Operation-owned local sync acquisition; no Mesh or provider dependency."""

from __future__ import annotations

import asyncio
import os
import socket
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .contract import ContractError
from .mesh_source import MAX_INCARNATIONS, CachedAgentSource, boottime_ms
from .sync_contract import (
    ACTIVE_SYNC_PROTOCOL,
    MAX_CHANGE_BYTES,
    MAX_TRANSACTIONS,
    SYNC_PROTOCOL,
    parse_request,
    validate_request,
)
from .sync_native import MAX_HEAD_BYTES, MAX_MESSAGE_BYTES, parse_message

MAX_CHANNELS = 16


@dataclass(frozen=True)
class BaselineTicket:
    data: bytes
    tag: tuple
    cursor: tuple


@dataclass(frozen=True)
class SyncControl:
    data: bytes
    status: str
    reason: str
    tag: tuple | None
    cursor: tuple | None


@dataclass(frozen=True)
class ResyncRequired(SyncControl):
    """Explicit recovery, never a replacement-family fallback."""


@dataclass(frozen=True)
class _Received:
    data: bytes
    document: dict


@dataclass
class _History:
    service: str | None = None
    generation: int = 0
    emitted: int = 0
    receipts: dict = field(default_factory=dict)


async def _finish_owned(task):
    interrupted = False
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            interrupted = True
    result = task.result()
    if interrupted:
        raise asyncio.CancelledError
    return result


async def _reap(task):
    await asyncio.gather(task, return_exceptions=True)


class SourceWatch:
    """One subscription; closing it never closes its source or sibling watches."""

    def __init__(self, source, request):
        self.source, self.request = source, request
        self._iterator = None
        self._pending = None
        self._closed = False
        self._close_task = None
        self._history = _History()

    async def __aenter__(self):
        if self._closed or self.source._closed:
            raise ContractError("sync_source_closed")
        return self

    async def __aexit__(self, *_args):
        await self.aclose()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed or self.source._closed:
            raise StopAsyncIteration
        if self._pending is not None:
            raise ContractError("sync_watch_busy")
        if len(self.source._tasks) >= MAX_CHANNELS:
            raise ContractError("sync_acquisition_capacity")
        if self._iterator is None:
            self._iterator = self.source._frames(self.request, history=self._history)
        task = self._pending = asyncio.create_task(anext(self._iterator))
        self.source._tasks.add(task)
        try:
            result = await task
            return self.source._watch_value(result)
        except BaseException:
            await self.aclose()
            raise
        finally:
            self.source._tasks.discard(task)
            self._pending = None

    async def aclose(self):
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._close())
        await _finish_owned(self._close_task)

    async def _close(self):
        try:
            task = self._pending
            if task is not None and task is not asyncio.current_task():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if self._iterator is not None:
                await self._iterator.aclose()
        finally:
            self.source._watches.discard(self)


class CachedAgentSyncSource:
    """A bounded client of one configured full or active native sync view.

    The protected socket policy and absolute I/O timeout are shared with the
    existing cached source. The new path never enters its full-frame parser.
    """

    _socket_policy = CachedAgentSource._socket_policy
    _io = CachedAgentSource._io

    def __init__(self, host, path, *, view="full", timeout=15.0):
        if view not in {"full", "active"}:
            raise ContractError("sync_view")
        if type(timeout) not in (int, float) or not 1 <= timeout <= 60:
            raise ContractError("service_client_timeout")
        self.host, self.path, self.view, self.timeout = host, Path(path), view, timeout
        self._closed = False
        self._close_task = None
        self._tasks, self._sockets, self._watches = set(), set(), set()
        self._counts = {"requests": 0, "frames": 0, "receivedBytes": 0}
        self._service, self._binding, self._receipts = None, None, {}
        self._retired = set()
        self._histories = {operation: _History() for operation in ("baseline", "head")}
        self._read_locks = {operation: asyncio.Lock() for operation in self._histories}

    @property
    def protocol(self):
        return ACTIVE_SYNC_PROTOCOL if self.view == "active" else SYNC_PROTOCOL

    def _request(self, operation, **fields):
        from .sync_commitment import canonical

        value = validate_request({"syncProtocol": self.protocol, "version": 1,
                                  "operation": operation, "hostScope": self.host, **fields})
        return canonical(value) + b"\n"

    @staticmethod
    def _control(received):
        value = received.document
        control = SyncControl if value["status"] in {"complete", "heartbeat"} else ResyncRequired
        return control(received.data, value["status"], value["reason"],
                       None if value.get("tag") is None else tuple(value["tag"]),
                       None if value.get("cursor") is None else tuple(value["cursor"]))

    def _watch_value(self, received):
        # Subclasses used for transport-lifetime fixtures may supply owned
        # bytes directly; real socket reads always carry a parsed outer frame.
        if isinstance(received, bytes):
            return received
        if received.document["kind"] == "control":
            return self._control(received)
        return received.data

    def _admit(self, value, *, history=None):
        kind = value["kind"]
        if kind == "baseline":
            clock = value["nativeBinding"]
            receipts = value["tables"]["receipts"]
        elif kind in {"head", "control"}:
            clock = value["ownerClock"]
            receipts = value.get("originalReceipts", ())
        else:
            clock = None
            receipts = ()
        epoch = value["resultCursor"][0] if kind == "transaction" else clock["ownerEpoch"]
        if epoch in self._retired:
            raise ContractError("sync_publisher_retired")
        binding = None
        if clock is not None:
            if (clock["uid"] != os.geteuid() or clock["hostScope"] != self.host
                    or clock["bootId"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                    or clock["clockDomain"] != os.readlink("/proc/self/ns/time")
                    or clock.get("boottimeMs", 0) > boottime_ms()):
                raise ContractError("sync_clock_context")
            binding = tuple(clock[name] for name in ("hostScope", "uid", "bootId", "clockDomain"))
            if epoch == self._service and self._binding is not None and binding != self._binding:
                raise ContractError("sync_acquisition_scope_changed")
        watermarks = {} if epoch != self._service else dict(self._receipts)
        current_receipts = {}
        for key, receipt in receipts:
            key = tuple(key)
            if receipt["sampledBoottimeMs"] is not None and receipt["sampledBoottimeMs"] > boottime_ms():
                raise ContractError("sync_receipt_future")
            current = tuple(receipt[name] for name in (
                "accepted", "sampledBoottimeMs", "expiresBoottimeMs",
            ))
            current_receipts[key] = current
            previous = watermarks.get(key)
            if previous is not None:
                if current[0] == previous[0] and current[1:] != previous[1:]:
                    raise ContractError("sync_receipt_renewal")
                if (current[0] > previous[0] and current[1] is not None and previous[1] is not None
                        and current[1] < previous[1]):
                    raise ContractError("sync_receipt_clock_regression")
            if previous is None or current[0] > previous[0]:
                watermarks[key] = current
        tag = value.get("resultTag", value.get("tag"))
        generation = None if tag is None else tag[1]
        emitted = 0 if clock is None else clock.get("boottimeMs", 0)
        if history is not None and history.service == epoch:
            if generation is not None and generation < history.generation:
                raise ContractError("sync_acquisition_superseded")
            if emitted and emitted < history.emitted:
                raise ContractError("sync_acquisition_clock_regression")
            if current_receipts and history.receipts and set(current_receipts) != set(history.receipts):
                raise ContractError("sync_acquisition_scope_changed")
            for key, current in current_receipts.items():
                previous = history.receipts.get(key)
                if previous is not None and current[0] < previous[0]:
                    raise ContractError("sync_receipt_regression")
        if epoch != self._service and self._service is not None:
            if len(self._retired) >= MAX_INCARNATIONS - 1:
                raise ContractError("sync_incarnation_capacity")
            self._retired.add(self._service)
        # Admission commits atomically, after all bounded checks succeed.
        self._service = epoch
        self._binding = binding if binding is not None else self._binding
        self._receipts = watermarks
        if history is not None:
            history.service = epoch
            if generation is not None:
                history.generation = generation
            if emitted:
                history.emitted = emitted
            if current_receipts:
                history.receipts = current_receipts

    async def _frames(self, raw_request, *, history=None):
        request = parse_request(raw_request, expected_host=self.host, expected_protocol=self.protocol)
        node = self._socket_policy()
        if self._closed:
            raise ContractError("sync_source_closed")
        if len(self._sockets) >= MAX_CHANNELS:
            raise ContractError("sync_acquisition_capacity")
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sockets.add(peer)
        operation = request["operation"]
        limit = MAX_HEAD_BYTES if operation == "head" else MAX_MESSAGE_BYTES
        loop = asyncio.get_running_loop()
        cursor = tuple(request["cursor"]) if operation == "watch" else None
        change_tag = tuple(request["baseTag"]) if operation == "changes" else None
        self._counts["requests"] += 1
        try:
            peer.setblocking(False)
            await self._io(loop.sock_connect(peer, str(self.path)), min(2, self.timeout))
            current = self.path.lstat()
            if (current.st_dev, current.st_ino) != (node.st_dev, node.st_ino):
                raise ContractError("service_socket_changed")
            _pid, uid, _gid = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.geteuid():
                raise ContractError("service_peer_ownership")
            await self._io(loop.sock_sendall(peer, raw_request), min(2, self.timeout))
            pending = bytearray()
            while True:
                deadline = boottime_ms() + int(self.timeout * 1000)
                while b"\n" not in pending:
                    remaining = (deadline - boottime_ms()) / 1000
                    if remaining <= 0:
                        raise ContractError("service_transport_timeout")
                    part = await self._io(loop.sock_recv(peer, min(65536, limit + 1 - len(pending))), remaining)
                    if not part:
                        raise ContractError("sync_disconnected")
                    self._counts["receivedBytes"] += len(part)
                    pending.extend(part)
                    if len(pending) > limit and b"\n" not in pending:
                        raise ContractError("sync_message_limit")
                line, _, rest = pending.partition(b"\n")
                pending = bytearray(rest)
                raw = bytes(line) + b"\n"
                del line, rest
                if len(raw) > limit:
                    raise ContractError("sync_message_limit")
                value = parse_message(raw, view=self.view, expected_host=self.host)
                current = self._socket_policy()
                if (current.st_dev, current.st_ino) != (node.st_dev, node.st_ino):
                    raise ContractError("service_socket_changed")
                kind = value["kind"]
                if kind != "control" and kind != {"baseline": "baseline", "head": "head",
                                                  "changes": "transaction", "watch": "transaction"}[operation]:
                    raise ContractError("sync_operation_binding")
                if kind == "head" and value["challenge"] != request["challenge"]:
                    raise ContractError("sync_challenge_binding")
                if kind == "transaction" and operation == "changes":
                    target, result = tuple(request["targetTag"]), tuple(value["resultTag"])
                    if (tuple(value["baseTag"]) != change_tag or result[0] != target[0]
                            or result[1] > target[1] or result[1] == target[1] and result != target):
                        raise ContractError("sync_change_order")
                    change_tag = result
                if kind == "transaction" and operation == "watch":
                    if tuple(value["baseCursor"]) != cursor:
                        raise ContractError("sync_watch_order")
                    cursor = tuple(value["resultCursor"])
                if kind == "control" and operation == "watch" and value["status"] in {"complete", "heartbeat"}:
                    if value.get("cursor") is not None and tuple(value["cursor"]) != cursor:
                        raise ContractError("sync_watch_order")
                if kind == "control" and operation == "changes" and value["status"] == "complete":
                    if (value.get("baseTag") != request["baseTag"]
                            or value.get("targetTag") != request["targetTag"]
                            or change_tag != tuple(request["targetTag"])):
                        raise ContractError("sync_change_target")
                self._admit(value, history=history)
                self._counts["frames"] += 1
                terminal = (operation in {"baseline", "head"}
                            or kind == "control" and (operation == "changes"
                                or value["status"] not in {"complete", "heartbeat"}))
                yield _Received(raw, value)
                del value, raw
                if terminal:
                    return
        finally:
            peer.close()
            self._sockets.discard(peer)

    async def _single(self, request, operation):
        async with self._read_locks[operation]:
            iterator = self._frames(request, history=self._histories[operation])
            try:
                return await anext(iterator)
            finally:
                await iterator.aclose()

    async def baseline(self):
        received = await self._owned(self._io(self._single(self._request("baseline"), "baseline"), self.timeout))
        if received.document["kind"] == "control":
            return self._control(received)
        value = received.document
        return BaselineTicket(received.data, tuple(value["tag"]), tuple(value["cursor"]))

    async def head_after_nonce(self, challenge):
        received = await self._owned(self._io(self._single(self._request("head", challenge=challenge), "head"),
                                             min(2, self.timeout)))
        return received.data

    async def _changes(self, request):
        expected = parse_request(request)
        iterator = self._frames(request)
        result, size, tag = [], 0, tuple(expected["baseTag"])
        try:
            async for received in iterator:
                value = received.document
                if value["kind"] == "control":
                    control = self._control(received)
                    if isinstance(control, ResyncRequired):
                        return control
                    if (value.get("baseTag") != expected["baseTag"]
                            or value.get("targetTag") != expected["targetTag"]
                            or tag != tuple(expected["targetTag"])):
                        raise ContractError("sync_change_target")
                    return tuple(result)
                if tuple(value["baseTag"]) != tag:
                    raise ContractError("sync_change_order")
                tag = tuple(value["resultTag"])
                result.append(received.data)
                size += len(received.data)
                if len(result) > expected["maxTransactions"] or size > expected["maxBytes"]:
                    raise ContractError("sync_change_limit")
                del value, received
            raise ContractError("sync_change_incomplete")
        finally:
            await iterator.aclose()

    async def changes(self, base, *, target, max_transactions=MAX_TRANSACTIONS, max_bytes=MAX_CHANGE_BYTES):
        request = self._request("changes", baseTag=list(base), targetTag=list(target),
                                maxTransactions=max_transactions, maxBytes=max_bytes)
        return await self._owned(self._io(self._changes(request), self.timeout))

    def watch(self, cursor):
        if self._closed:
            raise ContractError("sync_source_closed")
        if len(self._watches) >= MAX_CHANNELS:
            raise ContractError("sync_acquisition_capacity")
        result = SourceWatch(self, self._request("watch", cursor=list(cursor)))
        self._watches.add(result)
        return result

    def inspect(self):
        return {"closed": self._closed, "activeTasks": len(self._tasks),
                "activeSockets": len(self._sockets), "activeWatches": len(self._watches),
                **self._counts}

    async def _owned(self, operation):
        if self._closed:
            operation.close()
            raise ContractError("sync_source_closed")
        if len(self._tasks) >= MAX_CHANNELS:
            operation.close()
            raise ContractError("sync_acquisition_capacity")
        task = asyncio.create_task(operation)
        self._tasks.add(task)
        try:
            return await task
        finally:
            try:
                if not task.done():
                    task.cancel()
                    await _finish_owned(asyncio.create_task(_reap(task)))
            finally:
                self._tasks.discard(task)

    async def aclose(self):
        if self._close_task is None:
            self._closed = True
            # Revoke blocked acquisitions before yielding to cleanup.
            for peer in tuple(self._sockets):
                peer.close()
            self._close_task = asyncio.create_task(self._close())
        await _finish_owned(self._close_task)

    async def _close(self):
        tasks = [task for task in self._tasks if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.difference_update(tasks)
        results = await asyncio.gather(*(watch.aclose() for watch in tuple(self._watches)), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result
