"""Verify and seal bounded compatibility, keeping saved capacity unexecuted."""

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here, root = Path(__file__).resolve().parent, Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("field_compat_runner", here / "qualify_compatibility.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    worker, helper = runner.utilities()
    work = args.output.resolve()
    data = helper.read(work / "qualification.json")
    assert (data["meshRuntime"], data["meshEvidence"], data["observerRuntime"]) == (runner.MESH, runner.EVIDENCE, runner.OBSERVER)
    assert data["scripts"] == dict(runner=helper.pin(here / "qualify_compatibility.py"),
                                   worker=helper.pin(Path(worker.__file__)), utility=helper.pin(Path(helper.__file__)))
    mesh, observer = work / "mesh-30e2011", work / "observer-7e496b2"
    repo = Path("/home/bryan/code/mesh-plus")
    helper.verify_git(repo, runner.MESH, data["meshInputs"])
    helper.verify_git(root, runner.OBSERVER, data["observerInputs"])
    helper.verify_git(repo, runner.MESH, data["protectedInputs"])
    assert helper.inventory(mesh, ("src", "tests", "scripts", "contracts")) == data["meshInputs"]
    assert helper.inventory(observer, ("agent_observer", "tests")) == data["observerInputs"]
    assert helper.inventory(root, ("agent_observer", "tests")) == data["observerInputs"]
    for name, expected in data["artifacts"].items():
        assert helper.pin(work / name) == expected, name
    assert data["peerReceiptPin"] == helper.pin(mesh / runner.PREFIX / "receipt.json")
    for name, expected in data["peerReceipt"]["artifacts"].items():
        assert helper.pin(mesh / name) == expected, name
    assert not data["independentCapacityRerun"] and not data["independentScalarAuditRerun"]
    assert len(data["independentFocused"]) == 4
    for value in data["independentFocused"].values():
        assert value["gcDisabled"] and value["tests"] == (64 if value["role"] == "observer" else 72)
        assert value["failures"] == value["errors"] == value["skips"] == 0
        for name, expected in value["loadedInputs"].items():
            role, relative = name.split("/", 1)
            files = data["observerInputs"] if role == "observer" else data["meshInputs"]
            assert files[relative]["sha256"] == expected, name
    canonical, path = None, work / "canonical314.log"
    if path.exists():
        text = path.read_text()
        assert "\nRan 947 tests " in text and "\nOK\n" in text and "skipped=" not in text
        assert "PASS: 204 Markdown files" in text
        canonical = dict(tests=947, skips=0, markdownFiles=204, artifact=helper.pin(path))
    receipt = dict(
        status="Independent focused source compatibility PASS; capacity/audit read-hash verification only",
        qualification=data, canonical=canonical,
        sourceCounts=dict(mesh=len(data["meshInputs"]), observer=len(data["observerInputs"]), protected=len(data["protectedInputs"])),
        guide=helper.pin(here / "README.md"), scripts={path.name: helper.pin(path) for path in here.glob("*.py")},
        artifacts={str(path.relative_to(root)): helper.pin(path) for path in work.iterdir() if path.is_file()},
        independentCapacityRerun=False, independentScalarAuditRerun=False,
        exclusions=data["exclusions"], oldCpuAndCapacityFailuresUnchanged=True,
        noProductionApiCapsSchemaIdVersionArtifactSelectionSiblingOrRolloutChange=True, gitCleanup="HOLD")
    target = here / "receipt.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(receipt=helper.pin(target), canonical=canonical, sourceCounts=receipt["sourceCounts"]), indent=2))


if __name__ == "__main__":
    main()
