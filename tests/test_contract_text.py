"""Pure validator text fast path preserves Unicode-category admission."""

import unicodedata
import unittest

from agent_observer.contract import ContractError, validate_shape


class ContractTextTests(unittest.TestCase):
    def test_scalar_and_union_types_preserve_exact_integer_boolean_admission(self):
        values = (None, {}, [], "text", 0, True, 1.0, (), b"text")
        kinds = ("null", "object", "array", "string", "integer", "boolean", "unsupported")
        predicates = {
            "null": lambda v: v is None, "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list), "string": lambda v: isinstance(v, str),
            "integer": lambda v: type(v) is int, "boolean": lambda v: type(v) is bool,
        }
        for kind in kinds:
            for value in values:
                for types in (kind, [kind], ["null", kind]):
                    expected = predicates.get(kind, lambda v: False)(value)
                    expected |= isinstance(types, list) and "null" in types and value is None
                    # An unconstrained array still needs an item schema.
                    spec = {"type": types, "items": {}}
                    with self.subTest(kind=types, value=value):
                        if expected:
                            validate_shape(value, spec)
                        else:
                            with self.assertRaisesRegex(ContractError, "invalid_contract_type"):
                                validate_shape(value, spec)

    def test_ascii_controls_and_printable_characters_match_unicode_oracle(self):
        for ordinal in range(128):
            value = "prefix" + chr(ordinal) + "suffix"
            with self.subTest(ordinal=ordinal):
                if unicodedata.category(chr(ordinal)).startswith("C"):
                    with self.assertRaisesRegex(ContractError, "invalid_contract_text"):
                        validate_shape(value, {"type": "string"})
                else:
                    validate_shape(value, {"type": "string"})

    def test_non_ascii_categories_and_boundaries_preserve_admission(self):
        for value in ("", "é", "汉字", "🙂", "a\u0301", "\u0085", "\u200d", "\ue000", "\ud800", "\u0378"):
            with self.subTest(value=ascii(value)):
                if any(unicodedata.category(char).startswith("C") for char in value):
                    with self.assertRaisesRegex(ContractError, "invalid_contract_text"):
                        validate_shape(value, {"type": "string"})
                else:
                    validate_shape(value, {"type": "string"})
        with self.assertRaisesRegex(ContractError, "invalid_contract_text"):
            validate_shape("x" * 17, {"type": "string", "maxLength": 16})
        with self.assertRaisesRegex(ContractError, "invalid_contract_text"):
            validate_shape("", {"type": "string", "minLength": 1})

    def test_subclass_cannot_spoof_ascii_classification(self):
        class Spoof(str):
            def isascii(self):
                return True

        with self.assertRaisesRegex(ContractError, "invalid_contract_text"):
            validate_shape(Spoof("\u200d"), {"type": "string"})


if __name__ == "__main__":
    unittest.main()
