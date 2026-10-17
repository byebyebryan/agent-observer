"""Opt-in prepaid local sync acquisition through public structural protocols.

Sealed refs own bytes only. Complete material and proof admission remains at
its independently configured consumer. Core/source imports no Mesh code.
"""

from __future__ import annotations

import asyncio
import sys
import weakref

from .contract import ContractError
from .mesh_source import boottime_ms
from .sync_acquisition import MAX_CAPTURED_BYTES, MAX_RECEIPT_BYTES, _retire_failure, parse_header
from .sync_contract import (
    MAX_CHALLENGE_BYTES,
    MAX_CHALLENGE_DEPTH,
    MAX_CHALLENGE_NODES,
    MAX_CHANGE_BYTES,
    MAX_REQUEST_BYTES,
    MAX_TRANSACTIONS,
    SAFE_INTEGER,
)
from .sync_native import MAX_HEAD_BYTES, MAX_MESSAGE_BYTES
from .sync_source import MAX_CHANNELS, CachedAgentSyncSource, SourceWatch, _finish_owned, _reap

# Bounded source controls, 64 refs/tickets/leases, 64 owner incarnations and
# small receipt-watermark maps. Payload/parse storage has separate leases.
_STATE_HEAP = 512 * 1024
_REQUEST_HEAP = 768 * 1024  # request/512 nodes, batch and completed I/O callback scratch
_CHUNK = 65536
_IO_HEAP = 8192 + _CHUNK
_REQUEST_ENCODED = MAX_REQUEST_BYTES + _CHUNK
_PARSE_ENCODED = 4 * (MAX_CAPTURED_BYTES + MAX_RECEIPT_BYTES)
_MAX_ITEMS = 64
_BYTEARRAY_BASE = sys.getsizeof(bytearray())


class _SourceLease:
    def __init__(self, session, raw):
        self._session, self._raw = weakref.ref(session), raw

    @property
    def heap_bytes(self):
        return 0 if self._raw is None else self._raw.heap_bytes

    @property
    def encoded_bytes(self):
        return 0 if self._raw is None else self._raw.encoded_bytes

    def resize(self, heap_bytes, *, encoded_bytes=0):
        if self._raw is None:
            raise ContractError("sync_source_lease_closed")
        self._raw.resize(heap_bytes, encoded_bytes=encoded_bytes)

    def seal(self, raw):
        if self._raw is None:
            raise ContractError("sync_source_lease_closed")
        return self._raw.seal(raw)

    def close(self):
        raw, self._raw = self._raw, None
        if raw is not None:
            raw.close()
            session = self._session()
            if session is not None:
                session._leases.discard(self)


class _ParserBudget:
    def __init__(self, session):
        self.session = session

    def reserve(self, amount, *, encoded=0):
        return self.session._reserve(amount, encoded_bytes=encoded)


class _OwnedPacket:
    """A separate header lease survives consumption of the opaque data ref."""

    def __init__(self, session, data, header, scope):
        self._session, self._data = weakref.ref(session), data
        self._header, self._scope = header, scope
        session._packets.add(self)

    @property
    def _document(self):
        if self._header is None:
            raise ContractError("sync_ticket_closed")
        return self._header.document

    @property
    def data(self):
        if self._data is None:
            raise ContractError("sync_ticket_closed")
        return self._data

    def _detach(self):
        data, self._data = self.data, None
        self.close()
        return data

    def close(self):
        data, header = self._data, self._header
        self._data = self._header = None
        if data is not None:
            data.close()
        if header is not None:
            header.close()
        self._scope = None
        session = self._session()
        if session is not None:
            session._packets.discard(self)
            if data is not None:
                session._refs.pop(id(data), None)


class OwnedBaselineTicket(_OwnedPacket):
    @property
    def tag(self):
        return tuple(self._document["tag"])

    @property
    def cursor(self):
        return tuple(self._document["cursor"])


