"""Contract tests for isolated Claude SDK saved-history metadata projection."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import _claude_history_worker
from agent_observer._claude_history_worker import (
    MAX_COMPANION_BYTES,
    _bounded_cwd,
    _WorkerFailure,
    census_projects,
    duplicate_file_kind,
    transcript_activity,
)
from agent_observer.claude_history import SDK_VERSION, _run_worker, collect_saved_history

FIRST = "01234567-0123-4567-89ab-0123456789ab"
SECOND = "11234567-0123-4567-89ab-0123456789ab"
THIRD = "21234567-0123-4567-89ab-0123456789ab"


class MetadataSdkLoadingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ao-sdk-load-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.package = self.root / "claude_agent_sdk"
        self.package.mkdir()
        (self.package / "__init__.py").write_text("raise AssertionError('client initializer executed')\n")
        (self.package / "_version.py").write_text("__version__ = " + repr(SDK_VERSION) + "\n")
        (self.package / "types.py").write_text("SENTINEL = 'metadata fixture'\n")
        (self.package / "_internal").mkdir()
        (self.package / "_internal/__init__.py").write_text("\n")
        (self.package / "_internal/sessions.py").write_text(
            "from ..types import SENTINEL\n"
            "def list_sessions(): return [SENTINEL]\n"
            "def _read_session_lite(path): return None\n"
            "def _parse_session_info_from_lite(sid, lite): return None\n"
        )

    def child(self, assertion):
        worker = str(Path(_claude_history_worker.__file__).resolve())
        source = (
            "import json,runpy,sys\n"
            "sys.path.insert(0," + repr(str(self.root)) + ")\n"
            "worker=runpy.run_path(" + repr(worker) + ")\n"
            "blocked=[]\nworker['_install_audit_guard'](blocked)\n" + assertion
        )
        return subprocess.run([os.sys.executable, "-I", "-B", "-c", source],
                              capture_output=True, timeout=10)

    def test_only_metadata_subtree_loads_without_client_initializer(self):
        result = self.child(
            "v,s=worker['_metadata_sdk']()\n"
            "assert v==worker['SDK_VERSION']\n"
            "assert s.list_sessions()==['metadata fixture']\n"
            "assert 'claude_agent_sdk' not in sys.modules\n"
            "assert '_observer_claude_metadata.types' in sys.modules\n"
            "assert not blocked\nprint(json.dumps({'status':'loaded'}))\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"status": "loaded"})

    def test_missing_function_and_changed_sdk_dependency_fail_explicitly(self):
        for change in ("missing_function", "different_version"):
            with self.subTest(change=change):
                version_file = self.package / "_version.py"
                version_file.write_text("__version__ = " + repr(SDK_VERSION if change == "missing_function" else "0.0.0") + "\n")
                sessions = self.package / "_internal/sessions.py"
                previous = sessions.read_text()
                if change == "missing_function":
                    sessions.write_text(previous + "\n_read_session_lite = None\n")
                result = self.child(
                    "try: worker['_metadata_sdk']()\n"
                    "except ImportError: print(json.dumps({'status':'unavailable'}))\n"
                    "else: raise AssertionError('invalid binding accepted')\n"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"status": "unavailable"})
                sessions.write_text(previous)

    def test_metadata_import_cannot_write_or_spawn(self):
        forbidden = self.root / "forbidden"
        for code in (
            "from pathlib import Path\nPath(" + repr(str(forbidden)) + ").write_text('forbidden')\n",
            "import subprocess\nsubprocess.run(['/usr/bin/true'])\n",
            "import socket\nsocket.socket()\n",
        ):
            with self.subTest(code=code.splitlines()[0]):
                (self.package / "types.py").write_text(code)
                result = self.child(
                    "try: worker['_metadata_sdk']()\n"
                    "except PermissionError: print(json.dumps({'blocked':bool(blocked)}))\n"
                    "else: raise AssertionError('mutating import accepted')\n"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"blocked": True})
                self.assertFalse(forbidden.exists())

    def test_ambiguous_package_location_and_existing_public_import_are_rejected(self):
        for prefix in (
            "import importlib.util,types\nimportlib.util.find_spec=lambda _:types.SimpleNamespace(origin='fixture',submodule_search_locations=['one','two'])\n",
            "sys.modules['claude_agent_sdk']=object()\n",
        ):
            with self.subTest(prefix=prefix):
                result = self.child(prefix +
                    "try: worker['_metadata_sdk']()\n"
                    "except ImportError: print(json.dumps({'status':'unavailable'}))\n"
                    "else: raise AssertionError('ambiguous binding accepted')\n"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"status": "unavailable"})


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
    def test_census_distinguishes_sdk_omissions_companions_and_display_limits(self):
        payload = worker_payload([worker_row(FIRST, created_at=1, last_modified=2),
                                  worker_row(SECOND, created_at=1, last_modified=3)], candidates=5)
        counts = {"candidate_ids": 4, "sdk_returned_ids": 3, "projected_ids": 2,
                  "sdk_omitted_ids": 1, "unresolved_ids": 1, "duplicate_ids": 1,
                  "resolved_companion_ids": 1, "malformed_filename_ids": 0}
        payload["census"].update(counts)
        result = self.run_collector(payload, history_limit=1)
        self.assertEqual(result["census"]["sdk_omitted_ids"], 1)
        self.assertEqual(result["census"]["unresolved_ids"], 1)
        self.assertEqual(result["census"]["display_omitted_ids"], 1)
        self.assertFalse(result["coverage"]["complete"])
        for field in counts:
            invalid = json.loads(json.dumps(payload))
            invalid["census"][field] = True
            self.assertEqual(self.run_collector(invalid)["errors"], [{"code": "history_source_failed"}])
        payload["census"]["sdk_omitted_ids"] = 2
        self.assertEqual(self.run_collector(payload)["errors"], [{"code": "history_source_failed"}])

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

    def test_metadata_companion_does_not_compete_with_exact_conversation_source(self):
        projects = self.config / "projects"
        original = projects / "original"
        worktree = projects / "worktree"
        original.mkdir(parents=True)
        worktree.mkdir()
        full = original / (FIRST + ".jsonl")
        companion = worktree / full.name
        full.write_text(json.dumps({"type": "file-history-snapshot", "snapshot": {}}) + "\n" + json.dumps({"type": "user", "sessionId": FIRST, "timestamp": "2026-10-05T00:00:00Z", "message": {"content": "synthetic"}}) + "\n")
        companion.write_text(json.dumps({"type": "custom-title", "sessionId": FIRST, "customTitle": "Companion title"}) + "\n")
        self.assertEqual(duplicate_file_kind(full, FIRST), "conversation")
        self.assertEqual(duplicate_file_kind(companion, FIRST), "companion")
        census = census_projects(projects)
        self.assertIn(FIRST, census["resolved_duplicates"])
        self.assertEqual(census["transcript_paths"][FIRST], full)
        # A second conversation, mismatched UUID, unknown metadata, duplicate
        # keys and a partial record cannot be resolved by mtime/size preference.
        for content in (
            full.read_text(),
            json.dumps({"type": "custom-title", "sessionId": SECOND}) + "\n",
            json.dumps({"type": "future-metadata", "sessionId": FIRST}) + "\n",
            '{"type":"custom-title","sessionId":"' + FIRST + '","sessionId":"' + SECOND + '"}\n',
            json.dumps({"type": "custom-title", "sessionId": FIRST}),
        ):
            with self.subTest(content=content[:24]):
                companion.write_text(content)
                self.assertNotIn(FIRST, census_projects(projects)["resolved_duplicates"])

    def test_companion_resolution_refuses_oversize_and_inflight_growth(self):
        companion = self.config / (FIRST + ".jsonl")
        record = {"type": "custom-title", "sessionId": FIRST, "customTitle": "x" * MAX_COMPANION_BYTES}
        companion.write_text(json.dumps(record) + "\n")
        self.assertEqual(duplicate_file_kind(companion, FIRST), "unproved")

        record["customTitle"] = "Stable title"
        companion.write_text(json.dumps(record) + "\n")
        real_read = os.read

        def read_while_provider_appends(fd, count):
            data = real_read(fd, count)
            with companion.open("ab") as stream:
                stream.write((json.dumps({"type": "mode", "sessionId": FIRST, "mode": "normal"}) + "\n").encode())
            return data

        with patch("agent_observer._claude_history_worker.os.read", side_effect=read_while_provider_appends):
            self.assertEqual(duplicate_file_kind(companion, FIRST), "unproved")
        self.assertEqual(duplicate_file_kind(companion, FIRST), "companion")

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
            *(
                {**message, "type": "user", "timestamp": "2026-10-04T02:00:00Z",
                 "message": {"role": "user", "content": envelope}}
                for envelope in ("<command-name>/exit</command-name><command-message>exit</command-message><command-args></command-args>",
                                 "<local-command-stdout>private UI output</local-command-stdout>",
                                 "<local-command-stderr>private UI error</local-command-stderr>")
            ),
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
        before_prompt = transcript_activity(path, FIRST)["at"]

        # Ordinary slash-looking text is still a conversation prompt.
        prompt = {**message, "type": "user", "timestamp": "2026-10-06T01:02:03Z",
                  "message": {"role": "user", "content": "/path is the example I want explained"}}
        with path.open("a") as handle:
            handle.write(json.dumps(prompt) + "\n")
        self.assertGreater(transcript_activity(path, FIRST)["at"], before_prompt)

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
