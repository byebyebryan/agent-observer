"""Service protocol invariants, including independent structural conformance."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent_observer.contract import ContractError, canonical
from agent_observer.service_contract import (
    StreamGuard,
    interface,
    parse_frame,
    parse_request,
    schema_document,
    validate_frame,
)
from agent_observer.workspace import context

ROOT = Path(__file__).resolve().parent.parent


def fixture():
    return json.loads((ROOT / "tests/fixtures/service-v2/view.json").read_text())


class ServiceContractTest(unittest.TestCase):
    def test_roundtrip_and_bundled_schemas(self):
        value = fixture()
        self.assertEqual(parse_frame((canonical(value) + "\n").encode(), expected_host="fixture", expected_uid=1000), value)
        for kind in ("request", "frame"):
            bundled = json.loads((ROOT / f"agent_observer/contracts/service-{kind}.schema.json").read_text())
            self.assertEqual(schema_document(kind), bundled)
        self.assertEqual(interface()["embeddedSnapshotVersion"], 4)

    def test_strict_request_and_frame_failures(self):
        self.assertEqual(parse_request(b'{"serviceProtocol":2,"operation":"snapshot","hostScope":"fixture"}\n')["operation"], "snapshot")
        bad = [
            lambda v: v.update(serviceProtocol=1),
            lambda v: v.update(uid=True),
            lambda v: v.update(extra="untrusted"),
            lambda v: v.update(hostScope="another-host"),
            lambda v: v["sources"][0]["components"][0].update(expiresBoottimeMs=1),
            lambda v: v["sources"][0]["components"].pop(),
            lambda v: v["sources"][0].update(namespace="sha256:" + "0" * 64),
            lambda v: v["sources"][0]["components"][0].update(health="stale"),
        ]
        for mutate in bad:
            value = fixture()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_frame(value, expected_host="fixture", expected_uid=1000)
        for wire in (
            b'{"serviceProtocol":2,"operation":"resume","hostScope":"fixture"}\n',
            b'{"serviceProtocol":2,"operation":"snapshot","hostScope":"fixture","home":"/arbitrary"}\n',
            b'{"serviceProtocol":2,"operation":"snapshot","hostScope":"fixture"}',
            b'{}\n{}\n',
        ):
            with self.assertRaises(ValueError):
                parse_request(wire)

    def test_epoch_sequence_gap_and_resync(self):
        guard = StreamGuard(expected_host="fixture")
        value = fixture()
        guard.accept(value)
        repeated = copy.deepcopy(value)
        with self.assertRaises(ContractError):
            guard.accept(repeated)
        gap = {**value, "sequence": 2, "kind": "gap", "snapshot": None}
        guard.accept(gap)
        with self.assertRaises(ContractError):
            guard.accept({**value, "sequence": 3, "kind": "heartbeat", "snapshot": None})
        guard.accept({**value, "sequence": 3, "kind": "resync"})
        with self.assertRaises(ContractError):
            guard.accept({**value, "sequence": 4, "serviceId": "00000000-0000-0000-0000-000000000099"})

    def test_saved_coverage_and_workspace_require_a_history_lease(self):
        for workspace in (False, True):
            with self.subTest(workspace=workspace):
                value = fixture()
                source = value["sources"][0]
                next(c for c in source["components"] if c["name"] == "history")["health"] = "stale"
                if workspace:
                    native = next(s for s in value["snapshot"]["sources"] if s["provider"] == source["provider"])
                    native["coverage"]["saved"].update(status="unavailable", reason="service_history_expired")
                    row = next(r for r in value["snapshot"]["sessions"] if r["identity"]["provider"] == source["provider"])
                    row["workspace"] = context(row["cwd"], {"roots": [], "projects": []})
                with self.assertRaisesRegex(ContractError, "service_workspace_without_lease" if workspace else "service_coverage_without_lease"):
                    validate_frame(value)

    def test_service_facade_remains_pure(self):
        code = "import sys;import agent_observer.service_public;assert not any(x in sys.modules for x in ['agent_observer.collection','agent_observer.write_client','agent_observer.codex_snapshot','agent_observer.claude_snapshot'])"
        self.assertEqual(subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True).returncode, 0)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "independent proof uses its own jsonschema environment")
    def test_independent_jsonschema_reader(self):
        import jsonschema
        value = fixture()
        schema = json.loads((ROOT / "agent_observer/contracts/service-frame.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(value)
        value["snapshot"]["sessions"][0]["phase"]["observedAt"] = "invalid"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(value)
