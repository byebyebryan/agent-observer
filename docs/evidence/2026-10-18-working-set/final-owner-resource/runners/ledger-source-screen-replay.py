from __future__ import annotations
import argparse, copy, gc, hashlib, importlib.util, json, os, sys
gc.disable()
from pathlib import Path
from uuid import UUID

parser = argparse.ArgumentParser(description='Replay one bounded final-source ledger case.')
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--seed', type=Path, required=True)
parser.add_argument('--helper', type=Path, required=True)
parser.add_argument('--count', type=int, choices=(100, 200, 400), required=True)
args = parser.parse_args()
ROOT = args.root.resolve()
SEED_PATH = args.seed.resolve()
HELPER = args.helper.resolve()
COUNT = args.count
WINDOW = 259_200_000
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('matched_fixture', HELPER)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from agent_observer.contract import canonical, validate_snapshot
from agent_observer.service_contract import parse_frame as parse_full
from agent_observer.service_state import ServiceState
from agent_observer.working_set_contract import parse_frame as parse_working

def graph(owner):
    sizes = {}
    def add(value):
        sizes[id(value)] = sys.getsizeof(value)
    add(owner); add(owner._charge); add(owner._entry_resize_at); add(owner._support_resize_at); add(owner.context)
    if owner.context is not None:
        for value in owner.context: add(value)
    add(owner.prefix)
    if owner.prefix is not None:
        for value in owner.prefix: add(value)
    add(owner._entries); add(owner._supports)
    for native_id, atom in owner._entries.items():
        add(native_id); add(atom); add(atom.key); add(atom.value); add(atom.charge)
        for key, value in atom.value.items(): add(key); add(value)
    for key, record in owner._supports.items():
        add(key); add(record); add(record[0]); add(record[1])
    return sizes

def trace_capture(frame, event, arg):
    def inside(current, current_event, current_arg):
        if current_event == 'line':
            loc = current.f_locals
            if 'combined' in loc and not captured:
                old, candidate = loc.get('old_ledger'), loc.get('ledger')
                if old is not None:
                    old_graph = graph(old)
                    candidate_graph = graph(candidate) if candidate is not None else {}
                    overlap = old_graph.keys() & candidate_graph.keys()
                    support_table = loc.get('support_table')
                    scope_maps = loc.get('scope', {}).get('supportTable', ())
                    builder_maps = getattr(support_table, '_table', ())
                    candidate_map_ids = {id(atom.value) for atom, _count in candidate._supports.values()} if candidate else set()
                    captured.append({
                        'observationRevision': loc.get('observation_revision'),
                        'trackingCapacity': loc.get('tracking_capacity'),
                        'combinedBytes': loc.get('combined'),
                        'trackingBytes': loc.get('tracking_bytes'),
                        'maxLedgerBytes': loc.get('self').max_ledger_bytes,
                        'guardBytes': loc.get('self').decisions.guard_bytes,
                        'supportPreflightBytes': getattr(support_table, 'preflight_charge', None),
                        'supportOverheadBytes': getattr(support_table, 'overhead_charge', None),
                        'oldLedger': {'charge': old.charge, 'count': old.count, 'supports': old.support_count,
                                      'entryDictBytes': sys.getsizeof(old._entries), 'supportDictBytes': sys.getsizeof(old._supports),
                                      'graphObjects': len(old_graph), 'graphUniqueBytes': sum(old_graph.values())},
                        'graphWithinCharge': old.charge >= sum(old_graph.values()) and (candidate is None or candidate.charge >= sum(candidate_graph.values())),
                        'candidateLedger': None if candidate is None else {
                            'charge': candidate.charge, 'count': candidate.count, 'supports': candidate.support_count,
                            'entryDictBytes': sys.getsizeof(candidate._entries), 'supportDictBytes': sys.getsizeof(candidate._supports),
                            'graphObjects': len(candidate_graph), 'graphUniqueBytes': sum(candidate_graph.values()),
                        },
                        'sharedGraphObjects': len(overlap),
                        'sharedGraphUniqueBytes': sum(old_graph[key] for key in overlap),
                        'supportTableMaps': len(scope_maps),
                        'supportTableMapsAliasedToCandidateAtoms': sum(id(value) in candidate_map_ids for value in scope_maps),
                        'supportTableMapsAliasedToOldAtoms': sum(id(value) in {id(atom.value) for atom, _count in old._supports.values()} for value in scope_maps),
                    })
                    loc['_screen_captured'] = True
        return inside
    if event == 'call' and frame.f_code.co_name == '_accept_owned' and frame.f_globals.get('__name__') == 'agent_observer.working_set_feed':
        return inside
    return None

