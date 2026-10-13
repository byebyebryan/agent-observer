#!/usr/bin/env python3
"""Offline timing research; no provider IO, production imports or public wire.

The input clock is a deterministic monotonic offset in fixtures/replay. This
prototype records an observed phase streak, never an exact phase-entry time.
One instance belongs to one complete session identity and observer lifetime.
"""

import argparse
import hashlib
import json
import unittest
from pathlib import Path


class ObservedStreak:
    def __init__(self):
        self.last_sample = None
        self.anchor = None
        self.context = None
        self.deadline = None

    def observe(self, at, phase, turn_id, *, incarnation="daemon-a", ttl=60_000,
                current=True):
        if self.last_sample is not None and at <= self.last_sample:
            return False
        expired = self.deadline is not None and at >= self.deadline
        self.last_sample = at
        if not current or phase not in {"working", "blocked", "waiting"}:
            self.anchor = self.context = self.deadline = None
            return True
        context = incarnation, phase, turn_id
        if expired or self.anchor is None or context != self.context:
            self.anchor = at
        self.context = context
        self.deadline = at + ttl
        return True

    def span(self, now):
        if self.deadline is None or now >= self.deadline:
            return None
        return now - self.anchor


def phase_of(status):
    if status.get("type") == "idle":
        return "waiting"
    if status.get("type") == "active":
        blocked = {"waitingOnApproval", "waitingOnUserInput"}
        return "blocked" if blocked.intersection(status.get("activeFlags", [])) else "working"
    return None


def native_turn_elapsed(sample, now_wall_ms, *, saved=True, current=True):
    """Only elapsed time of a positively admitted ongoing native turn."""
    start = sample.get("startedAt")
    if (not saved or not current or type(start) is not int or start < 0
            or start > 4_000_000_000 or start * 1000 > now_wall_ms
            or sample.get("turnStatus") != "inProgress"
            or sample.get("completedAt") is not None):
        return None
    return now_wall_ms - start * 1000


def replay():
    path = Path(__file__).with_name("controlled-native.json")
    value = json.loads(path.read_text())
    base = value["samples"][0]["sampledAtMs"]
    tracker = ObservedStreak()
    rows = []
    for sample in value["samples"]:
        offset = sample["sampledAtMs"] - base
        phase = phase_of(sample["status"])
        tracker.observe(offset, phase, sample["turnId"])
        rows.append({
            "label": sample["label"], "phase": phase,
            "turnId": sample["turnId"], "nativeStartedAt": sample["startedAt"],
            "nativeUpdatedAt": sample["updatedAt"],
            "nativeTurnElapsedMs": native_turn_elapsed(sample, sample["sampledAtMs"]),
            "firstObservedOffsetMs": tracker.anchor,
            "observationSpanMs": tracker.span(offset),
        })
    return {
        "kind": "offline-native-metadata-replay-and-synthetic-timing-spike",
        "inputSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "providerReads": 0, "providerActions": 0,
        "publicContractChanged": False,
        "semantics": "observed_phase_streak_not_exact_or_lower_bound_phase_age",
        "replayClock": "sample_wall_time_offsets_for_deterministic_replay_only",
        "rows": rows,
    }


