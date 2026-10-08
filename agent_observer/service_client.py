"""Explicit Unix read transport; no autostart, provider access or fallback."""

import os
import socket
import stat
import struct
import time
from pathlib import Path

from .contract import ContractError, canonical
from .service_contract import MAX_FRAME_BYTES, StreamGuard, parse_frame, validate_request


def frames(path, *, host_scope, operation="watch", timeout=15.0):
    if type(timeout) not in (int, float) or not 1 <= timeout <= 60:
        raise ContractError("service_client_timeout")
    path = Path(path)
    if not path.is_absolute() or path.parent.resolve() != path.parent:
        raise ContractError("service_socket_path")
    directory, node = path.parent.stat(), path.lstat()
    uid = os.geteuid()
    if directory.st_uid != uid or stat.S_IMODE(directory.st_mode) != 0o700 or node.st_uid != uid or not stat.S_ISSOCK(node.st_mode) or stat.S_IMODE(node.st_mode) != 0o600:
        raise ContractError("service_socket_ownership")
    request = validate_request({"serviceProtocol": 2, "operation": operation, "hostScope": host_scope})
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    domain = os.readlink("/proc/self/ns/time")
    guard = StreamGuard(expected_host=host_scope, expected_uid=uid)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(timeout)
        peer.connect(str(path))
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (node.st_dev, node.st_ino):
            raise ContractError("service_socket_changed")
        _pid, owner, _gid = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if owner != uid:
            raise ContractError("service_peer_ownership")
        peer.sendall((canonical(request) + "\n").encode())
        pending = bytearray()
        while True:
            deadline = time.clock_gettime(time.CLOCK_BOOTTIME) + timeout
            while b"\n" not in pending:
                remaining = deadline - time.clock_gettime(time.CLOCK_BOOTTIME)
                if remaining <= 0:
                    raise ContractError("service_transport_timeout")
                peer.settimeout(remaining)
                part = peer.recv(min(65536, MAX_FRAME_BYTES + 1 - len(pending)))
                if not part:
                    raise ContractError("service_disconnected")
                pending.extend(part)
                if len(pending) > MAX_FRAME_BYTES and b"\n" not in pending:
                    raise ContractError("service_frame_limit")
            line, _, rest = pending.partition(b"\n")
            pending = bytearray(rest)
            frame = guard.accept(parse_frame(bytes(line) + b"\n"))
            if frame["bootId"] != boot or frame["clockDomain"] != domain:
                raise ContractError("service_clock_context")
            now = int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
            if frame["emittedBoottimeMs"] > now:
                raise ContractError("service_clock_context")
            if any(c["health"] in {"current", "partial"} and c["expiresBoottimeMs"] <= now for s in frame["sources"] for c in s["components"]):
                raise ContractError("service_frame_expired")
            if frame["kind"] == "error":
                raise ContractError(frame["reason"])
            yield frame
            if operation != "watch":
                return
