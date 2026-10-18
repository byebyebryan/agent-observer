"""Run the bounded synthetic resource cases in fresh 3.14 and 3.11 processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DEFAULT = Path(__file__).resolve().parents[4]
CASE_SCRIPT = Path(__file__).resolve().with_name("resource_case.py")
PYTHON_314 = "/home/bryan/code/mesh-plus/.venv/bin/python"
PYTHON_311 = "/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"
SOURCE_REVISION = "bb7b8aab91574fc3a325325ac8debf21b525712a"


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=CASE_SCRIPT.parent / "reports")
    parser.add_argument("--source-revision", default=SOURCE_REVISION)
    parser.add_argument("--python314", default=PYTHON_314)
    parser.add_argument("--python311", default=PYTHON_311)
    parser.add_argument("--rows", type=int, nargs="+", choices=(100, 500, 2000), default=(100, 500, 2000))
    parser.add_argument("--mixes", nargs="+", choices=("small", "quarter", "burst"), default=("small", "quarter", "burst"))
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if next(output_dir.iterdir(), None) is not None:
        raise FileExistsError(f"resource_output_dir_not_empty:{output_dir}")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    entries = []
    failures = []
    variants = (("py314", args.python314, "3.14."), ("py311", args.python311, "3.11."))
    cases = [(rows, mix, "ordinary") for rows in args.rows for mix in args.mixes]
    # A separate upper-size fixture retains ordinary fields and lengthens only
    # title and cwd. It stays below the frozen native snapshot limit.
    cases.extend((2000, mix, "long-title-cwd") for mix in ("small", "quarter"))

    for variant, interpreter, expected_version in variants:
        for rows, mix, fields in cases:
            stem = f"{variant}-n{rows}-{mix}-{fields}"
            report_path = output_dir / f"{stem}.json"
            log_path = output_dir / f"{stem}.log"
            command = [
                interpreter,
                "-B",
                str(CASE_SCRIPT),
                str(root),
                str(report_path),
                "--source-revision",
                args.source_revision,
                "--python-entrypoint",
                interpreter,
                "--rows",
                str(rows),
                "--mix",
                mix,
                "--fields",
                fields,
            ]
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            log = {
                "case": stem,
                "command": command,
                "exitCode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            log_path.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n")
            report = None
            if report_path.is_file():
                report = json.loads(report_path.read_text())
            if completed.returncode != 0:
                failures.append(f"{stem}:child_exit_{completed.returncode}")
            if report is None:
                failures.append(f"{stem}:report_missing")
            else:
                if not report["pythonVersion"].startswith(expected_version):
                    failures.append(f"{stem}:unexpected_python_version")
                if report["sourceRevision"] != args.source_revision:
                    failures.append(f"{stem}:source_revision_mismatch")
                if report["caseStatus"] not in {"complete", "explicit_bounded_refusal"}:
                    failures.append(f"{stem}:unexpected_case_status")
                if not is_sha256(report["case"].get("initialInputSha256")):
                    failures.append(f"{stem}:initial_input_digest_missing")
                if any(
                    not is_sha256(generation.get("inputSnapshotSha256"))
                    for generation in report["generations"]
                ):
                    failures.append(f"{stem}:accepted_input_digest_missing")
                if report["gcEnabled"]:
                    failures.append(f"{stem}:garbage_collection_enabled")
                if not report["allActualCountersWithinDefaultLimit"]:
                    failures.append(f"{stem}:encoded_counter_limit")
                if not report["allAdmittedReservationsWithinDefaultLimit"]:
                    failures.append(f"{stem}:reservation_limit")
                if report["runtime"]["runtimePeerCountAtPeak"] > 16:
                    failures.append(f"{stem}:peer_limit")
                if report["meshImports"]:
                    failures.append(f"{stem}:mesh_import")
                if not report["allCountersMatchConservativeRoleCharge"]:
                    failures.append(f"{stem}:role_inventory_mismatch")
                if any(
                    not point["uniqueBufferBytesWithinConservativeCharge"]
                    or not point["pinnedPeerBodyAliasesMatchCache"]
                    for point in report["counterPoints"]
                ):
                    failures.append(f"{stem}:body_alias_accounting")
                if report["runtime"]["workersStarted"] != 0:
                    failures.append(f"{stem}:worker_started")
                if report["cleanup"]["runtimePeersAfterCleanup"] != 0:
                    failures.append(f"{stem}:peer_cleanup")
                if report["cleanup"]["runtimeBodiesAfterCleanup"] != 0:
                    failures.append(f"{stem}:body_cache_cleanup")
                if report["cleanup"]["peerFragmentPartsRetainedAfterCleanup"] != 0:
                    failures.append(f"{stem}:peer_fragment_cleanup")
                if len(report["generations"]) != 3 or any(
                    generation["providerRuntimeHealth"] != "current"
                    or generation["providerRuntimeAccepted"] != index + 1
                    for index, generation in enumerate(report["generations"])
                ):
                    failures.append(f"{stem}:accepted_generation_sequence")
                entries.append({
                    "case": stem,
                    "report": report_path.name,
                    "reportSha256": digest_file(report_path),
                    "log": log_path.name,
                    "logSha256": digest_file(log_path),
                    "caseStatus": report["caseStatus"],
                    "outcomes": report["outcomes"],
                    "encodedCounterHighWaterBytes": report["encodedCounterHighWaterBytes"],
                    "admittedReservationHighWaterBytes": report["admittedReservationHighWaterBytes"],
                    "refusedReservationCount": report["refusedReservationCount"],
                    "nativeSnapshotHighWaterBytes": max(
                        generation["inputSnapshotBytes"] for generation in report["generations"]
                    ),
                    "initialInputSha256": report["case"]["initialInputSha256"],
                    "acceptedInputSnapshotSha256s": [
                        generation["inputSnapshotSha256"]
                        for generation in report["generations"]
                    ],
                    "pythonVersion": report["pythonVersion"],
                    "sourceRevision": report["sourceRevision"],
                })

    summary = {
        "schema": "working-set-resource-source-matrix-v1",
        "sourceRevision": args.source_revision,
        "root": str(root),
        "runnerSha256": digest_file(Path(__file__).resolve()),
        "caseRunnerSha256": digest_file(CASE_SCRIPT),
        "pythonEntrypoints": {name: interpreter for name, interpreter, _version in variants},
        "caseCount": len(entries),
        "plannedCaseCount": len(variants) * len(cases),
        "allPlannedCasesProducedReports": len(entries) == len(variants) * len(cases),
        "failureCount": len(failures),
        "failures": failures,
        "cases": entries,
        "scope": "serial fresh-process synthetic source resource qualification; not a CPU, heap/RSS, provider, service, Mesh, SDK, network, delta, or production qualification",
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "summary": str(summary_path),
        "caseCount": summary["caseCount"],
        "plannedCaseCount": summary["plannedCaseCount"],
        "failureCount": summary["failureCount"],
        "sourceRevision": args.source_revision,
    }, sort_keys=True))
    if failures:
        raise SystemExit("resource_matrix_failures:" + ",".join(failures))


if __name__ == "__main__":
    main()
