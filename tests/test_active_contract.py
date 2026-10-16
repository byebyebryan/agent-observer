"""Projected native admission: exact receipts, scope authority and wire bounds."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.active_contract import (
    MAX_IDENTITIES,
    MAX_REQUEST_BYTES,
    SELECTOR,
    SELECTOR_DIGEST,
    StreamGuard,
    interface,
    parse_frame,
    parse_request,
    schema_document,
    support_matches,
    validate_frame,
    validate_request,
)
from agent_observer.contract import ContractError, canonical

ROOT = Path(__file__).resolve().parent.parent


def support(value, component="runtime"):
    source = value["sources"][0]
    receipt = next(c for c in source["components"] if c["name"] == component)
    return {
        "serviceId": value["serviceId"], "provider": source["provider"],
        "namespace": source["namespace"], "contextGeneration": source["contextGeneration"],
        "component": component, **{key: receipt[key] for key in (
            "accepted", "sampledBoottimeMs", "expiresBoottimeMs",
        )},
    }


def fixture():
    value = json.loads((ROOT / "tests/fixtures/service-v4/view.json").read_text())
    row = value.pop("snapshot")["sessions"][0]
    value.pop("serviceProtocol")
    value["sources"] = value["sources"][:1]
    value.update(activeFeedProtocol=1, selector=copy.deepcopy(SELECTOR), selectorDigest=SELECTOR_DIGEST)
    runtime = support(value)
    fields = dict.fromkeys((
        "runtime", "phase", "kind", "savedIdentity", "activity", "outcome", "workspace",
        "lastUpdated", "latestTurn",
    ))
    fields.update(runtime=copy.deepcopy(runtime), phase=copy.deepcopy(runtime), kind=copy.deepcopy(runtime))
    source = value["sources"][0]
    value["projection"] = {
        "scopes": [{
            "provider": "codex", "namespace": source["namespace"],
            "contextGeneration": source["contextGeneration"], "continuity": 1,
            "coverage": {"status": "complete", "reason": "daemon_threads_complete", "supports": [runtime]},
            "members": [{"identity": copy.deepcopy(row["identity"]), "fieldSupports": fields}],
            "uncertain": [], "nonmembers": [],
        }],
        "sessions": [row],
    }
    return value


def uncertain(value):
    scope = value["projection"]["scopes"][0]
    row = value["projection"]["sessions"].pop()
    scope["members"].clear()
    scope["coverage"].update(status="partial", reason="native_status_unresolved")
    prior = support(value)
    prior.update(accepted=1, sampledBoottimeMs=1000, expiresBoottimeMs=14000)
    entry = {
        "identity": row["identity"], "reason": "native_status_unresolved",
        "priorSupport": prior, "support": support(value), "horizonBoottimeMs": 14000,
    }
    scope["uncertain"].append(entry)
    return entry


class ActiveContractTest(unittest.TestCase):
    def test_roundtrip_selector_and_bundled_schemas(self):
        value = fixture()
        self.assertEqual(parse_frame((canonical(value) + "\n").encode(), expected_host="fixture", expected_uid=1000), value)
        self.assertEqual(SELECTOR_DIGEST, "sha256:" + hashlib.sha256(canonical(SELECTOR).encode()).hexdigest())
        for kind in ("request", "frame"):
            self.assertEqual(schema_document(kind), json.loads(
                (ROOT / f"agent_observer/contracts/active-{kind}.schema.json").read_text(),
            ))
        public = interface()
        public["selector"]["providers"].append("claude")
        self.assertEqual(interface()["selector"], SELECTOR)
        with self.assertRaisesRegex(ContractError, "active_schema_kind"):
            schema_document("snapshot")

    def test_request_is_fixed_and_has_no_dynamic_predicate(self):
        request = {
            "activeFeedProtocol": 1, "operation": "snapshot", "hostScope": "fixture",
            "selector": copy.deepcopy(SELECTOR), "selectorDigest": SELECTOR_DIGEST,
        }
        self.assertEqual(parse_request((canonical(request) + "\n").encode()), request)
        for mutate in (
            lambda v: v["selector"].update(kinds=["user"]),
            lambda v: v["selector"].update(runtimeValues=["parked"]),
            lambda v: v["selector"].update(version=True),
            lambda v: v["selector"].update(version=1.0),
            lambda v: v.update(selectorDigest="sha256:" + "0" * 64),
            lambda v: v.update(predicate="running"),
            lambda v: v.update(activeFeedProtocol=True),
            lambda v: v.update(operation="refresh"),
        ):
            bad = copy.deepcopy(request)
            mutate(bad)
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                validate_request(bad)
        for version in (True, 1.0):
            value = fixture()
            value["selector"]["version"] = version
            with self.assertRaisesRegex(ContractError, "active_selector_mismatch"):
                validate_frame(value)
        for wire in (b"{}\n{}\n", canonical(request).encode(), b" " * (MAX_REQUEST_BYTES + 1)):
            with self.assertRaises(ValueError):
                parse_request(wire)

    def test_support_matches_does_not_rebind_same_component(self):
        value = fixture()
        original = support(value)
        source = value["sources"][0]
        self.assertTrue(support_matches(original, source, value["serviceId"], 15000))
        self.assertFalse(support_matches(original, source, value["serviceId"], 20000))
        self.assertFalse(support_matches(original, source, value["serviceId"], True))
        for key, replacement in (
            ("accepted", 2), ("sampledBoottimeMs", 10001), ("expiresBoottimeMs", 20001),
            ("contextGeneration", 2), ("serviceId", "00000000-0000-0000-0000-000000000099"),
        ):
            changed = {**original, key: replacement}
            with self.subTest(key=key):
                self.assertFalse(support_matches(changed, source, value["serviceId"]))
        self.assertFalse(support_matches({}, source, value["serviceId"]))

    def test_current_member_requires_actual_exact_support(self):
        for mutate in (
            lambda fields: fields.update(runtime=None),
            lambda fields: fields["runtime"].update(accepted=2),
            lambda fields: fields["runtime"].update(expiresBoottimeMs=25000),
            lambda fields: fields["runtime"].update(contextGeneration=0),
            lambda fields: fields["kind"].update(sampledBoottimeMs=9999),
            lambda fields: fields.update(kind=None),
            lambda fields: fields.update(phase=None),
            lambda fields: fields["phase"].update(component="history"),
        ):
            value = fixture()
            fields = value["projection"]["scopes"][0]["members"][0]["fieldSupports"]
            mutate(fields)
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                validate_frame(value)

    def test_unknown_kind_is_selected_without_inventing_positive_kind_support(self):
        value = fixture()
        value["projection"]["sessions"][0]["kind"] = "unknown"
        value["projection"]["scopes"][0]["members"][0]["fieldSupports"]["kind"] = None
        validate_frame(value)

    def test_old_uncertainty_is_context_only_and_keeps_original_horizon(self):
        value = fixture()
        entry = uncertain(value)
        validate_frame(value)
        self.assertFalse(support_matches(entry["priorSupport"], value["sources"][0], value["serviceId"], 15000))
        for mutate in (
            lambda e: e.update(horizonBoottimeMs=14001),
            lambda e: e["priorSupport"].update(serviceId="00000000-0000-0000-0000-000000000099"),
            lambda e: e["priorSupport"].update(contextGeneration=2),
            lambda e: e["priorSupport"].update(component="history"),
        ):
            bad = copy.deepcopy(value)
            mutate(bad["projection"]["scopes"][0]["uncertain"][0])
            with self.assertRaises(ContractError):
                validate_frame(bad)
        bad = copy.deepcopy(value)
        bad["projection"]["scopes"][0]["coverage"]["status"] = "complete"
        with self.assertRaisesRegex(ContractError, "active_complete_uncertain"):
            validate_frame(bad)

    def test_stale_optional_value_support_cannot_be_promoted_to_current(self):
        value = fixture()
        fields = value["projection"]["scopes"][0]["members"][0]["fieldSupports"]
        fields["activity"] = {**support(value), "sampledBoottimeMs": 1000, "expiresBoottimeMs": 14000}
        row = value["projection"]["sessions"][0]
        row["activity"].update(health="stale", source="codex_rpc", lastKnownAt=1700000010000)
        validate_frame(value)
        row["activity"].update(health="current", at=1700000010000)
        row["activity"].pop("lastKnownAt")
        with self.assertRaisesRegex(ContractError, "active_support_mismatch"):
            validate_frame(value)

    def test_complete_empty_has_own_runtime_authority(self):
        value = fixture()
        scope = value["projection"]["scopes"][0]
        scope["members"].clear()
        value["projection"]["sessions"].clear()
        validate_frame(value)
        for supports in ([], [support(value, "history")], [{**support(value), "sampledBoottimeMs": 9999}]):
            bad = copy.deepcopy(value)
            bad["projection"]["scopes"][0]["coverage"]["supports"] = supports
            with self.assertRaises(ContractError):
                validate_frame(bad)
        scope["coverage"].update(status="partial", supports=[])
        validate_frame(value)

    def test_nonmember_current_lease_is_distinct_from_prior_positive_horizon(self):
        value = fixture()
        scope = value["projection"]["scopes"][0]
        row = value["projection"]["sessions"].pop()
        scope["members"].clear()
        scope["coverage"].update(status="partial", supports=[])
        negative = {
            "identity": row["identity"], "reason": "parked", "value": "parked",
            "supports": [support(value)], "horizonBoottimeMs": 50000,
        }
        scope["nonmembers"].append(negative)
        validate_frame(value)
        for mutate in (
            lambda n: n.update(supports=[]),
            lambda n: n["supports"][0].update(accepted=2),
            lambda n: n.update(reason="excluded_kind"),
            lambda n: n.update(value="child"),
            lambda n: n.update(supports=[support(value, "history")]),
        ):
            bad = copy.deepcopy(value)
            mutate(bad["projection"]["scopes"][0]["nonmembers"][0])
            with self.assertRaises(ContractError):
                validate_frame(bad)
        negative.update(reason="excluded_kind", value="system", supports=[support(value, "history")])
        validate_frame(value)

    def test_exact_scope_and_member_body_correspondence(self):
        for mutate in (
            lambda v: v["projection"]["scopes"].clear(),
            lambda v: v["projection"]["sessions"].clear(),
            lambda v: v["projection"]["scopes"][0]["members"].clear(),
            lambda v: v["projection"]["scopes"][0].update(contextGeneration=2),
            lambda v: v["projection"]["sessions"][0]["identity"].update(hostScope="other"),
            lambda v: v["projection"]["sessions"].append(copy.deepcopy(v["projection"]["sessions"][0])),
            lambda v: v["projection"]["scopes"][0]["members"].append(copy.deepcopy(v["projection"]["scopes"][0]["members"][0])),
        ):
            value = fixture()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_frame(value)

    def test_source_and_receipt_admission_is_strict(self):
        for mutate in (
            lambda v: v["sources"][0].update(provider="claude"),
            lambda v: v["sources"][0].update(configHome="relative"),
            lambda v: v["sources"][0].update(namespace="sha256:" + "0" * 64),
            lambda v: v["sources"][0]["components"].pop(),
            lambda v: v["sources"][0]["components"][0].update(accepted=2),
            lambda v: v["sources"][0]["components"][0].update(sampledBoottimeMs=16000),
            lambda v: v["sources"][0]["components"][0].update(expiresBoottimeMs=15000),
            lambda v: v["sources"][0]["components"][0].update(health="stale"),
        ):
            value = fixture()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_frame(value)

    def test_control_frames_do_not_smuggle_inventory(self):
        for kind in ("status", "heartbeat", "gap", "error"):
            value = {**fixture(), "kind": kind, "projection": None}
            validate_frame(value)
        value.update(kind="status", state="warming")
        validate_frame(value)
        value.update(kind="error", sources=[])
        validate_frame(value)
        for mutate in (
            lambda v: v.update(snapshot={}),
            lambda v: v.update(kind="heartbeat"),
            lambda v: v.update(state="warming"),
            lambda v: v.update(projection=None),
        ):
            bad = fixture()
            mutate(bad)
            with self.assertRaises(ContractError):
                validate_frame(bad)

    def test_selected_session_retains_api4_invariants(self):
        for mutate in (
            lambda row: row.update(prompt="forbidden"),
            lambda row: row.update(kind="system"),
            lambda row: row["runtime"].update(value="parked"),
            lambda row: row["runtime"].update(health="stale"),
            lambda row: row["nativeIds"].update(threadId="00000000-0000-0000-0000-000000000099"),
            lambda row: row.update(cwd="relative"),
            lambda row: row.update(blockedReasons=[]),
            lambda row: row["phase"].update(observedAt=1),
        ):
            value = fixture()
            mutate(value["projection"]["sessions"][0])
            with self.assertRaises(ContractError):
                validate_frame(value)

    def test_timing_cannot_bind_to_unrelated_receipt(self):
        value = fixture()
        row = value["projection"]["sessions"][0]
        row["lastUpdated"].update(
            at=1700000010000, timestampPrecisionMs=1000, observedAt=1700000020000,
            source="codex_rpc", health="current", reason="native_timestamp",
            receipt={"component": "runtime", "sampledBoottimeMs": 10000,
                     "observedBoottimeMs": 15000, "contextGeneration": 1},
        )
        fields = value["projection"]["scopes"][0]["members"][0]["fieldSupports"]
        fields["lastUpdated"] = support(value)
        validate_frame(value)
        for key, replacement in (("component", "history"), ("sampledBoottimeMs", 9999), ("observedBoottimeMs", 20000)):
            bad = copy.deepcopy(value)
            bad["projection"]["sessions"][0]["lastUpdated"]["receipt"][key] = replacement
            with self.assertRaises(ContractError):
                validate_frame(bad)

    def test_stream_order_gap_scope_clock_and_single_admission(self):
        value = fixture()
        wire = (canonical(value) + "\n").encode()
        guard = StreamGuard(expected_host="fixture", expected_uid=1000)
        with patch("agent_observer.active_contract.validate_frame", wraps=validate_frame) as validate:
            self.assertEqual(guard.parse(wire), value)
            self.assertEqual(validate.call_count, 1)
        with self.assertRaisesRegex(ContractError, "active_stream_order"):
            guard.accept(value)
        guard.accept({**value, "sequence": 2, "kind": "gap", "projection": None})
        with self.assertRaisesRegex(ContractError, "active_resync_required"):
            guard.accept({**value, "sequence": 3, "kind": "heartbeat", "projection": None})
        guard.accept({**value, "sequence": 3, "kind": "resync"})
        for changes in (
            {"sequence": 4, "serviceId": "00000000-0000-0000-0000-000000000099"},
            {"sequence": 4, "clockDomain": "other"},
            {"sequence": 4, "emittedBoottimeMs": 14000},
        ):
            with self.assertRaises(ContractError):
                guard.accept({**value, **changes})
        for bad_wire in (wire[:-1], wire + wire, wire.replace(b'"uid":1000', b'"uid":true')):
            with self.assertRaises(ValueError):
                StreamGuard().parse(bad_wire)
        with self.assertRaisesRegex(ContractError, "active_host_mismatch"):
            parse_frame((canonical(value) + "\n").encode(), expected_host="other")
        with self.assertRaisesRegex(ContractError, "active_uid_mismatch"):
            validate_frame(value, expected_uid=1001)

    def test_identity_ledger_and_frame_capacity_are_independent(self):
        value = fixture()
        entry = uncertain(value)
        scope = value["projection"]["scopes"][0]
        scope["uncertain"] = [entry] * (MAX_IDENTITIES + 1)
        with self.assertRaises(ContractError):
            validate_frame(value)
        value = fixture()
        with patch("agent_observer.active_contract.MAX_LEDGER_BYTES", 100):
            with self.assertRaisesRegex(ContractError, "active_ledger_limit"):
                validate_frame(value)
        with patch("agent_observer.active_contract.MAX_FRAME_BYTES", 100):
            with self.assertRaisesRegex(ContractError, "active_frame_limit"):
                validate_frame(value)
        with patch("agent_observer.active_contract.MAX_OVERHEAD_BYTES", 100):
            with self.assertRaisesRegex(ContractError, "active_overhead_limit"):
                validate_frame(value)

    def test_pure_import_has_no_engine_service_or_mesh_dependency(self):
        code = (
            "import sys;import agent_observer.active_contract;"
            "assert not any(x in sys.modules for x in "
            "['agent_observer.collection','agent_observer.engine','agent_observer.service_runtime',"
            "'agent_observer.codex_snapshot','mesh_plus'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_cli_active_exports_are_pure_and_match_packaged_contract(self):
        code = """