class OwnedSyncControl(_OwnedPacket):
    @property
    def status(self):
        return self._document["status"]

    @property
    def reason(self):
        return self._document["reason"]

    @property
    def tag(self):
        tag = self._document.get("tag")
        return None if tag is None else tuple(tag)

    @property
    def cursor(self):
        cursor = self._document.get("cursor")
        return None if cursor is None else tuple(cursor)


class OwnedResyncRequired(OwnedSyncControl):
    """Bounded explicit recovery, never an alternate profile/family."""


class OwnedSourceWatch(SourceWatch):
    def __init__(self, session, request, lease):
        super().__init__(session._client, request)
        self._session, self._request_lease = weakref.ref(session), lease

    async def __anext__(self):
        try:
            return await super().__anext__()
        except BaseException as error:
            # The base implementation has awaited watch cleanup. A saved
            # failure must not retain its now-unpaid decoded request frames.
            _retire_failure(error)
            raise error from None

    async def _close(self):
        session = self._session()
        if session is not None:
            session._revoke_scope(self._history)
        try:
            await super()._close()
        finally:
            self.request = None
            self._history.receipts.clear()
            self._history.service = None
            self._request_lease.close()


class _OwnedClient(CachedAgentSyncSource):
    def __init__(self, parent, session):
        super().__init__(parent.host, parent.path, view=parent.view, timeout=parent.timeout)
        self._parent_source, self._session = weakref.ref(parent), weakref.ref(session)

    def _watch_value(self, received):
        return received if isinstance(received, OwnedSyncControl) else received._detach()

    async def _read_frame(self, peer, request, node, stream, history):
        session = self._session()
        session._check()
        if stream.intake is None:
            stream.intake = session._reserve(_IO_HEAP, encoded_bytes=_CHUNK)
        credit = stream.intake
        operation = request["operation"]
        limit = MAX_HEAD_BYTES if operation == "head" else MAX_MESSAGE_BYTES
        loop = asyncio.get_running_loop()
        raw = part = header = data = parse_credit = None
        try:
            deadline = boottime_ms() + int(self.timeout * 1000)
            while b"\n" not in stream.pending:
                remaining = (deadline - boottime_ms()) / 1000
                if remaining <= 0:
                    raise ContractError("service_transport_timeout")
                want = min(65536, limit + 1 - len(stream.pending))
                # Old + enlarged mutable allocation + received chunk coexist.
                # 2*needed+64 bounds bytearray capacity/resize on supported
                # CPython versions; actual capacity replaces this credit later.
                growth = 2 * (len(stream.pending) + want + 1) + 64
                copies = _capacity(stream.pending) + growth + want
                credit.resize(_IO_HEAP + copies, encoded_bytes=copies + _CHUNK)
                part = await self._io(loop.sock_recv(peer, want), remaining)
                if not part:
                    raise ContractError("sync_disconnected")
                self._counts["receivedBytes"] += len(part)
                stream.pending.extend(part)
                part = None
                credit.resize(_IO_HEAP + _capacity(stream.pending), encoded_bytes=_capacity(stream.pending) + _CHUNK)
                if len(stream.pending) > limit and b"\n" not in stream.pending:
                    raise ContractError("sync_message_limit")
            end = stream.pending.index(b"\n") + 1
            if end > limit:
                raise ContractError("sync_message_limit")
            cost = session._inputs.buffer_heap(end)
            tail = len(stream.pending) - end
            tail_credit = 0 if not tail else 2 * (tail + 1) + 64
            copies = _capacity(stream.pending) + tail_credit
            credit.resize(_IO_HEAP + copies + cost, encoded_bytes=copies + end + _CHUNK)
            raw = bytes(memoryview(stream.pending)[:end])
            stream.pending = bytearray(memoryview(stream.pending)[end:]) if tail else bytearray()
            credit.resize(_IO_HEAP + _capacity(stream.pending) + cost,
                          encoded_bytes=_capacity(stream.pending) + len(raw) + _CHUNK)
            # Heap preflight belongs to the parser's own structural budget;
            # canonical header/digest temporaries also need encoded credit.
            parse_credit = session._reserve(8192, encoded_bytes=_PARSE_ENCODED)
            header = parse_header(raw, self.view, self.host, budget=_ParserBudget(session))
            parse_credit.close()
            parse_credit = None
            if boottime_ms() >= deadline:
                raise ContractError("service_transport_timeout")
            self._check_frame(request, node, stream, history, header.document)
            session._check()
            session._prune_refs()
            if len(session._refs) >= _MAX_ITEMS or len(session._packets) >= _MAX_ITEMS:
                raise ContractError("sync_source_ownership_capacity")
            data = credit.seal(raw)
            raw = None  # the sealed ref exclusively owns this immutable buffer
            session._refs[id(data)] = (data, stream.scope)
            credit.resize(_IO_HEAP + _capacity(stream.pending), encoded_bytes=_capacity(stream.pending) + _CHUNK)
            kind = header.document["kind"]
            packet_type = (OwnedBaselineTicket if kind == "baseline" else
                           OwnedSyncControl if kind == "control" and header.document["status"] in
                           {"complete", "heartbeat"} else
                           OwnedResyncRequired if kind == "control" else _OwnedPacket)
            result = packet_type(session, data, header, stream.scope)
            data = header = None
            return result
        except BaseException as error:
            _retire_failure(error)
            raise error from None
        finally:
            raw = part = None
            if data is not None:
                data.close()
                session._refs.pop(id(data), None)
            if header is not None:
                header.close()
            if parse_credit is not None:
                parse_credit.close()
            # On failure the conservative receive credit survives until
            # _frames drops pending storage and closes the stream lease.


