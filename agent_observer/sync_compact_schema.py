"""Candidate compact wire schema; no route, encoding allocation or admission.

The separate encoding restores the exact existing logical native descriptor.
Its complete schema and fixed positions require counterpart compatibility review
before freeze. Old schemas and logical descriptor bytes remain unchanged.
"""

from __future__ import annotations

import copy

from .contract import HEALTH, IDENTITY, INTEGER, SNAPSHOT, SOURCE, TIME, TIMING_RECEIPT, obj
from .projection_support import FACT_SUPPORT, NONMEMBER, UNCERTAIN
from .projection_support import SCOPE as ACTIVE_SCOPE
from .service_contract import SOURCE as SERVICE_SOURCE
from .sync_contract import CONTENT, CURSOR, GENERATION, HEX, NATIVE_TAG
from .sync_native import COHORT, FRAME, NATIVE_BINDING, RECEIPT, RECEIPT_KEY, TABLES, descriptor
from .sync_projection_schema import FRAME as ACTIVE_FRAME

CANDIDATE_ENCODING_ID = "agent-observer.compact/1"
BODY_FIELDS = (
    "identity", "nativeIds", "title", "kind", "cwd", "cwdSource", "inventory",
    "hasSavedHistory", "phase", "runtime", "outcome", "blockedReasons", "createdAt",
    "activity", "lastUpdated", "latestTurn", "workspace", "metadataIssues",
)
SUPPORT_FIELDS = (
    "runtime", "phase", "kind", "savedIdentity", "activity", "outcome", "workspace",
    "lastUpdated", "latestTurn",
)
MOVED_FIELDS = ("runtime", "phase", "activity", "outcome", "lastUpdated", "latestTurn")
TIMING_FIELDS = ("component", "sampledBoottimeMs", "observedBoottimeMs", "contextGeneration")
SLOT_FIELDS = ("alias", "birthGeneration", "body", "orderGroup")
assert list(BODY_FIELDS) == CONTENT["required"]
assert list(TIMING_FIELDS) == TIMING_RECEIPT["anyOf"][0]["required"]

NULL = {"type": "null"}
U64 = {"type": "integer", "minimum": 0, "maximum": 2**64 - 1}
ALIAS = {**U64, "minimum": 1}
INDEX = {"type": "integer", "minimum": 0, "maximum": 31}
MASK = {"type": "integer", "minimum": 0, "maximum": 511}
IDENTITY_TUPLE = {"type": "array", "minItems": 5, "maxItems": 5,
                  "prefixItems": [IDENTITY["properties"][name] for name in IDENTITY["required"]],
                  "items": False}


def tuple_shape(*items):
    return {"type": "array", "minItems": len(items), "maxItems": len(items),
            "prefixItems": list(items), "items": False}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


def nullable(shape):
    return {"anyOf": [shape, NULL]}


def without(shape, names):
    result = copy.deepcopy(shape)
    for name in names:
        result["properties"].pop(name)
        result["required"].remove(name)
    return result


