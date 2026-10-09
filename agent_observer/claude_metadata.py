"""Passive interactive registrations and scoped lifecycle; no provider actions.

Native job metadata is a negative conflict guard only. Private required
contracts select support; executable versions/hashes are diagnostic identity.
"""

from __future__ import annotations

import errno
import os
import re
import stat
import sys
import time
import unicodedata
from typing import Any

from .bounded_json import WireError, decode_document
from .native_artifacts import inspect_process
from .native_contracts import CLAUDE_READ, claude_registry_capabilities
from .observation_model import (
    Evidence,
    NativeIdentity,
    SessionObservation,
    bounded_native_title,
)

_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_PID_NAME = re.compile(r"([1-9][0-9]{0,9})\.json\Z", re.ASCII)
_PROC_START = re.compile(r"[0-9]{1,20}\Z", re.ASCII)
_JOB_ID = re.compile(r"[a-f0-9]{8}\Z", re.ASCII)
_SHA256 = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
_MACHINE_ID = re.compile(r"[a-fA-F0-9]{32}\Z", re.ASCII)
_PID_NAMESPACE = re.compile(r"pid:\[[0-9]{1,20}\]\Z", re.ASCII)
_SESSION_KINDS = frozenset({"interactive", "bg", "daemon", "daemon-worker"})
_SESSION_STATUSES = frozenset({"busy", "shell", "idle", "waiting"})
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
_MAX_JOB_FILE_BYTES = 4 * 1024 * 1024
_MAX_JOB_TOTAL_BYTES = 24 * 1024 * 1024
_MAX_DIRECTORY_ENTRIES = 4096
_MAX_ERRORS = 128
_MAX_TIME_MS = 4_000_000_000_000


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
    return token, "absent" if fields_after_comm[0] in {"Z", "X"} else "present"


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


def _open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, dir_fd=parent_fd)
    if os.fstat(fd).st_uid != os.geteuid():
        os.close(fd)
        raise OSError("directory_ownership_mismatch")
    return fd


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
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid():
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
            or (before.st_dev, before.st_ino) != (lambda v: (v.st_dev, v.st_ino))(os.stat(name, dir_fd=directory_fd, follow_symlinks=False))
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
        and ".." not in value.split("/")
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
    image_matches, _ = _linux_process_uses_supported_binary(record["pid"], image_cache)
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
        return Evidence("presence", health="unavailable" if image_matches is None else "unsupported",
                        reason="source_unavailable" if image_matches is None else "unsupported")
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



def _status_work(record, presence, observed_at):
    clock = record["statusUpdatedAt"]
    if presence.effective_value != "present":
        return Evidence("work"), "unknown"
    if clock is None or clock > observed_at:
        return Evidence("work", health="unsupported", reason="unsupported"), "unknown"
    status, wait = record["status"], "unknown"
    if status in {"busy", "shell"}:
        value = "working"
    elif status == "idle":
        value = "settled"
    elif status == "waiting" and (record["waitReason"] == "approval" or record["questionWait"]):
        value = "needs_input"
        wait = "question" if record["questionWait"] else "approval"
    else:
        return Evidence("work", health="unsupported", reason="unsupported"), "unknown"
    return Evidence("work", value, clock, "claude_registry", "current", "native_snapshot"), wait


def _stamp(info):
    return info.st_dev, info.st_ino


def _error(errors, code):
    item = {"code": code}
    if len(errors) < _MAX_ERRORS and item not in errors:
        errors.append(item)


def _background_guard(root_fd):
    """UUID conflicts and a final bracket check, never job observations."""
    try:
        fd = _open_directory_at(root_fd, "jobs")
    except FileNotFoundError:
        def unchanged():
            try:
                os.stat("jobs", dir_fd=root_fd, follow_symlinks=False)
            except FileNotFoundError:
                return True
            return False
        return set(), unchanged, []
    conflicts, records, job_fds = set(), [], []
    try:
        stamp = _stamp(os.fstat(fd))
        names, capped = _directory_names(fd)
        ids = sorted(name for name in names if _JOB_ID.fullmatch(name))
        if capped or len(ids) > _MAX_JOB_ROWS:
            raise _ReadFailure("background_guard_limit")
        total = 0
        for jid in ids:
            job_fd = _open_directory_at(fd, jid)
            job_fds.append(job_fd)
            job, size = _read_json_at(job_fd, "state.json", _MAX_JOB_FILE_BYTES)
            total += size
            if total > _MAX_JOB_TOTAL_BYTES:
                raise _ReadFailure("background_guard_byte_limit")
            if not isinstance(job, dict) or _uuid(job.get("sessionId")) is None:
                raise _ReadFailure("background_guard_identity_unavailable")
            fields = {key: job.get(key) for key in ("sessionId", "state", "tempo", "inFlight")}
            counts = fields["inFlight"]
            quiet = (fields["state"] in {"done", "failed", "stopped"} and fields["tempo"] == "idle"
                     and isinstance(counts, dict) and all(type(counts.get(k)) is int and counts[k] == 0
                                                         for k in ("tasks", "queued", "drainableMonitors")))
            if not quiet:
                conflicts.add(_uuid(fields["sessionId"]))
            records.append((jid, job_fd, _stamp(os.fstat(job_fd)), fields))

        def unchanged():
            later, capped = _directory_names(fd)
            if capped or sorted(later) != sorted(names) or _stamp(os.stat("jobs", dir_fd=root_fd, follow_symlinks=False)) != stamp:
                return False
            for jid, job_fd, job_stamp, fields in records:
                job, _ = _read_json_at(job_fd, "state.json", _MAX_JOB_FILE_BYTES)
                if (not isinstance(job, dict) or any(job.get(k) != v for k, v in fields.items())
                        or _stamp(os.stat(jid, dir_fd=fd, follow_symlinks=False)) != job_stamp):
                    return False
            return True
        return conflicts, unchanged, [fd, *job_fds]
    except BaseException:
        for opened in [fd, *job_fds]:
            os.close(opened)
        raise


