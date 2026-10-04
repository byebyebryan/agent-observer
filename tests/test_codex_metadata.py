"""Synthetic projections derived from inspected schema/native metadata shape."""

import json
import unittest

from agent_observer.codex_metadata import (
    MetadataError,
    live_thread_metadata,
    saved_thread_metadata,
)


class CodexMetadataTest(unittest.TestCase):
    def setUp(self):
        self.scope = {
            "host_scope": "host-a",
            "namespace": "config-a",
            "runtime_version": "0.160.0",
        }
        self.row = {
            "id": "01234567-0123-4567-89ab-0123456789ab",
            "sessionId": "11234567-0123-4567-89ab-0123456789ab",
            "name": "Native label",
            "cwd": "/project",
            "createdAt": 1_800_000_000,
            "updatedAt": 1_800_000_123,
            "status": {"type": "idle"},
            "source": "vscode",
            "threadSource": "user",
            "preview": "synthetic_private_preview",
            "turns": [{"text": "synthetic_private_turn"}],
            "arbitraryField": "synthetic_private_payload",
        }

    def test_live_idle_and_presence_have_actual_snapshot_clock(self):
        value = live_thread_metadata(self.row, **self.scope, observed_at=100)
        self.assertEqual(value["work"]["value"], "settled")
        self.assertEqual(value["work"]["observedAt"], 100)
        self.assertEqual(value["presence"]["value"], "present")
        self.assertEqual(value["attachment"]["value"], "unknown")
        self.assertEqual(value["attachment"]["health"], "unsupported")

    def test_saved_idle_is_not_fresh_work_or_presence(self):
        value = saved_thread_metadata(self.row, **self.scope)
        self.assertEqual(value["work"]["value"], "unknown")
        self.assertIsNone(value["work"]["observedAt"])
        self.assertEqual(value["presence"]["value"], "unknown")

    def test_native_history_seconds_project_to_nullable_unix_milliseconds(self):
        saved = saved_thread_metadata(self.row, **self.scope)
        live = live_thread_metadata(self.row, **self.scope, observed_at=500_000)
        expected = {"createdAt": 1_800_000_000_000, "updatedAt": 1_800_000_123_000}
        self.assertEqual(expected, saved["nativeHistoryTimes"])
        self.assertEqual(expected, live["nativeHistoryTimes"])
        self.assertEqual([], saved["metadataIssues"])

    def test_missing_or_unrecognized_history_times_are_null_with_finite_issue(self):
        missing = {**self.row}
        missing.pop("createdAt")
        missing.pop("updatedAt")
        missing_value = saved_thread_metadata(missing, **self.scope)
        self.assertEqual(
            {"createdAt": None, "updatedAt": None}, missing_value["nativeHistoryTimes"]
        )
        self.assertEqual(["native_history_time_unavailable"], missing_value["metadataIssues"])

        malformed = {
            **self.row,
            "createdAt": True,
            "updatedAt": float("nan"),
            "privateTime": "synthetic_private_time_text",
        }
        value = saved_thread_metadata(malformed, **self.scope)
        self.assertEqual({"createdAt": None, "updatedAt": None}, value["nativeHistoryTimes"])
        self.assertEqual(["native_history_time_unavailable"], value["metadataIssues"])
        serialized = json.dumps(value, allow_nan=False)
        self.assertNotIn("synthetic_private_time_text", serialized)
        self.assertNotIn("privateTime", serialized)

        partial = saved_thread_metadata(
            {**self.row, "createdAt": -1, "updatedAt": 1_800_000_123}, **self.scope
        )
        self.assertEqual(
            {"createdAt": None, "updatedAt": 1_800_000_123_000},
            partial["nativeHistoryTimes"],
        )
        self.assertEqual(["native_history_time_unavailable"], partial["metadataIssues"])

    def test_history_time_evidence_does_not_follow_live_observation_clock(self):
        first = live_thread_metadata(self.row, **self.scope, observed_at=100_000)
        later = live_thread_metadata(self.row, **self.scope, observed_at=900_000)
        self.assertEqual(first["nativeHistoryTimes"], later["nativeHistoryTimes"])
        self.assertEqual(100_000, first["work"]["observedAt"])
        self.assertEqual(900_000, later["presence"]["observedAt"])

    def test_distinct_thread_and_session_ids_are_never_collapsed(self):
        value = saved_thread_metadata(self.row, **self.scope)
        self.assertEqual(value["identity"]["nativeId"], self.row["id"])
        self.assertEqual(value["nativeIds"]["sessionId"], self.row["sessionId"])
        self.assertNotEqual(value["nativeIds"]["threadId"], value["nativeIds"]["sessionId"])

    def test_content_and_unknown_fields_never_escape(self):
        serialized = json.dumps(live_thread_metadata(self.row, **self.scope, observed_at=100))
        self.assertNotIn("synthetic_private", serialized)
        self.assertNotIn("preview", serialized)
        self.assertNotIn("turns", serialized)

    def test_non_cli_native_source_is_preserved_without_exclusion(self):
        value = saved_thread_metadata(self.row, **self.scope)
        self.assertEqual(value["sourceKind"], "vscode")
        self.assertEqual(value["threadKind"], "user")

    def test_saved_and_loaded_thread_spawn_children_keep_classification_and_clocks(self):
        child_source = {
            "subAgent": {
                "thread_spawn": {
                    "parent_thread_id": "21234567-0123-4567-89ab-0123456789ab",
                    "depth": 1,
                    "agent_path": "root/worker",
                    "agent_nickname": "worker",
                    "agent_role": "reviewer",
                }
            }
        }
        child = {**self.row, "source": child_source, "threadSource": "subagent"}
        saved = saved_thread_metadata(child, **self.scope)
        loaded = live_thread_metadata(
            {**child, "status": {"type": "active", "activeFlags": []}},
            **self.scope,
            observed_at=500_000,
        )

        for value in (saved, loaded):
            self.assertEqual("subagent", value["sourceKind"])
            self.assertEqual("child", value["threadKind"])
            self.assertEqual(self.row["id"], value["identity"]["nativeId"])
        self.assertEqual("saved", saved["inventory"])
        self.assertEqual("unknown", saved["work"]["value"])
        self.assertEqual("live", loaded["inventory"])
        self.assertEqual("working", loaded["work"]["value"])
        self.assertEqual(500_000, loaded["work"]["observedAt"])
        self.assertEqual(500_000, loaded["presence"]["observedAt"])
        self.assertEqual(saved["nativeHistoryTimes"], loaded["nativeHistoryTimes"])
        serialized = json.dumps({"saved": saved, "loaded": loaded})
        for private_value in ("thread_spawn", "parent_thread_id", "root/worker", "reviewer"):
            self.assertNotIn(private_value, serialized)

    def test_native_review_and_compact_sources_are_children_without_thread_source(self):
        for variant in ("review", "compact"):
            value = saved_thread_metadata(
                {**self.row, "source": {"subAgent": variant}, "threadSource": None},
                **self.scope,
            )
            self.assertEqual("subagent", value["sourceKind"])
            self.assertEqual("child", value["threadKind"])
        malformed = saved_thread_metadata(
            {**self.row, "source": {"subAgent": "unknown_variant"}, "threadSource": None},
            **self.scope,
        )
        self.assertEqual("unknown", malformed["threadKind"])
        self.assertIn("thread_classification_unavailable", malformed["metadataIssues"])

    def test_unknown_history_classification_stays_visible_as_unknown(self):
        value = saved_thread_metadata(
            {**self.row, "source": "unknown", "threadSource": "unknown"}, **self.scope
        )
        self.assertEqual("unknown", value["sourceKind"])
        self.assertEqual("unknown", value["threadKind"])

    def test_each_authoritative_child_signal_can_classify_without_the_other(self):
        by_thread_source = saved_thread_metadata(
            {**self.row, "source": None, "threadSource": "subagent"}, **self.scope
        )
        self.assertEqual("unknown", by_thread_source["sourceKind"])
        self.assertEqual("child", by_thread_source["threadKind"])

        by_source_marker = saved_thread_metadata(
            {
                **self.row,
                "source": {
                    "subAgent": {
                        "thread_spawn": {"parent_thread_id": "21234567-0123-4567-89ab-0123456789ab"}
                    }
                },
                "threadSource": "unknown",
            },
            **self.scope,
        )
        self.assertEqual("subagent", by_source_marker["sourceKind"])
        self.assertEqual("child", by_source_marker["threadKind"])

    def test_malformed_or_conflicting_subagent_metadata_stays_unknown_and_private(self):
        malformed_source = {
            "subAgent": {
                "thread_spawn": {
                    "parent_thread_id": "not-a-native-id",
                    "depth": 1,
                    "agent_path": "synthetic_private_path",
                    "agent_nickname": "worker",
                    "agent_role": {"private": "synthetic_private_role"},
                }
            }
        }
        malformed = saved_thread_metadata(
            {**self.row, "source": malformed_source, "threadSource": "unknown"},
            **self.scope,
        )
        self.assertEqual("unknown", malformed["sourceKind"])
        self.assertEqual("unknown", malformed["threadKind"])
        self.assertEqual(["thread_classification_unavailable"], malformed["metadataIssues"])

        conflicting = saved_thread_metadata(
            {
                **self.row,
                "source": {
                    "subAgent": {
                        "thread_spawn": {
                            "parent_thread_id": "21234567-0123-4567-89ab-0123456789ab",
                            "depth": 1,
                            "agent_path": "root/worker",
                            "agent_nickname": "worker",
                            "agent_role": "reviewer",
                        }
                    }
                },
                "threadSource": "user",
            },
            **self.scope,
        )
        self.assertEqual("subagent", conflicting["sourceKind"])
        self.assertEqual("unknown", conflicting["threadKind"])
        self.assertEqual(["thread_classification_conflict"], conflicting["metadataIssues"])
        serialized = json.dumps({"malformed": malformed, "conflicting": conflicting})
        for private_value in (
            "synthetic_private_path",
            "synthetic_private_role",
            "thread_spawn",
            "parent_thread_id",
            "root/worker",
        ):
            self.assertNotIn(private_value, serialized)

    def test_active_and_wait_flags_are_schema_candidates(self):
        for flags, expected, reason in (
            ([], "working", "unknown"),
            (["waitingOnApproval"], "needs_input", "approval"),
            (["waitingOnUserInput"], "needs_input", "user_input"),
        ):
            row = {**self.row, "status": {"type": "active", "activeFlags": flags}}
            value = live_thread_metadata(row, **self.scope, observed_at=100)
            self.assertEqual(value["work"]["value"], expected)
            self.assertEqual(value["waitReason"], reason)

    def test_unknown_missing_duplicate_wait_flags_preserve_uncertainty(self):
        for flags in (
            None,
            ["synthetic_private_flag"],
            ["waitingOnApproval", "waitingOnApproval"],
            {},
        ):
            row = {**self.row, "status": {"type": "active", "activeFlags": flags}}
            value = live_thread_metadata(row, **self.scope, observed_at=100)
            self.assertEqual(value["work"]["value"], "unknown")
            self.assertEqual(value["work"]["health"], "unsupported")
            self.assertNotIn("synthetic_private", json.dumps(value))

    def test_not_loaded_is_not_logical_session_end(self):
        row = {**self.row, "status": {"type": "notLoaded"}}
        value = live_thread_metadata(row, **self.scope, observed_at=100)
        self.assertEqual(value["presence"]["value"], "absent")
        self.assertEqual(value["work"]["value"], "unknown")
        self.assertIn("sessionId", value["nativeIds"])

    def test_version_schema_and_native_id_mismatch_fail_with_bounded_codes(self):
        with self.assertRaisesRegex(MetadataError, "^unsupported_runtime_version$"):
            saved_thread_metadata(self.row, **{**self.scope, "runtime_version": "0.161.0"})
        for status in ("idle", {"type": []}, {"type": "synthetic_private_state"}):
            with self.assertRaisesRegex(MetadataError, "^unsupported_status_schema$"):
                live_thread_metadata({**self.row, "status": status}, **self.scope, observed_at=100)
        with self.assertRaisesRegex(MetadataError, "^invalid_native_identity$"):
            saved_thread_metadata({**self.row, "sessionId": "ambiguous"}, **self.scope)

    def test_title_and_cwd_are_bounded_without_path_rewriting(self):
        value = saved_thread_metadata(
            {
                **self.row,
                "name": "x" * 1000,
                "cwd": "/project\\nsecret".replace("\\n", "\n"),
            },
            **self.scope,
        )
        self.assertEqual(len(value["title"]), 256)
        self.assertIsNone(value["cwd"])
        self.assertEqual(value["metadataIssues"], ["cwd_unavailable"])
