"""Human timer wakes cannot renew evidence or count as protocol frames."""

import argparse
import asyncio
import copy
import importlib.util
import unittest
from unittest.mock import patch

from test_read_cache import cache, fixture

from agent_observer import mesh_cli, service_cli


class LocalHumanWatchTest(unittest.TestCase):
    def test_quiet_expiry_count_age_and_eof_invalidation(self):
        value = fixture()
        heartbeat = {**copy.deepcopy(value), "sequence": 2, "kind": "heartbeat", "snapshot": None}
        frames = [value, None, None, heartbeat]
        times = iter([15000, 20000, 30000, 30000])
        outputs, closed = [], []

        def stream():
            try:
                yield from frames
                raise AssertionError("ticks must not consume the frame count")
            finally:
                closed.append(True)

        subject = cache()
        args = argparse.Namespace(include_children=False, provider=None, order="activity", count=2)
        service_cli.human_watch(stream(), args, cache=subject, now=lambda: next(times),
                               wall=lambda: 1700000020000, output=outputs.append)
        self.assertEqual(closed, [True])
        self.assertIn("Observer partial", outputs[1])
        self.assertIn("codex runtime: stale", outputs[1])
        self.assertIn("claude runtime: current", outputs[1])
        self.assertIn("19s", outputs[1])
        self.assertIn("revoked", outputs[-1])
        self.assertIsNone(subject.current(30000)["snapshot"])

    def test_output_failure_closes_owned_stream_and_invalidates(self):
        subject, closed = cache(), []

        def stream():
            try:
                yield fixture()
                yield None
            finally:
                closed.append(True)

        def output(value):
            raise OSError("closed output")

        args = argparse.Namespace(include_children=False, provider=None, order="activity", count=None)
        with self.assertRaises(OSError):
            service_cli.human_watch(stream(), args, cache=subject, now=lambda: 15000,
                                   wall=lambda: 1700000020000, output=output)
        self.assertEqual(closed, [True])
        self.assertIsNone(subject.current(15000)["snapshot"])


class TimerStreamTest(unittest.IsolatedAsyncioTestCase):
    async def test_tick_keeps_pending_read_and_cancellation_closes_it(self):
        gate, closed = asyncio.Event(), []

        async def stream():
            try:
                await gate.wait()
                yield {"data": True}
            finally:
                closed.append(True)

        real_wait = asyncio.wait

        async def short_wait(tasks, *, timeout):
            return await real_wait(tasks, timeout=0.01)

        source = stream()
        timed = mesh_cli.ticked(source)
        with patch("agent_observer.mesh_cli.asyncio.wait", short_wait):
            self.assertIsNone(await anext(timed))
            gate.set()
            self.assertEqual(await anext(timed), {"data": True})
            with self.assertRaises(StopAsyncIteration):
                await anext(timed)
        self.assertEqual(closed, [True])

        source = stream()
        gate.clear()
        timed = mesh_cli.ticked(source)
        with patch("agent_observer.mesh_cli.asyncio.wait", short_wait):
            self.assertIsNone(await anext(timed))
            await timed.aclose()
        self.assertEqual(closed, [True, True])


@unittest.skipUnless(importlib.util.find_spec("mesh_plus"), "optional Mesh SDK not installed")
class MeshHumanWatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_idle_timer_uses_guard_receipts_and_count_closes_owned_stream(self):
        from mesh_plus.reader import Endpoint, Reader
        from mesh_plus.transport import boottime_ms

        args = mesh_cli.parser().parse_args(["watch", "--human", "--local-host", "fixture", "--count", "2"])
        sdk = Reader("agent", [Endpoint("fixture", True, None, None)], local_host="fixture")
        closed, outputs = [], []

        class FakeReader:
            async def execute(self, request):
                try:
                    for number in range(1, 3):
                        frame = sdk.compose(sdk.endpoints, {"fixture": (sdk.unavailable(sdk.endpoints[0]), [])},
                                            request["requestId"], request["operation"])
                        frame["mesh"]["reader"]["sequence"] = number
                        yield frame
                    raise AssertionError("count should close the reader")
                finally:
                    closed.append(True)

        async def configured(*args, **kwargs):
            return FakeReader()

        async def ticks(stream):
            async for value in stream:
                yield value
                yield None

        clock = [boottime_ms()]

        def advance():
            clock[0] += 10000
            return clock[0]

        with patch("mesh_plus.configured_read.configured_reader", configured), patch("agent_observer.mesh_cli.ticked", ticks), patch("mesh_plus.transport.boottime_ms", advance):
            await mesh_cli.run(args, human_output=outputs.append)
        self.assertEqual(closed, [True])
        self.assertIn("revoked", outputs[-1])
        self.assertEqual(len([v for v in outputs if "cached state" in v]), 3)

        # asyncio.run turns Ctrl-C into task cancellation before raising
        # KeyboardInterrupt to its caller. It must still close and revoke.
        gate = asyncio.Event()
        args.count = None

        class WaitingReader:
            async def execute(self, request):
                try:
                    frame = sdk.compose(sdk.endpoints, {"fixture": (sdk.unavailable(sdk.endpoints[0]), [])},
                                        request["requestId"], request["operation"])
                    frame["mesh"]["reader"]["sequence"] = 1
                    yield frame
                    gate.set()
                    await asyncio.Event().wait()
                finally:
                    closed.append(True)

        async def waiting(*args, **kwargs):
            return WaitingReader()

        with patch("mesh_plus.configured_read.configured_reader", waiting):
            task = asyncio.create_task(mesh_cli.run(args, human_output=outputs.append))
            await asyncio.wait_for(gate.wait(), timeout=2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(closed, [True, True])
        self.assertIn("revoked", outputs[-1])
