"""Isolated read-only worker for the pinned Claude Agent SDK history API.

This file is executed by :mod:`agent_observer.claude_history` in a bounded
Python subprocess. It deliberately imports no Agent Observer code and emits
only allowlisted session metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

SDK_VERSION = "0.2.163"
MAX_PROJECTS = 256
MAX_FILES = 2048
MAX_DIRECTORY_ENTRIES = 8192
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_CENSUS_SECONDS = 5.0
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_TIME_MS = 4_000_000_000_000
MAX_ACTIVITY_BYTES = 512 * 1024
MAX_ACTIVITY_TOTAL_BYTES = 64 * 1024 * 1024
MAX_COMPANION_BYTES = 64 * 1024
_COMPANION_KEYS = {
    "last-prompt": {"lastPrompt", "leafUuid"},
    "custom-title": {"customTitle"},
    "agent-name": {"agentName"},
    "agent-color": {"agentColor"},
    "mode": {"mode"},
    "permission-mode": {"permissionMode"},
    "atis-latch": {"atis"},
    "worktree-state": {"worktreeSession"},
    "pr-link": {"prNumber", "prRepository", "prUrl", "timestamp"},
    "cost-state": {
        "hasUnknownModelCost", "modelUsage", "startTime", "totalAPIDuration",
        "totalAPIDurationWithoutRetries", "totalCostUSD", "totalDuration",
        "totalLinesAdded", "totalLinesRemoved", "totalToolDuration",
    },
}
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
_FORBIDDEN_EVENTS = frozenset(
    {
        "subprocess.Popen",
        "os.system",
        "os.fork",
        "os.posix_spawn",
        "os.spawn",
        "socket.__new__",
        "socket.connect",
        "socket.getaddrinfo",
        "socket.getnameinfo",
        "socket.sendto",
        "socket.sendmsg",
        "os.mkdir",
        "os.rmdir",
        "os.remove",
        "os.rename",
        "os.replace",
        "os.truncate",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.symlink",
        "os.utime",
    }
)


class _WorkerFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise _WorkerFailure("history_limit")


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


def duplicate_file_kind(path: Path, session_id: str) -> str:
    """Classify exact UUID-bound native envelopes, never by size or recency."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not _owner_is_current(before):
                return "unproved"
            data = os.read(fd, MAX_COMPANION_BYTES + 1)
            after = os.fstat(fd)
            current = path.lstat()
            if _file_stamp(before) != _file_stamp(after) or _file_stamp(before) != _file_stamp(current):
                return "unproved"
        finally:
            os.close(fd)
        complete = len(data) == before.st_size and data.endswith(b"\n")
        lines = data.splitlines() if complete else data.splitlines()[:-1]
        if not lines:
            return "unproved"
        companion = complete and before.st_size <= MAX_COMPANION_BYTES
        conversation = False
        for line in lines:
            value = json.loads(line, object_pairs_hook=_unique_pairs)
            if not isinstance(value, dict):
                return "unproved"
            native_id = value.get("sessionId")
            if native_id is not None and (
                not isinstance(native_id, str) or native_id.lower() != session_id
            ):
                return "unproved"
            kind = value.get("type")
            if kind in {"user", "assistant"} and value.get("isSidechain") is not True:
                if native_id is None:
                    return "unproved"
                conversation = True
            if native_id is None or kind not in _COMPANION_KEYS or not set(value) <= (
                _COMPANION_KEYS.get(kind, set()) | {"type", "sessionId"}
            ):
                companion = False
        return "conversation" if conversation else "companion" if companion else "unproved"
    except (OSError, ValueError, TypeError, AttributeError, RecursionError):
        return "unproved"


def exact_sdk_metadata(path: Path, session_id: str):
    """Pinned SDK parser applied to the single proved conversation file.

    Its global catalog deduplicates by mtime and can choose a companion. Keep
    title/cwd extraction in the pinned SDK, binding its lite parser to an owned
    open descriptor instead of accepting that catalog preference.
    """
    from claude_agent_sdk._internal.sessions import (
        _parse_session_info_from_lite,
        _read_session_lite,
    )

    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        lite = _read_session_lite(Path(f"/proc/self/fd/{fd}"))
        after = os.fstat(fd)
        current = path.lstat()
        if lite is None or _file_stamp(before) != _file_stamp(after) or _file_stamp(before) != _file_stamp(current):
            return None
        return _parse_session_info_from_lite(session_id, lite)
    finally:
        os.close(fd)


