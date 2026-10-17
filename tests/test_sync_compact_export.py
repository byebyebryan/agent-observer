"""Actual compact owner output, synthetic generations and independent Reader."""

import copy
import gc
import json
import unittest
import uuid
from unittest.mock import patch

import test_mesh_sync_codec as codec_fixture
import test_mesh_sync_read as read_fixture
from compact_vectors_support import (
    raw_transaction_id,
    restore_baseline,
    restore_transaction,
    sorted_tables,
)
from jsonschema import Draft202012Validator

from agent_observer.contract import ContractError
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import canonical
from agent_observer.sync_compact_schema import schema_document
from agent_observer.sync_native import parse_message
from agent_observer.sync_state import OwnerSyncCache


class SyncCompactExportTest(unittest.TestCase):
    fixture = read_fixture.MeshSyncReadTest.fixture

    def setUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.now, self.owners = 15000, []

    def tearDown(self):
        for owner in self.owners:
            if owner._sync_cache is not None:
                account = owner._sync_cache.account
                owner._sync_cache.close()
                self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])
                self.assertEqual(owner._sync_cache.encoded_staged, 0)
        self.assertFalse(gc.isenabled())
        if self.enabled:
            gc.enable()

    def owner(self, serialization="compact", value=None):
        value = self.fixture(3) if value is None else value
        source = value["sources"][0]
        with patch("agent_observer.service_state.uuid.uuid4", return_value=uuid.UUID(int=61440)):
            owner = ServiceState(
                host_scope="fixture", configs={"codex": (source["configHome"], source["configHomeKind"])},
                uid=1000, clock=lambda: self.now,
                boot_id="00000000-0000-4000-8000-000000000001", clock_domain="time:[123]",
                sync_serialization=serialization,
            )
        owner.wall_clock = lambda: 150000
        owner.collection_id = lambda: str(uuid.UUID(int=61440))
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.owners.append(owner)
        return owner

    def test_explicit_compact_full_active_restore_exact_legacy_tables_and_roots(self):
        compact, legacy = self.owner(), self.owner("expanded")
        validator = Draft202012Validator(schema_document())
        for view in ("full", "active"):
            raw_bytes = compact.sync_baseline(view)
            raw = json.loads(raw_bytes)
            validator.validate(raw)
            expected = parse_message(legacy.sync_baseline(view), view, "fixture")
            restored, rows = restore_baseline(raw)
            self.assertEqual(restored["tables"], sorted_tables(expected["tables"]))
            self.assertEqual(restored["tag"], expected["tag"])
            self.assertEqual(len(rows), 3)
            self.assertEqual(raw_bytes, canonical(raw) + b"\n")
            self.assertIs(compact.sync_baseline(view), raw_bytes)
            self.assertLess(len(raw_bytes), len(legacy.sync_baseline(view)))

    def test_warming_and_empty_selected_generations_keep_complete_metadata(self):
        for serialization in ("expanded", "compact"):
            owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture", "explicit")},
                                 uid=1000, clock=lambda: self.now, clock_domain="time:[123]",
                                 sync_serialization=serialization)
            self.owners.append(owner)
            for view in ("full", "active"):
                message = json.loads(owner.sync_baseline(view))
                if serialization == "compact":
                    restored, rows = restore_baseline(message)
                    self.assertEqual(rows, [])
                    self.assertEqual(restored["tables"]["memberships"], [])
                    Draft202012Validator(schema_document()).validate(message)
                self.assertTrue(message["nativeBinding"]["sourceContexts"])

    def test_transactions_preserve_masks_omission_and_raw_id_and_all_table_roots(self):
        validator = Draft202012Validator(schema_document())
        for view in ("full", "active"):
            compact, legacy = self.owner(), self.owner("expanded")
            previous, _rows = restore_baseline(json.loads(compact.sync_baseline(view)))
            legacy.sync_baseline(view)
            for step in range(4):
                value = self.fixture(3 if step < 2 else 2 if step == 2 else 4)
                if step in {1, 3}:
                    value["sessions"][0]["title"] = "new Ω title"
                base = compact.sync_current_tag(view)
                self.now += 10
                for owner in (compact, legacy):
                    owner.accept("codex", "runtime", copy.deepcopy(value), sampled_ms=self.now, ttl_ms=10000)
                target = compact.sync_current_tag(view)
                frames = compact.sync_changes(view, base, target)
                self.assertEqual(len(frames), 2)
                raw = json.loads(frames[0])
                validator.validate(raw)
                self.assertEqual(raw["transactionId"], raw_transaction_id(raw))
                self.assertEqual(frames[0], canonical(raw) + b"\n")
                if step < 2:
                    self.assertEqual(raw["operations"]["memberships"], [])
                previous = restore_transaction(raw, previous)
                expected = parse_message(legacy.sync_baseline(view), view, "fixture")
                self.assertEqual(previous["tables"], sorted_tables(expected["tables"]))
                self.assertEqual(previous["tag"], expected["tag"])

    def test_heads_controls_default_and_one_serializer_do_not_change(self):
        compact, legacy = self.owner(), self.owner("expanded")
        for view in ("full", "active"):
            compact.sync_baseline(view)
            legacy.sync_baseline(view)
            self.assertEqual(compact.sync_head(view, {"nonce": "a" * 32}),
                             legacy.sync_head(view, {"nonce": "a" * 32}))
            for status in ("complete", "heartbeat", "baseline_required"):
                self.assertEqual(compact.sync_control(view, status), legacy.sync_control(view, status))
            self.assertNotIn("receiptRefs", json.loads(legacy.sync_baseline(view)))
        with self.assertRaisesRegex(ContractError, "sync_owner_serialization"):
            OwnerSyncCache(compact, serialization="unknown")
        with self.assertRaisesRegex(ContractError, "sync_owner_compact_backend"):
            OwnerSyncCache(compact, serialization="compact")
        with self.assertRaisesRegex(ContractError, "sync_owner_serialization"):
            ServiceState(host_scope="fixture", configs={}, sync_serialization=True)

    def test_baseline_never_calls_expanded_export_or_decodes_whole_frame(self):
        from agent_observer.sync_compact_export import _Export
        from agent_observer.sync_encoded import EncodedMap

        owner = self.owner()
        owner.sync_baseline("full")
        owner._sync_cache.views["full"].baseline.close()
        owner._sync_cache.views["full"].baseline = None
        original = json.loads
        close_export = _Export.close
        sizes = []

        def one_value(raw, *args, **kwargs):
            sizes.append(len(raw))
            self.assertLess(len(raw), 8192)
            return original(raw, *args, **kwargs)

        def output_owned_before_scratch_retirement(export):
            self.assertIsNotNone(owner._sync_cache.views["full"].baseline)
            self.assertTrue(owner.sync_retained_buffers())
            close_export(export)

        with (patch.object(OwnerSyncCache, "_baseline_write", side_effect=AssertionError("expanded export")),
              patch.object(EncodedMap, "lookup_encoded", side_effect=AssertionError("unprepaid logical key")),
              patch.object(_Export, "close", new=output_owned_before_scratch_retirement),
              patch("agent_observer.sync_compact_export.json.loads", side_effect=one_value)):
            data = owner.sync_baseline("full")
        self.assertTrue(sizes)
        self.assertGreater(len(data), max(sizes))

    def test_frame_and_preallocation_rejection_preserve_current_and_reclaim_scratch(self):
        owner = self.owner()
        owner.sync_baseline("full")
        cache = owner._sync_cache
        tag = owner.sync_current_tag("full")
        cache.views["full"].baseline.close()
        cache.views["full"].baseline = None
        before = cache.account.snapshot()["used"]
        errors = []
        for mode in ("frame", "encoded"):
            try:
                if mode == "frame":
                    with patch("agent_observer.sync_state.FRAME_LIMIT", 128):
                        owner.sync_baseline("full")
                else:
                    cache.reserver = lambda _amount: False
                    with patch("agent_observer.sync_state._encode_parts", side_effect=AssertionError("unpaid output")):
                        owner.sync_baseline("full")
            except ContractError as error:
                errors.append(error)
            finally:
                cache.reserver = None
            self.assertEqual(owner.sync_current_tag("full"), tag)
            self.assertIsNone(cache.views["full"].baseline)
            self.assertEqual(cache.encoded_staged, 0)
            self.assertEqual(cache.account.snapshot()["used"], before)
        self.assertEqual(len(errors), 2)
        self.assertTrue(owner.sync_baseline("full").endswith(b"\n"))

    def test_transaction_serializer_uses_changed_rows_without_membership_or_body_scan(self):
        from agent_observer.sync_compact_export import transaction
        from agent_observer.sync_encoded import EncodedMap

        owner = self.owner(value=self.fixture(100))
        base = json.loads(owner.sync_baseline("full"))["tag"]
        original = EncodedMap.encoded_items
        scans = []

        def only_bounded_receipts(table, **kwargs):
            scans.append((table.space, table.count))
            self.assertEqual(table.space, "receipts")
            self.assertLessEqual(table.count, 32)
            return original(table, **kwargs)

        value = self.fixture(100)
        value["sessions"][0]["title"] = "one changed body"
        self.now += 10
        def serialize(*args):
            # Normalization's retained legacy table/index work is deliberately
            # outside this serializer-only scan assertion and CPU boundary.
            with patch.object(EncodedMap, "encoded_items", new=only_bounded_receipts):
                return transaction(*args)

        with patch("agent_observer.sync_compact_export.transaction", new=serialize):
            owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.assertEqual(len(scans), 2)
        frames = owner.sync_changes("full", base, owner.sync_current_tag("full"))
        raw = json.loads(frames[0])
        self.assertEqual(len(raw["operations"]["bodies"]), 2)  # one retired, one inserted
        self.assertEqual(raw["operations"]["memberships"], [])

    def test_optional_journal_quota_failure_requires_baseline_without_encoding_fallback(self):
        owner = self.owner()
        base = json.loads(owner.sync_baseline("full"))["tag"]
        self.now += 10
        with patch("agent_observer.sync_state.JOURNAL_LIMIT", 128):
            owner.accept("codex", "runtime", self.fixture(2), sampled_ms=self.now, ttl_ms=10000)
        target = owner.sync_current_tag("full")
        self.assertNotEqual(list(target), base)
        result = owner.sync_changes("full", base, target)
        self.assertIs(type(result), bytes)
        self.assertEqual(json.loads(result)["status"], "baseline_required")
        self.assertEqual(owner._sync_cache.views["full"].journal, [])
        baseline = json.loads(owner.sync_baseline("full"))
        self.assertIn("receiptRefs", baseline)
        self.assertEqual(baseline["tag"], list(target))


