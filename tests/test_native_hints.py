"""Controlled native metadata shapes and actual disposable inotify trees."""

import copy
import json
import os
from pathlib import Path
import select
import struct
import tempfile
import time
import unittest

from agent_observer.claude_hints import Watcher, OVERFLOW, MAX_FINGERPRINTS, MAX_METADATA_BYTES, MAX_METADATA_EVENTS, scheduling_projection
from agent_observer.codex_hints import Changes, MAX_CONTEXTS


class CodexHintsTest(unittest.TestCase):
    def test_finite_methods_and_wait_flags_deduplicate_without_content(self):
        changes = Changes()
        value = {"method": "thread/status/changed", "params": {"threadId": "fixture", "status": {"type": "active", "activeFlags": []}}}
        self.assertEqual(changes.components(value), ("runtime", "history"))
        self.assertEqual(changes.components(value), ())
        value["params"]["status"]["activeFlags"] = ["waitingOnUserInput"]
        self.assertEqual(changes.components(value), ("runtime", "history"))
        self.assertEqual(changes.components(value), ())
        value["params"]["status"] = {"type": "idle"}
        self.assertEqual(changes.components(value), ("runtime", "history"))

    def test_unknown_requests_content_and_malformed_messages_are_ignored(self):
        changes = Changes()
        for value in ([], {"method": []}, {"method": "turn/completed", "params": {"threadId": "fixture"}},
                      {"method": "thread/started", "id": 1, "params": {"thread": {"id": "fixture"}}},
                      {"method": "thread/started", "params": {"thread": {"id": "bad\n"}}},
                      {"method": "thread/status/changed", "params": {"threadId": "fixture", "status": {"type": []}}}):
            with self.subTest(value=value):
                self.assertEqual(changes.components(value), ())
        self.assertFalse(changes.seen)

    def test_name_hints_retain_only_a_digest_and_started_cache_is_bounded(self):
        changes = Changes()
        value = {"method": "thread/name/updated", "params": {"threadId": "fixture", "threadName": "private native label"}}
        self.assertTrue(changes.components(value))
        self.assertFalse(changes.components(value))
        self.assertNotIn("private native label", str(changes.seen))
        for number in range(MAX_CONTEXTS + 10):
            changes.components({"method": "thread/started", "params": {"thread": {"id": str(number), "preview": "discarded"}}})
        self.assertEqual(len(changes.seen), MAX_CONTEXTS)
        self.assertNotIn("discarded", str(changes.seen))


