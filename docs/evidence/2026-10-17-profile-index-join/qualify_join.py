"""Qualify exact Agent patch and Mesh index workspace sources, without edits."""

import argparse
import fcntl
import gc
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


OBSERVER = "b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f"
MESH = "231a631337bb8c4d5feb7cd7d7c8193ef29b5ffc"
EVIDENCE = "103f3b3056d5f88d4e72e6556e7af6e8ff2e7aed"
PREFIX = "docs/evidence/2026-10-17-reader-capacity/"
OBSERVER_MODULES = ("test_mesh_sync_patch", "test_mesh_sync_profile", "test_mesh_sync_codec", "test_mesh_sync_read")
MESH_MODULES = ("test_sync_reconstruction", "test_sync_compact", "test_sync_ordered",
                "test_sync_packed_nodes", "test_sync_patch_workspace")


def utilities():
    root = Path(__file__).resolve().parents[3]
    path = root / "docs/evidence/2026-10-17-profile-phase-join/qualify_join.py"
    spec = importlib.util.spec_from_file_location("phase_join_utilities", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    assert helper.pin(path)["sha256"] == "5f14f53d8c97e5cb38ba0be19246d6704fd14f35a067ccf60f59f2ee787e4356"
    helper.verify_git(root, "78b9ceee999c5e73c980b2f4f678db37cf3f57c4", {str(path.relative_to(root)): helper.pin(path)})
    return helper


def worker(args, helper):
    mesh, observer = args.mesh.resolve(), args.observer.resolve()
    modules = OBSERVER_MODULES if args.role == "observer" else MESH_MODULES
    tests = observer / "tests" if args.role == "observer" else mesh / "tests"
    # Separate fresh interpreters avoid same-named fixture modules across repos.
    sys.path[:0] = [str(mesh / "src"), str(tests), str(observer)]
    gc.disable()
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    with args.log.open("x") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    assert not gc.isenabled()
    helper.write(args.output, dict(role=args.role, python=sys.version.split()[0], tests=result.testsRun,
                                  failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
                                  gcDisabled=True, modules=modules, loadedInputs=helper.loaded_inputs(mesh, observer)))
    assert result.wasSuccessful() and not result.skipped


def qualify(args, helper):
    root, repo = args.observer_repo.resolve(), args.mesh_repo.resolve()
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    mesh, observer = work / "mesh-103f3b3", work / "observer-b6ce842"
    helper.export(repo, EVIDENCE, mesh)
    helper.export(root, OBSERVER, observer)
    mesh_inputs = helper.inventory(mesh, ("src", "tests", "scripts", "contracts"))
    owner_inputs = helper.inventory(observer, ("agent_observer", "tests"))
    helper.verify_git(repo, MESH, mesh_inputs)
    helper.verify_git(root, OBSERVER, owner_inputs)
    protected = helper.read(observer / "docs/evidence/2026-10-17-profile-patch/receipt.json")["protectedInputs"]
    helper.verify_git(repo, MESH, protected)
    upstream = {}
    for prefix, digest in ((PREFIX, "34759770cf03bb0864bdf95e6fe7524cd781ad99db21050499245e5614a4c7b9"),
                           ("docs/evidence/2026-10-17-normalization-phases/", "6a98a0f27563f174a0981fe6c7b2f190bf10669b1ae4247b55b67de6e21bafaf"),
                           ("docs/evidence/2026-10-17-group-ownership/", "c6de2a8f62f2729325d9bd01fb5cf6664df562fae937f9936af9297153fac789"),
                           ("docs/evidence/2026-10-17-index-workspace/", "b34e41750f18f4708e10b92d5d69c9c75ffaeb866571229ab7ae8be7ff160ad7")):
        path = mesh / prefix / "receipt.json"
        assert helper.pin(path)["sha256"] == digest
        data = helper.read(path)
        for name, expected in data["artifacts"].items():
            assert helper.pin(mesh / name) == expected, name
        helper.verify_git(repo, EVIDENCE, data["artifacts"])
        upstream[prefix] = dict(receipt=helper.pin(path), artifacts=data["artifacts"])
    probe = mesh / PREFIX / "probe_reader_intake.py"
    runners = {PREFIX + "probe_reader_intake.py": helper.pin(probe)}
    helper.verify_git(repo, EVIDENCE, runners)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=f"{mesh / 'src'}:{observer}:{observer / 'tests'}")
    commands, tests, capacity = [], {}, {}

    def run(argv, log):
        with log.open("x") as stream:
            result = subprocess.run(argv, cwd=observer, env=env, stdout=stream, stderr=subprocess.STDOUT)
        commands.append(dict(argv=argv, cwd=str(observer), log=log.name, returncode=result.returncode))
        assert result.returncode == 0, log

    def loaded(value):
        for name, digest in value["loadedInputs"].items():
            role, relative = name.split("/", 1)
            files = owner_inputs if role == "observer" else mesh_inputs | runners
            assert files[relative]["sha256"] == digest, name

    lock_path = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
    with lock_path.open("a") as lock:
        print("Waiting for shared advisory lock", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        print("Lock acquired; no performance claim", flush=True)
        for label, python in (("314", sys.executable), ("311", str(args.python311.absolute()))):
            for role, count in (("observer", 64), ("mesh", 68)):
                name = f"focused-{role}-{label}"
                path = work / f"{name}.json"
                run([python, "-B", str(Path(__file__).resolve()), "--worker", "--role", role,
                     "--mesh", str(mesh), "--observer", str(observer), "--output", str(path),
                     "--log", str(work / f"{name}.log")], work / f"{name}.stdout.log")
                value = helper.read(path)
                loaded(value)
                assert value["tests"] == count and value["failures"] == value["errors"] == value["skips"] == 0
                assert value["gcDisabled"]
                tests[name] = value
                print(f"Python {value['python']}:{role} {count} focused methods PASS", flush=True)
            for rows in (100, 500, 2000):
                for backend in ("default", "packed"):
                    name = f"{rows}-{backend}-{label}"
                    path = work / f"{name}.json"
                    run([python, "-B", str(probe), "--mesh", str(mesh), "--observer", str(observer),
                         "--rows", str(rows), "--backend", backend, "--output", str(path)], work / f"{name}.log")
                    value = helper.read(path)
                    loaded(value)
                    assert value["gcDisabled"] and value["finalCounters"] == [0] * 6
                    assert value["heapPeak"] <= 67108864 and value["encodedPeakReservedBound"] <= 33554432
                    capacity[name] = value
                    print(json.dumps({key: value[key] for key in ("rows", "backend", "python", "outcome", "heapPeak", "encodedPeakReservedBound", "failure")}), flush=True)
    assert helper.inventory(mesh, ("src", "tests", "scripts", "contracts")) == mesh_inputs
    assert helper.inventory(observer, ("agent_observer", "tests")) == owner_inputs
    helper.verify_git(repo, MESH, mesh_inputs)
    helper.verify_git(root, OBSERVER, owner_inputs)
    helper.write(work / "qualification.json", dict(
        observerRuntime=OBSERVER, meshRuntime=MESH, meshEvidence=EVIDENCE,
        status="Bounded source join only; outcomes do not grant producer acceptance",
        observerInputs=owner_inputs, meshInputs=mesh_inputs, protectedInputs=protected,
        upstream=upstream, focused=tests, capacity=capacity, commands=commands,
        artifacts={path.name: helper.pin(path) for path in work.iterdir() if path.is_file()},
        scripts=dict(runner=helper.pin(Path(__file__)), utility=helper.pin(Path(helper.__file__))),
        originalProbe=runners, sharedLock=str(lock_path), gitCleanup="HOLD",
        exclusions="Actual compact source IPC and Reader share original32/64 ledger; native owner separate. Private nonce/nativepin/proofcarrier, synthetic clock, extra prepaid proof scratch, test-owned packed arena. Full-only710/3510/14010cells, notdense9/fullactive/slowpeers. No ordinary Reader/authroute/controller/relay, inclusive physical/RSS/CPU/2s15s/nativefleet/fixedSSH/installedpair/producer acceptance. Old source tuples/failures unchanged."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--role", choices=("observer", "mesh"))
    for name in ("observer-repo", "mesh-repo", "python311", "mesh", "observer", "log"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    helper = utilities()
    if args.worker:
        worker(args, helper)
    else:
        assert args.observer_repo and args.mesh_repo and args.python311
        qualify(args, helper)


if __name__ == "__main__":
    main()
