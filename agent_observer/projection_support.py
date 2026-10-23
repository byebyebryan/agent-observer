"""Shared pure projection schemas and original receipt/identity validation."""

from __future__ import annotations

from pathlib import PurePosixPath

from .contract import (
    CODE,
    DIGEST,
    IDENTITY,
    INTEGER,
    MAX_BYTES,
    MAX_SESSIONS,
    SESSION,
    UUID,
    ContractError,
    array,
    choice,
    identity_key,
    obj,
    store_namespace,
    text,
    validate_shape,
)
from .observation_support import support_matches as _support_matches

MAX_REQUEST_BYTES = 16 * 1024


MAX_OVERHEAD_BYTES = 16 * 1024


MAX_FRAME_BYTES = MAX_BYTES + MAX_OVERHEAD_BYTES


MAX_LEDGER_BYTES = 1024 * 1024


MAX_IDENTITIES = MAX_SESSIONS


POSITIVE_INTEGER = {**INTEGER, "minimum": 1}


FACT_SUPPORT = obj(
    serviceId=text(36, pattern=UUID),
    provider=choice("codex"),
    namespace=text(71, pattern=DIGEST),
    contextGeneration=INTEGER,
    component=choice("runtime", "history"),
    accepted=POSITIVE_INTEGER,
    sampledBoottimeMs=INTEGER,
    expiresBoottimeMs=INTEGER,
)


NULL_SUPPORT = {"anyOf": [FACT_SUPPORT, {"type": "null"}]}


FIELD_SUPPORTS = obj(**{
    name: NULL_SUPPORT for name in (
        "runtime", "phase", "kind", "savedIdentity", "activity", "outcome",
        "workspace", "lastUpdated", "latestTurn",
    )
})


MEMBER = obj(identity=IDENTITY, fieldSupports=FIELD_SUPPORTS)


UNCERTAIN = obj(
    identity=IDENTITY,
    reason=text(128, pattern=CODE),
    priorSupport=NULL_SUPPORT,
    support=NULL_SUPPORT,
    horizonBoottimeMs=INTEGER,
)


NONMEMBER = obj(
    identity=IDENTITY,
    reason=choice("parked", "excluded_kind"),
    value=choice("parked", "child", "system"),
    supports=array(FACT_SUPPORT, 2),
    horizonBoottimeMs=INTEGER,
)


SCOPE = obj(
    provider=choice("codex"),
    namespace=text(71, pattern=DIGEST),
    contextGeneration=INTEGER,
    continuity=POSITIVE_INTEGER,
    coverage=obj(
        status=choice("complete", "partial", "warming", "stale", "unavailable", "unsupported"),
        reason=text(128, pattern=CODE),
        supports=array(FACT_SUPPORT, 2),
    ),
    members=array(MEMBER, MAX_IDENTITIES),
    uncertain=array(UNCERTAIN, MAX_IDENTITIES),
    nonmembers=array(NONMEMBER, MAX_IDENTITIES),
)


PROJECTION = obj(scopes=array(SCOPE, 1), sessions=array(SESSION, MAX_SESSIONS))


def support_matches(support, source, service_id, now_ms=None):
    """Whether an original reference is the source's current usable receipt.

    A newer receipt at the same provider/component key never renews an old
    reference.  ``now_ms`` is owner boottime here; remote readers must use Mesh's
    translated receipt deadlines instead.
    """
    try:
        validate_shape(support, FACT_SUPPORT)
        if now_ms is not None and (type(now_ms) is not int or now_ms < 0):
            return False
        return (support["sampledBoottimeMs"] < support["expiresBoottimeMs"]
                and _support_matches(support, source, service_id=service_id, now_ms=now_ms))
    except (ContractError, KeyError, TypeError):
        return False


def _sources(value):
    result = {}
    for source in value["sources"]:
        provider = source["provider"]
        home = PurePosixPath(source["configHome"])
        if not home.is_absolute() or ".." in home.parts:
            raise ContractError("active_store_invalid")
        if provider != "codex" or provider in result or source["namespace"] != store_namespace(
            provider, source["configHome"], source["configHomeKind"], value["uid"],
        ):
            raise ContractError("active_source_invalid")
        components = {item["name"]: item for item in source["components"]}
        if len(source["components"]) != 2 or set(components) != {"runtime", "history"}:
            raise ContractError("active_components_invalid")
        for component in components.values():
            sample, expiry = component["sampledBoottimeMs"], component["expiresBoottimeMs"]
            if component["accepted"] > component["attempts"] or (sample is None) != (expiry is None):
                raise ContractError("active_receipt_invalid")
            if sample is not None and (sample > value["emittedBoottimeMs"] or expiry < sample):
                raise ContractError("active_clock_invalid")
            if component["health"] in {"current", "partial"} and (
                sample is None or expiry <= value["emittedBoottimeMs"] or component["accepted"] < 1
            ):
                raise ContractError("active_lease_expired")
        result[provider] = source
    if not result and value["kind"] != "error":
        raise ContractError("active_sources_missing")
    return result


def _support_scope(support, scope, value):
    if (support["serviceId"] != value["serviceId"]
            or support["provider"] != scope["provider"]
            or support["namespace"] != scope["namespace"]
            or support["contextGeneration"] > scope["contextGeneration"]):
        raise ContractError("active_support_scope")
    if (support["sampledBoottimeMs"] > value["emittedBoottimeMs"]
            or support["expiresBoottimeMs"] < support["sampledBoottimeMs"]):
        raise ContractError("active_support_clock")


def _current_support(support, source, scope, value):
    _support_scope(support, scope, value)
    if not support_matches(support, source, value["serviceId"], value["emittedBoottimeMs"]):
        raise ContractError("active_support_mismatch")


def _support_set(supports, source, scope, value, *, runtime=False):
    components = set()
    for support in supports:
        _current_support(support, source, scope, value)
        if support["component"] in components:
            raise ContractError("active_duplicate_support")
        components.add(support["component"])
    if runtime and "runtime" not in components:
        raise ContractError("active_runtime_support_missing")


def _identity(identity, scope, value):
    if (identity["hostScope"] != value["hostScope"]
            or identity["provider"] != scope["provider"]
            or identity["namespace"] != scope["namespace"]
            or identity["nativeIdKind"] != "thread"):
        raise ContractError("active_identity_scope")
    return identity_key(identity)

