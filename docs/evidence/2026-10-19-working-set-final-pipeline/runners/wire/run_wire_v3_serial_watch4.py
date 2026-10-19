#!/usr/bin/env python3
"""Prepare or run the gated serial-watch4 kernel-write capture matrix.

Plan-only validation reads immutable source manifests and audits the Python
send dispatch. Application cases require a separately reviewed config edit.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRIVATE_ROOT = Path(__file__).resolve().parent
PAIR_CONFIG = PRIVATE_ROOT / "approved-source-pair.json"
HARNESS = PRIVATE_ROOT / "sdk_pipeline_wire_serial_watch4_v3.py"
METER = PRIVATE_ROOT / "socket_meter_v2.py"
METER_TESTS = PRIVATE_ROOT / "test_socket_meter_v2.py"
CPU_HELPER = PRIVATE_ROOT / "cpu_exclusions_v3_8.py"
V2_HELPER = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/"
    "sdk-pipeline-matrix/wire-v2/sdk_pipeline_wire_v2.py"
)
V2_HELPER_SHA256 = "33ea9a2dd29de1fcb2c2db88cce8aeb6e4a61aeb54a9e99de1d59117d75bdbbc"
ORIGINAL_METER_SHA256 = "c06e8371084122616ea983305e42f60d5f302308dd25f0e5d59ae756d8cdb8c6"
METER_SHA256 = "8d2bd32980d54d96d2b82c5c9821ba1ba5dbd095676114c6d3a97154dc15f80b"
METER_TESTS_SHA256 = "03eaa491d3e678c03060b1065625240427a932237b2f3f6acc9fa658b3601eed"
V38_HARNESS_SHA256 = "786d050b4220f068ef661f71d5a96955dc4cd5499f6c0080610925ae00d7f63e"
V38_CPU_HELPER_SHA256 = "aa1d63a8d67e3e0ebd90069a55aa5330194efeb95d907cdc074a810a10baf3bb"
V38_CONFIG_SHA256 = "755bcdf1893ab9588a6eda9a817a5bef881217d756e1e102b38a49f453ea97f8"
V38_ROOT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/sdk-pipeline-matrix/v3/v3.8-serial-watch4")
V38_HARNESS = V38_ROOT / "sdk_pipeline_matrix_v3_8_serial_watch4.py"
V38_SOURCE_CPU_HELPER = V38_ROOT / "cpu_exclusions_v3_8.py"
V38_CONFIG = V38_ROOT / "approved-source-pair.json"
SHARED_LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
RUNS_ROOT = PRIVATE_ROOT / "runs"
INTERPRETERS = {
    "py314": Path("/home/bryan/code/mesh-plus/.venv/bin/python"),
    "py311": Path("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"),
}
ROWS = (500, 2000)
VARIANTS = ("full", "working")
INTERPRETER_ORDER = ("py314", "py311")
SELECTED_ROWS = {500: 4, 2000: 20}
CASE_TIMEOUT_SECONDS = 300
MAX_CHILD_OUTPUT_BYTES = 64 * 1024
MAX_CHILD_SUMMARY_STRING = 256
EXPECTED_PAIR = (
    "b176ac06b39daeead4be0a33ff9d781304091fe0"
    "+b9e8488e0f0fa438119e36848ac7c9887038ea1c"
)
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


def _dispatch_audit(config: dict[str, Any]) -> dict[str, Any]:
    if _sha256(V2_HELPER) != V2_HELPER_SHA256:
        raise HarnessError("reviewed_wire_v2_dispatch_helper_hash_mismatch")
    if _sha256(METER) != METER_SHA256:
        raise HarnessError("reviewed_wire_v2_meter_hash_mismatch")
    if _sha256(METER_TESTS) != METER_TESTS_SHA256:
        raise HarnessError("reviewed_wire_v2_meter_test_hash_mismatch")
    if (not HARNESS.is_file() or _sha256(CPU_HELPER) != V38_CPU_HELPER_SHA256
            or _sha256(V38_HARNESS) != V38_HARNESS_SHA256
            or _sha256(V38_SOURCE_CPU_HELPER) != V38_CPU_HELPER_SHA256
            or _sha256(V38_CONFIG) != V38_CONFIG_SHA256):
        raise HarnessError("v3_8_lineage_or_local_helper_hash_mismatch")
    if str(PRIVATE_ROOT) not in sys.path:
        sys.path.insert(0, str(PRIVATE_ROOT))
    spec = importlib.util.spec_from_file_location("wire_v2_dispatch_helper", V2_HELPER)
    if spec is None or spec.loader is None:
        raise HarnessError("wire_dispatch_helper_load_failed")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    audit = helper._audit_target_io_dispatch(
        Path(config["observerSource"]), Path(config["meshSource"])
    )
    if audit.get("result") != "static_target_paths_clear":
        raise HarnessError("static_target_io_dispatch_not_clear")
    return audit


def _approved_config(*, require_capture: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        config = json.loads(PAIR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError("source_pair_config_unreadable") from error
    if config.get("schema") != "private.sdk-pipeline.wire-v3-serial-watch4.source-pair.v1":
        raise HarnessError("source_pair_config_schema")
    if (config.get("observerId") + "+" + config.get("meshId") != EXPECTED_PAIR
            or config.get("approvedSourcePair") != EXPECTED_PAIR):
        raise HarnessError("source_pair_not_exact_final_pair")
    if require_capture and (
        config.get("status") != "approved-by-root-for-wire-v3-serial-watch4-captures"
        or config.get("captureAuthorized") is not True
    ):
        raise HarnessError("wire_capture_authorization_missing")
    observer_root = Path(config["observerSource"]).resolve(strict=True)
    observer_tests = Path(config["observerTests"]).resolve(strict=True)
    matched = Path(config["matchedSource"]).resolve(strict=True)
    mesh_export_root = Path(config["meshExportRoot"]).resolve(strict=True)
    mesh_root = Path(config["meshSource"]).resolve(strict=True)
    expected_observer_root = Path(
        "/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06"
    ).resolve()
    expected_mesh_root = Path(
        "/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-b9e8488e"
    ).resolve()
    if observer_root != expected_observer_root or observer_tests != observer_root / "tests":
        raise HarnessError("observer_root_or_tests_not_exact_immutable_export")
    if matched != observer_root / "docs/evidence/2026-10-18-working-set/performance-source/read_matched.py":
        raise HarnessError("matched_reference_not_exact_immutable_export")
    if mesh_export_root != expected_mesh_root or mesh_root != mesh_export_root / "src":
        raise HarnessError("mesh_import_root_not_exact_export_src")
    expected_metadata = {
        "observerSourceManifestSha256": EXPECTED_OBSERVER_MANIFEST_SHA256,
        "observerSourceArchiveSha256": EXPECTED_OBSERVER_ARCHIVE_SHA256,
        "meshSourceManifestSha256": EXPECTED_MESH_MANIFEST_SHA256,
        "meshSourceArchiveSha256": EXPECTED_MESH_ARCHIVE_SHA256,
    }
    if any(config.get(key) != value for key, value in expected_metadata.items()):
        raise HarnessError("source_manifest_or_archive_pin_mismatch")
    if config.get("meterPath") != str(METER) or config.get("meterSha256") != METER_SHA256:
        raise HarnessError("meter_copy_identity_mismatch")
    if config.get("runnerPath") != str(HARNESS) or config.get("runnerSha256") != _sha256(HARNESS):
        raise HarnessError("serial_watch_runner_identity_mismatch")
    if (config.get("meterOriginalPath") != str(PRIVATE_ROOT.parent / "wire-v2" / "socket_meter_v2.py")
            or config.get("meterOriginalSha256") != ORIGINAL_METER_SHA256):
        raise HarnessError("meter_original_identity_mismatch")
    if (config.get("v38OriginalHarnessSha256") != V38_HARNESS_SHA256
            or config.get("v38OriginalCpuHelperSha256") != V38_CPU_HELPER_SHA256
            or config.get("v38OriginalConfigSha256") != V38_CONFIG_SHA256):
        raise HarnessError("v3_8_lineage_pin_mismatch")
    plan = config.get("capturePlan")
    if (plan != {
        "rows": [500, 2000], "variants": ["full", "working"],
        "interpreters": ["py314", "py311"], "generations": 3,
        "newPublicWatchAdmissionsPerGeneration": 4, "totalCasesMaximum": 8,
        "caseWallTimeoutSeconds": CASE_TIMEOUT_SECONDS,
        "maximumMeterSocketGenerations": 128, "cpuClaim": False,
        "rssClaim": False, "physicalWireClaim": False,
    }):
        raise HarnessError("capture_plan_shape_mismatch")
    observer_manifest = _verify_export(
        observer_root,
        Path(config["observerSourceManifestPath"]),
        config["observerSourceManifestSha256"],
        Path(config["observerSourceArchivePath"]),
        config["observerSourceArchiveSha256"],
        config["observerId"],
    )
    mesh_manifest = _verify_export(
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
    audit = _dispatch_audit(config)
    config["meshImportRelative"] = mesh_root.relative_to(mesh_export_root).as_posix()
    config["observerFileCount"] = len(observer_manifest["files"])
    config["meshFileCount"] = len(mesh_manifest["files"])
    return config, audit


def _plan(config: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    cases = []
    trial_index = 0
    for interpreter_name in INTERPRETER_ORDER:
        for rows in ROWS:
            for variant in VARIANTS:
                cases.append({
                    "caseIndex": len(cases) + 1,
                    "trialIndex": trial_index,
                    "interpreterName": interpreter_name,
                    "interpreter": str(INTERPRETERS[interpreter_name]),
                    "rows": rows,
                    "selectedRows": SELECTED_ROWS[rows],
                    "variant": variant,
                    "generations": 3,
                    "newWatchAdmissionsPerGeneration": 4,
                    "totalPublicWatchAdmissions": 12,
                    "argvTemplate": [
                        "rtk", "proxy", str(INTERPRETERS[interpreter_name]),
                        "<private-runner-copy>",
                        "--observer-source", config["observerSource"],
                        "--observer-tests", config["observerTests"],
                        "--mesh-source", config["meshSource"],
                        "--matched-source", config["matchedSource"],
                        "--observer-id", config["observerId"],
                        "--mesh-id", config["meshId"],
                        "--approved-source-pair", config["approvedSourcePair"],
                        "--mode", "wire", "--rows", str(rows),
                        "--variant", variant, "--trial-index", str(trial_index),
                        "--generations", "3", "--watch-admissions-per-generation", "4",
                        "--output", "<private-case-report.json>",
                    ],
                })
                trial_index += 1
    return {
        "format": "private.sdk-pipeline.wire-v3-serial-watch4.plan.v1",
        "status": "plan_only_no_application_capture",
        "captureAuthorized": config.get("captureAuthorized") is True,
        "configStatus": config.get("status"),
        "sourcePair": config["approvedSourcePair"],
        "observerManifestSha256": config["observerSourceManifestSha256"],
        "meshManifestSha256": config["meshSourceManifestSha256"],
        "observerFileCount": config["observerFileCount"],
        "meshFileCount": config["meshFileCount"],
        "meterSha256": _sha256(METER),
        "meterOriginalSha256": _sha256(Path(config["meterOriginalPath"])),
        "runnerSha256": _sha256(HARNESS),
        "controllerSha256": _sha256(Path(__file__).resolve()),
        "wireV2DispatchHelperSha256": _sha256(V2_HELPER),
        "ioDispatchAudit": audit,
        "caseOrder": "py314 then py311; each row count runs full then working; no ABBA timing",
        "caseTimeoutSeconds": CASE_TIMEOUT_SECONDS,
        "lock": str(SHARED_LOCK),
        "meterSemantics": "positive kernel-return send/sendmsg prefixes on classified native/Mesh AF_UNIX SOCK_STREAM writes; loop-control is separate",
        "workload": "3 generations x 4 new ordinary Reader.watch_admitted streams per generation; each stream has a distinct request ID/fresh proof and is retired before the next",
        "totalCasesMaximum": len(cases),
        "noCostOrPhysicalWireClaim": True,
        "cases": cases,
    }


def _validate_loaded_module_map(loaded: Any, manifests: dict[str, dict[str, str]],
                                mesh_import_relative: Path) -> int:
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
    return len(loaded)


def _validate_wire_snapshot(snapshot: Any, config: dict[str, Any] | None = None,
                            case: dict[str, Any] | None = None) -> tuple[dict[str, Any], bool]:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "private.sdk-pipeline.socket-meter.v2":
        raise HarnessError("wire_meter_snapshot_missing")
    if snapshot.get("maxGenerations") != 128:
        raise HarnessError("wire_meter_generation_cap_changed")
    if (snapshot.get("basis") != "positive byte prefixes returned by kernel send/sendmsg on classified AF_UNIX SOCK_STREAM descriptors"
            or snapshot.get("deliveryTotalsIncludeOnlyRoles") != ["native", "mesh"]
            or snapshot.get("loopControlBytesIncludedInDeliveryTotals") is not False
            or snapshot.get("physicalWireClaim") is not False
            or snapshot.get("validatedPeerReadClaim") is not False
            or snapshot.get("payloadRetained") is not False
            or snapshot.get("unsupportedWrites")):
        raise HarnessError("wire_meter_unsupported_writes_present")
    connections = snapshot.get("connections")
    if not isinstance(connections, list) or len(connections) != snapshot.get("generationCount"):
        raise HarnessError("wire_meter_connection_registry_incomplete")
    if any(item.get("open") is not False or item.get("writeInProgress") is not False for item in connections):
        raise HarnessError("wire_meter_socket_cleanup_incomplete")
    endpoints = snapshot.get("endpoints")
    if (not isinstance(endpoints, list)
            or {item.get("role") for item in endpoints} != {"native", "mesh"}
            or any(item.get("bindCount") != 1 for item in endpoints)):
        raise HarnessError("wire_meter_endpoint_bind_audit_incomplete")
    for item in connections:
        if item.get("positiveWrites", 0) and item.get("role") not in {"native", "mesh", "loop_control"}:
            raise HarnessError("wire_meter_positive_write_unclassified")
        if item.get("role") in {"native", "mesh"} and (
            item.get("family") != socket.AF_UNIX
            or (int(item.get("socketType", 0)) & getattr(socket, "SOCK_TYPE_MASK", 0xF)) != socket.SOCK_STREAM
        ):
            raise HarnessError("wire_meter_target_socket_identity_mismatch")
    totals = snapshot.get("totalsByRoleAndSide")
    if not isinstance(totals, list):
        raise HarnessError("wire_meter_role_totals_missing")
    roles = {role: {item.get("side") for item in totals if item.get("role") == role}
             for role in ("native", "mesh")}
    if any(roles[role] != {"client", "server"} for role in roles):
        raise HarnessError("wire_meter_role_sides_incomplete")
    summary = {
        "native": sum(item.get("bytesKernelAccepted", 0) for item in totals if item.get("role") == "native"),
        "mesh": sum(item.get("bytesKernelAccepted", 0) for item in totals if item.get("role") == "mesh"),
        "loopControl": sum(item.get("bytesKernelAccepted", 0) for item in connections if item.get("role") == "loop_control"),
        "connections": len(connections),
        "allSocketConnectionsClosed": True,
        "unsupportedWrites": [],
    }
    summary["totalRepeatedDeliveryKernelAcceptedBytes"] = summary["native"] + summary["mesh"]
    return summary, True


def _validate_case_report(report: dict[str, Any], config: dict[str, Any],
                          manifests: dict[str, dict[str, str]], case: dict[str, Any]) -> dict[str, Any]:
    if (report.get("format") != "agent-observer.working-set.sdk-pipeline-matrix.wire-v3-serial-watch4"
            or report.get("sourcePair") != config["approvedSourcePair"]
            or report.get("mode") != "serial-watch4-kernel-write-capture"
            or report.get("timed") is not False
            or report.get("cpuClaim") is not False):
        raise HarnessError("wire_case_report_identity_mismatch")
    loaded_count = _validate_loaded_module_map(
        report.get("loadedProjectModules"), manifests, Path(config["meshImportRelative"])
    )
    if _canonical_sha256(report["loadedProjectModules"]) != report.get("sourceModuleMapSha256"):
        raise HarnessError("source_module_map_digest_mismatch")
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != 1:
        raise HarnessError("wire_case_report_case_count_mismatch")
    result = cases[0]
    if (result.get("variant") != case["variant"] or result.get("rows") != case["rows"]
            or result.get("selectedRows") != case["selectedRows"]
            or result.get("trialIndex") != case["trialIndex"]):
        raise HarnessError("wire_case_parameters_mismatch")
    generations = result.get("generations")
    if not isinstance(generations, list) or len(generations) != 3:
        raise HarnessError("wire_generation_count_mismatch")
    request_hashes: list[str] = []
    nonce_hashes: list[str] = []
    comparable: list[dict[str, Any]] = []
    for generation in generations:
        admissions = generation.get("watchAdmissions")
        if (not isinstance(admissions, list) or len(admissions) != 4
                or generation.get("watchRequestIdsDistinct") is not True
                or generation.get("proofNoncesDistinct") is not True):
            raise HarnessError("wire_watch_admission_shape_or_uniqueness_mismatch")
        for admission in admissions:
            request_sha = admission.get("requestIdSha256")
            nonce_sha = admission.get("targetProofNonceSha256")
            if (type(request_sha) is not str or len(request_sha) != 64
                    or type(nonce_sha) is not str or len(nonce_sha) != 64):
                raise HarnessError("wire_request_or_proof_hash_missing")
            request_hashes.append(request_sha)
            nonce_hashes.append(nonce_sha)
            event = admission.get("targetEvent")
            if (not isinstance(event, dict) or event.get("proofPresent") is not True
                    or event.get("proofFresh") is not True
                    or event.get("proofNonceFreshFromPreviousWatchAdmission") is not True):
                raise HarnessError("wire_fresh_public_proof_event_missing")
            if (admission.get("facadeCurrentContextPresent") is not True
                    or admission.get("facadeIdentityOrderMatches") is not True
                    or admission.get("facadeDtoSha256") != admission.get("expectedDtoSha256")
                    or admission.get("nativeFrameMatchesPublicPublisherDigest") is not True
                    or admission.get("nativeDtoMatchesExpected") is not True):
                raise HarnessError("wire_public_facade_or_native_dto_check_failed")
            comparable.append({
                "generation": generation.get("generation"),
                "admissionIndex": admission.get("watchIndex"),
                "expectedIdsSha256": admission.get("expectedIdsSha256"),
                "expectedDtoSha256": admission.get("expectedDtoSha256"),
                "facadeDtoSha256": admission.get("facadeDtoSha256"),
                "acceptedFullDtoSha256": admission.get("acceptedFullDtoSha256"),
            })
    if len(set(request_hashes)) != 12 or len(set(nonce_hashes)) != 12:
        raise HarnessError("wire_trial_request_or_nonce_reuse")
    cleanup = result.get("cleanupCounts")
    if not isinstance(cleanup, dict):
        raise HarnessError("wire_case_cleanup_counts_missing")
    cleanup_zero = (
        cleanup.get("readerActiveConnections") == 0
        and cleanup.get("readerCleanupFailures") == 0
        and cleanup.get("readerConnectionsOpened") == cleanup.get("readerConnectionsClosed")
        and cleanup.get("cachedSourceWrapper") == {
            "activeSourceOperations": 0,
            "pendingSnapshotCalls": 0,
            "openWatchIterators": 0,
        }
        and cleanup.get("runtime") is not None
        and cleanup["runtime"].get("runtimePeersAfterRun") == 0
        and cleanup["runtime"].get("selectorRegistrationsAfterRun") == 0
        and cleanup["runtime"].get("selectorClosed") is True
        and cleanup["runtime"].get("runtimeThreadAlive") is False
        and cleanup["runtime"].get("selectorHookRestored") is True
        and cleanup.get("bridgeHandlersStarted") == cleanup.get("bridgeHandlersReturned", 0) + cleanup.get("bridgeHandlersRaised", 0)
        and cleanup.get("bridgeActiveHandlers") == 0
        and cleanup.get("retainedReaderClients", 0) <= 16
        and cleanup.get("retainedBridgeChannels", 0) <= 16
    )
    if not cleanup_zero:
        raise HarnessError("wire_functional_cleanup_check_failed")
    wire_summary, clean = _validate_wire_snapshot(report.get("kernelAcceptedUnixStreamWrites"), config, case)
    if report.get("wireCaptureClean") is not True or clean is not True:
        raise HarnessError("wire_capture_cleanup_or_classification_incomplete")
    reported_summary = report.get("kernelAcceptedDeliverySummary")
    if (not isinstance(reported_summary, dict)
            or reported_summary.get("totalRepeatedDeliveryKernelAcceptedBytes") != wire_summary["totalRepeatedDeliveryKernelAcceptedBytes"]
            or reported_summary.get("perRole", {}).get("native", {}).get("bytesKernelAccepted") != wire_summary["native"]
            or reported_summary.get("perRole", {}).get("mesh", {}).get("bytesKernelAccepted") != wire_summary["mesh"]
            or reported_summary.get("loopControl", {}).get("bytesKernelAccepted") != wire_summary["loopControl"]
            or reported_summary.get("nativeAndMeshBytesCountedOncePerPositiveWrite") is not True
            or reported_summary.get("loopControl", {}).get("excludedFromRepeatedDeliveryTotal") is not True):
        raise HarnessError("wire_total_repeated_delivery_numerator_mismatch")
    return {
        "caseIndex": case["caseIndex"],
        "trialIndex": case["trialIndex"],
        "interpreterName": case["interpreterName"],
        "pythonVersion": report.get("pythonVersion"),
        "rows": case["rows"],
        "variant": case["variant"],
        "loadedProjectModuleCount": loaded_count,
        "sourceModuleMapSha256": report["sourceModuleMapSha256"],
        "selectedComparableOutputs": comparable,
        "requestAndNonceSha256DistinctCount": len(set(request_hashes)),
        "cleanupZero": True,
        "kernelAcceptedDelivery": wire_summary,
        "reportSha256": None,
    }


def _validate_comparable_selected_outputs(results: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    indexed = {(item["interpreterName"], item["rows"], item["variant"]): item for item in results}
    for interpreter_name in INTERPRETER_ORDER:
        for rows in ROWS:
            full = indexed[(interpreter_name, rows, "full")]
            working = indexed[(interpreter_name, rows, "working")]
            full_outputs = full["selectedComparableOutputs"]
            working_outputs = working["selectedComparableOutputs"]
            if len(full_outputs) != 12 or len(working_outputs) != 12:
                raise HarnessError("selected_output_comparison_admission_count")
            for full_item, work_item in zip(full_outputs, working_outputs, strict=True):
                for key in ("expectedIdsSha256", "expectedDtoSha256", "facadeDtoSha256", "acceptedFullDtoSha256"):
                    if full_item.get(key) != work_item.get(key):
                        raise HarnessError("full_working_selected_output_hash_mismatch")
                comparisons.append({
                    "interpreterName": interpreter_name,
                    "rows": rows,
                    "generation": full_item["generation"],
                    "admissionIndex": full_item["admissionIndex"],
                    "selectedIdsSha256": full_item["expectedIdsSha256"],
                    "selectedDtoSha256": full_item["expectedDtoSha256"],
                    "fullFacadeDtoSha256": full_item["facadeDtoSha256"],
                    "workingFacadeDtoSha256": work_item["facadeDtoSha256"],
                    "sameSelectedOutput": True,
                })
    return {"matchedAdmissions": len(comparisons), "comparisons": comparisons}


def _safe_child_summary(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None or len(raw) > MAX_CHILD_OUTPUT_BYTES:
        return {"omitted": "child_output_missing_or_exceeds_bound"} if raw is not None else None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    summary = {}
    for key in ("status", "errorType", "code", "output", "sourcePair", "timed", "cpuClaim", "wireCaptureClean"):
        value = parsed.get(key)
        if isinstance(value, str):
            summary[key] = value[:MAX_CHILD_SUMMARY_STRING]
        elif isinstance(value, (bool, int)) or value is None:
            summary[key] = value
    return summary


def _run_one_case(run_root: Path, config: dict[str, Any], case: dict[str, Any],
                  controller_sha: str) -> dict[str, Any]:
    case_dir = run_root / f"case-{case['caseIndex']:02d}-{case['interpreterName']}-{case['rows']}-{case['variant']}"
    case_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    runner_copy = case_dir / HARNESS.name
    meter_copy = case_dir / METER.name
    cpu_helper_copy = case_dir / CPU_HELPER.name
    controller_copy = case_dir / Path(__file__).name
    config_copy = case_dir / PAIR_CONFIG.name
    for source, target in (
        (HARNESS, runner_copy), (METER, meter_copy), (CPU_HELPER, cpu_helper_copy),
        (Path(__file__), controller_copy), (PAIR_CONFIG, config_copy),
    ):
        shutil.copyfile(source, target)
        os.chmod(target, 0o600)
    report_path = case_dir / "report.json"
    interpreter = INTERPRETERS[case["interpreterName"]]
    argv = [
        "rtk", "proxy", str(interpreter), str(runner_copy),
        "--observer-source", config["observerSource"],
        "--observer-tests", config["observerTests"],
        "--mesh-source", config["meshSource"],
        "--matched-source", config["matchedSource"],
        "--observer-id", config["observerId"],
        "--mesh-id", config["meshId"],
        "--approved-source-pair", config["approvedSourcePair"],
        "--mode", "wire", "--rows", str(case["rows"]),
        "--variant", case["variant"], "--trial-index", str(case["trialIndex"]),
        "--generations", "3", "--watch-admissions-per-generation", "4",
        "--output", str(report_path),
    ]
    invocation = {
        "status": "prepared",
        "argv": argv,
        "interpreter": str(interpreter),
        "interpreterName": case["interpreterName"],
        "rows": case["rows"],
        "selectedRows": case["selectedRows"],
        "variant": case["variant"],
        "generations": 3,
        "newWatchAdmissionsPerGeneration": 4,
        "runnerSha256": _sha256(runner_copy),
        "meterSha256": _sha256(meter_copy),
        "cpuHelperSha256": _sha256(cpu_helper_copy),
        "controllerSha256": controller_sha,
        "controllerCopySha256": _sha256(controller_copy),
        "configSha256": _sha256(config_copy),
        "observerManifestSha256": config["observerSourceManifestSha256"],
        "meshManifestSha256": config["meshSourceManifestSha256"],
        "observerArchiveSha256": config["observerSourceArchiveSha256"],
        "meshArchiveSha256": config["meshSourceArchiveSha256"],
        "wireV2DispatchHelperSha256": _sha256(V2_HELPER),
        "classification": "untimed kernel-accepted native+Mesh AF_UNIX serial-watch4 case; no CPU or RSS claim",
        "reportPath": str(report_path),
    }
    _write_json(case_dir / "invocation.json", invocation)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, timeout=CASE_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, bytes) else (error.stdout or "").encode()
        stderr = error.stderr if isinstance(error.stderr, bytes) else (error.stderr or "").encode()
        provenance = {
            "status": "timeout",
            "timeoutSeconds": CASE_TIMEOUT_SECONDS,
            "processJoined": True,
            "stdoutBytes": len(stdout),
            "stdoutSha256": hashlib.sha256(stdout).hexdigest(),
            "stdoutSummary": _safe_child_summary(stdout),
            "stderrBytes": len(stderr),
            "stderrSha256": hashlib.sha256(stderr).hexdigest(),
            "stderrSummary": _safe_child_summary(stderr),
            "functionalPassClaim": False,
            "wireCaptureClaim": False,
        }
        _write_json(case_dir / "child-result.json", provenance)
        return {**provenance, "caseIndex": case["caseIndex"], "caseDirectory": str(case_dir)}
    stdout = completed.stdout.encode("utf-8", "replace")
    stderr = completed.stderr.encode("utf-8", "replace")
    provenance = {
        "exitCode": completed.returncode,
        "stdoutBytes": len(stdout),
        "stdoutSha256": hashlib.sha256(stdout).hexdigest(),
        "stdoutSummary": _safe_child_summary(stdout),
        "stderrBytes": len(stderr),
        "stderrSha256": hashlib.sha256(stderr).hexdigest(),
        "stderrSummary": _safe_child_summary(stderr),
        "reportPresent": report_path.is_file(),
    }
    _write_json(case_dir / "child-result.json", provenance)
    if completed.returncode != 0 or not report_path.is_file():
        return {
            "status": "failed",
            "caseIndex": case["caseIndex"],
            "caseDirectory": str(case_dir),
            "code": "child_exit_or_report_missing",
            **provenance,
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "status": "failed", "caseIndex": case["caseIndex"],
            "caseDirectory": str(case_dir), "code": "child_report_unreadable",
            "errorType": type(error).__name__, **provenance,
        }
    manifests = {
        "agent_observer": json.loads(Path(config["observerSourceManifestPath"]).read_text()) ["files"],
        "mesh_plus": json.loads(Path(config["meshSourceManifestPath"]).read_text()) ["files"],
    }
    try:
        checked = _validate_case_report(report, config, manifests, case)
    except HarnessError as error:
        failure = {
            "status": "failed", "caseIndex": case["caseIndex"],
            "caseDirectory": str(case_dir), "code": str(error),
            "reportSha256": _sha256(report_path), **provenance,
        }
        _write_json(case_dir / "validation-failure.json", failure)
        return failure
    checked["status"] = "pass"
    checked["caseDirectory"] = str(case_dir)
    checked["reportSha256"] = _sha256(report_path)
    checked["stdoutSha256"] = provenance["stdoutSha256"]
    checked["stderrSha256"] = provenance["stderrSha256"]
    checked["runnerSha256"] = invocation["runnerSha256"]
    checked["meterSha256"] = invocation["meterSha256"]
    _write_json(case_dir / "validated-case.json", checked)
    return checked


def _run_matrix(config: dict[str, Any], audit: dict[str, Any]) -> int:
    if config.get("captureAuthorized") is not True:
        raise HarnessError("wire_capture_authorization_missing")
    if not SHARED_LOCK.is_file():
        raise HarnessError("shared_measurement_lock_missing")
    plan = _plan(config, audit)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = RUNS_ROOT / run_id
    run_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    controller_sha = _sha256(Path(__file__).resolve())
    _write_json(run_root / "run-pins.json", {
        "sourcePair": config["approvedSourcePair"],
        "observerManifestSha256": config["observerSourceManifestSha256"],
        "meshManifestSha256": config["meshSourceManifestSha256"],
        "observerArchiveSha256": config["observerSourceArchiveSha256"],
        "meshArchiveSha256": config["meshSourceArchiveSha256"],
        "meterSha256": _sha256(METER),
        "controllerSha256": controller_sha,
        "configSha256": _sha256(PAIR_CONFIG),
        "dispatchAudit": audit,
        "caseTimeoutSeconds": CASE_TIMEOUT_SECONDS,
        "maximumCases": len(plan["cases"]),
    })
    completed: list[dict[str, Any]] = []
    with SHARED_LOCK.open("r+b") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        for case in plan["cases"]:
            result = _run_one_case(run_root, config, case, controller_sha)
            completed.append(result)
            _write_json(run_root / "progress.json", {
                "completedCases": completed,
                "nextCaseIndex": case["caseIndex"] + 1,
                "stoppedOnFailure": result.get("status") != "pass",
            })
            if result.get("status") != "pass":
                failure = {
                    "format": "private.sdk-pipeline.wire-v3-serial-watch4.result.v1",
                    "status": "failed",
                    "runDirectory": str(run_root),
                    "completedCases": completed,
                    "pipelineExecutionStopped": True,
                    "noCpuOrRssClaim": True,
                }
                _write_json(run_root / "result.json", failure)
                print(json.dumps({"status": "failed", "runDirectory": str(run_root),
                                  "failedCase": case["caseIndex"]}, sort_keys=True))
                return 1
    comparison = _validate_comparable_selected_outputs(completed)
    total_bytes = sum(item["kernelAcceptedDelivery"]["totalRepeatedDeliveryKernelAcceptedBytes"] for item in completed)
    result = {
        "format": "private.sdk-pipeline.wire-v3-serial-watch4.result.v1",
        "status": "pass",
        "runDirectory": str(run_root),
        "sourcePair": config["approvedSourcePair"],
        "completedCases": completed,
        "selectedOutputComparison": comparison,
        "matrixTotalRepeatedDeliveryKernelAcceptedBytes": total_bytes,
        "totalDeliveryBasis": "sum of positive kernel-return send/sendmsg prefixes on native and Mesh AF_UNIX stream paths for all eight complete cases; loop-control excluded",
        "loopControlExcluded": True,
        "caseCount": len(completed),
        "pipelineExecutionStopped": False,
        "cpuClaim": False,
        "rssClaim": False,
        "physicalWireClaim": False,
        "peerReadOrParseClaim": False,
    }
    _write_json(run_root / "result.json", result)
    print(json.dumps({"status": "pass", "runDirectory": str(run_root),
                      "caseCount": len(completed), "matchedAdmissions": comparison["matchedAdmissions"],
                      "matrixTotalRepeatedDeliveryKernelAcceptedBytes": total_bytes,
                      "cpuClaim": False, "rssClaim": False}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--print-plan", action="store_true")
    group.add_argument("--run-approved-captures", action="store_true")
    args = parser.parse_args()
    try:
        config, audit = _approved_config(require_capture=args.run_approved_captures)
        if args.run_approved_captures:
            return _run_matrix(config, audit)
        print(json.dumps(_plan(config, audit), sort_keys=True, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({
            "status": "refused_or_failed_before_capture",
            "errorType": type(error).__name__,
            "code": str(error)[:160],
            "captureAuthorized": False,
        }, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
