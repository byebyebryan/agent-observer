"""Topology and lifetime checks for the private working-set ledger owner."""

import sys
import unittest
from uuid import UUID

from agent_observer.contract import ContractError
from agent_observer.working_set_ledger import WorkingSetLedger
from agent_observer.working_set_supports import SUPPORT_PLAN_SCRATCH_BYTES, SupportTableBuilder

SERVICE_ID = "00000000-0000-0000-0000-000000000001"
NAMESPACE = "sha256:" + "a" * 64
CONTEXT = ("codex", NAMESPACE, 7)
PREFIX = ("fixture", "codex", NAMESPACE, "thread")


def support(*, accepted=1, sampled=100, expires=1000, component="runtime"):
    return {
        "serviceId": SERVICE_ID,
        "provider": "codex",
        "namespace": NAMESPACE,
        "contextGeneration": CONTEXT[2],
        "component": component,
        "accepted": accepted,
        "sampledBoottimeMs": sampled,
        "expiresBoottimeMs": expires,
    }


def identity(number, prefix=PREFIX):
    return (*prefix, str(UUID(int=number)))


def insert(owner, identity_key, value, *, limit=1024 * 1024, current_charge=None):
    update = owner.plan_put(
        identity_key,
        value,
        current_charge=owner.charge if current_charge is None else current_charge,
        limit=limit,
    )
    return owner.put(update, dict(value))


def unique_graph_charge(owner):
    graph = {id(owner): owner, id(owner.context): owner.context}
    graph.update({
        id(owner._charge): owner._charge,
        id(owner._entry_resize_at): owner._entry_resize_at,
        id(owner._support_resize_at): owner._support_resize_at,
    })
    if owner.prefix is not None:
        graph[id(owner.prefix)] = owner.prefix
        graph.update({id(value): value for value in owner.prefix})
    graph[id(owner._entries)] = owner._entries
    graph[id(owner._supports)] = owner._supports
    for native_id, atom in owner._entries.items():
        graph[id(native_id)] = native_id
        graph[id(atom)] = atom
        graph[id(atom.charge)] = atom.charge
        graph[id(atom.key)] = atom.key
        graph[id(atom.value)] = atom.value
        graph.update({id(value): value for value in atom.key})
        for key, value in atom.value.items():
            graph[id(key)] = key
            graph[id(value)] = value
    for key, record in owner._supports.items():
        graph[id(key)] = key
        graph[id(record)] = record
        graph[id(record[1])] = record[1]
    return sum(sys.getsizeof(value) for value in graph.values())


