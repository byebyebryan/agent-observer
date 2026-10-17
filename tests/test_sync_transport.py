"""Supported structural relay facade only; no live/native/relay acceptance."""

import copy
import gc
import json
import subprocess
import sys
import threading
import unittest
import weakref
from unittest.mock import patch

from test_sync_acquisition import Budget, opaque, wire
from test_sync_native import baseline, control, head, transaction

from agent_observer import sync_acquisition, sync_transport
from agent_observer.contract import ContractError
from agent_observer.sync_acquisition import SCAN_SCRATCH_BYTES
from agent_observer.sync_commitment import descriptor_digest
from agent_observer.sync_native import MAX_HEAD_BYTES, TABLES, descriptor, parse_message
from agent_observer.sync_transport import AgentSyncTransportCodec


def codec(view="full", host="fixture"):
    # A local fixture identifier, never an allocated production encoding ID.
    return AgentSyncTransportCodec(view, encoding_id="fixture-expanded/1", expected_host=host)


def physical_size(value):
    seen = set()

    def visit(item):
        if id(item) in seen:
            return 0
        seen.add(id(item))
        size = sys.getsizeof(item)
        if type(item) is dict:
            size += sum(visit(key) + visit(child) for key, child in item.items())
        elif type(item) is list:
            size += sum(visit(child) for child in item)
        return size

    try:
        return visit(value)
    finally:
        visit = None


