"""Physical output retirement precedes a replacement reservation.

Weak-referenceable bytearrays expose the same peer/buffer reference edges as
ordinary immutable output bytes. These are topology tests, not RSS or wire
qualification; GC remains disabled and callers intentionally retain the peer.
"""

import gc
import selectors
import socket
import unittest
import weakref

from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState


class TrackedBuffer(bytearray):
    pass


def runtime_fixture():
    state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
    return Runtime(state, "/unused/read.sock", collect=False)


class ServiceDeliveryRetirementTests(unittest.TestCase):
    def test_eviction_retires_raw_parts_before_accounting_reuses_credit(self):
        enabled = gc.isenabled()
        gc.disable()
        try:
            for family in ("service", "active", "working_set"):
                with self.subTest(family=family):
                    runtime = runtime_fixture()
                    sender, receiver = socket.socketpair()
                    peer = Peer(sender, 1, family=family, operation="watch", write_started=1)
                    runtime.peers.add(peer)
                    runtime.selector.register(sender, selectors.EVENT_WRITE, ("peer", peer))
                    body = TrackedBuffer(b"x" * (5 * 1024 * 1024))
                    live = weakref.ref(body)
                    revision = (family, 1) if family != "service" else 1
                    peer.parts = (b"{", body, b"}\n")
                    peer.body_revision = revision
                    runtime.bodies[revision] = body
                    runtime.latest[family] = revision
                    del body
                    runtime.encoded_limit = 8 * 1024 * 1024
                    try:
                        runtime._room(4 * 1024 * 1024)
                        self.assertNotIn(peer, runtime.peers)
                        self.assertTrue(live() is None, "retained dropped peer still owns retired raw body")
                        self.assertEqual(peer.parts, ())
                        self.assertIsNone(peer.body_revision)
                        self.assertEqual(runtime.encoded_bytes(), 0)
                        runtime._drop(peer)
                    finally:
                        runtime._drop(peer)
                        receiver.close()
                        runtime.selector.close()
        finally:
            if enabled:
                gc.enable()

    def test_completed_control_send_releases_export_before_replacement_queue(self):
        enabled = gc.isenabled()
        gc.disable()
        try:
            for family in ("service", "active", "working_set"):
                with self.subTest(family=family):
                    runtime = runtime_fixture()
                    sender, receiver = socket.socketpair()
                    peer = Peer(sender, 1, family=family, operation="watch", pending=2)
                    runtime.peers.add(peer)
                    runtime.selector.register(sender, selectors.EVENT_WRITE, ("peer", peer))
                    control = TrackedBuffer(b'{"control":"gap"}\n')
                    live = weakref.ref(control)
                    peer.parts = (control,)
                    del control
                    replacements = []

                    def replacement(actual_peer, kind, reason="observed_view", *,
                                    expected_peer=peer, prior=live, calls=replacements):
                        self.assertIs(actual_peer, expected_peer)
                        self.assertTrue(prior() is None, "completed send still exports retired control")
                        calls.append(kind)

                    runtime._queue = replacement
                    try:
                        runtime._write(peer)
                        self.assertEqual(replacements, ["view"])
                        self.assertEqual(runtime.encoded_bytes(), 0)
                    finally:
                        runtime._drop(peer)
                        receiver.close()
                        runtime.selector.close()
        finally:
            if enabled:
                gc.enable()
