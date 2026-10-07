"""Proof fixture overrides cannot select ordinary runtime or borrow auth on reuse."""

import hashlib
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class NativeIsolationTest(unittest.TestCase):
    def setUp(self):
        self.prepare = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/native-isolation"))["prepare"]

    def test_reused_fixture_rejects_before_reading_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "fixture_already_prepared"):
                self.prepare(root, "starship", root / "missing-prefix")
            self.assertFalse((root / "native-starship").exists())

    def test_cached_cli_override_is_a_private_copy_with_accurate_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            ordinary, prefix, root = base / "ordinary", base / "prefix", base / "proof"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "bin/agent-observer-write").write_text("fixture")
            root.mkdir()
            release = "1.2.3-x86_64-unknown-linux-musl"
            binary = ordinary / ".codex/packages/app-server-daemon/releases" / release / "bin/codex"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"private-native-image-fixture")
            (ordinary / ".codex/auth.json").write_text("{}")
            with patch.dict(self.prepare.__globals__, ORDINARY=ordinary):
                self.prepare(root, "starship", prefix, release=release, cli_release=release)
            copied = root / "native-starship/native-cli/codex-bin/codex"
            self.assertEqual(copied.read_bytes(), binary.read_bytes())
            self.assertNotEqual(copied.stat().st_ino, binary.stat().st_ino)
            receipt = json.loads((root / "fixture.json").read_text())
            self.assertEqual(receipt["codexCliSource"], str(binary))
            self.assertEqual(receipt["installedCliSha256"]["codex"], hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertFalse(receipt["apiKeyModelDiscoveryDisabledInFixture"])
            self.assertFalse((ordinary / ".codex/packages/app-server-daemon/current").exists())
