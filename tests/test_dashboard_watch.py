"""Persistent ownership/scheduling tests; injected cases are not SDK admission proof."""

import asyncio
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_terminal_model import NAMESPACE, lease, read, row
from test_terminal_sources import source_from_sample, synthetic_state, terminal_source

from agent_observer.terminal.watch import PersistentSources, blocking_failure, next_deadline

FILTERS = {
    "membership": (),
    "runtime": (),
    "phase": (),
    "query": (),
    "includeChildren": False,
    "includeSystem": False,
    "sort": "activity",
    "group": "none",
}


async def until(predicate, timeout=2):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.005)


class Frame:
    def __init__(self, *, kind="view", namespace=NAMESPACE, count=1):
        self.kind, self.namespace, self.count = kind, namespace, count

    def context(self):
        return {"mesh": {"kind": self.kind, "hosts": []}}

    def snapshot(self):
        return {
            "mesh": {
                "kind": self.kind,
                "hosts": [
                    {
                        "owner": {
                            "metadata": {
                                "scopes": [
                                    {
                                        "members": [
                                            {"identity": row(str(i))["identity"]}
                                            for i in range(self.count)
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                ],
            }
        }


class Harness:
    def __init__(self):
        self.now = 1000
        self.clock = {"bootId": "fixture-boot", "timeNamespace": "time:7"}
        self.queues = {}
        self.guards = []
        self.closed_streams = 0
        self.cleanup_started = asyncio.Event()
        self.cleanup_finished = asyncio.Event()
        self.cleanup_delay = 0
        self.alias_id = None
        self.disconnect_failure = False
        self.setup_barrier = None
        self.setup_cancelled = asyncio.Event()
        self.setup_calls = []
        self.field_deadline = None

    def dependencies(self):
        harness = self

        class Guard:
            def __init__(self, _request, *, profile, **_kwargs):
                self.source = profile.source
                self.closed = False
                self.frame = None
                self.reads = 0
                harness.guards.append(self)

            def accept(self, frame):
                if self.closed:
                    raise AssertionError("retired_guard_reused")
                self.frame = frame

            def read(self, now, clock):
                assert not self.closed and clock == harness.clock
                self.reads += 1
                present = now < 1700
                native_id = harness.alias_id or self.source
                value = read(
                    rows=[row(native_id)] if present else [],
                    leases=[lease(native_id)] if present else [],
                )
                value.scopes[0]["namespace"] = self.frame.namespace
                if now >= 1700:
                    value.scopes[0]["coverage"].update(status="partial", expiresAtMs=None)
                if harness.field_deadline is not None and value.member_leases:
                    value.member_leases[0]["fieldExpiresAtMs"] = {"runtime": harness.field_deadline}
                return value

            def disconnect(self):
                if harness.disconnect_failure:
                    raise RuntimeError("synthetic pure guard cleanup failure")
                self.closed = True

        class Reader:
            def __init__(self, source):
                self.queue = asyncio.Queue()
                harness.queues.setdefault(source, []).append(self.queue)

            def execute_admitted(self, request):
                assert request["access"] == "cached"

                async def stream():
                    try:
                        while True:
                            value = await self.queue.get()
                            if value is None:
                                return
                            yield value
                    finally:
                        harness.cleanup_started.set()
                        await asyncio.sleep(harness.cleanup_delay)
                        harness.closed_streams += 1
                        harness.cleanup_finished.set()

                return stream()

        async def configured(_domain, *, source, profile, **kwargs):
            assert kwargs["report_routes"] is False
            harness.setup_calls.append(asyncio.get_running_loop().time())
            barrier = harness.setup_barrier
            if barrier is not None:
                try:
                    await barrier.wait()
                except asyncio.CancelledError:
                    harness.setup_cancelled.set()
                    raise
            profile.source = source
            return Reader(source)

        return {
            "clock_domain": lambda: dict(harness.clock),
            "boottime_ms": lambda: harness.now,
            "WorkingSetAgentProfile": lambda window: SimpleNamespace(
                descriptor=SimpleNamespace(profile_id="fixture"), window=window
            ),
            "PreparedWorkingSetAgentWatch": Guard,
            "AdmittedResponse": Frame,
            "configured_reader": configured,
        }

    async def baseline(self, watch, source="working", **kwargs):
        await until(lambda: self.queues.get(source))
        await self.queues[source][-1].put(Frame(**kwargs))
        await until(
            lambda: (
                watch.slots[0].state["read"] is not None
                or watch.slots[0].stage in {"blocked", "retry-wait"}
            )
        )


class PersistentWatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_clock_worker_does_not_sleep_past_a_known_receiving_deadline(self):
        harness = Harness()
        watch = PersistentSources(
            (terminal_source("default", mesh_source="working"),),
            dependencies=harness.dependencies(),
        )
        watch.slots[0].deadline = harness.now + 5
        sleeps = []

        async def stop_at_sleep(delay):
            sleeps.append(delay)
            watch._stop.set()

        with patch("agent_observer.terminal.watch.asyncio.sleep", stop_at_sleep):
            await watch._clock_worker()
        self.assertEqual(sleeps, [0.005])
        self.assertIsNone(watch.cleanup_error)

    async def test_priority_latches_a_shorter_deadline_not_yet_seen_by_the_ui(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        old_projection = watch.projection(FILTERS)
        self.assertEqual(old_projection.next_deadline_boottime_ms, 1500)
        harness.field_deadline = 1005
        revision = watch.revision
        await harness.queues["working"][-1].put(Frame())
        await until(lambda: watch.revision > revision)
        self.assertEqual(watch.slots[0].deadline, 1005)
        self.assertFalse(watch.requires_priority_refresh(old_projection))
        harness.now = 1006
        watch.refresh_due()
        self.assertEqual(watch.slots[0].deadline, 1500)
        self.assertTrue(watch.requires_priority_refresh(old_projection))
        current = watch.projection(FILTERS)
        self.assertFalse(watch.requires_priority_refresh(current))

    async def test_only_revocation_and_due_deadlines_require_priority_refresh(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        projection = watch.projection(FILTERS)
        self.assertEqual(projection.next_deadline_boottime_ms, 1500)
        self.assertFalse(watch.requires_priority_refresh(projection))
        revision = watch.revision
        await harness.queues["working"][-1].put(Frame())
        await until(lambda: watch.revision > revision)
        self.assertFalse(watch.is_current(projection))
        self.assertFalse(watch.requires_priority_refresh(projection))
        projection = watch.projection(FILTERS)
        harness.now = 1500
        self.assertTrue(watch.requires_priority_refresh(projection))
        projection = watch.projection(FILTERS)
        self.assertEqual(projection.next_deadline_boottime_ms, 1700)
        self.assertFalse(watch.requires_priority_refresh(projection))
        epoch = watch.status()[0]["epoch"]
        await harness.queues["working"][-1].put(Frame(kind="gap"))
        await until(lambda: watch.status()[0]["epoch"] > epoch)
        self.assertTrue(watch.requires_priority_refresh(projection))

    async def make_watch(self, harness, sources=None):
        sources = sources or (terminal_source("default", mesh_source="working"),)
        watch = PersistentSources(
            sources,
            dependencies=harness.dependencies(),
            setup_interval=0,
            retry_steps=(0.05,),
            jitter=lambda: 1,
        )
        await watch.start()
        self.addAsyncCleanup(watch.close)
        return watch

    def test_deadlines_include_absence_receipts_fields_and_ignore_native_horizons(self):
        value = read()
        value.context["hosts"][0]["receipts"] = [{"expiresAtMs": 1400}]
        value.uncertain = [{"horizonBoottimeMs": 1001}]
        self.assertEqual(next_deadline(value, 1000), 1400)
        value.member_leases = [{"fieldExpiresAtMs": {"runtime": 1200}}]
        self.assertEqual(next_deadline(value, 1000), 1200)
        self.assertEqual(next_deadline(value, 1400), 2000)
        self.assertIsNone(next_deadline(value, 2000))
        self.assertFalse(blocking_failure("channel_failed"))
        self.assertTrue(blocking_failure("namespace_mismatch"))

    def test_empty_scope_and_negative_receipts_keep_only_future_receiving_deadlines(self):
        value = read(scopes=False, nonmembers=[{"horizonBoottimeMs": 1001}])
        value.context["hosts"][0]["receipts"] = [
            {"expiresAtMs": v} for v in (None, True, -1, 1000, "1002", 1500)
        ]
        self.assertEqual(next_deadline(value, 1000), 1500)
        self.assertIsNone(next_deadline(value, 1500))
        empty = read()
        self.assertEqual(next_deadline(empty, 1000), 2000)

    async def test_cleanup_failure_blocks_instead_of_replacing_the_guard(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        harness.disconnect_failure = True
        await harness.queues["working"][-1].put(Frame(kind="gap"))
        await until(lambda: watch.status()[0]["stage"] == "blocked")
        await asyncio.sleep(0.08)
        self.assertEqual(watch.status()[0]["attempts"], 1)
        self.assertEqual(watch.report(FILTERS)["sources"][0]["health"], "blocked")
        self.assertEqual(watch.status()[0]["cleanupError"], "runtimeerror")
        self.assertEqual(watch.report(FILTERS)["totals"]["members"], 0)
        harness.disconnect_failure = False

    async def test_clock_change_during_reader_setup_cancels_the_old_attempt(self):
        harness = Harness()
        harness.setup_barrier = asyncio.Event()
        watch = await self.make_watch(harness)
        await until(lambda: len(harness.setup_calls) == 1)
        harness.clock["timeNamespace"] = "time:8"
        watch.refresh_due()
        await harness.setup_cancelled.wait()
        self.assertEqual(len(harness.guards), 0)
        harness.setup_barrier.set()
        await until(lambda: watch.status()[0]["attempts"] == 2)
        await harness.baseline(watch)
        self.assertEqual(watch.states[0]["clock"]["timeNamespace"], "time:8")
        self.assertEqual(watch.report(FILTERS)["result"], "complete")

    async def test_manual_retry_is_globally_throttled(self):
        harness = Harness()
        sources = (
            terminal_source("a", mesh_source="working"),
            terminal_source("b", mesh_source="sibling", home="second"),
        )
        watch = await self.make_watch(harness, sources)
        await until(lambda: len(harness.queues) == 2)
        for values in harness.queues.values():
            await values[-1].put(Frame(namespace="sha256:" + "b" * 64))
        await until(lambda: all(s.stage == "blocked" for s in watch.slots))
        self.assertTrue(watch.retry("a"))
        self.assertFalse(watch.retry("b"))
        harness.now += 1000
        self.assertTrue(watch.retry("b"))

    async def test_queued_projection_and_pending_frame_cannot_survive_revocation(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        projection = watch.projection(FILTERS)
        self.assertTrue(watch.is_current(projection))
        harness.queues["working"][-1].put_nowait(Frame())
        watch.request_close()
        await watch.close()
        self.assertFalse(watch.is_current(projection))
        self.assertEqual(watch.report(FILTERS)["totals"]["members"], 0)

    async def test_global_default_start_spacing_and_four_setup_slots(self):
        harness = Harness()
        sources = tuple(
            terminal_source(f"s{i}", mesh_source=f"working{i}", home=f"h{i}") for i in range(8)
        )
        watch = await self.make_watch(harness, sources)
        await until(lambda: len(harness.queues) == 4)
        await asyncio.sleep(0.03)
        self.assertEqual(len(harness.queues), 4)
        for queues in tuple(harness.queues.values()):
            await queues[-1].put(Frame())
        await until(lambda: len(harness.queues) == 8)
        for queues in tuple(harness.queues.values()):
            if queues[-1].empty():
                await queues[-1].put(Frame())
        await until(lambda: watch.report(FILTERS)["totals"]["members"] == 8)
        await watch.close()

        spaced = Harness()
        second = PersistentSources(
            (
                terminal_source("a", mesh_source="one"),
                terminal_source("b", mesh_source="two", home="second"),
            ),
            dependencies=spaced.dependencies(),
        )
        await second.start()
        try:
            await until(lambda: len(spaced.setup_calls) == 2)
            self.assertGreaterEqual(spaced.setup_calls[1] - spaced.setup_calls[0], 0.98)
        finally:
            await second.close()

    async def test_setup_timeout_cancels_owned_setup_and_preserves_unknown_coverage(self):
        harness = Harness()
        harness.setup_barrier = asyncio.Event()
        watch = await self.make_watch(harness)
        watch.connect_timeout = 1
        await until(lambda: watch.status()[0]["reason"] == "baseline_timeout")
        self.assertTrue(harness.setup_cancelled.is_set())
        report = watch.report(FILTERS)
        self.assertEqual(report["totals"]["members"], 0)
        self.assertNotEqual(report["totals"]["state"], "complete-empty")

    async def test_retry_steps_jitter_and_stable_delivery_reset(self):
        harness = Harness()
        deps = harness.dependencies()

        async def unavailable(*_args, **_kwargs):
            raise ConnectionError("synthetic transport failure")

        deps["configured_reader"] = unavailable
        watch = PersistentSources(
            (terminal_source("default", mesh_source="working"),),
            dependencies=deps,
            setup_interval=0,
            jitter=lambda: 0.8,
        )
        await watch.start()
        try:
            for index, step in enumerate((1, 2, 4, 8, 16, 30, 30), 1):
                await until(
                    lambda n=index: (
                        watch.status()[0]["attempts"] == n
                        and watch.status()[0]["stage"] == "retry-wait"
                    )
                )
                self.assertEqual(
                    watch.status()[0]["retryAtBoottimeMs"] - harness.now, int(step * 0.8 * 1000)
                )
                harness.now += 1000
                self.assertTrue(watch.retry("default"))
            deps["configured_reader"] = harness.dependencies()["configured_reader"]
            await harness.baseline(watch)
            harness.now += 60_001
            await harness.queues["working"][-1].put(Frame())
            await until(lambda: watch.slots[0].failure_step == 0)
            self.assertEqual(watch.slots[0].failure_step, 0)
        finally:
            await watch.close()

    async def test_quiet_checks_do_not_repeat_projection_and_expiry_is_not_empty(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        self.assertEqual(watch.report(FILTERS)["totals"]["members"], 1)
        original = watch.metrics["guardReads"]
        for _ in range(20):
            harness.now += 1
            watch.refresh_due()
        self.assertEqual(watch.metrics["guardReads"], original)
        harness.now = 1500
        self.assertEqual(watch.report(FILTERS)["sessions"][0]["membership"], "recent")
        harness.now = 1700
        result = watch.report(FILTERS)
        self.assertEqual(result["totals"]["members"], 0)
        self.assertNotEqual(result["totals"]["state"], "complete-empty")
        self.assertEqual(result["sources"][0]["health"], "partial")

    async def test_recovery_requires_a_new_guard_and_a_new_baseline(self):
        harness = Harness()
        sources = (
            terminal_source("a", mesh_source="working"),
            terminal_source("b", mesh_source="sibling", home="second"),
        )
        watch = await self.make_watch(harness, sources)
        await harness.baseline(watch)
        await until(lambda: harness.queues.get("sibling"))
        await harness.queues["sibling"][-1].put(Frame())
        await until(lambda: watch.report(FILTERS)["totals"]["members"] == 2)
        first = harness.guards[0]
        projection = watch.projection(FILTERS)
        await harness.queues["working"][-1].put(None)
        await until(lambda: len(harness.queues["working"]) == 2)
        self.assertTrue(first.closed)
        self.assertFalse(watch.is_current(projection))
        self.assertFalse(watch._closing)
        result = watch.report(FILTERS)
        self.assertEqual(result["totals"]["members"], 1)
        self.assertNotEqual(result["result"], "complete")
        await harness.queues["working"][-1].put(Frame())
        await until(lambda: watch.report(FILTERS)["totals"]["members"] == 2)
        self.assertIsNot(first, harness.guards[-1])
        self.assertTrue(watch.is_current(watch.projection(FILTERS)))

    async def test_wrong_namespace_blocks_until_explicit_retry(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch, namespace="sha256:" + "b" * 64)
        await until(lambda: watch.slots[0].stage == "blocked")
        await asyncio.sleep(0.08)
        self.assertEqual(watch.slots[0].attempts, 1)
        self.assertEqual(watch.report(FILTERS)["sources"][0]["reason"], "namespace_mismatch")
        self.assertTrue(watch.retry("default"))
        await until(lambda: watch.slots[0].attempts == 2)
        self.assertFalse(watch.retry("default"))
        await harness.queues["working"][-1].put(Frame())
        await until(lambda: watch.report(FILTERS)["result"] == "complete")

    async def test_receiving_clock_change_revokes_before_new_attempt(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        first = harness.guards[0]
        projection = watch.projection(FILTERS)
        harness.clock = {"bootId": "fixture-boot", "timeNamespace": "time:8"}
        harness.queues["working"][-1].put_nowait(Frame())
        # The frame task may complete, but its worker cannot publish before
        # this queued clock barrier invalidates the original source epoch.
        asyncio.get_running_loop().call_soon(watch.refresh_due)
        await asyncio.sleep(0)
        self.assertFalse(watch.is_current(projection))
        self.assertFalse(watch._closing)
        self.assertEqual(watch.report(FILTERS)["totals"]["members"], 0)
        self.assertTrue(first.closed)
        await until(lambda: watch.slots[0].attempts == 2)
        await harness.queues["working"][-1].put(Frame())
        await until(lambda: watch.report(FILTERS)["result"] == "complete")
        self.assertEqual(watch.states[0]["clock"]["timeNamespace"], "time:8")

    async def test_capacity_failure_is_visible_and_never_silently_truncated(self):
        harness = Harness()
        watch = await self.make_watch(
            harness, (terminal_source("small", mesh_source="working", max_identities=1),)
        )
        await harness.baseline(watch, count=2)
        await until(lambda: watch.slots[0].stage == "blocked")
        result = watch.report(FILTERS)
        self.assertEqual(result["sources"][0]["reason"], "source_identity_capacity")
        self.assertEqual(result["totals"]["members"], 0)
        self.assertEqual(watch.metrics["guardReads"], 0)

    async def test_conflicting_exact_claims_block_all_sources_until_explicit_retry(self):
        harness = Harness()
        harness.alias_id = "same-exact-identity"
        sources = (
            terminal_source("a", mesh_source="working"),
            terminal_source("b", mesh_source="sibling", home="second"),
        )
        watch = await self.make_watch(harness, sources)
        await until(lambda: len(harness.queues) == 2)
        for values in harness.queues.values():
            await values[-1].put(Frame())
        await until(lambda: all(s.state["read"] is not None for s in watch.slots))
        result = watch.report(FILTERS)
        self.assertEqual(result["totals"]["members"], 0)
        self.assertTrue(all(s["reason"] == "identity_conflict" for s in result["sources"]))
        await until(lambda: all(s.stage == "blocked" for s in watch.slots))
        self.assertTrue(all(g.closed for g in harness.guards))
        await asyncio.sleep(0.08)
        self.assertEqual([s.attempts for s in watch.slots], [1, 1])

    async def test_a_closing_attempt_cannot_be_replaced_by_manual_retry(self):
        harness = Harness()
        harness.cleanup_delay = 0.15
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        await harness.queues["working"][-1].put(Frame(kind="gap"))
        await harness.cleanup_started.wait()
        self.assertEqual(watch.status()[0]["stage"], "retiring")
        self.assertFalse(watch.retry("default"))
        self.assertEqual(watch.status()[0]["attempts"], 1)
        await harness.cleanup_finished.wait()
        await until(lambda: watch.status()[0]["attempts"] == 2)

    async def test_unchanged_admitted_heartbeat_does_not_rebuild_a_report(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        first = watch.report(FILTERS)
        count = watch.metrics["guardReads"]
        await harness.queues["working"][-1].put(Frame(kind="heartbeat"))
        await until(lambda: watch.metrics["frames"] == 2)
        self.assertEqual(watch.metrics["guardReads"], count)
        self.assertIs(watch.report(FILTERS), first)

    async def test_clock_failure_revokes_every_current_source(self):
        harness = Harness()
        watch = await self.make_watch(harness)
        await harness.baseline(watch)

        def unavailable():
            raise OSError("synthetic clock failure")

        watch.dependencies["clock_domain"] = unavailable
        await until(lambda: watch.cleanup_error is not None)
        self.assertEqual(watch.cleanup_error, "receiving_clock_unavailable")
        self.assertEqual(watch.report(FILTERS)["totals"]["members"], 0)
        self.assertNotEqual(watch.report(FILTERS)["totals"]["state"], "complete-empty")

    async def test_repeated_close_cancellation_does_not_interrupt_cleanup(self):
        harness = Harness()
        harness.cleanup_delay = 0.15
        watch = await self.make_watch(harness)
        await harness.baseline(watch)
        watch.request_close()
        task = asyncio.create_task(watch.close())
        await harness.cleanup_started.wait()
        task.cancel()
        await asyncio.sleep(0.02)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(harness.cleanup_finished.is_set())
        self.assertEqual(harness.closed_streams, 1)
        self.assertEqual(watch._tasks, [])
        self.assertEqual(watch.status()[0]["stage"], "closed")


class ControlledPersistentWatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_public_disconnect_recoveries_release_owned_resources(self):
        initial_tasks = len(asyncio.all_tasks())
        initial_fds = len(os.listdir("/proc/self/fd"))
        from mesh_test_support import require_working_set_sdk

        if not require_working_set_sdk():
            self.skipTest("compatible working-set SDK required")
        from mesh_plus.api import Bridge
        from mesh_plus.transport import IPCServer
        from test_service_runtime import Running

        from agent_observer.mesh_working_set_publisher import make_working_set_publisher

        state, sample = synthetic_state(ttl_ms=120_000)
        with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "mesh.sock"
            publisher = make_working_set_publisher(
                "fixture", "agent_working_set", native.path, window_ms=0
            )
            channels = set()

            async def handler(channel):
                channels.add(channel)
                try:
                    await Bridge(publisher).serve(channel)
                finally:
                    channels.discard(channel)

            server = await IPCServer(socket, handler).start()
            watch = PersistentSources(
                (source_from_sample(sample, socket),),
                setup_interval=0,
                retry_steps=(0.01,),
                jitter=lambda: 1,
            )
            try:
                await watch.start()
                await until(lambda: watch.report(FILTERS)["result"] == "complete")
                await asyncio.sleep(0.05)
                tasks_before = len(asyncio.all_tasks())
                fds_before = len(os.listdir("/proc/self/fd"))
                cycles = int(os.environ.get("AO_DASHBOARD_CHURN_CYCLES", "3"))
                self.assertGreaterEqual(cycles, 1)
                self.assertLessEqual(cycles, 1000)
                for _ in range(cycles):
                    epoch = watch.status()[0]["epoch"]
                    # An abrupt delivery loss closes owned test channels first.
                    # Graceful publisher shutdown may wait for its next request;
                    # that owner lifecycle is not the consumer outage being tested.
                    await asyncio.gather(*(channel.close() for channel in tuple(channels)))
                    await server.close()
                    await until(lambda prior=epoch: watch.status()[0]["epoch"] > prior)
                    self.assertEqual(watch.report(FILTERS)["totals"]["members"], 0)
                    server = await IPCServer(socket, handler).start()
                    await until(lambda: watch.report(FILTERS)["result"] == "complete")
                await asyncio.sleep(0.05)
                self.assertLessEqual(len(asyncio.all_tasks()), tasks_before)
                self.assertLessEqual(len(os.listdir("/proc/self/fd")), fds_before)
            finally:
                await watch.close()
                await server.close()
            self.assertIsNone(watch.cleanup_error)
        self.assertLessEqual(len(asyncio.all_tasks()), initial_tasks)
        self.assertLessEqual(len(os.listdir("/proc/self/fd")), initial_fds)

    async def test_public_cached_facade_quiet_expiry_and_namespace_failure(self):
        from mesh_test_support import require_working_set_sdk

        if not require_working_set_sdk():
            self.skipTest("compatible working-set SDK required")
        from mesh_plus.api import Bridge
        from mesh_plus.transport import IPCServer
        from test_service_runtime import Running

        from agent_observer.mesh_working_set_publisher import make_working_set_publisher

        state, sample = synthetic_state(ttl_ms=600)
        with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "mesh.sock"
            publisher = make_working_set_publisher(
                "fixture", "agent_working_set", native.path, window_ms=0
            )
            server = await IPCServer(socket, Bridge(publisher).serve).start()
            source = source_from_sample(sample, socket)
            wrong = replace(
                source, id="wrong", namespace="sha256:" + "c" * 64, mesh_source="agent_working_set"
            )
            # Separate supervisors intentionally exercise one failed binding
            # beside an independently healthy reader over the same fixture.
            watch = PersistentSources((source,), setup_interval=0)
            bad = PersistentSources((wrong,), setup_interval=0)
            try:
                await watch.start()
                await bad.start()
                await until(lambda: watch.report(FILTERS)["totals"]["members"] == 1)
                await until(lambda: bad.status()[0]["stage"] == "blocked")
                self.assertEqual(bad.report(FILTERS)["sources"][0]["reason"], "namespace_mismatch")
                await until(lambda: watch.report(FILTERS)["totals"]["members"] == 0)
                self.assertNotEqual(watch.report(FILTERS)["totals"]["state"], "complete-empty")
            finally:
                await asyncio.gather(watch.close(), bad.close())
                await server.close()
            self.assertIsNone(watch.cleanup_error)
