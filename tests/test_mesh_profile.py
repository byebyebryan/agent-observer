"""Owner native semantics and import isolation; no provider or service I/O."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    value = json.loads((ROOT / "tests/fixtures/service-v2/view.json").read_text())
    value["clockDomain"] = "time:[1]"
    return value


@unittest.skipUnless(importlib.util.find_spec("mesh_plus"), "optional Mesh SDK not installed")
class AgentProfileTests(unittest.TestCase):
    def setUp(self):
        from agent_observer.mesh_profile import AgentProfile
        self.profile = AgentProfile()
        self.codec = self.profile.bind("fixture", "agent")

    def test_native_roundtrip_identity_receipts_and_nonmutation(self):
        value = fixture()
        before = copy.deepcopy(value)
        state = self.codec.inspect_native(value)
        self.assertEqual(self.profile.restore_native(state.owner, state.records), before)
        self.assertEqual(state.publisher, value["serviceId"])
        self.assertEqual(state.emitted_ms, 15000)
        self.assertEqual(state.clock, {"bootId": value["bootId"], "timeNamespace": "time:1"})
        self.assertEqual(len(state.receipts), 4)
        for source in value["sources"]:
            expected = frozenset((source["provider"] + ":" + source["namespace"], name)
                                 for name in ("runtime", "history"))
            row = next(r for r in state.records if r["identity"]["provider"] == source["provider"])
            self.assertEqual(self.profile.record_receipts(row, state), expected)
            self.assertEqual(self.profile.record_identity(row), tuple(row["identity"][key] for key in
                             ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")))
        self.assertEqual(value, before)
        with self.assertRaises(FrozenInstanceError):
            self.codec.source = "changed"
        with self.assertRaises(FrozenInstanceError):
            self.profile.descriptor = None

    def test_empty_warming_and_configured_source_are_lossless(self):
        for warming in (False, True):
            value = fixture()
            if warming:
                value.update(kind="status", state="warming", snapshot=None)
            else:
                value["snapshot"]["sessions"] = []
            state = self.profile.bind("fixture", "default").inspect_native(value)
            self.assertEqual(self.profile.restore_native(state.owner, state.records), value)
            self.assertFalse(state.records)
            self.assertTrue(all(r["sourceId"] != "agent" for r in state.receipts))

    def test_provider_namespace_receipts_and_unsaved_eligibility_are_independent(self):
        state = self.codec.inspect_native(fixture())
        codex, claude = copy.deepcopy(state.records[0]), copy.deepcopy(state.records[3])
        codex["hasSavedHistory"] = False
        self.assertTrue(self.profile.record_eligible(codex, state))
        without_runtime = replace(state, receipts=tuple(r for r in state.receipts
                                  if r["sourceId"].startswith("claude:") or r["component"] != "runtime"))
        self.assertFalse(self.profile.record_eligible(codex, without_runtime))
        self.assertTrue(self.profile.record_eligible(claude, without_runtime))
        codex["identity"]["namespace"] = "sha256:" + "f" * 64
        self.assertIsNone(self.profile.record_receipts(codex, state))
        self.assertFalse(self.profile.record_eligible(codex, state))
        codex["hasSavedHistory"] = True
        self.assertTrue(self.profile.record_eligible(codex, state))
        stale = replace(state, receipts=tuple({**r, "health": "stale"} for r in state.receipts))
        self.assertIsNone(self.profile.record_receipts(claude, stale))

    def test_native_context_faults_and_sdk_contract_mismatch_reject(self):
        from mesh_plus.protocol import ProtocolError

        from agent_observer import mesh_profile
        from agent_observer.public import ContractError
        for change in (lambda v: v.update(hostScope="foreign"), lambda v: v.update(serviceProtocol=1),
                       lambda v: v["snapshot"].update(schemaVersion=3)):
            value = fixture()
            change(value)
            with self.assertRaises(ContractError):
                self.codec.inspect_native(value)
        for host, source in (("foreign host", "agent"), ("fixture", "provider:namespace")):
            with self.assertRaises(ProtocolError):
                self.profile.bind(host, source)
        with patch.object(mesh_profile, "SDK_INTERFACE_VERSION", 2):
            with self.assertRaisesRegex(ProtocolError, "^mesh_sdk_incompatible$"):
                mesh_profile.AgentProfile()
        with self.assertRaisesRegex(ProtocolError, "^mesh_sdk_incompatible$"):
            mesh_profile.AgentProfile(replace(self.profile.descriptor, native_version=3))
        invalid = fixture()
        invalid["clockDomain"] = "time:[unsupported]"
        with self.assertRaisesRegex(ProtocolError, "^owner_clock_domain$"):
            self.codec.inspect_native(invalid)

    def test_reference_and_collector_imports_blocked_for_every_callback(self):
        code = '''import builtins,json,sys
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def limited(name,*args,**kwargs):
 if name.startswith(('tmux_observer','mesh_plus.observer','agent_observer.collection',
 'agent_observer.service_runtime','agent_observer.write_client','agent_observer.codex_',
 'agent_observer.claude_')): raise AssertionError(name)
 return original(name,*args,**kwargs)
builtins.__import__=limited
from agent_observer.mesh_profile import AgentProfile
p=AgentProfile();v=json.loads(sys.stdin.read());c=p.bind('fixture','agent');s=c.inspect_native(v)
assert p.restore_native(s.owner,s.records)==v
c.validate_bridge({'hostId':'fixture','sourceId':'agent','ownerFrame':v})
p.validate_response({})
for r in s.records:
 p.record_identity(r);p.record_host(r);p.record_receipts(r,s);p.record_eligible(r,s)
assert not any(n.startswith(('tmux_observer','mesh_plus.observer')) for n in sys.modules)
'''
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(ROOT)],
                                input=json.dumps(fixture()), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
