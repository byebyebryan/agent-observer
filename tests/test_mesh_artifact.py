"""Archived transport selection rejects ambiguity before invoking any verifier."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MeshArtifactTest(unittest.TestCase):
    def test_duplicate_or_unreviewed_mesh_manifest_fails_before_subprocess(self):
        path = Path(__file__).resolve().parents[1] / "scripts/verify-mesh-artifact"
        loader = importlib.machinery.SourceFileLoader("mesh_artifact_gate", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        for versions in (("0.1.0a4", "0.1.0a8"), ("0.1.0a9",)):
            with self.subTest(versions=versions), tempfile.TemporaryDirectory() as name:
                archive = Path(name)
                (archive / "observer-0.5.0a13.json").write_text("{}")
                for version in versions:
                    (archive / f"mesh-{version}.json").write_text(json.dumps({
                        "package": "mesh-plus", "version": version,
                        "agentProfile": "agent-observer.mesh-candidate.v1"}))
                with patch.object(module.subprocess, "run") as run:
                    with self.assertRaises(ValueError):
                        module.verify(archive, archive, "core")
                    run.assert_not_called()
