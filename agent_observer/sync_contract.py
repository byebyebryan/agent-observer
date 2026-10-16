"""Pure sync requests and lossless API 4 record factorization.

Baseline/transaction table messages are intentionally defined by their own
reviewed contract. These helpers neither grant evidence authority nor perform
whole-view admission as a shortcut for changed-record validation.
"""

from __future__ import annotations

import copy

from .bounded_json import decode_document
from .contract import (
    HEALTH,
    INTEGER,
    SESSION,
    TIME,
    TIMING_RECEIPT,
    UUID,
    ContractError,
    choice,
    identity_key,
    obj,
    text,
    validate_shape,
)
from .contract import (
    validate_record as validate_record,
)
from .observation_support import SUPPORT_FIELDS

SYNC_PROTOCOL = "agent-observer.sync"
ACTIVE_SYNC_PROTOCOL = "agent-observer.active-sync"
SYNC_VERSION = 1
PROTOCOLS = (SYNC_PROTOCOL, ACTIVE_SYNC_PROTOCOL)
OPERATIONS = ("baseline", "changes", "head", "watch")
FIELD_NAMES = SUPPORT_FIELDS
MAX_REQUEST_BYTES = 16 * 1024
MAX_REQUEST_DEPTH = 10
MAX_REQUEST_NODES = 512
MAX_CHALLENGE_BYTES = 4096
MAX_CHALLENGE_DEPTH = 8
MAX_CHALLENGE_NODES = 256
MAX_TRANSACTIONS = 4
MAX_CHANGE_BYTES = 8 * 1024 * 1024
SAFE_INTEGER = 2**53 - 1
GENERATION = {"type": "integer", "minimum": 0, "maximum": 2**64 - 1}
HEX = text(64, pattern=r"^[0-9a-f]{64}$")

# Keep the generic item spec for the small pure validator; independent JSON
# Schema consumers additionally enforce the exact positional tuple types.
NATIVE_TAG = {
    "type": "array", "minItems": 3, "maxItems": 3,
    "items": {"anyOf": [HEX, GENERATION]},
    "prefixItems": [HEX, GENERATION, HEX],
}
CURSOR = {
    "type": "array", "minItems": 3, "maxItems": 3,
    "items": {"anyOf": [text(36, pattern=UUID), GENERATION, HEX]},
    "prefixItems": [text(36, pattern=UUID), GENERATION, HEX],
}
_JSON_REF = {"$ref": "#/$defs/challengeValue"}
_CHALLENGE = {"type": "object", "additionalProperties": _JSON_REF}
_COMMON = {
    "syncProtocol": choice(*PROTOCOLS), "version": {"const": SYNC_VERSION},
    "hostScope": copy.deepcopy(SESSION["properties"]["identity"]["properties"]["hostScope"]),
}
REQUEST = {"anyOf": [
    obj(**_COMMON, operation={"const": "baseline"}),
    obj(**_COMMON, operation={"const": "changes"}, baseTag=NATIVE_TAG, targetTag=NATIVE_TAG,
        maxTransactions={**INTEGER, "minimum": 1, "maximum": MAX_TRANSACTIONS},
        maxBytes={**INTEGER, "minimum": 1, "maximum": MAX_CHANGE_BYTES}),
    obj(**_COMMON, operation={"const": "head"}, challenge=_CHALLENGE),
    obj(**_COMMON, operation={"const": "watch"}, cursor=CURSOR),
]}

MOVED_PATHS = {
    "runtime": ("health", "observedAt"),
    "phase": ("health", "observedAt"),
    "activity": ("health",),
    "outcome": ("health",),
    "lastUpdated": ("health", "observedAt", "receipt"),
    "latestTurn": ("health", "observedAt", "receipt"),
}
CONTENT = copy.deepcopy(SESSION)
for _name, _paths in MOVED_PATHS.items():
    _spec = CONTENT["properties"][_name]
    if _name == "phase":
        _spec = _spec["anyOf"][0]
    for _path in _paths:
        _spec["properties"].pop(_path)
        _spec["required"].remove(_path)
