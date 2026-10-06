"""Version-gated, read-only projection of Claude 2.1.287 private metadata.

This is a provisional spike source. It reads only bounded session-registry and
job-state JSON files. It never invokes Claude, its roster command, a socket, or
any provider action. The on-disk schema is private and is not a stable API.
"""

from __future__ import annotations

import calendar
import errno
import os
import re
import stat
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .bounded_json import WireError, decode_document
from .native_artifacts import CLAUDE, inspect_process
from .native_contracts import CLAUDE_READ, claude_registry_capabilities
from .observation_model import (
    Evidence,
    NativeIdentity,
    SessionObservation,
    bounded_native_title,
)

SUPPORTED_VERSION = CLAUDE.version
SUPPORTED_SHA256 = CLAUDE.sha256
SUPPORTED_BINARY_PATH = CLAUDE.path

_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_PID_NAME = re.compile(r"([1-9][0-9]{0,9})\.json\Z", re.ASCII)
_PID = re.compile(r"[1-9][0-9]{0,9}\Z", re.ASCII)
_PROC_START = re.compile(r"[0-9]{1,20}\Z", re.ASCII)
_JOB_ID = re.compile(r"[a-f0-9]{8}\Z", re.ASCII)
_SHA256 = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
_MACHINE_ID = re.compile(r"[a-fA-F0-9]{32}\Z", re.ASCII)
_PID_NAMESPACE = re.compile(r"pid:\[[0-9]{1,20}\]\Z", re.ASCII)
_ISO_UTC_MILLIS = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\Z",
    re.ASCII,
)

_SESSION_KINDS = frozenset({"interactive", "bg", "daemon", "daemon-worker"})
_SESSION_STATUSES = frozenset({"busy", "shell", "idle", "waiting"})
_JOB_STATES = frozenset({"working", "done", "failed", "stopped"})
_JOB_TEMPOS = frozenset({"active", "idle", "blocked"})
_WAIT_REASON_MAP = {
    "input needed": "user_input",
    "permission prompt": "approval",
    "worker request": "worker_request",
    "sandbox request": "sandbox_request",
    "dialog open": "user_input",
}

_MAX_REGISTRY_ROWS = 256
_MAX_REGISTRY_FILE_BYTES = 256 * 1024
_MAX_REGISTRY_TOTAL_BYTES = 4 * 1024 * 1024
_MAX_JOB_ROWS = 128
_MAX_JOB_FILE_BYTES = 8 * 1024 * 1024
_MAX_JOB_TOTAL_BYTES = 24 * 1024 * 1024
_MAX_DIRECTORY_ENTRIES = 4096
_MAX_ERRORS = 128
_MAX_TIME_MS = 4_000_000_000_000


@dataclass(frozen=True)
class _Job:
    job_id: str
    session_id: str | None
    state: str
    tempo: str
    terminal_at: int | None
    cwd: str | None = None
    issues: tuple[str, ...] = ()
    title: str | None = field(default=None, compare=False)
    in_flight: tuple[int, int, int] | None = None
    last_terminal_at: int | None = None
    question_wait: bool = False
    in_flight_invalid: bool = False


class _ReadFailure(Exception):
    """Content-free local failure code for a bounded filesystem read."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def linux_pid_domain(machine_id: str, pid_namespace: str) -> str | None:
    """Return Claude's Linux pidDomain formula after validating its inputs."""
    if not isinstance(machine_id, str) or not (
        machine_id == "" or _MACHINE_ID.fullmatch(machine_id)
    ):
        return None
    if not isinstance(pid_namespace, str) or not _PID_NAMESPACE.fullmatch(pid_namespace):
        return None
    return f"linux:{machine_id.strip()}:{pid_namespace}"


