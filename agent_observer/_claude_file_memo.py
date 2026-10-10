"""Private bounded normalized transcript memo; current native guards own reuse.

This module is stdlib-only so the isolated SDK metadata worker can load it
without importing either client runtime. No registrations, phases or content.
"""

import copy
import fcntl
import json
import os
import re
import stat
from collections import OrderedDict
from pathlib import Path

MAX_ENTRIES = 2048
MAX_PACKET = 1024 * 1024
MAX_TIME = 4_000_000_000_000
_UUID_FILE = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\.jsonl\Z")
_CONTEXT = re.compile(r"[0-9a-f]{64}\Z")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
# Linux UAPI values remain stable even when CPython was built with headers
# that omit the sealing names. Kernel fcntl admission still enforces the seals.
_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
_SEALS = (getattr(fcntl, "F_SEAL_WRITE", 8) | getattr(fcntl, "F_SEAL_GROW", 4)
          | getattr(fcntl, "F_SEAL_SHRINK", 2) | getattr(fcntl, "F_SEAL_SEAL", 1))


def directory_stamp(info):
    return [info.st_dev, info.st_ino, info.st_uid, info.st_mode]


def file_stamp(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_uid, info.st_mode]


def _owned_directory(fd):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise ValueError("claude_memo_directory")
    return directory_stamp(info)


def _integers(value, length):
    return (isinstance(value, list) and len(value) == length
            and all(type(v) is int and -(2**63) <= v < 2**64 for v in value))


def _leaf(value):
    return (isinstance(value, str) and value not in {"", ".", ".."}
            and "/" not in value and "\0" not in value
            and len(os.fsencode(value)) <= 255)


def validate_projection(value):
    if not isinstance(value, dict) or set(value) != {"activity", "kind"}:
        raise ValueError("claude_memo_projection")
    if not isinstance(value["kind"], str) or value["kind"] not in {"user", "child"}:
        raise ValueError("claude_memo_projection")
    activity = value["activity"]
    if not isinstance(activity, dict) or set(activity) != {"at", "source", "health", "reason"}:
        raise ValueError("claude_memo_activity")
    if activity["at"] is None:
        valid = (activity["source"] is None and activity["health"] == "unavailable"
                 and isinstance(activity["reason"], str)
                 and activity["reason"] in {"no_conversation_activity", "activity_tail_limit"})
    else:
        valid = (type(activity["at"]) is int and 0 <= activity["at"] <= MAX_TIME
                 and activity["source"] == "claude_transcript_message"
                 and activity["health"] == "current"
                 and activity["reason"] == "native_conversation_event")
    if not valid:
        raise ValueError("claude_memo_activity")
    return value


def validate_packet(value, home):
    """Syntax/metadata-only admission; it performs no provider filesystem IO."""
    if (not isinstance(value, dict) or set(value) != {"memoVersion", "home", "scope", "context", "entries"}
            or type(value["memoVersion"]) is not int or value["memoVersion"] != 1
            or value["home"] != str(home)
            or value["context"] is not None and (not isinstance(value["context"], str) or not _CONTEXT.fullmatch(value["context"]))
            or not isinstance(value["entries"], list) or len(value["entries"]) > MAX_ENTRIES):
        raise ValueError("claude_memo_packet")
    scope = value["scope"]
    if scope is None:
        if value["entries"]:
            raise ValueError("claude_memo_scope")
    elif (not isinstance(scope, list) or len(scope) != 2
          or any(not _integers(d, 4) or d[2] != os.geteuid() or not stat.S_ISDIR(d[3]) for d in scope)):
        raise ValueError("claude_memo_scope")
    seen = set()
    for row in value["entries"]:
        if (not isinstance(row, dict) or not {"path", "project", "file"} <= set(row)
                or set(row) - {"path", "project", "file", "positive", "projection"}
                or not isinstance(row["path"], list) or len(row["path"]) != 2
                or not all(_leaf(p) for p in row["path"]) or not _UUID_FILE.fullmatch(row["path"][1])
                or not _integers(row["project"], 4) or row["project"][2] != os.geteuid() or not stat.S_ISDIR(row["project"][3])
                or not _integers(row["file"], 7) or row["file"][2] < 0
                or row["file"][5] != os.geteuid() or not stat.S_ISREG(row["file"][6])
                or "positive" in row and row["positive"] is not True):
            raise ValueError("claude_memo_entry")
        key = tuple(row["path"])
        if key in seen or not ({"positive", "projection"} & set(row)):
            raise ValueError("claude_memo_entry")
        seen.add(key)
        if "projection" in row:
            validate_projection(row["projection"])
    if len(json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()) > MAX_PACKET:
        raise ValueError("claude_memo_limit")
    return value


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("claude_memo_duplicate")
        result[key] = value
    return result


