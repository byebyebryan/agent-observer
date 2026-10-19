"""Verify saved checkpoint evidence without rerunning source experiments."""

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent.parent
REVISION = "610afaac658903ddd6c466c793f9856b45e9f03e"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def raw_report(path):
    return path.read_bytes() if path.exists() else gzip.decompress(
        path.with_suffix(path.suffix + ".gz").read_bytes()
    )


def load(path):
    return json.loads(raw_report(path))


def git_pin(path, expected):
    raw = subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=ROOT)
    assert sha(raw) == expected, path
    assert sha((ROOT / path).read_bytes()) == expected, path


def inventory(value):
    if isinstance(value, list):
        return sum(inventory(item) for item in value)
    if not isinstance(value, dict):
        return 0
    count = 0
    if "uniqueBuffers" in value:
        buffers = value["uniqueBuffers"]
        unique = sum(item["bytes"] for item in buffers)
        roles = {}
        for item in buffers:
            for role in {name.split(".", 1)[0] for name in item["roles"]}:
                roles[role] = roles.get(role, 0) + item["bytes"]
        assert unique == value["uniqueBufferBytes"]
        assert roles == value["uniqueBufferBytesByRole"]
        assert sum(roles.values()) - unique == value["roleOverlapBytes"]
        charge = (
            value["syncEncodedBytes"] + roles.get("owner", 0)
            + sum(item["bytes"] for item in value["bodyCache"])
            + value["roleReferences"].get("peer", {}).get("referenceBytes", 0)
            - sum(item["bytes"] for item in value["peerBodyAliases"])
        )
        assert charge == value["manualChargeBytes"] == value["runtimeEncodedBytes"]
        assert unique <= charge <= value["encodedLimitBytes"] == 67_108_864
        assert all(item["matchesCacheObject"] for item in value["peerBodyAliases"])
        count = 1
    return count + sum(inventory(item) for item in value.values())


def pressure():
    base = BASE / "resource-pressure"
    storage = load(base / "storage.json")
    for entry in storage["files"]:
        packed = (base / entry["storedPath"]).read_bytes()
        raw = gzip.decompress(packed)
        assert sha(packed) == entry["storedSha256"]
        assert sha(raw) == entry["rawSha256"]
        assert len(raw) == entry["rawBytes"]
    summaries = sorted((base / "reports").glob("*/summary.json"))
    for path in summaries:
        for case in load(path)["cases"]:
            for name in ("report", "log"):
                if case.get(name):
                    assert sha(raw_report(path.parent / case[name])) == case[name + "Sha256"]
    summary = load(base / "reports/final6-610afaac/summary.json")
    assert summary["failureCount"] == 0 and summary["crossInterpreterNormalizedParity"]
    assert sha((base / "pressure_case.py").read_bytes()) == summary["caseRunnerSha256"]
    assert sha((base / "run_pressure.py").read_bytes()) == summary["runnerSha256"]
    checked = []
    for case in summary["cases"]:
        report = load(base / "reports/final6-610afaac" / case["report"])
        assert not report["gcEnabled"] and not report["failures"]
        pins = report["sourceFilesSha256"]
        for path, digest in pins.items():
            if path.startswith("resource-pressure/"):
                assert sha((BASE / path).read_bytes()) == digest
            else:
                git_pin(path, digest)
        assert len(report["counterInventories"]) == 420
        count = inventory(report)
        reservations = report["reservationEvents"]
        assert len(reservations) == 14
        assert sum(event["currentPlusAdditionalBeforeBytes"] > 67_108_864
                   for event in reservations) == 2
        for event in reservations:
            assert event["admitted"] and event["fitsAfterRoom"]
            assert event["currentPlusAdditionalAfterBytes"] <= 67_108_864
        assert [event["peer"] for event in report["dropEvents"]] == [
            "full_slow_00", "full_slow_01"
        ]
        for event in report["dropEvents"]:
            assert event["peerPartsRetainedBySourceDrop"]
            assert event["wasOldestWriteStartedCandidate"]
            assert not event["peerObjectAliveAfterRoomReturn"]
            assert event["peerPartBytesAfterRoomReturn"] == 0
        assert len(report["generations"]) == 14
        for generation in report["generations"]:
            assert [generation[key]["rowCount"] for key in ("full", "active", "workingSet")] == [2000, 10, 20]
            assert all(generation["fullHealthyReader"][key] for key in (
                "dtoMatchesDirectFrame", "peerRemainedLive", "streamGuardAccepted",
                "wireDigestMatchesQueuedParts",
            ))
            for sibling in generation["healthySiblingReaders"].values():
                assert sibling["peerRemainedLive"] and sibling["streamGuardAccepted"]
                assert sibling["wireDigestMatchesQueuedParts"]
        cleanup = report["cleanup"]
        assert cleanup["allReceiverSocketsClosed"] and cleanup["allSenderSocketsClosed"]
        assert cleanup["runtimePeersAfterCleanup"] == cleanup["runtimeBodiesAfterCleanup"] == 0
        assert cleanup["runtimeEncodedBytesAfterCleanup"] == 134_521
        checked.append({"python": report["pythonVersion"], "gitPins": len(pins) - 2,
                        "inventoryEquationsCheckedIncludingNestedCopies": count})
    return {"reports": checked, "losslessCompressedReports": len(storage["files"]),
            "historicalSummariesHashChecked": len(summaries)}


