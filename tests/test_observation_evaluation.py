"""Reference-comparison decisions; no provider runtime or payload fixtures."""

import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    "independent_observation_evaluation",
    str(Path(__file__).parent.parent / "scripts/evaluate-observation"),
)
spec = importlib.util.spec_from_loader(loader.name, loader)
evaluation = importlib.util.module_from_spec(spec)
loader.exec_module(evaluation)

SID = "01234567-0123-4567-89ab-0123456789ab"


class ObservationEvaluationTest(unittest.TestCase):
    def native(self, **fields):
        row = {"title": "Native title", "cwd": "/tmp/project", "runtime": "running", "phase": "working", "activity": 100, "kind": "user", "sessionId": SID, "createdAt": 50}
        return {"rows": {SID: {**row, **fields}}}

    def public(self, **fields):
        row = {"identity": {"provider": "codex", "nativeId": SID}, "title": "Native title", "cwd": "/tmp/project", "runtime": {"value": "running"}, "phase": {"value": "working"}, "activity": {"at": 100}, "kind": "user", "nativeIds": {"sessionId": SID}, "createdAt": 50}
        return {"sessions": [{**row, **fields}]}

    def test_stable_missing_row_and_native_active_inventory_are_retained(self):
        result = evaluation.compare(self.native(), {"sessions": []}, self.native(), "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "membership", "result": "missing_cli_row"}])
        self.assertEqual(result["nativeActive"][0]["id"], SID)

    def test_changed_native_phase_is_a_race_not_a_projection_mismatch(self):
        result = evaluation.compare(self.native(), self.public(), self.native(phase="waiting"), "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "phase", "result": "sampling_race"}])
        result = evaluation.compare(self.native(phase="waiting"), self.public(), self.native(phase="waiting"), "codex")
        self.assertEqual(result["issues"][0]["result"], "mismatch")

    def test_public_only_row_is_unproved_without_double_counting_a_race(self):
        result = evaluation.compare({"rows": {}}, self.public(), {"rows": {}}, "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "membership", "result": "cli_only_unproved", "runtime": "running"}])

    def test_inactive_unknown_phase_and_recent_cwd_are_distinct_semantics(self):
        native = self.native(runtime=None, phase=None, latestConversationCwd="/tmp/project/worktree")
        public = self.public(runtime={"value": "unknown"}, phase={"value": "unknown"})
        result = evaluation.compare(native, public, native, "codex")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["contextDifferences"][0]["recordedCwd"], "/tmp/project")

    def test_reference_never_dispatches_session_or_content_operations(self):
        client = evaluation.NativeRPC.__new__(evaluation.NativeRPC)
        for method, params in (("thread/resume", {}), ("thread/start", {}), ("thread/read", {"includeTurns": True}), ("thread/turns/list", {"itemsView": "loaded"})):
            with self.subTest(method=method), self.assertRaises(ValueError):
                client.call(method, params)

    def test_claude_classification_is_compared_independently(self):
        native = self.native()
        public = self.public(identity={"provider": "claude", "nativeId": SID})
        self.assertEqual(evaluation.compare(native, public, native, "claude")["issues"], [])
        public["sessions"][0]["kind"] = "unknown"
        result = evaluation.compare(native, public, native, "claude")
        self.assertEqual(result["issues"], [{"id": SID, "field": "kind", "result": "mismatch",
                                            "native": "user", "cli": "unknown"}])

    def test_native_foreground_permission_wait_has_independent_phase_reference(self):
        with tempfile.TemporaryDirectory() as scratch:
            home = Path(scratch)
            (home / "sessions").mkdir()
            pid = os.getpid()
            record = {
                "sessionId": SID, "pid": pid, "procStart": evaluation.birth(pid)[0],
                "pidDomain": "linux:" + Path("/etc/machine-id").read_text().strip()
                + ":" + os.readlink("/proc/self/ns/pid"),
                "kind": "interactive", "status": "waiting",
                "waitingFor": "permission prompt", "jobId": None,
            }
            registry = home / "sessions" / f"{pid}.json"
            with patch.object(evaluation, "image", return_value={"provider": "claude",
                                                                "version": "2.1.289"}):
                for changes, expected in (
                    ({}, "blocked"), ({"kind": "bg"}, None),
                    ({"waitingFor": "input needed"}, None),
                    ({"status": "idle"}, None),
                ):
                    registry.write_text(json.dumps({**record, **changes}))
                    native = evaluation.claude_reference(home, {})
                    self.assertEqual(native["rows"][SID]["phase"], expected)
