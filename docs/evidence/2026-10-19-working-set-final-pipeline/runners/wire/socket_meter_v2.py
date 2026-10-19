"""Bounded kernel-accepted byte meter for the private SDK pipeline fixture.

The meter observes only AF_UNIX stream sends that dispatch through the patched
Python socket class. It hashes the positive prefix returned by the kernel,
never retains payload bytes, and refuses known unmetered write APIs on socket
descriptors. This is diagnostic instrumentation, not a physical-wire counter.
"""

from __future__ import annotations

import errno
import hashlib
import os
import socket as _socket_module
import stat
import threading
import time
from pathlib import Path
from typing import Any


MAX_GENERATIONS = 128
TARGET_ROLES = frozenset({"native", "mesh"})
LOOP_CONTROL_ROLE = "loop_control"
_BASE_SOCKET = _socket_module.socket
_BASE_SOCKETPAIR = _socket_module.socketpair
_BASE_OS_WRITE = os.write
_BASE_OS_WRITEV = getattr(os, "writev", None)
_BASE_OS_SENDFILE = getattr(os, "sendfile", None)
_SOCK_TYPE_MASK = getattr(_socket_module, "SOCK_TYPE_MASK", 0xF)


class WireMeterError(RuntimeError):
    """Instrumentation could not preserve a trustworthy byte count."""


def _kind(sock_type: int) -> int:
    return int(sock_type) & _SOCK_TYPE_MASK


def _absolute_path(address: Any) -> str | None:
    if not isinstance(address, (str, bytes, os.PathLike)):
        return None
    value = os.fsdecode(os.fspath(address))
    if not value or value.startswith("\x00"):
        return None
    return os.path.abspath(value)


def _buffer_view(data: Any) -> memoryview:
    try:
        view = memoryview(data)
        if not view.contiguous:
            raise WireMeterError("noncontiguous_successful_send_buffer")
        return view.cast("B")
    except (TypeError, ValueError) as exc:
        raise WireMeterError("unsupported_successful_send_buffer") from exc


def _buffer_nbytes(data: Any) -> int | None:
    try:
        return memoryview(data).nbytes
    except (TypeError, ValueError):
        return None


def _buffers_nbytes(buffers: tuple[Any, ...]) -> int | None:
    total = 0
    for item in buffers:
        size = _buffer_nbytes(item)
        if size is None:
            return None
        total += size
    return total


def _bounded_iovec_limit() -> int:
    try:
        value = int(os.sysconf("SC_IOV_MAX"))
    except (AttributeError, OSError, ValueError):
        value = 1024
    if value < 1:
        value = 1024
    return min(value, 1024)


