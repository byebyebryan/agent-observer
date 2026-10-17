"""Synthetic actual owner/source/relay -> independent Reader over two IPC paths.

All native and Mesh request setup is explicit test composition. This does not
qualify a controller grammar, production route or aggregate resource budget.
The only private receiving operation is existing test nonce request setup.
"""

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

from mesh_plus.protocol import ProtocolError  # noqa: E402
from mesh_plus.sync import (  # noqa: E402
    OwnedSyncCache,
    SyncBudgets,
    create_sync_relay,
    source_binding,
)
from mesh_plus.sync.budget import AllocationLedger  # noqa: E402
from mesh_plus.sync.canonical import canonical, decode  # noqa: E402
from mesh_plus.transport import LineChannel, boottime_ms  # noqa: E402
from test_service_runtime import scoped_snapshot  # noqa: E402
from test_sync_service_delivery import seeded  # noqa: E402

from agent_observer.mesh_sync_profile import AgentSyncProfile  # noqa: E402
from agent_observer.sync_source import CachedAgentSyncSource  # noqa: E402
from agent_observer.sync_transport import AgentSyncTransportCodec  # noqa: E402

outcomes = []


class JoinedReader(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.errors = []

    async def probe(self, view, count):
        enabled = gc.isenabled()
        gc.disable()
        owner, ledger = seeded(), AllocationLedger()
        source = relay = channel = capsule = cache = None
        handlers, received = set(), asyncio.Queue()
        sent, failures = [], []
        row = {"view": view, "transactions": count}
        with tempfile.TemporaryDirectory() as directory:
            native, output = Path(directory) / "native.sock", Path(directory) / "mesh.sock"

            async def native_input(reader, writer):
                handlers.add(asyncio.current_task())
                try:
                    request = json.loads(await reader.readline())
                    if request["operation"] == "changes":
                        frames = owner.sync_changes(view, request["baseTag"], request["targetTag"],
                                                    max_transactions=request["maxTransactions"],
                                                    max_bytes=request["maxBytes"])
                        self.assertIs(type(frames), tuple)
                    elif request["operation"] == "head":
                        frames = (owner.sync_head(view, request["challenge"]),)
                    else:
                        self.assertEqual(request["operation"], "baseline")
                        frames = (owner.sync_baseline(view),)
                    sent.extend(frames)
                    for raw in frames:
                        writer.write(raw)
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
                source = CachedAgentSyncSource("fixture", native, view=view, timeout=2)
                profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
                codec = AgentSyncTransportCodec(view, encoding_id="fixture-expanded/1", expected_host="fixture")
                binding = source_binding("fixture", "agents", profile.descriptor)
                relay = create_sync_relay(source, profile.descriptor, binding, native_codec=codec,
                                          budgets=SyncBudgets(), ledger=ledger)
                request = {"readerEpoch": "a" * 32, "requestId": "joined-completion-reader",
                           "catalogRevision": "fixture", "hosts": ["fixture"], "route": "controlled-ipc",
                           "channelEpoch": "c" * 32, "bridgeId": relay.bridge_id, "role": "transport-relay",
                           "encodingDigest": hashlib.sha256(canonical(dict(codec.encoding))).hexdigest()}
                input_reader, writer = await asyncio.open_unix_connection(output)
                channel = await relay.open_channel(LineChannel(input_reader, writer, "client"), request,
                                                   setup_deadline_ms=boottime_ms() + 15000)
                setup = decode(await asyncio.wait_for(received.get(), 2))
                self.assertEqual(setup["role"], "transport-relay")
                # The same immutable 15-second capsule covers baseline, both
                # fresh nonce proofs and catch-up. No attempt budget resets.
                capsule = channel.begin_acquisition(deadline_ms=boottime_ms() + 15000)
                reader_clock = {"bootId": "fixture-reader", "timeNamespace": "time:999"}
                cache = OwnedSyncCache(profile, binding, request_binding=request, _clock=reader_clock)
                sequence = 0

                async def delivery():
                    nonlocal sequence
                    raw = await asyncio.wait_for(received.get(), 2)
                    document = decode(raw)
                    sequence += 1
                    self.assertEqual(document["sequence"], sequence)
                    self.assertEqual(document["requestBinding"], request)
                    return raw, document["payload"]

                async def confirm(candidate):
                    # Disclosed test-only nonce setup, matching existing owner
                    # tests. Public relay/source produce every proof byte.
                    challenge = cache._proof_request(candidate)
                    await capsule.head_after_nonce(challenge)
                    raw, proof = await delivery()
                    self.assertEqual(proof["kind"], "proof")
                    self.assertEqual(proof["challenge"], challenge)
                    self.assertIn(sent[-1][:-1], raw)
                    confirmed = cache.confirm(candidate, canonical(proof), reader_clock)
                    context = confirmed.context(boottime_ms(), reader_clock)
                    self.assertEqual(context["status"], "confirmed")
                    self.assertTrue(any(receipt["current"] for receipt in context["receipts"]))
                    self.assertEqual(confirmed.export_committed(),
                                     owner.snapshot if view == "full" else owner.active_projection)
                    return challenge["nonce"]

                await capsule.baseline()
                raw, payload = await delivery()
                self.assertEqual(payload["kind"], "material")
                self.assertIn(sent[-1][:-1], raw)
                baseline = payload["native"]
                row["baselineRows"] = len(baseline["tables"]["records"])
                candidate = cache.admit_baseline(canonical(baseline))
                with self.assertRaisesRegex(ProtocolError, "sync_unconfirmed"):
                    cache.acquire()
                nonce = await confirm(candidate)

                base = baseline["tag"]
                if count == 1:
                    owner.attempt("codex", "history")
                elif count == 4:
                    for index in range(2):
                        value = scoped_snapshot()
                        value["sessions"][0]["title"] = f"reader joined change {index}"
                        owner.attempt("codex", "history")
                        self.assertTrue(owner.accept("codex", "history", value, sampled_ms=owner.clock(),
                                                     ttl_ms=60000, runtime_ttl_ms=60000))
                target = owner.sync_current_tag(view)
                start = len(sent)
                await capsule.changes(base, target=target)
                self.assertEqual(len(sent) - start, count + 1)
                for index in range(count + 1):
                    raw, payload = await delivery()
                    self.assertIn(sent[start + index][:-1], raw)
                    self.assertEqual(payload["kind"], "material" if index < count else "control")
                    if index < count:
                        candidate = cache.stage(canonical(payload["native"]))
                    else:
                        complete = payload["native"]
                        self.assertEqual(complete["status"], "complete")
                        self.assertEqual(complete["baseTag"], base)
                        self.assertEqual(complete["tag"], complete["targetTag"])
                        self.assertEqual(complete["tag"], list(target))
                if count:
                    with self.assertRaisesRegex(ProtocolError, "sync_unconfirmed"):
                        cache.acquire()
                self.assertEqual(candidate.tag.native.wire(), list(target))
                self.assertNotEqual(await confirm(candidate), nonce)
                row.update(exactOriginalFragments=True, freshProofs=2, losslessFinalDTO=True,
                           finalNativeTag=list(target), deliveries=sequence)
            except BaseException as error:
                row.update(errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc())
                self.errors.append(error)
                raise
            finally:
                for value in (capsule, channel, relay, source):
                    if value is not None:
                        await value.aclose()
                if cache is not None:
                    cache.close()
                    book = cache.ledger
                    row["readerFinalCounters"] = [book.used, book.reserved, book.encoded,
                                                  book.encoded_reserved, book.pending_units, book.pending_encoded]
                    self.assertEqual(row["readerFinalCounters"], [0] * 6)
                owner._sync_cache.close()
                native_server.close()
                mesh_server.close()
                await native_server.wait_closed()
                await mesh_server.wait_closed()
                if handlers:
                    await asyncio.wait_for(asyncio.gather(*tuple(handlers)), 2)
                row["relayFinalCounters"] = [ledger.used, ledger.reserved, ledger.encoded,
                                             ledger.encoded_reserved, ledger.pending_units]
                row["queuedOutputAfterConsumption"] = received.qsize()
                row["nativeHandlerFailures"] = failures
                outcomes.append(row)
                self.assertEqual(row["relayFinalCounters"], [0] * 5)
                self.assertEqual(received.qsize(), 0)
                self.assertFalse(gc.isenabled())
                if enabled:
                    gc.enable()

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


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(JoinedReader))
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
          "limits": "Small synthetic source/relay/independent Reader only; fixture/oracle/native and Reader/relay separate ledgers, no aggregate resource/RSS/CPU, native/installed/route acceptance; no pin-prune fix."}
with args.output.open("x") as output:
    json.dump(report, output, sort_keys=True, indent=2)
    output.write("\n")
raise SystemExit(0 if result.wasSuccessful() else 1)
