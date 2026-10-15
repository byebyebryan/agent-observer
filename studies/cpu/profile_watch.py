"""Bounded passive owner/reader CPU attribution; retain metadata and counts only."""

import argparse
import asyncio
import collections
import cProfile
import importlib.metadata
import json
import pstats
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--scope', choices=('local', 'fleet'), default='fleet')
parser.add_argument('--workload', choices=('reader', 'publisher'), default='reader')
parser.add_argument('--host-scope')
parser.add_argument('--local-host')
parser.add_argument('--socket', type=Path)
parser.add_argument('--seconds', type=int, default=45)
parser.add_argument('--profile', action='store_true')
parser.add_argument('--spans', action='store_true')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--owner-root', type=Path)
args = parser.parse_args()
if not 1 <= args.seconds <= 300:
    parser.error('--seconds must be 1..300')
if args.workload == 'publisher' and not args.host_scope:
    parser.error('--host-scope is required for publisher observation')
if args.spans and args.profile:
    parser.error('run lightweight spans and cProfile separately')

if args.owner_root:
    import sys
    sys.path.insert(0, str(args.owner_root.resolve()))

from agent_observer import mesh_cli
from agent_observer.mesh_read import PreparedAgentWatch

counts = collections.Counter()
shapes = set()
revisions = {}
span_stats = {}
stack = []
if args.spans:
    import sys
    from agent_observer import contract, service_contract, read_client, mesh_profile, mesh_read
    from mesh_plus import view, prepared, reader
    def span(label, function):
        def wrapped(*a, **kw):
            started = time.thread_time_ns()
            entry = [label, 0]
            stack.append(entry)
            try:
                return function(*a, **kw)
            finally:
                elapsed = time.thread_time_ns() - started
                stack.pop()
                row = span_stats.setdefault(label, {'calls': 0, 'cpuNs': 0, 'exclusiveCpuNs': 0})
                row['calls'] += 1
                row['cpuNs'] += elapsed
                row['exclusiveCpuNs'] += elapsed - entry[1]
                if stack:
                    stack[-1][1] += elapsed
        return wrapped
    for module, name in ((contract, 'validate_snapshot'), (service_contract, 'validate_frame'),
                         (read_client, 'ordered_snapshots'), (view, '_validated_response')):
        original = getattr(module, name)
        wrapped = span(module.__name__ + '.' + name, original)
        for imported in tuple(sys.modules.values()):
            if imported is not None and getattr(imported, '__name__', '').startswith(('agent_observer', 'mesh_plus')):
                for key, value in tuple(vars(imported).items()):
                    if value is original:
                        setattr(imported, key, wrapped)
    for cls, name in ((mesh_profile.AgentCodec, 'inspect_native'), (mesh_profile.AgentCodec, 'validate_bridge'),
                      (mesh_read.PreparedAgentWatch, 'accept'), (mesh_read.PreparedAgentWatch, 'read'),
                      (prepared.PreparedReadGuard, '_prepare'), (reader.Reader, 'compose')):
        setattr(cls, name, span(cls.__name__ + '.' + name, getattr(cls, name)))
original_accept = PreparedAgentWatch.accept
def accept(self, frame):
    counts['frame:' + frame.get('mesh', {}).get('kind', 'base_error')] += 1
    if 'sessions' in frame:
        shapes.add(len(frame['sessions']))
    for host in frame.get('mesh', {}).get('hosts', []):
        counts['delivery:' + host['hostId'] + ':' + host['delivery']['status'] + ':' + str(host['delivery']['error'])] += 1
        if host['owner'] is not None:
            service = host['owner']['service']
            revision = (service['serviceId'], service['viewRevision'])
            if host['hostId'] in revisions:
                counts['native:' + host['hostId'] + (':same' if revisions[host['hostId']] == revision else ':changed')] += 1
            revisions[host['hostId']] = revision
    return original_accept(self, frame)
PreparedAgentWatch.accept = accept

def discard_human(value):
    counts['humanRenders'] += 1

async def run():
    if args.workload == 'publisher':
        import os, secrets
        from agent_observer.mesh_publisher import make_publisher
        publisher = make_publisher(args.host_scope, 'agent', Path(f'/run/user/{os.getuid()}/agent-observer/read.sock'))
        async def watch():
            stream = publisher.watch()
            try:
                async for frame in stream:
                    counts['publisher:watch'] += 1
            finally:
                await stream.aclose()
        async def proof():
            while True:
                await publisher.proof({'nonce': secrets.token_hex(16)})
                counts['publisher:proof'] += 1
                await asyncio.sleep(5)
        try:
            async with asyncio.timeout(args.seconds):
                async with asyncio.TaskGroup() as group:
                    group.create_task(watch())
                    group.create_task(proof())
        except TimeoutError:
            pass
        if publisher.native._active:
            raise ValueError('source_cleanup')
        return
    argv = ['watch', '--human', '--prepared', '--scope', args.scope]
    if args.local_host:
        argv += ['--local-host', args.local_host]
    if args.socket:
        argv += ['--socket', str(args.socket)]
    cli_args = mesh_cli.parser().parse_args(argv)
    async with asyncio.timeout(args.seconds):
        try:
            await mesh_cli.run(cli_args, human_output=discard_human)
        except asyncio.CancelledError:
            raise

profiler = cProfile.Profile()
cpu, wall = time.process_time(), time.monotonic()
if args.profile:
    profiler.enable()
try:
    asyncio.run(run())
except (TimeoutError, KeyboardInterrupt):
    pass
finally:
    if args.profile:
        profiler.disable()
import agent_observer, hashlib
owner = Path(agent_observer.__file__).parent
result = {'workload': args.workload, 'scope': args.scope, 'profiled': args.profile, 'seconds': time.monotonic()-wall,
          'cpuSeconds': time.process_time()-cpu, 'counts': dict(counts), 'rowCounts': sorted(shapes),
          'packages': {p: importlib.metadata.version(p) for p in ('agent-observer','mesh-plus','jsonschema')}}
result['ownerRoot'] = str(owner)
result['ownerDigests'] = {name: hashlib.sha256((owner/name).read_bytes()).hexdigest() for name in ('contract.py','service_contract.py','service_client.py','mesh_source.py')}
result['spans'] = span_stats
result['limits'] = [
    'ordinary active sources; not a controlled timing comparison',
    'process CPU only; remote publisher, collector, SSH child/server CPU excluded',
    'publisher workload owns one watch and a cached proof read every five seconds; not full Bridge/carrier',
    'cProfile overhead can change cadence and cause timeout/resync; use only for call-path diagnosis',
    'spans are synchronous thread CPU; nested inclusive values must not be summed',
    'source overrides are identified by file digests; distribution metadata may describe another checkout',
]
if args.profile:
    stats = pstats.Stats(profiler)
    def row(key, value):
        cc, nc, tt, ct, callers = value
        return {'file': key[0], 'line': key[1], 'function': key[2], 'calls': nc, 'selfSeconds': tt, 'cumulativeSeconds': ct}
    result['self'] = [row(k,v) for k,v in sorted(stats.stats.items(), key=lambda kv: kv[1][2], reverse=True)[:45]]
    result['cumulative'] = [row(k,v) for k,v in sorted(stats.stats.items(), key=lambda kv: kv[1][3], reverse=True)[:65]]
    result['validation'] = [row(k,v) for k,v in stats.stats.items() if k[2] in ('validate_frame','validate_snapshot','validate_response','_validated_response','validate_bridge','inspect_native','validate','compose','accept','read_host','_prepare')]
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('self','cumulative','validation')}))
