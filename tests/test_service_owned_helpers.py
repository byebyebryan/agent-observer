"""Actual owned helper groups are stopped on deadline and leader failure."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from test_service_runtime import Running

from agent_observer.claude_history import _run_worker
from agent_observer.service_runtime import Runtime, Worker
from agent_observer.service_scheduler import Scheduler


def alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


class OwnedHelpersTest(unittest.TestCase):
    def test_collection_has_its_own_deadline_without_a_publisher(self):
        with tempfile.TemporaryDirectory(prefix="ao-independent-deadline-") as directory:
            root = Path(directory)
            marker = root / "child.pid"
            child = "import os,time;from pathlib import Path;Path(" + repr(str(marker)) + ").write_text(str(os.getpid()));time.sleep(30)"
            code = "import sys,time,subprocess;sys.path.insert(0," + repr(str(Path(__file__).resolve().parent.parent)) + ");from agent_observer import _service_worker;from unittest.mock import patch\ndef slow(*a,**k):\n subprocess.Popen([sys.executable,'-c'," + repr(child) + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n time.sleep(30)\nwith patch('agent_observer.codex_snapshot.collect_codex',side_effect=slow):_service_worker.main()"
            process = subprocess.Popen([sys.executable, "-I", "-B", "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
            request = {"hostScope": "fixture", "provider": "codex", "component": "runtime", "configHome": str(root), "configHomeKind": "explicit", "timeoutMs": 1000}
            try:
                process.communicate(json.dumps(request).encode(), timeout=3)
                self.assertEqual(process.returncode, -9)
                pid = int(marker.read_text())
                deadline = time.monotonic() + 1
                while alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(alive(pid))
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, 9)
                    process.wait()
    def test_shared_history_group_requires_its_own_leader(self):
        with patch("agent_observer.claude_history.os.getpgrp", return_value=-1), patch("agent_observer.claude_history.subprocess.Popen") as spawn:
            self.assertEqual(_run_worker(Path("/unused"), timeout=1, owned_worker_group=True), (None, "history_source_failed"))
        spawn.assert_not_called()

    def test_outer_deadline_stops_actual_history_helper(self):
        with tempfile.TemporaryDirectory(prefix="ao-helper-proof-") as directory:
            root = Path(directory)
            marker, child = root / "pid.json", root / "fake_sdk.py"
            child.write_text("import os,json,time\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").write_text(json.dumps([os.getpid(),os.getpgrp()]))\ntime.sleep(30)\n")
            source_root = str(Path(__file__).resolve().parent.parent)
            code = "import sys;sys.path.insert(0," + repr(source_root) + ");from pathlib import Path;from unittest.mock import patch;from agent_observer.claude_history import _run_worker\nwith patch('agent_observer.claude_history.Path.with_name',return_value=Path(" + repr(str(child)) + ")):_run_worker(Path(" + repr(str(root)) + "),timeout=30,owned_worker_group=True)"
            parents = []
            def factory(job):
                process = subprocess.Popen([sys.executable, "-I", "-B", "-c", code], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
                parents.append(process)
                return process
            with Running(collect=True, factory=factory, scheduler=Scheduler(("codex",), timeout_ms=1000)) as server:
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                pid, group = json.loads(marker.read_text())
                self.assertEqual(group, parents[0].pid)
                while alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertFalse(alive(pid))
                self.assertIsNotNone(parents[0].returncode)
                self.assertEqual(server.state.receipts["codex"]["runtime"].lastResult, "collection_timeout")

    def test_exited_leader_is_not_reaped_before_group_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="ao-helper-crash-") as directory:
            marker = Path(directory) / "child.pid"
            child = "import os,time;from pathlib import Path;Path(" + repr(str(marker)) + ").write_text(str(os.getpid()));time.sleep(30)"
            leader = "import subprocess,sys,time,os;subprocess.Popen([sys.executable,'-c'," + repr(child) + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.1);os._exit(1)"
            process = subprocess.Popen([sys.executable, "-I", "-B", "-c", leader], stdout=subprocess.PIPE, start_new_session=True)
            try:
                deadline = time.monotonic() + 3
                while (not marker.exists() or Runtime._exit_status(process) is None) and time.monotonic() < deadline:
                    time.sleep(0.01)
                pid = int(marker.read_text())
                self.assertTrue(alive(pid))
                self.assertEqual(Runtime._exit_status(process), 1)
                self.assertIsNone(process.returncode)
                Runtime._stop_worker(None, Worker(None, process))
                self.assertEqual(process.returncode, 1)
                while alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(alive(pid))
            finally:
                if process.returncode is None:
                    os.killpg(process.pid, 9)
                    process.wait()
                process.stdout.close()