class WireMeter:
    """Install a socket subclass and metadata-only bypass guards.

    Call :meth:`register_endpoint` for each allowed server path before it is
    bound. Call :meth:`install` before target imports and event-loop creation.
    A custom loop factory must call :meth:`tag_loop_control_pair` with the
    selector loop's own socketpair before running it.
    """

    def __init__(self, *, max_generations: int = MAX_GENERATIONS) -> None:
        if max_generations < 1 or max_generations > MAX_GENERATIONS:
            raise ValueError("generation_cap_out_of_range")
        self.max_generations = max_generations
        self._lock = threading.RLock()
        self._pair_local = threading.local()
        self._records: list[dict[str, Any]] = []
        self._by_fd: dict[int, int] = {}
        self._hashers: dict[int, Any] = {}
        self._endpoints: dict[str, dict[str, Any]] = {}
        self._installed = False
        self._next_generation = 1
        self._next_pair = 1
        self._unsupported: list[dict[str, Any]] = []
        self._counting_socket_class: type[_BASE_SOCKET] | None = None
        self._original_os: dict[str, Any] = {}
        self._patched_os: dict[str, Any] = {}
        self._original_socket = _BASE_SOCKET
        self._original_socketpair = _BASE_SOCKETPAIR

    @property
    def installed(self) -> bool:
        return self._installed

    def register_endpoint(self, path: str | os.PathLike[str], role: str) -> None:
        if role not in TARGET_ROLES:
            raise ValueError("unsupported_endpoint_role")
        absolute = _absolute_path(path)
        if absolute is None:
            raise ValueError("filesystem_endpoint_required")
        with self._lock:
            prior = self._endpoints.get(absolute)
            if prior is not None and prior["role"] != role:
                raise WireMeterError("endpoint_role_conflict")
            self._endpoints[absolute] = {
                "role": role,
                "device": None,
                "inode": None,
                "bindCount": 0,
            }

    def _new_pair_token(self) -> int:
        with self._lock:
            value = self._next_pair
            self._next_pair += 1
            return value

    def _record_for(self, generation: int | None) -> dict[str, Any] | None:
        if generation is None or generation < 1 or generation > len(self._records):
            return None
        record = self._records[generation - 1]
        if record["generation"] != generation:
            raise WireMeterError("generation_registry_corrupt")
        return record

    def _register_socket(self, sock: _BASE_SOCKET) -> int | None:
        fd = sock.fileno()
        if fd < 0:
            raise WireMeterError("socket_registered_without_fd")
        try:
            stat_result = os.fstat(fd)
            actual_type = int(sock.getsockopt(_socket_module.SOL_SOCKET, _socket_module.SO_TYPE))
        except OSError as exc:
            raise WireMeterError("socket_registration_failed") from exc
        with self._lock:
            if len(self._records) >= self.max_generations:
                raise WireMeterError("socket_generation_cap_exceeded")
            old_generation = self._by_fd.get(fd)
            if old_generation is not None:
                old = self._record_for(old_generation)
                if old is not None and old["open"]:
                    raise WireMeterError("live_fd_reused_without_close")
            generation = self._next_generation
            self._next_generation += 1
            pair_token = getattr(self._pair_local, "token", None)
            record: dict[str, Any] = {
                "generation": generation,
                "fd": fd,
                "device": int(stat_result.st_dev),
                "inode": int(stat_result.st_ino),
                "family": int(sock.family),
                "socketType": actual_type,
                "kind": _kind(actual_type),
                "role": None,
                "side": None,
                "endpointDevice": None,
                "endpointInode": None,
                "listenerGeneration": None,
                "pairToken": pair_token,
                "connectAttempts": 0,
                "connectStatus": "created",
                "open": True,
                "detached": False,
                "createdNs": time.monotonic_ns(),
                "closedNs": None,
                "attempts": 0,
                "positiveWrites": 0,
                "zeroWrites": 0,
                "bytesKernelAccepted": 0,
                "sha256": None,
                "methods": {},
                "errors": {},
                "concurrentWriteDetected": False,
                "writeInProgress": False,
                "lastWriteNs": None,
            }
            self._records.append(record)
            self._by_fd[fd] = generation
            self._hashers[generation] = hashlib.sha256()
            return generation

    def _meta_for_socket(self, sock: _BASE_SOCKET) -> dict[str, Any] | None:
        generation = getattr(sock, "_wire_meter_generation", None)
        return self._record_for(generation)

    def _verify_record_fd(self, record: dict[str, Any], fd: int) -> None:
        if not record["open"] or record["detached"] or fd < 0:
            raise WireMeterError("write_on_closed_or_detached_socket")
        try:
            current = os.fstat(fd)
        except OSError as exc:
            raise WireMeterError("socket_fd_not_live") from exc
        if (int(current.st_dev), int(current.st_ino)) != (
            record["device"], record["inode"]
        ):
            raise WireMeterError("socket_fd_identity_changed")
        if self._by_fd.get(fd) != record["generation"]:
            raise WireMeterError("socket_fd_generation_changed")

    def _set_role(self, record: dict[str, Any], *, role: str, side: str,
                  endpoint: dict[str, Any], listener_generation: int | None = None) -> None:
        record["role"] = role
        record["side"] = side
        record["endpointDevice"] = endpoint["device"]
        record["endpointInode"] = endpoint["inode"]
        record["listenerGeneration"] = listener_generation

    def _record_bind(self, sock: _BASE_SOCKET, address: Any) -> None:
        path = _absolute_path(address)
        if path is None:
            return
        generation = getattr(sock, "_wire_meter_generation", None)
        record = self._record_for(generation)
        if record is None or record["kind"] != _socket_module.SOCK_STREAM:
            return
        expected = self._endpoints.get(path)
        if expected is None:
            return
        try:
            endpoint_stat = os.lstat(path)
        except OSError as exc:
            raise WireMeterError("bound_endpoint_identity_missing") from exc
        if not stat.S_ISSOCK(endpoint_stat.st_mode):
            raise WireMeterError("bound_endpoint_not_socket")
        with self._lock:
            if expected["device"] is not None:
                if (expected["device"], expected["inode"]) != (
                    int(endpoint_stat.st_dev), int(endpoint_stat.st_ino)
                ):
                    raise WireMeterError("endpoint_inode_changed")
            expected["device"] = int(endpoint_stat.st_dev)
            expected["inode"] = int(endpoint_stat.st_ino)
            expected["bindCount"] += 1
            self._set_role(record, role=expected["role"], side="server", endpoint=expected)

    def _record_connect(self, sock: _BASE_SOCKET, address: Any) -> None:
        path = _absolute_path(address)
        generation = getattr(sock, "_wire_meter_generation", None)
        record = self._record_for(generation)
        if path is None or record is None or record["kind"] != _socket_module.SOCK_STREAM:
            return
        expected = self._endpoints.get(path)
        if expected is None:
            return
        try:
            endpoint_stat = os.lstat(path)
        except OSError as exc:
            raise WireMeterError("connect_endpoint_identity_missing") from exc
        if not stat.S_ISSOCK(endpoint_stat.st_mode):
            raise WireMeterError("connect_endpoint_not_socket")
        expected_identity = (expected["device"], expected["inode"])
        actual_identity = (int(endpoint_stat.st_dev), int(endpoint_stat.st_ino))
        if expected_identity != (None, None) and expected_identity != actual_identity:
            raise WireMeterError("connect_endpoint_identity_mismatch")
        if expected_identity == (None, None):
            # A client must not establish role identity from an unobserved server.
            raise WireMeterError("connect_before_registered_bind")
        with self._lock:
            self._set_role(record, role=expected["role"], side="client", endpoint=expected)
            record["connectAttempts"] += 1
            record["connectStatus"] = "pending"

    def _inherit_accept(self, listener: _BASE_SOCKET, accepted: _BASE_SOCKET) -> None:
        listener_record = self._meta_for_socket(listener)
        accepted_record = self._meta_for_socket(accepted)
        if listener_record is None or accepted_record is None:
            return
        if listener_record["role"] not in TARGET_ROLES:
            return
        with self._lock:
            self._set_role(
                accepted_record,
                role=listener_record["role"],
                side="server",
                endpoint={
                    "device": listener_record["endpointDevice"],
                    "inode": listener_record["endpointInode"],
                },
                listener_generation=listener_record["generation"],
            )
            accepted_record["connectStatus"] = "accepted"

    def tag_loop_control_pair(self, left: _BASE_SOCKET, right: _BASE_SOCKET) -> None:
        """Tag only the exact socketpair recorded during socketpair creation."""
        left_record = self._meta_for_socket(left)
        right_record = self._meta_for_socket(right)
        if left_record is None or right_record is None:
            raise WireMeterError("loop_control_pair_untracked")
        pair_token = left_record["pairToken"]
        if (
            pair_token is None
            or right_record["pairToken"] != pair_token
            or left_record["kind"] != _socket_module.SOCK_STREAM
            or right_record["kind"] != _socket_module.SOCK_STREAM
            or left.family != _socket_module.AF_UNIX
            or right.family != _socket_module.AF_UNIX
        ):
            raise WireMeterError("loop_control_pair_identity_mismatch")
        with self._lock:
            left_record["role"] = LOOP_CONTROL_ROLE
            left_record["side"] = "selector-client"
            right_record["role"] = LOOP_CONTROL_ROLE
            right_record["side"] = "selector-server"

    def _begin_write(self, sock: _BASE_SOCKET, method: str,
                     requested: int | None) -> dict[str, Any] | None:
        record = self._meta_for_socket(sock)
        if record is None or record["kind"] != _socket_module.SOCK_STREAM:
            return None
        fd = sock.fileno()
        self._verify_record_fd(record, fd)
        if record["role"] not in TARGET_ROLES and record["role"] != LOOP_CONTROL_ROLE:
            self._unsupported_write(record, method, "unclassified_stream_write")
        with self._lock:
            if record["writeInProgress"]:
                record["concurrentWriteDetected"] = True
                self._unsupported_write(record, method, "concurrent_same_socket_write")
            record["writeInProgress"] = True
            record["attempts"] += 1
            record["methods"][method] = record["methods"].get(method, 0) + 1
            record["lastRequestedBytes"] = (
                max(0, int(requested)) if requested is not None else None
            )
        return record

    def _end_write(self, record: dict[str, Any] | None, method: str,
                   buffers: tuple[Any, ...], result: int | None,
                   error: BaseException | None = None) -> None:
        if record is None:
            return
        with self._lock:
            if error is not None:
                key = f"{type(error).__name__}:{getattr(error, 'errno', None)}"
                record["errors"][key] = record["errors"].get(key, 0) + 1
            elif result is not None and result > 0:
                remaining = int(result)
                if remaining > sum(_buffer_view(item).nbytes for item in buffers):
                    record["writeInProgress"] = False
                    raise WireMeterError("kernel_return_exceeds_iovec")
                hasher = self._hashers[record["generation"]]
                for item in buffers:
                    if remaining <= 0:
                        break
                    view = _buffer_view(item)
                    take = min(remaining, view.nbytes)
                    hasher.update(view[:take])
                    remaining -= take
                if remaining:
                    record["writeInProgress"] = False
                    raise WireMeterError("accepted_prefix_not_hashable")
                record["positiveWrites"] += 1
                record["bytesKernelAccepted"] += int(result)
                record["sha256"] = hasher.hexdigest()
                if (record["role"] in TARGET_ROLES
                        and record["side"] == "client"
                        and record["connectStatus"] == "pending"):
                    record["connectStatus"] = "kernel_send_accepted"
            else:
                record["zeroWrites"] += 1
            record["lastWriteNs"] = time.monotonic_ns()
            record["writeInProgress"] = False

    def _unsupported_write(self, record: dict[str, Any] | None, operation: str,
                           reason: str) -> None:
        item = {
            "operation": operation,
            "reason": reason,
            "generation": record["generation"] if record else None,
            "fd": record["fd"] if record else None,
            "role": record["role"] if record else None,
            "atNs": time.monotonic_ns(),
        }
        with self._lock:
            if len(self._unsupported) < MAX_GENERATIONS:
                self._unsupported.append(item)
        raise WireMeterError(reason)

    def _close_socket(self, sock: _BASE_SOCKET, *, detached: bool = False) -> None:
        record = self._meta_for_socket(sock)
        if record is None:
            return
        fd = sock.fileno()
        with self._lock:
            if record["open"]:
                record["open"] = False
                record["detached"] = detached
                record["closedNs"] = time.monotonic_ns()
                if self._by_fd.get(record["fd"]) == record["generation"]:
                    self._by_fd.pop(record["fd"], None)
            if fd >= 0 and fd != record["fd"]:
                raise WireMeterError("socket_fd_changed_before_close")

    def _classify_raw_socket_fd(self, fd: int, operation: str) -> None:
        try:
            current = os.fstat(fd)
        except OSError:
            return
        if not stat.S_ISSOCK(current.st_mode):
            stale_generation = self._by_fd.get(fd)
            stale_record = self._record_for(stale_generation)
            if stale_record is not None and stale_record["open"]:
                self._unsupported_write(
                    stale_record, operation, "tracked_socket_fd_reused_without_close"
                )
            return
        generation = self._by_fd.get(fd)
        record = self._record_for(generation)
        if record is None:
            self._unsupported_write(None, operation, "unclassified_socket_fd_write")
        if (record["device"], record["inode"]) != (
            int(current.st_dev), int(current.st_ino)
        ):
            self._unsupported_write(record, operation, "socket_fd_identity_changed")
        if record["family"] != _socket_module.AF_UNIX:
            self._unsupported_write(record, operation, "unclassified_socket_fd_write")
        # Independent AF_UNIX SOCK_SEQPACKET provider/worker sockets are
        # outside this collect=False stream meter and remain untouched.
        if record["kind"] == _socket_module.SOCK_STREAM:
            self._unsupported_write(record, operation, "unmetered_stream_fd_operation")
        if (record["family"] == _socket_module.AF_UNIX
                and record["kind"] != getattr(_socket_module, "SOCK_SEQPACKET", -1)):
            self._unsupported_write(record, operation, "unregistered_unix_socket_fd_operation")

    def install(self) -> None:
        if self._installed:
            raise WireMeterError("meter_already_installed")
        meter = self
        self._original_socket = _socket_module.socket
        self._original_socketpair = _socket_module.socketpair
        if self._original_socket is not _BASE_SOCKET or self._original_socketpair is not _BASE_SOCKETPAIR:
            raise WireMeterError("socket_factory_changed_before_install")

        class CountingSocket(_BASE_SOCKET):
            def __init__(self, family: int = -1, type: int = -1, proto: int = -1,
                         fileno: int | None = None) -> None:
                super().__init__(family, type, proto, fileno)
                try:
                    self._wire_meter_generation = meter._register_socket(self)
                except BaseException:
                    super().close()
                    raise

            def bind(self, address: Any) -> None:
                record = meter._meta_for_socket(self)
                if self.family != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.bind", "nonlocal_socket_operation_disallowed")
                if (record is not None
                        and record["kind"] == _socket_module.SOCK_STREAM
                        and _absolute_path(address) not in meter._endpoints):
                    meter._unsupported_write(record, "socket.bind", "unregistered_unix_stream_endpoint")
                super().bind(address)
                meter._record_bind(self, address)

            def connect(self, address: Any) -> None:
                record = meter._meta_for_socket(self)
                if self.family != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.connect", "nonlocal_socket_operation_disallowed")
                if (record is not None
                        and record["kind"] == _socket_module.SOCK_STREAM
                        and _absolute_path(address) not in meter._endpoints):
                    meter._unsupported_write(record, "socket.connect", "unregistered_unix_stream_endpoint")
                meter._record_connect(self, address)
                try:
                    super().connect(address)
                except OSError as exc:
                    record = meter._meta_for_socket(self)
                    if record is not None and record["role"] in TARGET_ROLES:
                        meter._note_connect_error(record, exc)
                    raise
                else:
                    meter._note_connect_success(meter._meta_for_socket(self))

            def connect_ex(self, address: Any) -> int:
                record = meter._meta_for_socket(self)
                if self.family != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.connect_ex", "nonlocal_socket_operation_disallowed")
                if (record is not None
                        and record["kind"] == _socket_module.SOCK_STREAM
                        and _absolute_path(address) not in meter._endpoints):
                    meter._unsupported_write(record, "socket.connect_ex", "unregistered_unix_stream_endpoint")
                meter._record_connect(self, address)
                try:
                    result = super().connect_ex(address)
                except OSError as exc:
                    record = meter._meta_for_socket(self)
                    if record is not None and record["role"] in TARGET_ROLES:
                        meter._note_connect_error(record, exc)
                    raise
                record = meter._meta_for_socket(self)
                if record is not None and record["role"] in TARGET_ROLES:
                    meter._note_connect_errno(record, result)
                return result

            def listen(self, backlog: int = _socket_module.SOMAXCONN) -> None:
                record = meter._meta_for_socket(self)
                if self.family != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.listen", "nonlocal_socket_operation_disallowed")
                if (record is not None
                        and record["kind"] == _socket_module.SOCK_STREAM
                        and record["role"] not in TARGET_ROLES):
                    meter._unsupported_write(record, "socket.listen", "unregistered_unix_stream_endpoint")
                super().listen(backlog)

            def accept(self) -> tuple[_BASE_SOCKET, Any]:
                accepted, address = super().accept()
                meter._inherit_accept(self, accepted)
                return accepted, address

            def send(self, data: Any, flags: int = 0) -> int:
                record = meter._meta_for_socket(self)
                if record is not None and record["family"] != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.send", "nonlocal_socket_operation_disallowed")
                if record is not None and record["kind"] == _socket_module.SOCK_DGRAM:
                    meter._unsupported_write(record, "socket.send", "unregistered_unix_datagram_write")
                if record is None or record["kind"] != _socket_module.SOCK_STREAM:
                    return super().send(data, flags)
                requested = _buffer_nbytes(data)
                active = meter._begin_write(self, "send", requested)
                try:
                    result = super().send(data, flags)
                except BaseException as exc:
                    meter._end_write(active, "send", (), None, exc)
                    raise
                meter._end_write(active, "send", (data,), result)
                return result

            def sendmsg(self, buffers: Any, ancdata: Any = (), flags: int = 0,
                        address: Any = None) -> int:
                base_sendmsg = getattr(_BASE_SOCKET, "sendmsg", None)
                if base_sendmsg is None:
                    raise NotImplementedError("socket_sendmsg_unavailable")
                record = meter._meta_for_socket(self)
                if record is not None and record["family"] != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.sendmsg", "nonlocal_socket_operation_disallowed")
                if record is not None and record["kind"] == _socket_module.SOCK_DGRAM:
                    meter._unsupported_write(record, "socket.sendmsg", "unregistered_unix_datagram_write")
                if record is None or record["kind"] != _socket_module.SOCK_STREAM:
                    return base_sendmsg(self, buffers, ancdata, flags, address)
                iov_max = _bounded_iovec_limit()
                materialized_list = []
                for item in buffers:
                    if len(materialized_list) >= iov_max:
                        raise WireMeterError("iovec_count_exceeds_SC_IOV_MAX")
                    materialized_list.append(item)
                materialized = tuple(materialized_list)
                requested = _buffers_nbytes(materialized)
                active = meter._begin_write(self, "sendmsg", requested)
                try:
                    result = base_sendmsg(self, materialized, ancdata, flags, address)
                except BaseException as exc:
                    meter._end_write(active, "sendmsg", materialized, None, exc)
                    raise
                meter._end_write(active, "sendmsg", materialized, result)
                return result

            def sendall(self, data: Any, flags: int = 0) -> None:
                record = meter._meta_for_socket(self)
                if record is not None and record["family"] != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.sendall", "nonlocal_socket_operation_disallowed")
                if record is not None and record["kind"] == _socket_module.SOCK_STREAM:
                    meter._unsupported_write(record, "socket.sendall", "unsupported_sendall_bypass")
                return super().sendall(data, flags)

            def sendfile(self, file: Any, offset: int = 0, count: int | None = None) -> int:
                record = meter._meta_for_socket(self)
                if record is not None and record["family"] != _socket_module.AF_UNIX:
                    meter._unsupported_write(record, "socket.sendfile", "nonlocal_socket_operation_disallowed")
                if record is not None and record["kind"] == _socket_module.SOCK_STREAM:
                    meter._unsupported_write(record, "socket.sendfile", "unsupported_sendfile_bypass")
                return super().sendfile(file, offset, count)

            def sendto(self, *args: Any, **kwargs: Any) -> int:
                record = meter._meta_for_socket(self)
                if (record is not None
                        and record["family"] == _socket_module.AF_UNIX
                        and record["kind"] == getattr(_socket_module, "SOCK_SEQPACKET", -1)):
                    return super().sendto(*args, **kwargs)
                meter._unsupported_write(record, "socket.sendto", "unregistered_socket_sendto")

            def close(self) -> None:
                meter._close_socket(self)
                super().close()

            def detach(self) -> int:
                meter._close_socket(self, detached=True)
                return super().detach()

        CountingSocket.__name__ = "WireV2CountingSocket"
        CountingSocket.__qualname__ = "WireV2CountingSocket"
        self._counting_socket_class = CountingSocket
        _socket_module.socket = CountingSocket
        _socket_module.socketpair = self._socketpair_wrapper
        self._patch_os()
        self._installed = True

    def _socketpair_wrapper(self, family: int | None = None,
                            type: int = _socket_module.SOCK_STREAM,
                            proto: int = 0) -> tuple[_BASE_SOCKET, _BASE_SOCKET]:
        with self._lock:
            if len(self._records) + 2 > self.max_generations:
                raise WireMeterError("socket_generation_cap_exceeded")
        token = self._new_pair_token()
        prior = getattr(self._pair_local, "token", None)
        self._pair_local.token = token
        try:
            return self._original_socketpair(family, type, proto)
        finally:
            self._pair_local.token = prior

    def _patch_os(self) -> None:
        self._original_os = {
            "write": os.write,
            "writev": getattr(os, "writev", None),
            "sendfile": getattr(os, "sendfile", None),
        }

        def guarded_write(fd: int, data: Any) -> int:
            self._classify_raw_socket_fd(fd, "os.write")
            return _BASE_OS_WRITE(fd, data)

        os.write = guarded_write
        if _BASE_OS_WRITEV is not None:
            def guarded_writev(fd: int, buffers: Any) -> int:
                self._classify_raw_socket_fd(fd, "os.writev")
                return _BASE_OS_WRITEV(fd, buffers)

            os.writev = guarded_writev
        if _BASE_OS_SENDFILE is not None:
            def guarded_sendfile(*args: Any, **kwargs: Any) -> int:
                if args:
                    descriptors = args[:2]
                else:
                    descriptors = (kwargs.get("out_fd"), kwargs.get("in_fd"))
                for fd in descriptors:
                    if fd is not None:
                        self._classify_raw_socket_fd(fd, "os.sendfile")
                return _BASE_OS_SENDFILE(*args, **kwargs)

            os.sendfile = guarded_sendfile
        self._patched_os = {
            "write": os.write,
            "writev": getattr(os, "writev", None),
            "sendfile": getattr(os, "sendfile", None),
        }

    def _note_connect_error(self, record: dict[str, Any], error: BaseException) -> None:
        error_number = getattr(error, "errno", None)
        with self._lock:
            if error_number in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
                record["connectStatus"] = "pending"
                key = f"connect:pending:{type(error).__name__}:{error_number}"
            else:
                record["connectStatus"] = "failed"
                key = f"connect:{type(error).__name__}:{error_number}"
            record["errors"][key] = record["errors"].get(key, 0) + 1

    def _note_connect_success(self, record: dict[str, Any] | None) -> None:
        if record is None:
            return
        with self._lock:
            record["connectStatus"] = "connected"

    def _note_connect_errno(self, record: dict[str, Any], error_number: Any,
                            error_type: str = "OSError") -> None:
        with self._lock:
            if error_number in (0, errno.EISCONN):
                record["connectStatus"] = "connected"
                return
            if error_number in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
                record["connectStatus"] = "pending"
                key = f"connect:pending:{error_type}:{error_number}"
            else:
                record["connectStatus"] = "failed"
                key = f"connect:{error_type}:{error_number}"
            record["errors"][key] = record["errors"].get(key, 0) + 1

    def uninstall(self) -> None:
        if not self._installed:
            return
        if _socket_module.socket is not self._counting_socket_class:
            raise WireMeterError("socket_factory_changed_before_uninstall")
        if _socket_module.socketpair != self._socketpair_wrapper:
            # Bound-method equality is stable for the same instance/function.
            raise WireMeterError("socketpair_factory_changed_before_uninstall")
        if (os.write is not self._patched_os.get("write")
                or (self._patched_os.get("writev") is not None
                    and os.writev is not self._patched_os["writev"])
                or (self._patched_os.get("sendfile") is not None
                    and os.sendfile is not self._patched_os["sendfile"])):
            raise WireMeterError("os_write_guard_changed_before_uninstall")
        _socket_module.socket = self._original_socket
        _socket_module.socketpair = self._original_socketpair
        os.write = self._original_os["write"]
        if self._original_os.get("writev") is not None:
            os.writev = self._original_os["writev"]
        if self._original_os.get("sendfile") is not None:
            os.sendfile = self._original_os["sendfile"]
        self._installed = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            records = []
            totals: dict[str, dict[str, Any]] = {}
            for item in self._records:
                record = {key: value for key, value in item.items()
                          if key not in {"writeInProgress", "pairToken"}}
                hasher = self._hashers.get(item["generation"])
                if hasher is not None:
                    record["sha256"] = hasher.hexdigest()
                record["writeInProgress"] = bool(item["writeInProgress"])
                records.append(record)
                role = item["role"]
                side = item["side"]
                if role not in TARGET_ROLES or side is None:
                    continue
                key = f"{role}:{side}"
                total = totals.setdefault(key, {
                    "role": role,
                    "side": side,
                    "connections": 0,
                    "attempts": 0,
                    "positiveWrites": 0,
                    "zeroWrites": 0,
                    "bytesKernelAccepted": 0,
                    "sha256": hashlib.sha256(),
                    "openConnections": 0,
                    "errors": {},
                })
                total["connections"] += 1
                total["attempts"] += item["attempts"]
                total["positiveWrites"] += item["positiveWrites"]
                total["zeroWrites"] += item["zeroWrites"]
                total["bytesKernelAccepted"] += item["bytesKernelAccepted"]
                if item["open"]:
                    total["openConnections"] += 1
                for error_key, count in item["errors"].items():
                    total["errors"][error_key] = total["errors"].get(error_key, 0) + count
                # Aggregate digest is explicitly a per-connection digest list
                # hash, not a concatenated byte-stream digest across sockets.
                total["sha256"].update(
                    f"{item['generation']}:{item['sha256'] or hashlib.sha256().hexdigest()}\n".encode()
                )
            for value in totals.values():
                value["sha256"] = value["sha256"].hexdigest()
            return {
                "schema": "private.sdk-pipeline.socket-meter.v2",
                "basis": "positive byte prefixes returned by kernel send/sendmsg on classified AF_UNIX SOCK_STREAM descriptors",
                "perConnectionHashBasis": "concatenated positive accepted prefixes in serialized write-call completion order; concurrent same-socket writes are rejected",
                "aggregateHashBasis": "SHA-256 over generation number and per-connection digest records, not a cross-connection byte stream",
                "deliveryTotalsIncludeOnlyRoles": ["native", "mesh"],
                "loopControlBytesIncludedInDeliveryTotals": False,
                "physicalWireClaim": False,
                "validatedPeerReadClaim": False,
                "payloadRetained": False,
                "nonlocalSocketOperationsAllowed": False,
                "registryScope": "all socket generations; only registered native/Mesh AF_UNIX stream writes are measured",
                "maxGenerations": self.max_generations,
                "generationCount": len(self._records),
                "endpoints": [
                    {
                        "role": value["role"],
                        "device": value["device"],
                        "inode": value["inode"],
                        "bindCount": value["bindCount"],
                    }
                    for value in self._endpoints.values()
                ],
                "totalsByRoleAndSide": sorted(totals.values(), key=lambda item: (item["role"], item["side"])),
                "connections": records,
                "unsupportedWrites": list(self._unsupported),
            }


def selector_loop_factory(meter: WireMeter):
    """Return a loop factory that verifies and tags only its own self-pipe."""
    import asyncio

    def factory():
        loop = asyncio.SelectorEventLoop()
        left = getattr(loop, "_ssock", None)
        right = getattr(loop, "_csock", None)
        if left is None or right is None:
            loop.close()
            raise WireMeterError("selector_loop_control_pair_unavailable")
        try:
            meter.tag_loop_control_pair(left, right)
        except BaseException:
            loop.close()
            raise
        return loop

    return factory


def run_with_meter(meter: WireMeter, awaitable: Any) -> Any:
    """Run one coroutine with the meter installed before loop construction."""
    import asyncio

    if not meter.installed:
        raise WireMeterError("meter_not_installed")
    with asyncio.Runner(loop_factory=selector_loop_factory(meter)) as runner:
        return runner.run(awaitable)
