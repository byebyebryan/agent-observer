#!/usr/bin/env python3
"""Plan or run the gated V3.8 serial-watch4 CPU ABBA matrix."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cpu_exclusions_v3_8 import EXCLUSION_LABELS


PRIVATE_ROOT = Path(__file__).resolve().parent
HARNESS = PRIVATE_ROOT / "sdk_pipeline_matrix_v3_8_serial_watch4.py"
CPU_HELPER = PRIVATE_ROOT / "cpu_exclusions_v3_8.py"
CPU_HELPER_SHA256 = "aa1d63a8d67e3e0ebd90069a55aa5330194efeb95d907cdc074a810a10baf3bb"
PAIR_CONFIG = PRIVATE_ROOT / "approved-source-pair.json"
SHARED_LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
RUNS_ROOT = PRIVATE_ROOT / "runs"
INTERPRETERS = {
    "py314": Path("/home/bryan/code/mesh-plus/.venv/bin/python"),
    "py311": Path("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"),
}
ABBA_ORDER = ("full", "working", "working", "full")
CELLS = (("py314", 500), ("py314", 2000), ("py311", 500), ("py311", 2000))
CASE_TIMEOUT_SECONDS = 300
MAX_CHILD_SUMMARY_BYTES = 64 * 1024
MAX_CHILD_SUMMARY_STRING = 256
EXPECTED_LIMITS = {
    "ledgerBytes": 1_048_576,
    "identities": 4096,
    "frameBytes": 8_404_992,
    "encodedBytes": 64 * 1024 * 1024,
    "serviceClients": 16,
}
EXPECTED_OBSERVER_MANIFEST_SHA256 = "c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877"
EXPECTED_OBSERVER_ARCHIVE_SHA256 = "a1785e81f1f998a134cf23f283eb638f398b681395ab71a4c69948f26e78c47e"
EXPECTED_MESH_MANIFEST_SHA256 = "48794aa52c889a480bde024bd8c68f2dc82cf49955fdcbee12d21b377072ae53"
EXPECTED_MESH_ARCHIVE_SHA256 = "4010bee06a40619fad5f8b0ceebdf971c544df6ce4d0f57f98018cede11a39de"


class HarnessError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _verify_export(source_root: Path, manifest_path: Path, manifest_sha: str,
                   archive_path: Path, archive_sha: str, commit: str) -> dict[str, Any]:
    source_root = source_root.resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    archive_path = archive_path.resolve(strict=True)
    if _sha256(manifest_path) != manifest_sha:
        raise HarnessError("source_manifest_hash_mismatch")
    if _sha256(archive_path) != archive_sha:
        raise HarnessError("source_archive_hash_mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError("source_manifest_unreadable") from error
    files = manifest.get("files")
    if (manifest.get("commit") != commit
            or manifest.get("archiveSha256") != archive_sha
            or type(files) is not dict
            or manifest.get("fileCount") != len(files)):
        raise HarnessError("source_manifest_identity_mismatch")
    expected_paths: set[str] = set()
    for relative, expected_hash in files.items():
        if type(relative) is not str or type(expected_hash) is not str:
            raise HarnessError("source_manifest_entry_invalid")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise HarnessError("source_manifest_path_invalid")
        target = (source_root / relative_path).resolve(strict=True)
        if not target.is_relative_to(source_root) or not target.is_file():
            raise HarnessError("source_manifest_path_escape")
        if _sha256(target) != expected_hash:
            raise HarnessError("source_file_hash_mismatch")
        expected_paths.add(relative_path.as_posix())
    actual_paths = {
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if actual_paths != expected_paths:
        raise HarnessError("source_file_set_mismatch")
    return manifest


def _approved_config(*, require_capture: bool) -> dict[str, Any]:
    try:
        config = json.loads(PAIR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError("source_pair_config_unreadable") from error
    if config.get("schema") != "private.sdk-pipeline.serial-watch4.v3.8.source-pair.v1":
        raise HarnessError("source_pair_config_schema")
    expected_pair = (
        "b176ac06b39daeead4be0a33ff9d781304091fe0"
        "+b9e8488e0f0fa438119e36848ac7c9887038ea1c"
    )
    if (config.get("observerId") != expected_pair.split("+", 1)[0]
            or config.get("meshId") != expected_pair.split("+", 1)[1]
            or config.get("approvedSourcePair") != expected_pair):
        raise HarnessError("source_pair_not_exact_final_pair")
    if require_capture and (
        config.get("status") != "approved-by-root-for-v3.8-cpu-matrix"
        or config.get("captureAuthorized") is not True
    ):
        raise HarnessError("awaiting_parent_timing_block_review_and_capture_authorization")
    observer_root = Path(config["observerSource"]).resolve(strict=True)
    observer_tests = Path(config["observerTests"]).resolve(strict=True)
    matched = Path(config["matchedSource"]).resolve(strict=True)
    mesh_root = Path(config["meshSource"]).resolve(strict=True)
    mesh_export_root = Path(config["meshExportRoot"]).resolve(strict=True)
    expected_observer_root = Path(
        "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06"
    ).resolve()
    expected_mesh_export_root = Path(
        "/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-b9e8488e"
    ).resolve()
    if observer_root != expected_observer_root:
        raise HarnessError("observer_root_not_exact_immutable_export")
    if (observer_tests != observer_root / "tests"
            or matched != observer_root / "docs/evidence/2026-10-18-working-set/"
            "performance-source/read_matched.py"):
        raise HarnessError("observer_fixture_paths_not_exact")
    if (mesh_export_root != expected_mesh_export_root
            or mesh_root != expected_mesh_export_root / "src"):
        raise HarnessError("mesh_import_root_not_exact_export_src")
    expected_pins = {
        "observerSourceManifestSha256": EXPECTED_OBSERVER_MANIFEST_SHA256,
        "observerSourceArchiveSha256": EXPECTED_OBSERVER_ARCHIVE_SHA256,
        "meshSourceManifestSha256": EXPECTED_MESH_MANIFEST_SHA256,
        "meshSourceArchiveSha256": EXPECTED_MESH_ARCHIVE_SHA256,
    }
    if any(config.get(key) != value for key, value in expected_pins.items()):
        raise HarnessError("source_pair_manifest_or_archive_pin_mismatch")
    expected_metadata_paths = {
        "observerSourceManifestPath": Path(
            "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06-manifest.json"
        ),
        "observerSourceArchivePath": Path(
            "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06.tar"
        ),
        "meshSourceManifestPath": Path(
            "/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-b9e8488e-manifest.json"
        ),
        "meshSourceArchivePath": Path(
            "/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-b9e8488e.tar"
        ),
    }
    if any(Path(config.get(key, "")).resolve() != value.resolve()
           for key, value in expected_metadata_paths.items()):
        raise HarnessError("source_pair_metadata_path_mismatch")
    if require_capture:
        _verify_export(
            observer_root,
            Path(config["observerSourceManifestPath"]),
            config["observerSourceManifestSha256"],
            Path(config["observerSourceArchivePath"]),
            config["observerSourceArchiveSha256"],
            config["observerId"],
        )
        _verify_export(
            mesh_export_root,
            Path(config["meshSourceManifestPath"]),
            config["meshSourceManifestSha256"],
            Path(config["meshSourceArchivePath"]),
            config["meshSourceArchiveSha256"],
            config["meshId"],
        )
        if not (observer_root / "agent_observer").is_dir() or not (observer_tests / "test_service_runtime.py").is_file():
            raise HarnessError("observer_source_layout_mismatch")
        if not (mesh_root / "mesh_plus").is_dir():
            raise HarnessError("mesh_source_layout_mismatch")
        config["meshImportRelative"] = mesh_root.relative_to(mesh_export_root).as_posix()
    return config


def _validate_loaded_module_map(
    loaded: Any,
    manifests: dict[str, dict[str, str]],
    mesh_import_relative: Path,
) -> None:
    if not isinstance(loaded, dict) or not loaded:
        raise HarnessError("loaded_project_module_pins_missing")
    roots = {entry.get("root") for entry in loaded.values() if isinstance(entry, dict)}
    if roots != {"agent_observer", "mesh_plus"}:
        raise HarnessError("loaded_project_module_root_mismatch")
    for entry in loaded.values():
        root = entry.get("root")
        relative = entry.get("path")
        if (root not in manifests or type(relative) is not str
                or Path(relative).is_absolute() or ".." in Path(relative).parts):
            raise HarnessError("loaded_project_module_path_mismatch")
        manifest_relative = Path(relative)
        if root == "mesh_plus":
            manifest_relative = mesh_import_relative / manifest_relative
        if manifests[root].get(manifest_relative.as_posix()) != entry.get("sha256"):
            raise HarnessError("loaded_project_module_hash_mismatch")


def _validate_cpu_measurement(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HarnessError("cpu_measurement_missing")
    labels = set(EXCLUSION_LABELS)
    excluded = value.get("excludedMainThreadCpuNsByLabel")
    counts = value.get("excludedBlockCountsByLabel")
    if (not isinstance(excluded, dict) or set(excluded) != labels
            or not isinstance(counts, dict) or set(counts) != labels):
        raise HarnessError("cpu_exclusion_labels_incomplete")
    if (any(type(item) is not int or item < 0 for item in excluded.values())
            or any(type(item) is not int or item < 0 for item in counts.values())):
        raise HarnessError("cpu_exclusion_counter_invalid")
    raw = value.get("rawProcessCpuNs")
    excluded_total = value.get("excludedMainThreadCpuNs")
    adjusted = value.get("adjustedProcessCpuNs")
    if (type(raw) is not int or type(excluded_total) is not int or type(adjusted) is not int
            or raw < 0 or excluded_total < 0 or adjusted < 0
            or sum(excluded.values()) != excluded_total
            or raw - excluded_total != adjusted):
        raise HarnessError("cpu_measurement_arithmetic_invalid")
    if (value.get("otherThreadCpuDuringExclusionsIncluded") is not True
            or value.get("exclusionNestedIntervalsCountedOnce") is not True
            or type(value.get("windowStartThreadId")) is not int):
        raise HarnessError("cpu_measurement_contract_metadata_missing")
    return {"rawProcessCpuNs": raw, "excludedMainThreadCpuNs": excluded_total,
            "adjustedProcessCpuNs": adjusted, "excludedBlockCountsByLabel": counts,
            "excludedMainThreadCpuNsByLabel": excluded}


def _validate_case_report(report_path: Path, config: dict[str, Any], *, interpreter_name: str,
                          rows: int, variant: str, trial_index: int,
                          runner_sha256: str) -> dict[str, Any]:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError("cpu_report_unreadable") from error
    if (report.get("format") != "agent-observer.working-set.sdk-pipeline-matrix.v3.8-serial-watch4-cpu"
            or report.get("mode") != "serial-watch4-cpu"
            or report.get("timed") is not True
            or report.get("sourcePair") != config["approvedSourcePair"]
            or report.get("cyclicGc", {}).get("enabled") is not False
            or report.get("cyclicGc", {}).get("explicitCollections") != 0
            or report.get("rssSnapshots") != []):
        raise HarnessError("cpu_report_identity_or_gc_contract_mismatch")
    shape = report.get("configuredShape") or {}
    selected = {100: 2, 500: 4, 2000: 20}[rows]
    if (shape.get("rows") != [rows] or shape.get("generations") != 3
            or shape.get("watchAdmissionsPerGeneration") != 4
            or shape.get("totalWatchAdmissions") != 12
            or shape.get("facadeDtoReadsPerAdmission") != 1
            or shape.get("outerAcquisitionWaitSeconds") != 15.0):
        raise HarnessError("cpu_report_configured_shape_mismatch")
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != 1:
        raise HarnessError("cpu_report_case_count_mismatch")
    case = cases[0]
    if (case.get("trialIndex") != trial_index or case.get("variant") != variant
            or case.get("rows") != rows or case.get("selectedRows") != selected
            or len(case.get("generations", [])) != 3):
        raise HarnessError("cpu_report_case_identity_mismatch")
    source_inputs = case.get("sourceInputs") or {}
    if (source_inputs.get("observerId") != config["observerId"]
            or source_inputs.get("meshId") != config["meshId"]
            or source_inputs.get("approvedSourcePair") != config["approvedSourcePair"]
            or Path(source_inputs.get("observerSource", "/nonexistent")).resolve()
            != Path(config["observerSource"]).resolve()
            or Path(source_inputs.get("meshSource", "/nonexistent")).resolve()
            != Path(config["meshSource"]).resolve()
            or source_inputs.get("limits") != EXPECTED_LIMITS):
        raise HarnessError("cpu_report_source_inputs_mismatch")
    manifests = {
        "agent_observer": json.loads(Path(config["observerSourceManifestPath"]).read_text(encoding="utf-8"))["files"],
        "mesh_plus": json.loads(Path(config["meshSourceManifestPath"]).read_text(encoding="utf-8"))["files"],
    }
    loaded = report.get("loadedProjectModules")
    if _canonical_sha256(loaded) != report.get("sourceModuleMapSha256"):
        raise HarnessError("loaded_project_module_map_hash_mismatch")
    _validate_loaded_module_map(loaded, manifests, Path(config["meshImportRelative"]))
    loaded_counts = {
        root: sum(1 for entry in loaded.values() if entry.get("root") == root)
        for root in ("agent_observer", "mesh_plus")
    }

    all_request_hashes: list[str] = []
    all_nonce_hashes: list[str] = []
    for expected_generation, generation in enumerate(case["generations"], 1):
        admissions = generation.get("watchAdmissions")
        if (generation.get("accepted") is not True
                or generation.get("generation") != expected_generation
                or not isinstance(admissions, list) or len(admissions) != 4):
            raise HarnessError("cpu_generation_or_admission_count_mismatch")
        if (generation.get("watchRequestIdsDistinct") is not True
                or generation.get("proofNoncesDistinct") is not True
                or generation.get("allDtoHashesMatchExpected") is not True
                or generation.get("selectedCanonicalBodyAtMostQuarterOfFull") is not True):
            raise HarnessError("cpu_generation_distinctness_dto_or_quarter_gate_failed")
        full_bytes = generation.get("fullCanonicalBodyBytes")
        selected_bytes = generation.get("selectedCanonicalBodyBytes")
        if (type(full_bytes) is not int or type(selected_bytes) is not int
                or full_bytes <= 0 or selected_bytes < 0 or selected_bytes * 4 > full_bytes):
            raise HarnessError("cpu_generation_body_ratio_invalid")
        generation_expected_hash = generation.get("expectedDtoSha256")
        generation_ids_hash = generation.get("expectedIdsSha256")
        if (not isinstance(generation_expected_hash, str) or len(generation_expected_hash) != 64
                or not isinstance(generation_ids_hash, str) or len(generation_ids_hash) != 64):
            raise HarnessError("cpu_generation_expected_hash_missing")
        for watch_index, admission in enumerate(admissions, 1):
            if (admission.get("generation") != expected_generation
                    or admission.get("watchIndex") != watch_index):
                raise HarnessError("cpu_admission_order_mismatch")
            request_hash = admission.get("requestIdSha256")
            nonce_hash = admission.get("targetProofNonceSha256")
            if (not isinstance(request_hash, str) or len(request_hash) != 64
                    or not isinstance(nonce_hash, str) or len(nonce_hash) != 64):
                raise HarnessError("cpu_admission_request_or_nonce_hash_missing")
            all_request_hashes.append(request_hash)
            all_nonce_hashes.append(nonce_hash)
            event = admission.get("targetEvent") or {}
            witness = admission.get("publicPublisherDigestWitness") or {}
            if (event.get("runtimeAccepted") != expected_generation
                    or event.get("meshStatus") != "complete"
                    or event.get("hostDeliveryStatus") != "ready"
                    or event.get("hostViewState") != "current"
                    or event.get("proofPresent") is not True
                    or event.get("proofFresh") is not True
                    or event.get("proofNonceSha256") != nonce_hash
                    or event.get("requestIdMatchesAdmission") is not True
                    or type(event.get("proofRttMs")) is not int
                    or not 0 <= event["proofRttMs"] <= 2000
                    or not any(receipt.get("accepted") == expected_generation
                               and receipt.get("health") == "current"
                               for receipt in event.get("receiptRuntime", []))):
                raise HarnessError("cpu_admission_target_proof_or_receipt_mismatch")
            if (admission.get("facadeCurrentContextPresent") is not True
                    or admission.get("facadeIdentityOrderMatches") is not True
                    or admission.get("facadeDtoSha256") != generation_expected_hash
                    or admission.get("expectedDtoSha256") != generation_expected_hash
                    or admission.get("expectedIdsSha256") != generation_ids_hash
                    or admission.get("nativeDtoMatchesExpected") is not True
                    or admission.get("nativeFrameMatchesPublicPublisherDigest") is not True
                    or not admission.get("nativeFullSelectionMatchesExpected")):
                raise HarnessError("cpu_admission_dto_or_public_digest_mismatch")
            native_digest = admission.get("nativeOwnerDigest")
            frame_hash = admission.get("nativeFrameSha256")
            if (native_digest != "sha256:" + str(frame_hash)
                    or witness.get("operation") != "proof"
                    or witness.get("runtimeAccepted") != expected_generation
                    or witness.get("ownerDigest") != native_digest
                    or witness.get("ownerDigest") != event.get("proofPayloadDigest")
                    or witness.get("nonceSha256") != nonce_hash):
                raise HarnessError("cpu_admission_exact_public_digest_witness_mismatch")
            if variant == "working" and admission.get("workingScopeComplete") is not True:
                raise HarnessError("cpu_working_scope_incomplete")
            connection = admission.get("connectionDiagnostics") or {}
            source_after = connection.get("sourceOutstandingAfterClose") or {}
            reader_after = connection.get("readerCountsAfterClose") or {}
            if (connection.get("streamClosedBeforeNextAdmission") is not True
                    or source_after != {
                        "activeSourceOperations": 0,
                        "pendingSnapshotCalls": 0,
                        "openWatchIterators": 0,
                    }
                    or reader_after.get("activeConnections") != 0
                    or reader_after.get("connectionsOpened") != reader_after.get("connectionsClosed")):
                raise HarnessError("cpu_admission_retirement_mismatch")
    if len(set(all_request_hashes)) != 12 or len(set(all_nonce_hashes)) != 12:
        raise HarnessError("cpu_trial_request_or_nonce_not_unique")

    cleanup = case.get("cleanupCounts") or {}
    runtime = cleanup.get("runtime") or {}
    source = cleanup.get("cachedSourceWrapper") or {}
    if (cleanup.get("readerActiveConnections") != 0
            or cleanup.get("readerConnectionsOpened") != cleanup.get("readerConnectionsClosed")
            or cleanup.get("readerCleanupFailures") != 0
            or cleanup.get("bridgeActiveHandlers") != 0
            or cleanup.get("bridgeHandlersStarted") != (
                cleanup.get("bridgeHandlersReturned", -1) + cleanup.get("bridgeHandlersRaised", -1)
            )
            or cleanup.get("refusedConnectedClients") != 0
            or cleanup.get("failedPublicConnects") != 0
            or cleanup.get("bridgeOverflowConnections") != 0
            or source != {"activeSourceOperations": 0, "pendingSnapshotCalls": 0, "openWatchIterators": 0}
            or runtime.get("runtimePeersAfterRun") != 0
            or runtime.get("runtimeThreadAlive") is not False
            or runtime.get("selectorRegistrationsAfterRun") != 0
            or runtime.get("selectorClosed") is not True
            or runtime.get("selectorHookRestored") is not True):
        raise HarnessError("cpu_final_cleanup_unbalanced")
    cpu = _validate_cpu_measurement(case.get("cpuMeasurement"))
    return {
        "status": "pass",
        "interpreter": interpreter_name,
        "rows": rows,
        "variant": variant,
        "trialIndex": trial_index,
        "runnerSha256": runner_sha256,
        "reportSha256": _sha256(report_path),
        "sourceModuleMapSha256": report["sourceModuleMapSha256"],
        "loadedProjectModuleCounts": loaded_counts,
        "adjustedProcessCpuNs": cpu["adjustedProcessCpuNs"],
        "rawProcessCpuNs": cpu["rawProcessCpuNs"],
        "excludedMainThreadCpuNs": cpu["excludedMainThreadCpuNs"],
        "excludedMainThreadCpuNsByLabel": cpu["excludedMainThreadCpuNsByLabel"],
        "selectedCanonicalBodyBytes": [g["selectedCanonicalBodyBytes"] for g in case["generations"]],
        "fullCanonicalBodyBytes": [g["fullCanonicalBodyBytes"] for g in case["generations"]],
        "quarterBodyGate": True,
        "functionalAndCleanupPass": True,
    }


def _safe_child_summary(value: str | bytes | None) -> dict[str, Any] | None:
    if value is None:
        return None
    raw = value.encode("utf-8", "replace") if isinstance(value, str) else value
    if len(raw) > MAX_CHILD_SUMMARY_BYTES:
        return {"summaryOmitted": "child_output_exceeds_summary_bound"}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    result: dict[str, Any] = {}
    for key in ("status", "error", "code", "output", "sourcePair", "timed", "moduleMapSha256"):
        item = parsed.get(key)
        if isinstance(item, str):
            result[key] = item[:MAX_CHILD_SUMMARY_STRING]
        elif isinstance(item, (bool, int)) or item is None:
            result[key] = item
    if isinstance(parsed.get("cases"), list):
        result["casesCount"] = len(parsed["cases"])
    return result


def _run_child(argv: list[str], env: dict[str, str]):
    try:
        return subprocess.run(
            argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, timeout=CASE_TIMEOUT_SECONDS, check=False,
        ), None
    except subprocess.TimeoutExpired as error:
        return None, error


def _record_child_streams(case_dir: Path, stdout: str | bytes | None,
                          stderr: str | bytes | None) -> dict[str, Any]:
    def record(label: str, value: str | bytes | None) -> dict[str, Any]:
        raw = b"" if value is None else value.encode("utf-8", "replace") if isinstance(value, str) else value
        return {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "summary": _safe_child_summary(raw),
        }
    return {"stdout": record("stdout", stdout), "stderr": record("stderr", stderr)}


def _freeze_case_sources(case_dir: Path) -> dict[str, Path]:
    if _sha256(CPU_HELPER) != CPU_HELPER_SHA256:
        raise HarnessError("cpu_helper_changed")
    frozen = {}
    for source in (HARNESS, PAIR_CONFIG, Path(__file__), CPU_HELPER):
        target = case_dir / source.name
        shutil.copyfile(source, target)
        os.chmod(target, 0o600)
        frozen[source.name] = target
    return frozen


def _run_one_case(
    *, run_root: Path, cell_dir: Path, config: dict[str, Any],
    interpreter_name: str, rows: int, variant: str, trial_index: int,
    abba_position: int, controller_sha256: str,
) -> dict[str, Any]:
    interpreter = INTERPRETERS[interpreter_name]
    case_dir = cell_dir / f"{abba_position:02d}-{variant}-trial-{trial_index:02d}"
    case_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    frozen = _freeze_case_sources(case_dir)
    runner_copy = frozen[HARNESS.name]
    config_copy = frozen[PAIR_CONFIG.name]
    controller_copy = frozen[Path(__file__).name]
    report_path = case_dir / "report.json"
    argv = [
        "rtk", "proxy", str(interpreter), str(runner_copy),
        "--observer-source", config["observerSource"],
        "--observer-tests", config["observerTests"],
        "--mesh-source", config["meshSource"],
        "--matched-source", config["matchedSource"],
        "--observer-id", config["observerId"],
        "--mesh-id", config["meshId"],
        "--approved-source-pair", config["approvedSourcePair"],
        "--variant", variant,
        "--trial-index", str(trial_index),
        "--mode", "cpu",
        "--rows", str(rows),
        "--generations", "3",
        "--watch-admissions-per-generation", "4",
        "--output", str(report_path),
    ]
    invocation = {
        "cell": cell_dir.name,
        "abbaPosition": abba_position,
        "interpreterName": interpreter_name,
        "interpreter": str(interpreter),
        "rows": rows,
        "variant": variant,
        "trialIndex": trial_index,
        "argv": argv,
        "runnerSha256": _sha256(runner_copy),
        "cpuHelperSha256": _sha256(frozen[CPU_HELPER.name]),
        "controllerSha256": controller_sha256,
        "controllerCopySha256": _sha256(controller_copy),
        "sourceConfigSha256": _sha256(config_copy),
        "observerManifestSha256": config["observerSourceManifestSha256"],
        "observerArchiveSha256": config["observerSourceArchiveSha256"],
        "meshManifestSha256": config["meshSourceManifestSha256"],
        "meshArchiveSha256": config["meshSourceArchiveSha256"],
        "classification": "timed serial-watch4 CPU trial; no wire meter installed",
    }
    _write_json(case_dir / "invocation.json", invocation)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result: dict[str, Any] = {
        "caseDir": str(case_dir),
        "interpreter": interpreter_name,
        "rows": rows,
        "variant": variant,
        "trialIndex": trial_index,
        "invocationSha256": _sha256(case_dir / "invocation.json"),
        "reportPath": str(report_path),
    }
    completed, timeout = _run_child(argv, env)
    if timeout is not None:
        result.update({
            "status": "timed_out",
            "timeoutSeconds": CASE_TIMEOUT_SECONDS,
            "ownedChildProcessKilledAndWaited": True,
            "applicationCleanupVerified": False,
            "functionalAndCleanupPass": False,
            "streams": _record_child_streams(case_dir, timeout.stdout, timeout.stderr),
        })
        _write_json(case_dir / "case-result.json", result)
        _write_json(run_root / "progress.json", {"status": "stopped_on_timeout", "case": result})
        return result
    assert completed is not None
    result["exitCode"] = completed.returncode
    result["streams"] = _record_child_streams(case_dir, completed.stdout, completed.stderr)
    if completed.returncode != 0 or not report_path.is_file():
        result.update({"status": "child_failed", "reportExists": report_path.is_file()})
        _write_json(case_dir / "case-result.json", result)
        return result
    try:
        verified = _validate_case_report(
            report_path, config, interpreter_name=interpreter_name, rows=rows,
            variant=variant, trial_index=trial_index, runner_sha256=invocation["runnerSha256"],
        )
    except Exception as error:
        result.update({
            "status": "validation_failed",
            "errorType": type(error).__name__,
            "errorCode": str(error)[:128],
            "reportSha256": _sha256(report_path),
        })
        _write_json(case_dir / "case-result.json", result)
        return result
    result.update(verified)
    _write_json(case_dir / "case-result.json", result)
    return result


def _fraction_median(values: list[int]) -> dict[str, int | str]:
    if len(values) != 2 or any(type(value) is not int or value < 0 for value in values):
        raise HarnessError("cpu_median_requires_two_whole_trial_totals")
    numerator = sum(values)
    if numerator % 2 == 0:
        median = numerator // 2
        return {"numeratorNs": median, "denominator": 1, "exact": str(median)}
    return {"numeratorNs": numerator, "denominator": 2,
            "exact": f"{numerator}/2"}


def _cell_result(case_results: list[dict[str, Any]], *, interpreter_name: str,
                 rows: int) -> dict[str, Any]:
    if len(case_results) != 4 or any(case.get("status") != "pass" for case in case_results):
        return {"status": "incomplete_or_failed", "comparisonEligible": False,
                "cases": case_results}
    if [item["variant"] for item in case_results] != list(ABBA_ORDER):
        raise HarnessError("abba_order_mismatch")
    full = [item["adjustedProcessCpuNs"] for item in (case_results[0], case_results[3])]
    working = [item["adjustedProcessCpuNs"] for item in (case_results[1], case_results[2])]
    quarter_pass = all(item.get("quarterBodyGate") is True for item in case_results)
    return {
        "status": "pass",
        "interpreter": interpreter_name,
        "rows": rows,
        "abbaOrder": [item["variant"] for item in case_results],
        "fullTrialAdjustedProcessCpuNs": full,
        "workingTrialAdjustedProcessCpuNs": working,
        "fullMedianWholeTrialAdjustedProcessCpuNs": _fraction_median(full),
        "workingMedianWholeTrialAdjustedProcessCpuNs": _fraction_median(working),
        "comparisonEligible": all(item.get("functionalAndCleanupPass") is True for item in case_results)
        and quarter_pass,
        "quarterBodyPrerequisitePassed": quarter_pass,
        "medianBasis": "two complete trial totals per variant within this ABBA cell",
    }


def _verify_interpreter(interpreter_name: str, env: dict[str, str]) -> str:
    interpreter = INTERPRETERS[interpreter_name]
    if not interpreter.is_file():
        raise HarnessError(f"interpreter_missing:{interpreter_name}")
    completed = subprocess.run(
        ["rtk", "proxy", str(interpreter), "--version"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, timeout=15, check=False,
    )
    text = (completed.stdout + completed.stderr).strip()
    prefix = "Python 3.14." if interpreter_name == "py314" else "Python 3.11."
    if completed.returncode != 0 or not text.startswith(prefix):
        raise HarnessError(f"interpreter_version_mismatch:{interpreter_name}")
    return text


def _run_cell(run_root: Path, config: dict[str, Any], interpreter_name: str,
              rows: int, trial_index_start: int, controller_sha256: str) -> dict[str, Any]:
    if not SHARED_LOCK.is_file():
        raise HarnessError("shared_cpu_lock_missing")
    cell_dir = run_root / f"{interpreter_name}-{rows}-abba"
    cell_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    python_version = _verify_interpreter(interpreter_name, env)
    case_results: list[dict[str, Any]] = []
    with SHARED_LOCK.open("r+b") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        for position, variant in enumerate(ABBA_ORDER, 1):
            result = _run_one_case(
                run_root=run_root, cell_dir=cell_dir, config=config,
                interpreter_name=interpreter_name, rows=rows, variant=variant,
                trial_index=trial_index_start + position - 1,
                abba_position=position, controller_sha256=controller_sha256,
            )
            result["pythonVersion"] = python_version
            case_results.append(result)
            _write_json(cell_dir / "progress.json", {
                "completedCases": case_results,
                "nextAbbaPosition": position + 1,
            })
            if result.get("status") != "pass":
                return {"status": "failed", "interpreter": interpreter_name,
                        "rows": rows, "cases": case_results,
                        "comparisonEligible": False}
    cell = _cell_result(case_results, interpreter_name=interpreter_name, rows=rows)
    cell["pythonVersion"] = python_version
    _write_json(cell_dir / "cell-result.json", cell)
    return cell


def _plan(config: dict[str, Any]) -> dict[str, Any]:
    trial_index = 0
    cells = []
    for interpreter_name, rows in CELLS:
        cases = []
        for position, variant in enumerate(ABBA_ORDER, 1):
            cases.append({
                "abbaPosition": position,
                "variant": variant,
                "trialIndex": trial_index,
                "argvTemplate": [
                    "rtk", "proxy", str(INTERPRETERS[interpreter_name]),
                    str(HARNESS),
                    "--observer-source", config["observerSource"],
                    "--observer-tests", config["observerTests"],
                    "--mesh-source", config["meshSource"],
                    "--matched-source", config["matchedSource"],
                    "--observer-id", config["observerId"],
                    "--mesh-id", config["meshId"],
                    "--approved-source-pair", config["approvedSourcePair"],
                    "--mode", "cpu", "--rows", str(rows),
                    "--variant", variant, "--trial-index", str(trial_index),
                    "--generations", "3", "--watch-admissions-per-generation", "4",
                    "--output", "<private-case-report.json>",
                ],
            })
            trial_index += 1
        cells.append({"interpreter": interpreter_name, "rows": rows,
                      "abbaOrder": list(ABBA_ORDER), "cases": cases})
    return {
        "status": "plan_only_no_pipeline_execution",
        "captureAuthorized": config.get("captureAuthorized") is True,
        "sourcePair": config.get("approvedSourcePair"),
        "configStatus": config.get("status"),
        "cells": cells,
        "trialCount": trial_index,
        "caseWallTimeoutSeconds": CASE_TIMEOUT_SECONDS,
        "lock": str(SHARED_LOCK),
        "wholeTrialCpuMedianBasis": "two complete process CPU totals per variant per ABBA cell",
    }


def _run_matrix() -> int:
    config = _approved_config(require_capture=True)
    if not HARNESS.is_file():
        raise HarnessError("cpu_harness_missing")
    if not SHARED_LOCK.is_file():
        raise HarnessError("shared_cpu_lock_missing")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = RUNS_ROOT / run_id
    run_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    controller_sha = _sha256(Path(__file__).resolve())
    harness_sha = _sha256(HARNESS)
    _write_json(run_root / "run-pins.json", {
        "sourcePair": config["approvedSourcePair"],
        "observerManifestSha256": config["observerSourceManifestSha256"],
        "observerArchiveSha256": config["observerSourceArchiveSha256"],
        "meshManifestSha256": config["meshSourceManifestSha256"],
        "meshArchiveSha256": config["meshSourceArchiveSha256"],
        "controllerSha256": controller_sha,
        "harnessSha256": harness_sha,
        "configSha256": _sha256(PAIR_CONFIG),
        "caseTimeoutSeconds": CASE_TIMEOUT_SECONDS,
        "matrixCells": CELLS,
        "abbaOrder": ABBA_ORDER,
    })
    cell_results = []
    trial_index_start = 0
    for interpreter_name, rows in CELLS:
        cell = _run_cell(run_root, config, interpreter_name, rows,
                         trial_index_start, controller_sha)
        cell_results.append(cell)
        trial_index_start += len(ABBA_ORDER)
        _write_json(run_root / "progress.json", {
            "completedCells": cell_results,
            "nextCellIndex": len(cell_results),
        })
        if cell.get("status") != "pass":
            result = {
                "format": "private.sdk-pipeline.serial-watch4.v3.8.cpu-matrix.v1",
                "status": "stopped_after_cell_failure",
                "sourcePair": config["approvedSourcePair"],
                "completedCells": cell_results,
                "comparisonEligible": False,
                "pipelineExecutionStopped": True,
            }
            _write_json(run_root / "result.json", result)
            print(json.dumps({"status": result["status"], "runRoot": str(run_root),
                              "failedCell": cell}, sort_keys=True))
            return 1
    result = {
        "format": "private.sdk-pipeline.serial-watch4.v3.8.cpu-matrix.v1",
        "status": "pass" if all(cell.get("comparisonEligible") is True for cell in cell_results) else "functional_pass_quarter_gate_failed",
        "sourcePair": config["approvedSourcePair"],
        "completedCells": cell_results,
        "comparisonEligible": all(cell.get("comparisonEligible") is True for cell in cell_results),
        "pipelineExecutionStopped": False,
        "scope": "serial public watch acquisitions with local facade copies; whole-trial Python process CPU after named main-thread harness exclusions; no RSS or wire claim",
    }
    _write_json(run_root / "result.json", result)
    print(json.dumps({"status": result["status"], "runRoot": str(run_root),
                      "resultSha256": _sha256(run_root / "result.json"),
                      "comparisonEligible": result["comparisonEligible"]}, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--print-plan", action="store_true")
    group.add_argument("--run-approved-matrix", action="store_true")
    args = parser.parse_args()
    try:
        config = _approved_config(require_capture=False)
        if args.run_approved_matrix:
            return _run_matrix()
        print(json.dumps(_plan(config), sort_keys=True, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "refused_or_failed_before_run",
                          "errorType": type(error).__name__,
                          "code": str(error)[:160]}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
