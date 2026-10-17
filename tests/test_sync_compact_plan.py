"""Private bounded compact-plan parser, not generic/native acceptance."""

import copy
import gc
import json
import subprocess
import sys
import threading
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_sync_acquisition import Budget, wire
from test_sync_native import control, head

from agent_observer import sync_compact_plan
from agent_observer.contract import ContractError
from agent_observer.sync_compact_plan import _open_compact_plan
from agent_observer.sync_compact_schema import value_schema
from agent_observer.sync_native import TABLES

ROOT = Path(__file__).resolve().parents[1]


class SyncCompactPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "docs/evidence/2026-10-16-delta-sync-source/compact-raw-vectors.json").read_text())
        # Fixed test validator configuration is outside isolated fixture credit.
        cls.validators = {(space, operation): Draft202012Validator(value_schema(space, operation=operation))
                          for space in TABLES for operation in (False, True)}

    def setUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.plans, self.budgets = [], []

    def tearDown(self):
        for plan in self.plans:
            plan.close()
        for budget in self.budgets:
            self.assertEqual(budget.used, 0)
        self.assertFalse(gc.isenabled())
        if self.enabled:
            gc.enable()

    def baseline(self):
        return copy.deepcopy(self.fixture["baselines"][0]["raw"])

    def validate(self, space, value, operation):
        self.validators[space, operation].validate(value)

    def opened(self, message=None, *, validate=None, budget=None):
        message = self.baseline() if message is None else message
        budget = Budget() if budget is None else budget
        self.budgets.append(budget)
        raw = wire(message)
        plan = _open_compact_plan(raw, message["descriptor"]["view"], budget,
                                  validate_value=self.validate if validate is None else validate,
                                  expected_host="fixture")
        self.plans.append(plan)
        return plan, budget, raw

    def test_import_is_mesh_provider_service_free(self):
        code = ("import sys;import agent_observer.sync_compact_plan;"
                "assert not any(x in sys.modules for x in ('mesh_plus',"
                "'agent_observer.observation_engine','agent_observer.service_runtime',"
                "'agent_observer.codex_snapshot'))")
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_open_retains_one_borrowed_frame_eight_spans_and_no_decoded_rows(self):
        calls = []
        plan, budget, raw = self.opened(validate=lambda *args: calls.append(args))
        self.assertIs(plan._raw, raw)
        self.assertEqual(set(plan._arrays), set(TABLES))
        self.assertEqual(len(plan._arrays), 8)
        self.assertEqual(calls, [])
        header = plan.header
        credit = budget.reserve(header.materialization_bytes)
        try:
            document = header.materialize()
            self.assertNotIn("receiptRefs", document)
            self.assertTrue(all(not rows for name, rows in document["tables"].items() if name != "receipts"))
            document = None
        finally:
            credit.close()
        plan.close()
        self.assertIsNone(plan._raw)
        self.assertIsNone(plan._refs)
        with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
            header.materialize()
        self.assertEqual(budget.used, 0)

    def test_all_eight_baselines_ten_transactions_one_local_value_at_a_time(self):
        for case in self.fixture["baselines"] + self.fixture["transactions"]:
            with self.subTest(case=case["name"]):
                message = case["raw"]
                plan, budget, _raw = self.opened(message)
                group = "tables" if message["kind"] == "baseline" else "operations"
                for space in TABLES:
                    count = 0
                    for ticket in plan._values(space, budget):
                        copy_credit = budget.reserve(ticket.materialization_bytes)
                        value = None
                        try:
                            value = ticket.materialize()
                            self.assertEqual(value, message[group][space][count])
                            count += 1
                        finally:
                            value = None
                            copy_credit.close()
                            ticket.close()
                    self.assertEqual(count, len(message[group][space]))
                plan.close()
                self.assertEqual(budget.used, 0)

    def test_live_value_and_live_iterator_reject_without_invalidating_current(self):
        plan, budget, _raw = self.opened()
        iterator = plan._values("bodies", budget)
        ticket = next(iterator)
        with self.assertRaisesRegex(ContractError, "sync_compact_value_live"):
            next(iterator)
        with self.assertRaisesRegex(ContractError, "sync_compact_iterator_live"):
            plan._values("records", budget)
        credit = budget.reserve(ticket.materialization_bytes)
        value = ticket.materialize()
        self.assertEqual(len(value), 2)
        value = None
        credit.close()
        ticket.close()
        iterator.close()
        plan._values("records", budget).close()

    def test_iterator_uses_current_budget_not_retired_open_capability(self):
        budget = Budget()
        self.budgets.append(budget)

        class OpenScope:
            live = True

            def reserve(self, amount, *, encoded=0):
                if not self.live:
                    raise AssertionError("reused retired open budget")
                return budget.reserve(amount, encoded=encoded)

        scope = OpenScope()
        message = self.baseline()
        plan = _open_compact_plan(wire(message), message["descriptor"]["view"], scope,
                                  validate_value=self.validate)
        self.plans.append(plan)
        scope.live = False
        reference = weakref.ref(scope)
        del scope
        self.assertIsNone(reference())
        iterator = plan._values("bodies", budget)
        ticket = next(iterator)
        self.assertGreater(ticket.materialization_bytes, 0)
        ticket.close()
        iterator.close()
        plan.close()
        self.assertEqual(budget.used, 0)

    def test_row_reservation_refusal_precedes_payload_decode_and_preserves_sibling(self):
        plan, budget, _raw = self.opened()
        sibling, _budget, _other = self.opened(budget=budget)
        iterator = plan._values("bodies", budget)
        held = budget.used
        budget.maximum = held
        with patch("agent_observer.sync_compact_plan._decode", side_effect=AssertionError("unpaid decode")):
            with self.assertRaisesRegex(ContractError, "fixture_heap_capacity"):
                next(iterator)
        self.assertLess(budget.used, held)
        self.assertGreater(sibling.header.materialization_bytes, 0)
        budget.maximum = 64 * 1024 * 1024

    def test_invalid_late_value_rejects_before_yield_and_keeps_prior_copy_separate(self):
        message = self.baseline()
        message["tables"]["bodies"] *= 2
        message["tables"]["bodies"][1] = copy.deepcopy(message["tables"]["bodies"][1])
        message["tables"]["bodies"][1][1].pop()
        plan, budget, _raw = self.opened(message)
        iterator = plan._values("bodies", budget)
        first = next(iterator)
        credit = budget.reserve(first.materialization_bytes)
        value = first.materialize()
        first.close()
        held = budget.used
        with self.assertRaisesRegex(ContractError, "sync_compact_value_shape") as caught:
            next(iterator)
        self.assertIsNone(caught.exception.__context__)
        self.assertLess(budget.used, held)
        self.assertEqual(len(value[1]), 18)
        value = None
        credit.close()

    def test_duplicate_opaque_object_key_rejects_when_its_row_is_visited(self):
        message = self.baseline()
        message["tables"]["metadata"] = [["OPAQUE", None]]
        raw = wire(message).replace(b'"OPAQUE"', b'{"duplicate":1,"duplicate":2}')
        budget = Budget()
        self.budgets.append(budget)
        plan = _open_compact_plan(raw, message["descriptor"]["view"], budget, validate_value=self.validate)
        self.plans.append(plan)
        with self.assertRaisesRegex(ContractError, "sync_ticket_header_json"):
            next(plan._values("metadata", budget))

    def test_closed_plan_revokes_current_value_iterator_and_keeps_sibling(self):
        plan, budget, _raw = self.opened()
        sibling, _budget, _other = self.opened(budget=budget)
        iterator = plan._values("bodies", budget)
        ticket = next(iterator)
        plan.close()
        with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
            ticket.materialize()
        with self.assertRaisesRegex(ContractError, "sync_compact_iterator_closed"):
            next(iterator)
        self.assertGreater(sibling.header.materialization_bytes, 0)
        sibling.close()
        self.assertEqual(budget.used, 0)

    def test_reentrant_close_during_validation_revokes_now_keeps_all_credit_through_unwind(self):
        state = {}

        def validator(_space, _value, _operation):
            held = state["budget"].used
            state["plan"].close()
            self.assertEqual(state["budget"].used, held)
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                state["plan"].header.materialize()

        plan, budget, _raw = self.opened(validate=validator)
        state.update(plan=plan, budget=budget)
        with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
            next(plan._values("bodies", budget))
        self.assertEqual(budget.used, 0)

    def test_close_during_value_copy_keeps_physical_credit_until_unwind(self):
        plan, budget, _raw = self.opened()
        iterator = plan._values("bodies", budget)
        ticket = next(iterator)
        copy_amount = ticket.materialization_bytes
        copy_credit = budget.reserve(copy_amount)
        entered, release, errors = threading.Event(), threading.Event(), []
        deepcopy = copy.deepcopy

        def gated(document):
            entered.set()
            self.assertTrue(release.wait(3))
            return deepcopy(document)

        def read():
            try:
                ticket.materialize()
            except BaseException as error:
                errors.append(error)

        with patch("agent_observer.sync_transport.copy.deepcopy", gated):
            thread = threading.Thread(target=read)
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                plan.close()
                self.assertGreater(budget.used, copy_amount)
                with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                    ticket.materialize()
            finally:
                release.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ContractError)
        copy_credit.close()
        self.assertEqual(budget.used, 0)

    def test_saved_schema_error_keeps_no_decoded_row_with_gc_disabled(self):
        class WeakList(list):
            pass

        original, refs, errors = sync_compact_plan._decode, [], []

        def decoded(raw, span):
            value = WeakList(original(raw, span))
            refs.append(weakref.ref(value))
            return value

        def reject(_space, value, _operation):
            error = ValueError("payload-bearing schema error")
            error.instance = value
            raise error

        plan, budget, _raw = self.opened(validate=reject)
        held = budget.used
        with patch("agent_observer.sync_compact_plan._decode", decoded):
            try:
                next(plan._values("bodies", budget))
            except ContractError as error:
                errors.append(error)
        self.assertEqual(len(errors), 1)
        self.assertTrue(refs and all(ref() is None for ref in refs))
        self.assertEqual(budget.used, held)

    def test_drop_plan_retires_raw_and_metadata_with_retained_handles_without_gc(self):
        plan, budget, _raw = self.opened()
        header = plan.header
        iterator = plan._values("bodies", budget)
        ticket = next(iterator)
        reference = weakref.ref(plan)
        self.plans.remove(plan)
        del plan
        self.assertIsNone(reference())
        self.assertEqual(budget.used, 0)
        for read in (header.materialize, ticket.materialize, lambda: next(iterator)):
            with self.assertRaises(ContractError):
                read()

    def test_busy_next_and_concurrent_close_cannot_refund_inflight_validator(self):
        entered, release, errors = threading.Event(), threading.Event(), []

        def validator(_space, _value, _operation):
            entered.set()
            self.assertTrue(release.wait(3))

        plan, budget, _raw = self.opened(validate=validator)
        iterator = plan._values("bodies", budget)

        def read():
            try:
                next(iterator)
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=read)
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            held = budget.used
            with self.assertRaisesRegex(ContractError, "sync_compact_value_live"):
                next(iterator)
            self.assertEqual(budget.used, held)
            plan.close()
            self.assertEqual(budget.used, held)
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                plan.header.materialize()
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ContractError)
        self.assertEqual(budget.used, 0)

    def test_head_control_never_become_material_plans(self):
        for message in (head(), control()):
            budget = Budget()
            with self.assertRaisesRegex(ContractError, "sync_compact_material_kind"):
                _open_compact_plan(wire(message), "full", budget, validate_value=self.validate)
            self.assertEqual(budget.used, 0)

    def test_full_frame_and_dictionary_checks_precede_row_decode(self):
        message = self.baseline()
        raw = wire(message)
        values = (raw[:-1], raw + b"\n", raw.replace(b'"receiptRefs":', b'"unknown":'))
        for data in values:
            budget = Budget()
            with self.assertRaises(ContractError):
                _open_compact_plan(data, message["descriptor"]["view"], budget, validate_value=self.validate)
            self.assertEqual(budget.used, 0)

    def test_lexical_table_capacity_rejects_before_any_material_decode(self):
        message = self.baseline()
        message["tables"]["records"] = [message["tables"]["records"][0]] * 4097
        budget = Budget()
        with self.assertRaisesRegex(ContractError, "sync_compact_table_capacity"):
            _open_compact_plan(wire(message), message["descriptor"]["view"], budget,
                               validate_value=lambda *_args: self.fail("row decoded at open"))
        self.assertEqual(budget.used, 0)