def snapshot(config_root, *, host_scope, namespace, runtime_version, binary_sha256,
             image_cache=None, saved_session_ids=()):
    """Bracket provider-native registrations; project one interactive UUID row."""
    result = {
        "source": "claude_private_metadata", "schema": CLAUDE_READ.name, "supported": False,
        "runtime": {"version": runtime_version, "sha256": binary_sha256},
        "coverage": {"sessionRegistry": "unavailable", "backgroundGuard": "unavailable", "workerPresence": "unavailable"},
        "errors": [], "observations": [], "parkedSupported": False,
        "limitations": ["private_required_contract", "interactive_runtime_only", "native_registration_assumed",
                        "unregistered_interactive_runtime_unproved", "background_runtime_unsupported"],
    }
    errors = result["errors"]
    try:
        NativeIdentity(host_scope, "claude", namespace, "session", "00000000-0000-0000-0000-000000000000")
        root_path = os.fspath(config_root)
        if not isinstance(root_path, str) or not os.path.isabs(root_path):
            raise ValueError("invalid_source_scope")
        if not isinstance(runtime_version, str) or not 0 < len(runtime_version) <= 64:
            raise ValueError("invalid_runtime_version_metadata")
        if binary_sha256 is not None and (not isinstance(binary_sha256, str) or not _SHA256.fullmatch(binary_sha256)):
            raise ValueError("invalid_runtime_digest")
        if not isinstance(saved_session_ids, (set, frozenset, tuple, list)) or len(saved_session_ids) > 4096:
            raise ValueError("invalid_saved_identity_sample")
        saved = {_uuid(sid) for sid in saved_session_ids}
        if None in saved:
            raise ValueError("invalid_saved_identity_sample")
    except (ValueError, TypeError) as error:
        _error(errors, str(error) if isinstance(error, ValueError) else "invalid_source_scope")
        return result
    if not sys.platform.startswith("linux"):
        _error(errors, "unsupported_platform")
        return result
    root_fd, registry_fd, guard_fds = None, None, []
    records, groups, unresolved, conflicts = [], {}, set(), set()
    registry_complete, guard_complete, stable = False, False, False
    domain = _current_pid_domain()
    observed = time.time_ns() // 1_000_000
    try:
        root_fd = os.open(root_path, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW)
        if os.fstat(root_fd).st_uid != os.geteuid():
            raise _ReadFailure("config_ownership_mismatch")
        root_stamp = _stamp(os.fstat(root_fd))
        result["supported"] = True
        try:
            registry_fd = _open_directory_at(root_fd, "sessions")
            registry_stamp = _stamp(os.fstat(registry_fd))
            names, capped = _directory_names(registry_fd)
            files = sorted(name for name in names if name.endswith(".json"))
            registry_complete = not capped and len(files) <= _MAX_REGISTRY_ROWS
            if not registry_complete:
                _error(errors, "registry_limit")
            total = 0
            for name in files[:_MAX_REGISTRY_ROWS]:
                try:
                    raw, size = _read_json_at(registry_fd, name, _MAX_REGISTRY_FILE_BYTES)
                    total += size
                    if total > _MAX_REGISTRY_TOTAL_BYTES:
                        raise _ReadFailure("registry_byte_limit")
                    record = _session_record(name, raw)
                    records.append((name, record))
                    sid = record["sessionId"]
                    presence = _presence(record, domain, observed, image_cache)
                    groups.setdefault(sid, []).append((record, presence))
                except (_ReadFailure, OSError) as error:
                    registry_complete = False
                    _error(errors, error.code if isinstance(error, _ReadFailure) else "registry_read_unavailable")
                    if total > _MAX_REGISTRY_TOTAL_BYTES:
                        break
            stable = True
        except (OSError, _ReadFailure):
            _error(errors, "sessions_unavailable")
        try:
            conflicts, guard_check, guard_fds = _background_guard(root_fd)
            guard_complete = guard_check()
            if not guard_complete:
                _error(errors, "background_guard_changed")
        except (OSError, _ReadFailure):
            _error(errors, "background_guard_unavailable")
        if registry_fd is not None:
            later_names, capped = _directory_names(registry_fd)
            if (capped or sorted(later_names) != sorted(names)
                    or _stamp(os.stat("sessions", dir_fd=root_fd, follow_symlinks=False)) != registry_stamp
                    or _stamp(os.stat(root_path, follow_symlinks=False)) != root_stamp):
                stable = registry_complete = False
                _error(errors, "registry_changed")
            for name, original in records:
                try:
                    raw, _ = _read_json_at(registry_fd, name, _MAX_REGISTRY_FILE_BYTES)
                    if _session_record(name, raw) != original:
                        raise _ReadFailure("registry_record_changed")
                except (OSError, _ReadFailure):
                    unresolved.add(original["sessionId"])
                    registry_complete = False
                    _error(errors, "registry_record_changed")
            # Authenticate at the end of the bounded native bracket too. A
            # crash may leave the record unchanged while the worker dies.
            observed = time.time_ns() // 1_000_000
            groups = {}
            for _, record in records:
                groups.setdefault(record["sessionId"], []).append(
                    (record, _presence(record, domain, observed, image_cache)))
            if guard_complete and not guard_check():
                guard_complete = False
                _error(errors, "background_guard_changed")
            final_names, capped = _directory_names(registry_fd)
            if capped or sorted(final_names) != sorted(names):
                stable = registry_complete = False
                _error(errors, "registry_changed")
    except (OSError, _ReadFailure):
        stable = registry_complete = False
        _error(errors, "source_unavailable")
    finally:
        for fd in [*guard_fds, registry_fd, root_fd]:
            if fd is not None:
                os.close(fd)
    if domain is None:
        registry_complete = False
        _error(errors, "pid_domain_unavailable")
    result["coverage"]["sessionRegistry"] = "complete" if registry_complete and stable else "partial" if records else "unavailable"
    result["coverage"]["backgroundGuard"] = "complete" if guard_complete else "partial" if result["supported"] else "unavailable"
    result["coverage"]["workerPresence"] = "complete" if registry_complete and stable and all(p.health == "current" for g in groups.values() for _, p in g) else "partial" if records else "unavailable"
    negative_healthy = registry_complete and stable and guard_complete and domain is not None
    result["parkedSupported"] = negative_healthy
    for sid in sorted(saved | set(groups)):
        group = groups.get(sid, [])
        issues = list(dict.fromkeys(issue for record, _ in group for issue in record["issues"]))
        live = [(r, p) for r, p in group if p.effective_value == "present" and r["kind"] == "interactive"
                and r["jobId"] is None and "invalid_job_reference" not in r["issues"]]
        unknown_worker = any(p.effective_value == "unknown" for _, p in group)
        excluded_live = any(p.effective_value == "present" and (r["kind"] != "interactive" or r["jobId"] is not None
                            or "invalid_job_reference" in r["issues"]) for r, p in group)
        presence, work, wait = Evidence("presence"), Evidence("work"), "unknown"
        disposition = {"value": "unknown", "observedAt": None, "source": None, "health": "unsupported", "reason": "interactive_runtime_unproved"}
        if not stable or sid in unresolved:
            disposition["reason"] = "native_registration_unstable"
        elif live:
            presence = live[0][1]
            work_values = [_status_work(r, p, observed) for r, p in live]
            work, wait = work_values[0]
            if any((w.effective_value, wr) != (work.effective_value, wait) for w, wr in work_values[1:]):
                work, wait = Evidence("work", health="ambiguous", reason="native_state_conflict"), "unknown"
            if len(live) > 1:
                issues.append("duplicate_live_incarnations")
        elif sid in saved and negative_healthy and not unknown_worker and not excluded_live and sid not in conflicts:
            presence = Evidence("presence", "absent", observed, "claude_registry", "current", "native_snapshot")
            disposition = {"value": "parked", "observedAt": observed, "source": "claude_registry", "health": "current",
                           "reason": "interactive_registration_assumed"}
        elif excluded_live or sid in conflicts:
            disposition["reason"] = "background_runtime_unsupported"
            issues.append("noninteractive_conflict")
        elif unknown_worker:
            disposition.update(health="ambiguous", reason="native_incarnation_unproved")
        elif not negative_healthy:
            disposition.update(health="unavailable", reason="native_registration_scan_incomplete")
        selected = live if stable and sid not in unresolved else []
        cwd_values = {r["cwd"] for r, _ in selected if r["cwd"] is not None}
        titles = {r["title"] for r, _ in selected if r["title"] is not None}
        cwd = next(iter(cwd_values)) if len(cwd_values) == 1 else None
        title = next(iter(titles)) if len(titles) == 1 else "Claude " + sid
        item = SessionObservation(NativeIdentity(host_scope, "claude", namespace, "session", sid), work, presence).metadata()
        item.update(nativeIds={"sessionId": sid}, title=title, cwd=cwd, cwdSource="claude_registry" if cwd else None,
                    waitReason=wait, phaseCapabilities=claude_registry_capabilities(live[0][0]) if live and stable and sid not in unresolved else [],
                    metadataIssues=issues, savedIdentity=sid in saved, runtimeDisposition=disposition)
        result["observations"].append(item)
    return result
