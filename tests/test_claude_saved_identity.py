"""Runtime saved-existence proof must be positive, bounded and read-only."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.claude_saved_identity import saved_ids
from agent_observer import claude_saved_identity as module

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
            self.assertEqual(saved_ids(home), {SID})
            path.write_text(json.dumps({"sessionId": "wrong"}) + "\n")
            self.assertEqual(saved_ids(home, {SID}), set())

    def test_catalog_keeps_proven_prefix_at_limits_and_does_not_follow_project_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "projects/project"
            project.mkdir(parents=True)
            (project / (SID + ".jsonl")).write_text(json.dumps({"sessionId": SID}) + "\n")
            (home / "projects/link").symlink_to(project)
            self.assertEqual(saved_ids(home), {SID})
            with patch.object(module, "MAX_IDS", 0):
                self.assertEqual(saved_ids(home), set())
            with patch.object(module, "MAX_PROJECTS", 0):
                self.assertEqual(saved_ids(home), set())
            with patch.object(module, "MAX_ENTRIES", 0):
                self.assertEqual(saved_ids(home), set())

    def test_catalog_rejects_conflicting_uuid_and_reads_bounded_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "projects/project"
            project.mkdir(parents=True)
            path = project / (SID + ".jsonl")
            positive = json.dumps({"sessionId": SID}) + "\n"
            path.write_text(positive + (json.dumps({"padding": "x" * 4096}) + "\n") * 40 + positive)
            self.assertEqual(saved_ids(home), {SID})
            path.write_text(positive + json.dumps({"sessionId": "another"}) + "\n")
            self.assertEqual(saved_ids(home), set())
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