import builtins,json,socket,subprocess,sys
original=builtins.__import__
blocked=('mesh_plus','agent_observer.collection','agent_observer.provider',
         'agent_observer.adapters','agent_observer.codex_snapshot',
         'agent_observer.codex_rpc','agent_observer.service_runtime',
         'agent_observer.service_state','agent_observer.service_client',
         'agent_observer.observation_engine','agent_observer.mesh_active_profile',
         'agent_observer.mesh_active_source','agent_observer.mesh_active_read')
relative={name.split('.')[-1] for name in blocked if name.startswith('agent_observer.')}
def limited(name,globals=None,locals=None,fromlist=(),level=0):
    if any(name==item or name.startswith(item+'.') for item in blocked) or (level and name in relative):
        raise AssertionError('forbidden_import:'+name)
    return original(name,globals,locals,fromlist,level)
def forbidden(*args,**kwargs):
    raise AssertionError('unexpected_acquisition')
builtins.__import__=limited
socket.socket=forbidden
subprocess.Popen=forbidden
from agent_observer.cli import main
try:
    result=main(json.loads(sys.argv[1]))
finally:
    assert not any(name==item or name.startswith(item+'.') for name in sys.modules for item in blocked)
raise SystemExit(result)
"""
        cases = [
            (["service", "active-api"], interface()),
            (["service", "active-schema", "--kind", "request"], schema_document("request")),
            (["service", "active-schema", "--kind", "frame"], schema_document("frame")),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", code, json.dumps(arguments)],
                    cwd=ROOT, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(json.loads(result.stdout), expected)
        for arguments in (
            ["service", "active-schema"],
            ["service", "active-schema", "--kind", "snapshot"],
        ):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", code, json.dumps(arguments)],
                    cwd=ROOT, capture_output=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr.decode())
                self.assertFalse(result.stdout)
                self.assertNotIn(b"forbidden_import", result.stderr)
                self.assertNotIn(b"unexpected_acquisition", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "independent schema validator unavailable")
    def test_independent_structural_schema_validation(self):
        import jsonschema
        schema = schema_document("frame")
        value = fixture()
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
        value["projection"]["scopes"][0]["coverage"]["supports"][0]["accepted"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(value)
