import os,sys,json,time,subprocess,stat,hashlib,runpy,shutil
from pathlib import Path
home=Path.home();root=home/'.cache/agent-observer-timing-20261013'; source=root/'render-source'; managed=home/'.local/share/chezmoi';host=sys.argv[1]
assert host in ('snap','starship')
helpers=root/'source/scripts'
ops=runpy.run_path(str(helpers/'agent-observer-operations'))
bridge=runpy.run_path(str(helpers/'mesh-selection-acceptance'))
node=ops['node']; owned=ops['owned_unit'];rendered=ops['rendered'];owned.__globals__['ROOT']=managed
baseline=root/'paired-baseline.json'
UNITS=('mesh-plus-agent.service','agent-observer.service')
def run(argv,timeout=60):
    p=subprocess.run(argv,capture_output=True,timeout=timeout,cwd='/tmp')
    if p.returncode:
        print('rejected',Path(argv[0]).name,p.stdout.decode()[-1000:],p.stderr.decode()[-1000:],flush=True)
        raise RuntimeError('command_failed_'+Path(argv[0]).name)
    return p.stdout

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def protected():
    sock=Path('/run/user/1000/tmux-observer/owner.sock')
    import socket,struct
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(str(sock));pid,uid,_=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    assert uid==os.getuid()
    ticks=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    return {'tmuxOwner':{'pid':pid,'startTicks':ticks},'tmuxSelectionSha256':digest(managed/'deployments/tmux-observer.json'),'writerLink':os.readlink(home/'.local/bin/agent-observer-write'),'codexConfigSha256':digest(home/'.codex/config.toml'),'claudeSettingsSha256':digest(home/'.claude/settings.json')}

