"""Independent offset oracle and producer integration; no live clock/provider I/O."""

import copy
import unittest
from uuid import UUID

from projection_fixture import provider_snapshot
from test_service_contract import fixture as service_fixture
from test_working_set_decisions import fixture, owner

from agent_observer.service_state import ServiceState
from agent_observer.working_set_clocks import WorkingSetClocks
from agent_observer.working_set_contract import validate_frame
from agent_observer.working_set_policy import DEFAULT_WINDOW_MS


class ClockEnvelopeOracleTest(unittest.TestCase):
    def test_observed_step_sized_envelope_agrees_with_every_possible_mapping(self):
        # The measured boot correction was +561.002ms. Integer worker brackets
        # include their own outward allowance; this is a synthetic 561ms trace,
        # not a reconstruction of the lost incident's actual worker brackets.
        before = fixture(lower_ms=100_000, upper_ms=100_000, wall_ms=1_000_000_000)
        after = fixture(
            sample_number=21,
            lower_ms=100_000,
            upper_ms=100_000,
            wall_ms=1_000_000_561,
        )
        clock = before[3]
        clocks = WorkingSetClocks(clock.service_id, clock.boot_id, clock.clock_domain)
        clocks.accept(clock, component="runtime", accepted=1)
        clocks.accept(after[3], component="runtime", accepted=2)
        self.assertEqual(clocks.generation, 1)
        offsets = range(clocks.floor, clocks.ceiling + 1)

        # Exhaustive independent oracle: classify each individual offset, then
        # require unanimous truth. Future events never establish a negative.
        cases = (
            (age, distance)
            for age in (0, DEFAULT_WINDOW_MS)
            for distance in range(-1000, 1001)
        )
        for age, distance in cases:
            event = after[3].wall_ms - age + distance
            possibilities = {
                "recent"
                if 0 <= age < DEFAULT_WINDOW_MS
                else "old"
                if age >= DEFAULT_WINDOW_MS
                else "future"
                for offset in offsets
                for age in (100_000 - (event - offset),)
            }
            expected = (
                True if possibilities == {"recent"} else False if possibilities == {"old"} else None
            )
            values = fixture(
                sample_number=21,
                runtime_value="parked",
                event_at=event,
                lower_ms=100_000,
                upper_ms=100_000,
                wall_ms=after[3].wall_ms,
            )
            row, fields, source, sample, _ = values
            result = owner().classify(
                row,
                fields,
                source,
                clock=sample,
                clock_generation=1,
                clock_ceiling=clocks.ceiling,
                clock_floor=clocks.floor,
                now_ms=100_000,
                expected_sample_id=sample.sample_id,
            )
            self.assertIs(result.recent.decision, expected, (distance, possibilities))


class ClockRecoveryProducerAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.now = 10_001
        original = service_fixture()
        self.state = ServiceState(
            host_scope="fixture",
            configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000,
            clock=lambda: self.now,
            boot_id=original["bootId"],
            clock_domain="time:[4242]",
            working_set_window_ms=10_000,
        )
        self.number = 100
        self.wall = 1_700_000_020_000

    def sample(self, wall, events):
        value = provider_snapshot("codex")
        self.number += 1
        value.update(collectionId=str(UUID(int=self.number)), collectedAt=wall)
        value["sources"][0]["capabilities"]["activity"] = True
        base = value["sessions"][0]
        value["sessions"] = []
        for number, event in enumerate(events, 1000):
            row = copy.deepcopy(base)
            identifier = str(UUID(int=number))
            row["identity"]["nativeId"] = identifier
            row["nativeIds"].update(threadId=identifier, sessionTreeRootId=identifier)
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
            row["activity"].update(
                at=event, health="current", source="codex_rpc", reason="native_timestamp"
            )
            value["sessions"].append(row)
        return value

    def accept(self, wall, events, lower):
        self.state.attempt("codex", "runtime")
        self.assertTrue(
            self.state.accept(
                "codex",
                "runtime",
                self.sample(wall, events),
                sampled_ms=lower,
                ttl_ms=100_000,
                accepted_boottime_ms=self.now,
            )
        )
        frame = self.state.working_set_frame("status", 1)
        validate_frame(frame)
        return frame

    @staticmethod
    def scope(frame):
        return frame["projection"]["scopes"][0]

    def test_first_native_rows_after_boot_step_are_classifiable(self):
        self.accept(self.wall, [], 10_000)
        self.now = 40_001
        self.accept(self.wall + 30_561, [], 40_000)
        service_id = self.state.service_id
        self.now = 137_001
        wall = self.wall + 127_561
        frame = self.accept(wall, [wall - 5_000, wall - 100_000], 137_000)
        self.assertEqual(frame["clockGeneration"], 1)
        self.assertEqual(frame["serviceId"], service_id)
        self.assertEqual(self.scope(frame)["coverage"]["status"], "complete")
        self.assertEqual(len(self.scope(frame)["members"]), 1)
        self.assertEqual(frame["projection"]["sessions"][0]["activity"]["at"], wall - 5_000)

    def test_silence_reaches_retained_negative_boundary_with_v1_bounds(self):
        event = self.wall - 5_000
        self.accept(self.wall, [event], 10_000)
        self.now = 11_001
        stepped = self.accept(self.wall + 1_561, [event], 11_000)
        branch = self.scope(stepped)["members"][0]["recent"]
        positive_cutoff = branch["lowerBoottimeMs"]
        current_sample_upper = branch["upperBoottimeMs"]
        retained_upper = event + 10_000 - self.state.working_set_clocks.floor
        self.assertLess(current_sample_upper, retained_upper)

        self.now = positive_cutoff
        uncertain = self.state.working_set_frame("status", 2)
        self.assertEqual(self.scope(uncertain)["coverage"]["status"], "partial")
        self.assertEqual(self.scope(uncertain)["members"], [])
        # Current-sample upper alone cannot restore complete negative coverage.
        self.now = current_sample_upper
        still_uncertain = self.state.working_set_frame("status", 3)
        self.assertEqual(self.scope(still_uncertain)["coverage"]["status"], "partial")
        self.assertLessEqual(self.state.working_set_projector.next_deadline_ms, retained_upper)

        self.now = retained_upper
        outside = self.state.working_set_frame("status", 4)
        validate_frame(outside)
        scope = self.scope(outside)
        self.assertEqual(scope["coverage"]["status"], "complete")
        self.assertEqual(scope["members"], [])
        self.assertEqual(len(scope["nonmembers"]), 1)
        self.assertEqual(scope["nonmembers"][0]["recent"]["upperBoottimeMs"], current_sample_upper)
        self.assertEqual(outside["clockGeneration"], 1)
        self.assertEqual(outside["serviceId"], stepped["serviceId"])


if __name__ == "__main__":
    unittest.main()
