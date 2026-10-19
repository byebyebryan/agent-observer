"""Run the slow-reader pressure case in fresh pinned Python processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT_DEFAULT = Path(__file__).resolve().parents[4]
CASE_SCRIPT = Path(__file__).resolve().with_name("pressure_case.py")
PYTHON_314 = "/home/bryan/code/mesh-plus/.venv/bin/python"
PYTHON_311 = "/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"
SOURCE_REVISION = "610afaac658903ddd6c466c793f9856b45e9f03e"
RUNTIME_SOURCE_REVISION = "bb7b8aab91574fc3a325325ac8debf21b525712a"
COMPARISON_OMIT_KEYS = {
    "pythonVersion",
    "pythonEntrypoint",
    "pythonExecutableDiagnostic",
    "rssCurrentKiB",
    "processRssHighWaterKiB",
    # ServiceState assigns fresh UUID collection IDs and real wall samples;
    # the per-run route oracle independently checks each cached payload hash.
    "bodySha256",
}


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=CASE_SCRIPT.parent / "reports" / f"final-{SOURCE_REVISION[:8]}",
    )
    parser.add_argument("--source-revision", default=SOURCE_REVISION)
    parser.add_argument("--runtime-source-revision", default=RUNTIME_SOURCE_REVISION)
    parser.add_argument("--python314", default=PYTHON_314)
    parser.add_argument("--python311", default=PYTHON_311)
    return parser.parse_args()


def comparable(value):
    if isinstance(value, dict):
        return {
            key: comparable(item)
            for key, item in value.items()
            if key not in COMPARISON_OMIT_KEYS
        }
    if isinstance(value, list):
        return [comparable(item) for item in value]
    return value


def difference_paths(left, right, path=""):
    differences = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            if key not in left or key not in right:
                differences.append(f"{path}/{key}")
            else:
                differences.extend(difference_paths(left[key], right[key], f"{path}/{key}"))
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            differences.append(f"{path}/length")
        for index, (a, b) in enumerate(zip(left, right, strict=False)):
            differences.extend(difference_paths(a, b, f"{path}/{index}"))
    elif left != right:
        differences.append(path)
    return differences


def main():
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if next(output_dir.iterdir(), None) is not None:
        raise FileExistsError(f"pressure_output_dir_not_empty:{output_dir}")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(root), str(root / "tests"), env.get("PYTHONPATH", "")) if item
    )

    variants = (
        ("py314", args.python314, "3.14."),
        ("py311", args.python311, "3.11."),
    )
    cases = []
    failures = []
    reports_by_variant = {}
    for variant, interpreter, expected_version in variants:
        report_path = output_dir / f"{variant}-n2000-long-title-cwd-slow-pressure.json"
        log_path = report_path.with_suffix(".log")
        command = [
            interpreter,
            "-B",
            str(CASE_SCRIPT.resolve()),
            "--root",
            str(root),
            "--output",
            str(report_path),
            "--source-revision",
            args.source_revision,
            "--runtime-source-revision",
            args.runtime_source_revision,
            "--python-entrypoint",
            interpreter,
            "--driver",
            str(Path(__file__).resolve()),
        ]
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        log_path.write_text(json.dumps({
            "case": report_path.stem,
            "command": command,
            "exitCode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }, indent=2, sort_keys=True) + "\n")

        report = None
        if report_path.is_file():
            report = json.loads(report_path.read_text())
        if completed.returncode != 0:
            failures.append(f"{variant}:child_exit_{completed.returncode}")
        if report is None:
            failures.append(f"{variant}:report_missing")
            continue
        if not report["pythonVersion"].startswith(expected_version):
            failures.append(f"{variant}:unexpected_python_version")
        if report["sourceRevision"] != args.source_revision:
            failures.append(f"{variant}:source_revision_mismatch")
        if report["runtimeSourceRevision"] != args.runtime_source_revision:
            failures.append(f"{variant}:runtime_source_revision_mismatch")
        if report["caseStatus"] != "pressure_complete":
            failures.append(f"{variant}:case_not_complete")
        if report["gcEnabled"]:
            failures.append(f"{variant}:garbage_collection_enabled")
        if report["meshImports"]:
            failures.append(f"{variant}:mesh_imported")
        if report["runtime"]["workersStarted"] != 0:
            failures.append(f"{variant}:worker_started")
        if len(report["generations"]) != 14:
            failures.append(f"{variant}:accepted_generation_count")
        if report["pressure"]["naturalRuntimeRoomDropCount"] < 1:
            failures.append(f"{variant}:no_runtime_room_drop")
        if not report["pressure"]["allDropsWereOldestPinnedSlowFullPeers"]:
            failures.append(f"{variant}:unexpected_drop_victim")
        if report["failures"]:
            failures.extend(f"{variant}:{item}" for item in report["failures"])
        reports_by_variant[variant] = report
        cases.append({
            "variant": variant,
            "report": report_path.name,
            "reportSha256": digest_file(report_path),
            "log": log_path.name,
            "logSha256": digest_file(log_path),
            "pythonVersion": report["pythonVersion"],
            "sourceRevision": report["sourceRevision"],
            "runtimeSourceRevision": report["runtimeSourceRevision"],
            "caseStatus": report["caseStatus"],
            "generationCount": len(report["generations"]),
            "slowBodyDigestCount": len({
                item["slowReader"]["bodySha256"]
                for item in report["generations"]
                if item["slowReader"] is not None
            }),
            "encodedCounterHighWaterBytes": report["pressure"]["actualCounterHighWaterBytes"],
            "maxReservationCurrentPlusAdditionalBytes": report["pressure"][
                "maxReservationCurrentPlusAdditionalBytes"
            ],
            "naturalRuntimeRoomDropCount": report["pressure"]["naturalRuntimeRoomDropCount"],
            "droppedPeers": report["pressure"]["naturalDroppedPeerLabels"],
            "fullInputSha256": report["case"]["initialInputSha256"],
            "acceptedInputSha256s": [
                generation["inputSnapshotSha256"]
                for generation in report["generations"]
            ],
        })

    parity_paths = []
    if "py314" in reports_by_variant and "py311" in reports_by_variant:
        parity_paths = difference_paths(
            comparable(reports_by_variant["py314"]),
            comparable(reports_by_variant["py311"]),
        )
        if parity_paths:
            failures.append("cross_interpreter_measurement_mismatch")

    summary = {
        "schema": "working-set-resource-pressure-summary-v1",
        "sourceRevision": args.source_revision,
        "runtimeSourceRevision": args.runtime_source_revision,
        "root": str(root),
        "runnerSha256": digest_file(Path(__file__).resolve()),
        "caseRunnerSha256": digest_file(CASE_SCRIPT.resolve()),
        "pythonEntrypoints": {name: interpreter for name, interpreter, _ in variants},
        "caseCount": len(cases),
        "plannedCaseCount": len(variants),
        "allCasesProducedReports": len(cases) == len(variants),
        "crossInterpreterNormalizedParity": not parity_paths
        and len(reports_by_variant) == len(variants),
        "crossInterpreterOmittedFields": sorted(COMPARISON_OMIT_KEYS),
        "crossInterpreterDifferencePaths": parity_paths[:100],
        "failureCount": len(failures),
        "failures": failures,
        "cases": cases,
        "scope": "synthetic accepted snapshots through default source Runtime budget and local slow socketpair readers; no provider, service process, Mesh, SDK, transport, CPU, heap or RSS acceptance",
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
        raise SystemExit("pressure_matrix_failures:" + ",".join(failures))


if __name__ == "__main__":
    main()