class SyncTransportTest(unittest.TestCase):
    def test_pure_import_and_public_role_surface(self):
        script = (
            "import sys;from agent_observer.sync_transport import AgentSyncTransportCodec;"
            "assert not any(name in sys.modules for name in ['mesh_plus',"
            "'agent_observer.service_runtime','agent_observer.observation_engine',"
            "'agent_observer.collection','agent_observer.codex_snapshot'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        facade = codec()
        for name in ("open", "entries", "operations", "check_baseline", "check_transaction",
                     "check_head", "snapshot", "lookup", "acquire", "restore", "profile"):
            self.assertFalse(hasattr(facade, name), name)

    def test_explicit_immutable_encoding_and_native_view(self):
        for view in ("full", "active"):
            selected = descriptor(view)
            facade = codec(view)
            self.assertEqual(dict(facade.encoding), {
                "id": "fixture-expanded/1", "schema": selected["schemaDigest"],
                "nativeDescriptor": descriptor_digest(selected),
            })
            with self.assertRaises((TypeError, AttributeError)):
                facade.encoding["id"] = "other"
            with self.assertRaises(AttributeError):
                facade._view = "other"
        for invalid in (None, True, "", "has space", "x" * 129, "nonasciié"):
            with self.subTest(invalid=invalid), self.assertRaises(ContractError):
                AgentSyncTransportCodec("full", encoding_id=invalid)
        with self.assertRaises(ContractError):
            AgentSyncTransportCodec("other", encoding_id="fixture/1")

    def test_all_header_families_detach_under_separate_copy_credit(self):
        for view in ("full", "active"):
            for make in (baseline, transaction, head, control):
                with self.subTest(view=view, kind=make.__name__):
                    budget, raw = Budget(), wire(make(view))
                    before = sys.getrefcount(raw)
                    ticket = codec(view).header(raw, budget)
                    header = ticket.header
                    self.assertEqual(sys.getrefcount(raw), before)
                    retained = budget.used
                    cost = header.materialization_bytes
                    copy_credit = budget.reserve(cost)
                    document = header.materialize()
                    self.assertGreaterEqual(cost, physical_size(document))
                    self.assertEqual(document, parse_message(raw, view, "fixture"))
                    document["descriptor"]["tables"].clear()
                    second_credit = budget.reserve(cost)
                    second = header.materialize()
                    self.assertEqual(len(second["descriptor"]["tables"]), len(TABLES))
                    second = None
                    second_credit.close()
                    ticket.close()
                    self.assertEqual(budget.used, cost)
                    self.assertGreater(retained, 0)
                    self.assertEqual(document["descriptor"]["tables"], [])
                    for operation in (lambda header=header: header.materialization_bytes, header.materialize,
                                      lambda ticket=ticket: ticket.header):
                        with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                            operation()
                    document = None
                    copy_credit.close()
                    ticket.close()
                    self.assertEqual(budget.used, 0)

    def test_material_opaque_payload_never_enters_header_decoder_or_copy(self):
        raw = opaque(b'{"same":1,"same":2,"payload":"' + b"x" * 262144 + b'"}')
        budget = Budget()
        sizes, loads = [], json.loads

        def bounded(data, *args, **kwargs):
            sizes.append(len(data))
            self.assertLess(len(data), 16384)
            return loads(data, *args, **kwargs)

        with patch("agent_observer.bounded_json.json.loads", bounded):
            ticket = codec().header(raw, budget)
            credit = budget.reserve(ticket.header.materialization_bytes)
            document = ticket.header.materialize()
            self.assertTrue(all(document["tables"][key] == [] for key in TABLES if key != "receipts"))
            ticket.close()
            document = None
            credit.close()
        self.assertTrue(sizes)
        self.assertEqual(budget.used, 0)
        with self.assertRaises(ValueError):
            parse_message(raw, "full", "fixture")

    def test_head_has_a_separate_cap_and_rejects_material_before_validation(self):
        facade, budget = codec(), Budget()
        raw = opaque(b'"' + b"x" * MAX_HEAD_BYTES + b'"')
        with patch.object(sync_acquisition._Scanner, "scan", side_effect=AssertionError("head scanned material")):
            with self.assertRaisesRegex(ContractError, "sync_ticket_header_limit"):
                facade.head(raw, budget)
        for make in (baseline, transaction):
            with patch.object(sync_acquisition, "validate_message", side_effect=AssertionError("material validation")):
                with self.assertRaisesRegex(ContractError, "sync_transport_head_kind"):
                    facade.head(wire(make()), budget)
        for make in (head, control):
            ticket = facade.head(wire(make()), budget)
            credit = budget.reserve(ticket.header.materialization_bytes)
            document = ticket.header.materialize()
            self.assertEqual(document["kind"], make()["kind"])
            ticket.close()
            document = None
            credit.close()
        self.assertEqual(budget.used, 0)

    def test_wrong_view_host_clock_and_framing_preserve_strict_boundary(self):
        facade = codec()
        invalid = [wire(baseline("active")), wire(baseline())[:-1], wire(baseline()) + b"\n"]
        value = head()
        value["ownerClock"]["clockDomain"] = "time:123"
        invalid.append(wire(value))
        value = baseline()
        value["nativeBinding"]["clockDomain"] = "time:[bad]"
        invalid.append(wire(value))
        for raw in invalid:
            budget = Budget()
            with self.subTest(raw=raw[:40]), self.assertRaises(ContractError):
                facade.header(raw, budget)
            self.assertEqual(budget.used, 0)
        with self.assertRaisesRegex(ContractError, "sync_host_mismatch"):
            codec(host="other").header(wire(baseline()), Budget())

    def test_preallocation_failure_precedes_scanner_and_retires_control(self):
        budget = Budget(sync_transport._CONTROL_HEAP + SCAN_SCRATCH_BYTES - 1)
        with patch.object(sync_acquisition._Scanner, "__init__", side_effect=AssertionError("unpaid scan")):
            with self.assertRaisesRegex(ContractError, "fixture_heap_capacity"):
                codec().header(wire(baseline()), budget)
        self.assertEqual(budget.used, 0)

    def test_reentrant_close_revokes_now_but_refunds_only_after_copy_unwind(self):
        enabled = gc.isenabled()
        gc.disable()
        try:
            budget = Budget()
            ticket = codec().head(wire(head()), budget)
            header = ticket.header
            copy_bytes = header.materialization_bytes
            copy_credit = budget.reserve(copy_bytes)
            charged = budget.used
            clone = copy.deepcopy

            def close_during_copy(document):
                ticket.close()
                self.assertEqual(budget.used, charged, "live header uncharged inside copy callback")
                self.assertEqual(document["kind"], "head")
                with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                    _ = header.materialization_bytes
                return clone(document)

            with patch.object(sync_transport.copy, "deepcopy", new=close_during_copy):
                with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                    header.materialize()
            self.assertEqual(budget.used, copy_bytes)
            copy_credit.close()
            self.assertEqual(budget.used, 0)
        finally:
            if enabled:
                gc.enable()

    def test_failed_scan_retires_error_graph_before_any_refund(self):
        class Probe:
            pass

        refs, refunds = [], []

        class GuardedBudget(Budget):
            def reserve(self, amount, *, encoded=0):
                lease = super().reserve(amount, encoded=encoded)

                class Observed:
                    def close(self):
                        refunds.append(amount)
                        self_case.assertTrue(all(ref() is None for ref in refs), "refund preceded error-frame retirement")
                        lease.close()

                return Observed()

        self_case = self

        def fail(document, *_args):
            marker = Probe()
            refs.append(weakref.ref(marker))
            document["marker"] = marker
            raise RuntimeError("fixture_header_failure")

        budget, saved = GuardedBudget(), None
        enabled = gc.isenabled()
        gc.disable()
        try:
            with patch.object(sync_acquisition, "validate_message", new=fail):
                try:
                    codec().header(wire(baseline()), budget)
                except RuntimeError as error:
                    saved = error
            self.assertEqual(saved.args, ("fixture_header_failure",))
            self.assertTrue(refunds)
            self.assertEqual(budget.used, 0)
            self.assertTrue(all(ref() is None for ref in refs))
        finally:
            if enabled:
                gc.enable()

    def test_gc_disabled_retained_headers_do_not_keep_closed_tickets_or_budget(self):
        retained, enabled = [], gc.isenabled()
        gc.disable()
        try:
            for _ in range(8):
                budget = Budget()
                ticket = codec().header(wire(baseline()), budget)
                weak = weakref.ref(ticket)
                retained.append(ticket.header)
                ticket.close()
                ticket = None
                self.assertIsNone(weak())
                self.assertEqual(budget.used, 0)
            for header in retained:
                with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                    header.materialize()
        finally:
            if enabled:
                gc.enable()

    def test_concurrent_close_keeps_copy_pin_and_cannot_return_a_late_header(self):
        budget = Budget()
        ticket = codec().head(wire(head()), budget)
        header = ticket.header
        copy_bytes = header.materialization_bytes
        copy_credit = budget.reserve(copy_bytes)
        before = budget.used
        entered, release = threading.Event(), threading.Event()
        clone = copy.deepcopy
        failures = []

        def paused(document):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("fixture_copy_timeout")
            return clone(document)

        def reader():
            try:
                header.materialize()
            except ContractError as error:
                failures.append(error)

        with patch.object(sync_transport.copy, "deepcopy", new=paused):
            worker = threading.Thread(target=reader)
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                ticket.close()
                self.assertEqual(budget.used, before)
                with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                    _ = header.materialization_bytes
            finally:
                release.set()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual([error.args for error in failures], [("sync_ticket_closed",)])
        self.assertEqual(budget.used, copy_bytes)
        copy_credit.close()
        self.assertEqual(budget.used, 0)

    def test_ticket_and_header_constructors_are_not_minting_apis(self):
        with self.assertRaisesRegex(ContractError, "sync_transport_ticket_owner"):
            sync_transport.NativeTransportTicket(None, None, 0)
        with self.assertRaisesRegex(ContractError, "sync_transport_ticket_owner"):
            sync_transport.HeaderRef(None)
