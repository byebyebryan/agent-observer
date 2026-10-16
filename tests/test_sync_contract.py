"""Lossless typed row split, independent field vectors and local sync requests."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import contract
from agent_observer.contract import ContractError, validate_snapshot
from agent_observer.sync_contract import (
    ACTIVE_SYNC_PROTOCOL,
    FIELD_NAMES,
    MAX_CHALLENGE_BYTES,
    MAX_REQUEST_BYTES,
    MOVED_PATHS,
    PROTOCOLS,
    SAFE_INTEGER,
    SYNC_PROTOCOL,
    admit_record,
    field_tokens,
    field_value,
    field_values,
    join_record,
    parse_request,
    schema_document,
    split_record,
    validate_record,
    validate_request,
)

ROOT = Path(__file__).resolve().parents[1]
EPOCH = "00000000-0000-4000-8000-000000000001"
DIGEST = "12" * 32
TAG = ["ab" * 32, 1, "cd" * 32]


def fixture():
    return json.loads((ROOT / "tests/fixtures/service-v4/view.json").read_text())["snapshot"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def request(operation="baseline", protocol=SYNC_PROTOCOL):
    result = {"syncProtocol": protocol, "version": 1, "operation": operation, "hostScope": "fixture"}
    if operation == "changes":
        result.update(baseTag=copy.deepcopy(TAG), targetTag=[TAG[0], 2, "ef" * 32],
                      maxTransactions=4, maxBytes=8 * 1024 * 1024)
    elif operation == "head":
        result["challenge"] = {"nonce": "a" * 32, "source": {"requestId": "b" * 32},
                               "scope": [None, True, -1, "é"]}
    elif operation == "watch":
        result["cursor"] = [EPOCH, TAG[1], TAG[2]]
    return result


class SyncRecordContractTest(unittest.TestCase):
    def test_split_admission_validates_one_complete_row_and_detaches_both_outputs(self):
        view = fixture()
        for original in view["sessions"]:
            content, observations = split_record(original)
            with patch("agent_observer.contract._SESSION_SHAPE", wraps=contract._SESSION_SHAPE) as validate:
                row, values = admit_record(content, observations, view["host"]["authority"], view["sources"])
            self.assertEqual(validate.call_count, 1)
            self.assertEqual(row, original)
            self.assertEqual(values, field_values(content))
            row["runtime"]["reason"] = "changed row"
            values["runtime"]["reason"] = "changed token input"
            self.assertEqual(join_record(content, observations), original)

    def test_split_admission_rejects_partition_overrides_and_native_semantic_errors(self):
        view = fixture()
        original = view["sessions"][0]
        changes = (
            lambda c, o: c["runtime"].update(health="current"),
            lambda c, o: o["runtime"].update(reason="override"),
            lambda c, o: o["runtime"].pop("health"),
            lambda c, o: o.update(unknown={}),
            lambda c, o: c["identity"].update(hostScope="foreign"),
            lambda c, o: c["nativeIds"].update(threadId=EPOCH),
            lambda c, o: c.update(phase=None),
            lambda c, o: c.pop("phase"),
        )
        for change in changes:
            content, observations = split_record(original)
            change(content, observations)
            with self.subTest(change=change), self.assertRaises(ContractError):
                admit_record(content, observations, view["host"]["authority"], view["sources"])
        row = copy.deepcopy(original)
        row.update(phase=None, blockedReasons=[])
        row["runtime"]["value"] = "parked"
        content, observations = split_record(row)
        self.assertEqual(admit_record(content, observations, view["host"]["authority"], view["sources"])[0], row)

    def test_every_fixture_row_roundtrips_detached_without_changing_old_schemas(self):
        view = fixture()
        for row in view["sessions"]:
            before = copy.deepcopy(row)
            content, observations = split_record(row)
            self.assertEqual(join_record(content, observations), before)
            self.assertEqual(set(observations), set(MOVED_PATHS) - ({"phase"} if row["phase"] is None else set()))
            for name, paths in MOVED_PATHS.items():
                if row[name] is None:
                    continue
                self.assertEqual(observations[name], {key: row[name][key] for key in paths})
                self.assertTrue(set(paths).isdisjoint(content[name]))
            joined = join_record(content, observations)
            joined["runtime"]["reason"] = "caller_changed"
            content["title"] = "caller content"
            observations["runtime"]["health"] = "stale"
            self.assertEqual(row, before)

    def test_only_reviewed_paths_move_native_outcome_event_time_stays_content(self):
        row = fixture()["sessions"][0]
        row["outcome"].update(value="failed", health="current", observedAt=1700000000123,
                              source="native_outcome", clock="native", reason="native_failed")
        row["runtime"]["lastKnownValue"] = "running"
        row["activity"]["lastKnownAt"] = None
        content, observations = split_record(row)
        self.assertEqual(content["outcome"]["observedAt"], 1700000000123)
        self.assertNotIn("observedAt", observations["outcome"])
        self.assertIn("lastKnownValue", content["runtime"])
        self.assertIn("lastKnownAt", content["activity"])
        self.assertIsNone(content["activity"]["lastKnownAt"])
        self.assertEqual(join_record(content, observations), row)
        self.assertEqual(content["runtime"]["reason"], row["runtime"]["reason"])

    def test_missing_and_explicit_null_are_not_interchangeable(self):
        row = fixture()["sessions"][0]
        content, observations = split_record(row)
        absent = field_value(content, "activity")
        row["activity"]["lastKnownAt"] = None
        present, moved = split_record(row)
        self.assertNotEqual(absent, field_value(present, "activity"))
        self.assertEqual(join_record(present, moved), row)
        for name, paths in MOVED_PATHS.items():
            if name not in observations:
                continue
            for key in paths:
                bad = copy.deepcopy(observations)
                bad[name].pop(key)
                with self.subTest(name=name, key=key), self.assertRaises(ContractError):
                    join_record(content, bad)
        bad = copy.deepcopy(content)
        bad["runtime"]["health"] = "current"
        with self.assertRaises(ContractError):
            join_record(bad, observations)

    def test_null_phase_has_no_observation_object_and_null_token_value(self):
        row = fixture()["sessions"][0]
        row.update(phase=None, blockedReasons=[])
        row["runtime"]["value"] = "parked"
        content, observations = split_record(row)
        self.assertNotIn("phase", observations)
        self.assertIsNone(field_value(content, "phase"))
        self.assertEqual(join_record(content, observations), row)
        observations["phase"] = {"health": "current", "observedAt": 1700000000000}
        with self.assertRaisesRegex(ContractError, "sync_phase_observations"):
            join_record(content, observations)
        content, observations = split_record(fixture()["sessions"][0])
        observations.pop("phase")
        with self.assertRaisesRegex(ContractError, "sync_phase_observations"):
            join_record(content, observations)

    def test_exact_nine_field_extractions(self):
        row = fixture()["sessions"][0]
        content, _ = split_record(row)
        values = field_values(content)
        self.assertEqual(tuple(values), FIELD_NAMES)
        self.assertEqual(values, {
            "runtime": content["runtime"],
            "phase": {"phase": content["phase"], "blockedReasons": row["blockedReasons"]},
            "kind": row["kind"],
            "savedIdentity": {"inventory": row["inventory"], "hasSavedHistory": row["hasSavedHistory"]},
            "activity": content["activity"], "outcome": content["outcome"],
            "workspace": {"workspace": row["workspace"], "cwd": row["cwd"], "cwdSource": row["cwdSource"]},
            "lastUpdated": content["lastUpdated"], "latestTurn": content["latestTurn"],
        })
        values["runtime"]["reason"] = "mutated"
        self.assertNotEqual(content["runtime"]["reason"], "mutated")
        with self.assertRaisesRegex(ContractError, "sync_field_unknown"):
            field_value(content, "title")

    def test_independent_exact_field_token_vectors_and_birth_binding(self):
        content, _ = split_record(fixture()["sessions"][0])
        identity = list(contract.identity_key(content["identity"]))
        birth = [EPOCH, 7]
        tokens = field_tokens(DIGEST, identity, birth, content)

        def framed(data):
            return len(data).to_bytes(8, "big") + data

        for name, value in field_values(content).items():
            expected = hashlib.sha256(
                b"mesh-sync-field\0" + framed(bytes.fromhex(DIGEST))
                + framed(canonical(identity)) + framed(canonical(birth))
                + framed(name.encode()) + framed(canonical(value)),
            ).hexdigest()
            self.assertEqual(tokens[name], expected)
        changed = copy.deepcopy(content)
        changed["title"] += " renamed"
        self.assertEqual(tokens, field_tokens(DIGEST, identity, birth, changed))
        self.assertNotEqual(tokens, field_tokens(DIGEST, identity, [EPOCH, 8], content))
        content["phase"]["reason"] = "native_error"
        changed_tokens = field_tokens(DIGEST, identity, birth, content)
        self.assertNotEqual(tokens["phase"], changed_tokens["phase"])
        self.assertEqual(tokens["runtime"], changed_tokens["runtime"])
        with self.assertRaisesRegex(ContractError, "sync_field_identity"):
            field_tokens(DIGEST, ["other", *identity[1:]], birth, content)
        with self.assertRaises(ContractError):
            field_tokens(DIGEST, identity, [EPOCH, True], content)

    def test_moved_observations_change_without_rehashing_stable_field_values(self):
        row = fixture()["sessions"][0]
        content, observations = split_record(row)
        row["runtime"]["observedAt"] += 10
        row["phase"]["observedAt"] += 10
        changed, moved = split_record(row)
        self.assertEqual(content, changed)
        self.assertNotEqual(observations, moved)
        self.assertEqual(field_values(content), field_values(changed))

    def test_changed_row_native_errors_match_legacy_whole_view_errors(self):
        changes = (
            lambda row: row.update(prompt="forbidden"),
            lambda row: row["identity"].update(hostScope="foreign"),
            lambda row: row["nativeIds"].update(threadId=EPOCH),
            lambda row: row.update(cwd="relative"),
            lambda row: row["runtime"].update(observedAt=None),
            lambda row: row["activity"].update(at=1),
            lambda row: row["lastUpdated"].update(at=1),
            lambda row: row["runtime"].update(value="parked"),
            lambda row: row["phase"].update(source="different"),
            lambda row: row.update(blockedReasons=[]),
            lambda row: row.update(blockedReasons=["approval", "approval"]),
        )
        for change in changes:
            view = fixture()
            row = view["sessions"][0]
            change(row)
            with self.subTest(change=change):
                with self.assertRaises(ContractError) as legacy:
                    validate_snapshot(view)
                with patch("agent_observer.contract.validate_snapshot", side_effect=AssertionError("whole view")):
                    with self.assertRaises(ContractError) as incremental:
                        validate_record(row, view["host"]["authority"], view["sources"])
                self.assertEqual(str(legacy.exception), str(incremental.exception))
        view = fixture()
        index = {(s["provider"], s["namespace"]): s for s in view["sources"]}
        for row in view["sessions"]:
            self.assertIs(validate_record(row, view["host"]["authority"], index), row)

    def test_legacy_snapshot_does_not_validate_each_row_shape_twice(self):
        view = fixture()
        with patch("agent_observer.contract._SNAPSHOT_SHAPE", wraps=contract._SNAPSHOT_SHAPE) as whole, \
                patch("agent_observer.contract._SESSION_SHAPE", wraps=contract._SESSION_SHAPE) as individual:
            validate_snapshot(view)
        self.assertEqual(whole.call_count, 1)
        self.assertEqual(individual.call_count, 0)


class SyncRequestContractTest(unittest.TestCase):
    def test_requests_roundtrip_both_explicit_views_and_all_operations(self):
        for protocol in PROTOCOLS:
            for operation in ("baseline", "changes", "head", "watch"):
                value = request(operation, protocol)
                self.assertEqual(parse_request(canonical(value) + b"\n", expected_host="fixture",
                                               expected_protocol=protocol), value)
        with self.assertRaisesRegex(ContractError, "sync_protocol_mismatch"):
            validate_request(request(), expected_protocol=ACTIVE_SYNC_PROTOCOL)
        with self.assertRaisesRegex(ContractError, "sync_host_mismatch"):
            validate_request(request(), expected_host="other")

    def test_bundled_schema_and_detached_schema_exports(self):
        expected = json.loads((ROOT / "agent_observer/contracts/sync-request.schema.json").read_text())
        self.assertEqual(schema_document(), expected)
        changed = schema_document()
        changed["$defs"]["challengeValue"]["anyOf"][-1]["additionalProperties"].clear()
        self.assertEqual(schema_document(), expected)
        with self.assertRaisesRegex(ContractError, "sync_schema_kind"):
            schema_document("baseline")

    def test_closed_operation_shapes_types_and_catchup_limits(self):
        for value in (
            {**request(), "view": "active"},
            {**request(), "syncProtocol": "agent-observer.sync/1"},
            {**request(), "version": True},
            {**request(), "operation": "snapshot"},
            {**request("changes"), "maxTransactions": 5},
            {**request("changes"), "maxTransactions": True},
            {**request("changes"), "maxBytes": 0},
            {**request("changes"), "maxBytes": 8 * 1024 * 1024 + 1},
            {**request("watch"), "cursor": [EPOCH, 1]},
            {**request("watch"), "cursor": ["bad", 1, TAG[2]]},
            {**request("changes"), "baseTag": [TAG[0], 1.0, TAG[2]]},
            {**request("changes"), "targetTag": [TAG[0], True, TAG[2]]},
            {**request("head"), "challenge": []},
        ):
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_request(value)
        value = request("watch")
        value["cursor"][1] = 2**64 - 1
        validate_request(value)
        value["cursor"][1] += 1
        with self.assertRaises(ContractError):
            validate_request(value)

    def test_head_challenge_is_opaque_strict_bounded_and_not_interpreted(self):
        value = request("head")
        value["challenge"] = {"operation": "unknown", "hostScope": "informational", "": "", "null": None}
        self.assertIs(validate_request(value), value)
        exact = {"x": "a" * (MAX_CHALLENGE_BYTES - len(canonical({"x": ""})))}
        self.assertEqual(len(canonical(exact)), MAX_CHALLENGE_BYTES)
        validate_request({**value, "challenge": exact})
        for challenge in (
            {"value": 1.0}, {"value": SAFE_INTEGER + 1}, {"value": -(SAFE_INTEGER + 1)},
            {"value": b"bytes"}, {1: "nonstring key"}, {"value": (1, 2)},
            {"value": "x" * MAX_CHALLENGE_BYTES}, {"values": [None] * 256},
        ):
            with self.subTest(challenge=type(challenge)), self.assertRaises(ValueError):
                validate_request({**value, "challenge": challenge})
        nested = None
        for _ in range(9):
            nested = [nested]
        with self.assertRaisesRegex(ContractError, "sync_challenge_limit"):
            validate_request({**value, "challenge": {"nested": nested}})
        with self.assertRaises(ValueError):
            validate_request({**value, "challenge": {"bad": "\ud800"}})

    def test_native_wire_limits_duplicate_keys_and_line_framing(self):
        valid = canonical(request()) + b"\n"
        for wire in (
            valid[:-1], valid + valid, valid[:-1] + b"\r\n", b" " * (MAX_REQUEST_BYTES + 1),
            valid.replace(b'"version":1', b'"version":1,"version":1'),
            b'{"syncProtocol":"agent-observer.sync","version":1,"hostScope":"fixture","operation":"head","challenge":{"x":NaN}}\n',
        ):
            with self.assertRaises(ValueError):
                parse_request(wire)

    def test_pure_contract_import_loads_no_provider_service_or_mesh(self):
        code = (
            "import sys;import agent_observer.sync_contract;"
            "assert not any(name in sys.modules for name in "
            "['mesh_plus','agent_observer.collection','agent_observer.codex_snapshot',"
            "'agent_observer.service_runtime','agent_observer.observation_engine'])"
        )
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "independent schema validator unavailable")
    def test_independent_jsonschema_validates_tuple_positions(self):
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema_document())
        validator.check_schema(schema_document())
        for protocol in PROTOCOLS:
            for operation in ("baseline", "changes", "head", "watch"):
                validator.validate(request(operation, protocol))
        value = request("watch")
        value["cursor"] = [TAG[2], 1, EPOCH]
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(value)
