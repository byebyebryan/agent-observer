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
                            st.st_size,
                            st.st_mtime_ns,
                            st.st_ctime_ns,
                        )
                    )
                    if not os.access(entry.path, os.R_OK):
                        raise _WorkerFailure("history_source_failed")
                    if not _UUID.fullmatch(session_id):
                        malformed_ids += 1
                        continue
                    normalized_id = session_id.lower()
                    valid_ids.add(normalized_id)
                    id_counts[normalized_id] = id_counts.get(normalized_id, 0) + 1
        except _WorkerFailure:
            raise
        except OSError:
            raise _WorkerFailure("history_source_failed") from None

    duplicates = {session_id for session_id, count in id_counts.items() if count > 1}
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
        "malformed_ids": malformed_ids,
        "signature": signature.digest(),
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
        rows.append(
            {
                "session_id": session_id,
                "custom_title": _bounded_text(
                    getattr(session, "custom_title", None), max_chars=256, max_utf8_bytes=1024
                ),
                "cwd": _bounded_cwd(getattr(session, "cwd", None)),
                "created_at": _valid_epoch(getattr(session, "created_at", None)),
                "last_modified": _valid_epoch(getattr(session, "last_modified", None)),
            }
        )

    _emit(
        {
            "sdk_version": SDK_VERSION,
            "census": {
                "projects": census["projects"],
                "candidate_files": census["candidate_files"],
                "total_bytes": census["total_bytes"],
            },
            "rows": rows,
            "errors": sorted(errors),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