def census_projects(projects_dir: Path) -> dict[str, object]:
    """Bound and validate the SDK's top-level project/transcript scan surface."""
    deadline = time.monotonic() + MAX_CENSUS_SECONDS
    try:
        projects_stat = os.lstat(projects_dir)
    except OSError:
        raise _WorkerFailure("history_source_failed") from None
    if (
        stat.S_ISLNK(projects_stat.st_mode)
        or not stat.S_ISDIR(projects_stat.st_mode)
        or not _owner_is_current(projects_stat)
    ):
        raise _WorkerFailure("history_unsafe_entry")

    project_dirs: list[Path] = []
    signature_parts: list[tuple[object, ...]] = []
    entry_count = 0
    try:
        with os.scandir(projects_dir) as entries:
            for entry in entries:
                _check_deadline(deadline)
                entry_count += 1
                if entry_count > MAX_DIRECTORY_ENTRIES:
                    raise _WorkerFailure("history_limit")
                st = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(st.st_mode):
                    raise _WorkerFailure("history_unsafe_entry")
                if stat.S_ISDIR(st.st_mode):
                    if not _owner_is_current(st):
                        raise _WorkerFailure("history_unsafe_entry")
                    project_dirs.append(Path(entry.path))
                    signature_parts.append(
                        (b"project", os.fsencode(entry.name), st.st_dev, st.st_ino, st.st_uid)
                    )
                    if len(project_dirs) > MAX_PROJECTS:
                        raise _WorkerFailure("history_limit")
                elif stat.S_ISREG(st.st_mode):
                    if not _owner_is_current(st):
                        raise _WorkerFailure("history_unsafe_entry")
                    signature_parts.append(
                        (
                            b"root-file",
                            os.fsencode(entry.name),
                            st.st_dev,
                            st.st_ino,
                            st.st_size,
                            st.st_mtime_ns,
                            st.st_ctime_ns,
                        )
                    )
                else:
                    raise _WorkerFailure("history_unsafe_entry")
    except _WorkerFailure:
        raise
    except OSError:
        raise _WorkerFailure("history_source_failed") from None

    candidate_files = 0
    total_bytes = 0
    valid_ids: set[str] = set()
    id_counts: dict[str, int] = {}
    malformed_ids = 0
    transcript_paths = {}
    candidates = {}

    for project_dir in project_dirs:
        _check_deadline(deadline)
        try:
            with os.scandir(project_dir) as entries:
                for entry in entries:
                    _check_deadline(deadline)
                    entry_count += 1
                    if entry_count > MAX_DIRECTORY_ENTRIES:
                        raise _WorkerFailure("history_limit")
                    st = entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(st.st_mode):
                        raise _WorkerFailure("history_unsafe_entry")
                    if stat.S_ISDIR(st.st_mode):
                        if not _owner_is_current(st):
                            raise _WorkerFailure("history_unsafe_entry")
                        signature_parts.append(
                            (
                                b"transcript-dir",
                                os.fsencode(project_dir.name),
                                os.fsencode(entry.name),
                                st.st_dev,
                                st.st_ino,
                                st.st_uid,
                            )
                        )
                        continue
                    if not stat.S_ISREG(st.st_mode) or not _owner_is_current(st):
                        raise _WorkerFailure("history_unsafe_entry")
                    if not entry.name.endswith(".jsonl"):
                        signature_parts.append(
                            (
                                b"project-file",
                                os.fsencode(project_dir.name),
                                os.fsencode(entry.name),
                                st.st_dev,
                                st.st_ino,
                                st.st_size,
                                st.st_mtime_ns,
                                st.st_ctime_ns,
                            )
                        )
                        continue

                    candidate_files += 1
                    if candidate_files > MAX_FILES or st.st_size > MAX_FILE_BYTES:
                        raise _WorkerFailure("history_limit")
                    total_bytes += st.st_size
                    if total_bytes > MAX_TOTAL_BYTES:
                        raise _WorkerFailure("history_limit")
                    session_id = entry.name[:-6]
                    signature_parts.append(
                        (
                            b"transcript",
                            os.fsencode(project_dir.name),
                            os.fsencode(entry.name),
                            st.st_dev,
                            st.st_ino,
                            st.st_uid,
                        )
                    )
                    if not os.access(entry.path, os.R_OK):
                        raise _WorkerFailure("history_source_failed")
                    if not _UUID.fullmatch(session_id):
                        malformed_ids += 1
                        continue
                    normalized_id = session_id.lower()
                    transcript_paths[normalized_id] = Path(entry.path)
                    candidates.setdefault(normalized_id, []).append(Path(entry.path))
                    valid_ids.add(normalized_id)
                    id_counts[normalized_id] = id_counts.get(normalized_id, 0) + 1
        except _WorkerFailure:
            raise
        except OSError:
            raise _WorkerFailure("history_source_failed") from None

    duplicates = {session_id for session_id, count in id_counts.items() if count > 1}
    resolved_duplicates = set()
    for session_id in duplicates:
        _check_deadline(deadline)
        kinds = [(path, duplicate_file_kind(path, session_id)) for path in candidates[session_id]]
        conversations = [path for path, kind in kinds if kind == "conversation"]
        if len(conversations) == 1 and all(
            kind in {"conversation", "companion"} for _path, kind in kinds
        ):
            transcript_paths[session_id] = conversations[0]
            resolved_duplicates.add(session_id)
    signature = hashlib.sha256()
    for part in sorted(signature_parts):
        signature.update(
            b"\0".join(str(item).encode() if not isinstance(item, bytes) else item for item in part)
        )
        signature.update(b"\n")
    return {
        "projects": len(project_dirs),
        "entries": entry_count,
        "candidate_files": candidate_files,
        "total_bytes": total_bytes,
        "valid_ids": valid_ids,
        "duplicate_ids": duplicates,
        "resolved_duplicates": resolved_duplicates,
        "malformed_ids": malformed_ids,
        "signature": signature.digest(),
        "transcript_paths": transcript_paths,
    }


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


