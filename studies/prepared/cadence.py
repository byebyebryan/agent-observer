#!/usr/bin/env python3
"""Bounded cached fleet cadence; retain counts, never native payloads."""

import argparse
import asyncio
import importlib.metadata
import json
import os
import secrets
import sys
import time
from collections import Counter
from pathlib import Path


async def measure(seconds):
    from mesh_plus.api import ReadGuard, configured_reader
    from mesh_plus.catalog import SSHPlusAuthority

    from agent_observer.mesh_profile import AgentProfile

    profile = AgentProfile()
    reader = await configured_reader(
        "agent", source="agent", socket=Path(f"/run/user/{os.getuid()}/mesh-plus-agent/read.sock"),
        scope="hosts", hosts=["snap", "starship"], authority=SSHPlusAuthority(),
        report_routes=False, profile=profile,
    )
    request_id = secrets.token_hex(16)
    guard = ReadGuard("agent", request_id, profile=profile, host_ids=["snap", "starship"])
    stream = reader.execute({
        "meshProtocol": 1, "requestId": request_id, "operation": "watch",
        "profile": profile.descriptor.profile_id, "access": "cached",
        "selection": {"mode": "hosts", "hostIds": ["snap", "starship"]}, "extensions": {},
    })
    counts, shapes, revisions, native_changes = Counter(), [], {}, Counter()
    started = time.monotonic()
    try:
        async with asyncio.timeout(seconds):
            async for frame in stream:
                guard.accept(frame)
                if "mesh" not in frame:
                    counts["base_error"] += 1
                    break
                kind = frame["mesh"]["kind"]
                counts[kind] += 1
                if "sessions" not in frame:
                    continue
                shape = {}
                for host in frame["mesh"]["hosts"]:
                    name = host["hostId"]
                    rows = [r for r in frame["sessions"] if r["identity"]["hostScope"] == name]
                    shape[name] = {"rows": len(rows), "delivery": host["delivery"]["status"],
                                   "view": host["viewState"]}
                    owner = host["owner"]
                    if owner is not None:
                        revision = (owner["service"]["serviceId"], owner["service"]["viewRevision"])
                        if name in revisions and revision != revisions[name]:
                            native_changes[name] += 1
                        revisions[name] = revision
                shapes.append({"atSeconds": round(time.monotonic() - started, 3), "hosts": shape})
    except TimeoutError:
        pass
    finally:
        guard.disconnect()
        await stream.aclose()
    elapsed = time.monotonic() - started
    return {
        "evidence": "bounded installed cached fleet watch; not independent native completeness",
        "python": sys.version, "packages": {p: importlib.metadata.version(p) for p in ("agent-observer", "mesh-plus", "jsonschema")},
        "profile": profile.descriptor.profile_id, "seconds": round(elapsed, 3),
        "frameCounts": dict(counts), "nativeViewChanges": dict(native_changes),
        "oneHzReadsPerReplacement": round(elapsed / max(1, len(shapes)), 3),
        "shapes": shapes, "activeConnectionsAfter": reader.inspect()["activeConnections"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, choices=range(1, 301), default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(measure(args.seconds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "shapes"}))
