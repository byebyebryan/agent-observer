"""Reusable core with explicit host/clock inputs; native I/O is absent."""

import copy
import unittest

from agent_observer.observation_engine import ObservationEngine
from agent_observer.provider import profile_for
from test_service_contract import fixture
from test_service_state import provider_snapshot


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.wall = 1700000000000
        configs = {s["provider"]: (s["configHome"], s["configHomeKind"])
                   for s in fixture()["sources"]}
        self.engine = ObservationEngine(host_scope="fixture", configs=configs, uid=1000,
                                        clock=lambda: self.now, wall_clock=lambda: self.wall,
                                        collection_id=lambda: "00000000-0000-4000-8000-000000000001",
                                        native_hostname="injected-host",
                                        profiles={p: profile_for(p) for p in configs})

    def accept(self, provider, value=None, sampled=None):
        return self.engine.accept(provider, "history", value or provider_snapshot(provider),
                                  sampled_ms=self.now if sampled is None else sampled, ttl_ms=1000)

    def test_core_runs_without_service_and_uses_only_injected_host_clocks(self):
        self.assertIsNone(self.engine.snapshot)
        self.accept("codex")
        value = self.engine.snapshot
        self.assertEqual(value["host"]["nativeHostname"], "injected-host")
        self.assertEqual(value["collectedAt"], self.wall)
        self.assertEqual(value["collectionId"], "00000000-0000-4000-8000-000000000001")
        before = copy.deepcopy(value["sessions"])
        self.wall += 100000
        self.now += 1001
        self.engine.expire()
        after = self.engine.snapshot["sessions"]
        for old, row in zip(before, after, strict=True):
            self.assertEqual(row["runtime"]["value"], "unknown")
            self.assertEqual(row["runtime"]["observedAt"], old["runtime"]["observedAt"])
            if old["activity"]["at"] is not None:
                self.assertEqual(row["activity"]["lastKnownAt"], old["activity"]["at"])

    def test_generic_core_preserves_other_provider_facts_during_failure(self):
        self.accept("codex")
        self.accept("claude")  # Common-contract fixture, never a live adapter.
        prior = copy.deepcopy([r for r in self.engine.snapshot["sessions"]
                               if r["identity"]["provider"] == "claude"])
        self.engine.fail("codex", "runtime")
        rows = self.engine.snapshot["sessions"]
        self.assertTrue(all(r["runtime"]["value"] == "unknown" for r in rows
                            if r["identity"]["provider"] == "codex"))
        self.assertEqual([r for r in rows if r["identity"]["provider"] == "claude"], prior)

    def test_history_sample_publishes_once_with_independent_component_leases(self):
        self.assertTrue(self.engine.accept("codex", "history", provider_snapshot("codex"),
                                           sampled_ms=self.now, ttl_ms=10000,
                                           runtime_ttl_ms=1000))
        self.assertEqual(self.engine.revision, 1)
        receipts = self.engine.receipts["codex"]
        self.assertEqual(receipts["history"].accepted, 1)
        self.assertEqual(receipts["runtime"].accepted, 1)
        self.assertEqual(receipts["history"].expiresBoottimeMs, self.now + 10000)
        self.assertEqual(receipts["runtime"].expiresBoottimeMs, self.now + 1000)
        before = copy.deepcopy(self.engine.snapshot)
        self.now += 1001
        self.engine.expire()
        self.assertEqual(self.engine.revision, 2)
        self.assertEqual(receipts["history"].health, "current")
        self.assertEqual(receipts["runtime"].health, "stale")
        for old, row in zip(before["sessions"], self.engine.snapshot["sessions"], strict=True):
            self.assertEqual(row["runtime"]["value"], "unknown")
            self.assertEqual(row["runtime"]["observedAt"], old["runtime"]["observedAt"])

    def test_rejected_history_sample_does_not_publish_or_refresh_receipts(self):
        self.accept("codex")
        revision = self.engine.revision
        before = copy.deepcopy(self.engine.snapshot)
        accepted = {c: r.accepted for c, r in self.engine.receipts["codex"].items()}
        self.assertFalse(self.accept("codex", sampled=self.now - 1))
        self.assertEqual(self.engine.revision, revision)
        self.assertEqual(self.engine.snapshot, before)
        self.assertEqual({c: r.accepted for c, r in self.engine.receipts["codex"].items()}, accepted)

    def test_older_metadata_cannot_replace_newer_runtime_or_conversation_clock(self):
        self.accept("codex")
        previous = copy.deepcopy(self.engine.snapshot)
        self.assertFalse(self.accept("codex", sampled=self.now - 1))
        self.assertEqual(self.engine.snapshot, previous)

    def test_partial_empty_census_retains_identity_with_stale_original_evidence(self):
        self.accept("codex")
        original = self.engine.snapshot["sessions"][0]
        value = provider_snapshot("codex")
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="fixture_gap")
        value["sources"][0]["coverage"]["saved"].update(status="partial", reason="fixture_gap")
        self.now += 1
        self.accept("codex", value)
        retained = self.engine.snapshot["sessions"][0]
        self.assertEqual(retained["identity"], original["identity"])
        self.assertEqual(retained["runtime"]["value"], "unknown")
        self.assertEqual(retained["runtime"]["observedAt"], original["runtime"]["observedAt"])
        self.assertIn("retained_after_gap", retained["metadataIssues"])
