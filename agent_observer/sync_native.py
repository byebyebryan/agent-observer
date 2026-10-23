"""Strict native sync envelopes; table/domain/root admission is independent.

Parsed messages are acquisition tickets, never admitted state capabilities.
Baseline and changed table entries still require the owner's domain callback
and the receiver's independently computed commitments before current use.
"""

from __future__ import annotations

import copy
import hashlib
from functools import lru_cache
from importlib.resources import files
from pathlib import PurePosixPath

from .bounded_json import decode_document
from .contract import (
    CODE,
    DIGEST,
    INTEGER,
    PROVIDER,
    RUNTIME_INFO,
    SCOPE,
    UUID,
    ContractError,
    array,
    choice,
    obj,
    store_namespace,
    text,
    validate_shape,
)
from .service_contract import COMPONENT
from .sync_commitment import canonical, native_binding_digest
from .sync_contract import (
    ACTIVE_SYNC_PROTOCOL,
    CURSOR,
    GENERATION,
    HEX,
    NATIVE_TAG,
    PROTOCOLS,
    SYNC_PROTOCOL,
    SYNC_VERSION,
    _challenge,
    _tuple,
)
from .sync_projection_schema import SELECTOR, SELECTOR_DIGEST

TABLES = ("records", "bodies", "observations", "memberships", "receipts", "cohorts", "scopes", "metadata")
COMMITMENT = "mesh.patricia-sha256/1"
MAX_MESSAGE_BYTES = 8 * 1024 * 1024 + 16 * 1024
MAX_FRAME_BYTES = MAX_MESSAGE_BYTES
MAX_MESSAGE_DEPTH = 32
MAX_MESSAGE_NODES = 2_000_000
MAX_HEAD_BYTES = 49_152
MAX_HEAD_FIXED_BYTES = 8192
MAX_HEAD_RECEIPT_BYTES = 768
MAX_HEAD_COHORT_BYTES = 384
MAX_CONTROL_BYTES = 16_384
MAX_RECEIPTS = 32
MAX_TABLE_ENTRIES = 65_536
MAX_MEMBERSHIPS = 9 * 4096
_JSON_REF = {"$ref": "#/$defs/value"}
_TIME_DOMAIN = text(128, pattern=r"^time:\[[0-9]+\]$")
_NULL = {"type": "null"}
_TABLE_LIMITS = {
    "records": 4096, "bodies": 4096, "observations": 4096,
    "memberships": MAX_MEMBERSHIPS, "receipts": MAX_RECEIPTS, "cohorts": MAX_RECEIPTS,
    "scopes": MAX_TABLE_ENTRIES, "metadata": MAX_TABLE_ENTRIES,
}
DESCRIPTOR = obj(
    protocol=choice(*PROTOCOLS), version={"const": SYNC_VERSION}, schemaDigest=HEX,
    commitment={"const": COMMITMENT}, view=choice("full", "active"),
    selectorDigest={"anyOf": [text(71, pattern=DIGEST), _NULL]},
    tables=array(choice(*TABLES), len(TABLES)),
)
SOURCE_CONTEXT = obj(
    provider=PROVIDER, namespace=text(71, pattern=DIGEST), configHome=text(),
    configHomeKind=choice("default", "explicit"), contextGeneration=INTEGER,
    runtimeContext=RUNTIME_INFO,
)
_CONTINUITY = {
    "type": "array", "minItems": 3, "maxItems": 3,
    "items": _JSON_REF,
    "prefixItems": [PROVIDER, text(71, pattern=DIGEST), {**GENERATION, "minimum": 1}],
}
NATIVE_BINDING = obj(
    ownerEpoch=text(36, pattern=UUID), bootId=text(36, pattern=UUID), clockDomain=_TIME_DOMAIN,
    uid=INTEGER, hostScope=text(256, pattern=SCOPE), protocol=choice(*PROTOCOLS),
    version={"const": SYNC_VERSION}, schemaDigest=HEX, view=choice("full", "active"),
    selector={"anyOf": [{"const": SELECTOR}, _NULL]},
    sourceContexts=array(SOURCE_CONTEXT, 2), scopeContinuity=array(_CONTINUITY, 2),
)
OWNER_CLOCK = obj(
    bootId=text(36, pattern=UUID), clockDomain=_TIME_DOMAIN, boottimeMs=INTEGER,
    ownerEpoch=text(36, pattern=UUID), uid=INTEGER, hostScope=text(256, pattern=SCOPE),
)
RECEIPT_KEY = {
    "type": "array", "minItems": 3, "maxItems": 3, "items": _JSON_REF,
    "prefixItems": [PROVIDER, text(71, pattern=DIGEST), choice("runtime", "history")],
}
RECEIPT = copy.deepcopy(COMPONENT)
RECEIPT["properties"].update(serviceId=text(36, pattern=UUID), contextGeneration=INTEGER)
RECEIPT["required"] = list(RECEIPT["properties"])
_SEAL = {
    "type": "array", "minItems": 3, "maxItems": 3, "items": _JSON_REF,
    "prefixItems": [GENERATION, HEX, {**INTEGER, "maximum": MAX_MEMBERSHIPS}],
}
COHORT = obj(
    receipt=RECEIPT_KEY, seal=_SEAL, accepted={**INTEGER, "minimum": 1},
    sampledBoottimeMs=INTEGER, expiresBoottimeMs=INTEGER,
)
HEAD_COHORT = copy.deepcopy(COHORT)
HEAD_COHORT["properties"].pop("receipt")
HEAD_COHORT["required"].remove("receipt")


