"""Provisional 0.160.0 metadata projection, never provider action authority.

The native managed proof established thread/read(includeTurns=false), UUID
fields, name, and idle status. Active/wait mappings are schema candidates until
the corresponding native transition cases pass. Saved metadata never supplies
fresh work evidence. No preview, turn, originator or arbitrary payload escapes.
"""

from __future__ import annotations

import re
import unicodedata

from .observation_model import (
    Evidence,
    NativeIdentity,
    SessionObservation,
    bounded_native_title,
)

_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_WAIT_FLAGS = frozenset({"waitingOnApproval", "waitingOnUserInput"})
_STATUS = frozenset({"notLoaded", "idle", "active", "systemError"})
_SOURCES = frozenset({"cli", "vscode", "exec", "appServer", "unknown"})
_MAX_HISTORY_UNIX_SECONDS = 4_000_000_000


class MetadataError(ValueError):
    """Finite projection failure; never contains source values."""


def _uuid(value):
    if not isinstance(value, str) or not _UUID.fullmatch(value):
        raise MetadataError("invalid_native_identity")
    return value.lower()


def _history_times(payload):
    """Project only the provider's explicit Unix-second history fields."""

    result = {}
    unavailable = False
    for source_key, target_key in (("createdAt", "createdAt"), ("updatedAt", "updatedAt")):
        value = payload.get(source_key)
        if type(value) is not int or not 0 <= value <= _MAX_HISTORY_UNIX_SECONDS:
            result[target_key] = None
            unavailable = True
        else:
            result[target_key] = value * 1000
    return result, unavailable


def _subagent_source_state(source):
    """Return whether the bounded thread-spawn marker is valid or malformed."""

    if not isinstance(source, dict) or "subAgent" not in source:
        return False, False
    if set(source) != {"subAgent"}:
        return False, True
    subagent = source["subAgent"]
    if isinstance(subagent, str) and subagent in {"review", "compact"}:
        return True, True
    if not isinstance(subagent, dict) or "thread_spawn" not in subagent:
        return False, True
    spawn = subagent["thread_spawn"]
    if not isinstance(spawn, dict):
        return False, True
    parent_id = spawn.get("parent_thread_id")
    if not isinstance(parent_id, str) or not _UUID.fullmatch(parent_id):
        return False, True
    return True, True


def _thread_classification(source, thread_source):
    """Project either native child signal, leaving explicit conflicts unknown."""

    child_source, child_candidate = _subagent_source_state(source)
    if child_source:
        source_kind = "subagent"
    elif isinstance(source, str) and source in _SOURCES:
        source_kind = source
    else:
        source_kind = "unknown"

    if thread_source == "subagent":
        return source_kind, "child", None
    if child_source:
        if thread_source == "user":
            return source_kind, "unknown", "thread_classification_conflict"
        return source_kind, "child", None
    if child_candidate:
        issue = (
            "thread_classification_conflict"
            if thread_source == "user"
            else "thread_classification_unavailable"
        )
        return source_kind, "unknown", issue
    if thread_source == "user":
        source_is_bounded = source is None or (isinstance(source, str) and source in _SOURCES)
        if source_is_bounded:
            return source_kind, "user", None
        return source_kind, "unknown", "thread_classification_unavailable"
    return source_kind, "unknown", None


def _projection(payload, *, host_scope, namespace, runtime_version):
    if runtime_version != "0.160.0":
        raise MetadataError("unsupported_runtime_version")
    if not isinstance(payload, dict):
        raise MetadataError("invalid_thread_metadata")
    thread_id = _uuid(payload.get("id"))
    session_id = _uuid(payload.get("sessionId"))
    observation = SessionObservation(
        NativeIdentity(host_scope, "codex", namespace, "thread", thread_id),
        attachment=Evidence("attachment", health="unsupported", reason="unsupported"),
    )
    cwd = payload.get("cwd")
    issues = []
    if (
        not isinstance(cwd, str)
        or not cwd.startswith("/")
        or len(cwd) > 4096
        or any(unicodedata.category(char).startswith("C") for char in cwd)
    ):
        cwd = None
        issues.append("cwd_unavailable")
    source = payload.get("source")
    source, thread_source, thread_issue = _thread_classification(
        source, payload.get("threadSource")
    )
    if thread_issue is not None:
        issues.append(thread_issue)
    history_times, history_unavailable = _history_times(payload)
    if history_unavailable:
        issues.append("native_history_time_unavailable")
    metadata = {
        "nativeIds": {"threadId": thread_id, "sessionId": session_id},
        "title": bounded_native_title(payload.get("name"), "Codex " + thread_id),
        "cwd": cwd,
        "runtimeVersion": runtime_version,
        "sourceKind": source,
        "threadKind": thread_source,
        "nativeHistoryTimes": history_times,
        "metadataIssues": issues,
    }
    return observation, metadata


def saved_thread_metadata(payload, *, host_scope, namespace, runtime_version):
    observation, metadata = _projection(
        payload,
        host_scope=host_scope,
        namespace=namespace,
        runtime_version=runtime_version,
    )
    return {**observation.metadata(), **metadata, "inventory": "saved"}


def live_thread_metadata(payload, *, host_scope, namespace, runtime_version, observed_at):
    """Only for a current authoritative owning-runtime read, not saved files."""
    observation, metadata = _projection(
        payload,
        host_scope=host_scope,
        namespace=namespace,
        runtime_version=runtime_version,
    )
    status = payload.get("status")
    if (
        not isinstance(status, dict)
        or not isinstance(status.get("type"), str)
        or status["type"] not in _STATUS
    ):
        raise MetadataError("unsupported_status_schema")
    kind = status["type"]
    flags = status.get("activeFlags") if kind == "active" else []
    known_flags = (
        isinstance(flags, list)
        and len(flags) <= 8
        and all(isinstance(flag, str) and flag in _WAIT_FLAGS for flag in flags)
        and len(flags) == len(set(flags))
    )
    presence = Evidence(
        "presence",
        "absent" if kind == "notLoaded" else "present",
        observed_at,
        "codex_rpc",
        "current",
        "native_snapshot",
    )
    if kind == "notLoaded":
        work = Evidence("work", health="unavailable", reason="unobserved")
    elif kind == "idle":
        work = Evidence("work", "settled", observed_at, "codex_rpc", "current", "native_snapshot")
    elif kind == "systemError":
        work = Evidence("work", "error", observed_at, "codex_rpc", "current", "native_snapshot")
    elif known_flags:
        work = Evidence(
            "work",
            "needs_input" if flags else "working",
            observed_at,
            "codex_rpc",
            "current",
            "native_snapshot",
        )
    else:
        work = Evidence("work", health="unsupported", reason="unsupported")
    observation = SessionObservation(observation.identity, work, presence, observation.attachment)
    return {
        **observation.metadata(),
        **metadata,
        "inventory": "live",
        "nativeState": {"type": kind, "activeFlags": flags if known_flags else []},
        "waitReason": (
            "approval"
            if flags == ["waitingOnApproval"]
            else "user_input"
            if flags == ["waitingOnUserInput"]
            else "multiple"
            if known_flags and len(flags) > 1
            else "unknown"
        ),
    }
