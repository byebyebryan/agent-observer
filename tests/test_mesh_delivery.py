"""Explicit owner profile in real owned IPC and synthetic remote-proof paths."""

import asyncio
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("mesh_plus"), "optional Mesh SDK not installed")
class MeshOwnerDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from mesh_native_fixture import CachedPublisher
        from mesh_plus.api import Bridge, configured_reader
        from mesh_plus.transport import IPCServer

        self.directory = tempfile.TemporaryDirectory(prefix="owner-mesh-delivery-")
        self.publisher = CachedPublisher()
        self.socket = Path(self.directory.name) / "read.sock"
        self.server = await IPCServer(self.socket, Bridge(self.publisher).serve).start()
        self.reader = await configured_reader("agent", source="agent", socket=self.socket,
                                             scope="local", local_host="fixture", profile=self.publisher.state_profile)

    async def asyncTearDown(self):
        await self.server.close()
        self.directory.cleanup()

    async def test_native_roundtrip_and_independent_receipt_expiry(self):
        from mesh_plus.api import current_sessions, reconstructed

        frame = self.publisher.frame
        emitted = frame["emittedBoottimeMs"]
        for source in frame["sources"]:
            for item in source["components"]:
                item["expiresBoottimeMs"] = emitted + (40000 if source["provider"] == "claude" else 20000)
        before = copy.deepcopy(frame)
        response = await self.reader.snapshot()
        profile = self.publisher.state_profile
        clock = response["mesh"]["reader"]["clock"]
        self.assertEqual(reconstructed(response, response["mesh"]["hosts"][0], profile=profile), before)
        self.assertEqual(len(current_sessions(response, response["mesh"]["reader"]["encodedAtMs"], clock, profile=profile)), 5)
        survivors = current_sessions(response, emitted + 20000, clock, profile=profile)
        self.assertEqual(len(survivors), 2)
        self.assertTrue(all(row["identity"]["provider"] == "claude" for row in survivors))
        self.assertEqual(current_sessions(response, emitted + 40000, clock, profile=profile), [])
        self.assertEqual(frame, before)
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)

    async def test_replacement_push_guard_expiry_disconnect_and_owned_close(self):
        from mesh_plus.api import ReadGuard
        from mesh_plus.transport import boottime_ms

        stream = self.reader.watch(request_id="a" * 32, proof_interval=.1)
        guard = ReadGuard("agent", "a" * 32, profile=self.publisher.state_profile)
        try:
            for _ in range(10):
                frame = await asyncio.wait_for(anext(stream), 2)
                guard.accept(frame)
                rows = guard.current(boottime_ms(), frame["mesh"]["reader"]["clock"])
                if rows:
                    break
            self.assertEqual(len(rows), 5)
            original = [(r["sourceId"], r["component"], r["accepted"], r["expiresAtMs"])
                        for host in frame["mesh"]["hosts"] for r in host["receipts"]]
            deadline = max(r[3] for r in original)
            self.assertEqual(guard.current(deadline, frame["mesh"]["reader"]["clock"]), [])
            self.assertEqual(original, [(r["sourceId"], r["component"], r["accepted"], r["expiresAtMs"])
                                       for host in guard.view["mesh"]["hosts"] for r in host["receipts"]])
            guard.disconnect()
            self.assertEqual(guard.current(deadline, frame["mesh"]["reader"]["clock"]), [])
        finally:
            await stream.aclose()
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)
        self.assertEqual(self.publisher.watchers, 0)

    async def test_real_positive_cli_paths_share_the_same_profile(self):
        from mesh_plus import api

        from agent_observer import mesh_cli

        real_configured = api.configured_reader
        for command in ("snapshot", "list", "watch"):
            args = mesh_cli.parser().parse_args([command, "--local-host", "fixture", "--socket", str(self.socket)])
            args.count = 2 if command == "watch" else 1
            args.human = command != "snapshot"
            outputs, bindings = [], []

            async def configured(*values, _bindings=bindings, **kwargs):
                _bindings.append(kwargs["profile"])
                return await real_configured(*values, **kwargs)

            with patch.object(api, "configured_reader", configured), \
                 patch.object(api, "ReadGuard", wraps=api.ReadGuard) as guard, \
                 patch.object(api, "validate_response", wraps=api.validate_response) as validate, \
                 patch.object(api, "current_sessions", wraps=api.current_sessions) as current, \
                 patch.object(api, "reconstructed", wraps=api.reconstructed) as restore:
                self.assertEqual(await mesh_cli.run(args, output=outputs.append, human_output=outputs.append), 0)
                self.assertIs(guard.call_args.kwargs["profile"], bindings[0])
                if command != "watch":
                    self.assertIs(validate.call_args.kwargs["profile"], bindings[0])
                if command == "list":
                    self.assertIs(current.call_args.kwargs["profile"], bindings[0])
                    self.assertIs(restore.call_args.kwargs["profile"], bindings[0])
                if command == "snapshot":
                    self.assertEqual(len(outputs[0]["sessions"]), 5)
                else:
                    self.assertTrue(any("AGE" in value for value in outputs))
                if command == "watch":
                    self.assertIn("revoked", outputs[-1])

    async def test_snapshot_cancellation_retires_owned_reader(self):
        self.publisher.wait_snapshot = asyncio.Event()
        task = asyncio.create_task(self.reader.snapshot())
        await asyncio.wait_for(self.publisher.snapshot_started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)

    async def test_bounded_assessment_uses_owner_profile_without_route_writes(self):
        from mesh_plus import api

        if not importlib.util.find_spec("mesh_plus.diagnostics"):
            self.skipTest("optional Mesh diagnostics capability not installed")
        from mesh_plus import configured_read, diagnostics

        if not callable(getattr(diagnostics, "assess_configured", None)):
            self.skipTest("optional Mesh assessment capability not installed")
        from agent_observer import mesh_cli

        real_configured = api.configured_reader
        for mode in ("snapshot", "subscribe"):
            args = mesh_cli.parser().parse_args(["assess", "--mode", mode, "--local-host", "fixture",
                                                 "--socket", str(self.socket), "--timeout-ms", "2000"])
            reports, bindings = [], []

            async def configured(*values, _bindings=bindings, **kwargs):
                _bindings.append(kwargs)
                return await real_configured(*values, **kwargs)

            with patch.object(configured_read, "configured_reader", configured):
                self.assertEqual(await mesh_cli.run(args, output=reports.append), 0)
            self.assertTrue(reports[0]["ok"])
            self.assertIs(bindings[0]["profile"].__class__, self.publisher.state_profile.__class__)
            self.assertFalse(bindings[0]["report_routes"])
            self.assertEqual(reports[0]["runtime"]["activeConnections"], 0)
            self.assertEqual(self.publisher.watchers, 0)

    async def test_aggregate_admission_rejects_native_and_receipt_forgeries(self):
        from mesh_plus.api import validate_response
        from mesh_plus.protocol import ProtocolError

        from agent_observer.public import ContractError
        response = await self.reader.snapshot()
        for fault in ("duplicate", "native_version", "missing_receipt", "extended_receipt", "changed_host"):
            value = copy.deepcopy(response)
            host = value["mesh"]["hosts"][0]
            if fault == "duplicate":
                value["sessions"].insert(0, copy.deepcopy(value["sessions"][0]))
            elif fault == "native_version":
                host["owner"]["metadata"]["schemaVersion"] = 3
            elif fault == "missing_receipt":
                host["receipts"].pop()
            elif fault == "extended_receipt":
                host["receipts"][0]["expiresAtMs"] += 1000
            else:
                host["owner"]["service"]["hostScope"] = "foreign"
            with self.subTest(fault=fault), self.assertRaises((ProtocolError, ContractError)):
                validate_response(value, profile=self.publisher.state_profile)

    async def test_forged_remote_proof_cannot_borrow_local_sibling_receipts(self):
        from mesh_native_fixture import CachedPublisher
        from mesh_plus.api import Bridge, Client, Endpoint, Reader, current_sessions
        from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc

        remote = CachedPublisher("other")
        path = Path(self.directory.name) / "remote.sock"
        server = await IPCServer(path, Bridge(remote).serve).start()
        profile = self.publisher.state_profile
        codec = profile.bind("other", "agent")

        async def connect():
            return await Client.connect(await connect_ipc(path), host="other", source="agent",
                                        profile=profile.descriptor.profile_id, codec=codec.validate_bridge)

        reader = Reader("agent", [*self.reader.endpoints, Endpoint("other", False, "sha256:" + "a" * 64, connect, codec)],
                        local_host="fixture", catalog_revision="sha256:" + "b" * 64, profile=profile)
        try:
            good = await reader.snapshot()
            self.assertEqual(len(current_sessions(good, boottime_ms(), good["mesh"]["reader"]["clock"], profile=profile)), 10)
            self.assertGreater(remote.proof_reads, 0)

            def forge(payload):
                if payload["kind"] == "proof":
                    payload["remaining"][0]["remainingMs"] += 1000

            remote.alter = forge
            bad = await reader.snapshot()
            self.assertEqual(bad["mesh"]["status"], "partial")
            rows = current_sessions(bad, boottime_ms(), bad["mesh"]["reader"]["clock"], profile=profile)
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row["identity"]["hostScope"] == "fixture" for row in rows))
            self.assertEqual(reader.inspect()["activeConnections"], 0)
        finally:
            await server.close()