def _pair(key=_JSON_REF, value=_JSON_REF):
    return {"type": "array", "minItems": 2, "maxItems": 2, "items": _JSON_REF,
            "prefixItems": [key, value]}


def _entry(space):
    if space == "receipts":
        return _pair(RECEIPT_KEY, RECEIPT)
    if space == "cohorts":
        return _pair(RECEIPT_KEY, COHORT)
    return _pair()


def _operation(space):
    entry = _entry(space)
    return {"anyOf": [
        {"type": "array", "minItems": 4, "maxItems": 4, "items": _JSON_REF,
         "prefixItems": [{"const": "put"}, entry["prefixItems"][0],
                         {"anyOf": [HEX, _NULL]}, entry["prefixItems"][1]]},
        {"type": "array", "minItems": 3, "maxItems": 3, "items": _JSON_REF,
         "prefixItems": [{"const": "remove"}, entry["prefixItems"][0], HEX]},
    ]}


FRAME = {"anyOf": [
    obj(kind={"const": "baseline"}, descriptor=DESCRIPTOR, nativeBinding=NATIVE_BINDING,
        tag=NATIVE_TAG, cursor=CURSOR,
        tables=obj(**{name: array(_entry(name), _TABLE_LIMITS[name]) for name in TABLES})),
    obj(kind={"const": "transaction"}, descriptor=DESCRIPTOR, nativeBindingDigest=HEX,
        transactionId=HEX, baseTag=NATIVE_TAG, resultTag=NATIVE_TAG,
        baseCursor=CURSOR, resultCursor=CURSOR,
        operations=obj(**{name: array(_operation(name), _TABLE_LIMITS[name] * 2) for name in TABLES})),
    obj(kind={"const": "head"}, descriptor=DESCRIPTOR, nativeBindingDigest=HEX,
        tag=NATIVE_TAG, challenge={"type": "object", "additionalProperties": _JSON_REF},
        ownerClock=OWNER_CLOCK, originalReceipts=array(_entry("receipts"), MAX_RECEIPTS),
        cohortHeads=array(_pair(RECEIPT_KEY, HEAD_COHORT), MAX_RECEIPTS),
        attenuation=array(_pair(RECEIPT_KEY, INTEGER), MAX_RECEIPTS)),
    obj(kind={"const": "control"}, descriptor=DESCRIPTOR,
        status=choice("complete", "baseline_required", "gap", "error", "heartbeat", "warming"),
        reason=text(128, pattern=CODE), tag={"anyOf": [NATIVE_TAG, _NULL]},
        cursor={"anyOf": [CURSOR, _NULL]}, ownerClock=OWNER_CLOCK),
]}
FRAME["anyOf"][-1]["properties"].update(baseTag=NATIVE_TAG, targetTag=NATIVE_TAG)