def small_reports(folder, prefix, runner):
    reports = []
    for version in ("314", "311"):
        report = load(BASE / folder / f"{prefix}-{version}.json")
        assert not report["gcEnabled"] and report["sourceRevision"] == REVISION
        assert sha((BASE / folder / runner).read_bytes()) == report["runnerSha256"]
        for entry in report["loaded"].values():
            git_pin(entry["path"], entry["sha256"])
        reports.append(report)
    return reports


def main():
    result = {"schema": "working-set-review-checkpoint-verification-v1",
              "sourceRevision": REVISION, "scope": "Saved bytes, Git pins and scalar equations only; no experiment, model, CPU, native or SDK replay."}
    result["pressure"] = pressure()
    wires = small_reports("wire-density-source", "wire", "run_wire_density.py")
    assert wires[0]["results"] == wires[1]["results"]
    for case in wires[0]["results"]:
        assert case["selectedBodyRatio"] == case["selectedOriginalRowBytes"] / case["fullOriginalRowBytes"]
        if case["complete"]:
            assert abs(case["byteReductionPercent"] - 100 * (1 - case["workingNativeFrameBytes"] / case["fullNativeFrameBytes"])) < 1e-9
        else:
            assert case["reason"] == "projection_tracking_capacity"
            assert case["byteReductionPercent"] is None
    models = small_reports("support-density-model", "support-density", "run_support_density.py")
    for model, wire in zip(models, wires, strict=True):
        for case in model["results"]:
            old = next(item for item in wire["results"] if (item["rows"], item["selectedRows"]) == (case["rows"], case["selectedRows"]))
            assert case["inputSha256"] == old["inputSha256"]
            assert case["workingNativeFrameBytesWithLf"] == old["workingNativeFrameBytes"]
            if case["coverage"] == "complete":
                scope = case["scope"]
                assert scope["roundTripObjectEqual"] and scope["roundTripCanonicalBytesEqual"]
                assert all(item["rejected"] for item in scope["modelRejectVectors"])
                assert len(scope["modelRejectVectors"]) == 6
                assert case["workingNativeFrameBytesWithLf"] - scope["modeledWholeNativeFrameBytesWithLf"] == scope["scopeByteDelta"]
            else:
                assert not case["hypotheticalFullSelectedScope"]["constructed"]
                assert case["preFailureLocals"]["candidateTrackingCapacityAlreadyExceeded"]
    result["wireCasesPerInterpreter"] = len(wires[0]["results"])
    result["modelCasesPerInterpreter"] = len(models[0]["results"])
    result["wireAndModelLoadedGitPinsPerInterpreter"] = len(wires[0]["loaded"])
    result["status"] = "PASS"
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
