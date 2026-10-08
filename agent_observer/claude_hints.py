"""Bounded Linux wakeups; scheduling fingerprints never become observations."""

from collections import OrderedDict
import ctypes
from dataclasses import dataclass
import hashlib
import os
import re
import select
import stat
import struct
import time

MODIFY, ATTRIB, CLOSE_WRITE = 0x2, 0x4, 0x8
MOVED_FROM, MOVED_TO, CREATE, DELETE = 0x40, 0x80, 0x100, 0x200
DELETE_SELF, MOVE_SELF, OVERFLOW, IGNORED, ISDIR = 0x400, 0x800, 0x4000, 0x8000, 0x40000000
MASK = MODIFY | ATTRIB | CLOSE_WRITE | MOVED_FROM | MOVED_TO | CREATE | DELETE | DELETE_SELF | MOVE_SELF
MAX_WATCHES, MAX_ENTRIES = 2048, 8192
MAX_FINGERPRINTS, MAX_METADATA_BYTES, MAX_METADATA_EVENTS = 4096, 128 * 1024, 64
ROOTS = {"sessions": "runtime", "jobs": "runtime", "projects": "history"}


def scheduling_projection(root, name, payload, *, linked_job=None):
    # Reuse the authoritative adapter's pure field projection, without invoking
    # its process, image, roster or phase observation functions.
    from .claude_metadata import _job_record, _session_record
    if root == "sessions":
        record = _session_record(name, payload)
        if (record["issues"] or record["kind"] not in {"interactive", "bg"}
                or record["status"] == "waiting" and record["waitReason"] == "unknown"):
            raise ValueError("service_watch_metadata")
        # Busy and shell project to the same working phase. Failed/stopped or
        # unavailable job contexts still retain the exact registry clock because
        # its relation to a terminal clock can change an ambiguity predicate.
        clock_matters = record["jobId"] is not None and (
            linked_job is None or linked_job.session_id != record["sessionId"]
            or linked_job.state not in {"working", "done"} or linked_job.issues
            or linked_job.in_flight_invalid or linked_job.in_flight is None
        )
        if not clock_matters:
            record.pop("statusUpdatedAt")
        if record["status"] in {"busy", "shell"}:
            record["status"] = "working"
        return record
    job = _job_record(name, payload)
    if job.issues or job.in_flight_invalid or job.in_flight is None:
        raise ValueError("service_watch_metadata")
    block = payload.get("block")
    if block is not None and (not isinstance(block, dict)
            or block.get("questions") is not None and not job.question_wait):
        raise ValueError("service_watch_metadata")
    return [job.job_id, job.session_id, job.state, job.tempo, job.terminal_at,
            job.cwd, job.title, None if job.in_flight is None else any(job.in_flight),
            job.last_terminal_at, job.question_wait]


@dataclass(frozen=True)
class Directory:
    path: object
    component: str | None
    root: str
    identity: tuple


