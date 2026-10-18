"""Pure row selection, source joins and bounded last-T continuity guards."""

from __future__ import annotations

import copy
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

from test_service_contract import fixture as service_fixture
from test_service_state import provider_snapshot

from agent_observer.service_state import ServiceState
from agent_observer.working_set_decisions import WorkingSetDecisions
from agent_observer.working_set_policy import DEFAULT_WINDOW_MS, SampleClock

SERVICE_ID = "00000000-0000-4000-8000-000000000001"
BOOT_ID = "00000000-0000-4000-8000-000000000002"
CLOCK_DOMAIN = "linux-clock-boottime"
PROVIDER = "codex"
NAMESPACE = "scope-a"
CONTEXT_GENERATION = 7
WALL_MS = 1_700_000_000_000
LOWER_MS = 1_000
UPPER_MS = 1_000
ACTIVITY_AT = WALL_MS - 1_000
EXPIRY_MS = 1_000_000_000


def sample_id(number: int) -> str:
    return str(UUID(int=number))


def fixture(
    *,
    identity_number: int = 10,
    sample_number: int = 20,
    provider: str = PROVIDER,
    namespace: str = NAMESPACE,
    context_generation: int = CONTEXT_GENERATION,
    wall_ms: int = WALL_MS,
    lower_ms: int = LOWER_MS,
    upper_ms: int = UPPER_MS,
    event_at: int | None = ACTIVITY_AT,
    now_ms: int = 2_000,
    kind: str = "user",
    runtime_value: str = "running",
    activity_health: str = "current",
    activity_reason: str = "native_conversation_event",
    has_saved_history: bool = True,
    include_activity_support: bool = True,
):
    receipt = {
        "name": "runtime",
        "health": "current",
        "accepted": 1,
        "sampledBoottimeMs": lower_ms,
        "expiresBoottimeMs": EXPIRY_MS,
    }
    source = {
        "provider": provider,
        "namespace": namespace,
        "contextGeneration": context_generation,
        "components": [receipt],
    }
    support = {
        "serviceId": SERVICE_ID,
        "provider": provider,
        "namespace": namespace,
        "contextGeneration": context_generation,
        "component": "runtime",
        "accepted": 1,
        "sampledBoottimeMs": lower_ms,
        "expiresBoottimeMs": EXPIRY_MS,
    }
    clock = SampleClock(
        sample_id=sample_id(sample_number),
        origin_component="runtime",
        service_id=SERVICE_ID,
        provider=provider,
        namespace=namespace,
        context_generation=context_generation,
        boot_id=BOOT_ID,
        clock_domain=CLOCK_DOMAIN,
        lower_boottime_ms=lower_ms,
        wall_ms=wall_ms,
        upper_boottime_ms=upper_ms,
    )
    row = {
        "identity": {
            "hostScope": "fixture",
            "provider": provider,
            "namespace": namespace,
            "nativeIdKind": "thread" if provider == "codex" else "session",
            "nativeId": sample_id(identity_number),
        },
        "kind": kind,
        "hasSavedHistory": has_saved_history,
        "runtime": {"value": runtime_value, "health": "current"},
        "activity": {
            "at": event_at,
            "source": "codex_turn_metadata" if event_at is not None else None,
            "health": activity_health,
            "reason": activity_reason,
        },
        "latestTurn": {
            "value": None,
            "observedAt": WALL_MS,
            "source": "codex_turn_metadata",
            "health": "unsupported",
            "reason": "timing_source_unproved",
            "receipt": None,
        },
    }
    fields = {
        "runtime": support,
        "phase": support,
        "kind": support,
        "savedIdentity": support if has_saved_history else None,
        "activity": support if include_activity_support else None,
        "latestTurn": None,
    }
    return row, fields, source, clock, now_ms


def owner(*, window_ms=DEFAULT_WINDOW_MS, max_identities=4096, max_guard_bytes=1024 * 1024):
    value = WorkingSetDecisions(
        SERVICE_ID,
        window_ms=window_ms,
        max_identities=max_identities,
        max_guard_bytes=max_guard_bytes,
    )
    value.reset_context(PROVIDER, NAMESPACE, CONTEXT_GENERATION)
    return value


