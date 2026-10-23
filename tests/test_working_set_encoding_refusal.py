"""Bounded working-set encoding refusal and recovery behavior."""

import unittest
from unittest.mock import patch

from test_working_set_delivery import wire

from agent_observer.service_runtime import Runtime
from agent_observer.working_set_contract import StreamGuard


class WorkingSetEncodingRefusalTest(unittest.TestCase):
    def setUp(self):
        from test_working_set_delivery import WorkingSetDeliveryTest

        self.fixture = WorkingSetDeliveryTest()
        self.fixture.setUp()
        self.state = self.fixture.state
        self.runtime = None

    def tearDown(self):
        if self.runtime is not None:
            self.runtime.selector.close()

    def _runtime(self):
        self.runtime = Runtime(self.state, "/unused/working-set.sock", collect=False)
        return self.runtime

    def _accept(self, generation):
        self.fixture.now += 1
        self.fixture.accept(generation=generation)

    def _exact_boundary_refusal(self, runtime, calls):
        def reserve(additional_bytes):
            # Test-only placement at the exact currently retained budget. The
            # normal runtime limit is unchanged outside this refusal fixture.
            retained = runtime.encoded_bytes()
            runtime.encoded_limit = retained
            calls.append((additional_bytes, retained))
            return runtime._reserve_working_set(additional_bytes)

        self.state.working_set_reserver = reserve

    def test_first_refusal_allocates_no_buffer_and_leaves_legacy_reads_available(self):
        runtime = self._runtime()
        calls = []
        self._exact_boundary_refusal(runtime, calls)

        # The active owner is refreshed by native publication, then the
        # working-set stage reservation fails before its projector can encode.
        with patch(
            "agent_observer.working_set_feed.canonical",
            side_effect=AssertionError("refusal must not encode a replacement"),
        ):
            self._accept(1)

        projector = self.state.working_set_projector
        self.assertEqual(len(calls), 1)
        self.assertIsNone(projector._encoded)
        self.assertTrue(projector._capacity_blocked)
        self.assertIsNone(projector.snapshot())
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        self.assertEqual(self.state.working_set_retained_buffers(), ())
        self.assertIsNone(self.state._sync_projector)
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")
        self.assertEqual(self.state.receipts["codex"]["runtime"].accepted, 1)

        error = self.state.working_set_frame("view", 1)
        self.assertEqual(error["kind"], "error")
        self.assertEqual(error["reason"], "projection_encoding_capacity")
        self.assertIsNone(error["projection"])

        full = self.state.frame("status", 1)
        self.assertEqual(full["kind"], "status")
        self.assertEqual(len(full["snapshot"]["sessions"]), 1)
        self.assertFalse(hasattr(self.state, "active_frame"))

    def test_refused_first_stage_cannot_increase_saturated_encoded_counter(self):
        runtime = self._runtime()
        calls = []
        self._exact_boundary_refusal(runtime, calls)
        # No encoder hook: the real byte counter must stay within the fixture's
        # saturated limit after acceptance returns through the refusal path.
        self._accept(1)
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        self.assertEqual(runtime.encoded_bytes(), calls[0][1])
        self.assertEqual(self.state.receipts["codex"]["runtime"].accepted, 1)
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")
        self.assertIsNone(self.state.working_set_projector.snapshot())

    def test_retained_owner_buffer_blocks_reads_until_new_generation_reserves(self):
        self._accept(1)
        projector = self.state.working_set_projector
        old_encoded = projector._encoded
        self.assertIsNotNone(old_encoded)
        self.assertEqual(len(projector.decisions._guards), 1)

        runtime = self._runtime()
        calls = []
        captured = []

        def refuse_at_exact_boundary(additional_bytes):
            captured.append((
                self.state.working_set_clocks.ceiling,
                self.state.working_set_clocks.generation,
                dict(projector.decisions._guards),
                projector._context,
                projector.decisions._context,
            ))
            retained = runtime.encoded_bytes()
            runtime.encoded_limit = retained
            calls.append((additional_bytes, retained))
            return runtime._reserve_working_set(additional_bytes)

        self.state.working_set_reserver = refuse_at_exact_boundary
        guard = StreamGuard(expected_host="fixture", expected_uid=self.state.uid,
                            expected_window_ms=10000)
        first = guard.parse(wire(self.state.working_set_frame("status", 1)))
        self.assertEqual(len(first["projection"]["sessions"]), 1)

        with patch(
            "agent_observer.working_set_feed.canonical",
            side_effect=AssertionError("refusal must not encode a replacement"),
        ):
            self._accept(2)
        self.assertEqual(len(calls), 1)
        self.assertTrue(projector._capacity_blocked)
        self.assertIs(projector._encoded, old_encoded)
        self.assertIsNone(projector.snapshot())
        self.assertIn(old_encoded, self.state.working_set_retained_buffers())
        self.assertEqual(runtime.encoded_bytes(), calls[-1][1])
        self.assertEqual(
            captured[-1],
            (
                self.state.working_set_clocks.ceiling,
                self.state.working_set_clocks.generation,
                dict(projector.decisions._guards),
                projector._context,
                projector.decisions._context,
            ),
        )
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        error = guard.parse(wire(self.state.working_set_frame("status", 2)))
        self.assertEqual((error["kind"], error["reason"], error["projection"]),
                         ("error", "projection_encoding_capacity", None))

        # An unrelated publish of the same receipts must not retry the
        # reservation or replace the prior owner buffer.
        self.state.fail("codex", "history", "collection_failed")
        self.assertEqual(len(calls), 1)
        repeated = guard.parse(wire(self.state.working_set_frame("view", 3)))
        self.assertEqual((repeated["kind"], repeated["projection"]), ("error", None))
        self.assertIs(projector._encoded, old_encoded)

        # A newly accepted generation may retry, but another refusal still
        # retains exactly the prior bytes and keeps K/guard authority intact.
        before_view_revision = projector.revision
        with patch(
            "agent_observer.working_set_feed.canonical",
            side_effect=AssertionError("repeated refusal must not encode a replacement"),
        ):
            self._accept(3)
        self.assertEqual(len(calls), 2)
        self.assertIs(projector._encoded, old_encoded)
        self.assertEqual(projector.revision, before_view_revision)
        self.assertEqual(
            captured[-1],
            (
                self.state.working_set_clocks.ceiling,
                self.state.working_set_clocks.generation,
                dict(projector.decisions._guards),
                projector._context,
                projector.decisions._context,
            ),
        )
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        third_error = guard.parse(wire(self.state.working_set_frame("status", 4)))
        self.assertEqual((third_error["kind"], third_error["projection"]), ("error", None))

        # Restoring the runtime budget does not itself retry. The next accepted
        # sample is the admission edge that can reserve and commit recovery.
        runtime.encoded_limit = 64 * 1024 * 1024
        self.state.working_set_reserver = runtime._reserve_working_set
        self.state.fail("codex", "history", "collection_failed")
        self.assertTrue(projector._capacity_blocked)
        self._accept(4)

        self.assertFalse(projector._capacity_blocked)
        recovered = guard.parse(wire(self.state.working_set_frame("status", 5)))
        self.assertEqual(recovered["kind"], "status")
        self.assertEqual(len(recovered["projection"]["sessions"]), 1)
        self.assertGreater(recovered["viewRevision"], third_error["viewRevision"])
        self.assertGreater(
            recovered["projection"]["scopes"][0]["continuity"],
            first["projection"]["scopes"][0]["continuity"],
        )
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")


if __name__ == "__main__":
    unittest.main()