def _bounded_text(value: object, *, max_chars: int, max_utf8_bytes: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(
        " " if unicodedata.category(char).startswith("C") else char
        for char in value[: max_chars * 4]
    )
    cleaned = " ".join(cleaned.split()).strip()
    if not cleaned or len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    try:
        if len(cleaned.encode("utf-8")) > max_utf8_bytes:
            return None
    except UnicodeEncodeError:
        return None
    return cleaned or None


def _bounded_cwd(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or value.startswith("//")
        or "//" in value
        or len(value) > 4096
        or any(unicodedata.category(char).startswith("C") for char in value)
    ):
        return None
    try:
        if len(value.encode("utf-8")) > 4096:
            return None
    except UnicodeEncodeError:
        return None
    return value


def _valid_epoch(value: object) -> int | None:
    if type(value) is int and 0 <= value <= MAX_TIME_MS:
        return value
    return None


def _emit(payload: dict[str, object]) -> None:
    try:
        output = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        output = b'{"error":"history_source_failed"}'
    if len(output) > MAX_OUTPUT_BYTES:
        output = b'{"error":"history_limit"}'
    os.write(sys.stdout.fileno(), output + b"\n")


def _install_audit_guard(blocked: list[str]) -> None:
    def guard(event: str, args: tuple[object, ...]) -> None:
        if event in _FORBIDDEN_EVENTS:
            blocked.append(event)
            raise PermissionError("read-only SDK history scan")
        if event == "open":
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            if any(char in mode for char in "wax+") or flags & _WRITE_FLAGS:
                blocked.append("filesystem-write")
                raise PermissionError("read-only SDK history scan")
        if event == "os.open":
            flags = args[1] if len(args) > 1 and isinstance(args[1], int) else 0
            if flags & _WRITE_FLAGS:
                blocked.append("filesystem-write")
                raise PermissionError("read-only SDK history scan")

    sys.addaudithook(guard)


def main() -> int:
    sys.dont_write_bytecode = True
    config_value = os.environ.get("CLAUDE_CONFIG_DIR")
    if not config_value:
        _emit({"error": "history_source_failed"})
        return 0

    config_dir = Path(config_value)
    try:
        config_stat = os.lstat(config_dir)
    except OSError:
        _emit({"error": "history_source_failed"})
        return 0
    if (
        stat.S_ISLNK(config_stat.st_mode)
        or not stat.S_ISDIR(config_stat.st_mode)
        or not _owner_is_current(config_stat)
    ):
        _emit({"error": "history_unsafe_entry"})
        return 0

    try:
        census = census_projects(config_dir / "projects")
    except _WorkerFailure as exc:
        _emit({"error": exc.code})
        return 0

    blocked: list[str] = []
    _install_audit_guard(blocked)
    try:
        from claude_agent_sdk import __version__, list_sessions
    except ImportError:
        _emit({"error": "history_sdk_unavailable"})
        return 0
    except Exception:
        _emit({"error": "history_source_failed"})
        return 0
    if __version__ != SDK_VERSION:
        _emit({"error": "history_sdk_unavailable"})
        return 0

    try:
        sessions = list_sessions()
    except Exception:
        _emit({"error": "history_source_failed"})
        return 0
    if blocked:
        _emit({"error": "history_source_failed"})
        return 0
    try:
        after_census = census_projects(config_dir / "projects")
    except _WorkerFailure as exc:
        _emit({"error": exc.code})
        return 0
    if census["signature"] != after_census["signature"]:
        _emit({"error": "history_source_failed"})
        return 0
    if not isinstance(sessions, list) or len(sessions) > MAX_FILES:
        _emit({"error": "history_limit"})
        return 0

    errors: set[str] = set()
    valid_ids = census["valid_ids"]
    seen_ids: set[str] = set()
    rows: list[dict[str, object]] = []
    activity_bytes = 0
    for session in sessions:
        session_id = getattr(session, "session_id", None)
        if not isinstance(session_id, str) or not _UUID.fullmatch(session_id):
            errors.add("history_ambiguous")
            continue
        session_id = session_id.lower()
        if session_id not in valid_ids or session_id in seen_ids:
            errors.add("history_ambiguous")
            continue
        seen_ids.add(session_id)
        path = after_census["transcript_paths"].get(session_id)
        if session_id in census["duplicate_ids"] or session_id in after_census["duplicate_ids"]:
            if not (
                session_id in census["resolved_duplicates"]
                and session_id in after_census["resolved_duplicates"]
                and census["transcript_paths"][session_id] == path
            ):
                errors.add("history_ambiguous")
                continue
            try:
                session = exact_sdk_metadata(path, session_id)
            except Exception:
                session = None
            if session is None:
                errors.add("history_ambiguous")
                continue
        try:
            activity_bytes += min(path.stat().st_size, MAX_ACTIVITY_BYTES)
        except OSError:
            activity_bytes += MAX_ACTIVITY_BYTES
        activity = (
            transcript_activity(path, session_id)
            if activity_bytes <= MAX_ACTIVITY_TOTAL_BYTES
            else {
                "at": None,
                "source": None,
                "health": "unavailable",
                "reason": "activity_scan_limit",
            }
        )
        rows.append(
            {
                "session_id": session_id,
                "custom_title": _bounded_text(
                    getattr(session, "custom_title", None), max_chars=256, max_utf8_bytes=1024
                ),
                "cwd": _bounded_cwd(getattr(session, "cwd", None)),
                "created_at": _valid_epoch(getattr(session, "created_at", None)),
                "last_modified": _valid_epoch(getattr(session, "last_modified", None)),
                "activity": activity,
            }
        )

    _emit(
        {
            "sdk_version": SDK_VERSION,
            "census": {
                "projects": census["projects"],
                "candidate_files": census["candidate_files"],
                "total_bytes": census["total_bytes"],
                "candidate_ids": len(valid_ids),
                "sdk_returned_ids": len(seen_ids),
                "projected_ids": len(rows),
                "sdk_omitted_ids": len(valid_ids - seen_ids),
                "unresolved_ids": len(seen_ids - {r["session_id"] for r in rows}),
                "duplicate_ids": len(census["duplicate_ids"]),
                "resolved_companion_ids": len(census["resolved_duplicates"]),
                "malformed_filename_ids": census["malformed_ids"],
            },
            "rows": rows,
            "errors": sorted(errors),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
