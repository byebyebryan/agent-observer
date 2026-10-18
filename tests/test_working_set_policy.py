"""Conservative, source-bound working-set recency decisions."""

import unittest
from dataclasses import replace
from itertools import product

from agent_observer.working_set_policy import (
    DEFAULT_WINDOW_MS,
    MAX_WINDOW_MS,
    SampleClock,
    combine_membership,
    recent_activity,
)

SERVICE_ID = "00000000-0000-4000-8000-000000000001"
BOOT_ID = "00000000-0000-4000-8000-000000000002"
SAMPLE_ID = "00000000-0000-4000-8000-000000000003"
FOREIGN_SAMPLE_ID = "00000000-0000-4000-8000-000000000004"
CLOCK_DOMAIN = "linux-clock-boottime"
WALL_MS = 1_700_000_000_000
ACTIVITY_AT = WALL_MS - 1_000
LOWER_BOOT_MS = 80_000
UPPER_BOOT_MS = 80_000
RECEIPT_EXPIRY_MS = 1_000_000_000
_UNSET = object()


def fixture(*, upper_boottime_ms=UPPER_BOOT_MS):
    source = {
        "provider": "codex",
        "namespace": "scope-a",
        "contextGeneration": 7,
        "components": [
            {
                "name": "runtime",
                "health": "current",
                "accepted": 3,
                "sampledBoottimeMs": LOWER_BOOT_MS,
                "expiresBoottimeMs": RECEIPT_EXPIRY_MS,
            }
        ],
    }
    support = {
        "serviceId": SERVICE_ID,
        "provider": "codex",
        "namespace": "scope-a",
        "contextGeneration": 7,
        "component": "runtime",
        "accepted": 3,
        "sampledBoottimeMs": LOWER_BOOT_MS,
        "expiresBoottimeMs": RECEIPT_EXPIRY_MS,
    }
    clock = SampleClock(
        sample_id=SAMPLE_ID,
        origin_component="runtime",
        service_id=SERVICE_ID,
        provider="codex",
        namespace="scope-a",
        context_generation=7,
        boot_id=BOOT_ID,
        clock_domain=CLOCK_DOMAIN,
        lower_boottime_ms=LOWER_BOOT_MS,
        wall_ms=WALL_MS,
        upper_boottime_ms=upper_boottime_ms,
    )
    activity = {"health": "current", "at": ACTIVITY_AT, "source": "latest_turn"}
    return activity, support, clock, source


def fixture_with_clock_bracket(*, lower, upper, wall, activity_at, receipt_expiry):
    activity, support, clock, source = fixture(upper_boottime_ms=upper)
    support = {
        **support,
        "sampledBoottimeMs": lower,
        "expiresBoottimeMs": receipt_expiry,
    }
    source = {
        **source,
        "components": [
            {
                **source["components"][0],
                "sampledBoottimeMs": lower,
                "expiresBoottimeMs": receipt_expiry,
            }
        ],
    }
    clock = replace(
        clock,
        lower_boottime_ms=lower,
        wall_ms=wall,
        upper_boottime_ms=upper,
    )
    activity = {"health": "current", "at": activity_at, "source": "latest_turn"}
    return activity, support, clock, source


def decide(
    *,
    now_boottime_ms,
    activity=_UNSET,
    support=_UNSET,
    clock=_UNSET,
    source=_UNSET,
    expected_sample_id=SAMPLE_ID,
    window_ms=DEFAULT_WINDOW_MS,
    boot_id=BOOT_ID,
    service_id=SERVICE_ID,
    clock_domain=CLOCK_DOMAIN,
):
    default_activity, default_support, default_clock, default_source = fixture()
    return recent_activity(
        default_activity if activity is _UNSET else activity,
        default_support if support is _UNSET else support,
        default_clock if clock is _UNSET else clock,
        default_source if source is _UNSET else source,
        service_id=service_id,
        boot_id=boot_id,
        clock_domain=clock_domain,
        now_boottime_ms=now_boottime_ms,
        expected_sample_id=expected_sample_id,
        window_ms=window_ms,
    )


