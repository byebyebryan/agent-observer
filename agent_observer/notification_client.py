"""Explicit experimental notification client; stdout transport, no automatic TTY routing."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from collections import OrderedDict
from pathlib import Path

from .bounded_json import WireError, decode_document
from .notification_source import (
    MAX_EVENT_BYTES,
    MAX_HOOK_BYTES,
    NotificationError,
    normalize,
    parse_event,
    schema_document,
    validate_event,
)
from .public import ContractError, parse_snapshot


class RecentEvents:
    """Bounded process-local suppression; reconnect/restart/eviction allow duplicates."""

    def __init__(self, limit=256):
        if type(limit) is not int or not 1 <= limit <= 4096:
            raise NotificationError("invalid_dedupe_limit")
        self.limit, self.keys = limit, OrderedDict()

    def accept(self, event):
        validate_event(event)
        key = event["correlation"]["dedupeKey"] or "receipt:" + event["receiptId"]
        if key in self.keys:
            self.keys.move_to_end(key)
            return False
        self.keys[key] = None
        if len(self.keys) > self.limit:
            self.keys.popitem(last=False)
        return True


def _encode(text):
    return base64.b64encode(text.encode()).decode("ascii")


def render(event, form="kitty", *, tmux_passthrough=False):
    validate_event(event)
    if form not in {"kitty", "claude-hook"}:
        raise NotificationError("unsupported_transport")
    if tmux_passthrough and form != "kitty":
        raise NotificationError("unsupported_transport")
    if event["disposition"] != "notify":
        return "{}\n" if form == "claude-hook" else ""
    if form == "claude-hook" and event["identity"]["provider"] != "claude":
        raise NotificationError("unsupported_transport")
    sender = "Codex" if event["identity"]["provider"] == "codex" else "Claude"
    # This IDs chunks; it is not a desktop delivery/acknowledgement guarantee.
    identifier = "observer-" + (event["correlation"]["dedupeKey"] or event["receiptId"]).replace(
        "sha256:", ""
    )
    meta = f"i={identifier}:e=1:f={_encode(sender)}:o=unfocused:a=focus"
    sequence = f"\x1b]99;{meta}:d=0;{_encode(event['title'])}\x1b\\\x1b]99;{meta}:p=body:d=1;{_encode(event['body'])}\x1b\\"
    if tmux_passthrough:
        sequence = "\x1bPtmux;" + sequence.replace("\x1b", "\x1b\x1b") + "\x1b\\"
    return json.dumps({"terminalSequence": sequence}) + "\n" if form == "claude-hook" else sequence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema")
    normal = commands.add_parser("normalize")
    normal.add_argument(
        "--identity",
        required=True,
        help="full Observer reference JSON; caller supplies owning host/store",
    )
    normal.add_argument(
        "--snapshot", type=Path, help="optional public snapshot for exact kind/title lookup"
    )
    for name in ("render", "stream"):
        sub = commands.add_parser(name)
        sub.add_argument("--format", choices=("json", "kitty", "claude-hook"), default="json")
        sub.add_argument(
            "--tmux-passthrough",
            action="store_true",
            help="explicit Kitty tmux DCS wrapper; caller owns pane routing",
        )
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            output = json.dumps(schema_document()) + "\n"
        elif args.command == "normalize":
            ref = decode_document(args.identity.encode(), max_bytes=2048, max_nodes=32)
            if args.snapshot:
                with args.snapshot.open("rb") as file:
                    snapshot = parse_snapshot(file.read(8 * 1024 * 1024 + 1))
            else:
                snapshot = None
            output = (
                json.dumps(
                    normalize(sys.stdin.buffer.read(MAX_HOOK_BYTES + 1), ref, snapshot=snapshot)
                )
                + "\n"
            )
        elif args.command == "render":
            if args.tmux_passthrough and args.format != "kitty":
                raise NotificationError("unsupported_transport")
            event = parse_event(sys.stdin.buffer.read(MAX_EVENT_BYTES + 1))
            output = (
                json.dumps(event) + "\n"
                if args.format == "json"
                else render(event, args.format, tmux_passthrough=args.tmux_passthrough)
            )
        else:
            if args.tmux_passthrough and args.format != "kitty":
                raise NotificationError("unsupported_transport")
            seen = RecentEvents()
            while line := sys.stdin.buffer.readline(MAX_EVENT_BYTES + 1):
                event = parse_event(line, framed=True)
                if seen.accept(event):
                    output = (
                        json.dumps(event) + "\n"
                        if args.format == "json"
                        else render(event, args.format, tmux_passthrough=args.tmux_passthrough)
                    )
                    sys.stdout.write(output)
                    sys.stdout.flush()
            return 0
        sys.stdout.write(output)
        return 0
    except (WireError, ContractError, NotificationError, OSError, UnicodeError):
        print('{"error":"notification_input_or_transport_unavailable"}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
