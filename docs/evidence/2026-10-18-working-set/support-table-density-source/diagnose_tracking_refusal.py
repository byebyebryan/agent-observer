"""Capture untimed scalar budget locals for the 2,000/100 density case."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def _fixture(path: Path):
    spec = importlib.util.spec_from_file_location("density_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _owner_frame_locals(frame, code):
    current = frame.f_back
    while current is not None and current.f_code is not code:
        current = current.f_back
    return None if current is None else current.f_locals


def main() -> None:
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
    from agent_observer.contract import ContractError, canonical, validate_snapshot
    from agent_observer.service_state import ServiceState
    from agent_observer.working_set_contract import MAX_LEDGER_BYTES
    from agent_observer.working_set_feed import WorkingSetProjector, _ledger_bytes
    from agent_observer.working_set_supports import SupportTableBuilder

    helper = _fixture(args.fixture_helper)
    seed_bytes = args.seed.read_bytes()
    seed, wall, _, _, _ = helper.build_workload(json.loads(seed_bytes), 2000, canonical)
    selected_count = 100
    active_count = selected_count // 2
    for index, row in enumerate(seed["sessions"]):
        if index < active_count:
            row["runtime"]["value"] = "running"
            row["phase"] = copy.deepcopy(seed["sessions"][0]["phase"])
            row["blockedReasons"] = copy.deepcopy(seed["sessions"][0]["blockedReasons"])
        else:
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        age = 3_600_000 if active_count <= index < selected_count else 864_000_000
        row["activity"]["at"] = wall - age
    seed["collectedAt"] = wall
    validate_snapshot(seed)
    input_bytes = canonical(seed).encode("utf-8")

    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=1000,
        clock=lambda: 10_001,
        boot_id="00000000-0000-4000-8000-000000000001",
        clock_domain="time:[123]",
        working_set_window_ms=259_200_000,
    )
    code = WorkingSetProjector._accept_owned.__code__
    plan_code = SupportTableBuilder._plan.__code__
    captured: dict[str, object] = {}

    def trace(frame, event, _arg):
        if frame.f_code is plan_code and event == "exception":
            exception = _arg[1]
            if isinstance(exception, ContractError) and str(exception) == "working_set_support_capacity":
                local = frame.f_locals
                builder = local["self"]
                outer = _owner_frame_locals(frame, code)
                captured["rejectedEntry"] = {
                    "currentCharge": local["current_charge"],
                    "compactEntryBytes": local["serialized"],
                    "additionalLedgerCharge": local["additional_charge"],
                    "previousPreflightCharge": builder.preflight_charge,
                    "attemptPreflightCharge": local["delta_preflight"],
                    "attemptTotalCharge": (
                        local["current_charge"]
                        + local["serialized"]
                        + local["additional_charge"]
                        + builder.preflight_charge
                        + local["delta_preflight"]
                    ),
                    "limit": builder.limit,
                    "pendingUniqueMaps": len(local["pending_values"]),
                    "entryReferences": local["reference_count"],
                    "priorRetainedMaps": len(builder._table),
                    "priorReferenceCount": builder.references,
                    "priorPreflightCharge": builder.preflight_charge,
                    "priorRetainedOverheadCharge": builder.overhead_charge,
                    "candidateMembersBeforeAttempt": (
                        None if outer is None else len(outer["members"])
                    ),
                    "candidateBodiesBeforeAttempt": (
                        None if outer is None else len(outer["bodies"])
                    ),
                    "candidateLedgerEntriesBeforeAttempt": (
                        None if outer is None else len(outer["ledger"])
                    ),
                    "candidateLedgerBytesBeforeAttempt": (
                        None
                        if outer is None
                        else _ledger_bytes(outer["ledger"].values(), len(outer["ledger"]))
                    ),
                }
            return trace
        if frame.f_code is not code or event != "return":
            return trace
        local = frame.f_locals
        projector = local["self"]
        decisions = projector.decisions
        scope = local["scope"]
        builder = local["support_table"]
        canonical_bytes = len(canonical([scope]).encode("utf-8"))
        captured.update(
            {
                "guardBytes": projector.decisions.guard_bytes,
                "guardIdentityCount": decisions.guard_count,
                "guardPrefixBytes": decisions._prefix_bytes,
                "guardEntryBytes": decisions._guard_entries_bytes,
                "guardTableReserveBytes": decisions._dict_table_reserve(
                    len(decisions._guards)
                ),
                "guardLatched": decisions.latched,
                "guardLimitBytes": decisions.max_guard_bytes,
                "maxLedgerBytes": projector.max_ledger_bytes,
                "oldLedgerBytes": local["old_ledger_bytes"],
                "candidateLedgerBytes": local["candidate_ledger_bytes"],
                "trackingBaseBytesAtReturn": local["tracking_bytes"],
                "trackingCapacity": local["tracking_capacity"],
                "supportReferenceCount": builder.references,
                "supportTableEntriesInScope": len(scope["supportTable"]),
                "supportBuilderEntriesStillRetained": len(builder._table),
                "supportRetainedOverheadCharge": builder.overhead_charge,
                "supportPreflightCharge": builder.preflight_charge,
                "scopeCanonicalBytes": canonical_bytes,
                "combinedTrackingBytes": local["combined"],
                "trackedIdentities": len(local["tracked"]),
                "candidateLedgerEntries": len(local["ledger"]),
                "candidateLedgerBytesAtReturn": _ledger_bytes(
                    local["ledger"].values(), len(local["ledger"])
                ),
                "scopeMembers": len(scope["members"]),
                "scopeUncertain": len(scope["uncertain"]),
                "scopeNonmembers": len(scope["nonmembers"]),
                "coverageStatus": scope["coverage"]["status"],
                "coverageReason": scope["coverage"]["reason"],
                "encodedBytes": len(local["encoded"] or b""),
                "projectorBlocked": projector._capacity_blocked,
            }
        )
        return trace

    seed["collectionId"] = "00000000-0000-0000-0000-000000000064"
    sys.settrace(trace)
    try:
        state.attempt("codex", "runtime")
        accepted = state.accept(
            "codex",
            "runtime",
            seed,
            sampled_ms=10_000,
            ttl_ms=100_000,
            accepted_boottime_ms=10_001,
        )
    finally:
        sys.settrace(None)
    if accepted is not True or not captured:
        raise AssertionError("tracking_diagnostic_not_captured")
    frame = state.working_set_frame("status", 2)
    report = {
        "sourceRevision": args.source_revision,
        "scope": "single untimed accepted 2,000-row / 100-selected tracking diagnostic",
        "pythonVersion": sys.version.split()[0],
        "gcEnabled": gc.isenabled(),
        "seedSha256": hashlib.sha256(seed_bytes).hexdigest(),
        "acceptedInputSha256": hashlib.sha256(input_bytes).hexdigest(),
        "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixtureHelperSha256": hashlib.sha256(args.fixture_helper.read_bytes()).hexdigest(),
        "loaded": helper.capture_loaded_modules(root),
        "maxLedgerBytesConstant": MAX_LEDGER_BYTES,
        "accepted": accepted,
        "wireCoverageReason": frame["reason"],
        "wireProjectionPresent": frame["projection"] is not None,
        "diagnostic": captured,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "accepted": accepted}, sort_keys=True))


if __name__ == "__main__":
    main()
