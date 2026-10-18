"""Exact client counterexample; explicit before/after expectations, pure model."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--expect", choices=("before", "after"), required=True)
    args = parser.parse_args()
    root = args.source.absolute()
    sys.path.insert(0, str(root))
    gc.disable()
    from agent_observer.working_set_policy import SampleClock, combine_membership, recent_activity

    maximum = 2**53 - 1
    lower, upper, now, expiry = maximum - 10_000, maximum - 9_990, maximum - 9_900, maximum - 1
    service = "00000000-0000-4000-8000-000000000001"
    boot = "00000000-0000-4000-8000-000000000002"
    sample = "00000000-0000-4000-8000-000000000003"
    ref = {
        "serviceId": service,
        "provider": "codex",
        "namespace": "fixture",
        "contextGeneration": 1,
        "component": "runtime",
        "accepted": 1,
        "sampledBoottimeMs": lower,
        "expiresBoottimeMs": expiry,
    }
    source = {
        "provider": "codex",
        "namespace": "fixture",
        "contextGeneration": 1,
        "components": [
            {
                "name": "runtime",
                "health": "current",
                "accepted": 1,
                "sampledBoottimeMs": lower,
                "expiresBoottimeMs": expiry,
            }
        ],
    }
    clock = SampleClock(
        sample,
        "runtime",
        service,
        "codex",
        "fixture",
        1,
        boot,
        "fixture-boottime",
        lower,
        1_700_000_000_000,
        upper,
    )
    result = recent_activity(
        {"at": 1_699_999_999_000, "source": "codex_turn_metadata", "health": "current"},
        ref,
        clock,
        source,
        service_id=service,
        boot_id=boot,
        clock_domain="fixture-boottime",
        now_boottime_ms=now,
        expected_sample_id=sample,
    )
    if args.expect == "before":
        assert result.decision is True and result.reason == "recent"
        assert result.deadline_lower_boottime_ms == 9_007_199_513_929_990 > maximum
        assert result.deadline_upper_boottime_ms == 9_007_199_513_930_002 > maximum
    else:
        assert result.decision is None and result.reason == "cutoff_out_of_range"
        assert result.deadline_lower_boottime_ms is None
        assert result.deadline_upper_boottime_ms is None
    active = combine_membership(True, True, result.decision).decision
    assert active is True
    loaded = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename).absolute()
        if path.suffix == ".py" and path.is_relative_to(root):
            loaded[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "gcDisabled": not gc.isenabled(),
                "expectation": args.expect,
                "expectationSatisfied": True,
                "decision": result.decision,
                "reason": result.reason,
                "Dlo": result.deadline_lower_boottime_ms,
                "Dhi": result.deadline_upper_boottime_ms,
                "independentActiveSelected": active,
                "loadedInputs": loaded,
                "scope": "pure preparatory helper; no native schema/source/cache/lifetime/resource acceptance",
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
