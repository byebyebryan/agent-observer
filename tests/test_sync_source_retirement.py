"""Public retirement-query adoption; disclosed private generic pin fixtures."""

import hashlib
import importlib.util
import weakref
from pathlib import Path

from test_sync_source import message_fixture

from agent_observer.contract import ContractError

_PATH = Path(__file__).resolve().parents[1] / "tests/fixtures/delta-sync/source-ref-revocation.py"
_SPEC = importlib.util.spec_from_file_location("owned_ref_regression", _PATH)
overlay = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(overlay)


class OwnerDelegate:
    """Test-owned public protocol wrapper; no generic private-state access."""

    def __init__(self, owner, query):
        self.reserve, self.buffer_heap = owner.reserve, owner.buffer_heap
        self.ref_is_retired = query


class SourceRetirementTest(overlay.SourceRefRevocationTest):
    async def test_missing_capability_rejects_before_source_reservation_or_io(self):
        before = self.source.inspect(), self.cache.ledger.reserved
        for invalid in (None, False, 1, "query", object()):
            wrapper = OwnerDelegate(self.inputs, invalid)

            def forbidden(*_args, **_kwargs):
                raise AssertionError("unsupported owner reserved source state")

            wrapper.reserve = forbidden
            with self.assertRaisesRegex(ContractError, "sync_source_input_owner"):
                self.source.open_session(wrapper)
        self.assertEqual((self.source.inspect(), self.cache.ledger.reserved), before)

    async def test_nonbool_query_fails_intake_and_close_preserves_shared_owner_sibling(self):
        sibling = self.source.open_session(self.inputs)
        keep = await sibling.baseline()
        try:
            for invalid in (None, 0, 1, "false", [], {}):
                wrapper = OwnerDelegate(self.inputs, lambda _ref, value=invalid: value)
                session = self.source.open_session(wrapper)
                ref = await session.head_after_nonce({"nonce": "b" * 32})
                try:
                    for action in (session.inspect,):
                        try:
                            action()
                        except ContractError as error:
                            self.errors.append(error)
                            self.assertEqual(str(error), "sync_source_input_owner")
                        else:
                            self.fail("non-bool query accepted")
                    with self.assertRaisesRegex(ContractError, "sync_source_input_owner"):
                        await session.head_after_nonce({"nonce": "b" * 32})
                    self.assertIs(self.inputs.ref_is_retired(ref), False)
                finally:
                    await session.aclose()
                self.assertIs(self.inputs.ref_is_retired(ref), True)
                self.assertGreater(keep.data.nbytes, 0)
                with self.inputs.reserve(1):
                    pass
        finally:
            await sibling.aclose()

    async def test_captured_query_retires_after_cleanup_and_batch_close_needs_no_query(self):
        query = self.inputs.ref_is_retired
        captured = weakref.ref(query)
        wrapper = OwnerDelegate(self.inputs, query)
        session = self.source.open_session(wrapper)
        query = wrapper.ref_is_retired = None
        await session.head_after_nonce({"nonce": "b" * 32})
        self.assertIsNotNone(captured())
        await session.aclose()
        self.assertIsNone(captured())
        self.assertEqual(session.inspect()["ownedRefs"], 0)

        def forbidden(_ref):
            raise AssertionError("batch close queried unrelated state")

        session = self.source.open_session(OwnerDelegate(self.inputs, forbidden))
        complete = message_fixture("control")
        base = self.baseline["tag"]
        complete.update(baseTag=base, targetTag=base)
        await self.responses([complete])
        batch = await session.changes_with_completion(base, target=base)
        batch.close()
        self.assertEqual(session.inspect()["ownedRefs"], 0)
        await session.aclose()

    async def test_actual_relay_ref_pin_survives_inspect_receive_and_scope_close_revokes(self):
        from mesh_plus.protocol import ProtocolError
        from mesh_plus.sync import SyncBudgets, create_sync_relay, source_binding
        from mesh_plus.sync.budget import AllocationLedger
        from mesh_plus.sync.canonical import canonical
        from mesh_plus.sync.relay_inputs import RelayInputRef, relay_bytes
        from mesh_plus.transport import LineChannel, boottime_ms

        from agent_observer.sync_transport import AgentSyncTransportCodec

        class Capture:
            def __init__(capture, actual):
                capture.actual, capture.inputs, capture.session = actual, None, None

            def open_session(capture, inputs):
                capture.inputs = inputs
                capture.session = capture.actual.open_session(inputs)
                return capture.session

            async def aclose(capture):
                await capture.actual.aclose()

        class Writer:
            transport = None

            def get_write_buffer_limits(writer):
                return (16384, 65536)

            def set_write_buffer_limits(writer, **_kwargs):
                pass

            def get_write_buffer_size(writer):
                return 0

            def write(writer, _value):
                pass

            async def drain(writer):
                pass

            def close(writer):
                pass

            async def wait_closed(writer):
                pass

        writer = Writer()
        writer.transport = writer
        captured = Capture(self.source)
        profile = self.cache.profile
        ledger = AllocationLedger()
        codec = AgentSyncTransportCodec("full", encoding_id="fixture-expanded/1", expected_host="fixture")
        relay = create_sync_relay(captured, profile.descriptor,
                                  source_binding("fixture", "agents", profile.descriptor),
                                  native_codec=codec, budgets=SyncBudgets(), ledger=ledger,
                                  owns_source=False)
        request = {"readerEpoch": "a" * 32, "requestId": "retirement", "catalogRevision": "fixture",
                   "hosts": ["fixture"], "route": "test-sink", "channelEpoch": "c" * 32,
                   "bridgeId": relay.bridge_id, "role": "transport-relay",
                   "encodingDigest": hashlib.sha256(canonical(dict(codec.encoding))).hexdigest()}
        try:
            channel = await relay.open_channel(LineChannel(None, writer, "client"), request,
                                               setup_deadline_ms=boottime_ms() + 15000)
            session, inputs = captured.session, captured.inputs
            sibling = self.source.open_session(inputs)
            keep = await sibling.baseline()
            ref = await session.head_after_nonce({"nonce": "b" * 32})
            self.assertIs(type(ref), RelayInputRef)
            size, reached_end = ref.nbytes, False
            try:
                with relay_bytes(channel, ref) as raw:
                    self.assertEqual(len(raw), size)
                    self.assertEqual(session.inspect()["ownedRefs"], 1)
                    second = await session.head_after_nonce({"nonce": "b" * 32})
                    second.close()
                    self.assertEqual(session.inspect()["ownedRefs"], 1)
                    self.assertIs(inputs.ref_is_retired(ref), False)
                    await session.aclose()
                    self.assertIs(inputs.ref_is_retired(ref), True)
                    self.assertGreaterEqual(ledger.encoded_reserved, size)
                    self.assertGreater(keep.data.nbytes, 0)
                    with inputs.reserve(1):
                        pass
                    raw = None
                    reached_end = True
            except ProtocolError as error:
                self.errors.append(error)
                self.assertEqual(str(error), "sync_input_retired")
            else:
                self.fail("relay pin escaped source-scope revocation")
            finally:
                await sibling.aclose()
            self.assertTrue(reached_end)
        finally:
            await relay.aclose()
            self.assertEqual((ledger.used, ledger.reserved, ledger.encoded,
                              ledger.encoded_reserved, ledger.pending_units,
                              ledger.pending_encoded), (0,) * 6)
