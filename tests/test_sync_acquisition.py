"""Lexical acquisition tickets only; no Mesh, I/O or native acceptance."""

import copy
import gc
import json
import subprocess
import sys
import traceback
import unittest
import weakref
from unittest.mock import patch

from test_sync_native import baseline, control, head, transaction

from agent_observer import sync_acquisition
from agent_observer.bounded_json import WireError
from agent_observer.contract import ContractError
from agent_observer.sync_acquisition import (
    MAX_BINDING_BYTES,
    MAX_HEADER_HEAP_BYTES,
    MAX_KEY_BYTES,
    MAX_RECEIPT_BYTES,
    SCAN_SCRATCH_BYTES,
    parse_header,
)
from agent_observer.sync_native import MAX_HEAD_BYTES, MAX_MESSAGE_BYTES, TABLES, parse_message


class Budget:
    def __init__(self, maximum=MAX_HEADER_HEAP_BYTES):
        self.maximum = maximum
        self.used = self.peak = 0
        self.requests = []

    def reserve(self, amount, *, encoded=0):
        self.requests.append((amount, encoded))
        if encoded or self.used + amount > self.maximum:
            raise ContractError("fixture_heap_capacity")
        self.used += amount
        self.peak = max(self.peak, self.used)
        budget = self

        class Lease:
            closed = False

            def close(self):
                if not self.closed:
                    self.closed = True
                    budget.used -= amount

        return Lease()


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"


def opaque(raw_value, *, kind="baseline", group="metadata"):
    value = baseline() if kind == "baseline" else transaction()
    if kind == "baseline":
        value["tables"][group] = [["flood", "OPAQUE"]]
    else:
        value["operations"][group] = [["put", "flood", None, "OPAQUE"]]
    return wire(value).replace(b'"OPAQUE"', raw_value)