class ClaudeHintsTest(unittest.TestCase):
    def registry(self):
        return {"pid": 123, "sessionId": "12345678-1234-5678-9abc-123456789abc",
                "procStart": "123", "pidDomain": "fixture", "kind": "interactive",
                "status": "busy", "statusUpdatedAt": 1000, "jobId": None,
                "cwd": "/fixture", "nameSource": "user", "name": "Native name"}

    def job(self):
        return {"sessionId": self.registry()["sessionId"], "state": "working",
                "tempo": "active", "cwd": "/fixture", "inFlight":
                {"tasks": 1, "queued": 0, "drainableMonitors": 0}, "block": None}

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ao-watch-")
        self.home = Path(self.directory.name)
        for name in ("sessions", "jobs", "projects"):
            (self.home / name).mkdir()
        self.watcher = Watcher(self.home)

    def tearDown(self):
        self.watcher.close()
        self.directory.cleanup()

    def events(self):
        select.select([self.watcher.fd], [], [], 1)
        return self.watcher.read()

    def test_registry_noop_working_updates_deduplicate_but_attention_identity_and_metadata_wake(self):
        path = self.home / "sessions/123.json"
        value = self.registry()
        path.write_text(json.dumps(value))
        self.assertEqual(self.events(), {"runtime"})
        value.update(status="shell", statusUpdatedAt=2000, detail="private discarded detail")
        path.write_text(json.dumps(value))
        self.assertFalse(self.events())
        for changes in ({"status": "waiting", "waitingFor": "input needed"},
                        {"waitingFor": "permission prompt"}, {"procStart": "456"},
                        {"name": "Renamed"}, {"cwd": "/another"}, {"status": "idle"}):
            value.update(changes)
            path.write_text(json.dumps(value))
            self.assertEqual(self.events(), {"runtime"})
        self.assertNotIn("private discarded detail", str(self.watcher.fingerprints))
        self.assertNotIn("Renamed", str(self.watcher.fingerprints))

    def test_job_projection_ignores_nonzero_count_churn_but_preserves_pending_question_and_terminal_fields(self):
        value = self.job()
        first = scheduling_projection("jobs", "12345678", value)
        noisy = copy.deepcopy(value)
        noisy["inFlight"]["tasks"] = 12
        noisy["detail"] = "private discarded detail"
        self.assertEqual(first, scheduling_projection("jobs", "12345678", noisy))
        for changes in ({"inFlight": {"tasks": 0, "queued": 0, "drainableMonitors": 0}},
                        {"tempo": "blocked", "block": {"questions": [{}]}},
                        {"lastTerminalAt": "2026-10-07T00:00:01.000Z"},
                        {"cwd": "/another"},
                        {"state": "done", "tempo": "idle", "lastTerminalAt": "2026-10-07T00:00:02.000Z"}):
            changed = copy.deepcopy(value)
            changed.update(changes)
            self.assertNotEqual(first, scheduling_projection("jobs", "12345678", changed))

    def test_failed_job_keeps_registry_terminal_clock_relation_and_unfamiliar_records_wake(self):
        from agent_observer.claude_metadata import _job_record
        registry = self.registry()
        registry["jobId"] = "12345678"
        job = self.job()
        job.update(state="failed", tempo="idle", lastTerminalAt="2026-10-07T00:00:01.000Z")
        linked = _job_record("12345678", job)
        original = scheduling_projection("sessions", "123.json", registry, linked_job=linked)
        registry["statusUpdatedAt"] = 2000
        self.assertNotEqual(original, scheduling_projection("sessions", "123.json", registry, linked_job=linked))
        path = self.home / "sessions/123.json"
        for payload in ({}, {**self.registry(), "status": "new_phase"},
                        {**self.registry(), "kind": "daemon-worker"},
                        {**self.registry(), "status": "waiting", "waitingFor": "new wait"}):
            path.write_text(json.dumps(payload))
            self.assertEqual(self.events(), {"runtime"})
            path.write_text(json.dumps(payload))
            self.assertEqual(self.events(), {"runtime"})

    def test_invalid_oversized_fifo_delete_and_recovery_never_hide_a_wakeup(self):
        path = self.home / "sessions/123.json"
        valid = json.dumps(self.registry())
        path.write_text(valid)
        self.assertEqual(self.events(), {"runtime"})
        path.write_text(valid)
        self.assertFalse(self.events())
        for invalid in ('{"pid":123,"pid":123}', "x" * (MAX_METADATA_BYTES + 1)):
            path.write_text(invalid)
            self.assertEqual(self.events(), {"runtime"})
            path.write_text(valid)
            self.assertEqual(self.events(), {"runtime"})
        path.unlink()
        self.assertEqual(self.events(), {"runtime"})
        os.mkfifo(path)
        started = time.monotonic()
        self.assertEqual(self.events(), {"runtime"})
        self.assertLess(time.monotonic() - started, .5)
        path.unlink()
        path.write_text(valid)
        self.assertEqual(self.events(), {"runtime"})

    def test_fingerprint_count_is_bounded_and_overflow_forgets_old_digests(self):
        from unittest.mock import patch
        directory = next(d for d in self.watcher.watches.values() if d.root == "sessions")
        value = self.registry()
        with patch.object(self.watcher, "_metadata", return_value=value):
            for index in range(MAX_FINGERPRINTS + 5):
                # Unfamiliar filename/PID pairs must reconcile, not cache.
                self.watcher.runtime_changed(directory, str(index + 1) + ".json")
            for index in range(MAX_FINGERPRINTS + 5):
                value["pid"] = index + 1
                self.watcher.runtime_changed(directory, str(index + 1) + ".json")
        self.assertEqual(len(self.watcher.fingerprints), MAX_FINGERPRINTS)
        self.watcher.events(struct.pack("iIII", -1, OVERFLOW, 0, 0))
        self.assertFalse(self.watcher.fingerprints)

    def test_runtime_chunk_reads_unique_files_once_and_excess_work_reconciles(self):
        from unittest.mock import patch
        wd = next(wd for wd, directory in self.watcher.watches.items() if directory.root == "sessions")
        def packet(number):
            name = (str(number) + ".json").encode() + b"\0"
            return struct.pack("iIII", wd, 8, 0, len(name)) + name
        with patch.object(self.watcher, "runtime_changed", return_value=False) as changed:
            self.assertFalse(self.watcher.events(packet(123) * 100))
            self.assertEqual(changed.call_count, 1)
        with patch.object(self.watcher, "runtime_changed", return_value=False) as changed:
            self.assertEqual(self.watcher.events(b"".join(packet(n + 1) for n in range(MAX_METADATA_EVENTS + 10))), {"runtime"})
            self.assertEqual(changed.call_count, MAX_METADATA_EVENTS)

    def test_symlink_and_unsafe_files_reconcile_without_reading_their_contents(self):
        from unittest.mock import patch
        directory = next(d for d in self.watcher.watches.values() if d.root == "sessions")
        target = self.home / "unwatched.json"
        target.write_text(json.dumps(self.registry()))
        path = self.home / "sessions/123.json"
        path.symlink_to(target)
        with patch("agent_observer.claude_hints.os.read", wraps=os.read) as read:
            self.assertTrue(self.watcher.runtime_changed(directory, "123.json"))
            read.assert_not_called()
        path.unlink()
        path.write_text(json.dumps(self.registry()))
        path.chmod(0o622)
        with patch("agent_observer.claude_hints.os.read", wraps=os.read) as read:
            self.assertTrue(self.watcher.runtime_changed(directory, "123.json"))
            read.assert_not_called()
        self.assertFalse(self.watcher.fingerprints)

    def test_registry_atomic_replace_and_unrelated_files(self):
        temporary = self.home / "sessions/tmp-file"
        temporary.write_text("bounded fixture")
        self.assertFalse(self.events())
        os.replace(temporary, self.home / "sessions/123.json")
        self.assertEqual(self.events(), {"runtime"})
        (self.home / "settings.json").write_text("fixture")
        self.assertFalse(self.events())

    def test_new_job_and_project_then_append_to_open_history_file(self):
        job = self.home / "jobs/fixture"
        project = self.home / "projects/fixture"
        job.mkdir()
        project.mkdir()
        self.assertEqual(self.events(), {"runtime", "history"})
        self.watcher.reconcile()
        self.watcher.read()  # ignored old watches, if any
        (job / "state.json").write_text("fixture")
        self.assertEqual(self.events(), {"runtime"})
        (job / "stdout.log").write_text("ignored")
        self.assertFalse(self.events())
        with (project / "fixture.jsonl").open("w") as stream:
            stream.write("fixture\n")
            stream.flush()
            self.assertEqual(self.events(), {"history"})
        self.watcher.read()

    def test_overflow_and_directory_replacement_request_rearm(self):
        self.assertEqual(self.watcher.events(struct.pack("iIII", -1, OVERFLOW, 0, 0)), {"runtime", "history"})
        self.assertTrue(self.watcher.rearm)
        previous = len(self.watcher.watches)
        for number in range(20):
            old = self.home / "old-sessions"
            (self.home / "sessions").rename(old)
            (self.home / "sessions").mkdir()
            self.events()
            self.watcher.reconcile()
            old.rmdir()
            self.watcher.read()
        self.assertEqual(len(self.watcher.watches), previous)
        # Kernel watches also stay bounded, including moved-away directories.
        info = Path(f"/proc/self/fdinfo/{self.watcher.fd}").read_text()
        self.assertEqual(sum(line.startswith("inotify wd:") for line in info.splitlines()), previous)

    def test_nested_transcript_writes_do_not_refresh_the_primary_catalog(self):
        project = self.home / "projects/project"
        project.mkdir()
        self.assertEqual(self.events(), {"history"})
        self.watcher.reconcile()
        self.watcher.read()
        nested = project / "session/subagents"
        nested.mkdir(parents=True)
        self.assertFalse(self.events())
        self.assertFalse(self.watcher.rearm)
        self.assertFalse(self.watcher.reconcile())
        self.assertEqual(len(self.watcher.watches), 5)
        with (nested / "agent-fixture.jsonl").open("w") as stream:
            for _ in range(100):
                stream.write("bounded fixture\n")
                stream.flush()
        self.assertFalse(self.events())
        (project / "primary.jsonl").write_text("bounded fixture\n")
        self.assertEqual(self.events(), {"history"})

    def test_watch_limit_permission_and_symlink_failures_recover(self):
        with self.assertRaisesRegex(ValueError, "watch_limit"):
            Watcher(self.home, max_watches=1)
        link = self.home / "alias"
        link.symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "watch_scope"):
            Watcher(link)
        sessions = self.home / "sessions"
        sessions.chmod(0)
        try:
            if os.geteuid() != 0:
                with self.assertRaises(OSError):
                    Watcher(self.home)
        finally:
            sessions.chmod(0o700)
        recovered = Watcher(self.home)
        self.assertEqual(len(recovered.watches), 4)
        recovered.close()

    def test_malformed_events_fail_closed_and_depth_is_bounded(self):
        for data in (b'x', struct.pack("iIII", 1, 0, 0, 4097), struct.pack("iIII", 1, 0, 0, 8)):
            with self.assertRaisesRegex(ValueError, "watch_event"):
                self.watcher.events(data)
        directory = self.home / "projects/p"
        for _ in range(10):
            directory.mkdir()
            directory = directory / "nested"
        self.watcher.reconcile()
        self.assertEqual(len(self.watcher.watches), 5)
