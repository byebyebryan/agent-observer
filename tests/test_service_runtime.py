"""Actual local sockets and owned fake-source processes; no provider invocation."""

import copy
import os
import selectors
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

from test_service_state import provider_snapshot

from agent_observer.contract import canonical, store_namespace
from agent_observer.service_contract import StreamGuard, parse_frame
from agent_observer.service_runtime import Endpoint, Peer, Runtime
from agent_observer.service_state import ServiceState


class Running:
    def __init__(self, *, collect=False, timeout=1000, factory=None, scheduler=None):
        self.directory = tempfile.TemporaryDirectory(prefix="ao-service-test-")
        self.path = Path(self.directory.name) / "private" / "read.sock"
        self.state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
        self.runtime = Runtime(self.state, self.path, collect=collect, io_timeout_ms=timeout, heartbeat_ms=200, worker_factory=factory, scheduler=scheduler)
        self.stop = threading.Event()
        self.errors = []
        def run():
            try:
                self.runtime.run(self.stop)
            except BaseException as error:
                self.errors.append(error)
        self.thread = threading.Thread(target=run)

    def __enter__(self):
        self.thread.start()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.errors:
            try:
                if self.path.stat().st_mode & 0o777 == 0o600:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                        probe.connect(str(self.path))
                    break
            except OSError:
                pass
            time.sleep(0.01)
        if not self.path.exists():
            self.__exit__()
            raise AssertionError(self.errors)
        return self

    def connect(self, request=None):
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        peer.settimeout(3)
        peer.connect(str(self.path))
        if request:
            peer.sendall(request)
        return peer

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(4)
        if self.thread.is_alive():
            raise AssertionError("service did not stop")
        self.directory.cleanup()
        if self.errors:
            raise AssertionError(self.errors)


def scoped_snapshot():
    value = provider_snapshot("codex")
    value["host"]["uid"] = os.geteuid()
    namespace = store_namespace("codex", "/fixture/codex", "explicit", os.geteuid())
    value["sources"][0]["namespace"] = namespace
    for row in value["sessions"]:
        row["identity"]["namespace"] = namespace
    return value


def source_worker(job):
    wire = canonical(scoped_snapshot())
    return subprocess.Popen([sys.executable, "-I", "-B", "-c", "import sys;sys.stdout.write(" + repr(wire) + ")"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)


class ServiceRuntimeTest(unittest.TestCase):
    def test_partial_frame_is_immutable_and_coalesced_views_resync(self):
        state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
        value = scoped_snapshot()
        seed = value["sessions"][0]
        value["sessions"] = []
        for number in range(700):
            row = copy.deepcopy(seed)
            row["identity"]["nativeId"] = str(uuid.uuid5(uuid.NAMESPACE_OID, str(number)))
            row["nativeIds"]["threadId"] = row["identity"]["nativeId"]
            row["nativeIds"]["sessionId"] = row["identity"]["nativeId"]
            value["sessions"].append(row)
        state.attempt("codex", "runtime")
        state.accept("codex", "runtime", value, sampled_ms=state.clock(), ttl_ms=60000)
        runtime = Runtime(state, "/unused/read.sock", collect=False)
        sender, receiver = socket.socketpair()
        sender.setblocking(False)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        receiver.setblocking(False)
        peer = Peer(sender, state.clock(), operation="watch")
        runtime.peers.add(peer)
        runtime.selector.register(sender, selectors.EVENT_READ, ("peer", peer))
        try:
            runtime._queue(peer, "view")
            original_revision = peer.frame_revision
            runtime._write(peer)
            self.assertTrue(peer.parts)
            state.attempt("codex", "runtime")
            state.accept("codex", "runtime", value, sampled_ms=state.clock(), ttl_ms=60000)
            state.attempt("codex", "runtime")
            state.accept("codex", "runtime", value, sampled_ms=state.clock(), ttl_ms=60000)
            peer.pending, peer.skipped = state.revision, True
            raw = bytearray()
            deadline = time.monotonic() + 5
            while raw.count(b"\n") < 3 and time.monotonic() < deadline:
                runtime._write(peer) if peer.parts else None
                try:
                    raw.extend(receiver.recv(65536))
                except BlockingIOError:
                    pass
            guard = StreamGuard(expected_host="fixture", expected_uid=os.geteuid())
            frames = [guard.accept(parse_frame(bytes(line) + b"\n")) for line in raw.splitlines()]
            self.assertEqual([f["kind"] for f in frames], ["view", "gap", "resync"])
            self.assertEqual(frames[0]["viewRevision"], original_revision)
            self.assertEqual(frames[-1]["viewRevision"], state.revision)
            self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
        finally:
            runtime._drop(peer)
            receiver.close()
            runtime.selector.close()

    def test_cold_status_private_socket_and_singleton(self):
        with Running() as server:
            self.assertEqual(server.path.stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(ValueError, "already_running"):
                with Endpoint(server.path):
                    pass
            with server.connect(b'{"serviceProtocol":1,"operation":"status","hostScope":"fixture"}\n') as peer:
                with peer.makefile("rb") as reader:
                    value = parse_frame(reader.readline(), expected_host="fixture", expected_uid=os.geteuid())
                    self.assertEqual(value["state"], "warming")
                    self.assertIsNone(value["snapshot"])
                    self.assertEqual(reader.read(), b"")
        self.assertFalse(server.path.exists())

    def test_partial_and_pipelined_input_do_not_block_healthy_reader(self):
        with Running(timeout=200) as server:
            with server.connect(b'{"serviceProtocol":1') as stalled:
                with server.connect(b'{"serviceProtocol":1,"operation":"snapshot","hostScope":"fixture"}\n') as healthy:
                    self.assertEqual(parse_frame(healthy.makefile("rb").readline())["kind"], "status")
                time.sleep(0.3)
                self.assertEqual(stalled.recv(1), b"")
            with server.connect(b'{}\n{}\n') as bad:
                self.assertEqual(bad.recv(1), b"")

    def test_real_worker_watch_and_cached_reads_do_not_start_more_jobs(self):
        with Running(collect=True, factory=source_worker) as server:
            with server.connect(b'{"serviceProtocol":1,"operation":"watch","hostScope":"fixture"}\n') as peer:
                with peer.makefile("rb") as reader:
                    guard = StreamGuard(expected_host="fixture", expected_uid=os.geteuid())
                    frames = []
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        value = guard.accept(parse_frame(reader.readline()))
                        frames.append(value)
                        if value["snapshot"] and server.state.receipts["codex"]["history"].accepted:
                            break
                    self.assertTrue(any(f["snapshot"] for f in frames))
                    self.assertEqual(server.runtime.counts["workerStarts"], 2)
                    initial = server.runtime.counts["workerStarts"]
                    for _ in range(5):
                        with server.connect(b'{"serviceProtocol":1,"operation":"snapshot","hostScope":"fixture"}\n') as cached:
                            with cached.makefile("rb") as raw:
                                self.assertIsNotNone(parse_frame(raw.readline())["snapshot"])
                    self.assertEqual(server.runtime.counts["workerStarts"], initial)
                    self.assertLess(server.runtime.encoded_bytes(), server.runtime.encoded_limit)

    def test_foreign_node_and_symlink_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="ao-endpoint-") as directory:
            path = Path(directory) / "read.sock"
            path.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "foreign"):
                with Endpoint(path):
                    pass
            self.assertEqual(path.read_text(), "preserve")
            path.unlink()
            path.symlink_to("missing")
            with self.assertRaisesRegex(ValueError, "foreign"):
                with Endpoint(path):
                    pass
            self.assertTrue(path.is_symlink())
