"""Provisional, passive projection of one Agent Observer JSON snapshot.

This module has no Observer/provider/consumer imports and performs no I/O
except its bounded stdin/stdout command entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Any

FRAME_SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 512 * 1024
MAX_INPUT_DEPTH = 32
MAX_INPUT_NODES = 50_000
MAX_INPUT_ROWS = 8192
MAX_OUTPUT_BYTES = 256 * 1024
DEFAULT_ROW_LIMIT = 6
MAX_ROW_LIMIT = 24
_MAX_TIME_MS = 4_000_000_000_000_000
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_PROVIDERS = frozenset({"codex", "claude"})
_SOURCE_HEALTH = frozenset({"current", "stale", "unavailable", "unsupported"})
_FEED_HEALTH = frozenset({"current", "partial", "unavailable", "stale"})
_EVIDENCE_HEALTH = frozenset({"current", "stale", "unavailable", "unsupported", "ambiguous"})
_WORK_VALUES = frozenset({"working", "needs_input", "settled", "interrupted", "error", "unknown"})
_PRESENCE_VALUES = frozenset({"present", "absent", "unknown"})
_EVIDENCE_SOURCES = frozenset(
    {"codex_rpc", "claude_registry", "claude_roster", "claude_job_store", "synthetic"}
)
_EVIDENCE_REASONS = frozenset(
    {
        "unobserved",
        "native_snapshot",
        "native_event",
        "source_unavailable",
        "observation_gap",
        "unsupported",
        "identity_ambiguous",
        "synthetic",
    }
)
_WAIT_REASONS = frozenset(
    {"approval", "user_input", "worker_request", "sandbox_request", "multiple", "unknown"}
)
_INVENTORY = frozenset({"saved", "live", "retained_job", "registry"})
_PRESENCE_KINDS = frozenset({"server_thread_loaded", "os_worker"})
_COVERAGE_DIMENSIONS = (
    "saved",
    "loaded",
    "sessionRegistry",
    "jobStore",
    "workerPresence",
    "work",
    "attachment",
    "clientBinding",
)
_COVERAGE_STATES = frozenset(
    {"complete", "partial", "unavailable", "unsupported", "supported", "reported", "unknown"}
)
_COVERAGE_REASONS = frozenset(
    {
        "not_observed",
        "native_snapshot",
        "history_limit",
        "live_limit",
        "source_failed",
        "native_proof",
        "native_transition_proof_pending",
        "source_not_established",
    }
)
_KNOWN_ERROR_CODES = frozenset(
    {
        "duplicate_native_identity",
        "invalid_inventory_page",
        "invalid_inventory_cursor",
        "inventory_page_limit",
        "invalid_loaded_identity",
        "namespace_provenance_unavailable",
        "invalid_collection_scope",
        "collection_timeout",
        "runtime_namespace_mismatch",
        "loaded_identity_ambiguous",
        "inventory_cursor_cycle",
        "loaded_read_identity_conflict",
        "saved_identity_ambiguous",
        "native_identity_mapping_conflict",
        "unsupported_runtime_version",
        "invalid_runtime_digest",
        "unsupported_runtime_digest",
        "unsupported_platform",
        "invalid_source_scope",
        "config_root_unavailable",
        "sessions_unavailable",
        "jobs_unavailable",
        "job_directory_limit",
        "job_row_limit",
        "job_directory_unavailable",
        "job_total_byte_limit",
        "session_directory_limit",
        "session_row_limit",
        "session_total_byte_limit",
        "metadata_changed_during_snapshot",
        "directory_unreadable",
        "symlink_rejected",
        "file_unavailable",
        "not_regular_file",
        "byte_limit",
        "torn_or_oversized_file",
        "invalid_json",
        "invalid_job_record",
        "invalid_session_filename",
        "invalid_session_record",
        "session_pid_mismatch",
        "invalid_session_identity",
        "job_session_id_unavailable",
        "unknown_job_state",
        "unknown_job_tempo",
        "terminal_clock_unavailable",
        "worker_start_identity_unavailable",
        "worker_pid_domain_unavailable",
        "invalid_job_reference",
        "status_clock_unavailable",
        "unknown_session_status",
        "unknown_session_kind",
        "job_session_conflict",
        "status_after_terminal_clock",
        "unsupported_namespace",
        "runtime_artifact_changed",
        "unsupported_config_root",
        "source_unavailable",
        "duplicate_key",
        "nonfinite_number",
        "native_id_multiple_namespaces",
        "native_history_time_unavailable",
    }
)
_ERROR_REASONS = frozenset(
    {
        "invalid_document",
        "invalid_json",
        "duplicate_key",
        "nonfinite_number",
        "integer_limit",
        "byte_limit",
        "depth_limit",
        "node_limit",
        "unsupported_schema",
        "invalid_provenance",
        "invalid_source",
        "invalid_session",
        "invalid_limit",
        "frame_limit",
        "display_id_collision",
    }
)


class BridgeError(ValueError):
    """A finite input or projection error that never includes source content."""

    def __init__(self, code: str) -> None:
        super().__init__(code if code in _ERROR_REASONS else "invalid_document")
        self.code = code if code in _ERROR_REASONS else "invalid_document"


def _fail(code: str = "invalid_document") -> None:
    raise BridgeError(code)


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_key")
        result[key] = value
    return result


def _parse_integer(value: str) -> int:
    if len(value.lstrip("-")) > 20:
        _fail("integer_limit")
    number = int(value)
    if not -(2**63) <= number <= 2**64 - 1:
        _fail("integer_limit")
    return number


def _parse_constant(_value: str) -> None:
    _fail("nonfinite_number")


def decode_document(data: bytes) -> object:
    """Decode one bounded JSON document, rejecting duplicate keys and nonfinite values."""
    if not isinstance(data, bytes):
        _fail("invalid_json")
    if len(data) > MAX_INPUT_BYTES:
        _fail("byte_limit")
    if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data:
        _fail("invalid_json")
    try:
        value = json.loads(
            data.decode("utf-8", "strict"),
            object_pairs_hook=_object_pairs,
            parse_constant=_parse_constant,
            parse_int=_parse_integer,
        )
    except BridgeError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        _fail("invalid_json")
    stack = [(value, 0)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        if depth > MAX_INPUT_DEPTH:
            _fail("depth_limit")
        nodes += 1
        if isinstance(node, dict):
            nodes += len(node)
            stack.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            stack.extend((child, depth + 1) for child in node)
        elif isinstance(node, float) and not math.isfinite(node):
            _fail("nonfinite_number")
        if nodes > MAX_INPUT_NODES:
            _fail("node_limit")
    return value


def _keys(value: dict[str, Any], required: set[str], allowed: set[str]) -> None:
    keys = set(value)
    if not required <= keys or not keys <= allowed:
        _fail()


def _text(value: object, *, limit: int, empty: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value) > limit
        or (not empty and not value)
        or any(unicodedata.category(char).startswith("C") for char in value)
    ):
        _fail()
    return value


def _integer(value: object, *, maximum: int = _MAX_TIME_MS, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        _fail()
    return value


def _enum(value: object, choices: frozenset[str], *, fallback: str | None = None) -> str:
    if isinstance(value, str) and value in choices:
        return value
    if fallback is not None:
        return fallback
    _fail()


def _error_code(value: object) -> str:
    if isinstance(value, str) and value in _KNOWN_ERROR_CODES:
        return value
    return "unrecognized_source_error"


def _project_errors(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 256:
        _fail()
    result = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("code"), str):
            _fail()
        result.add(_error_code(item["code"]))
    return sorted(result)[:32]


def _coverage_item(dimension: str, raw: object) -> dict[str, str]:
    state = "unknown"
    reason = "unknown"
    if isinstance(raw, str):
        if raw in _COVERAGE_STATES:
            state = raw
    elif isinstance(raw, dict):
        complete = raw.get("complete")
        supported = raw.get("supported")
        if type(complete) is bool:
            state = "complete" if complete else "partial"
        elif type(supported) is bool:
            state = "supported" if supported else "unsupported"
        elif any(
            key in raw for key in ("supportedValues", "supportedWaitFlags", "supportedWaitReasons")
        ):
            state = "reported"
        raw_reason = raw.get("reason")
        if isinstance(raw_reason, str) and raw_reason in _COVERAGE_REASONS:
            reason = raw_reason
    else:
        _fail()
    return {"dimension": dimension, "state": state, "reason": reason}


def _source(source: object) -> dict[str, Any]:
    if not isinstance(source, dict):
        _fail("invalid_source")
    required = {"schemaVersion", "collectionId", "collectedAt", "provider", "coverage"}
    allowed = required | {
        "namespace",
        "configHome",
        "configHomeKind",
        "runtime",
        "errors",
        "limitations",
        "sourceHealth",
        "durationMs",
        "ignoredMessages",
    }
    _keys(source, required, allowed)
    if type(source["schemaVersion"]) is not int or source["schemaVersion"] != 1:
        _fail("unsupported_schema")
    if not isinstance(source["collectionId"], str) or not _UUID.fullmatch(source["collectionId"]):
        _fail("invalid_source")
    _integer(source["collectedAt"])
    provider = _enum(source["provider"], _PROVIDERS)
    health = _enum(source.get("sourceHealth", "unavailable"), _SOURCE_HEALTH)
    config_home_kind = _enum(
        source.get("configHomeKind", "unknown"),
        frozenset({"default", "explicit", "unknown"}),
        fallback="unknown",
    )
    if "ignoredMessages" in source:
        _integer(source["ignoredMessages"], maximum=1_000_000)
    namespace = source.get("namespace")
    if namespace is not None:
        namespace = _text(namespace, limit=4096)
    if health == "current" and namespace is None:
        _fail("invalid_source")
    raw_coverage = source["coverage"]
    if not isinstance(raw_coverage, dict) or len(raw_coverage) > 16:
        _fail("invalid_source")
    coverage = {}
    projected_coverage = []
    for dimension in _COVERAGE_DIMENSIONS:
        if dimension not in raw_coverage:
            continue
        item = _coverage_item(dimension, raw_coverage[dimension])
        coverage[dimension] = item
        projected_coverage.append(item)
    errors = _project_errors(source.get("errors", []))
    return {
        "provider": provider,
        "namespace": namespace,
        "health": health,
        "coverage": coverage,
        "frame": {
            "provider": provider,
            "namespace": namespace,
            "configHomeKind": config_home_kind,
            "health": health,
            "coverage": projected_coverage,
            "errors": errors,
        },
    }


def _evidence(dimension: str, raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _fail("invalid_session")
    allowed = {"value", "health", "observedAt", "source", "reason", "lastKnownValue"}
    _keys(raw, {"value", "health", "observedAt", "source", "reason"}, allowed)
    if dimension == "work":
        value = _enum(raw["value"], _WORK_VALUES)
    else:
        value = _enum(raw["value"], _PRESENCE_VALUES)
    health = _enum(raw["health"], _EVIDENCE_HEALTH)
    observed_at = _integer(raw["observedAt"], nullable=True)
    source = raw["source"]
    if source is not None:
        source = _enum(source, _EVIDENCE_SOURCES)
    reason = _enum(raw["reason"], _EVIDENCE_REASONS)
    if value != "unknown" and health == "current" and (observed_at is None or source is None):
        _fail("invalid_session")
    effective_value = value if health == "current" else "unknown"
    return {
        "value": effective_value,
        "health": health,
        "observedAt": observed_at,
        "source": source,
        "reason": reason,
    }


def _missing_evidence() -> dict[str, Any]:
    return {
        "value": "unknown",
        "health": "unavailable",
        "observedAt": None,
        "source": None,
        "reason": "unobserved",
    }


def _title(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback[:48]
    normalized = "".join(
        " " if unicodedata.category(char).startswith("C") else char for char in value[:1024]
    )
    result = " ".join(normalized.split())[:48]
    return result or fallback[:48]


def _history_times(row: dict[str, Any]) -> dict[str, int | None]:
    raw = row.get("nativeHistoryTimes")
    if raw is None:
        return {"createdAt": None, "updatedAt": None}
    if not isinstance(raw, dict) or set(raw) != {"createdAt", "updatedAt"}:
        _fail("invalid_session")
    created = _integer(raw["createdAt"], maximum=_MAX_TIME_MS, nullable=True)
    updated = _integer(raw["updatedAt"], maximum=_MAX_TIME_MS, nullable=True)
    return {"createdAt": created, "updatedAt": updated}


def _identity(row: object, host_scope: str, source_map: dict[tuple[str, str], dict[str, Any]]):
    if not isinstance(row, dict) or not isinstance(row.get("identity"), dict):
        _fail("invalid_session")
    raw = row["identity"]
    fields = {"hostScope", "provider", "namespace", "nativeIdKind", "nativeId"}
    _keys(raw, fields, fields)
    scope = _text(raw["hostScope"], limit=256)
    provider = _enum(raw["provider"], _PROVIDERS)
    namespace = _text(raw["namespace"], limit=4096)
    native_kind = _text(raw["nativeIdKind"], limit=32)
    native_id = _text(raw["nativeId"], limit=256)
    if (
        scope != host_scope
        or native_kind != ("thread" if provider == "codex" else "session")
        or not _UUID.fullmatch(native_id)
        or native_id != native_id.lower()
        or (provider, namespace) not in source_map
    ):
        _fail("invalid_provenance")
    return {
        "hostScope": scope,
        "provider": provider,
        "namespace": namespace,
        "nativeIdKind": native_kind,
        "nativeId": native_id,
    }


def _project_session(
    row: dict[str, Any],
    identity: dict[str, str],
    source_health: str,
    *,
    ambiguous: bool,
    namespace_collision: bool,
) -> dict[str, Any]:
    work = _evidence("work", row["work"]) if "work" in row else _missing_evidence()
    presence = _evidence("presence", row["presence"]) if "presence" in row else _missing_evidence()
    if ambiguous:
        work.update(value="unknown", health="ambiguous", reason="identity_ambiguous")
        presence.update(value="unknown", health="ambiguous", reason="identity_ambiguous")
    native_id = identity["nativeId"]
    provider_title = "Codex" if identity["provider"] == "codex" else "Claude"
    title = _title(row.get("title"), f"{provider_title} {native_id[:8]}")
    inventory = row.get("inventory", "unknown")
    if not isinstance(inventory, str) or inventory not in _INVENTORY:
        inventory = "unknown"
    presence_kind = row.get("presenceKind", "unknown")
    if not isinstance(presence_kind, str) or presence_kind not in _PRESENCE_KINDS:
        presence_kind = "unknown"
    wait_reason = row.get("waitReason", "unknown")
    if not isinstance(wait_reason, str) or wait_reason not in _WAIT_REASONS:
        wait_reason = "unknown"
    live_selected = (
        not ambiguous
        and source_health == "current"
        and presence["health"] == "current"
        and presence["value"] == "present"
    )
    return {
        "identity": identity,
        "title": title,
        "displayId": "",
        "identityHealth": "ambiguous" if ambiguous else "current",
        "namespaceCollision": namespace_collision,
        "inventory": inventory,
        "presenceKind": presence_kind,
        "work": work,
        "presence": presence,
        "waitReason": wait_reason,
        "history": _history_times(row),
        "liveSelected": live_selected,
    }


def _display_ids(sessions: list[dict[str, Any]]) -> None:
    digests = []
    for row in sessions:
        identity = row["identity"]
        material = "\0".join(
            identity[field]
            for field in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
        ).encode("utf-8")
        digests.append(hashlib.sha256(material).hexdigest())
    for width in range(8, 65, 4):
        owners: dict[str, tuple[str, str, str, str, str]] = {}
        collision = False
        for row, digest in zip(sessions, digests, strict=True):
            identity = row["identity"]
            key = tuple(
                identity[field]
                for field in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
            )
            short = digest[:width]
            if short in owners and owners[short] != key:
                collision = True
                break
            owners[short] = key
        if not collision:
            for row, digest in zip(sessions, digests, strict=True):
                row["displayId"] = f"S-{digest[:width]}"
            return
    _fail("display_id_collision")


def _attention_rank(session: dict[str, Any]) -> int:
    return {
        "needs_input": 0,
        "error": 1,
        "interrupted": 1,
        "working": 2,
        "unknown": 3,
        "settled": 4,
    }[session["work"]["value"]]


def _sort_time(session: dict[str, Any]) -> int:
    work_time = session["work"]["observedAt"]
    if work_time is not None:
        return work_time
    history = session["history"]
    if history["updatedAt"] is not None:
        return history["updatedAt"]
    if history["createdAt"] is not None:
        return history["createdAt"]
    return -1


def _sort_key(session: dict[str, Any]) -> tuple[Any, ...]:
    identity = session["identity"]
    key = tuple(
        identity[field]
        for field in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
    )
    stable_row = json.dumps(session, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return (
        0 if session["liveSelected"] else 1,
        _attention_rank(session),
        -_sort_time(session),
        key,
        stable_row,
    )


def _source_inventory_complete(source: dict[str, Any]) -> bool:
    if source["health"] != "current":
        return False
    coverage = source["coverage"]
    if source["provider"] == "codex":
        return coverage.get("loaded", {}).get("state") == "complete"
    return all(
        coverage.get(dimension, {}).get("state") == "complete"
        for dimension in ("sessionRegistry", "jobStore", "workerPresence")
    )


def project_document(document: object, *, row_limit: int = DEFAULT_ROW_LIMIT) -> dict[str, Any]:
    """Validate and reduce a decoded schema-v1 snapshot to a display-only frame."""
    if (
        isinstance(row_limit, bool)
        or not isinstance(row_limit, int)
        or not 1 <= row_limit <= MAX_ROW_LIMIT
    ):
        _fail("invalid_limit")
    if not isinstance(document, dict):
        _fail()
    required = {
        "schemaVersion",
        "collectionId",
        "collectedAt",
        "host",
        "sources",
        "sessions",
        "errors",
        "sourceHealth",
    }
    allowed = required | {"limitations", "durationMs"}
    _keys(document, required, allowed)
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        _fail("unsupported_schema")
    collection_id = document["collectionId"]
    if not isinstance(collection_id, str) or not _UUID.fullmatch(collection_id):
        _fail()
    collected_at = _integer(document["collectedAt"])
    host = document["host"]
    if not isinstance(host, dict):
        _fail("invalid_provenance")
    host_required = {"authority", "authoritySource"}
    host_allowed = host_required | {"nativeHostname", "uid"}
    _keys(host, host_required, host_allowed)
    host_scope = _text(host["authority"], limit=256)
    if host["authoritySource"] != "caller":
        _fail("invalid_provenance")
    if "nativeHostname" in host:
        _text(host["nativeHostname"], limit=256)
    if "uid" in host:
        _integer(host["uid"], maximum=2**31 - 1)
    input_source_health = _enum(document["sourceHealth"], _FEED_HEALTH)
    raw_sources = document["sources"]
    if not isinstance(raw_sources, list) or not 1 <= len(raw_sources) <= 8:
        _fail("invalid_source")
    sources = []
    source_map: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_source in raw_sources:
        source = _source(raw_source)
        key = (source["provider"], source["namespace"])
        if key in source_map:
            _fail("invalid_source")
        source_map[key] = source
        sources.append(source)
    sources.sort(
        key=lambda source: (
            source["provider"],
            source["namespace"] or "",
        )
    )
    raw_rows = document["sessions"]
    if not isinstance(raw_rows, list) or len(raw_rows) > MAX_INPUT_ROWS:
        _fail()
    identities = [_identity(row, host_scope, source_map) for row in raw_rows]
    key_tuples = [
        tuple(
            identity[field]
            for field in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
        )
        for identity in identities
    ]
    key_counts = Counter(key_tuples)
    namespace_groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for identity in identities:
        namespace_groups[
            (identity["provider"], identity["nativeIdKind"], identity["nativeId"])
        ].add(identity["namespace"])
    projected = []
    for row, identity, key in zip(raw_rows, identities, key_tuples, strict=True):
        source_health = source_map[(identity["provider"], identity["namespace"])]["health"]
        base_id = (identity["provider"], identity["nativeIdKind"], identity["nativeId"])
        projected.append(
            _project_session(
                row,
                identity,
                source_health,
                ambiguous=key_counts[key] > 1,
                namespace_collision=len(namespace_groups[base_id]) > 1,
            )
        )
    _display_ids(projected)
    projected.sort(key=_sort_key)
    visible = projected[:row_limit]
    global_errors = _project_errors(document["errors"])
    issues = set(global_errors)
    if any(count > 1 for count in key_counts.values()):
        issues.add("duplicate_native_identity")
    if any(len(namespaces) > 1 for namespaces in namespace_groups.values()):
        issues.add("native_id_multiple_namespaces")
    source_complete = {source["provider"] for source in sources} == _PROVIDERS and all(
        _source_inventory_complete(source) for source in sources
    )
    feed_complete = (
        source_complete
        and input_source_health == "current"
        and not global_errors
        and not any(count > 1 for count in key_counts.values())
        and all(not source["frame"]["errors"] for source in sources)
        and not any(
            session["inventory"] != "saved" and session["presence"]["value"] == "unknown"
            for session in projected
        )
    )
    row_facts_complete = all(
        session["work"]["health"] == "current"
        and session["work"]["value"] != "unknown"
        and session["presence"]["health"] == "current"
        and session["presence"]["value"] != "unknown"
        for session in projected
    )
    if feed_complete and row_facts_complete:
        feed_health = "current"
    elif any(source["health"] == "current" for source in sources) or projected:
        feed_health = "partial"
    else:
        feed_health = "unavailable"
    live_count = sum(
        1
        for session in projected
        if session["liveSelected"] and session["identityHealth"] == "current"
    )
    empty_state = (
        "live_rows" if live_count else "no_live_sessions" if feed_complete else "partial_or_unknown"
    )
    frame = {
        "frameSchemaVersion": FRAME_SCHEMA_VERSION,
        "candidate": True,
        "hostScope": host_scope,
        "collectionId": collection_id,
        "collectedAt": collected_at,
        "sourceHealth": input_source_health,
        "feedHealth": feed_health,
        "liveInventory": "complete" if feed_complete else "partial_or_unknown",
        "emptyState": empty_state,
        "liveRowCount": live_count,
        "rowCount": len(projected),
        "visibleRowCount": len(visible),
        "truncated": len(visible) < len(projected),
        "sources": [source["frame"] for source in sources],
        "issues": sorted(issues),
        "sessions": visible,
        "limitations": [
            "display_candidate",
            "device_transport_unaccepted",
            "no_provider_actions",
        ],
    }
    encoded = json.dumps(frame, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(encoded) > MAX_OUTPUT_BYTES:
        _fail("frame_limit")
    return frame


def project_bytes(data: bytes, *, row_limit: int = DEFAULT_ROW_LIMIT) -> dict[str, Any]:
    return project_document(decode_document(data), row_limit=row_limit)


def _error_frame(code: str) -> dict[str, Any]:
    return {
        "frameSchemaVersion": FRAME_SCHEMA_VERSION,
        "candidate": True,
        "feedHealth": "unavailable",
        "liveInventory": "partial_or_unknown",
        "emptyState": "partial_or_unknown",
        "liveRowCount": 0,
        "rowCount": 0,
        "visibleRowCount": 0,
        "truncated": False,
        "sources": [],
        "issues": [],
        "sessions": [],
        "error": {"code": code if code in _ERROR_REASONS else "invalid_document"},
        "limitations": [
            "display_candidate",
            "device_transport_unaccepted",
            "no_provider_actions",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_ROW_LIMIT)
    arguments = parser.parse_args(argv)
    if not 1 <= arguments.limit <= MAX_ROW_LIMIT:
        frame = _error_frame("invalid_limit")
        exit_code = 2
    else:
        try:
            raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
            frame = project_bytes(raw, row_limit=arguments.limit)
            exit_code = 0
        except BridgeError as error:
            frame = _error_frame(error.code)
            exit_code = 2
    output = json.dumps(frame, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    sys.stdout.write(output + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
