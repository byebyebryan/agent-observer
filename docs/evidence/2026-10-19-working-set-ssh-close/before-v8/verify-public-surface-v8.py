#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
EXPECTED = {
    "frame": ("mesh_plus/schemas/agent-working-set-native.schema.json", "a87b9661f3436a5894056e94f9b061ae84ecd9c78110d759e9e7d54b70956b95"),
    "request": ("mesh_plus/schemas/agent-working-set-request.schema.json", "4f9b3f83ce00aab688830a7b452d476111abf26d52aca608548da8aba2318aeb"),
}
EXPECTED_PROFILE = "agent-observer.mesh-working-set.v1"
EXPECTED_DESCRIPTOR = "sha256:8b1ab6d4d37c007867c3a005341f58b9b60705f7e65fb0ae86df316638b543e9"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def check(value: bool, code: str) -> None:
    if not value:
        raise RuntimeError(code)


def main() -> None:
    venv = PACKAGE_ROOT / "venv-314"
    python = venv / "bin/python"
    observer_cli = venv / "bin/agent-observer"
    mesh_wheel = ROOT / "wheels/mesh_plus-0.1.0a23-py3-none-any.whl"
    with zipfile.ZipFile(mesh_wheel) as archive:
        schemas = {}
        for kind, (name, expected_hash) in EXPECTED.items():
            raw = archive.read(name)
            check(digest(raw) == expected_hash, "mesh_schema_wheel_hash_mismatch")
            schemas[kind] = json.loads(raw)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    schema_rows = {}
    for kind, (_name, expected_hash) in EXPECTED.items():
        proc = subprocess.run([str(observer_cli), "service", "working-set-schema", "--kind", kind], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        check(proc.returncode == 0 and len(proc.stdout) <= 65536 and len(proc.stderr) <= 65536, "observer_schema_cli_failed")
        command_canonical = canonical(json.loads(proc.stdout))
        mesh_canonical = canonical(schemas[kind])
        check(command_canonical == mesh_canonical, "observer_mesh_schema_canonical_mismatch")
        schema_rows[kind] = {"canonicalMatch": True, "observerCommandCanonicalSha256": digest(command_canonical), "meshWheelRawSha256": expected_hash, "observerCommandBytes": len(proc.stdout)}
    code = r'''import argparse, contextlib, io, json, sys
from pathlib import Path
from unittest.mock import patch
import agent_observer, mesh_plus
from mesh_plus.api import descriptor
from agent_observer import service_cli
prefix=Path(sys.prefix).resolve()
for module in (agent_observer, mesh_plus):
    path=Path(module.__file__).resolve()
    if prefix not in path.parents: raise SystemExit('module_outside_venv')
d=descriptor('agent',profile_id='agent-observer.mesh-working-set.v1')
class Parsed(Exception):
    def __init__(self,value): self.value=value
def parse_only(argv):
    original=argparse.ArgumentParser.parse_args
    def capture(parser,args=None,namespace=None): raise Parsed(original(parser,args,namespace))
    with patch.object(argparse.ArgumentParser,'parse_args',capture):
        try: service_cli.serve(argv)
        except Parsed as caught: return caught.value
    raise SystemExit('runtime_would_have_been_reached')
base=['serve','--host-scope','fixture','--socket',str(Path(sys.prefix)/'never-created.sock'),'--provider','codex','--codex-home',str(Path(sys.prefix)/'codex-home')]
window_cases={}
for label,extra,want in [('bare',['--working-set-window-hours'],72),('explicit72',['--working-set-window-hours','72'],72),('zero',['--working-set-window-hours','0'],0),('default',[],None)]:
    args=parse_only(base+extra)
    if args.working_set_window_hours != want: raise SystemExit('window_default_or_value_mismatch')
    window_cases[label]=args.working_set_window_hours
bad=io.StringIO()
with contextlib.redirect_stderr(bad):
    try: parse_only(base+['--working-set-window-hours','721'])
    except SystemExit as error:
        if error.code != 2: raise SystemExit('window_invalid_status_mismatch')
    else: raise SystemExit('window_out_of_range_accepted')
print(json.dumps({'moduleRootsPrivate':True,'descriptor':{'profile':d.profile_id,'digest':d.contract_digest,'sdk':d.sdk_version,'protocol':d.native_protocol,'nativeVersion':d.native_version,'frameBytes':d.frame_bytes},'windowCases':window_cases,'outOfRangeRejected':True},sort_keys=True))'''
    probe = subprocess.run([str(python), "-c", code], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    check(probe.returncode == 0 and len(probe.stdout) <= 8192 and len(probe.stderr) <= 8192, "installed_profile_or_window_probe_failed")
    facts = json.loads(probe.stdout)
    descriptor = facts["descriptor"]
    check(descriptor == {"profile": EXPECTED_PROFILE, "digest": EXPECTED_DESCRIPTOR, "sdk": 1, "protocol": "agent-observer.working-set", "nativeVersion": 1, "frameBytes": 8404992}, "installed_descriptor_mismatch")
    check(facts["moduleRootsPrivate"] is True, "installed_module_root_mismatch")
    check(facts["windowCases"] == {"bare": 72, "explicit72": 72, "zero": 0, "default": None} and facts["outOfRangeRejected"] is True, "installed_service_window_cli_mismatch")
    report = {"schema": "agent-observer.working-set-fixed-ssh-v8-public-surface.v1", "status": "pass", "source": {"observerCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0", "meshCommit": "b9e8488e0f0fa438119e36848ac7c9887038ea1c"}, "interpreter": "3.14.8", "observerSchemaCli": schema_rows, "meshDescriptor": descriptor, "installedModuleRootsOnly": True, "serviceWindowArgumentParseOnly": facts["windowCases"], "outOfRangeRejectedBeforeServiceRuntime": True, "coverageLimits": ["installed CLI schemas are canonical-equal to Mesh packaged native/request schemas", "window checks stop at installed argument parsing; no service runtime, socket, IPC, provider or native call"]}
    target = ROOT / "working-set-fixed-ssh-v8-public-surface.json"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "pass", "schemaCanonicalMatches": True, "descriptorExact": True, "serviceWindowParseOnlyExact": True, "report": str(target)}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        message = str(error)
        code = message if message.replace("_", "").isalnum() and len(message) <= 96 else "public_surface_failed"
        print(json.dumps({"status": "failed", "reasonCode": code}, sort_keys=True))
        raise SystemExit(1) from None
