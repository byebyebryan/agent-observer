"""Exact completion transfer on disposable sockets, not provider/native proof."""

import asyncio
import gc
import hashlib
import unittest
import weakref
from unittest.mock import patch

import test_mesh_sync_read as read_fixture
import test_sync_owned_source as fixture
from test_sync_source import message_fixture, wire

from agent_observer.contract import ContractError
from agent_observer.sync_contract import MAX_CHANGE_BYTES
from agent_observer.sync_native import MAX_CONTROL_BYTES
from agent_observer.sync_owned_source import (
    _BATCH_HEAP,
    CompletedChanges,
    OwnedResyncRequired,
    _SourceLease,
)
from agent_observer.sync_source import CachedAgentSyncSource


def chain(count, *, view="full"):
    base = message_fixture(view=view)["tag"]
    transactions = [message_fixture("transaction", view=view, generation=i + 2) for i in range(count)]
    target = base if not transactions else transactions[-1]["resultTag"]
    complete = message_fixture("control", view=view, generation=count + 1)
    complete.update(baseTag=base, targetTag=target)
    return base, target, transactions, complete


@unittest.skipUnless(fixture.HAS_INPUTS, "optional public Mesh input ownership is unavailable")
class CompletedChangesTest(unittest.IsolatedAsyncioTestCase):
    # Reuse the socket fixture without importing/discovering its TestCase twice.
    new_cache = fixture.OwnedSourceTest.new_cache
    responses = fixture.OwnedSourceTest.responses

    async def asyncSetUp(self):
        self.gc_enabled = gc.isenabled()
        gc.disable()
        await fixture.OwnedSourceTest.asyncSetUp(self)
        self.errors = []

    async def asyncTearDown(self):
        try:
            await fixture.OwnedSourceTest.asyncTearDown(self)
            self.assertEqual(self.session.inspect()["ownedBatches"], 0)
            for cache in self.caches:
                self.assertEqual((cache.ledger.encoded, cache.ledger.pending_units), (0, 0))
            self.assertFalse(gc.isenabled())
        finally:
            if self.gc_enabled:
                gc.enable()

    def assert_retired(self, batch, refs):
        for name in ("transactions", "completion"):
            with self.assertRaisesRegex(ContractError, "sync_change_batch_closed"):
                getattr(batch, name)
        for ref in refs:
            with self.assertRaisesRegex(ValueError, "sync_input_retired"):
                _ = ref.nbytes

    async def test_full_active_zero_one_four_preserve_original_sealed_refs_and_exact_bytes(self):
        for view in ("full", "active"):
            for count in (0, 1, 4):
                with self.subTest(view=view, count=count):
                    base, target, transactions, complete = chain(count, view=view)
                    sent = [wire(value) for value in [*transactions, complete]]
                    await self.responses(sent)
                    source = CachedAgentSyncSource("fixture", self.path, view=view, timeout=1)
                    cache = self.new_cache(view)
                    session = source.open_session(cache.input_owner())
                    original = _SourceLease.seal
                    sealed = []

                    def seal(lease, raw, _original=original, _sealed=sealed):
                        result = _original(lease, raw)
                        _sealed.append((result, hashlib.sha256(raw).hexdigest()))
                        return result

                    try:
                        with patch.object(_SourceLease, "seal", new=seal):
                            batch = await session.changes_with_completion(base, target=target)
                        self.assertIsInstance(batch, CompletedChanges)
                        self.assertIs(type(batch.transactions), tuple)
                        refs = (*batch.transactions, batch.completion.data)
                        self.assertEqual(len(refs), count + 1)
                        self.assertEqual(sealed, list(zip(refs, (hashlib.sha256(raw).hexdigest()
                                                              for raw in sent), strict=True)))
                        self.assertEqual(sum(ref.nbytes for ref in refs), sum(map(len, sent)))
                        self.assertEqual(batch.completion.status, "complete")
                        self.assertEqual(batch.completion.tag, tuple(target))
                        self.assertEqual(batch.completion.cursor, tuple(complete["cursor"]))
                        self.assertEqual(cache.ledger.encoded_reserved, sum(map(len, sent)))
                        self.assertEqual(session.inspect()["ownedBatches"], 1)
                        self.assertEqual(session.inspect()["activeSockets"], 0)
                        with self.assertRaises(AttributeError):
                            batch.transactions = ()
                        batch.close()
                        batch.close()
                        self.assert_retired(batch, refs)
                        self.assertEqual(session.inspect()["ownedBatches"], 0)
                    finally:
                        await source.aclose()

    async def test_real_owner_full_active_batches_admit_only_after_independent_fresh_proof(self):
        from test_service_runtime import scoped_snapshot
        from test_sync_service_delivery import seeded

        helper = read_fixture.MeshSyncReadTest()
        helper.caches = self.caches
        for view in ("full", "active"):
            for count in (0, 1, 4):
                with self.subTest(view=view, transactions=count):
                    owner = seeded()
                    source = CachedAgentSyncSource("fixture", self.path, view=view, timeout=1)
                    parts = helper.cache(view)
                    cache = parts[0]
                    session = source.open_session(cache.input_owner())
                    try:
                        baseline = owner.sync_baseline(view)
                        await self.responses([baseline])
                        ticket = await session.baseline()
                        candidate = cache.admit_baseline(ticket.data)
                        base = ticket.tag
                        ticket.close()
                        if count == 1:
                            owner.attempt("codex", "history")
                        elif count == 4:
                            for index in range(2):
                                value = scoped_snapshot()
                                value["sessions"][0]["title"] = f"changed {index}"
                                owner.attempt("codex", "history")
                                self.assertTrue(owner.accept("codex", "history", value,
                                                             sampled_ms=owner.clock(), ttl_ms=60000,
                                                             runtime_ttl_ms=60000))
                        target = owner.sync_current_tag(view)
                        response = owner.sync_changes(view, base, target)
                        self.assertIs(type(response), tuple)
                        self.assertEqual(len(response), count + 1)
                        await self.responses(response)
                        batch = await session.changes_with_completion(base, target=target)
                        self.assertEqual(len(batch.transactions), count)
                        if count:
                            candidate = cache.stage_batch(candidate.tag, batch.transactions)
                        self.assertEqual(candidate.tag.native.wire(), list(target))
                        with self.assertRaises(ValueError):
                            cache.acquire()
                        # Existing test-owned challenge setup, then ordinary
                        # independent Mesh proof/root/lease confirmation.
                        confirmed = helper.confirm(parts, owner, candidate)
                        expected = owner.snapshot if view == "full" else owner.active_projection
                        self.assertEqual(confirmed.export_committed(), expected)
                        batch.close()
                        self.assertEqual(cache.acquire().tag, confirmed.tag)
                    finally:
                        await source.aclose()
                        owner._sync_cache.close()

    async def test_consumption_keeps_independent_batch_and_completion_metadata_until_close(self):
        base, target, transactions, complete = chain(4)
        await self.responses([*transactions, complete])
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        batch = await self.session.changes_with_completion(base, target=target)
        refs = batch.transactions
        control = batch.completion
        control_ref = control.data
        with self.assertRaises(ValueError):
            self.cache.stage_batch(None, refs)
        self.assertEqual(control.data.nbytes, len(wire(complete)))
        self.assertEqual(control.tag, tuple(target))
        with self.assertRaises(ValueError):
            self.cache.admit_baseline(control.data)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        self.assertEqual(batch.completion.status, "complete")
        self.assertGreater(self.cache.ledger.reserved, before[0] + _BATCH_HEAP)
        control.close()
        metadata = self.cache.ledger.reserved
        self.assertGreaterEqual(metadata, before[0] + _BATCH_HEAP)
        self.assertEqual(self.session.inspect()["ownedBatches"], 1)
        self.assertEqual(self.session.inspect()["ownedLeases"], 1)
        batch.close()
        # The input owner also charges its own reservation bookkeeping. All of
        # that credit lasts with the batch and retires only on its close.
        self.assertGreaterEqual(metadata - self.cache.ledger.reserved, _BATCH_HEAP)
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
        self.assert_retired(batch, (*refs, control_ref))

    async def test_batch_close_preserves_prior_baseline_and_shared_owner_sibling(self):
        prior = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        base, target, transactions, complete = chain(1)
        await self.responses([*transactions, complete])
        batch = await self.session.changes_with_completion(base, target=target)
        refs = (*batch.transactions, batch.completion.data)
        batch.close()
        self.assert_retired(batch, refs)
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
        self.assertGreater(prior.data.nbytes, 0)
        self.assertGreater(other.data.nbytes, 0)
        with self.inputs.reserve(1):
            pass
        await sibling.aclose()

    async def test_recovery_returns_original_control_and_closes_prefix_without_batch(self):
        base, target, transactions, complete = chain(1)
        complete.update(status="baseline_required", reason="sync_missing_base")
        await self.responses([*transactions, complete])
        control = await self.session.changes_with_completion(base, target=target)
        self.assertIsInstance(control, OwnedResyncRequired)
        self.assertEqual(control.status, "baseline_required")
        self.assertEqual(control.data.nbytes, len(wire(complete)))
        self.assertEqual(self.session.inspect()["ownedBatches"], 0)
        self.assertEqual(self.session.inspect()["ownedRefs"], 1)
        control.close()
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_invalid_or_missing_completion_never_exposes_prefix_and_keeps_siblings(self):
        prior = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        for case in ("missing", "wrong-tag", "heartbeat", "foreign-cursor", "wrong-base", "wrong-target"):
            with self.subTest(case=case):
                base, target, transactions, complete = chain(1)
                if case == "wrong-tag":
                    complete["tag"] = base
                    complete["cursor"][1:] = base[1:]
                if case == "heartbeat":
                    complete["status"] = "heartbeat"
                if case == "foreign-cursor":
                    complete["ownerClock"]["ownerEpoch"] = complete["cursor"][0] = "00000000-0000-0000-0000-000000000008"
                if case == "wrong-base":
                    complete["baseTag"] = target
                if case == "wrong-target":
                    complete["targetTag"] = base
                await self.responses(transactions if case == "missing" else [*transactions, complete])
                try:
                    await self.session.changes_with_completion(base, target=target)
                except ContractError as error:
                    self.errors.append(error)
                else:
                    self.fail("invalid completion exposed a batch")
                self.assertEqual(self.session.inspect()["ownedBatches"], 0)
                self.assertEqual(self.session.inspect()["ownedRefs"], 1)
                self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
                self.assertGreater(prior.data.nbytes, 0)
                self.assertGreater(other.data.nbytes, 0)
        self.assertEqual(len(self.errors), 6)
        await sibling.aclose()

    async def test_native_control_cap_stays_16k_and_material_quota_excludes_only_that_control(self):
        base, target, transactions, complete = chain(1)
        material = len(wire(transactions[0]))
        raw = wire(complete)
        for size in (MAX_CONTROL_BYTES, MAX_CONTROL_BYTES + 1, 65536):
            with self.subTest(bytes=size):
                padded = raw[:-1] + b" " * (size - len(raw)) + b"\n"
                await self.responses([transactions[0], padded])
                if size == MAX_CONTROL_BYTES:
                    batch = await self.session.changes_with_completion(base, target=target, max_bytes=material)
                    self.assertEqual(batch.completion.data.nbytes, size)
                    batch.close()
                else:
                    with self.assertRaisesRegex(ContractError, "sync_ticket_header_limit"):
                        await self.session.changes_with_completion(base, target=target, max_bytes=material)
                self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        await self.responses([transactions[0], complete])
        with self.assertRaisesRegex(ContractError, "sync_change_limit"):
            await self.session.changes_with_completion(base, target=target, max_bytes=material - 1)
        self.assertEqual(self.session.inspect()["ownedBatches"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_count_and_zero_chain_bounds_remain_strict(self):
        for case in ("five", "empty-moved"):
            base, target, transactions, complete = chain(5 if case == "five" else 1)
            await self.responses([*transactions, complete] if case == "five" else [complete])
            with self.assertRaisesRegex(ContractError, "sync_change_limit|sync_change_target"):
                await self.session.changes_with_completion(base, target=target)
            self.assertEqual(self.session.inspect()["ownedBatches"], 0)
            self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_exact_eight_mib_material_plus_control_and_one_byte_quota_refusal(self):
        base, target, transactions, complete = chain(4)
        frames = []
        for value in transactions:
            # Deliberately opaque, semantically invalid rows: structural
            # acquisition grants no admission. Fixture storage is caller-owned.
            value["operations"]["bodies"] = [["opaque", ""]]
            padding = MAX_CHANGE_BYTES // 4 - len(wire(value))
            value["operations"]["bodies"][0][1] = "x" * padding
            raw = wire(value)
            self.assertEqual(len(raw), MAX_CHANGE_BYTES // 4)
            frames.append(raw)
        await self.responses([*frames, complete])
        source = CachedAgentSyncSource("fixture", self.path, timeout=15)
        session = source.open_session(self.inputs)
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        try:
            batch = await session.changes_with_completion(base, target=target)
            self.assertEqual(sum(ref.nbytes for ref in batch.transactions), MAX_CHANGE_BYTES)
            self.assertEqual(self.cache.ledger.encoded_reserved, MAX_CHANGE_BYTES + len(wire(complete)))
            batch.close()
            with self.assertRaisesRegex(ContractError, "sync_change_limit"):
                await session.changes_with_completion(base, target=target, max_bytes=MAX_CHANGE_BYTES - 1)
            self.assertEqual(session.inspect()["ownedBatches"], 0)
            self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
        finally:
            await source.aclose()

    async def test_container_credit_refusal_precedes_constructor_and_retires_original_control(self):
        base, target, transactions, complete = chain(1)
        await self.responses([*transactions, complete])
        reserve = self.session._reserve
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved

        def refuse(amount, **kwargs):
            if amount == _BATCH_HEAP:
                raise ContractError("fixture_batch_refusal")
            return reserve(amount, **kwargs)

        with patch.object(self.session, "_reserve", side_effect=refuse), \
                patch.object(CompletedChanges, "__init__", side_effect=AssertionError("unpaid container")) as mint:
            try:
                await self.session.changes_with_completion(base, target=target)
            except ContractError as error:
                self.errors.append(error)
                self.assertEqual(str(error), "fixture_batch_refusal")
            else:
                self.fail("unpaid batch accepted")
            mint.assert_not_called()
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
        self.assertEqual(self.session.inspect()["ownedBatches"], 0)
        with self.assertRaisesRegex(ContractError, "sync_change_batch_mint"):
            CompletedChanges(None, (), None, None, None)

    async def test_completed_await_cancellation_retires_batch_without_touching_prior_or_sibling(self):
        prior = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        create = asyncio.create_task
        for count in (0, 1, 4):
            base, target, transactions, complete = chain(count)
            await self.responses([*transactions, complete])
            caller = create(self.session.changes_with_completion(base, target=target))
            attached = False

            def schedule(coroutine, *args, _caller=caller, **kwargs):
                nonlocal attached
                task = create(coroutine, *args, **kwargs)
                if not attached:
                    attached = True
                    task.add_done_callback(lambda done: _caller.cancel() if not done.cancelled()
                                           and done.exception() is None else None)
                return task

            with patch.object(asyncio, "create_task", side_effect=schedule):
                try:
                    await caller
                except asyncio.CancelledError as error:
                    self.errors.append(error)
                else:
                    self.fail("batch escaped completed-await cancellation")
            self.assertTrue(attached)
            self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
            self.assertEqual(self.session.inspect()["ownedBatches"], 0)
            self.assertGreater(prior.data.nbytes, 0)
            self.assertGreater(other.data.nbytes, 0)
        await sibling.aclose()

    async def test_cancel_during_completed_stream_cleanup_revokes_before_await_and_holds_io_credit(self):
        prior = await self.session.baseline()
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        base, target, transactions, complete = chain(1)
        await self.responses([*transactions, complete])
        entered, release = asyncio.Event(), asyncio.Event()
        frames = self.session._client._frames

        async def gated(*args, **kwargs):
            iterator = frames(*args, **kwargs)
            try:
                async for value in iterator:
                    yield value
            finally:
                entered.set()
                await release.wait()
                await iterator.aclose()

        with patch.object(self.session._client, "_frames", new=gated):
            caller = asyncio.create_task(self.session.changes_with_completion(base, target=target))
            await asyncio.wait_for(entered.wait(), 2)
            batch = next(iter(self.session._batches))
            refs = (*batch.transactions, batch.completion.data)
            caller.cancel()
            for _ in range(5):
                await asyncio.sleep(0)
            caller.cancel()
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertFalse(caller.done())
            self.assert_retired(batch, refs)
            self.assertGreater(self.cache.ledger.reserved, before[0])
            self.assertGreater(self.cache.ledger.encoded_reserved, before[1])
            self.assertGreater(prior.data.nbytes, 0)
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await caller
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)

    async def test_session_close_revokes_delivered_batch_before_gated_cleanup_and_preserves_sibling(self):
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        base, target, transactions, complete = chain(1)
        await self.responses([*transactions, complete])
        batch = await self.session.changes_with_completion(base, target=target)
        refs = (*batch.transactions, batch.completion.data)
        entered, release = asyncio.Event(), asyncio.Event()
        close = self.session._client._close

        async def gated():
            entered.set()
            await release.wait()
            await close()

        with patch.object(self.session._client, "_close", side_effect=gated):
            closing = asyncio.create_task(self.session.aclose())
            await asyncio.wait_for(entered.wait(), 2)
            self.assert_retired(batch, refs)
            self.assertGreater(other.data.nbytes, 0)
            with self.inputs.reserve(1):
                pass
            release.set()
            await closing
        with self.assertRaisesRegex(ContractError, "sync_source_closed"):
            await self.session.changes_with_completion(base, target=target)
        await sibling.aclose()

    async def test_live_tracking_is_bounded_and_retained_closed_handles_do_not_accumulate(self):
        base, target, _transactions, complete = chain(0)
        await self.responses([complete])
        before = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        retained = []
        for _ in range(70):
            batch = await self.session.changes_with_completion(base, target=target)
            retained.append((batch, batch.completion, batch.completion.data))
            batch.close()
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)
        self.assertEqual(self.session.inspect()["ownedBatches"], 0)
        self.assertEqual(self.session.inspect()["ownedLeases"], 0)
        live = []
        for _ in range(65):
            try:
                live.append(await self.session.changes_with_completion(base, target=target))
            except ValueError as error:
                self.errors.append(error)
                self.assertIn(str(error), ("sync_source_ownership_capacity", "sync_input_slots"))
                break
        else:
            self.fail("unbounded live batch registry")
        self.assertGreater(len(live), 1)
        self.assertLessEqual(self.session.inspect()["ownedBatches"], 64)
        for batch in live:
            batch.close()
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before)

    async def test_closed_batch_errors_and_handles_do_not_pin_closed_source_owners_without_gc(self):
        base, target, _transactions, complete = chain(0)
        await self.responses([complete])
        source = CachedAgentSyncSource("fixture", self.path, timeout=1)
        session = source.open_session(self.inputs)
        owner_ref, session_ref = weakref.ref(source), weakref.ref(session)
        batch = await session.changes_with_completion(base, target=target)
        ticket, data = batch.completion, batch.completion.data
        await source.aclose()
        for name in ("transactions", "completion"):
            try:
                getattr(batch, name)
            except ContractError as error:
                self.errors.append(error)
            else:
                self.fail("retired batch property accepted")
        source = session = None
        self.assertIsNone(owner_ref())
        self.assertIsNone(session_ref())
        self.assert_retired(batch, (data,))
        ticket.close()
