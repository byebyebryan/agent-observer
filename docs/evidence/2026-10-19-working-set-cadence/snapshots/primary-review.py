from pathlib import Path
import hashlib,json,math,statistics
ROOT=Path(__file__).resolve().parent
CACHE=ROOT.parent
s=json.loads((ROOT/'summary.json').read_text());m=json.loads((ROOT/'artifact-manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def same(a,b):assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8),(a,b)
assert s['status']=='pass' and len(s['cells'])==20 and s['measuredTrialCount']==80
assert sha(ROOT/'summary.json')==m['summarySha256']
assert sha(ROOT/'REPORT.md')==m['reportSha256']
for a in m['artifactFiles']:
 p=ROOT/a['path'];assert p.is_file() and sha(p)==a['sha256'] and p.stat().st_size==a['bytes'],a['path']
for path,h in m['controllerFiles'].items():assert sha(ROOT/path)==h
roots={'a7-full':CACHE/'owner-screen-59b1211/a7','candidate-working':CACHE/'final-source-b176ac06','candidate-full':CACHE/'final-source-b176ac06'}
loaded_count=0;out=[];expected_cells={(py,n,c) for py in ('py314','py311') for n in (100,500,2000) for c in (0,1,16)}|{(py,100,4) for py in ('py314','py311')}
assert {(c['pythonLabel'],c['rows'],c['readsPerGeneration']) for c in s['cells']}==expected_cells
for c in s['cells']:
 py,n,cad=c['pythonLabel'],c['rows'],c['readsPerGeneration'];rs={v:[] for v in ('a7-full','candidate-working')};sels=[]
 assert [a['variant'] for a in c['trialArtifacts']]==['a7-full','candidate-working','candidate-working','a7-full']
 for a in c['trialArtifacts']:
  p=ROOT/a['resultPath'];assert sha(p)==a['resultSha256'];r=json.loads(p.read_text());i=json.loads((ROOT/a['invocationPath']).read_text());assert sha(ROOT/a['invocationPath'])==a['invocationSha256']
  assert i['returnCode']==0 and i['status']=='pass' and i['sharedLockPath']==s['exclusiveLockPath'] and i['elapsedWallSeconds']<=180
  assert r['gcEnabled'] is False and r['variant']==a['variant'] and r['rows']==n and r['readsPerGeneration']==cad and r['measuredGenerations']==6 and r['warmupGenerations']==1 and r['measuredReads']==6*cad
  assert r['python']==s['pythonVersions'][py]['version']
  for name,h in r['loadedModules'].items():assert sha(roots[a['variant']]/h['path'])==h['sha256'],name;loaded_count+=1
  same(sum(r['generationCpuMs']),r['generationCpuTotalMs']);same(sum(r['readCpuMs']),r['readCpuTotalMs']);same(sum(r['readCpuByGenerationMs']),r['readCpuTotalMs']);same(sum(r['combinedCpuByGenerationMs']),r['combinedCpuTotalMs']);same(r['generationCpuTotalMs']+r['readCpuTotalMs'],r['combinedCpuTotalMs'])
  assert sum(r['readFrameBytesByRead'])==r['totalSerializedFrameBytes'] and sum(r['readBodyBytesByRead'])==r['totalSerializedBodyBytes'] and sum(r['selectedRowsBytesByRead'])==r['totalSelectedRowsBytes']
  assert len(r['readCpuMs'])==len(r['readFrameBytesByRead'])==6*cad
  assert r['fullRowsPerGeneration']==[n]*6
  for k in ('sourceInputDigest','seedInputDigest','generationInputDigests'):assert r[k]==c['originalSyntheticSourceSignatures'][k]
  for k in ('activeDigest','fullDigest','selectedDigest'):assert r[k]==c['matchingSnapshotDigests'][k]
  if a['variant']=='candidate-working':
   assert r['workingDigest']==r['selectedDigest'] and r['workingCoverage']=='complete'
   assert r['workingScopeMembers']==len(c['matchingSyntheticIdentity']['selectedIds']); assert r['workingScope']['memberIds']==c['matchingSyntheticIdentity']['selectedIds']; assert r['workingScope']['uncertain']==0
   assert r['activeRowsPerGeneration']==c['semanticCounts']['activeRowsPerGeneration'] and r['selectedRowsPerGeneration']==c['semanticCounts']['selectedRowsPerGeneration']
   assert all(w*4<=f for w,f in zip(r['workingBodyBytesPerGeneration'],r['fullBodyBytesPerGeneration']))
  rs[a['variant']].append(r)
 for v,rr in rs.items():
  for key,values in c['metricsByVariant'][v].items():
   totals=[r[key] for r in rr];assert totals==values['wholeTrialTotals'];same(statistics.median(totals),values['medianWholeTrialTotal'])
 a=statistics.median(r['combinedCpuTotalMs'] for r in rs['a7-full']);b=statistics.median(r['combinedCpuTotalMs'] for r in rs['candidate-working']);cpu=(a-b)/a*100;same(cpu,c['combinedCpuReductionPercent'])
 ab=statistics.median(r['totalSerializedFrameBytes'] for r in rs['a7-full']);bb=statistics.median(r['totalSerializedFrameBytes'] for r in rs['candidate-working']);br=(ab-bb)/ab*100 if ab else None
 if ab:same(br,c['serializedFrameByteReductionPercent'])
 else:assert c['serializedFrameByteReductionPercent'] is None
 out.append({'python':py,'rows':n,'cadence':cad,'fullCpuWholeSixGenMedianMs':a,'workingCpuWholeSixGenMedianMs':b,'cpuReductionPercent':cpu,'serializedFullFrameBytes':ab,'serializedWorkingFrameBytes':bb,'serializedFrameByteReductionPercent':br})
for a in s['rawResults']:assert sha(ROOT/a['path'])==a['sha256']
r={'schema':'agent-observer.working-set-cadence-primary-review.v1','status':'pass','summarySha256':sha(ROOT/'summary.json'),'artifactManifestSha256':sha(ROOT/'artifact-manifest.json'),'manifestFilesVerified':len(m['artifactFiles']),'rawResultHashesVerified':len(s['rawResults']),'measuredTrials':80,'cells':out,'loadedModuleHashesVerified':loaded_count,'scope':'independent arithmetic and exact-byte replay of saved SOURCE-only synthetic reports; no timing rerun, SDK/network/native collection/RSS or whole-producer acceptance','firstFailurePreserved':'inherited RLIMIT_FSIZE stopped wrapper after helper wrote valid JSON; corrected named V2 retry retained'}
(ROOT/'primary-review.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='cells'},indent=2));print('rangeByCadence', {c:[min(x['cpuReductionPercent'] for x in out if x['cadence']==c),max(x['cpuReductionPercent'] for x in out if x['cadence']==c)] for c in (0,1,4,16)})
