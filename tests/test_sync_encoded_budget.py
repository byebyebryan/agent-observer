"""Dual-budget physical canonical-buffer claims and leaf/stage lifetimes."""

import gc
import sys
import tracemalloc
import unittest
import weakref
from unittest.mock import patch

from agent_observer import sync_commitment as sync
from agent_observer import sync_encoded_budget as budget
from agent_observer.sync_encoded import EncodedMap
from agent_observer.sync_encoded_budget import EncodedOwnership


class EncodedOwnershipTest(unittest.TestCase):
    def test_physical_sharing_duplicates_and_independent_equal_buffers(self):
        account = sync.AllocationAccount()
        observations = []
        ledger = None

        def preflight(delta):
            observations.append((ledger.used, delta))

        ledger = EncodedOwnership(account, preflight=preflight)
        first = bytes(bytearray(b"same"))
        second = bytes(bytearray(first))
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        ledger.retain(first, first, second)
        self.assertEqual((ledger.used, ledger.count, ledger.peak), (8, 2, 8))
        self.assertEqual(observations, [(0, 8)])
        self.assertEqual(account._held[id(first)].refs, 1)
        ledger.retain(first, second)
        self.assertEqual(observations, [(0, 8)])
        ledger.release(first, second)
        ledger.release(first)
        self.assertEqual(ledger.used, 8)
        ledger.release(first, second)
        self.assertEqual((ledger.used, ledger.count, ledger.peak), (0, 0, 8))
        ledger.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_external_preflight_runs_before_claim_and_rejection_is_atomic(self):
        account = sync.AllocationAccount()
        ledger = None
        external, total_limit = 10, 20

        def preflight(delta):
            self.assertLessEqual(ledger.used, 10)
            if external + ledger.used + delta > total_limit:
                raise sync.BudgetExceeded("test_external_encoded_limit")

        ledger = EncodedOwnership(account, preflight=preflight)
        first, second = b"first", b"second"
        ledger.retain(first)
        before = account.snapshot()
        with self.assertRaises(sync.BudgetExceeded):
            ledger.retain(first, second)
        self.assertEqual((ledger.used, ledger.count), (5, 1))
        self.assertEqual(account._held[id(first)].encoded_refs, 1)
        self.assertEqual(account.snapshot()["objects"], before["objects"])
        with self.assertRaises(ValueError):
            ledger.release(first, second)
        self.assertEqual(account._held[id(first)].encoded_refs, 1)
        ledger.release(first)
        ledger.close()

    def test_partial_heap_adoption_failure_releases_every_fresh_claim(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        ledger.retain(b"warm-a", b"warm-b")
        ledger.release(b"warm-a", b"warm-b")
        before = account.snapshot()
        acquire = sync.AllocationAccount._acquire
        calls = 0

        def reject(current, size, kind, unique, **kwargs):
            nonlocal calls
            if current is account and kind == "containers" and size == 0:
                calls += 1
                if calls == 2:
                    raise sync.BudgetExceeded("test_partial_claim")
            return acquire(current, size, kind, unique, **kwargs)

        caught = None
        with patch.object(sync.AllocationAccount, "_acquire", new=reject):
            try:
                ledger.retain(b"first-new", b"second-new")
            except sync.BudgetExceeded as error:
                caught = error
        gc.collect()
        self.assertIsNotNone(caught)
        self.assertEqual((ledger.used, ledger.count), (0, 0))
        self.assertEqual(account.snapshot()["used"], before["used"])
        self.assertEqual(account.snapshot()["objects"], before["objects"])
        ledger.close()

    def test_reference_counter_transition_is_charged_and_reclaimed(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffer = b"one physical buffer"
        for _ in range(256):
            ledger.retain(buffer)
        before = account.snapshot()["used"]
        ledger.retain(buffer)
        self.assertEqual(account.snapshot()["used"] - before, sys.getsizeof(257))
        self.assertEqual(ledger.used, len(buffer))
        ledger.release(buffer)
        self.assertEqual(account.snapshot()["used"], before)
        for _ in range(256):
            ledger.release(buffer)
        self.assertEqual((ledger.used, ledger.count), (0, 0))
        ledger.close()

    def test_incremental_claims_do_not_iterate_untouched_buffers(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffers = [str(index).encode() for index in range(2000)]
        for buffer in buffers:
            ledger.retain(buffer)
        extra = b"extra unique buffer"
        with patch.object(sync._IdentityIndex, "__iter__",
                          side_effect=AssertionError("whole heap index scan")):
            ledger.retain(buffers[100])
            ledger.release(buffers[100])
            ledger.retain(extra)
            ledger.release(extra)
            for buffer in buffers:
                ledger.release(buffer)
            ledger.close()

    def test_invalid_calls_and_close_do_not_revoke_live_buffer_claims(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account, limit=4)
        ledger.retain(b"1234")
        with self.assertRaises(sync.BudgetExceeded):
            ledger.retain(b"x")
        with self.assertRaises(ValueError):
            ledger.retain(b"1234", bytearray(b"bad"))
        self.assertEqual(account._held[id(b"1234")].encoded_refs, 1)
        with self.assertRaisesRegex(ValueError, "in_use"):
            ledger.close()
        ledger.release(b"1234")
        ledger.close()
        ledger.close()
        with self.assertRaisesRegex(ValueError, "closed"):
            ledger.retain(b"x")
        with self.assertRaises(ValueError):
            EncodedOwnership(account, limit=32 * 1024 * 1024 + 1)

    def test_stage_and_multiple_roots_share_both_caps_until_final_claim(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        account.encoded_ownership = ledger
        key, old, new = b'"key"', b'{"old":true}', b'{"new":true}'
        ledger.retain(key, old)  # Producer's staged canonical objects.
        table = EncodedMap.from_encoded("bodies", [(key, old)], account=account, trusted=True)
        self.assertEqual(ledger.used, len(key) + len(old))
        self.assertEqual(account._held[id(old)].encoded_refs, 2)
        # Ledger owns one heap claim irrespective of its stage/leaf refcount.
        self.assertEqual(account._held[id(old)].refs, 2)  # Ledger + physical leaf.
        newer = table.put_encoded(key, new, trusted=True)
        self.assertEqual(ledger.used, len(key) + len(old) + len(new))
        self.assertEqual(account._held[id(key)].refs, 3)  # Ledger + two leaves.
        del table
        gc.collect()
        self.assertEqual(ledger.used, len(key) + len(old) + len(new))
        ledger.release(key, old)
        self.assertEqual(ledger.used, len(key) + len(new))
        del newer
        gc.collect()
        self.assertEqual((ledger.used, ledger.count), (0, 0))
        ledger.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_map_capacity_and_heap_rejections_preserve_prior_root_and_ledger(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account, limit=64)
        account.encoded_ownership = ledger
        table = EncodedMap.from_encoded("x", [(b'"key"', b'1')], account=account, trusted=True)
        root, used, count = table.root, ledger.used, ledger.count
        with self.assertRaises(sync.BudgetExceeded):
            table.put_encoded(b'"key"', b'"' + b"x" * 100 + b'"', trusted=True)
        self.assertEqual((table.root, ledger.used, ledger.count), (root, used, count))
        acquire = sync.AllocationAccount._acquire

        def reject(current, size, kind, unique, **kwargs):
            if current is account and kind == "nodes":
                raise sync.BudgetExceeded("test_leaf_heap_limit")
            return acquire(current, size, kind, unique, **kwargs)

        with patch.object(sync.AllocationAccount, "_acquire", new=reject):
            with self.assertRaises(sync.BudgetExceeded):
                table.put_encoded(b'"key"', b'2', trusted=True)
        self.assertEqual((table.root, ledger.used, ledger.count), (root, used, count))
        del table
        gc.collect()
        self.assertEqual(ledger.used, 0)
        ledger.close()

    def test_patch_staging_shares_buffer_claims_and_failed_batch_cleans_up(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        account.encoded_ownership = ledger
        table = EncodedMap.from_encoded("x", [(b'"a"', b'1'), (b'"b"', b'2')],
                                        account=account, trusted=True)
        key, value = b'"new"', b'{"clock":1}'
        ledger.retain(key, value)
        used, count = ledger.used, ledger.count
        newer = table.patch_encoded([("put", key, None, value)], trusted=True)
        self.assertEqual((ledger.used, ledger.count), (used, count))
        ledger.release(key, value)
        before = (ledger.used, ledger.count)
        with self.assertRaises(ValueError):
            table.patch_encoded([("put", b'"bad"', None, b'3'),
                                 ("put", b'"a"', None, b'4')], trusted=True)
        self.assertEqual((ledger.used, ledger.count), before)
        del table, newer
        gc.collect()
        self.assertEqual(ledger.used, 0)
        ledger.close()

    def test_leaf_releases_its_original_ledger_after_configuration_change(self):
        account = sync.AllocationAccount()
        first, second = EncodedOwnership(account), EncodedOwnership(account)
        account.encoded_ownership = first
        table = EncodedMap.from_encoded("x", [(b'"a"', b'1')], account=account, trusted=True)
        account.encoded_ownership = second
        del table
        gc.collect()
        self.assertEqual((first.used, second.used), (0, 0))
        first.close()
        second.close()
        foreign = EncodedOwnership(sync.AllocationAccount())
        account.encoded_ownership = foreign
        with self.assertRaisesRegex(ValueError, "account"):
            EncodedMap.from_encoded("x", [(b'"a"', b'1')], account=account, trusted=True)
        foreign.close()

    def test_owner_callback_cycle_collects_without_unraisable_finalizer_errors(self):
        class Owner:
            def __init__(self):
                self.account = sync.AllocationAccount()
                self.ledger = EncodedOwnership(self.account, preflight=self.preflight)
                self.account.encoded_ownership = self.ledger
                self.table = EncodedMap("x", [("key", {"x": 1})], account=self.account)

            def preflight(self, delta):
                self.assertion = self.ledger.used + delta

        owner = Owner()
        owner_ref, account_ref = weakref.ref(owner), weakref.ref(owner.account)
        errors = []
        with patch.object(sys, "unraisablehook", new=errors.append):
            del owner
            gc.collect()
        self.assertIsNone(owner_ref())
        self.assertIsNone(account_ref())
        self.assertEqual(errors, [])

    def test_real_bookkeeping_peak_is_prepaid_and_batch_preflight_precedes_claim_objects(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffers = [str(index).encode() for index in range(1000)]
        before = account.snapshot()["used"]
        tracemalloc.start()
        try:
            ledger.retain(*buffers)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLessEqual(peak, account.snapshot()["peak"] - before)
        self.assertEqual(ledger.used, sum(map(len, buffers)))
        ledger.release(*buffers)
        ledger.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])
        tiny = sync.AllocationAccount(limit=128 * 1024)
        bounded = EncodedOwnership(tiny)
        with patch.object(budget, "_EncodedBuffer",
                          side_effect=AssertionError("unfunded metadata construction")):
            with self.assertRaises(sync.BudgetExceeded):
                bounded.retain(*buffers)
        self.assertEqual((bounded.used, bounded.count), (0, 0))
        bounded.close()

    def test_released_buffers_leave_no_second_index_or_retained_capacity(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffers = [str(index).encode() for index in range(4000)]
        ledger.retain(b"warm")
        ledger.release(b"warm")
        before = account.snapshot()["used"]
        tracemalloc.start()
        try:
            for buffer in buffers:
                ledger.retain(buffer)
            populated = tracemalloc.get_traced_memory()[0]
            for buffer in buffers:
                ledger.release(buffer)
            empty = tracemalloc.get_traced_memory()[0]
            self.assertEqual(account.snapshot()["used"], before)
            ledger.close()
        finally:
            tracemalloc.stop()
        self.assertFalse(hasattr(ledger, "_claims"))
        self.assertEqual(ledger._extra_bytes, 0)
        self.assertGreater(populated - empty, 4000 * budget._ENCODED_OVERHEAD)
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_forced_cleanup_drops_heap_roots_without_a_retained_index(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffers = [str(index).encode() for index in range(1000)]
        for buffer in buffers:
            ledger.retain(buffer)
        self.assertEqual(ledger.count, 1000)
        ledger._force_close()
        self.assertEqual((ledger.used, ledger.count), (0, 0))
        self.assertFalse(hasattr(ledger, "_claims"))
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_new_buffer_reserves_only_two_extra_metadata_slots(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        buffers = [str(index).encode() for index in range(4000)]
        for buffer in buffers:
            ledger.retain(buffer)
        before = ledger._storage._size
        resize = sync._Lease.resize
        reservations = []

        def observe(lease, size):
            if lease is ledger._storage:
                reservations.append(size)
            return resize(lease, size)

        extra = b"one point insertion"
        with patch.object(sync._Lease, "resize", new=observe):
            ledger.retain(extra)
        self.assertEqual(max(reservations) - before, budget._ENCODED_OVERHEAD)
        self.assertEqual(budget._ENCODED_OVERHEAD, 16)
        ledger.release(extra)
        for buffer in buffers:
            ledger.release(buffer)
        ledger.close()

    def test_final_encoded_release_preserves_an_independent_heap_owner(self):
        account = sync.AllocationAccount()
        buffer = b"independently retained canonical bytes"
        ordinary = account._retain(0, "external", sync._owned_objects((buffer,)))
        ledger = EncodedOwnership(account)
        ledger.retain(buffer)
        self.assertIsInstance(account._held[id(buffer)], budget._EncodedBuffer)
        self.assertEqual(account._held[id(buffer)].refs, 2)
        ledger.release(buffer)
        self.assertIs(type(account._held[id(buffer)]), sync._Held)
        self.assertIs(account._held[id(buffer)].value, buffer)
        self.assertEqual(account._held[id(buffer)].refs, 1)
        self.assertEqual((ledger.used, ledger.count, ledger._extra_bytes), (0, 0, 0))
        ledger.close()
        ordinary.release()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_foreign_ledger_overlap_is_rejected_and_teardown_preserves_other_owners(self):
        account = sync.AllocationAccount()
        first, second = EncodedOwnership(account), EncodedOwnership(account)
        left, right = b"first owner", b"second owner"
        first.retain(left)
        second.retain(right)
        with self.assertRaisesRegex(ValueError, "conflict"):
            second.retain(right, left)
        self.assertEqual(account._held[id(right)].encoded_refs, 1)
        self.assertEqual((first.count, second.count), (1, 1))
        first._force_close()
        self.assertNotIn(id(left), account._held)
        self.assertIs(account._held[id(right)].encoded_owner, second)
        self.assertEqual((second.used, second.count), (len(right), 1))
        second.release(right)
        second.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])


if __name__ == "__main__":
    unittest.main()
