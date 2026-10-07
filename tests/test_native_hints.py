"""Controlled native metadata shapes and actual disposable inotify trees."""

import os
from pathlib import Path
import select
import struct
import tempfile
import unittest

from agent_observer.claude_hints import Watcher, OVERFLOW
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
        self.assertLessEqual(len(self.watcher.watches), 7)
