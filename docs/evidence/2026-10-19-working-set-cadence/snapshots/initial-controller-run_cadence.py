from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

OUT = Path(__file__).resolve().parent
REPO = Path("/home/bryan/code/agent-observer")
CACHE = Path("/home/bryan/.cache/agent-observer-working-set-20261018")
CANDIDATE_ROOT = CACHE / "final-source-b176ac06"
CANDIDATE_MANIFEST = CACHE / "final-source-b176ac06-manifest.json"
CANDIDATE_ARCHIVE = CACHE / "final-source-b176ac06.tar"
A7_ROOT = CACHE / "owner-screen-59b1211/a7"
SEED = CACHE / "cadence-cost-610afaa/seed.json"
HELPER = CANDIDATE_ROOT / "docs/evidence/2026-10-18-working-set/performance-source/read_matched.py"
LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
PYTHONS = {
    "py314": "/home/bryan/code/mesh-plus/.venv/bin/python",
    "py311": "/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python",
}
COMMITS = {
    "candidate": "b176ac06b39daeead4be0a33ff9d781304091fe0",
    "a7": "7807160384ba39b4d438c5c7f1b5f316c3608dcd",
}
PINS = {
    "manifestSha256": "c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877",
    "candidateArchiveSha256": "a1785e81f1f998a134cf23f283eb638f398b681395ab71a4c69948f26e78c47e",
    "helperSha256": "ccf91435e078fc5c1aadc5a1070e7e1973bdb06265351a8e1508b07c3644895b",
    "seedSha256": "92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9",
}
ORDER = ("a7-full", "candidate-working", "candidate-working", "a7-full")
ROWS = (100, 500, 2000)
CADENCES = (0, 1, 16)
EXTRA_CADENCE = 4
MAX_CASE_SECONDS = 180
MAX_JOB_SECONDS = 900
MAX_ARTIFACT_BYTES = 262144


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if len(data) > MAX_ARTIFACT_BYTES:
        raise RuntimeError("controller_artifact_exceeded_size_limit")
    path.write_bytes(data)


