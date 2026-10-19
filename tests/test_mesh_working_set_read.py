"""Domain expiry arithmetic over native-admitted frames, not SDK registration.

The host wrapper below supplies translated receipt deadlines directly. It is
not a Mesh proof oracle and these tests do not claim end-to-end Reader admission.
"""

import copy
import unittest
from unittest.mock import patch

import test_mesh_working_set_profile as profile_fixture
import test_working_set_projection as projection_fixture
from mesh_plus.api import descriptor as mesh_descriptor
from mesh_plus.protocol import ProtocolError

from agent_observer.mesh_working_set_profile import WORKING_SET_PROFILE_ID, WorkingSetAgentCodec
from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch, _WorkingSetSelection
from agent_observer.working_set_contract import validate_frame

WALL = projection_fixture.WALL
OFFSET = 100000


def new_fixture():
    original = projection_fixture.fixture()
    original["clockDomain"] = "time:[123]"
    fixture = projection_fixture.WorkingSetProjectionTest()
    with patch.object(projection_fixture, "fixture", return_value=original):
        fixture.setUp()
    return fixture


def context(frame):
    validate_frame(frame)
    state = WorkingSetAgentCodec("fixture", "local", 10000).inspect_native(frame)
    return {
        "protocol": WORKING_SET_PROFILE_ID,
        "sessions": list(state.records),
        "mesh": {"hosts": [{
            "hostId": "fixture", "owner": state.owner,
            "delivery": {"epoch": "fixture-epoch", "status": "ready"},
            "viewState": "current",
            "receipts": [
                {"sourceId": r["sourceId"], "component": r["component"],
                 "accepted": r["accepted"], "health": r["health"],
                 "expiresAtMs": None if r["expiry"] is None else r["expiry"] + OFFSET}
                for r in state.receipts
            ],
        }]},
    }


def selection(frame):
    value = context(frame)
    state = _WorkingSetSelection(10000)
    state.retain(copy.deepcopy(value))
    return state, value


