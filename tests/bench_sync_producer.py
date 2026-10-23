"""Matched synthetic producer CPU probe, without provider or service I/O.

Run with an installed Python in isolated mode for the legacy side and an
explicit source overlay for sync. This probes owner generation only: there is
no baseline frame delivery, publisher, Reader, installed candidate or native
acceptance. Keep runs serial under the shared CPU advisory lock.
"""

import argparse
import copy
import gc
import hashlib
import importlib.metadata
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

from agent_observer.service_state import ServiceState


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sources():
    return {
        module.__file__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for name, module in tuple(sys.modules.items())
        if name.startswith("agent_observer.") and getattr(module, "__file__", "").endswith(".py")
    }


def native_shaped_snapshot(rows):
    frame = json.loads((Path(__file__).parent / "fixtures/service-v4/view.json").read_text())
    snapshot = copy.deepcopy(frame["snapshot"])
    snapshot["sources"] = [s for s in snapshot["sources"] if s["provider"] == "codex"]
    template = next(r for r in snapshot["sessions"] if r["identity"]["provider"] == "codex")
    snapshot["sessions"] = []
    wall = 1_700_000_020_000
    snapshot["sources"][0]["capabilities"].update(
        activity=True, timing={"lastUpdated": True, "latestTurn": True}, runtime=["running", "parked"]
    )
    for index in range(rows):
        row = copy.deepcopy(template)
        identity = str(uuid.UUID(int=index + 1))
        row["identity"]["nativeId"] = identity
        row["nativeIds"] = {"threadId": identity, "sessionTreeRootId": identity}
        row.update(kind="user", title=f"native-shape-{index}", hasSavedHistory=True,
                   inventory="saved", workspace=None)
        row["runtime"]["value"] = "running" if index < 10 else "parked"
        if index >= 10:
            row["phase"], row["blockedReasons"] = None, []
        row["activity"] = {"at": wall - 1000, "source": "codex_turn_metadata",
                           "health": "current", "reason": "native_conversation_event"}
        row["outcome"] = {"value": "completed", "observedAt": wall - 1000,
                          "source": "codex_turn_metadata", "health": "current",
                          "reason": "latest_terminal_turn", "clock": "native"}
        receipt = {"component": "history", "sampledBoottimeMs": 15000,
                   "observedBoottimeMs": 15000, "contextGeneration": 0}
        row["lastUpdated"] = {"at": wall - 1000, "timestampPrecisionMs": 1000,
                              "observedAt": wall, "source": "codex_thread_metadata",
                              "health": "current", "reason": "native_thread_update",
                              "receipt": dict(receipt)}
        row["latestTurn"] = {
            "value": {"id": f"turn-{index}", "status": "completed", "startedAt": wall - 10000,
                      "completedAt": wall - 1000, "durationMs": 9000, "timestampPrecisionMs": 1000},
            "observedAt": wall, "source": "codex_turn_metadata", "health": "current",
            "reason": "native_latest_turn", "receipt": dict(receipt),
        }
        snapshot["sessions"].append(row)
    return frame["bootId"], snapshot, wall


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--mode", choices=("legacy", "sync"), required=True)
    parser.add_argument("--sync-serialization", choices=("expanded", "compact"), default="expanded")
    parser.add_argument("--workload", choices=("timestamp", "all-bodies"), default="timestamp")
    parser.add_argument("--generations", type=int, default=6)
    args = parser.parse_args()
    if args.generations < 6:
        parser.error("at least six generations are required")
    boot, value, wall = native_shaped_snapshot(args.rows)
    now = [15000]
    # This disposable process owns its synthetic clock/incarnation only.
    uuid.uuid4 = lambda: uuid.UUID(int=0xF000 + now[0])
    cold = time.process_time_ns()
    sync_options = {"sync_serialization": args.sync_serialization} if args.mode == "sync" else {}
    state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                         uid=1000, clock=lambda: now[0], boot_id=boot, clock_domain="time:[123]",
                         **sync_options)
    state.wall_clock = lambda: wall + now[0]
    state.attempt("codex", "history")
    state.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
    common_cold = time.process_time_ns() - cold
    owner, sync_cpu = None, [0]
    if args.mode == "sync":
        owner = state._sync_owner()
        cold = time.process_time_ns()
        owner.ensure("full")
        owner.ensure("active")
        sync_cold = time.process_time_ns() - cold
        original_publish = owner.publish

        def measured_publish(*a, **kw):
            started = time.process_time_ns()
            try:
                return original_publish(*a, **kw)
            finally:
                sync_cpu[0] += time.process_time_ns() - started

        owner.publish = measured_publish
    else:
        sync_cold = 0
    hashes = sources()
    totals, common, sync, oracle, signatures = [], [], [], [], []
    for _generation in range(args.generations):
        now[0] += 10
        for row in value["sessions"]:
            row["runtime"]["observedAt"] += 1000
            if row["phase"] is not None:
                row["phase"]["observedAt"] += 1000
            row["lastUpdated"]["observedAt"] += 1000
            if args.workload == "all-bodies":
                row["lastUpdated"]["at"] += 1000
            for name in ("lastUpdated", "latestTurn"):
                row[name]["receipt"].update(sampledBoottimeMs=now[0], observedBoottimeMs=now[0])
        before_sync = sync_cpu[0]
        started = time.process_time_ns()
        state.attempt("codex", "history")
        state.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
        oracle_started = time.process_time_ns()
        signature = {"snapshot": state.snapshot, "projection": state.sync_active_projection,
                     "supports": [[list(k), v] for k, v in sorted(state.projection_support.items())],
                     "census": state.projection_census}
        signatures.append(hashlib.sha256(canonical(signature).encode()).hexdigest())
        oracle.append(time.process_time_ns() - oracle_started)
        totals.append(time.process_time_ns() - started)
        sync.append(sync_cpu[0] - before_sync)
        common.append(totals[-1] - sync[-1] - oracle[-1])
    result = {
        "scope": "synthetic producer only; no delivered baseline, transport or installed candidate acceptance",
        "mode": args.mode, "workload": args.workload, "rows": args.rows,
        "serialization": args.sync_serialization if owner is not None else None,
        "cyclicGcEnabled": gc.isenabled(),
        "version": importlib.metadata.version("agent-observer"), "generations": args.generations,
        "cpuNs": totals, "medianCpuNs": statistics.median(totals), "commonCpuNs": common,
        "syncCpuNs": sync, "oracleCpuNs": oracle, "signatures": signatures,
        "commonColdCpuNs": common_cold, "syncRootsColdCpuNs": sync_cold,
        "sourceHashesStart": hashes, "sourceHashes": sources(),
        "account": None if owner is None else owner.account.snapshot(),
        "syncCounts": None if owner is None else dict(owner.counts),
        "failures": None if owner is None else {name: slot.failed for name, slot in owner.views.items()},
        "membershipCells": None if owner is None else {
            name: slot.current.tables["memberships"].count
            for name, slot in owner.views.items() if slot.current is not None
        },
    }
    if owner is not None:
        owner.close()
        result["closedAccount"] = owner.account.snapshot()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