def proof(obs,mesh,src,label):
    frame=None;deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        p=subprocess.run([str(home/obs['prefix']/'bin/agent-observer'),'service','status','--host-scope',host],capture_output=True,timeout=15,cwd='/tmp')
        if p.returncode==0:
            frame=json.loads(p.stdout)
            if frame.get('snapshot') and all(c['accepted'] and c['health'] in ('current','partial') for s in frame['sources'] for c in s['components']):break
        time.sleep(.3)
    else:raise RuntimeError('cache_warmup_failed')
    for name,argv in [('collector',[str(helpers/'agent-observer-operations'),'verify','--host',host,'--live','--source',str(src),'--selection',str(src/'deployments/agent-observer.json')]),('publisher',[str(helpers/'agent-observer-mesh-operations'),'--host',host,'--source',str(src),'--selection',str(src/'deployments/agent-observer-mesh.json'),'--observer-selection',str(src/'deployments/agent-observer.json')])]:
        value=json.loads(run(argv))
        assert value['status']=='accepted'
        (root/'evidence'/f'{host}-{label}-{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    read=json.loads(run([str(home/obs['readerPrefix']/'bin/agent-observer'),'mesh','assess','--scope','local','--mode','subscribe','--timeout-ms','10000']))
    assert read['ok']
    return {'stage':label,'serviceProtocol':frame['serviceProtocol'],'serviceId':frame['serviceId'],'rows':len(frame['snapshot']['sessions']),'readPublisherAccepted':True,'assessmentCleanup':read['runtime']['activeConnections']==0}

oldobs=json.loads((managed/'deployments/agent-observer.json').read_text());oldmesh=json.loads((managed/'deployments/agent-observer-mesh.json').read_text())
newobs=json.loads((source/'deployments/agent-observer.json').read_text());newmesh=json.loads((source/'deployments/agent-observer-mesh.json').read_text())
assert newobs['prefix']==newmesh['readerPrefix'] and newobs['serviceProtocol']==3
for argv in ([str(helpers/'agent-observer-operations'),'verify','--host',host,'--source',str(source),'--selection',str(source/'deployments/agent-observer.json')],[str(helpers/'agent-observer-mesh-operations'),'--host',host,'--candidate','--source',str(source),'--selection',str(source/'deployments/agent-observer-mesh.json'),'--observer-selection',str(source/'deployments/agent-observer.json')]):
    assert json.loads(run(argv))['status']=='accepted','candidate_preflight_rejected'
oldrender=rendered(home,oldobs)
newrender=rendered(home,newobs)
# Mesh-controlled targets follow their independently selected bundle.
mesh_targets={'.local/bin/mesh-plus':0o755,'.config/mesh-plus/sources.toml':0o600,'.config/systemd/user/mesh-plus-agent.service':0o644,'.config/systemd/user/default.target.wants/mesh-plus-agent.service':None}
for t,mode in mesh_targets.items():
    for src,values in ((managed,oldrender),(source,newrender)):
        data=run(['chezmoi','--source',str(src),'--refresh-externals=never','cat',str(home/t)]).decode()
        values[t]={'kind':'symlink','value':data.strip()} if mode is None else {'kind':'file','value':data,'mode':mode}
assert all(node(home/t)==v for t,v in oldrender.items()),'preexisting_target_drift'
for t in ('agent-observer.json','agent-observer-mesh.json'):
    path=managed/'deployments'/t;key=str(path.relative_to(home));oldrender[key]=node(path);newrender[key]={'kind':'file','value':(source/'deployments'/t).read_text(),'mode':oldrender[key]['mode']}
# Preserve unrelated managed changes; only the shared-launcher template is ours.
key=str((managed/'dot_local/bin/executable_mesh-plus.tmpl').relative_to(home));oldrender[key]=node(home/key);newrender[key]={'kind':'file','value':(source/'dot_local/bin/executable_mesh-plus.tmpl').read_text(),'mode':oldrender[key]['mode']}
assert not baseline.exists(),'baseline_already_exists'
before=protected();initial=proof(oldobs,oldmesh,managed,'baseline')
owned.__globals__['ROOT']=managed
old_unit=owned(oldobs,home,rendered(home,oldobs));old_bridge=bridge['bridge_identity'](oldmesh,home)
baseline.write_text(json.dumps({'host':host,'original':oldrender,'candidate':newrender,'protected':before,'oldObserver':oldobs,'oldMesh':oldmesh},indent=2)+'\n');baseline.chmod(0o600)

def identity(obs,mesh):
    info=owned(obs,home,rendered(home,obs));b=bridge['bridge_identity'](mesh,home)
    return (info,b)

def replace(t,wanted):
    p=home/t;p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name(p.name+'.observer-timing-owned')
    assert not temp.exists() and not temp.is_symlink(),'owned_temp_collision'
    if wanted['kind']=='symlink':temp.symlink_to(wanted['value'])
    else:temp.write_text(wanted['value']);temp.chmod(wanted['mode'])
    temp.replace(p)

def switch(expected,wanted,obs,mesh):
    assert all(node(home/t)==v for t,v in expected.items()),'target_changed'
    identity(obs,mesh)
    for unit in UNITS:run(['systemctl','--user','stop',unit])
    assert all(node(home/t)==v for t,v in expected.items()),'target_changed_after_stop'
    try:
        for t,v in wanted.items():replace(t,v)
        run(['systemctl','--user','daemon-reload'])
        for unit in reversed(UNITS):run(['systemctl','--user','reset-failed',unit]);run(['systemctl','--user','start',unit])
        assert all(node(home/t)==v for t,v in wanted.items())
        assert protected()==before,'protected_context_changed'
    except BaseException:
        # Restore only bytes still belonging to this captured transition.
        assert all(node(home/t) in (expected[t],wanted[t]) for t in expected),'foreign_target_during_recovery'
        for unit in UNITS:
            pid=int(run(['systemctl','--user','show',unit,'-p','MainPID','--value']))
            if pid:
                process=Path(f'/proc/{pid}');argv=process.joinpath('cmdline').read_bytes().split(b'\\0')
                assert process.stat().st_uid==os.getuid()
                allowed=[str(home/v['prefix']/'bin/agent-observer-service').encode() for v in (oldobs,newobs)] if unit=='agent-observer.service' else [str(home/v['readerPrefix']/'bin/mesh-plus').encode() for v in (oldmesh,newmesh)]
                assert argv[1] in allowed,'foreign_unit_during_recovery'
                run(['systemctl','--user','stop',unit])
        for t,v in expected.items():replace(t,v)
        run(['systemctl','--user','daemon-reload'])
        for unit in reversed(UNITS):run(['systemctl','--user','reset-failed',unit]);run(['systemctl','--user','start',unit])
        raise

stages=[initial]
current='old'
try:
    switch(oldrender,newrender,oldobs,oldmesh);current='new'
    stages.append(proof(newobs,newmesh,source,'candidate'))
    switch(newrender,oldrender,newobs,newmesh);current='old'
    stages.append(proof(oldobs,oldmesh,managed,'rollback'))
    switch(oldrender,newrender,oldobs,oldmesh);current='new'
    stages.append(proof(newobs,newmesh,source,'reselected'))
    receipt={'status':'passed','host':host,'stages':stages,'selectedTargets':len(newrender),'protectedBefore':before,'protectedAfter':protected(),'ordinaryProviderActions':0,'writerUnchanged':True,'tmuxOwnerAndSelectionUnchanged':True,'finalSelection':'0.6.0a2/mesh0.1.0a16','harnessSha256':digest(Path(__file__))}
    (root/'evidence'/f'{host}-paired-selection.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
except BaseException:
    if current=='new' and all(node(home/t)==v for t,v in newrender.items()):
        switch(newrender,oldrender,newobs,newmesh);proof(oldobs,oldmesh,managed,'failure-restored')
    raise
