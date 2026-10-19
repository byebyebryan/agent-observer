from pathlib import Path
import fcntl,hashlib,json,os,subprocess,time
R=Path(__file__).resolve().parent
p=R/'fixed-ssh-v8-plan.json'; token='f73cbc6959c30414056e9629656c5ff75e3aeb7aab88640163881d2c0d07d311';assert hashlib.sha256(p.read_bytes()).hexdigest()==token
review={'status':'reviewed_by_primary_under_existing_producer_authorization','planSha256':token,'scope':'One exclusive new private Snap install then synthetic collect=False fixed SSH ordinary Reader proof and owned cleanup; no provider/native/normal service or adoption.','sharedLock':'/home/bryan/.cache/agent-active-feed-cpu.lock','priorPackageManifestSha256':'ca2e05091cac27746cf072271179d62bfb268e3cd4ce1070e819baa888fdf4e8'}
(R/'primary-execution-review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
argv=['rtk','proxy','/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-b9e8488e/venv-314/bin/python','-I','-B',str(R/'execute-working-set-fixed-ssh-v8.py'),'--execute-reviewed-plan',token]
with open('/home/bryan/.cache/agent-active-feed-cpu.lock','a+b') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);start=time.monotonic()
 with (R/'primary-execution.stdout').open('xb') as out,(R/'primary-execution.stderr').open('xb') as err:
  p=subprocess.run(argv,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'},stdout=out,stderr=err,timeout=330)
 summary={'exitCode':p.returncode,'elapsedSeconds':time.monotonic()-start,'stdoutSha256':hashlib.sha256((R/'primary-execution.stdout').read_bytes()).hexdigest(),'stderrSha256':hashlib.sha256((R/'primary-execution.stderr').read_bytes()).hexdigest(),'planSha256':token,'lockHeldDuringQualification':True};(R/'primary-execution-observed.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary,sort_keys=True));raise SystemExit(p.returncode)
