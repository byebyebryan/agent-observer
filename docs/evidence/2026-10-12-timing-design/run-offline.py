#!/usr/bin/env python3
"""Run the timing design's offline cases/replay and bounded mutation checks."""

import argparse
import hashlib
import io
import json
import sys
import types
import unittest
from pathlib import Path

import test_timing_model
import timing_model

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / "2026-10-12-codex-timing" / "controlled-native.json"


def case_names(suite):
    names = []
    for case in suite:
        names.extend(case_names(case) if isinstance(case, unittest.TestSuite) else [case.id()])
    return names


def run_cases(module):
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    names = case_names(suite)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    failed = [case.id() for case, _ in result.failures + result.errors]
    return {"tests": result.testsRun, "passed": result.wasSuccessful(), "cases": names, "failedCases": failed}


def mutations():
    source = (HERE / "timing_model.py").read_text()
    test_source = (HERE / "test_timing_model.py").read_text()
    changes = [
        ("repeated_reads_reset_phase_anchor", "prior.first_ms if same else batch.stamp.seen_ms", "batch.stamp.seen_ms"),
        ("expiry_keeps_current_phase", "if self.entries[ref].expires_ms <= now:", "if False:"),
        ("new_turn_id_does_not_reset_series", "(prior.phase, prior.turn_id) == (row.phase, row.turn_id)", "prior.phase == row.phase"),
        ("expired_latest_promotes_old_completion", "newest = max(sample.stamp.sampled_ms for sample in matching)",
         "matching = [sample for sample in matching if sample.stamp.current(now)] or matching\n    newest = max(sample.stamp.sampled_ms for sample in matching)"),
        ("equal_time_selects_longer_lease", "sample = min(winners, key=lambda item: item.stamp.expires_ms)",
         "sample = max(winners, key=lambda item: item.stamp.expires_ms)"),
        ("different_turn_ids_form_timer", "if row.turn_id is not None and row.turn_id != turn.id:", "if False:"),
        ("late_success_undoes_newer_failure", "if batch.stamp.sampled_ms < previous:", "if False:"),
        ("native_epoch_delta_is_clamped", "if age_at_sample < 0:", "if False:"),
    ]
    outcomes = []
    original_model, original_tests = sys.modules["timing_model"], sys.modules["test_timing_model"]
    try:
        for name, before, after in changes:
            if source.count(before) != 1:
                raise ValueError("mutation_target_invalid")
            model = types.ModuleType("timing_model")
            model.__file__ = str(HERE / "timing_model.py")
            sys.modules["timing_model"] = model
            exec(compile(source.replace(before, after), model.__file__, "exec"), model.__dict__)
            tests = types.ModuleType("test_timing_model")
            tests.__file__ = str(HERE / "test_timing_model.py")
            sys.modules["test_timing_model"] = tests
            exec(compile(test_source, tests.__file__, "exec"), tests.__dict__)
            result = run_cases(tests)
            outcomes.append({"variant": name, "detected": not result["passed"],
                             "failedCases": result["failedCases"]})
    finally:
        sys.modules["timing_model"], sys.modules["test_timing_model"] = original_model, original_tests
    return outcomes


def native_replay():
    data = json.loads(NATIVE.read_text())
    origin = data["samples"][0]["sampledAtMs"]
    ref = timing_model.Ref("isolated-native", "codex", "timing-fixture", "thread", data["threadId"])
    model = timing_model.PhaseTracker(observer_id="offline-replay", clock_domain="fixture-wall-offsets",
                                     sources={ref.source: 0})
    statuses = {"inProgress": "in_progress", "completed": "completed", "failed": "failed", "interrupted": "cancelled"}
    rows = []
    for captured in data["samples"]:
        at = captured["sampledAtMs"] - origin
        phase = "waiting" if captured["status"]["type"] == "idle" else "blocked" if captured["status"].get("activeFlags") else "working"
        row = timing_model.PhaseRow(ref, "running", phase, captured["turnId"])
        stamp = timing_model.Stamp(0, at, at, captured["sampledAtMs"], at + 60_000,
                                   "offline-replay", "fixture-wall-offsets")
        model.accept_runtime(timing_model.Batch(ref.source, stamp, (row,)), now=at)
        turn = None if captured["turnId"] is None else timing_model.Turn(
            captured["turnId"], statuses[captured["turnStatus"]],
            None if captured["startedAt"] is None else captured["startedAt"] * 1000,
            None if captured["completedAt"] is None else captured["completedAt"] * 1000,
            captured["durationMs"],
        )
        selected = timing_model.select_latest((timing_model.TurnSample(ref, stamp, "runtime", turn),),
                                              ref=ref, generation=0, observer_id="offline-replay",
                                              clock_domain="fixture-wall-offsets", now=at)
        age = timing_model.current_turn_age(selected, row=row, runtime_stamp=stamp, now=at)
        rows.append({"label": captured["label"], "phase": phase, "turnId": captured["turnId"],
                     "startedAt": None if turn is None else turn.start_ms,
                     "completedAt": None if turn is None else turn.end_ms,
                     "nativeDurationMs": None if turn is None else turn.duration_ms,
                     "nativeUpdatedAt": captured["updatedAt"] * 1000,
                     "turnTimer": age, "observedSeries": model.view(ref, now=at)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    cases = run_cases(test_timing_model)
    variants = mutations()
    receipt = {
        "kind": "observer-only-offline-timing-design", "providerReads": 0, "providerActions": 0,
        "productionImports": False, "nativeQueriesReplayed": False,
        "clockMode": "fixture-wall-offsets-and-synthetic-monotonic-inputs-no-live-clock-proof",
        "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in (HERE / "timing_model.py", HERE / "test_timing_model.py",
                                Path(__file__).resolve(), NATIVE)},
        "acceptance": cases, "mutations": variants, "nativeReplay": native_replay(),
    }
    passed = cases["passed"] and all(item["detected"] for item in variants)
    receipt["passed"] = passed
    if args.receipt:
        with args.receipt.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"passed": passed, "tests": cases["tests"], "failedCases": cases["failedCases"],
                      "detectedMutations": sum(item["detected"] for item in variants),
                      "mutationCount": len(variants), "nativeReplaySamples": len(receipt["nativeReplay"])}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
