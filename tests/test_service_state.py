"""Actual source-lease/reconciliation/scheduling behavior with injected clocks."""

import copy
import unittest

from test_service_contract import fixture

from agent_observer.activity import codex_activity, codex_outcome
from agent_observer.contract import ContractError, validate_snapshot
from agent_observer.service_scheduler import Scheduler
from agent_observer.service_state import ServiceState


def provider_snapshot(provider):
    value = copy.deepcopy(fixture()["snapshot"])
    value["sources"] = [s for s in value["sources"] if s["provider"] == provider]
    value["sessions"] = [r for r in value["sessions"] if r["identity"]["provider"] == provider]
    return validate_snapshot(value)


class ServiceStateTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        value = fixture()
        self.state = ServiceState(host_scope="fixture", configs={s["provider"]: (s["configHome"], s["configHomeKind"]) for s in value["sources"]}, uid=1000, clock=lambda: self.now, boot_id=value["bootId"], clock_domain=value["clockDomain"])

    def accept(self, provider, component, *, ttl=10000, value=None):
        self.state.attempt(provider, component)
        self.state.accept(provider, component, value or provider_snapshot(provider), sampled_ms=self.now, ttl_ms=ttl)

    def test_cold_start_is_warming_not_complete_empty(self):
        frame = self.state.frame("status", 1)
        self.assertEqual(frame["state"], "warming")
        self.assertIsNone(frame["snapshot"])

    def test_runtime_confirmation_never_renews_history(self):
        self.accept("codex", "history", ttl=1000)
        self.accept("codex", "runtime", ttl=5000)
        history = self.state.receipts["codex"]["history"]
        sample = history.sampledBoottimeMs
        original_clock = provider_snapshot("codex")["sessions"][0]["phase"]["observedAt"]
        self.now += 1200
        self.accept("codex", "runtime", ttl=5000)
        frame = self.state.frame("view", 1)
        self.assertEqual(history.sampledBoottimeMs, sample)
        self.assertEqual(history.health, "stale")
        self.assertEqual(frame["snapshot"]["sessions"][0]["phase"]["value"], "blocked")
        self.assertEqual(frame["snapshot"]["sessions"][0]["phase"]["observedAt"], original_clock)

    def test_expiry_clears_blocked_runtime_and_preserves_clock(self):
        self.accept("codex", "runtime", ttl=1000)
        revision = self.state.revision
        row = self.state.snapshot["sessions"][0]
        clock = row["phase"]["observedAt"]
        self.now += 1001
        frame = self.state.frame("view", 1)
        row = frame["snapshot"]["sessions"][0]
        self.assertGreater(frame["viewRevision"], revision)
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["phase"]["lastKnownValue"], "blocked")
        self.assertEqual(row["phase"]["observedAt"], clock)
        self.assertEqual(row["blockedReason"], "unknown")
        self.assertEqual(row["runtime"]["value"], "unknown")

    def test_failed_source_preserves_healthy_provider(self):
        self.accept("codex", "runtime")
        self.accept("claude", "runtime")
        self.state.fail("claude", "runtime")
        frame = self.state.frame("view", 1)
        self.assertTrue(all(r["runtime"]["value"] == "running" for r in frame["snapshot"]["sessions"] if r["identity"]["provider"] == "codex"))
        self.assertTrue(all(r["runtime"]["value"] == "unknown" for r in frame["snapshot"]["sessions"] if r["identity"]["provider"] == "claude"))

    def test_wrong_worker_scope_does_not_replace_data(self):
        self.accept("codex", "runtime")
        previous = self.state.snapshot
        changed = provider_snapshot("claude")
        with self.assertRaises(ContractError):
            self.state.accept("codex", "runtime", changed, sampled_ms=self.now, ttl_ms=5000)
        self.assertIs(self.state.snapshot, previous)

    def test_heartbeat_preserves_collection_and_receipts(self):
        self.accept("codex", "runtime")
        previous = copy.deepcopy(self.state.snapshot)
        receipts = copy.deepcopy(self.state.frame("status", 1)["sources"])
        self.now += 1
        frame = self.state.frame("heartbeat", 2)
        self.assertIsNone(frame["snapshot"])
        self.assertEqual(self.state.snapshot, previous)
        self.assertEqual(frame["sources"], receipts)

    def test_changed_native_context_stales_the_other_component(self):
        value = provider_snapshot("codex")
        value["sources"][0]["runtime"] = {
            "version": "diagnostic", "binarySha256": "a" * 64,
            "topology": "native_managed_endpoint", "bootId": self.state.boot_id,
            "pid": 123, "startTicks": 456, "endpoint": "/fixture/endpoint",
        }
        self.accept("codex", "runtime", value=value)
        self.accept("codex", "history", value=value)
        first = self.state.generations["codex"]
        value["sources"][0]["runtime"]["startTicks"] += 1
        self.accept("codex", "history", value=value)
        self.assertGreater(self.state.generations["codex"], first)
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "stale")
        self.assertEqual(self.state.snapshot["sessions"][0]["runtime"]["value"], "unknown")
        self.accept("codex", "runtime", value=value)
        self.assertEqual(self.state.snapshot["sessions"][0]["runtime"]["value"], "running")

    def test_partial_inventory_keeps_missing_identity_as_stale(self):
        value = provider_snapshot("codex")
        self.accept("codex", "runtime", value=value)
        sid = value["sessions"][0]["identity"]
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="live_limit")
        self.accept("codex", "runtime", value=value)
        row = next(r for r in self.state.snapshot["sessions"] if r["identity"] == sid)
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertEqual(row["runtime"]["lastKnownValue"], "running")
        self.assertIn("retained_after_gap", row["metadataIssues"])

    def turn(self, status, start, end):
        value = provider_snapshot("codex")
        payload = {"data": [{"status": status, "startedAt": start, "completedAt": end,
                             "items": [], "itemsView": "notLoaded"}]}
        value["sessions"][0]["activity"] = codex_activity(payload)
        outcome = codex_outcome(payload)
        value["sessions"][0]["outcome"] = {**outcome, "clock": "native" if outcome["observedAt"] is not None else None}
        return value

    def test_new_turn_clears_old_terminal_from_either_component(self):
        for older, newer in (("history", "runtime"), ("runtime", "history")):
            with self.subTest(older=older):
                self.accept("codex", older, value=self.turn("completed", 1, 2))
                self.now += 1
                self.accept("codex", newer, ttl=1000, value=self.turn("inProgress", 3, None))
                row = self.state.snapshot["sessions"][0]
                self.assertEqual(row["outcome"]["value"], "unknown")
                self.assertEqual(row["outcome"]["reason"], "turn_in_progress")
                self.assertIsNone(row["outcome"]["observedAt"])
                self.assertEqual(row["activity"]["at"], 3000)
                self.now += 1001
                row = self.state.frame("view", 1)["snapshot"]["sessions"][0]
                self.assertEqual(row["outcome"]["value"], "unknown")
                self.assertIsNone(row["outcome"]["observedAt"])
                self.now += 1
                self.accept("codex", older, value=self.turn("completed", 3, 4))
                row = self.state.snapshot["sessions"][0]
                self.assertEqual(row["outcome"]["value"], "completed")
                self.assertEqual(row["outcome"]["observedAt"], 4000)


class SchedulerTest(unittest.TestCase):
    def test_independent_jobs_fair_history_and_dirty_followup(self):
        scheduler = Scheduler(("codex", "claude"))
        jobs = scheduler.start_due(10000)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(scheduler.start_due(10001), [])
        codex = next(j for j in jobs if j.provider == "codex")
        for _ in range(1000):
            scheduler.hint("codex", "runtime", 10100)
        self.assertTrue(scheduler.finish(codex, 10300, success=True))
        self.assertEqual(scheduler.start_due(10300)[0].component, "history")
        self.assertIn("claude", scheduler.active)

    def test_deadline_late_generation_and_backoff(self):
        scheduler = Scheduler(("codex",), timeout_ms=1000)
        job = scheduler.start_due(10000)[0]
        self.assertEqual(scheduler.expired(11000), [job])
        scheduler.invalidate("codex")
        self.assertFalse(scheduler.finish(job, 11000, success=False))
        self.assertEqual(scheduler.failures[("codex", "runtime")], 1)
