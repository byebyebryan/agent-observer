"""Synthetic malformed transport cases; no provider is invoked."""

import unittest

from agent_observer.bounded_json import WireError, decode_document


class BoundedJsonTest(unittest.TestCase):
    def assert_code(self, data, code, **limits):
        with self.assertRaisesRegex(WireError, "^" + code + "$"):
            decode_document(data, **limits)

    def test_valid_single_document(self):
        self.assertEqual(decode_document(b'{"id":1,"ok":true}'), {"id": 1, "ok": True})
        self.assertEqual(decode_document(b'{"id":1}\n', line_framed=True), {"id": 1})

    def test_duplicate_keys_rejected_at_any_depth(self):
        self.assert_code(b'{"id":1,"id":2}', "duplicate_key")
        self.assert_code(b'{"row":{"id":1,"id":2}}', "duplicate_key")

    def test_nonfinite_numbers_and_overflow_rejected(self):
        for data in (b"NaN", b"Infinity", b"-Infinity", b"1e9999"):
            self.assert_code(data, "nonfinite_number")
        self.assert_code(b"999999999999999999999", "integer_limit")

    def test_bad_encoding_and_multiple_documents_rejected_without_payload(self):
        self.assert_code(b"\xef\xbb\xbf{}", "invalid_encoding")
        self.assert_code(b'{"secret":"\xff"}', "invalid_json")
        self.assert_code(b'{"secret":"token"} {}', "invalid_json")
        self.assert_code(b"{}\x00", "invalid_encoding")

    def test_line_framing_is_explicit(self):
        for data in (b"{}", b"{}\n\n", b"{}\r\n", b"{\n}\n"):
            self.assert_code(data, "invalid_framing", line_framed=True)
        self.assertEqual(decode_document(b"{\n}"), {})

    def test_byte_depth_and_node_limits(self):
        self.assert_code(b"{}", "byte_limit", max_bytes=1)
        self.assert_code(b"[[[0]]]", "depth_limit", max_depth=2)
        self.assert_code(b"[0,1,2]", "node_limit", max_nodes=3)

    def test_invalid_limits_and_types_are_bounded(self):
        for changes in ({"max_bytes": True}, {"max_depth": 0}, {"max_nodes": -1}):
            self.assert_code(b"{}", "invalid_limit", **changes)
        self.assert_code("credential", "invalid_limit")
