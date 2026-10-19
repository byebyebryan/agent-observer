"""Strict, lossless and bounded frame-local FactSupport table behavior."""

import copy
import sys
import tracemalloc
import unittest
from types import MappingProxyType
from unittest.mock import patch

from test_active_contract import support
from test_working_set_contract import expand_scope, fixture

from agent_observer.contract import ContractError, canonical
from agent_observer.working_set_contract import validate_frame
from agent_observer.working_set_supports import (
    MAX_SUPPORT_INDEX,
    MAX_SUPPORT_TABLE,
    SUPPORT_PLAN_SCRATCH_BYTES,
    SupportTableBuilder,
    compact_scope,
    resolve_member,
)


def _frame(*, recent=True):
    return fixture(recent=recent)


def _support_value(index):
    return {
        "serviceId": "00000000-0000-0000-0000-000000000001",
        "provider": "codex",
        "namespace": "sha256:" + "a" * 64,
        "contextGeneration": 2**53 - 1,
        "component": "runtime" if index % 2 else "history",
        "accepted": index + 1,
        "sampledBoottimeMs": index,
        "expiresBoottimeMs": 2**53 - 1,
    }


def _graph_size(value, seen=None):
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    total = sys.getsizeof(value)
    if isinstance(value, dict):
        total += sum(_graph_size(key, seen) + _graph_size(item, seen) for key, item in value.items())
    elif isinstance(value, (list, tuple)):
        total += sum(_graph_size(item, seen) for item in value)
    return total


