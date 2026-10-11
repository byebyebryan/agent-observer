"""Portable managed-operation interfaces and owned rollback fixtures."""

import importlib.machinery
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManagedOperationsTests(unittest.TestCase):
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
        contract = {"agentProfile": "agent-observer.mesh-candidate.v1",
                    "lockSha256": "2b93e1c1e0b533be00e6646ea0ef62aefec357ba00e1e8a51489578ccde38489"}
        reader, bridge = {"mesh": {**contract, "version": "0.1.0a11"}}, {"mesh": {**contract, "version": "0.1.0a10"}}
        module.compatible_bridge(reader, bridge)
        for field, value in (("agentProfile", "foreign"), ("lockSha256", "a" * 64)):
            with self.assertRaisesRegex(ValueError, "^mesh_bridge_contract_selection$"):
                module.compatible_bridge(reader, {"mesh": {**bridge["mesh"], field: value}})


if __name__ == "__main__":
    unittest.main()