def decode_packet(data, home):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_PACKET:
        raise ValueError("claude_memo_limit")
    try:
        value = json.loads(data, object_pairs_hook=_pairs)
        return validate_packet(value, home)
    except (UnicodeError, RecursionError, TypeError, KeyError, OverflowError) as error:
        raise ValueError("claude_memo_packet") from error


def sealed_packet(data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_PACKET:
        raise ValueError("claude_memo_limit")
    writable = os.memfd_create("observer-claude-memo", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(writable, data[offset:])
        fcntl.fcntl(writable, _ADD_SEALS, _SEALS)
        return os.open(f"/proc/self/fd/{writable}", os.O_RDONLY | os.O_CLOEXEC)
    finally:
        os.close(writable)


def read_packet(fd, home):
    if type(fd) is not int or not 3 <= fd <= 1048576:
        raise ValueError("claude_memo_descriptor")
    info = os.fstat(fd)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or not 0 < info.st_size <= MAX_PACKET or flags & os.O_ACCMODE != os.O_RDONLY
            or fcntl.fcntl(fd, _GET_SEALS) & _SEALS != _SEALS):
        raise ValueError("claude_memo_descriptor")
    data = os.pread(fd, MAX_PACKET + 1, 0)
    if len(data) != info.st_size:
        raise ValueError("claude_memo_descriptor")
    return decode_packet(data, home)


class FileMemo:
    def __init__(self, home, value=None):
        self.home = Path(home)
        self.scope, self.context, self.entries = None, None, OrderedDict()
        if value is not None:
            value = validate_packet(value, self.home)
            self.scope = copy.deepcopy(value["scope"])
            self.context = value["context"]
            self.entries = OrderedDict((tuple(r["path"]), copy.deepcopy(r)) for r in value["entries"])

    def clear(self):
        self.entries.clear()
        self.scope = None

    def bind_context(self, context):
        if context != self.context:
            self.clear()
            self.context = context

    def _parents(self, project):
        root = projects = parent = None
        try:
            root = os.open(self.home, _DIR_FLAGS)
            projects = os.open("projects", _DIR_FLAGS, dir_fd=root)
            scope = [_owned_directory(root), _owned_directory(projects)]
            if scope != self.scope:
                self.entries.clear()
                self.scope = scope
            parent = os.open(project, _DIR_FLAGS, dir_fd=projects)
            stamp = _owned_directory(parent)
            return parent, stamp
        except BaseException:
            if parent is not None:
                os.close(parent)
            raise
        finally:
            for fd in (projects, root):
                if fd is not None:
                    os.close(fd)

    def _guard(self, fd, project, name):
        if not _leaf(project) or not _leaf(name) or not _UUID_FILE.fullmatch(name):
            raise ValueError("claude_memo_path")
        parent, directory = self._parents(project)
        try:
            info = os.fstat(fd)
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or file_stamp(info) != file_stamp(current)):
                raise ValueError("claude_memo_file")
            return directory, file_stamp(info)
        finally:
            os.close(parent)

    def get(self, fd, project, name, field):
        key = project, name
        try:
            directory, stamp = self._guard(fd, project, name)
            row = self.entries.get(key)
            if row is None:
                return None
            if row["project"] != directory or row["file"] != stamp:
                del self.entries[key]
                return None
            value = copy.deepcopy(row.get(field))
            if self._guard(fd, project, name) != (directory, stamp):
                self.entries.pop(key, None)
                return None
            self.entries.move_to_end(key)
            return value
        except (OSError, ValueError, UnicodeError):
            self.entries.pop(key, None)
            return None

    def put(self, fd, project, name, field, value, before):
        key = project, name
        try:
            if field == "positive":
                if value is not True:
                    return
            elif field == "projection":
                try:
                    validate_projection(value)
                except ValueError:
                    return
            else:
                raise ValueError("claude_memo_field")
            directory, stamp = self._guard(fd, project, name)
            if stamp != file_stamp(before):
                self.entries.pop(key, None)
                return
            row = self.entries.get(key)
            if row is None or row["project"] != directory or row["file"] != stamp:
                row = {"path": list(key), "project": directory, "file": stamp}
            row[field] = copy.deepcopy(value)
            self.entries[key] = row
            self.entries.move_to_end(key)
            while len(self.entries) > MAX_ENTRIES:
                self.entries.popitem(last=False)
        except (OSError, ValueError, UnicodeError):
            self.entries.pop(key, None)

    def retain(self, paths):
        for key in list(self.entries):
            if key not in paths:
                del self.entries[key]

    def export(self):
        while True:
            value = {"memoVersion": 1, "home": str(self.home), "scope": self.scope,
                     "context": self.context, "entries": list(self.entries.values())}
            data = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()
            if len(data) <= MAX_PACKET:
                return copy.deepcopy(value)
            self.entries.popitem(last=False)

    def descriptor(self):
        return sealed_packet(json.dumps(self.export(), separators=(",", ":")).encode())
