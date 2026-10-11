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
