"""Candidate compact A1 structural facade; no normalization/relay acceptance."""

import copy
import gc
import hashlib
import json
import subprocess
import sys
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

from test_sync_acquisition import Budget, wire
from test_sync_native import control, head

from agent_observer import sync_compact_acquisition, sync_transport
from agent_observer.contract import ContractError
from agent_observer.sync_acquisition import SCAN_SCRATCH_BYTES
from agent_observer.sync_commitment import descriptor_digest
from agent_observer.sync_compact_acquisition import (
    MAX_RECEIPT_REF_BYTES,
    CompactAgentSyncTransportCodec,
)
from agent_observer.sync_native import MAX_HEAD_BYTES, TABLES, descriptor
from agent_observer.sync_transport import AgentSyncTransportCodec

ROOT = Path(__file__).resolve().parents[1]


def codec(view="full", *, host="fixture"):
    # Unallocated fixture identity, supplied explicitly by trusted configuration.
    return CompactAgentSyncTransportCodec(view, encoding_id="fixture-compact/1", expected_host=host)


class SyncCompactTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "tests/fixtures/delta-sync/compact-raw-vectors.json").read_text())

    def baseline(self, view="full"):
        return copy.deepcopy(next(case["raw"] for case in self.fixture["baselines"]
                                  if case["name"] == f"{view}-running"))

    def detached(self, facade, raw, budget):
        ticket = facade.header(raw, budget)
        lease = budget.reserve(ticket.header.materialization_bytes)
        try:
            return ticket.header.materialize()
        finally:
            ticket.close()
            lease.close()

    def test_pure_import_and_only_structural_role_surface(self):
        script = (
            "import sys;from agent_observer.sync_compact_acquisition import CompactAgentSyncTransportCodec;"
            "assert not any(name in sys.modules for name in ['mesh_plus',"
            "'agent_observer.service_runtime','agent_observer.observation_engine',"
            "'agent_observer.collection','agent_observer.codex_snapshot'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        facade = codec()
        for name in ("spec", "open", "entries", "operations", "check_head", "restore", "profile", "acquire"):
            self.assertFalse(hasattr(facade, name), name)

    def test_explicit_immutable_candidate_schema_and_same_logical_descriptor(self):
        digest = hashlib.sha256((ROOT / "agent_observer/contracts/sync-compact-frame.schema.json").read_bytes()).hexdigest()
        for view in ("full", "active"):
            facade = codec(view)
            self.assertEqual(dict(facade.encoding), {
                "id": "fixture-compact/1", "schema": digest,
                "nativeDescriptor": descriptor_digest(descriptor(view)),
            })
            with self.assertRaises((TypeError, AttributeError)):
                facade.encoding["schema"] = "f" * 64
            with self.assertRaises(AttributeError):
                facade._view = "other"

    def test_all_eight_baseline_and_ten_transaction_headers_match_logical_projection(self):
        for case in self.fixture["baselines"] + self.fixture["transactions"]:
            message = case["raw"]
            view = message["descriptor"]["view"]
            budget, raw = Budget(), wire(message)
            before = sys.getrefcount(raw)
            ticket = codec(view).header(raw, budget)
            self.assertEqual(sys.getrefcount(raw), before)
            header = ticket.header
            lease = budget.reserve(header.materialization_bytes)
            document = header.materialize()
            expected = {k: v for k, v in message.items() if k not in {"receiptRefs", "tables", "operations"}}
            group = "tables" if message["kind"] == "baseline" else "operations"
            expected[group] = {name: message[group][name] if group == "tables" and name == "receipts" else []
                               for name in TABLES}
            self.assertEqual(document, expected)
            self.assertNotIn("receiptRefs", document)
            ticket.close()
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                header.materialize()
            document = None
            lease.close()
            self.assertEqual(budget.used, 0)

    def test_material_values_and_reference_semantics_are_not_admitted_by_relay(self):
        value = self.baseline()
        value["tables"]["bodies"][0][1][2] = "OPAQUE"
        raw = wire(value).replace(b'"OPAQUE"', b'{"same":1,"same":2,"body":"' + b"x" * 262144 + b'"}')
        sizes, loads = [], json.loads

        def bounded(data, *args, **kwargs):
            sizes.append(len(data))
            self.assertLess(len(data), 16384)
            return loads(data, *args, **kwargs)

        budget = Budget()
        with patch("agent_observer.bounded_json.json.loads", bounded):
            projected = self.detached(codec(), raw, budget)
        self.assertEqual(projected["tables"]["bodies"], [])
        self.assertTrue(sizes)
        self.assertEqual(budget.used, 0)
        # Exact existence is a Reader before/provisional-state check. A relay
        # has no semantic cache with which to resolve even a syntactic ref.
        value = self.baseline()
        value["receiptRefs"]["after"].append(["codex", "sha256:" + "f" * 64, "history"])
        self.detached(codec(), wire(value), budget)
        self.assertEqual(budget.used, 0)

    def test_dictionary_syntax_duplicates_bounds_and_baseline_before_reject(self):
        mutations = (
            lambda value: value["receiptRefs"].update(other=[]),
            lambda value: value["receiptRefs"].update(before=value["receiptRefs"]["after"][:1]),
            lambda value: value["receiptRefs"]["after"].append(value["receiptRefs"]["after"][0]),
            lambda value: value["receiptRefs"].update(after=value["receiptRefs"]["after"] * 17),
            lambda value: value["receiptRefs"].update(after=[True]),
            lambda value: value["receiptRefs"]["after"][0].__setitem__(0, True),
            lambda value: value["receiptRefs"]["after"][0].__setitem__(1, "bad-namespace"),
            lambda value: value["receiptRefs"]["after"][0].__setitem__(2, "unknown"),
            lambda value: value.update(kind=[]),
        )
        for mutation in mutations:
            value, budget = self.baseline(), Budget()
            mutation(value)
            with self.assertRaises(ContractError):
                codec().header(wire(value), budget)
            self.assertEqual(budget.used, 0)

    def test_explicit_encoding_routes_never_sniff_or_fallback(self):
        raw, budget = wire(self.baseline()), Budget()
        with self.assertRaisesRegex(ContractError, "sync_ticket_fields"):
            AgentSyncTransportCodec("full", encoding_id="fixture-expanded/1").header(raw, budget)
        value = self.baseline()
        value.pop("receiptRefs")
        with self.assertRaisesRegex(ContractError, "sync_ticket_fields"):
            codec().header(wire(value), budget)
        with self.assertRaises(ContractError):
            codec("active").header(raw, budget)
        with self.assertRaisesRegex(ContractError, "sync_host_mismatch"):
            codec(host="other").header(raw, budget)
        self.assertEqual(budget.used, 0)

    def test_bounded_dictionary_rejection_precedes_header_payload_decode(self):
        raw = wire(self.baseline()).replace(b'"receiptRefs":{', b'"receiptRefs":{' + b" " * MAX_RECEIPT_REF_BYTES)
        loads, sizes = json.loads, []

        def bounded(data, *args, **kwargs):
            sizes.append(len(data))
            self.assertLess(len(data), 16384)
            return loads(data, *args, **kwargs)

        budget = Budget()
        with patch("agent_observer.bounded_json.json.loads", bounded):
            with self.assertRaisesRegex(ContractError, "sync_ticket_header_limit"):
                codec().header(raw, budget)
        self.assertTrue(sizes)
        self.assertEqual(budget.used, 0)

    def test_two_maximum_fully_escaped_dictionaries_fit_existing_header_bound(self):
        value = copy.deepcopy(self.fixture["transactions"][0]["raw"])
        keys = [["codex", "sha256:" + f"{index:064x}", "runtime"] for index in range(32)]
        refs = value["receiptRefs"] = {"before": keys, "after": keys[::-1]}
        plain = wire(refs)[:-1]
        escaped = bytearray()
        quoted = False
        for char in plain:
            if char == 34:
                quoted = not quoted
                escaped.append(char)
            elif quoted:
                escaped.extend(f"\\u{char:04x}".encode())
            else:
                escaped.append(char)
        self.assertLess(len(escaped), MAX_RECEIPT_REF_BYTES)
        raw = wire(value).replace(plain, escaped)
        budget = Budget()
        document = self.detached(codec(value["descriptor"]["view"]), raw, budget)
        self.assertEqual(document["operations"], dict.fromkeys(TABLES, []))
        self.assertEqual(budget.used, 0)

    def test_prepaid_scan_refusal_before_compact_scanner_construction(self):
        budget = Budget(sync_transport._CONTROL_HEAP + SCAN_SCRATCH_BYTES - 1)
        with patch.object(sync_compact_acquisition._CompactScanner, "__init__", side_effect=AssertionError("unpaid")):
            with self.assertRaisesRegex(ContractError, "fixture_heap_capacity"):
                codec().header(wire(self.baseline()), budget)
        self.assertEqual(budget.used, 0)

    def test_head_path_keeps_original_bytes_and_never_constructs_compact_scanner(self):
        for view in ("full", "active"):
            for make in (head, control):
                budget = Budget()
                with patch.object(sync_compact_acquisition._CompactScanner, "__init__", side_effect=AssertionError("material scanner")):
                    ticket = codec(view).head(wire(make(view)), budget)
                    lease = budget.reserve(ticket.header.materialization_bytes)
                    document = ticket.header.materialize()
                    self.assertEqual(document, make(view))
                    ticket.close()
                    document = None
                    lease.close()
                self.assertEqual(budget.used, 0)
        for raw in (wire(self.baseline()), b"x" * (MAX_HEAD_BYTES + 1)):
            budget = Budget()
            with self.assertRaises(ContractError):
                codec().head(raw, budget)
            self.assertEqual(budget.used, 0)

    def test_close_revokes_immediately_with_header_credit_through_copy_unwind(self):
        budget = Budget()
        ticket = codec().header(wire(self.baseline()), budget)
        header = ticket.header
        cost = header.materialization_bytes
        lease = budget.reserve(cost)
        held, clone = budget.used, copy.deepcopy

        def retire(document):
            ticket.close()
            self.assertEqual(budget.used, held)
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                header.materialize()
            return clone(document)

        with patch.object(sync_transport.copy, "deepcopy", retire):
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                header.materialize()
        self.assertEqual(budget.used, cost)
        lease.close()
        self.assertEqual(budget.used, 0)

    def test_failure_frames_retire_scanner_with_gc_disabled_and_error_retained(self):
        enabled, refs, errors = gc.isenabled(), [], []
        gc.disable()
        try:
            class GuardedBudget(Budget):
                def reserve(self, amount, *, encoded=0):
                    lease = super().reserve(amount, encoded=encoded)

                    class GuardedLease:
                        def close(inner):
                            self_case.assertTrue(all(ref() is None for ref in refs),
                                                 "failed scanner still live at actual credit refund")
                            lease.close()

                    return GuardedLease()

            self_case, scan = self, sync_compact_acquisition._CompactScanner.scan
            for fail_scan in (True, False):
                def observe(scanner, fail_scan=fail_scan):
                    refs.append(weakref.ref(scanner))
                    if fail_scan:
                        raise ContractError("fixture_compact_scan_failed")
                    scan(scanner)

                value, budget = self.baseline(), GuardedBudget()
                value["receiptRefs"]["after"].append(value["receiptRefs"]["after"][0])
                with patch.object(sync_compact_acquisition._CompactScanner, "scan", observe):
                    try:
                        codec().header(wire(value), budget)
                    except ContractError as error:
                        errors.append(error)  # Retain the real traceback, without assertRaises clearing it.
                    else:
                        self.fail("expected failure")
                self.assertTrue(all(ref() is None for ref in refs))
                self.assertIsNone(errors[-1].__context__)
                self.assertEqual(budget.used, 0)
            self.assertEqual(len(errors), 2)
        finally:
            if enabled:
                gc.enable()

    def test_shared_budget_ticket_retirement_preserves_sibling_and_its_copy(self):
        budget = Budget()
        first = codec().header(wire(self.baseline()), budget)
        first_charge = budget.used
        second = codec("active").header(wire(self.baseline("active")), budget)
        header = second.header
        cost = header.materialization_bytes
        copy_credit = budget.reserve(cost)
        held = budget.used
        first.close()
        self.assertEqual(budget.used, held - first_charge)
        document = header.materialize()
        self.assertEqual(document["descriptor"]["view"], "active")
        value = self.baseline()
        value["receiptRefs"]["after"].append(value["receiptRefs"]["after"][0])
        held = budget.used
        with self.assertRaises(ContractError):
            codec().header(wire(value), budget)
        self.assertEqual(budget.used, held)
        second.close()
        self.assertEqual(budget.used, cost)
        self.assertEqual(document["descriptor"]["view"], "active")
        document = None
        copy_credit.close()
        self.assertEqual(budget.used, 0)
