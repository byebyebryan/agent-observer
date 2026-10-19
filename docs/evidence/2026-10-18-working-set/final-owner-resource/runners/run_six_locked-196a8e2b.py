from __future__ import annotations
import fcntl
import hashlib
import json
import os
import subprocess
from pathlib import Path

BASE = Path('/home/bryan/.cache/agent-observer-working-set-20261018/final-source-196a8e2b-screen')
SCREEN = BASE / 'runners/ledger-source-screen-196a8e2b.py'
LOCK = Path('/home/bryan/.cache/agent-active-feed-cpu.lock')
INTERPRETERS = {
    '314': '/home/bryan/code/mesh-plus/.venv/bin/python',
    '311': '/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python',
}
COUNTS = (100, 200, 400)
records = []
with LOCK.open('r') as lock_file:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    for py_name, executable in INTERPRETERS.items():
        for count in COUNTS:
            stem = f'ledger-final-{py_name}-{count}'
            stdout_path = BASE / 'outputs/stdout' / f'{stem}.json'
            stderr_path = BASE / 'outputs/stderr' / f'{stem}.log'
            child_env = os.environ.copy()
            child_env.pop('PYTHONPATH', None)
            with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
                completed = subprocess.run(
                    [executable, '-B', str(SCREEN), str(count)],
                    stdout=stdout,
                    stderr=stderr,
                    env=child_env,
                    check=False,
                )
            records.append({
                'pythonTag': py_name,
                'interpreter': executable,
                'count': count,
                'argv': [executable, '-B', str(SCREEN), str(count)],
                'returnCode': completed.returncode,
                'stdout': str(stdout_path),
                'stderr': str(stderr_path),
                'stdoutSha256': hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
                'stderrSha256': hashlib.sha256(stderr_path.read_bytes()).hexdigest(),
            })
manifest = {
    'sourceRoot': '/home/bryan/.cache/agent-observer-working-set-20261018/final-source-196a8e2b',
    'screenRunnerSha256': hashlib.sha256(SCREEN.read_bytes()).hexdigest(),
    'lockedBy': str(LOCK),
    'lockHeldAcrossAllRuns': True,
    'counts': list(COUNTS),
    'gcMode': 'child screen calls gc.disable(); no explicit gc.collect call',
    'records': records,
}
(BASE / 'provenance/run-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
print(json.dumps({'runs': len(records), 'returnCodes': [r['returnCode'] for r in records], 'manifest': str(BASE / 'provenance/run-manifest.json')}, sort_keys=True))
