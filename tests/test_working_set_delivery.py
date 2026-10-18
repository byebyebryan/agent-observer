"""Opt-in working-set IPC with independent legacy routes and cached bodies."""

import copy
import os
import selectors
import socket
import unittest
from uuid import UUID

from test_service_contract import fixture
from test_service_runtime import Running, scoped_snapshot

from agent_observer.contract import canonical
from agent_observer.service_contract import parse_frame as parse_full_frame
from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState
from agent_observer.working_set_contract import StreamGuard, parse_frame, selector, selector_digest

WALL = 1700000020000


def wire(value):
    return (canonical(value) + "\n").encode()


def request(operation="snapshot", *, window=10000, host="fixture"):
    policy = selector(window)
    return {
        "workingSetProtocol": 1,
        "operation": operation,
        "hostScope": host,
        "selector": policy,
        "selectorDigest": selector_digest(policy),
    }


class WorkingSetDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.now = 10001
        original = fixture()
        self.options = dict(
            host_scope="fixture",
            configs={"codex": ("/fixture/codex", "explicit")},
            uid=os.geteuid(),
            clock=lambda: self.now,
            boot_id=original["bootId"],
            clock_domain=original["clockDomain"],
        )
        self.state = ServiceState(**self.options, working_set_window_ms=10000)

    def sample(self, *, generation=1, count=1):
        value = scoped_snapshot()
        value.update(
            collectionId=str(UUID(int=100 + generation)), collectedAt=WALL + generation - 1
        )
        base = value["sessions"][0]
        base["runtime"]["value"] = "parked"
        base["phase"], base["blockedReasons"] = None, []
        base["activity"].update(
            at=WALL - 5000, health="current", source="codex_rpc", reason="native_timestamp"
        )
        value["sources"][0]["capabilities"]["activity"] = True
        value["sessions"] = []
        for number in range(count):
            row = copy.deepcopy(base)
            identifier = str(UUID(int=1000 + number))
            row["identity"]["nativeId"] = identifier
            row["nativeIds"].update(threadId=identifier, sessionTreeRootId=identifier)
            value["sessions"].append(row)
        return value

    def accept(self, *, generation=1, count=1):
        self.state.attempt("codex", "runtime")
        self.state.accept(
            "codex",
            "runtime",
            self.sample(generation=generation, count=count),
            sampled_ms=9999 + generation,
            ttl_ms=100000,
            accepted_boottime_ms=self.now,
        )

    def test_disabled_and_policy_mismatch_reject_without_full_fallback(self):
        legacy = ServiceState(**self.options)
        with Running(state=legacy) as server:
            with server.connect(wire(request())) as peer:
                self.assertEqual(peer.recv(1), b"")
            with server.connect(
                wire({"serviceProtocol": 4, "operation": "status", "hostScope": "fixture"})
            ) as peer:
                self.assertEqual(
                    parse_full_frame(peer.makefile("rb").readline())["state"], "warming"
                )
        with Running(state=self.state) as server:
            with server.connect(wire(request(window=20000))) as peer:
                self.assertEqual(peer.recv(1), b"")
            with server.connect(wire(request())) as peer:
                frame = parse_frame(peer.makefile("rb").readline(), expected_window_ms=10000)
                self.assertIsNone(frame["projection"])
                self.assertEqual(frame["state"], "warming")
            with server.connect(wire(request(host="other"))) as peer:
                self.assertEqual(parse_frame(peer.makefile("rb").readline())["kind"], "error")
        with self.assertRaises(AttributeError):
            self.state.working_set_window_ms = 20000

    def test_watch_delivers_quiet_cutoff_revision_without_new_worker_or_observation(self):
        self.accept()
        with Running(state=self.state) as server:
            with server.connect(wire(request("watch"))) as peer, peer.makefile("rb") as reader:
                guard = StreamGuard(expected_host="fixture", expected_window_ms=10000)
                first = guard.parse(reader.readline())
                self.assertEqual(len(first["projection"]["sessions"]), 1)
                lower = first["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"]
                self.now = lower
                middle = guard.parse(reader.readline())
                self.assertEqual(middle["projection"]["sessions"], [])
                self.assertEqual(middle["projection"]["scopes"][0]["coverage"]["status"], "partial")
                self.now = lower + 3
                final = guard.parse(reader.readline())
                self.assertEqual(
                    final["projection"]["scopes"][0]["nonmembers"][0]["reason"], "outside_window"
                )
                self.assertEqual(final["observationRevision"], first["observationRevision"])
                self.assertGreater(final["viewRevision"], middle["viewRevision"])
                self.assertEqual(server.runtime.counts["workerStarts"], 0)

    def test_old_slow_peer_and_new_body_remain_accounted_and_share_with_same_revision(self):
        self.accept(count=30)
        runtime = Runtime(self.state, "/unused/read.sock", collect=False)
        peers, readers = [], []
        try:
            for _ in range(3):
                sender, receiver = socket.socketpair()
                sender.setblocking(False)
                sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                receiver.setblocking(False)
                peer = Peer(sender, self.now, operation="watch", family="working_set")
                peers.append(peer)
                readers.append(receiver)
                runtime.peers.add(peer)
                runtime.selector.register(sender, selectors.EVENT_READ, ("peer", peer))
            runtime._queue(peers[0], "view")
            old = peers[0].body_revision
            runtime._write(peers[0])
            self.assertTrue(peers[0].parts)
            self.now += 1
            self.accept(generation=2, count=30)
            runtime._queue(peers[1], "view")
            runtime._queue(peers[2], "view")
            new = peers[1].body_revision
            self.assertNotEqual(old, new)
            self.assertIs(peers[1].parts[1], peers[2].parts[1])
            self.assertIn(old, runtime.bodies)
            owners = {id(v): v for v in self.state.working_set_retained_buffers()}
            expected = sum(map(len, owners.values())) + sum(map(len, runtime.bodies.values()))
            expected += sum(sum(len(v) for i, v in enumerate(p.parts) if i != 1) for p in peers)
            self.assertEqual(runtime.encoded_bytes(), expected)
            self.assertLessEqual(expected, runtime.encoded_limit)
            runtime._drop(peers[0])
            runtime._prune()
            self.assertNotIn(old, runtime.bodies)
        finally:
            for peer in peers:
                runtime._drop(peer)
            for reader in readers:
                reader.close()
            runtime.selector.close()

    def test_encoding_reservation_failure_is_feature_unavailable_and_not_provider_failure(self):
        self.accept()
        self.state.working_set_reserver = lambda _size: False
        self.now += 1
        self.accept(generation=2)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(frame["projection"]["sessions"], [])
        self.assertEqual(
            frame["projection"]["scopes"][0]["coverage"],
            {
                "status": "unavailable",
                "reason": "projection_encoding_capacity",
                "supports": [],
            },
        )
        self.assertEqual(self.state.receipts["codex"]["runtime"].health, "current")
        self.assertEqual(self.state.receipts["codex"]["runtime"].accepted, 2)
