"""Maximum public frames and actual encoded retention admission, not arithmetic."""

import copy
import socket
import unittest
import uuid

from test_service_contract import fixture
from test_service_state import provider_snapshot

from agent_observer.contract import MAX_SNAPSHOT_BYTES, canonical
from agent_observer.service_contract import MAX_FRAME_BYTES, parse_frame
from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState


def maximum_snapshot():
    value = provider_snapshot("codex")
    seed = value["sessions"][0]
    value["sessions"] = []
    for number in range(4096):
        row = copy.deepcopy(seed)
        sid = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(number)))
        row["identity"]["nativeId"] = sid
        row["nativeIds"]["threadId"] = row["nativeIds"]["sessionId"] = sid
        row["title"] = "T" * 256
        value["sessions"].append(row)
    remaining = MAX_SNAPSHOT_BYTES - 64 - len(canonical(value).encode())
    for row in value["sessions"]:
        for _ in range(128):
            size = 130 if not row["metadataIssues"] else 131
            if remaining < size:
                break
            row["metadataIssues"].append("p" * 128)
            remaining -= size
        if remaining < 131:
            break
    return value


class ServiceCapacityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = maximum_snapshot()

    def test_near_maximum_snapshot_crosses_real_service_parser(self):
        frame = fixture()
        frame["snapshot"] = self.value
        frame["sources"] = [s for s in frame["sources"] if s["provider"] == "codex"]
        raw = (canonical(frame) + "\n").encode()
        self.assertGreater(len(raw), MAX_SNAPSHOT_BYTES - 1024)
        self.assertLessEqual(len(raw), MAX_FRAME_BYTES)
        self.assertEqual(len(parse_frame(raw)["snapshot"]["sessions"]), 4096)

    def test_sixteen_distinct_pinned_bodies_obey_global_budget(self):
        state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")})
        runtime = Runtime(state, "/unused/socket", collect=False)
        receivers = []
        try:
            for revision in range(1, 17):
                sender, receiver = socket.socketpair()
                receivers.append(receiver)
                peer = Peer(sender, revision, operation="watch", write_started=revision)
                runtime.peers.add(peer)
                runtime._body(revision, self.value)
                peer.body_revision = revision
                peer.parts = (b"{", runtime.bodies[revision], b"}\n")
                self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
            self.assertGreater(runtime.counts["droppedConnections"], 0)
            self.assertLess(len(runtime.bodies), 16)
        finally:
            for peer in list(runtime.peers):
                runtime._drop(peer)
            for receiver in receivers:
                receiver.close()
            runtime.selector.close()
