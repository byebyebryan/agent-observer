"""Independent consumer expectations for quiet streams and component leases."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent_observer.contract import ContractError, identity_key, validate_snapshot
from agent_observer.read_client import human_rows
from agent_observer.service_public import ReadCache, validate_frame

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    value = json.loads((ROOT / "tests/fixtures/service-v2/view.json").read_text())
    for source in value["sources"]:
        for item in source["components"]:
            item["expiresBoottimeMs"] = (20000 if item["name"] == "runtime" else 40000) if source["provider"] == "codex" else 30000
    for row in value["snapshot"]["sessions"]:
        row["activity"] = {"at": 1700000001000, "source": "native_metadata", "health": "current", "reason": "native_snapshot"}
    value["snapshot"]["sessions"][0]["workspace"] = {
        "health": "current", "reason": "workspace_matched", "root": "/fixture", "rootKey": "code",
        "relativePath": "project", "projectKey": "code-project", "repo": None,
    }
    return validate_frame(value)


def cache():
    value = fixture()
    return ReadCache(host_scope="fixture", uid=1000, boot_id=value["bootId"], clock_domain=value["clockDomain"])


class ReadCacheTest(unittest.TestCase):
    def test_public_helper_imports_no_io_collectors_mesh_or_actions(self):
        code = """import sys
