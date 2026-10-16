"""Projection authority, original horizons, field provenance and bounded failure."""

import copy
import unittest
import uuid

from test_service_contract import fixture
from test_service_state import provider_snapshot as _provider_snapshot

from agent_observer.active_contract import validate_frame
from agent_observer.active_feed import ActiveFeedProjector
from agent_observer.contract import canonical, identity_key
from agent_observer.service_state import ServiceState


def provider_snapshot(provider):
    value = _provider_snapshot(provider)
    value["sessions"] = value["sessions"][:1]
    return value


class ActiveProjectionTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        value = fixture()
        self.state = ServiceState(
            host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000, clock=lambda: self.now, boot_id=value["bootId"],
            clock_domain=value["clockDomain"],
        )

    def accept(self, value=None, *, component="runtime", ttl=5000):
        self.state.attempt("codex", component)
        self.state.accept("codex", component, value or provider_snapshot("codex"),
                          sampled_ms=self.now, ttl_ms=ttl)
        return self.state.active_frame("status", 1)

    def scope(self, frame=None):
        return (frame or self.state.active_frame("status", 1))["projection"]["scopes"][0]

    def partial_missing(self):
        value = provider_snapshot("codex")
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"]["status"] = "partial"
        value["sources"][0]["coverage"]["saved"]["status"] = "partial"
        value["sources"][0]["sourceHealth"] = "partial"
        value["sourceHealth"] = "partial"
        return value

    def test_warming_is_not_complete_empty(self):
        frame = self.state.active_frame("status", 1)
        self.assertIsNone(frame["projection"])
        self.assertEqual(frame["state"], "warming")
        self.assertEqual(self.state.active_projector.generations, 0)

    def test_current_selected_body_and_complete_scope(self):
        frame = self.accept()
        self.assertEqual(len(frame["projection"]["sessions"]), 1)
        scope = self.scope(frame)
        self.assertEqual(scope["coverage"]["status"], "complete")
        self.assertTrue(scope["coverage"]["supports"])
        self.assertEqual(len(scope["members"]), 1)
        self.assertEqual(scope["uncertain"], [])
        self.assertEqual(scope["nonmembers"], [])
        self.assertEqual(frame["projection"]["sessions"][0], self.state.snapshot["sessions"][0])
        self.assertNotIn("snapshot", frame)
        validate_frame(frame)

    def test_status_exports_are_owned_and_project_only_once(self):
        first = self.accept()
        generation = self.state.active_projector.generations
        for _ in range(4):
            other = self.state.active_frame("status", 1)
            other["projection"]["sessions"][0]["title"] = "changed by caller"
            other["projection"]["scopes"][0]["coverage"]["supports"].clear()
        self.assertEqual(self.state.active_projector.generations, generation)
        self.assertEqual(self.state.active_frame("status", 1)["projection"], first["projection"])
        self.assertIsNone(self.state.active_frame("heartbeat", 2)["projection"])

    def test_history_acceptance_projects_reconciled_view_only_once(self):
        self.accept(component="history")
        self.assertEqual(self.state.revision, 1)
        self.assertEqual(self.state.active_projector.generations, 1)
        self.assertEqual(self.state.receipts["codex"]["runtime"].accepted, 1)

    def test_partial_missing_identity_is_uncertain_without_sliding_horizon(self):
        first = self.accept()
        support = self.scope(first)["members"][0]["fieldSupports"]["runtime"]
        for _ in range(2):
            self.now += 100
            frame = self.accept(self.partial_missing())
            scope = self.scope(frame)
            self.assertEqual(frame["projection"]["sessions"], [])
            self.assertEqual(scope["coverage"]["status"], "partial")
            self.assertEqual(scope["nonmembers"], [])
            self.assertEqual(scope["uncertain"][0]["priorSupport"], support)
            self.assertEqual(scope["uncertain"][0]["horizonBoottimeMs"], support["expiresBoottimeMs"])

    def test_pruned_bookkeeping_grants_no_retirement(self):
        self.accept(ttl=1000)
        self.now += 1001
        frame = self.accept(self.partial_missing())
        scope = self.scope(frame)
        self.assertEqual(scope["coverage"]["status"], "partial")
        self.assertEqual(scope["uncertain"], [])
        self.assertEqual(scope["nonmembers"], [])

    def test_positive_parked_fact_during_partial_scope_uses_its_own_lease(self):
        self.accept()
        value = provider_snapshot("codex")
        row = value["sessions"][0]
        row["runtime"]["value"] = "parked"
        row["phase"] = None
        row["blockedReasons"] = []
        value["sources"][0]["coverage"]["runtime"]["status"] = "partial"
        self.now += 100
        frame = self.accept(value, ttl=1000)
        scope = self.scope(frame)
        negative = scope["nonmembers"][0]
        self.assertEqual(negative["value"], "parked")
        self.assertEqual(negative["horizonBoottimeMs"], 20000)
        self.assertEqual(negative["supports"][0]["expiresBoottimeMs"], 16100)
        self.now = 16101
        expired = self.state.active_frame("status", 1)
        self.assertEqual(self.scope(expired)["nonmembers"], [])
        self.assertEqual(len(self.scope(expired)["uncertain"]), 1)

    def test_confirmed_kind_exclusion_and_unknown_kind_membership(self):
        self.accept()
        value = provider_snapshot("codex")
        value["sessions"][0]["kind"] = "system"
        self.now += 100
        scope = self.scope(self.accept(value))
        self.assertEqual(scope["nonmembers"][0]["reason"], "excluded_kind")
        self.assertEqual(scope["nonmembers"][0]["value"], "system")
        value["sessions"][0]["kind"] = "unknown"
        self.now += 100
        frame = self.accept(value)
        self.assertEqual(len(frame["projection"]["sessions"]), 1)

    def test_native_runtime_error_stays_member_and_preserves_reason(self):
        value = provider_snapshot("codex")
        row = value["sessions"][0]
        row["phase"].update(value="unknown", health="unsupported", reason="native_runtime_error",
                            observedAt=None, source=None, clock=None)
        row["blockedReasons"] = []
        frame = self.accept(value)
        selected = frame["projection"]["sessions"][0]
        self.assertEqual(selected["runtime"]["value"], "running")
        self.assertEqual(selected["phase"], row["phase"])

    def test_complete_empty_has_authority_without_selected_bodies(self):
        self.accept()
        value = provider_snapshot("codex")
        value["sessions"] = []
        self.now += 100
        frame = self.accept(value)
        self.assertEqual(frame["projection"]["sessions"], [])
        self.assertEqual(self.scope(frame)["coverage"]["status"], "complete")
        self.assertEqual(len(self.scope(frame)["coverage"]["supports"]), 1)
        self.assertEqual(self.scope(frame)["uncertain"], [])

    def test_failed_runtime_is_not_empty_authority(self):
        self.accept()
        self.state.fail("codex", "runtime")
        frame = self.state.active_frame("status", 1)
        self.assertEqual(frame["projection"]["sessions"], [])
        self.assertEqual(self.scope(frame)["coverage"]["status"], "stale")
        self.assertEqual(len(self.scope(frame)["uncertain"]), 1)

    def test_missing_actual_kind_support_is_not_guessed(self):
        self.accept()
        row = self.state.snapshot["sessions"][0]
        supports = copy.deepcopy(self.state.projection_support)
        supports[identity_key(row["identity"])]["kind"] = None
        projector = ActiveFeedProjector(service_id=self.state.service_id)
        projection = projector.accept(
            self.state.snapshot, supports, self.state.projection_census,
            [self.state.source_meta("codex")], revision=1, now_ms=self.now)
        self.assertEqual(projection["sessions"], [])
        self.assertEqual(projection["scopes"][0]["coverage"]["status"], "partial")

    def test_ledger_overflow_fails_scope_and_recovers_with_new_continuity(self):
        self.state.active_projector.max_identities = 1
        first = self.accept()
        original = self.scope(first)["continuity"]
        value = provider_snapshot("codex")
        extra = copy.deepcopy(value["sessions"][0])
        native_id = str(uuid.uuid4())
        extra["identity"]["nativeId"] = native_id
        extra["nativeIds"]["threadId"] = extra["nativeIds"]["sessionTreeRootId"] = native_id
        value["sessions"].append(extra)
        self.now += 100
        failed = self.accept(value)
        scope = self.scope(failed)
        self.assertEqual(scope["coverage"]["reason"], "projection_tracking_capacity")
        self.assertGreater(scope["continuity"], original)
        self.assertEqual(failed["projection"]["sessions"], [])
        self.assertEqual(scope["nonmembers"], [])
        self.assertEqual(len(self.state.snapshot["sessions"]), 2)
        self.now += 100
        recovered = self.accept()
        self.assertGreater(self.scope(recovered)["continuity"], scope["continuity"])
        self.assertEqual(len(recovered["projection"]["sessions"]), 1)

    def test_whole_metadata_budget_failure_is_explicit(self):
        self.state.active_projector.max_ledger_bytes = 1
        frame = self.accept()
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "projection_tracking_capacity")
        self.assertEqual(frame["projection"]["sessions"], [])

    def test_dormant_history_adds_no_transport_or_tracking_entries(self):
        value = provider_snapshot("codex")
        seed = value["sessions"][0]
        for number in range(100):
            row = copy.deepcopy(seed)
            native_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(number)))
            row["identity"]["nativeId"] = native_id
            row["nativeIds"]["threadId"] = row["nativeIds"]["sessionTreeRootId"] = native_id
            row["runtime"]["value"] = "parked"
            row["phase"] = None
            row["blockedReasons"] = []
            value["sessions"].append(row)
        frame = self.accept(value)
        scope = self.scope(frame)
        self.assertEqual(len(self.state.snapshot["sessions"]), 101)
        self.assertEqual(len(frame["projection"]["sessions"]), 1)
        self.assertEqual(scope["nonmembers"], [])
        self.assertEqual(scope["uncertain"], [])
        self.assertEqual(self.state.active_projector._ledger_size()[0], 1)
        self.assertLess(len(canonical(frame).encode()), len(canonical(self.state.frame("status", 1)).encode()))


if __name__ == "__main__":
    unittest.main()
