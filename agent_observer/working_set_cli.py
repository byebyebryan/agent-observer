"""Bounded human inspection of cached working-set state through the public SDK."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from .utility_read import run_mesh, validate_duration, window_hours


def lines(summary, *, active_only=False):
    """Render already qualified summaries; presentation grants no new authority."""
    view = summary["view"]
    if summary["lifecycle"] != "watching":
        failure = summary["transport"]["failure"]
        return [f"{summary['lifecycle']}: {failure}"] if failure else []
    now = (summary.get("clock") or {}).get("nowBoottimeMs", 0)
    output = [f"{summary['source']['sourceId']}: {view['state']}"]
    for scope in view["scopes"]:
        coverage = scope["coverage"]
        output.append(
            f"  {scope['hostScope']} {scope['namespace']} "
            f"coverage={coverage['status']} reason={coverage.get('reason', 'unknown')}"
        )
    shown = 0
    for row in view["members"]:
        lease = row["membershipLease"]
        active = lease.get("activeExpiresAtMs")
        active = type(active) is int and active > now
        if active_only and not active:
            continue
        identity = row["identity"]
        runtime = row.get("runtime") or {}
        phase = row.get("phase") or {}
        output.append(
            f"  {identity['hostScope']} {identity['namespace']} {identity['nativeId']} "
            f"membership={'active' if active else 'recent'} "
            f"runtime={runtime.get('value', 'unknown')} "
            f"phase={phase.get('value', 'unknown')}"
        )
        shown += 1
    output.append(
        f"  {shown} shown; {view['memberCount']} current members; "
        f"{len(view['uncertain'])} uncertain; {len(view['nonmembers'])} known nonmembers"
    )
    return output


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="operation", required=True)
    for operation in ("list", "watch"):
        selected = commands.add_parser(operation)
        selected.add_argument("--host", required=True, help="exact configured logical host")
        selected.add_argument("--source", default="agent_working_set")
        selected.add_argument("--scope", choices=("local", "hosts"), default="hosts")
        selected.add_argument(
            "--socket", type=Path,
            default=Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
            / "mesh-plus-agent-working-set/read.sock",
            help="local Mesh working-set bridge; remote reads use the configured host route",
        )
        selected.add_argument("--window-hours", type=window_hours, default=72)
        selected.add_argument("--active", action="store_true", help="show the current active branch only")
        selected.add_argument("--duration", type=float, default=5 if operation == "list" else 30)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        validate_duration(args.duration)
    except ValueError as error:
        parser().error(str(error))

    def show(summary):
        for line in lines(summary, active_only=args.active):
            print(line, flush=True)

    try:
        return asyncio.run(run_mesh(
            host=args.host, source=args.source, socket_path=args.socket,
            scope=args.scope, window_ms=args.window_hours * 60 * 60 * 1000,
            duration=args.duration, once=args.operation == "list", output=show,
        ))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
