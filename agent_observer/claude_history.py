"""Bounded saved-history projection through the pinned public Claude SDK."""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from .contract import ACTIVITY, validate_shape

SDK_VERSION = "0.2.163"
DEFAULT_HISTORY_LIMIT = 100
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_TIMEOUT_SECONDS = 30.0
MAX_HELPER_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_HELPER_ROWS = 2048
MAX_TIME_MS = 4_000_000_000_000
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_ERROR_CODES = frozenset(
    {
        "history_sdk_unavailable",
        "history_source_failed",
        "history_timeout",
        "history_limit",
        "history_unsafe_entry",
        "history_ambiguous",
    }
)


def _error(code: str) -> dict[str, object]:
    if code not in _ERROR_CODES:
        code = "history_source_failed"
    return {
        "rows": [],
        "coverage": {
            "complete": False,
            "reason": "history_limit" if code == "history_limit" else "source_failed",
        },
        "errors": [{"code": code}],
    }


def _valid_time(value: object) -> int | None:
    if type(value) is int and 0 <= value <= MAX_TIME_MS:
        return value
    return None


def _validate_payload(payload: object) -> tuple[list[dict[str, object]], list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("invalid_worker_payload")
    if "error" in payload:
        code = payload["error"]
        if not isinstance(code, str) or code not in _ERROR_CODES:
            raise ValueError("invalid_worker_error")
        return [], [code]
    if set(payload) != {"sdk_version", "census", "rows", "errors"}:
        raise ValueError("invalid_worker_fields")
    if payload.get("sdk_version") != SDK_VERSION:
        raise ValueError("invalid_worker_version")
    census = payload.get("census")
    if not isinstance(census, dict) or any(
        type(census.get(name)) is not int or census[name] < 0
        for name in ("projects", "candidate_files", "total_bytes")
    ):
        raise ValueError("invalid_worker_census")
    if census["projects"] > 256 or census["candidate_files"] > MAX_HELPER_ROWS:
        raise ValueError("worker_census_limit")
    if census["total_bytes"] > 2 * 1024 * 1024 * 1024:
        raise ValueError("worker_census_limit")
    count_fields = {"candidate_ids", "sdk_returned_ids", "projected_ids", "sdk_omitted_ids",
                    "unresolved_ids", "duplicate_ids", "resolved_companion_ids", "malformed_filename_ids"}
    if set(census) - {"projects", "candidate_files", "total_bytes"} not in (set(), count_fields):
        raise ValueError("invalid_worker_census")
    if count_fields <= set(census):
        if any(type(census[k]) is not int or not 0 <= census[k] <= MAX_HELPER_ROWS for k in count_fields):
            raise ValueError("invalid_worker_census")
        if (census["candidate_ids"] > census["candidate_files"]
                or census["sdk_returned_ids"] + census["sdk_omitted_ids"] != census["candidate_ids"]
                or census["projected_ids"] + census["unresolved_ids"] != census["sdk_returned_ids"]
                or census["resolved_companion_ids"] > census["duplicate_ids"]
                or census["duplicate_ids"] > census["candidate_ids"]):
            raise ValueError("invalid_worker_census")

    raw_rows = payload.get("rows")
    raw_errors = payload.get("errors")
    if not isinstance(raw_rows, list) or len(raw_rows) > MAX_HELPER_ROWS:
        raise ValueError("invalid_worker_rows")
    if len(raw_rows) > census["candidate_files"]:
        raise ValueError("invalid_worker_census")
    if "projected_ids" in census and len(raw_rows) != census["projected_ids"]:
        raise ValueError("invalid_worker_census")
    if not isinstance(raw_errors, list) or any(
        not isinstance(code, str) or code not in _ERROR_CODES for code in raw_errors
    ):
        raise ValueError("invalid_worker_errors")

    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for value in raw_rows:
        if not isinstance(value, dict) or set(value) != {
            "session_id",
            "custom_title",
            "cwd",
            "created_at",
            "last_modified",
            "activity",
        }:
            raise ValueError("invalid_worker_row")
        session_id = value.get("session_id")
        if not isinstance(session_id, str) or not _UUID.fullmatch(session_id):
            raise ValueError("invalid_worker_identity")
        session_id = session_id.lower()
        if session_id in seen:
            raise ValueError("invalid_worker_identity")
        seen.add(session_id)

        custom_title = value.get("custom_title")
        if custom_title is not None and (
            not isinstance(custom_title, str)
            or len(custom_title) > 256
            or len(custom_title.encode("utf-8")) > 1024
            or any(unicodedata.category(char).startswith("C") for char in custom_title)
        ):
            raise ValueError("invalid_worker_title")
        cwd = value.get("cwd")
        if cwd is not None and (
            not isinstance(cwd, str)
            or not cwd.startswith("/")
            or cwd.startswith("//")
            or "//" in cwd
            or len(cwd) > 4096
            or len(cwd.encode("utf-8")) > 4096
            or any(unicodedata.category(char).startswith("C") for char in cwd)
        ):
            raise ValueError("invalid_worker_cwd")
        validate_shape(value["activity"], ACTIVITY)
        if value["activity"]["at"] is not None and (
            value["activity"]["health"] != "current"
            or value["activity"]["source"] != "claude_transcript_message"
        ):
            raise ValueError("invalid_worker_activity")
        rows.append(
            {
                "session_id": session_id,
                "custom_title": custom_title,
                "cwd": cwd,
                "created_at": _valid_time(value.get("created_at")),
                "last_modified": _valid_time(value.get("last_modified")),
                "activity": value["activity"],
            }
        )
    return rows, list(dict.fromkeys(raw_errors))


def _kill_process(process: subprocess.Popen[bytes], *, grouped=True) -> None:
    try:
        if grouped and hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    except OSError:
        process.kill()


def _run_worker(config_home: Path, *, timeout: float, owned_worker_group=False) -> tuple[bytes | None, str | None]:
    if owned_worker_group and (os.getpgrp() != os.getpid() or os.getsid(0) != os.getpid()):
        return None, "history_source_failed"
    worker = Path(__file__).with_name("_claude_history_worker.py")
    env = {
        "CLAUDE_CONFIG_DIR": str(config_home),
        "HOME": str(Path.home()),
        "PATH": os.defpath,
        "PYTHONNOUSERSITE": "1",
    }
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(worker)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(config_home),
            env=env,
            close_fds=True,
            start_new_session=not owned_worker_group,
        )
    except OSError:
        return None, "history_source_failed"

    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process(process, grouped=not owned_worker_group)
                process.wait()
                return None, "history_timeout"
            ready = selector.select(remaining)
            if not ready:
                _kill_process(process, grouped=not owned_worker_group)
                process.wait()
                return None, "history_timeout"
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > MAX_HELPER_OUTPUT_BYTES + 1:
                _kill_process(process, grouped=not owned_worker_group)
                process.wait()
                return None, "history_limit"
        remaining = max(0.0, deadline - time.monotonic())
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _kill_process(process, grouped=not owned_worker_group)
            process.wait()
            return None, "history_timeout"
        if return_code != 0:
            return None, "history_source_failed"
        return bytes(output), None
    finally:
        selector.close()
        process.stdout.close()
        if process.poll() is None:
            _kill_process(process, grouped=not owned_worker_group)
            process.wait()


