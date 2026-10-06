"""Public consumer boundary, semantic negatives and exact write target changes."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent_observer import public


class PublicApiTest(unittest.TestCase):
    def fixture(self):
        return json.loads((Path(__file__).parent / "fixtures/contract-v3/snapshot.json").read_text())

    def test_pure_facade_and_cli_declare_the_same_interface_without_adapters(self):
        result = subprocess.run([sys.executable, "-I", "-c", """
import sys
sys.path.insert(0, sys.argv[1])
from agent_observer import public
assert not any(name in sys.modules for name in (
 'agent_observer.collection', 'agent_observer.write_client',
 'agent_observer.codex_snapshot', 'agent_observer.claude_snapshot'))
print(public.canonical(public.interface()))
""", str(Path(__file__).parent.parent)], capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), public.interface())
        cli = subprocess.run([sys.executable, "-m", "agent_observer.cli", "api"], capture_output=True, check=True)
        self.assertEqual(json.loads(cli.stdout), public.interface())
        self.assertEqual(public.interface()["schemas"], {"snapshot": 3, "watch": 3, "write": 1})

    def test_wrong_provider_scope_topology_and_metadata_are_rejected(self):
        mutations = (
            lambda v: v["sources"][0]["coverage"]["runtime"].update(scope="registered_workers"),
            lambda v: v["sources"][0]["runtime"].update(topology="private_session_registry_and_job_store"),
            lambda v: v["sources"][0]["capabilities"]["phase"].append("working"),
            lambda v: (v["sessions"][0]["phase"].update(value="waiting"), v["sessions"][0].update(blockedReason="approval")),
            lambda v: v["sessions"][0].update(sessionKind="bg"),
        )
        for mutate in mutations:
            value = copy.deepcopy(self.fixture())
            mutate(value)
            with self.assertRaises(public.ContractError):
                public.validate_snapshot(value)

    def test_job_identity_mismatch_is_not_an_action_reference(self):
        value = self.fixture()
        row = value["sessions"][-1]
        row["job"] = {"id": "abcdef01", "retained": True, "state": "done", "tempo": "idle", "terminalObservedAt": 100}
        with self.assertRaisesRegex(public.ContractError, "job_identity_conflict"):
            public.parse_snapshot(public.canonical(value).encode())