# The legacy small shape validator has no $ref resolver. Its private opaque
# value shape supplies array recursion; _json already enforces exact JSON
# types/cycles/depth/node limits. The public independent schema retains $refs.
_JSON_SHAPE = {
    "type": ["object", "array", "string", "integer", "boolean", "null"],
    "maxItems": MAX_MESSAGE_NODES, "maxLength": MAX_MESSAGE_BYTES,
    "minimum": -(2**63), "maximum": 2**64 - 1,
}
_JSON_SHAPE["items"] = _JSON_SHAPE


def _runtime_shape(value):
    if isinstance(value, dict):
        if "$ref" in value:
            return _JSON_SHAPE
        return {key: _runtime_shape(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_runtime_shape(child) for child in value]
    return value


_FRAME_SHAPE = _runtime_shape(FRAME)


def schema_document(kind="frame"):
    if kind != "frame":
        raise ContractError("sync_schema_kind")
    return copy.deepcopy({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:sync-frame:{SYNC_VERSION}",
        "$defs": {"value": {"anyOf": [
            {"type": "null"}, {"type": "boolean"},
            {"type": "integer", "minimum": -(2**63), "maximum": 2**64 - 1},
            {"type": "string"}, {"type": "array", "items": _JSON_REF},
            {"type": "object", "additionalProperties": _JSON_REF},
        ]}}, **FRAME,
    })


@lru_cache(maxsize=1)
def _schema_digest():
    raw = files("agent_observer").joinpath("contracts", "sync-frame.schema.json").read_bytes()
    return hashlib.sha256(raw).hexdigest()


def descriptor(view):
    if type(view) is not str or view not in {"full", "active"}:
        raise ContractError("sync_view")
    return {
        "protocol": SYNC_PROTOCOL if view == "full" else ACTIVE_SYNC_PROTOCOL,
        "version": SYNC_VERSION, "schemaDigest": _schema_digest(), "commitment": COMMITMENT,
        "view": view, "selectorDigest": None if view == "full" else SELECTOR_DIGEST,
        "tables": list(TABLES),
    }


def _json(value):
    seen, active, stack = 0, set(), [(value, 0, False)]
    while stack:
        item, depth, leave = stack.pop()
        if leave:
            active.remove(id(item))
            continue
        seen += 1
        if seen > MAX_MESSAGE_NODES or depth > MAX_MESSAGE_DEPTH:
            raise ContractError("sync_message_structure_limit")
        kind = type(item)
        if kind in {dict, list}:
            if id(item) in active:
                raise ContractError("sync_message_cycle")
            active.add(id(item))
            stack.append((item, depth, True))
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise ContractError("sync_message_json")
                seen += len(item)
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1, False) for child in children)
        elif kind is int:
            if not -(2**63) <= item <= 2**64 - 1:
                raise ContractError("sync_message_integer")
        elif kind not in {str, bool, type(None)}:
            raise ContractError("sync_message_json")
        if seen > MAX_MESSAGE_NODES:
            raise ContractError("sync_message_structure_limit")


def _entries(entries, space):
    result = {}
    for entry in entries:
        if type(entry) is not list or len(entry) != 2:
            raise ContractError("sync_entry_shape")
        key, value = entry
        encoded = canonical(key)
        if encoded in result:
            raise ContractError("sync_duplicate_key")
        if space == "receipts":
            _receipt(key, value)
        elif space == "cohorts":
            _cohort(key, value)
        elif space == "head_cohorts":
            validate_shape(value, HEAD_COHORT)
            _cohort(key, {**value, "receipt": key})
        result[encoded] = value
    return result