def collect_saved_history(
    config_home: Path,
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    owned_worker_group: bool = False,
) -> dict[str, object]:
    """Read bounded saved metadata without launching Claude or its daemon.

    Coverage remains explicitly partial because the SDK intentionally omits
    sidechains and transcripts without usable top-level metadata.
    """
    if (
        type(owned_worker_group) is not bool
        or not isinstance(config_home, Path)
        or not config_home.is_absolute()
        or len(str(config_home)) > 4096
        or any(unicodedata.category(char).startswith("C") for char in str(config_home))
        or type(history_limit) is not int
        or not 1 <= history_limit <= 1000
        or type(timeout) not in (int, float)
        or not 0.1 <= timeout <= MAX_TIMEOUT_SECONDS
    ):
        return _error("history_source_failed")

    try:
        resolved = config_home.resolve(strict=True)
    except OSError:
        return _error("history_source_failed")
    if resolved != config_home:
        return _error("history_unsafe_entry")

    output, failure = _run_worker(config_home, timeout=float(timeout), owned_worker_group=True) if owned_worker_group else _run_worker(config_home, timeout=float(timeout))
    if failure:
        return _error(failure)
    if output is None:
        return _error("history_source_failed")
    try:
        payload = json.loads(output.decode("utf-8", "strict"))
        rows, errors = _validate_payload(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, UnicodeEncodeError):
        return _error("history_source_failed")

    if errors and not rows:
        return _error(errors[0])
    rows.sort(
        key=lambda row: (
            row["activity"]["at"] is None,
            -(row["activity"]["at"] or 0),
            row["session_id"],
        )
    )
    display_limited = len(rows) > history_limit
    result_errors = [{"code": code} for code in errors]
    census = dict(payload.get("census", {}))
    census["displayed_ids"] = min(len(rows), history_limit)
    census["display_omitted_ids"] = max(0, len(rows) - history_limit)
    return {
        "rows": rows[:history_limit],
        "coverage": {
            "complete": False,
            "reason": "history_limit" if display_limited else "metadata_scan",
        },
        "errors": result_errors,
        "census": census,
    }
