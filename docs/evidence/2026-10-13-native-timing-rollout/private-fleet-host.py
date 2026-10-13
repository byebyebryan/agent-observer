import subprocess,sys,json,time,tomllib
from pathlib import Path
host=sys.argv[1]; root=Path('/home/bryan/.cache/agent-observer-timing-20261013'); p=Path('/home/bryan/.local/share/agent-observer/0.6.0a2-b22d2b5795a9b3dd-mesh-a16-timing'); d=root/'fleet';d.mkdir(mode=0o700,exist_ok=True)
cfg=d/'sources.toml';native=tomllib.loads((Path.home()/'.config/mesh-plus/sources.toml').read_text());tmux=native['sources']['tmux_default']['socket']
cfg.write_text(f'version=1\nhost={json.dumps(host)}\n[sources.agent]\ndomain="agent"\nsocket={json.dumps(str(d/"native.sock"))}\n[sources.tmux_default]\ndomain="tmux"\nsocket={json.dumps(tmux)}\n');cfg.chmod(0o600)
children=[]
def launch(argv):
    child=subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd='/tmp');children.append(child);return child
try:
    launch([str(p/'bin/agent-observer-service'),'serve','--host-scope',host,'--socket',str(d/'native.sock'),'--provider','codex','--runtime-interval','30','--history-interval','120'])
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        q=subprocess.run([str(p/'bin/agent-observer'),'service','status','--host-scope',host,'--socket',str(d/'native.sock')],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=15)
        if q.returncode==0 and json.loads(q.stdout).get('snapshot'):break
        time.sleep(.2)
    else:raise RuntimeError('warmup')
    for source,name in [('agent','agent'),('tmux_default','tmux')]:launch([str(root/'shared-launcher'),'serve','--source',source,'--config',str(cfg),'--socket',str(d/(name+'.sock'))])
    time.sleep(.4)
    assert all(c.poll() is None for c in children)
    print(json.dumps({'status':'ready','host':host}),flush=True)
    sys.stdin.read()
finally:
    for c in reversed(children):
        if c.poll() is None:c.terminate()
    for c in reversed(children):
        try:c.wait(timeout=10)
        except subprocess.TimeoutExpired:c.kill();c.wait(timeout=5)
