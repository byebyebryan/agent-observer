"""Accepted-only worker brackets; no provider read or selected-service action."""

import copy
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID

from projection_fixture import provider_snapshot
from test_service_contract import fixture

from agent_observer.contract import ContractError, canonical
from agent_observer.observation_support import fact_support
from agent_observer.service_runtime import Runtime, Worker
from agent_observer.service_state import ServiceState


class WorkingSetCaptureTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        value = fixture()
        self.options = dict(
            host_scope="fixture",
            configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000,
            clock=lambda: self.now,
            boot_id=value["bootId"],
            clock_domain=value["clockDomain"],
        )
        self.state = ServiceState(**self.options, working_set_window_ms=259200000)

    def sample(self, number=11):
        value = provider_snapshot("codex")
        value["collectionId"] = str(UUID(int=number))
        return value

    def accept(self, value=None, component="runtime", *, lower=14000, upper=15000):
        self.state.attempt("codex", component)
        return self.state.accept(
            "codex",
            component,
            value or self.sample(),
            sampled_ms=lower,
            ttl_ms=10000,
            accepted_boottime_ms=upper,
        )

    def test_default_has_no_clock_owner_and_window_is_explicit(self):
        legacy = ServiceState(**self.options)
        self.assertIsNone(legacy.working_set_clocks)
        self.assertIsNone(legacy.working_set_window_ms)
        for window in (True, -1, 2592000001, 72.0):
            with self.assertRaises(ContractError):
                ServiceState(**self.options, working_set_window_ms=window)
        zero = ServiceState(**self.options, working_set_window_ms=0)
        self.assertIsNotNone(zero.working_set_clocks)

    def test_clock_is_exact_accepted_original_and_history_mirror(self):
        value = self.sample()
        self.assertTrue(self.accept(value, "history"))
        source = self.state.source_meta("codex")
        exported = self.state.working_set_clocks.export(source)
        self.assertEqual(len(exported), 2)
        for component in ("runtime", "history"):
            receipt = self.state.receipts["codex"][component]
            ref = fact_support(self.state.service_id, source, component, receipt)
            clock = self.state.working_set_clocks.get(ref, source, sample_id=value["collectionId"])
            self.assertEqual(clock.sample_id, value["collectionId"])
            self.assertEqual(clock.origin_component, "history")
            self.assertEqual(
                (clock.lower_boottime_ms, clock.wall_ms, clock.upper_boottime_ms),
                (14000, value["collectedAt"], 15000),
            )
            self.assertIsNone(
                self.state.working_set_clocks.get(ref, source, sample_id=str(UUID(int=12)))
            )
        self.assertEqual(self.state.revision, 1)
        self.assertIsNone(self.state._sync_projector)

    def test_stale_rejected_input_does_not_change_clock_or_fail_new_receipt(self):
        self.assertTrue(self.accept())
        source = self.state.source_meta("codex")
        before = self.state.working_set_clocks.export(source)
        ceiling = self.state.working_set_clocks.ceiling
        self.assertFalse(self.accept(self.sample(12), lower=13000))
        self.assertEqual(
            self.state.working_set_clocks.export(self.state.source_meta("codex")), before
        )
        self.assertEqual(self.state.working_set_clocks.ceiling, ceiling)
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")

    def test_bad_clock_or_missing_capture_never_rebinds_previous_authority(self):
        self.accept()
        ceiling = self.state.working_set_clocks.ceiling
        for number, upper in ((12, 16000), (13, 13000), (14, True)):
            self.assertTrue(self.accept(self.sample(number), upper=upper))
            source = self.state.source_meta("codex")
            self.assertEqual(self.state.working_set_clocks.export(source), [])
            self.assertEqual(self.state.working_set_clocks.ceiling, ceiling)
            self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")
        self.state.attempt("codex", "runtime")
        self.state.accept("codex", "runtime", self.sample(15), sampled_ms=14000, ttl_ms=10000)
        self.assertEqual(self.state.working_set_clocks.export(self.state.source_meta("codex")), [])

    def test_context_retirement_keeps_incarnation_ceiling(self):
        self.accept()
        before = self.state.working_set_clocks.ceiling
        self.now = 16000
        value = self.sample(12)
        value["sources"][0]["runtime"]["pid"] += 1
        self.assertTrue(self.accept(value, lower=15000, upper=16000))
        self.assertEqual(self.state.working_set_clocks.ceiling, before)
        self.assertEqual(self.state.source_meta("codex")["contextGeneration"], 2)

    def test_runtime_process_success_does_not_install_a_superseded_sample(self):
        self.accept()
        before = self.state.working_set_clocks.export(self.state.source_meta("codex"))
        value = self.sample(12)
        process = SimpleNamespace(stdout=io.BytesIO())
        job = SimpleNamespace(provider="codex", component="runtime", started=13000, generation=0)
        worker = Worker(job, process)
        worker.buffer.extend(canonical(value).encode())
        runtime = Runtime(self.state, "/unused/read.sock", collect=False)
        runtime.workers["codex"] = worker
        runtime.scheduler.finish = Mock()
        try:
            with (
                patch.object(runtime, "_exit_status", return_value=0),
                patch.object(runtime, "_stop_worker"),
                patch.object(runtime, "_take_image_memo") as memo,
            ):
                runtime._complete(worker)
            self.assertFalse(memo.call_args.kwargs["eligible"])
            self.assertTrue(runtime.scheduler.finish.call_args.kwargs["success"])
            self.assertEqual(
                self.state.working_set_clocks.export(self.state.source_meta("codex")), before
            )
            self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")
        finally:
            runtime.selector.close()

    def test_unaccepted_malformed_input_does_not_install_a_clock(self):
        value = copy.deepcopy(self.sample())
        value["host"]["authority"] = "foreign"
        with self.assertRaises(ContractError):
            self.accept(value)
        self.assertIsNone(self.state.working_set_clocks.ceiling)
