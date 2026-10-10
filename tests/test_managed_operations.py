"""Portable managed-operation interfaces and owned rollback fixtures."""

import importlib.util
import subprocess
import sys
import unittest
from importlib.machinery import SourceFileLoader
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
        self.assertEqual(result.returncode, 0, result.stderr)
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


if __name__ == "__main__":
    unittest.main()
