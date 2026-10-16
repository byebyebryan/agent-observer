"""Mixed local request families and shared bounded delivery; no native reads."""

import copy
import os
import selectors
import socket
import time
import unittest
import uuid
from unittest.mock import patch

from test_active_contract import fixture as active_fixture
from test_service_contract import fixture as service_fixture
from test_service_runtime import Running, scoped_snapshot

from agent_observer.active_contract import (
    MAX_FRAME_BYTES,
    SELECTOR,
    SELECTOR_DIGEST,
    StreamGuard,
    parse_frame,
)
from agent_observer.bounded_json import decode_document
from agent_observer.contract import MAX_SNAPSHOT_BYTES, canonical, store_namespace
from agent_observer.service_contract import MAX_OVERHEAD_BYTES
from agent_observer.service_contract import parse_frame as parse_service_frame
from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState


def request(operation="snapshot", *, host="fixture"):
    return {
        "activeFeedProtocol": 1, "operation": operation, "hostScope": host,
        "selector": copy.deepcopy(SELECTOR), "selectorDigest": SELECTOR_DIGEST,
    }


def wire(value):
    return (canonical(value) + "\n").encode()


def local_uid(value):
    """Keep strict fixtures usable through the current user's protected socket."""
    value["uid"] = os.geteuid()
    namespaces = {
        source["namespace"]: store_namespace(source["provider"], source["configHome"],
                                             source["configHomeKind"], os.geteuid())
        for source in value["sources"]
    }
    def visit(item):
        if isinstance(item, dict):
            if "namespace" in item:
                item["namespace"] = namespaces.get(item["namespace"], item["namespace"])
            if "uid" in item:
                item["uid"] = os.geteuid()
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return value


def repeat_selected(value, count):
    projection = value["projection"]
    row, member = projection["sessions"][0], projection["scopes"][0]["members"][0]
    projection["sessions"], projection["scopes"][0]["members"] = [], []
    for number in range(count):
        sid = str(uuid.uuid5(uuid.NAMESPACE_OID, str(number)))
        copied_row, copied_member = copy.deepcopy(row), copy.deepcopy(member)
        copied_row["identity"]["nativeId"] = copied_member["identity"]["nativeId"] = sid
        copied_row["nativeIds"]["threadId"] = copied_row["nativeIds"]["sessionTreeRootId"] = sid
        projection["sessions"].append(copied_row)
        projection["scopes"][0]["members"].append(copied_member)
    return projection


class CachedFrames:
    """The runtime's cache/frame seam, independently strict at the wire reader."""

    def __init__(self, *, ready=True, empty=False, unsupported=False):
        self.full = local_uid(service_fixture())
        self.active = local_uid(active_fixture())
        if empty:
            self.active["projection"]["sessions"].clear()
            self.active["projection"]["scopes"][0]["members"].clear()
        self.host_scope, self.uid = "fixture", os.geteuid()
        self.configs = {"codex": (self.active["sources"][0]["configHome"], "default")}
        self.snapshot = self.full["snapshot"] if ready else None
        self.revision = 1 if ready else 0
        self.unsupported = unsupported
        self.advance_on_frame = False

    @staticmethod
    def clock():
        return int(time.monotonic() * 1000)

    def expire(self, *_args):
        pass

    def publish(self):
        self.revision += 1
        self.snapshot = self.full["snapshot"]

    def _frame(self, source, payload, kind, sequence, reason):
        if self.advance_on_frame:
            self.advance_on_frame = False
            self.publish()
        result = copy.deepcopy(source)
        result.update(sequence=sequence, viewRevision=self.revision, kind=kind, reason=reason,
                      state="ready" if self.snapshot is not None else "warming")
        if self.snapshot is None or kind not in {"status", "view", "resync"}:
            result[payload] = None
        return result

    def frame(self, kind, sequence, *, reason):
        return self._frame(self.full, "snapshot", kind, sequence, reason)

    def active_frame(self, kind, sequence, *, reason):
        result = self._frame(self.active, "projection", kind, sequence, reason)
        if self.unsupported:
            result.update(kind="error", reason="active_source_unsupported", sources=[], projection=None)
        return result


