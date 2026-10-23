"""Focused lifecycle and content-boundary tests for the developer example."""

import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_read_cache import fixture as service_fixture
from test_service_runtime import Running, scoped_snapshot

from agent_observer.service_public import ContractError, ReadCache
from agent_observer.service_state import ServiceState
from agent_observer.utility_read import (
    local_failure_code,
    local_summary,
    parser,
    run_local,
    run_mesh,
    ticked,
)


def assert_content_free(test_case, value):
    forbidden = {"title", "cwd", "workspace", "prompt", "content", "payload", "raw"}
    if isinstance(value, dict):
        test_case.assertFalse(forbidden.intersection(value))
        for item in value.values():
            assert_content_free(test_case, item)
    elif isinstance(value, list):
        for item in value:
            assert_content_free(test_case, item)


class CurrentSummaryLocalTests(unittest.TestCase):
    def make_cache(self):
        frame = service_fixture()
        return ReadCache(
            host_scope=frame["hostScope"],
            uid=frame["uid"],
            boot_id=frame["bootId"],
            clock_domain=frame["clockDomain"],
        ), frame

    def test_public_contract_reasons_are_safely_bounded(self):
        class ErrorWithCode(Exception):
            code = "service_transport_timeout"

        self.assertEqual(
            local_failure_code(ContractError("service_transport_timeout")),
            "service_transport_timeout",
        )
        self.assertEqual(local_failure_code(ContractError("invalid reason")), "service_read_failed")
        self.assertEqual(local_failure_code(ErrorWithCode()), "errorwithcode")

    def test_complete_empty_is_distinct_from_warming_partial_and_failure(self):
        cache, frame = self.make_cache()
        warming = local_summary(cache.current(15000), host="fixture", clock={})
        self.assertEqual(warming["view"]["state"], "warming")

        empty = copy.deepcopy(frame)
        empty["snapshot"]["sessions"] = []
        result = cache.accept(empty, now_ms=15000)
        current = local_summary(result, host="fixture", clock={})
        self.assertEqual(current["view"]["state"], "complete-empty")
        self.assertEqual(current["view"]["sessionCount"], 0)
        self.assertTrue(current["view"]["sources"])
        self.assertTrue(
            all(
                item["coverage"]["runtime"]["status"] == "complete"
                and item["coverage"]["saved"]["status"] == "complete"
                for item in current["view"]["sources"]
            )
        )

        cache.reset()
        cache.accept(frame, now_ms=15000)
        quiet = local_summary(cache.current(20000), host="fixture", clock={})
        self.assertIn(quiet["view"]["state"], {"partial", "stale"})
        self.assertTrue(any(not item["current"] for item in quiet["view"]["components"]))

        cache.invalidate("read_disconnected")
        failed = local_summary(cache.current(20001), host="fixture", clock={})
        self.assertEqual(failed["view"]["state"], "unavailable")

    def test_same_provider_two_homes_keep_exact_namespace_identity(self):
        rows = [
            {
                "identity": {
                    "hostScope": "fixture",
                    "provider": "codex",
                    "namespace": "a" * 64,
                    "nativeIdKind": "thread_id",
                    "nativeId": "00000000-0000-0000-0000-000000000001",
                },
                "runtime": {"value": "running", "health": "current", "reason": "native"},
                "phase": None,
            },
            {
                "identity": {
                    "hostScope": "fixture",
                    "provider": "codex",
                    "namespace": "f" * 64,
                    "nativeIdKind": "thread_id",
                    "nativeId": "00000000-0000-0000-0000-000000000002",
                },
                "runtime": {"value": "parked", "health": "current", "reason": "native"},
                "phase": None,
            },
        ]
        # Pure projection only: deliberately no public admission is claimed.
        result = {
            "snapshot": {"sources": [], "sessions": rows},
            "health": "partial",
            "reason": "projection_fixture",
            "components": [],
        }
        summary = local_summary(result, host="fixture", clock={})
        identities = [row["identity"] for row in summary["view"]["sessions"]]
        self.assertTrue(
            all(set(row) == {"identity", "runtime", "phase"} for row in summary["view"]["sessions"])
        )
        assert_content_free(self, summary)
        self.assertEqual([item["namespace"] for item in identities], ["a" * 64, "f" * 64])
        self.assertEqual(
            len({(item["provider"], item["namespace"], item["nativeId"]) for item in identities}), 2
        )

    def test_local_watch_recomputes_expiry_on_a_quiet_tick(self):
        _cache, frame = self.make_cache()
        emitted = []

        def quiet_frames(*_args, **_kwargs):
            yield frame
            while True:
                yield None

        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }
        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch(
                "agent_observer.utility_read.boottime_ms",
                side_effect=[15000, 15000, 19999, 20000, 25000, 25000],
            ),
            patch("agent_observer.utility_read.frames", side_effect=quiet_frames),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=10.0,
                output=emitted.append,
            )

        self.assertEqual(code, 0)
        self.assertEqual(emitted[0]["view"]["state"], "current")
        expired = next(
            item for item in emitted[1:-1] if item["view"]["state"] in {"partial", "stale"}
        )
        self.assertTrue(any(not item["current"] for item in expired["view"]["components"]))
        self.assertEqual(emitted[-1]["view"]["state"], "revoked")

    def test_real_service4_socket_runs_one_bounded_owned_watch(self):
        state = ServiceState(
            host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")}
        )
        sample = scoped_snapshot()
        sampled = state.clock()
        state.attempt("codex", "runtime")
        state.accept("codex", "runtime", sample, sampled_ms=sampled, ttl_ms=60000)
        state.attempt("codex", "history")
        state.accept(
            "codex", "history", sample, sampled_ms=sampled, ttl_ms=120000, runtime_ttl_ms=60000
        )
        with Running(state=state) as service:
            emitted = []
            code = run_local(
                host="fixture",
                socket_path=service.path,
                duration=1.2,
                output=emitted.append,
            )
            self.assertEqual(code, 0)
            self.assertGreaterEqual(len(emitted), 2)
            self.assertEqual(emitted[-1]["lifecycle"], "closed")
            self.assertEqual(emitted[-1]["view"]["state"], "revoked")
            self.assertEqual(emitted[-1]["view"]["sessions"], [])
            self.assertEqual(emitted[-1]["transport"]["state"], "closed")
            self.assertEqual(service.runtime.counts["workerStarts"], 0)

    def test_missing_local_socket_fails_visibly_and_revokes(self):
        with tempfile.TemporaryDirectory() as directory:
            emitted = []
            code = run_local(
                host="fixture",
                socket_path=Path(directory) / "missing.sock",
                duration=0.2,
                output=emitted.append,
            )
        self.assertEqual(code, 1)
        self.assertEqual(emitted[-1]["lifecycle"], "revoked")
        self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
        self.assertEqual(emitted[-1]["view"]["state"], "revoked")

    def test_local_setup_uses_the_public_one_second_minimum_timeout(self):
        timeouts = []

        def setup_stream(*_args, **kwargs):
            timeouts.append(kwargs["timeout"])

            def stream():
                raise ContractError("service_transport_timeout")
                yield None

            return stream()

        emitted = []
        _cache, frame = self.make_cache()
        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }
        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch("agent_observer.utility_read.boottime_ms", side_effect=[15000, 15100, 15110]),
            patch("agent_observer.utility_read.frames", side_effect=setup_stream),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=0.2,
                output=emitted.append,
            )
        self.assertEqual(timeouts, [1.0])
        self.assertEqual(code, 1)
        self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
        self.assertEqual(emitted[-1]["transport"]["failure"], "service_transport_timeout")
        self.assertEqual(emitted[-1]["view"]["state"], "revoked")

    def test_public_timeout_after_deadline_and_valid_baseline_closes_normally(self):
        _cache, frame = self.make_cache()
        emitted, timeouts = [], []
        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }

        def quiet_then_timeout(*_args, **kwargs):
            timeouts.append(kwargs["timeout"])
            yield frame
            for _ in range(11):
                yield None
            raise ContractError("service_transport_timeout")

        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch(
                "agent_observer.utility_read.boottime_ms",
                side_effect=[15000, 15000, *range(15100, 16200, 100), 16200, 16200],
            ),
            patch("agent_observer.utility_read.frames", side_effect=quiet_then_timeout),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=1.2,
                output=emitted.append,
            )

        self.assertEqual(timeouts, [1.2])
        self.assertEqual(code, 0)
        self.assertEqual(emitted[0]["view"]["state"], "current")
        self.assertEqual(emitted[1]["view"]["state"], "current")
        self.assertEqual(emitted[-1]["lifecycle"], "closed")
        self.assertEqual(emitted[-1]["transport"]["state"], "closed")
        self.assertIsNone(emitted[-1]["transport"]["failure"])

    def test_local_budget_includes_initial_read_and_quiet_ticks(self):
        _cache, frame = self.make_cache()
        emitted, timeouts = [], []
        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }

        def delayed_frame(*_args, **kwargs):
            timeouts.append(kwargs["timeout"])
            yield frame
            yield None
            raise OSError("read continued beyond the presentation deadline")

        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch("agent_observer.utility_read.boottime_ms", side_effect=[15000, 15100, 15200, 15200]),
            patch("agent_observer.utility_read.frames", side_effect=delayed_frame),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=0.2,
                output=emitted.append,
            )

        self.assertEqual(timeouts, [1.0])
        self.assertEqual(code, 0)
        self.assertEqual(emitted[0]["view"]["state"], "current")
        self.assertEqual(emitted[-1]["lifecycle"], "closed")

    def test_first_baseline_after_budget_fails_without_displaying_it(self):
        _cache, frame = self.make_cache()
        emitted = []
        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }

        def late_frame(*_args, **_kwargs):
            yield frame

        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch("agent_observer.utility_read.boottime_ms", side_effect=[15000, 15201, 15201]),
            patch("agent_observer.utility_read.frames", side_effect=late_frame),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=0.2,
                output=emitted.append,
            )

        self.assertEqual(code, 1)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[-1]["lifecycle"], "revoked")
        self.assertEqual(emitted[-1]["transport"]["failure"], "service_baseline_unavailable")
        self.assertEqual(emitted[-1]["view"]["sessions"], [])

    def test_local_close_failure_is_reported_after_cache_revocation(self):
        _cache, frame = self.make_cache()
        emitted = []

        class CloseFailure:
            def __init__(self):
                self.first = True

            def __next__(self):
                if self.first:
                    self.first = False
                    return frame
                return None

            def close(self):
                raise OSError("close failed")

        clock = {
            "bootId": frame["bootId"],
            "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", ""),
        }
        with (
            patch("agent_observer.utility_read.local_clock", return_value=clock),
            patch("agent_observer.utility_read.boottime_ms", side_effect=[15000, 15000, 15100, 15200]),
            patch("agent_observer.utility_read.frames", return_value=CloseFailure()),
        ):
            code = run_local(
                host="fixture",
                socket_path=Path("/unused.sock"),
                duration=0.05,
                output=emitted.append,
            )
        self.assertEqual(code, 1)
        self.assertEqual(emitted[-1]["lifecycle"], "revoked")
        self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
        self.assertEqual(emitted[-1]["transport"]["failure"], "oserror")

    def test_cli_window_is_an_integer_from_zero_through_720_hours(self):
        args = parser().parse_args(
            [
                "mesh",
                "--host",
                "snap",
                "--source",
                "agent_working_set",
                "--socket",
                "/tmp/bridge.sock",
                "--window-hours",
                "0",
            ]
        )
        self.assertEqual(args.window_hours, 0)
        for value in ("-1", "721", "72.5"):
            with self.subTest(window=value), self.assertRaises(SystemExit):
                parser().parse_args(
                    [
                        "mesh",
                        "--host",
                        "snap",
                        "--source",
                        "agent_working_set",
                        "--socket",
                        "/tmp/bridge.sock",
                        "--window-hours",
                        value,
                    ]
                )