class WorkingSetLedgerTest(unittest.TestCase):
    def test_owner_charge_covers_scalar_referents_when_empty_and_nonempty(self):
        empty = WorkingSetLedger.empty()
        self.assertGreaterEqual(empty.charge, unique_graph_charge(empty))

        owner = WorkingSetLedger.empty(CONTEXT)
        insert(owner, identity(0), support())
        self.assertGreaterEqual(owner.charge, unique_graph_charge(owner))
        atom = next(iter(owner._entries.values()))
        self.assertGreaterEqual(atom.charge, sys.getsizeof(atom.charge))

    def test_scope_prefix_and_full_identity_are_checked_on_every_join(self):
        owner = WorkingSetLedger.empty(CONTEXT)
        first_identity = identity(1)
        source_native_id = first_identity[4]
        original_support = support()
        insert(owner, first_identity, original_support)

        stored_key = next(iter(owner._entries))
        atom = owner._entries[stored_key]
        self.assertEqual(owner.prefix, PREFIX)
        self.assertTrue(all(left == right for left, right in zip(owner.prefix, PREFIX, strict=True)))
        self.assertIsNot(stored_key, source_native_id)
        for owned, borrowed in zip(owner.prefix, PREFIX, strict=True):
            self.assertIsNot(owned, borrowed)
        self.assertIs(atom.value, owner.get(first_identity)[0])
        self.assertEqual(owner.get(first_identity)[1], original_support["expiresBoottimeMs"])
        self.assertEqual(next(owner.iter_items())[0], first_identity)

        same_native_id_other_host = identity(1, ("other-host", *PREFIX[1:]))
        with self.assertRaisesRegex(ContractError, "ledger_prefix"):
            owner.get(same_native_id_other_host)
        self.assertIsNone(owner.get(identity(2)))
        self.assertEqual(owner.count, 1)

    def test_many_identities_share_one_full_support_map_and_expiry(self):
        owner = WorkingSetLedger.empty(CONTEXT)
        value = support(expires=12345)
        insert(owner, identity(1), value)
        atom = next(iter(owner._entries.values()))
        second_identity = identity(2)
        self.assertIs(owner.support_for(value), atom.value)
        insert(owner, second_identity, value)

        self.assertEqual(owner.count, 2)
        self.assertEqual(owner.support_count, 1)
        self.assertIs(owner._entries[identity(1)[4]], owner._entries[identity(2)[4]])
        self.assertEqual(owner._supports[atom.key][1], 2)
        for _full_identity, mapped_support, horizon in owner.iter_items():
            self.assertIs(mapped_support, atom.value)
            self.assertEqual(horizon, mapped_support["expiresBoottimeMs"])
        self.assertGreaterEqual(owner.charge, unique_graph_charge(owner))

    def test_support_builder_borrows_the_exact_ledger_map_after_member_preflight(self):
        owner = WorkingSetLedger.empty(CONTEXT)
        identity_key = identity(8)
        value = support()
        insert(owner, identity_key, value)
        owned = owner._entries[identity_key[4]].value
        fields = {
            "runtime": value,
            "phase": None,
            "kind": None,
            "savedIdentity": None,
            "activity": None,
            "outcome": None,
            "workspace": None,
            "lastUpdated": None,
            "latestTurn": None,
        }
        member = {
            "identity": {
                "hostScope": PREFIX[0],
                "provider": PREFIX[1],
                "namespace": PREFIX[2],
                "nativeIdKind": PREFIX[3],
                "nativeId": identity_key[4],
            },
            "fieldSupports": fields,
            "active": None,
            "recent": None,
        }
        builder = SupportTableBuilder(limit=1024 * 1024, support_lookup=owner.support_for)
        compact = builder.member(member, current_charge=SUPPORT_PLAN_SCRATCH_BYTES)
        self.assertEqual(compact["fieldSupports"]["runtime"], 0)
        self.assertIs(builder.owned_support(value), owned)
        scope = {
            "coverage": {"supports": []},
            "members": [compact],
            "uncertain": [],
            "nonmembers": [],
        }
        builder.finalize(scope)
        self.assertIs(scope["supportTable"][0], owned)
        self.assertEqual(scope["members"][0]["fieldSupports"]["runtime"], 0)

    def test_old_and_candidate_roots_share_immutable_maps_but_update_independently(self):
        old = WorkingSetLedger.empty(CONTEXT)
        first_identity = identity(11)
        second_identity = identity(12)
        first_support = support(accepted=3, sampled=100, expires=9000)
        insert(old, first_identity, first_support)
        insert(old, second_identity, first_support)
        old_atom = old._entries[first_identity[4]]
        old_key = next(key for key in old._entries if key == first_identity[4])

        self.assertLessEqual(old.clone_upper_charge(), old.charge + 2 * 512)
        candidate = old.clone_live(101)
        candidate_before = candidate.charge
        self.assertIs(candidate._entries[first_identity[4]], old_atom)
        self.assertIs(next(key for key in candidate._entries if key == first_identity[4]), old_key)

        replacement = support(accepted=4, sampled=101, expires=10000)
        combined_charge = old.charge + candidate.charge
        insert(
            candidate,
            first_identity,
            replacement,
            current_charge=combined_charge,
            limit=1024 * 1024 * 1024,
        )
        self.assertIs(old._entries[first_identity[4]], old_atom)
        self.assertIs(candidate._entries[second_identity[4]], old_atom)
        self.assertIsNot(candidate._entries[first_identity[4]], old_atom)
        self.assertEqual(old.support_count, 1)
        self.assertEqual(candidate.support_count, 2)
        self.assertGreaterEqual(candidate.charge, candidate._measure_charge())
        self.assertGreater(candidate.charge, candidate_before)
        candidate.detach_fallback()
        self.assertIsNone(candidate._fallback)

    def test_expiry_retires_only_candidate_atom_and_uses_map_expiry(self):
        old = WorkingSetLedger.empty(CONTEXT)
        entry_identity = identity(21)
        insert(old, entry_identity, support(expires=1000))
        atom = old._entries[entry_identity[4]]

        candidate = old.clone_live(1000)
        self.assertEqual(candidate.count, 0)
        self.assertEqual(candidate.support_count, 0)
        self.assertIs(old._entries[entry_identity[4]], atom)
        self.assertEqual(old.get(entry_identity)[1], 1000)

    def test_invalid_support_and_prefix_reset_never_join_old_native_ids(self):
        old = WorkingSetLedger.empty(CONTEXT)
        entry_identity = identity(31)
        invalid = support()
        invalid["accepted"] = True
        with self.assertRaises(ContractError):
            old.plan_put(entry_identity, invalid)
        self.assertEqual(old.count, 0)

        insert(old, entry_identity, support())
        new_context = ("codex", NAMESPACE, 8)
        reset = WorkingSetLedger.empty(new_context)
        self.assertIsNone(reset.get(entry_identity))
        self.assertEqual(reset.count, 0)
        self.assertEqual(old.count, 1)

    def test_maximum_admitted_prefix_and_safe_integer_support_values(self):
        host = "h" + "x" * 255
        maximum = 2**53 - 1
        owner = WorkingSetLedger.empty(CONTEXT)
        key = identity(32, (host, "codex", NAMESPACE, "thread"))
        value = support(accepted=maximum, sampled=maximum, expires=maximum)
        insert(owner, key, value)

        self.assertEqual(len(owner.prefix[0]), 256)
        self.assertEqual(owner.get(key)[0]["accepted"], maximum)
        unicode_identity = identity(33, (host + "é", "codex", NAMESPACE, "thread"))
        with self.assertRaisesRegex(ContractError, "ledger_identity"):
            owner.plan_put(unicode_identity, value)

    def test_resize_reserves_refuse_before_mutation_through_4096(self):
        owner = WorkingSetLedger.empty(CONTEXT)
        source = support()
        first = identity(1)
        insert(owner, first, source, limit=1024 * 1024 * 1024)
        observed_entry_resizes = 0

        for number in range(2, 4097):
            item = identity(number)
            before_charge = owner.charge
            before_count = owner.count
            before_size = sys.getsizeof(owner._entries)
            plan = owner.plan_put(
                item,
                source,
                current_charge=before_charge,
                limit=1024 * 1024 * 1024,
            )
            with self.assertRaisesRegex(ContractError, "ledger_capacity"):
                owner.plan_put(
                    item,
                    source,
                    current_charge=before_charge,
                    limit=before_charge + plan.peak_additional_bytes - 1,
                )
            self.assertEqual(owner.charge, before_charge)
            self.assertEqual(owner.count, before_count)
            self.assertEqual(sys.getsizeof(owner._entries), before_size)

            owner.put(plan, dict(source))
            self.assertLessEqual(owner.charge - before_charge, plan.peak_additional_bytes)
            after_size = sys.getsizeof(owner._entries)
            if after_size != before_size:
                observed_entry_resizes += 1
                self.assertLessEqual(after_size, 2 * before_size + 512)
                self.assertGreaterEqual(owner.charge, owner._measure_charge())

        self.assertEqual(owner.count, 4096)
        self.assertGreater(observed_entry_resizes, 8)
        self.assertGreaterEqual(owner.charge, unique_graph_charge(owner))
        at_limit_charge = owner.charge
        with self.assertRaisesRegex(ContractError, "ledger_capacity"):
            owner.plan_put(identity(4097), source, current_charge=owner.charge,
                           limit=1024 * 1024 * 1024)
        self.assertEqual(owner.count, 4096)
        self.assertEqual(owner.charge, at_limit_charge)
        # Replacement of an already retained identity remains legal at the
        # cardinality limit when its actual storage preflight succeeds.
        owner.put(owner.plan_put(identity(1), source, current_charge=owner.charge,
                                 limit=1024 * 1024 * 1024), dict(source))
        self.assertEqual(owner.count, 4096)

    def test_support_index_resize_reserves_refuse_before_mutation_through_4096(self):
        owner = WorkingSetLedger.empty(CONTEXT)
        observed_support_resizes = 0
        for number in range(1, 4097):
            item = identity(number)
            value = support(
                accepted=number,
                sampled=number,
                expires=1_000_000 + number,
            )
            before_charge = owner.charge
            before_count = owner.support_count
            before_size = sys.getsizeof(owner._supports)
            plan = owner.plan_put(
                item,
                value,
                current_charge=before_charge,
                limit=1024 * 1024 * 1024,
            )
            with self.assertRaisesRegex(ContractError, "ledger_capacity"):
                owner.plan_put(
                    item,
                    value,
                    current_charge=before_charge,
                    limit=before_charge + plan.peak_additional_bytes - 1,
                )
            self.assertEqual(owner.charge, before_charge)
            self.assertEqual(owner.support_count, before_count)
            self.assertEqual(sys.getsizeof(owner._supports), before_size)

            owner.put(plan, dict(value))
            self.assertLessEqual(owner.charge - before_charge, plan.peak_additional_bytes)
            after_size = sys.getsizeof(owner._supports)
            if after_size != before_size:
                observed_support_resizes += 1
                self.assertLessEqual(after_size, 2 * before_size + 512)
                self.assertGreaterEqual(owner.charge, owner._measure_charge())

        self.assertEqual(owner.count, 4096)
        self.assertEqual(owner.support_count, 4096)
        self.assertGreater(observed_support_resizes, 8)
        self.assertGreaterEqual(owner.charge, unique_graph_charge(owner))


if __name__ == "__main__":
    unittest.main()
