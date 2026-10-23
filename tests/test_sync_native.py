"""Native sync ticket grammar, binding, head limits and acquisition-only meaning."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.contract import ContractError
from agent_observer.sync_commitment import canonical, native_binding_digest
from agent_observer.sync_native import (
    MAX_HEAD_COHORT_BYTES,
    MAX_HEAD_FIXED_BYTES,
    MAX_HEAD_RECEIPT_BYTES,
    TABLES,
    descriptor,
    parse_message,
    schema_document,
    validate_message,
)
from agent_observer.sync_projection_schema import SELECTOR

ROOT = Path(__file__).resolve().parents[1]
EPOCH = "00000000-0000-4000-8000-000000000001"
BOOT = "00000000-0000-4000-8000-000000000002"
ROOT_HASH = "ab" * 32


def baseline(view="full"):
    original = json.loads((ROOT / "tests/fixtures/service-v4/view.json").read_text())
    service_source = original["sources"][0]
    source = {k: v for k, v in service_source.items() if k != "components"}
    source["runtimeContext"] = original["snapshot"]["sources"][0]["runtime"]
    selected = descriptor(view)
    binding = {
        **{key: selected[key] for key in ("protocol", "version", "schemaDigest", "view")},
        "ownerEpoch": EPOCH, "bootId": BOOT, "clockDomain": "time:[123]", "uid": 1000,
        "hostScope": "fixture", "selector": None if view == "full" else copy.deepcopy(SELECTOR),
        "sourceContexts": [source],
        "scopeContinuity": [] if view == "full" else [["codex", source["namespace"], 1]],
    }
    tag = [native_binding_digest(binding), 1, ROOT_HASH]
    tables = {name: [] for name in TABLES}
    for component in service_source["components"]:
        key = [source["provider"], source["namespace"], component["name"]]
        tables["receipts"].append([key, {"serviceId": EPOCH, "contextGeneration": 1, **component}])
    return {"kind": "baseline", "descriptor": selected, "nativeBinding": binding,
            "tag": tag, "cursor": [EPOCH, 1, ROOT_HASH], "tables": tables}


def owner_clock():
    return {"ownerEpoch": EPOCH, "bootId": BOOT, "clockDomain": "time:[123]",
            "uid": 1000, "hostScope": "fixture", "boottimeMs": 15000}


def head(view="full"):
    base = baseline(view)
    result = {
        "kind": "head", "descriptor": base["descriptor"], "nativeBindingDigest": base["tag"][0],
        "tag": base["tag"], "challenge": {"nonce": "a" * 32}, "ownerClock": owner_clock(),
        "originalReceipts": base["tables"]["receipts"], "cohortHeads": [], "attenuation": [],
    }
    for key, receipt in result["originalReceipts"]:
        result["cohortHeads"].append([copy.deepcopy(key), {
            "seal": [1, "cd" * 32, 1], "accepted": receipt["accepted"],
            "sampledBoottimeMs": receipt["sampledBoottimeMs"],
            "expiresBoottimeMs": receipt["expiresBoottimeMs"],
        }])
        result["attenuation"].append([copy.deepcopy(key), 5000])
    return result


def transaction(view="full"):
    base = baseline(view)
    return {
        "kind": "transaction", "descriptor": base["descriptor"],
        "nativeBindingDigest": base["tag"][0], "transactionId": "ef" * 32,
        "baseTag": base["tag"], "resultTag": [base["tag"][0], 2, "12" * 32],
        "baseCursor": base["cursor"], "resultCursor": [EPOCH, 2, "12" * 32],
        "operations": {name: [] for name in TABLES},
    }


def control(view="full", status="complete"):
    base = baseline(view)
    return {"kind": "control", "descriptor": base["descriptor"], "status": status,
            "reason": "service_alive", "tag": base["tag"], "cursor": base["cursor"],
            "ownerClock": owner_clock()}


class SyncNativeTest(unittest.TestCase):
    def test_transactions_cannot_collapse_multiple_native_generations(self):
        value = transaction()
        value["resultTag"][1] = value["resultCursor"][1] = 3
        with self.assertRaisesRegex(ContractError, "sync_transaction_binding"):
            validate_message(value, "full")

    def test_exact_outer_roundtrips_both_views_and_all_message_kinds(self):
        for view in ("full", "active"):
            for make in (baseline, transaction, head, control):
                value = make(view)
                self.assertIs(validate_message(value, view, "fixture"), value)
                self.assertEqual(parse_message(canonical(value) + b"\n", view, "fixture"), value)
        fresh = descriptor("active")
        fresh["tables"].clear()
        self.assertEqual(tuple(descriptor("active")["tables"]), TABLES)

    def test_bundled_schema_and_closed_descriptor_binding(self):
        bundled = json.loads((ROOT / "agent_observer/contracts/sync-frame.schema.json").read_text())
        self.assertEqual(schema_document(), bundled)
        exported = schema_document()
        exported["$defs"]["value"]["anyOf"].clear()
        self.assertEqual(schema_document(), bundled)
        for mutate in (
            lambda v: v["descriptor"].update(version=True),
            lambda v: v["descriptor"].update(schemaDigest="ff" * 32),
            lambda v: v["descriptor"].update(view="active"),
            lambda v: v["descriptor"]["tables"].reverse(),
            lambda v: v.update(extra="unknown"),
        ):
            value = baseline()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_message(value, "full")

    def test_native_binding_original_context_source_and_selector_are_exact(self):
        for mutate in (
            lambda b: b.update(selector=SELECTOR),
            lambda b: b.update(clockDomain="time:123"),
            lambda b: b["sourceContexts"][0].update(configHome="relative"),
            lambda b: b["sourceContexts"][0].update(namespace="sha256:" + "f" * 64),
            lambda b: b["sourceContexts"][0]["runtimeContext"].update(prompt="forbidden"),
            lambda b: b["sourceContexts"].append(copy.deepcopy(b["sourceContexts"][0])),
        ):
            value = baseline()
            mutate(value["nativeBinding"])
            with self.assertRaises(ContractError):
                validate_message(value, "full")
        value = baseline("active")
        value["nativeBinding"]["selector"]["version"] = True
        with self.assertRaises(ContractError):
            validate_message(value, "active")
        value = baseline("active")
        value["nativeBinding"]["scopeContinuity"].clear()
        with self.assertRaisesRegex(ContractError, "sync_scope_continuity"):
            validate_message(value, "active")

    def test_tag_cursor_owner_and_host_binding(self):
        for make in (baseline, head, control):
            with self.subTest(make=make), self.assertRaisesRegex(ContractError, "sync_host_mismatch"):
                validate_message(make(), "full", "foreign")
        for mutate in (
            lambda v: v["tag"].__setitem__(0, "ff" * 32),
            lambda v: v["cursor"].__setitem__(0, BOOT),
            lambda v: v["cursor"].__setitem__(1, 2),
            lambda v: v["tag"].__setitem__(1, True),
            lambda v: v["tag"].__setitem__(1, 2**64),
        ):
            value = baseline()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_message(value, "full")

    def test_all_eight_tables_and_unique_entries_are_required(self):
        for mutate in (
            lambda v: v["tables"].pop("memberships"),
            lambda v: v["tables"].update(unknown=[]),
            lambda v: v["tables"]["metadata"].extend([["same", 1], ["same", 2]]),
            lambda v: v["tables"]["bodies"].append(["only-key"]),
            lambda v: v["tables"]["receipts"][0][1].update(sampledBoottimeMs=None),
            lambda v: v["tables"]["receipts"][0][1].update(serviceId=BOOT),
        ):
            value = baseline()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_message(value, "full")

    def test_receipt_counters_preserve_history_promotions_and_direct_accepts(self):
        value = baseline()
        # History acceptance may also promote runtime without a separate
        # runtime attempt. Attempts and accepted observations are independent.
        for _, receipt in value["tables"]["receipts"]:
            receipt.update(attempts=0, accepted=2)
        before = copy.deepcopy(value["tables"]["receipts"])
        validate_message(value, "full")
        self.assertEqual(value["tables"]["receipts"], before)
        value = head()
        for _, receipt in value["originalReceipts"]:
            receipt.update(attempts=0, accepted=2)
        for _, cohort in value["cohortHeads"]:
            cohort["accepted"] = 2
        validate_message(value, "full")

    def test_public_history_accept_preserves_independent_component_counters(self):
        from test_service_state import provider_snapshot

        from agent_observer.service_state import ServiceState

        state = ServiceState(
            host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000, clock=lambda: 15000, boot_id=BOOT, clock_domain="time:[123]",
        )
        state.accept("codex", "history", provider_snapshot("codex"), sampled_ms=15000, ttl_ms=5000)
        self.assertEqual(state.receipts["codex"]["history"].attempts, 0)
        self.assertEqual(state.receipts["codex"]["history"].accepted, 1)
        self.assertEqual(state.receipts["codex"]["runtime"].accepted, 1)
        original = {name: (receipt.attempts, receipt.accepted)
                    for name, receipt in state.receipts["codex"].items()}
        for view in ("full", "active"):
            value = parse_message(state.sync_baseline(view), view, "fixture")
            self.assertTrue(value["tables"]["receipts"])
            for key, receipt in value["tables"]["receipts"]:
                self.assertEqual((receipt["attempts"], receipt["accepted"]), original[key[2]])
            parse_message(state.sync_head(view, {"nonce": "a" * 32}), view, "fixture")

    def test_transaction_outer_checks_do_not_masquerade_as_domain_or_root_admission(self):
        value = transaction()
        value["operations"]["bodies"] = [["put", "untrusted-body", None, {"unadmitted": True}]]
        # This is a grammar/acquisition ticket. The domain callback and generic
        # expected-value/root verification must reject it before state use.
        with patch("agent_observer.contract.validate_snapshot", side_effect=AssertionError("legacy frame")):
            self.assertIs(validate_message(value, "full"), value)
        for operation in (
            ["put", "key", True, {}], ["remove", "key", None], ["remove", "key"],
            [{"bad": "operation"}, "key", "aa" * 32], ["unknown", "key", "aa" * 32],
        ):
            bad = transaction()
            bad["operations"]["metadata"] = [operation]
            with self.assertRaises(ContractError):
                validate_message(bad, "full")
        value["operations"]["bodies"].append(["remove", "untrusted-body", "ab" * 32])
        with self.assertRaisesRegex(ContractError, "sync_duplicate_operation"):
            validate_message(value, "full")
        for mutate in (
            lambda v: v["resultTag"].__setitem__(1, 1),
            lambda v: v["resultTag"].__setitem__(0, "ff" * 32),
            lambda v: v["resultCursor"].__setitem__(0, BOOT),
        ):
            value = transaction()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_message(value, "full")

    def test_head_original_receipts_cohorts_and_attenuation_are_bound(self):
        for mutate in (
            lambda v: v["attenuation"][0].__setitem__(1, 5001),
            lambda v: v["attenuation"].pop(),
            lambda v: v["cohortHeads"][0][1].update(accepted=2),
            lambda v: v["cohortHeads"][0][1].update(receipt=v["cohortHeads"][0][0]),
            lambda v: v["cohortHeads"][0][1]["seal"].__setitem__(0, True),
            lambda v: v["originalReceipts"][0][1].update(serviceId=BOOT),
            lambda v: v["ownerClock"].update(boottimeMs=9999),
            lambda v: v["challenge"].update(float=1.0),
        ):
            value = head()
            mutate(value)
            with self.assertRaises(ValueError):
                validate_message(value, "full")
        value = head()
        value["ownerClock"]["boottimeMs"] = 25000
        for entry in value["attenuation"]:
            entry[1] = 0
        validate_message(value, "full")

    def test_max_32_receipt_cohort_encoded_boundary_vector(self):
        value = head()
        value["originalReceipts"], value["cohortHeads"], value["attenuation"] = [], [], []
        for index in range(32):
            key = ["codex", "sha256:" + format(index, "064x"), "runtime"]
            receipt = {
                "serviceId": EPOCH, "contextGeneration": 2**53 - 1, "name": "runtime",
                "attempts": 2**53 - 1, "accepted": 2**53 - 1,
                "sampledBoottimeMs": 4_000_000_000_000 - 1, "expiresBoottimeMs": 4_000_000_000_000,
                "health": "current", "lastResult": "x" * 128, "inFlight": False,
            }
            value["originalReceipts"].append([key, receipt])
            value["cohortHeads"].append([copy.deepcopy(key), {
                "seal": [2**64 - 1, "ff" * 32, 36864], "accepted": receipt["accepted"],
                "sampledBoottimeMs": receipt["sampledBoottimeMs"],
                "expiresBoottimeMs": receipt["expiresBoottimeMs"],
            }])
            value["attenuation"].append([copy.deepcopy(key), 0])
        value["ownerClock"]["boottimeMs"] = 2**53 - 1
        validate_message(value, "full")
        self.assertLessEqual(max(len(canonical(e)) + 1 for e in value["originalReceipts"]), MAX_HEAD_RECEIPT_BYTES)
        self.assertLessEqual(max(len(canonical(e)) + 1 for e in value["cohortHeads"]), MAX_HEAD_COHORT_BYTES)
        self.assertLessEqual(len(canonical({**value, "originalReceipts": [], "cohortHeads": []})) + 1,
                             MAX_HEAD_FIXED_BYTES)
        value["cohortHeads"].append(copy.deepcopy(value["cohortHeads"][0]))
        with self.assertRaises(ContractError):
            validate_message(value, "full")

    def test_head_fixed_entry_and_combined_limits_fail_without_truncation(self):
        value = head()
        before = copy.deepcopy(value)
        for constant in ("MAX_HEAD_COHORT_BYTES", "MAX_HEAD_RECEIPT_BYTES", "MAX_HEAD_FIXED_BYTES", "MAX_HEAD_BYTES"):
            with self.subTest(constant=constant), patch("agent_observer.sync_native." + constant, 1):
                with self.assertRaisesRegex(ContractError, "sync_.*limit"):
                    validate_message(value, "full")
        self.assertEqual(value, before)

    def test_controls_nullable_pair_liveness_and_gap_are_explicit(self):
        for status in ("complete", "baseline_required", "gap", "error", "heartbeat", "warming"):
            validate_message(control(status=status), "full")
        value = control(status="warming")
        value.update(tag=None, cursor=None)
        validate_message(value, "full")
        for mutate in (
            lambda v: v.update(status="complete"),
            lambda v: v.update(cursor=[EPOCH, 1, ROOT_HASH]),
            lambda v: v.update(status="unknown"),
            lambda v: v["ownerClock"].update(uid=True),
            lambda v: v["ownerClock"].update(clockDomain="other"),
        ):
            bad = copy.deepcopy(value)
            mutate(bad)
            with self.assertRaises(ContractError):
                validate_message(bad, "full")

    def test_native_wire_is_strict_bounded_json(self):
        wire = canonical(baseline()) + b"\n"
        for raw in (wire[:-1], wire + wire, wire.replace(b'"version":1', b'"version":1,"version":1')):
            with self.assertRaises(ValueError):
                parse_message(raw, "full")
        for value in (1.0, b"bytes", 2**64):
            frame = baseline()
            frame["tables"]["metadata"] = [["invalid", value]]
            with self.assertRaises(ContractError):
                validate_message(frame, "full")
        frame = baseline()
        frame["tables"]["metadata"] = [["cycle", frame]]
        with self.assertRaisesRegex(ContractError, "sync_message_cycle"):
            validate_message(frame, "full")

    def test_native_import_uses_no_mesh_provider_or_legacy_runtime(self):
        code = (
            "import sys;from agent_observer.sync_native import descriptor;descriptor('active');"
            "assert not any(name in sys.modules for name in "
            "['mesh_plus','agent_observer.collection','agent_observer.codex_snapshot',"
            "'agent_observer.service_runtime','agent_observer.observation_engine'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "independent schema validator unavailable")
    def test_independent_schema_matches_outer_grammar(self):
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema_document())
        validator.check_schema(schema_document())
        for view in ("full", "active"):
            for make in (baseline, transaction, head, control):
                validator.validate(make(view))
        value = head()
        value["cohortHeads"][0][1]["receipt"] = value["cohortHeads"][0][0]
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(value)
