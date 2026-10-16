"""Fixed Reader-side native bridge admission cost; synthetic data only."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch


async def run(args):
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "studies/prepared"))
    from workload import seed

    from mesh_plus.evidence import digest
    from mesh_plus.state import validate_bridge

    from agent_observer import mesh_profile

    initial = await seed(1, 250)
    profile = mesh_profile.AgentProfile()
    host = initial["mesh"]["hosts"][0]
    codec = profile.bind(host["hostId"], "agent")
    native = profile.restore_native(host["owner"], initial["sessions"])
    state = codec.inspect_native(native)
    payload = {"meshProtocol": 1, "kind": "candidate", "nonce": None,
               "bridgeId": "00000000-0000-0000-0000-000000000099", "sequence": 1,
               "sourceId": "agent", "hostId": host["hostId"], "clock": state.clock,
               "encodedAtMs": native["emittedBoottimeMs"] + 100,
               "ownerFrame": native, "ownerDigest": digest(native), "remaining": [], "error": None}
    validate_bridge(profile, codec, payload)
    with patch.object(mesh_profile, "validate_frame", wraps=mesh_profile.validate_frame) as validate:
        start = time.process_time_ns()
        for _ in range(20):
            state = validate_bridge(profile, codec, payload)
        cpu = time.process_time_ns() - start
    result = {"cpuNs": cpu, "nativeValidations": validate.call_count, "calls": 20, "rows": 250,
              "semanticSignature": hashlib.sha256(json.dumps(state.records, sort_keys=True).encode()).hexdigest(),
              "observer": importlib.metadata.version("agent-observer"),
              "mesh": importlib.metadata.version("mesh-plus"), "python": sys.version,
              "ownerModule": mesh_profile.__file__, "cleanup": True,
              "limits": ["synthetic complete generic bridge admission; immutable fixture setup and warm-up excluded",
                         "ordinary Client admission remains independent and is outside this specific measured operation",
                         "no live source, transport, publisher, collector, dashboard or device CPU claim"]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
