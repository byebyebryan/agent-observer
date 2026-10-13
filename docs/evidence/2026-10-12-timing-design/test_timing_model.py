"""Offline acceptance cases for the provisional model, not provider tests."""

import json
import unittest
from dataclasses import replace
from pathlib import Path

from timing_model import (
    Batch,
    PhaseRow,
    PhaseTracker,
    Ref,
    Stamp,
    Turn,
    TurnSample,
    current_turn_age,
    select_latest,
)

REF = Ref("snap", "codex", "store-a", "thread", "thread-a")
SOURCE = REF.source


def stamp(at, *, ttl=60_000, seen=None, wall=None, **options):
    seen = at if seen is None else seen
    return Stamp(0, at, seen, 1_000_000 + seen if wall is None else wall, at + ttl, **options)


def batch(at, *, rows=None, phase="working", turn="turn-a", healthy=True, complete=True, **options):
    return Batch(SOURCE, stamp(at, **options), (PhaseRow(REF, "running", phase, turn),)
                 if rows is None else tuple(rows), healthy, complete)


def tracker(*, sources=None, **options):
    return PhaseTracker(observer_id="observer-a", clock_domain="boot-a:ns-a",
                        sources={SOURCE: 0} if sources is None else sources, **options)


def turn_sample(at, *, turn=None, component="runtime", healthy=True, admitted=True, **options):
    return TurnSample(REF, stamp(at, **options), component,
                      Turn("turn-a", "in_progress", 1_000_000, None) if turn is None else turn,
                      healthy, admitted)


def select(samples, now, **options):
    return select_latest(tuple(samples), ref=REF, generation=0, observer_id="observer-a",
                         clock_domain="boot-a:ns-a", now=now, **options)


