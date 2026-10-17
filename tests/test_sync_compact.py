"""Candidate schema/one-row restoration and tiny DOM models only.

No configured NativeCodec, streaming plan, sparse generic staging, live source,
accounting, CPU, installed pair or schema freeze is exercised here.
"""

import copy
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from bench_sync_producer import native_shaped_snapshot
from compact_vectors_support import (
    pack_baseline,
    pack_transaction,
    raw_transaction_id,
    reference_context,
    restore_baseline,
    restore_transaction,
    sorted_tables,
)
from jsonschema import Draft202012Validator

from agent_observer.contract import ContractError
from agent_observer.service_state import ServiceState
from agent_observer.sync_compact_schema import schema_document, value_schema
from agent_observer.sync_compact_values import pack_value, restore_value
from agent_observer.sync_native import TABLES, parse_message

ROOT = Path(__file__).resolve().parents[1]


def owner_fixture(rows=2):
    boot, snapshot, wall = native_shaped_snapshot(rows)
    now = [15000]
    epoch = uuid.UUID(int=61440)
    with (patch("agent_observer.service_state.uuid.uuid4", return_value=epoch),
          patch("agent_observer.service_state.socket.gethostname", return_value="fixture-native")):
        owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                             uid=1000, clock=lambda: now[0], boot_id=boot, clock_domain="time:[123]")
    owner.wall_clock = lambda: wall
    owner.collection_id = lambda: str(epoch)
    owner.attempt("codex", "history")
    owner.accept("codex", "history", snapshot, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
    return owner, snapshot, now


class SyncCompactCandidateTest(unittest.TestCase):
    def setUp(self):
        self.owner, self.snapshot, self.now = owner_fixture()
        self.validator = Draft202012Validator(schema_document())

    def tearDown(self):
        if self.owner._sync_cache is not None:
            self.owner._sync_cache.close()

    def baseline(self, view="full"):
        return parse_message(self.owner.sync_baseline(view), view, "fixture")

    def test_candidate_schema_is_self_contained_and_reproduces_new_file(self):
        schema = schema_document()
        Draft202012Validator.check_schema(schema)
        path = ROOT / "agent_observer/contracts/sync-compact-frame.schema.json"
        self.assertEqual(json.loads(path.read_text()), schema)
        self.assertEqual(schema["$id"], "urn:agent-observer:sync-compact-frame:1")
        stack = [schema]
        while stack:
            value = stack.pop()
            if type(value) is dict:
                if "$ref" in value:
                    self.assertTrue(value["$ref"].startswith("#/$defs/"))
                    self.assertIn(value["$ref"].split("/")[-1], schema["$defs"])
                stack.extend(value.values())
            elif type(value) is list:
                stack.extend(value)

    def test_full_active_all_eight_table_restoration_and_native_body_identities(self):
        for view in ("full", "active"):
            original = self.baseline(view)
            raw = pack_baseline(original)
            self.validator.validate(raw)
            restored, rows = restore_baseline(raw)
            self.assertEqual(restored["tables"], sorted_tables(original["tables"]))
            self.assertEqual(restored["tag"], original["tag"])
            for row in rows:
                self.assertEqual(len(row["tokens"]), 9)
                self.assertEqual(row["identity"][4], row["body"]["nativeIds"]["threadId"])
            self.assertNotIn("sessions", raw)
            self.assertLess(len(json.dumps(raw)), len(json.dumps(original)))

    def test_value_schemas_cover_each_actual_nonmembership_entry(self):
        for view in ("full", "active"):
            raw = pack_baseline(self.baseline(view))
            for space in TABLES:
                validator = Draft202012Validator(value_schema(space))
                for entry in raw["tables"][space]:
                    validator.validate(entry)

    def test_warming_full_active_restore_without_selected_rows_or_current_support(self):
        owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                             uid=1000, clock=lambda: 15000, boot_id=self.owner.boot_id,
                             clock_domain="time:[123]")
        try:
            for view in ("full", "active"):
                original = parse_message(owner.sync_baseline(view), view, "fixture")
                raw = pack_baseline(original)
                self.validator.validate(raw)
                restored, rows = restore_baseline(raw)
                self.assertEqual(restored["tables"], sorted_tables(original["tables"]))
                self.assertEqual(rows, [])
                self.assertEqual(restored["tables"]["memberships"], [])
                self.assertTrue(all(value["accepted"] == 0 for _key, value in restored["tables"]["receipts"]))
        finally:
            if owner._sync_cache is not None:
                owner._sync_cache.close()

    def test_original_head_control_shapes_are_exact_and_reject_compact_material(self):
        from agent_observer.sync_native import FRAME

        self.assertEqual(schema_document()["anyOf"][2:], FRAME["anyOf"][2:])
        for view in ("full", "active"):
            self.baseline(view)
            messages = [parse_message(self.owner.sync_head(view, {"nonce": "a" * 32}), view, "fixture")]
            messages.extend(parse_message(self.owner.sync_control(view, status), view, "fixture")
                            for status in ("complete", "heartbeat", "baseline_required"))
            for message in messages:
                self.validator.validate(message)
                message["receiptRefs"] = {"before": [], "after": []}
                self.assertFalse(self.validator.is_valid(message))

    def test_syntactic_future_birth_requires_dynamic_generation_rejection(self):
        original = self.baseline()
        raw = pack_baseline(original)
        refs = reference_context(original["nativeBinding"], original["tag"][1], raw["receiptRefs"],
                                 dict.fromkeys(TABLES, []), original["tables"], baseline=True)
        key, value = copy.deepcopy(raw["tables"]["records"][0])
        value[1] = original["tag"][1] + 1
        Draft202012Validator(value_schema("records")).validate([key, value])
        with self.assertRaisesRegex(ContractError, "sync_compact_slot"):
            restore_value("records", key, value, refs)

    def test_schema_rejects_bad_lengths_booleans_masks_keys_and_missing_phase_position(self):
        raw = pack_baseline(self.baseline("active"))
        mutations = (
            lambda m: m.update(other=True),
            lambda m: m["receiptRefs"].update(before=m["receiptRefs"]["after"][:1]),
            lambda m: m["receiptRefs"]["after"].append(m["receiptRefs"]["after"][0]),
            lambda m: m["tables"]["records"][0][1].__setitem__(0, True),
            lambda m: m["tables"]["records"][0][1].__setitem__(1, 0),
            lambda m: m["tables"]["bodies"][0][1].pop(),
            lambda m: m["tables"]["observations"][0][1][0].pop(1),
            lambda m: m["tables"]["observations"][0][1][1].__setitem__(0, False),
            lambda m: m["tables"]["observations"][0][1][1].__setitem__(0, 32),
            lambda m: m["tables"]["memberships"][0].__setitem__(1, 0),
            lambda m: m["tables"]["memberships"][0].__setitem__(1, 512),
            lambda m: m["tables"]["metadata"].append(["unknown", None]),
        )
        for mutation in mutations:
            forged = copy.deepcopy(raw)
            mutation(forged)
            self.assertFalse(self.validator.is_valid(forged))

    def test_null_phase_and_nested_optional_null_remain_distinct(self):
        original = self.baseline()
        raw = pack_baseline(original)
        refs = reference_context(original["nativeBinding"], original["tag"][1], raw["receiptRefs"],
                                 dict.fromkeys(TABLES, []), original["tables"], baseline=True)
        key, body = copy.deepcopy(original["tables"]["bodies"][0])
        body["phase"] = None
        body["lastUpdated"]["lastKnownAt"] = None
        packed_key, packed = pack_value("bodies", key, body, refs)
        Draft202012Validator(value_schema("bodies")).validate([packed_key, packed])
        _, restored = restore_value("bodies", packed_key, packed, refs)
        self.assertIn("lastKnownAt", restored["lastUpdated"])
        self.assertIsNone(restored["lastUpdated"]["lastKnownAt"])
        self.assertEqual(restored, body)
        key, observed = copy.deepcopy(original["tables"]["observations"][0])
        observed["fields"].pop("phase", None)
        packed_key, packed = pack_value("observations", key, observed, refs)
        self.assertIsNone(packed[0][1])
        _, restored = restore_value("observations", packed_key, packed, refs)
        self.assertNotIn("phase", restored["fields"])
        self.assertEqual(restored, observed)

    def test_literal_old_context_and_timing_do_not_rebind_to_dictionary(self):
        original = self.baseline()
        raw = pack_baseline(original)
        refs = reference_context(original["nativeBinding"], original["tag"][1], raw["receiptRefs"],
                                 dict.fromkeys(TABLES, []), original["tables"], baseline=True)
        key, observed = copy.deepcopy(original["tables"]["observations"][0])
        identity = key[0]
        literal = {"serviceId": original["nativeBinding"]["ownerEpoch"], "provider": identity[1],
                   "namespace": identity[2], "component": "history", "contextGeneration": 0,
                   "accepted": 1, "sampledBoottimeMs": 2, "expiresBoottimeMs": 3}
        observed["supports"]["lastUpdated"] = ["context", literal]
        observed["fields"]["lastUpdated"]["receipt"] = {
            "component": "history", "sampledBoottimeMs": 2, "observedBoottimeMs": 2,
            "contextGeneration": 0}
        packed_key, packed = pack_value("observations", key, observed, refs)
        Draft202012Validator(value_schema("observations")).validate([packed_key, packed])
        _, restored = restore_value("observations", packed_key, packed, refs)
        self.assertEqual(restored, observed)
        self.assertEqual(restored["supports"]["lastUpdated"], ["context", literal])

    def test_native_body_change_transaction_with_omitted_masks_restores_all_tables(self):
        for view in ("full", "active"):
            before = self.baseline(view)
            self.now[0] += 10
            self.snapshot["sessions"][0]["lastUpdated"]["at"] += 1000
            for row in self.snapshot["sessions"]:
                for name in ("lastUpdated", "latestTurn"):
                    row[name]["receipt"].update(sampledBoottimeMs=self.now[0], observedBoottimeMs=self.now[0])
            self.owner.attempt("codex", "history")
            self.owner.accept("codex", "history", self.snapshot, sampled_ms=self.now[0],
                              ttl_ms=60000, runtime_ttl_ms=60000)
            target = self.baseline(view)
            changes = self.owner.sync_changes(view, before["tag"], target["tag"])
            current = before
            for encoded in changes:
                message = parse_message(encoded, view, "fixture")
                if message["kind"] == "control":
                    continue
                # Diagnostics and material may be two accepted generations.
                # Obtain this small fixture's exact target by applying the
                # existing expanded operations to its prior logical tables.
                after = expanded_apply(current, message)
                raw = pack_transaction(message, current, after)
                self.validator.validate(raw)
                self.assertEqual(raw["transactionId"], raw_transaction_id(raw))
                self.assertEqual(raw["operations"]["memberships"], [])
                restored = restore_transaction(raw, current)
                self.assertEqual(restored["tables"], sorted_tables(after["tables"]))
                current = after
            self.assertEqual(current["tag"], target["tag"])


def expanded_apply(before, message):
    from agent_observer.sync_commitment import canonical

    tables = {name: {canonical(key): [key, value] for key, value in rows}
              for name, rows in before["tables"].items()}
    for space, operations in message["operations"].items():
        for op in operations:
            if op[0] == "remove":
                tables[space].pop(canonical(op[1]))
            else:
                tables[space][canonical(op[1])] = [op[1], op[3]]
    return {**before, "tag": message["resultTag"], "cursor": message["resultCursor"],
            "tables": {name: list(rows.values()) for name, rows in tables.items()}}
