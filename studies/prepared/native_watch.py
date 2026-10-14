"""Installed cached IPC/fixed-SSH parity; bounded metadata only, no actions."""

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path


async def run(seconds):
    from mesh_plus.api import ReadGuard, configured_reader
    from mesh_plus.catalog import SSHPlusAuthority
    from mesh_plus.evidence import clock_domain
    from mesh_plus.transport import boottime_ms

    from agent_observer.mesh_profile import AgentProfile
    from agent_observer.mesh_read import PreparedAgentWatch

    profile = AgentProfile()
    reader = await configured_reader("agent", source="agent", scope="hosts", hosts=["snap", "starship"],
        socket=Path(f"/run/user/{os.getuid()}/mesh-plus-agent/read.sock"), authority=SSHPlusAuthority(),
        report_routes=False, profile=profile)
    request = secrets.token_hex(16)
    legacy = ReadGuard("agent", request, host_ids=["snap", "starship"], profile=profile)
    prepared = PreparedAgentWatch(request, host_ids=["snap", "starship"], profile=profile)
    stream = reader.execute({"meshProtocol": 1, "requestId": request, "operation": "watch",
        "profile": profile.descriptor.profile_id, "access": "cached",
        "selection": {"mode": "hosts", "hostIds": ["snap", "starship"]}, "extensions": {}})
    samples, replacements, seen = [], 0, set()
    try:
        async with asyncio.timeout(seconds):
            async for frame in stream:
                legacy.accept(frame)
                prepared.accept(frame)
                now = boottime_ms()
                current = prepared.read(now, clock_domain())
                if current.sessions != legacy.current(now, clock_domain()):
                    raise ValueError("installed_current_equality")
                if "sessions" in frame:
                    replacements += 1
                    if prepared.snapshot() != frame:
                        raise ValueError("installed_raw_equality")
                    for host in frame["mesh"]["hosts"]:
                        if host["delivery"]["status"] == "ready":
                            seen.add(host["hostId"])
                    samples.append({"kind": frame["mesh"]["kind"], "status": frame["mesh"]["status"],
                        "currentRows": len(current.sessions), "rawRows": len(frame["sessions"]),
                        "rawDigest": hashlib.sha256(json.dumps(frame, sort_keys=True).encode()).hexdigest(),
                        "hosts": [{"hostId": h["hostId"], "delivery": h["delivery"]["status"],
                                   "proof": h["delivery"]["proof"] is not None,
                                   "view": h["viewState"]} for h in frame["mesh"]["hosts"]]})
    except TimeoutError:
        pass
    finally:
        legacy.disconnect()
        prepared.disconnect()
        await stream.aclose()
    if seen != {"snap", "starship"} or replacements < 3 or reader.inspect()["activeConnections"]:
        raise ValueError("installed_coverage_or_cleanup")
    return {"status": "passed", "ownerModule": sys.modules["agent_observer.mesh_read"].__file__,
            "seconds": seconds, "samples": samples, "replacements": replacements,
            "currentAfterDisconnect": len(prepared.read(boottime_ms(), clock_domain()).sessions),
            "rawAfterDisconnect": prepared.snapshot(), "activeConnectionsAfter": reader.inspect()["activeConnections"],
            "limits": ["installed ordinary cached IPC/fixed SSH parity", "native daemon completeness checked independently",
                       "no provider actions, route writes or dashboard selection"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, choices=range(10, 121), default=40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(run(args.seconds))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}))
