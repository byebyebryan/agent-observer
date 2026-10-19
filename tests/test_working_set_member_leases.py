"""Receiving-clock presentation leases; direct policy fixtures are not SDK proofs."""

import copy
import unittest

import test_mesh_working_set_profile as profile_fixture
from test_mesh_working_set_read import OFFSET, selection


class WorkingSetMemberLeaseTest(unittest.TestCase):
    def test_recent_lease_uses_attenuated_cutoff_and_disappears_at_equality(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="parked")
        scope = frame["projection"]["scopes"][0]
        cutoff = scope["members"][0]["recent"]["lowerBoottimeMs"] + OFFSET - 200
        reader, value = selection(frame)
        for receipt in value["mesh"]["hosts"][0]["receipts"]:
            if receipt["expiresAtMs"] is not None:
                receipt["expiresAtMs"] -= 200
        read = reader.evaluate(value, cutoff - 1)
        lease, = read.member_leases
        self.assertEqual(lease["identity"], read.members[0]["identity"])
        self.assertIsNone(lease["activeExpiresAtMs"])
        self.assertEqual(lease["recentExpiresAtMs"], cutoff)
        self.assertEqual(lease["membershipExpiresAtMs"], cutoff)
        expired = reader.evaluate(value, cutoff)
        self.assertEqual(expired.member_leases, [])
        self.assertEqual(expired.nonmembers, [])
        self.assertEqual(expired.scopes[0]["coverage"]["status"], "partial")

    def test_active_survives_recent_cutoff_without_renewing_its_original_lease(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="running")
        reader, value = selection(frame)
        first, = reader.evaluate(value, OFFSET + 10001).member_leases
        self.assertGreater(first["activeExpiresAtMs"], first["recentExpiresAtMs"])
        later, = reader.evaluate(value, OFFSET + 20000).member_leases
        self.assertIsNone(later["recentExpiresAtMs"])
        self.assertEqual(later["activeExpiresAtMs"], first["activeExpiresAtMs"])
        self.assertEqual(later["membershipExpiresAtMs"], first["membershipExpiresAtMs"])
        self.assertEqual(later["fieldExpiresAtMs"], first["fieldExpiresAtMs"])

    def test_kind_deadline_caps_eligibility_even_when_active_branch_lasts_longer(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="running")
        reader, value = selection(frame)
        kind_ref = value["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]["members"][0]["fieldSupports"]["kind"]
        scope = value["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]
        kind_ref = scope["supportTable"][kind_ref]
        for receipt in value["mesh"]["hosts"][0]["receipts"]:
            if receipt["component"] == kind_ref["component"]:
                receipt["expiresAtMs"] = OFFSET + 11000
        lease, = reader.evaluate(value, OFFSET + 10001).member_leases
        self.assertEqual(lease["membershipExpiresAtMs"], OFFSET + 11000)
        self.assertEqual(lease["fieldExpiresAtMs"]["kind"], OFFSET + 11000)
        self.assertEqual(reader.evaluate(value, OFFSET + 11000).member_leases, [])

    def test_mutating_export_cannot_change_retained_state_or_next_lease(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="running")
        reader, value = selection(frame)
        read = reader.evaluate(value, OFFSET + 10001)
        expected = copy.deepcopy(read.member_leases)
        read.member_leases[0]["identity"]["nativeId"] = "changed"
        read.member_leases[0]["fieldExpiresAtMs"].clear()
        read.member_leases.clear()
        self.assertEqual(reader.evaluate(value, OFFSET + 10002).member_leases, expected)

    def test_delivery_loss_and_terminal_clear_export_no_positive_lease(self):
        frame = profile_fixture.MeshWorkingSetProfileTest.frame(runtime="running")
        reader, value = selection(frame)
        self.assertEqual(len(reader.evaluate(value, OFFSET + 10001).member_leases), 1)
        value["mesh"]["hosts"][0]["delivery"]["status"] = "disconnected"
        self.assertEqual(reader.evaluate(value, OFFSET + 10002).member_leases, [])
        reader.clear()
        self.assertEqual(reader.evaluate(value, OFFSET + 10003).member_leases, [])


if __name__ == "__main__":
    unittest.main()
