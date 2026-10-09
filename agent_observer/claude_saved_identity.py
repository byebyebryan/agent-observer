"""Bounded positive saved identities; catalog absence grants no lifecycle state."""

import os
import re
import stat
import time

from .bounded_json import decode_document

MAX_PROJECTS, MAX_ENTRIES, MAX_IDS, MAX_BYTES = 256, 8192, 4096, 64 * 1024
_UUID_FILE = re.compile(r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})\.jsonl\Z")
_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK


def _owned_directory(fd):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise ValueError("saved_directory_rejected")
    return info.st_dev, info.st_ino


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _identity(directory_fd, name, sid):
    fd = os.open(name, _FLAGS, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid():
            return False
        head = os.read(fd, MAX_BYTES)
        offset = max(0, before.st_size - MAX_BYTES)
        os.lseek(fd, offset, os.SEEK_SET)
        tail = os.read(fd, MAX_BYTES)
        if (_signature(before) != _signature(os.fstat(fd)) or _signature(before) !=
                _signature(os.stat(name, dir_fd=directory_fd, follow_symlinks=False))):
            return False
    finally:
        os.close(fd)
    lines = head.split(b"\n")[:-1] + (tail.split(b"\n")[1:-1] if offset else [])
    identities = set()
    for line in lines:
        if not line:
            continue
        value = decode_document(line, max_bytes=MAX_BYTES, max_depth=32, max_nodes=16384)
        if isinstance(value, dict) and isinstance(value.get("sessionId"), str):
            identities.add(value["sessionId"].lower())
    return identities == {sid}


def saved_ids(home, candidates=None):
    """Return fresh positive UUIDs, optionally restricted to supplied identities.

    An incomplete catalog retains proven positives; it is never a negative
    roster. All parent directories are descriptor anchored and owner checked.
    """
    found, root_fd = set(), None
    if candidates is not None and not candidates:
        return found
    deadline = time.monotonic() + 2
    try:
        root = home / "projects"
        root_fd = os.open(root, _FLAGS | os.O_DIRECTORY)
        root_stamp = _owned_directory(root_fd)
        directories = []
        with os.scandir(root_fd) as stream:
            for entry in stream:
                if len(directories) >= MAX_PROJECTS:
                    break
                directories.append(entry.name)
        entries = 0
        for name in directories:
            if time.monotonic() > deadline or len(found) >= MAX_IDS:
                break
            project_fd = None
            try:
                project_fd = os.open(name, _FLAGS | os.O_DIRECTORY, dir_fd=root_fd)
                stamp = _owned_directory(project_fd)
                proven = set()
                with os.scandir(project_fd) as files:
                    for entry in files:
                        entries += 1
                        if entries > MAX_ENTRIES or time.monotonic() > deadline or len(found | proven) >= MAX_IDS:
                            break
                        match = _UUID_FILE.fullmatch(entry.name)
                        if match is None:
                            continue
                        sid = match[1].lower()
                        if candidates is not None and sid not in candidates or sid in found:
                            continue
                        try:
                            if _identity(project_fd, entry.name, sid):
                                proven.add(sid)
                        except (OSError, ValueError):
                            continue
                current = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == stamp and stat.S_ISDIR(current.st_mode) and current.st_uid == os.geteuid():
                    found.update(proven)
            except (OSError, ValueError):
                continue
            finally:
                if project_fd is not None:
                    os.close(project_fd)
            if entries > MAX_ENTRIES:
                break
        current_root = root.lstat()
        if (current_root.st_dev, current_root.st_ino) != root_stamp:
            return set()
    except (OSError, ValueError):
        return set()
    finally:
        if root_fd is not None:
            os.close(root_fd)
    return found
