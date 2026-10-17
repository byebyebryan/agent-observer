"""Independently run focused compatibility; verify rather than replay capacity."""

import argparse
import fcntl
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


MESH = "13f27e25c46e1fd3da664975e964104a56fd6dbf"
EVIDENCE = "30e20118790ab83f526b2436d0739b7f531b4ed1"
OBSERVER = "b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f"
OBSERVER_EVIDENCE = "7e496b2b0555a76e7c381b1d5e6cada63f441c7b"
PREFIX = "docs/evidence/2026-10-17-field-ref-sharing/"


def utilities():
    root = Path(__file__).resolve().parents[3]
    path = root / "docs/evidence/2026-10-17-profile-index-join/qualify_join.py"
    spec = importlib.util.spec_from_file_location("index_join_utilities", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    helper = module.utilities()
    assert helper.pin(path)["sha256"] == "c3d71a92e6db62102135da14c23004232b1ee4650d2aacc763e770a31cbe43ba"
    helper.verify_git(root, OBSERVER_EVIDENCE, {str(path.relative_to(root)): helper.pin(path)})
    return module, helper


def qualify(args, worker_module, helper):
    root, repo, work = args.observer_repo.resolve(), args.mesh_repo.resolve(), args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    mesh, observer = work / "mesh-30e2011", work / "observer-7e496b2"
    helper.export(repo, EVIDENCE, mesh)
    helper.export(root, OBSERVER_EVIDENCE, observer)
    mesh_inputs = helper.inventory(mesh, ("src", "tests", "scripts", "contracts"))
    owner_inputs = helper.inventory(observer, ("agent_observer", "tests"))
    helper.verify_git(repo, MESH, mesh_inputs)
    helper.verify_git(root, OBSERVER, owner_inputs)
    path = mesh / PREFIX / "receipt.json"
    assert helper.pin(path)["sha256"] == "87e6168181ff0dcbc703331af732d39eb7b0320b9169fc85ad6f3a208df54381"
    receipt = helper.read(path)
    for name, expected in receipt["artifacts"].items():
        assert helper.pin(mesh / name) == expected, name
    helper.verify_git(repo, EVIDENCE, receipt["artifacts"])
    saved = helper.read(mesh / PREFIX / receipt["inputs"])
    assert saved["inputs"] == dict(mesh=mesh_inputs, observer=owner_inputs)
    helper.verify_git(repo, saved["beforeRuntime"], saved["beforeInputs"])
    overlay = dict(saved["beforeInputs"])
    overlay["tests/test_sync_patch_workspace.py"] = mesh_inputs["tests/test_sync_patch_workspace.py"]
    assert saved["beforeOverlayInputs"] == overlay
    protected = saved["protectedInputs"]
    helper.verify_git(repo, MESH, protected)
    prior_mesh = mesh / receipt["upstream"]["mesh"]["path"]
    assert helper.pin(prior_mesh) == receipt["upstream"]["mesh"]["pin"]
    prior = helper.read(prior_mesh)
    for name, expected in prior["artifacts"].items():
        assert helper.pin(mesh / name) == expected, name
    helper.verify_git(repo, EVIDENCE, prior["artifacts"])
    for role in ("observer", "observerGroupJoin", "observerIndexJoin"):
        item = receipt["upstream"][role]
        assert helper.pin(observer / item["path"]) == item["pin"]
    helper.verify_git(repo, EVIDENCE, receipt["privateAuditScripts"])
    extra_mesh = receipt["privateAuditScripts"]

    def loaded(value, *, before=False):
        for name, digest in value["loadedInputs"].items():
            role, relative = name.split("/", 1)
            files = owner_inputs if role == "observer" else (overlay if before else mesh_inputs | extra_mesh)
            assert files[relative]["sha256"] == digest, name

    # These are read/hash checks of Mesh's saved execution, not new runs.
    for value in saved["before"].values():
        loaded(value, before=True)
        assert value["methods"] == 1 and value["failures"] == 2 and value["errors"] == value["skipped"] == 0
    for version in saved["focused"].values():
        for value in version.values():
            loaded(value)
            assert value["gcDisabled"] and value["failures"] == value["errors"] == value["skipped"] == 0
    for value in saved["capacity"].values():
        loaded(value)
        assert value["gcDisabled"] and value["finalCounters"] == [0] * 6
        if value["rows"] == 2000:
            assert (value["failure"]["stage"], value["failure"]["code"]) == ("baseline-admit", "sync_decoded_capacity")
        else:
            assert value["outcome"] == "baseline-and-two-generations-confirmed" and value["failure"] is None
    audit = helper.read(mesh / PREFIX / "results/profile-packed2000-314.json")
    loaded(audit)
    assert audit["finalCounters"] == [0] * 6
    assert all(all(amount == 0 for amount in row.values()) for row in audit["privateScalarAllocationAudit"]["finalTypes"].values())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    commands, results = [], {}
    lock_path = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
    with lock_path.open("a") as lock:
        print("Waiting for shared advisory lock; focused source tests only", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        for label, python in (("314", sys.executable), ("311", str(args.python311.absolute()))):
            for role, count in (("observer", 64), ("mesh", 72)):
                name = f"focused-{role}-{label}"
                path = work / f"{name}.json"
                argv = [python, "-B", str(Path(__file__).resolve()), "--worker", "--role", role,
                        "--mesh", str(mesh), "--observer", str(observer), "--output", str(path),
                        "--log", str(work / f"{name}.log")]
                with (work / f"{name}.stdout.log").open("x") as stream:
                    result = subprocess.run(argv, cwd=observer, env=env, stdout=stream, stderr=subprocess.STDOUT)
                commands.append(dict(argv=argv, cwd=str(observer), returncode=result.returncode))
                assert result.returncode == 0, name
                value = helper.read(path)
                loaded(value)
                assert value["tests"] == count and value["gcDisabled"]
                assert value["failures"] == value["errors"] == value["skips"] == 0
                results[name] = value
                print(f"Python {value['python']}:{role} {count} focused methods PASS", flush=True)
    assert helper.inventory(mesh, ("src", "tests", "scripts", "contracts")) == mesh_inputs
    assert helper.inventory(observer, ("agent_observer", "tests")) == owner_inputs
    helper.verify_git(repo, MESH, mesh_inputs)
    helper.verify_git(root, OBSERVER, owner_inputs)
    helper.write(work / "qualification.json", dict(
        status="Independent bounded focused compatibility PASS; capacity/audit verification only",
        meshRuntime=MESH, meshEvidence=EVIDENCE, observerRuntime=OBSERVER, observerEvidence=OBSERVER_EVIDENCE,
        meshInputs=mesh_inputs, observerInputs=owner_inputs, protectedInputs=protected,
        peerReceipt=receipt, peerReceiptPin=helper.pin(mesh / PREFIX / "receipt.json"),
        peerSavedCapacityReadOnly=saved["capacity"], peerSavedAuditReadOnly=audit,
        verifiedPeerArtifacts=len(receipt["artifacts"]), verifiedPriorMeshArtifacts=len(prior["artifacts"]),
        independentFocused=results, independentCapacityRerun=False, independentScalarAuditRerun=False,
        commands=commands, sharedLock=str(lock_path),
        scripts=dict(runner=helper.pin(Path(__file__)), worker=helper.pin(Path(worker_module.__file__)),
                     utility=helper.pin(Path(helper.__file__))),
        artifacts={path.name: helper.pin(path) for path in work.iterdir() if path.is_file()},
        exclusions=receipt["exclusions"], noProductionApiCapsSchemaIdVersionArtifactSelectionSiblingOrRolloutChange=True,
        oldCpuHardFailureUnchanged=True, gitCleanup="HOLD"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--role", choices=("observer", "mesh"))
    for name in ("observer-repo", "mesh-repo", "python311", "mesh", "observer", "log"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    worker_module, helper = utilities()
    if args.worker:
        worker_module.worker(args, helper)
    else:
        assert args.observer_repo and args.mesh_repo and args.python311
        qualify(args, worker_module, helper)


if __name__ == "__main__":
    main()