def rtk_run(args, *, input_bytes=None):
    proc = subprocess.run(
        ["rtk", "proxy", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(
            "rtk_command_failed:" + " ".join(args) + ":" +
            proc.stderr[:500].decode(errors="replace")
        )
    return proc.stdout


def git_bytes(*args, input_bytes=None):
    return rtk_run(["git", "-C", str(REPO), *args], input_bytes=input_bytes)


def tracked_blob_map(commit: str, prefix: str | None = None):
    argv = ["ls-tree", "-rz", "--full-tree", commit]
    if prefix:
        argv += ["--", prefix]
    raw = git_bytes(*argv)
    items = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        _mode, kind, oid = meta.decode().split()
        if kind == "blob":
            items[name.decode()] = oid
    return items


def git_blob_data(oids):
    payload = ("".join(oid + "\n" for oid in oids)).encode()
    raw = git_bytes("cat-file", "--batch", input_bytes=payload)
    data = {}
    position = 0
    for oid in oids:
        end = raw.index(b"\n", position)
        header = raw[position:end].decode().split()
        if len(header) != 3 or header[0] != oid or header[1] != "blob":
            raise RuntimeError("git_blob_header_mismatch")
        size = int(header[2])
        position = end + 1
        data[oid] = raw[position:position + size]
        position += size + 1
    if position != len(raw):
        raise RuntimeError("git_blob_trailing_bytes")
    return data


def disk_map(root: Path):
    files = {}
    ignored = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            ignored.append(relative)
        else:
            files[relative] = sha(path.read_bytes())
    return files, sorted(ignored)


def check_pins():
    manifest_bytes = CANDIDATE_MANIFEST.read_bytes()
    manifest_sha = sha(manifest_bytes)
    if manifest_sha != PINS["manifestSha256"]:
        raise RuntimeError("candidate_manifest_sha_mismatch")
    manifest = json.loads(manifest_bytes)
    if manifest.get("commit") != COMMITS["candidate"] or manifest.get("fileCount") != 2223:
        raise RuntimeError("candidate_manifest_identity_mismatch")
    if sha(CANDIDATE_ARCHIVE.read_bytes()) != PINS["candidateArchiveSha256"]:
        raise RuntimeError("candidate_archive_sha_mismatch")
    if sha(HELPER.read_bytes()) != PINS["helperSha256"]:
        raise RuntimeError("helper_sha_mismatch")
    if sha(SEED.read_bytes()) != PINS["seedSha256"]:
        raise RuntimeError("seed_sha_mismatch")

    candidate_disk, candidate_ignored = disk_map(CANDIDATE_ROOT)
    candidate_manifest_files = manifest.get("files")
    if candidate_disk != candidate_manifest_files:
        missing = sorted(set(candidate_manifest_files) - set(candidate_disk))[:8]
        extra = sorted(set(candidate_disk) - set(candidate_manifest_files))[:8]
        changed = sorted(
            name for name in candidate_manifest_files.keys() & candidate_disk.keys()
            if candidate_manifest_files[name] != candidate_disk[name]
        )[:8]
        raise RuntimeError(
            f"candidate_export_mismatch:missing={missing}:extra={extra}:changed={changed}"
        )
    if len(candidate_disk) != 2223:
        raise RuntimeError("candidate_tracked_file_count_mismatch")

    candidate_git = tracked_blob_map(COMMITS["candidate"])
    candidate_blobs = git_blob_data(list(candidate_git.values()))
    candidate_git_files = {
        name: sha(candidate_blobs[oid]) for name, oid in candidate_git.items()
    }
    if candidate_git_files != candidate_manifest_files:
        raise RuntimeError("candidate_manifest_git_blob_mismatch")

    a7_git = tracked_blob_map(COMMITS["a7"], "agent_observer")
    a7_blobs = git_blob_data(list(a7_git.values()))
    a7_git_files = {name: sha(a7_blobs[oid]) for name, oid in a7_git.items()}
    a7_disk, a7_ignored = disk_map(A7_ROOT)
    if a7_disk != a7_git_files or len(a7_disk) != 63:
        missing = sorted(set(a7_git_files) - set(a7_disk))[:8]
        extra = sorted(set(a7_disk) - set(a7_git_files))[:8]
        changed = sorted(name for name in a7_disk.keys() & a7_git_files.keys()
                         if a7_disk[name] != a7_git_files[name])[:8]
        raise RuntimeError(
            f"a7_export_mismatch:missing={missing}:extra={extra}:changed={changed}"
        )

    helper_rel = HELPER.relative_to(CANDIDATE_ROOT).as_posix()
    if candidate_manifest_files.get(helper_rel) != PINS["helperSha256"]:
        raise RuntimeError("helper_not_bound_by_candidate_manifest")

    current_head = git_bytes("rev-parse", "HEAD").decode().strip()
    current_status = git_bytes("status", "--porcelain=v1").decode().splitlines()
    if current_status:
        raise RuntimeError("main_workspace_not_clean")
    python_versions = {}
    for label, executable in PYTHONS.items():
        version = rtk_run(
            [executable, "-c", "import sys; print(sys.version.split()[0])"]
        ).decode().strip()
        if (label == "py314" and not version.startswith("3.14.")) or (
            label == "py311" and not version.startswith("3.11.")
        ):
            raise RuntimeError(f"python_version_mismatch:{label}:{version}")
        python_versions[label] = {"executable": executable, "version": version}

    return {
        "status": "pass",
        "candidateCommit": COMMITS["candidate"],
        "candidateManifestSha256": manifest_sha,
        "candidateManifestFiles": len(candidate_manifest_files),
        "candidateGitBlobFiles": len(candidate_git_files),
        "candidateArchiveSha256": PINS["candidateArchiveSha256"],
        "candidateHelperPath": helper_rel,
        "candidateHelperSha256": PINS["helperSha256"],
        "a7Commit": COMMITS["a7"],
        "a7AgentObserverGitBlobFiles": len(a7_git_files),
        "seedSha256": PINS["seedSha256"],
        "currentWorkspaceHead": current_head,
        "currentWorkspaceStatus": "clean",
        "pythonVersions": python_versions,
        "preexistingGeneratedExtrasIgnored": {
            "candidate": {"count": len(candidate_ignored), "paths": candidate_ignored[:40]},
            "a7": {"count": len(a7_ignored), "paths": a7_ignored[:40]},
            "policy": "files under __pycache__ and *.pyc are runtime extras; left untouched; PYTHONDONTWRITEBYTECODE=1 for runs",
        },
        "sourceEquality": (
            "all candidate exported tracked file bytes equal the pinned Git b176 tree and manifest; "
            "all a7 agent_observer exported file bytes equal the pinned Git 7807160 tree"
        ),
    }


def expected_ids(rows):
    small = max(1, rows // 200)
    return {
        "small": small,
        "activeIds": [str(UUID(int=1000 + n)) for n in range(small)],
        "selectedIds": [str(UUID(int=1000 + n)) for n in range(2 * small)],
        "selectedCount": 2 * small,
    }


def artifact_paths(relative_base: Path):
    base = OUT / relative_base
    return {
        "result": base.with_suffix(".result.json"),
        "invocation": base.with_suffix(".invocation.json"),
        "stdout": base.with_suffix(".stdout.log"),
        "stderr": base.with_suffix(".stderr.log"),
    }


def limit_output_files():
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES))


def run_trial(*, label: str, rows: int, reads: int, variant: str,
              relative_base: Path, validate_only: bool, timeout_seconds: int):
    paths = artifact_paths(relative_base)
    for path in paths.values():
        if path.exists():
            raise RuntimeError(f"refusing_to_overwrite:{path.relative_to(OUT)}")
    paths["result"].parent.mkdir(parents=True, exist_ok=True)
    root = A7_ROOT if variant == "a7-full" else CANDIDATE_ROOT
    python = PYTHONS[label]
    command = [
        "rtk", "proxy", "timeout", "--signal=TERM", "--kill-after=5s",
        f"{timeout_seconds}s",
        "rtk", "proxy", python, str(HELPER), str(root), str(SEED),
        str(paths["result"]), "--rows", str(rows), "--variant", variant,
        "--reads-per-generation", str(reads),
    ]
    if validate_only:
        command.append("--validate-only")
    invocation = {
        "label": label,
        "rows": rows,
        "readsPerGeneration": reads,
        "variant": variant,
        "validateOnly": validate_only,
        "python": python,
        "helper": str(HELPER),
        "helperSha256": PINS["helperSha256"],
        "root": str(root),
        "rootCommit": COMMITS["a7"] if variant == "a7-full" else COMMITS["candidate"],
        "seedSha256": PINS["seedSha256"],
        "command": command,
        "perCaseTimeoutSeconds": timeout_seconds,
        "sharedLockPath": str(LOCK),
        "lockMode": "exclusive, held around controller and every trial",
        "gc": "disabled by exact helper",
        "pythonDontWriteBytecode": True,
        "startedAt": now(),
        "status": "running",
    }
    write_json(paths["invocation"], invocation)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    with paths["stdout"].open("wb") as stdout, paths["stderr"].open("wb") as stderr:
        proc = subprocess.Popen(
            command,
            cwd=OUT,
            env=env,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
            preexec_fn=limit_output_files,
        )
        try:
            returncode = proc.wait(timeout=timeout_seconds + 8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
            returncode = proc.returncode if proc.returncode is not None else 124
            invocation["controllerTimeout"] = True
    wall_seconds = time.monotonic() - started
    invocation["elapsedWallSeconds"] = round(wall_seconds, 6)
    invocation["returnCode"] = returncode
    invocation["completedAt"] = now()
    for kind in ("result", "stdout", "stderr"):
        if paths[kind].exists() and paths[kind].stat().st_size > MAX_ARTIFACT_BYTES:
            raise RuntimeError(f"artifact_size_limit_exceeded:{paths[kind].relative_to(OUT)}")
    if returncode != 0:
        invocation["status"] = "failed"
        write_json(paths["invocation"], invocation)
        raise RuntimeError(
            f"trial_failed:{label}:rows{rows}:reads{reads}:{variant}:rc{ returncode }"
        )
    if not paths["result"].is_file():
        invocation["status"] = "failed"
        write_json(paths["invocation"], invocation)
        raise RuntimeError("helper_result_missing")
    result = json.loads(paths["result"].read_text())
    validate_result(result, rows, reads, variant, validate_only)
    invocation["resultSha256"] = sha(paths["result"].read_bytes())
    invocation["status"] = "pass"
    write_json(paths["invocation"], invocation)
    return result, invocation


def validate_result(result, rows, reads, variant, validate_only):
    if result.get("rows") != rows or result.get("variant") != variant:
        raise RuntimeError("result_case_identity_mismatch")
    if result.get("gcEnabled") is not False:
        raise RuntimeError("garbage_collection_was_enabled")
    if validate_only:
        if result.get("validationOnly") is not True:
            raise RuntimeError("validate_only_result_missing_flag")
        if result.get("readsPerGenerationRequested") != reads:
            raise RuntimeError("validate_only_reads_request_mismatch")
        if result.get("verifiedSelectedRows") != expected_ids(rows)["selectedCount"]:
            raise RuntimeError("validate_only_selected_count_mismatch")
        return
    if result.get("readsPerGeneration") != reads:
        raise RuntimeError("measured_reads_cadence_mismatch")
    if result.get("measuredGenerations") != 6 or result.get("warmupGenerations") != 1:
        raise RuntimeError("generation_count_metadata_mismatch")
    if result.get("measuredReads") != 6 * reads:
        raise RuntimeError("read_count_mismatch")
    if len(result.get("generationCpuMs", [])) != 6:
        raise RuntimeError("generation_cpu_length_mismatch")
    if len(result.get("combinedCpuByGenerationMs", [])) != 6:
        raise RuntimeError("combined_cpu_length_mismatch")
    if len(result.get("readCpuMs", [])) != 6 * reads:
        raise RuntimeError("read_cpu_length_mismatch")
    if len(result.get("readFrameBytesByRead", [])) != 6 * reads:
        raise RuntimeError("read_frame_length_mismatch")
    if len(result.get("fullDigest", "")) != 64 or len(result.get("activeDigest", "")) != 64:
        raise RuntimeError("snapshot_digest_missing")
    if len(result.get("selectedDigest", "")) != 64:
        raise RuntimeError("selected_digest_missing")
    if variant == "candidate-working":
        if result.get("workingDigest") != result.get("selectedDigest"):
            raise RuntimeError("working_selection_digest_mismatch")
        if result.get("workingCoverage") != "complete":
            raise RuntimeError("working_coverage_not_complete")
    elif variant == "a7-full" and result.get("workingDigest") is not None:
        raise RuntimeError("a7_unexpected_working_digest")
    expected = expected_ids(rows)
    if result.get("fullRowsPerGeneration") != [rows] * 6:
        raise RuntimeError("full_row_count_mismatch")
    if result.get("activeRowsPerGeneration") != [expected["small"]] * 6:
        raise RuntimeError("active_row_count_mismatch")
    if result.get("selectedRowsPerGeneration") != [expected["selectedCount"]] * 6:
        raise RuntimeError("selected_row_count_mismatch")


def load_result(relative_base):
    return json.loads(artifact_paths(relative_base)["result"].read_text())


def preflight_validate_all(pins, stdout_progress=True):
    validation_results = []
    for label in ("py314", "py311"):
        for variant in ("a7-full", "candidate-full", "candidate-working"):
            base = Path("validation") / f"{label}-{variant}"
            result, _invocation = run_trial(
                label=label,
                rows=100,
                reads=0,
                variant=variant,
                relative_base=base,
                validate_only=True,
                timeout_seconds=MAX_CASE_SECONDS,
            )
            validation_results.append({
                "python": label,
                "variant": variant,
                "result": result,
                "resultPath": str(artifact_paths(base)["result"].relative_to(OUT)),
            })
            if stdout_progress:
                print(json.dumps({
                    "event": "validate_only_pass",
                    "python": label,
                    "variant": variant,
                    "selectedRows": result["verifiedSelectedRows"],
                    "fullDigest": result["fullDigest"],
                    "activeDigest": result["activeDigest"],
                    "selectedDigest": result["selectedDigest"],
                }, sort_keys=True), flush=True)

    full_digests = {item["result"]["fullDigest"] for item in validation_results}
    active_digests = {item["result"]["activeDigest"] for item in validation_results}
    selected_digests = {item["result"]["selectedDigest"] for item in validation_results}
    if len(full_digests) != 1 or len(active_digests) != 1 or len(selected_digests) != 1:
        raise RuntimeError("validate_only_cross_variant_digest_mismatch")
    expected = expected_ids(100)
    if any(item["result"]["verifiedSelectedRows"] != expected["selectedCount"]
           for item in validation_results):
        raise RuntimeError("validate_only_selection_id_count_mismatch")
    candidate = [item for item in validation_results
                 if item["variant"].startswith("candidate-")]
    if any(item["result"]["workingDigest"] != item["result"]["selectedDigest"]
           or item["result"]["workingCoverage"] != "complete" for item in candidate):
        raise RuntimeError("validate_only_candidate_working_digest_mismatch")
    if any(item["result"]["gcEnabled"] is not False for item in validation_results):
        raise RuntimeError("validate_only_gc_mismatch")

    check = {
        "status": "pass",
        "rows": 100,
        "readsPerGenerationRequested": 0,
        "runCount": len(validation_results),
        "variants": ["a7-full", "candidate-full", "candidate-working"],
        "pythonLabels": ["py314", "py311"],
        "literalSyntheticIdsExpectedAndInternallyCheckedByHelper": expected,
        "matchingDigests": {
            "fullDigest": next(iter(full_digests)),
            "activeDigest": next(iter(active_digests)),
            "selectedDigest": next(iter(selected_digests)),
            "candidateWorkingDigest": next(iter(
                item["result"]["workingDigest"] for item in candidate
            )),
        },
        "validatedOutputs": [
            {
                "python": item["python"],
                "variant": item["variant"],
                "resultPath": item["resultPath"],
                "fullDigest": item["result"]["fullDigest"],
                "activeDigest": item["result"]["activeDigest"],
                "selectedDigest": item["result"]["selectedDigest"],
                "workingDigest": item["result"].get("workingDigest"),
                "verifiedSelectedRows": item["result"]["verifiedSelectedRows"],
                "gcEnabled": item["result"]["gcEnabled"],
            }
            for item in validation_results
        ],
        "scope": "untimed helper checks only; not a CPU result",
        "completedAt": now(),
    }
    write_json(OUT / "validate-only.json", check)
    write_json(OUT / "preflight.json", {
        "status": "pass",
        "pins": pins,
        "validation": check,
        "completedAt": now(),
    })
    return check


def matrix_cases():
    for label in ("py314", "py311"):
        for rows in ROWS:
            for reads in CADENCES:
                yield label, rows, reads
        yield label, 100, EXTRA_CADENCE


def matrix_mode():
    started = time.monotonic()
    pins = check_pins()
    preflight_path = OUT / "preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("validated_preflight_missing")
    preflight = json.loads(preflight_path.read_text())
    if preflight.get("status") != "pass":
        raise RuntimeError("validated_preflight_not_passed")
    if preflight.get("pins") != pins:
        raise RuntimeError("preflight_pins_changed")
    if (OUT / "matrix-status.json").exists():
        raise RuntimeError("matrix_outputs_already_started; refusing_to_overwrite")

    planned = [
        {
            "python": label,
            "rows": rows,
            "readsPerGeneration": reads,
            "variantsInOrder": list(ORDER),
        }
        for label, rows, reads in matrix_cases()
    ]
    if len(planned) != 20 or 4 * len(planned) != 80:
        raise RuntimeError("fixed_matrix_shape_mismatch")
    status_path = OUT / "matrix-status.json"
    progress_path = OUT / "progress.jsonl"
    status = {
        "status": "running",
        "startedAt": now(),
        "plannedCells": len(planned),
        "plannedFreshTrials": 80,
        "maxCaseSeconds": MAX_CASE_SECONDS,
        "maxJobSecondsAfterLock": MAX_JOB_SECONDS,
        "pins": pins,
        "matrix": planned,
        "completedTrials": 0,
        "completedCells": 0,
        "scope": "synthetic pure ServiceState source component; no SDK or transport",
    }
    write_json(status_path, status)
    if progress_path.exists():
        raise RuntimeError("progress_path_already_exists")
    progress_path.write_text("")

    completed_trials = 0
    completed_cells = 0
    try:
        for label, rows, reads in matrix_cases():
            if time.monotonic() - started >= MAX_JOB_SECONDS:
                raise RuntimeError("15_minute_job_budget_exceeded_before_cell")
            for ordinal, variant in enumerate(ORDER, start=1):
                elapsed = time.monotonic() - started
                remaining = MAX_JOB_SECONDS - elapsed
                if remaining <= 0:
                    raise RuntimeError("15_minute_job_budget_exceeded_before_trial")
                case_timeout = min(MAX_CASE_SECONDS, max(1, int(remaining)))
                base = Path("trials") / label / f"rows{rows}" / f"reads{reads}" / f"trial{ordinal:02d}-{variant}"
                result, invocation = run_trial(
                    label=label,
                    rows=rows,
                    reads=reads,
                    variant=variant,
                    relative_base=base,
                    validate_only=False,
                    timeout_seconds=case_timeout,
                )
                completed_trials += 1
                progress = {
                    "event": "trial_pass",
                    "trial": completed_trials,
                    "plannedTrials": 80,
                    "cell": {
                        "python": label,
                        "rows": rows,
                        "readsPerGeneration": reads,
                    },
                    "ordinal": ordinal,
                    "variant": variant,
                    "elapsedWallSeconds": invocation["elapsedWallSeconds"],
                    "combinedCpuTotalMs": result["combinedCpuTotalMs"],
                    "totalSerializedFrameBytes": result["totalSerializedFrameBytes"],
                    "resultPath": str(artifact_paths(base)["result"].relative_to(OUT)),
                    "at": now(),
                }
                with progress_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(progress, sort_keys=True) + "\n")
                    stream.flush()
                status["completedTrials"] = completed_trials
                status["updatedAt"] = now()
                write_json(status_path, status)
                print(json.dumps(progress, sort_keys=True), flush=True)
            completed_cells += 1
            status["completedCells"] = completed_cells
            write_json(status_path, status)
        if completed_trials != 80 or completed_cells != 20:
            raise RuntimeError("matrix_trial_or_cell_count_mismatch")
        status.update(
            status="pass",
            completedTrials=completed_trials,
            completedCells=completed_cells,
            completedAt=now(),
            elapsedSeconds=round(time.monotonic() - started, 6),
            progressSha256=sha(progress_path.read_bytes()),
        )
        write_json(status_path, status)
        print(json.dumps({
            "event": "matrix_complete",
            "trials": completed_trials,
            "cells": completed_cells,
            "elapsedSeconds": status["elapsedSeconds"],
        }, sort_keys=True), flush=True)
    except Exception as exc:
        status.update(
            status="failed",
            completedTrials=completed_trials,
            completedCells=completed_cells,
            failure=f"{type(exc).__name__}:{exc}",
            failedAt=now(),
            elapsedSeconds=round(time.monotonic() - started, 6),
        )
        write_json(status_path, status)
        raise


def validate_mode():
    if (OUT / "preflight.json").exists():
        raise RuntimeError("preflight_already_exists; refusing_to_overwrite")
    pins = check_pins()
    write_json(OUT / "pin-report.json", pins)
    try:
        check = preflight_validate_all(pins)
    except Exception as exc:
        write_json(OUT / "preflight-failure.json", {
            "status": "failed",
            "failure": f"{type(exc).__name__}:{exc}",
            "completedAt": now(),
        })
        raise
    print(json.dumps({
        "event": "validate_only_complete",
        "runs": check["runCount"],
        "fullDigest": check["matchingDigests"]["fullDigest"],
        "activeDigest": check["matchingDigests"]["activeDigest"],
        "selectedDigest": check["matchingDigests"]["selectedDigest"],
    }, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("validate", "matrix"))
    args = parser.parse_args()
    if args.mode == "validate":
        validate_mode()
    else:
        matrix_mode()


if __name__ == "__main__":
    main()
