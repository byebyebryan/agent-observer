"""Fixed synthetic admission/render cost under an explicitly selected owner."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--owner-root', type=Path)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.owner_root:
    sys.path.insert(0, str(args.owner_root))
sys.path.insert(0, str(args.repo/'studies/prepared'))
from workload import seed, publications, REQUEST
from agent_observer.contract import validate_snapshot, canonical
from agent_observer.service_contract import StreamGuard, parse_frame
from agent_observer.mesh_profile import AgentProfile
from agent_observer.mesh_read import PreparedAgentWatch
from agent_observer.mesh_cli import prepared_human_view
from agent_observer.read_client import human_snapshots

async def run():
    profile = AgentProfile()
    original = await seed(2, 250)
    host = original['mesh']['hosts'][0]
    native = profile.restore_native(host['owner'], [r for r in original['sessions'] if r['identity']['hostScope']==host['hostId']])
    snapshot = native['snapshot']
    wire = (canonical(native)+'\n').encode()
    frames = publications(original, 4, 'native')
    def snapshot_case():
        for _ in range(20):
            validate_snapshot(snapshot)
        return len(snapshot['sessions'])
    def wire_case():
        for _ in range(20):
            guard = StreamGuard(expected_host=host['hostId'])
            if hasattr(guard, 'parse'):
                guard.parse(wire)
            else:
                guard.accept(parse_frame(wire))
        return len(wire)
    def consumer_case():
        guard = PreparedAgentWatch(REQUEST)
        digest = hashlib.sha256()
        try:
            for frame in frames:
                guard.accept(frame)
                for _ in range(3):
                    read = guard.read(original['mesh']['reader']['encodedAtMs'], original['mesh']['reader']['clock'])
                    qualification, snapshots = prepared_human_view(read, now_ms=original['mesh']['reader']['encodedAtMs'])
                    display = qualification+'\n'+human_snapshots(snapshots, now_ms=1700000030000)
                    digest.update(display.encode())
        finally:
            guard.disconnect()
        return digest.hexdigest()
    report = {}
    for name, function in (('snapshot',snapshot_case),('wire',wire_case),('consumer',consumer_case)):
        expected = function()
        start = time.process_time_ns()
        actual = function()
        elapsed = time.process_time_ns()-start
        if actual != expected:
            raise ValueError('benchmark_oracle')
        report[name] = {'cpuNs': elapsed, 'oracle': actual}
    import agent_observer
    report['ownerRoot'] = str(Path(agent_observer.__file__).parent)
    report['kind'] = 'synthetic CPU; unchanged SDK; no provider or network delivery'
    report['limits'] = ['fixture construction and warm-up excluded',
                        'wire case compares the old double admission with the candidate guard parser',
                        'consumer includes four native replacements and three human renders each',
                        'CPU timing is not an installed artifact, native completeness or rollout gate']
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
asyncio.run(run())
