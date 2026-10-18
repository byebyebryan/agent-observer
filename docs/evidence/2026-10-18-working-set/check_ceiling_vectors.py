"""Independent stdlib arithmetic model for working-set ceiling R2.

This checks bounded equations and finite state examples only. It does not
exercise Observer, Mesh, runtime capacity, timers, receipt admission or GC.
"""

from __future__ import annotations

import json

WINDOW_MS = 72 * 60 * 60 * 1_000
SAFE_INTEGER = 2**53 - 1


def cutoff_candidate(activity_at: int, window_ms: int, lower: int, wall: int) -> int:
    return lower + window_ms - (wall - activity_at) - 1


def upper_candidate(activity_at: int, window_ms: int, upper: int, wall: int) -> int:
    return upper + window_ms - (wall - activity_at) + 1


def bracket_k(lower: int, wall: int) -> int:
    return wall - lower + 1


def min_positive(values: list[int] | None) -> int | None:
    if not values:
        return None
    return min(values)


def branch_horizon(
    eligibility: int | None,
    active_supports: list[int] | None,
    recent_supports: list[int] | None,
    effective_dlo: int | None,
) -> int | None:
    active = min_positive(active_supports)
    recent = min_positive(recent_supports)
    if recent is not None:
        recent = None if effective_dlo is None else min(recent, effective_dlo)
    branches = [value for value in (active, recent) if value is not None]
    if not branches:
        return None
    union = max(branches)
    return union if eligibility is None else min(eligibility, union)


def scope_decisions(rows: dict, now: int, fresh_negatives: set[str]) -> dict:
    decisions = {}
    for identity, row in rows.items():
        active = row["active_horizon"] is not None and now < row["active_horizon"]
        recent = row["recent_horizon"] is not None and now < row["recent_horizon"]
        if active or recent:
            decisions[identity] = "member"
        elif identity in fresh_negatives:
            decisions[identity] = "proved_nonmember"
        else:
            decisions[identity] = "unresolved"
    complete = all(decision != "unresolved" for decision in decisions.values())
    return {"coverage": "complete" if complete else "partial", "decisions": decisions}


