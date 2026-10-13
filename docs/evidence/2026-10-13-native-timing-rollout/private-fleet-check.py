import asyncio,json,sys,subprocess,select,time,shlex,hashlib
from pathlib import Path
root=Path('/home/bryan/.cache/agent-observer-timing-20261013');prefix=Path('/home/bryan/.local/share/agent-observer/0.6.0a2-b22d2b5795a9b3dd-mesh-a16-timing')
sys.path.insert(0,'/home/bryan/.local/share/tmux-observer/python')
from mesh_plus.api import Client,Endpoint,Reader,ReadGuard,current_sessions
from mesh_plus.transport import connect_ipc,subprocess_channel,boottime_ms
from mesh_plus.evidence import clock_domain
from agent_observer.mesh_profile import AgentProfile
from tmux_observer.mesh_profile import TmuxMeshProfile
async def run(domain,profile,source,name):
    revision='sha256:'+'7'*64
    async def catalog():return revision
    endpoints=[]
    for host in ('snap','starship'):
        codec=profile.bind(host,source)
        async def connect(host=host,codec=codec):
            if host=='snap':channel=await connect_ipc(root/'fleet'/(name+'.sock'))
            else:
                argv=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ControlMaster=no','-o','ControlPath=none','starship',shlex.join([str(root/'shared-launcher'),'bridge','--source',source,'--config',str(root/'fleet/sources.toml'),'--stdio'])]
                channel=await subprocess_channel(argv)
            return await Client.connect(channel,host=host,source=source,profile=codec.profile_id,codec=codec.validate_bridge)
        endpoints.append(Endpoint(host,host=='snap',None if host=='snap' else 'sha256:'+'6'*64,connect,codec))
    reader=Reader(domain,endpoints,local_host='snap',catalog_revision=revision,catalog_check=catalog,profile=profile)
    response=await reader.snapshot(timeout_ms=15000)
    assert response['mesh']['status']=='complete',domain+'_snapshot'
    rows=current_sessions(response,boottime_ms(),clock_domain(),profile=profile)
    guard=ReadGuard(domain,'a'*32,host_ids=['snap','starship'],profile=profile)
    stream=reader.watch(request_id='a'*32)
    try:
        async with asyncio.timeout(30):
            async for frame in stream:
                guard.accept(frame)
                if frame.get('mesh',{}).get('status')=='complete' and all(h['delivery']['status']=='ready' for h in frame['mesh']['hosts']):break
            else:raise RuntimeError('missing_watch')
        assert all(h['delivery']['proof'] is not None for h in frame['mesh']['hosts'] if not h['local'])
        current=guard.current(boottime_ms(),clock_domain())
        assert guard.current(2**52,clock_domain())==[]
        guard.disconnect();assert guard.current(boottime_ms(),clock_domain())==[]
        hosts=[{'host':h['hostId'],'proof':h['delivery']['proof'] is not None,'delivery':h['delivery']['status']} for h in frame['mesh']['hosts']]
    finally:guard.disconnect();await stream.aclose()
    assert reader.inspect()['activeConnections']==0 and reader.inspect()['cleanupFailures']==0
    return {'domain':domain,'profile':profile.descriptor.profile_id,'snapshotRows':len(rows),'watchRows':len(current),'hosts':hosts,'expiryDisconnectCleanup':'passed'}
children=[]
try:
    for host in ('snap','starship'):
        argv=[str(prefix/'bin/python'),'-I',str(root/'private-fleet-host.py'),host]
        if host=='starship':argv=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=8','starship',shlex.join(argv)]
        c=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL);children.append(c)
        assert select.select([c.stdout],[],[],45)[0],'host_setup_timeout'
        assert json.loads(c.stdout.readline())['status']=='ready'
    async def main():return [await run('agent',AgentProfile(),'agent','agent'),await run('tmux',TmuxMeshProfile(),'tmux_default','tmux')]
    result={'status':'passed','scope':'installed candidate shared launcher, two-host private Agent service and ordinary cached Tmux source','domains':asyncio.run(main()),'normalSelectionsChanged':False,'harnessSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (root/'evidence/private-fleet.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
    for c in reversed(children):
        if c.stdin:c.stdin.close()
        try:c.wait(timeout=20)
        except subprocess.TimeoutExpired:c.terminate();c.wait(timeout=5)