class ActiveServiceDeliveryTest(unittest.TestCase):
    def runtime(self, state=None, **options):
        runtime = Runtime(state or CachedFrames(), "/unused/read.sock", collect=False, **options)
        self.addCleanup(runtime.selector.close)
        self.addCleanup(lambda: [runtime._drop(peer) for peer in list(runtime.peers)])
        self.addCleanup(lambda: [memo.close() for memo in runtime.image_memos.values()])
        return runtime

    def peer(self, runtime, family="service", *, write_started=0):
        sender, receiver = socket.socketpair()
        sender.setblocking(False)
        receiver.setblocking(False)
        self.addCleanup(receiver.close)
        peer = Peer(sender, runtime.state.clock(), family=family, operation="watch",
                    write_started=write_started)
        runtime.peers.add(peer)
        runtime.selector.register(sender, selectors.EVENT_READ, ("peer", peer))
        return peer, receiver

    def test_same_revision_has_distinct_family_bodies_and_shared_active_encoding(self):
        runtime = self.runtime()
        full, _ = self.peer(runtime)
        active, _ = self.peer(runtime, "active")
        second, _ = self.peer(runtime, "active")
        runtime._queue(full, "view")
        runtime._queue(active, "view")
        runtime._queue(second, "view")
        self.assertEqual(full.body_revision, 1)
        self.assertEqual(active.body_revision, ("active", 1))
        self.assertIs(active.parts[1], second.parts[1])
        self.assertNotEqual(full.parts[1], active.parts[1])
        self.assertEqual(parse_service_frame(b"".join(full.parts))["snapshot"], runtime.state.full["snapshot"])
        projected = parse_frame(b"".join(active.parts))
        self.assertEqual(projected["projection"], runtime.state.active["projection"])
        self.assertNotIn("snapshot", projected)
        expected = sum(map(len, runtime.bodies.values())) + sum(
            len(peer.parts[0]) + len(peer.parts[2]) for peer in runtime.peers
        )
        self.assertEqual(runtime.encoded_bytes(), expected)
        self.assertEqual(runtime.counts["workerStarts"], 0)

    def test_request_decodes_once_then_uses_the_selected_strict_validator(self):
        runtime = self.runtime()
        peer, receiver = self.peer(runtime)
        peer.operation = None
        receiver.sendall(wire(request()))
        with patch("agent_observer.service_runtime.decode_document", wraps=decode_document) as decode:
            runtime._request(peer)
        self.assertEqual(decode.call_count, 1)
        self.assertEqual(peer.family, "active")
        self.assertEqual(peer.operation, "snapshot")
        parse_frame(b"".join(peer.parts))

    def test_mixed_unknown_extra_and_mismatched_selectors_are_closed(self):
        mixed = request()
        mixed["serviceProtocol"] = 4
        wrong_selector = request()
        wrong_selector["selector"]["kinds"] = ["user"]
        bad = [
            {}, [], mixed, wrong_selector,
            {**request(), "activeFeedProtocol": 2},
            {**request(), "activeFeedProtocol": True},
            {**request(), "selectorDigest": "sha256:" + "0" * 64},
            {**request(), "extra": "rejected"},
            {"serviceProtocol": 4, "operation": "snapshot", "hostScope": "fixture", "selector": SELECTOR},
        ]
        with Running(state=CachedFrames()) as server:
            for value in bad:
                with self.subTest(value=value), server.connect(wire(value)) as peer:
                    self.assertEqual(peer.recv(1), b"")
            with server.connect(wire(request(host="foreign"))) as peer:
                with peer.makefile("rb") as reader:
                    frame = parse_frame(reader.readline())
                    self.assertEqual(frame["kind"], "error")
                    self.assertEqual(frame["reason"], "active_host_mismatch")
                    self.assertIsNone(frame["projection"])
                    self.assertEqual(reader.read(), b"")

    def test_warming_watch_becomes_complete_empty_without_any_collection(self):
        state = CachedFrames(ready=False, empty=True)
        with Running(state=state) as server:
            with server.connect(wire(request("watch"))) as peer:
                with peer.makefile("rb") as reader:
                    guard = StreamGuard(expected_host="fixture", expected_uid=os.geteuid())
                    initial = guard.parse(reader.readline())
                    self.assertEqual((initial["kind"], initial["state"], initial["projection"]),
                                     ("status", "warming", None))
                    state.publish()
                    frame = guard.parse(reader.readline())
                    self.assertEqual((frame["kind"], frame["state"]), ("view", "ready"))
                    self.assertEqual(frame["projection"]["sessions"], [])
                    self.assertEqual(frame["projection"]["scopes"][0]["coverage"]["status"], "complete")
                    for _ in range(4):
                        with server.connect(wire(request())) as cached:
                            with cached.makefile("rb") as cached_reader:
                                self.assertEqual(parse_frame(cached_reader.readline())["projection"], frame["projection"])
                    self.assertEqual(server.runtime.counts["workerStarts"], 0)

    def test_unsupported_active_source_is_explicit_and_watch_closes(self):
        with Running(state=CachedFrames(unsupported=True)) as server:
            with server.connect(wire(request("watch"))) as peer:
                with peer.makefile("rb") as reader:
                    frame = parse_frame(reader.readline())
                    self.assertEqual((frame["kind"], frame["reason"]), ("error", "active_source_unsupported"))
                    self.assertIsNone(frame["projection"])
                    self.assertEqual(reader.read(), b"")
            with server.connect(b'{"serviceProtocol":4,"operation":"snapshot","hostScope":"fixture"}\n') as peer:
                with peer.makefile("rb") as reader:
                    self.assertIsNotNone(parse_service_frame(reader.readline())["snapshot"])

    def test_partial_active_write_keeps_its_body_then_gaps_and_resyncs(self):
        state = CachedFrames()
        projection = repeat_selected(state.active, 200)
        runtime = self.runtime(state)
        peer, receiver = self.peer(runtime, "active")
        peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        runtime._queue(peer, "view")
        initial_body = peer.parts[1]
        runtime._write(peer)
        self.assertTrue(peer.parts)
        state.publish()
        state.publish()
        projection["sessions"][0]["title"] = "new generation"
        peer.pending, peer.skipped = state.revision, True
        raw = bytearray()
        deadline = time.monotonic() + 5
        while raw.count(b"\n") < 3 and time.monotonic() < deadline:
            if peer.parts:
                runtime._write(peer)
            try:
                raw.extend(receiver.recv(65536))
            except BlockingIOError:
                pass
        guard = StreamGuard(expected_host="fixture", expected_uid=os.geteuid())
        frames = [guard.parse(bytes(line) + b"\n") for line in raw.splitlines()]
        self.assertEqual([frame["kind"] for frame in frames], ["view", "gap", "resync"])
        self.assertEqual(frames[0]["viewRevision"], 1)
        self.assertEqual(frames[-1]["viewRevision"], 3)
        self.assertNotIn(b"new generation", initial_body)
        self.assertEqual(frames[-1]["projection"]["sessions"][0]["title"], "new generation")
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)

    def test_minimum_budget_evicts_idle_family_caches_without_dropping_peers(self):
        limit = MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES
        runtime = self.runtime(encoded_limit=limit)
        large = {"padding": "x" * (MAX_SNAPSHOT_BYTES - MAX_OVERHEAD_BYTES)}
        runtime._body(1, large)
        runtime._body(("active", 1), large)
        self.assertEqual(set(runtime.bodies), {("active", 1)})
        runtime._body(1, large)
        self.assertEqual(set(runtime.bodies), {1})
        self.assertEqual(runtime.counts["droppedConnections"], 0)
        self.assertLessEqual(runtime.encoded_bytes(), limit)

    def test_pinned_family_pressure_drops_oldest_writer_within_one_global_limit(self):
        limit = MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES
        runtime = self.runtime(encoded_limit=limit)
        slow, _ = self.peer(runtime, write_started=1)
        healthy, _ = self.peer(runtime, "active", write_started=2)
        large = {"padding": "x" * (MAX_SNAPSHOT_BYTES - 2 * MAX_OVERHEAD_BYTES)}
        runtime._body(1, large)
        slow.body_revision, slow.parts = 1, (b"{", runtime.bodies[1], b"}\n")
        runtime._body(("active", 1), {"small": True})
        healthy.body_revision = ("active", 1)
        healthy.parts = (b"{", runtime.bodies[healthy.body_revision], b"}\n")
        runtime._body(2, large)
        self.assertNotIn(slow, runtime.peers)
        self.assertIn(healthy, runtime.peers)
        self.assertEqual(runtime.counts["droppedConnections"], 1)
        self.assertLessEqual(runtime.encoded_bytes(), limit)

    def test_frame_expiry_uses_the_resulting_revision_for_body_and_heartbeat(self):
        runtime = self.runtime()
        peer, _ = self.peer(runtime, "active")
        peer.sent_revision = 1
        runtime.state.advance_on_frame = True
        runtime._queue(peer, "heartbeat", "service_alive")
        frame = parse_frame(b"".join(peer.parts))
        self.assertEqual(frame["kind"], "view")
        self.assertEqual(frame["reason"], "lease_expired")
        self.assertEqual(peer.body_revision, ("active", 2))
        self.assertEqual(set(runtime.bodies), {("active", 2)})

    def test_cached_body_header_pressure_evicts_idle_other_family_first(self):
        limit = MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES
        runtime = self.runtime(encoded_limit=limit)
        large = {"padding": "x" * (limit - 114)}
        runtime._body(("active", 1), large, overhead=1)
        runtime._body(1, {"small": True}, overhead=1)
        self.assertEqual(len(runtime.bodies), 2)
        runtime._body(("active", 1), large, overhead=95)
        self.assertEqual(set(runtime.bodies), {("active", 1)})
        self.assertEqual(runtime.counts["droppedConnections"], 0)

    def test_valid_frame_over_minimum_budget_closes_watch_without_stopping_service(self):
        limit = MAX_SNAPSHOT_BYTES + MAX_OVERHEAD_BYTES
        state = CachedFrames(ready=False)
        projection = repeat_selected(state.active, 500)
        remaining = MAX_FRAME_BYTES - 128 - len(wire(state.active))
        for row in projection["sessions"]:
            for _ in range(128):
                size = 130 if not row["metadataIssues"] else 131
                if remaining < size:
                    break
                row["metadataIssues"].append("p" * 128)
                remaining -= size
        encoded = wire(state.active)
        self.assertGreater(len(encoded), limit)
        self.assertLessEqual(len(encoded), MAX_FRAME_BYTES)
        parse_frame(encoded)
        with Running(state=state, encoded_limit=limit) as server:
            with server.connect(wire(request("watch"))) as peer:
                with peer.makefile("rb") as reader:
                    self.assertEqual(parse_frame(reader.readline())["state"], "warming")
                    state.publish()
                    self.assertEqual(reader.readline(), b"")
            with server.connect(b'{"serviceProtocol":4,"operation":"snapshot","hostScope":"fixture"}\n') as healthy:
                with healthy.makefile("rb") as reader:
                    self.assertIsNotNone(parse_service_frame(reader.readline())["snapshot"])
            self.assertLessEqual(server.runtime.encoded_bytes(), limit)

    def test_repeated_real_cached_reads_do_not_project_or_collect_again(self):
        state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
        state.attempt("codex", "runtime")
        state.accept("codex", "runtime", scoped_snapshot(), sampled_ms=state.clock(), ttl_ms=60000)
        generation, revision = state.active_projector.generations, state.revision
        receipt = copy.deepcopy(state.source_meta("codex"))
        expected = state.active_projection
        self.assertTrue(expected["sessions"])
        with Running(state=state) as server:
            with patch.object(state.active_projector, "_accept_owned", wraps=state.active_projector._accept_owned) as project:
                for _ in range(4):
                    with server.connect(wire(request())) as peer:
                        with peer.makefile("rb") as reader:
                            frame = parse_frame(reader.readline(), expected_uid=os.geteuid())
                            self.assertEqual(frame["projection"], expected)
                    with server.connect(b'{"serviceProtocol":4,"operation":"snapshot","hostScope":"fixture"}\n') as peer:
                        with peer.makefile("rb") as reader:
                            self.assertIsNotNone(parse_service_frame(reader.readline())["snapshot"])
                self.assertEqual(project.call_count, 0)
            self.assertEqual((state.active_projector.generations, state.revision), (generation, revision))
            self.assertEqual(state.source_meta("codex"), receipt)
            self.assertEqual(server.runtime.counts["workerStarts"], 0)
