"""Experimental metadata-only callback normalization; no publishing or provider reads."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import uuid

from .bounded_json import decode_document
from .contract import IDENTITY, TIME, UUID, choice, obj, text, validate_shape
from .public import identity_key, validate_snapshot

MAX_HOOK_BYTES = 1024 * 1024
MAX_EVENT_BYTES = 16384
BODIES = {
    "turn_complete": "Turn complete",
    "permission": "Permission needed",
    "question": "Waiting for input",
    "idle": "Waiting for input",
    "wake": None,
    "unsupported": None,
}
EVENT = obj(
    schemaVersion={"const": 1},
    receiptId=text(36, pattern=UUID),
    receivedAt=TIME,
    identity=IDENTITY,
    source=choice("codex_notify", "claude_hook"),
    sourceEvent=choice(
        "agent-turn-complete",
        "Notification",
        "Stop",
        "SubagentStop",
        "UserPromptSubmit",
        "unsupported",
    ),
    signal=choice(*BODIES),
    disposition=choice("notify", "wake", "ignore"),
    reason=choice(
        "native_signal",
        "child_suppressed",
        "noninteractive_suppressed",
        "unsupported_event",
        "response_end_only",
        "prompt_wakeup",
        "background_target_unproved",
    ),
    kind=choice("user", "child", "unknown"),
    title=text(256),
    titleSource=choice("snapshot", "fallback"),
    body=choice(*dict.fromkeys(BODIES.values())),
    correlation=obj(
        nativeId=text(36, pattern=UUID, nullable=True),
        scope=choice("native_turn", "native_prompt", "receipt_only"),
        dedupeKey=text(71, pattern=r"^sha256:[0-9a-f]{64}$", nullable=True),
    ),
)


class NotificationError(ValueError):
    """Finite metadata failure; never includes callback text."""


def schema_document():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **copy.deepcopy(EVENT)}


def _native_uuid(value):
    return value if isinstance(value, str) and re.fullmatch(UUID, value, re.ASCII) else None


def _turn_key(identity, native_id):
    data = json.dumps([*identity_key(identity), "turn_complete", native_id], separators=(",", ":"))
    return "sha256:" + hashlib.sha256(data.encode()).hexdigest()


def validate_event(event):
    validate_shape(event, EVENT)
    identity_key(event["identity"])
    provider = event["identity"]["provider"]
    if (
        event["receivedAt"] is None
        or event["identity"]["nativeIdKind"] != ("thread" if provider == "codex" else "session")
        or event["source"] != ("codex_notify" if provider == "codex" else "claude_hook")
        or event["body"] != BODIES[event["signal"]]
    ):
        raise NotificationError("invalid_notification_event")
    correlation = event["correlation"]
    expected_scope = (
        ("native_turn" if provider == "codex" else "native_prompt")
        if correlation["nativeId"]
        else "receipt_only"
    )
    expected_key = (
        _turn_key(event["identity"], correlation["nativeId"])
        if (provider == "codex" and event["signal"] == "turn_complete" and correlation["nativeId"])
        else None
    )
    if correlation["scope"] != expected_scope or correlation["dedupeKey"] != expected_key:
        raise NotificationError("invalid_notification_event")
    expected = (
        "ignore"
        if event["reason"] in {"child_suppressed", "noninteractive_suppressed", "unsupported_event"}
        else "wake"
        if event["reason"] in {"response_end_only", "prompt_wakeup", "background_target_unproved"}
        else "notify"
    )
    if event["disposition"] != expected or event["kind"] == "child" and expected != "ignore":
        raise NotificationError("invalid_notification_event")
    if event["disposition"] == "notify" and event["signal"] not in {
        "turn_complete",
        "permission",
        "question",
        "idle",
    }:
        raise NotificationError("invalid_notification_event")
    if provider == "claude" and event["signal"] == "turn_complete":
        raise NotificationError("invalid_notification_event")
    if provider == "codex" and event["sourceEvent"] not in {"agent-turn-complete", "unsupported"}:
        raise NotificationError("invalid_notification_event")
    if event["reason"] == "native_signal" and (
        event["sourceEvent"] != ("agent-turn-complete" if provider == "codex" else "Notification")
        or event["signal"]
        not in ({"turn_complete"} if provider == "codex" else {"permission", "question", "idle"})
    ):
        raise NotificationError("invalid_notification_event")
    if event["sourceEvent"] == "SubagentStop" and event["kind"] != "child":
        raise NotificationError("invalid_notification_event")
    return event


def parse_event(data, *, framed=False):
    return validate_event(
        decode_document(data, max_bytes=MAX_EVENT_BYTES, max_nodes=256, line_framed=framed)
    )


def normalize(data, identity, *, snapshot=None, received_at=None, receipt_id=None):
    """Caller supplies owning host/store identity; callback IDs must match it exactly.

    Raw message/title/transcript paths/tool payloads are discarded in memory.
    Stop is a wakeup only. Claude manager background events lack accepted target
    correlation. Prompt IDs correlate callbacks but do not identify attention events.
    """
    identity_key(identity)
    provider = identity["provider"]
    if identity["nativeIdKind"] != ("thread" if provider == "codex" else "session"):
        raise NotificationError("event_identity_mismatch")
    payload = decode_document(data, max_bytes=MAX_HOOK_BYTES, max_depth=32, max_nodes=100000)
    if not isinstance(payload, dict):
        raise NotificationError("invalid_hook_metadata")
    if payload.get("thread-id" if provider == "codex" else "session_id") != identity["nativeId"]:
        raise NotificationError("event_identity_mismatch")
    row = None
    if snapshot is not None:
        validate_snapshot(snapshot)
        if snapshot["host"]["authority"] != identity["hostScope"]:
            raise NotificationError("event_identity_mismatch")
        row = next((r for r in snapshot["sessions"] if r["identity"] == identity), None)
    kind = row["kind"] if row else "unknown"
    signal, reason, source_event = "unsupported", "unsupported_event", "unsupported"
    if provider == "codex":
        if payload.get("type") == "agent-turn-complete":
            signal, reason, source_event = "turn_complete", "native_signal", "agent-turn-complete"
        native_id = _native_uuid(payload.get("turn-id"))
        if payload.get("client") == "codex_exec":
            reason = "noninteractive_suppressed"
    else:
        event = payload.get("hook_event_name")
        if not isinstance(event, str):
            raise NotificationError("invalid_hook_metadata")
        native_id = _native_uuid(payload.get("prompt_id"))
        if event == "Notification":
            if not isinstance(payload.get("notification_type"), str):
                raise NotificationError("invalid_hook_metadata")
            source_event = event
            signal = {
                "permission_prompt": "permission",
                "idle_prompt": "idle",
                "elicitation_dialog": "question",
                "elicitation_url_dialog": "question",
            }.get(payload.get("notification_type"), "unsupported")
            if signal != "unsupported":
                reason = "native_signal"
            elif payload.get("notification_type") in {"agent_completed", "agent_needs_input"}:
                signal, reason = "wake", "background_target_unproved"
        elif event in {"Stop", "SubagentStop", "UserPromptSubmit"}:
            source_event, signal = event, "wake"
            reason = "prompt_wakeup" if event == "UserPromptSubmit" else "response_end_only"
        child_id = payload.get("agent_id")
        if child_id is not None and (
            not isinstance(child_id, str) or not 1 <= len(child_id) <= 128
        ):
            raise NotificationError("invalid_hook_metadata")
        if child_id is not None or event == "SubagentStop":
            kind = "child"
        # agent_type can describe a top-level --agent session; never suppress by it.
    if kind == "child":
        reason = "child_suppressed"
    disposition = (
        "ignore"
        if reason in {"child_suppressed", "noninteractive_suppressed", "unsupported_event"}
        else "wake"
        if signal == "wake"
        else "notify"
    )
    event = {
        "schemaVersion": 1,
        "receiptId": receipt_id or str(uuid.uuid4()),
        "receivedAt": int(time.time() * 1000) if received_at is None else received_at,
        "identity": copy.deepcopy(identity),
        "source": "codex_notify" if provider == "codex" else "claude_hook",
        "sourceEvent": source_event,
        "signal": signal,
        "disposition": disposition,
        "reason": reason,
        "kind": kind,
        "title": row["title"]
        if row
        else ("Codex " if provider == "codex" else "Claude ") + identity["nativeId"],
        "titleSource": "snapshot" if row else "fallback",
        "body": BODIES[signal],
        "correlation": {
            "nativeId": native_id,
            "scope": ("native_turn" if provider == "codex" else "native_prompt")
            if native_id
            else "receipt_only",
            "dedupeKey": _turn_key(identity, native_id)
            if provider == "codex" and signal == "turn_complete" and native_id
            else None,
        },
    }
    return validate_event(event)
