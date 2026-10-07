"""Bounded Linux metadata-directory wakeups; no transcript or registry reads."""

import ctypes
from dataclasses import dataclass
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
ROOTS = {"sessions": "runtime", "jobs": "runtime", "projects": "history"}


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
                pending.append((directory, 0))
        entries, deadline = 0, time.monotonic() + 2
        while pending:
            directory, depth = pending.pop()
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
                    if directory.root == "projects" and depth < 2:
                        pending.append((child, depth + 1))
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
        return changed

    def events(self, data):
        components, offset = set(), 0
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
                components.update(("runtime", "history"))
                self.rearm = True
                continue
            directory = self.watches.get(wd)
            if directory is None:
                continue
            if mask & (IGNORED | DELETE_SELF | MOVE_SELF):
                components.update((directory.component,) if directory.component else ROOTS.values())
                self.lib.inotify_rm_watch(self.fd, wd)
                self.watches.pop(wd, None)
                self.rearm = True
                continue
            if mask & ISDIR:
                if directory.component is None and name not in {b"sessions", b"jobs", b"projects"}:
                    continue
                components.update((directory.component,) if directory.component else (ROOTS[name.decode()],))
                self.rearm = True
            elif directory.root == "sessions" and re.fullmatch(rb"[0-9]+\.json", name):
                components.add("runtime")
            elif directory.root == "jobs" and directory.path.parent.name == "jobs" and name == b"state.json":
                components.add("runtime")
            elif directory.root == "projects" and name.endswith(b".jsonl"):
                components.add("history")
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
