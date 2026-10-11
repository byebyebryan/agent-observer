import asyncio,json,sys,time,copy
from pathlib import Path
from mesh_plus.api import configured_reader,ReadGuard,current_sessions,reconstructed
from mesh_plus.evidence import clock_domain
from mesh_plus.transport import boottime_ms
from agent_observer.mesh_profile import AgentProfile
from agent_observer.service_public import validate_frame
async def main():
 host,output=sys.argv[1:];profile=AgentProfile();reader=await configured_reader('agent',source='agent',socket=Path('/run/user/1000/mesh-plus-agent/read.sock'),scope='fleet',profile=profile)
 rid='a'*32;guard=ReadGuard('agent',rid,profile=profile);stream=reader.watch(request_id=rid,proof_interval=1)
 frames=[];started=time.monotonic();ready=0
 try:
  while time.monotonic()-started<18:
   frame=await asyncio.wait_for(anext(stream),6);guard.accept(frame)
   if frame['mesh']['kind'] not in {'gap','error'}:
    unchanged=copy.deepcopy(frame);rows=guard.current(boottime_ms(),clock_domain())
    hosts=[]
    for h in frame['mesh']['hosts']:
     hosts.append({'host':h['hostId'],'path':h['delivery']['path'],'delivery':h['delivery']['status'],'proof':h['delivery']['proof'] is not None,'sourceComponents':len(h['receipts']),'originalAccepted':[r['accepted'] for r in h['receipts']]})
     if h['owner'] is not None: validate_frame(reconstructed(frame,h,profile=profile),expected_host=h['hostId'])
    assert frame==unchanged
    frames.append({'kind':frame['mesh']['kind'],'status':frame['mesh']['status'],'effectiveRows':len(rows),'hosts':hosts})
    if frame['mesh']['status']=='complete': ready+=1
   else: frames.append({'kind':frame['mesh']['kind']})
  assert ready>=2
 finally:
  await stream.aclose();guard.disconnect()
 assert guard.current(boottime_ms(),clock_domain())==[]
 assert reader.inspect()['activeConnections']==0
 result={'host':host,'durationSeconds':round(time.monotonic()-started,3),'frames':frames,'completeFrames':ready,'closed':reader.inspect(),'postDisconnectRows':0,'nonmutation':True,'providerActions':0,'rawPayloadsRetained':False}
 Path(output).write_text(json.dumps(result,indent=2)+'\n');print({'host':host,'frames':len(frames),'completeFrames':ready,'activeConnections':0})
asyncio.run(main())
