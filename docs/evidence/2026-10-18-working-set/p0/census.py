"""Read one existing installed cached snapshot; emit aggregate metadata only."""

import collections
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys


def encoded_size(value):
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def main():
    host = sys.argv[1]
    endpoint = pathlib.Path(f"/run/user/{os.geteuid()}/agent-observer/read.sock")
    executable = shutil.which("agent-observer")
    if not endpoint.exists() or not executable:
        print(json.dumps({"hostScope": host, "status": "unavailable", "reason": "existing_cached_endpoint_missing"}))
        return 0
    result = subprocess.run(
        [executable, "service", "snapshot", "--host-scope", host, "--socket", str(endpoint), "--timeout", "15"],
        capture_output=True, timeout=25, cwd="/tmp",
    )
    if result.returncode:
        try:
            reason = json.loads(result.stderr).get("error", "cached_read_failed")
        except (ValueError, AttributeError):
            reason = "cached_read_failed"
        print(json.dumps({"hostScope": host, "status": "unavailable", "reason": reason, "returncode": result.returncode}))
        return 0
    frame = json.loads(result.stdout)
    snapshot = frame.get("snapshot")
    if frame.get("serviceProtocol") != 4 or frame.get("hostScope") != host or snapshot is None:
        print(json.dumps({"hostScope": host, "status": "unavailable", "reason": "cached_shape_or_warming"}))
        return 0
    windows = {"24h": 86_400_000, "3d": 259_200_000, "7d": 604_800_000}
    sets = {name: {"selected": 0, "selectedBodyBytes": 0, "recentNonactive": 0} for name in windows}
    kinds, runtimes, healths, ages = (collections.Counter() for _ in range(4))
    total_bytes = active_count = active_bytes = eligible_count = 0
    unknown_runtime_recent = collections.Counter()
    anchor_fields = collections.Counter()
    for row in snapshot["sessions"]:
        size = encoded_size(row)
        total_bytes += size
        kinds[row["kind"]] += 1
        runtime, activity = row["runtime"], row["activity"]
        runtimes[runtime["value"]] += 1
        healths[runtime["health"]] += 1
        if row["kind"] not in {"unknown", "user"}:
            continue
        eligible_count += 1
        active = runtime["health"] == "current" and runtime["value"] == "running"
        if active:
            active_count += 1
            active_bytes += size
        anchor_fields["activityCurrent"] += activity["health"] == "current" and type(activity["at"]) is int
        anchor_fields["runtimeSampleClockCurrent"] += (
            runtime["health"] == "current" and runtime["clock"] == "sample" and type(runtime["observedAt"]) is int
        )
        age = None
        if (activity["health"] == "current" and type(activity["at"]) is int
                and runtime["health"] == "current" and runtime["clock"] == "sample"
                and type(runtime["observedAt"]) is int):
            age = runtime["observedAt"] - activity["at"]
        if age is None:
            ages["unknown"] += 1
        elif age < 0:
            ages["future"] += 1
        else:
            ages["under24h" if age < windows["24h"] else "24hTo3d" if age < windows["3d"]
                 else "3dTo7d" if age < windows["7d"] else "7dOrOlder"] += 1
        for name, limit in windows.items():
            recent = age is not None and 0 <= age < limit
            if active or recent:
                sets[name]["selected"] += 1
                sets[name]["selectedBodyBytes"] += size
            if recent and not active:
                sets[name]["recentNonactive"] += 1
            if recent and runtime["value"] == "unknown":
                unknown_runtime_recent[name] += 1
    print(json.dumps({
        "hostScope": host, "nativeHostname": socket.gethostname(), "status": "cached_source_screen",
        "readerExecutable": str(pathlib.Path(executable).resolve()), "serviceProtocol": frame["serviceProtocol"],
        "viewRevision": frame["viewRevision"], "serviceState": frame["state"], "snapshotHealth": snapshot["sourceHealth"],
        "rows": len(snapshot["sessions"]), "eligibleByPublishedKind": eligible_count,
        "allBodyBytes": total_bytes, "cachedFrameBytes": len(result.stdout), "active": active_count,
        "activeBodyBytes": active_bytes, "kinds": dict(kinds), "runtimes": dict(runtimes),
        "runtimeHealths": dict(healths), "eligibleAgeBins": dict(ages), "windows": sets,
        "unknownRuntimeRecent": dict(unknown_runtime_recent), "sourceAgeFields": dict(anchor_fields),
        "sources": [{"provider": source["provider"], "sourceHealth": source["sourceHealth"],
                     "coverage": source["coverage"]} for source in snapshot["sources"]],
        "limits": ["one cached public snapshot; not independent native classification", "published kind/runtime/activity estimates; transient exact FactSupport unavailable in full wire", "age uses existing current runtime sample contract; not a new wall/BOOTTIME anchor proof", "body-byte totals exclude projected support/coverage/header ownership and all CPU/RSS claims"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
