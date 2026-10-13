"""Independent Service 2 acquisition, ordering, passivity and owned cleanup."""

import asyncio
import contextlib
import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from test_service_runtime import Running

from agent_observer.mesh_source import (
    MAX_CHANNELS,
    MAX_INCARNATIONS,
    CachedAgentSource,
    boottime_ms,
)
from agent_observer.service_public import ContractError, canonical, validate_frame


def native_frame():
    from agent_observer.public import store_namespace

    frame = json.loads(Path(__file__).with_name("fixtures").joinpath("service-v4/view.json").read_text())
    delta = boottime_ms() - 100 - frame["emittedBoottimeMs"]
    frame.update(uid=os.geteuid(), bootId=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                 clockDomain=os.readlink("/proc/self/ns/time"), sequence=1,
                 emittedBoottimeMs=frame["emittedBoottimeMs"] + delta)
    namespaces = {}
    for source in frame["sources"]:
        source["namespace"] = store_namespace(source["provider"], source["configHome"], source["configHomeKind"], os.geteuid())
        namespaces[source["provider"]] = source["namespace"]
        for component in source["components"]:
            for key in ("sampledBoottimeMs", "expiresBoottimeMs"):
                if component[key] is not None:
                    component[key] += delta
            if component["health"] in {"current", "partial"}:
                component["expiresBoottimeMs"] = frame["emittedBoottimeMs"] + 60000
    snapshot = frame["snapshot"]
    snapshot["host"]["uid"] = os.geteuid()
    for source in snapshot["sources"]:
        source["namespace"] = namespaces[source["provider"]]
    for row in snapshot["sessions"]:
        row["identity"]["namespace"] = namespaces[row["identity"]["provider"]]
    return validate_frame(frame)


class SourceOrderingTest(unittest.TestCase):
    def setUp(self):
        self.frame = native_frame()
        self.source = CachedAgentSource("fixture", "/nonexistent/read.sock")

    def test_original_receipts_and_failed_admission_are_atomic(self):
        self.source._admit(self.frame, watch=False)
        before = copy.deepcopy(self.source.__dict__)
        for field, value, reason in (("accepted", 0, "service_receipt_regression"),
                                     ("expiresBoottimeMs", self.frame["emittedBoottimeMs"] + 70000, "service_receipt_renewal")):
            bad = copy.deepcopy(self.frame)
            bad["sources"][0]["components"][0][field] = value
            with self.assertRaisesRegex(ContractError, reason):
                self.source._admit(bad, watch=False)
            self.assertEqual(self.source.__dict__, before)
        unchanged = copy.deepcopy(self.frame)
        unchanged["emittedBoottimeMs"] += 1
        self.assertTrue(self.source._admit(unchanged, watch=False))
        self.assertEqual(self.source._receipts, before["_receipts"])

    def test_superseded_watch_skips_but_status_cannot_prove_old_state(self):
        newest = copy.deepcopy(self.frame)
        newest["viewRevision"] += 1
        newest["emittedBoottimeMs"] += 1
        self.source._admit(newest, watch=False)
        self.assertFalse(self.source._admit(self.frame, watch=True))
        with self.assertRaisesRegex(ContractError, "service_acquisition_superseded"):
            self.source._admit(self.frame, watch=False)
        self.assertEqual(self.source._position, (newest["viewRevision"], newest["emittedBoottimeMs"]))

    def test_new_revision_cannot_regress_native_emission_clock(self):
        self.source._admit(self.frame, watch=False)
        bad = copy.deepcopy(self.frame)
        bad["viewRevision"] += 1
        bad["emittedBoottimeMs"] -= 1
        with self.assertRaisesRegex(ContractError, "service_acquisition_clock_regression"):
            self.source._admit(bad, watch=True)
        self.assertEqual(self.source._position, (self.frame["viewRevision"], self.frame["emittedBoottimeMs"]))

    def test_scope_disappearance_and_reappearance_cannot_reset_receipts(self):
        self.source._admit(self.frame, watch=False)
        for bad in (copy.deepcopy(self.frame), copy.deepcopy(self.frame)):
            if len(bad["sources"]) > 1:
                bad["sources"].pop()
            else:
                bad["sources"][0]["components"].pop()
            with self.assertRaisesRegex(ContractError, "service_acquisition_scope_changed"):
                self.source._admit(bad, watch=False)
        bad = copy.deepcopy(self.frame)
        bad["sources"][0]["components"][0]["accepted"] = 0
        with self.assertRaisesRegex(ContractError, "service_receipt_regression"):
            self.source._admit(bad, watch=False)

    def test_retired_incarnation_never_reappears_and_history_is_bounded(self):
        self.source._admit(self.frame, watch=False)
        replacement = copy.deepcopy(self.frame)
        for _ in range(MAX_INCARNATIONS - 1):
            replacement["serviceId"] = str(uuid.uuid4())
            self.source._admit(replacement, watch=False)
        with self.assertRaisesRegex(ContractError, "service_publisher_retired"):
            self.source._admit(self.frame, watch=False)
        replacement["serviceId"] = str(uuid.uuid4())
        with self.assertRaisesRegex(ContractError, "service_incarnation_capacity"):
            self.source._admit(replacement, watch=False)
        self.assertEqual(len(self.source._retired), MAX_INCARNATIONS - 1)


class SourceAcquisitionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="agent-cached-source-")
        self.path = Path(self.directory.name) / "read.sock"
        self.source = CachedAgentSource("fixture", self.path, timeout=1)
        self.handlers = set()
        self.requests = []
        self.frame = native_frame()
        self.release = asyncio.Event()
        self.connected = asyncio.Event()
        self.mode = "normal"

        async def handler(reader, writer):
            task = asyncio.current_task()
            self.handlers.add(task)
            try:
                line = await reader.readline()
                if not line:
                    return
                request = json.loads(line)
                self.requests.append(request)
                self.connected.set()
                if self.mode == "wait":
                    await self.release.wait()
                elif self.mode == "oversize":
                    from agent_observer.mesh_source import MAX_FRAME_BYTES
                    writer.write(b" " * (MAX_FRAME_BYTES + 1))
                    await writer.drain()
                    return
                frame = copy.deepcopy(self.frame)
                frame["kind"] = "status" if request["operation"] == "status" else "view"
                if self.mode == "wrong_kind":
                    frame["kind"] = "view"
                if self.mode == "gap":
                    frame.update(kind="gap", snapshot=None)
                writer.write((canonical(frame) + "\n").encode())
                await writer.drain()
                if request["operation"] == "watch":
                    heartbeat = {**frame, "kind": "heartbeat", "sequence": 2, "snapshot": None}
                    writer.write((canonical(heartbeat) + "\n").encode())
                    await writer.drain()
                await reader.read()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                self.handlers.discard(task)

        self.server = await asyncio.start_unix_server(handler, path=self.path)
        self.path.chmod(0o600)

    async def asyncTearDown(self):
        self.release.set()
        self.server.close()
        await self.server.wait_closed()
        for task in list(self.handlers):
            task.cancel()
        await asyncio.gather(*self.handlers, return_exceptions=True)
        self.directory.cleanup()

    async def test_checked_snapshot_requests_status_and_owns_each_socket(self):
        frame = await self.source.snapshot()
        self.assertEqual(frame["snapshot"], self.frame["snapshot"])
        self.assertEqual(self.requests, [{"serviceProtocol": 4, "operation": "status", "hostScope": "fixture"}])
        self.assertEqual(self.source._active, 0)

    async def test_same_view_queued_before_status_still_supplies_watch_baseline(self):
        self.frame["emittedBoottimeMs"] += 1
        watermark = self.frame["emittedBoottimeMs"]
        await self.source.snapshot()
        self.frame["emittedBoottimeMs"] -= 1
        stream = self.source._frames("watch")
        try:
            frame = await asyncio.wait_for(anext(stream), .2)
            self.assertEqual(frame["viewRevision"], self.frame["viewRevision"])
            self.assertEqual(self.source._position[1], watermark)
        finally:
            await stream.aclose()
        self.assertEqual(self.source._active, 0)
        a, b = await asyncio.gather(self.source.snapshot(), self.source.snapshot())
        self.assertEqual(a, b)
        self.assertEqual(self.source._active, 0)

    async def test_watch_filters_heartbeat_and_close_retires_socket(self):
        stream = self.source._frames("watch")
        self.assertEqual((await anext(stream))["kind"], "view")
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(.05)
        self.assertFalse(task.done())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await stream.aclose()
        self.assertEqual(self.source._active, 0)

    async def test_timeout_and_repeated_cancellation_leave_no_owned_channel(self):
        self.mode = "wait"
        task = asyncio.create_task(self.source.snapshot())
        await self.connected.wait()
        task.cancel()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.source._active, 0)
        with self.assertRaisesRegex(ContractError, "service_transport_timeout"):
            await self.source.snapshot()
        self.assertEqual(self.source._active, 0)

    async def test_capacity_is_explicit_and_constructor_does_not_acquire(self):
        self.assertEqual(self.requests, [])
        self.source._active = MAX_CHANNELS
        with self.assertRaisesRegex(ContractError, "service_acquisition_capacity"):
            await self.source.snapshot()
        self.assertEqual(self.source._active, MAX_CHANNELS)
        self.source._active = 0

    async def test_native_faults_cannot_supply_positive_delivery(self):
        for fault, reason in (("wrong_kind", "service_operation_binding"),
                              ("gap", "service_initial_frame"),
                              ("oversize", "service_frame_limit")):
            self.mode = fault
            with self.subTest(fault=fault), self.assertRaisesRegex(ContractError, reason):
                await self.source.snapshot()
            self.assertEqual(self.source._active, 0)
        self.mode = "normal"
        self.frame["bootId"] = str(uuid.uuid4())
        with self.assertRaisesRegex(ContractError, "service_clock_context"):
            await self.source.snapshot()

    async def test_socket_path_policy_and_connect_cancellation(self):
        self.path.chmod(0o666)
        with self.assertRaisesRegex(ContractError, "service_socket_ownership"):
            await self.source.snapshot()
        self.path.chmod(0o600)
        loop = asyncio.get_running_loop()
        started = asyncio.Event()

        async def connect(*args):
            started.set()
            await self.release.wait()

        with patch.object(loop, "sock_connect", connect):
            task = asyncio.create_task(self.source.snapshot())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.source._active, 0)

    async def test_peer_guard_failure_and_clock_expiry_close_before_admission(self):
        import agent_observer.mesh_source as module

        with patch.object(module.struct, "unpack", return_value=(0, os.geteuid() + 1, 0)):
            with self.assertRaisesRegex(ContractError, "service_peer_ownership"):
                await self.source.snapshot()
        self.assertEqual(self.source._active, 0)
        self.assertIsNone(self.source._service)
        with patch.object(module, "StreamGuard", side_effect=ContractError("fixture_guard_failure")):
            with self.assertRaisesRegex(ContractError, "fixture_guard_failure"):
                await self.source.snapshot()
        self.assertEqual(self.source._active, 0)
        with patch.object(module, "boottime_ms", return_value=self.frame["emittedBoottimeMs"] + 60001):
            with self.assertRaisesRegex(ContractError, "service_frame_expired"):
                await self.source.snapshot()
        self.assertIsNone(self.source._service)

    async def test_existing_cold_service_remains_passive(self):
        with Running() as server:
            source = CachedAgentSource("fixture", server.path)
            frame = await source.snapshot()
            self.assertEqual(frame["state"], "warming")
            self.assertIsNone(frame["snapshot"])
            self.assertEqual(server.runtime.counts["workerStarts"], 0)
            self.assertEqual(source._active, 0)


if __name__ == "__main__":
    unittest.main()
