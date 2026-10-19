from pathlib import Path
import fcntl,json,subprocess,os,hashlib,time
R=Path(__file__).resolve().parent
pythons={'314':'/home/bryan/code/mesh-plus/.venv/bin/python','311':'/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python'}
records=[]
with open('/home/bryan/.cache/agent-active-feed-cpu.lock','a+b') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for label,py in pythons.items():
  out=R/('py'+label+'-working-2000.json');start=time.monotonic()
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'};env.pop('PYTHONPATH',None)
  p=subprocess.run([py,'-B',str(R/'rss_normal_gc_128_probe.py'),'--variant','working','--rows','2000','--output',str(out)],cwd=R,env=env,capture_output=True,timeout=300)
  (R/('py'+label+'.stdout')).write_bytes(p.stdout);(R/('py'+label+'.stderr')).write_bytes(p.stderr)
  x=json.loads(out.read_text()) if out.exists() else {}
  rec={'python':label,'exitCode':p.returncode,'status':x.get('status'),'seconds':time.monotonic()-start,'reportSha256':hashlib.sha256(out.read_bytes()).hexdigest() if out.exists() else None,'rss':x.get('rssDescription'),'weakrefs':x.get('weakrefsAfterRunReturn'),'gc':x.get('gc')};records.append(rec)
  (R/'matrix-result.json').write_text(json.dumps(records,indent=2,sort_keys=True)+'\n');print(json.dumps(rec,sort_keys=True),flush=True)
  if p.returncode or x.get('status')!='pass':raise SystemExit(1)
