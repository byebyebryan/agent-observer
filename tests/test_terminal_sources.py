"""Controlled-server lifecycle tests for finite terminal source fan-in."""

import asyncio
import copy
import os
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from mesh_test_support import require_working_set_sdk
from test_service_runtime import Running, scoped_snapshot

from agent_observer.service_state import ServiceState
from agent_observer.terminal.config import TerminalSource
from agent_observer.terminal.model import build_report
from agent_observer.terminal.sources import read_sources


def synthetic_state(*, count=1, window_ms=0, ttl_ms=30_000, partial=False):
    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=os.geteuid(),
        working_set_window_ms=window_ms,
    )
    sample = scoped_snapshot()
    sample["collectedAt"] = int(time.time() * 1000)
    sample["sources"][0]["capabilities"]["activity"] = True
    if partial:
        sample["sourceHealth"] = "partial"
        sample["sources"][0]["sourceHealth"] = "partial"
        sample["sources"][0]["coverage"]["runtime"]["status"] = "partial"
        sample["sources"][0]["coverage"]["runtime"]["reason"] = "runtime_partial"
    base = copy.deepcopy(sample["sessions"][0])
    sample["sessions"] = []
    for index in range(count):
        row = copy.deepcopy(base)
        thread_id = str(UUID(int=50_000 + index))
        row["identity"]["nativeId"] = thread_id
        row["nativeIds"].update(threadId=thread_id, sessionTreeRootId=thread_id)
        row["activity"].update(
            at=sample["collectedAt"] - 1_000,
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        sample["sessions"].append(row)
    sampled = state.clock()
    state.attempt("codex", "runtime")
    if not state.accept(
        "codex",
        "runtime",
        sample,
        sampled_ms=sampled,
        ttl_ms=ttl_ms,
        runtime_ttl_ms=ttl_ms,
        accepted_boottime_ms=state.clock(),
    ):
        raise AssertionError("synthetic_service_acceptance_required")
    return state, sample


def terminal_source(
    source_id,
    *,
    host="fixture",
    home="default",
    mesh_source="agent_working_set",
    socket="/synthetic/mesh.sock",
    namespace=None,
    window_ms=0,
    max_identities=1024,
    max_payload_mib=4,
):
    return TerminalSource(
        id=source_id,
        host=host,
        home=home,
        label=home.title(),
        mesh_source=mesh_source,
        scope="local",
        socket=Path(socket),
        namespace=namespace or ("sha256:" + "a" * 64),
        window_hours=window_ms // 3_600_000,
        max_identities=max_identities,
        max_payload_mib=max_payload_mib,
    )


def source_from_sample(
    sample, mesh_path, *, source_id="default", mesh_source="agent_working_set", **overrides
):
    namespace = overrides.pop("namespace", sample["sources"][0]["namespace"])
    return terminal_source(
        source_id,
        mesh_source=mesh_source,
        socket=str(mesh_path),
        namespace=namespace,
        **overrides,
    )


def report_for(result, *, mode="list"):
    return build_report(
        result["states"],
        now_boottime_ms=result["nowBoottimeMs"],
        generated_at="2026-10-25T12:00:00.000Z",
        clock=result["clock"],
        mode=mode,
        filters={
            "source": (),
            "host": (),
            "home": (),
            "membership": (),
            "runtime": (),
            "phase": (),
            "query": (),
            "includeChildren": False,
            "includeSystem": False,
            "sort": "activity",
            "group": "none",
            "configPath": "/synthetic/terminal.toml",
        },
    )


class TerminalSourceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if not require_working_set_sdk():
            raise unittest.SkipTest("compatible public Mesh working-set SDK unavailable")

    async def run_controlled(self, state, sample, sources, *, timeout=3.0, configured_reader=None):
        from mesh_plus.api import Bridge
        from mesh_plus.transport import IPCServer

        from agent_observer.mesh_working_set_publisher import make_working_set_publisher

        with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
            source_id = sources[0].mesh_source
            publisher = make_working_set_publisher(
                "fixture", source_id, native.path, window_ms=state.working_set_window_ms
            )
            mesh_path = Path(directory) / "mesh.sock"
            server = await IPCServer(mesh_path, Bridge(publisher).serve).start()
            try:
                selected_sources = tuple(
                    item if item.id == "missing" else replace(item, socket=mesh_path)
                    for item in sources
                )
                if configured_reader is None:
                    return await read_sources(selected_sources, timeout=timeout)
                with patch("mesh_plus.api.configured_reader", side_effect=configured_reader):
                    return await read_sources(selected_sources, timeout=timeout)
            finally:
                await server.close()

    async def test_public_facade_complete_empty_and_partial_coverage(self):
        empty_state, empty_sample = synthetic_state(count=0)
        empty_source = source_from_sample(empty_sample, Path("/synthetic/mesh.sock"))
        empty_result = await self.run_controlled(empty_state, empty_sample, (empty_source,))
        empty_report = report_for(empty_result)
        self.assertEqual(empty_report["totals"]["state"], "complete-empty")
        self.assertEqual(empty_report["result"], "complete")

        partial_state, partial_sample = synthetic_state(count=1, partial=True)
        partial_source = source_from_sample(
            partial_sample, Path("/synthetic/mesh.sock"), source_id="partial"
        )
        partial_result = await self.run_controlled(partial_state, partial_sample, (partial_source,))
        partial_report = report_for(partial_result)
        self.assertEqual(partial_report["result"], "degraded")
        self.assertNotEqual(partial_report["totals"]["state"], "complete-empty")
        self.assertIn(partial_report["sources"][0]["health"], {"partial", "stale"})

    async def test_one_missing_source_preserves_healthy_public_facade_rows(self):
        state, sample = synthetic_state(count=1)
        with tempfile.TemporaryDirectory() as directory:
            healthy = source_from_sample(sample, Path("/synthetic/mesh.sock"), source_id="healthy")
            missing = terminal_source(
                "missing",
                host="missing-host",
                home="default",
                mesh_source="agent_working_set_missing",
                socket=str(Path(directory) / "missing.sock"),
                namespace=sample["sources"][0]["namespace"],
            )
            result = await self.run_controlled(state, sample, (healthy, missing))
        report_value = report_for(result)
        self.assertEqual(report_value["result"], "degraded")
        self.assertEqual(report_value["totals"]["members"], 1)
        self.assertEqual(len(report_value["sessions"]), 1)
        by_id = {item["id"]: item for item in report_value["sources"]}
        self.assertEqual(by_id["healthy"]["health"], "complete")
        self.assertEqual(by_id["missing"]["health"], "unavailable")

    async def test_wrong_namespace_blocks_before_any_row_is_labeled(self):
        state, sample = synthetic_state(count=1)
        source = source_from_sample(
            sample, Path("/synthetic/mesh.sock"), namespace="sha256:" + "b" * 64
        )
        result = await self.run_controlled(state, sample, (source,))
        report_value = report_for(result)
        self.assertEqual(report_value["sources"][0]["health"], "blocked")
        self.assertEqual(report_value["sources"][0]["reason"], "namespace_mismatch")
        self.assertEqual(
            report_value["sources"][0]["observedNamespace"], sample["sources"][0]["namespace"]
        )
        self.assertEqual(report_value["sessions"], [])
        self.assertEqual(report_value["totals"]["members"], 0)

    async def test_slow_peer_wait_rechecks_quiet_expiry_and_final_capture(self):
        state, sample = synthetic_state(count=1, ttl_ms=650)
        from mesh_plus.api import configured_reader as real_configured_reader

        with tempfile.TemporaryDirectory() as directory:
            mesh_path = Path(directory) / "mesh.sock"
            fast = source_from_sample(sample, mesh_path, source_id="fast")
            slow = terminal_source(
                "slow",
                host="slow-host",
                home="default",
                mesh_source="slow_route",
                socket=str(mesh_path),
                namespace=sample["sources"][0]["namespace"],
            )
            reads = []
            expiry_reached = asyncio.Event()
            expiry_scheduled = False
            from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

            original_read = PreparedWorkingSetAgentWatch.read

            def track_read(guard, now, clock):
                nonlocal expiry_scheduled
                read_value = original_read(guard, now, clock)
                leases = [item["membershipExpiresAtMs"] for item in read_value.member_leases]
                reads.append((now, len(read_value.members), min(leases, default=None)))
                if read_value.members and leases and not expiry_scheduled:
                    expiry_scheduled = True
                    delay = max(0, min(leases) - now + 50) / 1000
                    asyncio.get_running_loop().call_later(delay, expiry_reached.set)
                return read_value

            async def configured(domain, *, source, **kwargs):
                if source == "slow_route":
                    await expiry_reached.wait()
                    raise RuntimeError("synthetic slow source completed after peer expiry")
                return await real_configured_reader(domain, source=source, **kwargs)

            with patch.object(PreparedWorkingSetAgentWatch, "read", track_read):
                result = await self.run_controlled(
                    state, sample, (fast, slow), timeout=10.0, configured_reader=configured
                )
        report_value = report_for(result)
        self.assertFalse(result["timedOut"])
        self.assertGreater(len(reads), 2)
        first_positive = next(item for item in reads if item[1] > 0)
        last_read = reads[-1]
        self.assertIsNotNone(first_positive[2])
        self.assertGreater(last_read[0], first_positive[2])
        self.assertEqual(last_read[1], 0)
        by_id = {item["id"]: item for item in report_value["sources"]}
        fast_state = next(item for item in result["states"] if item["config"]["id"] == "fast")
        slow_state = next(item for item in result["states"] if item["config"]["id"] == "slow")
        self.assertEqual(slow_state["reason"], "runtimeerror")
        if by_id["fast"]["health"] in {"partial", "stale"}:
            self.assertEqual(fast_state["lifecycle"], "observing")
            self.assertTrue(fast_state["baseline"])
        else:
            self.assertEqual(by_id["fast"]["health"], "unavailable")
            self.assertIn(fast_state["reason"], {"mesh_resync", "mesh_delivery_disconnected"})
            self.assertTrue(
                fast_state.get("delivery_error"),
                "unavailable health lacks bounded SDK delivery evidence: "
                f"lifecycle={fast_state['lifecycle']} reason={fast_state['reason']} reads={reads}",
            )
            self.assertEqual(by_id["fast"].get("deliveryError"), fast_state["delivery_error"])
            self.assertIn(fast_state["delivery_error"], by_id["fast"]["reasons"])
        self.assertEqual(by_id["slow"]["health"], "unavailable")
        self.assertEqual(report_value["sessions"], [])

    async def test_window_mismatch_resync_preserves_synthetic_sdk_delivery_error(self):
        state, sample = synthetic_state(count=1)
        source = source_from_sample(
            sample,
            Path("/synthetic/mesh.sock"),
            source_id="mismatched-window",
            window_ms=3_600_000,
        )
        result = await self.run_controlled(state, sample, (source,))
        source_state = result["states"][0]
        self.assertEqual(source_state["reason"], "mesh_resync")
        self.assertEqual(
            source_state["delivery_error"],
            "channel_failed",
            "source did not preserve synthetic public-frame delivery evidence",
        )
        report_value = report_for(result)
        self.assertEqual(report_value["sources"][0]["deliveryError"], "channel_failed")
        self.assertIn("channel_failed", report_value["sources"][0]["reasons"])

    async def test_more_than_four_sources_progress_as_setups_settle(self):
        state, sample = synthetic_state(count=1)
        from mesh_plus.api import configured_reader as real_configured_reader

        active_setups = 0
        maximum_setups = 0
        setup_calls = 0
        lock = asyncio.Lock()

        async def configured(domain, *, source, **kwargs):
            nonlocal active_setups, maximum_setups, setup_calls
            async with lock:
                active_setups += 1
                setup_calls += 1
                maximum_setups = max(maximum_setups, active_setups)
            try:
                await asyncio.sleep(0.02)
                return await real_configured_reader(domain, source=source, **kwargs)
            finally:
                async with lock:
                    active_setups -= 1

        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "mesh.sock"
            sources = tuple(
                source_from_sample(sample, socket, source_id=f"source-{index}")
                for index in range(6)
            )
            result = await self.run_controlled(
                state, sample, sources, timeout=4.0, configured_reader=configured
            )

        report_value = report_for(result)
        self.assertEqual(setup_calls, 6)
        self.assertLessEqual(maximum_setups, 4)
        self.assertEqual(len(report_value["sources"]), 6)
        self.assertTrue(all(source["baseline"] for source in result["states"]))
        self.assertTrue(all(source["lifecycle"] == "observing" for source in result["states"]))

    async def test_final_timeout_cancels_and_drains_pending_setup(self):
        state, sample = synthetic_state(count=1)
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def configured(*_args, **_kwargs):
            started.set()
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        source = source_from_sample(sample, Path("/synthetic/mesh.sock"))
        result = await self.run_controlled(
            state, sample, (source,), timeout=0.15, configured_reader=configured
        )
        self.assertTrue(started.is_set())
        self.assertTrue(cancelled.is_set())
        self.assertTrue(result["timedOut"])
        self.assertEqual(result["states"][0]["lifecycle"], "timed_out")

    async def test_raw_heartbeat_is_admitted_without_snapshot_export(self):
        from agent_observer.terminal.sources import _new_state, _source_worker

        source = terminal_source("heartbeat")
        binding = {"bootId": "fixture-boot", "timeNamespace": "time:7"}
        state = _new_state(source, binding)
        heartbeat = {"mesh": {"kind": "heartbeat"}}
        accepted = []

        class AdmittedResponse:
            pass

        class Guard:
            def __init__(self, *_args, **_kwargs):
                pass

            def accept(self, frame):
                accepted.append(frame)

            def read(self, _now, _clock):
                return SimpleNamespace(
                    context={"hosts": [{"hostId": "fixture", "delivery": {"status": "ready"}}]},
                    scopes=[],
                    members=[],
                    uncertain=[],
                    nonmembers=[],
                    member_leases=[],
                )

            def disconnect(self):
                pass

        class Reader:
            def execute_admitted(self, _request):
                async def frames():
                    yield heartbeat
                    await asyncio.sleep(5)

                return frames()

        async def configured_reader(*_args, **_kwargs):
            return Reader()

        dependencies = {
            "AdmittedResponse": AdmittedResponse,
            "configured_reader": configured_reader,
            "WorkingSetAgentProfile": lambda _window_ms: SimpleNamespace(
                descriptor=SimpleNamespace(profile_id="fixture-profile")
            ),
            "PreparedWorkingSetAgentWatch": Guard,
            "boottime_ms": lambda: int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000),
        }
        final_event = asyncio.Event()
        final_reason = [None]
        worker = asyncio.create_task(
            _source_worker(
                state,
                source,
                dependencies=dependencies,
                semaphore=asyncio.Semaphore(4),
                final_event=final_event,
                final_reason=final_reason,
                clock_binding=binding,
            )
        )
        await asyncio.wait_for(state["settled"].wait(), timeout=1)
        final_event.set()
        await asyncio.wait_for(worker, timeout=1)
        self.assertEqual(accepted, [heartbeat])
        self.assertEqual(state["lifecycle"], "observing")
        self.assertIsNone(state["reason"])

    async def test_capture_clock_is_frozen_before_slow_guard_cleanup(self):
        state, sample = synthetic_state(count=1, ttl_ms=5_000)
        from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

        original_disconnect = PreparedWorkingSetAgentWatch.disconnect
        original_read = PreparedWorkingSetAgentWatch.read
        activity_expiry = [None]

        def short_activity_lease(guard, now, clock):
            read_value = original_read(guard, now, clock)
            if activity_expiry[0] is None:
                activity_expiry[0] = now + 400
            for lease in read_value.member_leases:
                lease["fieldExpiresAtMs"]["activity"] = activity_expiry[0]
            return read_value

        def delayed_disconnect(guard):
            original_disconnect(guard)
            time.sleep(1.1)

        with tempfile.TemporaryDirectory() as directory:
            source = source_from_sample(sample, Path(directory) / "mesh.sock")
            with (
                patch.object(PreparedWorkingSetAgentWatch, "read", short_activity_lease),
                patch.object(PreparedWorkingSetAgentWatch, "disconnect", delayed_disconnect),
            ):
                result = await self.run_controlled(state, sample, (source,), timeout=2.0)
        report_value = report_for(result)
        source_doc = report_value["sources"][0]
        current_after_cleanup = int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
        self.assertEqual(result["nowBoottimeMs"], source_doc["captureBoottimeMs"])
        self.assertEqual(
            report_value["result"],
            "complete",
            f"source health={source_doc['health']} reasons={source_doc['reasons']} capture={source_doc['captureBoottimeMs']}",
        )
        self.assertEqual(len(report_value["sessions"]), 1)
        activity_expiry = report_value["sessions"][0]["details"]["fieldExpiresAtBoottimeMs"][
            "activity"
        ]
        self.assertGreater(activity_expiry, source_doc["captureBoottimeMs"])
        self.assertGreaterEqual(current_after_cleanup, activity_expiry)
        self.assertEqual(report_value["sessions"][0]["activity"]["health"], "current")


if __name__ == "__main__":
    unittest.main()
