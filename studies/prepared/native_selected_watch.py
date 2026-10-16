"""Installed owned/selected cached IPC + SSH parity, bounded metadata only."""

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path


def expected(row):
    return (row["identity"]["provider"] == "codex" and row["kind"] in {"user", "unknown"}
            and row["runtime"]["value"] == "running" and row["runtime"]["health"] == "current")


def summary(row):
    return (tuple(row["identity"][key] for key in
                  ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")),
            row["kind"], row["runtime"]["value"], row["runtime"]["health"])


async def run(seconds):
    from mesh_plus.api import AdmittedResponse, ReadGuard, configured_reader
    from mesh_plus.catalog import SSHPlusAuthority
    from mesh_plus.evidence import clock_domain
    from mesh_plus.transport import boottime_ms

    from agent_observer.mesh_profile import AgentProfile
    from agent_observer.mesh_read import AgentSelection, PreparedAgentWatch

    profile = AgentProfile()
    reader = await configured_reader("agent", source="agent", scope="hosts", hosts=["snap", "starship"],
        socket=Path(f"/run/user/{os.getuid()}/mesh-plus-agent/read.sock"), authority=SSHPlusAuthority(),
        report_routes=False, profile=profile)
    request = secrets.token_hex(16)
    full = ReadGuard("agent", request, host_ids=["snap", "starship"], profile=profile)
    watch = PreparedAgentWatch(request, host_ids=["snap", "starship"], profile=profile,
        selection=AgentSelection(providers=frozenset({"codex"}), kinds=frozenset({"user", "unknown"}),
                                 runtime_values=frozenset({"running"}), runtime_healths=frozenset({"current"})))
    stream = reader.watch_admitted(mode="hosts", hosts=["snap", "starship"], request_id=request)
    samples, seen = [], set()
    try:
        async with asyncio.timeout(seconds):
            async for frame in stream:
                raw = frame.snapshot() if isinstance(frame, AdmittedResponse) else frame
                full.accept(raw)
                watch.accept(frame)
                now, clock = boottime_ms(), clock_domain()
                read, rows = watch.read(now, clock), full.current(now, clock)
                assert read.sessions == [r for r in rows if expected(r)]
                assert tuple((s.identity, s.kind, s.runtime_value, s.runtime_health) for s in read.summaries) == tuple(map(summary, rows))
                if "sessions" not in raw:
                    continue
                assert isinstance(frame, AdmittedResponse) and watch.snapshot() == raw
                hosts = raw["mesh"]["hosts"]
                seen.update(h["hostId"] for h in hosts if h["delivery"]["status"] == "ready")
                # Mutated raw exports must not change the token or guard.
                raw["sessions"].clear()
                assert watch.snapshot() == frame.snapshot()
                samples.append({"kind": read.context["kind"], "currentRows": len(rows),
                    "selectedRows": len(read.sessions), "currentSummaries": len(read.summaries),
                    "positiveExclusions": sum(s.kind in {"child", "system"} or
                                               s.runtime_health == "current" and s.runtime_value == "parked"
                                               for s in read.summaries),
                    "rawDigest": hashlib.sha256(json.dumps(frame.snapshot(), sort_keys=True).encode()).hexdigest(),
                    "hosts": [{"hostId": h["hostId"], "delivery": h["delivery"]["status"],
                               "proof": h["delivery"]["proof"] is not None, "view": h["viewState"]} for h in hosts]})
    except TimeoutError:
        pass
    finally:
        full.disconnect()
        watch.disconnect()
        await stream.aclose()
    assert seen == {"snap", "starship"} and len(samples) >= 3
    assert reader.inspect()["activeConnections"] == 0 and reader.inspect()["cleanupFailures"] == 0
    assert watch.snapshot() is None and watch.read(boottime_ms(), clock_domain()).summaries == ()
    return {"status": "passed", "seconds": seconds, "samples": samples,
            "ownerModule": sys.modules["agent_observer.mesh_read"].__file__,
            "activeConnectionsAfter": 0, "cleanupFailures": 0,
            "limits": ["real ordinary cached IPC/fixed SSH source, no provider actions or selection changes",
                       "strict full-read comparison checks facade parity, not independent native completeness",
                       "independent native daemon comparisons are separate evaluate-observation/evaluate-mesh receipts",
                       "extra diagnostic reader; never a CPU measurement or physical/device acceptance"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(run(args.seconds))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}))
