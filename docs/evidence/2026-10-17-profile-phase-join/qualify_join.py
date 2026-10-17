"""Qualify immutable Observer patch and Mesh phase sources without changing either."""

import argparse
import fcntl
import gc
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path


OBSERVER = "b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f"
MESH_RUNTIME = "13876e6d723ad3ff5511c12e2900e7dc34f2c778"
MESH_EVIDENCE = "2385712df2f0ea8ba0697facf01ae2543fb377d2"
PREFIX = "docs/evidence/2026-10-17-reader-capacity/"
PHASE_PREFIX = "docs/evidence/2026-10-17-normalization-phases/"
MODULES = ("test_mesh_sync_patch", "test_mesh_sync_profile", "test_mesh_sync_codec", "test_mesh_sync_read")


def pin(path):
    value = path.read_bytes()
    return dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(repo, *args):
    return subprocess.check_output(["rtk", "proxy", "git", "-C", str(repo), *args])


def export(repo, revision, target):
    target.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", revision))) as archive:
        archive.extractall(target, filter="data")


def inventory(root, directories):
    return {str(path.relative_to(root)): pin(path)
            for directory in directories for path in sorted((root / directory).rglob("*"))
            if path.is_file() and path.suffix in (".py", ".json")}


def verify_git(repo, revision, files):
    paths = sorted(files)
    request = "".join(f"{revision}:{path}\n" for path in paths).encode()
    data = subprocess.check_output(["rtk", "proxy", "git", "-C", str(repo), "cat-file", "--batch"], input=request)
    offset = 0
    for path in paths:
        end = data.index(b"\n", offset)
        _oid, kind, size = data[offset:end].split()
        assert kind == b"blob", path
        offset = end + 1
        value = data[offset:offset + int(size)]
        assert dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest()) == files[path], path
        offset += int(size)
        assert data[offset:offset + 1] == b"\n"
        offset += 1
    assert offset == len(data)


def loaded_inputs(mesh, observer):
    loaded = {}
    for module in tuple(sys.modules.values()):
        if getattr(module, "__name__", None) == "__main__":
            continue
        name = getattr(module, "__file__", None)
        if name and Path(name).suffix == ".py":
            path = Path(name).resolve()
            for role, root in (("mesh", mesh), ("observer", observer)):
                if path.is_relative_to(root):
                    loaded[role + "/" + str(path.relative_to(root))] = pin(path)["sha256"]
                    break
    return loaded


