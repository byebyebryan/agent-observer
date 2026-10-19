from pathlib import Path
import fcntl,hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parent
repo=Path("/home/bryan/code/agent-observer-working-set")
mesh=Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-bfa91a69/src")
env={**os.environ,"PATH":"/home/bryan/code/mesh-plus/.venv/bin:"+os.environ["PATH"],"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1","PYTHONPATH":str(mesh)+":"+str(repo)+":"+str(repo/"tests")}
env.pop("PYTHONHOME",None)
assert not (root/"result.json").exists()
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
with open("/home/bryan/.cache/agent-active-feed-cpu.lock","a+b") as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 start=time.monotonic()
 with (root/"check.log").open("xb") as log:
  p=subprocess.run(["rtk","proxy","./scripts/check"],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 r={"status":"pass" if p.returncode==0 else "failed","exitCode":p.returncode,"durationSeconds":time.monotonic()-start,"interpreter":"/home/bryan/code/mesh-plus/.venv/bin/python","meshSource":str(mesh),"observerBranchHeadBeforeDocumentationCommit":head,"logSha256":hashlib.sha256((root/"check.log").read_bytes()).hexdigest(),"sharedLock":True}
 (root/"result.json").write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps(r),flush=True)
 raise SystemExit(p.returncode)
