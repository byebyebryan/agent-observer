"""Controlled socket peers prove transport boundaries, not native support."""

import base64
import hashlib
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from agent_observer.codex_transport import PassiveClient, TransportError


def frame(payload, *, final=True, opcode=1):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    flag = (0x80 if final else 0) | opcode
    if len(body) < 126:
        return bytes((flag, len(body))) + body
    return bytes((flag, 126)) + struct.pack("!H", len(body)) + body


def exact(peer, count):
    result = bytearray()
    while len(result) < count:
        body = peer.recv(count - len(result))
        if not body:
            raise EOFError
        result.extend(body)
    return bytes(result)


def client_message(peer):
    first, second = exact(peer, 2)
    assert first == 0x81 and second & 0x80
    size = second & 127
    if size == 126:
        size = struct.unpack("!H", exact(peer, 2))[0]
    elif size == 127:
        size = struct.unpack("!Q", exact(peer, 8))[0]
    mask = exact(peer, 4)
    encoded = exact(peer, size)
    return json.loads(bytes(value ^ mask[index % 4] for index, value in enumerate(encoded)))


class PassiveTransportTest(unittest.TestCase):
    def test_controlled_handshake_reads_and_ignored_notification(self):
        client_socket, server = socket.socketpair()
        received = []
        failures = []

        def serve():
            try:
                request = bytearray()
                while not request.endswith(b"\r\n\r\n"):
                    request.extend(exact(server, 1))
                key = next(
                    line.split(b": ", 1)[1]
                    for line in request.split(b"\r\n")
                    if line.startswith(b"Sec-WebSocket-Key:")
                )
                accept = base64.b64encode(
                    hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()
                )
                server.sendall(
                    b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                    b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n"
                )
                for method in (
                    "initialize",
                    "initialized",
                    "thread/list",
                    "thread/read",
                    "thread/turns/list",
                ):
                    message = client_message(server)
                    received.append(message)
                    if method == "initialized":
                        continue
                    if method == "thread/list":
                        server.sendall(
                            frame(
                                {
                                    "method": "synthetic/notification",
                                    "params": {"content": "synthetic_private_payload"},
                                }
                            )
                        )
                    server.sendall(frame({"id": message["id"], "result": {"data": []}}))
            except (
                OSError,
                EOFError,
                ValueError,
                AssertionError,
                StopIteration,
            ) as error:
                failures.append(type(error).__name__)
            finally:
                server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        with PassiveClient(client_socket, timeout=1) as client:
            client.upgrade()
            client.initialize()
            self.assertEqual(client.list_threads(), {"data": []})
            client.read_thread("synthetic-native-id")
            client.latest_turn("synthetic-native-id")
            self.assertEqual(client.ignored_messages, 1)
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(
            [value["method"] for value in received],
            ["initialize", "initialized", "thread/list", "thread/read", "thread/turns/list"],
        )
        self.assertIs(received[-2]["params"]["includeTurns"], False)
        self.assertEqual(
            received[-1]["params"],
            {
                "threadId": "synthetic-native-id",
                "limit": 1,
                "itemsView": "notLoaded",
                "sortDirection": "desc",
            },
        )

    def test_mutations_and_content_reads_rejected_before_io(self):
        connection = Mock()
        client = PassiveClient(connection)
        client.initialized = True
        for method in (
            "thread/start",
            "thread/resume",
            "turn/start",
            "thread/name/set",
        ):
            with self.assertRaisesRegex(TransportError, "^method_not_passive$"):
                client._request(method, {})
        with self.assertRaisesRegex(TransportError, "^content_read_rejected$"):
            client._request("thread/read", {"includeTurns": True})
        for change in (
            {"itemsView": "full"},
            {"itemsView": "summary"},
            {"limit": 2},
            {"limit": True},
            {"cursor": "next"},
        ):
            params = {
                "threadId": "synthetic-native-id",
                "limit": 1,
                "itemsView": "notLoaded",
                "sortDirection": "desc",
                **change,
            }
            with self.assertRaisesRegex(TransportError, "^content_read_rejected$"):
                client._request("thread/turns/list", params)
        connection.sendall.assert_not_called()

    def test_fragment_aggregate_limit(self):
        connection, peer = socket.socketpair()
        try:
            peer.sendall(frame(b"x" * 200, final=False) + frame(b"x" * 200, opcode=0))
            client = PassiveClient(connection, max_message_bytes=256)
            with self.assertRaisesRegex(TransportError, "^message_limit$"):
                client._message(time.monotonic() + 1)
        finally:
            connection.close()
            peer.close()

    def test_duplicate_json_error_does_not_expose_payload(self):
        connection, peer = socket.socketpair()
        try:
            peer.sendall(frame(b'{"secret":"synthetic_private_payload","id":1,"id":2}'))
            client = PassiveClient(connection)
            with self.assertRaisesRegex(TransportError, "^invalid_rpc_json$"):
                client._message(time.monotonic() + 1)
        finally:
            connection.close()
            peer.close()

    def test_server_mask_and_binary_frames_rejected(self):
        for data in (b"\x81\x80", frame(b"{}", opcode=2)):
            connection, peer = socket.socketpair()
            try:
                peer.sendall(data)
                with self.assertRaisesRegex(TransportError, "^invalid_frame$"):
                    PassiveClient(connection)._message(time.monotonic() + 1)
            finally:
                connection.close()
                peer.close()

    def test_missing_socket_has_no_startup_or_filesystem_effect(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "missing.sock")
            with self.assertRaisesRegex(TransportError, "^endpoint_unavailable$"):
                PassiveClient.connect(path, expected_uid=os.getuid(), expected_pid=os.getpid())
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_peer_identity_mismatch_rejected_before_handshake(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "peer.sock")
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(path)
            server.listen()
            try:
                with self.assertRaisesRegex(TransportError, "^peer_mismatch$"):
                    PassiveClient.connect(
                        path,
                        expected_uid=os.getuid(),
                        expected_pid=os.getpid() + 100000,
                    )
                accepted, _address = server.accept()
                with accepted:
                    self.assertEqual(accepted.recv(1), b"")
            finally:
                server.close()

    def test_timeout_remains_unknown_transport_failure(self):
        connection, peer = socket.socketpair()
        try:
            with self.assertRaisesRegex(TransportError, "^timeout$"):
                PassiveClient(connection, timeout=0.05)._message(time.monotonic() + 0.02)
        finally:
            connection.close()
            peer.close()
