"""Optional cached state read client. Networking belongs to Mesh Plus."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import secrets
import sys
import time
from pathlib import Path

from .contract import canonical, identity_key
from .read_client import human_snapshots


def interface():
    return {
        "meshProtocol": 1,
        "profile": "agent-observer.mesh-candidate.v1",
        "operations": ["snapshot", "list", "watch"],
        "access": "cached",
        "readOnly": True,
        "routeReporting": False,
        "nativeEventReplay": False,
        "requires": ["configured_reader", "ReadGuard"],
    }


def human_view(frame, current_rows, *, reconstruct, now_ms=None):
    """Display current selection and explicit delivery/coverage qualifications."""
    mesh = frame["mesh"]
    if mesh["kind"] in {"gap", "error"}:
        return f"Mesh {mesh['kind']}: current view revoked"
    if mesh["kind"] == "heartbeat":
        return "Mesh heartbeat; source receipts are unchanged"
    current = {identity_key(row["identity"]) for row in current_rows}
    snapshots, qualifiers = [], []
    for host in mesh["hosts"]:
        qualifiers.append(f"{host['hostId']}: delivery={host['delivery']['status']} view={host['viewState']}")
        if now_ms is not None:
            expired = sum(r["health"] in {"current", "partial"} and r["expiresAtMs"] <= now_ms for r in host["receipts"])
            if expired:
                qualifiers.append(f"  expired receipts={expired}; current selection is reduced")
        if host["owner"] is None:
            continue
        snapshot = reconstruct(frame, host)["snapshot"]
        if snapshot is None:
            continue
        for source in snapshot["sources"]:
            coverage = source["coverage"]["runtime"]
            qualifiers.append(f"  {source['provider']}: runtime={coverage['status']} ({coverage['reason']})")
        snapshot["sessions"] = [row for row in snapshot["sessions"] if identity_key(row["identity"]) in current]
        snapshots.append(snapshot)
    return "\n".join([f"Mesh {mesh['status']} ({mesh['kind']}); cached state", *qualifiers]), snapshots


async def ticked(stream):
    """Wake human rendering while preserving the pending SDK read task."""
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(stream))
            done, _ = await asyncio.wait({pending}, timeout=1)
            if not done:
                yield None
                continue
            try:
                frame = pending.result()
            except StopAsyncIteration:
                return
            pending = None
            yield frame
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)


async def run(args, *, output=None, human_output=None):
    # Import only on explicit mesh reads. Core, host-local CLI and descriptors
    # remain usable with no Mesh package or network configuration installed.
    from mesh_plus.catalog import MeshAuthority, SSHPlusAuthority
    from mesh_plus.configured_read import configured_reader
    from mesh_plus.observer import clock_domain
    from mesh_plus.protocol import check
    from mesh_plus.transport import boottime_ms
    from mesh_plus.view import ReadGuard, current_sessions, reconstructed, validate_response

    from .cli import _watch_output, _write_output

    output = _watch_output if output is None else output
    human_output = (lambda value: _write_output((value + "\n").encode())) if human_output is None else human_output
    authority = MeshAuthority() if args.authority == "mesh" else SSHPlusAuthority()
    reader = await configured_reader("agent", source=args.source, socket=args.socket, scope=args.scope,
                                     hosts=args.hosts, local_host=args.local_host, authority=authority,
                                     report_routes=False)
    request_id = secrets.token_hex(16)
    operation = "watch" if args.command == "watch" else "snapshot"
    request = {"meshProtocol": 1, "requestId": request_id, "operation": operation,
               "profile": "agent-observer.mesh-candidate.v1", "access": "cached",
               "selection": {"mode": args.scope, "hostIds": args.hosts}, "extensions": {}}
    guard = ReadGuard("agent", request_id, host_ids=args.hosts if args.scope == "hosts" else None)
    stream = reader.execute(request)
    events = ticked(stream) if args.human and operation == "watch" else stream
    count, result = 0, 0
    render_at = 0
    try:
        async for frame in events:
            if frame is None:
                if boottime_ms() < render_at:
                    continue
            elif operation == "watch" or "mesh" not in frame:
                guard.accept(frame)
            else:
                validate_response(frame)
                check(frame["protocol"] == request["profile"] and frame["mesh"]["requestId"] == request_id
                      and frame["mesh"]["operation"] == "snapshot", "read_request_binding")
                check(args.scope != "hosts" or frame["mesh"]["scope"]["hostIds"] == args.hosts, "read_scope_binding")
            if frame is not None and "mesh" not in frame:
                if args.human:
                    human_output("Mesh error: " + frame["error"]["code"])
                else:
                    output(frame)
                return 1
            if args.human:
                now = boottime_ms()
                if frame is None:
                    if guard.view is None:
                        continue
                    display = guard.view
                else:
                    display = guard.view if frame["mesh"]["kind"] == "heartbeat" and guard.view is not None else frame
                rows = guard.current(now, clock_domain()) if operation == "watch" else current_sessions(frame, now, clock_domain())
                view = human_view(display, rows, reconstruct=reconstructed, now_ms=now)
                if isinstance(view, str):
                    human_output(view)
                else:
                    qualification, snapshots = view
                    human_output(qualification + "\n" + human_snapshots(
                        snapshots, now_ms=int(time.time() * 1000), include_children=args.include_children,
                        providers=args.provider, order=args.order))
                deadlines = [r["expiresAtMs"] for h in display["mesh"].get("hosts", []) for r in h["receipts"]
                             if r["health"] in {"current", "partial"} and r["expiresAtMs"] > now]
                render_at = min(now + 5000, min(deadlines, default=now + 5000))
            else:
                output(frame)
            if frame is None:
                continue
            result = 1 if frame["mesh"].get("status") == "unavailable" or frame["mesh"]["kind"] == "error" else 0
            count += 1
            if args.count is not None and count >= args.count:
                break
    finally:
        guard.disconnect()
        if events is not stream:
            await events.aclose()
        await stream.aclose()
        if args.human and operation == "watch" and sys.exc_info()[0] in {None, KeyboardInterrupt}:
            human_output("Mesh watch ended; current view revoked")
    return result


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("api", help="describe the optional state-only Mesh mode")
    for name in ("snapshot", "list", "watch"):
        command = commands.add_parser(name)
        command.add_argument("--scope", choices=("local", "fleet", "hosts"), default="fleet")
        command.add_argument("--hosts", nargs="+", default=[])
        command.add_argument("--source", default="agent")
        command.add_argument("--socket", type=Path, default=Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "mesh-plus-agent/read.sock")
        command.add_argument("--authority", choices=("ssh-plus", "mesh"), default="ssh-plus")
        command.add_argument("--local-host", help="explicit standalone identity; bypass the catalog")
        command.set_defaults(human=name == "list", count=None, include_children=False, provider=None, order="activity")
        if name == "watch":
            command.add_argument("--human", action="store_true")
            command.add_argument("--count", type=int, help="limit replacement/control frames")
        if name in {"list", "watch"}:
            command.add_argument("--include-children", action="store_true")
            command.add_argument("--provider", action="append", choices=("codex", "claude"))
            command.add_argument("--order", choices=("activity", "created"), default="activity")
    return root


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if args.command == "api":
        print(canonical(interface()))
        return 0
    if (args.scope == "hosts") != bool(args.hosts) or len(args.hosts) != len(set(args.hosts)):
        root.error("--hosts must be unique and supplied exactly with --scope hosts")
    if args.local_host is not None and (args.scope == "hosts" or args.hosts):
        root.error("--local-host requires local or fleet scope without --hosts")
    if args.count is not None and not 1 <= args.count <= 100000:
        root.error("--count must be 1..100000")
    if not args.human and (args.provider or args.include_children or args.order != "activity"):
        root.error("presentation filters require list or watch --human; raw frames are lossless")
    try:
        return asyncio.run(run(args))
    except ImportError:
        code = "mesh_dependency_unavailable"
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0
    except Exception as error:
        code = getattr(error, "code", "mesh_read_failed")
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code) is None:
            code = "mesh_read_failed"
    print(canonical({"error": code, "message": "Mesh read unavailable"}), file=sys.stderr)
    return 1