def _current_pid_domain() -> str | None:
    """Read the exact Linux namespace inputs used by the installed runtime."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        fd = os.open("/etc/machine-id", os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        try:
            raw = os.read(fd, 129)
        finally:
            os.close(fd)
        if len(raw) > 128:
            return None
        machine_id = raw.decode("ascii", "strict").strip()
    except OSError:
        # The installed formula explicitly substitutes an empty component.
        machine_id = ""
    except UnicodeError:
        return None
    try:
        pid_namespace = os.readlink("/proc/self/ns/pid")
    except OSError:
        return None
    return linux_pid_domain(machine_id, pid_namespace)


def _linux_proc_start_token(pid: int) -> tuple[str | None, str]:
    """Read Linux /proc starttime (stat field 22), without retaining proc data."""
    path = f"/proc/{pid}/stat"
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    except FileNotFoundError:
        return None, "absent"
    except OSError:
        return None, "unavailable"
    try:
        raw = os.read(fd, 8193)
        if len(raw) > 8192:
            return None, "malformed"
    except OSError:
        return None, "unavailable"
    finally:
        os.close(fd)
    try:
        text = raw.decode("ascii", "strict")
    except UnicodeError:
        return None, "malformed"
    closing_paren = text.rfind(")")
    if closing_paren < 0:
        return None, "malformed"
    fields_after_comm = text[closing_paren + 1 :].split()
    if len(fields_after_comm) <= 19:
        return None, "malformed"
    token = fields_after_comm[19]
    if not _PROC_START.fullmatch(token):
        return None, "malformed"
    return token, "present"


def _linux_process_uses_supported_binary(pid: int, cache=None) -> tuple[bool | None, str]:
    """Bind a supported image to this process, including upgrade survivors."""
    try:
        inspect_process(pid, "claude", cache=cache)
    except FileNotFoundError:
        return None, "process_unavailable"
    except OSError:
        return None, "unavailable"
    except ValueError:
        return False, "different_binary"
    return True, "matched"


def _phase_capabilities(record, presence, cache):
    """Match required registry semantics after verifying the same worker birth."""
    if presence.effective_value != "present":
        return []
    try:
        inspect_process(record["pid"], "claude", cache=cache)
        start, state = _linux_proc_start_token(record["pid"])
        if state != "present" or start != record["procStart"]:
            return []
        return claude_registry_capabilities(record)
    except (OSError, ValueError):
        return []


def _open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(name, flags, dir_fd=parent_fd)


def _directory_names(directory_fd: int) -> tuple[list[str], bool]:
    names: list[str] = []
    try:
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                if len(names) >= _MAX_DIRECTORY_ENTRIES:
                    return names, True
                names.append(entry.name)
    except OSError as exc:
        raise _ReadFailure("directory_unreadable") from exc
    return names, False


def _read_json_at(directory_fd: int, name: str, limit: int) -> tuple[Any, int]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise _ReadFailure("symlink_rejected") from exc
        raise _ReadFailure("file_unavailable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise _ReadFailure("not_regular_file")
        if before.st_size < 0 or before.st_size > limit:
            raise _ReadFailure("byte_limit")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        if (
            len(raw) > limit
            or len(raw) != before.st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
            or before.st_ino != after.st_ino
        ):
            raise _ReadFailure("torn_or_oversized_file")
    finally:
        os.close(fd)
    try:
        return (
            decode_document(raw, max_bytes=limit, max_depth=32, max_nodes=100000),
            len(raw),
        )
    except WireError as exc:
        raise _ReadFailure("invalid_json") from exc


def _uuid(value: object) -> str | None:
    return value.lower() if isinstance(value, str) and _UUID.fullmatch(value) else None


def _cwd(value: object) -> str | None:
    if (
        isinstance(value, str)
        and 0 < len(value) <= 4096
        and value.startswith("/")
        and not value.startswith("//")
        and not any(unicodedata.category(c).startswith("C") for c in value)
    ):
        return value
    return None


def _user_title(payload: dict[str, Any]) -> str | None:
    """Project only the installed writer's explicit user-assigned name."""
    value = payload.get("name")
    if payload.get("nameSource") != "user" or not isinstance(value, str):
        return None
    candidate = value[:1024]
    if not any(
        not char.isspace() and not unicodedata.category(char).startswith("C") for char in candidate
    ):
        return None
    return bounded_native_title(candidate, "Claude")


