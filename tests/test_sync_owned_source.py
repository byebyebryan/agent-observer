"""Prepaid unadmitted intake, real local sockets and independent Mesh admission."""

import asyncio
import contextlib
import copy
import gc
import json
import unittest
from unittest.mock import patch

import test_sync_source as fixture
from test_sync_source import message_fixture, wire

from agent_observer.contract import ContractError
from agent_observer.sync_owned_source import (
    OwnedBaselineTicket,
    OwnedResyncRequired,
    OwnedSyncControl,
)
from agent_observer.sync_source import CachedAgentSyncSource

try:
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync.cache import OwnedSyncCache, source_binding
    from mesh_plus.sync.inputs import OwnedInputRef

    from agent_observer.mesh_sync_profile import AgentSyncProfile
except ModuleNotFoundError as error:
    if error.name != "mesh_plus" and not error.name.startswith("mesh_plus."):
        raise
    HAS_INPUTS = False
else:
    HAS_INPUTS = callable(getattr(OwnedSyncCache, "input_owner", None))


@unittest.skipUnless(HAS_INPUTS, "optional public Mesh input ownership is unavailable")
class OwnedSourceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixture.SyncSourceAcquisitionTest.asyncSetUp(self)
        self.caches = []
        self.cache = self.new_cache()
        self.inputs = self.cache.input_owner()
        self.owner_credit = self.cache.ledger.reserved
        self.session = self.source.open_session(self.inputs)

    async def asyncTearDown(self):
        await fixture.SyncSourceAcquisitionTest.asyncTearDown(self)
        for cache in self.caches:
            cache.close()
        for cache in self.caches:
            self.assertEqual(cache.ledger.used, 0)
            self.assertEqual(cache.ledger.reserved, 0)
            self.assertEqual(cache.ledger.encoded_reserved, 0)

    def new_cache(self, view="full", *, ledger=None):
        profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
        cache = OwnedSyncCache(profile, source_binding("fixture", "agents", profile.descriptor), ledger=ledger)
        self.caches.append(cache)
        return cache

    async def responses(self, values, *, pause_after=None):
        self.server.close()
        await self.server.wait_closed()
        self.path.unlink(missing_ok=True)

        async def handler(reader, writer):
            task = asyncio.current_task()
            self.handlers.add(task)
            try:
                self.requests.append(json.loads(await reader.readline()))
                for index, value in enumerate(values):
                    writer.write(value if type(value) is bytes else wire(value))
                    await writer.drain()
                    if index == pause_after:
                        self.entered.set()
                        await self.release.wait()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                self.handlers.discard(task)

        self.server = await asyncio.start_unix_server(handler, path=self.path)
        self.path.chmod(0o600)

    async def test_baseline_header_outlives_failed_consume_and_source_does_not_close_owner(self):
        with patch("agent_observer.sync_source.parse_message", side_effect=AssertionError("whole DTO parse")):
            ticket = await self.session.baseline()
        self.assertIsInstance(ticket, OwnedBaselineTicket)
        self.assertIsInstance(ticket.data, OwnedInputRef)
        self.assertEqual(ticket.data.nbytes, len(wire(self.baseline)))
        self.assertEqual(ticket.tag, tuple(self.baseline["tag"]))
        before = self.cache.ledger.reserved
        # The transport fixture has fabricated roots. Its structural ticket
        # must still fail complete independent receiver admission.
        with self.assertRaises(ProtocolError):
            self.cache.admit_baseline(ticket.data)
        with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
            _ = ticket.data.nbytes
        self.assertEqual(ticket.tag, tuple(self.baseline["tag"]))
        header_credit = self.cache.ledger.reserved
        self.assertLess(header_credit, before)
        ticket.close()
        self.assertLess(self.cache.ledger.reserved, header_credit)
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        await self.session.aclose()
        self.assertIs(self.cache.input_owner(), self.inputs)
        lease = self.inputs.reserve(1, encoded_bytes=0)
        lease.close()
        self.assertEqual(self.source.inspect()["activeSessions"], 0)
        self.assertFalse(self.source.inspect()["closed"])
        self.assertEqual((await self.source.baseline()).data, wire(self.baseline))

    async def test_real_full_active_baselines_reach_independent_receiver_unconfirmed(self):
        from test_sync_service_delivery import seeded

        for view in ("full", "active"):
            with self.subTest(view=view):
                owner = seeded()
                self.baseline = json.loads(owner.sync_baseline(view))
                self.addCleanup(owner._sync_cache.close)
                source = CachedAgentSyncSource("fixture", self.path, view=view, timeout=1)
                self.addAsyncCleanup(source.aclose)
                cache = self.new_cache(view)
                session = source.open_session(cache.input_owner())
                ticket = await session.baseline()
                candidate = cache.admit_baseline(ticket.data)
                self.assertIsNotNone(candidate)
                self.assertEqual(ticket.tag, tuple(self.baseline["tag"]))
                with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
                    _ = ticket.data.nbytes
                ticket.close()
                await session.aclose()
                self.assertEqual(session.inspect()["ownedLeases"], 0)

    async def test_full_active_aliases_share_one_ledger_without_sharing_authority(self):
        from test_sync_service_delivery import seeded

        owner = seeded()
        self.baseline = json.loads(owner.sync_baseline("full"))
        self.addCleanup(owner._sync_cache.close)
        full = await self.session.baseline()
        full_bytes = full.data.nbytes
        self.baseline = json.loads(owner.sync_baseline("active"))
        source = CachedAgentSyncSource("fixture", self.path, view="active", timeout=1)
        self.addAsyncCleanup(source.aclose)
        cache = self.new_cache("active", ledger=self.cache.ledger)
        session = source.open_session(cache.input_owner())
        active = await session.baseline()
        active_bytes = active.data.nbytes
        self.assertIs(cache.ledger, self.cache.ledger)
        self.assertEqual(cache.ledger.encoded_reserved, full_bytes + active_bytes)
        await self.session.aclose()
        self.cache.close()
        self.assertEqual(active.data.nbytes, active_bytes)
        self.assertEqual(cache.ledger.encoded_reserved, active_bytes)
        self.assertIsNotNone(cache.admit_baseline(active.data))
        self.assertEqual(active.tag, tuple(self.baseline["tag"]))
        active.close()
        await session.aclose()
        self.assertEqual(cache.ledger.encoded_reserved, 0)

    async def test_four_item_batch_prepays_all_refs_and_failed_consume_retires_all(self):
        transactions = [message_fixture("transaction", generation=i) for i in range(2, 6)]
        terminal = message_fixture("control", generation=5)
        terminal.update(baseTag=self.baseline["tag"], targetTag=transactions[-1]["resultTag"])
        await self.responses([*transactions, terminal])
        result = await self.session.changes(self.baseline["tag"], target=transactions[-1]["resultTag"])
        self.assertEqual(len(result), 4)
        expected = sum(len(wire(value)) for value in transactions)
        self.assertEqual(sum(value.nbytes for value in result), expected)
        self.assertEqual(self.cache.ledger.encoded_reserved, expected)
        # No baseline is admitted; consuming a bounded valid batch still
        # retires every ref, including the later unprocessed frames.
        with self.assertRaises(ProtocolError):
            self.cache.stage_batch(None, result)
        for value in result:
            with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
                _ = value.nbytes
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_partial_batch_keeps_first_ref_and_pending_input_charged(self):
        first = message_fixture("transaction", generation=2)
        second = message_fixture("transaction", generation=3)
        terminal = message_fixture("control", generation=3)
        terminal.update(baseTag=self.baseline["tag"], targetTag=second["resultTag"])
        await self.responses([first, second, terminal], pause_after=0)
        pending = asyncio.create_task(self.session.changes(self.baseline["tag"], target=second["resultTag"]))
        await self.entered.wait()
        for _ in range(20):
            await asyncio.sleep(0)
            if self.session.inspect()["ownedRefs"]:
                break
        self.assertEqual(self.session.inspect()["ownedRefs"], 1)
        self.assertGreaterEqual(self.cache.ledger.encoded_reserved, len(wire(first)))
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        self.assertEqual(self.source.inspect()["activeSockets"], 0)
        self.release.set()

    async def test_watch_close_revokes_its_refs_but_preserves_sibling_and_baseline(self):
        baseline = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        watch = self.session.watch(baseline.cursor)
        control = await anext(watch)
        self.assertIsInstance(control, OwnedSyncControl)
        self.updates.put_nowait(self.transaction)
        update = await anext(watch)
        self.assertEqual(update.nbytes, len(wire(self.transaction)))
        await watch.aclose()
        with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
            _ = update.nbytes
        with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
            _ = control.status
        self.assertEqual(baseline.data.nbytes, len(wire(self.baseline)))
        await self.session.aclose()
        self.assertEqual(other.data.nbytes, len(wire(self.baseline)))
        self.assertFalse(sibling.inspect()["closed"])
        self.assertEqual(self.source.inspect()["activeSessions"], 1)
        other.close()
        await sibling.aclose()

    async def test_head_and_explicit_resync_control_are_owned_without_authority(self):
        data = await self.session.head_after_nonce({"nonce": "b" * 32})
        self.assertIsInstance(data, OwnedInputRef)
        self.assertGreater(data.nbytes, 0)
        data.close()
        self.mode = "required"
        control = await self.session.changes(self.baseline["tag"], target=self.transaction["resultTag"])
        self.assertIsInstance(control, OwnedResyncRequired)
        self.assertEqual(control.status, "baseline_required")
        self.assertEqual(self.session.inspect()["ownedRefs"], 1)
        control.close()
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_retired_input_keeps_receive_credit_until_repeated_cancel_cleanup(self):
        self.mode = "wait"
        pending = asyncio.create_task(self.session.baseline())
        await self.entered.wait()
        reserved = self.cache.ledger.reserved
        self.cache.disconnect()
        self.assertGreater(self.cache.ledger.reserved, 0)
        self.assertEqual(self.cache.ledger.reserved, reserved)
        started, release = asyncio.Event(), asyncio.Event()
        original = self.session._client._close

        async def gated_close():
            started.set()
            await release.wait()
            await original()

        with patch.object(self.session._client, "_close", side_effect=gated_close):
            closing = asyncio.create_task(self.session.aclose())
            await started.wait()
            closing.cancel()
            await asyncio.sleep(0)
            closing.cancel()
            self.assertGreater(self.cache.ledger.reserved, 0)
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await closing
        await asyncio.gather(pending, return_exceptions=True)
        self.release.set()
        self.assertEqual(self.session.inspect()["ownedLeases"], 0)
        self.assertEqual(self.cache.ledger.reserved, 0)
        self.assertEqual(self.source.inspect()["activeSockets"], 0)

    async def test_close_waits_for_outer_operation_storage_after_inner_io_has_retired(self):
        entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        unrelated = asyncio.create_task(asyncio.Event().wait())

        async def operation(*_args):
            lease = self.session._reserve(16384, encoded_bytes=8192)
            payload = bytearray(8192)
            try:
                entered.set()
                await asyncio.Event().wait()
            finally:
                cleaning.set()
                await release.wait()
                self.assertEqual(len(payload), 8192)
                payload = None
                lease.close()

        with patch.object(self.session, "_call", side_effect=operation):
            pending = asyncio.create_task(self.session.baseline())
            await entered.wait()
            self.assertEqual(self.session.inspect()["activeTasks"], 0)
            closing = asyncio.create_task(self.session.aclose())
            await cleaning.wait()
            closing.cancel()
            await asyncio.sleep(0)
            closing.cancel()
            await asyncio.sleep(0)
            self.assertFalse(closing.done())
            self.assertFalse(unrelated.done())
            self.assertEqual(self.cache.ledger.encoded_reserved, 8192)
            self.assertGreater(self.cache.ledger.reserved, 16384)
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await closing
            with self.assertRaises(asyncio.CancelledError):
                await pending
        unrelated.cancel()
        await asyncio.gather(unrelated, return_exceptions=True)
        self.assertEqual(self.cache.ledger.reserved, self.owner_credit)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        self.assertEqual(self.session.inspect()["ownedOperations"], 0)

    async def test_post_receipt_timeout_retires_only_its_operation_scope_without_gc(self):
        prior = await self.session.baseline()
        reserved, encoded = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        original = self.session._client._io

        async def delayed_result(operation, seconds):
            result = await original(operation, seconds)
            if isinstance(result, OwnedBaselineTicket):
                raise ContractError("service_transport_timeout")
            return result

        was_enabled = gc.isenabled()
        gc.disable()
        try:
            with patch.object(self.session._client, "_io", side_effect=delayed_result):
                try:
                    await self.session.baseline()
                except ContractError as error:
                    saved = error
                else:
                    self.fail("late returned packet was accepted")
            self.assertEqual(saved.args, ("service_transport_timeout",))
            self.assertEqual(self.session.inspect()["ownedRefs"], 1)
            self.assertEqual(self.session.inspect()["ownedTickets"], 1)
            self.assertEqual(self.cache.ledger.reserved, reserved)
            self.assertEqual(self.cache.ledger.encoded_reserved, encoded)
            self.assertEqual(prior.data.nbytes, len(wire(self.baseline)))
            prior.close()
            await self.session.aclose()
            self.assertEqual(self.cache.ledger.reserved, self.owner_credit)
            self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        finally:
            if was_enabled:
                gc.enable()

    async def test_paused_watch_keeps_coalesced_next_frame_and_callback_credit(self):
        control = message_fixture("control")
        second = message_fixture("transaction", generation=3)
        await self.responses([wire(control) + wire(self.transaction) + wire(second)])
        watch = self.session.watch(self.baseline["cursor"])
        header = await anext(watch)
        header.close()
        first = await anext(watch)
        stream = watch._iterator.ag_frame.f_locals["stream"]
        self.assertEqual(bytes(stream.pending), wire(second))
        self.assertGreaterEqual(self.cache.ledger.encoded_reserved, first.nbytes + len(stream.pending))
        self.assertGreater(stream.intake.encoded_bytes, len(stream.pending))
        await watch.aclose()
        self.assertEqual(len(stream.pending), 0)
        self.assertIsNone(stream.intake)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
            _ = first.nbytes

    async def test_challenge_and_tuple_preflight_bound_before_canonical_or_list_allocation(self):
        from agent_observer.sync_contract import validate_request
        from agent_observer.sync_owned_source import _challenge_preflight

        for challenge in ({"nonce": "x" * 4097}, {"x": [0] * 257}, {"x": [[[[[[[[0]]]]]]]]}):
            with self.subTest(challenge_type=type(challenge["x"]).__name__ if "x" in challenge else "string"):
                with patch.object(self.session._client, "_request", side_effect=AssertionError("unbounded encode")):
                    with self.assertRaisesRegex(ContractError, "sync_challenge_limit"):
                        await self.session.head_after_nonce(challenge)
        # The preflight is only a necessary bound; every challenge accepted by
        # the frozen validator in this boundary corpus must still pass it.
        challenges = [{}, {"nonce": "x" * 4084}, {"unicode": "\u00e9" * 1000},
                      {"a": list(range(250))}, {"a": [[[[[[[0]]]]]]]},
                      {"a": None, "b": [True, False, -((1 << 53) - 1)]}]
        for challenge in challenges:
            validate_request({"syncProtocol": self.source.protocol, "version": 1, "operation": "head",
                              "hostScope": "fixture", "challenge": challenge})
            _challenge_preflight(challenge)
        pulls = []

        def unbounded():
            while True:
                pulls.append(None)
                yield "x"

        with self.assertRaisesRegex(ContractError, "sync_tuple_shape"):
            self.session.watch(unbounded())
        self.assertEqual(len(pulls), 4)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_saved_watch_failure_drops_request_and_header_frames_before_refund(self):
        baseline = await self.session.baseline()
        before = self.cache.ledger.reserved
        control = message_fixture("control")
        invalid = copy.deepcopy(self.transaction)
        invalid["descriptor"]["unexpected"] = True
        await self.responses([control, invalid])
        watch = self.session.watch(baseline.cursor)
        (await anext(watch)).close()
        try:
            await anext(watch)
        except ContractError as error:
            saved = error
        else:
            self.fail("invalid watch was accepted")
        self.assertIsNone(watch.request)
        self.assertEqual(self.cache.ledger.reserved, before)
        self.assertEqual(self.session.inspect()["ownedLeases"], 1)  # independent baseline header
        frames = []
        trace = saved.__traceback__
        while trace is not None:
            frames.append(trace.tb_frame.f_code.co_name)
            trace = trace.tb_next
        self.assertNotIn("_frames", frames)
        self.assertNotIn("_read_frame", frames)

    async def test_malformed_header_rejects_and_releases_input(self):
        invalid = copy.deepcopy(self.baseline)
        invalid["descriptor"]["unexpected"] = True
        self.baseline = invalid
        with self.assertRaises(ContractError):
            await self.session.baseline()
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.session.inspect()["ownedTickets"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_duplicate_header_is_rejected_but_opaque_duplicate_requires_receiver_admission(self):
        raw = wire(self.baseline)
        duplicate = raw.replace(b'"kind":"baseline"', b'"kind":"baseline","kind":"baseline"')
        await self.responses([duplicate])
        with self.assertRaises(ContractError):
            await self.session.baseline()
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        opaque = raw.replace(b'"bodies":[]', b'"bodies":[["body",{"x":1,"x":2}]]')
        self.assertNotEqual(opaque, raw)
        await self.responses([opaque])
        with self.assertRaises(ValueError):
            await self.source.baseline()
        ticket = await self.session.baseline()
        self.assertEqual(ticket.data.nbytes, len(opaque))
        with self.assertRaises(ProtocolError):
            self.cache.admit_baseline(ticket.data)
        ticket.close()
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_quota_rejection_precedes_request_or_socket_allocation(self):
        available = self.cache.ledger.maximum - self.cache.ledger.used - self.cache.ledger.reserved
        hold = self.inputs.reserve(available - 2048, encoded_bytes=0)
        try:
            with self.assertRaisesRegex(ProtocolError, "sync_decoded_capacity"):
                await self.session.baseline()
            self.assertEqual(self.requests, [])
            self.assertEqual(self.source.inspect()["activeSockets"], 0)
        finally:
            hold.close()

    async def test_wrong_uid_and_challenge_keep_transport_guards_before_sealing(self):
        self.mode = "wrong_uid"
        with self.assertRaisesRegex(ContractError, "sync_clock_context"):
            await self.session.baseline()
        self.mode = "wrong_challenge"
        with self.assertRaisesRegex(ContractError, "sync_challenge_binding"):
            await self.session.head_after_nonce({"nonce": "b" * 32})
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_repeated_consumed_refs_do_not_accumulate_source_history(self):
        reserved = self.cache.ledger.reserved
        for _ in range(70):
            ticket = await self.session.baseline()
            with self.assertRaises(ProtocolError):
                self.cache.admit_baseline(ticket.data)
            ticket.close()
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.session.inspect()["ownedTickets"], 0)
        self.assertEqual(self.session.inspect()["ownedLeases"], 0)
        self.assertEqual(self.cache.ledger.reserved, reserved)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)

    async def test_session_close_does_not_renew_or_share_ref_across_cache_alias(self):
        ticket = await self.session.baseline()
        other = self.new_cache()
        with self.assertRaisesRegex(ProtocolError, "sync_input_owner"):
            other.admit_baseline(ticket.data)
        self.assertEqual(ticket.tag, tuple(self.baseline["tag"]))
        ticket.close()
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
        self.assertEqual(other.ledger.encoded_reserved, 0)

    async def test_parent_close_reaps_sessions_and_plain_watch_shares_the_channel_limit(self):
        watches = [self.session.watch(self.baseline["cursor"]) for _ in range(16)]
        with self.assertRaisesRegex(ContractError, "sync_acquisition_capacity"):
            self.source.watch(self.baseline["cursor"])
        self.assertEqual(self.source.inspect()["activeWatches"], 16)
        await self.source.aclose()
        self.assertTrue(self.session.inspect()["closed"])
        self.assertEqual(self.session.inspect()["ownedLeases"], 0)
        self.assertEqual(self.source.inspect()["activeSessions"], 0)
        for watch in watches:
            with self.assertRaises(StopAsyncIteration):
                await anext(watch)
        self.assertIs(self.cache.input_owner(), self.inputs)
