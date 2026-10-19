from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

OUT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-pressure-196a8e2b")
CACHE = Path("/home/bryan/.cache/agent-observer-working-set-20261018")
ROOT = CACHE / "final-source-196a8e2b"
MANIFEST = CACHE / "final-source-196a8e2b-manifest.json"
CASE = CACHE / "current-pressure-preparation" / "pressure_case_current.py"
LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
SOURCE_REVISION = "196a8e2bd114f90aae82c4ee79559db511b9dce7"
EXPECTED_CASE_SHA = "623f761a4a10bac8aad50ab5b8fcb3604cbe6f652cbeffddc97b16f9a956b3e0"
PYTHON = {
    "py314": "/home/bryan/code/mesh-plus/.venv/bin/python",
    "py311": "/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python",
}
EXPECTED_VERSIONS = {"py314": "3.14.", "py311": "3.11."}
ENCODED_LIMIT = 64 * 1024 * 1024
CLIENT_LIMIT = 16
EXPECTED_ROWS = 2000
EXPECTED_GENERATIONS = 14
EXPECTED_SMALL = 20


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def source_manifest_check() -> dict:
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("commit") != SOURCE_REVISION:
        raise RuntimeError("source_manifest_commit_mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("source_manifest_files_missing")
    mismatches = []
    for rel, expected in files.items():
        path = ROOT / rel
        if not path.is_file() or file_sha(path) != expected:
            mismatches.append(rel)
    return {
        "manifestSha256": sha(manifest_bytes),
        "manifestCommit": manifest["commit"],
        "manifestFileCount": len(files),
        "checkedFileCount": len(files),
        "mismatches": mismatches,
        "passed": not mismatches,
        "files": files,
    }


def report_source_checks(report: dict, manifest_files: dict[str, str], driver_sha: str) -> dict:
    observed = report.get("sourceFilesSha256")
    if not isinstance(observed, dict):
        return {"passed": False, "failures": ["source_file_hash_map_missing"]}
    failures = []
    for rel, actual in observed.items():
        if rel.startswith("agent_observer/") or rel.startswith("tests/"):
            expected = manifest_files.get(rel)
            if expected is None or actual != expected:
                failures.append(f"source_manifest:{rel}")
        elif rel == "resource-pressure/pressure_case.py":
            if actual != EXPECTED_CASE_SHA:
                failures.append("case_runner_sha")
        elif rel == "resource-pressure/run_pressure.py":
            if actual != driver_sha:
                failures.append("driver_sha")
        else:
            failures.append(f"unexpected_source_hash_key:{rel}")
    required = {
        "agent_observer/service_runtime.py",
        "agent_observer/service_state.py",
        "agent_observer/working_set_feed.py",
        "agent_observer/working_set_clocks.py",
        "agent_observer/working_set_ledger.py",
        "agent_observer/working_set_supports.py",
        "tests/test_service_state.py",
        "resource-pressure/pressure_case.py",
        "resource-pressure/run_pressure.py",
        "tests/fixtures/service-v4/view.json",
        "agent_observer/contracts/snapshot.schema.json",
    }
    missing = sorted(required - set(observed))
    failures.extend(f"required_source_missing:{item}" for item in missing)
    return {
        "passed": not failures,
        "failures": failures,
        "fileCount": len(observed),
        "caseScriptSha256": observed.get("resource-pressure/pressure_case.py"),
        "driverSha256": observed.get("resource-pressure/run_pressure.py"),
        "runtimeSourceSha256": observed.get("agent_observer/service_runtime.py"),
        "stateSourceSha256": observed.get("agent_observer/service_state.py"),
        "workingSetFeedSha256": observed.get("agent_observer/working_set_feed.py"),
        "testFixtureSha256": observed.get("tests/test_service_state.py"),
    }


def validate_report(report: dict, *, variant: str, entrypoint: str,
                    manifest_files: dict[str, str], driver_sha: str) -> dict:
    failures = []
    if report.get("schema") != "working-set-resource-pressure-case-v1":
        failures.append("schema_mismatch")
    if report.get("sourceRevision") != SOURCE_REVISION:
        failures.append("source_revision_mismatch")
    if report.get("runtimeSourceRevision") != SOURCE_REVISION:
        failures.append("runtime_source_revision_mismatch")
    if report.get("root") != str(ROOT.resolve()):
        failures.append("root_mismatch")
    if not str(report.get("pythonVersion", "")).startswith(EXPECTED_VERSIONS[variant]):
        failures.append("python_version_mismatch")
    if report.get("pythonEntrypoint") != entrypoint:
        failures.append("python_entrypoint_mismatch")
    if report.get("gcEnabled") is not False:
        failures.append("gc_enabled")
    if report.get("caseStatus") != "pressure_complete":
        failures.append("case_incomplete")
    if report.get("failures") != []:
        failures.append("case_failures")
    if report.get("meshImports") != []:
        failures.append("mesh_imported")
    runtime = report.get("runtime", {})
    if runtime.get("encodedLimitBytes") != ENCODED_LIMIT or runtime.get("encodedLimitChanged") is not False:
        failures.append("encoded_limit_changed")
    if runtime.get("defaultMaxClients", CLIENT_LIMIT) not in (CLIENT_LIMIT, None):
        failures.append("default_client_limit")
    if report.get("topology", {}).get("defaultMaxClients") != CLIENT_LIMIT:
        failures.append("topology_default_client_limit")
    if report.get("topology", {}).get("peerCountAtStart") != CLIENT_LIMIT:
        failures.append("initial_client_count")
    if report.get("topology", {}).get("peerCountAtPeak") > CLIENT_LIMIT:
        failures.append("peak_client_count")
    case = report.get("case", {})
    if (case.get("rows") != EXPECTED_ROWS or case.get("generationCount") != EXPECTED_GENERATIONS
            or case.get("expectedUnionCount") != EXPECTED_SMALL or case.get("activeCount") != 10
            or case.get("recentCount") != 10 or case.get("activityTimestampFixedAcrossGenerations") is not True):
        failures.append("fixture_shape")
    generations = report.get("generations", [])
    if len(generations) != EXPECTED_GENERATIONS:
        failures.append("generation_count")
    for index, generation in enumerate(generations):
        if generation.get("generation") != index:
            failures.append(f"generation_order:{index}")
        if generation.get("providerRuntimeHealth") != "current" or generation.get("providerRuntimeAccepted") != index + 1:
            failures.append(f"accepted_runtime_current:{index}")
        if generation.get("full", {}).get("rowCount") != EXPECTED_ROWS:
            failures.append(f"full_rows:{index}")
        if generation.get("active", {}).get("rowCount") != 10:
            failures.append(f"active_rows:{index}")
        if generation.get("workingSet", {}).get("rowCount") != EXPECTED_SMALL:
            failures.append(f"working_set_rows:{index}")
        if generation.get("workingSet", {}).get("coverageStatus") != "complete":
            failures.append(f"working_set_coverage:{index}")
        if not generation.get("fullHealthyReader", {}).get("dtoMatchesDirectFrame"):
            failures.append(f"full_delivery_dto:{index}")
        if not generation.get("fullHealthyReader", {}).get("streamGuardAccepted"):
            failures.append(f"full_stream_guard:{index}")
        sibling = generation.get("healthySiblingReaders", {})
        if set(sibling) != {"active_reader", "working_set_reader"}:
            failures.append(f"sibling_set:{index}")
        for label, record in sibling.items():
            if (not record.get("streamGuardAccepted") or not record.get("peerRemainedLive")
                    or record.get("rowCount") != (10 if label == "active_reader" else EXPECTED_SMALL)):
                failures.append(f"sibling_delivery:{index}:{label}")
        inv = generation.get("inventory", {})
        if (inv.get("counterMatchesManualCharge") is not True
                or inv.get("withinEncodedLimit") is not True
                or inv.get("uniqueBytesWithinRuntimeCharge") is not True
                or inv.get("allPeerAliasesMatchCache") is not True
                or inv.get("peerCount", CLIENT_LIMIT + 1) > CLIENT_LIMIT):
            failures.append(f"generation_inventory:{index}")
        rss = generation.get("instrumentedProcessRssKiB")
        if type(rss) is not int or rss <= 0:
            failures.append(f"rss_sample:{index}")
    inventories = report.get("counterInventories", [])
    if len(inventories) != 420:
        failures.append("inventory_count")
    for entry in inventories:
        inv = entry
        if (inv.get("counterMatchesManualCharge") is not True
                or inv.get("withinEncodedLimit") is not True
                or inv.get("uniqueBytesWithinRuntimeCharge") is not True
                or inv.get("allPeerAliasesMatchCache") is not True
                or inv.get("peerCount", CLIENT_LIMIT + 1) > CLIENT_LIMIT):
            failures.append(f"inventory_equation:{entry.get('label')}")
    reservation_events = report.get("reservationEvents", [])
    if len(reservation_events) != EXPECTED_GENERATIONS:
        failures.append("reservation_count")
    for index, event in enumerate(reservation_events):
        if (event.get("admitted") is not True or event.get("fitsAfterRoom") is not True
                or event.get("additionalBytes") != runtime.get("worstCaseStageReservationBytes")
                or event.get("currentPlusAdditionalAfterBytes", ENCODED_LIMIT + 1) > ENCODED_LIMIT):
            failures.append(f"reservation_preflight:{index}")
    pressure = report.get("pressure", {})
    if pressure.get("aboveLimitReservationCount", 0) < 1:
        failures.append("pressure_not_reached")
    if pressure.get("naturalRuntimeRoomDropCount", 0) < 1:
        failures.append("natural_room_drop_missing")
    if pressure.get("allDropsWereOldestPinnedSlowFullPeers") is not True:
        failures.append("wrong_drop_victim")
    drop_events = [item for item in report.get("dropEvents", []) if item.get("insideRuntimeRoom")]
    if len(drop_events) != pressure.get("naturalRuntimeRoomDropCount"):
        failures.append("drop_count_mismatch")
    for event in drop_events:
        if (event.get("family") != "service" or not event.get("peer", "").startswith("full_slow_")
                or event.get("wasOldestWriteStartedCandidate") is not True
                or event.get("bodyBytes", 0) <= 0
                or event.get("bodyRevision") is None
                or event.get("peerPartsRetainedBySourceDrop") is not False
                or event.get("peerBodyRevisionRetainedBySourceDrop") is not False
                or event.get("peerPartBytesAfterRoomReturn") != 0
                or event.get("bodyRevisionAfterRoomReturn") is not None):
            failures.append(f"drop_lifetime:{event.get('peer')}")
    cleanup = report.get("cleanup", {})
    if (cleanup.get("allSenderSocketsClosed") is not True
            or cleanup.get("allReceiverSocketsClosed") is not True
            or cleanup.get("runtimePeersAfterCleanup") != 0
            or cleanup.get("runtimeBodiesAfterCleanup") != 0
            or cleanup.get("runtimeLatestAfterCleanup") != 0
            or cleanup.get("workingSetReservationRemoved") is not True
            or cleanup.get("selectorClosed") is not True):
        failures.append("cleanup")
    owner_buffers = cleanup.get("ownerBuffersRetainedByLiveState", [])
    owner_expected = sum(item["bytes"] for item in owner_buffers)
    if cleanup.get("runtimeEncodedBytesAfterCleanup") != owner_expected:
        failures.append("live_owner_credit_mismatch")
    if cleanup.get("gcDisabledOwnerZeroClaim") is not False:
        failures.append("false_gc_zero_claim")
    if type(cleanup.get("rssCurrentKiB")) is not int or type(cleanup.get("processRssHighWaterKiB")) is not int:
        failures.append("rss_cleanup_metrics")
    if report.get("scope") != (
        "synthetic ServiceState acceptance plus actual default Runtime reserve/room/queue/write/drop on local socketpairs; "
        "no provider, service process, SDK, Mesh, network, CPU or RSS acceptance"
    ):
        failures.append("scope_mismatch")
    source_checks = report_source_checks(report, manifest_files, driver_sha)
    if not source_checks["passed"]:
        failures.extend(source_checks["failures"])
    return {
        "passed": not failures,
        "failureCount": len(failures),
        "failures": failures,
        "sourceChecks": source_checks,
        "rssSeriesKiB": [item["instrumentedProcessRssKiB"] for item in generations],
        "processRssHighWaterKiB": cleanup.get("processRssHighWaterKiB"),
        "encodedCounterHighWaterBytes": pressure.get("actualCounterHighWaterBytes"),
        "maximumPreflightRequestBytes": pressure.get("maxReservationCurrentPlusAdditionalBytes"),
        "naturalRoomDrops": pressure.get("naturalDroppedPeerLabels"),
        "liveOwnerBuffersAfterCleanup": owner_buffers,
        "runtimeEncodedBytesAfterCleanup": cleanup.get("runtimeEncodedBytesAfterCleanup"),
    }


def main() -> int:
    if any(path.name != Path(__file__).name for path in OUT.iterdir()):
        raise RuntimeError("output_directory_not_empty")
    if file_sha(CASE) != EXPECTED_CASE_SHA:
        raise RuntimeError("pressure_case_hash_mismatch")
    before = source_manifest_check()
    if not before["passed"]:
        raise RuntimeError("final_source_manifest_mismatch")

    manifest_data = json.loads(MANIFEST.read_bytes())
    manifest_files = manifest_data["files"]
    driver_sha = file_sha(Path(__file__).resolve())
    started_epoch = time.time()
    variants = []
    with LOCK.open("rb") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        acquired_epoch = time.time()
        after_lock = source_manifest_check()
        if not after_lock["passed"]:
            raise RuntimeError("final_source_changed_before_trial")
        (OUT / "lock-acquired.json").write_text(json.dumps({
            "lock": str(LOCK), "acquiredEpoch": acquired_epoch,
            "pid": os.getpid(),
        }, indent=2, sort_keys=True) + "\n")
        failures = []
        for variant, entrypoint in PYTHON.items():
            report_path = OUT / f"{variant}-n2000-long-title-cwd-slow-pressure.json"
            log_path = report_path.with_suffix(".log")
            command = [
                entrypoint, "-B", str(CASE),
                "--root", str(ROOT),
                "--output", str(report_path),
                "--source-revision", SOURCE_REVISION,
                "--runtime-source-revision", SOURCE_REVISION,
                "--python-entrypoint", entrypoint,
                "--driver", str(Path(__file__).resolve()),
            ]
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = os.pathsep.join(
                item for item in (str(ROOT), str(ROOT / "tests"), env.get("PYTHONPATH", "")) if item
            )
            completed = subprocess.run(
                command, cwd=str(ROOT), env=env, check=False,
                capture_output=True, text=True,
            )
            log_data = {
                "variant": variant, "command": command,
                "exitCode": completed.returncode,
                "stdout": completed.stdout, "stderr": completed.stderr,
            }
            log_path.write_text(json.dumps(log_data, indent=2, sort_keys=True) + "\n")
            if not report_path.is_file():
                failures.append(f"{variant}:report_missing")
                variants.append({"variant": variant, "entrypoint": entrypoint, "exitCode": completed.returncode})
                break
            report = json.loads(report_path.read_bytes())
            checked = validate_report(
                report, variant=variant, entrypoint=entrypoint,
                manifest_files=manifest_files, driver_sha=driver_sha,
            )
            if completed.returncode != 0:
                checked["failures"].append(f"child_exit:{completed.returncode}")
                checked["passed"] = False
                checked["failureCount"] = len(checked["failures"])
            item = {
                "variant": variant,
                "pythonEntrypoint": entrypoint,
                "pythonVersion": report.get("pythonVersion"),
                "report": report_path.name,
                "reportSha256": file_sha(report_path),
                "log": log_path.name,
                "logSha256": file_sha(log_path),
                "exitCode": completed.returncode,
                "caseStatus": report.get("caseStatus"),
                "acceptedGenerations": len(report.get("generations", [])),
                "acceptedInputSha256s": [
                    generation.get("inputSnapshotSha256")
                    for generation in report.get("generations", [])
                ],
                "initialInputSha256": report.get("case", {}).get("initialInputSha256"),
                "caseValidation": checked,
            }
            variants.append(item)
            if not checked["passed"]:
                failures.extend(f"{variant}:{failure}" for failure in checked["failures"])
                break

        after = source_manifest_check()
        if not after["passed"] or before["manifestSha256"] != after["manifestSha256"]:
            failures.append("source_manifest_changed_during_run")
        if len(variants) == 2 and variants[0]["caseValidation"]["passed"] and variants[1]["caseValidation"]["passed"]:
            first, second = (json.loads((OUT / item["report"]).read_bytes()) for item in variants)
            for key in ("initialInputSha256",):
                if first["case"][key] != second["case"][key]:
                    failures.append(f"cross_python_input:{key}")
            first_inputs = [item["inputSnapshotSha256"] for item in first["generations"]]
            second_inputs = [item["inputSnapshotSha256"] for item in second["generations"]]
            if first_inputs != second_inputs:
                failures.append("cross_python_accepted_inputs")
            for index, (left, right) in enumerate(zip(first["generations"], second["generations"], strict=True)):
                for family in ("full", "active", "workingSet"):
                    if left[family] != right[family]:
                        failures.append(f"cross_python_route_semantics:{index}:{family}")
            if first["pressure"]["actualCounterHighWaterBytes"] != second["pressure"]["actualCounterHighWaterBytes"]:
                failures.append("cross_python_encoded_highwater")
            if first["pressure"]["naturalDroppedPeerLabels"] != second["pressure"]["naturalDroppedPeerLabels"]:
                failures.append("cross_python_drop_set")

        summary = {
            "schema": "working-set-resource-pressure-final-summary-v1",
            "status": "pressure_complete" if not failures and len(variants) == 2 else "unexpected_failure",
            "sourceRevision": SOURCE_REVISION,
            "runtimeSourceRevision": SOURCE_REVISION,
            "root": str(ROOT),
            "sourceManifestBefore": {key: value for key, value in before.items() if key != "files"},
            "sourceManifestAfter": {key: value for key, value in after.items() if key != "files"},
            "sourceManifestStable": before["manifestSha256"] == after["manifestSha256"],
            "pressureCase": str(CASE),
            "pressureCaseSha256": file_sha(CASE),
            "driver": str(Path(__file__).resolve()),
            "driverSha256": driver_sha,
            "lock": str(LOCK),
            "lockAcquiredEpoch": acquired_epoch,
            "startedEpoch": started_epoch,
            "finishedEpoch": time.time(),
            "pythonEntrypoints": PYTHON,
            "variants": variants,
            "crossPythonInputAndRouteParity": not any(item.startswith("cross_python_") for item in failures),
            "failures": failures,
            "scope": (
                "Synthetic ServiceState plus default Runtime encoded budget and local slow-reader socketpairs. "
                "The report contains instrumented process RSS/HWM context; no heap/physical cap, plateau, "
                "provider, service process, Mesh, SDK, network, or production qualification is claimed."
            ),
            "limitations": [
                "RSS/HWM includes imports, fixture and audit objects, DTOs, caches, sockets, and transient parsing.",
                "GC remains disabled; live ServiceState active/working-set owner buffers remain after runtime cleanup.",
                "This is a bounded 14-generation source-level pressure case, not an RSS plateau or production memory bound.",
                "No provider, native daemon, service process, Mesh, SDK, or external network was contacted.",
            ],
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    (OUT / "README.md").write_text(
        "# Final 196a8e2b slow-reader pressure repeat\n\n"
        "This private repeat uses the byte-unchanged 623f761a harness against the immutable 196a8e2b source export. "
        "It runs the same 2,000-row, 14-generation long-title/cwd fixture under both pinned Python entrypoints with GC disabled, "
        "a default 16-peer topology, and the unchanged 64 MiB Runtime encoded limit. The harness admits real source snapshots, queues full/active/working-set frames, partially writes 13 slow full readers, and keeps healthy sibling readers draining.\n\n"
        "The summary validates source manifest bytes before and after, loaded Observer/test/fixture/schema hashes, exact reservation and counter equations, oldest slow-full peer drop clearing, healthy sibling streams, and socket/runtime cleanup. Raw reports retain the instrumented RSS series and process high-water value with fixture/audit scope.\n\n"
        "RSS values include the process's imports, fixture, oracle, audit inventory, DTOs, caches, sockets, and transient parsing. They do not establish Python heap bounds, physical memory limits, or an RSS plateau. Live ServiceState active and working-set owner buffers remain intentionally accounted after Runtime delivery cleanup. The run is synthetic and source-only; provider, service-process, Mesh, SDK, external network, and production behavior are outside scope.\n"
    )
    print(json.dumps({
        "summary": str(OUT / "summary.json"),
        "status": summary["status"],
        "variants": [
            {
                "python": item.get("pythonVersion"),
                "passed": item.get("caseValidation", {}).get("passed", False),
                "rssHwmKiB": item.get("caseValidation", {}).get("processRssHighWaterKiB"),
                "encodedHighwaterBytes": item.get("caseValidation", {}).get("encodedCounterHighWaterBytes"),
                "naturalDrops": item.get("caseValidation", {}).get("naturalRoomDrops"),
            }
            for item in variants
        ],
        "failures": failures,
    }, sort_keys=True))
    return 0 if summary["status"] == "pressure_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