def _bounded_time(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _MAX_TIME_MS:
        return None
    return value


def _terminal_time(value: object) -> int | None:
    """Parse the installed writer's Date.toISOString() millisecond value."""
    if not isinstance(value, str) or not _ISO_UTC_MILLIS.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        millis = calendar.timegm(parsed.timetuple()) * 1000 + parsed.microsecond // 1000
    except (OverflowError, ValueError):
        return None
    return millis if 0 <= millis <= _MAX_TIME_MS else None


def _job_record(job_id: str, payload: object) -> _Job:
    if not isinstance(payload, dict):
        raise _ReadFailure("invalid_job_record")
    session_id = _uuid(payload.get("sessionId"))
    state_value = payload.get("state")
    state = (
        state_value if isinstance(state_value, str) and state_value in _JOB_STATES else "unknown"
    )
    tempo_value = payload.get("tempo")
    tempo = (
        tempo_value if isinstance(tempo_value, str) and tempo_value in _JOB_TEMPOS else "unknown"
    )
    terminal_at = None
    if state in {"done", "failed", "stopped"}:
        terminal_at = _terminal_time(payload.get("lastTerminalAt"))
        if terminal_at is None:
            terminal_at = _terminal_time(payload.get("firstTerminalAt"))
    issues = []
    if session_id is None:
        issues.append("job_session_id_unavailable")
    if state == "unknown":
        issues.append(
            "native_blocked_phase_unproved" if state_value == "blocked" else "unknown_job_state"
        )
    if tempo == "unknown":
        issues.append("unknown_job_tempo")
    if state in {"done", "failed", "stopped"} and terminal_at is None:
        issues.append("terminal_clock_unavailable")
    return _Job(
        job_id,
        session_id,
        state,
        tempo,
        terminal_at,
        _cwd(payload.get("cwd")),
        tuple(issues),
        _user_title(payload),
        _in_flight(payload.get("inFlight")),
        _terminal_time(payload.get("lastTerminalAt")),
        _question_wait(payload.get("block")),
        payload.get("inFlight") is not None and _in_flight(payload.get("inFlight")) is None,
    )


def _question_wait(value):
    if not isinstance(value, dict):
        return False
    questions = value.get("questions")
    return isinstance(questions, list) and 1 <= len(questions) <= 32 and all(isinstance(q, dict) for q in questions)


def _in_flight(value):
    if not isinstance(value, dict):
        return None
    counts = tuple(value.get(k) for k in ("tasks", "queued", "drainableMonitors"))
    return counts if all(type(n) is int and 0 <= n <= 100000 for n in counts) else None


def _session_record(filename: str, payload: object) -> dict[str, Any]:
    match = _PID_NAME.fullmatch(filename)
    if match is None:
        raise _ReadFailure("invalid_session_filename")
    filename_pid = int(match.group(1))
    if not 1 <= filename_pid <= 2**31 - 1:
        raise _ReadFailure("invalid_session_filename")
    if not isinstance(payload, dict):
        raise _ReadFailure("invalid_session_record")
    pid_value = payload.get("pid")
    session_id = _uuid(payload.get("sessionId"))
    proc_start = payload.get("procStart")
    pid_domain = payload.get("pidDomain")
    kind_value = payload.get("kind")
    status_value = payload.get("status")
    job_id_value = payload.get("jobId")
    issues: list[str] = []
    if isinstance(pid_value, bool) or pid_value != filename_pid or not isinstance(pid_value, int):
        raise _ReadFailure("session_pid_mismatch")
    if session_id is None:
        raise _ReadFailure("invalid_session_identity")
    if not isinstance(proc_start, str) or not _PROC_START.fullmatch(proc_start):
        proc_start = None
        issues.append("worker_start_identity_unavailable")
    if not isinstance(pid_domain, str) or len(pid_domain) > 512:
        pid_domain = None
        issues.append("worker_pid_domain_unavailable")
    kind = kind_value if isinstance(kind_value, str) and kind_value in _SESSION_KINDS else "unknown"
    status = (
        status_value
        if isinstance(status_value, str) and status_value in _SESSION_STATUSES
        else "unknown"
    )
    job_id = (
        job_id_value if isinstance(job_id_value, str) and _JOB_ID.fullmatch(job_id_value) else None
    )
    if job_id_value is not None and job_id is None:
        issues.append("invalid_job_reference")
    status_updated_at = _bounded_time(payload.get("statusUpdatedAt"))
    if status != "unknown" and status_updated_at is None:
        issues.append("status_clock_unavailable")
    wait_reason = _wait_reason(payload.get("waitingFor")) if status == "waiting" else "unknown"
    if status == "unknown":
        issues.append("unknown_session_status")
    if kind == "unknown":
        issues.append("unknown_session_kind")
    return {
        "pid": filename_pid,
        "sessionId": session_id,
        "procStart": proc_start,
        "pidDomain": pid_domain,
        "kind": kind,
        "status": status,
        "statusUpdatedAt": status_updated_at,
        "jobId": job_id,
        "waitReason": wait_reason,
        "questionWait": status == "waiting" and payload.get("waitingFor") == "input needed",
        "cwd": _cwd(payload.get("cwd")),
        "title": _user_title(payload),
        "issues": tuple(issues),
    }


def _presence(record: dict[str, Any], pid_domain: str | None, observed_at: int, image_cache=None) -> Evidence:
    if pid_domain is None:
        return Evidence("presence", health="unavailable", reason="source_unavailable")
    if record["pidDomain"] != pid_domain:
        return Evidence("presence", health="ambiguous", reason="identity_ambiguous")
    if record["procStart"] is None:
        return Evidence("presence", health="ambiguous", reason="identity_ambiguous")
    current_start, process_state = _linux_proc_start_token(record["pid"])
    if process_state == "absent":
        return Evidence(
            "presence",
            "absent",
            observed_at,
            "claude_registry",
            "current",
            "native_snapshot",
        )
    if process_state != "present" or current_start is None:
        return Evidence("presence", health="unavailable", reason="source_unavailable")
    if current_start != record["procStart"]:
        return Evidence(
            "presence",
            "absent",
            observed_at,
            "claude_registry",
            "current",
            "native_snapshot",
        )
    image_matches, image_state = _linux_process_uses_supported_binary(record["pid"], image_cache)
    if image_state == "process_unavailable":
        return Evidence(
            "presence",
            "absent",
            observed_at,
            "claude_registry",
            "current",
            "native_snapshot",
        )
    if image_matches is None:
        return Evidence("presence", health="unavailable", reason="source_unavailable")
    # Bind the executable check to the same process instance. The PID could
    # exit and be reused after the first /proc stat read but before /proc/PID/exe.
    final_start, final_state = _linux_proc_start_token(record["pid"])
    if final_state == "absent":
        return Evidence(
            "presence",
            "absent",
            observed_at,
            "claude_registry",
            "current",
            "native_snapshot",
        )
    if final_state != "present" or final_start is None:
        return Evidence("presence", health="unavailable", reason="source_unavailable")
    if final_start != record["procStart"]:
        return Evidence(
            "presence",
            "absent",
            observed_at,
            "claude_registry",
            "current",
            "native_snapshot",
        )
    if not image_matches:
        # An extant birth with a different image can be an older upgraded
        # runtime or an exec transition. Unsupported image is not worker exit.
        return Evidence("presence", health="unsupported", reason="unsupported")
    return Evidence(
        "presence",
        "present",
        observed_at,
        "claude_registry",
        "current",
        "native_snapshot",
    )


def _wait_reason(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    exact = _WAIT_REASON_MAP.get(value)
    if exact is not None:
        return exact
    if value.startswith("dialog:"):
        return "user_input"
    return "unknown"


def _status_work(
    record: dict[str, Any], *, job: _Job | None, presence: Evidence
) -> tuple[Evidence, str]:
    status = record["status"]
    clock = record["statusUpdatedAt"]
    if status not in _SESSION_STATUSES or clock is None:
        return Evidence("work"), "unknown"
    if presence.effective_value != "present":
        return Evidence("work"), "unknown"
    if "invalid_job_reference" in record["issues"]:
        return Evidence("work", health="ambiguous", reason="identity_ambiguous"), "unknown"
    if job is not None:
        if job.state == "unknown" or job.tempo == "unknown":
            return Evidence("work", health="unsupported", reason="unsupported"), "unknown"
        if job.state in {"done", "failed", "stopped"}:
            return Evidence("work", health="ambiguous", reason="native_state_conflict"), "unknown"
        if status == "idle":
            # Native background roster idle is activity/status, not job completion.
            return Evidence("work"), "unknown"
        if job.state == "working":
            if status == "waiting" and job.tempo in {"active", "blocked"}:
                return (
                    Evidence(
                        "work",
                        "needs_input",
                        clock,
                        "claude_registry",
                        "current",
                        "native_snapshot",
                    ),
                    "needs_input",
                )
            if status in {"busy", "shell"} and job.tempo == "active":
                return (
                    Evidence(
                        "work",
                        "working",
                        clock,
                        "claude_registry",
                        "current",
                        "native_snapshot",
                    ),
                    "working",
                )
            return Evidence("work", health="ambiguous", reason="native_state_conflict"), "unknown"
        return Evidence("work", health="unsupported", reason="unsupported"), "unknown"
    elif record["jobId"] is not None or record["kind"] != "interactive":
        return Evidence("work", health="unsupported", reason="unsupported"), "unknown"
    if status in {"busy", "shell"}:
        value = "working"
    elif status == "waiting":
        value = "needs_input"
    else:
        value = "settled"
    work = Evidence("work", value, clock, "claude_registry", "current", "native_snapshot")
    return work, value


def _job_work(job: _Job, *, conflicted: bool) -> Evidence:
    if conflicted:
        return Evidence("work", health="ambiguous", reason="identity_ambiguous")
    if job.state == "unknown" or job.tempo == "unknown":
        return Evidence("work", health="unsupported", reason="unsupported")
    if job.state in {"done", "failed", "stopped"}:
        if job.tempo == "active":
            return Evidence("work", health="ambiguous", reason="identity_ambiguous")
        if job.terminal_at is None:
            return Evidence("work", health="unavailable", reason="unobserved")
        value = {"done": "settled", "failed": "error", "stopped": "interrupted"}[job.state]
        return Evidence(
            "work",
            value,
            job.terminal_at,
            "claude_job_store",
            "current",
            "native_snapshot",
        )
    return Evidence("work")


def _observation(
    *,
    session_id: str,
    host_scope: str,
    namespace: str,
    registry: dict[str, Any] | None,
    job: _Job | None,
    pid_domain: str | None,
    observed_at: int,
    job_store_complete: bool,
    conflicted: bool = False,
    issues: tuple[str, ...] = (),
    image_cache=None,
) -> dict[str, Any]:
    identity = NativeIdentity(host_scope, "claude", namespace, "session", session_id)
    attachment = Evidence("attachment", health="unsupported", reason="unsupported")
    metadata_issues = list(issues)
    phase_capabilities = []
    if job is not None:
        metadata_issues.extend(job.issues)
    if registry is not None:
        metadata_issues.extend(registry["issues"])

    if registry is None:
        presence = Evidence("presence")
        work = _job_work(job, conflicted=conflicted) if job is not None else Evidence("work")
        native_status = {"value": "unknown", "observedAt": None}
        session_kind = "unknown"
        linked_job_id = job.job_id if job is not None else None
    else:
        presence = _presence(registry, pid_domain, observed_at, image_cache)
        phase_capabilities = _phase_capabilities(registry, presence, image_cache)
        session_kind = registry["kind"]
        native_status = {
            "value": registry["status"],
            "observedAt": registry["statusUpdatedAt"],
        }
        linked_job_id = registry["jobId"]
        if conflicted:
            work = Evidence("work", health="ambiguous", reason="identity_ambiguous")
        elif job is not None and job.job_id != linked_job_id:
            work = Evidence("work", health="ambiguous", reason="identity_ambiguous")
            metadata_issues.append("job_session_conflict")
        elif "registry_phase" in phase_capabilities and registry["statusUpdatedAt"] is not None and (
            job is None and linked_job_id is None and registry["kind"] == "interactive"
            or job is not None and job.state in {"working", "done"}
        ):
            # Current-image registry activity overrides an older retained turn.
            # Idle alone cannot settle queued or background work.
            status = registry["status"]
            if status in {"busy", "shell", "waiting"}:
                work = Evidence("work", "needs_input" if status == "waiting" else "working",
                                registry["statusUpdatedAt"], "claude_registry", "current", "native_snapshot")
            elif job is None and "interactive_readiness" in phase_capabilities:
                work = Evidence("work", "settled", registry["statusUpdatedAt"],
                                "claude_registry", "current", "native_snapshot")
            elif (job is not None and job.state == "done" and job.tempo == "idle"
                  and job.in_flight == (0, 0, 0) and job.last_terminal_at is not None):
                work = Evidence("work", "settled", job.last_terminal_at,
                                "claude_job_store", "current", "native_snapshot")
            elif job is not None and job.in_flight is not None and any(job.in_flight):
                work = Evidence("work", health="unsupported", reason="native_pending_work")
            else:
                work = Evidence("work", health="unsupported", reason="native_readiness_unproved")
        elif job is not None and job.state in {"done", "failed", "stopped"}:
            if (
                registry["status"] in {"busy", "shell", "waiting"}
                and job.terminal_at is not None
                and registry["statusUpdatedAt"] is not None
                and registry["statusUpdatedAt"] > job.terminal_at
            ):
                work = Evidence("work", health="ambiguous", reason="identity_ambiguous")
                metadata_issues.append("status_after_terminal_clock")
            else:
                work = _job_work(job, conflicted=False)
        else:
            work, _ = _status_work(registry, job=job, presence=presence)

    if linked_job_id is None:
        retained: bool | None = False if job_store_complete else None
    else:
        retained = job is not None and job.job_id == linked_job_id
        if not retained and not job_store_complete:
            retained = None
    wait_reason = registry["waitReason"] if registry is not None else "unknown"
    if (registry is not None and registry.get("questionWait")
            and job is not None and job.state == "working" and job.tempo == "blocked"
            and job.question_wait and "job_question" in phase_capabilities):
        wait_reason = "question"
    title = registry["title"] if registry is not None else None
    if (
        title is None
        and job is not None
        and job.session_id == session_id
        and job.job_id == linked_job_id
        and not conflicted
    ):
        title = job.title
    item = SessionObservation(identity, work, presence, attachment).metadata()
    item.update(
        {
            "nativeIds": {"sessionId": session_id, "jobId": linked_job_id},
            "title": bounded_native_title(title, "Claude " + session_id),
            "sessionKind": session_kind,
            "nativeStatus": native_status,
            "job": {
                "id": linked_job_id,
                "retained": retained,
                "state": job.state
                if job is not None and job.job_id == linked_job_id
                else "unknown",
                "tempo": job.tempo
                if job is not None and job.job_id == linked_job_id
                else "unknown",
                "terminalObservedAt": (
                    job.terminal_at if job is not None and job.job_id == linked_job_id else None
                ),
            },
            "waitReason": wait_reason,
            "cwd": registry["cwd"]
            if registry is not None
            else job.cwd
            if job is not None
            else None,
            "cwdSource": "claude_registry"
            if registry is not None and registry["cwd"] is not None
            else "claude_job_store"
            if registry is None and job is not None and job.cwd is not None
            else None,
            "metadataIssues": list(dict.fromkeys(metadata_issues)),
            "phaseCapabilities": phase_capabilities,
        }
    )
    return item


def _error(errors: list[dict[str, str]], code: str, *, job_id: str | None = None) -> None:
    if len(errors) >= _MAX_ERRORS:
        return
    item = {"code": code}
    if job_id is not None and _JOB_ID.fullmatch(job_id):
        item["jobId"] = job_id
    errors.append(item)


def snapshot(
    config_root: str | os.PathLike[str],
    *,
    host_scope: str,
    namespace: str,
    runtime_version: str,
    binary_sha256: str | None,
) -> dict[str, Any]:
    """Read an allowlisted Claude metadata snapshot from an explicit config root.

    No environment variable or default home is consulted. The caller must pass
    the exact disposable or otherwise authorized config root to inspect.
    """
    result: dict[str, Any] = {
        "source": "claude_private_metadata",
        "schema": CLAUDE_READ.name,
        "supported": False,
        "runtime": {"version": "unknown", "sha256": "unknown"},
        "coverage": {
            "sessionRegistry": "unavailable",
            "jobStore": "unavailable",
            "workerPresence": "unavailable",
            "attachment": "unsupported",
        },
        "errors": [],
        "observations": [],
        "limitations": [
            "private_required_contract",
            "direct_metadata_reads_only",
            "attachment_not_observed",
            "hooks_and_current_client_not_observed",
            "job_roster_state_is_not_a_liveness_clock",
        ],
    }
    errors: list[dict[str, str]] = result["errors"]
    if not isinstance(runtime_version, str) or not 0 < len(runtime_version) <= 64:
        _error(errors, "invalid_runtime_version_metadata")
        return result
    if binary_sha256 is not None and (not isinstance(binary_sha256, str) or not _SHA256.fullmatch(binary_sha256)):
        _error(errors, "invalid_runtime_digest")
        return result
    if not sys.platform.startswith("linux"):
        _error(errors, "unsupported_platform")
        result["coverage"]["sessionRegistry"] = "unsupported"
        result["coverage"]["jobStore"] = "unsupported"
        return result
    # Exercise the identity constructor before filesystem access so invalid
    # caller scope cannot produce partial provider reads.
    try:
        NativeIdentity(
            host_scope,
            "claude",
            namespace,
            "session",
            "00000000-0000-0000-0000-000000000000",
        )
        root_path = os.fspath(config_root)
        if not isinstance(root_path, str) or not root_path:
            raise ValueError("invalid_config_root")
    except (TypeError, ValueError):
        _error(errors, "invalid_source_scope")
        return result

    try:
        root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        root_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        root_fd = os.open(root_path, root_flags)
    except OSError:
        _error(errors, "config_root_unavailable")
        return result

    pid_domain = _current_pid_domain()
    observed_at = time.time_ns() // 1_000_000
    jobs: dict[str, _Job] = {}
    registry_rows: list[dict[str, Any]] = []
    unstable_job_ids: set[str] = set()
    session_complete = False
    job_complete = False
    sessions_fd = None
    jobs_fd = None
    directory_ids = {"root": (os.fstat(root_fd).st_dev, os.fstat(root_fd).st_ino)}
    try:
        try:
            sessions_fd = _open_directory_at(root_fd, "sessions")
            info = os.fstat(sessions_fd)
            directory_ids["sessions"] = (info.st_dev, info.st_ino)
        except OSError:
            _error(errors, "sessions_unavailable")
        try:
            jobs_fd = _open_directory_at(root_fd, "jobs")
            info = os.fstat(jobs_fd)
            directory_ids["jobs"] = (info.st_dev, info.st_ino)
        except OSError:
            _error(errors, "jobs_unavailable")

        if jobs_fd is not None:
            try:
                names, overflow = _directory_names(jobs_fd)
                if overflow:
                    _error(errors, "job_directory_limit")
                    result["coverage"]["jobStore"] = "partial"
                elif len(names) > _MAX_JOB_ROWS:
                    _error(errors, "job_row_limit")
                    result["coverage"]["jobStore"] = "partial"
                else:
                    total = 0
                    job_issue = False
                    for name in sorted(names):
                        if not _JOB_ID.fullmatch(name):
                            continue
                        try:
                            job_dir_fd = _open_directory_at(jobs_fd, name)
                        except OSError:
                            _error(errors, "job_directory_unavailable", job_id=name)
                            job_issue = True
                            continue
                        try:
                            payload, size = _read_json_at(
                                job_dir_fd, "state.json", _MAX_JOB_FILE_BYTES
                            )
                        except _ReadFailure as exc:
                            _error(errors, exc.code, job_id=name)
                            job_issue = True
                            continue
                        finally:
                            os.close(job_dir_fd)
                        total += size
                        if total > _MAX_JOB_TOTAL_BYTES:
                            _error(errors, "job_total_byte_limit")
                            job_issue = True
                            break
                        try:
                            job = _job_record(name, payload)
                        except _ReadFailure as exc:
                            _error(errors, exc.code, job_id=name)
                            job_issue = True
                            continue
                        jobs[name] = job
                        if job.issues:
                            job_issue = True
                            for issue in job.issues:
                                _error(errors, issue, job_id=name)
                    job_complete = not overflow and len(names) <= _MAX_JOB_ROWS and not job_issue
                    result["coverage"]["jobStore"] = "complete" if job_complete else "partial"
            except _ReadFailure as exc:
                _error(errors, exc.code)
                result["coverage"]["jobStore"] = "partial"

        if sessions_fd is not None:
            try:
                names, overflow = _directory_names(sessions_fd)
                candidates = sorted(name for name in names if _PID_NAME.fullmatch(name))
                registry_issue = overflow or len(candidates) > _MAX_REGISTRY_ROWS
                if overflow:
                    _error(errors, "session_directory_limit")
                if len(candidates) > _MAX_REGISTRY_ROWS:
                    _error(errors, "session_row_limit")
                    candidates = candidates[:_MAX_REGISTRY_ROWS]
                total = 0
                for name in candidates:
                    try:
                        payload, size = _read_json_at(sessions_fd, name, _MAX_REGISTRY_FILE_BYTES)
                    except _ReadFailure as exc:
                        _error(errors, exc.code)
                        registry_issue = True
                        continue
                    total += size
                    if total > _MAX_REGISTRY_TOTAL_BYTES:
                        _error(errors, "session_total_byte_limit")
                        registry_issue = True
                        break
                    try:
                        record = _session_record(name, payload)
                    except _ReadFailure as exc:
                        _error(errors, exc.code)
                        registry_issue = True
                        continue
                    registry_rows.append(record)
                session_complete = not registry_issue
                result["coverage"]["sessionRegistry"] = (
                    "complete" if session_complete else "partial"
                )
            except _ReadFailure as exc:
                _error(errors, exc.code)
                result["coverage"]["sessionRegistry"] = "partial"

        # Recheck only fields that contribute to identity or projected state.
        # Names can refresh without invalidating stable identity/work facts.
        # Native updatedAt/detail/environment are not work clocks.
        if sessions_fd is not None:
            stable_rows: list[dict[str, Any]] = []
            for record in registry_rows:
                filename = f"{record['pid']}.json"
                try:
                    payload, _size = _read_json_at(sessions_fd, filename, _MAX_REGISTRY_FILE_BYTES)
                    current_record = _session_record(filename, payload)
                except _ReadFailure:
                    session_complete = False
                    _error(errors, "metadata_changed_during_snapshot")
                    continue
                if {key: value for key, value in current_record.items() if key != "title"} != {
                    key: value for key, value in record.items() if key != "title"
                }:
                    session_complete = False
                    _error(errors, "metadata_changed_during_snapshot")
                    continue
                stable_rows.append(current_record)
            registry_rows = stable_rows
        if jobs_fd is not None:
            for job_id in tuple(jobs):
                try:
                    job_dir_fd = _open_directory_at(jobs_fd, job_id)
                except OSError:
                    unstable_job_ids.add(job_id)
                    continue
                try:
                    payload, _size = _read_json_at(job_dir_fd, "state.json", _MAX_JOB_FILE_BYTES)
                    current_job = _job_record(job_id, payload)
                except _ReadFailure:
                    unstable_job_ids.add(job_id)
                    current_job = None
                finally:
                    os.close(job_dir_fd)
                if current_job != jobs.get(job_id):
                    unstable_job_ids.add(job_id)
                elif current_job is not None:
                    # Title is presentation metadata, excluded from _Job equality.
                    jobs[job_id] = current_job
            for job_id in unstable_job_ids:
                jobs.pop(job_id, None)
                job_complete = False
                _error(errors, "metadata_changed_during_snapshot", job_id=job_id)
    finally:
        if sessions_fd is not None:
            os.close(sessions_fd)
        if jobs_fd is not None:
            os.close(jobs_fd)
        os.close(root_fd)

    # Exact jobId/sessionId links only. Cwd, title, and PID are never join keys.
    registry_by_job: dict[str, set[str]] = {}
    pair_counts: dict[tuple[str, str | None], int] = {}
    for record in registry_rows:
        pair = (record["sessionId"], record["jobId"])
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        if record["jobId"] is not None:
            registry_by_job.setdefault(record["jobId"], set()).add(record["sessionId"])
    duplicate_pairs = {pair for pair, count in pair_counts.items() if count > 1}
    duplicate_jobs = {job_id for _session_id, job_id in duplicate_pairs if job_id is not None}
    conflicted_jobs = {
        job_id
        for job_id, session_ids in registry_by_job.items()
        if len(session_ids) > 1 or (job_id in jobs and jobs[job_id].session_id not in session_ids)
    }
    conflicted_jobs.update(duplicate_jobs)

    observations: list[dict[str, Any]] = []
    image_cache = {}
    paired_jobs: set[str] = set()
    for record in registry_rows:
        job_id = record["jobId"]
        job = jobs.get(job_id) if job_id is not None else None
        pair = (record["sessionId"], job_id)
        duplicate_pair = pair in duplicate_pairs
        conflicted = (job_id in conflicted_jobs if job_id is not None else False) or duplicate_pair
        row_issues = list(record["issues"])
        if job_id is not None and job_id in conflicted_jobs:
            row_issues.append("job_session_conflict")
        if duplicate_pair:
            row_issues.append("duplicate_session_job_pair")
            _error(errors, "duplicate_session_job_pair", job_id=job_id)
        if job_id in unstable_job_ids:
            row_issues.append("metadata_changed_during_snapshot")
        if job is not None and job.session_id == record["sessionId"]:
            paired_jobs.add(job_id)
        observations.append(
            _observation(
                session_id=record["sessionId"],
                host_scope=host_scope,
                namespace=namespace,
                registry=record,
                job=job,
                pid_domain=pid_domain,
                observed_at=observed_at,
                job_store_complete=job_complete,
                conflicted=conflicted,
                issues=tuple(row_issues),
                image_cache=image_cache,
            )
        )

    for job_id, job in sorted(jobs.items()):
        if job_id in paired_jobs:
            continue
        conflict = job_id in conflicted_jobs
        if conflict:
            _error(errors, "job_session_conflict", job_id=job_id)
        if job.session_id is None:
            continue
        observations.append(
            _observation(
                session_id=job.session_id,
                host_scope=host_scope,
                namespace=namespace,
                registry=None,
                job=job,
                pid_domain=pid_domain,
                observed_at=observed_at,
                job_store_complete=job_complete,
                conflicted=conflict,
                issues=("job_session_conflict",) if conflict else (),
            )
        )

    parked_supported = bool(jobs) and session_complete and job_complete and pid_domain is not None
    if parked_supported and session_complete and job_complete and pid_domain is not None:
        try:
            _parked_runtimes(root_path, directory_ids, registry_rows, jobs, observations,
                             pid_domain, image_cache)
        except (OSError, _ReadFailure):
            _error(errors, "parked_runtime_recheck_unavailable")
    result["parkedSupported"] = parked_supported
    result["supported"] = True
    result["runtime"] = {"version": runtime_version, "sha256": binary_sha256}
    result["observations"] = observations
    result["coverage"]["sessionRegistry"] = (
        "complete" if session_complete else "partial" if sessions_fd is not None else "unavailable"
    )
    result["coverage"]["jobStore"] = (
        "complete" if job_complete else "partial" if jobs_fd is not None else "unavailable"
    )
    result["coverage"]["workerPresence"] = (
        "unsupported"
        if pid_domain is None
        else "complete"
        if all(item["presence"]["health"] in {"current", "stale"} for item in observations)
        else "partial"
    )
    if not session_complete or not job_complete or errors:
        result["limitations"].append("one_or_more_metadata_reads_incomplete")
    if pid_domain is None:
        result["limitations"].append("linux_pid_domain_unavailable")
    return result


def _parked_runtimes(root_path, directory_ids, registry_rows, jobs, observations,
                     pid_domain, image_cache):
    """Prove terminal job inactivity within the complete registered-worker scope.

    Worker absence alone is insufficient. Require one exact-UUID terminal job,
    no conflicting/unsupported context, and stable inventory/identity after all
    process checks. Working changes in unrelated sessions do not renew old clocks
    or invalidate this session's negative runtime evidence.
    """
    by_session = {}
    for row in observations:
        by_session.setdefault(row["identity"]["nativeId"], []).append(row)
    job_counts = {}
    for job in jobs.values():
        job_counts[job.session_id] = job_counts.get(job.session_id, 0) + 1
    candidates = {}
    now = time.time_ns() // 1_000_000
    for job in jobs.values():
        rows = by_session.get(job.session_id, [])
        if (job.state not in {"stopped", "done"} or job.tempo != "idle" or job.issues
                or job.terminal_at is None or job.terminal_at > now
                or job.in_flight_invalid or job.in_flight is not None and any(job.in_flight)
                or job_counts[job.session_id] != 1 or len(rows) != 1):
            continue
        row = rows[0]
        if row["metadataIssues"] or row["job"]["retained"] is not True:
            continue
        matching = [r for r in registry_rows if r["sessionId"] == job.session_id]
        if any(_presence(r, pid_domain, now, image_cache).effective_value != "absent"
               for r in matching):
            continue
        candidates[job.job_id] = row
    if not candidates:
        return

    descriptors = {}
    try:
        descriptors["root"] = os.open(root_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for name in ("sessions", "jobs"):
            descriptors[name] = _open_directory_at(descriptors["root"], name)
        for name, fd in descriptors.items():
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) != directory_ids[name]:
                raise _ReadFailure("directory_changed")
        expected_names = {
            "sessions": sorted(f"{r['pid']}.json" for r in registry_rows),
            "jobs": sorted(jobs),
        }

        def check_names():
            for name, pattern in (("sessions", _PID_NAME), ("jobs", _JOB_ID)):
                names, overflow = _directory_names(descriptors[name])
                if overflow or sorted(n for n in names if pattern.fullmatch(n)) != expected_names[name]:
                    raise _ReadFailure("inventory_changed")

        check_names()
        identity_fields = ("pid", "sessionId", "procStart", "pidDomain", "jobId", "kind")
        for original in registry_rows:
            filename = f"{original['pid']}.json"
            payload, _size = _read_json_at(descriptors["sessions"], filename, _MAX_REGISTRY_FILE_BYTES)
            current = _session_record(filename, payload)
            if any(current[k] != original[k] for k in identity_fields):
                raise _ReadFailure("registry_identity_changed")
            if current["sessionId"] in {jobs[k].session_id for k in candidates}:
                if current["issues"] or _presence(current, pid_domain, now, image_cache).effective_value != "absent":
                    raise _ReadFailure("worker_changed")
        for job_id, original in jobs.items():
            fd = _open_directory_at(descriptors["jobs"], job_id)
            try:
                payload, _size = _read_json_at(fd, "state.json", _MAX_JOB_FILE_BYTES)
                current = _job_record(job_id, payload)
            finally:
                os.close(fd)
            if current.session_id != original.session_id or job_id in candidates and current != original:
                raise _ReadFailure("job_changed")
        check_names()
        current_root = os.stat(root_path, follow_symlinks=False)
        if (current_root.st_dev, current_root.st_ino) != directory_ids["root"]:
            raise _ReadFailure("directory_changed")
        for name in ("sessions", "jobs"):
            info = os.stat(name, dir_fd=descriptors["root"], follow_symlinks=False)
            if (info.st_dev, info.st_ino) != directory_ids[name]:
                raise _ReadFailure("directory_changed")
    finally:
        for fd in descriptors.values():
            os.close(fd)
    observed_at = time.time_ns() // 1_000_000
    for row in candidates.values():
        row["runtimeDisposition"] = {
            "value": "parked", "observedAt": observed_at, "source": "claude_job_store",
            "health": "current", "reason": "native_snapshot",
        }
        row["presence"] = Evidence("presence", "absent", observed_at, "claude_registry",
                                   "current", "native_snapshot").metadata()
        row["sessionKind"] = "bg"


__all__ = ["SUPPORTED_SHA256", "SUPPORTED_VERSION", "linux_pid_domain", "snapshot"]
