"""Descriptive 45-second cgroup CPU sample; no added reader or unit changes."""

import json
import subprocess
import time
import os
from pathlib import Path

UNITS = ('agent-observer.service', 'mesh-plus-agent.service', 'rlcd-agent-dashboard.service')

def sample():
    result = {}
    for unit in UNITS:
        raw = subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'MainPID', '-p', 'CPUUsageNSec'], text=True)
        fields = dict(line.split('=', 1) for line in raw.splitlines())
        result[unit] = {'pid': int(fields['MainPID']), 'cpuNs': int(fields['CPUUsageNSec']) if fields['CPUUsageNSec'].isdigit() else 0}
    return result

def processes():
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            argv = (path/'cmdline').read_bytes().split(b'\0')
            group = (path/'cgroup').read_text()
            role = next((unit for unit in UNITS if '/' + unit in group), None)
            if role is None and b'--source' in argv and argv[argv.index(b'--source')+1] == b'agent':
                role = 'extra-agent-source'
            if role is None:
                continue
            fields = (path/'stat').read_text().rsplit(')',1)[1].split()
            result[(int(path.name), int(fields[19]))] = {
                'role': role, 'ticks': int(fields[11])+int(fields[12]),
                'parent': int(fields[1]),
            }
        except (OSError, IndexError, ValueError):
            continue
    return result

a = sample()
pa = processes()
started = time.monotonic()
time.sleep(45)
b = sample()
pb = processes()
elapsed = time.monotonic() - started
print(json.dumps({'seconds': elapsed,
    'units': {u: {'pid': b[u]['pid'], 'stable': a[u]['pid'] == b[u]['pid'],
                 'cpuPercentOneCore': (b[u]['cpuNs'] - a[u]['cpuNs']) / 1e9 / elapsed * 100} for u in UNITS},
    'stableProcesses': [{'pid': pid, 'birth': birth, 'parent': pb[(pid,birth)]['parent'],
                         'role': pb[(pid,birth)]['role'],
                         'cpuPercentOneCore': (pb[(pid,birth)]['ticks']-pa[(pid,birth)]['ticks']) / os.sysconf('SC_CLK_TCK') / elapsed * 100}
                        for pid,birth in sorted(pa.keys() & pb.keys())],
    'processesCreatedOrLost': len(pa.keys() ^ pb.keys()),
    'limits': ['ordinary workload, no added reader', 'unit cgroups include helpers',
               'process CPU excludes created/lost processes and reaped children',
               'extra sources classified by explicit --source agent, not assumed SSH ownership',
               'do not add overlapping unit and process CPU values']}))