def _receipt(key, value):
    _tuple(key, RECEIPT_KEY)
    validate_shape(value, RECEIPT)
    sample, expiry = value["sampledBoottimeMs"], value["expiresBoottimeMs"]
    if (key[2] != value["name"]
            or (sample is None) != (expiry is None)
            or sample is not None and expiry < sample):
        raise ContractError("sync_receipt_shape")
    if value["health"] in {"current", "partial"} and (
        value["accepted"] < 1 or sample is None or expiry <= sample
    ):
        raise ContractError("sync_receipt_positive")


def _cohort(key, value):
    _tuple(key, RECEIPT_KEY)
    validate_shape(value, COHORT)
    _tuple(value["receipt"], RECEIPT_KEY)
    _tuple(value["seal"], _SEAL)
    if key != value["receipt"] or value["expiresBoottimeMs"] <= value["sampledBoottimeMs"]:
        raise ContractError("sync_cohort_shape")


def _cursor(tag, cursor, owner_epoch=None):
    _tuple(tag, NATIVE_TAG)
    _tuple(cursor, CURSOR)
    if cursor[1:] != tag[1:] or owner_epoch is not None and cursor[0] != owner_epoch:
        raise ContractError("sync_cursor_binding")


def _binding(binding, selected):
    if any(binding[name] != selected[name] for name in ("protocol", "version", "schemaDigest", "view")):
        raise ContractError("sync_native_descriptor")
    selector = None if selected["view"] == "full" else SELECTOR
    if canonical(binding["selector"]) != canonical(selector):
        raise ContractError("sync_selector_binding")
    sources = {}
    for source in binding["sourceContexts"]:
        key = source["provider"], source["namespace"]
        home = PurePosixPath(source["configHome"])
        if (key in sources or any(s[0] == key[0] for s in sources)
                or not home.is_absolute() or ".." in home.parts
                or source["namespace"] != store_namespace(
                    source["provider"], source["configHome"], source["configHomeKind"], binding["uid"],
                )):
            raise ContractError("sync_source_context")
        if selected["view"] == "active" and source["provider"] != "codex":
            raise ContractError("sync_source_context")
        sources[key] = source
    continuity = {}
    for entry in binding["scopeContinuity"]:
        _tuple(entry, _CONTINUITY)
        key = tuple(entry[:2])
        if key in continuity or key not in sources:
            raise ContractError("sync_scope_continuity")
        continuity[key] = entry[2]
    if (selected["view"] == "full" and continuity
            or selected["view"] == "active" and set(continuity) != set(sources)):
        raise ContractError("sync_scope_continuity")
    return sources


def _head(value):
    _tuple(value["tag"], NATIVE_TAG)
    if value["tag"][0] != value["nativeBindingDigest"]:
        raise ContractError("sync_tag_binding")
    _challenge(value["challenge"])
    receipts = _entries(value["originalReceipts"], "receipts")
    cohorts = _entries(value["cohortHeads"], "head_cohorts")
    attenuation = _entries(value["attenuation"], "attenuation")
    if set(attenuation) != set(receipts):
        raise ContractError("sync_attenuation_scope")
    for encoded, receipt in receipts.items():
        if receipt["serviceId"] != value["ownerClock"]["ownerEpoch"]:
            raise ContractError("sync_receipt_owner")
        if receipt["sampledBoottimeMs"] is not None and receipt["sampledBoottimeMs"] > value["ownerClock"]["boottimeMs"]:
            raise ContractError("sync_receipt_clock")
        remaining = (max(0, receipt["expiresBoottimeMs"] - value["ownerClock"]["boottimeMs"])
                     if receipt["health"] in {"current", "partial"} else 0)
        if type(attenuation[encoded]) is not int or attenuation[encoded] != remaining:
            raise ContractError("sync_attenuation_changed")
        if encoded in cohorts:
            cohort = cohorts[encoded]
            if any(cohort[key] != receipt[key] for key in (
                "accepted", "sampledBoottimeMs", "expiresBoottimeMs",
            )):
                raise ContractError("sync_cohort_support")
    if not set(cohorts) <= set(receipts):
        raise ContractError("sync_cohort_receipt")
    if any(len(canonical(entry)) + 1 > MAX_HEAD_RECEIPT_BYTES for entry in value["originalReceipts"]):
        raise ContractError("sync_head_receipt_limit")
    if any(len(canonical(entry)) + 1 > MAX_HEAD_COHORT_BYTES for entry in value["cohortHeads"]):
        raise ContractError("sync_head_cohort_limit")
    fixed = {**value, "originalReceipts": [], "cohortHeads": []}
    if len(canonical(fixed)) + 1 > MAX_HEAD_FIXED_BYTES:
        raise ContractError("sync_head_fixed_limit")


