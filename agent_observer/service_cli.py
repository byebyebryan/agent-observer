"""Explicit first-party service read client and foreground service entry."""

import argparse
import os
import signal
import sys
import threading
from pathlib import Path

from . import __version__
from .contract import ContractError, canonical
from .service_contract import interface, schema_document


def socket_path():
    root = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.geteuid()}")
    return Path(root) / "agent-observer" / "read.sock"


def report(error):
    code = str(error)
    if not code.replace("_", "").isalnum() or len(code) > 128:
        code = "service_io_unavailable"
    print(canonical({"serviceProtocol": 1, "error": code}), file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("api")
    schema = commands.add_parser("schema")
    schema.add_argument("--kind", choices=("request", "frame"), required=True)
    for name in ("status", "snapshot", "list", "watch"):
        sub = commands.add_parser(name)
        sub.add_argument("--socket", type=Path, default=socket_path())
        sub.add_argument("--host-scope", required=True)
        sub.add_argument("--timeout", type=float, default=15)
        sub.add_argument("--json", action="store_true")
        if name in {"list", "watch"}:
            sub.add_argument("--include-children", action="store_true")
            sub.add_argument("--provider", action="append", choices=("codex", "claude"))
            sub.add_argument("--order", choices=("activity", "created"), default="activity")
        if name == "watch":
            sub.add_argument("--count", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command in {"api", "schema"}:
            print(canonical(interface() if args.command == "api" else schema_document(args.kind)))
            return 0
        if args.command == "watch" and args.count is not None and not 1 <= args.count <= 100000:
            raise ContractError("service_watch_count")
        from .cli import _watch_output
        from .service_client import frames
        operation = "snapshot" if args.command == "list" else args.command
        stream = frames(args.socket, host_scope=args.host_scope, operation=operation, timeout=args.timeout)
        try:
            for count, frame in enumerate(stream, 1):
                if args.command == "list":
                    if frame["snapshot"] is None:
                        raise ContractError("service_warming")
                    from .read_client import human_rows, listing
                    options = dict(include_children=args.include_children, providers=args.provider, order=args.order)
                    if args.json:
                        frame["snapshot"] = listing(frame["snapshot"], **options)
                        print(canonical(frame))
                    else:
                        print(human_rows(frame["snapshot"], **options))
                elif args.command == "watch":
                    if frame["snapshot"] is not None:
                        from .read_client import listing
                        frame["snapshot"] = listing(frame["snapshot"], include_children=args.include_children, providers=args.provider, order=args.order)
                    _watch_output(frame)
                    if args.count is not None and count >= args.count:
                        break
                else:
                    print(canonical(frame))
        finally:
            stream.close()
        return 0
    except (ValueError, OSError) as error:
        return report(error)
    except KeyboardInterrupt:
        return 130


def serve(argv=None):
    parser = argparse.ArgumentParser(description="Foreground shared passive Observer service")
    parser.add_argument("--version", action="version", version=f"agent-observer-service {__version__}")
    parser.add_argument("command", choices=("serve",))
    parser.add_argument("--host-scope", required=True)
    parser.add_argument("--socket", type=Path, default=socket_path())
    parser.add_argument("--provider", choices=("codex", "claude"), action="append", required=True)
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))))
    parser.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))))
    parser.add_argument("--runtime-interval", type=float, default=20)
    parser.add_argument("--history-interval", type=float, default=60)
    parser.add_argument("--collection-timeout", type=float, default=10)
    parser.add_argument("--native-hints", action="store_true",
                        help="candidate passive native wakeups alongside periodic reconciliation")
    parser.add_argument("--hint-diagnostics", type=Path,
                        help="optional bounded private operator JSON, outside public frames")
    parser.add_argument("--workspace-config", type=Path,
                        help="startup-only local root/project mapping JSON; restart to reload")
    args = parser.parse_args(argv)
    try:
        if len(set(args.provider)) != len(args.provider):
            raise ContractError("invalid_provider_selection")
        if args.hint_diagnostics and not args.native_hints:
            raise ContractError("service_hint_diagnostics_mode")
        from .service_runtime import Runtime
        from .service_scheduler import Scheduler
        from .service_state import ServiceState
        from .workspace import load_config
        workspace_config = load_config(args.workspace_config) if args.workspace_config else None
        configs = {p: (str(args.codex_home), "explicit") if p == "codex" else (str(args.claude_home), "default" if args.claude_home == Path.home() / ".claude" and "CLAUDE_CONFIG_DIR" not in os.environ else "explicit") for p in args.provider}
        state = ServiceState(host_scope=args.host_scope, configs=configs)
        scheduler = Scheduler(configs, intervals={"runtime": int(args.runtime_interval * 1000), "history": int(args.history_interval * 1000)}, timeout_ms=int(args.collection_timeout * 1000))
        stop = threading.Event()
        handlers = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            for s in handlers:
                signal.signal(s, lambda *_args: stop.set())
            Runtime(state, args.socket, scheduler=scheduler, workspace_config=workspace_config,
                    native_hints=args.native_hints, hint_diagnostics=args.hint_diagnostics).run(stop)
        finally:
            for s, handler in handlers.items():
                signal.signal(s, handler)
        return 0
    except (ValueError, OSError, OverflowError) as error:
        return report(error)


if __name__ == "__main__":
    raise SystemExit(main())