class WorkingSetSupportTableTest(unittest.TestCase):
    def test_whole_maps_are_unique_sorted_and_index_zero_resolves_by_scope(self):
        frame = _frame()
        scope = frame["projection"]["scopes"][0]
        member = scope["members"][0]
        self.assertEqual(len(scope["supportTable"]), 1)
        self.assertEqual(member["fieldSupports"]["runtime"], 0)
        resolved = resolve_member(scope, member)
        self.assertIs(resolved["fieldSupports"]["runtime"], scope["supportTable"][0])
        self.assertEqual(
            [canonical(item).encode("utf-8") for item in scope["supportTable"]],
            sorted(canonical(item).encode("utf-8") for item in scope["supportTable"]),
        )
        validate_frame(frame)

    def test_same_partial_identity_with_different_expiry_remains_two_whole_maps(self):
        scope = expand_scope(_frame()["projection"]["scopes"][0])
        member = scope["members"][0]
        active_support = member["fieldSupports"]["runtime"]
        altered = copy.deepcopy(active_support)
        altered["expiresBoottimeMs"] += 1
        member["fieldSupports"]["outcome"] = altered
        compact = compact_scope(scope)
        self.assertEqual(len(compact["supportTable"]), 2)
        refs = compact["members"][0]["fieldSupports"]
        self.assertNotEqual(refs["runtime"], refs["outcome"])
        self.assertNotEqual(
            compact["supportTable"][refs["runtime"]], compact["supportTable"][refs["outcome"]]
        )

    def test_historical_uncertain_maps_and_two_current_component_receipts_survive(self):
        frame = _frame(recent=True)
        scope = expand_scope(frame["projection"]["scopes"][0])
        historical = support(frame)
        historical.update(
            component="history",
            contextGeneration=scope["contextGeneration"] - 1,
            sampledBoottimeMs=1000,
            expiresBoottimeMs=14000,
        )
        old_identity = copy.deepcopy(scope["members"][0]["identity"])
        old_identity["nativeId"] = "00000000-0000-0000-0000-000000000099"
        scope["uncertain"].append(
            {
                "identity": old_identity,
                "reason": "activity_unresolved",
                "priorSupport": historical,
                "support": support(frame),
                "horizonBoottimeMs": historical["expiresBoottimeMs"],
            }
        )
        scope["coverage"].update(status="partial", supports=[])
        compact = compact_scope(scope)
        frame["projection"]["scopes"][0] = compact
        validate_frame(frame)
        self.assertIn(
            historical,
            compact["supportTable"],
        )
        self.assertEqual(len(compact["supportTable"]), 2)
        uncertain = compact["uncertain"][0]
        self.assertEqual(
            compact["supportTable"][uncertain["priorSupport"]]["contextGeneration"], 0
        )

    def test_index_type_and_local_range_are_strict_without_map_fallback(self):
        original = _frame()
        scope = original["projection"]["scopes"][0]
        path = ("members", 0, "fieldSupports", "activity")
        for invalid in (True, 0.0, -1, len(scope["supportTable"]), MAX_SUPPORT_INDEX + 1):
            bad = copy.deepcopy(original)
            bad_scope = bad["projection"]["scopes"][0]
            bad_scope[path[0]][path[1]][path[2]][path[3]] = invalid
            with self.subTest(reference=invalid), self.assertRaises(ContractError):
                validate_frame(bad)

        bad = copy.deepcopy(original)
        bad_scope = bad["projection"]["scopes"][0]
        bad_scope["members"][0]["fieldSupports"]["activity"] = copy.deepcopy(
            bad_scope["supportTable"][0]
        )
        with self.assertRaises(ContractError):
            validate_frame(bad)

        bad = copy.deepcopy(original)
        del bad["projection"]["scopes"][0]["supportTable"]
        with self.assertRaises(ContractError):
            validate_frame(bad)

    def test_duplicate_unsorted_and_unreferenced_table_entries_are_rejected(self):
        original = _frame()
        duplicate = copy.deepcopy(original)
        table = duplicate["projection"]["scopes"][0]["supportTable"]
        table.append(copy.deepcopy(table[0]))
        with self.assertRaisesRegex(ContractError, "support_table_order"):
            validate_frame(duplicate)

        unsorted = copy.deepcopy(original)
        scope = unsorted["projection"]["scopes"][0]
        extra = copy.deepcopy(scope["supportTable"][0])
        extra["expiresBoottimeMs"] += 1
        table = [*scope["supportTable"], extra]
        table.sort(key=lambda item: canonical(item).encode("utf-8"))
        scope["supportTable"] = list(reversed(table))
        with self.assertRaisesRegex(ContractError, "support_table_order"):
            validate_frame(unsorted)

        unused = copy.deepcopy(original)
        scope = unused["projection"]["scopes"][0]
        extra = copy.deepcopy(scope["supportTable"][0])
        extra["expiresBoottimeMs"] += 1
        scope["supportTable"] = sorted(
            [*scope["supportTable"], extra],
            key=lambda item: canonical(item).encode("utf-8"),
        )
        with self.assertRaisesRegex(ContractError, "support_table_unused"):
            validate_frame(unused)

    def test_builder_refusal_precedes_owned_map_and_table_growth(self):
        scope = expand_scope(_frame()["projection"]["scopes"][0])
        original = copy.deepcopy(scope["members"][0])
        builder = SupportTableBuilder(limit=32)
        with patch("agent_observer.working_set_supports._owned_support") as own:
            with self.assertRaisesRegex(ContractError, "support_capacity"):
                builder.member(
                    scope["members"][0],
                    current_charge=32,
                )
            own.assert_not_called()
        self.assertEqual(builder._table, [])
        self.assertEqual(builder._keys, [])
        self.assertEqual(builder.references, 0)
        self.assertEqual(scope["members"][0], original)

    def test_maximum_current_entry_scratch_fits_the_reserved_topology(self):
        supports = [_support_value(index) for index in range(13)]
        field_names = (
            "runtime",
            "phase",
            "kind",
            "savedIdentity",
            "activity",
            "outcome",
            "workspace",
            "lastUpdated",
            "latestTurn",
        )
        member = {
            "identity": {
                "hostScope": "fixture",
                "provider": "codex",
                "namespace": supports[0]["namespace"],
                "nativeIdKind": "thread",
                "nativeId": "00000000-0000-0000-0000-000000000099",
            },
            "fieldSupports": MappingProxyType(
                dict(
                    zip(
                        field_names,
                        (MappingProxyType(item) for item in supports[:9]),
                        strict=True,
                    )
                )
            ),
            "active": MappingProxyType(
                {"supports": tuple(MappingProxyType(item) for item in supports[9:11])}
            ),
            "recent": MappingProxyType(
                {"supports": tuple(MappingProxyType(item) for item in supports[11:13])}
            ),
        }
        builder = SupportTableBuilder(limit=1024 * 1024)
        tracemalloc.start()
        compact = builder.member(member, current_charge=SUPPORT_PLAN_SCRATCH_BYTES)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(len(compact["fieldSupports"]), 9)
        self.assertEqual(builder.references, 13)
        self.assertLessEqual(peak - current, SUPPORT_PLAN_SCRATCH_BYTES)
        self.assertGreater(builder.preflight_charge, SUPPORT_PLAN_SCRATCH_BYTES)

    def test_table_resize_and_final_remap_stay_below_prepaid_topology(self):
        builder = SupportTableBuilder(limit=16 * 1024 * 1024)
        uncertain = []
        current_charge = SUPPORT_PLAN_SCRATCH_BYTES
        for index in range(640):
            entry = {
                "identity": {
                    "hostScope": "fixture",
                    "provider": "codex",
                    "namespace": "sha256:" + "a" * 64,
                    "nativeIdKind": "thread",
                    "nativeId": f"00000000-0000-0000-0000-{index:012x}",
                },
                "reason": "activity_unresolved",
                "priorSupport": _support_value(2 * index),
                "support": _support_value(2 * index + 1),
                "horizonBoottimeMs": 2**53 - 1,
            }
            compact = builder.uncertain(entry, current_charge=current_charge)
            current_charge += len(canonical(compact).encode("utf-8"))
            uncertain.append(compact)
        self.assertGreaterEqual(len(builder._table), 1024)
        self.assertGreater(sys.getsizeof(builder._indices), 20000)
        self.assertGreaterEqual(
            builder.overhead_charge,
            _graph_size((builder._keys, builder._table, builder._indices)),
        )
        scope = {
            "coverage": {"supports": []},
            "members": [],
            "uncertain": uncertain,
            "nonmembers": [],
        }
        table_count = len(builder._table)
        preflight_delta = builder.preflight_charge - builder.overhead_charge
        tracemalloc.start()
        before, _ = tracemalloc.get_traced_memory()
        builder.finalize(scope)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(len(scope["supportTable"]), table_count)
        self.assertLessEqual(peak - before, preflight_delta + SUPPORT_PLAN_SCRATCH_BYTES)

    def test_static_ceiling_accounts_for_two_historical_slots_per_identity(self):
        self.assertEqual(MAX_SUPPORT_TABLE, 2 * 4096 + 2)
        self.assertEqual(MAX_SUPPORT_INDEX, 8193)


if __name__ == "__main__":
    unittest.main()