def _definitions():
    definitions = {
        "identity": IDENTITY_TUPLE,
        "recordRef": tuple_shape(ALIAS, {**GENERATION, "minimum": 1}),
        "groupSide": tuple_shape(INDEX, ALIAS, {**GENERATION, "minimum": 1}),
        "slot": tuple_shape(ALIAS, {**GENERATION, "minimum": 1}, HEX,
                            {"type": "integer", "minimum": 0, "maximum": 1}),
        "support": {"anyOf": [NULL, INDEX, tuple_shape({"const": "context"}, FACT_SUPPORT)]},
        "timing": nullable(tuple_shape(*(TIMING_RECEIPT["anyOf"][0]["properties"][name]
                                          for name in TIMING_FIELDS))),
        "receiptKey": RECEIPT_KEY,
        "receipt": RECEIPT,
        "cohort": tuple_shape(COHORT["properties"]["seal"],
                              COHORT["properties"]["accepted"],
                              COHORT["properties"]["sampledBoottimeMs"],
                              COHORT["properties"]["expiresBoottimeMs"]),
        "group": tuple_shape(ref("groupSide"), {**MASK, "minimum": 1}),
        "groupChange": {"anyOf": [
            tuple_shape(NULL, NULL, ref("groupSide"), {**MASK, "minimum": 1}),
            tuple_shape(ref("groupSide"), {**MASK, "minimum": 1}, NULL, {"const": 0}),
            tuple_shape(ref("groupSide"), {**MASK, "minimum": 1},
                        ref("groupSide"), {**MASK, "minimum": 1}),
        ]},
        "fullCoverage": obj(
            coverage=SOURCE["properties"]["coverage"],
            sourceHealth=SOURCE["properties"]["sourceHealth"], contextGeneration=INTEGER,
            supports=obj(runtime=nullable(FACT_SUPPORT), saved=nullable(FACT_SUPPORT)),
            censusStatus={"enum": ["complete", "partial", "warming", "stale", "unavailable", "unsupported"]},
        ),
        "activeCoverage": without(ACTIVE_SCOPE, ("members", "nonmembers", "uncertain")),
        "nonmember": NONMEMBER, "uncertain": UNCERTAIN,
        "scopeCoverageKey": tuple_shape(RECEIPT_KEY["prefixItems"][0],
                                        RECEIPT_KEY["prefixItems"][1], {"const": "coverage"}),
        "scopeMemberKey": tuple_shape({"const": "members"}, ref("recordRef")),
        "scopeNonmemberKey": tuple_shape(RECEIPT_KEY["prefixItems"][0],
                                         RECEIPT_KEY["prefixItems"][1],
                                         {"const": "nonmembers"}, ref("identity")),
        "scopeUncertainKey": tuple_shape(RECEIPT_KEY["prefixItems"][0],
                                         RECEIPT_KEY["prefixItems"][1],
                                         {"const": "uncertain"}, ref("identity")),
        "member": tuple_shape(*(nullable(INDEX) for _ in SUPPORT_FIELDS)),
    }
    definitions["body"] = tuple_shape(*(ref("recordRef") if name == "identity"
                                         else CONTENT["properties"][name] for name in BODY_FIELDS))
    definitions["moved"] = tuple_shape(
        tuple_shape(HEALTH, TIME), nullable(tuple_shape(HEALTH, TIME)), HEALTH, HEALTH,
        tuple_shape(HEALTH, TIME, ref("timing")), tuple_shape(HEALTH, TIME, ref("timing")),
    )
    definitions["observation"] = tuple_shape(ref("moved"), tuple_shape(*(ref("support") for _ in SUPPORT_FIELDS)))
    definitions["scopeKey"] = {"anyOf": [ref(f"scope{name}Key") for name in
                                          ("Coverage", "Member", "Nonmember", "Uncertain")]}
    service = obj(serviceId=NATIVE_BINDING["properties"]["ownerEpoch"],
                  bootId=NATIVE_BINDING["properties"]["bootId"], uid=INTEGER,
                  hostScope=IDENTITY["properties"]["hostScope"], viewRevision=INTEGER,
                  state={"enum": ["warming", "ready"]},
                  clockDomain=NATIVE_BINDING["properties"]["clockDomain"],
                  sources={"type": "array", "items": SERVICE_SOURCE, "maxItems": 2})
    projection = without(ACTIVE_FRAME["properties"]["projection"]["anyOf"][0], ("sessions", "scopes"))
    definitions["metadataValues"] = {
        "service": service, "snapshot": nullable(without(SNAPSHOT, ("sessions",))),
        "projection": nullable(projection),
        "scopeOrder": {"type": "array", "maxItems": 2, "items": tuple_shape(
            RECEIPT_KEY["prefixItems"][0], RECEIPT_KEY["prefixItems"][1])},
        "validationSources": {"type": "array", "maxItems": 2, "items": obj(
            provider=RECEIPT_KEY["prefixItems"][0], namespace=RECEIPT_KEY["prefixItems"][1],
            capabilities=obj(timing=SOURCE["properties"]["capabilities"]["properties"]["timing"]))},
    }
    return definitions


