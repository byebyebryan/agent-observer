"""Matched owner/read CPU and serialized-frame screen; no native/SDK I/O."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import sys
import time
from pathlib import Path
from uuid import UUID

WINDOW_MS = 259_200_000
MEASURED_GENERATIONS = 6
VARIANTS = ("a7-full", "candidate-full", "candidate-working")


def digest(value, canonical):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def native_id(row):
    return row["identity"]["nativeId"]


def full_consumer_rows(snapshot):
    """Benchmark reference using API4's current sampled wall-time fields.

    This is an output filter for the synthetic matrix, not a proof of the
    candidate's private accepted-sample BOOTTIME deadline.
    """
    selected = []
    for row in snapshot["sessions"]:
        if row["kind"] not in {"unknown", "user"}:
            continue
        runtime = row["runtime"]
        active = runtime["health"] == "current" and runtime["value"] == "running"
        activity = row["activity"]
        observed = runtime["observedAt"]
        at = activity["at"]
        recent = (
            runtime["health"] == "current"
            and runtime["clock"] == "sample"
            and activity["health"] == "current"
            and type(observed) is int
            and type(at) is int
            and 0 <= observed - at < WINDOW_MS
        )
        if active or recent:
            selected.append(row)
    return selected


def working_rows(frame):
    projection = frame["projection"]
    if projection is None:
        raise AssertionError("working_projection_missing")
    return projection["sessions"]


def capture_loaded_modules(root):
    loaded = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root) and path.suffix == ".py":
            loaded[name] = {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    return loaded


def build_workload(seed, count, canonical):
    seed["sources"][0]["capabilities"]["runtime"] = ["running", "parked"]
    seed["sources"][0]["capabilities"]["activity"] = True
    row_template = seed["sessions"][0]
    seed["sessions"] = []
    wall = 1_700_000_020_000
    small = max(1, count // 200)
    expected_ids, running_ids = set(), set()
    for number in range(count):
        row = copy.deepcopy(row_template)
        identity = str(UUID(int=1000 + number))
        row["identity"]["nativeId"] = identity
        row["nativeIds"].update(threadId=identity, sessionTreeRootId=identity)
        row["kind"] = "unknown"
        if number < small:
            running_ids.add(identity)
            row["runtime"]["value"] = "running"
        else:
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        if number < 2 * small:
            expected_ids.add(identity)
        row["activity"].update(
            at=wall - (3_600_000 if small <= number < 2 * small else 864_000_000),
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        seed["sessions"].append(row)
    return seed, wall, small, expected_ids, running_ids


def consumer_read(state, sequence, parser, canonical, host, uid):
    frame = state.frame("status", sequence)
    wire = (canonical(frame) + "\n").encode()
    parsed = parser(wire, expected_host=host, expected_uid=uid)
    selected = full_consumer_rows(parsed["snapshot"])
    return parsed, selected, len(wire)


def working_read(state, sequence, parser, canonical, host, uid):
    frame = state.working_set_frame("status", sequence)
    wire = (canonical(frame) + "\n").encode()
    parsed = parser(
        wire,
        expected_host=host,
        expected_uid=uid,
        expected_window_ms=WINDOW_MS,
    )
    rows = working_rows(parsed)
    return parsed, rows, len(wire)


def verify_generation(state, candidate, host, uid, canonical, service_parser,
                      working_parser, expected_ids, running_ids, sequences):
    full_frame = state.frame("status", sequences["full"])
    sequences["full"] += 1
    full_snapshot = full_frame["snapshot"]
    if full_snapshot is None:
        raise AssertionError("full_snapshot_missing")
    independent = full_consumer_rows(full_snapshot)
    independent_ids = [native_id(row) for row in independent]
    if set(independent_ids) != expected_ids:
        raise AssertionError("full_consumer_selection_mismatch")

    active = state.active_projector.snapshot()
    active_rows = active["sessions"]
    if {native_id(row) for row in active_rows} != running_ids:
        raise AssertionError("active_selection_mismatch")

    result = {
        "fullDigest": digest(full_snapshot["sessions"], canonical),
        "activeDigest": digest(active_rows, canonical),
        "selectedDigest": digest(independent, canonical),
        "fullRows": len(full_snapshot["sessions"]),
        "activeRows": len(active_rows),
        "selectedRows": len(independent),
        "selectedIds": independent_ids,
        "fullBodyBytes": len(canonical(full_snapshot).encode()),
        "fullFrameBytes": len((canonical(full_frame) + "\n").encode()),
        "selectedRowsBytes": len(canonical(independent).encode()),
    }
    if candidate:
        projection = state.working_set_projector.snapshot()
        if projection is None:
            raise AssertionError("working_projection_missing")
        scopes = projection["scopes"]
        if len(scopes) != 1 or scopes[0]["coverage"]["status"] != "complete":
            raise AssertionError("working_coverage_not_complete")
        if scopes[0]["uncertain"]:
            raise AssertionError("working_scope_uncertain")
        members = [native_id(member) for member in scopes[0]["members"]]
        if set(members) != expected_ids:
            raise AssertionError("working_scope_members_mismatch")
        if projection["sessions"] != independent:
            raise AssertionError("working_dto_mismatch")
        working_frame = state.working_set_frame("status", sequences["working"])
        sequences["working"] += 1
        working_wire = (canonical(working_frame) + "\n").encode()
        parsed_working = working_parser(
            working_wire,
            expected_host=host,
            expected_uid=uid,
            expected_window_ms=WINDOW_MS,
        )
        parsed_rows = working_rows(parsed_working)
        if parsed_rows != independent:
            raise AssertionError("working_frame_dto_mismatch")
        result.update(
            workingDigest=digest(parsed_rows, canonical),
            workingRows=len(parsed_rows),
            workingCoverage=scopes[0]["coverage"]["status"],
            workingReason=scopes[0]["coverage"]["reason"],
            workingScopeMembers=len(members),
            workingScope={
                "provider": scopes[0]["provider"],
                "namespace": scopes[0]["namespace"],
                "contextGeneration": scopes[0]["contextGeneration"],
                "continuity": scopes[0]["continuity"],
                "memberIds": sorted(members),
                "nonmembers": len(scopes[0]["nonmembers"]),
                "uncertain": len(scopes[0]["uncertain"]),
            },
            workingBodyBytes=len(canonical(parsed_working["projection"]).encode()),
            workingFrameBytes=len(working_wire),
        )
    # Strictly validate the full public frame used as the independent input.
    full_wire = (canonical(full_frame) + "\n").encode()
    parsed_full = service_parser(full_wire, expected_host=host, expected_uid=uid)
    if parsed_full["snapshot"] != full_snapshot:
        raise AssertionError("full_frame_roundtrip_mismatch")
    return result, independent


def run(args):
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError("immutable_root_missing")
    sys.path.insert(0, str(root))
    from agent_observer.contract import canonical
    from agent_observer.service_contract import parse_frame as parse_service_frame
    from agent_observer.service_state import ServiceState

    is_candidate = args.variant != "a7-full"
    if is_candidate != hasattr(ServiceState, "working_set_frame"):
        raise ValueError("variant_source_api_mismatch")
    working_parser = None
    if is_candidate:
        from agent_observer.working_set_contract import parse_frame as parse_working_frame

        working_parser = parse_working_frame

    seed_bytes = args.seed.read_bytes()
    seed = json.loads(seed_bytes)
    seed, wall, _small, expected_ids, running_ids = build_workload(seed, args.rows, canonical)
    host, uid = "fixture", seed["host"]["uid"]
    clock_now = [10_001]
    options = {"working_set_window_ms": WINDOW_MS} if is_candidate else {}
    state = ServiceState(
        host_scope=host,
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=uid,
        clock=lambda: clock_now[0],
        boot_id="00000000-0000-4000-8000-000000000001",
        clock_domain="time:[123]",
        **options,
    )
    gc.disable()

    generation_cpu_ms = []
    read_cpu_by_generation_ms = []
    per_read_cpu_ms = []
    accepted_input_digests = []
    serialized_frame_bytes = []
    serialized_body_bytes = []
    serialized_selected_bytes = []
    verify_by_generation = []
    read_outputs = []
    sequences = {"full": 1, "working": 1}

    for generation in range(MEASURED_GENERATIONS + 1):
        clock_now[0] = 10_001 + generation
        seed["collectionId"] = str(UUID(int=100 + generation))
        seed["collectedAt"] = wall + generation
        accepted_input_digests.append(digest(seed, canonical))
        extras = {"accepted_boottime_ms": clock_now[0]} if is_candidate else {}

        if generation == 0 or args.validate_only:
            state.attempt("codex", "runtime")
            accepted = state.accept(
                "codex", "runtime", seed,
                sampled_ms=10_000 + generation,
                ttl_ms=100_000,
                **extras,
            )
        else:
            started = time.process_time_ns()
            state.attempt("codex", "runtime")
            accepted = state.accept(
                "codex", "runtime", seed,
                sampled_ms=10_000 + generation,
                ttl_ms=100_000,
                **extras,
            )
            generation_cpu_ms.append((time.process_time_ns() - started) / 1_000_000)
        if accepted is not True:
            raise AssertionError("snapshot_not_accepted")

        verified, independent_rows = verify_generation(
            state, is_candidate, host, uid, canonical, parse_service_frame,
            working_parser, expected_ids, running_ids, sequences,
        )
        verify_by_generation.append(verified)

        if args.validate_only:
            # One untimed local frame round trip validates the requested read
            # path without producing CPU measurements or matrix evidence.
            if args.variant == "candidate-working":
                parsed, rows, _frame_bytes = working_read(
                    state, sequences["working"], working_parser, canonical, host, uid,
                )
                sequences["working"] += 1
            else:
                parsed, rows, _frame_bytes = consumer_read(
                    state, sequences["full"], parse_service_frame, canonical, host, uid,
                )
                sequences["full"] += 1
            if rows != independent_rows:
                raise AssertionError("untimed_read_selection_mismatch")
            break

        read_count = args.reads_per_generation
        # Warm the parser and frame family outside all measured windows.
        if generation == 0:
            warmup_count = max(1, read_count)
            for _ in range(warmup_count):
                if args.variant == "candidate-working":
                    parsed, rows, _frame_bytes = working_read(
                        state, sequences["working"], working_parser, canonical, host, uid,
                    )
                    sequences["working"] += 1
                else:
                    parsed, rows, _frame_bytes = consumer_read(
                        state, sequences["full"], parse_service_frame, canonical, host, uid,
                    )
                    sequences["full"] += 1
                if rows != independent_rows:
                    raise AssertionError("warmup_read_selection_mismatch")
            continue

        generation_read_cpu = 0.0
        per_generation_outputs = []
        for _ in range(read_count):
            started = time.process_time_ns()
            if args.variant == "candidate-working":
                parsed, rows, frame_size = working_read(
                    state, sequences["working"], working_parser, canonical, host, uid,
                )
                sequences["working"] += 1
                payload = parsed["projection"]
            else:
                parsed, rows, frame_size = consumer_read(
                    state, sequences["full"], parse_service_frame, canonical, host, uid,
                )
                sequences["full"] += 1
                payload = parsed["snapshot"]
            elapsed = (time.process_time_ns() - started) / 1_000_000
            generation_read_cpu += elapsed
            per_read_cpu_ms.append(elapsed)
            serialized_frame_bytes.append(frame_size)
            # Byte accounting is outside the CPU window; the timed full-frame
            # encode above already includes this payload exactly once.
            serialized_body_bytes.append(len(canonical(payload).encode()))
            serialized_selected_bytes.append(len(canonical(rows).encode()))
            per_generation_outputs.append(rows)
        read_cpu_by_generation_ms.append(generation_read_cpu)
        read_outputs.append(per_generation_outputs)

    if args.validate_only:
        result = {
            "validationOnly": True,
            "variant": args.variant,
            "rows": args.rows,
            "readsPerGenerationRequested": args.reads_per_generation,
            "verifiedSelectedRows": verify_by_generation[-1]["selectedRows"],
            "workingCoverage": verify_by_generation[-1].get("workingCoverage"),
            "fullDigest": verify_by_generation[-1]["fullDigest"],
            "activeDigest": verify_by_generation[-1]["activeDigest"],
            "selectedDigest": verify_by_generation[-1]["selectedDigest"],
            "workingDigest": verify_by_generation[-1].get("workingDigest"),
            "gcEnabled": gc.isenabled(),
            "loadedModules": capture_loaded_modules(root),
            "scope": "untimed small API/setup check; not a CPU or producer result",
        }
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return

    if len(generation_cpu_ms) != MEASURED_GENERATIONS:
        raise AssertionError("generation_count_mismatch")
    if len(read_cpu_by_generation_ms) != MEASURED_GENERATIONS:
        raise AssertionError("read_generation_count_mismatch")
    if len(read_outputs) != MEASURED_GENERATIONS:
        raise AssertionError("read_output_generation_count_mismatch")
    for index, generation_outputs in enumerate(read_outputs):
        expected_check = verify_by_generation[index + 1]
        for rows in generation_outputs:
            if [native_id(row) for row in rows] != expected_check["selectedIds"]:
                raise AssertionError("read_selection_mismatch")
            if digest(rows, canonical) != expected_check["selectedDigest"]:
                raise AssertionError("read_selected_dto_mismatch")
    for generation_outputs in read_outputs:
        for rows in generation_outputs:
            if not isinstance(rows, list):
                raise AssertionError("read_output_not_rows")

    read_cpu_total = sum(per_read_cpu_ms)
    generation_cpu_total = sum(generation_cpu_ms)
    combined_by_generation = [
        generation_cpu_ms[index] + read_cpu_by_generation_ms[index]
        for index in range(MEASURED_GENERATIONS)
    ]
    result = {
        "python": sys.version.split()[0],
        "variant": args.variant,
        "rows": args.rows,
        "readsPerGeneration": args.reads_per_generation,
        "measuredGenerations": MEASURED_GENERATIONS,
        "warmupGenerations": 1,
        "measuredReads": len(per_read_cpu_ms),
        "generationCpuMs": generation_cpu_ms,
        "generationCpuTotalMs": generation_cpu_total,
        "readCpuMs": per_read_cpu_ms,
        "readCpuByGenerationMs": read_cpu_by_generation_ms,
        "readCpuTotalMs": read_cpu_total,
        "combinedCpuByGenerationMs": combined_by_generation,
        "combinedCpuTotalMs": generation_cpu_total + read_cpu_total,
        "gcEnabled": gc.isenabled(),
        "sourceInputDigest": digest(accepted_input_digests, canonical),
        "seedInputDigest": hashlib.sha256(seed_bytes).hexdigest(),
        "generationInputDigests": accepted_input_digests,
        "fullRowsPerGeneration": [item["fullRows"] for item in verify_by_generation[1:]],
        "activeRowsPerGeneration": [item["activeRows"] for item in verify_by_generation[1:]],
        "selectedRowsPerGeneration": [item["selectedRows"] for item in verify_by_generation[1:]],
        "fullDigest": verify_by_generation[-1]["fullDigest"],
        "activeDigest": verify_by_generation[-1]["activeDigest"],
        "selectedDigest": verify_by_generation[-1]["selectedDigest"],
        "workingDigest": verify_by_generation[-1].get("workingDigest"),
        "workingCoverage": verify_by_generation[-1].get("workingCoverage"),
        "workingReason": verify_by_generation[-1].get("workingReason"),
        "workingScopeMembers": verify_by_generation[-1].get("workingScopeMembers"),
        "workingScope": verify_by_generation[-1].get("workingScope"),
        "fullBodyBytesPerGeneration": [item["fullBodyBytes"] for item in verify_by_generation[1:]],
        "fullFrameBytesPerGeneration": [item["fullFrameBytes"] for item in verify_by_generation[1:]],
        "selectedRowsBytesPerGeneration": [item["selectedRowsBytes"] for item in verify_by_generation[1:]],
        "workingBodyBytesPerGeneration": [item.get("workingBodyBytes") for item in verify_by_generation[1:]],
        "workingFrameBytesPerGeneration": [item.get("workingFrameBytes") for item in verify_by_generation[1:]],
        "readFrameBytesByRead": serialized_frame_bytes,
        "readBodyBytesByRead": serialized_body_bytes,
        "selectedRowsBytesByRead": serialized_selected_bytes,
        "totalSerializedFrameBytes": sum(serialized_frame_bytes),
        "totalSerializedBodyBytes": sum(serialized_body_bytes),
        "totalSelectedRowsBytes": sum(serialized_selected_bytes),
        "loadedModules": capture_loaded_modules(root),
        "ageAnchor": (
            "full-feed filter uses current runtime.observedAt minus activity.at; "
            "the synthetic 1h/10d cases are away from the 72h edge and do not "
            "prove the private accepted-sample Dlo contract"
        ),
        "scope": (
            "pure ServiceState frame/strict parser read path; no SDK, Mesh, "
            "socket transport, native provider, RSS or production acceptance; "
            "serialized frame bytes are measured but not physically delivered"
        ),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="immutable a7 or candidate source root")
    parser.add_argument("seed", type=Path, help="shared API4 snapshot JSON seed")
    parser.add_argument("output", type=Path)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--reads-per-generation", type=int, choices=(0, 1, 4, 16), default=4)
    parser.add_argument("--validate-only", action="store_true",
                        help="one untimed setup/read check; emits no timing data")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
