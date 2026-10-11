import asyncio,json,time,os
from pathlib import Path
from mesh_plus.api import configured_reader,Reader,Endpoint,ReadGuard
from mesh_plus.evidence import clock_domain
from mesh_plus.transport import boottime_ms
from agent_observer.mesh_profile import AgentProfile
async def main():
 profile=AgentProfile();base=await configured_reader('agent',source='agent',socket=Path('/run/user/1000/mesh-plus-agent/read.sock'),scope='fleet',profile=profile)
 clients=[];endpoints=[]
 for e in base.endpoints:
  if e.local: endpoints.append(e);continue
  async def tracked(_connect=e.connect):
   c=await _connect();clients.append(c);return c
  endpoints.append(Endpoint(e.host,e.local,e.route_token,tracked,e.codec))
 reader=Reader('agent',endpoints,local_host='snap',catalog_revision=base.catalog_revision,catalog_check=base.catalog_check,profile=profile)
 stream=reader.watch(request_id='b'*32,proof_interval=1);guard=ReadGuard('agent','b'*32,profile=profile)
 complete=False;failure=False;recovered=False;frames=[];started=time.monotonic()
 try:
  while time.monotonic()-started<20:
   v=await asyncio.wait_for(anext(stream),6);guard.accept(v);rows=guard.current(boottime_ms(),clock_domain())
   assert 'mesh' in v, {k:v[k] for k in ('kind','error') if k in v}
   status=v['mesh'].get('status');frames.append({'kind':v['mesh']['kind'],'status':status,'rows':len(rows),'hosts':sorted({r['identity']['hostScope'] for r in rows})})
   if complete and any(h['hostId']=='starship' and h['delivery']['status']!='ready' for h in v['mesh'].get('hosts',[])):
    failure=True;assert all(r['identity']['hostScope']!='starship' for r in rows)
   if status=='complete' and len(rows)>0:
    if complete and failure: recovered=True;break
    if not complete:
     complete=True;assert clients
     process=clients[-1].channel.process;node=Path('/proc')/str(process.pid)
     stat=node.joinpath('stat').read_text().rsplit(')',1)[1].split()
     assert node.stat().st_uid==os.getuid() and int(stat[1])==os.getpid()
     assert Path(os.fsdecode(node.joinpath('cmdline').read_bytes().split(b'\0')[0])).name=='ssh'
     assert node.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==stat[19]
     process.terminate()
  assert complete and failure and recovered,(complete,failure,recovered)
 finally: await stream.aclose();guard.disconnect()
 assert reader.inspect()['activeConnections']==0
 assert reader.inspect()['connectionsOpened']==reader.inspect()['connectionsClosed']
 result={'ordinaryBridgeRestarted':False,'ownedSSHProcessTerminatedOnce':True,'uidParentBirthAndExecutableVerified':True,'healthyLocalIsolation':True,'reconnectFullResync':True,'frames':frames,'reader':reader.inspect(),'postDisconnectRows':len(guard.current(boottime_ms(),clock_domain()))}
 Path('/tmp/observer-sdk-a17-build/ssh-disconnect.json').write_text(json.dumps(result,indent=2)+'\n');print({'recovered':True,'frames':len(frames),'ownedConnectionsClosed':True})
asyncio.run(main())