def worker(args):
    mesh, observer = args.mesh.resolve(), args.observer.resolve()
    sys.path[:0] = [str(mesh / "src"), str(observer), str(observer / "tests"), str(mesh / "tests")]
    gc.disable()
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    # Both repositories have test_sync_compact.py. Load the Mesh file by its
    # exact path rather than allowing the Observer test directory to shadow it.
    spec = importlib.util.spec_from_file_location("mesh_phase_suite", mesh / "tests/test_sync_compact.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    with args.log.open("x") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    assert not gc.isenabled()
    write(args.output, dict(python=sys.version.split()[0], tests=result.testsRun,
                           failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
                           gcDisabled=True, modules=(*MODULES, "mesh/tests/test_sync_compact.py"),
                           loadedInputs=loaded_inputs(mesh, observer)))
    assert result.wasSuccessful() and not result.skipped


def qualify(args):
    root, repo = args.observer_repo.resolve(), args.mesh_repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=args.resume)
    mesh, observer = output / "mesh-2385712", output / "observer-b6ce842"
    if not mesh.exists():
        export(repo, MESH_EVIDENCE, mesh)
    if not observer.exists():
        export(root, OBSERVER, observer)
    mesh_inputs = inventory(mesh, ("src", "tests", "scripts", "contracts"))
    owner_inputs = inventory(observer, ("agent_observer", "tests"))
    verify_git(repo, MESH_RUNTIME, mesh_inputs)
    verify_git(root, OBSERVER, owner_inputs)
    owner_receipt = read(observer / "docs/evidence/2026-10-17-profile-patch/receipt.json")
    protected = owner_receipt["protectedInputs"]
    verify_git(repo, MESH_RUNTIME, protected)
    upstream = {}
    for prefix, expected in ((PREFIX, "34759770cf03bb0864bdf95e6fe7524cd781ad99db21050499245e5614a4c7b9"),
                             (PHASE_PREFIX, "6a98a0f27563f174a0981fe6c7b2f190bf10669b1ae4247b55b67de6e21bafaf")):
        receipt_path = mesh / prefix / "receipt.json"
        assert pin(receipt_path)["sha256"] == expected
        receipt = read(receipt_path)
        for name, expected_pin in receipt["artifacts"].items():
            assert pin(mesh / name) == expected_pin, name
        verify_git(repo, MESH_EVIDENCE, receipt["artifacts"])
        upstream[prefix] = dict(receipt=pin(receipt_path), artifacts=receipt["artifacts"])
    probe = mesh / PREFIX / "probe_reader_intake.py"
    extra_mesh = {PREFIX + "probe_reader_intake.py": pin(probe)}
    verify_git(repo, MESH_EVIDENCE, extra_mesh)
    commands, focused, cases = [], {}, {}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=f"{mesh / 'src'}:{observer}:{observer / 'tests'}")
    lock_path = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")

    def invoke(argv, log):
        initial, attempt = log, 1
        while log.exists():
            attempt += 1
            log = initial.with_name(initial.stem + f"-attempt{attempt}" + initial.suffix)
        with log.open("x") as stream:
            result = subprocess.run(argv, cwd=observer, env=env, stdout=stream, stderr=subprocess.STDOUT)
        commands.append(dict(argv=argv, cwd=str(observer), returncode=result.returncode))
        assert result.returncode == 0, log

    def verify_loaded(report):
        for name, digest in report["loadedInputs"].items():
            role, relative = name.split("/", 1)
            files = owner_inputs if role == "observer" else mesh_inputs | extra_mesh
            assert files[relative]["sha256"] == digest, name

    with lock_path.open("a") as lock:
        print("Waiting for shared advisory lock", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        print("Lock acquired; source/accounting qualification, no timing claim", flush=True)
        # Keep the venv launcher path: resolving its symlink bypasses that
        # environment and loses its declared dependencies.
        for version, python in (("314", sys.executable), ("311", str(args.python311.absolute()))):
            report_path = output / f"focused-{version}.json"
            if not report_path.exists():
                invoke([python, "-B", str(Path(__file__).resolve()), "--worker", "--mesh", str(mesh),
                        "--observer", str(observer), "--output", str(report_path), "--log", str(output / f"focused-{version}.log")],
                       output / f"focused-{version}.stdout.log")
            else:
                commands.append(dict(reusedExisting=report_path.name, pin=pin(report_path), testsRerun=False))
            report = read(report_path)
            verify_loaded(report)
            assert report["tests"] == 93 and report["failures"] == report["errors"] == report["skips"] == 0
            focused[version] = report
            print(f"Python {report['python']}:93 focused methods PASS", flush=True)
            for rows in (100, 500, 2000):
                for backend in ("default", "packed"):
                    name = f"{rows}-{backend}-{version}"
                    report_path = output / f"{name}.json"
                    if not report_path.exists():
                        invoke([python, "-B", str(probe), "--mesh", str(mesh), "--observer", str(observer),
                                "--rows", str(rows), "--backend", backend, "--output", str(report_path)], output / f"{name}.log")
                    else:
                        commands.append(dict(reusedExisting=report_path.name, pin=pin(report_path), testsRerun=False))
                    report = read(report_path)
                    verify_loaded(report)
                    assert report["gcDisabled"] and report["finalCounters"] == [0] * 6
                    assert report["heapPeak"] <= 67108864 and report["encodedPeakReservedBound"] <= 33554432
                    cases[name] = report
                    print(json.dumps({key: report[key] for key in ("rows", "backend", "python", "outcome", "heapPeak", "encodedPeakReservedBound")}), flush=True)
    assert inventory(mesh, ("src", "tests", "scripts", "contracts")) == mesh_inputs
    assert inventory(observer, ("agent_observer", "tests")) == owner_inputs
    verify_git(repo, MESH_RUNTIME, mesh_inputs)
    verify_git(root, OBSERVER, owner_inputs)
    artifacts = {path.name: pin(path) for path in output.iterdir() if path.is_file()}
    write(output / "qualification.json", dict(
        status="Bounded exact-source join; capacity outcomes below do not grant producer acceptance",
        observer=OBSERVER, meshRuntime=MESH_RUNTIME, meshEvidence=MESH_EVIDENCE,
        observerInputs=owner_inputs, meshInputs=mesh_inputs, protectedInputs=protected,
        upstream=upstream, observerPriorReceipt=pin(observer / "docs/evidence/2026-10-17-profile-patch/receipt.json"),
        probe=extra_mesh, runner=pin(Path(__file__)), focused=focused, capacity=cases,
        commands=commands, artifacts=artifacts, sharedLock=str(lock_path),
        exclusions="Actual compact source IPC and Reader share one unchanged32/64 ledger; native owner separate. Test nonce/native pin/proof carrier, synthetic clock and extra prepaid proof scratch; private packed arena test-owned. Full-only710/3510/14010 cells, not dense9. No relay/controller/authselectedroute, inclusive physical/RSS/CPU/absolute2s15s, recovery/nativefleet/fixedSSH/installedpair/producer claim. Original failures and source tuples unchanged.",
        gitCleanup="HOLD"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--resume", action="store_true", help="Verify and reuse completed reports after a harness interruption")
    for name in ("observer-repo", "mesh-repo", "python311", "mesh", "observer", "log"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.worker:
        worker(args)
    else:
        assert args.observer_repo and args.mesh_repo and args.python311
        qualify(args)


if __name__ == "__main__":
    main()
