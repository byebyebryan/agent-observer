"""API 4 observation wire 6; bounded pure validation without action imports."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import PurePosixPath

from .bounded_json import decode_document
from .contract_shape import compile_shape

SCHEMA_VERSION = 6
MAX_BYTES = 8 * 1024 * 1024
MAX_SNAPSHOT_BYTES = MAX_BYTES - 1024
MAX_NODES = 2_000_000
MAX_SESSIONS = 4096
UUID = r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$"
SCOPE = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$"
CODE = r"^[a-z][a-z0-9_]{0,127}$"
DIGEST = r"^sha256:[0-9a-f]{64}$"
ASCII_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")


def text(limit=4096, *, pattern=None, nullable=False):
    result = {"type": ["string", "null"] if nullable else "string", "maxLength": limit}
    if not nullable:
        result["minLength"] = 1
    if pattern:
        result["pattern"] = pattern
    return result


def choice(*values):
    return {"enum": list(values)}


def obj(**properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def array(items, limit=2048):
    return {"type": "array", "items": items, "maxItems": limit}


TIME = {"type": ["integer", "null"], "minimum": 0, "maximum": 4_000_000_000_000}
BOOL = {"type": "boolean"}
INTEGER = {"type": "integer", "minimum": 0, "maximum": 2**53 - 1}
HEALTH = choice("current", "stale", "unavailable", "unsupported", "ambiguous")
PROVIDER = choice("codex", "claude")
IDENTITY = obj(
    hostScope=text(256, pattern=SCOPE),
    provider=PROVIDER,
    namespace=text(71, pattern=DIGEST),
    nativeIdKind=choice("thread", "session"),
    nativeId=text(36, pattern=UUID),
)


def evidence(*values):
    result = obj(
        value=choice(*values, "unknown"),
        observedAt=TIME,
        source=text(128, pattern=CODE, nullable=True),
        health=HEALTH,
        reason=text(128, pattern=CODE),
        clock=choice("native", "sample", None),
    )
    result["properties"]["lastKnownValue"] = choice(*values)
    return result


PHASE = evidence("working", "blocked", "waiting")
RUNTIME = evidence("running", "parked")
OUTCOME = evidence("completed", "failed", "cancelled")
COVERAGE = obj(
    status=choice("complete", "partial", "unavailable", "unsupported"),
    reason=text(128, pattern=CODE),
)
RUNTIME_COVERAGE = {
    **COVERAGE,
    "properties": {
        **COVERAGE["properties"],
        "scope": choice("daemon_threads", "provider_sessions"),
    },
    "required": [*COVERAGE["required"], "scope"],
}
ACTIVITY = obj(
    at=TIME,
    source=text(128, pattern=CODE, nullable=True),
    health=HEALTH,
    reason=text(128, pattern=CODE),
)
ACTIVITY["properties"]["lastKnownAt"] = TIME
PRECISION = {"type": ["integer", "null"], "minimum": 1, "maximum": 4_000_000_000_000}
TIMING_RECEIPT = {"anyOf": [obj(
    component=choice("runtime", "history"), sampledBoottimeMs=INTEGER,
    observedBoottimeMs=INTEGER, contextGeneration=INTEGER,
), {"type": "null"}]}
TURN = obj(
    id=text(512, nullable=True),
    status=choice("in_progress", "completed", "failed", "cancelled", "unknown"),
    startedAt=TIME, completedAt=TIME, durationMs=TIME, timestampPrecisionMs=PRECISION,
)
LATEST_TURN = obj(
    value={"anyOf": [TURN, {"type": "null"}]}, observedAt=TIME,
    source=text(128, pattern=CODE, nullable=True), health=HEALTH,
    reason=text(128, pattern=CODE), receipt=TIMING_RECEIPT,
)
LATEST_TURN["properties"]["lastKnownValue"] = TURN
LAST_UPDATED = obj(
    at=TIME, timestampPrecisionMs=PRECISION, observedAt=TIME,
    source=text(128, pattern=CODE, nullable=True), health=HEALTH,
    reason=text(128, pattern=CODE), receipt=TIMING_RECEIPT,
)
LAST_UPDATED["properties"].update(lastKnownAt=TIME, lastKnownTimestampPrecisionMs=PRECISION)
RUNTIME_INFO = obj(
    version=text(64),
    binarySha256=text(64, pattern=r"^[0-9a-f]{64}$"),
    topology=text(128, pattern=CODE),
    bootId=text(36, pattern=UUID),
    pid={"type": ["integer", "null"], "minimum": 1},
    startTicks=TIME,
    endpoint=text(nullable=True),
)
RUNTIME_INFO = {"anyOf": [RUNTIME_INFO, {"type": "null"}]}
WORKSPACE = {
    "anyOf": [
        obj(
            health=choice("current", "unavailable", "unsupported"),
            reason=text(128, pattern=CODE),
            root=text(nullable=True),
            rootKey=text(128, pattern=SCOPE, nullable=True),
            relativePath=text(nullable=True),
            projectKey=text(256, pattern=SCOPE, nullable=True),
            repo={
                "anyOf": [
                    obj(root=text(), commonDir=text(), relativePath=text(nullable=True)),
                    {"type": "null"},
                ]
            },
        ),
        {"type": "null"},
    ]
}
DISCOVERY = {"anyOf": [obj(
    catalogMode=text(128, pattern=CODE),
    sourceKinds=array(text(128), 32),
    catalogRows=INTEGER,
    runtimeRows=INTEGER,
    parkedRows=INTEGER,
    pages=INTEGER,
    nativeMessageBytes=INTEGER,
    historyClocks=BOOL,
), {"type": "null"}]}
SOURCE = obj(
    provider=PROVIDER,
    namespace=text(71, pattern=DIGEST),
    runtimeNamespace=text(71, pattern=DIGEST, nullable=True),
    configHome=text(),
    configHomeKind=choice("default", "explicit"),
    runtime=RUNTIME_INFO,
    discovery=DISCOVERY,
    sourceHealth=choice("current", "partial", "stale", "unavailable"),
    coverage=obj(saved=COVERAGE, runtime=RUNTIME_COVERAGE),
    capabilities=obj(
        phase=array(choice("working", "blocked", "waiting"), 3),
        blockedReasons=array(choice("approval", "question"), 2),
        runtime=array(choice("running", "parked"), 2),
        activity=BOOL,
        timing=obj(lastUpdated=BOOL, latestTurn=BOOL),
    ),
    errors=array(text(128, pattern=CODE), 128),
    limitations=array(text(128, pattern=CODE), 128),
)
SESSION = obj(
    identity=IDENTITY,
    nativeIds={"anyOf": [
        obj(threadId=text(36, pattern=UUID), sessionTreeRootId=text(36, pattern=UUID)),
        obj(sessionId=text(36, pattern=UUID)),
    ]},
    title=text(256),
    kind=choice("user", "child", "system", "unknown"),
    cwd=text(nullable=True),
    cwdSource=text(128, pattern=CODE, nullable=True),
    inventory=choice("live", "saved"),
    hasSavedHistory=BOOL,
    phase={"anyOf": [PHASE, {"type": "null"}]},
    runtime=RUNTIME,
    outcome=OUTCOME,
    blockedReasons=array(choice("approval", "question"), 2),
    createdAt=TIME,
    activity=ACTIVITY,
    lastUpdated=LAST_UPDATED,
    latestTurn=LATEST_TURN,
    workspace=WORKSPACE,
    metadataIssues=array(text(128, pattern=CODE), 128),
)
SNAPSHOT = obj(
    schemaVersion={"const": SCHEMA_VERSION},
    collectionId=text(36, pattern=UUID),
    collectedAt=TIME,
    host=obj(
        authority=text(256, pattern=SCOPE),
        authoritySource=choice("caller"),
        nativeHostname=text(256),
        uid=INTEGER,
    ),
    sourceHealth=choice("current", "partial", "unavailable"),
    sources=array(SOURCE, 2),
    sessions=array(SESSION, MAX_SESSIONS),
    errors=array(text(128, pattern=CODE), 128),
    limitations=array(text(128, pattern=CODE), 128),
)
WATCH = obj(
    schemaVersion={"const": SCHEMA_VERSION},
    streamId=text(36, pattern=UUID),
    revision=INTEGER,
    kind=choice("snapshot", "change", "heartbeat", "gap", "resync"),
    sampledAt=TIME,
    reason=text(128, pattern=CODE),
    snapshot={"anyOf": [SNAPSHOT, {"type": "null"}]},
)


class ContractError(ValueError):
    """Finite code; never includes input values or field contents."""


# These versioned schema definitions are fixed contract inputs. Compile their
# complete shape checks once; the public dynamic interpreter remains available
# for caller-supplied schemas, and all cross-field semantics still run below.
_SESSION_SHAPE = compile_shape(SESSION, ContractError, ASCII_CONTROLS)
_SNAPSHOT_SHAPE = compile_shape(SNAPSHOT, ContractError, ASCII_CONTROLS)


def schema_document(name):
    spec = {"snapshot": SNAPSHOT, "watch": WATCH}[name]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:{name}:{SCHEMA_VERSION}",
        **copy.deepcopy(spec),
    }


def _matches_type(value, kind):
    # This runs for every typed node. Only evaluate the requested predicate;
    # building a dispatch dictionary evaluated all six on every call.
    if kind == "null":
        return value is None
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return type(value) is int
    if kind == "boolean":
        return type(value) is bool
    return False


def validate_shape(value, spec):
    """Validate the deliberately small JSON Schema vocabulary used above."""
    if "anyOf" in spec:
        for alternative in spec["anyOf"]:
            try:
                validate_shape(value, alternative)
                return
            except ContractError:
                pass
        raise ContractError("invalid_contract_shape")
    if "const" in spec and (type(value) is not type(spec["const"]) or value != spec["const"]):
        raise ContractError("schema_mismatch")
    if "enum" in spec and not any(
        type(value) is type(item) and value == item for item in spec["enum"]
    ):
        raise ContractError("invalid_contract_value")
    if "type" in spec:
        types = spec["type"]
        matches = (any(_matches_type(value, kind) for kind in types) if isinstance(types, list)
                   else _matches_type(value, types))
        if not matches:
            raise ContractError("invalid_contract_type")
    if isinstance(value, dict):
        properties = spec.get("properties", {})
        if not set(spec.get("required", ())) <= set(value) or (
            spec.get("additionalProperties") is False and not set(value) <= set(properties)
        ):
            raise ContractError("invalid_contract_fields")
        for key, item in value.items():
            if key in properties:
                validate_shape(item, properties[key])
    elif isinstance(value, list):
        if len(value) > spec.get("maxItems", 4096):
            raise ContractError("contract_row_limit")
        for item in value:
            validate_shape(item, spec["items"])
    elif isinstance(value, str):
        if not spec.get("minLength", 0) <= len(value) <= spec.get("maxLength", 4096):
            raise ContractError("invalid_contract_text")
        controls = (ASCII_CONTROLS.search(value) is not None if str.isascii(value) else
                    any(unicodedata.category(c).startswith("C") for c in value))
        if controls:
            raise ContractError("invalid_contract_text")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], value, re.ASCII):
            raise ContractError("invalid_contract_text")
    elif type(value) is int:
        if not spec.get("minimum", -(2**63)) <= value <= spec.get("maximum", 2**64 - 1):
            raise ContractError("invalid_contract_number")


def identity_key(identity):
    validate_shape(identity, IDENTITY)
    return _admitted_identity_key(identity)


def _admitted_identity_key(identity):
    """Internal tuple extraction after the containing row passed admission."""
    return (identity["hostScope"], identity["provider"], identity["namespace"],
            identity["nativeIdKind"], identity["nativeId"])


def _validate_record_semantics(row, host_scope, sources):
    """Already-shaped API 4 row against an admitted provider/namespace index."""
    identity = row["identity"]
    if (
        identity["hostScope"] != host_scope
        or (identity["provider"], identity["namespace"]) not in sources
    ):
        raise ContractError("provenance_mismatch")
    ids = row["nativeIds"]
    if row["cwd"] is not None and (
        not PurePosixPath(row["cwd"]).is_absolute() or ".." in PurePosixPath(row["cwd"]).parts
    ):
        raise ContractError("invalid_cwd_path")
    if (
        identity["provider"] == "codex"
        and (
            identity["nativeIdKind"] != "thread"
            or set(ids) != {"threadId", "sessionTreeRootId"}
            or identity["nativeId"] != ids.get("threadId")
        )
    ) or (
        identity["provider"] == "claude"
        and (
            identity["nativeIdKind"] != "session"
            or set(ids) != {"sessionId"}
            or identity["nativeId"] != ids.get("sessionId")
        )
    ):
        raise ContractError("native_identity_conflict")
    for dimension in ("phase", "runtime", "outcome"):
        fact = row[dimension]
        if fact is None:
            continue
        if fact["value"] != "unknown" and (
            fact["health"] != "current"
            or fact["observedAt"] is None
            or fact["source"] is None
            or fact["clock"] is None
        ):
            raise ContractError("missing_evidence_provenance")
    if row["activity"]["at"] is not None and (
        row["activity"]["source"] is None or row["activity"]["health"] != "current"
    ):
        raise ContractError("missing_activity_provenance")
    if row["activity"].get("lastKnownAt") is not None and (
        row["activity"]["at"] is not None
        or row["activity"]["health"] != "stale"
        or row["activity"]["source"] is None
    ):
        raise ContractError("invalid_last_known_activity")
    for name in ("lastUpdated", "latestTurn"):
        record = row[name]
        key = "at" if name == "lastUpdated" else "value"
        known = "lastKnownAt" if name == "lastUpdated" else "lastKnownValue"
        if record["health"] == "current" and (record["source"] is None or record["observedAt"] is None):
            raise ContractError("missing_timing_provenance")
        if record["health"] == "current" and not sources[identity["provider"], identity["namespace"]]["capabilities"]["timing"][name]:
            raise ContractError("timing_capability_missing")
        if record["health"] != "current" and record[key] is not None:
            raise ContractError("invalid_current_timing")
        if known in record and (record["health"] != "stale" or record[key] is not None
                                or record[known] is None or record["source"] is None or record["observedAt"] is None):
            raise ContractError("invalid_last_known_timing")
        if name == "lastUpdated":
            if (record["at"] is None) != (record["timestampPrecisionMs"] is None):
                raise ContractError("timing_precision_conflict")
            if ("lastKnownAt" in record) != ("lastKnownTimestampPrecisionMs" in record) or (
                "lastKnownAt" in record and record["lastKnownTimestampPrecisionMs"] is None
            ):
                raise ContractError("timing_precision_conflict")
        else:
            for turn in (record["value"], record.get("lastKnownValue")):
                if turn is None:
                    continue
                start, end = turn["startedAt"], turn["completedAt"]
                if (start is not None and end is not None and end < start
                        or (start is None and end is None) != (turn["timestampPrecisionMs"] is None)
                        or turn["id"] == ""
                        or turn["status"] == "in_progress" and (end is not None or turn["durationMs"] is not None)):
                    raise ContractError("invalid_turn_timing")
        receipt = record["receipt"]
        if receipt is not None and (record["observedAt"] is None
                                   or receipt["observedBoottimeMs"] < receipt["sampledBoottimeMs"]):
            raise ContractError("invalid_timing_receipt")
    phase = row["phase"]
    if (row["runtime"]["value"] == "parked") != (phase is None):
        raise ContractError("parked_phase_conflict")
    if row["runtime"]["value"] == "parked" and not row["hasSavedHistory"]:
        raise ContractError("parked_without_saved_identity")
    if phase and phase["value"] != "unknown" and (
        row["runtime"]["value"] != "running"
        or phase["source"] != row["runtime"]["source"]
        or phase["observedAt"] != row["runtime"]["observedAt"]
        or phase["clock"] != row["runtime"]["clock"]
    ):
        raise ContractError("phase_runtime_conflict")
    reasons = row["blockedReasons"]
    if len(reasons) != len(set(reasons)):
        raise ContractError("duplicate_blocked_reason")
    if phase and phase["value"] == "blocked" and not reasons:
        raise ContractError("missing_blocked_reason")
    if (phase is None or phase["value"] != "blocked") and reasons:
        raise ContractError("unexpected_blocked_reason")
    return row


def validate_record(row, host_scope, sources):
    """Strict changed-row admission without validating or constructing a view.

    ``sources`` is an admitted source index keyed by (provider, namespace), or
    the equivalent source sequence. Source-wide namespace/capability validation
    remains the caller's responsibility; this checks every row cross-reference.
    """
    _SESSION_SHAPE(row)
    if isinstance(sources, dict):
        indexed = sources
    else:
        indexed = {}
        for source in sources:
            key = source["provider"], source["namespace"]
            if key in indexed:
                raise ContractError("duplicate_source")
            indexed[key] = source
    return _validate_record_semantics(row, host_scope, indexed)


def validate_snapshot(value):
    _SNAPSHOT_SHAPE(value)
    sources = {}
    for source in value["sources"]:
        key = source["provider"], source["namespace"]
        if key in sources:
            raise ContractError("duplicate_source")
        sources[key] = source
        if source["namespace"] != store_namespace(
            source["provider"], source["configHome"], source["configHomeKind"], value["host"]["uid"]
        ):
            raise ContractError("store_provenance_mismatch")
        if (
            not PurePosixPath(source["configHome"]).is_absolute()
            or ".." in PurePosixPath(source["configHome"]).parts
        ):
            raise ContractError("invalid_config_path")
        if source["coverage"]["runtime"]["scope"] != (
            "daemon_threads" if source["provider"] == "codex" else "provider_sessions"
        ):
            raise ContractError("runtime_scope_conflict")
        runtime_info = source["runtime"]
        if runtime_info is not None and source["provider"] == "codex" and runtime_info["topology"] != "native_managed_endpoint":
            raise ContractError("runtime_topology_conflict")
        for capability in ("phase", "blockedReasons", "runtime"):
            values = source["capabilities"][capability]
            if len(values) != len(set(values)):
                raise ContractError("duplicate_capability")
    seen = set()
    for row in value["sessions"]:
        identity = row["identity"]
        key = _admitted_identity_key(identity)
        if key in seen:
            raise ContractError("duplicate_native_identity")
        seen.add(key)
        _validate_record_semantics(row, value["host"]["authority"], sources)
    if value["collectedAt"] is None:
        raise ContractError("missing_collection_time")
    if len(canonical(value).encode()) > MAX_SNAPSHOT_BYTES:
        raise ContractError("snapshot_byte_limit")
    return value


def parse_snapshot(data):
    return validate_snapshot(decode_document(data, max_bytes=MAX_SNAPSHOT_BYTES, max_nodes=MAX_NODES))


def validate_watch(value):
    validate_shape(value, WATCH)
    if value["sampledAt"] is None or value["revision"] < 1:
        raise ContractError("invalid_watch_sequence")
    if value["kind"] in {"snapshot", "change", "resync"} and value["snapshot"] is None:
        raise ContractError("missing_watch_snapshot")
    if value["kind"] in {"gap", "heartbeat"} and value["snapshot"] is not None:
        raise ContractError("unexpected_watch_snapshot")
    if value["snapshot"] is not None:
        validate_snapshot(value["snapshot"])
    if len(canonical(value).encode()) > MAX_BYTES - 1:
        raise ContractError("watch_byte_limit")
    return value


def parse_watch(data):
    """Parse one newline-terminated public frame with the same producer bounds."""
    return validate_watch(decode_document(
        data, max_bytes=MAX_BYTES, max_nodes=MAX_NODES, line_framed=True
    ))


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    )


def store_namespace(provider, config_home, selector, uid):
    """Stable within host/store/path/UID; independent of runtime/boot incarnation."""
    return (
        "sha256:"
        + hashlib.sha256(canonical([provider, config_home, selector, uid]).encode()).hexdigest()
    )
