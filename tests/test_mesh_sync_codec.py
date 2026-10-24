"""Actual Agent raw-to-admitted compact integration, synthetic source only."""

import copy
import gc
import hashlib
import json
import subprocess
import sys
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

import test_mesh_sync_read as read_fixture
from jsonschema import Draft202012Validator
from test_sync_acquisition import wire

from agent_observer.contract import ContractError
from agent_observer.sync_compact_schema import value_schema
from agent_observer.sync_compact_validation import _load_value_schema

try:
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync import OwnedSyncCache, source_binding
    from mesh_plus.sync.budget import AllocationLedger

    from agent_observer.mesh_sync_codec import AgentCompactSyncCodec
    from agent_observer.mesh_sync_profile import AgentSyncProfile
except ImportError:
    HAS_COMPACT = False
else:
    HAS_COMPACT = True

ROOT = Path(__file__).resolve().parents[1]


def source_root(binding, native_root):
    data = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(b"mesh-sync-source\0" + len(data).to_bytes(8, "big") + data
                          + bytes.fromhex(native_root)).hexdigest()


@unittest.skipUnless(HAS_COMPACT, "optional public Mesh R2 codec interface is unavailable")
class MeshSyncCodecTest(unittest.TestCase):
    fixture = read_fixture.MeshSyncReadTest.fixture
    owner = read_fixture.MeshSyncReadTest.owner
    confirm = read_fixture.MeshSyncReadTest.confirm

    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads((ROOT / "tests/fixtures/delta-sync/compact-raw-vectors.json").read_text())
        cls.cases = {case["name"]: case for case in cls.vectors["baselines"] + cls.vectors["transactions"]}

    def setUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.now, self.caches, self.owners = 15000, [], []

    def tearDown(self):
        for cache in self.caches:
            cache.close()
            ledger = cache.ledger
            self.assertEqual((ledger.used, ledger.reserved, ledger.encoded, ledger.encoded_reserved,
                              ledger.pending_units, ledger.pending_encoded), (0, 0, 0, 0, 0, 0))
        for owner in self.owners:
            if owner._sync_cache is not None:
                owner._sync_cache.close()
        self.assertFalse(gc.isenabled())
        if self.enabled:
            gc.enable()

    def cache(self, view="full", *, compact=True, source="agents"):
        profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
        reader_time = [100000]
        clock = {"bootId": "reader-boot", "timeNamespace": "time:2"}
        binding = source_binding("fixture", source, profile.descriptor)
        request = {"readerEpoch": "r" * 32, "channelEpoch": "c" * 32,
                   "bridgeId": "b" * 32, "hosts": ["fixture"], "route": "fixed"}
        codec = AgentCompactSyncCodec(view, encoding_id="fixture-compact/1", expected_host="fixture") if compact else None
        cache = OwnedSyncCache(profile, binding, request_binding=request, native_codec=codec,
                               _now_ms=lambda: reader_time[0], _clock=clock)
        self.caches.append(cache)
        return cache, reader_time, clock, binding, request

    def staged(self, case):
        chain, base = [], case
        while "before" in base:
            chain.append(base)
            base = self.cases[base["before"]]
        view = base["raw"]["descriptor"]["view"]
        cache = self.cache(view, source="agents_full" if view == "full" else "agents_active")[0]
        candidate = cache.admit_baseline(wire(base["raw"]))
        for transaction in reversed(chain):
            candidate = cache.stage(wire(transaction["raw"]))
        return cache, candidate

    def test_all_eight_baselines_and_ten_transactions_reach_exact_native_roots(self):
        for case in self.vectors["baselines"] + self.vectors["transactions"]:
            with self.subTest(case=case["name"]):
                cache, candidate = self.staged(case)
                self.assertEqual(candidate.tag.native.wire(), case["expected"]["tag"])
                # Frozen dotted names are arithmetic-only inputs; the SDK
                # requires a separately configured valid source name.
                self.assertEqual(source_root(case["sourceBinding"], case["summary"]["nativeRoot"]),
                                 case["summary"]["sourceRoot"])
                binding = {**case["sourceBinding"], "source": "agents_full" if cache.profile.view == "full" else "agents_active"}
                self.assertEqual(candidate.tag.root, source_root(binding, case["summary"]["nativeRoot"]))
                cache.close()

    def test_all_eight_schema_valid_model_rejections_fail_actual_admission(self):
        codes = {"wrong-before-birth": "sync_compact_record_birth",
                 "wrong-after-birth": "sync_compact_record_birth",
                 "combined-rebirth-group": "sync_compact_group_identity",
                 "wrong-old-mask": "sync_membership_old_mask",
                 "duplicate-group": "sync_duplicate_membership_group",
                 "wrong-expected-old": "sync_expected_value",
                 "wrong-body-id": "sync_body_digest",
                 "wrong-cohort-seal": "sync_cohort_seal_root"}
        errors = []
        for case in self.vectors["rejections"]:
            with self.subTest(case=case["name"]):
                cache, _candidate = self.staged(self.cases[case["before"]])
                try:
                    cache.stage(wire(case["raw"]))
                except ProtocolError as error:
                    self.assertEqual(str(error), codes[case["name"]])
                    errors.append(error)
                else:
                    self.fail("schema-valid invalid material admitted")
                cache.close()
        self.assertEqual(len(errors), 8)

    def test_full_active_fresh_confirmation_losslessly_exports_public_native_dto(self):
        from compact_vectors_support import pack_baseline

        from agent_observer.sync_native import parse_message

        owner = self.owner(self.fixture(3))
        for view in ("full", "active"):
            parts = self.cache(view)
            cache = parts[0]
            original = parse_message(owner.sync_baseline(view), view, "fixture")
            candidate = cache.admit_baseline(wire(pack_baseline(original)))
            # The test's sole private operation is existing test-owned proof
            # challenge setup in confirm(); runtime codec/profile uses none.
            with patch("agent_observer.mesh_sync_codec._load_value_schema", side_effect=AssertionError("head opened body schema")):
                confirmed = self.confirm(parts, owner, candidate)
            expected = owner.snapshot if view == "full" else owner.sync_active_projection
            self.assertEqual(confirmed.export_committed(), expected)
            self.assertEqual(confirmed.tag.native.wire(), original["tag"])

    def test_explicit_codec_and_strict_expanded_paths_do_not_fallback(self):
        from compact_vectors_support import pack_baseline

        from agent_observer.sync_native import parse_message

        owner = self.owner()
        expanded = owner.sync_baseline("full")
        compact = wire(pack_baseline(parse_message(expanded, "full", "fixture")))
        with self.assertRaises(ProtocolError):
            self.cache(compact=False)[0].admit_baseline(compact)
        with self.assertRaises(ProtocolError):
            self.cache()[0].admit_baseline(expanded)
        codec = AgentCompactSyncCodec("full", encoding_id="fixture-compact/1")
        with self.assertRaises(AttributeError):
            codec._view = "active"
        self.assertEqual(codec.spec.required_profile_features, ("provisional-memberships/1",))

    def test_receipt_dictionary_checks_unused_missing_and_wrong_side_keys(self):
        baseline = self.cases["full-running"]["raw"]
        for side in ("before", "after"):
            message = copy.deepcopy(baseline)
            message["receiptRefs"][side].append(["codex", "sha256:" + "f" * 64, "history"])
            with self.subTest(side=side), self.assertRaises(ProtocolError):
                self.cache()[0].admit_baseline(wire(message))

    def test_local_schema_validator_agrees_with_independent_draft_on_actual_values(self):
        ledger = AllocationLedger()
        schema = _load_value_schema(ledger)
        try:
            for case in self.vectors["baselines"] + self.vectors["transactions"]:
                message = case["raw"]
                operation = message["kind"] == "transaction"
                for space, values in message["operations" if operation else "tables"].items():
                    reference = Draft202012Validator(value_schema(space, operation=operation))
                    for value in values:
                        reference.validate(value)
                        schema(space, value, operation)
            message = copy.deepcopy(self.cases["full-running"]["raw"])
            examples = [
                ("records", [message["tables"]["records"][0][0], [True, 1, "a" * 64, 0]]),
                ("records", [message["tables"]["records"][0][0], [1, 0, "a" * 64, False]]),
                ("bodies", ["a" * 64, []]),
                ("memberships", [[0, 1, 1], False]),
                ("metadata", ["unknown-key", None]),
                ("cohorts", [0, [[1, "a" * 64], 1, 1, 2]]),
            ]
            for space, value in examples:
                self.assertFalse(Draft202012Validator(value_schema(space)).is_valid(value))
                with self.assertRaises(ContractError):
                    schema(space, value, False)
        finally:
            schema.close()
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))

    def test_schema_load_refusal_precedes_resource_read(self):
        ledger = AllocationLedger(maximum=4096)
        codec = AgentCompactSyncCodec("full", encoding_id="fixture-compact/1")
        with patch("agent_observer.sync_compact_validation.files", side_effect=AssertionError("unpaid schema read")):
            with self.assertRaisesRegex(ProtocolError, "sync_decoded_capacity"):
                codec.open(wire(self.cases["full-running"]["raw"]), ledger)
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))

    def test_schema_and_plan_retire_without_gc_with_header_retained(self):
        ledger = AllocationLedger()
        codec = AgentCompactSyncCodec("full", encoding_id="fixture-compact/1")
        plan = codec.open(wire(self.cases["full-running"]["raw"]), ledger)
        schema = weakref.ref(plan._validator_owner)
        header = plan.header
        plan.close()
        self.assertIsNone(schema())
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))
        with self.assertRaises(ContractError):
            header.materialize()

    def test_compact_callback_supplies_no_competing_membership_cell_expansion(self):
        recorded = []
        original = AgentSyncProfile._admit

        def capture(profile, ctx):
            result = original(profile, ctx)
            recorded.append((ctx.compact_memberships, result.membership_expansion))
            return result

        with patch.object(AgentSyncProfile, "_admit", capture):
            self.staged(self.cases["active-alias-reuse"])
        self.assertEqual(recorded, [(True, ()), (True, ())])

    def test_equal_mask_assertions_preserve_genuine_changed_tokens(self):
        from compact_vectors_support import group_masks, raw_transaction_id

        for view in ("full", "active"):
            case = self.cases[view + "-lastUpdated-value-change-delta-1"]
            before = self.cases[case["before"]]["expected"]
            message = copy.deepcopy(case["raw"])
            key, (cohort, identity, birth, mask) = next(iter(group_masks(before["tables"]).items()))
            self.assertIn(key, group_masks(case["expected"]["tables"]))
            slot = next(slot for name, slot in before["tables"]["records"] if name == identity)
            old = [message["receiptRefs"]["before"].index(cohort), slot["alias"], birth[1]]
            new = [message["receiptRefs"]["after"].index(cohort), slot["alias"], birth[1]]
            self.assertFalse(message["operations"]["memberships"])
            message["operations"]["memberships"].append([old, mask, new, mask])
            message["transactionId"] = raw_transaction_id(message)
            cache, _candidate = self.staged(self.cases[case["before"]])
            candidate = cache.stage(wire(message))
            self.assertEqual(candidate.tag.native.wire(), case["expected"]["tag"])

    def test_profile_must_explicitly_advertise_normalization_feature(self):
        class Unsupported(AgentSyncProfile):
            normalization_features = ()

        profile = Unsupported(profile_schema_digest="a" * 64)
        ledger = AllocationLedger()
        with self.assertRaisesRegex(ProtocolError, "sync_codec_features"):
            OwnedSyncCache(profile, source_binding("fixture", "agents", profile.descriptor), ledger=ledger,
                           native_codec=AgentCompactSyncCodec("full", encoding_id="fixture-compact/1"))
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))

    def test_retained_plan_context_and_iterator_reject_after_stage(self):
        class Recording(AgentCompactSyncCodec):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                object.__setattr__(self, "plans", [])
                object.__setattr__(self, "contexts", [])
                object.__setattr__(self, "iterators", [])

            def open(self, raw, budget):
                plan = super().open(raw, budget)
                self.plans.append(plan)
                return plan

            def entries(self, plan, space, ctx):
                self.contexts.append(ctx)
                iterator = super().entries(plan, space, ctx)
                self.iterators.append(iterator)
                return iterator

        profile = AgentSyncProfile(profile_schema_digest="a" * 64)
        codec = Recording("full", encoding_id="fixture-compact/1")
        cache = OwnedSyncCache(profile, source_binding("fixture", "agents", profile.descriptor), native_codec=codec)
        self.caches.append(cache)
        cache.admit_baseline(wire(self.cases["full-running"]["raw"]))
        self.assertEqual(len(codec.plans), 1)
        for plan in codec.plans:
            self.assertIsNone(plan._raw)
            self.assertIsNone(plan._validator_owner)
            with self.assertRaises(ContractError):
                plan.header.materialize()
        for ctx in codec.contexts:
            with self.assertRaises(ProtocolError):
                ctx.aliases.after.get(1)
        for iterator in codec.iterators:
            with self.assertRaises(ProtocolError):
                next(iterator)

    def test_owned_schema_credit_survives_reentrant_validation_close(self):
        from agent_observer import sync_compact_validation

        ledger = AllocationLedger()
        codec = AgentCompactSyncCodec("full", encoding_id="fixture-compact/1")
        plan = codec.open(wire(self.cases["full-running"]["raw"]), ledger)
        schema = weakref.ref(plan._validator_owner)
        original = sync_compact_validation._shape
        state = {"entered": False}

        def revoke(value, spec, definitions):
            if not state["entered"]:
                state["entered"] = True
                held = ledger.reserved
                plan.close()
                self.assertEqual(ledger.reserved, held)
                self.assertIsNotNone(schema())
            return original(value, spec, definitions)

        with patch.object(sync_compact_validation, "_shape", revoke):
            with self.assertRaisesRegex(ContractError, "sync_ticket_closed"):
                next(plan._values("bodies", ledger))
        self.assertTrue(state["entered"])
        self.assertIsNone(schema())
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))

    def test_core_schema_validation_imports_no_mesh_or_third_party_validator(self):
        code = ("import sys;import agent_observer.sync_compact_validation;"
                "assert not any(x in sys.modules for x in ('mesh_plus','jsonschema',"
                "'agent_observer.observation_engine','agent_observer.service_runtime'))")
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_head_failure_retains_no_unpaid_input_with_error_held(self):
        codec = AgentCompactSyncCodec("full", encoding_id="fixture-compact/1")
        ledger = AllocationLedger()
        raw = b" " * (49152 + 1) + b"\n"
        before = sys.getrefcount(raw)
        errors = []
        try:
            codec.head(raw, ledger)
        except ContractError as error:
            errors.append(error)
        self.assertEqual(len(errors), 1)
        self.assertEqual(sys.getrefcount(raw), before)
        self.assertEqual((ledger.used, ledger.reserved, ledger.encoded_reserved), (0, 0, 0))
