from __future__ import annotations

import fcntl
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path

OUT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/owner-screen-final-196a8e2b-paired-02")
CACHE = Path("/home/bryan/.cache/agent-observer-working-set-20261018")
LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
SEED = CACHE / "p3-owner-cost" / "seed.json"
RUNNER = Path("/home/bryan/code/agent-observer-working-set/docs/evidence/2026-10-18-working-set/performance-source/owner_matched_with_disabled.py")
A7_ROOT = CACHE / "owner-screen-59b1211" / "a7"
CURRENT_ROOT = CACHE / "final-source-196a8e2b"
PYTHON = {
    "314": "/home/bryan/code/mesh-plus/.venv/bin/python",
    "311": "/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python",
}
SOURCE_COMMITS = {
    "a7": "7807160384ba39b4d438c5c7f1b5f316c3608dcd",
    "candidate": "196a8e2bd114f90aae82c4ee79559db511b9dce7",
    "current-disabled": "196a8e2bd114f90aae82c4ee79559db511b9dce7",
}
EXPECTED_RUNNER_SHA = "de84a21389790fb95207fdb0885e2e291c612ec7dbc3f2640691573b786ec13a"
EXPECTED_SEED_SHA = "92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9"
GROUPS = (("314", 500), ("314", 2000), ("311", 500), ("311", 2000))
ORDER = ("a7", "candidate", "candidate", "a7",
         "current-disabled", "current-disabled")
