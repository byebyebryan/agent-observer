from pathlib import Path
import hashlib,json,subprocess,time,os
root=Path(__file__).resolve().parent
cases=[]
for label in ("py311-r2","py314-r1","py314-r2"):
 start=time.monotonic()
 p=subprocess.run(["/home/bryan/code/mesh-plus/.venv/bin/python","-I","-B",str(root/"primary_run_case.py"),label],capture_output=True,timeout=400)
 for suffix,raw in (("controller.stdout",p.stdout),("controller.stderr",p.stderr)):
  path=root/(label+"-"+suffix)
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,"wb") as f:f.write(raw)
 r={"case":label,"returncode":p.returncode,"elapsedSeconds":time.monotonic()-start}
 if (root/(label+".json")).is_file():
  q=json.loads((root/(label+".json")).read_text());r.update({"status":q["status"],"failureStage":q.get("failureStage"),"failureReason":q.get("failureReason")})
 cases.append(r);print(json.dumps(r),flush=True)
 if p.returncode:break
out=root/"primary-matrix-continuation.json"
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as f:json.dump({"cases":cases,"stopOnFailure":True},f,indent=2);f.write("\n")
raise SystemExit(0 if len(cases)==3 and all(x["returncode"]==0 for x in cases) else 1)
