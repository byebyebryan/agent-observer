"""Artifact and collection failure fixtures; no provider process is invoked."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.claude_snapshot import (
    CollectionError,
    _namespace,
    _verify_artifact,
    collect_claude,
)
from agent_observer.native_artifacts import CLAUDE, Inspection


class ClaudeCollectionTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.binary = self.root / "binary"
        self.binary.write_bytes(b"Synthetic non-executable artifact\n")
        self.binary.chmod(0o600)
        self.history = {
            "rows": [],
            "coverage": {"complete": False, "reason": "metadata_scan"},
            "errors": [],
        }
        patcher = patch(
            "agent_observer.claude_snapshot.collect_saved_history", return_value=self.history
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def native(self, *, partial=False):
        return {
            "supported": True,
            "coverage": {
                "sessionRegistry": "complete",
                "backgroundGuard": "partial" if partial else "complete",
                "workerPresence": "complete",
                "attachment": "unsupported",
            },
            "errors": [{"code": "file_unavailable"}] if partial else [],
            "limitations": [],
            "observations": [
                {
                    "identity": {
                        "hostScope": "snap",
                        "provider": "claude",
                        "namespace": "namespace",
                        "nativeIdKind": "session",
                        "nativeId": "01234567-0123-4567-89ab-0123456789ab",
                    },
                    "nativeIds": {
                        "sessionId": "01234567-0123-4567-89ab-0123456789ab",
                        "jobId": "1234abcd",
                    },
                    "title": "Claude 01234567-0123-4567-89ab-0123456789ab",
                    "sessionKind": "interactive",
                    "nativeStatus": {"value": "busy", "observedAt": 122},
                    "job": {
                        "id": "1234abcd",
                        "retained": True,
                        "state": "working",
                        "tempo": "active",
                        "terminalObservedAt": None,
                    },
                    "waitReason": "unknown",
                    "cwd": "/native/cwd",
                    "cwdSource": "claude_registry",
                    "metadataIssues": [],
                    "work": {
                        "value": "working",
                        "health": "current",
                        "observedAt": 123,
                        "source": "claude_registry",
                        "reason": "native_snapshot",
                    },
                    "presence": {
                        "value": "present",
                        "health": "current",
                        "observedAt": 456,
                        "source": "claude_registry",
                        "reason": "native_snapshot",
                    },
                    "attachment": {"value": "unknown", "health": "unsupported"},
                }
            ],
        }

    def test_unregistered_image_preserves_independently_verified_metadata(self):
        with patch("agent_observer.claude_snapshot.snapshot", return_value=self.native()) as source:
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        source.assert_called_once()
        self.assertEqual(value["runtime"]["version"], "unknown")
        self.assertEqual(value["errors"], [])
        self.assertEqual(value["sessions"][0]["work"]["value"], "working")
        self.assertEqual(value["sourceHealth"], "current")

    def test_runtime_failure_keeps_fresh_saved_history_independent(self):
        from agent_observer.collection import project_source

        self.history["rows"] = [
            {
                "session_id": "01234567-0123-4567-89ab-0123456789ab",
                "custom_title": "Saved native title",
                "cwd": str(self.config),
                "created_at": 100,
                "last_modified": 200,
                "activity": {
                    "at": 150,
                    "source": "claude_transcript_message",
                    "health": "current",
                    "reason": "native_conversation_event",
                },
            }
        ]
        unavailable = {"supported": False, "observations": [], "limitations": [],
                       "coverage": {"sessionRegistry": "unavailable", "backgroundGuard": "unavailable"},
                       "errors": [{"code": "session_registry_unavailable"}]}
        with patch("agent_observer.claude_snapshot.snapshot", return_value=unavailable) as native:
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        native.assert_called_once()
        self.assertEqual(value["sourceHealth"], "partial")
        self.assertEqual(value["sessions"][0]["activity"]["at"], 150)
        self.assertEqual(value["sessions"][0]["presence"]["value"], "unknown")
        source = project_source(value)
        self.assertEqual(source["coverage"]["runtime"]["status"], "unavailable")
        self.assertEqual(source["sourceHealth"], "partial")

    def test_default_configuration_is_distinct_from_explicit_same_directory(self):
        config = self.root / ".claude"
        config.mkdir()
        artifact = Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)
        with (
            patch("agent_observer.claude_snapshot.Path.home", return_value=self.root),
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=artifact),
            patch("agent_observer.claude_snapshot.snapshot", return_value=self.native()),
            patch.dict(os.environ, {}, clear=True),
        ):
            default = collect_claude(config, host_scope="snap", executable=self.binary)
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}):
                explicit = collect_claude(config, host_scope="snap", executable=self.binary)
        self.assertEqual("default", default["configHomeKind"])
        self.assertEqual("explicit", explicit["configHomeKind"])
        self.assertNotEqual(default["namespace"], explicit["namespace"])
        self.assertEqual(_namespace(config, "default")[0], default["namespace"])

    def test_symlink_and_writable_artifacts_are_rejected(self):
        link = self.root / "link"
        link.symlink_to(self.binary)
        with self.assertRaisesRegex(CollectionError, "runtime_image_ownership_mismatch"):
            _verify_artifact(link)
        self.binary.chmod(0o666)
        with self.assertRaisesRegex(CollectionError, "runtime_image_ownership_mismatch"):
            _verify_artifact(self.binary)

    def test_configured_namespace_is_not_inferred_from_rows(self):
        with (
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)),
            patch(
                "agent_observer.claude_snapshot._namespace",
                return_value=("exact-namespace", "boot"),
            ),
            patch("agent_observer.claude_snapshot.snapshot", return_value=self.native()) as source,
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        self.assertEqual(value["namespace"], "exact-namespace")
        self.assertEqual(source.call_args.kwargs["namespace"], "exact-namespace")
        self.assertEqual(value["host"]["authoritySource"], "caller")
        self.assertEqual(value["sourceHealth"], "current")
        self.assertFalse(value["coverage"]["saved"]["complete"])

    def test_partial_store_preserves_healthy_registry_evidence(self):
        with (
            patch(
                "agent_observer.claude_snapshot._verify_artifact",
                return_value=Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE),
            ),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch(
                "agent_observer.claude_snapshot.snapshot", return_value=self.native(partial=True)
            ),
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        self.assertEqual(value["sourceHealth"], "partial")
        self.assertEqual(value["sessions"][0]["work"]["value"], "working")
        self.assertEqual(value["coverage"]["backgroundGuard"], "partial")

    def test_schema_failure_mapping_cannot_bypass_native_proof_gate(self):
        native = self.native()
        native["observations"][0]["work"]["value"] = "error"
        with (
            patch(
                "agent_observer.claude_snapshot._verify_artifact",
                return_value=Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE),
            ),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch("agent_observer.claude_snapshot.snapshot", return_value=native),
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        self.assertEqual(value["sessions"][0]["work"]["value"], "unknown")
        self.assertEqual(value["sessions"][0]["work"]["health"], "unsupported")
        self.assertFalse(value["coverage"]["clientBinding"]["supported"])

    def test_installed_replacement_does_not_invalidate_worker_facts(self):
        expected = Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)

        def source(*_args, **_kwargs):
            replacement = self.root / "replacement"
            replacement.write_bytes(b"Another synthetic artifact")
            replacement.replace(self.binary)
            return self.native()

        with (
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=expected),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch("agent_observer.claude_snapshot.snapshot", side_effect=source),
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        self.assertEqual(value["errors"], [{"code": "installed_image_changed"}])
        self.assertEqual(value["sourceHealth"], "partial")
        self.assertIsNone(value["runtime"])
        work = value["sessions"][0]["work"]
        self.assertEqual(work["value"], "working")
        self.assertEqual(work["observedAt"], 123)

    def test_saved_history_merges_only_by_uuid_and_keeps_native_clocks_and_identity(self):
        matched_id = "01234567-0123-4567-89ab-0123456789ab"
        saved_id = "11234567-0123-4567-89ab-0123456789ab"
        self.history["rows"] = [
            {
                "session_id": matched_id,
                "custom_title": "SDK title",
                "cwd": "/sdk/path",
                "created_at": 1_700_000_000_000,
                "last_modified": 1_800_000_000_000,
            },
            {
                "session_id": saved_id,
                "custom_title": None,
                "cwd": "/saved/path ",
                "created_at": 1_700_000_000_100,
                "last_modified": 1_800_000_000_100,
            },
        ]
        self.history["coverage"] = {"complete": False, "reason": "metadata_scan"}
        native = self.native()
        expected = Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)
        with (
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=expected),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch("agent_observer.claude_snapshot.snapshot", return_value=native),
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)

        rows = {row["identity"]["nativeId"]: row for row in value["sessions"]}
        matched = rows[matched_id]
        self.assertEqual(matched["inventory"], "live")
        self.assertEqual(matched["nativeIds"]["jobId"], "1234abcd")
        self.assertEqual(matched["title"], "SDK title")
        self.assertEqual(matched["cwd"], "/native/cwd")
        self.assertEqual(matched["work"]["observedAt"], 123)
        self.assertEqual(
            matched["history"],
            {
                "source": "claude_sdk",
                "sdkVersion": "0.2.163",
                "createdAt": 1_700_000_000_000,
                "fileModifiedAt": 1_800_000_000_000,
            },
        )

        saved = rows[saved_id]
        self.assertEqual(saved["inventory"], "saved")
        self.assertEqual(saved["nativeIds"], {"sessionId": saved_id})
        self.assertNotIn("job", saved)
        self.assertEqual(saved["title"], "Claude " + saved_id)
        self.assertEqual(saved["cwd"], "/saved/path ")
        self.assertEqual(saved["cwdSource"], "claude_history")
        self.assertEqual(saved["work"]["value"], "unknown")
        self.assertEqual(saved["presence"]["value"], "unknown")
        self.assertNotIn("attachment", saved)
        self.assertIsNone(saved["presence"]["observedAt"])
        self.assertEqual(value["sourceHealth"], "current")

    def test_runtime_cadence_does_not_invoke_history_worker(self):
        with (
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch("agent_observer.claude_snapshot.snapshot", return_value=self.native()),
            patch("agent_observer.claude_snapshot.collect_saved_history") as history,
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary, include_history=False)
        history.assert_not_called()
        self.assertEqual(value["coverage"]["saved"]["reason"], "not_observed")

    def test_history_failure_does_not_stale_healthy_native_evidence(self):
        self.history["errors"] = [{"code": "history_source_failed"}]
        self.history["coverage"] = {"complete": False, "reason": "source_failed"}
        expected = Inspection((self.binary.stat().st_dev, self.binary.stat().st_ino), CLAUDE)
        with (
            patch("agent_observer.claude_snapshot._verify_artifact", return_value=expected),
            patch("agent_observer.claude_snapshot._namespace", return_value=("namespace", "boot")),
            patch("agent_observer.claude_snapshot.snapshot", return_value=self.native()),
        ):
            value = collect_claude(self.config, host_scope="snap", executable=self.binary)
        self.assertEqual(value["sourceHealth"], "current")
        self.assertEqual(value["sessions"][0]["work"]["value"], "working")
        self.assertEqual(value["coverage"]["saved"]["reason"], "source_failed")
        self.assertIn({"code": "history_source_failed"}, value["errors"])


if __name__ == "__main__":
    unittest.main()
