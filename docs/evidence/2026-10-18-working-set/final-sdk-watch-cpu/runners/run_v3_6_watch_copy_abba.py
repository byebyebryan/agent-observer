#!/usr/bin/env python3
"""Run approved V3.5 watch-copy trials, persisting each process before next."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


PRIVATE_ROOT = Path(__file__).resolve().parent
HARNESS = PRIVATE_ROOT / "sdk_pipeline_matrix_v3_6_watch_copy.py"
OBSERVER_ROOT = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06"
)
OBSERVER_MANIFEST = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06-manifest.json"
)
OBSERVER_ARCHIVE = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06.tar"
)
MESH_ROOT = Path("/home/bryan/code/mesh-plus-working-set/src")
LOCK_PATH = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
OBSERVER_ID = "b176ac06b39daeead4be0a33ff9d781304091fe0"
MESH_ID = "c06b33e058339d9d1d89ecf6844044867d816c58"
SOURCE_PAIR = f"{OBSERVER_ID}+{MESH_ID}"
EXPECTED_ARCHIVE_SHA256 = "a1785e81f1f998a134cf23f283eb638f398b681395ab71a4c69948f26e78c47e"
EXPECTED_MANIFEST_SHA256 = "c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877"
INTERPRETERS = (
    ("py314", Path("/home/bryan/code/mesh-plus/.venv/bin/python")),
    ("py311", Path("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python")),
)
ROW_COUNTS = (500, 2000)
ABBA = ("full", "working", "working", "full")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(payload)


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def verify_observer_export() -> dict:
    if sha256_file(OBSERVER_ARCHIVE) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("observer_archive_hash_mismatch")
    if sha256_file(OBSERVER_MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("observer_manifest_hash_mismatch")
    manifest = json.loads(OBSERVER_MANIFEST.read_text(encoding="utf-8"))
    if (manifest.get("commit") != OBSERVER_ID
            or manifest.get("archiveSha256") != EXPECTED_ARCHIVE_SHA256
            or manifest.get("fileCount") != 2223
            or not isinstance(manifest.get("files"), dict)
            or len(manifest["files"]) != 2223):
        raise RuntimeError("observer_manifest_identity_mismatch")
    for relative, expected in manifest["files"].items():
        path = (OBSERVER_ROOT / relative).resolve()
        if not path.is_relative_to(OBSERVER_ROOT.resolve()) or not path.is_file():
            raise RuntimeError("observer_export_file_missing_or_escaped")
        if sha256_file(path) != expected:
            raise RuntimeError("observer_export_file_hash_mismatch")
    if not (OBSERVER_ROOT / "agent_observer").is_dir() or not (OBSERVER_ROOT / "tests").is_dir():
        raise RuntimeError("observer_export_layout_mismatch")
    if not HARNESS.is_file() or not MESH_ROOT.is_dir():
        raise RuntimeError("qualified_source_path_missing")
    return {
        "observerCommit": OBSERVER_ID,
        "observerArchiveSha256": EXPECTED_ARCHIVE_SHA256,
        "observerManifestSha256": EXPECTED_MANIFEST_SHA256,
        "observerFilesVerified": len(manifest["files"]),
        "meshCommit": MESH_ID,
        "meshSourceRoot": str(MESH_ROOT),
    }


def verify_report(report_path: Path, trial: dict) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("format") != "agent-observer.working-set.sdk-pipeline-matrix.v3.6"
            or report.get("sourcePair") != SOURCE_PAIR
            or report.get("mode") != "trial"
            or report.get("timed") is not True
            or len(report.get("cases", [])) != 1):
        raise RuntimeError("trial_report_shape_mismatch")
    case = report["cases"][0]
    if (case.get("variant") != trial["variant"]
            or case.get("rows") != trial["rows"]
            or case.get("trialIndex") != trial["trialIndex"]
            or len(case.get("generations", [])) != 3):
        raise RuntimeError("trial_identity_mismatch")
    if report.get("configuredShape", {}).get("detachedLocalFacadeCopiesPerGeneration") != 4:
        raise RuntimeError("trial_copy_cadence_mismatch")
    if report.get("configuredShape", {}).get("diagnosticAcquisitionTimeoutSeconds") != 15.0:
        raise RuntimeError("trial_outer_acquisition_limit_changed")
    if report.get("configuredShape", {}).get("deliveryPattern", "").find(
            "one public Reader.watch_admitted") != 0:
        raise RuntimeError("trial_delivery_scope_mismatch")

    loaded = report.get("loadedProjectModules")
    if not isinstance(loaded, dict) or not loaded:
        raise RuntimeError("loaded_project_module_pins_missing")
    if canonical_sha256(loaded) != report.get("sourceModuleMapSha256"):
        raise RuntimeError("loaded_project_module_map_hash_mismatch")
    roots = {"agent_observer": OBSERVER_ROOT.resolve(), "mesh_plus": MESH_ROOT.resolve()}
    counts = {key: 0 for key in roots}
    for _name, entry in loaded.items():
        root_name = entry.get("root")
        if root_name not in roots:
            raise RuntimeError("loaded_project_module_root_mismatch")
        path = (roots[root_name] / entry["path"]).resolve()
        if not path.is_relative_to(roots[root_name]) or not path.is_file():
            raise RuntimeError("loaded_project_module_path_mismatch")
        if sha256_file(path) != entry.get("sha256"):
            raise RuntimeError("loaded_project_module_changed_after_run")
        counts[root_name] += 1
    if any(value == 0 for value in counts.values()):
        raise RuntimeError("loaded_project_module_root_missing")

    generations = case["generations"]
    for expected_generation, generation in enumerate(generations, 1):
        event = generation.get("targetEvent") or {}
        if (generation.get("accepted") is not True
                or generation.get("generation") != expected_generation
                or event.get("runtimeAccepted") != expected_generation
                or event.get("meshStatus") != "complete"
                or event.get("hostDeliveryStatus") != "ready"
                or event.get("hostViewState") != "current"
                or event.get("proofPresent") is not True
                or event.get("proofFresh") is not True
                or event.get("proofNonceFreshFromPreviousGeneration") is not True
                or type(event.get("proofRttMs")) is not int
                or event["proofRttMs"] > 2000):
            raise RuntimeError("generation_currentness_or_proof_check_failed")
        if generation.get("reconstructedNativeFrameSha256") is None:
            raise RuntimeError("native_frame_hash_missing")
        if "sha256:" + generation["reconstructedNativeFrameSha256"] != generation.get(
                "reconstructedNativeOwnerDigest"):
            raise RuntimeError("public_owner_digest_mismatch")
        witness = generation.get("publicPublisherDigestAudit") or {}
        if (witness.get("operation") != "proof"
                or witness.get("runtimeAccepted") != expected_generation
                or witness.get("ownerDigest") != generation.get("reconstructedNativeOwnerDigest")
                or witness.get("ownerDigest") != event.get("proofPayloadDigest")):
            raise RuntimeError("exact_public_proof_digest_witness_missing")
        expected_dto = generation.get("expectedDtoSha256")
        copies = generation.get("facadeReadDtoSha256")
        if (expected_dto is None or not isinstance(copies, list) or len(copies) != 4
                or any(item != expected_dto for item in copies)):
            raise RuntimeError("independent_expected_dto_mismatch")
        if type(generation.get("generationProcessCpuMs")) not in {int, float}:
            raise RuntimeError("generation_cpu_sample_missing")

    cleanup = case.get("cleanupCounts") or {}
    runtime = cleanup.get("runtime") or {}
    source = cleanup.get("cachedSourceWrapper") or {}
    if (cleanup.get("readerActiveConnections") != 0
            or cleanup.get("readerConnectionsOpened") != cleanup.get("readerConnectionsClosed")
            or cleanup.get("readerCleanupFailures") != 0
            or cleanup.get("bridgeActiveHandlers") != 0
            or cleanup.get("bridgeHandlersStarted") != (
                cleanup.get("bridgeHandlersReturned", -1)
                + cleanup.get("bridgeHandlersRaised", -1)
            )
            or cleanup.get("refusedConnectedClients") != 0
            or cleanup.get("failedPublicConnects") != 0
            or cleanup.get("bridgeOverflowConnections") != 0
            or source.get("activeSourceOperations") != 0
            or source.get("pendingSnapshotCalls") != 0
            or source.get("openWatchIterators") != 0
            or runtime.get("runtimePeersAfterRun") != 0
            or runtime.get("runtimeThreadAlive") is not False
            or runtime.get("selectorRegistrationsAfterRun") != 0
            or runtime.get("selectorClosed") is not True
            or runtime.get("selectorHookRestored") is not True):
        raise RuntimeError("trial_cleanup_unbalanced")

    counters = case.get("meshByteDiagnostic")
    if (not isinstance(counters, dict)
            or (counters.get("counterDiagnostics") or {}).get(
                "counterEqualityUsedForFunctionalAcceptance"
            ) is not False):
        raise RuntimeError("public_counter_scope_not_declared")
    delivery = counters.get("totalDelivery") or {}
    post = counters.get("postShutdown") or {}
    post_bridge = post.get("bridge") or {}
    post_clients = (post.get("clients") or {}).get("all") or {}
    completed_sender_bytes = post_bridge.get("sentBytes", 0) + post_clients.get("sentBytes", 0)
    completed_sender_frames = post_bridge.get("sentFrames", 0) + post_clients.get("sentFrames", 0)
    validated_receiver_bytes = post_bridge.get("receivedBytes", 0) + post_clients.get("receivedBytes", 0)
    validated_receiver_frames = post_bridge.get("receivedFrames", 0) + post_clients.get("receivedFrames", 0)
    if (delivery.get("completedSenderBytes") != completed_sender_bytes
            or delivery.get("completedSenderFrames") != completed_sender_frames
            or delivery.get("validatedReceiverBytes") != validated_receiver_bytes
            or delivery.get("validatedReceiverFrames") != validated_receiver_frames):
        raise RuntimeError("public_counter_totals_do_not_include_postshutdown")

    return {
        "reportSha256": sha256_file(report_path),
        "sourceModuleMapSha256": report["sourceModuleMapSha256"],
        "loadedProjectModules": loaded,
        "loadedModuleCounts": counts,
        "generationProcessCpuMs": [item["generationProcessCpuMs"] for item in generations],
        "nativeFrameHashesMatchPublicProofOwnerDigest": True,
        "independentExpectedDtoMatchesAllFourFacadeCopies": True,
        "freshCurrentProofs": True,
        "cleanupBalanced": True,
        "publicCompletedSenderTotalsIncludingTeardown": {
            "bytes": completed_sender_bytes,
            "frames": completed_sender_frames,
        },
        "publicValidatedReceiverTotalsIncludingTeardown": {
            "bytes": validated_receiver_bytes,
            "frames": validated_receiver_frames,
        },
        "publicCounterDiagnostics": {
            "bidirectionalByteCountsMatch": case[
                "meshPublicCompletedJsonLineCounters"
            ]["bidirectionalByteCountsMatch"],
            "counterDiagnostics": counters["counterDiagnostics"],
            "preShutdownCounterDeltas": counters["preShutdownCounterDeltas"],
            "postShutdownCounterDeltas": counters["postShutdownCounterDeltas"],
        },
        "readerAndBridgeCompletedJsonLineCounters": case[
            "meshPublicCompletedJsonLineCounters"
        ],
    }


def cell_plan(run_dir: Path):
    trial_index = 0
    for interpreter_name, interpreter in INTERPRETERS:
        for rows in ROW_COUNTS:
            cell_id = f"{interpreter_name}-{rows}"
            trials = []
            for position, variant in enumerate(ABBA):
                stem = f"{cell_id}-{position + 1:02d}-{variant}"
                trials.append({
                    "cellId": cell_id,
                    "cellPosition": position + 1,
                    "interpreterName": interpreter_name,
                    "interpreter": str(interpreter),
                    "rows": rows,
                    "variant": variant,
                    "trialIndex": trial_index,
                    "report": str(run_dir / f"{stem}.json"),
                    "runnerCopy": str(run_dir / f"{stem}.runner.py"),
                    "runnerMetadata": str(run_dir / f"{stem}.runner.json"),
                    "stdout": str(run_dir / f"{stem}.stdout.log"),
                    "stderr": str(run_dir / f"{stem}.stderr.log"),
                })
                trial_index += 1
            yield cell_id, trials


def validate_destination(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            raise RuntimeError("refusing_to_overwrite_existing_trial_artifact")


def run_trial(trial: dict, source_pin: dict) -> dict:
    interpreter = Path(trial["interpreter"])
    if not interpreter.is_file():
        raise RuntimeError("approved_interpreter_missing")
    report_path = Path(trial["report"])
    runner_copy = Path(trial["runnerCopy"])
    metadata_path = Path(trial["runnerMetadata"])
    stdout_path, stderr_path = Path(trial["stdout"]), Path(trial["stderr"])
    validate_destination([report_path, runner_copy, metadata_path, stdout_path, stderr_path])

    runner_bytes = HARNESS.read_bytes()
    runner_sha = sha256_bytes(runner_bytes)
    atomic_bytes(runner_copy, runner_bytes)
    args = [
        "rtk", "proxy", str(interpreter), str(runner_copy),
        "--mode", "trial",
        "--observer-id", OBSERVER_ID,
        "--mesh-id", MESH_ID,
        "--approved-source-pair", SOURCE_PAIR,
        "--trial-rows", str(trial["rows"]),
        "--trial-variant", trial["variant"],
        "--trial-index", str(trial["trialIndex"]),
        "--variant-order", ",".join(ABBA),
        "--output", str(report_path),
    ]
    argv_hash = canonical_sha256(args)
    sidecar = {
        "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6.runner.v1",
        "status": "prepared",
        "sourcePair": SOURCE_PAIR,
        "sourcePin": source_pin,
        "runnerPath": str(runner_copy),
        "runnerSha256": runner_sha,
        "argv": args,
        "argvSha256": argv_hash,
        "cellId": trial["cellId"],
        "cellPosition": trial["cellPosition"],
        "interpreterName": trial["interpreterName"],
        "interpreterPath": str(interpreter),
        "rows": trial["rows"],
        "variant": trial["variant"],
        "trialIndex": trial["trialIndex"],
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    atomic_json(metadata_path, sidecar)

    print(f"TRIAL_START {trial['cellId']} {trial['cellPosition']}/4 {trial['variant']}", flush=True)
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        completed = subprocess.run(args, stdout=stdout, stderr=stderr, check=False)

    sidecar["exitCode"] = completed.returncode
    if not report_path.is_file():
        sidecar["status"] = "failed_missing_report"
        atomic_json(metadata_path, sidecar)
        raise RuntimeError("trial_process_failed_without_report")
    try:
        verification = verify_report(report_path, trial)
    except Exception as error:
        sidecar["status"] = "failed_report_verification"
        sidecar["reportSha256"] = sha256_file(report_path)
        sidecar["verificationErrorType"] = type(error).__name__
        sidecar["verificationCode"] = str(error)[:128]
        atomic_json(metadata_path, sidecar)
        raise RuntimeError("trial_report_verification_failed") from None
    sidecar.update(verification)
    sidecar["runnerSha256AfterProcess"] = sha256_file(runner_copy)
    if sidecar["runnerSha256AfterProcess"] != runner_sha:
        sidecar["status"] = "failed_runner_bytes_changed"
        atomic_json(metadata_path, sidecar)
        raise RuntimeError("trial_runner_copy_changed")
    if completed.returncode != 0:
        sidecar["status"] = "failed_process_exit"
        atomic_json(metadata_path, sidecar)
        raise RuntimeError("trial_process_nonzero_exit")
    sidecar["status"] = "pass"
    atomic_json(metadata_path, sidecar)
    print(
        f"TRIAL_PASS {trial['cellId']} {trial['cellPosition']}/4 "
        f"{trial['variant']} cpuMs={verification['generationProcessCpuMs']}",
        flush=True,
    )
    return sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="final-b176ac06-watch-copy-abba-v3-6-20261018")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", args.run_id):
        raise ValueError("invalid_run_id")
    run_dir = PRIVATE_ROOT / "v3.6-runs" / args.run_id
    plan = list(cell_plan(run_dir))
    if args.dry_run:
        print(json.dumps({
            "sourcePair": SOURCE_PAIR,
            "abba": ABBA,
            "cells": [{"cellId": cell, "trials": trials} for cell, trials in plan],
            "trialCount": sum(len(trials) for _cell, trials in plan),
            "lockPath": str(LOCK_PATH),
            "lockHeldAcross": "one four-process ABBA cell; released between cells",
        }, sort_keys=True, indent=2))
        return 0

    if run_dir.exists():
        raise RuntimeError("run_directory_exists_preserve_existing_results")
    run_dir.mkdir(parents=True, mode=0o700)
    source_pin = verify_observer_export()
    if not HARNESS.is_file():
        raise RuntimeError("harness_identity_changed")
    if not LOCK_PATH.is_file():
        raise RuntimeError("shared_cpu_lock_missing")

    all_trials = []
    next_trial = 0
    for cell_id, trials in plan:
        print(f"LOCK_WAIT {cell_id}", flush=True)
        with LOCK_PATH.open("r+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            print(f"LOCK_ACQUIRED {cell_id}", flush=True)
            try:
                for trial in trials:
                    if trial["trialIndex"] != next_trial:
                        raise RuntimeError("trial_order_corrupt")
                    result = run_trial(trial, source_pin)
                    all_trials.append({
                        "cellId": cell_id,
                        "cellPosition": trial["cellPosition"],
                        "trialIndex": trial["trialIndex"],
                        "variant": trial["variant"],
                        "rows": trial["rows"],
                        "interpreterName": trial["interpreterName"],
                        "report": trial["report"],
                        "runnerMetadata": trial["runnerMetadata"],
                        "reportSha256": result["reportSha256"],
                        "generationProcessCpuMs": result["generationProcessCpuMs"],
                    })
                    next_trial += 1
                print(f"CELL_COMPLETE {cell_id}", flush=True)
            except Exception as error:
                failure_path = run_dir / f"failure-after-{cell_id}-{next_trial:02d}.json"
                atomic_json(failure_path, {
                    "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6.abba-failure.v1",
                    "status": "aborted_at_first_failed_trial",
                    "sourcePair": SOURCE_PAIR,
                    "sourcePin": source_pin,
                    "cellId": cell_id,
                    "nextTrialIndex": next_trial,
                    "errorType": type(error).__name__,
                    "errorCode": str(error)[:128],
                    "completedTrials": all_trials,
                    "noLaterTrialStarted": True,
                })
                print(f"ABBA_ABORT {cell_id} trial={next_trial} {type(error).__name__}", flush=True)
                return 1
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                print(f"LOCK_RELEASED {cell_id}", flush=True)

    manifest_path = run_dir / "abba-manifest.json"
    atomic_json(manifest_path, {
        "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6.abba-manifest.v1",
        "status": "pass",
        "sourcePair": SOURCE_PAIR,
        "sourcePin": source_pin,
        "workloadPattern": "one Reader.watch_admitted event per generation plus four detached local facade copies; not four SDK deliveries",
        "rows": list(ROW_COUNTS),
        "generationsPerTrial": 3,
        "copiesPerGeneration": 4,
        "interpreters": [{"name": name, "path": str(path)} for name, path in INTERPRETERS],
        "abba": ABBA,
        "trials": all_trials,
        "timingScope": "process CPU from generation through required native IPC, public Mesh watch/proof admission and facade copies; fixture/oracle/import/audit/cleanup excluded",
        "rssScope": "not measured in this tranche",
        "nativeIpcWireBytes": "unmeasured; Mesh completed JSON-line counters are retained per trial",
    })
    print(json.dumps({"status": "pass", "manifest": str(manifest_path), "trials": len(all_trials)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
