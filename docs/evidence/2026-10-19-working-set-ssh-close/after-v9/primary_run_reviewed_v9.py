from pathlib import Path
import fcntl,hashlib,json,subprocess,time,os
root=Path(__file__).resolve().parent
plan=root/"fixed-ssh-v9-plan.json"
want="ea146442216edb39739603e5df2bd12b51d0541e44a3a984d4ce62ee8885faa3"
assert hashlib.sha256(plan.read_bytes()).hexdigest()==want
out=root/"primary-execution.json"
assert not out.exists()
with open("/home/bryan/.cache/agent-active-feed-cpu.lock","a+") as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 start=time.monotonic()
 proc=subprocess.run(["/home/bryan/code/mesh-plus/.venv/bin/python","-I","-B",str(root/"execute-working-set-fixed-ssh-v9.py"),"--execute-reviewed-plan",want],capture_output=True,timeout=300,check=False)
 elapsed=time.monotonic()-start
 for name,raw in [("primary-execution.stdout",proc.stdout),("primary-execution.stderr",proc.stderr)]:
  p=root/name
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,"wb") as stream:stream.write(raw)
 result={"returncode":proc.returncode,"elapsedSeconds":elapsed,"sharedLock":True,"planSha256":want,"stdoutSha256":hashlib.sha256(proc.stdout).hexdigest(),"stderrSha256":hashlib.sha256(proc.stderr).hexdigest()}
 fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,"w") as stream:json.dump(result,stream,indent=2);stream.write("\n")
 print(json.dumps(result),flush=True)
 print(proc.stdout.decode(),flush=True)
 raise SystemExit(proc.returncode)
