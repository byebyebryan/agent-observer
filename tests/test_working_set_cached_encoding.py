"""Cached encoding boundaries for the opt-in working-set projector."""

import copy
import unittest
from unittest.mock import patch
from uuid import UUID

from test_active_projection import provider_snapshot
from test_service_contract import fixture

import agent_observer.working_set_feed as working_set_feed
from agent_observer.contract import ContractError, canonical
from agent_observer.service_state import ServiceState

WALL = 1700000020000


class WorkingSetCachedEncodingTest(unittest.TestCase):
    def setUp(self):
        self.now = 10001
        original = fixture()
        self.state = ServiceState(
            host_scope="fixture",
            configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000,
            clock=lambda: self.now,
            boot_id=original["bootId"],
            clock_domain=original["clockDomain"],
            working_set_window_ms=10000,
        )
        self.counter = 100

    def sample(self):
        value = provider_snapshot("codex")
        self.counter += 1
        value.update(collectionId=str(UUID(int=self.counter)), collectedAt=WALL)
        row = value["sessions"][0]
        row["kind"] = "unknown"
        row["runtime"]["value"] = "parked"
        row["phase"] = None
        row["blockedReasons"] = []
        row["activity"].update(
            at=WALL - 5000,
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        value["sources"][0]["capabilities"]["activity"] = True
        return value

    def accept(self, value=None):
        self.state.attempt("codex", "runtime")
        return self.state.accept(
            "codex",
            "runtime",
            value or self.sample(),
            sampled_ms=10000,
            ttl_ms=100000,
            accepted_boottime_ms=self.now,
        )

    def projector_args(self):
        samples = {
            name: receipt.data["collectionId"]
            for name, receipt in self.state.receipts["codex"].items()
            if receipt.data is not None
        }
        return (
            self.state.snapshot,
            self.state.projection_support,
            self.state.projection_census,
            [self.state.source_meta("codex")],
        ), {
            "observation_revision": self.state.revision,
            "now_ms": self.now,
            "sample_ids": samples,
        }

    def test_public_accept_validates_and_returns_detached_snapshot(self):
        self.accept()
        projector = self.state.working_set_projector
        args, kwargs = self.projector_args()

        returned = projector.accept(*args, **kwargs)
        cached = projector.snapshot()
        self.assertEqual(returned, cached)
        returned["sessions"].clear()
        returned["scopes"].clear()
        self.assertEqual(projector.snapshot(), cached)

        invalid = copy.deepcopy(self.state.snapshot)
        invalid["schemaVersion"] = -1
        revision = projector.revision
        with self.assertRaises(ContractError):
            projector.accept(invalid, *args[1:], **kwargs)
        self.assertEqual(projector.revision, revision)

    def test_owner_refresh_keeps_only_one_success_encoding_and_skips_decode(self):
        projector = self.state.working_set_projector
        original_canonical = working_set_feed.canonical
        serialized_projections = []

        def observe_canonical(value):
            if isinstance(value, dict) and set(value) == {"scopes", "sessions"}:
                serialized_projections.append(value)
            return original_canonical(value)

        with patch.object(
            projector, "snapshot", side_effect=AssertionError("owner refresh decoded cache")
        ) as snapshot, patch.object(
            working_set_feed, "canonical", side_effect=observe_canonical
        ):
            self.assertTrue(self.accept())

        snapshot.assert_not_called()
        self.assertEqual(len(serialized_projections), 1)
        cached = projector.snapshot()
        self.assertEqual(projector._encoded, canonical(cached).encode())
        self.assertEqual(len(cached["sessions"]), 1)

    def test_size_boundary_failure_and_recovery_cache_exact_final_bytes(self):
        self.accept()
        projector = self.state.working_set_projector
        initial = projector.snapshot()
        initial_encoded = canonical(initial).encode()
        revision = projector.revision
        guard_count = projector.decisions.guard_count
        clock_ceiling = self.state.working_set_clocks.ceiling
        args, kwargs = self.projector_args()

        with patch.object(working_set_feed, "MAX_BYTES", len(initial_encoded)):
            inclusive = projector.accept(*args, **kwargs)
        self.assertEqual(inclusive, initial)
        self.assertEqual(projector._encoded, initial_encoded)
        self.assertEqual(projector.revision, revision)

        with patch.object(working_set_feed, "MAX_BYTES", len(initial_encoded) - 1):
            failed = projector.accept(*args, **kwargs)
        failed_scope = failed["scopes"][0]
        self.assertEqual(failed_scope["coverage"]["reason"], "projection_frame_capacity")
        failed_continuity = failed_scope["continuity"]
        failed_encoded = canonical(failed).encode()
        self.assertEqual(projector._encoded, failed_encoded)
        self.assertEqual(projector._ledger, {})
        self.assertEqual(projector.revision, revision + 1)

        recovered = projector.accept(*args, **kwargs)
        self.assertEqual(recovered["scopes"][0]["coverage"]["status"], "complete")
        self.assertEqual(recovered["scopes"][0]["continuity"], failed_continuity + 1)
        self.assertEqual(projector._encoded, canonical(recovered).encode())
        self.assertEqual(projector.revision, revision + 2)
        self.assertEqual(projector.decisions.guard_count, guard_count)
        self.assertEqual(self.state.working_set_clocks.ceiling, clock_ceiling)

    def test_recovery_digit_growth_is_checked_before_continuity_commit(self):
        self.accept()
        projector = self.state.working_set_projector
        candidate_nine = projector.snapshot()
        candidate_nine["scopes"][0]["continuity"] = 9
        candidate_ten = copy.deepcopy(candidate_nine)
        candidate_ten["scopes"][0]["continuity"] = 10
        limit = len(canonical(candidate_nine).encode())
        self.assertEqual(len(canonical(candidate_ten).encode()), limit + 1)

        # Simulate a projector that reached continuity 9 after prior declared
        # failures; the next successful generation would publish 10.
        projector._continuity = 9
        projector._failed = True
        projector._ledger = {}
        guard_count = projector.decisions.guard_count
        clock_ceiling = self.state.working_set_clocks.ceiling
        args, kwargs = self.projector_args()

        with patch.object(working_set_feed, "MAX_BYTES", limit):
            refused = projector.accept(*args, **kwargs)

        scope = refused["scopes"][0]
        self.assertEqual(scope["coverage"]["reason"], "projection_frame_capacity")
        self.assertEqual(scope["continuity"], 9)
        self.assertEqual(projector._continuity, 9)
        self.assertTrue(projector._failed)
        self.assertEqual(projector._ledger, {})
        self.assertEqual(projector._encoded, canonical(refused).encode())
        self.assertEqual(projector.decisions.guard_count, guard_count)
        self.assertEqual(self.state.working_set_clocks.ceiling, clock_ceiling)


if __name__ == "__main__":
    unittest.main()
