"""Synthetic Claude target conformance; no provider or collector implementation."""

import copy
import json
import unittest
from pathlib import Path

from agent_observer import public, service_public


FIXTURES = Path(__file__).parent / "fixtures"


def snapshot():
    return json.loads((FIXTURES / "contract-v4/claude-interactive.json").read_text())


def frame():
    value = json.loads((FIXTURES / "service-v2/view.json").read_text())
    value["snapshot"] = snapshot()
    return value


def claude_source(value):
    return next(s for s in value["sources"] if s["provider"] == "claude")


def parked_row(value):
    return next(r for r in value["sessions"] if r["runtime"]["value"] == "parked")


class ClaudeContractAlignmentTest(unittest.TestCase):
    def test_existing_api_and_service_versions_accept_partial_scoped_parked(self):
        value = snapshot()
        self.assertEqual(public.API_VERSION, 2)
        self.assertEqual(public.interface()["schemas"], {"snapshot": 4, "watch": 4})
        self.assertEqual(service_public.interface()["serviceProtocol"], 2)
        self.assertEqual(public.parse_snapshot(public.canonical(value).encode()), value)
        source = claude_source(value)
        self.assertEqual(source["coverage"]["runtime"]["status"], "partial")
        self.assertIn("native_registration_assumed", source["limitations"])
        row = parked_row(value)
        self.assertIsNone(row["phase"])
        self.assertTrue(row["hasSavedHistory"])
        self.assertEqual(public.select(value, row["identity"]), row)

    def test_all_work_phases_and_typed_waits_fit_without_native_worker_fields(self):
        for phase, reasons in (("working", []), ("waiting", []), ("unknown", []),
                               ("blocked", ["approval"]), ("blocked", ["question"]),
                               ("blocked", ["approval", "question"])):
            with self.subTest(phase=phase, reasons=reasons):
                value = snapshot()
                row = next(r for r in value["sessions"] if r["identity"]["provider"] == "claude"
                           and r["runtime"]["value"] == "running")
                row["phase"].update(value=phase, health="current")
                row["blockedReasons"] = reasons
                public.validate_snapshot(value)
                self.assertFalse({"pid", "attachment", "job", "worker"}.intersection(row))

    def test_reason_codes_are_extensible_but_wire_fields_and_scope_are_strict(self):
        value = snapshot()
        parked_row(value)["runtime"]["reason"] = "future_native_predicate_reason"
        claude_source(value)["limitations"].append("future_source_limitation")
        public.validate_snapshot(value)
        for change in (
            lambda v: parked_row(v).update(pid=123),
            lambda v: claude_source(v)["coverage"]["runtime"].update(scope="interactive_sessions"),
            lambda v: v.update(schemaVersion=5),
        ):
            value = snapshot()
            change(value)
            with self.assertRaises(public.ContractError):
                public.validate_snapshot(value)

    def test_parked_requires_saved_identity_null_phase_and_empty_blocked_reasons(self):
        for change in (
            lambda r: r.update(hasSavedHistory=False),
            lambda r: r.update(phase=copy.deepcopy(snapshot()["sessions"][1]["phase"])),
            lambda r: r.update(blockedReasons=["question"]),
            lambda r: r["runtime"].update(health="stale"),
        ):
            value = snapshot()
            change(parked_row(value))
            with self.assertRaises(public.ContractError):
                public.validate_snapshot(value)

    def test_watch_and_service_resync_preserve_the_same_snapshot(self):
        value = snapshot()
        watch = {"schemaVersion": 4, "streamId": "00000000-0000-0000-0000-000000000020",
                 "revision": 1, "kind": "snapshot", "sampledAt": value["collectedAt"],
                 "reason": "synthetic_contract_example", "snapshot": value}
        self.assertEqual(public.parse_watch((public.canonical(watch) + "\n").encode())["snapshot"], value)
        initial = frame()
        parsed = service_public.parse_frame((public.canonical(initial) + "\n").encode(),
                                            expected_host="fixture", expected_uid=1000)
        self.assertEqual(parsed["snapshot"], value)
        guard = service_public.StreamGuard(expected_host="fixture", expected_uid=1000)
        guard.accept(parsed)
        guard.accept({**initial, "sequence": 2, "kind": "gap", "snapshot": None})
        with self.assertRaises(public.ContractError):
            guard.accept({**initial, "sequence": 3, "kind": "view"})
        self.assertEqual(guard.accept({**initial, "sequence": 3, "kind": "resync"})["snapshot"], value)

    def test_parked_cannot_outlive_runtime_lease_and_stale_form_preserves_old_clock(self):
        value = frame()
        runtime = next(c for c in claude_source(value)["components"] if c["name"] == "runtime")
        runtime.update(health="stale", expiresBoottimeMs=14_000)
        with self.assertRaises(public.ContractError):
            service_public.validate_frame(value)
        native = claude_source(value["snapshot"])
        native["coverage"]["runtime"].update(status="unavailable", reason="service_runtime_expired")
        for row in value["snapshot"]["sessions"]:
            if row["identity"]["provider"] != "claude":
                continue
            fact = row["runtime"]
            if fact["value"] != "unknown":
                fact.update(lastKnownValue=fact["value"], value="unknown", health="stale",
                            reason="service_runtime_expired")
            row["phase"] = {"value": "unknown", "observedAt": fact["observedAt"],
                            "source": fact["source"], "health": "stale",
                            "reason": "service_runtime_expired", "clock": fact["clock"]}
            row["blockedReasons"] = []
        service_public.validate_frame(value)
        retained = next(r for r in value["snapshot"]["sessions"]
                        if r["runtime"].get("lastKnownValue") == "parked")
        self.assertEqual(retained["runtime"]["observedAt"], snapshot()["collectedAt"])
        self.assertEqual(retained["phase"]["value"], "unknown")

    def test_current_saved_identity_proof_can_share_runtime_lease_without_history_refresh(self):
        value = frame()
        source = claude_source(value)
        history = next(c for c in source["components"] if c["name"] == "history")
        history.update(health="stale", expiresBoottimeMs=14_000)
        claude_source(value["snapshot"])["coverage"]["saved"].update(
            status="unavailable", reason="service_history_expired")
        for row in value["snapshot"]["sessions"]:
            if row["identity"]["provider"] == "claude":
                activity = row["activity"]
                activity.update(lastKnownAt=activity["at"], at=None, health="stale",
                                reason="service_history_expired")
        service_public.validate_frame(value)
        row = parked_row(value["snapshot"])
        self.assertTrue(row["hasSavedHistory"])
        self.assertIsNone(row["activity"]["at"])
        self.assertIsNotNone(row["activity"]["lastKnownAt"])

    def test_unknown_saved_runtime_and_ordering_need_no_provider_specific_client_policy(self):
        value = snapshot()
        rows = public.ordered_rows(value, providers=["claude"])
        self.assertEqual(rows[0]["phase"]["value"], "blocked")
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["runtime"]["value"] for r in rows], ["running", "parked", "unknown"])
        self.assertEqual(public.listing(value, providers=["claude"])["sources"], value["sources"])
        unknown = rows[-1]
        self.assertTrue(unknown["hasSavedHistory"])
        self.assertEqual(unknown["runtime"]["value"], "unknown")


if __name__ == "__main__":
    unittest.main()
