"""Differential fixed-schema compilation against public shape admission."""

import copy
import gc
import json
import unittest
import weakref
from pathlib import Path

from agent_observer.contract import (
    ASCII_CONTROLS,
    SESSION,
    SNAPSHOT,
    ContractError,
    validate_shape,
)
from agent_observer.contract_shape import compile_shape

FIXTURES = Path(__file__).parent / "fixtures/contract-v6"


class DictChild(dict):
    pass


class ListChild(list):
    pass


class TextChild(str):
    def isascii(self):
        return True


class IntChild(int):
    pass


def _outcome(validate, value):
    try:
        result = validate(value)
    except Exception as error:
        return type(error), str(error)
    return result


def _paths(value, prefix=()):
    yield prefix, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _paths(child, (*prefix, index))


def _replaced(value, path, replacement):
    result = copy.deepcopy(value)
    if not path:
        return replacement
    parent = result
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    return result


def _enriched_row():
    row = json.loads((FIXTURES / "snapshot.json").read_text())["sessions"][0]
    row["workspace"] = {
        "health": "current",
        "reason": "native_workspace",
        "root": "/fixture",
        "rootKey": "fixture",
        "relativePath": "src",
        "projectKey": "fixture",
        "repo": {"root": "/fixture", "commonDir": "/fixture/.git", "relativePath": "src"},
    }
    receipt = {
        "component": "runtime",
        "sampledBoottimeMs": 1,
        "observedBoottimeMs": 2,
        "contextGeneration": 3,
    }
    row["lastUpdated"].update(
        receipt=receipt,
        lastKnownAt=1,
        lastKnownTimestampPrecisionMs=1,
    )
    turn = {
        "id": "native-turn",
        "status": "completed",
        "startedAt": 1,
        "completedAt": 2,
        "durationMs": 1,
        "timestampPrecisionMs": 1,
    }
    row["latestTurn"].update(value=turn, receipt=receipt, lastKnownValue=copy.deepcopy(turn))
    row["runtime"]["lastKnownValue"] = "running"
    row["outcome"]["lastKnownValue"] = "completed"
    row["activity"]["lastKnownAt"] = 1
    return row


