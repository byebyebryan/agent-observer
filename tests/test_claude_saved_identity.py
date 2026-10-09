"""Runtime saved-existence proof must be positive, bounded and read-only."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from agent_observer.claude_saved_identity import saved_ids

SID = "01234567-0123-4567-89ab-0123456789ab"


class SavedIdentityTest(unittest.TestCase):
    def test_exact_metadata_identity_and_no_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(saved_ids(home, {SID}), set())
            self.assertEqual(list(home.iterdir()), [])
            project = home / "projects/project"
            project.mkdir(parents=True)
            path = project / (SID + ".jsonl")
            path.write_text(json.dumps({"type": "custom-title", "sessionId": SID}) + "\n")
            self.assertEqual(saved_ids(home, {SID}), {SID})
            path.write_text(json.dumps({"sessionId": "wrong"}) + "\n")
            self.assertEqual(saved_ids(home, {SID}), set())
            path.write_text(json.dumps({"sessionId": SID}))
            self.assertEqual(saved_ids(home, {SID}), set())

    def test_unsafe_paths_and_duplicate_keys_are_not_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "projects/project"
            project.mkdir(parents=True)
            path = project / (SID + ".jsonl")
            os.mkfifo(path)
            self.assertEqual(saved_ids(home, {SID}), set())
            path.unlink()
            other = home / "other"
            other.write_text(json.dumps({"sessionId": SID}) + "\n")
            path.symlink_to(other)
            self.assertEqual(saved_ids(home, {SID}), set())
            path.unlink()
            path.write_text('{"sessionId":"' + SID + '","sessionId":"wrong"}\n')
            self.assertEqual(saved_ids(home, {SID}), set())