def validate_message(value, view, expected_host=None):
    _json(value)
    validate_shape(value, _FRAME_SHAPE)
    selected = descriptor(view)
    if canonical(value["descriptor"]) != canonical(selected):
        raise ContractError("sync_descriptor_binding")
    kind = value["kind"]
    if kind == "baseline":
        binding = value["nativeBinding"]
        sources = _binding(binding, selected)
        _cursor(value["tag"], value["cursor"], binding["ownerEpoch"])
        if value["tag"][0] != native_binding_digest(binding):
            raise ContractError("sync_tag_binding")
        for space in TABLES:
            _entries(value["tables"][space], space)
        for key, receipt in value["tables"]["receipts"]:
            source = sources.get(tuple(key[:2]))
            if (source is None or receipt["serviceId"] != binding["ownerEpoch"]
                    or receipt["contextGeneration"] != source["contextGeneration"]):
                raise ContractError("sync_receipt_owner")
        host = binding["hostScope"]
    elif kind == "transaction":
        _cursor(value["baseTag"], value["baseCursor"])
        _cursor(value["resultTag"], value["resultCursor"], value["baseCursor"][0])
        if (value["baseTag"][0] != value["nativeBindingDigest"]
                or value["resultTag"][0] != value["nativeBindingDigest"]
                or value["resultTag"][1] != value["baseTag"][1] + 1):
            raise ContractError("sync_transaction_binding")
        for space, operations in value["operations"].items():
            seen = set()
            for operation in operations:
                if (type(operation) is not list or not operation
                        or type(operation[0]) is not str or operation[0] not in {"put", "remove"}):
                    raise ContractError("sync_operation_shape")
                size = 4 if operation[0] == "put" else 3
                if len(operation) != size:
                    raise ContractError("sync_operation_shape")
                key = canonical(operation[1])
                if key in seen:
                    raise ContractError("sync_duplicate_operation")
                seen.add(key)
                validate_shape(operation[2], {"anyOf": [HEX, _NULL]} if size == 4 else HEX)
                if size == 4:
                    _entries([[operation[1], operation[3]]], space)
                elif space in {"receipts", "cohorts"}:
                    _tuple(operation[1], RECEIPT_KEY)
        host = None  # Bound to the admitted NativeBinding by the domain cache.
    elif kind == "head":
        _head(value)
        host = value["ownerClock"]["hostScope"]
    else:
        tag, cursor = value["tag"], value["cursor"]
        if (tag is None) != (cursor is None) or (
            value["status"] in {"complete", "heartbeat"} and tag is None
        ):
            raise ContractError("sync_control_binding")
        if tag is not None:
            _cursor(tag, cursor, value["ownerClock"]["ownerEpoch"])
        for name in ("baseTag", "targetTag"):
            if name in value:
                _tuple(value[name], NATIVE_TAG)
        host = value["ownerClock"]["hostScope"]
    if expected_host is not None and host is not None and host != expected_host:
        raise ContractError("sync_host_mismatch")
    limit = MAX_HEAD_BYTES if kind == "head" else MAX_CONTROL_BYTES if kind == "control" else MAX_MESSAGE_BYTES
    if len(canonical(value)) + 1 > limit:
        raise ContractError("sync_message_byte_limit")
    return value


def parse_message(raw, view, expected_host=None):
    return validate_message(decode_document(
        raw, max_bytes=MAX_MESSAGE_BYTES, max_depth=MAX_MESSAGE_DEPTH,
        max_nodes=MAX_MESSAGE_NODES, line_framed=True,
    ), view, expected_host)