def classify(
    decision_owner,
    values,
    *,
    now_ms=None,
    clock_generation=0,
    clock_ceiling=None,
    expected_sample_id=None,
):
    row, fields, source, clock, fixture_now = values
    if clock_ceiling is None:
        clock_ceiling = clock.wall_ms - clock.lower_boottime_ms + 1
    if expected_sample_id is None:
        expected_sample_id = clock.sample_id
    return decision_owner.classify(
        row,
        fields,
        source,
        clock=clock,
        clock_generation=clock_generation,
        clock_ceiling=clock_ceiling,
        now_ms=fixture_now if now_ms is None else now_ms,
        expected_sample_id=expected_sample_id,
    )


class WorkingSetDecisionsTest(unittest.TestCase):
    def test_unknown_kind_and_current_user_kind_have_distinct_eligibility(self):
        decision_owner = owner()
        unknown = fixture(kind="unknown")
        unknown[1]["kind"] = None
        decision = classify(decision_owner, unknown)
        self.assertTrue(decision.eligibility)
        self.assertTrue(decision.active)
        self.assertTrue(decision.selected)

        missing_kind = fixture(kind="user")
        missing_kind[1]["kind"] = None
        decision = classify(owner(), missing_kind)
        self.assertIsNone(decision.eligibility)
        self.assertTrue(decision.active)
        self.assertIsNone(decision.selected)

    def test_current_child_or_system_kind_excludes_even_a_live_runtime(self):
        for kind in ("child", "system"):
            with self.subTest(kind=kind):
                values = fixture(kind=kind)
                result = classify(owner(), values)
                self.assertFalse(result.eligibility)
                self.assertTrue(result.active)
                self.assertFalse(result.selected)
                self.assertEqual(result.negative_kind, "excluded_kind")
                self.assertEqual(result.negative_supports, (values[1]["kind"],))

    def test_active_true_wins_when_recent_is_unknown(self):
        values = fixture(event_at=None, include_activity_support=False)
        result = classify(owner(), values)
        self.assertTrue(result.eligibility)
        self.assertTrue(result.active)
        self.assertIsNone(result.recent.decision)
        self.assertTrue(result.selected)
        self.assertIsNone(result.negative_kind)

    def test_parked_is_false_only_with_current_saved_identity_join(self):
        values = fixture(runtime_value="parked")
        result = classify(owner(), values)
        self.assertFalse(result.active)
        self.assertEqual(len(result.active_supports), 1)  # equal runtime/saved receipt deduplicates

        missing_saved = fixture(runtime_value="parked", has_saved_history=False)
        result = classify(owner(), missing_saved)
        self.assertIsNone(result.active)

        mismatched_saved = fixture(runtime_value="parked")
        mismatched_saved[1]["savedIdentity"] = {**mismatched_saved[1]["runtime"], "accepted": 2}
        result = classify(owner(), mismatched_saved)
        self.assertIsNone(result.active)

    def test_running_waiting_or_blocked_rows_are_active(self):
        for phase in ("waiting", "blocked"):
            with self.subTest(phase=phase):
                values = fixture()
                values[0]["phase"] = {"value": phase, "health": "current"}
                result = classify(owner(), values)
                self.assertTrue(result.active)
                self.assertTrue(result.selected)

    def test_activity_receipt_and_expected_sample_id_are_required(self):
        values = fixture(runtime_value="parked")
        result = classify(owner(), values, expected_sample_id=sample_id(99))
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

        values = fixture(runtime_value="parked")
        values[1]["activity"] = None
        result = classify(owner(), values)
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

    def test_positive_and_negative_recent_keep_current_support_only(self):
        positive = fixture(runtime_value="parked")
        result = classify(owner(), positive, now_ms=2_000)
        self.assertTrue(result.recent.decision)
        self.assertEqual(len(result.recent_supports), 1)  # fixture uses one shared current receipt
        self.assertTrue(result.selected)

        outside = fixture(runtime_value="parked")
        result = classify(owner(), outside, now_ms=DEFAULT_WINDOW_MS + 5_000)
        self.assertFalse(result.recent.decision)
        self.assertEqual(result.recent.reason, "outside_window")
        self.assertEqual(result.negative_kind, "outside_window")
        self.assertIn(outside[1]["activity"], result.negative_supports)
        self.assertFalse(result.selected)

    def test_last_known_activity_never_proves_positive_or_negative(self):
        values = fixture(runtime_value="parked", event_at=None, include_activity_support=False)
        values[0]["activity"].update(
            health="stale",
            reason="active_support_expired",
            lastKnownAt=ACTIVITY_AT,
        )
        result = classify(owner(), values, now_ms=DEFAULT_WINDOW_MS + 100_000)
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

    def test_shared_clock_ceiling_prevents_same_event_from_sliding_later(self):
        decision_owner = owner()
        first = fixture(
            runtime_value="unknown",
            event_at=ACTIVITY_AT,
            lower_ms=1_000,
            upper_ms=40_000,
            now_ms=DEFAULT_WINDOW_MS - 10_000,
        )
        first_k = first[3].wall_ms - first[3].lower_boottime_ms + 1
        first_result = classify(decision_owner, first, now_ms=DEFAULT_WINDOW_MS - 10_000)
        self.assertTrue(first_result.recent.decision)

        later = fixture(
            identity_number=10,
            sample_number=21,
            runtime_value="unknown",
            event_at=ACTIVITY_AT,
            lower_ms=10_000,
            upper_ms=50_000,
            now_ms=DEFAULT_WINDOW_MS + 5_000,
        )
        current_k = later[3].wall_ms - later[3].lower_boottime_ms + 1
        self.assertLess(current_k, first_k)
        result = classify(
            decision_owner,
            later,
            now_ms=DEFAULT_WINDOW_MS + 5_000,
            clock_ceiling=first_k,
        )
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "clock_bracket_overlap")
        self.assertLessEqual(
            result.recent.deadline_lower_boottime_ms,
            first_result.recent.deadline_lower_boottime_ms,
        )

    def test_cutoff_upper_remains_current_sample_bound_with_shared_ceiling(self):
        values = fixture(
            runtime_value="parked",
            lower_ms=1_000,
            upper_ms=5_000,
            now_ms=DEFAULT_WINDOW_MS + 5_000,
        )
        k = values[3].wall_ms - values[3].lower_boottime_ms + 1
        result = classify(
            owner(), values, now_ms=DEFAULT_WINDOW_MS + 5_000, clock_ceiling=k + 10_000
        )
        self.assertEqual(
            result.recent.deadline_upper_boottime_ms,
            values[3].upper_boottime_ms + DEFAULT_WINDOW_MS - (values[3].wall_ms - ACTIVITY_AT) + 1,
        )
        self.assertFalse(result.recent.decision)

    def test_older_activity_timestamp_cannot_prove_outside_window(self):
        decision_owner = owner()
        first = fixture(runtime_value="parked", event_at=WALL_MS - 200)
        self.assertTrue(classify(decision_owner, first, now_ms=2_000).recent.decision)

        older = fixture(
            runtime_value="parked",
            sample_number=21,
            event_at=WALL_MS - DEFAULT_WINDOW_MS - 5,
            lower_ms=2_000,
            upper_ms=2_000,
            now_ms=3_000,
        )
        result = classify(decision_owner, older, now_ms=3_000)
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "activity_timestamp_regression")
        self.assertIsNone(result.recent.deadline_lower_boottime_ms)
        self.assertIsNone(result.recent.deadline_upper_boottime_ms)
        self.assertIsNone(result.negative_kind)

    def test_equal_timestamp_after_clock_step_stays_unknown_until_newer_event(self):
        decision_owner = owner()
        first = fixture(runtime_value="parked", event_at=WALL_MS - 200)
        self.assertTrue(classify(decision_owner, first, now_ms=2_000).recent.decision)

        stepped = fixture(
            sample_number=21,
            runtime_value="parked",
            event_at=WALL_MS - 200,
            lower_ms=2_000,
            upper_ms=2_000,
            now_ms=3_000,
        )
        same = classify(decision_owner, stepped, now_ms=3_000, clock_generation=1)
        self.assertIsNone(same.recent.decision)
        self.assertEqual(same.recent.reason, "clock_discontinuity")

        newer = fixture(
            sample_number=22,
            runtime_value="parked",
            event_at=WALL_MS - 100,
            lower_ms=3_000,
            upper_ms=3_000,
            now_ms=4_000,
        )
        repaired = classify(decision_owner, newer, now_ms=4_000, clock_generation=1)
        self.assertTrue(repaired.recent.decision)
        with self.assertRaisesRegex(ValueError, "clock_generation_regression"):
            classify(decision_owner, newer, now_ms=4_000, clock_generation=0)

    def test_new_identity_after_clock_step_latches_first_timestamp(self):
        decision_owner = owner()
        values = fixture(identity_number=10, runtime_value="parked")
        result = classify(decision_owner, values, now_ms=2_000, clock_generation=1)
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "clock_discontinuity")

        same = fixture(identity_number=10, sample_number=21, runtime_value="parked")
        result = classify(decision_owner, same, now_ms=2_000, clock_generation=1)
        self.assertIsNone(result.recent.decision)

        newer = fixture(
            identity_number=10, sample_number=22, runtime_value="parked", event_at=ACTIVITY_AT + 1
        )
        result = classify(decision_owner, newer, now_ms=2_000, clock_generation=1)
        self.assertTrue(result.recent.decision)

    def test_capacity_failure_latches_until_an_actual_context_change(self):
        decision_owner = owner(max_identities=1)
        first = fixture(identity_number=10, runtime_value="parked")
        self.assertTrue(classify(decision_owner, first).recent.decision)
        second = fixture(identity_number=11, sample_number=21, runtime_value="parked")
        result = classify(decision_owner, second)
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "recent_tracking_capacity")
        self.assertTrue(decision_owner.latched)
        self.assertEqual(decision_owner.guard_count, 0)
        self.assertEqual(decision_owner.guard_bytes, 0)

        self.assertFalse(decision_owner.reset_context(PROVIDER, NAMESPACE, CONTEXT_GENERATION))
        result = classify(decision_owner, first)
        self.assertEqual(result.recent.reason, "recent_tracking_capacity")

        moved = fixture(
            identity_number=10,
            sample_number=22,
            namespace="scope-b",
            context_generation=CONTEXT_GENERATION + 1,
            runtime_value="parked",
        )
        self.assertTrue(decision_owner.reset_context(PROVIDER, "scope-b", CONTEXT_GENERATION + 1))
        result = classify(decision_owner, moved)
        self.assertTrue(result.recent.decision)
        self.assertFalse(decision_owner.latched)

    def test_byte_capacity_latches_and_exact_integer_inputs_are_enforced(self):
        decision_owner = owner(max_guard_bytes=1)
        result = classify(decision_owner, fixture())
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "recent_tracking_capacity")
        self.assertTrue(decision_owner.latched)
        self.assertEqual(decision_owner.guard_count, 0)

        for kwargs in (
            {"window_ms": True},
            {"max_identities": True},
            {"max_guard_bytes": True},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                WorkingSetDecisions(SERVICE_ID, **kwargs)
        with self.assertRaisesRegex(ValueError, "clock_generation_invalid"):
            decision_owner.classify(
                *fixture()[:3],
                clock=fixture()[3],
                clock_generation=True,
                clock_ceiling=fixture()[3].wall_ms - fixture()[3].lower_boottime_ms + 1,
                now_ms=2_000,
                expected_sample_id=fixture()[3].sample_id,
            )

    def test_guard_tracks_full_identity_and_conservative_memory_estimate(self):
        decision_owner = owner()
        first = fixture(identity_number=10)
        classify(decision_owner, first)
        other_identity = fixture(identity_number=11)
        classify(decision_owner, other_identity)
        self.assertEqual(decision_owner.guard_count, 2)
        self.assertGreater(decision_owner.guard_bytes, 0)
        self.assertLessEqual(decision_owner.guard_bytes, decision_owner.max_guard_bytes)

    def test_guard_shares_owned_prefix_and_fits_two_thousand_ascii_identities(self):
        decision_owner = owner()
        for number in range(10_000, 12_000):
            values = fixture(identity_number=number, runtime_value="unknown")
            result = classify(decision_owner, values)
            self.assertTrue(result.recent.decision)

        self.assertEqual(decision_owner.guard_count, 2_000)
        self.assertFalse(decision_owner.latched)
        self.assertLessEqual(decision_owner.guard_bytes, 1024 * 1024)
        keys = tuple(decision_owner._guards)
        self.assertEqual(len(keys), 2_000)
        for key in keys[1:]:
            for index in range(4):
                self.assertIs(key[index], keys[0][index])
        self.assertIs(decision_owner._identity_prefix[0], keys[0][0])
        original_prefix = (
            "fixture",
            PROVIDER,
            NAMESPACE,
            "thread",
        )
        for owned, original in zip(decision_owner._identity_prefix, original_prefix, strict=True):
            self.assertEqual(owned, original)
            self.assertIsNot(owned, original)

    def test_prepaid_table_bound_covers_old_plus_new_size_at_every_resize(self):
        table = {}
        previous_size = sys.getsizeof(table)
        for count in range(1, 4097):
            table[(count,)] = (count, 0)
            current_size = sys.getsizeof(table)
            prepaid = 512 + 128 * count
            self.assertLessEqual(previous_size + current_size, prepaid)
            previous_size = current_size

    def test_quota_refusal_happens_before_owned_copy_or_table_growth(self):
        decision_owner = owner()
        first = fixture(identity_number=10)
        self.assertTrue(classify(decision_owner, first).recent.decision)
        before_keys = tuple(decision_owner._guards.items())
        before_bytes = decision_owner.guard_bytes
        before_table_size = sys.getsizeof(decision_owner._guards)
        decision_owner.max_guard_bytes = before_bytes + 1
        observed = {}
        latch = decision_owner._latch_capacity

        def inspect_before_latch():
            observed["keys"] = tuple(decision_owner._guards.items())
            observed["bytes"] = decision_owner.guard_bytes
            observed["table_size"] = sys.getsizeof(decision_owner._guards)
            return latch()

        second = fixture(identity_number=11, sample_number=21)
        with (
            patch.object(decision_owner, "_latch_capacity", side_effect=inspect_before_latch),
            patch.object(
                WorkingSetDecisions,
                "_owned_ascii",
                side_effect=AssertionError("quota refusal copied an identity string"),
            ) as owned_copy,
        ):
            result = classify(decision_owner, second)

        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "recent_tracking_capacity")
        owned_copy.assert_not_called()
        self.assertEqual(observed["keys"], before_keys)
        self.assertEqual(observed["bytes"], before_bytes)
        self.assertEqual(observed["table_size"], before_table_size)
        self.assertTrue(decision_owner.latched)
        self.assertEqual(decision_owner.guard_count, 0)

    def test_equal_or_older_event_lookup_avoids_owned_identity_copies(self):
        decision_owner = owner()
        first = fixture(identity_number=10)
        self.assertTrue(classify(decision_owner, first).recent.decision)
        same = fixture(identity_number=10, sample_number=21)
        older = fixture(identity_number=10, sample_number=22, event_at=ACTIVITY_AT - 1)
        with patch.object(
            WorkingSetDecisions,
            "_owned_ascii",
            side_effect=AssertionError("existing key lookup copied an identity string"),
        ) as owned_copy:
            self.assertTrue(classify(decision_owner, same).recent.decision)
            regression = classify(decision_owner, older)
        owned_copy.assert_not_called()
        self.assertIsNone(regression.recent.decision)
        self.assertEqual(regression.recent.reason, "activity_timestamp_regression")

    def test_changed_event_credit_is_preflighted_before_value_replacement(self):
        decision_owner = owner()
        first = fixture(identity_number=10)
        self.assertTrue(classify(decision_owner, first).recent.decision)
        before_items = tuple(decision_owner._guards.items())
        before_bytes = decision_owner.guard_bytes
        decision_owner.max_guard_bytes = before_bytes + 1
        observed = {}
        latch = decision_owner._latch_capacity

        def inspect_before_latch():
            observed["items"] = tuple(decision_owner._guards.items())
            observed["bytes"] = decision_owner.guard_bytes
            return latch()

        newer = fixture(identity_number=10, sample_number=21, event_at=ACTIVITY_AT + 1)
        with (
            patch.object(decision_owner, "_latch_capacity", side_effect=inspect_before_latch),
            patch.object(
                WorkingSetDecisions,
                "_owned_ascii",
                side_effect=AssertionError("quota refusal copied an identity string"),
            ) as owned_copy,
        ):
            result = classify(decision_owner, newer)

        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "recent_tracking_capacity")
        owned_copy.assert_not_called()
        self.assertEqual(observed["items"], before_items)
        self.assertEqual(observed["bytes"], before_bytes)
        self.assertTrue(decision_owner.latched)
        self.assertEqual(decision_owner.guard_count, 0)

    def test_guard_prefix_and_native_kind_cannot_attach_to_foreign_identity(self):
        decision_owner = owner()
        first = fixture(identity_number=10)
        self.assertTrue(classify(decision_owner, first).recent.decision)

        foreign_host = copy.deepcopy(first)
        foreign_host[0]["identity"]["hostScope"] = "other-host"
        result = classify(decision_owner, foreign_host)
        self.assertTrue(result.active)
        self.assertTrue(result.selected)
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "identity_scope_mismatch")
        self.assertEqual(decision_owner.guard_count, 1)

        foreign_kind = copy.deepcopy(first)
        foreign_kind[0]["identity"]["nativeIdKind"] = "session"
        result = classify(decision_owner, foreign_kind)
        self.assertIsNone(result.recent.decision)
        self.assertEqual(result.recent.reason, "identity_unproved")
        self.assertEqual(decision_owner.guard_count, 1)

        unicode_host = copy.deepcopy(first)
        unicode_host[0]["identity"]["hostScope"] = "fixture-é"
        result = classify(decision_owner, unicode_host)
        self.assertIsNone(result.selected)
        self.assertEqual(result.recent.reason, "identity_unproved")
        self.assertEqual(decision_owner.guard_count, 1)

    def test_context_generation_cannot_regress_within_provider_namespace(self):
        decision_owner = owner()
        values = fixture(runtime_value="parked")
        self.assertTrue(classify(decision_owner, values).recent.decision)
        with self.assertRaisesRegex(ValueError, "context_regression"):
            decision_owner.reset_context(PROVIDER, NAMESPACE, CONTEXT_GENERATION - 1)
        self.assertEqual(decision_owner.guard_count, 1)
        self.assertTrue(classify(decision_owner, values).recent.decision)

    def test_no_turn_absence_requires_exact_live_latest_turn_sample(self):
        values = fixture(runtime_value="parked", event_at=None, include_activity_support=False)
        row, fields, _, clock, _ = values
        row["activity"].update(health="unavailable", reason="no_conversation_activity")
        row["latestTurn"].update(
            health="current",
            reason="no_native_turn",
            observedAt=WALL_MS,
            receipt={
                "component": "runtime",
                "sampledBoottimeMs": clock.lower_boottime_ms,
                "observedBoottimeMs": clock.lower_boottime_ms,
                "contextGeneration": CONTEXT_GENERATION,
            },
        )
        fields["latestTurn"] = fields["runtime"]
        result = classify(owner(), values)
        self.assertFalse(result.recent.decision)
        self.assertEqual(result.recent.reason, "no_native_turn")
        self.assertEqual(result.negative_kind, "no_activity")
        self.assertIn(fields["latestTurn"], result.negative_supports)
        self.assertFalse(result.selected)

        future_binding = copy.deepcopy(values)
        future_binding[0]["latestTurn"]["receipt"]["observedBoottimeMs"] = clock.upper_boottime_ms + 1
        result = classify(owner(), future_binding)
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

        foreign = list(values)
        result = classify(owner(), foreign, expected_sample_id=sample_id(99))
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

        rejected = copy.deepcopy(values)
        rejected[0]["activity"]["reason"] = "no_conversation_activity"
        rejected[0]["activity"]["health"] = "unavailable"
        rejected[0]["latestTurn"]["reason"] = "native_turn_content_rejected"
        result = classify(owner(), rejected)
        self.assertIsNone(result.recent.decision)
        self.assertIsNone(result.negative_kind)

    def test_zero_window_is_false_without_any_activity_or_clock_authority(self):
        values = fixture(runtime_value="parked", event_at=None, include_activity_support=False)
        result = classify(owner(window_ms=0), values, clock_ceiling=None, expected_sample_id=None)
        self.assertFalse(result.recent.decision)
        self.assertEqual(result.recent.reason, "window_disabled")
        self.assertEqual(result.recent_supports, ())
        self.assertEqual(result.negative_kind, "outside_window")

    def test_context_reset_keeps_global_clock_generation_monotonic(self):
        decision_owner = owner()
        values = fixture(runtime_value="parked")
        classify(decision_owner, values, clock_generation=2)
        self.assertTrue(decision_owner.reset_context(PROVIDER, "scope-b", CONTEXT_GENERATION + 1))
        with self.assertRaisesRegex(ValueError, "clock_generation_regression"):
            classify(
                decision_owner,
                fixture(namespace="scope-b", context_generation=CONTEXT_GENERATION + 1),
                clock_generation=1,
            )

    def test_actual_service_state_supports_join_the_original_worker_sample(self):
        initial = service_fixture()
        now = 15_000
        configs = {
            source["provider"]: (source["configHome"], source["configHomeKind"])
            for source in initial["sources"]
        }
        state = ServiceState(
            host_scope="fixture",
            configs=configs,
            uid=1000,
            clock=lambda: now,
            boot_id=initial["bootId"],
            clock_domain=initial["clockDomain"],
        )
        native = provider_snapshot("codex")
        original_sample_id = native["collectionId"]
        wall_ms = native["collectedAt"]
        native_source = native["sources"][0]
        native_source["capabilities"]["activity"] = True
        native_source["capabilities"]["timing"]["latestTurn"] = True
        row = native["sessions"][0]
        row["activity"] = {
            "at": wall_ms - 1_000,
            "source": "codex_turn_metadata",
            "health": "current",
            "reason": "native_conversation_event",
        }
        row["latestTurn"].update(
            value={
                "id": "fixture-turn",
                "status": "completed",
                "startedAt": wall_ms - 2_000,
                "completedAt": wall_ms - 1_000,
                "durationMs": 1_000,
                "timestampPrecisionMs": 1_000,
            },
            observedAt=wall_ms,
            source="codex_turn_metadata",
            health="current",
            reason="native_latest_turn",
            receipt={
                "component": "history",
                "sampledBoottimeMs": now,
                "observedBoottimeMs": now,
                "contextGeneration": 0,
            },
        )
        state.attempt("codex", "history")
        state.accept("codex", "history", native, sampled_ms=now, ttl_ms=10_000)

        current_row = state.snapshot["sessions"][0]
        current_fields = state.projection_support[
            (
                current_row["identity"]["hostScope"],
                current_row["identity"]["provider"],
                current_row["identity"]["namespace"],
                current_row["identity"]["nativeIdKind"],
                current_row["identity"]["nativeId"],
            )
        ]
        source = state.source_meta("codex")
        self.assertEqual(current_fields["activity"]["component"], "runtime")
        self.assertEqual(current_fields["latestTurn"]["component"], "history")
        clock = SampleClock(
            sample_id=original_sample_id,
            origin_component="history",
            service_id=state.service_id,
            provider=source["provider"],
            namespace=source["namespace"],
            context_generation=source["contextGeneration"],
            boot_id=state.boot_id,
            clock_domain=state.clock_domain,
            lower_boottime_ms=now,
            wall_ms=wall_ms,
            upper_boottime_ms=now,
        )
        decision_owner = WorkingSetDecisions(state.service_id)
        decision_owner.reset_context(
            source["provider"], source["namespace"], source["contextGeneration"]
        )
        result = decision_owner.classify(
            current_row,
            current_fields,
            source,
            clock=clock,
            clock_generation=0,
            clock_ceiling=wall_ms - now + 1,
            now_ms=now + 1,
            expected_sample_id=original_sample_id,
        )
        self.assertTrue(result.eligibility)
        self.assertTrue(result.active)
        self.assertTrue(result.recent.decision)
        self.assertTrue(result.selected)


if __name__ == "__main__":
    unittest.main()
