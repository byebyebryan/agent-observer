from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parent
PY={'py311':'/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python','py314':'/home/bryan/code/mesh-plus/.venv/bin/python'}
ORDER=[('py311','a7',1),('py314','b176',1),('py314','a7',1),('py311','b176',1),('py311','b176',2),('py314','a7',2),('py314','b176',2),('py311','a7',2)]
PINS={'measure_common_cost.py':'e2ca768a31085cdae261d10095d6db7dca7cbfbf0368c7d70b2869d548f92a01','fixture_server.py':'17c0246d4ca51388d6adf2f3e6948a96e7343a210ed33f63c5263ca7138c7c4d'}
start=time.monotonic();done=[]
for py,source,rep in ORDER:
 for n,h in PINS.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
 target=ROOT/f'{py}-{source}-r{rep}.json';assert not target.exists()
 cmd=['rtk','proxy',PY[py],'-I','-B',str(ROOT/'measure_common_cost.py'),'--source',source,'--interpreter',py,'--replicate',str(rep)]
 before=time.monotonic();r=subprocess.run(cmd,capture_output=True,timeout=40)
 (ROOT/f'{py}-{source}-r{rep}.stdout').write_bytes(r.stdout);(ROOT/f'{py}-{source}-r{rep}.stderr').write_bytes(r.stderr)
 row={'python':py,'source':source,'replicate':rep,'returncode':r.returncode,'elapsedSeconds':time.monotonic()-before,'command':cmd,'receiptExists':target.exists()}
 if target.exists():
  x=json.loads(target.read_text());row.update({'status':x['status'],'failureStage':x.get('failureStage'),'failureReason':x.get('failureReason'),'cleanup':x['cleanup'],'accounting':x['accounting']})
 done.append(row);(ROOT/'matrix-execution.json').write_text(json.dumps({'order':ORDER,'pins':PINS,'cases':done,'elapsedSeconds':time.monotonic()-start,'timingType':'16coldworker invocations, no warmup, percaseexclusive lock, componentonly'},indent=2)+'\n')
 print(json.dumps(row),flush=True)
 if r.returncode or row.get('status')!='passed':raise SystemExit(1)
 if time.monotonic()-start>600:raise SystemExit('controller_budget')
