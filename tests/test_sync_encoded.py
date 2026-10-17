"""Encoded-only Patricia parity, detached queries and allocation diagnostics."""

import copy
import gc
import json
import random
import statistics
import sys
import time
import tracemalloc
import unittest
import weakref
from unittest.mock import patch

from test_sync_commitment import reference_root

from agent_observer import sync_commitment as sync
from agent_observer import sync_encoded as encoded
from agent_observer.sync_encoded_budget import EncodedOwnership


def _wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


class EncodedMapTest(unittest.TestCase):
    def test_gc_disabled_replay_and_rejection_reclaim_roots_and_account(self):
        enabled = gc.isenabled()
        gc.collect()
        gc.disable()
        try:
            for tracked in (False, True):
                account = sync.AllocationAccount()
                reference = weakref.ref(account)
                ledger = EncodedOwnership(account) if tracked else None
                if ledger is not None:
                    account.encoded_ownership = ledger
                values = {str(i): {"v": [i, None]} for i in range(32)}
                current = encoded.EncodedMap("records", values.items(), account=account)
                previous = None
                for generation in range(16):
                    key = str(generation % 32)
                    value = {"v": [generation + 100, "é"]}
                    prior = current.root
                    newer = current.patch([("put", key, current.get_hash(key), value)])
                    self.assertEqual(current.root, prior)
                    previous, current = current, newer
                    values[key] = value
                    self.assertEqual(current.root, reference_root("records", values.items()))
                    before = account.snapshot()
                    with self.assertRaises(ValueError):
                        current.patch([("put", key, None, {"wrong": True})])
                    self.assertEqual(account.snapshot()["objects"], before["objects"])
                    self.assertEqual(account.snapshot()["allocations"], before["allocations"])
                del previous, current, newer
                if ledger is not None:
                    self.assertEqual((ledger.used, ledger.count), (0, 0))
                    ledger.close()
                snapshot = account.snapshot()
                self.assertEqual((snapshot["allocations"], snapshot["objects"]), (0, 0))
                self.assertEqual(snapshot["used"], snapshot["base"])
                del ledger, account
                self.assertIsNone(reference())
        finally:
            if enabled:
                gc.enable()

    def test_baseline_exact_oracle_and_detached_exports(self):
        rows = [(["host", "codex", "ns", "thread", str(index)], value)
                for index, value in enumerate((None, True, 1, {"é": [False, None, "漢🙂"]}, {}))]
        table = encoded.EncodedMap("bodies", rows)
        legacy = sync.PersistentMap("bodies", rows)
        self.assertEqual(table.root, reference_root("bodies", rows))
        self.assertEqual(table.root, legacy.root)
        self.assertEqual(table.encoded_size, len(_wire(list(table.items()))))
        self.assertEqual(table.count, len(rows))
        self.assertEqual(list(table.encoded_items()), list(legacy.encoded_items()))
        key, value, digest, key_bytes, value_bytes = table.lookup_entry(rows[3][0])
        self.assertEqual(digest, sync.value_hash("bodies", value))
        self.assertEqual(key_bytes, _wire(key))
        self.assertEqual(value_bytes, _wire(value))
        key.append("caller")
        value["é"].append("caller")
        rows[3][1]["é"].append("input mutation")
        self.assertEqual(table.get(rows[3][0]), {"é": [False, None, "漢🙂"]})
        exported = list(table.items())
        exported[0][0].append("caller")
        self.assertEqual(table.count, 5)
        self.assertIs(table.get("absent"), sync.ABSENT)
        self.assertIsNone(table.lookup_entry("absent", None))

    def test_strict_raw_json_and_strict_encoded_canonical_admission(self):
        cycle = []
        cycle.append(cycle)
        for invalid in (1.5, float("nan"), {1: "key"}, "\ud800", cycle, object()):
            with self.subTest(invalid=type(invalid)):
                with self.assertRaises(ValueError):
                    encoded.EncodedMap("x", [("key", invalid)])
        for raw in (b' {"x":1}', b'{"b":1,"a":2}', b'{"x":1,"x":1}',
                    b'1.0', b'NaN', b'"\\ud800"', b'"\xff"', b'01', b'true false',
                    b'"\\u0061"', b'[1, 2]'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    encoded.EncodedMap.from_encoded("x", [(b'"key"', raw)])
        table = encoded.EncodedMap.from_encoded("x", [(b'"key"', b'{"x":[true,null,1]}')])
        self.assertEqual(table.get("key"), {"x": [True, None, 1]})
        with self.assertRaises(ValueError):
            table.put_encoded(b'"key"', b'{"b":1, "a":2}')
        with self.assertRaises(ValueError):
            table.patch_encoded([("put", b'"key"', table.get_hash("key"), b'1.0')])
        with self.assertRaises(ValueError):
            encoded.EncodedMap.from_encoded("x", [(b'"key"', "not bytes")], trusted=True)

    def test_trusted_encoded_path_does_zero_json_work(self):
        rows = [(["id", index], {"body": [index, "é", None]}) for index in range(100)]
        source = [(_wire(key), _wire(value)) for key, value in rows]
        expected = reference_root("bodies", rows)
        with (patch.object(sync, "canonical", side_effect=AssertionError("canonical")),
              patch.object(sync, "freeze", side_effect=AssertionError("freeze")),
              patch.object(encoded, "_loads", side_effect=AssertionError("parse")),
              patch.object(encoded, "_parse_bound", side_effect=AssertionError("scan"))):
            table = encoded.EncodedMap.from_encoded("bodies", source, trusted=True)
            self.assertEqual(table.root, expected)
            key, value, old = table.lookup_encoded_entry(source[0][0], trusted=True)
            self.assertIs(key, source[0][0])
            self.assertIs(value, source[0][1])
            newer = table.put_encoded(key, b'{"new":true}', expected=old, trusted=True)
            batch = newer.patch_encoded([("remove", key, newer.lookup_encoded_entry(
                key, trusted=True)[2]), ("put", b'"new"', None, b'null')], trusted=True)
            self.assertEqual(batch.count, table.count)
            self.assertIs(batch.lookup_encoded_entry(key, trusted=True), sync.ABSENT)
            self.assertEqual(len(list(batch.encoded_items())), 100)

    def test_random_batches_match_independent_full_oracle(self):
        rng = random.Random(833)
        current = {index: {"at": index, "text": "é漢"} for index in range(80)}
        table = encoded.EncodedMap("observations", current.items())
        for generation in range(18):
            operations = []
            for key in rng.sample(range(120), 12):
                expected = table.get_hash(key) if key in current else None
                if key in current and rng.randrange(3) == 0:
                    operations.append(("remove", key, expected))
                    del current[key]
                else:
                    value = {"at": generation, "text": "é漢", "null": None}
                    operations.append(("put", key, expected, value))
                    current[key] = value
            before = table
            table = table.patch(operations)
            self.assertEqual(table.root, reference_root("observations", current.items()))
            self.assertEqual(dict(table.items()), current)
            self.assertEqual(table.count, len(current))
            self.assertNotEqual(table.root, before.root)

    def test_expected_values_duplicates_and_failures_are_atomic(self):
        table = encoded.EncodedMap("x", [("a", {"v": 1}), ("b", None)])
        initial = table.root
        for operations in (
            [("put", "a", "0" * 64, {})],
            [("put", "a", None, {})],
            [("remove", "missing", "0" * 64)],
            [("remove", "a", None)],
            [("put", "a", table.get_hash("a"), {}), ("put", "missing", "0" * 64, {})],
            [("put", "new", None, {}), ("put", "new", None, {})],
            [("put", "new", sync.ANY, {})],
        ):
            with self.subTest(operations=operations):
                with patch.object(encoded.EncodedMap, "_entry_bytes",
                                  side_effect=AssertionError("expected check ran late")):
                    with self.assertRaises(ValueError):
                        table.patch(operations)
                self.assertEqual(table.root, initial)
        with self.assertRaises(ValueError):
            table.remove("a", expected=None)
        self.assertEqual(table.put("a", {"v": 1}).root, initial)
        same = table.patch([("put", "a", table.get_hash("a"), {"v": 1})])
        self.assertFalse(same.last_update.changed)
        self.assertEqual(same.last_update.created_nodes, 0)
        self.assertEqual(same.root, initial)

    def test_sparse_work_has_no_roster_iteration_and_keeps_path_bound(self):
        for size in (100, 500, 2000):
            with self.subTest(size=size):
                rows = [(_wire(index), _wire({"n": index})) for index in range(size)]
                table = encoded.EncodedMap.from_encoded("records", rows, trusted=True)
                key = _wire(size // 2)
                expected = table.lookup_encoded_entry(key, trusted=True)[2]
                with (patch.object(encoded.EncodedMap, "_entries",
                                   side_effect=AssertionError("full iteration")),
                      patch.object(encoded, "_loads", side_effect=AssertionError("parse"))):
                    changed = table.put_encoded(key, b'{"changed":true}', expected=expected,
                                                trusted=True)
                    self.assertLessEqual(changed.last_update.path_visits, 256)
                    self.assertLessEqual(changed.last_update.created_nodes, 257)
                    expected = changed.lookup_encoded_entry(key, trusted=True)[2]
                    removed = changed.patch_encoded([("remove", key, expected)], trusted=True)
                    self.assertLessEqual(removed.last_update.path_visits, 512)
                    self.assertEqual(removed.last_update.enumerated_keys, 1)
                self.assertEqual(removed.count, size - 1)
                self.assertEqual(table.count, size)

    def test_bytes_are_shared_by_identity_and_no_decoded_graph_is_retained(self):
        account = sync.AllocationAccount()
        key, value = b'"key"', _wire({"body": [{"n": n} for n in range(80)]})
        table = encoded.EncodedMap.from_encoded("bodies", [(key, value)], account=account,
                                                trusted=True)
        before = account.snapshot()
        replacement = b'{"replacement":true}'
        newer = table.put_encoded(bytes(bytearray(key)), replacement, trusted=True)
        self.assertIs(newer.lookup_encoded_entry(key, trusted=True)[0], key)
        self.assertEqual(account.snapshot()["objectsCreated"] - before["objectsCreated"], 1)
        other = encoded.EncodedMap.from_encoded("other", [(key, value)], account=account,
                                                trusted=True)
        self.assertEqual(account._held[id(value)].refs, 2)
        self.assertEqual(account._held[id(key)].refs, 3)
        self.assertNotEqual(table.root, other.root)
        for held in account._held.values():
            self.assertNotIsInstance(held.value, (sync._FrozenArray, sync._FrozenObject, dict, list))
        del table, newer, other
        gc.collect()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])
        self.assertEqual(account.snapshot()["objects"], 0)

    def test_budget_reservation_precedes_json_encoding_and_parsing(self):
        account = sync.AllocationAccount(limit=1024 * 1024)
        table = encoded.EncodedMap("x", [("key", {"long": "a" * 10000})], account=account)
        before = account.snapshot()["used"]
        canonical = sync.canonical

        def funded_key_only(value):
            if value != "key":
                raise AssertionError("unfunded encode")
            return canonical(value)

        with account.reserve(account.limit - before - 32000):
            with patch.object(encoded, "_loads", side_effect=AssertionError("unfunded parse")):
                with self.assertRaises(sync.BudgetExceeded):
                    table.get("key")
            with patch.object(sync, "canonical", side_effect=funded_key_only):
                with self.assertRaises(sync.BudgetExceeded):
                    table.put("key", {"large": "b" * 10000})
        self.assertEqual(account.snapshot()["used"], before)
        self.assertEqual(table.get("key"), {"long": "a" * 10000})

    def test_all_replaced_roots_and_batch_credit_release(self):
        account = sync.AllocationAccount()
        table = encoded.EncodedMap("observations", [(n, {"clock": n}) for n in range(500)],
                                    account=account)
        operations = [("put", n, table.get_hash(n), {"clock": n + 1}) for n in range(500)]
        newer = table.patch(operations)
        self.assertEqual(newer.count, 500)
        self.assertEqual(account.snapshot()["byKind"]["stage"], 0)
        del table, newer
        gc.collect()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_collision_checks_apply_to_encoded_and_batch_paths(self):
        with patch.object(encoded.EncodedMap, "_key_digest", return_value=b"x" * 32):
            table = encoded.EncodedMap.from_encoded("x", [(b'"a"', b'1')], trusted=True)
            with self.assertRaisesRegex(ValueError, "collision"):
                table.put_encoded(b'"b"', b'2', trusted=True)
            with self.assertRaisesRegex(ValueError, "collision"):
                table.patch_encoded([("put", b'"b"', None, b'2')], trusted=True)
            with self.assertRaisesRegex(ValueError, "collision"):
                table.lookup_encoded_entry(b'"b"', trusted=True)

    def test_decode_uses_fast_bound_and_returned_rows_are_independent(self):
        table = encoded.EncodedMap("x", [("a", {"body": [{"x": 1}]})])
        with patch.object(encoded, "_parse_bound", side_effect=AssertionError("slow scan")):
            first = table.get("a")
            second, _ = table.lookup("a")
        first["body"][0]["x"] = 2
        self.assertEqual(second, {"body": [{"x": 1}]})
        self.assertGreater(encoded.decode_bound(b'{"x":1}'), len(b'{"x":1}'))

    def test_failed_batch_traceback_releases_all_minted_scratch_and_nodes(self):
        account = sync.AllocationAccount()
        table = encoded.EncodedMap("x", [(n, {"clock": n}) for n in range(40)], account=account)
        operations = [("put", n, table.get_hash(n), {"clock": n + 1}) for n in range(40)]
        before = account.snapshot()
        caught = None
        original = encoded.EncodedMap._branch

        def reject(current, split, left, right, work):
            if current is table:
                raise sync.BudgetExceeded("test_atomic_capacity")
            return original(current, split, left, right, work)

        with patch.object(encoded.EncodedMap, "_branch", new=reject):
            try:
                table.patch(operations)
            except sync.BudgetExceeded as error:
                caught = error
        self.assertIsNotNone(caught)
        self.assertIsNotNone(caught.__traceback__)
        gc.collect()
        self.assertEqual(account.snapshot()["byKind"]["stage"], 0)
        self.assertEqual(account.snapshot()["objects"], before["objects"])
        self.assertEqual(account.snapshot()["byKind"]["nodes"], before["byKind"]["nodes"])
        self.assertEqual(table.root, reference_root("x", [(n, {"clock": n}) for n in range(40)]))

    def test_real_sparse_construction_peak_fits_the_accounted_reservation(self):
        account = sync.AllocationAccount()
        table = encoded.EncodedMap.from_encoded("observations", [(_wire(n), _wire({"clock": n}))
                                       for n in range(2000)], account=account, trusted=True)
        operations = [("put", _wire(n), table.get_hash(n), _wire({"clock": n + 1}))
                      for n in range(0, 2000, 17)]
        before = account.snapshot()["used"]
        tracemalloc.start()
        try:
            newer = table.patch_encoded(operations, trusted=True)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLessEqual(peak, account.snapshot()["peak"] - before)
        self.assertEqual(newer.last_update.enumerated_keys, len(operations))
        self.assertEqual(account.snapshot()["byKind"]["stage"], 0)

    def test_typed_keys_and_bounded_depth_do_not_merge_or_recurse_unboundedly(self):
        table = encoded.EncodedMap("x", [(True, "bool"), (1, "int"), (None, "null")])
        self.assertEqual(table.count, 3)
        self.assertEqual(table.get(True), "bool")
        self.assertEqual(table.get(1), "int")
        nested = b"[" * 257 + b"null" + b"]" * 257
        with self.assertRaisesRegex(ValueError, "depth"):
            encoded.EncodedMap.from_encoded("x", [(b"1", nested)])
        with self.assertRaises(ValueError):
            encoded.EncodedMap.from_encoded("x", [(b"1", b"1"), (b"1", b"2")], trusted=True)

    def test_borrowed_lookup_scratch_is_exact_live_and_avoids_new_leases(self):
        account = sync.AllocationAccount()
        table = encoded.EncodedMap("x", [("key", {"value": 1})], account=account)
        with account.reserve(8192, kind="stage") as scratch:
            with patch.object(sync.AllocationAccount, "reserve",
                              side_effect=AssertionError("fresh lookup lease")):
                found = table.lookup_encoded_entry(b'"key"', trusted=True, scratch=scratch)
                self.assertEqual(found[:2], (b'"key"', b'{"value":1}'))
                self.assertEqual(table.lookup_encoded_bytes(b'"key"', trusted=True,
                                                          scratch=scratch), found[:2])
        with self.assertRaisesRegex(ValueError, "scratch"):
            table.lookup_encoded_entry(b'"key"', trusted=True, scratch=scratch)
        with account.reserve(8191) as small:
            with self.assertRaisesRegex(ValueError, "scratch"):
                table.lookup_encoded_entry(b'"key"', trusted=True, scratch=small)
        other = sync.AllocationAccount()
        with other.reserve(8192) as foreign:
            with self.assertRaisesRegex(ValueError, "scratch"):
                table.lookup_encoded_entry(b'"key"', trusted=True, scratch=foreign)

    def test_bulk_and_patch_reuse_one_stage_for_all_node_construction(self):
        account = sync.AllocationAccount()
        reserve = sync.AllocationAccount.reserve
        calls = []

        def observe(current, size, **kwargs):
            calls.append(size)
            return reserve(current, size, **kwargs)

        with patch.object(sync.AllocationAccount, "reserve", new=observe):
            table = encoded.EncodedMap.from_encoded("x", [(_wire(n), _wire(n)) for n in range(100)],
                                                     account=account, trusted=True)
            self.assertEqual(len(calls), 2)  # Initial map metadata, then the bulk stage.
            operations = [("put", _wire(n), table.lookup_encoded_entry(_wire(n), trusted=True)[2],
                           _wire(n + 1)) for n in range(100)]
            calls.clear()
            newer = table.patch_encoded(operations, trusted=True)
            self.assertEqual(len(calls), 1)
            self.assertEqual(newer.count, 100)

    def test_large_preowned_replacement_batch_uses_measured_metadata_and_funded_real_peak(self):
        account = sync.AllocationAccount()
        ledger = EncodedOwnership(account)
        account.encoded_ownership = ledger
        old_rows = [(_wire("old-" + str(n)), _wire({"body": n})) for n in range(2000)]
        table = encoded.EncodedMap.from_encoded("bodies", old_rows, account=account, trusted=True)
        new_rows = [(_wire("new-" + str(n)), _wire({"body": n + 1})) for n in range(2000)]
        for key, value in new_rows:
            ledger.retain(key, value)  # Source-owned buffers predate table patching.
        operations = [("remove", key, table.lookup_encoded_entry(key, trusted=True)[2])
                      for key, _ in old_rows]
        operations += [("put", key, None, value) for key, value in new_rows]
        before = account.snapshot()["used"]
        max_stage = [0]
        prepare = encoded.EncodedMap._stage_buffers

        def observe(stage, *args, **kwargs):
            prepare(stage, *args, **kwargs)
            max_stage[0] = max(max_stage[0], stage._size)

        tracemalloc.start()
        try:
            with patch.object(encoded.EncodedMap, "_stage_buffers", new=staticmethod(observe)):
                newer = table.patch_encoded(operations, trusted=True)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(max_stage[0], 2 * 1024 * 1024)
        self.assertLessEqual(peak, account.snapshot()["peak"] - before)
        self.assertEqual(newer.last_update.enumerated_keys, 4000)
        self.assertEqual(newer.root, reference_root("bodies", [(json.loads(k), json.loads(v))
                                                              for k, v in new_rows]))
        self.assertEqual(table.count, 2000)
        self.assertIsNot(table.lookup_encoded_entry(old_rows[0][0], trusted=True), sync.ABSENT)
        for key, value in new_rows:
            ledger.release(key, value)
        del table, newer
        gc.collect()
        self.assertEqual(ledger.used, 0)
        ledger.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_mixed_noops_removals_and_replacements_keep_original_expected_semantics(self):
        original = {n: {"clock": n} for n in range(100)}
        table = encoded.EncodedMap("observations", original.items())
        operations = [("put", n, table.get_hash(n), value) for n, value in original.items()]
        operations[20] = ("remove", 20, table.get_hash(20))
        operations[80] = ("put", 80, table.get_hash(80), {"clock": 1000})
        newer = table.patch(operations)
        expected = dict(original)
        del expected[20]
        expected[80] = {"clock": 1000}
        self.assertEqual(newer.root, reference_root("observations", expected.items()))
        self.assertEqual(dict(table.items()), original)
        self.assertEqual(newer.last_update.enumerated_keys, 100)
        self.assertEqual(newer.count, 99)


