"""Owned cached native source through public Mesh publisher/factory interfaces."""

import asyncio
import copy
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PUBLISHER_AVAILABLE = False
if importlib.util.find_spec("mesh_plus"):
    from mesh_plus import api
    PUBLISHER_AVAILABLE = hasattr(api, "CachedPublisher")


@unittest.skipUnless(PUBLISHER_AVAILABLE, "optional Mesh cached publisher capability not installed")
class PublisherTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from mesh_plus.api import Bridge, configured_reader
        from mesh_plus.transport import IPCServer
        from test_service_runtime import Running, source_worker

        from agent_observer.mesh_publisher import make_publisher

        self.native = Running(collect=True, factory=source_worker)
        self.native.__enter__()
        self.directory = tempfile.TemporaryDirectory(prefix="agent-owned-publisher-")
        self.path = Path(self.directory.name) / "read.sock"
        self.publisher = make_publisher("fixture", "agent", str(self.native.path))
        self.server = await IPCServer(self.path, Bridge(self.publisher).serve).start()
        self.reader = await configured_reader("agent", source="agent", socket=self.path, scope="local",
                                              local_host="fixture", profile=self.publisher.state_profile)

    async def asyncTearDown(self):
        await self.server.close()
        self.directory.cleanup()
        self.native.__exit__(None, None, None)
        self.assertEqual(self.publisher.native._active, 0)

    async def test_local_and_remote_proof_paths_preserve_native_receipts(self):
        from mesh_plus.api import Client, Endpoint, Reader, reconstructed
        from mesh_plus.transport import connect_ipc

        codec = self.publisher.state_profile.bind("fixture", "agent")

        async def connect():
            return await Client.connect(await connect_ipc(self.path), host="fixture", source="agent",
                                        profile=self.publisher.profile, codec=self.publisher.validate)

        remote = Reader("agent", [Endpoint("fixture", False, "sha256:" + "a" * 64, connect, codec)],
                        local_host="local", catalog_revision="sha256:" + "b" * 64,
                        profile=self.publisher.state_profile)
        for reader, needs_proof in ((self.reader, False), (remote, True)):
            response = await reader.snapshot()
            host = response["mesh"]["hosts"][0]
            self.assertEqual(host["delivery"]["status"], "ready")
            self.assertEqual(host["delivery"]["proof"] is not None, needs_proof)
            frame = reconstructed(response, host, profile=self.publisher.state_profile)
            self.assertEqual(frame["serviceId"], self.native.runtime.state.service_id)
            self.assertEqual(frame["uid"], os.geteuid())
            self.assertEqual(reader.inspect()["activeConnections"], 0)
        self.assertEqual(self.publisher.native._active, 0)

    async def test_push_disconnect_retires_native_and_mesh_connections(self):
        from mesh_plus.api import ReadGuard
        from mesh_plus.transport import boottime_ms

        stream = self.reader.watch(request_id="a" * 32, proof_interval=.1)
        guard = ReadGuard("agent", "a" * 32, profile=self.publisher.state_profile)
        try:
            async with asyncio.timeout(5):
                async for response in stream:
                    guard.accept(response)
                    if guard.current(boottime_ms(), response["mesh"]["reader"]["clock"]):
                        break
            self.assertTrue(guard.view["sessions"])
            original = copy.deepcopy(guard.view["mesh"]["hosts"][0]["receipts"])
            guard.disconnect()
            self.assertEqual(guard.current(boottime_ms(), response["mesh"]["reader"]["clock"]), [])
            self.assertEqual(original, response["mesh"]["hosts"][0]["receipts"])
        finally:
            await stream.aclose()
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)
        await asyncio.sleep(.05)
        self.assertEqual(self.publisher.native._active, 0)

    async def test_nonce_rejection_precedes_fresh_native_acquisition(self):
        from mesh_plus.protocol import ProtocolError

        before = self.native.runtime.counts["acceptedConnections"]
        with self.assertRaises(ProtocolError):
            await self.publisher.proof({"nonce": "invalid"})
        self.assertEqual(self.native.runtime.counts["acceptedConnections"], before)
        proof = await self.publisher.proof({"nonce": "b" * 32})
        self.assertEqual(proof["nonce"], "b" * 32)
        self.assertGreater(self.native.runtime.counts["acceptedConnections"], before)
        self.assertEqual(self.publisher.native._active, 0)


@unittest.skipUnless(PUBLISHER_AVAILABLE, "optional Mesh cached publisher capability not installed")
class PublisherFactoryTests(unittest.TestCase):
    def test_static_factory_binding_and_terminal_failure(self):
        from mesh_plus.cli import configured_adapter
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_publisher import make_publisher

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.toml"
            path.write_text('version=1\nhost="fixture"\n[sources.agent]\ndomain="agent"\nsocket="/nonexistent/read.sock"\n')
            path.chmod(0o600)
            with patch("mesh_plus.observer.ObserverAdapter", side_effect=AssertionError("reference selected")):
                publisher = configured_adapter(path, "agent", publisher_factories={"agent": make_publisher})
                self.assertEqual(publisher.native._active, 0)
                self.assertEqual(publisher.source, "agent")
                for factory in (lambda *_: None, lambda *_: (_ for _ in ()).throw(ImportError("missing owner"))):
                    with self.assertRaises((ProtocolError, ImportError)):
                        configured_adapter(path, "agent", publisher_factories={"agent": factory})

    def test_owner_launcher_leaves_authority_fast_path_lazy(self):
        code = """
import sys
from agent_observer.mesh_publisher import main
sys.argv=['mesh-plus','mesh','--help']
try:
 main()
except SystemExit as e:
 assert e.code==0
assert not any(n in sys.modules for n in ('mesh_plus.observer','mesh_plus.publisher',
 'agent_observer.mesh_source','agent_observer.mesh_profile','agent_observer.collection',
 'agent_observer.codex_snapshot','agent_observer.service_runtime','tmux_observer'))
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
