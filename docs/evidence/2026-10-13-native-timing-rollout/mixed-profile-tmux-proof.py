import sys,asyncio,json,subprocess
from pathlib import Path
sys.path.insert(0,'/home/bryan/.local/share/tmux-observer/python')
from mesh_plus.api import Client,Endpoint,Reader,ReadGuard,current_sessions
from mesh_plus.transport import connect_ssh,subprocess_channel,boottime_ms
from mesh_plus.evidence import clock_domain
from tmux_observer.mesh_profile import TmuxMeshProfile
root=Path('/home/bryan/.cache/agent-observer-timing-20261013')
old=Path('/home/bryan/.local/share/agent-observer/0.5.0a20-8241cafc13dbfdfe-mesh-a15-publisher/bin/agent-observer')
p=subprocess.run([str(old),'mesh','assess','--scope','local','--mode','snapshot','--timeout-ms','10000'],capture_output=True,timeout=20,cwd='/tmp')
rejected=json.loads(p.stdout);assert not rejected['ok'],'old_profile_admitted_new_endpoint'
async def run():
 profile=TmuxMeshProfile();revision='sha256:'+'5'*64
 async def catalog():return revision
 endpoints=[]
 for host in ('snap','starship'):
  codec=profile.bind(host,'tmux_default')
  async def connect(host=host,codec=codec):
   channel=await subprocess_channel(['/home/bryan/.local/bin/mesh-plus','bridge','--source','tmux_default','--stdio']) if host=='snap' else await connect_ssh('starship','tmux_default',timeout_seconds=8)
   return await Client.connect(channel,host=host,source='tmux_default',profile=codec.profile_id,codec=codec.validate_bridge)
  endpoints.append(Endpoint(host,host=='snap',None if host=='snap' else 'sha256:'+'4'*64,connect,codec))
 reader=Reader('tmux',endpoints,local_host='snap',catalog_revision=revision,catalog_check=catalog,profile=profile)
 frame=await reader.snapshot(timeout_ms=15000);assert frame['mesh']['status']=='complete'
 rows=current_sessions(frame,boottime_ms(),clock_domain(),profile=profile)
 guard=ReadGuard('tmux','a'*32,host_ids=['snap','starship'],profile=profile);stream=reader.watch(request_id='a'*32)
 try:
  async with asyncio.timeout(30):
   async for f in stream:
    guard.accept(f)
    if f.get('mesh',{}).get('status')=='complete':break
   else:raise RuntimeError('missing_push')
  current=guard.current(boottime_ms(),clock_domain());assert guard.current(2**52,clock_domain())==[]
  guard.disconnect();assert guard.current(boottime_ms(),clock_domain())==[]
  proof=all(h['delivery']['proof'] is not None for h in f['mesh']['hosts'] if not h['local']);assert proof
 finally:guard.disconnect();await stream.aclose()
 assert not reader.inspect()['activeConnections'] and not reader.inspect()['cleanupFailures']
 return {'snapshotRows':len(rows),'pushRows':len(current),'remoteProof':proof,'expiryDisconnectCleanup':'passed'}
result={'status':'passed','oldAgentProfileRejected':True,'oldAgentAssessment':rejected,'tmuxAfterAgentFailure':asyncio.run(run()),'scope':'normal shared launcher and ordinary cached Tmux source; manual fixed two-host endpoint scope','providerActions':0,'selectionChanges':0}
(root/'evidence/mixed-profile-tmux.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'passed','oldAgentProfileRejected':True,'tmux':result['tmuxAfterAgentFailure']}))
