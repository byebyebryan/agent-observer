"""Private local IPC, bounded fan-out and Observer-owned collection workers."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ._image_memo import ImageMemo, receive as receive_memo, send as send_memo
from .bounded_json import decode_document
from .contract import MAX_SNAPSHOT_BYTES, canonical, parse_snapshot
from .service_contract import MAX_OVERHEAD_BYTES, MAX_REQUEST_BYTES, parse_request
from .service_scheduler import Scheduler
from .workspace import MAX_CONFIG_BYTES, validate_config


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
    operation: str | None = None
    sequence: int = 0
    parts: tuple = ()
    part: int = 0
    offset: int = 0
    sent_revision: int = 0
    frame_revision: int = 0
    body_revision: int | None = None
    pending: int | None = None
    skipped: bool = False
    recover: bool = False
    write_started: int = 0
    last_sent: int = 0


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
        self.latest = None
        self.counts = {"acceptedConnections": 0, "droppedConnections": 0, "frames": 0, "workerStarts": 0}
        self.native_hints, self.hint_factory = native_hints, hint_factory
        self.hint_diagnostics, self.hints = hint_diagnostics, None
        self.image_memos = {provider: ImageMemo(provider) for provider in state.configs}

    def _spawn(self, job):
        payload = {"hostScope": self.state.host_scope, "provider": job.provider,
                   "component": job.component, "configHome": self.state.configs[job.provider][0],
                   "configHomeKind": self.state.configs[job.provider][1],
                   "timeoutMs": self.scheduler.timeout,
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
        if peer not in self.peers:
            return
        self.peers.remove(peer)
        try:
            self.selector.unregister(peer.sock)
        except (KeyError, ValueError):
            pass
        peer.sock.close()
        self.counts["droppedConnections"] += 1

    def _prune(self):
        keep = {p.body_revision for p in self.peers if p.body_revision is not None}
        if self.latest is not None:
            keep.add(self.latest)
        self.bodies = {rev: body for rev, body in self.bodies.items() if rev in keep}

    def encoded_bytes(self):
        return sum(len(body) for body in self.bodies.values()) + sum(
            sum(len(part) for index, part in enumerate(p.parts) if not (index == 1 and p.body_revision is not None))
            for p in self.peers
        )

    def _body(self, revision, snapshot):
        if revision in self.bodies:
            return
        self.latest = None
        self._prune()
        reserve = MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES
        while self.encoded_bytes() + reserve > self.encoded_limit:
            candidates = [p for p in self.peers if p.parts]
            if not candidates:
                raise ValueError("service_encoding_limit")
            self._drop(min(candidates, key=lambda p: p.write_started))
            self._prune()
        body = canonical(snapshot).encode()
        self.bodies[revision] = body
        self.latest = revision

    def _queue(self, peer, kind, reason="observed_view"):
        peer.sequence += 1
        frame = self.state.frame(kind, peer.sequence, reason=reason)
        if kind == "heartbeat" and frame["viewRevision"] != peer.sent_revision:
            frame = self.state.frame("view", peer.sequence, reason="lease_expired")
        snapshot = frame.pop("snapshot")
        peer.body_revision = None
        if snapshot is not None:
            self._body(frame["viewRevision"], snapshot)
            if peer not in self.peers:
                return
            peer.body_revision = frame["viewRevision"]
            peer.parts = ((canonical(frame)[:-1] + ',"snapshot":').encode(), self.bodies[peer.body_revision], b"}\n")
        else:
            peer.parts = ((canonical({**frame, "snapshot": None}) + "\n").encode(),)
        peer.part = peer.offset = 0
        peer.frame_revision = frame["viewRevision"]
        peer.write_started = self.state.clock()
        if self.encoded_bytes() > self.encoded_limit:
            self._drop(peer)
            self._prune()
            return
        self.selector.modify(peer.sock, selectors.EVENT_READ | selectors.EVENT_WRITE, ("peer", peer))
        self.counts["frames"] += 1

    def _request(self, peer):
        data = peer.sock.recv(16384)
        if not data:
            self._drop(peer)
            return
        if peer.operation is not None:
            self._drop(peer)
            return
        peer.incoming.extend(data)
        if len(peer.incoming) > MAX_REQUEST_BYTES:
            self._drop(peer)
            return
        if b"\n" not in peer.incoming:
            return
        request = parse_request(bytes(peer.incoming))
        peer.incoming.clear()
        peer.operation = request["operation"]
        if request["hostScope"] != self.state.host_scope:
            peer.operation = "error"
            self._queue(peer, "error", "service_host_mismatch")
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
        peer.body_revision = None
        peer.last_sent = self.state.clock()
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
                    for peer in list(self.peers):
                        if peer.operation is None and now - peer.since >= self.io_timeout or peer.parts and now - peer.write_started >= self.io_timeout:
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
                                if len(obj.buffer) > MAX_SNAPSHOT_BYTES:
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