class PhaseCases(unittest.TestCase):
    def test_repeats_and_reader_ticks_preserve_first_observation(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        first = model.view(REF, now=2000)
        model.accept_runtime(batch(3000), now=3000)
        last = model.view(REF, now=4000)
        self.assertEqual(first["firstObservedAt"], last["firstObservedAt"])
        self.assertEqual(first["series"], last["series"])
        self.assertEqual(last["observedSpanMs"], 3000)

    def test_reader_arrival_reconnect_and_output_mutation_do_not_reset_producer(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        client_view = model.view(REF, now=1500)
        client_view["firstObservedAt"] = 0
        model.accept_runtime(batch(2000), now=2000)
        # A new/reconnected reader sees the shared producer anchor.
        self.assertEqual(model.view(REF, now=2500)["firstObservedAt"], 1_001_000)
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 1500)

    def test_changed_phase_resets_series(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        before = model.view(REF, now=1000)
        model.accept_runtime(batch(2000, phase="blocked"), now=2000)
        after = model.view(REF, now=2500)
        self.assertNotEqual(before["series"], after["series"])
        self.assertEqual(after["observedSpanMs"], 500)

    def test_same_phase_new_turn_resets_series(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.accept_runtime(batch(2000, turn="turn-b"), now=2000)
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 500)

    def test_known_to_missing_turn_identity_starts_new_observation_series(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.accept_runtime(batch(2000, turn=None), now=2000)
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 500)

    def test_missing_to_known_turn_identity_is_not_backdated(self):
        model = tracker()
        model.accept_runtime(batch(1000, turn=None), now=1000)
        model.accept_runtime(batch(2000), now=2000)
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 500)

    def test_metadata_only_refresh_cannot_renew_phase_lease(self):
        model = tracker()
        model.accept_runtime(batch(1000, ttl=2000), now=1000)
        metadata = turn_sample(2500, component="history", ttl=60_000)
        self.assertEqual(select([metadata], 4000)["health"], "current")
        self.assertIsNone(model.view(REF, now=4000))

    def test_metadata_only_new_turn_cannot_start_a_phase_anchor(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        metadata = turn_sample(2000, turn=Turn("turn-b", "in_progress", 1_002_000, None))
        self.assertEqual(select([metadata], 2000)["sample"].turn.id, "turn-b")
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 1500)
        model.accept_runtime(batch(3000, turn="turn-b"), now=3000)
        self.assertEqual(model.view(REF, now=3500)["observedSpanMs"], 500)

    def test_arrival_after_expiry_cannot_create_current_phase_time(self):
        model = tracker()
        result = model.accept_runtime(batch(1000, ttl=2000), now=4000)
        self.assertEqual(result["reason"], "source_gap")
        self.assertIsNone(model.view(REF, now=4000))

    def test_read_duration_consumes_the_original_lease(self):
        model = tracker()
        model.accept_runtime(batch(1000, seen=2500, ttl=2000), now=2500)
        self.assertEqual(model.view(REF, now=2800)["observedSpanMs"], 300)
        self.assertIsNone(model.view(REF, now=3000))

    def test_collection_finishing_after_its_lease_is_not_current(self):
        model = tracker()
        value = batch(1000, seen=4000, ttl=2000)
        self.assertEqual(model.accept_runtime(value, now=4000)["reason"], "source_gap")
        self.assertIsNone(model.view(REF, now=4000))

    def test_failure_and_recovery_never_bridge_the_gap(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.accept_runtime(batch(2000, rows=(), healthy=False), now=2000)
        self.assertIsNone(model.view(REF, now=2500))
        model.accept_runtime(batch(3000), now=3000)
        self.assertEqual(model.view(REF, now=4000)["observedSpanMs"], 1000)

    def test_late_success_cannot_undo_a_newer_failure(self):
        model = tracker()
        model.accept_runtime(batch(2000, rows=(), healthy=False), now=2000)
        self.assertFalse(model.accept_runtime(batch(1000), now=3000)["accepted"])
        self.assertIsNone(model.view(REF, now=3000))

    def test_generation_change_rejects_late_old_context(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.advance_generation(SOURCE, 1, now=2000)
        self.assertFalse(model.accept_runtime(batch(3000), now=3000)["accepted"])
        fresh = replace(batch(4000), stamp=replace(stamp(4000), generation=1))
        model.accept_runtime(fresh, now=4000)
        self.assertEqual(model.view(REF, now=4500)["observedSpanMs"], 500)

    def test_new_generation_must_be_registered_by_the_owner(self):
        model = tracker()
        future = replace(batch(1000), stamp=replace(stamp(1000), generation=1))
        self.assertFalse(model.accept_runtime(future, now=1000)["accepted"])
        with self.assertRaisesRegex(ValueError, "generation_invalid"):
            model.advance_generation(SOURCE, 0, now=1000)

    def test_old_observer_and_wrong_clock_domain_are_rejected(self):
        for options in ({"observer_id": "observer-old"}, {"clock_domain": "boot-b:ns-b"}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, "observation_scope"):
                    tracker().accept_runtime(batch(1000, **options), now=1000)

    def test_restart_recovers_turn_start_but_observed_phase_starts_now(self):
        model = tracker()
        model.accept_runtime(batch(10_000), now=10_000)
        native = turn_sample(10_000)
        age = current_turn_age(select([native], 10_000), row=batch(10_000).rows[0],
                               runtime_stamp=stamp(10_000), now=10_000)
        self.assertEqual(age["ageMs"], 10_000)
        self.assertEqual(model.view(REF, now=10_000)["observedSpanMs"], 0)

    def test_unknown_phase_and_parked_break_the_observed_series(self):
        for row in (PhaseRow(REF, "running", None), PhaseRow(REF, "parked", None)):
            with self.subTest(row=row):
                model = tracker()
                model.accept_runtime(batch(1000), now=1000)
                model.accept_runtime(batch(2000, rows=(row,)), now=2000)
                self.assertIsNone(model.view(REF, now=2000))

    def test_missing_partial_row_breaks_only_its_series(self):
        second = replace(REF, native_id="thread-b")
        model = tracker()
        model.accept_runtime(batch(1000, rows=(PhaseRow(REF, "running", "working"),
                                               PhaseRow(second, "running", "blocked"))), now=1000)
        model.accept_runtime(batch(2000, rows=(PhaseRow(second, "running", "blocked"),),
                                   complete=False), now=2000)
        self.assertIsNone(model.view(REF, now=2500))
        self.assertEqual(model.view(second, now=2500)["observedSpanMs"], 1500)

    def test_complete_omission_does_not_assert_parked(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.accept_runtime(batch(2000, rows=()), now=2000)
        self.assertIsNone(model.view(REF, now=2000))

    def test_hidden_same_turn_cycle_disproves_lower_bound_age(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        # Native blocks at 2000 and resumes at 2900; neither is sampled.
        model.accept_runtime(batch(3000), now=3000)
        self.assertEqual(model.view(REF, now=3000)["observedSpanMs"], 2000)
        self.assertGreater(model.view(REF, now=3000)["observedSpanMs"], 100)

    def test_identity_uses_host_provider_store_and_id_kind(self):
        refs = [REF, replace(REF, host="starship"), replace(REF, provider="pi"),
                replace(REF, namespace="store-b"), replace(REF, id_kind="session")]
        sources = {ref.source: 0 for ref in refs}
        model = tracker(sources=sources)
        for index, source in enumerate(sources, 1):
            # A source receipt is one roster; send both id kinds together so
            # complete omission does not deliberately retire the earlier row.
            rows = tuple(PhaseRow(ref, "running", "working") for ref in refs if ref.source == source)
            value = Batch(source, stamp(index * 1000), rows)
            model.accept_runtime(value, now=index * 1000)
        self.assertEqual(len(model.entries), 5)
        self.assertEqual(len({model.view(ref, now=6000)["series"] for ref in refs}), 5)

    def test_capacity_is_bounded_and_does_not_evict_existing_current_series(self):
        model = tracker(capacity=1)
        model.accept_runtime(batch(1000), now=1000)
        second = replace(REF, native_id="thread-b")
        rows = (PhaseRow(second, "running", "working"), PhaseRow(REF, "running", "working", "turn-a"))
        result = model.accept_runtime(batch(2000, rows=rows), now=2000)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(len(model.entries), 1)
        self.assertEqual(model.view(REF, now=2500)["observedSpanMs"], 1500)
        self.assertIsNone(model.view(second, now=2500))

    def test_expired_capacity_and_anti_replay_use_source_watermarks(self):
        model = tracker(capacity=1)
        model.accept_runtime(batch(1000, ttl=1000), now=1000)
        second = replace(REF, native_id="thread-b")
        model.accept_runtime(batch(3000, rows=(PhaseRow(second, "running", "working"),)), now=3000)
        self.assertFalse(model.accept_runtime(batch(1500), now=3500)["accepted"])
        self.assertEqual(len(model.entries), 1)
        self.assertIsNone(model.view(REF, now=3500))

    def test_clock_regression_is_terminal_until_a_new_owner(self):
        model = tracker()
        model.accept_runtime(batch(2000), now=2000)
        with self.assertRaisesRegex(ValueError, "clock_invalid"):
            model.view(REF, now=1000)
        with self.assertRaisesRegex(ValueError, "tracker_terminal"):
            model.view(REF, now=3000)

    def test_wall_clock_jump_does_not_rewrite_observed_anchor(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        model.accept_runtime(batch(2000, wall=100), now=2000)
        view = model.view(REF, now=2500)
        self.assertEqual(view["firstObservedAt"], 1_001_000)
        self.assertEqual(view["observedSpanMs"], 1500)

    def test_equal_sample_order_is_explicitly_ambiguous(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        result = model.accept_runtime(batch(1000, phase="blocked"), now=2000)
        self.assertEqual(result["reason"], "equal_order_ambiguous")
        self.assertIsNone(model.view(REF, now=2000))


class NativeClockCases(unittest.TestCase):
    def test_blocked_and_working_share_native_turn_age(self):
        metadata = turn_sample(1000)
        for phase in ("working", "blocked"):
            row = PhaseRow(REF, "running", phase, "turn-a")
            value = current_turn_age(select([metadata], 2000), row=row,
                                     runtime_stamp=stamp(1000), now=2000)
            self.assertEqual(value["ageMs"], 2000)
            self.assertEqual(value["association"], "compatible_non_atomic_samples")

    def test_expiring_new_in_progress_cannot_restore_old_completion(self):
        old = turn_sample(1000, component="history", turn=Turn("old", "completed", 900_000, 901_000))
        new = turn_sample(2000, ttl=1000, turn=Turn("new", "in_progress", 1_002_000, None))
        selected = select([old, new], 4000)
        self.assertEqual(selected["sample"].turn.id, "new")
        self.assertEqual(selected["health"], "stale")

    def test_observation_order_not_largest_event_timestamp_selects_latest(self):
        old = turn_sample(1000, component="history", turn=Turn("old", "completed", 900_000, 901_000))
        authoritative = turn_sample(2000, turn=Turn("restored", "completed", 800_000, 801_000))
        selected = select([old, authoritative], 2500)
        self.assertEqual(selected["sample"].turn.id, "restored")
        self.assertEqual(selected["sample"].turn.end_ms, 801_000)

    def test_missing_new_turn_start_never_fills_from_old_turn(self):
        old = turn_sample(1000, component="history")
        new = turn_sample(2000, turn=Turn("turn-b", "in_progress", None, None))
        selected = select([old, new], 2500)
        value = current_turn_age(selected, row=PhaseRow(REF, "running", "working", "turn-b"),
                                 runtime_stamp=stamp(2000), now=2500)
        self.assertIsNone(value["ageMs"])
        self.assertIsNone(selected["sample"].turn.start_ms)

    def test_provider_without_native_turn_id_can_supply_explicit_boundaries(self):
        native = turn_sample(1000, turn=Turn(None, "in_progress", 1_000_000, None))
        value = current_turn_age(select([native], 2000), row=PhaseRow(REF, "running", "working"),
                                 runtime_stamp=stamp(1000), now=2000)
        self.assertEqual(value["ageMs"], 2000)
        self.assertIsNone(native.turn.id)

    def test_known_empty_latest_turn_supersedes_old_history(self):
        old = turn_sample(1000, component="history")
        new = replace(turn_sample(2000), turn=None)
        selected = select([old, new], 2500)
        self.assertEqual(selected["health"], "current")
        self.assertIsNone(selected["sample"].turn)

    def test_failed_new_metadata_does_not_restore_older_current_history(self):
        old = turn_sample(1000, component="history", turn=Turn("old", "completed", 900_000, 901_000))
        failed = replace(turn_sample(2000, healthy=False), turn=None)
        selected = select([old, failed], 2500)
        self.assertEqual(selected["health"], "stale")
        self.assertIsNone(selected["sample"].turn)

    def test_metadata_and_runtime_expire_independently(self):
        metadata = turn_sample(1000, component="history", ttl=10_000)
        runtime = stamp(1000, ttl=2000)
        selected = select([metadata], 4000)
        self.assertEqual(selected["health"], "current")
        self.assertIsNone(current_turn_age(selected, row=batch(1000).rows[0],
                                          runtime_stamp=runtime, now=4000)["ageMs"])

    def test_latest_receipt_owns_metadata_lease_in_either_component(self):
        for component in ("runtime", "history"):
            selected = select([turn_sample(1000, component=component, ttl=2000)], 3000)
            self.assertEqual(selected["health"], "stale")
            self.assertEqual(selected["sample"].component, component)

    def test_same_time_conflicting_turns_are_ambiguous(self):
        first = turn_sample(1000)
        second = turn_sample(1000, component="history", turn=Turn("turn-b", "in_progress", 1_000_000, None))
        self.assertEqual(select([first, second], 2000)["health"], "ambiguous")

    def test_same_time_same_turn_uses_the_earlier_lease(self):
        first = turn_sample(1000, ttl=2000)
        second = turn_sample(1000, component="history", ttl=10_000)
        self.assertEqual(select([first, second], 3000)["health"], "stale")

    def test_unproved_unsaved_clock_does_not_erase_phase(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        selected = select([turn_sample(1000, admitted=False)], 2000)
        self.assertEqual(selected["health"], "unavailable")
        self.assertIsNotNone(model.view(REF, now=2000))

    def test_idle_in_progress_and_working_terminal_samples_do_not_form_timer(self):
        ongoing = select([turn_sample(1000)], 2000)
        self.assertIsNone(current_turn_age(ongoing, row=PhaseRow(REF, "running", "waiting"),
                                          runtime_stamp=stamp(1000), now=2000)["ageMs"])
        terminal = select([turn_sample(1000, turn=Turn("turn-a", "completed", 900_000, 901_000))], 2000)
        self.assertIsNone(current_turn_age(terminal, row=batch(1000).rows[0],
                                          runtime_stamp=stamp(1000), now=2000)["ageMs"])

    def test_native_turn_identity_disagreement_suppresses_derived_timer(self):
        selected = select([turn_sample(2000, turn=Turn("turn-b", "in_progress", 1_002_000, None))], 2500)
        value = current_turn_age(selected, row=batch(1000).rows[0], runtime_stamp=stamp(1000), now=2500)
        self.assertEqual(value["reason"], "turn_identity_race")

    def test_new_start_after_status_observation_suppresses_derived_timer(self):
        selected = select([turn_sample(5000, turn=Turn("turn-b", "in_progress", 1_004_000, None))], 5000)
        value = current_turn_age(selected, row=PhaseRow(REF, "running", "working"),
                                 runtime_stamp=stamp(1000), now=5000)
        self.assertEqual(value["reason"], "turn_started_after_status")

    def test_cross_session_clock_context_and_observer_are_not_joined(self):
        for options in ({"observer_id": "observer-old"}, {"clock_domain": "boot-b:ns-b"}):
            with self.subTest(options=options):
                self.assertEqual(select([turn_sample(1000, **options)], 2000)["health"], "unavailable")
        with self.assertRaisesRegex(ValueError, "selection_scope"):
            select([replace(turn_sample(1000), ref=replace(REF, native_id="other"))], 2000)

    def test_duplicate_receipt_components_are_not_two_independent_sources(self):
        with self.assertRaisesRegex(ValueError, "selection_components"):
            select([turn_sample(1000), turn_sample(2000)], 2500)

    def test_native_future_clock_is_not_rewritten_or_clamped(self):
        native = turn_sample(1000, turn=Turn("turn-a", "in_progress", 1_001_500, None))
        selected = select([native], 2000)
        value = current_turn_age(selected, row=batch(1000).rows[0], runtime_stamp=stamp(1000), now=2000)
        self.assertIsNone(value["ageMs"])
        self.assertEqual(selected["sample"].turn.start_ms, 1_001_500)

    def test_display_ticks_use_monotonic_elapsed_not_new_local_wall_time(self):
        native = turn_sample(1000)
        selected = select([native], 3000)
        value = current_turn_age(selected, row=batch(1000).rows[0], runtime_stamp=stamp(1000), now=3000)
        self.assertEqual(value["ageMs"], 3000)

    def test_terminal_duration_can_be_finer_than_seconds_boundaries(self):
        value = Turn("turn-a", "completed", 1000, 3000, 2466)
        self.assertEqual(value.duration_ms, 2466)
        self.assertEqual(value.end_ms - value.start_ms, 2000)

    def test_invalid_native_timing_inputs_do_not_mutate_phase_tracker(self):
        model = tracker()
        model.accept_runtime(batch(1000), now=1000)
        for options in ({"start_ms": True}, {"start_ms": -1}, {"end_ms": 5}, {"duration_ms": 1}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, "turn_invalid"):
                    Turn("turn-a", "in_progress", **({"start_ms": 1000, "end_ms": None} | options))
        self.assertEqual(model.view(REF, now=2000)["observedSpanMs"], 1000)

    def test_resumed_waiting_history_is_not_idle_entry_time(self):
        model = tracker()
        model.accept_runtime(batch(10_000, phase="waiting"), now=10_000)
        native = turn_sample(10_000, turn=Turn("turn-a", "completed", 500_000, 501_000))
        self.assertEqual(select([native], 10_000)["sample"].turn.end_ms, 501_000)
        self.assertEqual(model.view(REF, now=10_000)["observedSpanMs"], 0)


class AdmissionCases(unittest.TestCase):
    def test_duplicate_rows_invalid_scope_and_boolean_clocks_are_rejected(self):
        row = PhaseRow(REF, "running", "working")
        with self.assertRaisesRegex(ValueError, "batch_invalid"):
            batch(1000, rows=(row, row))
        with self.assertRaisesRegex(ValueError, "batch_invalid"):
            Batch(("other", "codex", "store-a"), stamp(1000), (row,))
        for value in (True, -1, 1.2):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "stamp_invalid"):
                    Stamp(0, value, 2000, 1_002_000, 3000)

    def test_future_receipt_and_unknown_source_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "future_observation"):
            tracker().accept_runtime(batch(2000), now=1000)
        unknown = replace(REF, namespace="not-configured")
        with self.assertRaisesRegex(ValueError, "source_invalid"):
            tracker().accept_runtime(Batch(unknown.source, stamp(1000),
                                          (PhaseRow(unknown, "running", "working"),)), now=1000)

    def test_owned_context_count_and_row_admission_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "tracker_config_invalid"):
            tracker(capacity=0)
        with self.assertRaisesRegex(ValueError, "tracker_config_invalid"):
            tracker(sources={(str(i), "pi", "store"): 0 for i in range(33)})
        with self.assertRaisesRegex(ValueError, "batch_invalid"):
            batch(1000, rows=[PhaseRow(replace(REF, native_id=str(i)), "running", "working")
                              for i in range(1513)])

    def test_boolean_timer_now_is_not_a_monotonic_timestamp(self):
        with self.assertRaisesRegex(ValueError, "timer_input_invalid"):
            current_turn_age(select([turn_sample(1000)], 2000), row=batch(1000).rows[0],
                             runtime_stamp=stamp(1000), now=True)


class CapturedReplay(unittest.TestCase):
    def test_captured_native_approval_cycle_keeps_turn_start_and_resets_observed_phase(self):
        path = Path(__file__).parents[1] / "2026-10-12-codex-timing" / "controlled-native.json"
        data = json.loads(path.read_text())
        origin = data["samples"][0]["sampledAtMs"]
        model = tracker()
        results = {}
        native_status = {"inProgress": "in_progress", "completed": "completed", "failed": "failed", "interrupted": "cancelled"}
        for record in data["samples"]:
            at = record["sampledAtMs"] - origin
            flags = record["status"].get("activeFlags", [])
            phase = "waiting" if record["status"]["type"] == "idle" else "blocked" if flags else "working"
            value = PhaseRow(REF, "running", phase, record["turnId"])
            timing = stamp(at, wall=record["sampledAtMs"])
            model.accept_runtime(Batch(SOURCE, timing, (value,)), now=at)
            turn = None if record["turnId"] is None else Turn(
                record["turnId"], native_status[record["turnStatus"]],
                None if record["startedAt"] is None else record["startedAt"] * 1000,
                None if record["completedAt"] is None else record["completedAt"] * 1000,
                record["durationMs"],
            )
            selected = select([TurnSample(REF, timing, "runtime", turn)], at)
            results[record["label"]] = (model.view(REF, now=at), selected,
                                        current_turn_age(selected, row=value, runtime_stamp=timing, now=at))
        before, _, before_age = results["approval_blocked"]
        repeat, _, _ = results["approval_blocked_again"]
        after, after_turn, after_age = results["approval_answered_working"]
        self.assertEqual(before["series"], repeat["series"])
        self.assertNotEqual(before["series"], after["series"])
        self.assertEqual(after["observedSpanMs"], 0)
        self.assertGreater(after_age["ageMs"], before_age["ageMs"])
        self.assertEqual(after_turn["sample"].turn.start_ms, 1791842909000)
        self.assertEqual(len(results), 19)


if __name__ == "__main__":
    unittest.main(verbosity=2)