class Watcher:
    def __init__(self, home, *, max_watches=MAX_WATCHES):
        if not home.is_absolute() or home.resolve(strict=True) != home or not 1 <= max_watches <= MAX_WATCHES:
            raise ValueError("service_watch_scope")
        self.home, self.max_watches = home, max_watches
        self.lib = ctypes.CDLL(None, use_errno=True)
        self.lib.inotify_init1.argtypes = [ctypes.c_int]
        self.lib.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        self.lib.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
        self.fd = self.lib.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "service_watch_unavailable")
        self.watches = {}
        self.fingerprints = OrderedDict()
        self.rearm = False
        try:
            self.root_identity = self._directory(home, None, "").identity
            self.reconcile()
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1
        self.watches.clear()
        self.fingerprints.clear()

    def _metadata(self, directory, name):
        from .bounded_json import decode_document
        parent = os.open(directory.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(parent)
            if (info.st_dev, info.st_ino) != directory.identity or info.st_uid != os.geteuid():
                raise ValueError("service_watch_incarnation")
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
            try:
                before = os.fstat(fd)
                if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                        or before.st_mode & 0o022 or not 0 < before.st_size <= MAX_METADATA_BYTES):
                    raise ValueError("service_watch_metadata")
                data = os.read(fd, MAX_METADATA_BYTES + 1)
                stamp = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                       value.st_mtime_ns, value.st_ctime_ns, value.st_uid, value.st_mode)
                if (len(data) != before.st_size or stamp(before) != stamp(os.fstat(fd))
                        or stamp(before) != stamp(os.stat(name, dir_fd=parent, follow_symlinks=False))):
                    raise ValueError("service_watch_metadata")
                value = decode_document(data, max_bytes=MAX_METADATA_BYTES, max_depth=16, max_nodes=8192)
                if self._directory(directory.path, directory.component, directory.root) != directory:
                    raise ValueError("service_watch_incarnation")
                return value
            finally:
                os.close(fd)
        finally:
            os.close(parent)

    def runtime_changed(self, directory, name, *, deleted=False):
        from .claude_metadata import _ReadFailure
        key = directory.identity, name
        try:
            if deleted:
                raise ValueError("service_watch_metadata")
            payload = self._metadata(directory, name)
            linked_job = None
            if directory.root == "sessions" and isinstance(payload, dict):
                job_id = payload.get("jobId")
                if isinstance(job_id, str) and re.fullmatch(r"[a-f0-9]{8}", job_id):
                    from .claude_metadata import _job_record
                    job_directory = self._directory(self.home / "jobs" / job_id, "runtime", "jobs")
                    linked_job = _job_record(job_id, self._metadata(job_directory, "state.json"))
            projection = scheduling_projection(directory.root, name if directory.root == "sessions" else directory.path.name,
                                               payload, linked_job=linked_job)
            from .contract import canonical
            digest = hashlib.sha256(canonical(projection).encode()).digest()
        except (OSError, ValueError, TypeError, KeyError, _ReadFailure):
            # Failure/recovery cannot be hidden by a previously valid digest.
            self.fingerprints.pop(key, None)
            return True
        changed = self.fingerprints.get(key) != digest
        self.fingerprints[key] = digest
        self.fingerprints.move_to_end(key)
        while len(self.fingerprints) > MAX_FINGERPRINTS:
            self.fingerprints.popitem(last=False)
        return changed

    def _directory(self, path, component, root):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError("service_watch_directory")
        return Directory(path, component, root, (info.st_dev, info.st_ino))

    def census(self):
        result = [self._directory(self.home, None, "")]
        pending = []
        for name, component in ROOTS.items():
            path = self.home / name
            try:
                directory = self._directory(path, component, name)
            except FileNotFoundError:
                continue
            result.append(directory)
            if name != "sessions":
                pending.append(directory)
        entries, deadline = 0, time.monotonic() + 2
        while pending:
            directory = pending.pop()
            with os.scandir(directory.path) as children:
                for entry in children:
                    entries += 1
                    if entries > MAX_ENTRIES or time.monotonic() > deadline:
                        raise ValueError("service_watch_census_limit")
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    child = self._directory(directory.path / entry.name, directory.component, directory.root)
                    result.append(child)
                    if len(result) > self.max_watches:
                        raise ValueError("service_watch_limit")
                    # The saved-history collector scans project-level files.
                    # Nested session/subagent transcripts are outside that
                    # catalog and cannot update its conversation activity.
        if len(result) > self.max_watches:
            raise ValueError("service_watch_limit")
        return result

    def reconcile(self):
        desired = self.census()
        if desired[0].identity != self.root_identity:
            raise ValueError("service_watch_incarnation")
        existing = {directory.path: (wd, directory) for wd, directory in self.watches.items()}
        changed = set()
        wanted = {d.path for d in desired}
        for wd, directory in list(self.watches.items()):
            if directory.path not in wanted:
                self.lib.inotify_rm_watch(self.fd, wd)
                del self.watches[wd]
                changed.update((directory.component,) if directory.component else ROOTS.values())
        for directory in desired:
            previous = existing.get(directory.path)
            if previous and previous[1] == directory:
                continue
            if previous and previous[0] in self.watches:
                self.lib.inotify_rm_watch(self.fd, previous[0])
                del self.watches[previous[0]]
            wd = self.lib.inotify_add_watch(self.fd, os.fsencode(directory.path), MASK | 0x01000000 | 0x02000000)
            if wd < 0:
                raise OSError(ctypes.get_errno(), "service_watch_unavailable")
            if self._directory(directory.path, directory.component, directory.root) != directory:
                raise ValueError("service_watch_incarnation")
            self.watches[wd] = directory
            changed.update((directory.component,) if directory.component else ROOTS.values())
        self.rearm = False
        if "runtime" in changed:
            self.fingerprints.clear()
        return changed

    def events(self, data):
        components, offset, runtime_files = set(), 0, {}
        while offset < len(data):
            if len(data) - offset < 16:
                raise ValueError("service_watch_event")
            wd, mask, _cookie, length = struct.unpack_from("iIII", data, offset)
            offset += 16
            if length > 4096 or offset + length > len(data):
                raise ValueError("service_watch_event")
            name = data[offset:offset + length].split(b"\0", 1)[0]
            offset += length
            if mask & OVERFLOW:
                self.fingerprints.clear()
                components.update(("runtime", "history"))
                self.rearm = True
                continue
            directory = self.watches.get(wd)
            if directory is None:
                continue
            if mask & (IGNORED | DELETE_SELF | MOVE_SELF):
                self.fingerprints.clear()
                components.update((directory.component,) if directory.component else ROOTS.values())
                self.lib.inotify_rm_watch(self.fd, wd)
                self.watches.pop(wd, None)
                self.rearm = True
                continue
            if mask & ISDIR:
                if directory.component is None and name not in {b"sessions", b"jobs", b"projects"}:
                    continue
                if directory.root in {"projects", "jobs"} and directory.path != self.home / directory.root:
                    continue
                components.update((directory.component,) if directory.component else (ROOTS[name.decode()],))
                self.rearm = True
            elif directory.root == "sessions" and re.fullmatch(rb"[0-9]+\.json", name):
                key = wd, os.fsdecode(name)
                runtime_files[key] = runtime_files.get(key, False) or bool(mask & (DELETE | MOVED_FROM))
            elif directory.root == "jobs" and directory.path.parent.name == "jobs" and name == b"state.json":
                key = wd, "state.json"
                runtime_files[key] = runtime_files.get(key, False) or bool(mask & (DELETE | MOVED_FROM))
            elif directory.root == "projects" and directory.path.parent == self.home / "projects" and name.endswith(b".jsonl"):
                components.add("history")
        # MODIFY/CLOSE_WRITE/atomic-replace bursts share one bounded read per
        # watched file in this chunk. Excess work becomes a conservative wakeup.
        for index, ((wd, name), deleted) in enumerate(runtime_files.items()):
            directory = self.watches.get(wd)
            if directory is None or index >= MAX_METADATA_EVENTS:
                if directory is not None:
                    self.fingerprints.pop((directory.identity, name), None)
                components.add("runtime")
            elif self.runtime_changed(directory, name, deleted=deleted):
                components.add("runtime")
        return components

    def read(self):
        components = set()
        for _ in range(4):
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                break
            if not data:
                raise ValueError("service_watch_unavailable")
            components.update(self.events(data))
        return components


def run(home, emitter):
    watcher = Watcher(home)
    try:
        for component in ("runtime", "history"):
            emitter.hint(component, "source_ready")
        checked = time.monotonic()
        while True:
            emitter.flush()
            now = time.monotonic()
            if now - checked >= (1 if watcher.rearm else 5):
                for component in watcher.reconcile():
                    emitter.hint(component, "watch_rearmed")
                checked = now
            if select.select([watcher.fd], [], [], 0.2)[0]:
                for component in watcher.read():
                    emitter.hint(component)
    finally:
        watcher.close()
