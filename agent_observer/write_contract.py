"""Narrow first-party write-client contracts, independent of observation."""

from __future__ import annotations

from .contract import (
    BOOL,
    CODE,
    IDENTITY,
    INTEGER,
    PROVIDER,
    TIME,
    choice,
    obj,
    text,
    validate_shape,
)

REQUEST = obj(
    schemaVersion={"const": 1},
    operation=choice("new", "resume"),
    hostScope=IDENTITY["properties"]["hostScope"],
    provider=PROVIDER,
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
    binarySha256=text(64),
    settingsSha256=text(64, nullable=True),
    runtimeToken=text(64, nullable=True),
)
PLAN = obj(
    schemaVersion={"const": 1},
    request=REQUEST,
    guard=GUARD,
    route=choice("codex_new", "codex_resume", "claude_new", "claude_attach", "claude_saved_resume"),
    createdAt=TIME,
)
HANDOFF = {"anyOf": [PLAN, {"type": "null"}]}
RESULT = obj(
    schemaVersion={"const": 1},
    operation=choice("new", "resume"),
    status=choice("prepared", "ready", "rejected", "uncertain"),
    reason=text(128, pattern=CODE),
    effect=choice("none", "confirmed", "uncertain"),
    requestedIdentity={"anyOf": [IDENTITY, {"type": "null"}]},
    resultingIdentity={"anyOf": [IDENTITY, {"type": "null"}]},
    identityPending=BOOL,
    handoff=HANDOFF,
)


def validate_request(value):
    from .contract import ContractError

    validate_shape(value, REQUEST)
    reference = value["reference"]
    if (value["operation"] == "new") != (reference is None):
        raise ContractError("invalid_write_reference")
    if reference is not None and (
        reference["hostScope"] != value["hostScope"] or reference["provider"] != value["provider"]
    ):
        raise ContractError("write_provenance_mismatch")
    return value


def validate_plan(value):
    validate_shape(value, PLAN)
    validate_request(value["request"])
    return value


def validate_result(value):
    validate_shape(value, RESULT)
    if value["handoff"] is not None:
        validate_plan(value["handoff"])
    return value


def schema_document(name):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:write-{name}:1",
        **{"request": REQUEST, "plan": PLAN, "result": RESULT}[name],
    }
