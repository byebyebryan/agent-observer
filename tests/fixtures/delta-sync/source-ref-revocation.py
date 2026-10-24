"""Source revocation regression; private generic pin is disclosed test setup."""

import gc
import unittest

import test_sync_owned_source as fixture


@unittest.skipUnless(fixture.HAS_INPUTS, "public input owner unavailable")
class SourceRefRevocationTest(unittest.IsolatedAsyncioTestCase):
    new_cache = fixture.OwnedSourceTest.new_cache
    responses = fixture.OwnedSourceTest.responses

    async def asyncSetUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.errors = []
        await fixture.OwnedSourceTest.asyncSetUp(self)

    async def asyncTearDown(self):
        try:
            await fixture.OwnedSourceTest.asyncTearDown(self)
            for cache in self.caches:
                self.assertEqual((cache.ledger.used, cache.ledger.reserved, cache.ledger.encoded,
                                  cache.ledger.encoded_reserved, cache.ledger.pending_units), (0,) * 5)
            self.assertFalse(gc.isenabled())
        finally:
            if self.enabled:
                gc.enable()

    async def pin_and_close(self, *, inspect=False, receive=False):
        from mesh_plus.sync.inputs import input_bytes

        sibling = self.source.open_session(self.inputs)
        other = await sibling.baseline()
        ref = await self.session.head_after_nonce({"nonce": "b" * 32})
        size = ref.nbytes
        registered = 1
        error_code = None
        reached_end_of_pin_body = False
        try:
            with input_bytes(self.cache, ref) as (raw, _):
                self.assertEqual(len(raw), size)
                if receive:
                    second = await self.session.head_after_nonce({"nonce": "b" * 32})
                    second.close()
                if inspect or receive:
                    registered = self.session.inspect()["ownedRefs"]
                await self.session.aclose()
                self.assertEqual(self.session.inspect()["ownedRefs"], 0)
                self.assertGreaterEqual(self.cache.ledger.encoded_reserved, size)
                # Source close cannot close the shared owner or sibling. The
                # generic pin exit may subsequently reject its own admission.
                with self.inputs.reserve(1):
                    pass
                self.assertGreater(other.data.nbytes, 0)
                raw = None
                reached_end_of_pin_body = True
        except fixture.ProtocolError as error:
            self.errors.append(error)
            error_code = str(error)
        finally:
            await sibling.aclose()
        self.assertTrue(reached_end_of_pin_body, "pin body did not finish before pin-exit rejection")
        self.assertEqual(registered, 1)
        self.assertEqual(error_code, "sync_input_retired")

    async def test_scope_close_revokes_head_without_inspection(self):
        await self.pin_and_close()

    async def test_public_inspect_preserves_head_pin_for_scope_close(self):
        await self.pin_and_close(inspect=True)

    async def test_receive_pruning_preserves_another_head_pin_for_scope_close(self):
        await self.pin_and_close(receive=True)

    async def test_inspection_does_not_abort_a_healthy_pin(self):
        from mesh_plus.sync.inputs import input_bytes

        ref = await self.session.head_after_nonce({"nonce": "b" * 32})
        with input_bytes(self.cache, ref) as (raw, _):
            count = self.session.inspect()["ownedRefs"]
            self.assertGreater(len(raw), 0)
            raw = None
        self.assertEqual(count, 1)
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)

    async def test_retained_terminal_heads_do_not_accumulate_live_history(self):
        from mesh_plus.sync.inputs import input_bytes

        refs = []
        for _ in range(70):
            ref = await self.session.head_after_nonce({"nonce": "b" * 32})
            refs.append(ref)
            with input_bytes(self.cache, ref) as (raw, _):
                self.assertGreater(len(raw), 0)
                raw = None
            self.assertEqual(self.session.inspect()["ownedRefs"], 0)
        self.assertEqual(self.cache.ledger.encoded_reserved, 0)