OBSERVATIONS = obj(
    runtime=obj(health=HEALTH, observedAt=TIME),
    activity=obj(health=HEALTH),
    outcome=obj(health=HEALTH),
    lastUpdated=obj(health=HEALTH, observedAt=TIME, receipt=TIMING_RECEIPT),
    latestTurn=obj(health=HEALTH, observedAt=TIME, receipt=TIMING_RECEIPT),
)
# A null phase has no moved observation object. Missing and explicit null are
# deliberately distinct; the exact relationship is checked by join_record.
OBSERVATIONS["properties"]["phase"] = obj(health=HEALTH, observedAt=TIME)


def interface():
    return {
        "syncVersion": SYNC_VERSION, "protocols": list(PROTOCOLS),
        "operations": list(OPERATIONS), "observationApiVersion": 4,
        "fields": list(FIELD_NAMES), "hostLocal": True, "stability": "prerelease",
        "limits": {
            "requestBytes": MAX_REQUEST_BYTES, "challengeBytes": MAX_CHALLENGE_BYTES,
            "challengeDepth": MAX_CHALLENGE_DEPTH, "challengeNodes": MAX_CHALLENGE_NODES,
            "maxTransactions": MAX_TRANSACTIONS, "maxChangeBytes": MAX_CHANGE_BYTES,
        },
    }


def schema_document(kind="request"):
    if kind != "request":
        raise ContractError("sync_schema_kind")
    return copy.deepcopy({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:sync-request:{SYNC_VERSION}",
        "$defs": {"challengeValue": {"anyOf": [
            {"type": "null"}, {"type": "boolean"},
            {"type": "integer", "minimum": -SAFE_INTEGER, "maximum": SAFE_INTEGER},
            {"type": "string"}, {"type": "array", "items": _JSON_REF}, _CHALLENGE,
        ]}},
        **REQUEST,
    })


def _canonical(value):
    from .sync_commitment import canonical

    return canonical(value)


def _tuple(value, spec):
    if type(value) is not list or len(value) != 3:
        raise ContractError("sync_tuple_shape")
    for item, shape in zip(value, spec["prefixItems"], strict=True):
        validate_shape(item, shape)


def _challenge(value):
    seen, stack = 0, [(value, 0)]
    while stack:
        node, depth = stack.pop()
        seen += 1
        if depth > MAX_CHALLENGE_DEPTH or seen > MAX_CHALLENGE_NODES:
            raise ContractError("sync_challenge_limit")
        kind = type(node)
        if kind is dict:
            if any(type(key) is not str for key in node):
                raise ContractError("sync_challenge_type")
            seen += len(node)
            stack.extend((child, depth + 1) for child in node.values())
        elif kind is list:
            stack.extend((child, depth + 1) for child in node)
        elif kind is int:
            if not -SAFE_INTEGER <= node <= SAFE_INTEGER:
                raise ContractError("sync_challenge_integer")
        elif kind not in {str, bool, type(None)}:
            raise ContractError("sync_challenge_type")
        if seen > MAX_CHALLENGE_NODES:
            raise ContractError("sync_challenge_limit")
    if len(_canonical(value)) > MAX_CHALLENGE_BYTES:
        raise ContractError("sync_challenge_limit")


def validate_request(value, *, expected_host=None, expected_protocol=None):
    validate_shape(value, REQUEST)
    if expected_host is not None and value["hostScope"] != expected_host:
        raise ContractError("sync_host_mismatch")
    if expected_protocol is not None and value["syncProtocol"] != expected_protocol:
        raise ContractError("sync_protocol_mismatch")
    operation = value["operation"]
    if operation == "changes":
        _tuple(value["baseTag"], NATIVE_TAG)
        _tuple(value["targetTag"], NATIVE_TAG)
    elif operation == "watch":
        _tuple(value["cursor"], CURSOR)
    elif operation == "head":
        _challenge(value["challenge"])
    if len(_canonical(value)) + 1 > MAX_REQUEST_BYTES:
        raise ContractError("sync_request_limit")
    return value


