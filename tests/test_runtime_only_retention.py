"""Finite observation memory; expiry is omission, never a native lifecycle claim."""

import copy
import unittest

from agent_observer.contract import ContractError, identity_key, store_namespace, validate_snapshot
from agent_observer.service_state import ServiceState
from agent_observer.watch import RUNTIME_ONLY_RETENTION_MS, SampledWatch
from test_service_contract import fixture
from test_service_state import provider_snapshot


def unsaved(provider="claude"):
    value = provider_snapshot(provider)
    value["sessions"] = value["sessions"][:1]
    row = value["sessions"][0]
    row.update(hasSavedHistory=False, inventory="live")
    row["activity"] = {"at": 1700000040000, "health": "current",
                       "reason": "native_conversation_event",
                       "source": "claude_transcript_message" if provider == "claude" else "codex_turn_metadata"}
    value["sourceHealth"] = value["sources"][0]["sourceHealth"] = "partial"
    value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="fixture_gap")
    return validate_snapshot(value)


def missing(value):
    value = copy.deepcopy(value)
    value["sessions"] = []
    for dimension in value["sources"][0]["coverage"].values():
        dimension.update(status="partial", reason="fixture_gap")
    return validate_snapshot(value)


class RuntimeOnlyRetentionTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        frame = fixture()
        self.state = ServiceState(host_scope="fixture", uid=1000,
            configs={s["provider"]: (s["configHome"], s["configHomeKind"])
                     for s in frame["snapshot"]["sources"]},
            clock=lambda: self.now, boot_id=frame["bootId"], clock_domain=frame["clockDomain"])

    def accept(self, value, *, component="runtime", ttl=1000, sampled=None):
        provider = value["sources"][0]["provider"]
        self.state.attempt(provider, component)
        return self.state.accept(provider, component, value,
            sampled_ms=self.now if sampled is None else sampled, ttl_ms=ttl,
            runtime_ttl_ms=1000)

    def test_repeated_partial_reads_and_heartbeats_do_not_slide_original_deadline(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                original = unsaved(provider)
                self.accept(original)
                native_row = copy.deepcopy(original["sessions"][0])
                deadline = self.now + 1000
                for delta in (400, 400, 199):
                    self.now += delta
                    self.accept(missing(original), ttl=10000)
                    row = next(r for r in self.state.snapshot["sessions"]
                               if r["identity"] == native_row["identity"])
                    self.assertEqual(row["runtime"]["value"], "unknown")
                    self.assertEqual(row["runtime"]["observedAt"], native_row["runtime"]["observedAt"])
                    self.assertIn("retained_after_gap", row["metadataIssues"])
                    self.assertEqual(self.state.retention[provider].deadlines[
                        identity_key(row["identity"])], deadline)
                    before = copy.deepcopy(self.state.snapshot)
                    self.state.frame("heartbeat", 1)
                    self.assertEqual(self.state.snapshot, before)
                revision = self.state.revision
                self.now = deadline
                frame = self.state.frame("view", 2)
                self.assertGreater(frame["viewRevision"], revision)
                self.assertFalse(any(r["identity"] == native_row["identity"]
                                     for r in frame["snapshot"]["sessions"]))
                self.assertEqual(self.state.retention[provider].deadlines, {})
                self.assertEqual(frame["snapshot"]["sources"][[s["provider"] for s in
                    frame["snapshot"]["sources"]].index(provider)]["coverage"]["runtime"]["status"], "partial")

    def test_total_source_failure_retires_unsaved_but_preserves_other_provider(self):
        original = unsaved()
        self.accept(original)
        self.accept(provider_snapshot("codex"), ttl=10000)
        other = copy.deepcopy([r for r in self.state.snapshot["sessions"]
                               if r["identity"]["provider"] == "codex"])
        self.now += 200
        self.state.fail("claude", "runtime")
        self.assertTrue(any(r["identity"]["provider"] == "claude"
                            for r in self.state.snapshot["sessions"]))
        self.now += 800
        frame = self.state.frame("view", 1)
        self.assertEqual(frame["snapshot"]["sessions"], other)

    def test_current_native_rows_with_unknown_phase_are_protected_and_reappearance_is_exact(self):
        original = unsaved()
        self.accept(original)
        self.now += 999
        current = copy.deepcopy(original)
        row = current["sessions"][0]
        row["phase"].update(value="unknown", health="unsupported", reason="fixture_unknown")
        row["blockedReasons"] = []
        self.accept(current)
        self.now += 1
        self.state.expire()
        self.assertEqual(self.state.snapshot["sessions"][0]["runtime"]["value"], "running")
        self.assertEqual(self.state.snapshot["sessions"][0]["phase"]["value"], "unknown")
        self.accept(missing(original), ttl=10000)
        self.now += 999
        self.state.expire()
        self.assertEqual(self.state.snapshot["sessions"], [])
        self.now += 1
        self.accept(original)
        restored = self.state.snapshot["sessions"][0]
        self.assertEqual(restored["identity"], original["sessions"][0]["identity"])
        self.assertEqual(restored["activity"], original["sessions"][0]["activity"])
        self.assertNotIn("retained_after_gap", restored["metadataIssues"])

    def test_history_lease_cannot_keep_an_unsaved_row_after_its_runtime_lease(self):
        original = unsaved()
        self.accept(original, component="history", ttl=100000)
        self.now += 10
        self.accept(missing(original), ttl=10000)
        self.now += 990
        self.state.frame("view", 1)
        self.assertEqual(self.state.receipts["claude"]["history"].health, "current")
        self.assertEqual(self.state.snapshot["sessions"], [])
        self.assertEqual(self.state.receipts["claude"]["history"].data["sessions"], [])

    def test_saved_history_learned_after_runtime_survives_expiry_and_sdk_failure(self):
        original = unsaved()
        self.accept(original)
        saved = copy.deepcopy(original)
        saved["sessions"][0].update(hasSavedHistory=True, inventory="saved")
        saved["sources"][0]["coverage"]["runtime"].update(status="unavailable", reason="metadata_only")
        self.now += 400
        self.accept(saved, component="history", ttl=100000)
        row = self.state.snapshot["sessions"][0]
        self.assertTrue(row["hasSavedHistory"])
        self.assertEqual(row["inventory"], "saved")
        self.accept(missing(original), ttl=10000)
        self.state.fail("claude", "history", "sdk_failed")
        self.now += 1000
        self.state.frame("view", 1)
        row = self.state.snapshot["sessions"][0]
        self.assertTrue(row["hasSavedHistory"])
        self.assertEqual(row["runtime"]["value"], "unknown")
        activity = original["sessions"][0]["activity"]
        if activity["at"] is not None:
            self.assertEqual(row["activity"]["lastKnownAt"], activity["at"])

    def test_delayed_metadata_and_rejected_runtime_do_not_restore_expired_unsaved_rows(self):
        original = unsaved()
        start = self.now
        self.accept(original)
        self.now += 500
        self.accept(missing(original), ttl=10000)
        self.assertFalse(self.accept(original, sampled=start))
        self.now += 500
        self.state.expire()
        self.assertEqual(self.state.snapshot["sessions"], [])
        self.accept(original, component="history", ttl=100000, sampled=start + 1)
        self.assertEqual(self.state.snapshot["sessions"], [])
        self.assertEqual(self.state.retention["claude"].deadlines, {})

    def test_complete_absence_clears_deadline_and_history_cannot_restore_runtime_only_row(self):
        original = unsaved()
        self.accept(original, component="history", ttl=100000)
        gone = missing(original)
        gone["sources"][0]["coverage"]["runtime"].update(status="complete", reason="native_snapshot")
        self.now += 1
        self.accept(gone)
        self.assertEqual(self.state.snapshot["sessions"], [])
        self.assertEqual(self.state.retention["claude"].deadlines, {})

    def test_context_replacement_does_not_renew_missing_rows_and_cold_start_has_no_memory(self):
        original = unsaved("codex")
        original["sources"][0]["runtime"] = {
            "version": "diagnostic", "binarySha256": "a" * 64,
            "topology": "native_managed_endpoint", "bootId": self.state.boot_id,
            "pid": 123, "startTicks": 456, "endpoint": "/fixture/endpoint"}
        self.accept(original)
        gone = missing(original)
        gone["sources"][0]["runtime"]["startTicks"] += 1
        self.now += 500
        self.accept(gone, ttl=10000)
        self.assertEqual(self.state.generations["codex"], 2)
        self.now += 500
        self.state.frame("view", 1)
        self.assertEqual(self.state.snapshot["sessions"], [])
        fresh = ServiceState(host_scope="fixture", configs=self.state.configs, uid=1000,
            clock=lambda: self.now, boot_id=self.state.boot_id, clock_domain=self.state.clock_domain)
        self.assertIsNone(fresh.snapshot)
        self.assertFalse(any(r.deadlines for r in fresh.retention.values()))


class WatchRetentionTest(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.watch = SampledWatch(clock=lambda: self.now)

    def test_partial_watch_retires_unsaved_at_original_bound_and_resyncs_saved_rows(self):
        original = unsaved()
        self.watch.sample(original)
        for delta in (20000, 20000, 19999):
            self.now += delta
            self.watch.sample(missing(original))
            self.assertEqual(len(self.watch.previous["sessions"]), 1)
        self.now = RUNTIME_ONLY_RETENTION_MS
        frames = self.watch.sample(missing(original))
        self.assertEqual(frames[-1]["kind"], "change")
        self.assertEqual(frames[-1]["snapshot"]["sessions"], [])
        self.assertEqual(self.watch.retention.deadlines, {})
        self.watch.gap("collection_failed")
        self.now += 1
        frames = self.watch.sample(original)
        self.assertEqual(frames[-1]["kind"], "resync")
        self.assertEqual(frames[-1]["snapshot"]["sessions"][0]["identity"],
                         original["sessions"][0]["identity"])

    def test_collection_latency_does_not_start_retention_at_delivery_time(self):
        original = unsaved()
        self.now = RUNTIME_ONLY_RETENTION_MS + 1
        self.watch.sample(original, sampled_ms=0)
        self.assertEqual(len(self.watch.previous["sessions"]), 1)
        self.now += 1
        self.watch.sample(missing(original))
        self.assertEqual(self.watch.previous["sessions"], [])

    def test_future_sample_is_rejected_without_mutating_retention(self):
        original = unsaved()
        self.watch.sample(original)
        before = copy.deepcopy(self.watch.retention.deadlines)
        with self.assertRaisesRegex(ContractError, "invalid_watch_sample_clock"):
            self.watch.sample(original, sampled_ms=self.now + 1)
        self.assertEqual(self.watch.retention.deadlines, before)

    def test_complete_runtime_absence_drops_unsaved_despite_partial_history(self):
        original = unsaved()
        self.watch.sample(original)
        gone = missing(original)
        gone["sources"][0]["coverage"]["runtime"].update(status="complete", reason="native_snapshot")
        self.now += 1
        self.watch.sample(gone)
        self.assertEqual(self.watch.previous["sessions"], [])
        self.assertEqual(self.watch.retention.deadlines, {})

    def test_saved_rows_preserve_original_age_across_gaps_and_long_partial_watch(self):
        original = provider_snapshot("claude")
        original["sources"][0]["coverage"]["saved"].update(status="partial", reason="metadata_scan")
        self.watch.sample(original)
        self.now += 10 * RUNTIME_ONLY_RETENTION_MS
        self.watch.gap("collection_failed")
        frames = self.watch.sample(missing(original))
        self.assertEqual(frames[-1]["kind"], "resync")
        rows = {identity_key(r["identity"]): r for r in self.watch.previous["sessions"]}
        for old in original["sessions"]:
            row = rows[identity_key(old["identity"])]
            self.assertTrue(row["hasSavedHistory"])
            self.assertEqual(row["runtime"]["value"], "unknown")
            if old["activity"]["at"] is not None:
                self.assertEqual(row["activity"]["lastKnownAt"], old["activity"]["at"])

    def test_current_native_rows_renew_only_their_own_bound_and_namespace_is_exact(self):
        original = unsaved()
        self.watch.sample(original)
        self.now = RUNTIME_ONLY_RETENTION_MS - 1
        self.watch.sample(original)
        self.now += 2
        self.watch.sample(missing(original))
        self.assertEqual(len(self.watch.previous["sessions"]), 1)
        changed = copy.deepcopy(original)
        source = changed["sources"][0]
        source["configHome"] += "-other"
        source["namespace"] = store_namespace(source["provider"], source["configHome"],
                                              source["configHomeKind"], changed["host"]["uid"])
        for row in changed["sessions"]:
            row["identity"]["namespace"] = changed["sources"][0]["namespace"]
        self.watch.sample(changed)
        self.assertEqual(len(self.watch.retention.deadlines), 1)
        self.assertEqual(self.watch.previous["sessions"][0]["identity"],
                         changed["sessions"][0]["identity"])


if __name__ == "__main__":
    unittest.main()
