"""Study-only passive Codex Unix WebSocket transport.

The caller must establish exact endpoint/process/namespace ownership first.
This module never launches a provider and only permits the inspected read
methods. Results live in memory; adapters must filter them before emitting.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import time

from .bounded_json import WireError, decode_document

_READ_METHODS = frozenset(
    {"initialize", "thread/list", "thread/loaded/list", "thread/read", "thread/turns/list"}
)
SOURCE_KINDS = (
    "cli", "vscode", "exec", "appServer", "subAgent", "subAgentReview",
    "subAgentCompact", "subAgentThreadSpawn", "subAgentOther", "unknown",
)
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class TransportError(ValueError):
    """Content-free failure code, never a native message or payload."""


class PassiveClient:
    def __init__(
        self,
        connection: socket.socket,
        *,
        timeout: float = 5.0,
        max_message_bytes: int = 2 * 1024 * 1024,
    ):
        if (
            type(timeout) not in (int, float)
            or not 0 < timeout <= 30
            or type(max_message_bytes) is not int
            or not 256 <= max_message_bytes <= 8 * 1024 * 1024
        ):
            raise TransportError("invalid_limit")
        self.connection = connection
        self.timeout = timeout
        self.max_message_bytes = max_message_bytes
        self.buffer = bytearray()
        self.next_id = 1
        self.initialized = False
        self.ignored_messages = 0

    @classmethod
    def connect(
        cls,
        endpoint: str,
        *,
        expected_uid: int,
        expected_pid: int,
        timeout: float = 5.0,
    ):
        """Connect to an existing endpoint; no CLI, daemon startup or repair."""
        if (
            not isinstance(endpoint, str)
            or not endpoint.startswith("/")
            or "\x00" in endpoint
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in endpoint)
            or len(endpoint.encode()) > 107
            or isinstance(expected_uid, bool)
            or not isinstance(expected_uid, int)
            or expected_uid < 0
            or isinstance(expected_pid, bool)
            or not isinstance(expected_pid, int)
            or expected_pid < 1
        ):
            raise TransportError("invalid_endpoint")
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client = cls(connection, timeout=timeout)
            connection.settimeout(timeout)
            connection.connect(endpoint)
            peer_pid, peer_uid, _gid = struct.unpack(
                "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            )
            if peer_uid != expected_uid or peer_pid != expected_pid:
                raise TransportError("peer_mismatch")
            client.upgrade()
            return client
        except TransportError:
            connection.close()
            raise
        except OSError:
            connection.close()
            raise TransportError("endpoint_unavailable") from None

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    def _receive(self, count, deadline):
        while len(self.buffer) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportError("timeout")
            self.connection.settimeout(remaining)
            try:
                chunk = self.connection.recv(min(65536, count - len(self.buffer)))
            except TimeoutError:
                raise TransportError("timeout") from None
            except OSError:
                raise TransportError("connection_failed") from None
            if not chunk:
                raise TransportError("peer_closed")
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def upgrade(self):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Key: "
            + key
            + "\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost\r\n\r\n"
        )
        self._send(request.encode("ascii"))
        deadline = time.monotonic() + self.timeout
        head = bytearray()
        while not head.endswith(b"\r\n\r\n"):
            if len(head) >= 16384:
                raise TransportError("handshake_limit")
            head.extend(self._receive(1, deadline))
        try:
            lines = head[:-4].decode("ascii", "strict").split("\r\n")
            fields = {}
            for line in lines[1:]:
                name, value = line.split(":", 1)
                name = name.lower()
                if name in fields:
                    raise TransportError("invalid_handshake")
                fields[name] = value.strip()
            expected = base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()
            if (
                lines[0] != "HTTP/1.1 101 Switching Protocols"
                or fields.get("sec-websocket-accept") != expected
                or fields.get("upgrade", "").lower() != "websocket"
                or "upgrade"
                not in {token.strip().lower() for token in fields.get("connection", "").split(",")}
            ):
                raise TransportError("invalid_handshake")
        except (UnicodeError, ValueError):
            raise TransportError("invalid_handshake") from None

    def _send(self, data):
        try:
            self.connection.settimeout(self.timeout)
            self.connection.sendall(data)
        except TimeoutError:
            raise TransportError("timeout") from None
        except OSError:
            raise TransportError("connection_failed") from None

    def _send_frame(self, payload: bytes, opcode: int = 1):
        if len(payload) > self.max_message_bytes:
            raise TransportError("message_limit")
        mask = os.urandom(4)
        size = len(payload)
        header = (
            bytes((0x80 | opcode, 0x80 | size))
            if size < 126
            else (
                bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", size)
                if size < 65536
                else bytes((0x80 | opcode, 0x80 | 127)) + struct.pack("!Q", size)
            )
        )
        encoded = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._send(header + mask + encoded)

    def _message(self, deadline):
        fragments = bytearray()
        fragmented = False
        for _ in range(256):
            first, second = self._receive(2, deadline)
            final, opcode = bool(first & 0x80), first & 0x0F
            if first & 0x70 or second & 0x80:
                raise TransportError("invalid_frame")
            size = second & 0x7F
            if size == 126:
                size = struct.unpack("!H", self._receive(2, deadline))[0]
            elif size == 127:
                size = struct.unpack("!Q", self._receive(8, deadline))[0]
            if size > self.max_message_bytes or len(fragments) + size > self.max_message_bytes:
                raise TransportError("message_limit")
            if opcode >= 8 and (not final or size > 125):
                raise TransportError("invalid_frame")
            body = self._receive(size, deadline)
            if opcode == 8:
                raise TransportError("peer_closed")
            if opcode == 9:
                self._send_frame(body, 10)
                continue
            if opcode == 10:
                continue
            if opcode == 1:
                if fragmented:
                    raise TransportError("invalid_frame")
                fragmented = not final
            elif opcode != 0 or not fragmented:
                raise TransportError("invalid_frame")
            fragments.extend(body)
            if final:
                try:
                    return decode_document(bytes(fragments), max_bytes=self.max_message_bytes)
                except WireError:
                    raise TransportError("invalid_rpc_json") from None
        raise TransportError("frame_limit")

    def _request(self, method, params):
        if not isinstance(method, str) or method not in _READ_METHODS:
            raise TransportError("method_not_passive")
        if not isinstance(params, dict):
            raise TransportError("invalid_request")
        if method != "initialize" and not self.initialized:
            raise TransportError("not_initialized")
        if method == "thread/read" and params.get("includeTurns") is not False:
            raise TransportError("content_read_rejected")
        if method == "thread/turns/list" and (
            set(params) != {"threadId", "limit", "sortDirection", "itemsView"}
            or params.get("itemsView") != "notLoaded"
            or type(params.get("limit")) is not int
            or params["limit"] != 1
            or params.get("sortDirection") != "desc"
        ):
            raise TransportError("content_read_rejected")
        identifier = self.next_id
        self.next_id += 1
        self._send_frame(
            json.dumps(
                {"id": identifier, "method": method, "params": params},
                separators=(",", ":"),
            ).encode()
        )
        deadline = time.monotonic() + self.timeout
        for _ in range(256):
            value = self._message(deadline)
            if not isinstance(value, dict):
                raise TransportError("invalid_rpc_response")
            if "method" in value or type(value.get("id")) is not int or value["id"] != identifier:
                self.ignored_messages += 1
                continue
            if ("result" in value) == ("error" in value):
                raise TransportError("invalid_rpc_response")
            if "error" in value:
                raise TransportError("native_read_failed")
            return value["result"]
        raise TransportError("message_count_limit")

    def initialize(self):
        if self.initialized:
            raise TransportError("already_initialized")
        result = self._request(
            "initialize",
            {"clientInfo": {"name": "agent-observer-study", "version": "0.0.0"}},
        )
        self._send_frame(b'{"method":"initialized","params":{}}')
        self.initialized = True
        return result

    def notification(self):
        """Receive bounded unsolicited metadata; never subscribe or acknowledge.

        The caller waits for socket readability and owns reconnect after any
        timeout/protocol error, because an incomplete frame cannot be reused.
        """
        if not self.initialized:
            raise TransportError("not_initialized")
        return self._message(time.monotonic() + self.timeout)

    def list_threads(self, *, cursor=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise TransportError("invalid_limit")
        if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 4096):
            raise TransportError("invalid_cursor")
        return self._request("thread/list", {
            "cursor": cursor, "limit": limit, "useStateDbOnly": True,
            "sourceKinds": list(SOURCE_KINDS),
        })

    def loaded_threads(self, *, cursor=None):
        if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 4096):
            raise TransportError("invalid_cursor")
        return self._request("thread/loaded/list", {"cursor": cursor})

    def read_thread(self, native_id: str):
        if (
            not isinstance(native_id, str)
            or not 1 <= len(native_id) <= 256
            or any(ord(char) < 32 for char in native_id)
        ):
            raise TransportError("invalid_native_id")
        return self._request("thread/read", {"threadId": native_id, "includeTurns": False})

    def latest_turn(self, native_id: str):
        if (
            not isinstance(native_id, str)
            or not 1 <= len(native_id) <= 256
            or any(ord(char) < 32 for char in native_id)
        ):
            raise TransportError("invalid_native_id")
        return self._request(
            "thread/turns/list",
            {"threadId": native_id, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"},
        )
