#!/usr/bin/env python3
"""Controlled cached-producer cost; no providers, services, Mesh or network I/O.

Run this same file with separately selected installed interpreters.  It never
adds the checkout to sys.path, and full mode uses only the accepted a6 APIs.
Construction, warm-up and semantic hashing are outside the measured CPU windows.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import patch


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True,
                        help="explicit frozen Service 4 view fixture")
    parser.add_argument("--mode", choices=("full", "active"), required=True)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--active", type=int, default=10)
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--reads", type=int, default=4)
    parser.add_argument("--output", type=Path, help="also write the compact JSON result here")
    args = parser.parse_args()
    if not 1 <= args.active <= args.rows:
        parser.error("--active must be between 1 and --rows")
    if not 1 <= args.generations <= 1000 or not 1 <= args.reads <= 100:
        parser.error("--generations must be 1..1000 and --reads must be 1..100")
    return args


def run(args):
    import agent_observer
    from agent_observer.contract import (
        MAX_SESSIONS,
        MAX_SNAPSHOT_BYTES,
        canonical,
        identity_key,
        validate_snapshot,
    )
    from agent_observer.service_contract import MAX_FRAME_BYTES as FULL_FRAME_CAP
    from agent_observer.service_contract import parse_frame as parse_full_frame
    from agent_observer.service_contract import validate_frame as validate_full_frame
    from agent_observer.service_state import ServiceState

    if args.mode == "active":
        from agent_observer.active_contract import MAX_FRAME_BYTES as FRAME_CAP
        from agent_observer.active_contract import parse_frame
    else:
        FRAME_CAP, parse_frame = FULL_FRAME_CAP, parse_full_frame

    fixture = validate_full_frame(json.loads(args.fixture.read_text(encoding="utf-8")))
    snapshot = fixture["snapshot"]
    source = next(s for s in snapshot["sources"] if s["provider"] == "codex")
    template = next(r for r in snapshot["sessions"] if r["identity"]["provider"] == "codex")
    host, uid = fixture["hostScope"], fixture["uid"]
    base_boot = fixture["emittedBoottimeMs"]
    base_wall = fixture["emittedAt"]
    lease_ms, runtime_lease_ms, cadence_ms = 60000, 30000, 1000
    # Even the maximum requested read count stays within the next generation's
    # cadence and both original leases; reads themselves never renew a sample.
    read_step_ms = min(100, max(1, cadence_ms // (args.reads + 1)))
    clock = [base_boot]
    fixed_uuid = uuid.UUID(fixture["serviceId"])

    def wall_ns():
        return (base_wall + clock[0] - base_boot) * 1_000_000

    def create_state():
        state = ServiceState(
            host_scope=host, configs={"codex": (source["configHome"], source["configHomeKind"])},
            uid=uid, clock=lambda: clock[0], boot_id=fixture["bootId"],
            clock_domain=fixture["clockDomain"],
        )
        state.native_hostname = snapshot["host"]["nativeHostname"]
        return state

    def selected(row):
        return (row["identity"]["provider"] == "codex" and row["kind"] in {"user", "unknown"}
                and row["runtime"]["value"] == "running" and row["runtime"]["health"] == "current")

    def native_generation(generation):
        sample = base_boot + generation * cadence_ms
        wall = base_wall + generation * cadence_ms
        value = copy.deepcopy(snapshot)
        value["sources"] = [copy.deepcopy(source)]
        native_source = value["sources"][0]
        native_source.update(sourceHealth="current", errors=[], limitations=["synthetic_controlled_native_fixture"])
        native_source["coverage"]["runtime"].update(status="complete", reason="native_snapshot")
        native_source["coverage"]["saved"].update(status="complete", reason="native_snapshot")
        native_source["capabilities"].update(runtime=["running", "parked"],
                                               phase=["working", "blocked", "waiting"],
                                               blockedReasons=["approval"], activity=True,
                                               timing={"lastUpdated": True, "latestTurn": True})
        value.update(collectedAt=wall, collectionId=str(fixed_uuid), sourceHealth="current",
                     errors=[], sessions=[], limitations=["synthetic_controlled_native_fixture"])
        for number in range(args.rows):
            row = copy.deepcopy(template)
            identifier = str(uuid.UUID(int=number + 1))
            active = number < args.active
            phase = ("working", "blocked", "waiting")[(generation + number) % 3] if active else None
            row["identity"]["nativeId"] = identifier
            row["nativeIds"] = {"threadId": identifier, "sessionTreeRootId": identifier}
            row.update(title="synthetic-agent-" + str(number), kind="unknown" if number % 2 else "user",
                       hasSavedHistory=True, inventory="saved", workspace=None, metadataIssues=[])
            row["runtime"].update(value="running" if active else "parked", health="current",
                                  source="codex_rpc", reason="native_snapshot", observedAt=wall, clock="sample")
            if active:
                row["phase"] = {"value": phase, "health": "current", "source": "codex_rpc",
                                "reason": "native_snapshot", "observedAt": wall, "clock": "sample"}
            else:
                row["phase"] = None
            row["blockedReasons"] = ["approval"] if phase == "blocked" else []
            activity = wall - 1000 - number
            row["activity"] = {"at": activity, "source": "codex_turn_metadata", "health": "current",
                               "reason": "native_conversation_event"}
            pending = phase in {"working", "blocked"}
            row["outcome"] = (
                {"value": "unknown", "observedAt": None, "source": None, "health": "unavailable",
                 "reason": "turn_in_progress", "clock": None} if pending else
                {"value": "completed", "observedAt": activity, "source": "codex_turn_metadata",
                 "health": "current", "reason": "latest_terminal_turn", "clock": "native"}
            )
            origin = {"component": "history", "sampledBoottimeMs": sample,
                      "observedBoottimeMs": sample, "contextGeneration": 0}
            row["lastUpdated"] = {
                "at": wall - 1000, "timestampPrecisionMs": 1000, "observedAt": wall,
                "source": "codex_thread_metadata", "health": "current", "reason": "native_thread_update",
                "receipt": copy.deepcopy(origin),
            }
            row["latestTurn"] = {
                "value": {"id": "synthetic-turn-" + str(number),
                          "status": "in_progress" if pending else "completed", "startedAt": wall - 10000,
                          "completedAt": None if pending else wall - 1000,
                          "durationMs": None if pending else 9000, "timestampPrecisionMs": 1000},
                "observedAt": wall, "source": "codex_turn_metadata", "health": "current",
                "reason": "native_latest_turn", "receipt": copy.deepcopy(origin),
            }
            value["sessions"].append(row)
        validate_snapshot(value)
        size = len(canonical(value).encode())
        if len(value["sessions"]) > MAX_SESSIONS or size > MAX_SNAPSHOT_BYTES:
            raise ValueError("synthetic_native_capacity")
        return value, size

    def accept(state, value):
        state.attempt("codex", "history")
        if not state.accept("codex", "history", value, sampled_ms=clock[0], ttl_ms=lease_ms,
                            runtime_ttl_ms=runtime_lease_ms):
            raise ValueError("synthetic_accept_rejected")

    def cached_frame(state, sequence):
        if args.mode == "active":
            return state.active_frame("status", sequence)
        return state.frame("status", sequence)

    def parse_select(wire):
        frame = parse_frame(wire, expected_host=host, expected_uid=uid)
        if args.mode == "active":
            rows = frame["projection"]["sessions"]
        else:
            rows = [row for row in frame["snapshot"]["sessions"] if selected(row)]
        return frame, rows

    def digest_update(digest, value):
        digest.update(canonical(value).encode())
        digest.update(b"\n")

    def leases(frame):
        return [{"provider": item["provider"], "namespace": item["namespace"],
                 "contextGeneration": item["contextGeneration"],
                 "components": sorted(item["components"], key=lambda c: c["name"])}
                for item in sorted(frame["sources"], key=lambda s: (s["provider"], s["namespace"]))]

    cpu = dict.fromkeys(("generation", "cachedFrame", "encoding", "parseSelection"), 0)
    wire_sizes, native_sizes = [], []
    selected_digest, lease_digest, decision_digest = (hashlib.sha256() for _ in range(3))
    complete_reads = 0
    with patch("agent_observer.service_state.uuid.uuid4", new=lambda: fixed_uuid), \
            patch("agent_observer.service_state.time.time_ns", new=wall_ns):
        # Warm the same public paths in a disposable in-process state.  The
        # measured state starts fresh, with the same exact receipt counters.
        warm_value, _ = native_generation(0)
        warm = create_state()
        accept(warm, warm_value)
        parse_select((canonical(cached_frame(warm, 1)) + "\n").encode())
        del warm, warm_value
        state = create_state()
        for generation in range(args.generations):
            clock[0] = base_boot + generation * cadence_ms
            value, native_size = native_generation(generation)
            native_sizes.append(native_size)
            expected_keys = {identity_key(row["identity"]) for row in value["sessions"]}
            expected_selected = {identity_key(row["identity"]) for row in value["sessions"] if selected(row)}
            start = time.process_time_ns()
            accept(state, value)
            cpu["generation"] += time.process_time_ns() - start
            if state.revision != generation + 1 or len(state.snapshot["sessions"]) != args.rows:
                raise ValueError("generation_or_capacity_parity")
            expected_rows = sorted((row for row in state.snapshot["sessions"] if selected(row)),
                                   key=lambda row: identity_key(row["identity"]))
            expected_leases = leases({"sources": [state.source_meta("codex")]})
            for read in range(args.reads):
                clock[0] = base_boot + generation * cadence_ms + read * read_step_ms
                sequence = generation * args.reads + read + 1
                start = time.process_time_ns()
                frame = cached_frame(state, sequence)
                cpu["cachedFrame"] += time.process_time_ns() - start
                start = time.process_time_ns()
                wire = (canonical(frame) + "\n").encode()
                cpu["encoding"] += time.process_time_ns() - start
                wire_sizes.append(len(wire))
                if len(wire) > FRAME_CAP:
                    raise ValueError("synthetic_frame_capacity")
                start = time.process_time_ns()
                parsed, rows = parse_select(wire)
                cpu["parseSelection"] += time.process_time_ns() - start
                # These stronger oracles and hashes are deliberately outside
                # all CPU windows; active transport never receives inactive IDs.
                rows = sorted(rows, key=lambda row: identity_key(row["identity"]))
                actual_selected = {identity_key(row["identity"]) for row in rows}
                if rows != expected_rows or actual_selected != expected_selected or len(rows) != args.active:
                    raise ValueError("selected_body_parity")
                if leases(parsed) != expected_leases or state.revision != generation + 1:
                    raise ValueError("cached_read_renewed_original_lease")
                if args.mode == "full":
                    if {identity_key(row["identity"]) for row in parsed["snapshot"]["sessions"]} != expected_keys:
                        raise ValueError("full_identity_parity")
                    coverage = parsed["snapshot"]["sources"][0]["coverage"]
                    complete = all(coverage[dimension]["status"] == "complete" for dimension in ("runtime", "saved"))
                else:
                    scopes = parsed["projection"]["scopes"]
                    complete = (len(scopes) == 1 and scopes[0]["coverage"]["status"] == "complete"
                                and not scopes[0]["uncertain"] and not scopes[0]["nonmembers"]
                                and {identity_key(item["identity"]) for item in scopes[0]["members"]} == actual_selected)
                if not complete:
                    raise ValueError("full_membership_authority_incomplete")
                complete_reads += 1
                actual_decisions = [(list(key), key in actual_selected) for key in sorted(expected_keys)]
                expected_decisions = [(list(key), key in expected_selected) for key in sorted(expected_keys)]
                if actual_decisions != expected_decisions:
                    raise ValueError("full_membership_decision_parity")
                digest_update(selected_digest, rows)
                digest_update(lease_digest, expected_leases)
                digest_update(decision_digest, actual_decisions)
        projector = getattr(state, "active_projector", None)
        projector_generations = getattr(projector, "generations", None)
        if projector_generations is not None and projector_generations != args.generations:
            raise ValueError("projection_recomputed_during_cached_reads")
    cpu["cachedReadTotal"] = sum(cpu[key] for key in ("cachedFrame", "encoding", "parseSelection"))
    cpu["measuredTotal"] = cpu["generation"] + cpu["cachedReadTotal"]
    try:
        version = importlib.metadata.version("agent-observer")
    except importlib.metadata.PackageNotFoundError:
        version = getattr(agent_observer, "__version__", None)
    return {
        "kind": "controlled synthetic cached producer; no Mesh/native/rollout acceptance",
        "mode": args.mode, "ownerRoot": str(Path(agent_observer.__file__).resolve().parent),
        "ownerVersion": version, "python": sys.version.split()[0],
        "fixture": str(args.fixture.resolve()), "rows": args.rows, "active": args.active,
        "generations": args.generations, "readsPerGeneration": args.reads,
        "warmupGenerationsExcluded": 1, "cadenceMs": cadence_ms, "cpuNs": cpu,
        "bytes": {"cachedReadsTotal": sum(wire_sizes), "perReadMin": min(wire_sizes),
                  "perReadMax": max(wire_sizes), "nativeGenerationTotal": sum(native_sizes),
                  "nativeGenerationMax": max(native_sizes)},
        "selectedSignature": selected_digest.hexdigest(), "originalLeasesSignature": lease_digest.hexdigest(),
        "fullMembershipSignature": decision_digest.hexdigest(), "fullMembershipDecisionParity": True,
        "selectedBodyParity": True, "originalLeasesPreserved": True,
        "completeReads": complete_reads, "cachedProjectorGenerations": projector_generations,
        "limits": {"nativeRows": MAX_SESSIONS, "nativeBytes": MAX_SNAPSHOT_BYTES,
                   "frameBytes": FRAME_CAP, "capacityPassed": True,
                   "measurementsExclude": ["fixture construction", "warmup", "semantic hashing", "transport", "Mesh", "RLCD"],
                   "memory": "not measured; no profiler/tracemalloc in CPU windows"},
        "cleanup": {"nativeActions": 0, "servers": 0, "connections": 0,
                    "filesWritten": 1 if args.output else 0},
    }


def main():
    args = arguments()
    result = json.dumps(run(args), sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
