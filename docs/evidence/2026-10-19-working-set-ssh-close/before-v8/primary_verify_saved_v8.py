from pathlib import Path
import hashlib,json,stat
ROOT=Path(__file__).resolve().parent
PKG=ROOT.parent/'installed-pair-b176ac06-b9e8488e'
PAY=PKG/'fixed-ssh-v8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
assert sha(ROOT/'fixed-ssh-v8-plan.json')=='f73cbc6959c30414056e9629656c5ff75e3aeb7aab88640163881d2c0d07d311'
assert sha(ROOT/'execute-working-set-fixed-ssh-v8.py')=='96c87ba3548989a065954db85ec6ad21bb9d21c70436987c436a7bf7d702a14c'
assert sha(ROOT/'run-working-set-fixed-ssh-v8-reader.py')=='5b58c58edeb09418a8f8fd6e2cb86dcf08e428dd26dfdb4610a8e8fe33fdd5f5'
x=read(ROOT/'fixed-ssh-v8-execution.json');r=read(PAY/'working-set-fixed-ssh-reader-v8.json');manifest=read(PAY/'working-set-fixed-ssh-v8-manifest.json')
a=read(PKG/'package-artifact-manifest.json')['artifacts']
for i in a:
 p=PKG/i['path'];assert sha(p)==i['sha256'] and p.stat().st_size==i['bytes']
for i in manifest['payloadFiles']:
 p=PKG/i['path'];assert not p.is_symlink() and stat.S_ISREG(p.stat().st_mode) and sha(p)==i['sha256'] and p.stat().st_size==i['bytes'] and stat.S_IMODE(p.stat().st_mode)==0o600
assert x['source']==r['source']==manifest['source']
assert x['transfer']['status']=='pass' and x['transfer']['allHashesExact'] is True and x['transfer']['noLinks'] is True and x['transfer']['fileCount']==25
assert x['install']['status']=='pass' and x['install']['wheelHashesExact'] is True and x['install']['pipCheck']=='pass' and x['install']['recordCheck']=='pass' and x['install']['publicSurface']=='pass'
assert r['reader']['actualIdentityHashes']==r['reader']['expectedIdentityHashes']
assert r['reader']['proofNonceCount']==r['reader']['proofRequests']==2
assert r['reader']['membershipExact'] is True and r['reader']['coverage']=='complete' and r['reader']['uncertainCount']==0 and r['reader']['actualSelectedCount']==r['reader']['expectedSelectedCount']==2
assert r['reader']['dtoFieldChecks']==r['reader']['activityAgeChecks']==2
assert all(v is True for v in r['cleanup'].values())
assert sha(PAY/'working-set-fixed-ssh-v8-preclose.json')==r['precloseReceiptSha256']
c=r['remoteFixture']['closeReceipt'];assert c['status']=='pass' and c['remoteProcess']['sameIncarnationStillAlive'] is False and c['privateConfigAbsent'] is True and c['caughtSignal'] is None
for k in ('selectorClosed','socketPathsAbsent','sourceCleanupComplete','threadStopped'):assert c['runtime'][k] is True
for k in ('peerCount','workerCount','workerStarts'):assert c['runtime'][k]==0
for k in ('localInstalledModules',):assert r[k]['loadedModulesUnderPrivateVenvAndWheelExact'] is True and r[k]['wheelSha256']==manifest['wheels']
assert c['loadedModulesFinal']['installedModuleBytesExact'] is True and c['loadedModulesFinal']['wheelSha256']==manifest['wheels']
assert c['bridgeRunTerminal']=={'code':None,'expectedTransportTerminal':True,'type':'EOFError'} and c['bridgeExitCode']==1 and r['sshExitCode']==255
assert r['normalCliExitPass'] is False and r['gracefulEofPass'] is False
z={'schema':'agent-observer.working-set-fixed-ssh-v8-primary-review.v1','status':'functional_and_physical_cleanup_verified_terminal_exit_under_review','packageArtifactsRehashed':len(a),'payloadFilesRehashed':len(manifest['payloadFiles']),'source':x['source'],'wheels':manifest['wheels'],'reportSha256':sha(PAY/'working-set-fixed-ssh-reader-v8.json'),'executionSha256':sha(ROOT/'fixed-ssh-v8-execution.json'),'separateFreshNonces':2,'selectedRows':2,'coverage':'complete','bridgeExitCode':1,'bridgeTerminal':'EOFError','sdkSshExitCode':255,'normalCliExitPass':False,'physicalCleanup':'one independent bounded SSH close/process/path observation passes','collection':'collect=False synthetic only; normal provider/services not used','noNewExecution':'saved-result hash/arithmetic/contract checks only; actual fixed-SSH run was one guarded plan under exclusive lock'}
(ROOT/'primary-saved-review.json').write_text(json.dumps(z,indent=2,sort_keys=True)+'\n');print(json.dumps(z,indent=2))
