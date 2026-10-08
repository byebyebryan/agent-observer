"""Narrow first-party write-client contracts, independent of observation."""

from __future__ import annotations

from .contract import (
    BOOL,
    CODE,
    IDENTITY,
    INTEGER,
    TIME,
    choice,
    obj,
    text,
    validate_shape,
)

REQUEST = obj(
    schemaVersion={"const": 2},
    operation=choice("new", "resume"),
    hostScope=IDENTITY["properties"]["hostScope"],
    provider=choice("codex"),
    configHome=text(),
    configHomeKind=choice("default", "explicit"),
    cwd=text(),
    reference={"anyOf": [IDENTITY, {"type": "null"}]},
)
STAMP = obj(device=INTEGER, inode=INTEGER)
GUARD = obj(
    uid=INTEGER,
    cwd=STAMP,
    config=STAMP,
    binary=STAMP,
    binarySha256=text(64, pattern=r"^[0-9a-f]{64}$"),
    settingsSha256=text(64, pattern=r"^[0-9a-f]{64}$", nullable=True),
    runtimeToken=text(64, pattern=r"^[0-9a-f]{64}$", nullable=True),
)
PLAN = obj(
    schemaVersion={"const": 2},
    request=REQUEST,
    guard=GUARD,
    route=choice("codex_new", "codex_resume"),
    createdAt=TIME,
)
RESULT = obj(
    schemaVersion={"const": 2},
    operation=choice("new", "resume"),
    status=choice("prepared"),
    reason=text(128, pattern=CODE),
    effect=choice("none"),
    requestedIdentity={"anyOf": [IDENTITY, {"type": "null"}]},
    resultingIdentity={"type": "null"},
    identityPending=BOOL,
    handoff=PLAN,
)


def validate_request(value):
    from .contract import ContractError

    if isinstance(value, dict) and value.get("provider") == "claude":
        raise ContractError("unsupported_provider")
    validate_shape(value, REQUEST)
    reference = value["reference"]
    if (value["operation"] == "new") != (reference is None):
        raise ContractError("invalid_write_reference")
    if reference is not None and (
        reference["hostScope"] != value["hostScope"]
        or reference["provider"] != value["provider"]
        or reference["nativeIdKind"] != "thread"
    ):
        raise ContractError("write_provenance_mismatch")
    return value


def validate_plan(value):
    from .contract import ContractError

    validate_shape(value, PLAN)
    request = validate_request(value["request"])
    if value["route"] != "codex_" + request["operation"]:
        raise ContractError("write_route_mismatch")
    if value["createdAt"] is None:
        raise ContractError("missing_plan_time")
    return value


def validate_result(value):
    from .contract import ContractError

    validate_shape(value, RESULT)
    requested = value["requestedIdentity"]
    if (value["operation"] == "new") != (requested is None):
        raise ContractError("invalid_write_reference")
    handoff = validate_plan(value["handoff"])
    if (
        handoff["request"]["operation"] != value["operation"]
        or handoff["request"]["reference"] != requested
        or value["identityPending"] != (value["operation"] == "new")
    ):
        raise ContractError("write_handoff_mismatch")
    return value


def schema_document(name):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:write-{name}:2",
        **{"request": REQUEST, "plan": PLAN, "result": RESULT}[name],
    }
