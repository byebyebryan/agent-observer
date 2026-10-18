"""Verify saved resource evidence without rerunning the source matrix."""

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports/final-bb7b8aab"
REVISION = "bb7b8aab91574fc3a325325ac8debf21b525712a"
LIMIT = 64 * 1024 * 1024
RSS_KEYS = {"rssCurrentKiB", "processRssHighWaterKiB"}


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text())


def normalize(value):
    """Keep resource/semantic fields while removing disclosed process metadata."""
    if isinstance(value, dict):
        omitted = RSS_KEYS | {
            "pythonVersion", "pythonEntrypoint", "pythonExecutableDiagnostic",
        }
        return {key: normalize(item) for key, item in value.items() if key not in omitted}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def main():
    summary_path = REPORTS / "summary.json"
    summary = read_json(summary_path)
    check(summary["sourceRevision"] == REVISION, "summary_source_revision")
    check(summary["failureCount"] == 0 and not summary["failures"], "summary_failures")
    check(summary["caseCount"] == summary["plannedCaseCount"] == 22, "case_count")
    check(summary["runnerSha256"] == sha256((HERE / "run_matrix.py").read_bytes()), "driver_hash")
    case_runner_hash = sha256((HERE / "resource_case.py").read_bytes())
    check(summary["caseRunnerSha256"] == case_runner_hash, "case_runner_hash")
    source_pins, artifacts, grouped = {}, {}, {}
    outcomes = Counter()
    peak_charge = peak_request = peak_unique = peak_overlap = peak_input = 0
    evictions = peer_drops = point_count = 0

    for entry in summary["cases"]:
        path = REPORTS / entry["report"]
        log_path = REPORTS / entry["log"]
        for artifact, expected in ((path, entry["reportSha256"]), (log_path, entry["logSha256"])):
            actual = sha256(artifact.read_bytes())
            check(actual == expected, f"artifact_hash:{artifact.name}")
            artifacts[str(artifact.relative_to(HERE))] = actual
        report, log = read_json(path), read_json(log_path)
        check(log["exitCode"] == 0 and log["stderr"] == "", f"child_failure:{path.name}")
        check(report["sourceRevision"] == REVISION, f"report_source:{path.name}")
        check(not report["gcEnabled"] and not report["failures"], f"case_failure:{path.name}")
        check(not report["meshImports"] and report["runtime"]["workersStarted"] == 0, "scope")
        check(report["runtime"]["encodedLimitBytes"] == LIMIT, "encoded_limit")
        check(report["runtime"]["maxClients"] == 16, "client_limit")
        check(report["runtime"]["runtimePeerCountAtPeak"] == 15, "peer_count")
        check(report["refusedReservationCount"] == 0, "unexpected_stage_refusal")
        check(entry["caseStatus"] == report["caseStatus"], "case_status")
        outcomes[report["caseStatus"]] += 1
        check(len(report["generations"]) == 3, "generation_count")
        for index, generation in enumerate(report["generations"]):
            check(generation["providerRuntimeAccepted"] == index + 1, "accepted_sequence")
            check(generation["providerRuntimeHealth"] == "current", "runtime_health")
            peak_input = max(peak_input, generation["inputSnapshotBytes"])
            if report["caseStatus"] == "complete":
                check(generation["coverageStatus"] == "complete", "complete_scope")
                check(generation["exactMembershipWhenComplete"] is True, "membership")
                check(generation["originalFullDtoEqualityWhenComplete"] is True, "dto_equality")
            else:
                check(generation["capacityOutcome"] == "projection_tracking_capacity", "refusal_reason")
        for point in report["counterPoints"]:
            point_count += 1
            charge = point["runtimeEncodedBytes"]
            check(charge == point["manualChargedBytes"] <= LIMIT, "counter_equation")
            check(point["roleByteSum"] == sum(point["uniqueBufferBytesByRole"].values()), "role_sum")
            check(point["roleByteSum"] - point["roleOverlapBytes"] == point["uniqueBufferBytes"], "overlap")
            check(point["uniqueBufferBytes"] <= charge, "unique_exceeds_charge")
            check(point["pinnedPeerBodyAliasesMatchCache"] is True, "pin_alias")
            peak_charge = max(peak_charge, charge)
            peak_unique = max(peak_unique, point["uniqueBufferBytes"])
            peak_overlap = max(peak_overlap, point["roleOverlapBytes"])
        check(report["encodedCounterHighWaterBytes"] == max(
            point["runtimeEncodedBytes"] for point in report["counterPoints"]
        ), "charge_high_water")
        for reservation in report["reservations"]:
            requested = reservation["currentBytesBefore"] + reservation["worstCaseAdditionalBytes"]
            check(requested == reservation["requestedCurrentPlusAdditionalBytes"], "reservation_request")
            admitted = reservation["currentBytesAfterRoom"] + reservation["worstCaseAdditionalBytes"]
            check(reservation["admitted"] is True, "reservation_refusal")
            check(admitted == reservation["admittedCurrentPlusAdditionalBytes"] <= LIMIT, "reservation_admission")
            peak_request = max(peak_request, requested)
        cleanup = report["cleanup"]
        for key in ("runtimePeersAfterCleanup", "runtimeBodiesAfterCleanup", "runtimeLatestAfterCleanup",
                    "peerBodyPinsRetainedAfterCleanup", "peerFragmentPartsRetainedAfterCleanup"):
            check(cleanup[key] == 0, f"cleanup:{key}")
        for key in ("workingSetReserverRemoved", "peerSocketsClosed", "receiverSocketsAllClosed", "selectorClosed"):
            check(cleanup[key] is True, f"cleanup:{key}")
        check(cleanup["runtimeEncodedBytesAfterCleanup"] == sum(
            item["bytes"] for item in cleanup["ownerBuffersRetainedAfterCleanup"]
        ), "live_owner_cleanup")
        evictions += report["observedCacheEvictionCount"]
        peer_drops += report["observedRuntimePeerDropCount"]
        for name, digest in report["sourceFilesSha256"].items():
            check(source_pins.get(name, digest) == digest, f"source_drift:{name}")
            source_pins[name] = digest
        case = report["case"]
        grouped.setdefault((case["rows"], case["mix"], case["fields"]), []).append(report)

    for key, pair in grouped.items():
        check(len(pair) == 2 and normalize(pair[0]) == normalize(pair[1]), f"interpreter_difference:{key}")
    for name, digest in source_pins.items():
        if name == "resource-source/resource_case.py":
            check(digest == case_runner_hash, "loaded_runner_hash")
            continue
        blob = subprocess.run(["git", "show", f"{REVISION}:{name}"], cwd=ROOT,
                              check=True, capture_output=True).stdout
        check(sha256(blob) == digest, f"loaded_git_blob:{name}")
        check(sha256((ROOT / name).read_bytes()) == digest, f"current_source_drift:{name}")

    print(json.dumps({
        "scope": "primary review of saved source matrix; no matrix, CPU or native replay",
        "sourceRevision": REVISION,
        "summarySha256": sha256(summary_path.read_bytes()),
        "verifierSha256": sha256(Path(__file__).read_bytes()),
        "artifactsSha256": artifacts,
        "sourceFilesSha256": source_pins,
        "loadedGitInputCount": len(source_pins) - 1,
        "cases": sum(outcomes.values()),
        "selectionOutcomes": dict(sorted(outcomes.items())),
        "matchingInterpreterPairs": len(grouped),
        "verifiedCounterPoints": point_count,
        "peakEncodedChargeBytes": peak_charge,
        "peakRequestedCurrentPlusStageBytes": peak_request,
        "peakUniqueBufferBytes": peak_unique,
        "peakRoleOverlapBytes": peak_overlap,
        "peakNativeInputBytes": peak_input,
        "observedCacheEvictions": evictions,
        "observedPeerDrops": peer_drops,
        "limitations": [
            "saved object-identity inventory checked in case runner, not reconstructed from raw buffers",
            "tracking refusals do not qualify a complete selected set",
            "no heap/RSS, SDK, native provider, deployment or producer acceptance",
        ],
        "failures": [],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
