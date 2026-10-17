"""Prepaid local compact schema interpreter; no Mesh or provider dependency.

Schema configuration belongs to one active plan, not an uncharged global cache.
The deliberately conservative load credit is included in the same caller budget
and is not a capacity/performance acceptance claim.
"""

from __future__ import annotations

import hashlib
import re
from importlib.resources import files

from .bounded_json import decode_document
from .contract import ContractError
from .sync_acquisition import _retire_failure

COMPACT_SCHEMA_DIGEST = "cad76406eceab62bb5ba982f3472258b0f604d05dc890a865c7cd2acb43fb23e"
_SCHEMA_BYTES = 256 * 1024
_SCHEMA_HEAP = 8 * 1024 * 1024


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def _check(condition):
    if not condition:
        raise ContractError("sync_compact_value_shape")


def _shape(value, spec, definitions):
    if type(spec) is bool:
        _check(spec)
        return
    if "$ref" in spec:
        name = spec["$ref"]
        _check(name.startswith("#/$defs/") and name[8:] in definitions)
        _shape(value, definitions[name[8:]], definitions)
        if len(spec) == 1:
            return
    if "anyOf" in spec:
        matched = False
        for candidate in spec["anyOf"]:
            try:
                _shape(value, candidate, definitions)
                matched = True
                break
            except ContractError:
                pass
        _check(matched)
    if "const" in spec:
        _check(_same(value, spec["const"]))
    if "enum" in spec:
        _check(any(_same(value, item) for item in spec["enum"]))
    if "type" in spec:
        kinds = spec["type"] if type(spec["type"]) is list else [spec["type"]]
        allowed = {"object": dict, "array": list, "string": str, "integer": int,
                   "boolean": bool, "null": type(None)}
        _check(any(type(value) is allowed.get(kind) for kind in kinds))
    if type(value) is dict:
        properties = spec.get("properties", {})
        _check(all(key in value for key in spec.get("required", ())))
        for key, child in value.items():
            _shape(child, properties.get(key, spec.get("additionalProperties", True)), definitions)
    elif type(value) is list:
        _check(spec.get("minItems", 0) <= len(value) <= spec.get("maxItems", 2**64))
        if spec.get("uniqueItems", False):
            _check(not any(_same(value[i], value[j]) for i in range(len(value)) for j in range(i)))
        prefix = spec.get("prefixItems", ())
        for index, child in enumerate(value):
            _shape(child, prefix[index] if index < len(prefix) else spec.get("items", True), definitions)
    elif type(value) is str:
        _check(spec.get("minLength", 0) <= len(value) <= spec.get("maxLength", 2**64))
        if "pattern" in spec:
            _check(re.search(spec["pattern"], value) is not None)
    elif type(value) is int:
        _check(spec.get("minimum", -(2**64)) <= value <= spec.get("maximum", 2**64))


class _ValueSchema:
    def __init__(self, document, credit):
        self._document, self._credit = document, credit

    def __call__(self, space, value, operation):
        _check(self._document is not None)
        definitions = self._document["$defs"]
        _shape(value, definitions[space + ("Operation" if operation else "Entry")], definitions)

    def close(self):
        self._document = None
        credit, self._credit = self._credit, None
        if credit is not None:
            credit.close()


def _load_value_schema(budget):
    credit = scratch = raw = document = None
    try:
        credit = budget.reserve(_SCHEMA_HEAP)
        scratch = budget.reserve(3 * _SCHEMA_BYTES, encoded=_SCHEMA_BYTES)
        raw = files("agent_observer").joinpath("contracts", "sync-compact-frame.schema.json").read_bytes()
        _check(len(raw) <= _SCHEMA_BYTES and hashlib.sha256(raw).hexdigest() == COMPACT_SCHEMA_DIGEST)
        document = decode_document(raw, max_bytes=_SCHEMA_BYTES, max_depth=64, max_nodes=32768)
        raw = None
        result = _ValueSchema(document, credit)
        document = credit = None
        return result
    except BaseException as error:
        _retire_failure(error)
        raw = document = budget = None
        if credit is not None:
            credit.close()
            credit = None
        raise error from None
    finally:
        raw = document = None
        if scratch is not None:
            scratch.close()
