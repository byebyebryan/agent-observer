"""Real image descriptors and bounded private transfer; no native providers."""

import array
import copy
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from test_service_runtime import Running, scoped_snapshot
from test_service_owned_helpers import alive

from agent_observer import native_artifacts
from agent_observer._image_memo import MAX_ENTRIES, MAX_PACKET, ImageMemo, receive, send
from agent_observer.claude_history import _run_worker
from agent_observer.contract import canonical, parse_snapshot
from agent_observer.native_artifacts import inspect_installed, inspect_process
from agent_observer.service_runtime import Runtime, Worker
from agent_observer.service_state import ServiceState


def image_fds(path):
    expected = path.stat()
    result = set()
    for value in os.listdir("/proc/self/fd"):
        try:
            info = os.fstat(int(value))
        except OSError:
            continue
        if (info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino):
            result.add(int(value))
    return result


class ImageMemoTest(unittest.TestCase):
    def test_cross_transfer_reuses_hash_and_keeps_replaced_resident_image_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sleep"
            shutil.copyfile("/usr/bin/sleep", path)
            path.chmod(0o700)
            child = subprocess.Popen([str(path), "30"])
            original, returned = ImageMemo("claude"), None
            left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            sha = hashlib.sha256
            try:
                with patch.object(native_artifacts.hashlib, "sha256", wraps=sha) as hashes:
                    first = inspect_installed(path, "claude", cache=original)
                    send(left, original)
                    returned = receive(right, "claude")
                    original.close()
                    self.assertEqual(
                        inspect_process(
                            child.pid, "claude", cache=returned, expected_path=path
                        ).artifact.sha256,
                        first.artifact.sha256,
                    )
                    self.assertEqual(hashes.call_count, 1)
                    replacement = path.with_name("replacement")
                    replacement.write_bytes(path.read_bytes() + b"\0")
                    replacement.chmod(0o700)
                    replacement.replace(path)
                    second = inspect_installed(path, "claude", cache=returned)
                    self.assertNotEqual(second.artifact.sha256, first.artifact.sha256)
                    self.assertEqual(
                        inspect_process(
                            child.pid, "claude", cache=returned, expected_path=path
                        ).artifact.sha256,
                        first.artifact.sha256,
                    )
                    # Removing the old directory entry also changes its ctime;
                    # the surviving resident image must be rehashed once.
                    inspect_process(child.pid, "claude", cache=returned, expected_path=path)
                    self.assertEqual(hashes.call_count, 3)
                    returned.export()
                    self.assertEqual(len(returned), 2)
            finally:
                child.terminate()
                child.wait(timeout=5)
                original.close()
                if returned is not None:
                    anchors = [fd for fd, _ in returned.entries.values()]
                    returned.close()
                    for fd in anchors:
                        with self.assertRaises(OSError):
                            os.fstat(fd)
                left.close()
                right.close()

    def test_same_inode_mutation_and_mode_change_cannot_use_old_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            path.write_bytes(b"first")
            path.chmod(0o700)
            memo = ImageMemo("codex")
            try:
                before = inspect_installed(path, "codex", cache=memo)
                stamp = path.stat()
                path.write_bytes(b"other")
                os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                after = inspect_installed(path, "codex", cache=memo)
                self.assertEqual(before.stamp, after.stamp)
                self.assertNotEqual(before.artifact.sha256, after.artifact.sha256)
                memo.export()
                self.assertEqual(len(memo), 1)
                path.chmod(0o722)
                with self.assertRaisesRegex(ValueError, "runtime_image_ownership_mismatch"):
                    inspect_installed(path, "codex", cache=memo)
                self.assertEqual(json.loads(memo.export()[0])["records"], [])
                with self.assertRaisesRegex(ValueError, "anchor_required"):
                    memo[("codex", ())] = before.artifact
            finally:
                memo.close()

    def test_capacity_eviction_closes_old_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            memo = ImageMemo("codex")
            oldest = None
            try:
                for index in range(MAX_ENTRIES + 1):
                    path = Path(directory) / str(index)
                    path.write_bytes(b"image")
                    inspect_installed(path, "codex", cache=memo)
                    if oldest is None:
                        oldest = next(iter(memo.entries.values()))[0]
                self.assertEqual(len(memo), MAX_ENTRIES)
                self.assertLessEqual(len(memo.export()[0]), MAX_PACKET)
                with self.assertRaises(OSError):
                    os.fstat(oldest)
            finally:
                memo.close()

    def test_rejected_packets_close_all_received_rights(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            path.write_bytes(b"image")
            path.chmod(0o700)
            memo = ImageMemo("codex")
            inspect_installed(path, "codex", cache=memo)
            packet, fds = memo.export()
            value = json.loads(packet)
            writable = os.open(path, os.O_RDWR)
            cases = [
                (b'{"imageMemo":1,"imageMemo":1}', fds, False),
                (packet + b" " * (MAX_PACKET + 1), fds, False),
                (json.dumps({**value, "provider": "claude"}).encode(), fds, False),
                (json.dumps({**value, "records": value["records"] * 2}).encode(), fds * 2, False),
                (packet, [writable], False),
                (packet, fds * 64, False),
                (packet, fds, True),
                (json.dumps({**value, "records": []}).encode(), fds, False),
            ]
            try:
                for data, rights, credentials in cases:
                    with self.subTest(size=len(data), rights=len(rights), credentials=credentials):
                        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                        try:
                            if credentials:
                                right.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
                            before = image_fds(path)
                            left.sendmsg(
                                [data],
                                [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", rights))],
                            )
                            with self.assertRaises(ValueError):
                                receive(right, "codex")
                            self.assertEqual(image_fds(path), before)
                        finally:
                            left.close()
                            right.close()
            finally:
                os.close(writable)
                memo.close()

    def test_sdk_child_does_not_inherit_image_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image, marker, child = root / "image", root / "marker", root / "sdk.py"
            image.write_bytes(b"image")
            memo = ImageMemo("claude")
            inspect_installed(image, "claude", cache=memo)
            stamp = image.stat()
            child.write_text(
                "import os,json\nfrom pathlib import Path\nfound=False\n"
                'for value in os.listdir("/proc/self/fd"):\n'
                " try: s=os.fstat(int(value))\n"
                " except OSError: continue\n"
                " found |= (s.st_dev,s.st_ino)==" + repr((stamp.st_dev, stamp.st_ino)) + "\n"
                "Path("
                + repr(str(marker))
                + ').write_text(json.dumps({"imageAnchorInherited":found}))\n'
                'print("{}")\n'
            )
            try:
                with patch("agent_observer.claude_history.Path.with_name", return_value=child):
                    _run_worker(root, timeout=2)
                self.assertEqual(json.loads(marker.read_text()), {"imageAnchorInherited": False})
            finally:
                memo.close()

    def test_actual_spawn_and_optional_send_failure_still_return_bounded_observations(self):
        for fail_send in [False, True]:
            with (
                self.subTest(fail_send=fail_send),
                tempfile.TemporaryDirectory() as directory,
                Running() as server,
            ):
                server.state.configs["codex"] = (directory, "explicit")
                job = server.runtime.scheduler.start_due(server.state.clock())[0]
                try:
                    if fail_send:
                        with patch(
                            "agent_observer.service_runtime.send_memo", side_effect=BlockingIOError
                        ):
                            process = server.runtime._spawn(job)
                    else:
                        process = server.runtime._spawn(job)
                    channel = process._observer_image_reply
                    output = process.stdout.read()
                    self.assertEqual(process.wait(timeout=3), 0)
                    value = parse_snapshot(output)
                    self.assertEqual(value["host"]["authority"], "fixture")
                    self.assertIsNone(value["sources"][0]["runtime"])
                    self.assertEqual(value["sessions"], [])
                finally:
                    server.runtime._close_memo_channel(process)
                    process.stdout.close()
                self.assertIsNone(process._observer_image_reply)
                self.assertTrue(process.stdin.closed and process.stdout.closed)
                if channel is not None:
                    self.assertEqual(channel.fileno(), -1)

    def test_failed_spawn_closes_private_channel(self):
        with Running() as server:
            job = server.runtime.scheduler.start_due(server.state.clock())[0]
            pair = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            with (
                patch("agent_observer.service_runtime.socket.socketpair", return_value=pair),
                patch("agent_observer.service_runtime.subprocess.Popen", side_effect=OSError),
            ):
                with self.assertRaises(OSError):
                    server.runtime._spawn(job)
            self.assertEqual([channel.fileno() for channel in pair], [-1, -1])

    def test_outer_worker_deadline_retires_transferred_anchors_and_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image, marker = root / "image", root / "marker"
            image.write_bytes(b"image")
            memo = ImageMemo("codex")
            inspect_installed(image, "codex", cache=memo)
            left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            source = str(Path(__file__).resolve().parent.parent)
            code = (
                "import sys,time,json,os,subprocess;from pathlib import Path;sys.path.insert(0,"
                + repr(source)
                + ");"
                "from agent_observer import _service_worker;from unittest.mock import patch\n"
                "def slow(*a,**k):\n"
                ' m=k["image_cache"];assert len(m)==1\n'
                ' p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
                " Path("
                + repr(str(marker))
                + ').write_text(json.dumps({"imageAnchorVerified":True,"childPid":p.pid}))\n'
                " time.sleep(30)\n"
                'with patch("agent_observer.codex_snapshot.collect_codex",side_effect=slow):_service_worker.main()'
            )
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", "-c", code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                pass_fds=(right.fileno(),),
            )
            descriptor = right.fileno()
            right.close()
            request = {
                "hostScope": "fixture",
                "provider": "codex",
                "component": "runtime",
                "configHome": directory,
                "configHomeKind": "explicit",
                "timeoutMs": 1000,
                "workspaceConfig": None,
                "imageMemoFd": descriptor,
            }
            try:
                send(left, memo)
                process.communicate(canonical(request).encode(), timeout=3)
                self.assertEqual(process.returncode, -9)
                proof = json.loads(marker.read_text())
                self.assertTrue(proof["imageAnchorVerified"])
                deadline = time.monotonic() + 1
                while alive(proof["childPid"]) and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(alive(proof["childPid"]), "owned helper survived its group deadline")
                self.assertEqual(left.recv(MAX_PACKET), b"")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, 9)
                    process.wait()
                memo.close()
                left.close()

    def test_runtime_accepts_memo_only_after_unchanged_context_and_valid_generation(self):
        for changed, invalidate, malformed, timeout in [
            (False, False, False, False),
            (True, False, False, False),
            (False, True, False, False),
            (False, False, True, False),
            (False, False, False, True),
        ]:
            with self.subTest(
                changed=changed, invalidate=invalidate, malformed=malformed, timeout=timeout
            ):
                with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
                    # This test completes workers directly. A running service
                    # loop would race to complete the same already-exited worker.
                    state = ServiceState(
                        host_scope="fixture",
                        configs={"codex": ("/fixture/codex", "explicit")},
                    )
                    runtime = Runtime(state, Path(directory) / "read.sock", collect=False)
                    cleanup.callback(runtime.selector.close)
                    cleanup.callback(lambda: runtime.image_memos["codex"].close())
                    path = Path(directory) / "image"
                    path.write_bytes(b"image")
                    value = scoped_snapshot()
                    value["sources"][0]["runtime"] = {
                        "version": "diagnostic",
                        "binarySha256": "a" * 64,
                        "topology": "native_managed_endpoint",
                        "bootId": state.boot_id,
                        "pid": 123,
                        "startTicks": 456,
                        "endpoint": "/fixture/endpoint",
                    }
                    state.accept(
                        "codex", "runtime", value, sampled_ms=state.clock(), ttl_ms=60000
                    )
                    old = copy.deepcopy(value)
                    if changed:
                        value["sources"][0]["runtime"]["startTicks"] += 1
                    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                    root = str(Path(__file__).resolve().parent.parent)
                    code = (
                        "import sys,socket;sys.path.insert(0," + repr(root) + ");"
                        "from pathlib import Path;from agent_observer._image_memo import ImageMemo,send;"
                        "from agent_observer.native_artifacts import inspect_installed;"
                        'm=ImageMemo("codex");inspect_installed(Path('
                        + repr(str(path))
                        + '),"codex",cache=m);'
                        "s=socket.socket(fileno="
                        + str(right.fileno())
                        + ");"
                        + ('s.send(b"malformed");' if malformed else "send(s,m);")
                        + "m.close()"
                    )
                    process = subprocess.Popen(
                        [sys.executable, "-I", "-B", "-c", code],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        pass_fds=(right.fileno(),),
                    )
                    right.close()
                    left.setblocking(False)
                    process._observer_image_reply = left
                    process.stdout.read()
                    deadline = time.monotonic() + 2
                    while Runtime._exit_status(process) is None and time.monotonic() < deadline:
                        time.sleep(0.01)
                    job = runtime.scheduler.start_due(state.clock())[0]
                    state.attempt("codex", job.component)
                    worker = Worker(job, process, bytearray(canonical(value).encode()), True)
                    runtime.workers["codex"] = worker
                    if invalidate:
                        runtime.scheduler.invalidate("codex")
                    original_receive = receive

                    def stopped_first(*args, process=process, original_receive=original_receive):
                        self.assertIsNotNone(process.returncode)
                        return original_receive(*args)

                    try:
                        with patch(
                            "agent_observer.service_runtime.receive_memo", side_effect=stopped_first
                        ):
                            runtime._complete(worker, timed_out=timeout)
                        expected = not (changed or invalidate or malformed or timeout)
                        self.assertEqual(len(runtime.image_memos["codex"]), int(expected))
                        self.assertIsNone(process._observer_image_reply)
                        receipt = state.receipts["codex"]["runtime"]
                        self.assertEqual(
                            receipt.lastResult,
                            "collection_timeout"
                            if timeout
                            else "collection_failed"
                            if invalidate
                            else "accepted",
                        )
                        if invalidate:
                            self.assertEqual(receipt.data, old)
                    finally:
                        if process.poll() is None:
                            os.killpg(process.pid, 9)
                            process.wait()
                        process.stdout.close()
                        left.close()


if __name__ == "__main__":
    unittest.main()
