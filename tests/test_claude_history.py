"""Contract tests for isolated Claude SDK saved-history metadata projection."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer._claude_history_worker import (
    _bounded_cwd,
    _WorkerFailure,
    census_projects,
    transcript_activity,
)
from agent_observer.claude_history import SDK_VERSION, _run_worker, collect_saved_history

FIRST = "01234567-0123-4567-89ab-0123456789ab"
SECOND = "11234567-0123-4567-89ab-0123456789ab"
THIRD = "21234567-0123-4567-89ab-0123456789ab"


def worker_row(session_id, *, created_at, last_modified, cwd=None, title=None, activity_at=None):
    return {
        "session_id": session_id,
        "custom_title": title,
        "cwd": cwd,
        "created_at": created_at,
        "last_modified": last_modified,
        "activity": {
            "at": activity_at,
            "source": "claude_transcript_message" if activity_at is not None else None,
            "health": "current" if activity_at is not None else "unavailable",
            "reason": "native_conversation_event"
            if activity_at is not None
            else "no_conversation_activity",
        },
    }


def worker_payload(rows, *, errors=None, candidates=None):
    return {
        "sdk_version": SDK_VERSION,
        "census": {
            "projects": 1,
            "candidate_files": len(rows) if candidates is None else candidates,
            "total_bytes": 1024,
        },
        "rows": rows,
        "errors": [] if errors is None else errors,
    }


class ClaudeHistoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.config = Path(self.temporary.name) / "config"
        self.config.mkdir()

    def run_collector(self, payload, *, history_limit=100):
        with (
            patch("agent_observer.claude_history.Path.resolve", return_value=self.config),
            patch(
                "agent_observer.claude_history._run_worker",
                return_value=(json.dumps(payload).encode(), None),
            ),
        ):
            return collect_saved_history(self.config, history_limit=history_limit)

    def test_activity_order_precedes_display_cap_and_ignores_creation_and_mtime(self):
        payload = worker_payload(
            [
                worker_row(FIRST, created_at=100, last_modified=999_999, activity_at=20),
                worker_row(SECOND, created_at=200, last_modified=1, activity_at=10),
                worker_row(THIRD, created_at=None, last_modified=2_000_000),
            ],
            candidates=34,
        )
        result = self.run_collector(payload, history_limit=2)
        self.assertEqual(
            [row["session_id"] for row in result["rows"]],
            [FIRST, SECOND],
        )
        self.assertEqual(result["coverage"], {"complete": False, "reason": "history_limit"})
        self.assertEqual(result["errors"], [])
        self.assertEqual(
            set(result["rows"][0]),
            {"session_id", "custom_title", "cwd", "created_at", "last_modified", "activity"},
        )

    def test_preserves_exact_cwd_and_rejects_ambiguous_paths(self):
        cwd = "/work/Agent  Plus "
        row = worker_row(FIRST, created_at=10, last_modified=11, cwd=cwd)
        result = self.run_collector(worker_payload([row]))
        self.assertEqual(result["rows"][0]["cwd"], cwd)
        self.assertEqual(_bounded_cwd(cwd), cwd)
        for path in ("relative/path", "//server/share", "/work//Agent", "/work\n/tmp"):
            with self.subTest(path=path):
                self.assertIsNone(_bounded_cwd(path))

    def test_times_out_of_consumer_range_are_not_projected(self):
        row = worker_row(FIRST, created_at=4_000_000_000_001, last_modified=-1)
        result = self.run_collector(worker_payload([row]))
        self.assertIsNone(result["rows"][0]["created_at"])
        self.assertIsNone(result["rows"][0]["last_modified"])

    def test_worker_errors_have_finite_independent_coverage(self):
        for code in (
            "history_sdk_unavailable",
            "history_source_failed",
            "history_timeout",
            "history_limit",
            "history_unsafe_entry",
            "history_ambiguous",
        ):
            with self.subTest(code=code):
                result = self.run_collector({"error": code})
                self.assertEqual(result["errors"], [{"code": code}])
                self.assertFalse(result["coverage"]["complete"])
                self.assertEqual(result["rows"], [])

    def test_prompt_projection_fields_are_rejected(self):
        row = worker_row(FIRST, created_at=10, last_modified=11)
        row["summary"] = "must not cross the helper boundary"
        with self.assertRaisesRegex(ValueError, "invalid_worker_row"):
            from agent_observer.claude_history import _validate_payload

            _validate_payload(worker_payload([row]))

    def test_worker_timeout_kills_and_reaps_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            worker = Path(temporary) / "sleep_worker.py"
            worker.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
            processes = []
            real_popen = subprocess.Popen

            def tracking_popen(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                processes.append(process)
                return process

            with (
                patch("agent_observer.claude_history.Path.with_name", return_value=worker),
                patch("agent_observer.claude_history.subprocess.Popen", side_effect=tracking_popen),
            ):
                output, failure = _run_worker(self.config, timeout=0.1)
            self.assertIsNone(output)
            self.assertEqual(failure, "history_timeout")
            self.assertEqual(len(processes), 1)
            self.assertIsNotNone(processes[0].poll())

    def test_worker_stdout_cap_kills_and_reaps_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            worker = Path(temporary) / "flood_worker.py"
            worker.write_text(
                "import os,sys,time\nos.write(sys.stdout.fileno(), b'x' * 8192)\ntime.sleep(5)\n",
                encoding="utf-8",
            )
            processes = []
            real_popen = subprocess.Popen

            def tracking_popen(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                processes.append(process)
                return process

            with (
                patch("agent_observer.claude_history.Path.with_name", return_value=worker),
                patch("agent_observer.claude_history.subprocess.Popen", side_effect=tracking_popen),
                patch("agent_observer.claude_history.MAX_HELPER_OUTPUT_BYTES", 1024),
            ):
                output, failure = _run_worker(self.config, timeout=2.0)
            self.assertIsNone(output)
            self.assertEqual(failure, "history_limit")
            self.assertEqual(len(processes), 1)
            self.assertIsNotNone(processes[0].poll())

    def test_root_census_rejects_symlink_and_fifo_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            projects = Path(temporary) / "projects"
            projects.mkdir()
            (projects / "link").symlink_to(Path(temporary), target_is_directory=True)
            with self.assertRaises(_WorkerFailure) as symlink_error:
                census_projects(projects)
            self.assertEqual(symlink_error.exception.code, "history_unsafe_entry")

        with tempfile.TemporaryDirectory() as temporary:
            projects = Path(temporary) / "projects"
            project = projects / "project"
            project.mkdir(parents=True)
            os.mkfifo(project / (FIRST + ".jsonl"))
            with self.assertRaises(_WorkerFailure) as fifo_error:
                census_projects(projects)
            self.assertEqual(fifo_error.exception.code, "history_unsafe_entry")

    def test_transcript_clock_ignores_rename_housekeeping_sidechains_and_meta_messages(self):
        path = self.config / "transcript.jsonl"
        message = {
            "type": "assistant",
            "sessionId": FIRST,
            "isSidechain": False,
            "timestamp": "2026-10-01T01:02:03.456Z",
            "message": {"role": "assistant", "content": "private text must be discarded"},
        }
        path.write_text(json.dumps(message) + "\n")
        initial = transcript_activity(path, FIRST)
        for record in (
            {"type": "custom-title", "customTitle": "Renamed"},
            {"type": "system", "timestamp": "2026-10-02T01:02:03Z"},
            {**message, "isSidechain": True, "timestamp": "2026-10-03T01:02:03Z"},
            {**message, "isMeta": True, "timestamp": "2026-10-04T01:02:03Z"},
        ):
            with path.open("a") as handle:
                handle.write(json.dumps(record) + "\n")
        os.utime(path, None)
        self.assertEqual(transcript_activity(path, FIRST), initial)
        self.assertEqual(set(initial), {"at", "source", "health", "reason"})
        self.assertNotIn("private", json.dumps(initial))
        newer = {**message, "timestamp": "2026-10-05T01:02:03.456Z"}
        with path.open("a") as handle:
            handle.write(json.dumps(newer) + "\n")
        self.assertGreater(transcript_activity(path, FIRST)["at"], initial["at"])

    def test_incomplete_wrong_identity_and_unsafe_activity_fail_per_row(self):
        path = self.config / "transcript.jsonl"
        value = {
            "type": "user",
            "sessionId": SECOND,
            "isSidechain": False,
            "timestamp": "2026-10-01T01:02:03Z",
            "message": {"role": "user"},
        }
        path.write_text(json.dumps(value) + "\n")
        self.assertEqual(transcript_activity(path, FIRST)["reason"], "activity_identity_conflict")
        path.write_text(json.dumps(value))
        self.assertEqual(transcript_activity(path, FIRST)["reason"], "activity_record_incomplete")
        link = self.config / "link.jsonl"
        link.symlink_to(path)
        self.assertIsNone(transcript_activity(link, FIRST)["at"])


if __name__ == "__main__":
    unittest.main()