def _capacity(value):
    return max(0, sys.getsizeof(value) - _BYTEARRAY_BASE)


def _tuple_copy(value):
    # A caller iterator must not allocate an unbounded list before validation.
    iterator, result = iter(value), []
    for item in iterator:
        if len(result) == 3:
            raise ContractError("sync_tuple_shape")
        result.append(item)
    if len(result) != 3:
        raise ContractError("sync_tuple_shape")
    return result


def _challenge_preflight(value):
    # Necessary bounds only; the ordinary strict request validator remains
    # authoritative. Cap children BEFORE stack expansion and string lengths
    # BEFORE canonical encoding. Legal requests fit the prepaid request lease.
    seen, characters, stack = 0, 0, [(value, 0)]
    while stack:
        node, depth = stack.pop()
        seen += 1
        if depth > MAX_CHALLENGE_DEPTH or seen > MAX_CHALLENGE_NODES:
            raise ContractError("sync_challenge_limit")
        kind = type(node)
        if kind in (dict, list):
            children = len(node)
            if kind is dict:
                seen += children
            if seen + len(stack) + children > MAX_CHALLENGE_NODES:
                raise ContractError("sync_challenge_limit")
            if kind is dict:
                for key in node:
                    if type(key) is not str:
                        raise ContractError("sync_challenge_type")
                    characters += len(key)
                stack.extend((child, depth + 1) for child in node.values())
            else:
                stack.extend((child, depth + 1) for child in node)
        elif kind is str:
            characters += len(node)
        elif kind is int:
            if not -SAFE_INTEGER <= node <= SAFE_INTEGER:
                raise ContractError("sync_challenge_integer")
        elif kind not in (bool, type(None)):
            raise ContractError("sync_challenge_type")
        if characters > MAX_CHALLENGE_BYTES:
            raise ContractError("sync_challenge_limit")


