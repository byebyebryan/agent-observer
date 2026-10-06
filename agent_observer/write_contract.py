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
    binarySha256=text(64, pattern=r"^[0-9a-f]{64}$"),
    settingsSha256=text(64, pattern=r"^[0-9a-f]{64}$", nullable=True),
    runtimeToken=text(64, pattern=r"^[0-9a-f]{64}$", nullable=True),
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
        reference["hostScope"] != value["hostScope"]
        or reference["provider"] != value["provider"]
        or reference["nativeIdKind"] != ("thread" if value["provider"] == "codex" else "session")
    ):
        raise ContractError("write_provenance_mismatch")
    return value


def validate_plan(value):
    from .contract import ContractError

    validate_shape(value, PLAN)
    request = validate_request(value["request"])
    routes = {
        ("codex", "new"): {"codex_new"},
        ("codex", "resume"): {"codex_resume"},
        ("claude", "new"): {"claude_new"},
        ("claude", "resume"): {"claude_attach", "claude_saved_resume"},
    }
    if value["route"] not in routes[request["provider"], request["operation"]]:
        raise ContractError("write_route_mismatch")
    if value["createdAt"] is None:
        raise ContractError("missing_plan_time")
    return value


def validate_result(value):
    from .contract import ContractError

    validate_shape(value, RESULT)
    requested, resulting = value["requestedIdentity"], value["resultingIdentity"]
    if (value["operation"] == "new") != (requested is None):
        raise ContractError("invalid_write_reference")
    for reference in (requested, resulting):
        if reference is not None and reference["nativeIdKind"] != (
            "thread" if reference["provider"] == "codex" else "session"
        ):
            raise ContractError("write_provenance_mismatch")
    if requested is not None and resulting is not None and any(
        requested[key] != resulting[key]
        for key in ("hostScope", "provider", "namespace", "nativeIdKind")
    ):
        raise ContractError("write_provenance_mismatch")
    if (
        requested is not None and resulting is not None
        and requested["provider"] == "codex" and requested != resulting
    ):
        raise ContractError("invalid_result_identity")
    if value["effect"] == "none" and resulting is not None:
        raise ContractError("invalid_result_identity")
    if value["effect"] == "confirmed" and (
        value["resultingIdentity"] is None or value["identityPending"]
    ):
        raise ContractError("missing_result_identity")
    if value["status"] == "prepared" and (value["effect"] != "none" or value["handoff"] is None):
        raise ContractError("invalid_prepared_result")
    if value["status"] == "ready" and (value["effect"] != "confirmed" or value["handoff"] is None):
        raise ContractError("invalid_ready_result")
    if value["effect"] == "uncertain" and (
        value["status"] != "uncertain" or value["handoff"] is not None
        or resulting is not None or not value["identityPending"]
    ):
        raise ContractError("invalid_uncertain_result")
    if value["handoff"] is not None:
        handoff = validate_plan(value["handoff"])
        if value["status"] == "prepared":
            if (
                handoff["request"]["operation"] != value["operation"]
                or handoff["request"]["reference"] != requested
                or handoff["route"] not in {"codex_new", "codex_resume", "claude_attach"}
                or value["identityPending"] != (value["operation"] == "new")
            ):
                raise ContractError("write_handoff_mismatch")
        elif value["status"] == "ready":
            if (
                handoff["route"] != "claude_attach"
                or handoff["request"]["reference"] != resulting
            ):
                raise ContractError("write_handoff_mismatch")
        else:
            raise ContractError("unexpected_write_handoff")
    if value["status"] == "rejected" and (
        value["effect"] != "none" or value["identityPending"]
    ):
        raise ContractError("invalid_rejected_result")
    if value["status"] == "uncertain" and value["effect"] == "none":
        raise ContractError("invalid_uncertain_result")
    return value


def schema_document(name):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:write-{name}:1",
        **{"request": REQUEST, "plan": PLAN, "result": RESULT}[name],
    }
