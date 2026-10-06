"""Artifact identity must reject before installation or any provider invocation."""

import hashlib
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
HELPER = runpy.run_path(str(ROOT / "scripts/candidate-artifact"))


class CandidateArtifactTest(unittest.TestCase):
    def test_rejected_wheel_has_no_install_effect(self):
        with tempfile.TemporaryDirectory() as root:
            wheel = Path(root) / "invalid.whl"
            wheel.write_bytes(b"invalid")
            prefix = Path(root) / "candidate"
            manifest = {"wheel": wheel.name, "wheelSha256": "f" * 64}
            with patch.dict(
                HELPER["install"].__globals__, run=lambda *a, **k: self.fail("spawned")
            ):
                with self.assertRaisesRegex(ValueError, "wheel_mismatch"):
                    HELPER["install"](prefix, wheel, manifest, "core")
            self.assertFalse(prefix.exists())

    def test_accepted_manifest_has_exact_source_and_interfaces(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.2.0a3.json")
        self.assertEqual(["agent-observer", "agent-observer-write"], manifest["entrypoints"])
        self.assertEqual(2, manifest["schemas"]["snapshot"])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            manifest["sourceRevision"] = "moving-branch"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_zip_traversal_rejected_before_extracting(self):
        import zipfile

        with tempfile.TemporaryDirectory() as root:
            wheel = Path(root) / "candidate.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("../outside", "untrusted")
            manifest = {
                "wheel": wheel.name,
                "wheelSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
            with self.assertRaisesRegex(ValueError, "wheel_path_invalid"):
                HELPER["wheel_check"](wheel, manifest)

    def test_v3_candidate_receipt_requires_matching_read_and_watch_versions(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.2.0a11.json")
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            manifest["schemas"] = {"snapshot": 3, "watch": 3, "write": 1}
            manifest["apiVersion"] = 1
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path)["schemas"]["snapshot"], 3)
            manifest["schemas"]["watch"] = 2
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_failed_install_removes_only_owned_new_prefix(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            prefix = root / "candidate"
            unrelated = root / "user-file"
            unrelated.write_text("preserve")
            functions = HELPER["install"].__globals__
            with patch.dict(
                functions,
                wheel_check=lambda *a: None,
                run=lambda *a, **k: (_ for _ in ()).throw(ValueError("failed")),
            ):
                with self.assertRaises(ValueError):
                    HELPER["install"](prefix, root / "wheel", {}, "core")
            self.assertFalse(prefix.exists())
            self.assertEqual("preserve", unrelated.read_text())
