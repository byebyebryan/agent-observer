"""Process-image support must survive upgrades without trusting unknown images."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import native_artifacts
from agent_observer.native_artifacts import Artifact, inspect_installed, inspect_process


class NativeArtifactTest(unittest.TestCase):
    def test_replaced_installed_file_does_not_erase_supported_resident_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sleep"
            shutil.copyfile("/usr/bin/sleep", path)
            path.chmod(0o700)
            before = path.read_bytes()
            old = Artifact("claude", "old", hashlib.sha256(before).hexdigest(), str(path))
            after = before + b"\0"
            new = Artifact("claude", "new", hashlib.sha256(after).hexdigest(), str(path))
            process = subprocess.Popen([str(path), "30"])
            try:
                # Popen returns after exec; replacement leaves that open ELF alive.
                replacement = Path(directory) / "replacement"
                replacement.write_bytes(after)
                replacement.chmod(0o700)
                replacement.replace(path)
                with patch.object(native_artifacts, "ARTIFACTS", (old, new)):
                    cache = {}
                    self.assertEqual(inspect_installed(path, "claude").artifact, new)
                    self.assertEqual(inspect_process(process.pid, "claude", cache=cache).artifact, old)
                    self.assertEqual(inspect_process(process.pid, "claude", cache=cache).artifact, old)
                    self.assertEqual(len(cache), 1)
                    with patch.object(native_artifacts, "ARTIFACTS", (new,)):
                        with self.assertRaisesRegex(ValueError, "runtime_artifact_not_accepted"):
                            inspect_process(process.pid, "claude")
            finally:
                process.terminate()
                process.wait(timeout=5)

    def test_digest_registration_cannot_substitute_provider_or_version_family(self):
        for profile in native_artifacts.ARTIFACTS:
            self.assertEqual(native_artifacts.registered(profile.provider, profile.sha256), profile)
            self.assertIsNone(native_artifacts.registered("other", profile.sha256))
        self.assertIsNone(native_artifacts.registered("claude", "f" * 64))
