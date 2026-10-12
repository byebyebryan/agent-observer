"""Agent-owned cached Service 2 acquisition; no provider or Mesh imports."""

from __future__ import annotations

import asyncio
import os
import socket
import stat
import struct
import time
from pathlib import Path

from .service_public import (
    ContractError,
    StreamGuard,
    canonical,
    interface,
    parse_frame,
    validate_request,
)

MAX_FRAME_BYTES = interface()["limits"]["frameBytes"]
MAX_INCARNATIONS = 64
MAX_CHANNELS = 32


def boottime_ms():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


class CachedAgentSource:
    """Operation-owned sockets and bounded native ordering across acquisitions.

    Service 2 fixes source/component scope inside one service incarnation.
    Delayed watch views are skipped after a newer acquisition. Delayed status
    reads fail instead of supplying an older nonce-bound proof. Retired service
    IDs cannot become current again; exhaustion requires a fresh publisher.
    """

    def __init__(self, host, path, *, timeout=15.0):
        if type(timeout) not in (int, float) or not 1 <= timeout <= 60:
            raise ContractError("service_client_timeout")
        self.host, self.path, self.timeout = host, Path(path), timeout
        self._service = None
        self._binding = None
        self._position = (0, 0)
        self._receipts = {}
        self._retired = set()
        self._active = 0

    def _socket_policy(self):
        path, uid = self.path, os.geteuid()
        if not path.is_absolute() or path.parent.resolve() != path.parent:
            raise ContractError("service_socket_path")
        directory, node = path.parent.stat(), path.lstat()
        if (directory.st_uid != uid or stat.S_IMODE(directory.st_mode) != 0o700
                or node.st_uid != uid or not stat.S_ISSOCK(node.st_mode)
                or stat.S_IMODE(node.st_mode) != 0o600):
            raise ContractError("service_socket_ownership")
        return node

    async def _io(self, operation, seconds):
        deadline = boottime_ms() + int(seconds * 1000)
        try:
            async with asyncio.timeout(seconds):
                result = await operation
            if boottime_ms() >= deadline:
                raise TimeoutError
            return result
        except TimeoutError:
            raise ContractError("service_transport_timeout") from None

    def _admit(self, frame, *, watch):
        service = frame["serviceId"]
        if service in self._retired:
            raise ContractError("service_publisher_retired")
        binding = (
            frame["hostScope"], frame["uid"], frame["bootId"], frame["clockDomain"],
            tuple(sorted((s["provider"], s["namespace"], s["configHome"], s["configHomeKind"])
                         for s in frame["sources"])),
        )
        position = frame["viewRevision"], frame["emittedBoottimeMs"]
        receipts = {
            (s["provider"], s["namespace"], c["name"]):
                (c["accepted"], c["sampledBoottimeMs"], c["expiresBoottimeMs"])
            for s in frame["sources"] for c in s["components"]
        }
        if service == self._service:
            if binding != self._binding or set(receipts) != set(self._receipts):
                raise ContractError("service_acquisition_scope_changed")
            if position[0] < self._position[0]:
                if watch:
                    return False
                raise ContractError("service_acquisition_superseded")
            if position[0] > self._position[0] and position[1] < self._position[1]:
                raise ContractError("service_acquisition_clock_regression")
            for key, current in receipts.items():
                previous = self._receipts[key]
                if current[0] < previous[0]:
                    raise ContractError("service_receipt_regression")
                if current[0] == previous[0] and current[1:] != previous[1:]:
                    raise ContractError("service_receipt_renewal")
                if (previous[1] is not None and current[1] is not None
                        and current[1] < previous[1]):
                    raise ContractError("service_receipt_clock_regression")
        elif self._service is not None:
            if len(self._retired) >= MAX_INCARNATIONS - 1:
                raise ContractError("service_incarnation_capacity")
            self._retired.add(self._service)
        # No await: concurrent operations cannot partially commit admission.
        # Same-revision frames can be queued on another connection before a
        # newer status emission. Their original receipts still describe the
        # same view; suppressing the initial watch would stall subscription.
        if service == self._service:
            position = position[0], max(position[1], self._position[1])
        self._service, self._binding = service, binding
        self._position, self._receipts = position, receipts
        return True

    async def _frames(self, operation):
        request = validate_request({"serviceProtocol": 2, "operation": operation, "hostScope": self.host})
        node = self._socket_policy()
        uid = os.geteuid()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        domain = os.readlink("/proc/self/ns/time")
        guard = StreamGuard(expected_host=self.host, expected_uid=uid)
        loop = asyncio.get_running_loop()
        if self._active >= MAX_CHANNELS:
            raise ContractError("service_acquisition_capacity")
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._active += 1
        try:
            peer.setblocking(False)
            await self._io(loop.sock_connect(peer, str(self.path)), min(2, self.timeout))
            current = self.path.lstat()
            if (current.st_dev, current.st_ino) != (node.st_dev, node.st_ino):
                raise ContractError("service_socket_changed")
            _pid, owner, _gid = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if owner != uid:
                raise ContractError("service_peer_ownership")
            await self._io(loop.sock_sendall(peer, (canonical(request) + "\n").encode()), min(2, self.timeout))
            pending = bytearray()
            while True:
                deadline = boottime_ms() + int(self.timeout * 1000)
                while b"\n" not in pending:
                    remaining = (deadline - boottime_ms()) / 1000
                    if remaining <= 0:
                        raise ContractError("service_transport_timeout")
                    part = await self._io(loop.sock_recv(peer, min(65536, MAX_FRAME_BYTES + 1 - len(pending))), remaining)
                    if not part:
                        raise ContractError("service_disconnected")
                    pending.extend(part)
                    if len(pending) > MAX_FRAME_BYTES and b"\n" not in pending:
                        raise ContractError("service_frame_limit")
                line, _, rest = pending.partition(b"\n")
                pending = bytearray(rest)
                frame = guard.accept(parse_frame(bytes(line) + b"\n"))
                now = boottime_ms()
                if (frame["bootId"] != boot or frame["clockDomain"] != domain
                        or frame["emittedBoottimeMs"] > now):
                    raise ContractError("service_clock_context")
                if frame["kind"] in {"gap", "error"}:
                    raise ContractError("service_native_gap_or_error")
                if operation == "status" and frame["kind"] != "status":
                    raise ContractError("service_operation_binding")
                if any(c["health"] in {"current", "partial"} and c["expiresBoottimeMs"] <= now
                       for s in frame["sources"] for c in s["components"]):
                    raise ContractError("service_frame_expired")
                if frame["kind"] != "heartbeat" and self._admit(frame, watch=operation == "watch"):
                    yield frame
                if operation == "status":
                    return
        finally:
            # Synchronous cleanup also survives repeated caller cancellation;
            # no writer, executor or background acquisition task is retained.
            peer.close()
            self._active -= 1

    async def snapshot(self):
        iterator = self._frames("status")
        try:
            return await anext(iterator)
        finally:
            await iterator.aclose()

    async def watch(self):
        from mesh_plus.api import CachedPublication

        iterator = self._frames("watch")
        try:
            async for frame in iterator:
                yield CachedPublication(frame, frame["serviceId"], {"viewRevision": frame["viewRevision"]})
        finally:
            await iterator.aclose()