def benchmark(repetitions=5):
    """Table-only diagnostic, native-shaped API4 body plus observation clocks.

    Raw input graphs predate timing/accounting, identically for both backends.
    Trusted encoded timings INCLUDE native JSON serialization of changed rows;
    schema/provider/whole-owner work and native acceptance are outside this test.
    """
    from test_service_state import provider_snapshot

    from agent_observer.sync_contract import split_record

    body, observations = split_record(provider_snapshot("codex")["sessions"][0])
    report = []
    for count in (500, 2000):
        bodies, observed = [], []
        for index in range(count):
            content = copy.deepcopy(body)
            content["identity"]["nativeId"] = "00000000-0000-0000-0000-" + f"{index:012x}"
            bodies.append((index, content))
            observed.append((index, copy.deepcopy(observations)))
        changed = []
        for key, value in observed:
            value = copy.deepcopy(value)
            for fact in value.values():
                for field, clock in fact.items():
                    if type(clock) is int:
                        fact[field] = clock + 1
            changed.append((key, value))
        for backend in (sync.PersistentMap, encoded.EncodedMap):
            account = sync.AllocationAccount()
            started = time.process_time_ns()
            base_body = backend("bodies", bodies, account=account)
            base_obs = backend("observations", observed, account=account)
            baseline_ms = (time.process_time_ns() - started) / 1e6
            retained = account.snapshot()["used"]
            expected = {key: base_obs.get_hash(key) for key, _ in changed}
            timings = {"one": [], "all": []}
            last = None
            for mode, rows in (("one", changed[:1]), ("all", changed)):
                for _ in range(repetitions):
                    started = time.process_time_ns()
                    if backend is encoded.EncodedMap:
                        operations = [("put", _wire(key), expected[key], _wire(value))
                                      for key, value in rows]
                        newer = base_obs.patch_encoded(operations, trusted=True)
                    else:
                        operations = [("put", key, expected[key], value) for key, value in rows]
                        newer = base_obs.patch(operations)
                    timings[mode].append((time.process_time_ns() - started) / 1e6)
                    if mode == "all":
                        last = newer.root
                    del newer, operations
            result = {"rows": count, "backend": backend.__name__, "baselineMs": baseline_ms,
                      "retainedBytes": retained, "peakBytes": account.snapshot()["peak"],
                      "oneRowMedianMs": statistics.median(timings["one"]),
                      "allClockMedianMs": statistics.median(timings["all"]),
                      "bodyRoot": base_body.root, "resultRoot": last}
            report.append(result)
            del base_body, base_obs
            gc.collect()
            assert account.snapshot()["used"] == account.snapshot()["base"]
        assert report[-1]["bodyRoot"] == report[-2]["bodyRoot"]
        assert report[-1]["resultRoot"] == report[-2]["resultRoot"]
    return report


if __name__ == "__main__":
    if "--benchmark" in sys.argv:
        print(json.dumps(benchmark(), sort_keys=True, indent=2))
    else:
        unittest.main()
