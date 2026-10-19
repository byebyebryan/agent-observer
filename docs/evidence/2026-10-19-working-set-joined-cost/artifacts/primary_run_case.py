from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path(__file__).resolve().parent
pins=json.loads((root/"primary-preexecution-review.json").read_text())["fileSha256"]
for name,want in pins.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==want
label=sys.argv[1]
allowed={"py311-r1":("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python","py311",1),"py311-r2":("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python","py311",2),"py314-r1":("/home/bryan/code/mesh-plus/.venv/bin/python","py314",1),"py314-r2":("/home/bryan/code/mesh-plus/.venv/bin/python","py314",2)}
exe,py,rep=allowed[label]
assert not (root/(label+".json")).exists()
assert not (root/(label+"-primary.json")).exists()
start=time.monotonic()
p=subprocess.run([exe,"-B",str(root/"joined_sdk_trial.py"),"--run-reviewed-trial","--interpreter",py,"--replicate",str(rep)],cwd=root,capture_output=True,timeout=360,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","TMPDIR":"/tmp"})
elapsed=time.monotonic()-start
for name,raw in [(label+".stdout",p.stdout),(label+".stderr",p.stderr)]:
 fd=os.open(root/name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,"wb") as stream:stream.write(raw)
r={"case":label,"returncode":p.returncode,"elapsedSeconds":elapsed,"sourceRunnerSha256":pins["joined_sdk_trial.py"],"stdoutSha256":hashlib.sha256(p.stdout).hexdigest(),"stderrSha256":hashlib.sha256(p.stderr).hexdigest(),"sharedLockOwnedInsideRunner":True}
fd=os.open(root/(label+"-primary.json"),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as stream:json.dump(r,stream,indent=2);stream.write("\n")
print(json.dumps(r),flush=True)
if (root/(label+".json")).is_file():
 r=json.loads((root/(label+".json")).read_text())
 print(json.dumps({k:r[k] for k in ("status","failureStage","failureReason","cleanup","cpu","readJoin") if k in r}),flush=True)
raise SystemExit(p.returncode)