class WorkingSetReadPolicyTest(unittest.TestCase):
    def test_recent_expiry_alone_downgrades_complete_and_never_becomes_negative(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        reader, value = selection(frame)
        member = frame["projection"]["scopes"][0]["members"][0]
        cutoff = member["recent"]["lowerBoottimeMs"] + OFFSET
        before = reader.evaluate(value, cutoff - 1)
        self.assertEqual(len(before.members), 1)
        self.assertEqual(before.scopes[0]["coverage"]["status"], "complete")
        for now in (cutoff, member["recent"]["upperBoottimeMs"] + OFFSET + 1000):
            expired = reader.evaluate(value, now)
            self.assertEqual(expired.members, [])
            self.assertEqual(expired.nonmembers, [])
            self.assertEqual(len(expired.uncertain), 1)
            self.assertEqual(expired.scopes[0]["coverage"]["status"], "partial")

    def test_active_survives_recent_cutoff_and_unknown_age_can_be_complete(self):
        for recent in (True, False):
            frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="running", recent=recent)
            reader, value = selection(frame)
            result = reader.evaluate(value, OFFSET + 20000)
            self.assertEqual(len(result.members), 1)
            self.assertEqual(result.members[0]["runtime"]["value"], "running")
            self.assertEqual(result.scopes[0]["coverage"]["status"], "complete")
            self.assertEqual(result.uncertain, [])

    def test_runtime_expiry_keeps_independent_recent_and_masks_runtime_phase(self):
        fixture = new_fixture()
        original = fixture.sample(runtime="running")
        original["sessions"][0]["kind"] = "unknown"
        fixture.state.attempt("codex", "history")
        fixture.state.accept("codex", "history", original, sampled_ms=10000,
                             ttl_ms=100000, runtime_ttl_ms=2000, accepted_boottime_ms=10001)
        fixture.now = 10501
        runtime = fixture.sample(runtime="running", at=None, wall=WALL + 500)
        runtime["sessions"][0]["kind"] = "unknown"
        fixture.state.attempt("codex", "runtime")
        fixture.state.accept("codex", "runtime", runtime, sampled_ms=10500,
                             ttl_ms=1500, accepted_boottime_ms=10501)
        frame = fixture.state.working_set_frame("status", 1)
        reader, value = selection(frame)
        result = reader.evaluate(value, OFFSET + 12000)
        self.assertEqual(len(result.members), 1)
        row = result.members[0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["activity"]["at"], WALL - 5000)
        self.assertNotEqual(result.scopes[0]["coverage"]["status"], "complete")

    def test_current_kind_required_even_with_an_independent_recent_branch(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        reader, value = selection(frame)
        value["mesh"]["hosts"][0]["receipts"][0]["accepted"] += 1
        result = reader.evaluate(value, OFFSET + 10001)
        self.assertEqual(result.members, [])
        self.assertEqual(result.nonmembers, [])
        self.assertNotEqual(result.scopes[0]["coverage"]["status"], "complete")
        # Same receipt key with a newer accepted counter cannot renew an old ref.
        self.assertEqual(len(result.uncertain), 1)

    def test_only_admitted_quiet_negative_restores_complete_absence_then_expires(self):
        fixture = new_fixture()
        first = fixture.accept()
        reader, _ = selection(first)
        fixture.now = 15002
        negative = fixture.state.working_set_frame("status", 2)
        value = context(negative)
        reader.retain(copy.deepcopy(value))
        result = reader.evaluate(value, OFFSET + 15002)
        self.assertEqual(result.members, [])
        self.assertEqual(len(result.nonmembers), 1)
        self.assertEqual(result.nonmembers[0]["reason"], "outside_window")
        self.assertEqual(result.scopes[0]["coverage"]["status"], "complete")
        expired = reader.evaluate(value, OFFSET + 110000)
        self.assertEqual(expired.nonmembers, [])
        self.assertEqual(expired.scopes[0]["coverage"]["status"], "partial")

    def test_complete_empty_scope_still_requires_census_and_reader_currentness(self):
        fixture = new_fixture()
        sample = fixture.sample()
        sample["sessions"] = []
        frame = fixture.accept(sample)
        reader, value = selection(frame)
        self.assertEqual(reader.evaluate(value, OFFSET + 10001).scopes[0]["coverage"]["status"], "complete")
        result = reader.evaluate(value, OFFSET + 110000)
        self.assertEqual(result.members, [])
        self.assertEqual(result.scopes[0]["coverage"]["status"], "partial")
        reader.clear()
        self.assertEqual(reader.evaluate(value, OFFSET + 110000).scopes, [])

    def test_delivery_failure_revokes_positive_and_negative_but_preserves_context(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        reader, value = selection(frame)
        value["mesh"]["hosts"][0]["delivery"]["status"] = "disconnected"
        result = reader.evaluate(value, OFFSET + 10001)
        self.assertEqual(result.members, [])
        self.assertEqual(result.nonmembers, [])
        self.assertEqual(len(result.uncertain), 1)
        self.assertEqual(result.scopes[0]["coverage"]["status"], "unavailable")
        self.assertIsNotNone(result.context)

    def test_retained_dto_and_context_exports_are_detached(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        reader, value = selection(frame)
        result = reader.evaluate(value, OFFSET + 10001)
        result.members[0]["identity"]["nativeId"] = "mutated"
        result.context["hosts"].clear()
        result.scopes[0]["coverage"]["status"] = "complete"
        again = reader.evaluate(value, OFFSET + 10002)
        self.assertEqual(again.members[0]["identity"], frame["projection"]["sessions"][0]["identity"])
        self.assertEqual(len(again.context["hosts"]), 1)

    def test_window_clock_and_scope_bindings_cannot_be_reinterpreted(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        reader, value = selection(frame)
        for field in ("clockCeiling", "clockGeneration"):
            bad = copy.deepcopy(value)
            bad["mesh"]["hosts"][0]["owner"]["service"][field] -= 1
            with self.subTest(field=field), self.assertRaisesRegex(ProtocolError, "clock_regression"):
                reader.retain(bad)
        bad_scope = copy.deepcopy(value)
        bad_scope["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]["contextGeneration"] += 1
        with self.assertRaisesRegex(ProtocolError, "scope_continuity"):
            reader.retain(bad_scope)
        wrong = _WorkingSetSelection(0)
        with self.assertRaisesRegex(ProtocolError, "policy_binding"):
            wrong.retain(value)
        reader.evaluate(value, OFFSET + 10001)
        with self.assertRaisesRegex(ProtocolError, "clock_regression"):
            reader.evaluate(value, OFFSET + 10000)

    def test_translated_recent_cutoff_is_exclusive_under_receipt_attenuation(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        entry = frame["projection"]["scopes"][0]["members"][0]
        scope = frame["projection"]["scopes"][0]
        ref = scope["supportTable"][entry["fieldSupports"]["activity"]]
        for margin in (0, 1, 200, 4998):
            reader, value = selection(frame)
            for receipt in value["mesh"]["hosts"][0]["receipts"]:
                if receipt["expiresAtMs"] is not None:
                    receipt["expiresAtMs"] -= margin
            translated = ref["expiresBoottimeMs"] + OFFSET - margin
            expected = translated - max(0, ref["expiresBoottimeMs"] - entry["recent"]["lowerBoottimeMs"])
            self.assertEqual(len(reader.evaluate(value, expected - 1).members), 1)
            expired = reader.evaluate(value, expected)
            self.assertEqual(expired.members, [])
            self.assertEqual(expired.nonmembers, [])
            self.assertEqual(expired.scopes[0]["coverage"]["status"], "partial")

    def test_live_facade_setup_remains_gated_by_real_sdk_descriptor(self):
        # No private guard injection or fabricated registered descriptor.
        try:
            mesh_descriptor("agent", profile_id=WORKING_SET_PROFILE_ID)
        except ValueError:
            with self.assertRaises(ValueError):
                PreparedWorkingSetAgentWatch("candidate-request")
        else:
            watch = PreparedWorkingSetAgentWatch("candidate-request")
            watch.disconnect()


class WorkingSetGapPolicyTest(unittest.TestCase):
    """No SDK bypass: native admission plus direct translated-header policy."""

    @staticmethod
    def frames():
        low = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        high = copy.deepcopy(low)
        high["clockCeiling"] += 4000
        high["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] -= 4000
        high["projection"]["scopes"][0]["continuity"] = 3
        low["projection"]["scopes"][0]["continuity"] = 3
        low["sequence"] += 1
        low["viewRevision"] += 1
        validate_frame(high)
        validate_frame(low)
        now = high["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] + OFFSET + 1
        return high, low, now

    def test_gap_cannot_reauthorize_expired_row_with_regressed_native_clock(self):
        high, low, now = self.frames()
        reader, admitted = selection(high)
        expired = reader.evaluate(admitted, now)
        self.assertEqual(expired.members, [])
        self.assertEqual(expired.scopes[0]["coverage"]["status"], "partial")
        reader.retain(None)
        self.assertEqual(reader.evaluate(None, now).members, [])
        self.assertIsNone(reader.snapshot)
        self.assertEqual(reader.rows, {})
        with self.assertRaisesRegex(ProtocolError, "working_set_clock_regression"):
            reader.retain(context(low))

    def test_no_generation_read_keeps_scope_continuity_without_row_history(self):
        high, _, now = self.frames()
        reader, admitted = selection(high)
        reader.evaluate(admitted, now)
        reader.evaluate(None, now)
        older = copy.deepcopy(high)
        older["projection"]["scopes"][0]["continuity"] -= 1
        validate_frame(older)
        self.assertIsNone(reader.snapshot)
        with self.assertRaisesRegex(ProtocolError, "working_set_scope_continuity"):
            reader.retain(context(older))

    def test_reader_time_cannot_regress_during_or_after_gap(self):
        high, _, now = self.frames()
        for restore in (False, True):
            with self.subTest(restore=restore):
                reader, admitted = selection(high)
                reader.evaluate(admitted, now)
                reader.retain(None)
                reader.evaluate(None, now + 1)
                if restore:
                    reader.retain(copy.deepcopy(admitted))
                with self.assertRaisesRegex(ProtocolError, "working_set_reader_clock_regression"):
                    reader.evaluate(admitted if restore else None, now)

    def test_valid_same_incarnation_resync_preserves_expiry_and_bounded_watermarks(self):
        high, _, now = self.frames()
        reader, admitted = selection(high)
        reader.evaluate(admitted, now)
        for step in range(12):
            reader.retain(None)
            unavailable = reader.evaluate(None, now + step)
            self.assertIsNone(unavailable.context)
            self.assertEqual(unavailable.members + unavailable.nonmembers, [])
            reader.retain(copy.deepcopy(admitted))
            resumed = reader.evaluate(admitted, now + step)
            self.assertEqual(resumed.members + resumed.nonmembers, [])
            self.assertEqual(resumed.scopes[0]["coverage"]["status"], "partial")
            self.assertEqual(len(resumed.uncertain), 1)
            self.assertEqual(len(reader.clocks), 1)
            self.assertEqual(len(reader.bindings), 1)

    def test_terminal_clear_releases_watermarks_and_rows(self):
        high, low, now = self.frames()
        reader, admitted = selection(high)
        reader.evaluate(admitted, now)
        reader.clear()
        self.assertEqual(reader.clocks, {})
        self.assertEqual(reader.bindings, {})
        self.assertIsNone(reader.last_now)
        self.assertIsNone(reader.snapshot)
        self.assertEqual(reader.rows, {})
        # A new terminal watch has its own independent baseline/clock. This
        # helper test does not replace those generic Reader admission checks.
        fresh = context(low)
        reader.retain(fresh)
        self.assertEqual(len(reader.evaluate(fresh, now - 1).members), 1)


if __name__ == "__main__":
    unittest.main()
