"""Frozen a14 parser oracle for optimization parity tests; never production."""

import json, os, stat

from pathlib import Path

from datetime import datetime

MAX_ACTIVITY_BYTES = 512 * 1024

MAX_COMPANION_BYTES = 64 * 1024

MAX_TIME_MS = 4_000_000_000_000

def _owner_is_current(st: os.stat_result) -> bool:
    return st.st_uid == os.geteuid()

def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_metadata_key")
        result[key] = value
    return result

def _file_stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

def transcript_activity(path: Path, session_id: str) -> dict[str, object]:
    """Read a bounded tail; only timestamp provenance crosses this boundary."""

    def missing(reason):
        return {"at": None, "source": None, "health": "unavailable", "reason": reason}

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_metadata_key")
            result[key] = value
        return result

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not _owner_is_current(before):
                return missing("activity_source_unsafe")
            offset = max(0, before.st_size - MAX_ACTIVITY_BYTES)
            os.lseek(fd, offset, os.SEEK_SET)
            content = os.read(fd, MAX_ACTIVITY_BYTES)
            if len(content) != before.st_size - offset:
                return missing("activity_source_changed")
            after = os.fstat(fd)
            bound = os.stat(path, follow_symlinks=False)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) or (after.st_dev, after.st_ino) != (bound.st_dev, bound.st_ino):
                return missing("activity_source_changed")
        finally:
            os.close(fd)
    except OSError:
        return missing("activity_source_unavailable")
    if content and not content.endswith(b"\n"):
        return missing("activity_record_incomplete")
    lines = content.splitlines()
    if offset:
        lines = lines[1:]
    latest = None
    for line in lines:
        if not line:
            continue
        try:
            value = json.loads(line, object_pairs_hook=pairs)
        except (ValueError, UnicodeError, RecursionError):
            return missing("activity_metadata_invalid")
        if not isinstance(value, dict) or value.get("type") not in {"user", "assistant"}:
            continue
        if value.get("isSidechain") is not False or value.get("isMeta") is True:
            continue
        if value.get("sessionId") != session_id:
            return missing("activity_identity_conflict")
        message = value.get("message")
        if not isinstance(message, dict) or message.get("role") != value["type"]:
            return missing("activity_metadata_invalid")
        # Native local slash commands/output are user records without isMeta.
        # Only their reserved envelope is inspected; no text crosses this boundary.
        body = message.get("content")
        if value["type"] == "user" and isinstance(body, str) and body.startswith(
            ("<command-name>", "<local-command-stdout>", "<local-command-stderr>", "<local-command-caveat>")
        ):
            continue
        stamp = value.get("timestamp")
        try:
            if not isinstance(stamp, str) or len(stamp) > 64:
                raise ValueError()
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError()
            at = int(parsed.timestamp() * 1000)
            if not 0 <= at <= MAX_TIME_MS:
                raise ValueError()
        except (ValueError, OverflowError, OSError):
            return missing("activity_clock_unavailable")
        latest = max(latest or 0, at)
    if latest is None:
        return missing("activity_tail_limit" if offset else "no_conversation_activity")
    return {
        "at": latest,
        "source": "claude_transcript_message",
        "health": "current",
        "reason": "native_conversation_event",
    }

def transcript_kind(path: Path, session_id: str) -> str:
    """Identity-bound conversation classification, independent of its clock."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not _owner_is_current(before):
                return "unknown"
            data = os.read(fd, MAX_COMPANION_BYTES)
            offset = max(0, before.st_size - MAX_ACTIVITY_BYTES)
            os.lseek(fd, offset, os.SEEK_SET)
            tail = os.read(fd, MAX_ACTIVITY_BYTES)
            if _file_stamp(before) != _file_stamp(os.fstat(fd)) or _file_stamp(before) != _file_stamp(path.lstat()):
                return "unknown"
        finally:
            os.close(fd)
        lines = data.splitlines() if data.endswith(b"\n") else data.splitlines()[:-1]
        tail_lines = tail.splitlines() if tail.endswith(b"\n") else tail.splitlines()[:-1]
        lines += tail_lines[1:] if offset else tail_lines
        kinds = set()
        for line in lines:
            value = json.loads(line, object_pairs_hook=_unique_pairs)
            if not isinstance(value, dict) or value.get("type") not in {"user", "assistant"}:
                continue
            if value.get("sessionId") != session_id:
                return "unknown"
            if value.get("isMeta") is True:
                continue
            message = value.get("message")
            if not isinstance(message, dict) or message.get("role") != value["type"]:
                return "unknown"
            body = message.get("content")
            if value["type"] == "user" and isinstance(body, str) and body.startswith(
                ("<command-name>", "<local-command-stdout>", "<local-command-stderr>", "<local-command-caveat>")
            ):
                continue
            if value.get("isSidechain") is False:
                kinds.add("user")
            elif value.get("isSidechain") is True:
                kinds.add("child")
        return next(iter(kinds)) if len(kinds) == 1 else "unknown"
    except (OSError, ValueError, TypeError, RecursionError):
        return "unknown"