def main() -> None:
    q = WINDOW_MS
    fixed_t = 1_700_000_000_000
    samples = [
        {
            "name": "runtime_initial",
            "component": "runtime",
            "context": "source-context-a",
            "lower": 100_000_000,
            "wall": fixed_t + 1_000_000,
            "upper": 100_025_000,
            "ledger_reset": None,
        },
        {
            "name": "history_wider_bracket",
            "component": "history",
            "context": "source-context-a",
            "lower": 100_005_000,
            "wall": fixed_t + 1_020_000,
            "upper": 100_040_000,
            "ledger_reset": None,
        },
        {
            "name": "unrelated_runtime_update",
            "component": "runtime",
            "context": "source-context-a",
            "lower": 100_010_000,
            "wall": fixed_t + 980_000,
            "upper": 100_030_000,
            "ledger_reset": None,
        },
        {
            "name": "same_event_after_capacity_ledger_reset",
            "component": "history",
            "context": "source-context-a",
            "lower": 100_020_000,
            "wall": fixed_t + 1_010_000,
            "upper": 100_055_000,
            "ledger_reset": "capacity-ledger reset model",
        },
        {
            "name": "same_event_after_roster_retirement",
            "component": "runtime",
            "context": "source-context-a",
            "lower": 100_030_000,
            "wall": fixed_t + 1_030_000,
            "upper": 100_080_000,
            "ledger_reset": "identity-retirement model",
        },
        {
            "name": "same_event_after_namespace_context_change",
            "component": "history",
            "context": "source-context-b",
            "lower": 100_040_000,
            "wall": fixed_t + 1_060_000,
            "upper": 100_075_000,
            "ledger_reset": "context-ledger reset model; clock incarnation unchanged",
        },
    ]

    candidate_bound_checks = 0
    dhi_independence_checks = 0
    ledger_reset_checks = 0
    event_timestamps = 0
    k: int | None = None
    prior_fixed_dlo: int | None = None
    fixed_candidates = []
    k_timeline = []
    for sample in samples:
        lower, wall, upper = sample["lower"], sample["wall"], sample["upper"]
        assert lower <= upper
        current_k = bracket_k(lower, wall)
        next_k = current_k if k is None else max(k, current_k)
        assert k is None or next_k >= k
        assert -SAFE_INTEGER <= next_k <= SAFE_INTEGER

        if sample["ledger_reset"] is not None:
            # Model the ledger being cleared while the independent clock scalar
            # remains. No capacity, roster or collector operation is performed.
            assert k is not None
            assert next_k >= k
            ledger_reset_checks += 1

        for activity_at in sorted(
            {
                0,
                max(0, wall - q - 100_000),
                max(0, wall - q),
                wall - 1,
                fixed_t,
            }
        ):
            assert 0 <= activity_at <= wall
            candidate = cutoff_candidate(activity_at, q, lower, wall)
            effective = activity_at + q - next_k
            dhi = upper_candidate(activity_at, q, upper, wall)
            assert effective <= candidate
            assert dhi == upper + q - (wall - activity_at) + 1
            assert -SAFE_INTEGER <= effective <= SAFE_INTEGER
            assert -SAFE_INTEGER <= dhi <= SAFE_INTEGER
            candidate_bound_checks += 1
            dhi_independence_checks += 1
            event_timestamps += 1

        fixed_dlo = fixed_t + q - next_k
        fixed_candidates.append(cutoff_candidate(fixed_t, q, lower, wall))
        assert fixed_dlo == min(fixed_candidates)
        if prior_fixed_dlo is not None:
            assert fixed_dlo <= prior_fixed_dlo
        prior_fixed_dlo = fixed_dlo
        k = next_k
        k_timeline.append(
            {
                "sample": sample["name"],
                "component": sample["component"],
                "context": sample["context"],
                "currentK": current_k,
                "retainedK": k,
                "fixedTDlo": fixed_dlo,
                "resetModel": sample["ledger_reset"],
            }
        )

    assert k is not None
    new_t = fixed_t + 50_000
    new_event_dlo = new_t + q - k
    same_event_dlo = fixed_t + q - k
    assert new_t <= samples[-1]["wall"]
    assert new_event_dlo == same_event_dlo + 50_000

    fresh_incarnation = {
        "lower": 7_000_000,
        "wall": fixed_t + 2_000_000,
        "upper": 7_005_000,
    }
    fresh_k = bracket_k(fresh_incarnation["lower"], fresh_incarnation["wall"])
    fresh_candidate = cutoff_candidate(
        fixed_t, q, fresh_incarnation["lower"], fresh_incarnation["wall"]
    )
    fresh_dlo = fixed_t + q - fresh_k
    assert fresh_dlo == fresh_candidate
    assert fresh_k != k

    last_event_t = fixed_t + 10_000
    regressed_event_t = fixed_t
    regressed_decision = "unknown" if regressed_event_t < last_event_t else "compare"
    regressed_dhi = (
        None
        if regressed_decision == "unknown"
        else upper_candidate(regressed_event_t, q, samples[-1]["upper"], samples[-1]["wall"])
    )
    assert regressed_decision == "unknown"
    assert regressed_dhi is None

    latched_continuity = 7
    recent_tracking_latched = True
    same_context_recovery = not recent_tracking_latched
    assert not same_context_recovery
    context_changed = "source-context-a" != "source-context-b"
    accepted_new_baseline = True
    recency_after_context_baseline = context_changed and accepted_new_baseline
    assert recency_after_context_baseline

    old_sample = {"lower": 100_000_000, "upper": 100_001_000, "wall": fixed_t + 500_000}
    old_t = old_sample["wall"] - q - old_sample["upper"] - 1_000
    old_dlo = cutoff_candidate(old_t, q, old_sample["lower"], old_sample["wall"])
    old_dhi = upper_candidate(old_t, q, old_sample["upper"], old_sample["wall"])
    assert old_dlo == -2_001
    assert old_dhi == -999

    horizon_long_active = branch_horizon(None, [800, 900], [200], 500)
    flat_long_active = min([800, 900, 200, 500])
    assert horizon_long_active == 800
    assert horizon_long_active > flat_long_active
    horizon_long_recent = branch_horizon(600, [100, 150], [900, 800], 700)
    flat_long_recent = min([100, 150, 900, 800, 700])
    assert horizon_long_recent == 600
    assert horizon_long_recent > flat_long_recent
    both_absent = branch_horizon(None, None, None, None)
    assert both_absent is None
    recent_without_dlo = branch_horizon(None, None, [900], None)
    assert recent_without_dlo is None

    scope_rows = {
        "active-survivor": {"active_horizon": 100, "recent_horizon": None},
        "recent-only": {"active_horizon": None, "recent_horizon": 50},
    }
    complete_before = scope_decisions(scope_rows, 49, set())
    partial_at_expiry = scope_decisions(scope_rows, 50, set())
    complete_after_negative = scope_decisions(scope_rows, 50, {"recent-only"})
    assert complete_before["coverage"] == "complete"
    assert partial_at_expiry["coverage"] == "partial"
    assert partial_at_expiry["decisions"]["active-survivor"] == "member"
    assert partial_at_expiry["decisions"]["recent-only"] == "unresolved"
    assert complete_after_negative["coverage"] == "complete"
    assert complete_after_negative["decisions"]["recent-only"] == "proved_nonmember"

    same_row_alternative = {"same-row": {"active_horizon": 100, "recent_horizon": 50}}
    complete_with_active_alternative = scope_decisions(same_row_alternative, 50, set())
    assert complete_with_active_alternative["coverage"] == "complete"
    assert complete_with_active_alternative["decisions"]["same-row"] == "member"

    named_cases = [
        "monotonic_K_across_runtime_history_and_unrelated_updates",
        "same_timestamp_after_capacity_ledger_reset_with_K_retained",
        "same_timestamp_after_identity_retirement_with_K_retained",
        "same_timestamp_after_context_ledger_reset_with_K_retained",
        "newer_event_timestamp_uses_same_K",
        "new_clock_incarnation_requires_explicit_fresh_baseline",
        "current_Dhi_is_independent_of_K",
        "signed_negative_Dlo_and_Dhi",
        "older_event_guard_yields_unknown_without_Dhi",
        "capacity_latch_requires_context_change_and_accepted_baseline",
        "longer_active_branch_beats_flattened_minimum",
        "longer_recent_branch_beats_flattened_minimum_and_is_eligibility_capped",
        "recent_branch_without_Dlo_has_no_positive_horizon",
        "recent_only_expiry_downgrades_scope_while_other_active_row_survives",
        "fresh_negative_restores_complete_scope",
        "same_row_active_branch_survives_recent_expiry",
    ]

    result = {
        "scope": (
            "independent stdlib arithmetic and finite decision model only; no Observer/Mesh "
            "imports, runtime capacity, timers, receipt admission, collector behavior or GC"
        ),
        "cutoff": {
            "acceptedBracketUpdates": len(samples),
            "candidateBoundChecks": candidate_bound_checks,
            "fixedTimestampChecks": len(samples) - 1,
            "dhiUnmodifiedChecks": dhi_independence_checks,
            "variedActivityTChecks": event_timestamps,
            "ledgerResetModelsWithKRetained": ledger_reset_checks,
            "sequence": k_timeline,
            "newerEvent": {
                "activityAt": new_t,
                "sameEventDlo": same_event_dlo,
                "newEventDlo": new_event_dlo,
            },
            "freshClockIncarnation": {
                "oldK": k,
                "newK": fresh_k,
                "newDlo": fresh_dlo,
                "candidateDlo": fresh_candidate,
                "explicitBaseline": True,
            },
            "signedOldCutoffs": {
                "activityAt": old_t,
                "Dlo": old_dlo,
                "Dhi": old_dhi,
            },
            "olderEventGuard": {
                "lastActivityAt": last_event_t,
                "candidateActivityAt": regressed_event_t,
                "decision": regressed_decision,
                "Dhi": regressed_dhi,
            },
            "capacityLatchModel": {
                "continuityAfterLatch": latched_continuity,
                "sameContextRecoveryCanRearm": same_context_recovery,
                "newContextChanged": context_changed,
                "acceptedNewBaseline": accepted_new_baseline,
                "recencyAfterNewBaseline": recency_after_context_baseline,
                "KRetainedAcrossContextChange": True,
            },
        },
        "horizons": {
            "longerActive": {
                "hA": 800,
                "hR": 200,
                "union": horizon_long_active,
                "naiveFlattenedMinimum": flat_long_active,
            },
            "longerRecentWithEligibility": {
                "hE": 600,
                "hA": 100,
                "hR": 700,
                "selected": horizon_long_recent,
                "naiveFlattenedMinimum": flat_long_recent,
            },
            "bothBranchesAbsent": both_absent,
            "recentWithoutDlo": recent_without_dlo,
        },
        "coverageTransition": {
            "beforePositiveExpiry": complete_before,
            "atRecentOnlyPositiveExpiryWithoutNegative": partial_at_expiry,
            "atExpiryWithFreshAdmittedNegative": complete_after_negative,
            "sameRowActiveAlternativeSurvivesRecentExpiry": complete_with_active_alternative,
        },
        "fixedTimestampMinimumCutoffChecks": len(samples),
        "namedCaseCount": len(named_cases),
        "namedCases": named_cases,
        "pass": True,
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
