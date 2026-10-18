"""Synthetic owner-only early diagnostic; excludes collection/read/transport."""

import argparse
import copy
import gc
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from uuid import UUID

ROOT = Path(sys.argv[1]).resolve()
del sys.argv[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_service_runtime import scoped_snapshot
from agent_observer.contract import canonical
from agent_observer.service_state import ServiceState

parser = argparse.ArgumentParser()
parser.add_argument('--rows', type=int, required=True)
parser.add_argument('--enabled', type=int, choices=(0, 1), required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
count = args.rows
seed = scoped_snapshot()
seed['sources'][0]['capabilities']['runtime'] = ['running', 'parked']
seed['sources'][0]['capabilities']['activity'] = True
template = seed['sessions'][0]
seed['sessions'] = []
selected = max(1, count // 200)
wall = 1700000020000
for number in range(count):
    row = copy.deepcopy(template)
    identity = str(UUID(int=1000 + number))
    row['identity']['nativeId'] = identity
    row['nativeIds'].update(threadId=identity, sessionTreeRootId=identity)
    row['kind'] = 'unknown'
    running = number < selected
    row['runtime']['value'] = 'running' if running else 'parked'
    if not running:
        row['phase'], row['blockedReasons'] = None, []
    row['activity'].update(at=wall - (3600000 if selected <= number < 2 * selected else 864000000),
                           health='current', source='codex_rpc', reason='native_timestamp')
    seed['sessions'].append(row)
now = [10001]
gc.disable()
durations, outcomes = [], []
for trial in range(3):
    now[0] = 10001
    state = ServiceState(host_scope='fixture', uid=seed['host']['uid'],
                         configs={'codex': ('/fixture/codex', 'explicit')}, clock=lambda: now[0],
                         working_set_window_ms=259200000 if args.enabled else None)
    start = time.process_time_ns()
    for generation in range(6):
        now[0] = 10001 + generation
        seed['collectedAt'] = wall + generation
        seed['collectionId'] = str(UUID(int=100 + generation))
        state.attempt('codex', 'runtime')
        state.accept('codex', 'runtime', seed, sampled_ms=10000 + generation, ttl_ms=100000,
                     accepted_boottime_ms=now[0])
    durations.append((time.process_time_ns() - start) / 1e6)
    if args.enabled:
        projection = state.working_set_projector.snapshot()
        outcomes.append({'bodies': len(projection['sessions']), 'expected': selected * 2,
                         'coverage': projection['scopes'][0]['coverage']['status'],
                         'reason': projection['scopes'][0]['coverage']['reason'],
                         'guardBytes': state.working_set_projector.decisions.guard_bytes,
                         'bodyDigest': hashlib.sha256(canonical(projection).encode()).hexdigest()})
    del state
loaded = {}
for name, module in tuple(sys.modules.items()):
    path = getattr(module, '__file__', None)
    if path and Path(path).is_relative_to(ROOT) and Path(path).suffix == '.py':
        p = Path(path)
        loaded[name] = {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
args.output.write_text(json.dumps({'rows': count, 'enabled': bool(args.enabled),
                                  'python': sys.version.split()[0], 'gcEnabled': gc.isenabled(),
                                  'sixGenerationCpuMs': durations, 'medianMs': statistics.median(durations),
                                  'outcomes': outcomes, 'loaded': loaded,
                                  'scope': 'early synthetic owner-only; excludes native collection, reads, proof, transport, startup and RSS; not producer/cost acceptance'},
                                 indent=2, sort_keys=True) + '\n')