class PendingStream:
    def __init__(self):
        self.calls = 0
        self.cancelled = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        self.calls += 1
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise


class CurrentSummaryMeshTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from mesh_test_support import require_working_set_sdk

        require_working_set_sdk()

    async def test_quiet_ticks_preserve_one_pending_anext_and_close_cleanly(self):
        stream = PendingStream()
        events = ticked(stream, interval=0.01)
        self.assertIsNone(await anext(events))
        self.assertIsNone(await anext(events))
        self.assertIsNone(await anext(events))
        self.assertEqual(stream.calls, 1)
        await events.aclose()
        self.assertEqual(stream.cancelled, 1)
        self.assertEqual(stream.calls, 1)

    async def test_configured_reader_reprojects_quiet_expiry_and_preserves_sibling(self):
        from mesh_plus.api import (
            AdmittedResponse,
            Bridge,
            Client,
            Endpoint,
            Reader,
            configured_reader,
        )
        from mesh_plus.transport import IPCServer, connect_ipc
        from test_working_set_registered_sdk import state_with_rows

        from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
        from agent_observer.mesh_working_set_publisher import make_working_set_publisher
        from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

        window_ms = 0
        state, sample = state_with_rows(window=window_ms, count=1)
        sample["collectionId"] = "00000000-0000-0000-0000-000000000099"
        sampled = state.clock()
        state.attempt("codex", "runtime")
        self.assertTrue(
            state.accept(
                "codex",
                "runtime",
                sample,
                sampled_ms=sampled,
                ttl_ms=1200,
                runtime_ttl_ms=1200,
                accepted_boottime_ms=sampled,
            )
        )
        profile = WorkingSetAgentProfile(window_ms)
        request = {
            "meshProtocol": 1,
            "requestId": "b" * 32,
            "operation": "watch",
            "profile": profile.descriptor.profile_id,
            "access": "cached",
            "selection": {"mode": "local", "hostIds": []},
            "extensions": {},
        }
        with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
            publisher = make_working_set_publisher(
                "fixture", "working", native.path, window_ms=window_ms
            )
            mesh_path = Path(directory) / "mesh.sock"
            server = await IPCServer(mesh_path, Bridge(publisher).serve).start()
            codec = profile.bind("fixture", "working")

            async def connect():
                return await Client.connect(
                    await connect_ipc(mesh_path),
                    host="fixture",
                    source="working",
                    profile=profile.descriptor.profile_id,
                    codec=codec.validate_bridge,
                )

            sibling = Reader(
                "agent",
                [Endpoint("fixture", True, None, connect, codec)],
                local_host="fixture",
                profile=profile,
            )
            sibling_stream = sibling.execute_admitted(request)
            try:
                await asyncio.wait_for(anext(sibling_stream), 5)
                actual_configured_reader = configured_reader
                owned_readers, source_frames = [], [0]
                baseline_frame_count = [None]

                class QuietReader:
                    def __init__(self, reader):
                        self.reader = reader

                    def execute_admitted(self, request_value):
                        source_stream = self.reader.execute_admitted(request_value)

                        async def quiet_after_baseline():
                            try:
                                while True:
                                    frame = await anext(source_stream)
                                    source_frames[0] += 1
                                    ready = isinstance(frame, AdmittedResponse) and all(
                                        host_view["delivery"]["status"] == "ready"
                                        for host_view in frame.context()["mesh"]["hosts"]
                                    )
                                    yield frame
                                    if ready:
                                        baseline_frame_count[0] = source_frames[0]
                                        await asyncio.Future()
                            finally:
                                await source_stream.aclose()

                        return quiet_after_baseline()

                async def track_reader(*args, **kwargs):
                    reader = await actual_configured_reader(*args, **kwargs)
                    owned_readers.append(reader)
                    return QuietReader(reader)

                emitted, observations = [], []
                read = PreparedWorkingSetAgentWatch.read

                def observe_read(watch, now, clock):
                    result = read(watch, now, clock)
                    observations.append(
                        (
                            now,
                            len(result.members),
                            tuple(item["coverage"]["status"] for item in result.scopes),
                        )
                    )
                    return result

                started = asyncio.get_running_loop().time()
                with (
                    patch("mesh_plus.api.configured_reader", side_effect=track_reader),
                    patch.object(PreparedWorkingSetAgentWatch, "read", observe_read),
                    patch("agent_observer.utility_read.OUTPUT_SECONDS", 0.1),
                ):
                    code = await run_mesh(
                        host="fixture",
                        source="working",
                        socket_path=mesh_path,
                        scope="local",
                        window_ms=window_ms,
                        duration=1.6,
                        output=emitted.append,
                    )
                elapsed = asyncio.get_running_loop().time() - started
                self.assertEqual(code, 0)
                self.assertGreaterEqual(elapsed, 1.45)
                self.assertLess(elapsed, 3.0)
                self.assertEqual(emitted[-1]["lifecycle"], "closed")
                self.assertEqual(emitted[-1]["view"]["state"], "revoked")
                counts = [count for _now, count, _coverage in observations]
                positive = next(index for index, count in enumerate(counts) if count > 0)
                self.assertTrue(any(count == 0 for count in counts[positive + 1 :]))
                self.assertEqual(source_frames[0], baseline_frame_count[0])
                self.assertGreater(len(observations), 5)
                for item in emitted:
                    assert_content_free(self, item)
                self.assertEqual(owned_readers[0].inspect()["activeConnections"], 0)
                self.assertEqual(sibling.inspect()["activeConnections"], 1)
            finally:
                await sibling_stream.aclose()
                await server.close()
            self.assertEqual(sibling.inspect()["activeConnections"], 0)

    async def test_configured_reader_failure_is_visible_and_revokes(self):
        from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

        original_disconnect = PreparedWorkingSetAgentWatch.disconnect
        disconnected = []

        def track_disconnect(watch):
            disconnected.append(watch)
            original_disconnect(watch)

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.sock"
            emitted = []
            with patch.object(PreparedWorkingSetAgentWatch, "disconnect", track_disconnect):
                code = await run_mesh(
                    host="fixture",
                    source="working",
                    socket_path=missing,
                    scope="local",
                    duration=1.0,
                    output=emitted.append,
                )
            self.assertEqual(code, 1)
            self.assertTrue(disconnected)
            self.assertEqual(emitted[-1]["lifecycle"], "revoked")
            self.assertEqual(emitted[-1]["view"]["state"], "revoked")
            self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
            self.assertIsNotNone(emitted[-1]["transport"]["failure"])

    async def test_configured_reader_setup_is_inside_duration_deadline(self):
        async def slow_setup(*_args, **_kwargs):
            await asyncio.sleep(0.5)

        emitted = []
        started = asyncio.get_running_loop().time()
        with patch("mesh_plus.api.configured_reader", side_effect=slow_setup):
            code = await run_mesh(
                host="fixture",
                source="working",
                socket_path=Path("/unused.sock"),
                scope="local",
                duration=0.1,
                output=emitted.append,
            )
        elapsed = asyncio.get_running_loop().time() - started
        self.assertEqual(code, 1)
        self.assertLess(elapsed, 0.4)
        self.assertEqual(emitted[-1]["lifecycle"], "revoked")
        self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
        self.assertEqual(emitted[-1]["transport"]["failure"], "mesh_setup_timeout")

    async def test_stream_timeout_after_baseline_is_a_visible_failure(self):
        guards = []

        class Reader:
            def execute_admitted(self, _request):
                async def stream():
                    yield {"mesh": {"kind": "baseline"}}
                    raise TimeoutError("stream timeout")

                return stream()

        class Guard:
            def __init__(self, *_args, **_kwargs):
                self.disconnected = False
                guards.append(self)

            def accept(self, _frame):
                pass

            def read(self, _now, _clock):
                return SimpleNamespace(
                    context={
                        "hosts": [
                            {
                                "hostId": "fixture",
                                "delivery": {"path": "ipc", "status": "ready"},
                                "viewState": "current",
                            }
                        ]
                    },
                    scopes=[],
                    member_leases=[],
                    members=[],
                    uncertain=[],
                    nonmembers=[],
                )

            def disconnect(self):
                self.disconnected = True

        emitted = []
        with (
            patch("mesh_plus.api.configured_reader", return_value=Reader()),
            patch(
                "agent_observer.mesh_working_set_read.PreparedWorkingSetAgentWatch",
                Guard,
            ),
        ):
            code = await run_mesh(
                host="fixture",
                source="working",
                socket_path=Path("/unused.sock"),
                scope="local",
                duration=2.0,
                output=emitted.append,
            )
        self.assertEqual(code, 1)
        self.assertEqual(emitted[-1]["lifecycle"], "revoked")
        self.assertEqual(emitted[-1]["transport"]["state"], "disconnected")
        self.assertEqual(emitted[-1]["transport"]["failure"], "mesh_operation_timeout")
        self.assertTrue(guards[0].disconnected)


if __name__ == "__main__":
    unittest.main()