seed_bytes = SEED_PATH.read_bytes()
seed0 = json.loads(seed_bytes)
seed, wall, small, _, _ = fixture.build_workload(copy.deepcopy(seed0), 2000, canonical)
selected = COUNT
active_count = selected // 2
recent_count = selected - active_count
template = copy.deepcopy(seed0['sessions'][0])
for index, row in enumerate(seed['sessions']):
    if index < active_count:
        row['runtime']['value'] = 'running'
        row['phase'] = copy.deepcopy(template['phase'])
        row['blockedReasons'] = copy.deepcopy(template['blockedReasons'])
    else:
        row['runtime']['value'] = 'parked'
        row['phase'], row['blockedReasons'] = None, []
    recent = active_count <= index < active_count + recent_count
    row['activity']['at'] = wall - (3_600_000 if recent else 864_000_000)
seed['collectedAt'] = wall
validate_snapshot(seed)
source_input_sha = hashlib.sha256(canonical(seed).encode()).hexdigest()
host, uid = 'fixture', seed['host']['uid']
now = [10_001]
state = ServiceState(host_scope=host, configs={'codex': ('/fixture/codex', 'explicit')}, uid=uid,
                     clock=lambda: now[0], boot_id='00000000-0000-4000-8000-000000000001',
                     clock_domain='time:[123]', working_set_window_ms=WINDOW)
gen_hashes=[]
accepted_rows=[]
for generation in range(3):
    now[0] = 10_001 + generation
    seed['collectionId'] = str(UUID(int=100 + generation))
    seed['collectedAt'] = wall + generation
    gen_hashes.append(hashlib.sha256(canonical(seed).encode()).hexdigest())
    state.attempt('codex','runtime')
    captured=[]
    sys.settrace(trace_capture)
    try:
        accepted = state.accept('codex','runtime',seed,sampled_ms=10_000+generation,ttl_ms=100_000,accepted_boottime_ms=now[0])
    finally:
        sys.settrace(None)
    if accepted is not True:
        raise AssertionError('snapshot_not_accepted')
    full_frame=state.frame('status',generation+1)
    full_wire=(canonical(full_frame)+'\n').encode()
    parsed_full=parse_full(full_wire,expected_host=host,expected_uid=uid)
    if parsed_full != full_frame:
        raise AssertionError('full_frame_roundtrip_mismatch')
    full=parsed_full['snapshot']
    independent=fixture.full_consumer_rows(full)
    work_frame=state.working_set_frame('status',generation+1)
    work_wire=(canonical(work_frame)+'\n').encode()
    parsed_work=parse_working(work_wire,expected_host=host,expected_uid=uid,expected_window_ms=WINDOW)
    projection=parsed_work['projection']
    if projection is None:
        raise AssertionError('working_projection_missing')
    scope=projection['scopes'][0]
    complete=scope['coverage']['status']=='complete'
    if complete and projection['sessions'] != independent:
        raise AssertionError('working_dto_mismatch')
    if complete and len(independent)!=selected:
        raise AssertionError('selected_count_mismatch')
    if not complete and (projection['sessions'] or scope['coverage']['reason'] != 'projection_tracking_capacity'):
        raise AssertionError('unexpected_incomplete_projection')
    accepted_rows.append({
        'generation':generation+1,'accepted':accepted,'fullRows':len(full['sessions']),
        'selectedExpectedRows':len(independent),'selectedIdsDigest':hashlib.sha256(canonical([r['identity']['nativeId'] for r in independent]).encode()).hexdigest(),
        'fullDtoDigest':hashlib.sha256(canonical(full['sessions']).encode()).hexdigest(),
        'workingDtoDigest':hashlib.sha256(canonical(projection['sessions']).encode()).hexdigest(),
        'workingCoverage':scope['coverage']['status'],'workingReason':scope['coverage']['reason'],
        'workingMemberRows':len(scope['members']),'workingUncertainRows':len(scope['uncertain']),
        'workingNonmemberRows':len(scope['nonmembers']),'workingProjectionBytes':len(canonical(projection).encode()),
        'fullFrameBytes':len(full_wire),'workingFrameBytes':len(work_wire),
        'ledger':{'charge':state.working_set_projector._ledger.charge,'count':state.working_set_projector._ledger.count,
                  'supports':state.working_set_projector._ledger.support_count},
        'budgetPhase':captured[-1] if captured else None,
    })

def filehash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
print(json.dumps({
    'python':sys.version.split()[0],'gcEnabled':gc.isenabled(),'rows':2000,'selectedRequested':COUNT,
    'activeRows':active_count,'recentOnlyRows':recent_count,'generations':accepted_rows,
    'seedSha256':hashlib.sha256(seed_bytes).hexdigest(),'inputSha256BeforeGenerationMutation':source_input_sha,
    'generationInputSha256':gen_hashes,'fixtureRunnerSha256':filehash(HELPER),
    'loadedSourceSha256':{name:filehash(ROOT/'agent_observer'/name) for name in ['working_set_feed.py','working_set_ledger.py','working_set_supports.py','working_set_decisions.py','working_set_clocks.py','service_state.py','service_contract.py','working_set_contract.py']},
    'scope':'untimed source-only three-generation synthetic owner budget/DTO screen; not heap/RSS/native/SDK qualification'
},sort_keys=True))
