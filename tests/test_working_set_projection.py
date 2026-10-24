"""Actual engine/support joins and quiet working-set replacement revisions."""

import copy
import unittest
from unittest.mock import patch
from uuid import UUID

from projection_fixture import provider_snapshot
from test_service_contract import fixture

from agent_observer.service_state import ServiceState
from agent_observer.working_set_contract import validate_frame
from agent_observer.working_set_decisions import WorkingSetDecision, WorkingSetDecisions
from agent_observer.working_set_feed import _primary_unresolved_reason
from agent_observer.working_set_ledger import WorkingSetLedger
from agent_observer.working_set_policy import PolicyResult

WALL = 1700000020000


class WorkingSetProjectionTest(unittest.TestCase):
    def setUp(self):
        self.now = 10001
        original = fixture()
        self.state = ServiceState(
            host_scope="fixture",
            configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000,
            clock=lambda: self.now,
            boot_id=original["bootId"],
            clock_domain=original["clockDomain"],
            working_set_window_ms=10000,
        )
        self.counter = 100

    def sample(self, *, runtime="parked", at=WALL - 5000, wall=WALL):
        value = provider_snapshot("codex")
        self.counter += 1
        value.update(collectionId=str(UUID(int=self.counter)), collectedAt=wall)
        row = value["sessions"][0]
        row["runtime"]["value"] = runtime
        if runtime == "parked":
            row["phase"] = None
            row["blockedReasons"] = []
        elif runtime == "unknown":
            row["runtime"].update(
                observedAt=None,
                source=None,
                clock=None,
                health="unavailable",
                reason="not_observed",
            )
            row["phase"].update(
                value="unknown",
                observedAt=None,
                source=None,
                clock=None,
                health="unavailable",
                reason="not_observed",
            )
            row["blockedReasons"] = []
        if at is not None:
            row["activity"].update(
                at=at, health="current", source="codex_rpc", reason="native_timestamp"
            )
            value["sources"][0]["capabilities"]["activity"] = True
        return value

    def accept(self, value=None, *, lower=10000, upper=None):
        self.state.attempt("codex", "runtime")
        self.state.accept(
            "codex",
            "runtime",
            value or self.sample(),
            sampled_ms=lower,
            ttl_ms=100000,
            accepted_boottime_ms=self.now if upper is None else upper,
        )
        return self.state.working_set_frame("status", 1)

    @staticmethod
    def scope(frame):
        return frame["projection"]["scopes"][0]

    @staticmethod
    def key():
        identity = provider_snapshot("codex")["sessions"][0]["identity"]
        return tuple(
            identity[name]
            for name in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
        )

    @staticmethod
    def semantics(frame):
        scope = WorkingSetProjectionTest.scope(frame)
        return {
            "coverage": {
                key: value for key, value in scope["coverage"].items() if key != "reason"
            },
            "sessionIds": [row["identity"]["nativeId"] for row in frame["projection"]["sessions"]],
            "memberCount": len(scope["members"]),
            "uncertainCount": len(scope["uncertain"]),
            "nonmemberCount": len(scope["nonmembers"]),
        }

    def test_recent_parked_and_runtime_unknown_are_selected_with_original_bodies(self):
        for runtime in ("parked", "unknown"):
            value = self.sample(runtime=runtime)
            frame = self.accept(value)
            self.assertEqual(len(frame["projection"]["sessions"]), 1)
            row = frame["projection"]["sessions"][0]
            self.assertEqual(row["runtime"]["value"], runtime)
            self.assertEqual(row["phase"], value["sessions"][0]["phase"])
            member = self.scope(frame)["members"][0]
            self.assertIsNone(member["active"])
            self.assertIsNotNone(member["recent"])
            self.assertEqual(row["activity"]["at"], WALL - 5000)
            validate_frame(frame)

    def test_active_wins_old_or_unknown_activity_and_overlap_is_single_row(self):
        for at in (None, WALL - 100000, WALL - 5000):
            frame = self.accept(self.sample(runtime="running", at=at))
            self.assertEqual(len(frame["projection"]["sessions"]), 1)
            self.assertEqual(self.scope(frame)["coverage"]["status"], "complete")
            self.assertEqual(self.scope(frame)["coverage"]["reason"], "complete_native_census")
            member = self.scope(frame)["members"][0]
            self.assertIsNotNone(member["active"])
            self.assertEqual(member["recent"] is not None, at == WALL - 5000)

    def test_complete_empty_census_is_not_inferred_from_zero_members_alone(self):
        value = self.sample()
        value["sessions"] = []
        frame = self.accept(value)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "complete")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "complete_native_census")
        self.assertEqual(self.semantics(frame), {
            "coverage": {"status": "complete", "supports": [0]},
            "sessionIds": [], "memberCount": 0, "uncertainCount": 0, "nonmemberCount": 0,
        })

    def test_clock_discontinuity_names_primary_cause_without_changing_projection(self):
        self.state.working_set_clocks._generation = 1
        frame = self.accept()
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "clock_discontinuity")
        self.assertEqual(self.semantics(frame), {
            "coverage": {"status": "partial", "supports": []},
            "sessionIds": [], "memberCount": 0, "uncertainCount": 0, "nonmemberCount": 0,
        })

    def test_primary_census_decision_reason_preserves_other_positive_members(self):
        self.state.working_set_clocks._generation = 1
        value = self.sample(runtime="running", at=None)
        parked = copy.deepcopy(value["sessions"][0])
        identifier = str(UUID(int=999))
        parked["identity"]["nativeId"] = identifier
        parked["nativeIds"].update(threadId=identifier, sessionTreeRootId=identifier)
        parked["runtime"].update(value="parked")
        parked["phase"] = None
        parked["blockedReasons"] = []
        parked["activity"].update(
            at=WALL - 5000, health="current", source="codex_rpc", reason="native_timestamp"
        )
        value["sessions"].append(parked)

        frame = self.accept(value)
        scope = self.scope(frame)
        self.assertEqual(scope["coverage"]["status"], "partial")
        self.assertEqual(scope["coverage"]["reason"], "clock_discontinuity")
        self.assertEqual(self.semantics(frame), {
            "coverage": {"status": "partial", "supports": []},
            "sessionIds": [self.sample(runtime="running", at=None)["sessions"][0]["identity"]["nativeId"]],
            "memberCount": 1, "uncertainCount": 0, "nonmemberCount": 0,
        })

    def test_partial_native_census_reason_keeps_positive_member(self):
        value = self.sample(runtime="running", at=None)
        value["sources"][0]["coverage"]["runtime"].update(
            status="partial", reason="native_scan_partial"
        )
        frame = self.accept(value)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "native_scan_partial")
        self.assertEqual(self.semantics(frame)["memberCount"], 1)

    def test_unprojected_census_identity_reports_that_blocker(self):
        frame = self.accept()
        self.state.projection_census["codex"]["identities"] = (
            (*self.key()[:4], str(UUID(int=999))),
        )
        self.state._refresh_working_set(self.now)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "census_identity_unprojected")
        self.assertEqual(self.semantics(frame)["memberCount"], 1)

    def test_unproved_census_support_reports_that_blocker(self):
        self.accept()
        census = self.state.projection_census["codex"]
        census["support"] = {**census["support"], "accepted": census["support"]["accepted"] + 1}
        self.state._refresh_working_set(self.now)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "census_support_unproved")
        self.assertEqual(self.semantics(frame)["memberCount"], 1)

    def test_unproved_eligibility_support_reports_that_blocker(self):
        self.accept(self.sample(runtime="running", at=None))
        self.state.projection_support[self.key()]["kind"] = None
        self.state._refresh_working_set(self.now)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(
            self.scope(frame)["coverage"]["reason"], "eligibility_support_unproved"
        )
        self.assertEqual(self.semantics(frame)["memberCount"], 0)

    def test_unproved_active_support_reports_that_blocker(self):
        self.accept()
        self.now = 20000
        self.state.projection_support[self.key()]["runtime"] = None
        self.state._refresh_working_set(self.now)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "active_support_unproved")
        self.assertEqual(self.semantics(frame)["memberCount"], 0)

    def test_primary_unresolved_reason_uses_smallest_identity_not_input_order(self):
        def unresolved(reason):
            return WorkingSetDecision(
                eligibility=True,
                active=False,
                recent=PolicyResult(None, reason),
                selected=None,
                active_supports=(),
                recent_supports=(),
                negative_kind=None,
                negative_supports=(),
            )

        low = ("fixture", "codex", "scope-a", "thread", str(UUID(int=1)))
        high = ("fixture", "codex", "scope-a", "thread", str(UUID(int=2)))
        census = {"identities": (high, low)}
        classified = {
            high: unresolved("clock_discontinuity"),
            low: unresolved("activity_support_unproved"),
        }
        self.assertEqual(
            _primary_unresolved_reason(census, classified), "activity_support_unproved"
        )

    def test_expired_runtime_source_reports_stale_reason(self):
        self.accept()
        self.now = 110000
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "stale")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "service_source_expired")
        self.assertEqual(self.semantics(frame)["memberCount"], 0)

    def test_quiet_lower_then_upper_cutoff_without_new_observation_or_collection(self):
        first = self.accept()
        member = self.scope(first)["members"][0]
        lower, upper = member["recent"]["lowerBoottimeMs"], member["recent"]["upperBoottimeMs"]
        self.assertEqual((lower, upper), (14999, 15002))
        observation_revision = self.state.revision
        accepted = self.state.receipts["codex"]["runtime"].accepted
        self.now = lower
        uncertain = self.state.working_set_frame("status", 1)
        self.assertEqual(uncertain["projection"]["sessions"], [])
        self.assertEqual(self.scope(uncertain)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(uncertain)["coverage"]["reason"], "clock_bracket_overlap")
        self.assertEqual(len(self.scope(uncertain)["uncertain"]), 1)
        self.assertEqual(self.scope(uncertain)["nonmembers"], [])
        self.assertGreater(uncertain["viewRevision"], first["viewRevision"])
        self.assertEqual(uncertain["observationRevision"], observation_revision)
        self.now = upper
        negative = self.state.working_set_frame("status", 1)
        self.assertEqual(self.scope(negative)["coverage"]["status"], "complete")
        self.assertEqual(self.scope(negative)["coverage"]["reason"], "complete_native_census")
        self.assertEqual(self.scope(negative)["nonmembers"][0]["reason"], "outside_window")
        self.assertEqual(negative["observationRevision"], observation_revision)
        self.assertEqual(self.state.receipts["codex"]["runtime"].accepted, accepted)
        self.assertGreater(negative["viewRevision"], uncertain["viewRevision"])

    def test_cached_reads_are_owned_and_do_not_advance_or_renew(self):
        first = self.accept()
        generations = self.state.working_set_projector.generations
        for _ in range(5):
            exported = self.state.working_set_frame("status", 1)
            exported["projection"]["sessions"].clear()
            exported["projection"]["scopes"][0]["members"].clear()
        self.assertEqual(
            self.state.working_set_frame("status", 1)["projection"], first["projection"]
        )
        self.assertEqual(self.state.working_set_projector.generations, generations)

    def test_same_timestamp_does_not_extend_and_older_timestamp_is_not_negative(self):
        first = self.accept()
        cutoff = self.scope(first)["members"][0]["recent"]["lowerBoottimeMs"]
        self.now = 11001
        same = self.accept(self.sample(wall=WALL + 1000), lower=11000)
        self.assertEqual(self.scope(same)["members"][0]["recent"]["lowerBoottimeMs"], cutoff)
        self.now = 20001
        older = self.accept(self.sample(wall=WALL + 10000, at=WALL - 5001), lower=20000)
        self.assertEqual(older["projection"]["sessions"], [])
        self.assertEqual(self.scope(older)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(older)["coverage"]["reason"], "activity_timestamp_regression")
        self.assertEqual(self.scope(older)["nonmembers"], [])
        self.assertEqual(len(self.scope(older)["uncertain"]), 1)

    def test_runtime_expiry_does_not_hide_independently_recent_row_or_invent_parked_phase(self):
        self.state.attempt("codex", "history")
        value = self.sample()
        value["sessions"][0]["kind"] = "unknown"
        self.state.accept(
            "codex",
            "history",
            value,
            sampled_ms=10000,
            ttl_ms=100000,
            runtime_ttl_ms=2000,
            accepted_boottime_ms=10001,
        )
        # A later runtime-only sample has no activity authority. The selected
        # activity must therefore name the still-current history receipt,
        # rather than borrowing a same-valued expired runtime reference.
        self.now = 10501
        self.state.attempt("codex", "runtime")
        runtime_only = self.sample(at=None, wall=WALL + 500)
        runtime_only["sessions"][0]["kind"] = "unknown"
        self.state.accept(
            "codex",
            "runtime",
            runtime_only,
            sampled_ms=10500,
            ttl_ms=1500,
            accepted_boottime_ms=10501,
        )
        before = self.state.working_set_frame("status", 1)
        self.assertEqual(
            self.scope(before)["members"][0]["recent"]["clock"]["component"], "history"
        )
        self.now = 12000
        frame = self.state.working_set_frame("status", 1)
        row = frame["projection"]["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertIsNotNone(row["phase"])
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertIsNotNone(self.scope(frame)["members"][0]["recent"])

    def test_current_no_turn_requires_original_latest_turn_receipt(self):
        self.accept()
        self.now = 11001
        value = self.sample(at=None, wall=WALL + 1000)
        row = value["sessions"][0]
        row["activity"].update(
            at=None, health="unavailable", source=None, reason="no_conversation_activity"
        )
        row["latestTurn"].update(
            value=None,
            health="current",
            source="codex_rpc",
            reason="no_native_turn",
            observedAt=WALL + 1000,
            receipt={
                "component": "runtime",
                "sampledBoottimeMs": 11000,
                "observedBoottimeMs": 11001,
                "contextGeneration": 0,
            },
        )
        value["sources"][0]["capabilities"]["timing"]["latestTurn"] = True
        frame = self.accept(value, lower=11000)
        self.assertEqual(self.scope(frame)["nonmembers"][0]["reason"], "no_activity")
        self.assertEqual(self.scope(frame)["coverage"]["status"], "complete")

    def test_context_horizon_is_not_union_authority_when_recent_support_outlives_cutoff(self):
        value = self.sample(runtime="running")
        value["sessions"][0]["kind"] = "unknown"
        self.state.attempt("codex", "history")
        self.state.accept(
            "codex",
            "history",
            value,
            sampled_ms=10000,
            ttl_ms=40000,
            runtime_ttl_ms=10000,
            accepted_boottime_ms=10001,
        )
        self.now = 11001
        runtime_only = self.sample(runtime="running", at=None, wall=WALL + 1000)
        runtime_only["sessions"][0]["kind"] = "unknown"
        self.state.attempt("codex", "runtime")
        self.state.accept(
            "codex",
            "runtime",
            runtime_only,
            sampled_ms=11000,
            ttl_ms=9000,
            accepted_boottime_ms=11001,
        )
        first = self.state.working_set_frame("status", 1)
        member = self.scope(first)["members"][0]
        self.assertIsNotNone(member["active"])
        self.assertIsNotNone(member["recent"])
        recent_support = self.scope(first)["supportTable"][member["recent"]["supports"][0]]
        self.assertEqual(recent_support["expiresBoottimeMs"], 50000)
        self.assertEqual(member["recent"]["lowerBoottimeMs"], 14999)
        self.now = 14999
        active = self.state.working_set_frame("status", 1)
        self.assertEqual(len(active["projection"]["sessions"]), 1)
        self.assertIsNone(self.scope(active)["members"][0]["recent"])
        self.assertIsNotNone(self.scope(active)["members"][0]["active"])
        self.now = 20000
        expired = self.state.working_set_frame("status", 1)
        self.assertEqual(expired["projection"]["sessions"], [])
        self.assertNotEqual(self.scope(expired)["coverage"]["status"], "complete")
        self.assertEqual(self.scope(expired)["nonmembers"], [])

    def test_old_and_candidate_ledger_overlap_is_preflighted_before_copy(self):
        self.accept()
        projector = self.state.working_set_projector
        committed = projector._ledger
        self.assertEqual(committed.count, 1)
        projector.max_ledger_bytes = 1

        with patch.object(
            WorkingSetLedger,
            "clone_live",
            autospec=True,
            side_effect=AssertionError("unadmitted candidate root was copied"),
        ) as candidate_copy:
            frame = self.accept(self.sample(wall=WALL + 1000), lower=10000, upper=10001)
        candidate_copy.assert_not_called()
        validate_frame(frame)
        scope = self.scope(frame)
        self.assertEqual(scope["coverage"]["status"], "unavailable")
        self.assertEqual(scope["coverage"]["reason"], "projection_tracking_capacity")
        self.assertEqual(projector._ledger.count, 0)

    def test_unchanged_ledger_entry_is_shared_by_identity_across_replacement(self):
        self.accept()
        projector = self.state.working_set_projector
        committed = projector._ledger
        identity = next(committed.identities())
        atom = committed._entries[identity[4]]
        native_id = str(UUID(int=10_099))
        extra_identity = (*identity[:4], native_id)
        plan = committed.plan_put(
            extra_identity,
            atom.value,
            current_charge=committed.charge,
            limit=projector.max_ledger_bytes,
        )
        committed.put(plan, atom.value)
        original_key = next(key for key in committed._entries if key == native_id)

        self.now += 1
        frame = self.accept(self.sample(wall=WALL + 1000), lower=self.now - 1, upper=self.now)
        validate_frame(frame)
        self.assertIs(projector._ledger._entries[native_id], atom)
        new_key = next(key for key in projector._ledger._entries if key == native_id)
        self.assertIs(new_key, original_key)

    def test_guard_capacity_latch_drops_earlier_recency_but_preserves_independent_active(self):
        self.state.working_set_projector.decisions = WorkingSetDecisions(
            self.state.service_id,
            10000,
            max_guard_bytes=1,
        )
        value = self.sample()
        active = copy.deepcopy(value["sessions"][0])
        identifier = str(UUID(int=999))
        active["identity"]["nativeId"] = identifier
        active["nativeIds"].update(threadId=identifier, sessionTreeRootId=identifier)
        source_row = provider_snapshot("codex")["sessions"][0]
        active["runtime"], active["phase"] = source_row["runtime"], source_row["phase"]
        active["blockedReasons"] = source_row["blockedReasons"]
        value["sessions"].append(active)
        frame = self.accept(value)
        self.assertEqual(
            [r["identity"]["nativeId"] for r in frame["projection"]["sessions"]], [identifier]
        )
        self.assertEqual(self.scope(frame)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(frame)["coverage"]["reason"], "recency_tracking_capacity")
        self.assertIsNone(self.scope(frame)["members"][0]["recent"])
