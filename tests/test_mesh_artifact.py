"""Archived transport selection rejects ambiguity before invoking any verifier."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MeshArtifactTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "scripts/verify-mesh-artifact"
        loader = importlib.machinery.SourceFileLoader("mesh_artifact_gate", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.module = importlib.util.module_from_spec(spec)
        loader.exec_module(self.module)
        self.manifest = json.loads((path.parents[1] / "artifacts/mesh-0.1.0a9.json").read_text())

    def test_version_is_diagnostic_but_frozen_contract_is_required(self):
        with tempfile.TemporaryDirectory() as name:
            for version in ("0.1.0a11", "0.1.0a123"):
                value = {**self.manifest, "version": version,
                         "wheel": f"mesh_plus-{version}-py3-none-any.whl"}
                path = Path(name) / f"mesh-{version}.json"
                path.write_text(json.dumps(value))
                self.assertEqual(self.module.mesh_manifest(path), value)

    def test_additive_lock_binds_reviewed_state_schemas_and_sdk(self):
        value = {**self.manifest, "manifestVersion": 2, "lockSha256": "f" * 64,
                 "stateSchemasSha256": self.module.STATE_SCHEMAS_SHA256, "sdkInterface": 1}
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "mesh-0.1.0a9.json"
            path.write_text(json.dumps(value))
            self.assertEqual(self.module.mesh_manifest(path), value)
            for fault in ({"sdkInterface": 2}, {"sdkInterface": True},
                          {"stateSchemasSha256": "f" * 64}, {"lockSha256": "wrong"}):
                path.write_text(json.dumps({**value, **fault}))
                with self.assertRaises(ValueError):
                    self.module.mesh_manifest(path)

    def test_ambiguous_or_malformed_artifact_fails_before_subprocess(self):
        for changed in ({"agentProfile": "unreviewed"}, {"lockSha256": "f" * 64},
                        {"wheel": "../foreign.whl"}, {"sourceRevision": "wrong"},
                        {"wheelSha256": "wrong"}, {"manifestVersion": 2},
                        {"extra": True}, None, {}):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as name:
                archive = Path(name)
                (archive / "observer-0.5.0a13.json").write_text("{}")
                path = archive / "mesh-0.1.0a9.json"
                value = {**self.manifest, **(changed or {})}
                path.write_text(json.dumps(value))
                if changed is None:
                    (archive / "mesh-duplicate.json").write_text(path.read_text())
                # The otherwise valid manifest still has no authenticated wheel.
                with patch.object(self.module.subprocess, "run") as run:
                    with self.assertRaises(ValueError):
                        self.module.verify(archive, archive, "core")
                    run.assert_not_called()
