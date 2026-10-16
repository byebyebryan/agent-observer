"""Actual-value provenance without changing public full-inventory semantics."""

import copy
import unittest
from types import MappingProxyType
from unittest.mock import patch

from test_service_state import provider_snapshot

from agent_observer import timing
from agent_observer.activity import codex_activity, codex_outcome
from agent_observer.contract import identity_key
from agent_observer.observation_engine import ObservationEngine
from agent_observer.observation_support import SUPPORT_FIELDS, support_matches
from agent_observer.provider import profile_for
from agent_observer.workspace import context


class ObservationSupportTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.value = provider_snapshot("codex")
        self.value["sessions"] = [self.value["sessions"][0]]
        self.engine = self.make_engine()

    def make_engine(self, incarnation="service-fixture"):
        source = self.value["sources"][0]
        return ObservationEngine(
            host_scope="fixture", configs={"codex": (source["configHome"], source["configHomeKind"])},
            uid=1000, clock=lambda: self.now, wall_clock=lambda: 1700000000000,
            collection_id=lambda: "00000000-0000-4000-8000-000000000001",
            native_hostname="fixture-host", profiles={"codex": profile_for("codex")},
            support_incarnation=incarnation)

    def sample(self, component="runtime", *, value=None, ttl=10000, runtime_ttl=None,
               fold=False, engine=None, bind_timing=False):
        value = copy.deepcopy(self.value if value is None else value)
        if component == "history" and not fold:
            value["sources"][0]["coverage"]["runtime"].update(status="unavailable", reason="metadata_only")
        if bind_timing:
            for row in value["sessions"]:
                row["lastUpdated"] = timing.codex_updated({"updatedAt": 12}, observed_at=20000)
                row["latestTurn"] = timing.codex_turn({"data": []}, observed_at=20000)
                for name in ("lastUpdated", "latestTurn"):
                    row[name]["receipt"] = {"component": component, "sampledBoottimeMs": self.now,
                                            "observedBoottimeMs": self.now, "contextGeneration": 0}
            value["sources"][0]["capabilities"]["timing"] = {"lastUpdated": True, "latestTurn": True}
        return (engine or self.engine).accept("codex", component, value, sampled_ms=self.now,
                                            ttl_ms=ttl, runtime_ttl_ms=runtime_ttl)

    def key(self, row=None):
        return identity_key((row or self.value["sessions"][0])["identity"])

    def support(self, name, row=None):
        return self.engine.projection_support[self.key(row)][name]

    def matches(self, token, engine=None):
        engine = engine or self.engine
        return support_matches(token, engine.source_meta("codex"),
                               service_id=engine.support_incarnation, now_ms=self.now)

    def turn(self, status="completed", start=1, end=2):
        value = copy.deepcopy(self.value)
        payload = {"data": [{"status": status, "startedAt": start, "completedAt": end,
                             "items": [], "itemsView": "notLoaded"}]}
        value["sessions"][0]["activity"] = codex_activity(payload)
        outcome = codex_outcome(payload)
        value["sessions"][0]["outcome"] = {**outcome, "clock": "native" if outcome["observedAt"] is not None else None}
        return value

    def other_identity(self, value=None):
        value = copy.deepcopy(self.value if value is None else value)
        row = value["sessions"][0]
        row["identity"]["nativeId"] = row["nativeIds"]["threadId"] = "00000000-0000-4000-8000-000000000099"
        return value

    def test_tokens_are_exact_detached_samples_and_receipts_stay_unchanged(self):
        value = self.turn()
        value["sessions"][0]["workspace"] = context(value["sessions"][0]["cwd"], {"roots": [], "projects": []})
        self.sample("history", value=value, fold=True, bind_timing=True)
        fields = self.engine.projection_support[self.key()]
        self.assertEqual(set(fields), set(SUPPORT_FIELDS))
        for name in SUPPORT_FIELDS:
            self.assertIsNotNone(fields[name], name)
            self.assertTrue(self.matches(fields[name]), name)
            self.assertEqual(set(fields[name]), {"serviceId", "provider", "namespace", "contextGeneration",
                                                "component", "accepted", "sampledBoottimeMs", "expiresBoottimeMs"})
        self.assertEqual(fields["runtime"]["component"], "runtime")
        self.assertEqual(fields["workspace"]["component"], "history")
        self.assertEqual(fields["latestTurn"]["component"], "history")
        self.assertNotIn("data", self.engine.receipts["codex"]["runtime"].public())
        self.assertNotIn("support", str(self.engine.snapshot))
        original = copy.deepcopy(fields)
        fields["runtime"]["accepted"] = 100
        self.engine.publish()
        self.assertEqual(self.engine.projection_support[self.key()], original)

    def test_unrelated_equal_valued_receipt_does_not_renew_retained_fields(self):
        self.sample(value=self.turn())
        original = copy.deepcopy(self.engine.projection_support[self.key()])
        self.now += 1
        value = self.other_identity(self.turn())
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.sample(value=value)
        retained = next(row for row in self.engine.snapshot["sessions"] if self.key(row) == self.key())
        self.assertIn("retained_after_gap", retained["metadataIssues"])
        self.assertEqual(self.engine.projection_support[self.key()], original)
        self.assertFalse(self.matches(self.support("kind")))
        self.assertEqual(self.engine.projection_census["codex"]["identities"], (self.key(value["sessions"][0]),))
        # A genuinely fresh equal-valued observation may establish the fact again.
        self.now += 1
        self.sample(value=self.turn())
        self.assertTrue(self.matches(self.support("kind")))
        self.assertNotEqual(self.support("kind"), original["kind"])

    def test_upstream_retained_row_is_never_an_actual_new_census_observation(self):
        self.sample()
        original = copy.deepcopy(self.engine.projection_support[self.key()])
        retained = copy.deepcopy(self.value)
        retained["sessions"][0]["metadataIssues"].append("retained_after_gap")
        self.now += 1
        self.sample(value=retained)
        self.assertEqual(self.engine.projection_support[self.key()], original)
        self.assertFalse(self.matches(self.support("runtime")))
        self.assertEqual(self.engine.projection_census["codex"]["identities"], ())
        self.assertEqual(self.engine.projection_census["codex"]["status"], "partial")

    def test_history_kind_fallback_keeps_the_actual_history_support(self):
        history = copy.deepcopy(self.value)
        history["sessions"][0]["kind"] = "system"
        self.sample("history", value=history)
        expected = copy.deepcopy(self.support("kind"))
        self.now += 1
        runtime = copy.deepcopy(self.value)
        runtime["sessions"][0]["kind"] = "unknown"
        self.sample(value=runtime)
        self.assertEqual(self.engine.snapshot["sessions"][0]["kind"], "system")
        self.assertEqual(self.support("kind"), expected)
        self.assertEqual(self.support("runtime")["component"], "runtime")
        self.now += 1
        runtime["sessions"][0]["kind"] = "user"
        self.sample(value=runtime)
        self.assertEqual(self.engine.snapshot["sessions"][0]["kind"], "user")
        self.assertEqual(self.support("kind")["component"], "runtime")

    def test_saved_identity_merge_does_not_become_runtime_sample_support(self):
        self.sample("history")
        self.now += 1
        value = copy.deepcopy(self.value)
        value["sessions"][0]["hasSavedHistory"] = False
        value["sessions"][0]["inventory"] = "live"
        self.sample(value=value)
        self.assertTrue(self.engine.snapshot["sessions"][0]["hasSavedHistory"])
        self.assertEqual(self.support("savedIdentity")["component"], "history")
        self.assertEqual(self.support("runtime")["component"], "runtime")

    def test_activity_uses_winner_even_when_its_event_clock_is_older(self):
        self.sample(value=self.turn(start=10, end=20))
        self.now += 1
        self.sample("history", value=self.turn(start=1, end=2), ttl=1000)
        expected = copy.deepcopy(self.support("activity"))
        self.assertEqual(self.engine.snapshot["sessions"][0]["activity"]["at"], 2000)
        self.assertEqual(expected["component"], "history")
        self.now += 1001
        self.engine.expire()
        row = self.engine.snapshot["sessions"][0]
        self.assertEqual(row["activity"]["lastKnownAt"], 2000)
        self.assertEqual(self.support("activity"), expected)
        self.assertFalse(self.matches(expected))
        self.assertTrue(self.matches(self.support("runtime")))

    def test_runtime_activity_winner_uses_runtime_support(self):
        self.sample("history", value=self.turn(start=10, end=20))
        self.now += 1
        self.sample(value=self.turn(start=1, end=2))
        self.assertEqual(self.engine.snapshot["sessions"][0]["activity"]["at"], 2000)
        self.assertEqual(self.support("activity")["component"], "runtime")

    def test_pending_outcome_support_survives_expiry_without_restoring_terminal(self):
        for older, newer in (("history", "runtime"), ("runtime", "history")):
            with self.subTest(newer=newer):
                self.setUp()
                self.sample(older, value=self.turn())
                self.now += 1
                self.sample(newer, value=self.turn("inProgress", 3, None), ttl=1000)
                row = self.engine.snapshot["sessions"][0]
                token = copy.deepcopy(self.support("outcome"))
                self.assertEqual(row["outcome"]["reason"], "turn_in_progress")
                self.assertEqual(token["component"], newer)
                self.assertTrue(self.matches(token))
                self.now += 1001
                self.engine.expire()
                self.assertEqual(self.engine.snapshot["sessions"][0]["outcome"]["value"], "unknown")
                self.assertEqual(self.support("outcome"), token)
                self.assertFalse(self.matches(token))

    def test_terminal_outcome_assignment_copies_history_support(self):
        self.sample(value=self.turn())
        self.now += 1
        self.sample("history", value=self.turn(start=3, end=4))
        self.assertEqual(self.engine.snapshot["sessions"][0]["outcome"]["observedAt"], 4000)
        self.assertEqual(self.support("outcome")["component"], "history")
        self.assertEqual(self.support("phase")["component"], "runtime")

    def test_history_folded_runtime_keeps_timing_origin_and_independent_lease(self):
        self.sample("history", fold=True, ttl=10000, runtime_ttl=1000, bind_timing=True)
        row = self.engine.snapshot["sessions"][0]
        self.assertEqual(row["latestTurn"]["receipt"]["component"], "history")
        self.assertEqual(self.support("runtime")["component"], "runtime")
        self.assertEqual(self.support("latestTurn")["component"], "history")
        self.now += 1001
        self.engine.expire()
        self.assertFalse(self.matches(self.support("runtime")))
        self.assertTrue(self.matches(self.support("latestTurn")))
        self.assertEqual(self.engine.snapshot["sessions"][0]["latestTurn"]["health"], "current")

    def test_timing_retention_keeps_original_token_and_cannot_borrow_same_key(self):
        self.sample(bind_timing=True)
        original = copy.deepcopy(self.support("lastUpdated"))
        self.now += 1
        gap = copy.deepcopy(self.value)
        gap["sessions"] = []
        gap["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.sample(value=gap)
        self.assertEqual(self.support("lastUpdated"), original)
        self.assertFalse(self.matches(original))
        self.assertEqual(self.engine.snapshot["sessions"][0]["lastUpdated"]["health"], "stale")

    def test_equal_timing_uses_the_original_deterministic_lease_winner(self):
        for history_ttl, expected in ((500, "history"), (2000, "runtime")):
            with self.subTest(history_ttl=history_ttl):
                self.setUp()
                self.sample(ttl=1000, bind_timing=True)
                self.sample("history", ttl=history_ttl, bind_timing=True)
                self.assertEqual(self.engine.snapshot["sessions"][0]["lastUpdated"]["receipt"]["component"], expected)
                self.assertEqual(self.support("lastUpdated")["component"], expected)

    def test_conflicting_equal_order_timing_grants_no_support(self):
        self.sample(bind_timing=True)
        value = copy.deepcopy(self.value)
        for name in ("lastUpdated", "latestTurn"):
            value["sessions"][0][name] = copy.deepcopy(self.engine.snapshot["sessions"][0][name])
            value["sessions"][0][name]["receipt"]["component"] = "history"
        value["sessions"][0]["lastUpdated"]["at"] += 1000
        value["sources"][0]["capabilities"]["timing"] = {"lastUpdated": True, "latestTurn": True}
        self.sample("history", value=value)
        self.assertEqual(self.engine.snapshot["sessions"][0]["lastUpdated"]["health"], "ambiguous")
        self.assertIsNone(self.support("lastUpdated"))

    def test_workspace_support_only_follows_a_chosen_history_workspace(self):
        value = copy.deepcopy(self.value)
        value["sessions"][0]["workspace"] = context(value["sessions"][0]["cwd"], {"roots": [], "projects": []})
        self.sample("history", value=value)
        self.assertEqual(self.support("workspace")["component"], "history")
        self.now += 1
        runtime = copy.deepcopy(self.value)
        runtime["sessions"][0]["cwd"] = "/another/runtime/path"
        self.sample(value=runtime)
        self.assertIsNone(self.engine.snapshot["sessions"][0]["workspace"])
        self.assertIsNone(self.support("workspace"))

    def test_changed_context_invalidates_retained_original_support(self):
        self.sample("history")
        old = copy.deepcopy(self.support("kind"))
        self.now += 1
        changed = self.other_identity()
        changed["sources"][0]["runtime"]["startTicks"] += 1
        changed["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.sample(value=changed)
        self.assertFalse(self.matches(old))
        self.assertEqual(self.support("kind"), old)
        self.assertEqual(self.support("runtime"), None)
        self.assertGreater(self.engine.generations["codex"], old["contextGeneration"])

    def test_complete_census_uses_original_native_rows_and_not_loaded_absence(self):
        self.sample()
        census = self.engine.projection_census["codex"]
        self.assertEqual(census["status"], "complete")
        self.assertEqual(census["identities"], (self.key(),))
        self.assertTrue(self.matches(census["support"]))
        self.now += 1
        empty = copy.deepcopy(self.value)
        empty["sessions"] = []
        self.sample(value=empty)
        self.assertEqual(self.engine.projection_census["codex"]["status"], "complete")
        self.assertEqual(self.engine.projection_census["codex"]["identities"], ())
        self.assertEqual(self.engine.projection_support, {})
        # Saved-history incompleteness cannot become a loaded-only full census.
        self.now += 1
        empty["sources"][0]["coverage"]["saved"].update(status="partial", reason="history_limit")
        self.sample(value=empty)
        self.assertEqual(self.engine.projection_census["codex"]["status"], "partial")

    def test_unresolved_actual_rows_prevent_complete_census(self):
        value = copy.deepcopy(self.value)
        value["sessions"][0]["runtime"].update(value="unknown", health="unavailable", reason="native_read_failed")
        value["sessions"][0]["phase"].update(value="unknown", health="unavailable", reason="native_read_failed")
        value["sessions"][0]["blockedReasons"] = []
        self.sample(value=value)
        self.assertEqual(self.engine.projection_census["codex"]["status"], "partial")
        self.assertIsNone(self.support("runtime"))

    def test_support_prunes_with_receipt_and_published_row_bounds(self):
        self.sample()
        original = self.key()
        self.now += 1
        self.sample(value=self.other_identity())
        self.assertNotIn(original, self.engine._component_support["codex"]["runtime"])
        self.assertNotIn(original, self.engine.projection_support)
        with patch("agent_observer.observation_engine.MAX_SESSIONS", 0):
            self.engine.publish()
        self.assertEqual(self.engine.projection_support, {})
        self.assertEqual(self.engine.projection_census["codex"]["status"], "partial")

    def test_runtime_only_retirement_prunes_private_support(self):
        value = copy.deepcopy(self.value)
        value["sessions"][0].update(hasSavedHistory=False, inventory="live")
        self.sample(value=value, ttl=1000)
        self.now += 1
        gap = copy.deepcopy(value)
        gap["sessions"] = []
        gap["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.sample(value=gap)
        self.assertIn(self.key(), self.engine._component_support["codex"]["runtime"])
        self.now += 1000
        self.engine.expire()
        self.assertEqual(self.engine._component_support["codex"]["runtime"], {})
        self.assertEqual(self.engine.projection_support, {})

    def test_support_checks_incarnation_receipt_tuple_health_and_query_clock(self):
        self.sample()
        token = copy.deepcopy(self.support("runtime"))
        source = self.engine.source_meta("codex")
        for name, replacement in (("serviceId", "other-service"), ("namespace", "other-store"),
                                  ("contextGeneration", 99), ("accepted", 99),
                                  ("accepted", True),
                                  ("sampledBoottimeMs", self.now - 1), ("expiresBoottimeMs", self.now + 1)):
            bad = {**token, name: replacement}
            self.assertFalse(support_matches(bad, source, service_id=self.engine.support_incarnation))
        self.assertFalse(support_matches(token, source, service_id=self.engine.support_incarnation, now_ms=self.now - 1))
        self.assertFalse(support_matches(token, source, service_id=self.engine.support_incarnation, now_ms=token["expiresBoottimeMs"]))
        self.engine.fail("codex", "runtime")
        self.assertFalse(self.matches(token))
        self.assertEqual(self.engine.projection_census["codex"]["status"], "unavailable")

    def test_matcher_accepts_immutable_metadata_and_rejects_malformed_values(self):
        self.sample()
        token = copy.deepcopy(self.support("runtime"))
        source = self.engine.source_meta("codex")
        immutable = MappingProxyType({**source, "components": tuple(MappingProxyType(r) for r in source["components"])})
        self.assertTrue(support_matches(MappingProxyType(token), immutable,
                                        service_id=self.engine.support_incarnation, now_ms=self.now))
        for bad in (None, [], 0, {}, {**token, "component": []}, {**token, "accepted": None},
                    {**token, "sampledBoottimeMs": "15000"}, {**token, "expiresBoottimeMs": None}):
            self.assertFalse(support_matches(bad, source, service_id=self.engine.support_incarnation))
        for bad in (None, [], 0, {}, {**source, "components": None},
                    {**source, "components": [None]}, {**source, "contextGeneration": None}):
            self.assertFalse(support_matches(token, bad, service_id=self.engine.support_incarnation))
        for bad_clock in (False, "15000", -1, [], {}):
            self.assertFalse(support_matches(token, source, service_id=self.engine.support_incarnation, now_ms=bad_clock))

    def test_disabled_support_preserves_public_snapshot_receipt_and_revision_parity(self):
        plain = self.make_engine(None)
        for component, value, fold in (("history", self.turn(), True),
                                       ("runtime", self.other_identity(self.turn()), False)):
            self.sample(component, value=value, fold=fold, engine=plain)
            self.sample(component, value=value, fold=fold)
            self.now += 1
            self.assertEqual(plain.snapshot, self.engine.snapshot)
            self.assertEqual(plain.revision, self.engine.revision)
            self.assertEqual(plain.source_meta("codex"), self.engine.source_meta("codex"))
        self.now += 10001
        plain.expire()
        self.engine.expire()
        self.assertEqual(plain.snapshot, self.engine.snapshot)
        self.assertEqual(plain.projection_support, {})
        self.assertEqual(plain.projection_census, {})


if __name__ == "__main__":
    unittest.main()
