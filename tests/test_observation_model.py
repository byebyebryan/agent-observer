"""Synthetic acceptance of invariant handling, not native runtime coverage."""

import unittest
from dataclasses import replace

from agent_observer.observation_model import (
    Evidence,
    NativeIdentity,
    SessionObservation,
    bounded_native_title,
)


class ObservationInvariantTest(unittest.TestCase):
    def setUp(self):
        self.identity = NativeIdentity("host-a", "codex", "namespace-a", "thread", "native-a")

    def test_liveness_refresh_preserves_work_clock(self):
        work = Evidence("work", "working", 10, "synthetic", "current", "synthetic")
        before = SessionObservation(self.identity, work=work)
        after = before.refresh_presence(
            Evidence("presence", "present", 10000, "synthetic", "current", "synthetic")
        )
        self.assertEqual(after.work.observed_at, 10)
        self.assertIs(after.work, work)
        self.assertEqual(after.presence.observed_at, 10000)

    def test_observation_gap_exposes_unknown_and_retains_original_age(self):
        known = Evidence("work", "needs_input", 20, "synthetic", "current", "synthetic")
        stale = known.invalidate()
        self.assertEqual(stale.effective_value, "unknown")
        self.assertEqual(stale.observed_at, 20)
        self.assertEqual(stale.metadata()["lastKnownValue"], "needs_input")
        self.assertEqual(stale.metadata()["value"], "unknown")

    def test_worker_absence_does_not_end_work(self):
        work = Evidence("work", "needs_input", 20, "synthetic", "current", "synthetic")
        row = SessionObservation(self.identity, work=work).refresh_presence(
            Evidence("presence", "absent", 21, "synthetic", "current", "synthetic")
        )
        self.assertEqual(row.work.effective_value, "needs_input")
        self.assertNotIn("attachment", row.metadata())

    def test_unavailable_evidence_never_becomes_idle(self):
        row = SessionObservation(self.identity)
        self.assertEqual(row.work.metadata()["value"], "unknown")
        self.assertIsNone(row.work.observed_at)
        self.assertEqual(row.presence.metadata()["value"], "unknown")

    def test_host_namespace_provider_and_native_kind_are_identity_scope(self):
        variants = (
            self.identity,
            replace(self.identity, host_scope="host-b"),
            replace(self.identity, namespace="namespace-b"),
            replace(self.identity, provider="claude"),
            replace(self.identity, native_id_kind="session"),
        )
        self.assertEqual(len({identity.key for identity in variants}), len(variants))

    def test_wrong_dimension_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_observation_dimension"):
            SessionObservation(self.identity, work=Evidence("presence"))

    def test_known_value_requires_timestamp_and_source(self):
        with self.assertRaisesRegex(ValueError, "missing_evidence_provenance"):
            Evidence("work", "working")
        with self.assertRaisesRegex(ValueError, "invalid_evidence_time"):
            Evidence("work", "working", True, "synthetic", "current", "synthetic")

    def test_arbitrary_payload_text_is_not_an_evidence_code(self):
        for changes in (
            {"reason": "arbitrary payload text"},
            {"source": "arbitrary payload text"},
        ):
            with self.assertRaisesRegex(ValueError, "invalid_evidence_code"):
                Evidence("work", **changes)

    def test_malformed_types_produce_bounded_codes(self):
        with self.assertRaisesRegex(ValueError, "invalid_evidence_code"):
            Evidence("work", value={})
        with self.assertRaisesRegex(ValueError, "invalid_native_identity"):
            NativeIdentity("host-a", [], "namespace", "thread", "native-a")
        with self.assertRaisesRegex(ValueError, "invalid_observation_dimension"):
            SessionObservation(self.identity, work={})

    def test_native_title_is_bounded_and_controls_are_removed(self):
        self.assertEqual(bounded_native_title(" native\x00title\n", "native-id"), "native title")
        self.assertEqual(bounded_native_title("x" * 1000, "native-id", limit=20), "x" * 20)
        self.assertEqual(bounded_native_title(None, "native-id"), "native-id")
        self.assertEqual(bounded_native_title("\x00\n", "native-id"), "native-id")


if __name__ == "__main__":
    unittest.main()
