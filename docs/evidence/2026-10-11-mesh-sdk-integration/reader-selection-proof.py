import json,hashlib,os,sys,subprocess,importlib.machinery,importlib.util
from pathlib import Path
host,root=sys.argv[1:];root=Path(root);home=Path.home();source=home/'.local/share/chezmoi';baseline=json.loads((root/'baseline.json').read_text());candidate=json.loads((root/'selection.json').read_text());observer=json.loads((root/'observer-selection.json').read_text())
def run(argv):
 p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=90)
 assert p.returncode==0,{'command':Path(str(argv[0])).name,'exitCode':p.returncode,'reason':p.stdout[-300:] if not p.stderr else p.stderr[-300:]}
 return p.stdout
def record(p):
 if p.is_symlink(): return {'kind':'symlink','value':os.readlink(p),'uid':p.lstat().st_uid}
 if p.exists(): return {'kind':'file','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&511,'uid':p.stat().st_uid}
 return {'kind':'absent'}
def unit(name):
 pid=int(run(['systemctl','--user','show',name,'-p','MainPID','--value']));p=Path('/proc')/str(pid)
 assert pid>0 and p.stat().st_uid==os.getuid()
 return {'pid':pid,'startTicks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]}
loader=importlib.machinery.SourceFileLoader('selected_bridge_guard',str(root/'mesh-selection-acceptance'));spec=importlib.util.spec_from_loader(loader.name,loader);guard=importlib.util.module_from_spec(spec);loader.exec_module(guard)
def protected():
 for path,value in baseline['protected'].items(): assert record(home/path)==value,('protected',path)
 for path,value in baseline['targets'].items():
  if path!='.local/bin/agent-observer': assert record(home/path)==value,('target',path)
 for path,value in baseline['unrelatedSource'].items(): assert record(source/path)==value,('unrelated',path)
 for name,value in baseline['units'].items(): assert unit(name)==value,('unit',name)
 guard.same_bridge(candidate,home,baseline['units']['mesh-plus-agent.service'])
def operations(is_candidate=False):
 argv=[root/'agent-observer-mesh-operations','--host',host,'--source',source,'--selection',source/'deployments/agent-observer-mesh.json','--observer-selection',source/'deployments/agent-observer.json']
 if is_candidate: argv+=['--candidate']
 return json.loads(run(argv))
def read(label):
 v=json.loads(run([home/'.local/bin/agent-observer','mesh','snapshot','--scope','fleet']))
 assert v['mesh']['status']=='complete' and {h['hostId'] for h in v['mesh']['hosts']}=={'snap','starship'}
 return {'label':label,'version':run([home/'.local/bin/agent-observer','--version']).strip(),'rawRows':len(v['sessions']),'hosts':len(v['mesh']['hosts']),'status':v['mesh']['status']}
protected()
for name,value in (('agent-observer.json',observer),('agent-observer-mesh.json',candidate)):
 path=source/'deployments'/name;assert json.loads(path.read_text())==baseline['sourceSelections'][name],('source_drift',name)
 path.write_text(json.dumps(value,indent=2)+'\n')
# Candidate rendering must change only the reader target; actual selection remains prior.
operations(True)
entry=home/'.local/bin/agent-observer';desired=str(home/candidate['readerPrefix']/'bin/agent-observer')
for path,value in baseline['targets'].items():
 rendered=run(['chezmoi','--source',source,'--refresh-externals=never','cat',home/path])
 if path=='.local/bin/agent-observer': assert rendered.strip()==desired
 elif value['kind']=='symlink': assert rendered.strip()==value['value']
 else: assert hashlib.sha256(rendered.encode()).hexdigest()==value['sha256']
dry=run(['chezmoi','--source',source,'--refresh-externals=never','apply','--dry-run','--verbose','--force','--exclude=scripts,externals',entry])
(root/'reader-dry-run.txt').write_text(dry)
assert record(entry)==baseline['targets']['.local/bin/agent-observer'];protected()
run(['chezmoi','--source',source,'--refresh-externals=never','apply','--force','--exclude=scripts,externals',entry])
assert os.readlink(entry)==desired;protected();selected=operations();reads=[read('selected')]
prior=baseline['targets']['.local/bin/agent-observer']['value']
assert baseline['targets']['.local/bin/agent-observer']['uid']==os.getuid()
# Roll back one captured link; production source remains at the reviewed candidate.
assert entry.lstat().st_uid==os.getuid() and entry.parent.stat().st_uid==os.getuid()
protected();assert os.readlink(entry)==desired
try:
 temp=entry.with_name('.agent-observer-sdk-rollback');assert not (temp.exists() or temp.is_symlink());temp.symlink_to(prior);os.replace(temp,entry)
 assert record(entry)==baseline['targets']['.local/bin/agent-observer'];protected();reads.append(read('rollback'))
finally:
 assert os.readlink(entry) in (prior,desired);protected()
 run(['chezmoi','--source',source,'--refresh-externals=never','apply','--force','--exclude=scripts,externals',entry])
assert os.readlink(entry)==desired;protected();final=operations();reads.append(read('reselected'))
assert selected['liveBridge']==final['liveBridge']
for name,value in (('agent-observer.json',observer),('agent-observer-mesh.json',candidate)): assert json.loads((source/'deployments'/name).read_text())==value
result={'host':host,'readerSelection':candidate['readerPrefix'],'bridgeSelection':candidate['bridgeSelection']['readerPrefix'],'readerOnlyTargetChanged':True,'reads':reads,'collectorAndBridgeIncarnationsUnchanged':baseline['units'],'protectedControlsUnchanged':True,'protectedProviderSettingsUnchanged':True,'unrelatedSourceUnchanged':sorted(baseline['unrelatedSource']),'sharedMeshCliUnchanged':True,'providerActions':0,'rollbackOnlyReaderLink':True,'reselected':True,'operationsStatus':final['status']}
(root/'selection-acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
