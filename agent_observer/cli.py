"""Public command candidate. Observation has no provider action commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .host_snapshot import collect_host

VERSION = "0.1.0a5"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"agent-observer {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="read existing host-local provider metadata")
    snapshot.add_argument("--host-scope", required=True)
    snapshot.add_argument("--provider", choices=("codex", "claude"), action="append")
    snapshot.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
    )
    snapshot.add_argument(
        "--claude-home",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))),
    )
    args = parser.parse_args()
    try:
        value = collect_host(
            host_scope=args.host_scope,
            providers=args.provider or ["codex", "claude"],
            codex_home=args.codex_home,
            claude_home=args.claude_home,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
