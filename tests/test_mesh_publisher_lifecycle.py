"""Independent controlled Service 2 changes/loss through the installed SDK seam."""

import asyncio
import contextlib
import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from test_mesh_publisher import PUBLISHER_AVAILABLE
from test_mesh_source import native_frame

from agent_observer.service_public import canonical, validate_frame


@unittest.skipUnless(PUBLISHER_AVAILABLE, "optional Mesh cached publisher capability not installed")
class PublisherLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from mesh_plus.api import Bridge, configured_reader
        from mesh_plus.transport import IPCServer

        from agent_observer.mesh_publisher import make_publisher

        self.directory = tempfile.TemporaryDirectory(prefix="agent-native-publisher-lifecycle-")
        root = Path(self.directory.name)
        self.path = root / "native.sock"
        self.frame = native_frame()
        self.watchers, self.handlers = {}, set()
        self.requests = []

        async def handler(reader, writer):
            task = asyncio.current_task()
            self.handlers.add(task)
            queue = asyncio.Queue()
            try:
                line = await reader.readline()
                if not line:
                    return
                request = json.loads(line)
                self.requests.append(request)
                watch = request["operation"] == "watch"
                if watch:
                    self.watchers[writer] = queue
                sequence = 0
                while True:
                    sequence += 1
                    frame = copy.deepcopy(self.frame)
                    frame.update(sequence=sequence, kind="view" if watch else "status")
                    writer.write((canonical(frame) + "\n").encode())
                    await writer.drain()
                    if not watch:
                        return
                    value = await queue.get()
                    if value == "close":
                        return
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                self.watchers.pop(writer, None)
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                self.handlers.discard(task)

        self.native = await asyncio.start_unix_server(handler, path=self.path)
        self.path.chmod(0o600)
        self.publisher = make_publisher("fixture", "agent", self.path)
        self.mesh_path = root / "mesh.sock"
        self.mesh = await IPCServer(self.mesh_path, Bridge(self.publisher).serve).start()
        self.reader = await configured_reader("agent", source="agent", socket=self.mesh_path, scope="local",
                                              local_host="fixture", profile=self.publisher.state_profile)

    async def asyncTearDown(self):
        for task in list(self.handlers):
            task.cancel()
        await asyncio.gather(*self.handlers, return_exceptions=True)
        await self.mesh.close()
        self.native.close()
        await self.native.wait_closed()
        self.assertEqual(self.publisher.native._active, 0)
        self.directory.cleanup()

    async def change(self, *, restart=False):
        self.frame["viewRevision"] += 1
        self.frame["snapshot"]["sessions"][0]["title"] = "controlled pushed update"
        if restart:
            self.frame["serviceId"] = str(uuid.uuid4())
        validate_frame(self.frame)
        for queue in self.watchers.values():
            queue.put_nowait("close" if restart else "update")

    async def until(self, stream, predicate, guard=None):
        async with asyncio.timeout(5):
            async for response in stream:
                if "mesh" not in response:
                    self.fail(response["error"]["code"])
                if guard is not None:
                    guard.accept(response)
                if predicate(response):
                    return response
        self.fail("missing publisher transition")

    async def test_native_update_and_restart_revoke_then_restore_original_receipts(self):
        from mesh_plus.api import ReadGuard
        from mesh_plus.transport import boottime_ms

        stream = self.reader.watch(request_id="c" * 32, proof_interval=60)
        guard = ReadGuard("agent", "c" * 32, profile=self.publisher.state_profile)
        try:
            baseline = await self.until(stream, lambda r: r["mesh"]["hosts"][0]["delivery"]["status"] == "ready", guard)
            self.assertTrue(guard.current(boottime_ms(), baseline["mesh"]["reader"]["clock"]))
            async with asyncio.timeout(3):
                while not self.watchers:
                    await asyncio.sleep(.01)
            receipts = copy.deepcopy(baseline["mesh"]["hosts"][0]["receipts"])
            original = [{k: v for k, v in receipt.items() if k != "remainingMs"} for receipt in receipts]
            await self.change()
            expected = self.frame["snapshot"]["sessions"][0]["identity"]
            update = await self.until(stream, lambda r: any(row["identity"] == expected
                                     and row["title"] == "controlled pushed update" for row in r["sessions"]), guard)
            updated_receipts = update["mesh"]["hosts"][0]["receipts"]
            self.assertEqual([{k: v for k, v in receipt.items() if k != "remainingMs"}
                              for receipt in updated_receipts], original)
            self.assertTrue(all(a["remainingMs"] <= b["remainingMs"]
                                for a, b in zip(updated_receipts, receipts, strict=True)))
            old_epoch = update["mesh"]["hosts"][0]["delivery"]["epoch"]
            await self.change(restart=True)
            lost = await self.until(stream, lambda r: r["mesh"]["hosts"][0]["delivery"]["status"] == "unavailable", guard)
            self.assertEqual(guard.current(boottime_ms(), lost["mesh"]["reader"]["clock"]), [])
            resumed = await self.until(stream, lambda r: r["mesh"]["hosts"][0]["delivery"]["status"] == "ready", guard)
            self.assertEqual(resumed["mesh"]["kind"], "resync")
            self.assertGreater(resumed["mesh"]["hosts"][0]["delivery"]["epoch"], old_epoch)
            self.assertEqual([{k: v for k, v in receipt.items() if k != "remainingMs"}
                              for receipt in resumed["mesh"]["hosts"][0]["receipts"]], original)
        finally:
            guard.disconnect()
            await stream.aclose()
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)

    async def test_complete_empty_and_missing_source_are_distinct(self):
        self.frame["snapshot"]["sessions"] = []
        validate_frame(self.frame)
        empty = await self.reader.snapshot()
        self.assertEqual(empty["mesh"]["status"], "complete")
        self.assertEqual(empty["sessions"], [])
        self.native.close()
        await self.native.wait_closed()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.path)
        lost = await self.reader.snapshot()
        self.assertEqual(lost["mesh"]["status"], "unavailable")
        self.assertEqual(lost["sessions"], [])
        self.assertEqual(self.reader.inspect()["activeConnections"], 0)
