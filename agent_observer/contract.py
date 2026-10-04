"""Public v2 contract and bounded validation; no provider or action imports."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import PurePosixPath

from .bounded_json import decode_document

SCHEMA_VERSION = 2
MAX_BYTES = 8 * 1024 * 1024
UUID = r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$"
SCOPE = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$"
CODE = r"^[a-z][a-z0-9_]{0,127}$"
DIGEST = r"^sha256:[0-9a-f]{64}$"


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
PRESENCE = evidence("present", "absent")
RUNTIME = evidence("running", "parked")
OUTCOME = evidence("completed", "failed", "cancelled")
ATTACHMENT = evidence("attached", "detached")
COVERAGE = obj(
    status=choice("complete", "partial", "unavailable", "unsupported"),
    reason=text(128, pattern=CODE),
)
RUNTIME_COVERAGE = {
    **COVERAGE,
    "properties": {
        **COVERAGE["properties"],
        "scope": choice("loaded_threads", "registered_workers"),
    },
    "required": [*COVERAGE["required"], "scope"],
}
ACTIVITY = obj(
    at=TIME,
    source=text(128, pattern=CODE, nullable=True),
    health=HEALTH,
    reason=text(128, pattern=CODE),
)
RUNTIME_INFO = obj(
    version=text(64),
    binarySha256=text(64, pattern=r"^[0-9a-f]{64}$"),
    topology=choice("native_managed_endpoint", "private_session_registry_and_job_store"),
    bootId=text(36, pattern=UUID),
    pid={"type": ["integer", "null"], "minimum": 1},
    startTicks=TIME,
    endpoint=text(nullable=True),
)
RUNTIME_INFO = {"anyOf": [RUNTIME_INFO, {"type": "null"}]}
HISTORY = {
    "anyOf": [
        obj(
            source=choice("claude_sdk"),
            sdkVersion=choice("0.2.163"),
            createdAt=TIME,
            fileModifiedAt=TIME,
        ),
        {"type": "null"},
    ]
}
JOB = {
    "anyOf": [
        obj(
            id=text(8, pattern=r"^[0-9a-f]{8}$", nullable=True),
            retained={"type": ["boolean", "null"]},
            state=choice("working", "done", "failed", "stopped", "unknown"),
            tempo=choice("active", "blocked", "idle", "unknown"),
            terminalObservedAt=TIME,
        ),
        {"type": "null"},
    ]
}
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
SOURCE = obj(
    provider=PROVIDER,
    namespace=text(71, pattern=DIGEST),
    runtimeNamespace=text(71, pattern=DIGEST, nullable=True),
    configHome=text(),
    configHomeKind=choice("default", "explicit"),
    runtime=RUNTIME_INFO,
    sourceHealth=choice("current", "partial", "stale", "unavailable"),
    coverage=obj(saved=COVERAGE, runtime=RUNTIME_COVERAGE),
    capabilities=obj(
        phase=array(choice("working", "blocked", "waiting"), 3),
        blockedReasons=array(choice("approval", "question"), 2),
        runtime=array(choice("running", "parked"), 2),
        activity=BOOL,
        clientBinding=BOOL,
    ),
    errors=array(text(128, pattern=CODE), 128),
    limitations=array(text(128, pattern=CODE), 128),
)
SESSION = obj(
    identity=IDENTITY,
    nativeIds=obj(
        threadId=text(36, pattern=UUID, nullable=True),
        sessionId=text(36, pattern=UUID),
        jobId=text(8, pattern=r"^[0-9a-f]{8}$", nullable=True),
    ),
    title=text(256),
    kind=choice("user", "child", "unknown"),
    cwd=text(nullable=True),
    cwdSource=text(128, pattern=CODE, nullable=True),
    inventory=choice("live", "saved", "retained_job", "registry"),
    phase=PHASE,
    runtime=RUNTIME,
    worker=PRESENCE,
    attachment=ATTACHMENT,
    outcome=OUTCOME,
    blockedReason=choice("approval", "question", "unknown"),
    createdAt=TIME,
    activity=ACTIVITY,
    workspace=WORKSPACE,
    sessionKind=choice("interactive", "bg", "unknown"),
    job=JOB,
    history=HISTORY,
    metadataIssues=array(text(128, pattern=CODE), 128),
)
SNAPSHOT = obj(
    schemaVersion={"const": 2},
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
    sessions=array(SESSION, 4096),
    errors=array(text(128, pattern=CODE), 128),
    limitations=array(text(128, pattern=CODE), 128),
)
WATCH = obj(
    schemaVersion={"const": 2},
    streamId=text(36, pattern=UUID),
    revision=INTEGER,
    kind=choice("snapshot", "change", "heartbeat", "gap", "resync"),
    sampledAt=TIME,
    reason=text(128, pattern=CODE),
    snapshot={"anyOf": [SNAPSHOT, {"type": "null"}]},
)


class ContractError(ValueError):
    """Finite code; never includes input values or field contents."""


def schema_document(name):
    spec = {"snapshot": SNAPSHOT, "watch": WATCH}[name]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:{name}:2",
        **copy.deepcopy(spec),
    }


def _matches_type(value, kind):
    return {
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "boolean": type(value) is bool,
    }.get(kind, False)


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
        types = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
        if not any(_matches_type(value, kind) for kind in types):
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
        if not spec.get("minLength", 0) <= len(value) <= spec.get("maxLength", 4096) or any(
            unicodedata.category(c).startswith("C") for c in value
        ):
            raise ContractError("invalid_contract_text")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], value, re.ASCII):
            raise ContractError("invalid_contract_text")
    elif type(value) is int:
        if not spec.get("minimum", -(2**63)) <= value <= spec.get("maximum", 2**64 - 1):
            raise ContractError("invalid_contract_number")


def identity_key(identity):
    validate_shape(identity, IDENTITY)
    return tuple(identity[name] for name in IDENTITY["required"])


def validate_snapshot(value):
    validate_shape(value, SNAPSHOT)
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
    seen = set()
    for row in value["sessions"]:
        identity = row["identity"]
        key = identity_key(identity)
        if key in seen:
            raise ContractError("duplicate_native_identity")
        seen.add(key)
        if (
            identity["hostScope"] != value["host"]["authority"]
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
                or identity["nativeId"] != ids["threadId"]
                or ids["jobId"] is not None
            )
        ) or (
            identity["provider"] == "claude"
            and (
                identity["nativeIdKind"] != "session"
                or identity["nativeId"] != ids["sessionId"]
                or ids["threadId"] is not None
            )
        ):
            raise ContractError("native_identity_conflict")
        for dimension in ("phase", "runtime", "worker", "attachment", "outcome"):
            fact = row[dimension]
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
        if row["runtime"]["value"] == "parked" and row["phase"]["value"] != "unknown":
            raise ContractError("parked_phase_conflict")
        if row["phase"]["value"] == "blocked" and row["blockedReason"] == "unknown":
            raise ContractError("missing_blocked_reason")
    if value["collectedAt"] is None:
        raise ContractError("missing_collection_time")
    return value


def parse_snapshot(data):
    return validate_snapshot(decode_document(data, max_bytes=MAX_BYTES))


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
    return value


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
