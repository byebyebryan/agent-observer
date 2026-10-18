"""Matched pure owner acceptance: no provider/socket/transport/read timing."""
import argparse
import copy
import gc
import hashlib
import json
import sys
import time
from pathlib import Path
from uuid import UUID

parser = argparse.ArgumentParser()
parser.add_argument('root', type=Path)
parser.add_argument('seed', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--rows', type=int, required=True)
parser.add_argument('--variant', choices=('a7','candidate','current-disabled'), required=True)
args = parser.parse_args()
root = args.root.resolve()
sys.path.insert(0, str(root))
from agent_observer.contract import canonical
from agent_observer.service_state import ServiceState

seed = json.loads(args.seed.read_bytes())
seed['sources'][0]['capabilities']['runtime'] = ['running','parked']
seed['sources'][0]['capabilities']['activity'] = True
row_template = seed['sessions'][0]
seed['sessions'] = []
wall = 1700000020000
small = max(1, args.rows // 200)
expected, running = set(), set()
for i in range(args.rows):
    row = copy.deepcopy(row_template)
    nid = str(UUID(int=1000+i))
    row['identity']['nativeId'] = nid
    row['nativeIds'].update(threadId=nid,sessionTreeRootId=nid)
    row['kind'] = 'unknown'
    if i < small:
        running.add(nid)
        row['runtime']['value'] = 'running'
    else:
        row['runtime']['value'] = 'parked'
        row['phase'],row['blockedReasons'] = None,[]
    if i < 2 * small:
        expected.add(nid)
    row['activity'].update(at=wall-(3600000 if small <= i < 2*small else 864000000),
                            health='current',source='codex_rpc',reason='native_timestamp')
    seed['sessions'].append(row)
workload_digest = hashlib.sha256(canonical(seed).encode()).hexdigest()
now=[10001]
options = {'working_set_window_ms':259200000} if args.variant=='candidate' else {}
state = ServiceState(host_scope='fixture',configs={'codex':('/fixture/codex','explicit')},
                     uid=seed['host']['uid'],clock=lambda:now[0],
                     boot_id='00000000-0000-4000-8000-000000000001',clock_domain='time:[123]',**options)
gc.disable()
# One warmup is excluded. Newer native collection IDs make each generation a
# real accepted input; parent parsing/native collection remain outside scope.
component_ms=[]
for generation in range(7):
    now[0]=10001+generation
    seed['collectionId']=str(UUID(int=100+generation))
    seed['collectedAt']=wall+generation
    extras={'accepted_boottime_ms':now[0]} if args.variant=='candidate' else {}
    start=time.process_time_ns()
    state.attempt('codex','runtime')
    accepted=state.accept('codex','runtime',seed,sampled_ms=10000+generation,ttl_ms=100000,**extras)
    elapsed=(time.process_time_ns()-start)/1e6
    assert accepted is True
    if generation:component_ms.append(elapsed)
rows=state.snapshot['sessions']
assert len(rows)==args.rows
active=state.active_projector.snapshot()['sessions']
assert {r['identity']['nativeId'] for r in active}==running
selected=[r for r in rows if r['identity']['nativeId'] in expected]
checks={'fullRows':len(rows),'activeRows':len(active),'selectedRows':len(selected),
        'fullDigest':hashlib.sha256(canonical(rows).encode()).hexdigest(),
        'activeDigest':hashlib.sha256(canonical(active).encode()).hexdigest(),
        'selectedDigest':hashlib.sha256(canonical(selected).encode()).hexdigest()}
if args.variant=='candidate':
    p=state.working_set_projector.snapshot()
    assert {r['identity']['nativeId'] for r in p['sessions']}==expected
    assert p['sessions']==selected
    assert p['scopes'][0]['coverage']['status']=='complete'
    checks.update(workingBodies=len(p['sessions']),workingCoverage='complete',guardBytes=state.working_set_projector.decisions.guard_bytes)
loaded={}
for name,module in tuple(sys.modules.items()):
    filename=getattr(module,'__file__',None)
    if filename:
        path=Path(filename).resolve()
        if path.is_relative_to(root) and path.suffix=='.py':
            loaded[name]={'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
args.output.write_text(json.dumps({'python':sys.version.split()[0],'variant':args.variant,'rows':args.rows,
                                  'generationCpuMs':component_ms,'totalSixGenerationCpuMs':sum(component_ms),
                                  'gcEnabled':gc.isenabled(),'fixtureDigest':workload_digest,'checks':checks,
                                  'loaded':loaded,'scope':'immutable accepted-a7 vs candidate pure ServiceState attempt/accept including retained full/active and new working owner; excludes constructor/warmup/native collection/parent parse/reads/proof/transport/RSS; component evidence only'},indent=2,sort_keys=True)+'\n')
