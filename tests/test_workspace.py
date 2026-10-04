"""Local repository/worktree and explicit project mapping fixtures."""

import tempfile
import unittest
from pathlib import Path

from agent_observer.workspace import context, validate_config


class WorkspaceTest(unittest.TestCase):
    def test_git_directory_and_linked_worktree_keep_distinct_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            subdir = repo / "src"
            subdir.mkdir()
            gitdir = repo / ".git/worktrees/second"
            gitdir.mkdir(parents=True)
            (gitdir / "commondir").write_text("../..\n")
            worktree = root / "second"
            worktree.mkdir()
            (worktree / ".git").write_text(f"gitdir: {gitdir}\n")
            config = {
                "roots": [{"key": "code", "path": temp}],
                "projects": [{"rootKey": "code", "relativePath": "repo", "projectKey": "observer"}],
            }
            first, second = context(str(subdir), config), context(str(worktree), config)
            self.assertEqual(first["relativePath"], "repo/src")
            self.assertEqual(first["repo"]["relativePath"], "src")
            self.assertEqual(first["projectKey"], "observer")
            self.assertIsNone(second["projectKey"])
            self.assertNotEqual(first["repo"]["root"], second["repo"]["root"])
            self.assertEqual(first["repo"]["commonDir"], second["repo"]["commonDir"])

    def test_missing_root_and_non_repo_do_not_fail_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            config = {"roots": [{"key": "missing", "path": temp + "/absent"}], "projects": []}
            result = context(temp, config)
            self.assertEqual(result["health"], "current")
            self.assertIsNone(result["repo"])
            self.assertIsNone(result["root"])
            self.assertEqual(context(temp + "/absent", config)["health"], "unavailable")

    def test_explicit_mapping_required_across_roots_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "project").mkdir()
            config = {"roots": [{"key": "code", "path": temp}], "projects": []}
            self.assertIsNone(context(str(root / "project"), config)["projectKey"])
            config["projects"] = [
                {"rootKey": "code", "relativePath": "../project", "projectKey": "wrong"}
            ]
            with self.assertRaises(ValueError):
                validate_config(config)
