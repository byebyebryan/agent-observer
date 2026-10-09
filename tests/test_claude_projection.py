"""Shared Claude evidence invariants; fixture reads do not execute a provider."""

import copy
import unittest

from agent_observer.collection import compose_snapshot

SID = "01234567-0123-4567-89ab-0123456789ab"
NAMESPACE = "sha256:" + "0" * 64


def sample():
    evidence = {"value": "working", "observedAt": 100, "source": "claude_registry",
                "health": "current", "reason": "native_snapshot"}
    row = {"identity": {"hostScope": "fixture", "provider": "claude", "namespace": NAMESPACE,
                        "nativeIdKind": "session", "nativeId": SID},
           "nativeIds": {"sessionId": SID, "jobId": None}, "title": "native title",
           "cwd": "/workspace", "cwdSource": "claude_registry", "metadataIssues": [],
           "presence": {**evidence, "value": "present", "observedAt": 200}, "work": evidence,
           "history": {"createdAt": 10},
           "activity": {"at": 90, "source": "claude_transcript_message", "health": "current",
                        "reason": "native_conversation_event"}}
    return {"provider": "claude", "configHome": "/fixture/claude", "configHomeKind": "explicit",
            "namespace": NAMESPACE, "host": {"authority": "fixture", "uid": 1000},
            "sourceHealth": "current", "runtime": None, "parkedSupported": True,
            "activitySupported": True, "errors": [],
            "coverage": {"sessionRegistry": "complete", "backgroundGuard": "complete",
                         "workerPresence": "complete", "saved": {"complete": False, "reason": "metadata_scan"}},
            "sessions": [row]}


class ClaudeProjectionTest(unittest.TestCase):
    def project(self, native):
        return compose_snapshot(host_scope="fixture", provider_snapshots=[native])

    def test_running_status_is_current_native_read_without_terminal_fields(self):
        native = sample()
        for work, expected in (("working", "working"), ("settled", "waiting")):
            native["sessions"][0]["work"]["value"] = work
            row = self.project(native)["sessions"][0]
            self.assertEqual((row["runtime"]["value"], row["phase"]["value"]), ("running", expected))
            self.assertEqual(row["phase"]["observedAt"], row["runtime"]["observedAt"])
            self.assertEqual(row["activity"]["at"], 90)
            self.assertEqual(row["nativeIds"], {"sessionId": SID})
            self.assertFalse(set(row) & {"worker", "job", "attachment", "sessionKind"})

    def test_liveness_never_restores_missing_work_and_waits_need_typed_evidence(self):
        native = sample()
        row = native["sessions"][0]
        row["work"].update(value="unknown", health="unsupported", reason="status_clock_unavailable")
        projected = self.project(native)["sessions"][0]
        self.assertEqual(projected["runtime"]["value"], "running")
        self.assertEqual(projected["phase"]["value"], "unknown")
        row["work"].update(value="needs_input", health="current")
        for wait in ("approval", "question", "dialog", "worker_request"):
            row["waitReason"] = wait
            projected = self.project(native)["sessions"][0]
            self.assertEqual(projected["phase"]["value"], "blocked" if wait in {"approval", "question"} else "unknown")
            self.assertEqual(projected["blockedReasons"], [wait] if wait in {"approval", "question"} else [])

    def test_absence_and_saved_history_do_not_establish_parked(self):
        native = sample()
        row = native["sessions"][0]
        row["presence"]["value"] = "absent"
        self.assertEqual(self.project(native)["sessions"][0]["runtime"]["value"], "unknown")
        row["runtimeDisposition"] = {**row["presence"], "value": "parked", "source": "claude_registry"}
        projected = self.project(native)["sessions"][0]
        self.assertEqual(projected["runtime"]["value"], "parked")
        self.assertIsNone(projected["phase"])
        del row["history"]
        self.assertEqual(self.project(native)["sessions"][0]["runtime"]["value"], "unknown")
        row["savedIdentity"] = True
        self.assertEqual(self.project(native)["sessions"][0]["runtime"]["value"], "parked")

    def test_failed_work_and_identity_conflicts_remain_explicit(self):
        native = sample()
        row = native["sessions"][0]
        row["presence"].update(value="unknown", health="ambiguous")
        row["runtimeDisposition"] = {"value": "unknown", "reason": "native_incarnation_unproved", "health": "ambiguous"}
        self.assertEqual(self.project(native)["sessions"][0]["runtime"]["health"], "ambiguous")
        row["presence"].update(value="present", health="current")
        native["sessions"].append(copy.deepcopy(row))
        value = self.project(native)
        self.assertEqual(len(value["sessions"]), 1)
        self.assertEqual(value["sessions"][0]["phase"]["health"], "ambiguous")

    def test_history_failure_preserves_runtime_coverage(self):
        native = sample()
        native["errors"] = [{"code": "history_timeout"}]
        native["coverage"]["saved"] = {"complete": False, "reason": "source_failed"}
        value = self.project(native)
        self.assertEqual(value["sources"][0]["coverage"]["saved"]["status"], "unavailable")
        self.assertEqual(value["sources"][0]["coverage"]["runtime"]["status"], "partial")
        self.assertEqual(value["sessions"][0]["phase"]["value"], "working")

    def test_future_phase_clock_does_not_borrow_runtime_freshness(self):
        native = sample()
        native["sessions"][0]["work"]["observedAt"] = 201
        row = self.project(native)["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "running")
        self.assertEqual(row["phase"]["value"], "unknown")
