"""Daemon authority regressions independent of terminals and current provider releases."""

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import test_codex_snapshot as snapshot_test
from test_codex_snapshot import FIRST, SECOND, FakeClient, native
from test_service_state import provider_snapshot

from agent_observer.collection import compose_snapshot, project_source
from agent_observer.contract import ContractError, canonical, parse_snapshot, validate_snapshot
from agent_observer.public import interface
from agent_observer.service_state import ServiceState
from agent_observer.watch import SampledWatch


class CodexAuthorityTest(unittest.TestCase):
    def collect(self, statuses, *, loaded=(), **options):
        records = {sid: {**native(sid), "status": status} for sid, status in statuses.items()}
        client = FakeClient({"data": list(loaded), "nextCursor": None},
                            {"data": list(records.values()), "nextCursor": None})
        client.read_thread = lambda sid: {"thread": records[sid]}
        value = snapshot_test.SnapshotCollectionTest().collect(client, **options)
        value["namespace"] = "sha256:" + "a" * 64
        for row in value["sessions"]:
            row["identity"]["namespace"] = value["namespace"]
        return compose_snapshot(host_scope="host-a", provider_snapshots=[value]), client

    def test_all_parked_startup_keeps_capabilities_and_not_applicable_phase(self):
        value, _ = self.collect({FIRST: {"type": "notLoaded"}})
        row = value["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "parked")
        self.assertIsNone(row["phase"])
        self.assertTrue(row["hasSavedHistory"])
        self.assertEqual(value["sources"][0]["capabilities"]["phase"], ["working", "blocked", "waiting"])
        self.assertEqual(value["sources"][0]["coverage"]["runtime"]["scope"], "daemon_threads")

    def test_active_catalog_row_outside_loaded_list_survives_history_cap(self):
        value, _ = self.collect({FIRST: {"type": "notLoaded"}, SECOND: {"type": "active", "activeFlags": []}}, history_limit=1)
        rows = {r["identity"]["nativeId"]: r for r in value["sessions"]}
        self.assertEqual(rows[SECOND]["runtime"]["value"], "running")
        self.assertEqual(rows[SECOND]["phase"]["value"], "working")
        self.assertEqual(value["sources"][0]["coverage"]["runtime"]["status"], "partial")

    def test_combined_known_waits_are_blocked_with_both_reasons(self):
        value, _ = self.collect({FIRST: {"type": "active", "activeFlags": ["waitingOnUserInput", "waitingOnApproval"]}})
        row = value["sessions"][0]
        self.assertEqual(row["phase"]["value"], "blocked")
        self.assertEqual(row["blockedReasons"], ["approval", "question"])

    def test_unknown_wait_flag_preserves_running_without_guessing_phase(self):
        value, _ = self.collect({FIRST: {"type": "active", "activeFlags": ["futureWait"]}})
        row = value["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "running")
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["blockedReasons"], [])

    def test_missing_status_and_missing_loaded_membership_do_not_prove_parked(self):
        value, _ = self.collect({FIRST: {}})
        self.assertEqual(value["sessions"][0]["runtime"]["value"], "unknown")

    def test_fast_collection_keeps_parked_state_without_conversation_reads(self):
        value, _ = self.collect({FIRST: {"type": "notLoaded"}}, include_history=False)
        self.assertEqual(value["sessions"][0]["runtime"]["value"], "parked")
        self.assertIsNone(value["sessions"][0]["activity"]["at"])

    def test_unreadable_saved_summary_is_unresolved_and_coverage_is_partial(self):
        record = {**native(FIRST), "status": {"type": "notLoaded"}}
        client = FakeClient({"data": [], "nextCursor": None}, {"data": [record], "nextCursor": None})
        client.read_thread = lambda _: {"thread": None}
        result = snapshot_test.SnapshotCollectionTest().collect(client)
        self.assertEqual(result["sessions"][0]["runtimeDisposition"]["value"], "unknown")
        self.assertFalse(result["sessions"][0]["savedIdentity"])
        self.assertFalse(result["coverage"]["daemon"]["complete"])

    def test_classification_budget_cannot_leave_unverified_parked_fact(self):
        with patch("agent_observer.codex_snapshot.MAX_SAVED_CLASSIFICATIONS", 0):
            value, _ = self.collect({FIRST: {"type": "notLoaded"}})
        row = value["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertFalse(row["hasSavedHistory"])
        self.assertIsNotNone(row["phase"])

    def test_bad_catalog_row_does_not_erase_healthy_sibling(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None},
                            {"data": [{"id": "bad"}, native(SECOND)], "nextCursor": None})
        value = snapshot_test.SnapshotCollectionTest().collect(client)
        self.assertEqual({r["identity"]["nativeId"] for r in value["sessions"]}, {FIRST, SECOND})
        self.assertEqual(value["sourceHealth"], "partial")
        self.assertFalse(value["coverage"]["daemon"]["complete"])

    def test_discovery_declares_query_selection_and_bounds(self):
        value, _ = self.collect({FIRST: {"type": "notLoaded"}}, include_history=False)
        discovery = value["sources"][0]["discovery"]
        self.assertEqual(discovery["catalogMode"], "database_only")
        self.assertIn("appServer", discovery["sourceKinds"])
        self.assertIn("subAgentThreadSpawn", discovery["sourceKinds"])
        self.assertEqual(discovery["catalogRows"], 1000)
        self.assertFalse(discovery["historyClocks"])

    def test_read_contract_excludes_actions_and_old_wire(self):
        self.assertEqual(interface()["schemas"], {"snapshot": 4, "watch": 4})
        self.assertNotIn("writeCommands", interface())
        old = (Path(__file__).parent / "fixtures/contract-v3/snapshot.json").read_bytes()
        with self.assertRaises(ContractError):
            parse_snapshot(old)
        with self.assertRaisesRegex(ValueError, "unsupported_provider"):
            project_source({"provider": "claude"})

    def test_phase_and_parked_identity_constraints(self):
        value, _ = self.collect({FIRST: {"type": "active", "activeFlags": []}})
        value["sessions"][0]["runtime"]["value"] = "unknown"
        with self.assertRaisesRegex(ContractError, "phase_runtime_conflict"):
            validate_snapshot(value)
        value, _ = self.collect({FIRST: {"type": "notLoaded"}})
        value["sessions"][0]["hasSavedHistory"] = False
        with self.assertRaisesRegex(ContractError, "parked_without_saved_identity"):
            validate_snapshot(value)

    def state(self, value):
        source = value["sources"][0]
        self.now = 15000
        return ServiceState(host_scope="fixture", configs={"codex": (source["configHome"], source["configHomeKind"])},
                            uid=value["host"]["uid"], clock=lambda: self.now)

    def test_history_native_status_uses_short_runtime_lease_and_expires_null_phase(self):
        value = provider_snapshot("codex")
        row = value["sessions"][0]
        row["runtime"]["value"], row["phase"], row["blockedReasons"] = "parked", None, []
        value["sessions"] = [row]
        state = self.state(value)
        state.attempt("codex", "history")
        state.accept("codex", "history", value, sampled_ms=self.now, ttl_ms=10000, runtime_ttl_ms=1000)
        self.assertEqual(state.frame("view", 1)["snapshot"]["sessions"][0]["runtime"]["value"], "parked")
        self.now += 1001
        current = state.frame("view", 2)["snapshot"]["sessions"][0]
        self.assertEqual(current["runtime"]["value"], "unknown")
        self.assertEqual(current["runtime"]["lastKnownValue"], "parked")
        self.assertEqual(current["phase"]["value"], "unknown")
        self.assertEqual(state.receipts["codex"]["history"].health, "current")

    def test_late_same_component_sample_cannot_restore_old_state(self):
        value = provider_snapshot("codex")
        state = self.state(value)
        state.attempt("codex", "runtime")
        state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=1000)
        before = canonical(state.snapshot)
        self.assertFalse(state.accept("codex", "runtime", value, sampled_ms=self.now - 1, ttl_ms=1000))
        self.assertEqual(canonical(state.snapshot), before)

    def test_watch_retains_expired_parked_as_unknown_with_original_clock(self):
        value, _ = self.collect({FIRST: {"type": "notLoaded"}})
        watch = SampledWatch()
        watch.sample(value)
        missing = copy.deepcopy(value)
        missing["sessions"] = []
        missing["sources"][0]["coverage"]["runtime"]["status"] = "partial"
        row = watch.sample(missing)[-1]["snapshot"]["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertEqual(row["runtime"]["lastKnownValue"], "parked")
        self.assertEqual(row["runtime"]["observedAt"], value["sessions"][0]["runtime"]["observedAt"])
        self.assertEqual(row["phase"]["value"], "unknown")


if __name__ == "__main__":
    unittest.main()
