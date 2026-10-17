"""Serial unchanged Mesh intake probe against an exact owning source overlay."""

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def inventory(root, directories):
    return {str(path.relative_to(root)): pin(path)
            for directory in directories for path in sorted((root / directory).rglob("*"))
            if path.is_file() and path.suffix in (".py", ".json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "observer", "python311", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    mesh, observer, output = args.mesh.resolve(), args.observer.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    mesh_inputs = inventory(mesh, ("src", "tests", "scripts", "contracts"))
    owner_inputs = inventory(observer, ("agent_observer", "tests"))
    probe_path = "docs/evidence/2026-10-17-reader-capacity/probe_reader_intake.py"
    probe = mesh / probe_path
    probe_pin = pin(probe)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=f"{mesh / 'src'}:{observer}:{observer / 'tests'}")
    commands, outcomes = [], []
    lock_path = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
    with lock_path.open("a") as lock:
        print("Waiting for shared CPU advisory lock", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        print("Shared lock acquired; accounting screen only", flush=True)
        for version, python in (("314", sys.executable), ("311", str(args.python311.absolute()))):
            for rows in (100, 500, 2000):
                for backend in ("default", "packed"):
                    name = f"{rows}-{backend}-{version}"
                    report_path, log = output / (name + ".json"), output / (name + ".log")
                    argv = [python, "-B", str(probe), "--mesh", str(mesh), "--observer", str(observer),
                            "--rows", str(rows), "--backend", backend, "--output", str(report_path)]
                    with log.open("x") as stream:
                        result = subprocess.run(argv, cwd=observer, env=env, stdout=stream, stderr=subprocess.STDOUT)
                    commands.append(dict(argv=argv, returncode=result.returncode, cwd=str(observer)))
                    assert result.returncode == 0, log
                    report = json.loads(report_path.read_text())
                    assert report["gcDisabled"] and report["finalCounters"] == [0] * 6
                    assert report["heapPeak"] <= 67108864 and report["encodedPeakReservedBound"] <= 33554432
                    for name, digest in report["loadedInputs"].items():
                        role, relative = name.split("/", 1)
                        expected = probe_pin if role == "mesh" and relative == probe_path else (
                            mesh_inputs if role == "mesh" else owner_inputs)[relative]
                        assert expected["sha256"] == digest, name
                    assert pin(probe) == probe_pin
                    scalar = {key: report[key] for key in ("rows", "backend", "python", "outcome", "heapPeak",
                                                            "encodedPeakReservedBound", "nativeMembershipCells")}
                    scalar["failure"] = None if report["failure"] is None else {
                        key: report["failure"][key] for key in ("stage", "code")}
                    outcomes.append(scalar)
                    print(json.dumps(scalar), flush=True)
    assert inventory(mesh, ("src", "tests", "scripts", "contracts")) == mesh_inputs
    assert inventory(observer, ("agent_observer", "tests")) == owner_inputs
    report = dict(status="Diagnostic capacity only; refusals remain FAIL, no CPU/RSS/producer acceptance",
                  meshRuntime="d013d2afd14c3d6fa03a3fe377b62aff3ee5944b",
                  meshEvidence="f0924e457230c49d04d3e5983476766d4c58a4af",
                  observerBase="b8e25cad39ad741a987fd639d988da5717becad2",
                  observerOverlay={path: owner_inputs[path] for path in
                                   ("agent_observer/mesh_sync_profile.py", "tests/test_mesh_sync_patch.py")},
                  observerInputs=owner_inputs, meshInputs=mesh_inputs, probe=probe_pin,
                  runner=pin(Path(__file__)), sharedLock=str(lock_path), commands=commands,
                  outcomes=outcomes, artifacts={path.name: pin(path) for path in output.iterdir()},
                  exclusions="Unchanged actual compact IPC source+Reader shared32/64 ledger. Native owner, fixtures and oracle/proof carrier separate; not dense9/full+active/RSS/CPU/deadline/relay/controller/auth/selectedroute/2k-recovery/nativeprovider/fixedSSH/installedpair acceptance. Private packed arena explicitly test-owned; nonce/native pin/proof scratch disclosed by upstream probe.")
    (output / "qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
