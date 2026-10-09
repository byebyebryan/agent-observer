"""Bounded positive saved identities for runtime reads; absence grants no state."""

import os
import stat
import time

from .bounded_json import decode_document

MAX_PROJECTS, MAX_ENTRIES, MAX_BYTES = 256, 8192, 64 * 1024


def saved_ids(home, candidates):
    found = set()
    if not candidates:
        return found
    deadline = time.monotonic() + 2
    try:
        root = home / "projects"
        stamp = root.lstat()
        if not stat.S_ISDIR(stamp.st_mode) or stamp.st_uid != os.geteuid():
            return found
        with os.scandir(root) as projects:
            directories = list(projects)
        if len(directories) > MAX_PROJECTS:
            return found
        entries = 0
        for directory in directories:
            if time.monotonic() > deadline:
                break
            info = directory.stat(follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
                continue
            with os.scandir(directory.path) as files:
                names = []
                for entry in files:
                    entries += 1
                    if entries > MAX_ENTRIES or time.monotonic() > deadline:
                        return found
                    names.append(entry.name)
            for sid in candidates - found:
                name = sid + ".jsonl"
                if name not in names:
                    continue
                path = home / "projects" / directory.name / name
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
                    try:
                        before = os.fstat(fd)
                        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid():
                            continue
                        head = os.read(fd, MAX_BYTES)
                        offset = max(0, before.st_size - MAX_BYTES)
                        os.lseek(fd, offset, os.SEEK_SET)
                        tail = os.read(fd, MAX_BYTES)
                        signature = lambda v: (v.st_dev, v.st_ino, v.st_size, v.st_mtime_ns, v.st_ctime_ns)
                        if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(path.lstat()):
                            continue
                    finally:
                        os.close(fd)
                    current_parent = (root / directory.name).lstat()
                    if (current_parent.st_dev, current_parent.st_ino) != (info.st_dev, info.st_ino):
                        continue
                    lines = head.split(b"\n")[:-1] + (tail.split(b"\n")[1:-1] if offset else [])
                    identities = set()
                    for line in lines:
                        if not line:
                            continue
                        value = decode_document(line, max_bytes=MAX_BYTES, max_depth=32, max_nodes=16384)
                        if isinstance(value, dict) and isinstance(value.get("sessionId"), str):
                            identities.add(value["sessionId"])
                    if identities == {sid}:
                        found.add(sid)
                except (OSError, ValueError):
                    continue
        if (root.lstat().st_dev, root.lstat().st_ino) != (stamp.st_dev, stamp.st_ino):
            return set()
    except OSError:
        pass
    return found