class OwnedSourceSession:
    """One opt-in source's I/O, refs and leases; owns no native service."""

    def __init__(self, parent, inputs, state_credit):
        self._parent, self._inputs = weakref.ref(parent), inputs
        self._state_credit = state_credit
        self._refs, self._packets, self._leases, self._calls = {}, set(), set(), set()
        self._closed, self._close_task = False, None
        self._client = _OwnedClient(parent, self)
        parent._sessions.add(self)

    def _check(self):
        parent = self._parent()
        if self._closed or parent is None or parent._closed:
            raise ContractError("sync_source_closed")

    def _reserve(self, heap_bytes, *, encoded_bytes=0):
        self._check()
        if len(self._leases) >= _MAX_ITEMS:
            raise ContractError("sync_source_ownership_capacity")
        raw = self._inputs.reserve(heap_bytes, encoded_bytes=encoded_bytes)
        try:
            result = _SourceLease(self, raw)
            self._leases.add(result)
            return result
        except BaseException:
            raw.close()
            raise

    def _prune_refs(self):
        for marker, (data, _scope) in tuple(self._refs.items()):
            try:
                _ = data.nbytes
            except ValueError as error:
                if error.args != ("sync_input_retired",):
                    raise
                del self._refs[marker]

    def _revoke_scope(self, scope):
        for marker, (data, owner) in tuple(self._refs.items()):
            if owner is scope:
                data.close()
                del self._refs[marker]
        for packet in tuple(self._packets):
            if packet._scope is scope:
                packet.close()

    async def _run(self, operation):
        parent = self._parent()
        active = 0 if parent is None else len(parent._tasks) + sum(
            len(session._calls) + sum(watch._pending is not None for watch in session._client._watches)
            for session in parent._sessions)
        if self._closed or parent is None or parent._closed or active >= MAX_CHANNELS:
            operation.close()
            raise ContractError("sync_source_closed" if self._closed or parent is None or parent._closed
                                else "sync_acquisition_capacity")
        task = asyncio.create_task(operation)
        self._calls.add(task)
        delivered = False
        try:
            result = await task
            self._check()
            delivered = True
            return result
        finally:
            try:
                if not task.done():
                    task.cancel()
                    await _finish_owned(asyncio.create_task(_reap(task)))
            finally:
                try:
                    # Cancellation may win after the operation completes but
                    # before its result reaches this awaiter. Retire that
                    # operation's ticket/ref tuple without closing the session
                    # or an unrelated watch on the same input owner.
                    if (not delivered and task.done() and not task.cancelled()
                            and task.exception() is None):
                        returned = task.result()
                        for item in returned if type(returned) is tuple else (returned,):
                            item.close()
                        self._prune_refs()
                finally:
                    self._calls.discard(task)

    async def _call(self, operation, fields):
        self._check()
        lease = self._reserve(_REQUEST_HEAP, encoded_bytes=_REQUEST_ENCODED)
        request = received = None
        scope = object()
        try:
            if operation == "head":
                _challenge_preflight(fields["challenge"])
            request = self._client._request(operation, **fields)
            received = await self._client._owned(self._client._io(
                self._client._single(request, operation, scope=scope),
                min(2, self._client.timeout) if operation == "head" else self._client.timeout))
            self._check()
            return received if operation == "baseline" else received._detach()
        except BaseException as error:
            self._revoke_scope(scope)
            if received is not None:
                received.close()
            _retire_failure(error)
            raise error from None
        finally:
            request = received = fields = None
            lease.close()

    async def baseline(self):
        return await self._run(self._call("baseline", {}))

    async def head_after_nonce(self, challenge):
        return await self._run(self._call("head", {"challenge": challenge}))

    async def changes(self, base, *, target, max_transactions=MAX_TRANSACTIONS, max_bytes=MAX_CHANGE_BYTES):
        return await self._run(self._changes(base, target, max_transactions, max_bytes))

    async def _changes(self, base, target, max_transactions, max_bytes):
        self._check()
        lease = self._reserve(_REQUEST_HEAP, encoded_bytes=_REQUEST_ENCODED)
        request = iterator = received = None
        result, transferred = [], False
        scope = object()
        try:
            request = self._client._request("changes", baseTag=_tuple_copy(base), targetTag=_tuple_copy(target),
                                             maxTransactions=max_transactions, maxBytes=max_bytes)
            async def collect():
                nonlocal iterator, received
                iterator = self._client._frames(request, scope=scope)
                size = 0
                async for received in iterator:
                    if isinstance(received, OwnedSyncControl):
                        if isinstance(received, OwnedResyncRequired):
                            return received
                        received.close()
                        received = None
                        return tuple(result)
                    size += received.data.nbytes
                    result.append(received._detach())
                    received = None
                    if len(result) > max_transactions or size > max_bytes:
                        raise ContractError("sync_change_limit")
                raise ContractError("sync_change_incomplete")
            value = await self._client._owned(self._client._io(collect(), self._client.timeout))
            self._check()
            transferred = type(value) is tuple
            return value
        except BaseException as error:
            self._revoke_scope(scope)
            _retire_failure(error)
            raise error from None
        finally:
            if iterator is not None:
                await iterator.aclose()
            if received is not None and not isinstance(received, OwnedResyncRequired):
                received.close()
            if not transferred:
                for data in result:
                    data.close()
            result.clear()
            request = iterator = received = collect = None
            lease.close()

    def watch(self, cursor):
        self._check()
        if self._client._family_count("_watches") >= MAX_CHANNELS:
            raise ContractError("sync_acquisition_capacity")
        lease = self._reserve(_REQUEST_HEAP, encoded_bytes=_REQUEST_ENCODED)
        request = watch = None
        try:
            request = self._client._request("watch", cursor=_tuple_copy(cursor))
            watch = OwnedSourceWatch(self, request, lease)
            self._client._watches.add(watch)
            return watch
        except BaseException as error:
            _retire_failure(error)
            request = watch = None
            lease.close()
            raise error from None

    def inspect(self):
        self._prune_refs()
        return {"closed": self._closed, "activeTasks": len(self._client._tasks),
                "activeSockets": len(self._client._sockets), "activeWatches": len(self._client._watches),
                "ownedOperations": len(self._calls),
                "ownedRefs": len(self._refs), "ownedTickets": len(self._packets),
                "ownedLeases": len(self._leases), "stateHeapCredit": self._state_credit.heap_bytes,
                **self._client._counts}

    def _begin_close(self):
        if self._close_task is None:
            self._closed = True
            for data, _scope in tuple(self._refs.values()):
                data.close()
            self._refs.clear()
            for task in tuple(self._calls):
                task.cancel()
            # Unsealed receive storage keeps its lease through awaited cleanup.
            for peer in tuple(self._client._sockets):
                peer.close()
            self._close_task = asyncio.create_task(self._close())

    async def aclose(self):
        self._begin_close()
        await _finish_owned(self._close_task)

    async def _close(self):
        try:
            # Await complete source operations, not just their inner I/O tasks:
            # request/batch storage can survive an inner task's completion.
            await asyncio.gather(*tuple(self._calls), return_exceptions=True)
            await self._client.aclose()
        finally:
            for packet in tuple(self._packets):
                packet.close()
            for lease in tuple(self._leases):
                lease.close()
            self._client._receipts.clear()
            self._client._retired.clear()
            self._client._binding = self._client._service = None
            for history in self._client._histories.values():
                history.receipts.clear()
                history.service = None
            parent = self._parent()
            if parent is not None:
                parent._sessions.discard(self)
                for name, value in self._client._counts.items():
                    parent._counts[name] += value
            self._state_credit.close()


def open_session(parent, inputs):
    if not callable(getattr(inputs, "reserve", None)) or not callable(getattr(inputs, "buffer_heap", None)):
        raise ContractError("sync_source_input_owner")
    state_credit = inputs.reserve(_STATE_HEAP, encoded_bytes=0)
    try:
        return OwnedSourceSession(parent, inputs, state_credit)
    except BaseException as error:
        _retire_failure(error)
        state_credit.close()
        raise error from None
