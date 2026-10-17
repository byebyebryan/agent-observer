"""Verify the joined source reports and bind their exact bytes into one receipt."""

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here, root = Path(__file__).resolve().parent, Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("join_qualifier", here / "qualify_join.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    work = args.output.resolve()
    mesh, observer = work / "mesh-2385712", work / "observer-b6ce842"
    repo = Path("/home/bryan/code/mesh-plus")
    report = helper.read(work / "qualification.json")
    assert (report["observer"], report["meshRuntime"], report["meshEvidence"]) == (
        helper.OBSERVER, helper.MESH_RUNTIME, helper.MESH_EVIDENCE)
    assert report["runner"] == helper.pin(here / "qualify_join.py")
    observer_inputs, mesh_inputs = report["observerInputs"], report["meshInputs"]
    helper.verify_git(root, helper.OBSERVER, observer_inputs)
    helper.verify_git(repo, helper.MESH_RUNTIME, mesh_inputs)
    helper.verify_git(repo, helper.MESH_RUNTIME, report["protectedInputs"])
    assert helper.inventory(observer, ("agent_observer", "tests")) == observer_inputs
    assert helper.inventory(mesh, ("src", "tests", "scripts", "contracts")) == mesh_inputs
    assert helper.inventory(root, ("agent_observer", "tests")) == observer_inputs
    for prefix, upstream in report["upstream"].items():
        assert helper.pin(mesh / prefix / "receipt.json") == upstream["receipt"]
        for name, expected in upstream["artifacts"].items():
            assert helper.pin(mesh / name) == expected, name
    for name, expected in report["artifacts"].items():
        assert helper.pin(work / name) == expected, name

    extra_mesh = {helper.PREFIX + name: helper.pin(mesh / helper.PREFIX / name)
                  for name in ("probe_reader_intake.py", "profile_intake.py")}
    helper.verify_git(repo, helper.MESH_EVIDENCE, extra_mesh)

    def loaded(value):
        for name, expected in value["loadedInputs"].items():
            role, relative = name.split("/", 1)
            source = observer_inputs if role == "observer" else mesh_inputs | extra_mesh
            assert source[relative]["sha256"] == expected, name

    for value in report["focused"].values():
        loaded(value)
        assert value["gcDisabled"] and value["tests"] == 93
        assert value["failures"] == value["errors"] == value["skips"] == 0
    assert len(report["capacity"]) == 12
    for value in report["capacity"].values():
        loaded(value)
        assert value["gcDisabled"] and value["finalCounters"] == [0] * 6
        if value["rows"] == 2000:
            assert (value["failure"]["stage"], value["failure"]["code"]) == ("baseline-admit", "sync_decoded_capacity")
        else:
            assert value["outcome"] == "baseline-and-two-generations-confirmed" and value["failure"] is None
    audits = {name: helper.read(work / name) for name in (
        "refusal-packed2000-314.json", "audit-packed2000-314.json", "ledger-refusal-packed2000-314.json")}
    for value in audits.values():
        loaded(value)
        assert value["gcDisabled"] and value["finalCounters"] == [0] * 6
    assert audits["refusal-packed2000-314.json"]["privateScalarChargeRefusals"] == []
    audit = audits["audit-packed2000-314.json"]["privateScalarAllocationAudit"]
    assert all(all(amount == 0 for amount in row.values()) for row in audit["finalTypes"].values())
    event, = audits["ledger-refusal-packed2000-314.json"]["privateScalarLedgerRefusals"]
    assert event["operation"] == "reserve" and event["amount"] == 1050528
    assert event["ledger"]["decodedBytes"] + event["ledger"]["reservedBytes"] + event["amount"] > 67108864
    canonical = None
    canonical_path = work / "canonical314.log"
    if canonical_path.exists():
        text = canonical_path.read_text()
        assert "\nRan 947 tests " in text and "\nOK\n" in text and "skipped=" not in text
        assert "PASS: 201 Markdown files" in text
        canonical = dict(tests=947, skips=0, markdownFiles=201, artifact=helper.pin(canonical_path))
    diagnostics = {str(path.relative_to(root)): helper.pin(path)
                   for path in (root / ".cache/profile-phase-join-20261017").iterdir() if path.is_file()}
    artifacts = {str(path.relative_to(root)): helper.pin(path) for path in work.iterdir() if path.is_file()}
    receipt = dict(
        status="Bounded source compatibility PASS; 2000baseline capacity FAIL, producer gates OPEN",
        qualification=report, scalarAudits=audits, canonical=canonical,
        guide=helper.pin(here / "README.md"), scripts={path.name: helper.pin(path) for path in here.glob("*.py")},
        artifacts=artifacts, initialHarnessDiagnosticArtifacts=diagnostics,
        sourceCounts=dict(observer=len(observer_inputs), mesh=len(mesh_inputs), protected=len(report["protectedInputs"])),
        upstreamArtifactCount=sum(len(value["artifacts"]) for value in report["upstream"].values()),
        diagnostics=["Initial module-name collision:74passing Observer tests; count assertion stopped before any capacity case.",
                     "Two Python3.11 dependency import failures preceded tests because the harness resolved the venv launcher symlink. Retaining the launcher path corrected setup; no producer defect.",
                     "Completed Python3.14 reports verified and reused without rerunning. Initial diagnostics remain separate and unchanged."],
        exclusions=report["exclusions"], noProductionAbiCapsSchemaIdVersionArtifactSelectionSiblingOrRolloutChange=True,
        oldCpuHardFailureUnchanged=True, gitCleanup="HOLD")
    target = here / "receipt.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(receipt=helper.pin(target), canonical=canonical,
                         sourceCounts=receipt["sourceCounts"], upstreamArtifacts=receipt["upstreamArtifactCount"],
                         failedRetains=audit["failedRetains"], refusedReserve=event), indent=2))


if __name__ == "__main__":
    main()