EXPECTED_PYTHON = {"314": "3.14.8", "311": "3.11.17"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def tree_manifest(root: Path) -> dict[str, str]:
    package = root / "agent_observer"
    rows = {}
    for path in sorted(package.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        rows[rel] = file_sha(path)
    payload = "".join(f"{name}\0{digest}\n" for name, digest in rows.items()).encode()
    return {"treeSha256": sha(payload), "files": rows}


def loaded_matches(report: dict, root: Path) -> None:
    loaded = report.get("loaded")
    if not isinstance(loaded, dict):
        raise RuntimeError("loaded_manifest_missing")
    for module, entry in loaded.items():
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise RuntimeError("loaded_manifest_entry_shape")
        rel = entry["path"]
        expected_rel = "agent_observer/__init__.py" if module == "agent_observer" else module.replace(".", "/") + ".py"
        if rel != expected_rel or not rel.endswith(".py") or ".." in Path(rel).parts:
            raise RuntimeError("loaded_manifest_identity")
        if file_sha(root / rel) != entry["sha256"]:
            raise RuntimeError("loaded_source_hash_mismatch")


def main() -> int:
    if any(p.name != Path(__file__).name for p in OUT.iterdir()):
        raise RuntimeError("output_directory_not_empty")
    runner_sha = file_sha(RUNNER)
    seed_sha = file_sha(SEED)
    if runner_sha != EXPECTED_RUNNER_SHA:
        raise RuntimeError("runner_hash_mismatch")
    if seed_sha != EXPECTED_SEED_SHA:
        raise RuntimeError("seed_hash_mismatch")
    for py in PYTHON.values():
        if not Path(py).is_file():
            raise RuntimeError("python_entrypoint_missing")
    before_sources = {
        "a7": tree_manifest(A7_ROOT),
        "current": tree_manifest(CURRENT_ROOT),
    }
    start_epoch = time.time()
    records = []
    reports_by_group = []
    with LOCK.open("rb") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        lock_acquired_epoch = time.time()
        (OUT / "lock-acquired.json").write_text(json.dumps({
            "lock": str(LOCK), "acquiredEpoch": lock_acquired_epoch,
            "pid": __import__("os").getpid(),
        }, sort_keys=True) + "\n")
        stopped = None
        try:
            for py, rows in GROUPS:
                group_reports = []
                for sample, variant in enumerate(ORDER):
                    name = f"{py}-{rows}-{sample}-{variant}"
                    report_path = OUT / f"{name}.json"
                    log_path = OUT / f"{name}.log"
                    root = A7_ROOT if variant == "a7" else CURRENT_ROOT
                    command = [
                        PYTHON[py], "-B", str(RUNNER), str(root), str(SEED),
                        str(report_path), "--rows", str(rows), "--variant", variant,
                    ]
                    proc = subprocess.run(
                        command, cwd=str(root), stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, check=False,
                    )
                    log_path.write_bytes(proc.stdout + proc.stderr)
                    if proc.returncode != 0 or not report_path.exists():
                        stopped = f"trial_failed:{name}:{proc.returncode}"
                        raise RuntimeError(stopped)
                    report = json.loads(report_path.read_bytes())
                    if report.get("variant") != variant or report.get("rows") != rows:
                        stopped = f"trial_identity:{name}"
                        raise RuntimeError(stopped)
                    if report.get("python") != EXPECTED_PYTHON[py] or report.get("gcEnabled") is not False:
                        stopped = f"trial_runtime:{name}"
                        raise RuntimeError(stopped)
                    if len(report.get("generationCpuMs", [])) != 6:
                        stopped = f"trial_generation_count:{name}"
                        raise RuntimeError(stopped)
                    if not math.isclose(sum(report["generationCpuMs"]), report["totalSixGenerationCpuMs"], rel_tol=1e-12, abs_tol=1e-9):
                        stopped = f"trial_component_sum:{name}"
                        raise RuntimeError(stopped)
                    source_root = A7_ROOT if variant == "a7" else CURRENT_ROOT
                    loaded_matches(report, source_root)
                    checks = report["checks"]
                    small = max(1, rows // 200)
                    if (checks.get("fullRows") != rows or checks.get("activeRows") != small
                            or checks.get("selectedRows") != 2 * small):
                        stopped = f"trial_semantics:{name}"
                        raise RuntimeError(stopped)
                    if variant == "candidate":
                        if (checks.get("workingBodies") != 2 * small
                                or checks.get("workingCoverage") != "complete"
                                or type(checks.get("guardBytes")) is not int):
                            stopped = f"candidate_incomplete:{name}"
                            raise RuntimeError(stopped)
                    records.append({
                        "python": py, "pythonPath": PYTHON[py], "pythonVersion": report["python"],
                        "rows": rows, "variant": variant, "sample": sample,
                        "report": report_path.name, "log": log_path.name,
                        "exitCode": proc.returncode,
                        "sixGenerationCpuMs": report["totalSixGenerationCpuMs"],
                        "generationCpuMs": report["generationCpuMs"],
                        "fixtureDigest": report["fixtureDigest"],
                        "checks": checks, "loaded": report["loaded"],
                        "command": command,
                    })
                    group_reports.append(report)
                if tuple(r["variant"] for r in group_reports) != ORDER:
                    stopped = f"group_order:{py}:{rows}"
                    raise RuntimeError(stopped)
                first = group_reports[0]
                for current in group_reports[1:]:
                    if current["fixtureDigest"] != first["fixtureDigest"]:
                        stopped = f"group_input_mismatch:{py}:{rows}"
                        raise RuntimeError(stopped)
                    for key in ("fullDigest", "activeDigest", "selectedDigest"):
                        if current["checks"][key] != first["checks"][key]:
                            stopped = f"group_output_mismatch:{py}:{rows}:{key}"
                            raise RuntimeError(stopped)
                    for key in ("fullRows", "activeRows", "selectedRows"):
                        if current["checks"][key] != first["checks"][key]:
                            stopped = f"group_count_mismatch:{py}:{rows}:{key}"
                            raise RuntimeError(stopped)
                reports_by_group.append((py, rows, group_reports))
        except Exception as exc:
            if stopped is None:
                stopped = f"runner_error:{type(exc).__name__}:{exc}"
            raise
        finally:
            after_sources = {
                "a7": tree_manifest(A7_ROOT),
                "current": tree_manifest(CURRENT_ROOT),
            }
            summary = []
            for py, rows, group_reports in reports_by_group:
                medians = {
                    variant: statistics.median(
                        report["totalSixGenerationCpuMs"]
                        for report in group_reports if report["variant"] == variant
                    )
                    for variant in ("a7", "candidate", "current-disabled")
                }
                delta = 100 * (medians["candidate"] / medians["a7"] - 1)
                summary.append({
                    "python": py, "rows": rows, "mediansCpuMs": medians,
                    "candidateVsA7Percent": delta,
                    "ownerOverhead25PercentPass": delta <= 25.0,
                    "fixtureDigest": group_reports[0]["fixtureDigest"],
                    "fullOutputDigest": group_reports[0]["checks"]["fullDigest"],
                    "activeOutputDigest": group_reports[0]["checks"]["activeDigest"],
                    "selectedOutputDigest": group_reports[0]["checks"]["selectedDigest"],
                    "candidateGuardBytes": next(
                        r["checks"]["guardBytes"] for r in group_reports
                        if r["variant"] == "candidate"
                    ),
                })
            source_stable = before_sources == after_sources
            gate_pass = (
                stopped is None and len(records) == 24 and source_stable
                and all(row["ownerOverhead25PercentPass"] for row in summary)
            )
            driver = {
                "screen": "final-owner-cpu-component-paired-a7",
                "sourceCommit": SOURCE_COMMITS["candidate"],
                "a7BaselineCommit": SOURCE_COMMITS["a7"],
                "immutableExports": {"a7": str(A7_ROOT), "current": str(CURRENT_ROOT)},
                "runner": str(RUNNER), "runnerSha256": runner_sha,
                "seed": str(SEED), "seedSha256": seed_sha,
                "lock": str(LOCK), "lockAcquiredEpoch": lock_acquired_epoch,
                "startedEpoch": start_epoch, "finishedEpoch": time.time(),
                "groups": [{"python": py, "rows": rows} for py, rows, _ in reports_by_group],
                "order": "A7,candidate,candidate,A7,current-disabled,current-disabled per group",
                "lexicalPythonPaths": PYTHON,
                "beforeSourceManifests": before_sources,
                "afterSourceManifests": after_sources,
                "sourceStable": source_stable,
                "recordCount": len(records), "records": records, "summary": summary,
                "gate": {
                    "ownerOverheadMaxPercent": 25.0,
                    "passed": gate_pass,
                    "evaluatedAgainstPairedA7": True,
                    "completedAll24": len(records) == 24,
                },
                "stopped": stopped,
                "scope": (
                    "Pure ServiceState component CPU only: six accepted attempt/accept generations "
                    "after one excluded warmup; constructor, native collection, parent parsing, reads, "
                    "SDK/transport, RSS, and whole-producer cost are outside this screen."
                ),
            }
            (OUT / "driver.json").write_text(json.dumps(driver, indent=2, sort_keys=True) + "\n")
            (OUT / "README.md").write_text(
                "# Final 196a8e2b owner CPU screen\n\n"
                "This private source-only screen compares the final Observer source export with the accepted a7 baseline. "
                "It uses 24 trials over 500 and 2,000 rows on the exact Python 3.14.8 and 3.11.17 entrypoints. "
                "For each interpreter/size group the order is A7, candidate, candidate, A7, current-disabled, current-disabled. "
                "Each trial includes one excluded warmup plus six accepted generations; only the six attempt/accept calls contribute to process CPU totals.\n\n"
                "The candidate has the 72-hour working-set window enabled and accepted-BOOTTIME capture enabled through the unchanged pinned runner. "
                "The disabled controls run the same final source with working-set options omitted. The full, active, and independently selected DTO digests must match across variants; candidate working-set output must be complete and equal to the independently filtered rows.\n\n"
                "The gate compares candidate median component CPU to paired A7 median and allows at most 25 percent overhead. This is a component screen only; it does not establish native, SDK, installed, transport, whole-pipeline, physical, or RSS acceptance.\n\n"
                "Exact lexical interpreter paths, immutable export manifests, runner/seed hashes, per-trial generation sums, output digests, and pre/post source manifests are in driver.json. Each trial report contains only bounded synthetic fixture metadata and hashes; logs are expected to be empty.\n"
            )
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    print(json.dumps({
        "output": str(OUT), "records": len(records),
        "gatePass": gate_pass, "sourceStable": source_stable,
        "groups": summary,
    }, sort_keys=True))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