def _shapes(definitions):
    pairs = {
        "records": [(ref("identity"), ref("slot"))],
        "bodies": [(HEX, ref("body"))],
        "observations": [(ref("recordRef"), ref("observation"))],
        "receipts": [(ref("receiptKey"), ref("receipt"))],
        "cohorts": [(INDEX, ref("cohort"))],
        "scopes": [(ref("scopeCoverageKey"), {"anyOf": [ref("fullCoverage"), ref("activeCoverage")]}),
                   (ref("scopeMemberKey"), ref("member")),
                   (ref("scopeNonmemberKey"), ref("nonmember")),
                   (ref("scopeUncertainKey"), ref("uncertain"))],
        "metadata": [({"const": key}, value) for key, value in definitions.pop("metadataValues").items()],
    }
    for space, kinds in pairs.items():
        definitions[f"{space}Entry"] = {"anyOf": [tuple_shape(key, value) for key, value in kinds]}
        definitions[f"{space}Operation"] = {"anyOf": [
            shape for key, value in kinds for shape in (
                tuple_shape({"const": "put"}, key, nullable(HEX), value),
                tuple_shape({"const": "remove"}, key, HEX),
            )]}
    definitions["membershipsEntry"] = ref("group")
    definitions["membershipsOperation"] = ref("groupChange")
    return definitions


def schema_document():
    """Complete candidate schema, with all references self-contained."""
    definitions = _shapes(_definitions())
    definitions["value"] = {"anyOf": [NULL, {"type": "boolean"},
        {"type": "integer", "minimum": -(2**63), "maximum": 2**64 - 1},
        {"type": "string"}, {"type": "array", "items": ref("value")},
        {"type": "object", "additionalProperties": ref("value")}]}
    dictionaries = {"type": "array", "maxItems": 32, "uniqueItems": True, "items": ref("receiptKey")}
    receipt_refs = obj(before=copy.deepcopy(dictionaries), after=copy.deepcopy(dictionaries))
    baseline_refs = copy.deepcopy(receipt_refs)
    baseline_refs["properties"]["before"] = {"const": []}
    counts = dict.fromkeys(TABLES, 4096)
    counts.update(memberships=36864, receipts=32, cohorts=32, scopes=65536, metadata=65536)
    selected = {"anyOf": [{"const": descriptor(view)} for view in ("full", "active")]}
    baseline = obj(kind={"const": "baseline"}, descriptor=selected, nativeBinding=NATIVE_BINDING,
                   tag=NATIVE_TAG, cursor=CURSOR, receiptRefs=baseline_refs,
                   tables=obj(**{name: {"type": "array", "maxItems": counts[name],
                                       "items": ref(f"{name}Entry")} for name in TABLES}))
    transaction = obj(kind={"const": "transaction"}, descriptor=selected,
                      nativeBindingDigest=HEX, transactionId=HEX, baseTag=NATIVE_TAG,
                      resultTag=NATIVE_TAG, baseCursor=CURSOR, resultCursor=CURSOR,
                      receiptRefs=receipt_refs,
                      operations=obj(**{name: {"type": "array", "maxItems": counts[name] * 2,
                                              "items": ref(f"{name}Operation")} for name in TABLES}))
    return copy.deepcopy({"$schema": "https://json-schema.org/draft/2020-12/schema",
                          "$id": "urn:agent-observer:sync-compact-frame:1", "$defs": definitions,
                          "anyOf": [baseline, transaction, *FRAME["anyOf"][2:]]})


def value_schema(space, *, operation=False):
    document = schema_document()
    return {"$schema": document["$schema"], "$defs": document["$defs"],
            "$ref": f"#/$defs/{space}{'Operation' if operation else 'Entry'}"}