class ContractShapeTests(unittest.TestCase):
    def test_dropped_compiled_shape_retires_without_cyclic_collection(self):
        enabled = gc.isenabled()
        gc.collect()
        gc.disable()
        try:
            compiled = compile_shape({"type": "object", "properties": {
                "items": {"type": "array", "items": {"type": "integer"}}}},
                ContractError, ASCII_CONTROLS)
            compiled({"items": [1, 2, 3]})
            reference = weakref.ref(compiled)
            del compiled
            self.assertIsNone(reference())
        finally:
            if enabled:
                gc.enable()

    def compare(self, spec, values):
        compiled = compile_shape(spec, ContractError, ASCII_CONTROLS)
        for value in values:
            with self.subTest(spec=spec, value=ascii(value)[:160]):
                self.assertEqual(
                    _outcome(compiled, value),
                    _outcome(lambda item: validate_shape(item, spec), value),
                )

    def test_all_pinned_snapshot_and_session_shapes_match(self):
        snapshot_check = compile_shape(SNAPSHOT, ContractError, ASCII_CONTROLS)
        session_check = compile_shape(SESSION, ContractError, ASCII_CONTROLS)
        for path in sorted(FIXTURES.glob("*.json")):
            snapshot = json.loads(path.read_text())
            if "sessions" not in snapshot:
                continue
            self.assertIsNone(validate_shape(snapshot, SNAPSHOT))
            self.assertIsNone(snapshot_check(snapshot))
            for row in snapshot["sessions"]:
                self.assertIsNone(session_check(row))
        self.assertIsNone(validate_shape(_enriched_row(), SESSION))
        self.assertIsNone(session_check(_enriched_row()))

    def test_session_and_snapshot_nested_scalar_mutants_match_exact_errors(self):
        row = _enriched_row()
        snapshot = json.loads((FIXTURES / "snapshot.json").read_text())
        snapshot["sessions"] = [row]
        snapshot["sources"] = snapshot["sources"][:1]
        replacements = (
            None,
            False,
            True,
            -1,
            0,
            1,
            1.0,
            -(2**63) - 1,
            2**64,
            "",
            "ordinary",
            "é🙂",
            "\u200d",
            "\n",
            [],
            {},
            (),
            b"text",
        )
        cases = 0
        for spec, original in ((SESSION, row), (SNAPSHOT, snapshot)):
            compiled = compile_shape(spec, ContractError, ASCII_CONTROLS)
            for path, _ in _paths(original):
                for replacement in replacements:
                    value = _replaced(original, path, replacement)
                    self.assertEqual(
                        _outcome(compiled, value),
                        _outcome(lambda item, schema=spec: validate_shape(item, schema), value),
                        (path, ascii(replacement)),
                    )
                    cases += 1
        self.assertGreater(cases, 4000)

    def test_closed_nested_objects_missing_required_and_extra_fields_match(self):
        row = _enriched_row()
        compiled = compile_shape(SESSION, ContractError, ASCII_CONTROLS)
        for path, item in _paths(row):
            if not isinstance(item, dict):
                continue
            changes = [dict(item, unexpected=True)]
            for key in item:
                changed = dict(item)
                del changed[key]
                changes.append(changed)
            for changed in changes:
                value = _replaced(row, path, changed)
                self.assertEqual(
                    _outcome(compiled, value),
                    _outcome(lambda item: validate_shape(item, SESSION), value),
                    (path, tuple(changed)),
                )

    def test_const_enum_are_typed_and_keep_interpreter_error_precedence(self):
        values = (
            None,
            False,
            True,
            0,
            1,
            1.0,
            "one",
            "",
            [],
            [True],
            [1],
            {},
            {"value": True},
            {"value": 1},
            TextChild("one"),
            IntChild(1),
        )
        for spec in (
            {"const": 1},
            {"const": True},
            {"const": [True]},
            {"const": {"value": True}},
            {"enum": [None, False, 1, "one"]},
            {"enum": [[True], {"value": True}]},
            {"enum": []},
            {"const": 1, "enum": [2], "type": "string"},
            {"enum": [1], "type": "boolean"},
        ):
            self.compare(spec, values)
        nan = float("nan")
        self.compare({"const": nan}, (nan, float("nan")))
        self.compare({"enum": [nan], "items": {}}, (nan, float("nan")))

    def test_anyof_returns_early_ignores_siblings_and_catches_only_contract_errors(self):
        self.compare(
            {
                "anyOf": [{"type": "integer"}, {"type": "string"}],
                "const": None,
                "maxLength": 0,
                "pattern": "[",
            },
            (1, "valid", True, {}, None, "\n"),
        )
        self.compare({"anyOf": []}, (None, 1, {}))
        # A missing array items schema raises KeyError, not ContractError;
        # anyOf must propagate it rather than trying its later alternative.
        self.compare({"anyOf": [{"type": "array"}, {}]}, ([], [1], None))

    def test_types_preserve_dict_list_string_subclasses_and_exact_integer_boolean(self):
        values = (
            None,
            {},
            DictChild(value=1),
            [],
            ListChild([1]),
            "text",
            TextChild("text"),
            0,
            True,
            IntChild(1),
            1.0,
            (),
            b"text",
        )
        for kind in ("null", "object", "array", "string", "integer", "boolean", "unknown"):
            for kinds in (kind, [kind], ["null", kind], ("null", kind)):
                self.compare({"type": kinds, "items": {}}, values)
        self.compare({"type": [], "items": {}}, values)
        self.compare({"items": {}}, values)

    def test_defaults_untyped_values_and_optional_unknown_fields_match(self):
        self.compare(
            {},
            (
                None,
                {},
                {"unknown": object()},
                [],
                "",
                "x" * 4096,
                "x" * 4097,
                -(2**63),
                -(2**63) - 1,
                2**64 - 1,
                2**64,
                True,
                IntChild(2**80),
                1.0,
                (),
                b"text",
            ),
        )
        self.compare({}, ([1],))  # Missing items is reached only for an element.
        self.compare({"items": {}}, ([], [None] * 4096, [None] * 4097))
        for additional in (None, True, False, 0, {}):
            self.compare(
                {
                    "type": "object",
                    "properties": {"known": {"type": "boolean"}},
                    "required": ["known", "known"],
                    "additionalProperties": additional,
                },
                ({}, {"known": True}, {"known": 1}, {"known": True, "unknown": []}),
            )

    def test_ascii_unicode_controls_lengths_and_ascii_regex_match(self):
        values = ["prefix" + chr(ordinal) + "suffix" for ordinal in range(128)]
        values.extend(
            (
                "",
                "é",
                "汉字",
                "🙂",
                "a\u0301",
                "\u0085",
                "\u200d",
                "\ue000",
                "\ud800",
                "\u0378",
                TextChild("\u200d"),
            )
        )
        for spec in (
            {"type": "string"},
            {"type": "string", "minLength": 1, "maxLength": 6},
            {"type": "string", "pattern": r"\w+"},
            {"type": "string", "pattern": r"^prefix.*suffix$"},
        ):
            self.compare(spec, values)

    def test_integer_boundaries_nullability_and_bool_noncoercion_match(self):
        values = (None, False, True, -1, 0, 1, 2, 3, 1.0, IntChild(1))
        self.compare({"type": ["integer", "null"], "minimum": 0, "maximum": 2}, values)
        self.compare({"type": "boolean", "minimum": 2}, values)
        self.compare({"minimum": 0, "maximum": 2}, values)

    def test_explicit_compilation_detaches_mutable_schema_invariants(self):
        spec = {
            "type": "object",
            "properties": {"value": {"enum": [[True]], "items": {}}},
            "required": ["value"],
            "additionalProperties": False,
        }
        compiled = compile_shape(spec, ContractError, ASCII_CONTROLS)
        original = {"value": [True]}
        compiled(original)
        spec["properties"]["value"]["enum"][0][0] = False
        spec["required"].append("new")
        spec["additionalProperties"] = True
        self.assertIsNone(compiled(original))
        with self.assertRaises(ContractError):
            validate_shape(original, spec)
        self.assertEqual(original, {"value": [True]})

    def test_supplied_error_type_and_control_matcher_need_no_contract_import(self):
        class LocalError(Exception):
            pass

        compiled = compile_shape({"type": "integer"}, LocalError, ASCII_CONTROLS)
        with self.assertRaisesRegex(LocalError, "invalid_contract_type"):
            compiled(True)
        compiled = compile_shape({"anyOf": [{"type": "integer"}]}, LocalError, ASCII_CONTROLS)
        with self.assertRaisesRegex(LocalError, "invalid_contract_shape"):
            compiled(False)

    def test_cyclic_schema_is_rejected_at_explicit_compilation(self):
        spec = {"type": "object"}
        spec["properties"] = {"child": spec}
        with self.assertRaisesRegex(ValueError, "cyclic_contract_shape"):
            compile_shape(spec, ContractError, ASCII_CONTROLS)


if __name__ == "__main__":
    unittest.main()
