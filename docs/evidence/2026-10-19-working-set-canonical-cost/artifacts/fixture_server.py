"""Disposable stdlib Codex-shaped JSON-RPC/WebSocket server for local tests."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import signal
import socket
import struct
import time
from collections import Counter
from pathlib import Path
from uuid import UUID


MAX_FRAME = 2 * 1024 * 1024
EXPECTED_ROW_COUNT = 500
PAGE_SIZE = 100
SOURCE_KINDS = [
    "cli", "vscode", "exec", "appServer", "subAgent", "subAgentReview",
    "subAgentCompact", "subAgentThreadSpawn", "subAgentOther", "unknown",
]
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
METHODS = {
    "initialize",
    "thread/list",
    "thread/loaded/list",
    "thread/read",
    "thread/turns/list",
}


class ProtocolFailure(Exception):
    pass


def exact(stream: socket.socket, count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        part = stream.recv(count - len(chunks))
        if not part:
            raise EOFError
        chunks.extend(part)
    return bytes(chunks)


def until_headers(stream: socket.socket) -> bytes | None:
    data = bytearray()
    while not data.endswith(b"\r\n\r\n"):
        part = stream.recv(1)
        if not part:
            return None
        data.extend(part)
        if len(data) > 16384:
            raise ProtocolFailure("handshake_limit")
    return bytes(data)


def websocket_handshake(stream: socket.socket) -> bool:
    try:
        raw = until_headers(stream)
    except TimeoutError:
        # inspect_managed_endpoint connects only to obtain SO_PEERCRED and
        # closes without sending an HTTP request.
        return False
    if raw is None:
        return False
    try:
        lines = raw[:-4].decode("ascii", "strict").split("\r\n")
        if lines[0] != "GET / HTTP/1.1":
            raise ProtocolFailure("invalid_handshake")
        fields = {}
        for line in lines[1:]:
            name, value = line.split(":", 1)
            key = name.lower()
            if key in fields:
                raise ProtocolFailure("invalid_handshake")
            fields[key] = value.strip()
        if fields.get("upgrade", "").lower() != "websocket":
            raise ProtocolFailure("invalid_handshake")
        if "upgrade" not in {
            item.strip().lower() for item in fields.get("connection", "").split(",")
        }:
            raise ProtocolFailure("invalid_handshake")
        key = fields.get("sec-websocket-key")
        if not key or fields.get("sec-websocket-version") != "13":
            raise ProtocolFailure("invalid_handshake")
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
    except (UnicodeError, ValueError):
        raise ProtocolFailure("invalid_handshake") from None
    stream.sendall(
        (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode("ascii")
    )
    return True


def websocket_message(stream: socket.socket) -> dict | None:
    while True:
        try:
            first, second = exact(stream, 2)
        except EOFError:
            return None
        final, opcode = bool(first & 0x80), first & 0x0F
        masked = bool(second & 0x80)
        size = second & 0x7F
        if first & 0x70 or not masked or not final:
            raise ProtocolFailure("invalid_frame")
        if size == 126:
            size = struct.unpack("!H", exact(stream, 2))[0]
        elif size == 127:
            size = struct.unpack("!Q", exact(stream, 8))[0]
        if size > MAX_FRAME or (opcode >= 8 and size > 125):
            raise ProtocolFailure("message_limit")
        mask = exact(stream, 4)
        payload = exact(stream, size)
        decoded = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 8:
            return None
        if opcode == 9:
            websocket_send(stream, decoded, opcode=10)
            continue
        if opcode == 10:
            continue
        if opcode != 1:
            raise ProtocolFailure("invalid_frame")
        try:
            value = json.loads(decoded.decode("utf-8", "strict"))
        except (UnicodeError, json.JSONDecodeError):
            raise ProtocolFailure("invalid_rpc_json") from None
        if not isinstance(value, dict):
            raise ProtocolFailure("invalid_rpc_request")
        return value


def websocket_send(stream: socket.socket, payload: bytes, *, opcode=1) -> None:
    size = len(payload)
    if size > MAX_FRAME:
        raise ProtocolFailure("message_limit")
    if size < 126:
        header = bytes((0x80 | opcode, size))
    elif size < 65536:
        header = bytes((0x80 | opcode, 126)) + struct.pack("!H", size)
    else:
        header = bytes((0x80 | opcode, 127)) + struct.pack("!Q", size)
    stream.sendall(header + payload)


def row_map_value(value: object) -> tuple[dict[str, dict], list[str]]:
    if not isinstance(value, list) or len(value) != EXPECTED_ROW_COUNT:
        raise ProtocolFailure("fixture_row_limit")
    rows = {}
    for row in value:
        if not isinstance(row, dict) or set(row) != {
            "id", "sessionId", "cwd", "source", "threadSource", "ephemeral",
            "createdAt", "updatedAt", "status",
        }:
            raise ProtocolFailure("fixture_row_shape")
        identifier = row["id"]
        session_id = row["sessionId"]
        if (
            not isinstance(identifier, str)
            or not isinstance(session_id, str)
            or identifier == session_id
            or identifier in rows
        ):
            raise ProtocolFailure("fixture_identity")
        try:
            if str(UUID(identifier)) != identifier or str(UUID(session_id)) != session_id:
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            raise ProtocolFailure("fixture_identity") from None
        status = row["status"]
        status_type = status.get("type") if isinstance(status, dict) else None
        if (
            not isinstance(status, dict)
            or not isinstance(status_type, str)
            or status_type not in {"active", "idle", "notLoaded"}
            or set(status) != ({"type", "activeFlags"} if status_type == "active" else {"type"})
            or (status_type == "active" and status.get("activeFlags") != [])
            or not isinstance(row["cwd"], str)
            or not isinstance(row["source"], str)
            or not isinstance(row["threadSource"], str)
            or type(row["ephemeral"]) is not bool
            or type(row["createdAt"]) is not int
            or type(row["updatedAt"]) is not int
        ):
            raise ProtocolFailure("fixture_status_shape")
        rows[identifier] = row
    statuses = Counter(row["status"]["type"] for row in rows.values())
    if statuses != Counter({"active": 1, "idle": 1, "notLoaded": 498}):
        raise ProtocolFailure("fixture_status_census")
    return rows, list(rows)


def row_map(path: Path) -> tuple[dict[str, dict], list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ProtocolFailure("fixture_unavailable") from None
    return row_map_value(value)


class FixtureServer:
    def __init__(self, endpoint: Path, config_home: str, rows: dict, order: list[str]):
        self.endpoint = endpoint
        self.config_home = config_home
        self.rows = rows
        self.order = order
        self.stop = False
        self.stats = {
            "acceptedConnections": 0,
            "methodCounts": Counter(),
            "threadListPageSizes": [],
            "hardFail": False,
        }

    def dispatch(self, message: dict) -> tuple[int | None, dict | None]:
        identifier = message.get("id")
        method = message.get("method")
        params = message.get("params", {})
        if method == "initialized":
            if "id" in message or params != {}:
                raise ProtocolFailure("invalid_initialized")
            self.stats["methodCounts"]["initialized"] += 1
            return None, None
        if not isinstance(method, str) or method not in METHODS:
            raise ProtocolFailure("method_not_passive")
        if type(identifier) is not int or not isinstance(params, dict):
            raise ProtocolFailure("invalid_rpc_request")
        self.stats["methodCounts"][method] += 1

        if method == "initialize":
            if set(params) != {"clientInfo"}:
                raise ProtocolFailure("initialize_params")
            result = {"codexHome": self.config_home}
        elif method == "thread/loaded/list":
            if set(params) != {"cursor"} or params["cursor"] is not None:
                raise ProtocolFailure("loaded_list_params")
            loaded = [
                item for item in self.order
                if self.rows[item]["status"]["type"] != "notLoaded"
            ]
            result = {"data": loaded, "nextCursor": None}
        elif method == "thread/list":
            if set(params) != {"cursor", "limit", "useStateDbOnly", "sourceKinds"}:
                raise ProtocolFailure("thread_list_params")
            cursor = params["cursor"]
            limit = params["limit"]
            if type(limit) is not int or not 1 <= limit <= PAGE_SIZE:
                raise ProtocolFailure("thread_list_params")
            if (
                params["useStateDbOnly"] is not True
                or params["sourceKinds"] != SOURCE_KINDS
            ):
                raise ProtocolFailure("thread_list_params")
            if cursor is None:
                offset = 0
            elif isinstance(cursor, str) and cursor.startswith("offset:"):
                raw_offset = cursor[len("offset:"):]
                if not raw_offset.isascii() or not raw_offset.isdecimal():
                    raise ProtocolFailure("thread_list_cursor")
                offset = int(raw_offset)
            else:
                raise ProtocolFailure("thread_list_cursor")
            if offset < 0 or offset >= len(self.order) or offset % PAGE_SIZE:
                raise ProtocolFailure("thread_list_cursor")
            expected_limit = min(PAGE_SIZE, len(self.order) - offset)
            if limit != expected_limit:
                raise ProtocolFailure("thread_list_page_size")
            end = offset + limit
            self.stats["threadListPageSizes"].append(limit)
            result = {
                "data": [dict(self.rows[item]) for item in self.order[offset:end]],
                "nextCursor": f"offset:{end}" if end < len(self.order) else None,
            }
        elif method == "thread/read":
            if set(params) != {"threadId", "includeTurns"} or params["includeTurns"] is not False:
                raise ProtocolFailure("thread_read_params")
            thread_id = params["threadId"]
            if thread_id not in self.rows:
                raise ProtocolFailure("thread_read_identity")
            result = {"thread": dict(self.rows[thread_id])}
        elif method == "thread/turns/list":
            if set(params) != {"threadId", "limit", "sortDirection", "itemsView"}:
                raise ProtocolFailure("turns_list_params")
            if (
                params["threadId"] not in self.rows
                or params["limit"] != 1
                or params["sortDirection"] != "desc"
                or params["itemsView"] != "notLoaded"
            ):
                raise ProtocolFailure("turns_list_params")
            result = {"data": [], "nextCursor": None}
        else:
            raise ProtocolFailure("method_not_passive")
        return identifier, {"id": identifier, "result": result}

    def connection(self, stream: socket.socket) -> None:
        self.stats["acceptedConnections"] += 1
        stream.settimeout(0.25)
        if not websocket_handshake(stream):
            return
        stream.settimeout(5.0)
        while not self.stop:
            message = websocket_message(stream)
            if message is None:
                return
            _, response = self.dispatch(message)
            if response is not None:
                websocket_send(
                    stream,
                    json.dumps(response, separators=(",", ":")).encode("utf-8"),
                )

    def run(self) -> int:
        if os.path.lexists(self.endpoint):
            raise ProtocolFailure("endpoint_target_present")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        bound_stat = None
        try:
            listener.bind(str(self.endpoint))
            os.chmod(self.endpoint, 0o600)
            listener.listen(8)
            listener.settimeout(0.25)
            bound_stat = self.endpoint.lstat()
            while not self.stop:
                try:
                    stream, _ = listener.accept()
                except TimeoutError:
                    continue
                try:
                    with stream:
                        self.connection(stream)
                except ProtocolFailure:
                    self.stats["hardFail"] = True
                    self.stop = True
            return 0 if not self.stats["hardFail"] else 2
        finally:
            listener.close()
            try:
                current = self.endpoint.lstat()
                if (
                    bound_stat is not None
                    and current.st_dev == bound_stat.st_dev
                    and current.st_ino == bound_stat.st_ino
                    and current.st_uid == os.geteuid()
                    and stat_socket(current.st_mode)
                ):
                    self.endpoint.unlink()
            except FileNotFoundError:
                pass


def stat_socket(mode: int) -> bool:
    import stat

    return stat.S_ISSOCK(mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", type=Path, required=True)
    parser.add_argument("--config-home", required=True)
    parser.add_argument("--rows-file", type=Path, required=True)
    parser.add_argument("--stats-file", type=Path, required=True)
    args = parser.parse_args()
    if os.path.lexists(args.endpoint) or os.path.lexists(args.stats_file):
        raise SystemExit(70)
    rows, order = row_map(args.rows_file)
    server = FixtureServer(args.endpoint, args.config_home, rows, order)
    signal.signal(signal.SIGTERM, lambda *_: setattr(server, "stop", True))
    code = 70
    try:
        code = server.run()
    except ProtocolFailure:
        server.stats["hardFail"] = True
        code = 71
    finally:
        value = {
            "acceptedConnections": server.stats["acceptedConnections"],
            "methodCounts": dict(sorted(server.stats["methodCounts"].items())),
            "threadListPageSizes": server.stats["threadListPageSizes"],
            "hardFail": bool(server.stats["hardFail"]),
        }
        args.stats_file.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(args.stats_file, 0o600)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
