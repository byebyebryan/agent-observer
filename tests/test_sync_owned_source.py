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

    async def test_change_completion_correlation_rejects_for_plain_and_owned_without_revoking_siblings(self):
        baseline = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        held = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        errors, enabled = [], gc.isenabled()
        gc.disable()
        try:
            for owned in (False, True):
                for case in ("wrong-target", "heartbeat", "foreign-control", "foreign-transaction"):
                    with self.subTest(owned=owned, case=case):
                        transactions = [copy.deepcopy(self.transaction)]
                        terminal = message_fixture("control", generation=3 if case == "wrong-target" else 2)
                        target = transactions[-1]["resultTag"]
                        if case == "heartbeat":
                            terminal["status"] = "heartbeat"
                        if case == "foreign-control":
                            terminal["ownerClock"]["ownerEpoch"] = terminal["cursor"][0] = "00000000-0000-0000-0000-000000000008"
                        if case == "foreign-transaction":
                            following = message_fixture("transaction", generation=3)
                            following["baseCursor"][0] = following["resultCursor"][0] = "00000000-0000-0000-0000-000000000008"
                            transactions.append(following)
                            target = following["resultTag"]
                            terminal = message_fixture("control", generation=3)
                            terminal["ownerClock"]["ownerEpoch"] = terminal["cursor"][0] = following["resultCursor"][0]
                        terminal.update(baseTag=self.baseline["tag"], targetTag=target)
                        await self.responses([*transactions, terminal])
                        source = CachedAgentSyncSource("fixture", self.path, timeout=1)
                        session = source.open_session(self.inputs) if owned else None
                        method = session.changes if owned else source.changes
                        try:
                            try:
                                returned = await method(self.baseline["tag"], target=target)
                            except ContractError as error:
                                self.assertIn(error.args[0], ("sync_change_target", "sync_change_order"))
                                errors.append(error)
                            else:
                                if owned:
                                    for ref in returned:
                                        ref.close()
                                returned = None
                                self.fail("uncorrelated change completion accepted")
                        finally:
                            await source.aclose()
                        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), held)
                        self.assertEqual(self.session.inspect()["ownedRefs"], 1)
                        self.assertEqual(self.session.inspect()["ownedTickets"], 1)
                        self.assertGreater(baseline.data.nbytes, 0)
                        self.assertGreater(other.data.nbytes, 0)
                        self.assertEqual(sibling.inspect()["ownedRefs"], 1)
            self.assertEqual(len(errors), 8)
        finally:
            if enabled:
                gc.enable()
            baseline.close()
            other.close()
            await sibling.aclose()

    async def test_zero_transaction_exact_completion_preserves_legacy_success_shape(self):
        terminal = message_fixture("control")
        terminal.update(baseTag=self.baseline["tag"], targetTag=self.baseline["tag"])
        for owned in (False, True):
            await self.responses([terminal])
            method = self.session.changes if owned else self.source.changes
            self.assertEqual(await method(self.baseline["tag"], target=self.baseline["tag"]), ())
            self.assertEqual(self.cache.ledger.encoded_reserved, 0)
            self.assertEqual(self.session.inspect()["ownedRefs"], 0)
            self.assertEqual(self.session.inspect()["ownedTickets"], 0)

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
        before_watch = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        tail = wire(message_fixture("transaction", generation=3))[:73]
        await self.responses([wire(message_fixture("control")) + wire(self.transaction) + tail], pause_after=0)
        watch = self.session.watch(baseline.cursor)
        control = await anext(watch)
        self.assertIsInstance(control, OwnedSyncControl)
        update = await anext(watch)
        self.assertEqual(update.nbytes, len(wire(self.transaction)))
        control_data = control.data
        encoded_before_close = self.cache.ledger.encoded_reserved
        retired_bytes = update.nbytes + control_data.nbytes
        entered, release = asyncio.Event(), asyncio.Event()
        cleanup = watch._close

        async def gated_cleanup():
            entered.set()
            await release.wait()
            await cleanup()

        try:
            with patch.object(watch, "_close", side_effect=gated_cleanup):
                closing = asyncio.create_task(watch.aclose())
                try:
                    await asyncio.wait_for(entered.wait(), 2)
                    with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
                        _ = update.nbytes
                    with self.assertRaisesRegex(ProtocolError, "sync_input_retired"):
                        _ = control_data.nbytes
                    with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                        _ = control.status
                    # The unread partial frame, stream and request remain live.
                    self.assertEqual(self.cache.ledger.encoded_reserved, encoded_before_close - retired_bytes)
                    self.assertGreater(self.cache.ledger.encoded_reserved, before_watch[1] + len(tail))
                    self.assertGreater(self.cache.ledger.reserved, before_watch[0])
                    self.assertGreater(baseline.data.nbytes, 0)
                    self.assertGreater(other.data.nbytes, 0)
                finally:
                    release.set()
                    await closing
        finally:
            self.release.set()
            await watch.aclose()
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before_watch)
        self.assertEqual(baseline.data.nbytes, len(wire(self.baseline)))
        await self.session.aclose()
        self.assertEqual(other.data.nbytes, len(wire(self.baseline)))
        self.assertFalse(sibling.inspect()["closed"])
        self.assertEqual(self.source.inspect()["activeSessions"], 1)
        other.close()
        await sibling.aclose()

    async def test_watch_close_rejects_inflight_and_completed_frames_without_late_refs(self):
        baseline = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        try:
            for phase in ("receiving", "completed"):
                with self.subTest(phase=phase):
                    await self.check_watch_close_frame(phase, baseline, other)
            usable = await sibling.baseline()
            usable.close()
        finally:
            baseline.close()
            other.close()
            await sibling.aclose()

    async def check_watch_close_frame(self, phase, baseline, other):
        before_watch = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        watch = self.session.watch(baseline.cursor)
        (await anext(watch)).close()
        entered, returned, release_frame = asyncio.Event(), asyncio.Event(), asyncio.Event()
        cleanup_entered, release_cleanup = asyncio.Event(), asyncio.Event()
        original_io, original_frame = self.session._client._io, self.session._client._read_frame
        cleanup = watch._close
        received_bytes = 0

        async def receive(operation, timeout):
            nonlocal received_bytes
            if phase == "receiving":
                entered.set()
            part = await original_io(operation, timeout)
            received_bytes += len(part)
            return part

        async def frame(*args, **kwargs):
            try:
                result = await original_frame(*args, **kwargs)
                if phase == "completed":
                    entered.set()
                    await release_frame.wait()
                return result
            finally:
                returned.set()

        async def gated_cleanup():
            cleanup_entered.set()
            await release_cleanup.wait()
            await cleanup()

        with (patch.object(self.session._client, "_io", side_effect=receive),
              patch.object(self.session._client, "_read_frame", side_effect=frame),
              patch.object(watch, "_close", side_effect=gated_cleanup)):
            pending = asyncio.create_task(anext(watch))
            closing = None
            try:
                if phase == "completed":
                    self.updates.put_nowait(self.transaction)
                await asyncio.wait_for(entered.wait(), 2)
                held_credit = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
                bytes_before_close = self.session.inspect()["receivedBytes"]
                closing = asyncio.create_task(watch.aclose())
                await asyncio.wait_for(cleanup_entered.wait(), 2)
                if phase == "receiving":
                    self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), held_credit)
                    self.updates.put_nowait(self.transaction)
                else:
                    release_frame.set()
                await asyncio.wait_for(returned.wait(), 2)
                counts = self.session.inspect()
                self.assertEqual((counts["ownedRefs"], counts["ownedTickets"]), (1, 1))
                self.assertEqual(counts["receivedBytes"], bytes_before_close + (
                    received_bytes if phase == "receiving" else 0))
                self.assertFalse(pending.done())  # late failure still awaits cleanup
                self.assertGreater(self.cache.ledger.reserved, before_watch[0])
                self.assertGreater(baseline.data.nbytes, 0)
                self.assertGreater(other.data.nbytes, 0)
            finally:
                release_frame.set()
                release_cleanup.set()
                await watch.aclose()
                outcomes = await asyncio.gather(pending, *(() if closing is None else (closing,)),
                                                return_exceptions=True)
            self.assertIsInstance(outcomes[0], ContractError)
            self.assertEqual(str(outcomes[0]), "sync_source_closed")
        self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), before_watch)
        with self.inputs.reserve(0):
            pass

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

    async def test_cancel_after_completed_operation_retires_only_its_unreturned_result(self):
        baseline = await self.session.baseline()
        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        watch = sibling.watch(other.cursor)
        control = await anext(watch)
        before = self.session.inspect()
        credit = self.cache.ledger.reserved, self.cache.ledger.encoded_reserved
        saved = []
        create = asyncio.create_task
        enabled = gc.isenabled()
        gc.disable()
        try:
            for name in ("baseline", "head", "changes", "required"):
                with self.subTest(operation=name):
                    self.mode = "required" if name == "required" else "normal"
                    operation = (self.session.baseline() if name == "baseline" else
                                 self.session.head_after_nonce({"nonce": "b" * 32}) if name == "head" else
                                 self.session.changes(self.baseline["tag"], target=self.transaction["resultTag"]))
                    caller = create(operation)
                    attached = False

                    def schedule(coroutine, *args, _caller=caller, **kwargs):
                        nonlocal attached
                        task = create(coroutine, *args, **kwargs)
                        if not attached:
                            attached = True
                            # Run before the completed operation's awaiter:
                            # its successful result never reaches the caller.
                            task.add_done_callback(lambda done: _caller.cancel() if not done.cancelled()
                                                   and done.exception() is None else None)
                        return task

                    with patch.object(asyncio, "create_task", side_effect=schedule):
                        try:
                            await caller
                        except asyncio.CancelledError as error:
                            saved.append(error)
                        else:
                            self.fail("completed result reached the cancelled caller")
                    self.assertTrue(attached)
                    counts = self.session.inspect()
                    for key in ("ownedRefs", "ownedTickets", "ownedLeases", "ownedOperations"):
                        self.assertEqual(counts[key], before[key], key)
                    self.assertEqual((self.cache.ledger.reserved, self.cache.ledger.encoded_reserved), credit)
                    self.assertGreater(baseline.data.nbytes, 0)
                    self.assertGreater(other.data.nbytes, 0)
                    self.assertGreater(control.data.nbytes, 0)
                    self.assertEqual(sibling.inspect()["activeWatches"], 1)
            self.assertEqual(len(saved), 4)
            self.mode = "normal"
            usable = await sibling.baseline()
            usable.close()
        finally:
            if enabled:
                gc.enable()
            await watch.aclose()
            baseline.close()
            other.close()
            await sibling.aclose()

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
