"""Private patch topology/prepayment; actual admission remains independently strict."""

import dataclasses
import gc
import sys
import unittest
from types import SimpleNamespace

from test_mesh_sync_profile import HAS_MESH_SYNC

if HAS_MESH_SYNC:
    from agent_observer import mesh_sync_profile as patch_module
    from agent_observer.observation_support import SUPPORT_FIELDS
    from mesh_plus.sync.canonical import canonical
    from mesh_plus.sync.commitment import ABSENT

    _Patch = patch_module._Patch
    # The before source's private byte markers remain part of its evidence.
    _marker = getattr(patch_module, "_marker", canonical)


def graph_size(*roots):
    """Unique live test-owned containers/scalars/DTOs; excludes context/ledger."""
    seen, pending, size = set(), list(roots), 0
    while pending:
        value = pending.pop()
        if id(value) in seen or value is ABSENT:
            continue
        seen.add(id(value))
        size += sys.getsizeof(value)
        if type(value) is dict:
            pending.extend(value)
            pending.extend(value.values())
        elif type(value) in (tuple, list):
            pending.extend(value)
        elif dataclasses.is_dataclass(value):
            pending.extend(getattr(value, field.name) for field in dataclasses.fields(value))
    return size


class Meter:
    def __init__(self):
        self.used, self.refuse = 0, False

    def charge(self, amount):
        if self.refuse:
            raise ValueError("test_patch_capacity")
        self.used += amount


@unittest.skipUnless(HAS_MESH_SYNC, "optional Mesh sync interface unavailable")
class PatchStorageTest(unittest.TestCase):
    def setUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.budget = Meter()
        empty = SimpleNamespace(get=lambda _key: ABSENT)
        self.patch = _Patch(SimpleNamespace(budget=self.budget, index=lambda _name: empty))

    def tearDown(self):
        self.assertFalse(gc.isenabled())
        if self.enabled:
            gc.enable()

    def test_record_groups_share_exact_ref_and_keep_final_field_writes(self):
        identity = ["fixture", "codex", "default", "thread", "one"]
        for birth in (1, 2):
            ref = [list(identity), ["owner", birth]]
            for field in SUPPORT_FIELDS:
                self.patch.token(ref, field, "a" * 64, _marker(ref))
            self.patch.token([list(identity), ["owner", birth]], "runtime", None, _marker(ref))
            self.patch.token(ref, "runtime", "b" * 64, _marker(ref))
        result = self.patch.result(())
        self.assertEqual(len(self.patch.tokens), 2)
        self.assertEqual(len(result.field_tokens), 2 * len(SUPPORT_FIELDS))
        for offset in (0, len(SUPPORT_FIELDS)):
            fields = result.field_tokens[offset:offset + len(SUPPORT_FIELDS)]
            self.assertTrue(all(item.record_ref is fields[0].record_ref for item in fields))
            self.assertEqual(next(item.token for item in fields if item.field == "runtime"), "b" * 64)

    def test_markers_keep_key_types_without_retained_encoded_buffers(self):
        ref = [["fixture", "codex", "default", "thread", "one"], ["owner", 1]]
        self.patch.put("row_rules", ref, 42)
        self.patch.token(ref, "runtime", "a" * 64, _marker(ref))
        pending = [self.patch.values, self.patch.tokens]
        while pending:
            value = pending.pop()
            self.assertNotIsInstance(value, (bytes, bytearray, memoryview))
            if type(value) is dict:
                pending.extend(value)
                pending.extend(value.values())
            elif type(value) in (tuple, list):
                pending.extend(value)
        self.assertNotEqual(_marker([1]), _marker(["1"]))
        self.assertNotEqual(_marker(["1"]), _marker([["1"]]))
        for invalid in (True, {"one": 1}, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                _marker([invalid])

    def test_repeated_counter_puts_keep_one_slot_and_high_water_overlap_credit(self):
        first_key = ["codex", "default"]
        self.patch.put("scope_stats", first_key, {"records": 1})
        self.patch.put("scope_stats", list(first_key), {"records": 2})
        overlap_charge = self.budget.used
        previous = None
        for count in range(3, 4001):
            previous = self.patch.get("scope_stats", first_key)
            self.patch.put("scope_stats", list(first_key), {"records": count})
            self.assertGreaterEqual(self.budget.used, graph_size(self.patch.values, previous))
        self.assertEqual(len(self.patch.values), 1)
        self.assertEqual(self.budget.used, overlap_charge)
        self.assertIs(next(iter(self.patch.values.values()))[0], first_key)
        self.patch.remove("scope_stats", first_key)
        self.assertIs(self.patch.get("scope_stats", first_key), ABSENT)
        self.assertEqual(self.budget.used, overlap_charge)
        self.patch.put("scope_stats", first_key, {"records": 4, "members": 2})
        result = self.patch.result(())
        self.assertEqual(len(result.writes), 1)
        self.assertFalse(result.removes)
        self.assertEqual(result.writes[0].value, {"records": 4, "members": 2})
        self.assertGreaterEqual(self.budget.used, graph_size(self.patch.values, self.patch.tokens, result, previous))

    def test_refusal_precedes_stored_value_or_token_replacement(self):
        key = ["codex", "default"]
        self.patch.put("scope_stats", key, {"records": 1})
        ref = [["fixture", "codex", "default", "thread", "one"], ["owner", 1]]
        self.patch.token(ref, "runtime", "a" * 64, _marker(ref))
        self.budget.refuse = True
        with self.assertRaisesRegex(ValueError, "test_patch_capacity"):
            self.patch.put("scope_stats", key, {"records": 1, "members": 2, "uncertain": 3})
        self.assertEqual(self.patch.get("scope_stats", key), {"records": 1})
        with self.assertRaisesRegex(ValueError, "test_patch_capacity"):
            self.patch.token(ref, "activity", "b" * 64, _marker(ref))
        self.budget.refuse = False
        result = self.patch.result(())
        self.assertEqual(len(result.field_tokens), 1)
        self.assertEqual(result.field_tokens[0].field, "runtime")
        self.assertEqual(result.field_tokens[0].token, "a" * 64)

    def test_normal_scales_reserve_more_than_unique_live_patch_graph(self):
        for rows in (100, 500, 2000):
            with self.subTest(rows=rows):
                self.budget = Meter()
                empty = SimpleNamespace(get=lambda _key: ABSENT)
                self.patch = _Patch(SimpleNamespace(budget=self.budget, index=lambda _name: empty))
                for number in range(rows):
                    ref = [["fixture", "codex", "default", "thread", str(number)], ["owner", 1]]
                    marker = _marker(ref)
                    self.patch.put("aliases", number + 1, ref)
                    self.patch.put("row_rules", ref, 42)
                    self.patch.put("order", [0, [part.encode().decode() for part in ref[0]]], ref)
                    for field in SUPPORT_FIELDS:
                        self.patch.token(ref, field, f"{number:064x}", marker)
                    if number + 1 in (1, 2, 5, 8, 16, 100, 500, 2000):
                        # Include extra complete dictionary copies for resize
                        # overlap, independently of the final result credit.
                        self.assertGreaterEqual(
                            self.budget.used, graph_size(self.patch.values, self.patch.tokens)
                            + 2 * sys.getsizeof(self.patch.values) + 2 * sys.getsizeof(self.patch.tokens))
                result = self.patch.result(())
                self.assertEqual(len(self.patch.tokens), rows)
                self.assertEqual(len(result.field_tokens), rows * len(SUPPORT_FIELDS))
                self.assertGreaterEqual(self.budget.used, graph_size(self.patch.values, self.patch.tokens, result))
                result = None