class SyncAcquisitionTest(unittest.TestCase):
    def assert_retired_failure(self, error):
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)
        for frame, _line in traceback.walk_tb(error.__traceback__):
            if frame.f_code.co_filename == sync_acquisition.__file__:
                if frame.f_code.co_name == "parse_header":
                    self.assertIsNone(frame.f_locals["raw"])
                    self.assertIsNone(frame.f_locals["budget"])
                else:
                    self.assertEqual(frame.f_locals, {})

    def test_import_is_mesh_provider_and_service_free(self):
        code = (
            "import sys;from agent_observer.sync_acquisition import parse_header;"
            "assert not any(name in sys.modules for name in "
            "['mesh_plus','agent_observer.collection','agent_observer.codex_snapshot',"
            "'agent_observer.service_runtime','agent_observer.observation_engine'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_small_structural_projections_both_views_and_all_families(self):
        for view in ("full", "active"):
            for make in (baseline, transaction, head, control):
                with self.subTest(view=view, kind=make.__name__):
                    value = make(view)
                    raw = wire(value)
                    budget = Budget()
                    with parse_header(raw, view, "fixture", budget=budget) as ticket:
                        self.assertEqual(ticket.document, parse_message(raw, view, "fixture"))
                        self.assertEqual(ticket.scanned_bytes, len(raw))
                        self.assertGreater(ticket.scanned_nodes, 1)
                        self.assertGreater(budget.used, 0)
                    self.assertEqual(budget.used, 0)
                    ticket.close()
                    with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                        _ = ticket.document

    def test_dense_three_megabyte_opaque_arrays_never_reach_json_loads(self):
        # Construct encoded data directly: no million-element fixture tree.
        count = 1_100_000
        dense = b"[" + b"[]," * (count - 1) + b"[]]"
        raw = opaque(dense)
        self.assertGreater(len(raw), 3 * 1024 * 1024)
        sizes, loads = [], json.loads

        def bounded_loads(value, *args, **kwargs):
            sizes.append(len(value))
            self.assertLess(len(value), 16384, "opaque body reached JSON decoder")
            return loads(value, *args, **kwargs)

        budget = Budget()
        with (
            patch("agent_observer.bounded_json.json.loads", bounded_loads),
            patch(
                "agent_observer.sync_acquisition.parse_message",
                side_effect=AssertionError("full parse"),
            ),
        ):
            ticket = parse_header(raw, "full", "fixture", budget=budget)
        with ticket:
            self.assertGreater(ticket.scanned_nodes, count)
            self.assertEqual(ticket.document["tables"]["metadata"], [])
            self.assertEqual(
                ticket.document["tables"]["receipts"], baseline()["tables"]["receipts"]
            )
            self.assertTrue(
                all(ticket.document["tables"][name] == [] for name in TABLES if name != "receipts")
            )
            self.assertLess(sum(sizes), 16384)
            self.assertLess(budget.peak, 4 * 1024 * 1024)
        self.assertEqual(budget.used, 0)
        self.assertEqual(budget.requests[0], (SCAN_SCRATCH_BYTES, 0))

    def test_transaction_payloads_are_opaque_and_operations_projection_is_empty(self):
        raw = opaque(
            b'{"nested":[[1,2,3],{"text":"caf\xc3\xa9 \xf0\x9f\x98\x80"}]}',
            kind="transaction",
            group="bodies",
        )
        with patch(
            "agent_observer.sync_acquisition.parse_message",
            side_effect=AssertionError("full parse"),
        ):
            with parse_header(raw, "full", "fixture") as ticket:
                self.assertEqual(ticket.document["operations"], dict.fromkeys(TABLES, []))
                self.assertEqual(ticket.document["resultTag"], transaction()["resultTag"])

    def test_invalid_opaque_grammar_integer_encoding_and_unicode_fail(self):
        cases = (
            b"[1,]",
            b'{"a" 1}',
            b'{"a":}',
            b"[truefalse]",
            b"--1",
            b"01",
            b"1.2",
            b"1e9",
            b"18446744073709551616",
            b"-9223372036854775809",
            b'"\\x"',
            b'"\\u123"',
            b'"\\ud800"',
            b'"\\udc00"',
            b'"\\ud800q"',
            b'"\xc0\xaf"',
            b'"\xed\xa0\x80"',
            b'"\xf4\x90\x80\x80"',
            b'"\x80"',
            b'"\xf0\x9f\x98"',
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ContractError):
                parse_header(opaque(value), "full", "fixture")
        for value in (
            b'"caf\xc3\xa9 \xf0\x9f\x98\x80"',
            b'"\\ud83d\\ude00"',
            b"-9223372036854775808",
            b"18446744073709551615",
        ):
            with self.subTest(value=value), parse_header(opaque(value), "full", "fixture"):
                pass

    def test_depth_and_node_limits_cover_opaque_values_and_object_keys(self):
        with parse_header(opaque(b"[" * 28 + b"0" + b"]" * 28), "full", "fixture"):
            pass
        with self.assertRaisesRegex(ContractError, "sync_ticket_structure_limit"):
            parse_header(opaque(b"[" * 29 + b"0" + b"]" * 29), "full", "fixture")
        raw = opaque(b'{"a":[1,2],"b":null}')
        with parse_header(raw, "full", "fixture") as ticket:
            count = ticket.scanned_nodes
        with patch("agent_observer.sync_acquisition.MAX_MESSAGE_NODES", count - 1):
            with self.assertRaisesRegex(ContractError, "sync_ticket_structure_limit"):
                parse_header(raw, "full", "fixture")
        with patch("agent_observer.sync_acquisition.MAX_MESSAGE_NODES", count):
            with parse_header(raw, "full", "fixture"):
                pass

    def test_closed_root_and_table_registries_reject_duplicates_and_unknown_keys(self):
        cases = []
        for make, name in ((baseline, "tables"), (transaction, "operations")):
            for alter in (
                lambda v, name=name: v[name].pop("records"),
                lambda v, name=name: v[name].update(other=[]),
                lambda v, name=name: v[name].update(records={}),
                lambda v: v.update(extra=True),
            ):
                value = make()
                alter(value)
                cases.append(wire(value))
            raw = wire(make())
            cases.append(raw.replace(b'"records":[]', b'"records":[],"records":[]'))
            cases.append(raw.replace(b'"records":[]', b'"records":[],"\\u0072ecords":[]'))
            cases.append(b'{"kind":"baseline",' + raw[1:])
        for raw in cases:
            with self.subTest(raw=raw[:100]), self.assertRaises(ContractError):
                parse_header(raw, "full", "fixture")

    def test_duplicate_opaque_object_keys_are_explicitly_deferred(self):
        raw = opaque(b'{"same":1,"same":2}')
        with parse_header(raw, "full", "fixture") as ticket:
            self.assertEqual(ticket.document["tables"]["metadata"], [])
        with self.assertRaises(WireError):
            parse_message(raw, "full", "fixture")

    def test_captured_byte_caps_reject_before_large_slice_or_json_allocation(self):
        sizes, loads = [], json.loads

        def key_only_loads(value, *args, **kwargs):
            sizes.append(len(value))
            self.assertLessEqual(len(value), MAX_KEY_BYTES, "oversized capture was decoded")
            return loads(value, *args, **kwargs)

        value = baseline()
        value["nativeBinding"] = "HEADER"
        too_large = wire(value).replace(b'"HEADER"', b'"' + b"x" * MAX_BINDING_BYTES + b'"')
        value = baseline()
        value["tables"]["receipts"] = "RECEIPTS"
        receipts = wire(value).replace(b'"RECEIPTS"', b"[" + b" " * MAX_RECEIPT_BYTES + b"]")
        for raw in (too_large, receipts):
            with patch("agent_observer.bounded_json.json.loads", key_only_loads):
                with self.assertRaisesRegex(ContractError, "sync_ticket_header_limit"):
                    parse_header(raw, "full", "fixture")
        self.assertTrue(sizes)

    def test_decode_heap_is_prepaid_and_all_failure_paths_release_scratch(self):
        value = baseline()
        value["nativeBinding"] = "HEADER"
        raw = wire(value).replace(b'"HEADER"', b"[" + b"0," * 127999 + b"0]")
        sizes, loads = [], json.loads

        def small_only(value, *args, **kwargs):
            sizes.append(len(value))
            self.assertLessEqual(len(value), MAX_KEY_BYTES)
            return loads(value, *args, **kwargs)

        budget = Budget()
        with patch("agent_observer.bounded_json.json.loads", small_only):
            with self.assertRaisesRegex(ContractError, "fixture_heap_capacity"):
                parse_header(raw, "full", "fixture", budget=budget)
        self.assertEqual(budget.used, 0)
        self.assertGreater(budget.requests[-1][0], MAX_HEADER_HEAP_BYTES)
        budget = Budget(SCAN_SCRATCH_BYTES)
        with self.assertRaisesRegex(ContractError, "fixture_heap_capacity"):
            parse_header(wire(baseline()), "full", "fixture", budget=budget)
        self.assertEqual(budget.used, 0)
        for raw in (opaque(b"[1,]"), wire({**baseline(), "tag": ["f" * 64, 1, "a" * 64]})):
            budget = Budget()
            with self.assertRaises(ContractError):
                parse_header(raw, "full", "fixture", budget=budget)
            self.assertEqual(budget.used, 0)

    def test_ticket_lifetime_holds_header_credit_and_fallback_releases_it(self):
        budget = Budget()
        first = parse_header(wire(baseline()), "full", "fixture", budget=budget)
        amount = budget.used
        second = parse_header(wire(transaction()), "full", "fixture", budget=budget)
        self.assertGreater(budget.used, amount)
        second.close()
        self.assertEqual(budget.used, amount)
        del first
        gc.collect()
        self.assertEqual(budget.used, 0)

    def test_saved_late_admission_error_retires_frames_and_body_references(self):
        class Probe:
            pass

        references = []
        scanner_init = sync_acquisition._Scanner.__init__

        def observed_scanner(scanner, raw):
            scanner_init(scanner, raw)
            references.append(weakref.ref(scanner))

        def fail_validation(document, *_args):
            probe = Probe()
            references.append(weakref.ref(probe))
            document["probe"] = probe
            raise ContractError("fixture_late_admission")

        raw = opaque(b'"' + b"x" * 65536 + b'"')
        before = sys.getrefcount(raw)
        budget = Budget()
        saved = None
        with (
            patch.object(sync_acquisition._Scanner, "__init__", observed_scanner),
            patch.object(sync_acquisition, "validate_message", fail_validation),
        ):
            try:
                parse_header(raw, "full", "fixture", budget=budget)
            except ContractError as error:
                saved = error
        self.assertEqual(saved.args, ("fixture_late_admission",))
        self.assertEqual(sys.getrefcount(raw), before)
        self.assertEqual(budget.used, 0)
        self.assertTrue(references)
        self.assertTrue(all(reference() is None for reference in references))
        self.assert_retired_failure(saved)

    def test_saved_header_decode_errors_keep_only_type_and_code(self):
        class Probe:
            pass

        original = sync_acquisition.decode_document
        raw = opaque(b'"' + b"x" * 65536 + b'"')
        for error_type in (ValueError, RecursionError, ContractError):
            references = []

            def fail_header(data, *, error_type=error_type, references=references, **kwargs):
                if len(data) > MAX_KEY_BYTES:
                    probe = Probe()
                    references.append(weakref.ref(probe))
                    try:
                        raise WireError("fixture_inner_decode")
                    except WireError:
                        raise error_type("fixture_header_decode") from None
                return original(data, **kwargs)

            budget = Budget()
            before = sys.getrefcount(raw)
            saved = None
            with patch.object(sync_acquisition, "decode_document", fail_header):
                try:
                    parse_header(raw, "full", "fixture", budget=budget)
                except error_type as error:
                    saved = error
            self.assertIs(type(saved), error_type)
            self.assertEqual(saved.args, ("fixture_header_decode",))
            self.assertEqual(sys.getrefcount(raw), before)
            self.assertEqual(budget.used, 0)
            self.assertTrue(all(reference() is None for reference in references))
            self.assert_retired_failure(saved)

    def test_explicit_ticket_close_keeps_work_counters_without_hidden_input(self):
        raw = opaque(b'"' + b"x" * 65536 + b'"')
        before = sys.getrefcount(raw)
        budget = Budget()
        ticket = parse_header(raw, "full", "fixture", budget=budget)
        counters = ticket.scanned_bytes, ticket.scanned_nodes
        self.assertEqual(sys.getrefcount(raw), before)
        ticket.close()
        self.assertEqual(sys.getrefcount(raw), before)
        self.assertEqual((ticket.scanned_bytes, ticket.scanned_nodes), counters)
        self.assertEqual(budget.used, 0)
        self.assertIsNone(ticket._document)
        self.assertIsNone(ticket._reservation)

    def test_small_head_control_and_original_receipt_validation_stays_strict(self):
        for make in (head, control):
            raw = wire(make())[:-1] + b" " * MAX_HEAD_BYTES + b"\n"
            with patch(
                "agent_observer.sync_acquisition.parse_message",
                side_effect=AssertionError("oversized decode"),
            ):
                with self.assertRaisesRegex(ContractError, "sync_ticket_header_limit"):
                    parse_header(raw, "full", "fixture")
        changes = (
            lambda v: v["tables"]["receipts"][0][1].update(
                serviceId="00000000-0000-4000-8000-000000000099"
            ),
            lambda v: v["tables"]["receipts"][0][1].update(contextGeneration=999),
            lambda v: v["tables"]["receipts"][0][1].update(expiresBoottimeMs=1),
            lambda v: v["tables"]["receipts"].append(copy.deepcopy(v["tables"]["receipts"][0])),
            lambda v: v["descriptor"].update(view="active"),
        )
        for alter in changes:
            value = baseline()
            alter(value)
            with self.subTest(alter=alter), self.assertRaises(ContractError):
                parse_header(wire(value), "full", "fixture")
        with self.assertRaisesRegex(ContractError, "sync_host_mismatch"):
            parse_header(wire(baseline()), "full", "foreign")
        value = transaction()
        value["resultTag"][1] += 1
        with self.assertRaises(ContractError):
            parse_header(wire(value), "full", "fixture")

    def test_input_framing_and_size_reject_before_reserving(self):
        raw = wire(baseline())
        budget = Budget()
        for value in (
            raw[:-1],
            raw + b"\n",
            raw[:-1] + b"\r\n",
            b"\xef\xbb\xbf" + raw,
            b"\0" + raw,
            b" " * (MAX_MESSAGE_BYTES + 1),
            bytearray(raw),
        ):
            with self.subTest(value_type=type(value)), self.assertRaises(ContractError):
                parse_header(value, "full", "fixture", budget=budget)
        self.assertEqual(budget.requests, [])