class WorkingSetPolicyTest(unittest.TestCase):
    def test_floored_zero_width_bracket_edges_are_conservative_by_one_ms(self):
        activity, support, clock, source = fixture()
        expected_lower = LOWER_BOOT_MS + DEFAULT_WINDOW_MS - 1_000 - 1
        expected_upper = UPPER_BOOT_MS + DEFAULT_WINDOW_MS - 1_000 + 1

        before = decide(now_boottime_ms=expected_lower - 1)
        at_lower = decide(now_boottime_ms=expected_lower)
        before_upper = decide(now_boottime_ms=expected_upper - 1)
        at_upper = decide(now_boottime_ms=expected_upper)

        self.assertEqual((before.decision, before.reason), (True, "recent"))
        self.assertIsNone(at_lower.decision)
        self.assertEqual(at_lower.reason, "clock_bracket_overlap")
        self.assertIsNone(before_upper.decision)
        self.assertEqual(before_upper.reason, "clock_bracket_overlap")
        self.assertEqual((at_upper.decision, at_upper.reason), (False, "outside_window"))
        for result in (before, at_lower, before_upper, at_upper):
            self.assertEqual(result.deadline_lower_boottime_ms, expected_lower)
            self.assertEqual(result.deadline_upper_boottime_ms, expected_upper)

    def test_broad_clock_bracket_keeps_its_overlap_unknown(self):
        _, _, clock, _ = fixture(upper_boottime_ms=LOWER_BOOT_MS + 10_000)
        lower = LOWER_BOOT_MS + DEFAULT_WINDOW_MS - 1_000 - 1
        upper = LOWER_BOOT_MS + 10_000 + DEFAULT_WINDOW_MS - 1_000 + 1

        self.assertTrue(decide(now_boottime_ms=lower - 1, clock=clock).decision)
        middle = decide(now_boottime_ms=(lower + upper) // 2, clock=clock)
        self.assertIsNone(middle.decision)
        self.assertEqual(middle.reason, "clock_bracket_overlap")
        self.assertFalse(decide(now_boottime_ms=upper, clock=clock).decision)
        self.assertEqual(middle.deadline_lower_boottime_ms, lower)
        self.assertEqual(middle.deadline_upper_boottime_ms, upper)

    def test_zero_window_is_false_without_activity_or_clock_evidence(self):
        result = recent_activity(
            None,
            None,
            None,
            None,
            service_id=None,
            boot_id=None,
            clock_domain=None,
            now_boottime_ms=None,
            expected_sample_id=None,
            window_ms=0,
        )
        self.assertEqual((result.decision, result.reason), (False, "window_disabled"))
        self.assertIsNone(result.deadline_lower_boottime_ms)
        self.assertIsNone(result.deadline_upper_boottime_ms)

    def test_default_and_maximum_windows_are_supported(self):
        activity, support, clock, source = fixture()
        default = decide(now_boottime_ms=100_000)
        maximum = recent_activity(
            activity,
            support,
            clock,
            source,
            service_id=SERVICE_ID,
            boot_id=BOOT_ID,
            clock_domain=CLOCK_DOMAIN,
            now_boottime_ms=100_000,
            expected_sample_id=SAMPLE_ID,
            window_ms=MAX_WINDOW_MS,
        )
        self.assertEqual(DEFAULT_WINDOW_MS, 72 * 60 * 60 * 1000)
        self.assertEqual(MAX_WINDOW_MS, 30 * 24 * 60 * 60 * 1000)
        self.assertTrue(default.decision)
        self.assertTrue(maximum.decision)
        self.assertEqual(
            maximum.deadline_lower_boottime_ms, LOWER_BOOT_MS + MAX_WINDOW_MS - 1_000 - 1
        )

    def test_window_requires_exact_integer_in_supported_range(self):
        for invalid in (True, False, -1, MAX_WINDOW_MS + 1, 1.0, "72h"):
            with (
                self.subTest(window_ms=invalid),
                self.assertRaisesRegex(ValueError, "working_set_window_invalid"),
            ):
                decide(now_boottime_ms=100_000, window_ms=invalid)

    def test_missing_stale_and_future_activity_never_prove_recent(self):
        stale = {"health": "stale", "at": None, "lastKnownAt": ACTIVITY_AT, "source": "latest_turn"}
        missing_at = {"health": "current", "at": None, "source": "latest_turn"}
        future = {"health": "current", "at": WALL_MS + 1, "source": "latest_turn"}
        invalid_bool = {"health": "current", "at": True, "source": "latest_turn"}

        for activity in (None, stale, missing_at, future, invalid_bool):
            with self.subTest(activity=activity):
                result = decide(now_boottime_ms=100_000, activity=activity)
                self.assertIsNone(result.decision)
        self.assertEqual(
            decide(now_boottime_ms=100_000, activity=stale).reason, "activity_unavailable"
        )
        self.assertEqual(
            decide(now_boottime_ms=100_000, activity=future).reason, "activity_in_future"
        )

    def test_support_must_match_exact_current_receipt_and_snapshot(self):
        activity, support, clock, source = fixture()
        accepted_mismatch = {**support, "accepted": 2}
        expired_support = {**support, "expiresBoottimeMs": 100_000}

        mismatch = decide(now_boottime_ms=100_000, support=accepted_mismatch)
        expired = decide(now_boottime_ms=100_000, support=expired_support)
        foreign_sample = decide(now_boottime_ms=100_000, expected_sample_id=FOREIGN_SAMPLE_ID)
        missing_reference = decide(now_boottime_ms=100_000, expected_sample_id=None)
        self.assertIsNone(mismatch.decision)
        self.assertIsNone(expired.decision)
        self.assertIsNone(foreign_sample.decision)
        self.assertIsNone(missing_reference.decision)
        self.assertEqual(mismatch.reason, "activity_support_unproved")
        self.assertEqual(expired.reason, "activity_support_unproved")
        self.assertEqual(foreign_sample.reason, "clock_sample_mismatch")
        self.assertEqual(missing_reference.reason, "clock_sample_mismatch")

    def test_history_origin_can_be_mirrored_into_runtime_for_same_sample(self):
        activity, support, clock, source = fixture()
        history_origin = replace(clock, origin_component="history")

        matched = decide(
            now_boottime_ms=100_000,
            activity=activity,
            support=support,
            clock=history_origin,
            source=source,
        )
        wrong_sample = decide(
            now_boottime_ms=100_000,
            activity=activity,
            support=support,
            clock=history_origin,
            source=source,
            expected_sample_id=FOREIGN_SAMPLE_ID,
        )
        self.assertTrue(matched.decision)
        self.assertIsNone(wrong_sample.decision)
        self.assertEqual(wrong_sample.reason, "clock_sample_mismatch")

    def test_clock_incarnation_context_and_structure_mismatches_are_unknown(self):
        activity, support, clock, source = fixture()
        changed_namespace = {**source, "namespace": "scope-b"}
        changed_generation = {**source, "contextGeneration": 8}
        invalid_clocks = (
            replace(clock, lower_boottime_ms=True),
            replace(clock, lower_boottime_ms=90_000, upper_boottime_ms=80_000),
            replace(clock, origin_component=[]),
        )

        cases = (
            ("boot_id", BOOT_ID.replace("0002", "0005")),
            ("service_id", SERVICE_ID.replace("0001", "0005")),
            ("clock_domain", "different-domain"),
        )
        for key, value in cases:
            with self.subTest(scope=key):
                result = decide(now_boottime_ms=100_000, **{key: value})
                self.assertIsNone(result.decision)
        for changed_source in (changed_namespace, changed_generation):
            with self.subTest(source=changed_source):
                result = decide(now_boottime_ms=100_000, source=changed_source)
                self.assertIsNone(result.decision)
                self.assertEqual(result.reason, "clock_context_mismatch")
        for invalid_clock in invalid_clocks:
            with self.subTest(clock=invalid_clock):
                result = decide(now_boottime_ms=100_000, clock=invalid_clock)
                self.assertIsNone(result.decision)
                self.assertEqual(result.reason, "clock_invalid")

    def test_clock_upper_point_cannot_be_in_the_readers_future(self):
        _, _, clock, _ = fixture(upper_boottime_ms=90_000)
        result = decide(now_boottime_ms=85_000, clock=clock)
        self.assertIsNone(result.decision)
        self.assertEqual(result.reason, "clock_from_future")

    def test_negative_known_deadlines_remain_available(self):
        old = {"health": "current", "at": 1, "source": "latest_turn"}
        result = decide(now_boottime_ms=100_000, activity=old)
        self.assertFalse(result.decision)
        self.assertLess(result.deadline_lower_boottime_ms, 0)
        self.assertLess(result.deadline_upper_boottime_ms, 0)

    def test_cutoff_out_of_range_with_valid_joined_inputs_is_unknown(self):
        max_safe = 9_007_199_254_740_991
        lower_clock = 9_007_199_254_730_991
        upper_clock = 9_007_199_254_731_001
        now = 9_007_199_254_731_091
        receipt_expiry = 9_007_199_254_740_990
        wall = 1_700_000_000_000
        activity_at = 1_699_999_999_000
        window = 259_200_000
        activity, support, clock, source = fixture_with_clock_bracket(
            lower=lower_clock,
            upper=upper_clock,
            wall=wall,
            activity_at=activity_at,
            receipt_expiry=receipt_expiry,
        )

        expected_lower = lower_clock + window - (wall - activity_at) - 1
        expected_upper = upper_clock + window - (wall - activity_at) + 1
        self.assertEqual(expected_lower, 9_007_199_513_929_990)
        self.assertEqual(expected_upper, 9_007_199_513_930_002)
        self.assertGreater(expected_lower, max_safe)
        self.assertGreater(expected_upper, max_safe)

        result = decide(
            now_boottime_ms=now,
            activity=activity,
            support=support,
            clock=clock,
            source=source,
            window_ms=window,
        )

        self.assertIsNone(result.decision)
        self.assertEqual(result.reason, "cutoff_out_of_range")
        self.assertIsNone(result.deadline_lower_boottime_ms)
        self.assertIsNone(result.deadline_upper_boottime_ms)

    def test_upper_cutoff_alone_out_of_range_invalidates_both_bounds(self):
        max_safe = 9_007_199_254_740_991
        window = DEFAULT_WINDOW_MS
        lower_clock = max_safe - window + 999
        activity, support, clock, source = fixture_with_clock_bracket(
            lower=lower_clock,
            upper=lower_clock + 1,
            wall=WALL_MS,
            activity_at=ACTIVITY_AT,
            receipt_expiry=max_safe,
        )
        expected_lower = lower_clock + window - 1_000 - 1
        expected_upper = lower_clock + 1 + window - 1_000 + 1
        self.assertEqual(expected_lower, max_safe - 2)
        self.assertEqual(expected_upper, max_safe + 1)

        result = decide(
            now_boottime_ms=lower_clock + 1,
            activity=activity,
            support=support,
            clock=clock,
            source=source,
        )

        self.assertIsNone(result.decision)
        self.assertEqual(result.reason, "cutoff_out_of_range")
        self.assertIsNone(result.deadline_lower_boottime_ms)
        self.assertIsNone(result.deadline_upper_boottime_ms)

    def test_signed_safe_cutoff_endpoints_are_inclusive(self):
        max_safe = 9_007_199_254_740_991
        max_window = DEFAULT_WINDOW_MS
        lower_clock = max_safe - max_window + 999
        activity, support, clock, source = fixture_with_clock_bracket(
            lower=lower_clock,
            upper=lower_clock,
            wall=WALL_MS,
            activity_at=ACTIVITY_AT,
            receipt_expiry=max_safe,
        )
        positive = decide(
            now_boottime_ms=lower_clock,
            activity=activity,
            support=support,
            clock=clock,
            source=source,
        )
        self.assertTrue(positive.decision)
        self.assertEqual(positive.deadline_lower_boottime_ms, max_safe - 2)
        self.assertEqual(positive.deadline_upper_boottime_ms, max_safe)

        activity, support, clock, source = fixture_with_clock_bracket(
            lower=0,
            upper=0,
            wall=max_safe,
            activity_at=0,
            receipt_expiry=max_safe,
        )
        negative = decide(
            now_boottime_ms=0,
            activity=activity,
            support=support,
            clock=clock,
            source=source,
            window_ms=1,
        )
        self.assertFalse(negative.decision)
        self.assertEqual(negative.deadline_lower_boottime_ms, -max_safe)
        self.assertEqual(negative.deadline_upper_boottime_ms, -max_safe + 2)

    def test_three_valued_union_truth_table_and_positive_recent_branch(self):
        for eligible, active, recent in product((False, None, True), repeat=3):
            if eligible is False or (active is False and recent is False):
                expected = False
            elif eligible is True and (active is True or recent is True):
                expected = True
            else:
                expected = None
            with self.subTest(eligible=eligible, active=active, recent=recent):
                self.assertIs(combine_membership(eligible, active, recent).decision, expected)

        # Runtime/active membership may be unknown while a proved recent branch
        # still selects the row.
        self.assertTrue(combine_membership(True, True, None).decision)
        self.assertTrue(combine_membership(True, None, True).decision)
        self.assertIsNone(combine_membership(None, False, True).decision)
        self.assertFalse(combine_membership(False, True, True).decision)
        with self.assertRaisesRegex(ValueError, "working_set_evidence_invalid"):
            combine_membership(True, 1, False)


if __name__ == "__main__":
    unittest.main()
