"""Pure admission cases for the allocation refinement; no provider or Mesh IO."""

import unittest

from agent_observer.contract import ContractError, _matches_type, validate_shape


class ShapeDispatchTests(unittest.TestCase):
    def test_json_types_remain_distinct_and_unions_keep_ordered_admission(self):
        values = ((None, "null"), ({}, "object"), ([], "array"), ("x", "string"),
                  (1, "integer"), (True, "boolean"))
        for value, accepted in values:
            for _, kind in values:
                with self.subTest(value=value, kind=kind):
                    self.assertEqual(_matches_type(value, kind), kind == accepted)
            validate_shape(value, {"type": ["string", accepted]})
        for value in (False, 1.0, "1"):
            with self.assertRaisesRegex(ContractError, "invalid_contract_type"):
                validate_shape(value, {"type": "integer"})
        with self.assertRaisesRegex(ContractError, "invalid_contract_type"):
            validate_shape(None, {"type": []})

    def test_subclasses_and_malformed_specs_retain_legacy_behavior(self):
        class DictSubclass(dict):
            pass

        class IntSubclass(int):
            pass

        class StringSubclass(str):
            pass

        self.assertTrue(_matches_type(DictSubclass(), "object"))
        self.assertFalse(_matches_type(IntSubclass(1), "integer"))
        self.assertTrue(_matches_type("x", StringSubclass("string")))
        self.assertFalse(_matches_type(1, "unknown"))
        with self.assertRaises(TypeError):
            validate_shape(1, {"type": [[]]})

    def test_allocation_change_does_not_relax_non_type_checks(self):
        cases = (
            (True, {"const": 1}, "schema_mismatch"),
            (False, {"enum": [0]}, "invalid_contract_value"),
            (2, {"type": "integer", "maximum": 1}, "invalid_contract_number"),
            ("a\x00b", {"type": "string"}, "invalid_contract_text"),
            ("a\u202eb", {"type": "string"}, "invalid_contract_text"),
            ("12", {"type": "string", "pattern": "[a-z]+"}, "invalid_contract_text"),
            ("", {"type": "string", "minLength": 1}, "invalid_contract_text"),
            ({"extra": 1}, {"type": "object", "properties": {}, "additionalProperties": False}, "invalid_contract_fields"),
            ([], {"type": "object"}, "invalid_contract_type"),
            ([1, 2], {"type": "array", "items": {"type": "integer"}, "maxItems": 1}, "contract_row_limit"),
        )
        for value, spec, error in cases:
            with self.subTest(error=error, spec=spec):
                with self.assertRaisesRegex(ContractError, "^" + error + "$"):
                    validate_shape(value, spec)


if __name__ == "__main__":
    unittest.main()