from agent_observer.service_public import ReadCache
assert not any(n in sys.modules for n in ('agent_observer.collection',
 'agent_observer.service_runtime','agent_observer.service_client','agent_observer.write_client',
 'agent_observer.codex_snapshot','agent_observer.claude_snapshot','mesh_plus'))
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, check=True, capture_output=True)

    def test_warming_and_positive_empty_are_distinct(self):
        subject = cache()
        value = fixture()
        value.update(kind="status", snapshot=None, state="warming")
        self.assertIsNone(subject.accept(value, now_ms=15000)["snapshot"])
        empty = fixture()
        empty["sequence"] = 2
        empty["snapshot"]["sessions"] = []
        result = subject.accept(empty, now_ms=15000)
        self.assertEqual(result["snapshot"]["sessions"], [])
        self.assertEqual(result["health"], "current")

    def test_runtime_expires_during_silence_without_discarding_history_or_other_provider(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        self.assertEqual(subject.current(19999)["nextExpiryBoottimeMs"], 20000)
        result = subject.current(20000)
        codex = [r for r in result["snapshot"]["sessions"] if r["identity"]["provider"] == "codex"]
        claude = [r for r in result["snapshot"]["sessions"] if r["identity"]["provider"] == "claude"]
        self.assertTrue(all(r["runtime"]["value"] == "unknown" and not r["blockedReasons"] for r in codex))
        self.assertEqual(codex[0]["workspace"], value["snapshot"]["sessions"][0]["workspace"])
        self.assertEqual(claude[0]["runtime"]["value"], "running")
        self.assertEqual(result["health"], "partial")
        self.assertEqual(result["nextExpiryBoottimeMs"], 30000)
        validate_snapshot(result["snapshot"])

    def test_history_expiry_preserves_runtime_but_qualifies_merged_metadata(self):
        subject, value = cache(), fixture()
        for item in value["sources"][0]["components"]:
            item["expiresBoottimeMs"] = 40000 if item["name"] == "runtime" else 20000
        subject.accept(value, now_ms=15000)
        row = subject.current(20000)["snapshot"]["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "running")
        self.assertEqual(row["phase"]["value"], "blocked")
        self.assertIsNone(row["workspace"])
        self.assertEqual(row["activity"]["lastKnownAt"], 1700000001000)
        self.assertEqual(row["activity"]["health"], "stale")

    def test_heartbeat_receipts_never_renew_cached_view(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        heartbeat = copy.deepcopy(value)
        heartbeat.update(sequence=2, kind="heartbeat", snapshot=None, emittedBoottimeMs=19000)
        for source in heartbeat["sources"]:
            for item in source["components"]:
                item.update(sampledBoottimeMs=18000, expiresBoottimeMs=50000)
        subject.accept(heartbeat, now_ms=19000)
        self.assertEqual(subject.current(20000)["snapshot"]["sessions"][0]["runtime"]["value"], "unknown")

    def test_delayed_valid_frame_is_expired_at_receipt(self):
        result = cache().accept(fixture(), now_ms=40000)
        self.assertEqual(result["health"], "stale")
        self.assertIsNone(result["nextExpiryBoottimeMs"])
        self.assertTrue(all(r["runtime"]["value"] == "unknown" for r in result["snapshot"]["sessions"]))

    def test_control_context_and_fault_revoke_only_affected_component_until_new_view(self):
        for changed in (False, True):
            subject, value = cache(), fixture()
            subject.accept(value, now_ms=15000)
            control = copy.deepcopy(value)
            control.update(sequence=2, kind="heartbeat", snapshot=None)
            if changed:
                control["sources"][0]["contextGeneration"] += 1
            else:
                control["sources"][0]["components"][0]["health"] = "stale"
            result = subject.accept(control, now_ms=15000)
            self.assertEqual(result["snapshot"]["sessions"][0]["runtime"]["value"], "unknown")
            self.assertEqual(result["snapshot"]["sessions"][3]["runtime"]["value"], "running")
            self.assertEqual(result["reason"], "read_context_revoked")
            control = copy.deepcopy(value)
            control.update(sequence=3, kind="heartbeat", snapshot=None)
            if changed:
                control["sources"][0]["contextGeneration"] += 1
            self.assertEqual(subject.accept(control, now_ms=15000)["snapshot"]["sessions"][0]["runtime"]["value"], "unknown")
            value["sequence"] = 4
            if changed:
                value["sources"][0]["contextGeneration"] += 1
            self.assertEqual(subject.accept(value, now_ms=15000)["snapshot"]["sessions"][0]["runtime"]["value"], "running")

    def test_regressed_context_cannot_restore_revoked_evidence(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        control = copy.deepcopy(value)
        control.update(sequence=2, kind="heartbeat", snapshot=None)
        control["sources"][0]["contextGeneration"] += 1
        subject.accept(control, now_ms=15000)
        value["sequence"] = 3
        with self.assertRaisesRegex(ContractError, "read_context_regression"):
            subject.accept(value, now_ms=15000)
        self.assertIsNone(subject.current(15000)["snapshot"])

    def test_gap_status_resync_and_terminal_barrier(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        gap = {**value, "sequence": 2, "kind": "gap", "snapshot": None}
        self.assertIsNone(subject.accept(gap, now_ms=15000)["snapshot"])
        status = {**value, "sequence": 3, "kind": "status"}
        self.assertIsNone(subject.accept(status, now_ms=15000)["snapshot"])
        self.assertIsNotNone(subject.accept({**value, "sequence": 4, "kind": "resync"}, now_ms=15000)["snapshot"])
        subject.invalidate()
        self.assertIsNone(subject.current(15000)["snapshot"])
        with self.assertRaisesRegex(ContractError, "read_terminal"):
            subject.accept({**value, "sequence": 5}, now_ms=15000)
        subject.reset()
        self.assertIsNotNone(subject.accept(value, now_ms=15000)["snapshot"])

    def test_invalid_scope_incarnation_sequence_and_clock_revoke_positives(self):
        for mutation in (lambda v: v.update(sequence=3),
                         lambda v: v.update(serviceId="00000000-0000-0000-0000-000000000099"),
                         lambda v: v.update(clockDomain="other"),
                         lambda v: v.update(emittedBoottimeMs=16000)):
            subject, value = cache(), fixture()
            subject.accept(value, now_ms=15000)
            value["sequence"] = 2
            mutation(value)
            with self.assertRaises(ContractError):
                subject.accept(value, now_ms=15000)
            self.assertIsNone(subject.current(15000)["snapshot"])

    def test_bad_clock_and_error_frame_invalidate(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        with self.assertRaisesRegex(ContractError, "read_clock_invalid"):
            subject.current(14999)
        self.assertIsNone(subject.current(15000)["snapshot"])
        subject.reset()
        value.update(kind="error", snapshot=None)
        self.assertIsNone(subject.accept(value, now_ms=15000)["snapshot"])

    def test_saved_rows_survive_unsaved_omission_without_parked_assertion(self):
        subject, value = cache(), fixture()
        row = value["snapshot"]["sessions"][0]
        row["hasSavedHistory"] = False
        subject.accept(value, now_ms=15000)
        result = subject.current(20000)["snapshot"]
        self.assertEqual(len(result["sessions"]), len(value["snapshot"]["sessions"]) - 1)
        self.assertFalse(any(r["runtime"]["value"] == "parked" for r in result["sessions"]))

    def test_age_identity_order_and_last_known_remain_unchanged(self):
        subject, value = cache(), fixture()
        before = copy.deepcopy(value)
        subject.accept(value, now_ms=15000)
        result = subject.current(20000)
        self.assertEqual([identity_key(r["identity"]) for r in result["snapshot"]["sessions"]],
                         [identity_key(r["identity"]) for r in before["snapshot"]["sessions"]])
        self.assertIn("19s", human_rows(result["snapshot"], now_ms=1700000020000))
        self.assertEqual(subject.last_known, before)
        subject.last_known["snapshot"]["sessions"].clear()
        self.assertEqual(subject.last_known, before)
        self.assertEqual(value, before)

    def test_value_renewal_requires_replacement_view_and_selection_reset_clears_cache(self):
        subject, value = cache(), fixture()
        subject.accept(value, now_ms=15000)
        renewal = copy.deepcopy(value)
        renewal.update(sequence=2, viewRevision=2, emittedBoottimeMs=19000)
        for source in renewal["sources"]:
            for item in source["components"]:
                item.update(sampledBoottimeMs=18000, expiresBoottimeMs=50000)
        subject.accept(renewal, now_ms=19000)
        self.assertEqual(subject.current(20000)["snapshot"]["sessions"][0]["runtime"]["value"], "running")
        subject.reset()
        self.assertIsNone(subject.last_known)
        self.assertIsNone(subject.current(20000)["snapshot"])
