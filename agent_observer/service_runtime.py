"""Private local IPC, bounded fan-out and Observer-owned collection workers."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from ._image_memo import ImageMemo
from ._image_memo import receive as receive_memo
from ._image_memo import send as send_memo
from .active_contract import MAX_REQUEST_BYTES as MAX_ACTIVE_REQUEST_BYTES
from .active_contract import validate_request as validate_active_request
from .bounded_json import decode_document
from .contract import MAX_SNAPSHOT_BYTES, ContractError, canonical, parse_snapshot
from .observation_scheduler import Scheduler
from .service_contract import MAX_OVERHEAD_BYTES, MAX_REQUEST_BYTES, validate_request
from .sync_contract import (
    MAX_REQUEST_BYTES as MAX_SYNC_REQUEST_BYTES,
)
from .sync_contract import (
    MAX_REQUEST_DEPTH as MAX_SYNC_REQUEST_DEPTH,
)
from .sync_contract import (
    MAX_REQUEST_NODES as MAX_SYNC_REQUEST_NODES,
)
from .sync_contract import (
    validate_request as validate_sync_request,
)
from .sync_native import MAX_HEAD_BYTES, MAX_MESSAGE_BYTES
from .workspace import MAX_CONFIG_BYTES, validate_config

MAX_SYNC_ENCODED_BYTES = 32 * 1024 * 1024


def birth(pid):
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


class Endpoint:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = None
        self.listener = None
        self.identity = None

    def __enter__(self):
        if not self.path.is_absolute() or len(os.fsencode(self.path)) > 100 or self.path.parent.resolve() != self.path.parent:
            raise ValueError("service_socket_path")
        self.path.parent.mkdir(mode=0o700, exist_ok=True)
        parent = self.path.parent.stat()
        if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            raise ValueError("service_socket_directory")
        try:
            self.lock = os.open(str(self.path) + ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            info = os.fstat(self.lock)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError("service_lock_ownership")
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("service_already_running") from None
            if self.path.exists() or self.path.is_symlink():
                info = self.path.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
                    raise ValueError("service_socket_foreign")
                os.lseek(self.lock, 0, os.SEEK_SET)
                try:
                    record = json.loads(os.read(self.lock, 4096))
                    if record["inode"] != info.st_ino or record["device"] != info.st_dev:
                        raise ValueError("service_socket_foreign")
                    try:
                        if birth(record["pid"]) == record["birth"]:
                            raise ValueError("service_owner_alive")
                    except FileNotFoundError:
                        pass
                except (KeyError, json.JSONDecodeError):
                    raise ValueError("service_socket_foreign") from None
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.2)
                    try:
                        probe.connect(str(self.path))
                    except OSError as error:
                        if error.errno not in {errno.ECONNREFUSED, errno.ENOENT}:
                            raise ValueError("service_socket_busy") from None
                    else:
                        raise ValueError("service_socket_busy")
                if self.path.lstat().st_ino != info.st_ino:
                    raise ValueError("service_socket_changed")
                self.path.unlink()
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.bind(str(self.path))
            os.chmod(self.path, 0o600)
            info = self.path.lstat()
            self.identity = info.st_dev, info.st_ino
            record = canonical({"pid": os.getpid(), "birth": birth(os.getpid()), "device": info.st_dev, "inode": info.st_ino}).encode()
            os.ftruncate(self.lock, 0)
            os.lseek(self.lock, 0, os.SEEK_SET)
            os.write(self.lock, record)
            self.listener.listen(16)
            self.listener.setblocking(False)
            return self.listener
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_args):
        if self.listener:
            self.listener.close()
        if self.identity:
            try:
                info = self.path.lstat()
                if (info.st_dev, info.st_ino) == self.identity and stat.S_ISSOCK(info.st_mode):
                    self.path.unlink()
            except FileNotFoundError:
                pass
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None


@dataclass(eq=False)
class Peer:
    sock: socket.socket
    since: int
    incoming: bytearray = field(default_factory=bytearray)
    family: str = "service"
    operation: str | None = None
    sequence: int = 0
    parts: tuple = ()
    part: int = 0
    offset: int = 0
    sent_revision: int = 0
    frame_revision: int = 0
    body_revision: int | tuple[str, int] | None = None
    pending: int | None = None
    skipped: bool = False
    recover: bool = False
    write_started: int = 0
    last_sent: int = 0
    sync_view: str | None = None
    sync_cursor: tuple | None = None
    sync_send_cursor: tuple | None = None
    sync_pending_cursor: tuple | None = None
    sync_close: bool = False
    sync_pins: object | None = None


@dataclass
class Worker:
    job: object
    process: object
    buffer: bytearray = field(default_factory=bytearray)
    eof: bool = False


class Runtime:
    def __init__(self, state, path, *, scheduler=None, worker_factory=None, collect=True,
                 max_clients=16, encoded_limit=64 * 1024 * 1024, io_timeout_ms=5000,
                 heartbeat_ms=10000, workspace_config=None, native_hints=False,
                 hint_factory=None, hint_diagnostics=None):
        if (collect and worker_factory is None) or (native_hints and hint_factory is None):
            from .adapters import select_adapters
            select_adapters(list(state.configs))
        if not 1 <= max_clients <= 16 or encoded_limit < MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES or not 100 <= io_timeout_ms <= 30000:
            raise ValueError("service_runtime_limits")
        self.state, self.path = state, Path(path)
        # Own an immutable startup value, independent of the caller/file. Only
        # history jobs receive it; runtime samples cannot enrich/freshen it.
        configured = workspace_config if workspace_config is not None else {"roots": [], "projects": []}
        validate_config(configured)
        self.workspace_config = decode_document(canonical(configured).encode(), max_bytes=MAX_CONFIG_BYTES)
        self.scheduler = scheduler or Scheduler(state.configs)
        self.worker_factory = worker_factory or self._spawn
        self.collect = collect
        self.max_clients, self.encoded_limit = max_clients, encoded_limit
        self.io_timeout, self.heartbeat = io_timeout_ms, heartbeat_ms
        self.selector = selectors.DefaultSelector()
        self.peers = set()
        self.workers = {}
        self.bodies = {}
        self.latest = {}
        self.counts = {"acceptedConnections": 0, "droppedConnections": 0, "frames": 0, "workerStarts": 0}
        self.native_hints, self.hint_factory = native_hints, hint_factory
        self.hint_diagnostics, self.hints = hint_diagnostics, None
        self.image_memos = {provider: ImageMemo(provider) for provider in state.configs}
        self._sync_reserver = self._reserve_sync

    def _spawn(self, job):
        payload = {"hostScope": self.state.host_scope, "provider": job.provider,
                   "component": job.component, "configHome": self.state.configs[job.provider][0],
                   "configHomeKind": self.state.configs[job.provider][1],
                   "timeoutMs": self.scheduler.timeout,
                   "sampledBoottimeMs": job.started,
                   "workspaceConfig": self.workspace_config if job.component == "history" else None}
        parent, child, process = None, None, None
        try:
            parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            parent.setblocking(False)
            payload['imageMemoFd'] = child.fileno()
            request = (canonical(payload) + "\n").encode()
            if len(request) > MAX_CONFIG_BYTES + 16384:
                raise ValueError("service_worker_request_limit")
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", str(Path(__file__).with_name("_service_worker.py"))],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True, pass_fds=(child.fileno(),),
            )
            child.close()
            child = None
            process._observer_image_reply = parent
            try:
                send_memo(parent, self.image_memos[job.provider])
            except (ValueError, OSError):
                self.image_memos[job.provider].close()
                self._close_memo_channel(process)
            process.stdin.write(request)
            process.stdin.close()
        except BaseException:
            self.image_memos[job.provider].close()
            if parent is not None:
                parent.close()
            if child is not None:
                child.close()
            if process is not None:
                self._close_memo_channel(process)
                try:
                    self._stop_worker(Worker(job, process))
                finally:
                    process.stdout.close()
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
            raise
        return process

    @staticmethod
    def _close_memo_channel(process):
        channel = getattr(process, '_observer_image_reply', None)
        process._observer_image_reply = None
        if channel is not None:
            channel.close()

    def _take_image_memo(self, process, provider, *, eligible):
        channel = getattr(process, '_observer_image_reply', None)
        replacement = None
        try:
            if eligible and channel is not None:
                try:
                    replacement = receive_memo(channel, provider)
                except (ValueError, OSError):
                    pass
        finally:
            self._close_memo_channel(process)
        self.image_memos[provider].close()
        self.image_memos[provider] = replacement if replacement is not None else ImageMemo(provider)

    def _drop(self, peer):
        self._release_sync_pins(peer)
        if peer.sync_view is not None:
            peer.parts = ()
        if peer not in self.peers:
            return
        self.peers.remove(peer)
        try:
            self.selector.unregister(peer.sock)
        except (KeyError, ValueError):
            pass
        peer.sock.close()
        self.counts["droppedConnections"] += 1

    @staticmethod
    def _release_sync_pins(peer):
        pins, peer.sync_pins = peer.sync_pins, None
        if pins is not None:
            pins.release()

    def _prune(self):
        keep = {p.body_revision for p in self.peers if p.body_revision is not None}
        keep.update(self.latest.values())
        self.bodies = {rev: body for rev, body in self.bodies.items() if rev in keep}

    def encoded_bytes(self):
        return self.sync_encoded_bytes() + sum(len(body) for body in self.bodies.values()) + sum(
            sum(len(part) for index, part in enumerate(p.parts) if not (index == 1 and p.body_revision is not None))
            for p in self.peers if p.sync_view is None
        )

    def _sync_buffers(self):
        retained = getattr(self.state, "sync_retained_buffers", None)
        return {} if retained is None else {id(value): value for value in retained()}

    def sync_encoded_bytes(self):
        buffers = self._sync_buffers()
        references = 0
        for peer in self.peers:
            if peer.sync_view is not None and peer.parts:
                buffers.update((id(part), part) for part in peer.parts)
                references += sys.getsizeof(peer.parts)
        owned = getattr(self.state, "sync_owned_encoded_bytes", None)
        internal = 0 if owned is None else owned()
        return sum(len(value) for value in buffers.values()) + references + internal

    def _sync_room(self, reserve):
        while self.sync_encoded_bytes() + reserve > MAX_SYNC_ENCODED_BYTES:
            peers = [peer for peer in self.peers if peer.sync_view is not None and peer.parts]
            if not peers:
                return False
            self._drop(min(peers, key=lambda peer: peer.write_started))
            self._prune()
        return True

    def _reserve_sync(self, additional_bytes):
        if type(additional_bytes) is not int or additional_bytes < 0:
            raise ValueError("service_encoding_limit")
        if not self._sync_room(additional_bytes):
            return False
        try:
            self._room(additional_bytes)
        except ValueError as error:
            if error.args != ("service_encoding_limit",):
                raise
            return False
        return True

    def _room(self, reserve, *, protected=None):
        while self.encoded_bytes() + reserve > self.encoded_limit:
            # The two families share one budget. An idle family's latest body
            # is only a cache, not a reason to evict a pinned slow reader.
            pinned = {p.body_revision for p in self.peers if p.body_revision is not None}
            cached = next((name for name, key in self.latest.items()
                           if key != protected and key not in pinned), None)
            if cached is not None:
                del self.latest[cached]
                self._prune()
                continue
            candidates = [p for p in self.peers if p.parts]
            if not candidates:
                raise ValueError("service_encoding_limit")
            self._drop(min(candidates, key=lambda p: p.write_started))
            self._prune()

    def _body(self, revision, snapshot, *, overhead=MAX_OVERHEAD_BYTES):
        family = revision[0] if isinstance(revision, tuple) else "service"
        if revision in self.bodies:
            self.latest[family] = revision
            self._room(overhead, protected=revision)
            return
        self.latest.pop(family, None)
        self._prune()
        body = canonical(snapshot).encode()
        self._room(len(body) + overhead)
        self.bodies[revision] = body
        self.latest[family] = revision

    def _queue(self, peer, kind, reason="observed_view"):
        peer.sequence += 1
        make_frame = self.state.active_frame if peer.family == "active" else self.state.frame
        payload_key = "projection" if peer.family == "active" else "snapshot"
        frame = make_frame(kind, peer.sequence, reason=reason)
        if kind == "heartbeat" and frame["viewRevision"] != peer.sent_revision:
            frame = make_frame("view", peer.sequence, reason="lease_expired")
        if frame["kind"] == "error":
            peer.operation = "error"
        snapshot = frame.pop(payload_key)
        peer.body_revision = None
        try:
            if snapshot is not None:
                # Frame construction can expire leases and advance the revision.
                # Resolve the key only after constructing the authoritative frame.
                revision = ("active", frame["viewRevision"]) if peer.family == "active" else frame["viewRevision"]
                prefix = (canonical(frame)[:-1] + ',"' + payload_key + '":').encode()
                self._body(revision, snapshot, overhead=len(prefix) + 2)
                if peer not in self.peers:
                    return
                peer.body_revision = revision
                peer.parts = (prefix, self.bodies[revision], b"}\n")
            else:
                control = (canonical({**frame, payload_key: None}) + "\n").encode()
                self._room(len(control))
                if peer not in self.peers:
                    return
                peer.parts = (control,)
        except ValueError as error:
            if error.args != ("service_encoding_limit",):
                raise
            # A protocol-valid frame can exceed a deliberately smaller runtime
            # budget. Unsolicited watch updates must fail this peer, not hosting.
            self._drop(peer)
            self._prune()
            return
        peer.part = peer.offset = 0
        peer.frame_revision = frame["viewRevision"]
        peer.write_started = self.state.clock()
        if self.encoded_bytes() > self.encoded_limit:
            self._drop(peer)
            self._prune()
            return
        self.selector.modify(peer.sock, selectors.EVENT_READ | selectors.EVENT_WRITE, ("peer", peer))
        self.counts["frames"] += 1

    def _queue_sync(self, peer, lines, *, cursor=None, close=False):
        parts = (lines,) if isinstance(lines, bytes) else tuple(lines)
        limit = MAX_HEAD_BYTES if peer.operation == "head" else MAX_MESSAGE_BYTES
        if (not parts or len(parts) > 5
                or any(type(part) is not bytes or not part.endswith(b"\n") or len(part) > limit for part in parts)):
            self.state.sync_discard_buffers(parts)
            raise ValueError("service_sync_encoding")
        if peer not in self.peers:
            self.state.sync_discard_buffers(parts)
            return
        shared = self._sync_buffers()
        for other in self.peers:
            if other.sync_view is not None:
                shared.update((id(part), part) for part in other.parts)
        new = {id(part): part for part in parts if id(part) not in shared}
        if not self._reserve_sync(sum(len(part) for part in new.values()) + sys.getsizeof(parts)):
            self.state.sync_discard_buffers(parts)
            self._drop(peer)
            return
        if peer not in self.peers:
            self.state.sync_discard_buffers(parts)
            return
        try:
            pins = self.state.sync_pin_buffers(parts)
        except ValueError as error:
            # Heap admission is independent of the encoded-byte preflight.
            # Reject only this delivery, including any superseded frame pin.
            self.state.sync_discard_buffers(parts)
            self._drop(peer)
            traceback.clear_frames(error.__traceback__)
            return
        if peer not in self.peers:
            pins.release()
            self.state.sync_discard_buffers(parts)
            return
        self._release_sync_pins(peer)
        peer.parts = parts
        peer.sync_pins = pins
        peer.part = peer.offset = 0
        peer.body_revision = None
        peer.sync_send_cursor = None if cursor is None else tuple(cursor)
        peer.sync_close = close
        peer.write_started = self.state.clock()
        self.selector.modify(peer.sock, selectors.EVENT_READ | selectors.EVENT_WRITE, ("peer", peer))
        self.counts["frames"] += len(parts)

    def _sync_watch_next(self, peer, *, initial=False):
        current = self.state.sync_cursor(peer.sync_view)
        if current is None:
            self._queue_sync(peer, self.state.sync_control(
                peer.sync_view, "baseline_required", "sync_cache_unavailable"), close=True)
            return
        cursor = tuple(current)
        if cursor == peer.sync_cursor:
            reason = "watch_subscribed" if initial else "service_alive"
            self._queue_sync(peer, self.state.sync_control(peer.sync_view, "complete", reason), cursor=cursor)
            return
        base = self.state.sync_tag_for_cursor(peer.sync_view, peer.sync_cursor)
        if base is None:
            self._queue_sync(peer, self.state.sync_control(
                peer.sync_view, "baseline_required", "sync_base_evicted"), close=True)
            return
        target = self.state.sync_current_tag(peer.sync_view)
        # These getters only read the committed cache. If another serialized
        # publisher advances between reads, use explicit recovery, never pair
        # a newer root with the previously captured cursor.
        if tuple(target[1:]) != cursor[1:]:
            self._queue_sync(peer, self.state.sync_control(
                peer.sync_view, "baseline_required", "sync_head_moved"), close=True)
            return
        result = self.state.sync_changes(peer.sync_view, base, target,
                                         max_transactions=4, max_bytes=8 * 1024 * 1024)
        self._queue_sync(peer, result, cursor=cursor, close=isinstance(result, bytes))

    def _sync_request(self, peer, request):
        peer.sync_view = "active" if request["syncProtocol"] == "agent-observer.active-sync" else "full"
        peer.family = "sync-" + peer.sync_view
        peer.operation = request["operation"]
        validate_sync_request(request, expected_host=self.state.host_scope)
        try:
            if peer.operation == "baseline":
                self._queue_sync(peer, self.state.sync_baseline(peer.sync_view), close=True)
            elif peer.operation == "head":
                # This route deliberately does not enter frame/active_frame or
                # expiry/publication. The owner cache supplies its fresh small head.
                self._queue_sync(peer, self.state.sync_head(peer.sync_view, request["challenge"]), close=True)
            elif peer.operation == "changes":
                result = self.state.sync_changes(peer.sync_view, request["baseTag"], request["targetTag"],
                                                 max_transactions=request["maxTransactions"],
                                                 max_bytes=request["maxBytes"])
                self._queue_sync(peer, result, close=True)
            else:
                peer.sync_cursor = tuple(request["cursor"])
                self._sync_watch_next(peer, initial=True)
        except ValueError as error:
            reason = (error.args[0] if isinstance(error, ContractError) and len(error.args) == 1
                      and type(error.args[0]) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", error.args[0])
                      else "sync_source_unavailable")
            self._queue_sync(peer, self.state.sync_control(peer.sync_view, "error", reason), close=True)

    def _sync_tick(self, peer, now):
        if peer.operation != "watch" or peer.sync_close:
            return
        current = self.state.sync_cursor(peer.sync_view)
        cursor = None if current is None else tuple(current)
        if current is None and peer.parts:
            self._drop(peer)
            return
        if peer.parts and cursor != peer.sync_send_cursor:
            if peer.sync_pending_cursor is None:
                peer.sync_pending_cursor = cursor
            elif peer.sync_pending_cursor != cursor:
                # One pending base reference is bounded; another move cannot
                # replace a transaction which this subscriber has not read.
                self._drop(peer)
        elif not peer.parts and (
            cursor != peer.sync_cursor or now - peer.last_sent >= self.heartbeat
        ):
            self._sync_watch_next(peer)

    def _request(self, peer):
        data = peer.sock.recv(16384)
        if not data:
            self._drop(peer)
            return
        if peer.operation is not None:
            self._drop(peer)
            return
        peer.incoming.extend(data)
        if len(peer.incoming) > max(MAX_REQUEST_BYTES, MAX_ACTIVE_REQUEST_BYTES, MAX_SYNC_REQUEST_BYTES):
            self._drop(peer)
            return
        if b"\n" not in peer.incoming:
            return
        request = decode_document(bytes(peer.incoming),
                                  max_bytes=max(MAX_REQUEST_BYTES, MAX_ACTIVE_REQUEST_BYTES, MAX_SYNC_REQUEST_BYTES),
                                  max_nodes=MAX_SYNC_REQUEST_NODES, max_depth=MAX_SYNC_REQUEST_DEPTH,
                                  line_framed=True)
        if not isinstance(request, dict) or sum(key in request for key in (
            "serviceProtocol", "activeFeedProtocol", "syncProtocol",
        )) != 1:
            raise ValueError("service_request_family")
        if "syncProtocol" in request:
            peer.incoming.clear()
            self._sync_request(peer, request)
            return
        if "activeFeedProtocol" in request:
            validate_active_request(request)
            peer.family = "active"
        else:
            validate_request(request)
        peer.incoming.clear()
        peer.operation = request["operation"]
        if request["hostScope"] != self.state.host_scope:
            peer.operation = "error"
            reason = "active_host_mismatch" if peer.family == "active" else "service_host_mismatch"
            self._queue(peer, "error", reason)
            return
        kind = "status" if peer.operation == "status" or self.state.snapshot is None else "view"
        self._queue(peer, kind)

    def _write(self, peer):
        budget = 65536
        while budget > 0 and peer.part < len(peer.parts):
            data = memoryview(peer.parts[peer.part])[peer.offset:peer.offset + budget]
            try:
                size = peer.sock.send(data)
            except BlockingIOError:
                return
            if not size:
                self._drop(peer)
                return
            budget -= size
            peer.offset += size
            if peer.offset == len(peer.parts[peer.part]):
                peer.part += 1
                peer.offset = 0
        if peer.part < len(peer.parts):
            return
        peer.parts = ()
        self._release_sync_pins(peer)
        peer.body_revision = None
        peer.last_sent = self.state.clock()
        if peer.sync_view is not None:
            peer.sync_cursor = peer.sync_send_cursor
            peer.sync_send_cursor = peer.sync_pending_cursor = None
            if peer.sync_close or peer.operation != "watch":
                self._drop(peer)
            else:
                self.selector.modify(peer.sock, selectors.EVENT_READ, ("peer", peer))
            self._prune()
            return
        peer.sent_revision = peer.frame_revision
        if peer.operation != "watch":
            self._drop(peer)
        elif peer.recover:
            peer.recover = False
            peer.pending = None
            peer.skipped = False
            self._queue(peer, "resync", "delivery_coalesced")
        elif peer.pending is not None:
            peer.pending = None
            if peer.skipped:
                peer.skipped = False
                peer.recover = True
                self._queue(peer, "gap", "delivery_coalesced")
            else:
                self._queue(peer, "view")
        else:
            self.selector.modify(peer.sock, selectors.EVENT_READ, ("peer", peer))
        self._prune()

    def _stop_worker(self, worker):
        process = worker.process
        if process.returncode is None:
            # Each process is spawned in its own owned session; never a native
            # provider's process group. A still-unreaped child cannot be PID-reused.
            try:
                if os.getpgid(process.pid) != process.pid:
                    raise ValueError("service_worker_group_changed")
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=2)

    @staticmethod
    def _exit_status(process):
        if process.returncode is not None:
            return process.returncode
        # Keep the exited leader unreaped until its owned helper group has been
        # stopped. EOF or a leader crash must not orphan a still-running helper.
        result = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if result is None:
            return None
        return result.si_status if result.si_code == os.CLD_EXITED else -result.si_status

    def _complete(self, worker, *, timed_out=False):
        provider = worker.job.provider
        process = worker.process
        try:
            self.selector.unregister(process.stdout)
        except (KeyError, ValueError):
            pass
        exit_status = self._exit_status(process)
        self._stop_worker(worker)
        success = False
        prior_context = self.state.contexts[provider]
        if not timed_out and exit_status == 0:
            try:
                value = parse_snapshot(bytes(worker.buffer))
                ttl = max(self.scheduler.timeout + 2 * self.scheduler.intervals[worker.job.component] + 1000, 3 * self.scheduler.intervals[worker.job.component])
                if worker.job.generation == self.scheduler.generation[provider]:
                    self.state.accept(provider, worker.job.component, value, sampled_ms=worker.job.started, ttl_ms=ttl, runtime_ttl_ms=max(self.scheduler.timeout + 2 * self.scheduler.intervals["runtime"] + 1000, 3 * self.scheduler.intervals["runtime"]))
                    success = True
            except (ValueError, OSError):
                pass
        eligible = success and prior_context is not None and prior_context == self.state.contexts[provider]
        if success:
            eligible = eligible and value['sources'][0]['runtime'] is not None and value['sources'][0]['coverage']['runtime']['status'] in {'complete', 'partial'}
        self._take_image_memo(process, provider, eligible=eligible)
        self.scheduler.finish(worker.job, self.state.clock(), success=success)
        if not success:
            self.state.fail(provider, worker.job.component, "collection_timeout" if timed_out else "collection_failed")
        process.stdout.close()
        del self.workers[provider]

    def run(self, stop):
        if hasattr(self.state, "sync_reserver"):
            self.state.sync_reserver = self._sync_reserver
        try:
            with Endpoint(self.path) as listener:
                self.selector.register(listener, selectors.EVENT_READ, ("listener", None))
                if self.native_hints:
                    from .service_hints import Hints
                    self.hints = Hints(self.state.configs, self.selector, self.scheduler,
                                       lambda process: self._stop_worker(Worker(None, process)),
                                       factory=self.hint_factory, diagnostics=self.hint_diagnostics)
                while not stop.is_set():
                    now = self.state.clock()
                    self.state.expire()
                    if self.hints:
                        self.hints.tick(now)
                    for worker in list(self.workers.values()):
                        if now >= worker.job.deadline:
                            self._complete(worker, timed_out=True)
                        elif worker.eof and self._exit_status(worker.process) is not None:
                            self._complete(worker)
                    if self.collect:
                        for job in self.scheduler.start_due(now):
                            self.state.attempt(job.provider, job.component)
                            process = None
                            try:
                                process = self.worker_factory(job)
                                os.set_blocking(process.stdout.fileno(), False)
                                worker = Worker(job, process)
                                self.workers[job.provider] = worker
                                self.selector.register(process.stdout, selectors.EVENT_READ, ("worker", worker))
                                self.counts["workerStarts"] += 1
                            except (ValueError, OSError):
                                if process is not None:
                                    self._stop_worker(Worker(job, process))
                                    self._close_memo_channel(process)
                                    process.stdout.close()
                                    self.workers.pop(job.provider, None)
                                self.image_memos[job.provider].close()
                                self.scheduler.finish(job, now, success=False)
                                self.state.fail(job.provider, job.component)
                    self._sync_room(0)
                    for peer in list(self.peers):
                        if peer.operation is None and now - peer.since >= self.io_timeout or peer.parts and now - peer.write_started >= self.io_timeout:
                            self._drop(peer)
                            continue
                        if peer.sync_view is not None:
                            try:
                                self._sync_tick(peer, now)
                            except (ValueError, OSError):
                                self._drop(peer)
                            continue
                        if peer.operation == "watch" and self.state.revision > peer.sent_revision:
                            if peer.parts:
                                if self.state.revision > peer.frame_revision:
                                    peer.skipped |= self.state.revision > max(peer.frame_revision, peer.pending or 0) + 1 or peer.pending is not None and peer.pending != self.state.revision
                                    peer.pending = self.state.revision
                            elif self.state.snapshot is not None:
                                if self.state.revision > peer.sent_revision + 1:
                                    peer.recover = True
                                    self._queue(peer, "gap", "delivery_coalesced")
                                else:
                                    self._queue(peer, "view")
                        elif peer.operation == "watch" and not peer.parts and now - peer.last_sent >= self.heartbeat:
                            self._queue(peer, "heartbeat", "service_alive")
                    for key, mask in self.selector.select(0.05):
                        kind, obj = key.data
                        if kind == "listener":
                            connection, _ = listener.accept()
                            connection.setblocking(False)
                            _pid, uid, _gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                            if uid != self.state.uid or len(self.peers) >= self.max_clients:
                                connection.close()
                                continue
                            peer = Peer(connection, now)
                            self.peers.add(peer)
                            self.selector.register(connection, selectors.EVENT_READ, ("peer", peer))
                            self.counts["acceptedConnections"] += 1
                        elif kind == "worker":
                            data = os.read(obj.process.stdout.fileno(), 65536)
                            if data:
                                obj.buffer.extend(data)
                                limit = MAX_SNAPSHOT_BYTES
                                if len(obj.buffer) > limit:
                                    self._complete(obj, timed_out=True)
                            else:
                                obj.eof = True
                                self.selector.unregister(obj.process.stdout)
                        elif kind == "hint":
                            self.hints.read(obj, self.state.clock())
                        elif obj in self.peers:
                            try:
                                if mask & selectors.EVENT_READ:
                                    self._request(obj)
                                if obj in self.peers and mask & selectors.EVENT_WRITE:
                                    self._write(obj)
                            except (ValueError, OSError):
                                self._drop(obj)
                    self._prune()
        finally:
            if getattr(self.state, "sync_reserver", None) is self._sync_reserver:
                self.state.sync_reserver = None
            if self.hints:
                self.hints.close()
            for peer in list(self.peers):
                self._drop(peer)
            for worker in list(self.workers.values()):
                self._stop_worker(worker)
                self._close_memo_channel(worker.process)
                worker.process.stdout.close()
            for memo in self.image_memos.values():
                memo.close()
            self.selector.close()
