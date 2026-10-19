#!/usr/bin/env python3
"""Thirty-two-generation RSS resource screen over the pinned V3.6 SDK pipeline.

The V3.6 runner is loaded unchanged. This adapter overrides only the private
_run_variant arguments for the requested untimed 500/2000-row / 32-generation / 4
facade-read case and adds bounded scalar lifecycle telemetry.
"""
from __future__ import annotations

import argparse
import asyncio
import gc
import hashlib
import importlib.util
import json
import sys
import weakref
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "sdk_pipeline_matrix_v3_6_watch_copy.py"
SOURCE_PAIR = (
    "b176ac06b39daeead4be0a33ff9d781304091fe0"
    "+042fe3a5671fabbedfd36bbef10a8e8abcb25485"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("rss_v36_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("runner_import")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.DEFAULT_MESH_ID = "042fe3a5671fabbedfd36bbef10a8e8abcb25485"
    module.DEFAULT_MESH_SOURCE = Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-042fe3a5/src")
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_code(runner, error: BaseException) -> str:
    return runner._safe_failure_code(error)


def _alive(ref):
    if ref is None:
        return None
    value = ref()
    answer = value is not None
    del value
    return answer


def _runtime_scalars(runtime, stage):
    state = runtime.state
    owners = state.working_set_retained_buffers()
    unique_owner_ids = set()
    unique_owner_bytes = 0
    for value in owners:
        marker = id(value)
        if marker not in unique_owner_ids:
            unique_owner_ids.add(marker)
            unique_owner_bytes += len(value)
    body_bytes = sum(len(value) for value in runtime.bodies.values())
    peer_count = len(runtime.peers)
    peer_part_count = 0
    peer_non_body_part_bytes = 0
    peer_body_alias_bytes = 0
    for peer in runtime.peers:
        for index, part in enumerate(peer.parts):
            peer_part_count += 1
            if index == 1 and peer.body_revision is not None:
                peer_body_alias_bytes += len(part)
            else:
                peer_non_body_part_bytes += len(part)
    sync_bytes = runtime.sync_encoded_bytes()
    encoded_current = runtime.encoded_bytes()
    component_sum = unique_owner_bytes + body_bytes + peer_non_body_part_bytes + sync_bytes
    return {
        "runtimeEncodedBytesCurrent": encoded_current,
        "runtimeEncodedComponentSum": component_sum,
        "runtimeEncodedComponentsReconcile": encoded_current == component_sum,
        "currentOwnerBufferCount": len(owners),
        "currentOwnerBufferBytes": unique_owner_bytes,
        "activeEncodedBytes": (
            0 if state.active_projector._encoded is None
            else len(state.active_projector._encoded)
        ),
        "workingSetEncodedBytes": (
            0 if state.working_set_projector is None
            or state.working_set_projector._encoded is None
            else len(state.working_set_projector._encoded)
        ),
        "peerCount": peer_count,
        "peerPartCount": peer_part_count,
        "peerNonBodyPartBytes": peer_non_body_part_bytes,
        "peerBodyAliasReferenceBytes": peer_body_alias_bytes,
        "bodyCount": len(runtime.bodies),
        "bodyBytes": body_bytes,
        "syncEncodedBytes": sync_bytes,
        "workingSetCapacityBlocked": (
            None if state.working_set_projector is None
            else state.working_set_projector._capacity_blocked
        ),
        "stageReservationCalls": stage["calls"],
        "stageLastRequestedAdditionalBytes": stage["lastRequested"],
        "stageMaximumRequestedAdditionalBytes": stage["maximumRequested"],
        "stageCurrentlyReservedAtSampleBytes": 0,
    }


def _make_case(runner, variant: str, output: Path, *, rows: int, generation_count: int, facade_reads: int):
    if output.resolve().parent != ROOT.resolve():
        raise ValueError("output_must_remain_in_private_probe_directory")
    if output.exists():
        raise ValueError("output_already_exists")
    if rows not in {500, 2000} or generation_count != 32 or facade_reads != 4:
        raise ValueError("declared_resource_matrix_only")
    if variant not in {"full", "working"}:
        raise ValueError("variant")
    if gc.isenabled():
        raise AssertionError("cyclic_gc_must_be_disabled")

    args = runner._parser().parse_args([
        "--mode", "diagnostic",
        "--diagnostic-variant", variant,
        "--diagnostic-rows", str(rows),
        "--reads-per-generation", str(facade_reads),
        "--approved-source-pair", SOURCE_PAIR,
    ])
    source_inputs, reference = runner._preflight(args, timed=False)
    if (source_inputs["observerId"] + "+" + source_inputs["meshId"]) != SOURCE_PAIR:
        raise AssertionError("source_pair_mismatch")

    from mesh_plus.api import Bridge, Client, Reader

    from agent_observer.service_runtime import Runtime

    stage = {"calls": 0, "lastRequested": 0, "maximumRequested": 0}
    refs = {name: [] for name in ("runtimeThread", "runtime", "state", "reader", "bridge", "client")}
    latest_runtime_thread = {"ref": None}
    closed_runtime = {"scalars": None}
    rss: list[dict] = []

    original_reserve = Runtime._reserve_working_set

    def reserve_with_scalar_telemetry(self, additional_bytes):
        stage["calls"] += 1
        stage["lastRequested"] = additional_bytes
        stage["maximumRequested"] = max(stage["maximumRequested"], additional_bytes)
        return original_reserve(self, additional_bytes)

    Runtime._reserve_working_set = reserve_with_scalar_telemetry

    original_thread_init = runner.RuntimeThread.__init__
    original_thread_exit = runner.RuntimeThread.__exit__

    def thread_init_with_weakrefs(self, state, path, runtime_class):
        original_thread_init(self, state, path, runtime_class)
        refs["runtimeThread"].append(weakref.ref(self))
        refs["runtime"].append(weakref.ref(self.runtime))
        refs["state"].append(weakref.ref(state))
        latest_runtime_thread["ref"] = weakref.ref(self)

    def thread_exit_with_close_snapshot(self, *args):
        try:
            return original_thread_exit(self, *args)
        finally:
            closed_runtime["scalars"] = _runtime_scalars(self.runtime, stage)

    runner.RuntimeThread.__init__ = thread_init_with_weakrefs
    runner.RuntimeThread.__exit__ = thread_exit_with_close_snapshot

    original_reader_init = Reader.__init__
    original_bridge_init = Bridge.__init__
    original_client_connect = Client.__dict__["connect"].__func__

    def reader_init_with_weakref(self, *args, **kwargs):
        original_reader_init(self, *args, **kwargs)
        refs["reader"].append(weakref.ref(self))

    def bridge_init_with_weakref(self, *args, **kwargs):
        original_bridge_init(self, *args, **kwargs)
        refs["bridge"].append(weakref.ref(self))

    async def client_connect_with_weakref(cls, *args, **kwargs):
        client = await original_client_connect(cls, *args, **kwargs)
        refs["client"].append(weakref.ref(client))
        return client

    Reader.__init__ = reader_init_with_weakref
    Bridge.__init__ = bridge_init_with_weakref
    Client.connect = classmethod(client_connect_with_weakref)

    original_read_rss = runner._read_rss

    def measured_read_rss(phase: str):
        sample = original_read_rss(phase)
        runtime_ref = refs["runtime"][-1] if refs["runtime"] else None
        thread_ref = latest_runtime_thread["ref"]
        runtime_thread = None if thread_ref is None else thread_ref()
        runtime = None if runtime_ref is None else runtime_ref()
        if runtime is not None:
            # The harness already owns this selector-boundary pause. It gives
            # an untimed, stable owner/peer census without changing SDK APIs.
            paused_here = False
            if runtime_thread is not None and not runtime_thread.pause.held:
                runtime_thread.pause.request_and_wait()
                paused_here = True
            try:
                sample.update(_runtime_scalars(runtime, stage))
                sample["runtimeAliveAtSample"] = True
            finally:
                if paused_here:
                    runtime_thread.pause.resume_and_wait()
        else:
            sample["runtimeAliveAtSample"] = False
        del runtime, runtime_thread
        return sample

    runner._read_rss = measured_read_rss
    runner.V3_CONTEXT.clear()
    runner.V3_FAILURES.clear()
    runner.V3_CONTEXT.update({
        "mode": "rss-prototype",
        "sourcePair": SOURCE_PAIR,
        "observerSource": str(args.observer_source.resolve()),
        "meshSource": str(args.mesh_source.resolve()),
        "rows": rows,
        "generations": generation_count,
        "detachedLocalFacadeCopiesPerGeneration": facade_reads,
        "timed": False,
        "variant": variant,
        "sourceInputs": source_inputs,
    })
    rss.append(measured_read_rss("preflight-imports-complete"))

    case = None
    error = None
    try:
        case = asyncio.run(runner._run_variant(
            variant=variant,
            rows=rows,
            generations=generation_count,
            reads_per_generation=facade_reads,
            trial_index=0,
            variant_order=[variant],
            timed=False,
            diagnostic_acquisition_timeout=15.0,
            complete_pair_after_byte_mismatch=False,
            source_inputs=source_inputs,
            reference=reference,
            rss=rss,
        ))
    except BaseException as caught:
        error = caught
    finally:
        runner._read_rss = original_read_rss
        runner.RuntimeThread.__init__ = original_thread_init
        runner.RuntimeThread.__exit__ = original_thread_exit
        Reader.__init__ = original_reader_init
        Bridge.__init__ = original_bridge_init
        Client.connect = classmethod(original_client_connect)
        Runtime._reserve_working_set = original_reserve

    loaded_modules = runner._capture_project_modules(args.observer_source, args.mesh_source)
    module_map_hash = hashlib.sha256(
        json.dumps(loaded_modules, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    if error is not None:
        summary = {
            "format": "agent-observer.working-set.rss-resource-screen.v2",
            "status": "failed",
            "failureType": type(error).__name__,
            "failureCode": _safe_code(runner, error),
        }
        del error
    else:
        generations = case["generations"]
        expected_shapes = [
            generation["generation"] == index + 1
            and generation["accepted"] is True
            and generation["facadeReads"] == facade_reads
            and generation["detachedLists"] is True
            and generation["detachedRows"] is True
            and generation["selectedRows"] == runner.SELECTED_COUNTS[rows]
            and generation["expectedDtoSha256"]
            and generation["expectedIdsSha256"]
            and generation["reconstructedNativeFrameSha256"]
            for index, generation in enumerate(generations)
        ]
        if len(generations) != generation_count or not all(expected_shapes):
            raise AssertionError("generation_output_shape")
        generation_summaries = []
        for generation in generations:
            event = generation["targetEvent"]
            generation_summaries.append({
                "generation": generation["generation"],
                "accepted": generation["accepted"],
                "selectedRows": generation["selectedRows"],
                "expectedDtoSha256": generation["expectedDtoSha256"],
                "expectedIdsSha256": generation["expectedIdsSha256"],
                "acceptedFullDtoSha256": generation["acceptedFullDtoSha256"],
                "reconstructedNativeFrameSha256": generation["reconstructedNativeFrameSha256"],
                "reconstructedNativeOwnerDigest": generation["reconstructedNativeOwnerDigest"],
                "targetComplete": (
                    event["meshStatus"] == "complete"
                    and event["hostDeliveryStatus"] == "ready"
                    and event["hostViewState"] == "current"
                    and event["proofPresent"] is True
                    and event["proofFresh"] is True
                ),
                "targetRuntimeAccepted": event["runtimeAccepted"],
                "coverageComplete": (
                    variant != "working"
                    or (event["coverageStatus"] == "complete" and event["scopeMemberCount"] == runner.SELECTED_COUNTS[rows])
                ),
                "receiptRuntimeCurrent": any(
                    item.get("accepted") == generation["generation"]
                    and item.get("health") == "current"
                    for item in event["receiptRuntime"]
                ),
                "publicSnapshotProofMatched": len(generation["nativeFrameAudit"]) == 1,
                "publicOwnerDigestProofMatched": (
                    generation["reconstructedNativeOwnerDigest"]
                    == generation["publicPublisherDigestAudit"]["ownerDigest"]
                ),
                "activityTimestampsRenewed": generation["clockAnchor"]["activityTimestampsRenewed"],
            })
        live_after_return = {name: [_alive(ref) for ref in values] for name, values in refs.items()}
        required_dead = ("runtimeThread", "runtime", "state", "reader", "bridge", "client")
        summary = {
            "format": "agent-observer.working-set.rss-resource-screen.v2",
            "status": "pass" if all(item["targetComplete"] and item["coverageComplete"]
                                      and item["receiptRuntimeCurrent"]
                                      and item["publicSnapshotProofMatched"]
                                      and item["publicOwnerDigestProofMatched"]
                                      and item["activityTimestampsRenewed"] is False
                                      for item in generation_summaries)
                      and all(not any(live_after_return[name]) for name in required_dead)
                      else "failed",
            "case": {"variant": variant, "rows": rows, "generations": generation_count,
                     "facadeReadsPerGeneration": facade_reads, "timed": False},
            "generationChecks": generation_summaries,
            "runtimeAfterClose": closed_runtime["scalars"],
            "weakrefsAfterRunReturn": live_after_return,
            "weakrefsExpectedDeadAfterRunReturn": list(required_dead),
            "rssSnapshots": rss,
            "gc": {"enabled": gc.isenabled(), "explicitCollections": 0},
            "cleanupCounts": {
                "readerActiveConnections": case["cleanupCounts"]["readerActiveConnections"],
                "readerConnectionsOpened": case["cleanupCounts"]["readerConnectionsOpened"],
                "readerConnectionsClosed": case["cleanupCounts"]["readerConnectionsClosed"],
                "readerCleanupFailures": case["cleanupCounts"]["readerCleanupFailures"],
                "runtime": case["cleanupCounts"]["runtime"],
                "retainedReaderClients": case["cleanupCounts"]["retainedReaderClients"],
                "retainedBridgeChannels": case["cleanupCounts"]["retainedBridgeChannels"],
            },
            "harnessConnectionHistoryBound": case["meshByteDiagnostic"]["boundedConnectionHistory"],
            "publicByteCountersMatch": case["meshPublicCompletedJsonLineCounters"]["bidirectionalByteCountsMatch"],
            "sensitivePayloadsPersisted": False,
        }
        del case

    released = [item["rssBytes"] for item in rss if item["phase"].endswith("copies-released")]
    tail = released[-16:]
    n = len(tail)
    mean_x = (n - 1) / 2 if n else 0
    mean_y = sum(tail) / n if n else 0
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    slope = (sum((i - mean_x) * (value - mean_y) for i, value in enumerate(tail)) / denominator
             if denominator else None)
    rss_description = {
        "basis": "post-copy-release process VmRSS; final16 of32 accepted generations",
        "samples": len(released), "tailSamples": n,
        "tailMinBytes": min(tail) if tail else None,
        "tailMaxBytes": max(tail) if tail else None,
        "tailFirstBytes": tail[0] if tail else None,
        "tailLastBytes": tail[-1] if tail else None,
        "tailRangeBytes": max(tail) - min(tail) if tail else None,
        "tailOlsBytesPerGeneration": slope,
        "automaticPlateauAcceptance": False,
        "processHeapCapClaim": False,
    }
    report = {
        **summary,
        "classification": "controlled synthetic native IPC to public Mesh watch/proof/facade lifecycle; source RSS resource screen only; status covers function/retirement, not automatic plateau acceptance",
        "sourcePair": SOURCE_PAIR,
        "runner": {
            "path": RUNNER_PATH.name,
            "sha256": sha256(RUNNER_PATH),
            "unchangedCopy": True,
            "configurationOverrides": {"meshCommit": "042fe3a5671fabbedfd36bbef10a8e8abcb25485", "meshSource": "/home/bryan/.cache/agent-observer-working-set-20261018/final-mesh-042fe3a5/src"},
        },
        "inputs": source_inputs,
        "loadedProjectModulesSha256": module_map_hash,
        "loadedProjectModules": loaded_modules,
        "interpreter": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "rssDescription": rss_description,
        "rssScope": "single process VmRSS/VmHWM includes imports, fixture/oracle, instrumentation, owner state, local IPC and facade copies; no heap/encoded-cap or physical-RSS acceptance claim",
        "postCloseOwnershipNote": "ServiceState and current encoded owner buffers remain caller-owned while the in-scope _run_variant frame exists; weakref liveness is checked only after that frame and its detached outputs are discarded.",
        "exclusions": [
            "no provider/native RPC, installed service, wheel, SSH/network, native payload, device, or whole-pipeline RSS claim",
            "no explicit cyclic collection; GC is disabled",
            "the harness connection history is capped at 16 and is not product capacity",
            "public byte counters are application-channel diagnostics, not raw socket or peer-parse proof",
            "the stage metric is the current/maximum source reservation request, not a direct measurement of temporary Python heap bytes",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "variant": variant,
        "rows": rows,
        "generations": generation_count,
        "interpreter": report["interpreter"],
        "rssSamples": len(report.get("rssSnapshots", [])),
        "output": str(output),
    }, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("full", "working"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, choices=(500, 2000), required=True)
    args = parser.parse_args()
    runner = load_runner()
    return _make_case(runner, args.variant, args.output, rows=args.rows, generation_count=32, facade_reads=4)


if __name__ == "__main__":
    raise SystemExit(main())
