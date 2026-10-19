"""Compare receipt-table density reports with each other and the 610 baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIXTURE_FIELDS = (
    "rows",
    "selectionPercent",
    "selectedRows",
    "inputBytes",
    "inputSha256",
    "selectedOriginalRowBytes",
    "fullOriginalRowBytes",
    "selectedBodyRatio",
    "fullNativeFrameBytes",
)


def _read(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return json.loads(raw), raw


def _key(row: dict) -> tuple[int, int]:
    return row["rows"], row["selectionPercent"]


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-314", type=Path, required=True)
    parser.add_argument("--candidate-311", type=Path, required=True)
    parser.add_argument("--baseline-314", type=Path, required=True)
    parser.add_argument("--baseline-311", type=Path, required=True)
    parser.add_argument("--diagnostic-314", type=Path, required=True)
    parser.add_argument("--diagnostic-311", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    paths = {
        "candidate314": args.candidate_314,
        "candidate311": args.candidate_311,
        "baseline314": args.baseline_314,
        "baseline311": args.baseline_311,
        "diagnostic314": args.diagnostic_314,
        "diagnostic311": args.diagnostic_311,
    }
    loaded = {name: _read(path) for name, path in paths.items()}
    reports = {name: pair[0] for name, pair in loaded.items()}
    rows = {
        name: {_key(result): result for result in report["results"]}
        for name, report in reports.items()
        if name.startswith("candidate") or name.startswith("baseline")
    }
    case_keys = sorted(rows["candidate314"])
    if len(case_keys) != 12 or any(set(rows[name]) != set(case_keys) for name in rows):
        raise AssertionError("density_case_set_mismatch")

    cases = []
    cross_python_differences = []
    for key in case_keys:
        current314 = rows["candidate314"][key]
        current311 = rows["candidate311"][key]
        baseline314 = rows["baseline314"][key]
        baseline311 = rows["baseline311"][key]
        if any(current314[field] != current311[field] for field in FIXTURE_FIELDS):
            raise AssertionError("candidate_cross_python_input_mismatch")
        for baseline, current in (
            (baseline314, current314),
            (baseline311, current311),
        ):
            if any(baseline[field] != current[field] for field in FIXTURE_FIELDS):
                raise AssertionError("input_or_full_frame_changed")

        changed = sorted(
            field
            for field in current314
            if current314[field] != current311[field]
        )
        if changed:
            cross_python_differences.append(
                {
                    "rows": key[0],
                    "selectionPercent": key[1],
                    "fields": changed,
                    "python314": {
                        field: current314[field] for field in changed
                    },
                    "python311": {
                        field: current311[field] for field in changed
                    },
                }
            )
        cases.append(
            {
                "rows": key[0],
                "selectionPercent": key[1],
                "inputAndFullRowBytesMatch610": True,
                "fullNativeFrameBytesMatch610": True,
                "baselineWorkingFrameBytes": {
                    "python314": baseline314["workingNativeFrameBytes"],
                    "python311": baseline311["workingNativeFrameBytes"],
                },
                "currentWorkingFrameBytes": {
                    "python314": current314["workingNativeFrameBytes"],
                    "python311": current311["workingNativeFrameBytes"],
                },
                "coverage": {
                    "python314": {
                        "complete": current314["complete"],
                        "reason": current314["reason"],
                    },
                    "python311": {
                        "complete": current311["complete"],
                        "reason": current311["reason"],
                    },
                },
                "runnerAssertedExactIndependentDtoOnComplete": {
                    "python314": current314["complete"],
                    "python311": current311["complete"],
                },
                "sameOutcomeAcrossPython": (
                    current314["complete"] == current311["complete"]
                    and current314["reason"] == current311["reason"]
                    and current314["workingNativeFrameBytes"]
                    == current311["workingNativeFrameBytes"]
                ),
            }
        )

    mismatch = (
        reports["candidate314"]["sourceRevision"]
        != reports["candidate311"]["sourceRevision"]
        or reports["candidate314"]["seedSha256"]
        != reports["candidate311"]["seedSha256"]
    )
    if mismatch:
        raise AssertionError("candidate_provenance_mismatch")
    diagnostic_comparison = {
        name: {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "pythonVersion": report["pythonVersion"],
            "diagnostic": report["diagnostic"],
        }
        for name, (report, raw) in loaded.items()
        if name.startswith("diagnostic")
    }
    output = {
        "sourceRevision": reports["candidate314"]["sourceRevision"],
        "baselineSourceRevision": reports["baseline314"]["sourceRevision"],
        "scope": "untimed source wire-density comparison; no native/SDK/transport/RSS claim",
        "caseCount": len(cases),
        "currentCompleteCases": {
            "python314": sum(row["complete"] for row in reports["candidate314"]["results"]),
            "python311": sum(row["complete"] for row in reports["candidate311"]["results"]),
        },
        "currentRefusalReasons": {
            "python314": sorted(
                {row["reason"] for row in reports["candidate314"]["results"] if not row["complete"]}
            ),
            "python311": sorted(
                {row["reason"] for row in reports["candidate311"]["results"] if not row["complete"]}
            ),
        },
        "fixtureAndFullFramePreservedAgainst610": True,
        "crossPythonScalarResultsEqual": not cross_python_differences,
        "crossPythonDifferences": cross_python_differences,
        "cases": cases,
        "diagnostic": diagnostic_comparison,
        "inputReports": {
            name: {
                "path": str(paths[name]),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            for name, (_report, raw) in loaded.items()
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    _main()