@unittest.skipUnless(codec_fixture.HAS_COMPACT, "optional Mesh compact interface is unavailable")
class CompactExportReaderTest(unittest.TestCase):
    fixture = SyncCompactExportTest.fixture
    owner = SyncCompactExportTest.owner
    cache = codec_fixture.MeshSyncCodecTest.cache
    confirm = read_fixture.MeshSyncReadTest.confirm

    def setUp(self):
        SyncCompactExportTest.setUp(self)
        self.caches = []

    def tearDown(self):
        for cache in self.caches:
            cache.close()
            ledger = cache.ledger
            self.assertEqual((ledger.used, ledger.reserved, ledger.encoded, ledger.encoded_reserved,
                              ledger.pending_units, ledger.pending_encoded), (0, 0, 0, 0, 0, 0))
        SyncCompactExportTest.tearDown(self)

    def test_real_owner_baseline_transactions_fresh_proof_and_lossless_facade(self):
        owner = self.owner()
        for view in ("full", "active"):
            parts = self.cache(view)
            reader = parts[0]
            candidate = reader.admit_baseline(owner.sync_baseline(view))
            self.assertEqual(self.confirm(parts, owner, candidate).export_committed(),
                             owner.snapshot if view == "full" else owner.active_projection)
            for count in (3, 1, 4):
                base = owner.sync_current_tag(view)
                value = self.fixture(count)
                value["sessions"][0]["title"] = f"changed {count}"
                self.now += 10
                owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
                target = owner.sync_current_tag(view)
                frames = owner.sync_changes(view, base, target)
                candidate = reader.stage(frames[0])
                self.assertEqual(candidate.tag.native.wire(), list(target))
                self.assertEqual(self.confirm(parts, owner, candidate).export_committed(),
                                 owner.snapshot if view == "full" else owner.active_projection)

    def test_compact_raw_expected_old_and_root_rejection_leave_earlier_material_intact(self):
        from mesh_plus.protocol import ProtocolError

        owner = self.owner()
        parts = self.cache()
        reader = parts[0]
        candidate = reader.admit_baseline(owner.sync_baseline("full"))
        self.confirm(parts, owner, candidate)
        base = owner.sync_current_tag("full")
        value = self.fixture(2)
        self.now += 10
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        frames = owner.sync_changes("full", base, owner.sync_current_tag("full"))
        original = json.loads(frames[0])
        for fault in ("old", "root"):
            raw = copy.deepcopy(original)
            if fault == "old":
                raw["operations"]["records"][0][2] = "e" * 64
            else:
                raw["resultTag"][2] = raw["resultCursor"][2] = "e" * 64
            raw["transactionId"] = raw_transaction_id(raw)
            with self.assertRaises(ProtocolError):
                reader.stage(canonical(raw) + b"\n")
        self.assertEqual(reader.stage(frames[0]).tag.native.wire(), original["resultTag"])