def parse_request(data, *, expected_host=None, expected_protocol=None):
    return validate_request(decode_document(
        data, max_bytes=MAX_REQUEST_BYTES, max_depth=MAX_REQUEST_DEPTH,
        max_nodes=MAX_REQUEST_NODES, line_framed=True,
    ), expected_host=expected_host, expected_protocol=expected_protocol)


def split_record(row):
    """Detach exact stable content and the explicit moved observation paths.

    Structural validation is local. Use validate_record with admitted scope and
    source metadata to establish all joined native row semantics.
    """
    validate_shape(row, SESSION)
    content, observations = copy.deepcopy(row), {}
    for name, paths in MOVED_PATHS.items():
        if content[name] is None:
            continue
        observations[name] = {path: content[name].pop(path) for path in paths}
    return content, observations


def join_record(content, observations):
    """Strict, detached inverse; missing paths cannot silently become null."""
    validate_shape(content, CONTENT)
    validate_shape(observations, OBSERVATIONS)
    if (content["phase"] is None) != ("phase" not in observations):
        raise ContractError("sync_phase_observations")
    row = copy.deepcopy(content)
    for name in MOVED_PATHS:
        if name in observations:
            row[name].update(copy.deepcopy(observations[name]))
    return row


def admit_record(content, observations, host_scope, sources):
    """Admit one split native row with a single complete API 4 validation.

    The partition checks prevent either half from overriding fields owned by
    the other. The reconstructed row then passes the same strict shape and
    source-aware semantics as the ordinary public row contract.
    """
    if type(content) is not dict or type(observations) is not dict:
        raise ContractError("sync_record_partition")
    expected = set(MOVED_PATHS)
    if content.get("phase") is None:
        expected.remove("phase")
    if set(observations) != expected:
        raise ContractError("sync_record_partition")
    for name, paths in MOVED_PATHS.items():
        fact = content.get(name)
        if name == "phase" and fact is None:
            continue
        if (type(fact) is not dict or not set(paths).isdisjoint(fact)
                or type(observations[name]) is not dict
                or set(observations[name]) != set(paths)):
            raise ContractError("sync_record_partition")
    row = copy.deepcopy(content)
    for name, fact in observations.items():
        row[name].update(copy.deepcopy(fact))
    validate_record(row, host_scope, sources)
    return row, copy.deepcopy(_field_values(content))


def _field_values(content):
    return {
        "runtime": content["runtime"],
        "phase": None if content["phase"] is None else {
            "phase": content["phase"], "blockedReasons": content["blockedReasons"],
        },
        "kind": content["kind"],
        "savedIdentity": {"inventory": content["inventory"], "hasSavedHistory": content["hasSavedHistory"]},
        "activity": content["activity"], "outcome": content["outcome"],
        "workspace": {"workspace": content["workspace"], "cwd": content["cwd"], "cwdSource": content["cwdSource"]},
        "lastUpdated": content["lastUpdated"], "latestTurn": content["latestTurn"],
    }


def field_values(content):
    """The exact nine token inputs; observation health/clocks remain separate."""
    validate_shape(content, CONTENT)
    return copy.deepcopy(_field_values(content))


def field_value(content, name):
    if name not in FIELD_NAMES:
        raise ContractError("sync_field_unknown")
    validate_shape(content, CONTENT)
    return copy.deepcopy(_field_values(content)[name])


def field_tokens(descriptor_digest_hex, identity, birth, content):
    from .sync_commitment import field_token

    validate_shape(content, CONTENT)
    if type(identity) not in {list, tuple} or tuple(identity) != identity_key(content["identity"]):
        raise ContractError("sync_field_identity")
    if type(birth) not in {list, tuple} or len(birth) != 2:
        raise ContractError("sync_field_birth")
    validate_shape(birth[0], text(36, pattern=UUID))
    validate_shape(birth[1], GENERATION)
    return {name: field_token(descriptor_digest_hex, identity, birth, name, value)
            for name, value in _field_values(content).items()}
