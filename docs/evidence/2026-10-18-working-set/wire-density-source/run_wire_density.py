"""Untimed native frame-density evidence over fixed synthetic observations."""

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--fixture-helper", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = args.root.resolve()
    gc.disable()
    sys.path.insert(0, str(root))
    from agent_observer.contract import canonical, validate_snapshot
    from agent_observer.service_contract import parse_frame as parse_full
    from agent_observer.service_state import ServiceState
    from agent_observer.working_set_contract import parse_frame as parse_working

    spec = importlib.util.spec_from_file_location("wire_ratio_fixture", args.fixture_helper)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    seed_bytes = args.seed.read_bytes()
    seed0 = json.loads(seed_bytes)
    results = []
    for count in (100, 500, 2000):
        for percent in (5, 10, 20, 24):
            seed, wall, _, _, _ = fixture.build_workload(copy.deepcopy(seed0), count, canonical)
            selected_count = count * percent // 100
            active_count = selected_count // 2
            for index, row in enumerate(seed["sessions"]):
                if index < active_count:
                    row["runtime"]["value"] = "running"
                    row["phase"] = copy.deepcopy(seed0["sessions"][0]["phase"])
                    row["blockedReasons"] = copy.deepcopy(seed0["sessions"][0]["blockedReasons"])
                else:
                    row["runtime"]["value"] = "parked"
                    row["phase"], row["blockedReasons"] = None, []
                age = 3_600_000 if active_count <= index < selected_count else 864_000_000
                row["activity"]["at"] = wall - age
            seed["collectedAt"] = wall
            validate_snapshot(seed)
            input_bytes = canonical(seed).encode()
            state = ServiceState(
                host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                uid=1000, clock=lambda: 10001,
                boot_id="00000000-0000-4000-8000-000000000001",
                clock_domain="time:[123]", working_set_window_ms=259_200_000,
            )
            state.attempt("codex", "runtime")
            assert state.accept("codex", "runtime", seed, sampled_ms=10000,
                                ttl_ms=100000, accepted_boottime_ms=10001)
            full = state.frame("status", 1)
            working = state.working_set_frame("status", 1)
            full_wire = (canonical(full) + "\n").encode()
            working_wire = (canonical(working) + "\n").encode()
            assert parse_full(full_wire, expected_host="fixture", expected_uid=1000) == full
            assert parse_working(working_wire, expected_host="fixture", expected_uid=1000,
                                 expected_window_ms=259_200_000) == working
            expected = fixture.full_consumer_rows(full["snapshot"])
            assert len(expected) == selected_count
            projection = working["projection"]
            complete = projection is not None and projection["scopes"][0]["coverage"]["status"] == "complete"
            if complete:
                assert projection["sessions"] == expected
            selected_bytes = len(canonical(expected).encode())
            full_rows_bytes = len(canonical(full["snapshot"]["sessions"]).encode())
            applies = complete and count >= 500 and selected_bytes <= full_rows_bytes / 4
            results.append({
                "rows": count, "selectionPercent": percent, "selectedRows": selected_count,
                "inputBytes": len(input_bytes), "inputSha256": hashlib.sha256(input_bytes).hexdigest(),
                "selectedOriginalRowBytes": selected_bytes, "fullOriginalRowBytes": full_rows_bytes,
                "selectedBodyRatio": selected_bytes / full_rows_bytes,
                "fullNativeFrameBytes": len(full_wire), "workingNativeFrameBytes": len(working_wire),
                "complete": complete,
                "reason": None if projection is None else projection["scopes"][0]["coverage"]["reason"],
                "byteReductionPercent": 100 * (1 - len(working_wire) / len(full_wire)) if complete else None,
                "component50PercentTargetApplies": applies,
                "component50PercentTargetPass": (len(working_wire) <= len(full_wire) / 2) if applies else None,
            })
    data = {
        "sourceRevision": args.source_revision,
        "scope": "untimed native source-frame density only, not SDK/transport/CPU or producer acceptance",
        "pythonVersion": sys.version.split()[0], "gcEnabled": gc.isenabled(),
        "seedSha256": hashlib.sha256(seed_bytes).hexdigest(),
        "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixtureHelperSha256": hashlib.sha256(args.fixture_helper.read_bytes()).hexdigest(),
        "results": results, "loaded": fixture.capture_loaded_modules(root),
    }
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "cases": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
