"""Portable managed-operation interfaces and owned rollback fixtures."""

import importlib.machinery
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManagedOperationsTests(unittest.TestCase):
    def test_scoped_render_ignores_unrelated_global_template_dependencies(self):
        loader = importlib.machinery.SourceFileLoader(
            "scoped_observer_operations", str(ROOT / "scripts/agent-observer-operations"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        fixture = ROOT / "tests/fixtures/managed-operations"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            shutil.copytree(fixture / "source", source)
            # Select a controlled fixture host rather than the runner's hostname.
            (source / ".chezmoidata/machines.yaml").write_text(json.dumps({
                "machine": {"by_hostname": {socket.gethostname(): "starship"}}
            }) + "\n")
            (source / ".chezmoiignore").write_text(
                '{{ includeTemplate "unrelated-desktop-profile.tmpl" . }}\n')
            module.ROOT = source
            selection = json.loads((fixture / "selection.json").read_text())
            values = module.rendered(Path.home(), selection)
            self.assertEqual(set(values), set(module.PAIRS.values()))
            self.assertTrue(all(value["value"] for value in values.values()))

    def test_owned_process_restore_guards(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/agent-observer-operations"), "--self-test"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status": "accepted"', result.stdout)

    def test_explicit_paths_required(self):
        for script, arguments in (
            ("agent-observer-operations", ["verify", "--host", "snap"]),
            ("agent-observer-mesh-operations", ["--host", "snap"]),
        ):
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), *arguments],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "required" in result.stderr + result.stdout
                or "explicit" in result.stderr + result.stdout
            )

    def test_reader_bridge_artifacts_share_contract_not_version(self):
        loader = importlib.machinery.SourceFileLoader(
            "mesh_operations_gate", str(ROOT / "scripts/agent-observer-mesh-operations"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        contract = {"manifestVersion": 1, "agentProfile": "agent-observer.mesh-candidate.v1",
                    "lockSha256": "2b93e1c1e0b533be00e6646ea0ef62aefec357ba00e1e8a51489578ccde38489"}
        reader, bridge = {"mesh": {**contract, "version": "0.1.0a11"}}, {"mesh": {**contract, "version": "0.1.0a10"}}
        module.compatible_bridge(reader, bridge)
        updated = {"mesh": {**contract, "manifestVersion": 2, "version": "0.1.0a15",
                             "lockSha256": "f" * 64, "sdkInterface": 1,
                             "stateSchemasSha256": "a5cd4814025777aa093cc3bf0d5791a78230ae0d08d2c15e6e4b0f98062fdd46"}}
        module.compatible_bridge(updated, bridge)
        module.compatible_bridge(reader, updated)
        timing = {"mesh": {**updated["mesh"], "manifestVersion": 3,
                           "agentProfile": "agent-observer.mesh-candidate.v2",
                           "stateSchemasSha256": "b15f8c69909ec2574ba2adc17a3ccda5b44ab4ec1a1173a50732fd134c183900"}}
        module.compatible_bridge(timing, timing)
        with self.assertRaisesRegex(ValueError, "^mesh_bridge_contract_selection$"):
            module.compatible_bridge(timing, updated)
        for changed in ({"sdkInterface": 2}, {"stateSchemasSha256": "a" * 64}):
            with self.assertRaisesRegex(ValueError, "^mesh_bridge_contract_selection$"):
                module.compatible_bridge(reader, {"mesh": {**updated["mesh"], **changed}})
        for field, value in (("agentProfile", "foreign"), ("lockSha256", "a" * 64)):
            with self.assertRaisesRegex(ValueError, "^mesh_bridge_contract_selection$"):
                module.compatible_bridge(reader, {"mesh": {**bridge["mesh"], field: value}})

    def test_retired_bridge_dependency_profile_does_not_leak_into_reader(self):
        from unittest.mock import patch
        loader = importlib.machinery.SourceFileLoader(
            "mesh_profile_selection", str(ROOT / "scripts/agent-observer-mesh-operations"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        contract = {"manifestVersion": 1, "agentProfile": "agent-observer.mesh-candidate.v1",
                    "lockSha256": "2b93e1c1e0b533be00e6646ea0ef62aefec357ba00e1e8a51489578ccde38489"}
        bridge = {"mesh": contract, "profiles": {"snap": "claude-history"}}
        reader = {"mesh": contract, "profiles": {"snap": "core"}, "bridgeSelection": bridge}
        with patch.object(module, "artifact", side_effect=[("reader", {}), ("bridge", {})]) as gate:
            module.selected_artifacts(reader, "snap")
        self.assertEqual(gate.call_args_list[0].args, (reader, "snap", {"snap": "core"}))
        self.assertEqual(gate.call_args_list[1].args, (bridge, "snap", {"snap": "claude-history"}))


if __name__ == "__main__":
    unittest.main()
