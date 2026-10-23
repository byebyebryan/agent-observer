"""Configured compact native IPC; synthetic state, no provider invocation."""

import asyncio
import gc
import hashlib
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_mesh_sync_codec as codec_fixture
from test_service_runtime import Running, scoped_snapshot

from agent_observer.contract import ContractError
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import canonical
from agent_observer.sync_compact_source import CachedCompactAgentSyncSource
from agent_observer.sync_native import parse_message
from agent_observer.sync_owned_source import OwnedSyncControl, _SourceLease
from agent_observer.sync_source import CachedAgentSyncSource


class CompactSourceSurfaceTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_owned_source_rejects_byte_operations_before_io(self):
        source = CachedCompactAgentSyncSource("fixture", "/unused/compact.sock")
        try:
            for operation in (source.baseline(), source.head_after_nonce({"nonce": "a" * 32}),
                              source.changes(("a", 1, "b"), target=("a", 1, "b"))):
                with self.assertRaisesRegex(ContractError, "sync_source_input_owner"):
                    await operation
            with self.assertRaisesRegex(ContractError, "sync_source_input_owner"):
                source.watch(("a", 1, "b"))
            self.assertEqual(source.inspect()["requests"], 0)
            self.assertEqual(source.inspect()["activeSockets"], 0)
        finally:
            await source.aclose()

    async def test_import_is_mesh_and_provider_free(self):
        script = (
            "import sys;from agent_observer.sync_compact_source import CachedCompactAgentSyncSource;"
            "assert not any(name in sys.modules for name in ['mesh_plus',"
            "'agent_observer.service_runtime','agent_observer.observation_engine',"
            "'agent_observer.collection','agent_observer.codex_snapshot'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(codec_fixture.HAS_COMPACT, "optional public Mesh compact interface unavailable")
class CompactSourceIpcTest(unittest.IsolatedAsyncioTestCase):
    cache = codec_fixture.MeshSyncCodecTest.cache

    async def asyncSetUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.caches, self.owners, self.sources, self.errors = [], [], [], []

    async def asyncTearDown(self):
        try:
            for source in self.sources:
                await source.aclose()
                self.assertEqual(source.inspect()["activeSessions"], 0)
                self.assertEqual(source.inspect()["activeSockets"], 0)
            for cache in self.caches:
                cache.close()
                ledger = cache.ledger
                self.assertEqual((ledger.used, ledger.reserved, ledger.encoded,
                                  ledger.encoded_reserved, ledger.pending_units,
                                  ledger.pending_encoded), (0,) * 6)
            for owner in self.owners:
                if owner._sync_cache is not None:
                    account = owner._sync_cache.account
                    owner._sync_cache.close()
                    self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])
            self.assertFalse(gc.isenabled())
        finally:
            if self.enabled:
                gc.enable()

    def owner(self, serialization="compact"):
        owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                             sync_serialization=serialization)
        owner.attempt("codex", "history")
        owner.accept("codex", "history", scoped_snapshot(), sampled_ms=owner.clock(),
                     ttl_ms=60000, runtime_ttl_ms=60000)
        self.owners.append(owner)
        return owner

    def source(self, path, view, *, compact=True):
        cls = CachedCompactAgentSyncSource if compact else CachedAgentSyncSource
        source = cls("fixture", path, view=view, timeout=2)
        self.sources.append(source)
        return source

    async def confirm(self, parts, session, candidate):
        # Disclosed test-only nonce setup/native-byte pin and carrier proof.
        # Actual source IPC supplies the original freshly challenged head.
        from mesh_plus.sync.inputs import input_bytes

        cache, reader_time, clock, binding, request = parts
        challenge = cache._proof_request(candidate)
        ref = await session.head_after_nonce(challenge)
        with input_bytes(cache, ref) as (raw, _):
            head = parse_message(raw, cache.profile.view, "fixture")
            raw = None
        self.assertEqual(head["challenge"], challenge)
        bridge_time = head["ownerClock"]["boottimeMs"] + 1
        proof = {"protocol": "mesh.state-sync/1", "kind": "proof",
                 "descriptor": cache.descriptor.wire(), "sourceBinding": binding,
                 "sourceTag": candidate.tag.wire(), "requestBinding": request,
                 "challenge": challenge, "bridgeId": request["bridgeId"],
                 "bridgeClock": {"bootId": head["ownerClock"]["bootId"],
                                 "timeNamespace": head["ownerClock"]["clockDomain"].replace("[", "").replace("]", ""),
                                 "boottimeMs": bridge_time}, "head": head,
                 "remaining": [[key, max(0, value["expiresBoottimeMs"] - bridge_time)
                                if value["health"] in {"current", "partial"} else 0]
                               for key, value in head["originalReceipts"]]}
        reader_time[0] += 20
        return cache.confirm(candidate, canonical(proof), clock)

    async def test_runtime_full_active_zero_one_four_batches_and_fresh_reader_proof(self):
        for view in ("full", "active"):
            for count in (0, 1, 4):
                with self.subTest(view=view, count=count), Running(state=self.owner(), experimental_sync=True) as server:
                    owner = server.state
                    source = self.source(server.path, view)
                    parts = self.cache(view)
                    reader = parts[0]
                    session = source.open_session(reader.input_owner())
                    try:
                        ticket = await session.baseline()
                        base = ticket.tag
                        candidate = reader.admit_baseline(ticket.data)
                        ticket.close()
                        confirmed = await self.confirm(parts, session, candidate)
                        self.assertEqual(confirmed.export_committed(),
                                         owner.snapshot if view == "full" else owner.sync_active_projection)
                        if count == 1:
                            owner.attempt("codex", "history")
                        elif count == 4:
                            for index in range(2):
                                value = scoped_snapshot()
                                value["sessions"][0]["title"] = f"compact source {index}"
                                owner.attempt("codex", "history")
                                owner.accept("codex", "history", value, sampled_ms=owner.clock(),
                                             ttl_ms=60000, runtime_ttl_ms=60000)
                        target = owner.sync_current_tag(view)
                        expected = []
                        original_changes = owner.sync_changes

                        def changes(*args, _original=original_changes, _expected=expected, **kwargs):
                            frames = _original(*args, **kwargs)
                            _expected.extend(frames)
                            return frames

                        sealed, original = [], _SourceLease.seal

                        def seal(lease, raw, _original=original, _sealed=sealed):
                            result = _original(lease, raw)
                            _sealed.append((result, hashlib.sha256(raw).hexdigest()))
                            return result

                        with (patch.object(_SourceLease, "seal", new=seal),
                              patch.object(owner, "sync_changes", new=changes)):
                            batch = await session.changes_with_completion(base, target=target)
                        self.assertEqual(len(batch.transactions), count)
                        self.assertEqual(sealed, list(zip((*batch.transactions, batch.completion.data),
                                                         (hashlib.sha256(raw).hexdigest() for raw in expected),
                                                         strict=True)))
                        if count:
                            candidate = reader.stage_batch(candidate.tag, batch.transactions)
                            with self.assertRaises(ValueError):
                                reader.acquire()
                        self.assertEqual(candidate.tag.native.wire(), list(target))
                        confirmed = await self.confirm(parts, session, candidate)
                        self.assertEqual(confirmed.export_committed(),
                                         owner.snapshot if view == "full" else owner.sync_active_projection)
                        batch.close()
                    finally:
                        await source.aclose()

    async def test_expanded_and_compact_sources_reject_opposite_material_without_fallback(self):
        for serialization, compact in (("expanded", True), ("compact", False)):
            with self.subTest(serialization=serialization), Running(state=self.owner(serialization), experimental_sync=True) as server:
                source = self.source(server.path, "full", compact=compact)
                reader = self.cache()[0]
                session = source.open_session(reader.input_owner())
                try:
                    try:
                        await session.baseline()
                    except ContractError as error:
                        self.errors.append(error)
                    else:
                        self.fail("wrong encoding source accepted material")
                    self.assertEqual(session.inspect()["ownedRefs"], 0)
                    self.assertEqual(session.inspect()["ownedTickets"], 0)
                finally:
                    await source.aclose()

    async def test_head_keeps_original_path_without_compact_scanner_or_body_schema(self):
        from agent_observer.sync_compact_acquisition import _CompactScanner

        with Running(state=self.owner(), experimental_sync=True) as server:
            source = self.source(server.path, "full")
            parts = self.cache()
            session = source.open_session(parts[0].input_owner())
            ticket = await session.baseline()
            candidate = parts[0].admit_baseline(ticket.data)
            ticket.close()
            with (patch.object(_CompactScanner, "__init__", side_effect=AssertionError("compact scan")),
                  patch("agent_observer.mesh_sync_codec._load_value_schema", side_effect=AssertionError("body schema"))):
                self.assertEqual((await self.confirm(parts, session, candidate)).tag.native.wire(),
                                 list(server.state.sync_current_tag("full")))
            await source.aclose()

    async def test_opaque_body_is_not_source_admission_and_reader_rejects_original_bytes(self):
        with Running(state=self.owner(), experimental_sync=True) as server:
            raw = json.loads(server.state.sync_baseline("full"))
            raw["tables"]["bodies"][0][1][2] = {"opaque": "x" * 200000}
            corrupted = canonical(raw) + b"\n"
            source = self.source(server.path, "full")
            reader = self.cache()[0]
            session = source.open_session(reader.input_owner())
            loads = json.loads

            def bounded(data, *args, **kwargs):
                self.assertLess(len(data), 16384)
                return loads(data, *args, **kwargs)

            with (patch.object(server.state, "sync_baseline", new=lambda _view: corrupted),
                  patch("agent_observer.bounded_json.json.loads", new=bounded),
                  patch("agent_observer.mesh_sync_codec._load_value_schema", side_effect=AssertionError("body schema"))):
                ticket = await session.baseline()
            self.assertEqual(ticket.data.nbytes, len(corrupted))
            try:
                reader.admit_baseline(ticket.data)
            except ValueError as error:
                self.errors.append(error)
            else:
                self.fail("Reader admitted invalid compact body")
            ticket.close()
            await source.aclose()

    async def test_watch_close_revokes_delivered_compact_update_preserving_prior_ticket(self):
        with Running(state=self.owner(), experimental_sync=True) as server:
            source = self.source(server.path, "full")
            reader = self.cache()[0]
            session = source.open_session(reader.input_owner())
            baseline = await session.baseline()
            watch = session.watch(baseline.cursor)
            first = await asyncio.wait_for(anext(watch), 2)
            self.assertIsInstance(first, OwnedSyncControl)
            first.close()
            server.state.attempt("codex", "history")
            update = await asyncio.wait_for(anext(watch), 2)
            self.assertGreater(update.nbytes, 0)
            await watch.aclose()
            with self.assertRaises(ValueError):
                _ = update.nbytes
            self.assertGreater(baseline.data.nbytes, 0)
            baseline.close()
            await source.aclose()
