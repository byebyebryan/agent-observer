"""Actual immutable Observer source -> Mesh relay on two disposable IPC paths."""

import argparse
import asyncio
import contextlib
import gc
import hashlib
import json
import sys
import tempfile
import traceback
import unittest
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mesh", type=Path, required=True)
parser.add_argument("--observer", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path[:0] = [str(args.mesh / "src"), str(args.observer), str(args.observer / "tests")]

from mesh_plus.sync import SyncBudgets, create_sync_relay, source_binding  # noqa: E402
from mesh_plus.sync.budget import AllocationLedger  # noqa: E402
from mesh_plus.sync.canonical import canonical, decode  # noqa: E402
from mesh_plus.transport import LineChannel, boottime_ms  # noqa: E402
from test_service_runtime import scoped_snapshot  # noqa: E402
from test_sync_service_delivery import seeded  # noqa: E402

from agent_observer.mesh_sync_profile import AgentSyncProfile  # noqa: E402
from agent_observer.sync_source import CachedAgentSyncSource  # noqa: E402
from agent_observer.sync_transport import AgentSyncTransportCodec  # noqa: E402

outcomes = []


class JoinedCompletion(unittest.IsolatedAsyncioTestCase):
    async def probe(self, view, count):
        enabled = gc.isenabled()
        gc.disable()
        owner, ledger = seeded(), AllocationLedger()
        source = relay = channel = capsule = None
        handlers, received = set(), asyncio.Queue()
        sent, failures = [], []
        row = {"view": view, "transactions": count}
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "native.sock"
            output = Path(directory) / "mesh.sock"

            async def native_input(reader, writer):
                handlers.add(asyncio.current_task())
                try:
                    request = json.loads(await reader.readline())
                    if request["operation"] == "changes":
                        raw = owner.sync_changes(view, request["baseTag"], request["targetTag"],
                                                 max_transactions=request["maxTransactions"],
                                                 max_bytes=request["maxBytes"])
                        self.assertIs(type(raw), tuple)
                    else:
                        self.assertEqual(request["operation"], "baseline")
                        raw = (owner.sync_baseline(view),)
                    sent.extend(raw)
                    for value in raw:
                        writer.write(value)
                        await writer.drain()
                except BaseException as error:
                    failures.append(str(error))
                    raise
                finally:
                    writer.close()
                    with contextlib.suppress(ConnectionError):
                        await writer.wait_closed()
                    handlers.discard(asyncio.current_task())

            async def receive(reader, writer):
                handlers.add(asyncio.current_task())
                try:
                    while raw := await reader.readline():
                        received.put_nowait(raw)
                finally:
                    writer.close()
                    with contextlib.suppress(ConnectionError):
                        await writer.wait_closed()
                    handlers.discard(asyncio.current_task())

            native_server = await asyncio.start_unix_server(native_input, native)
            native.chmod(0o600)
            mesh_server = await asyncio.start_unix_server(receive, output, limit=8470528)
            try:
                baseline = json.loads(owner.sync_baseline(view))
                if count == 1:
                    owner.attempt("codex", "history")
                elif count == 4:
                    for index in range(2):
                        value = scoped_snapshot()
                        value["sessions"][0]["title"] = f"joined change {index}"
                        owner.attempt("codex", "history")
                        self.assertTrue(owner.accept("codex", "history", value,
                                                     sampled_ms=owner.clock(), ttl_ms=60000,
                                                     runtime_ttl_ms=60000))
                target = owner.sync_current_tag(view)
                source = CachedAgentSyncSource("fixture", native, view=view, timeout=2)
                profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
                codec = AgentSyncTransportCodec(view, encoding_id="fixture-expanded/1", expected_host="fixture")
                binding = source_binding("fixture", "agents", profile.descriptor)
                relay = create_sync_relay(source, profile.descriptor, binding, native_codec=codec,
                                          budgets=SyncBudgets(), ledger=ledger)
                request = {"readerEpoch": "a" * 32, "requestId": "joined-completion",
                           "catalogRevision": "fixture", "hosts": ["fixture"], "route": "controlled-ipc",
                           "channelEpoch": "c" * 32, "bridgeId": relay.bridge_id, "role": "transport-relay",
                           "encodingDigest": hashlib.sha256(canonical(dict(codec.encoding))).hexdigest()}
                reader, writer = await asyncio.open_unix_connection(output)
                channel = await relay.open_channel(LineChannel(reader, writer, "client"), request,
                                                   setup_deadline_ms=boottime_ms() + 15000)
                setup = decode(await asyncio.wait_for(received.get(), 2))
                self.assertEqual(setup["role"], "transport-relay")
                capsule = channel.begin_acquisition(deadline_ms=boottime_ms() + 15000)
                try:
                    await capsule.changes(baseline["tag"], target=target)
                except BaseException as error:
                    row.update(errorType=type(error).__name__, error=str(error),
                               traceback=traceback.format_exc())
                    self.errors.append(error)
                    raise
                deliveries = [await asyncio.wait_for(received.get(), 2) for _ in range(count + 1)]
                self.assertEqual(len(sent), count + 1)
                for index, (native_raw, delivery) in enumerate(zip(sent, deliveries, strict=True)):
                    document = decode(delivery)
                    self.assertEqual(document["sequence"], index + 1)
                    self.assertEqual(document["payload"]["kind"], "material" if index < count else "control")
                    self.assertIn(native_raw[:-1], delivery)
                row.update(delivered=len(deliveries), exactOriginalFragments=True)
            finally:
                row["completionKeys"] = sorted(json.loads(sent[-1])) if sent else []
                row["nativeFrameCount"] = len(sent)
                for value in (capsule, channel, relay, source):
                    if value is not None:
                        await value.aclose()
                owner._sync_cache.close()
                native_server.close()
                mesh_server.close()
                await native_server.wait_closed()
                await mesh_server.wait_closed()
                if handlers:
                    await asyncio.wait_for(asyncio.gather(*tuple(handlers)), 2)
                row["finalCounters"] = [ledger.used, ledger.reserved, ledger.encoded,
                                        ledger.encoded_reserved, ledger.pending_units]
                row["framesEmittedAfterSetup"] = received.qsize()
                row["nativeHandlerFailures"] = failures
                outcomes.append(row)
                self.assertEqual(row["finalCounters"], [0] * 5)
                self.assertFalse(gc.isenabled())
                if enabled:
                    gc.enable()

    async def asyncSetUp(self):
        self.errors = []

    async def test_full_zero(self):
        await self.probe("full", 0)

    async def test_full_one(self):
        await self.probe("full", 1)

    async def test_full_four(self):
        await self.probe("full", 4)

    async def test_active_zero(self):
        await self.probe("active", 0)

    async def test_active_one(self):
        await self.probe("active", 1)

    async def test_active_four(self):
        await self.probe("active", 4)


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(JoinedCompletion))
loaded = {}
for module in tuple(sys.modules.values()):
    filename = getattr(module, "__file__", None)
    if filename and Path(filename).suffix == ".py":
        path = Path(filename).resolve()
        for label, root in (("mesh", args.mesh.resolve()), ("observer", args.observer.resolve())):
            if path.is_relative_to(root):
                loaded[label + "/" + str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
report = {"python": sys.version.split()[0], "testsRun": result.testsRun,
          "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
          "cases": outcomes, "loadedInputs": loaded,
          "limits": "Controlled source/relay IPC only, no provider/normal service/installed/SSH/performance/RSS acceptance; native fixture and output oracle outside relay ledger."}
with args.output.open("x") as output:
    json.dump(report, output, sort_keys=True, indent=2)
    output.write("\n")
raise SystemExit(0 if result.wasSuccessful() else 1)
