"""Explicit compilation of the observation contract's small shape vocabulary.

This module has no dependency on ``contract``. Callers provide its finite error
type and ASCII-control expression, and choose when to compile a fixed schema.
Compilation snapshots the schema: later schema mutations require recompilation.
It does not replace semantic checks or the dynamic public shape interpreter.
"""

from __future__ import annotations

import copy
import re
import unicodedata

_MISSING = object()
_ATOM_TYPES = (str, int, bool, type(None))


def _enum_checker(values):
    atoms, others = {}, {}
    for value in values:
        kind = type(value)
        if kind in _ATOM_TYPES:
            atoms.setdefault(kind, set()).add(value)
        else:
            others.setdefault(kind, []).append(value)
    atoms = {kind: frozenset(items) for kind, items in atoms.items()}
    others = {kind: tuple(items) for kind, items in others.items()}

    def matches(value):
        kind = type(value)
        accepted = atoms.get(kind)
        if accepted is not None:
            return value in accepted
        # Complex enum members use the interpreter's typed, left-hand value
        # equality, including its behavior for NaN and unhashable JSON values.
        for item in others.get(kind, ()):
            if value == item:
                return True
        return False

    return matches


def _type_checker(kinds):
    exact, instances = [], []
    for kind in kinds:
        if kind == "null":
            exact.append(type(None))
        elif kind == "object":
            instances.append(dict)
        elif kind == "array":
            instances.append(list)
        elif kind == "string":
            instances.append(str)
        elif kind == "integer":
            exact.append(int)
        elif kind == "boolean":
            exact.append(bool)
    exact, instances = tuple(exact), tuple(instances)
    if not instances:
        return lambda value: type(value) in exact
    if not exact:
        return lambda value: isinstance(value, instances)
    return lambda value: type(value) in exact or isinstance(value, instances)


def _missing_items(_value):
    # An empty array does not inspect items in the dynamic interpreter.
    raise KeyError("items")


def compile_shape(spec, error_type, ascii_controls):
    """Return ``validate(value) -> None`` for a fixed finite shape schema.

    Preserve the current interpreter's branch order, defaults and error codes.
    ``anyOf`` returns immediately on success and ignores sibling constraints.
    Const/enum equality is typed at the outer value; dict/list/string types
    accept subclasses, while integer and boolean require their exact types.

    The input schema must use the interpreter's deliberately small, finite
    vocabulary. Capturing it is explicit and detached; mutating a public schema
    after compilation does not alter this callable. Unknown schema keywords
    remain ignored. Runtime validation neither mutates nor copies the value.
    """
    captured = copy.deepcopy(spec)
    memo, active = {}, set()
    control_search = ascii_controls.search
    category = unicodedata.category

    def compile_node(node):
        marker = id(node)
        if marker in memo:
            return memo[marker]
        if marker in active:
            raise ValueError("cyclic_contract_shape")
        active.add(marker)
        try:
            if "anyOf" in node:
                alternatives = tuple(compile_node(child) for child in node["anyOf"])

                def validate_any(value):
                    for alternative in alternatives:
                        try:
                            alternative(value)
                            return
                        except error_type:
                            pass
                    raise error_type("invalid_contract_shape")

                memo[marker] = validate_any
                return validate_any

            constant = node.get("const", _MISSING)
            constant_type = type(constant)
            enum_matches = _enum_checker(node["enum"]) if "enum" in node else None
            if "type" in node:
                kinds = node["type"]
                type_matches = _type_checker(kinds if isinstance(kinds, list) else (kinds,))
            else:
                type_matches = None
            properties = {
                name: compile_node(child) for name, child in node.get("properties", {}).items()
            }
            required = frozenset(node.get("required", ()))
            allowed = frozenset(properties)
            closed = node.get("additionalProperties") is False
            item_check = compile_node(node["items"]) if "items" in node else _missing_items
            max_items = node.get("maxItems", 4096)
            min_length, max_length = node.get("minLength", 0), node.get("maxLength", 4096)
            pattern = re.compile(node["pattern"], re.ASCII).fullmatch if "pattern" in node else None
            minimum, maximum = node.get("minimum", -(2**63)), node.get("maximum", 2**64 - 1)
            property_get = properties.get

            def validate(value):
                if constant is not _MISSING and (
                    type(value) is not constant_type or value != constant
                ):
                    raise error_type("schema_mismatch")
                if enum_matches is not None and not enum_matches(value):
                    raise error_type("invalid_contract_value")
                if type_matches is not None and not type_matches(value):
                    raise error_type("invalid_contract_type")
                if isinstance(value, dict):
                    if not required <= set(value) or (closed and not set(value) <= allowed):
                        raise error_type("invalid_contract_fields")
                    for key, item in value.items():
                        child = property_get(key)
                        if child is not None:
                            child(item)
                elif isinstance(value, list):
                    if len(value) > max_items:
                        raise error_type("contract_row_limit")
                    for item in value:
                        item_check(item)
                elif isinstance(value, str):
                    if not min_length <= len(value) <= max_length:
                        raise error_type("invalid_contract_text")
                    if str.isascii(value):
                        if control_search(value) is not None:
                            raise error_type("invalid_contract_text")
                    else:
                        for character in value:
                            if category(character).startswith("C"):
                                raise error_type("invalid_contract_text")
                    if pattern is not None and not pattern(value):
                        raise error_type("invalid_contract_text")
                elif type(value) is int:
                    if not minimum <= value <= maximum:
                        raise error_type("invalid_contract_number")

            memo[marker] = validate
            return validate
        finally:
            active.remove(marker)

    return compile_node(captured)
