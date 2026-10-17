"""Verify exact source/test pins and bind the index-workspace join evidence."""

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here, root = Path(__file__).resolve().parent, Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("index_join_runner", here / "qualify_join.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    helper, work = runner.utilities(), args.output.resolve()
    report = helper.read(work / "qualification.json")
    assert (report["observerRuntime"], report["meshRuntime"], report["meshEvidence"]) == (
        runner.OBSERVER, runner.MESH, runner.EVIDENCE)
    assert report["scripts"] == dict(runner=helper.pin(here / "qualify_join.py"), utility=helper.pin(Path(helper.__file__)))
    mesh, observer = work / "mesh-103f3b3", work / "observer-b6ce842"
    repo = Path("/home/bryan/code/mesh-plus")
    helper.verify_git(root, runner.OBSERVER, report["observerInputs"])
    helper.verify_git(repo, runner.MESH, report["meshInputs"])
    helper.verify_git(repo, runner.MESH, report["protectedInputs"])
    assert helper.inventory(root, ("agent_observer", "tests")) == report["observerInputs"]
    assert helper.inventory(observer, ("agent_observer", "tests")) == report["observerInputs"]
    assert helper.inventory(mesh, ("src", "tests", "scripts", "contracts")) == report["meshInputs"]
    for name, expected in report["artifacts"].items():
        assert helper.pin(work / name) == expected, name
    for prefix, upstream in report["upstream"].items():
        assert helper.pin(mesh / prefix / "receipt.json") == upstream["receipt"]
        for name, expected in upstream["artifacts"].items():
            assert helper.pin(mesh / name) == expected, name

    def loaded(value):
        for name, expected in value["loadedInputs"].items():
            role, relative = name.split("/", 1)
            source = report["observerInputs"] if role == "observer" else report["meshInputs"] | report["originalProbe"]
            assert source[relative]["sha256"] == expected, name

    assert len(report["focused"]) == 4
    for value in report["focused"].values():
        loaded(value)
        assert value["gcDisabled"] and value["tests"] == (64 if value["role"] == "observer" else 68)
        assert value["failures"] == value["errors"] == value["skips"] == 0
    successes, failures = [], {}
    assert len(report["capacity"]) == 12
    for name, value in report["capacity"].items():
        loaded(value)
        assert value["gcDisabled"] and value["finalCounters"] == [0] * 6
        assert value["heapPeak"] <= 67108864 and value["encodedPeakReservedBound"] <= 33554432
        if value["failure"] is None:
            assert value["outcome"] == "baseline-and-two-generations-confirmed"
            successes.append(name)
        else:
            assert value["rows"] == 2000 and value["failure"]["code"] == "sync_decoded_capacity"
            failures[name] = value["failure"]
    prior_path = root / "docs/evidence/2026-10-17-profile-group-join/receipt.json"
    assert helper.pin(prior_path)["sha256"] == "97a67e444ebc290ad0555542464b5177167f835119f773a63122261b30b00f88"
    prior = helper.read(prior_path)
    for name, expected in prior["artifacts"].items():
        assert helper.pin(root / name) == expected, name
    canonical, path = None, work / "canonical314.log"
    if path.exists():
        text = path.read_text()
        assert "\nRan 947 tests " in text and "\nOK\n" in text and "skipped=" not in text
        assert "PASS: 203 Markdown files" in text
        canonical = dict(tests=947, skips=0, markdownFiles=203, artifact=helper.pin(path))
    receipt = dict(
        status="Bounded source join only; outcomes do not grant producer acceptance",
        qualification=report, canonical=canonical, successes=successes, refusals=failures,
        sourceCounts=dict(observer=len(report["observerInputs"]), mesh=len(report["meshInputs"]), protected=len(report["protectedInputs"])),
        upstreamArtifactsVerified=sum(len(value["artifacts"]) for value in report["upstream"].values()),
        priorJoin=dict(receipt=helper.pin(prior_path), unchangedArtifactsVerified=len(prior["artifacts"])),
        guide=helper.pin(here / "README.md"), scripts={path.name: helper.pin(path) for path in here.glob("*.py")},
        artifacts={str(path.relative_to(root)): helper.pin(path) for path in work.iterdir() if path.is_file()},
        exclusions=report["exclusions"], oldCpuHardFailureUnchanged=True,
        noProductionAbiCapsSchemaIdVersionArtifactSelectionSiblingOrRolloutChange=True, gitCleanup="HOLD")
    target = here / "receipt.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(receipt=helper.pin(target), canonical=canonical, sourceCounts=receipt["sourceCounts"],
                         successes=successes, refusals=failures), indent=2))


if __name__ == "__main__":
    main()