class TimingTests(unittest.TestCase):
    def test_repeated_reads_do_not_reset_observed_anchor(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        tracker.observe(3000, "working", "turn-a")
        self.assertEqual(tracker.span(5000), 4000)

    def test_block_answer_resets_phase_streak_but_not_native_turn(self):
        rows = {row["label"]: row for row in replay()["rows"]}
        before = rows["approval_blocked"]
        repeat = rows["approval_blocked_again"]
        after = rows["approval_answered_working"]
        self.assertEqual(before["firstObservedOffsetMs"], repeat["firstObservedOffsetMs"])
        self.assertGreater(after["firstObservedOffsetMs"], before["firstObservedOffsetMs"])
        self.assertEqual(before["nativeStartedAt"], after["nativeStartedAt"])
        self.assertEqual(before["nativeUpdatedAt"], after["nativeUpdatedAt"])
        self.assertGreater(after["nativeTurnElapsedMs"], before["nativeTurnElapsedMs"])

    def test_late_receipt_does_not_rewind_series(self):
        tracker = ObservedStreak()
        tracker.observe(2000, "working", "turn-a")
        self.assertFalse(tracker.observe(1000, "blocked", "turn-a"))
        self.assertFalse(tracker.observe(2000, "blocked", "turn-a"))
        self.assertEqual(tracker.context[1], "working")
        self.assertEqual(tracker.anchor, 2000)

    def test_expiry_requires_fresh_observed_anchor(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a", ttl=2000)
        self.assertIsNone(tracker.span(3000))
        tracker.observe(4000, "working", "turn-a")
        self.assertEqual(tracker.anchor, 4000)

    def test_source_failure_breaks_observation_series(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        tracker.observe(2000, "working", "turn-a", current=False)
        self.assertIsNone(tracker.span(2500))
        tracker.observe(3000, "working", "turn-a")
        self.assertEqual(tracker.anchor, 3000)

    def test_daemon_incarnation_breaks_observation_series(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        tracker.observe(2000, "working", "turn-a", incarnation="daemon-b")
        self.assertEqual(tracker.anchor, 2000)

    def test_restart_recovers_native_turn_but_not_observed_phase_history(self):
        sample = {"startedAt": 1, "turnStatus": "inProgress", "completedAt": None}
        tracker = ObservedStreak()
        tracker.observe(10_000, "working", "turn-a")
        self.assertEqual(tracker.span(10_000), 0)
        self.assertEqual(native_turn_elapsed(sample, 10_000), 9000)

    def test_new_turn_resets_series_even_with_same_phase(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        tracker.observe(2000, "working", "turn-b")
        self.assertEqual(tracker.anchor, 2000)

    def test_new_terminal_turn_resets_waiting_series(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "waiting", "turn-a")
        tracker.observe(2000, "waiting", "turn-b")
        self.assertEqual(tracker.anchor, 2000)

    def test_unknown_phase_breaks_observation_series(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        tracker.observe(2000, None, "turn-a")
        self.assertIsNone(tracker.span(2500))
        tracker.observe(3000, "working", "turn-a")
        self.assertEqual(tracker.anchor, 3000)

    def test_polling_cannot_prove_a_continuous_phase(self):
        tracker = ObservedStreak()
        tracker.observe(1000, "working", "turn-a")
        # Actual hidden events: blocked at 2000, working again at 2900.
        tracker.observe(3000, "working", "turn-a")
        self.assertEqual(tracker.span(3000), 2000)
        actual_phase_age = 3000 - 2900
        self.assertGreater(tracker.span(3000), actual_phase_age)

    def test_blocked_reason_change_is_not_necessarily_new_phase(self):
        tracker = ObservedStreak()
        for at, flag in [(1000, "waitingOnApproval"), (2000, "waitingOnUserInput")]:
            phase = phase_of({"type": "active", "activeFlags": [flag]})
            tracker.observe(at, phase, "turn-a")
        self.assertEqual(tracker.anchor, 1000)

    def test_missing_invalid_or_unproved_native_clock_is_unavailable(self):
        sample = {"startedAt": 1, "turnStatus": "inProgress", "completedAt": None}
        for patch, options in [({"startedAt": None}, {}), ({"startedAt": True}, {}),
                               ({"startedAt": -1}, {}), ({"startedAt": 20}, {}),
                               ({"turnStatus": "completed", "completedAt": 2}, {}),
                               ({}, {"saved": False}), ({}, {"current": False})]:
            with self.subTest(patch=patch, options=options):
                self.assertIsNone(native_turn_elapsed(sample | patch, 10_000, **options))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TimingTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    receipt = replay()
    receipt.update(tests=result.testsRun, passed=True)
    if args.receipt:
        with args.receipt.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "rows"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
