"""Controlled owned pipes and scheduler clocks; no native provider actions."""

import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from agent_observer.service_hints import Hints, MAX_BUFFER, message, parse_message
from agent_observer.service_scheduler import Scheduler
from agent_observer.service_state import ServiceState


def stop_process(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=2)


class HintPortTest(unittest.TestCase):
    def setUp(self):
        self.selector = selectors.DefaultSelector()
        self.scheduler = Scheduler(("codex",), intervals={"runtime": 20000, "history": 60000})
        self.processes = []
        self.port = None

    def tearDown(self):
        if self.port:
            self.port.close()
        for process in self.processes:
            if process.returncode is None:
                stop_process(process)
        self.selector.close()

    def factory(self, payload):
        def spawn(provider, config, epoch):
            wire = payload(epoch)
            process = subprocess.Popen([sys.executable, "-I", "-B", "-c",
                "import os,time;os.write(1," + repr(wire) + ");time.sleep(30)"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
            self.processes.append(process)
            return process
        return spawn

    def start(self, payload, **options):
        self.port = Hints({"codex": ("/fixture/codex", "explicit")}, self.selector,
                          self.scheduler, stop_process, factory=self.factory(payload), **options)
        self.port.tick(1000)
        return self.port.sources["codex"]

    def read(self, source, now=1001):
        self.assertTrue(self.selector.select(2))
        self.port.read(source, now)

    def test_hints_never_change_receipts_or_conversation_clocks(self):
        state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
        before = state.frame("status", 1)
        source = self.start(lambda epoch: message(epoch, "runtime", "native_event") + message(epoch, "history", "native_event"))
        self.read(source)
        after = state.frame("status", 2)
        self.assertEqual(before["sources"], after["sources"])
        self.assertIsNone(after["snapshot"])
        self.assertEqual(self.scheduler.dirty, {("codex", "runtime"): 1, ("codex", "history"): 1})

    def test_large_valid_burst_is_bounded_and_coalesced(self):
        source = self.start(lambda epoch: message(epoch, "history", "native_event") * 1000)
        deadline = time.monotonic() + 4
        while self.port.counts["codex"]["history"] < 2 and time.monotonic() < deadline:
            self.read(source)
        self.assertLessEqual(len(source.buffer), MAX_BUFFER)
        self.assertIn("codex", self.port.sources)
        self.assertEqual(self.scheduler.dirty[("codex", "history")], 1)
        self.port.close()
        self.assertIsNotNone(source.process.returncode)

    def test_old_epoch_malformed_and_oversized_messages_reject_source(self):
        for payload in (lambda epoch: message(str(uuid.uuid4()), "runtime", "native_event"),
                        lambda epoch: b'{"raw":"content"}\n',
                        lambda epoch: b'x' * 2048,
                        lambda epoch: json.dumps({"epoch": epoch, "component": [], "reason": "native_event"}).encode() + b'\n'):
            with self.subTest(payload=payload):
                source = self.start(payload)
                self.read(source)
                self.assertEqual(self.port.sources, {})
                self.assertEqual(self.port.counts["codex"]["rejected"], 1)
                self.assertIsNotNone(source.process.returncode)
                self.assertGreater(self.port.due["codex"], 1001)
                self.port.close()

    def test_stale_source_object_cannot_hint_new_source(self):
        source = self.start(lambda epoch: message(epoch, "runtime", "native_event"))
        self.port.drop(source, 1001)
        self.port.tick(6001)
        successor = self.port.sources["codex"]
        self.assertNotEqual(source.epoch, successor.epoch)
        self.port.read(source, 6002)
        self.assertEqual(self.scheduler.dirty[("codex", "runtime")], 0)

    def test_unavailable_feed_retry_does_not_poll_provider_faster(self):
        source = self.start(lambda epoch: b'')
        self.port.drop(source, 1001)
        self.assertEqual(self.scheduler.dirty[("codex", "runtime")], 0)
        self.port.tick(6001)
        self.port.drop(self.port.sources["codex"], 6002)
        self.assertEqual(self.port.due["codex"], 16002)
        self.assertEqual(self.scheduler.dirty[("codex", "history")], 0)

    def test_ready_loss_requests_only_budgeted_reconciliation(self):
        source = self.start(lambda epoch: message(epoch, "runtime", "source_ready"))
        self.read(source)
        self.assertTrue(self.port.counts["codex"]["ready"])
        self.port.drop(source, 1002)
        self.assertFalse(self.port.counts["codex"]["ready"])
        self.assertEqual(self.scheduler.dirty[("codex", "history")], 1)

    def test_diagnostics_are_private_bounded_and_reject_foreign_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "hints.json"
            source = self.start(lambda epoch: message(epoch, "history", "source_ready"), diagnostics=path)
            self.read(source)
            self.port.tick(2001)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertLess(path.stat().st_size, 4096)
            self.assertTrue(json.loads(path.read_text())["providers"]["codex"]["ready"])
            path.unlink()
            path.symlink_to(root / "unowned")
            self.port.changed = True
            with self.assertRaisesRegex(ValueError, "diagnostics_scope"):
                self.port.tick(3001)
            self.assertFalse((root / "unowned").exists())

    def test_private_message_contract_rejects_extra_payload(self):
        epoch = str(uuid.uuid4())
        self.assertEqual(parse_message(message(epoch, "runtime", "native_event"), epoch)["component"], "runtime")
        with self.assertRaises(ValueError):
            parse_message(json.dumps({"epoch": epoch, "component": "runtime", "reason": "native_event", "payload": "x"}).encode(), epoch)
