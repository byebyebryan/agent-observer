"""Public passive read client and on-demand sampled watch."""

from __future__ import annotations

import argparse
import math
import os
import select
import sys
import time
from pathlib import Path

from . import __version__
from .bounded_json import WireError, decode_document
from .contract import MAX_BYTES, SCHEMA_VERSION, ContractError, canonical, parse_snapshot, schema_document
from .native_artifacts import supported_versions
from .read_client import diagnostic, human_rows, listing
from .read_client import select as select_session
from .watch import MIN_INTERVAL, SampledWatch

VERSION = __version__


def _input(path, limit=MAX_BYTES):
    if str(path) == "-":
        data = sys.stdin.buffer.read(limit + 1)
    else:
        with Path(path).open("rb") as stream:
            data = stream.read(limit + 1)
    if len(data) > limit:
        raise ContractError("byte_limit")
    return data


def _scope(parser):
    parser.add_argument("--host-scope")
    parser.add_argument("--provider", choices=("codex", "claude"), action="append")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
    )
    parser.add_argument(
        "--claude-home",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))),
    )
    parser.add_argument(
        "--input", type=Path, help="public snapshot file or - for stdin; does not collect"
    )
    parser.add_argument("--workspace-config", type=Path, help="local root/project mapping JSON")


def _snapshot(args):
    if args.input is not None:
        value = parse_snapshot(_input(args.input))
        if args.host_scope is not None and value["host"]["authority"] != args.host_scope:
            raise ContractError("provenance_mismatch")
        return value
    if args.host_scope is None:
        raise ContractError("host_scope_required")
    from .collection import collect

    config = (
        decode_document(_input(args.workspace_config, 128 * 1024))
        if args.workspace_config
        else None
    )
    return collect(
        host_scope=args.host_scope,
        providers=args.provider or ["codex", "claude"],
        codex_home=args.codex_home,
        claude_home=args.claude_home,
        workspace_config=config,
    )


def _watch_output(frame):
    """Bound stdout backpressure; reconnect starts a new epoch/snapshot."""
    data = (canonical(frame) + "\n").encode()
    fd = sys.stdout.fileno()
    blocking = os.get_blocking(fd)
    deadline = time.monotonic() + 5
    try:
        os.set_blocking(fd, False)
        while data:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [fd], [], max(0, remaining))[1]:
                raise ContractError("watch_output_timeout")
            try:
                size = os.write(fd, data)
            except BlockingIOError:
                continue
            data = data[size:]
    finally:
        os.set_blocking(fd, blocking)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"agent-observer {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)
    schemas = commands.add_parser("schema", help="emit a bundled public JSON schema")
    schemas.add_argument("--kind", choices=("snapshot", "watch"), required=True)
    for command in ("snapshot", "list", "show", "doctor", "watch"):
        command_parser = commands.add_parser(command)
        _scope(command_parser)
        command_parser.add_argument("--json", action="store_true")
        if command in {"list", "watch"}:
            command_parser.add_argument("--include-children", action="store_true")
            command_parser.add_argument(
                "--order", choices=("activity", "created"), default="activity"
            )
        if command == "show":
            command_parser.add_argument(
                "--ref", required=True, help="exact JSON identity from a snapshot row"
            )
        if command == "doctor":
            command_parser.add_argument("--history-census", action="store_true",
                                        help="separate bounded Claude history scan with exclusion counts")
        if command == "watch":
            command_parser.add_argument("--interval", type=float, default=2.0)
            command_parser.add_argument("--count", type=int, help="stop after this many samples")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(canonical(schema_document(args.kind)))
            return 0
        if args.command == "watch":
            if (
                not math.isfinite(args.interval)
                or not MIN_INTERVAL <= args.interval <= 3600
                or (args.count is not None and not 1 <= args.count <= 100000)
            ):
                raise ContractError("invalid_watch_limits")
            watch = SampledWatch()
            count = 0
            while args.count is None or count < args.count:
                started = time.monotonic()
                try:
                    snapshot = _snapshot(args)
                    frames = watch.sample(
                        snapshot, include_children=args.include_children,
                        providers=args.provider, order=args.order,
                    )
                except (ContractError, WireError, ValueError, OSError):
                    frames = [watch.gap()]
                for frame in frames:
                    _watch_output(frame)
                count += 1
                if args.count is None or count < args.count:
                    time.sleep(max(0, args.interval - (time.monotonic() - started)))
            return 0
        value = _snapshot(args)
        if args.command == "list":
            options = dict(
                include_children=args.include_children, providers=args.provider, order=args.order
            )
            print(
                canonical(listing(value, **options)) if args.json else human_rows(value, **options)
            )
        elif args.command == "show":
            reference = decode_document(args.ref.encode(), max_bytes=8192)
            row = select_session(value, reference)
            print(
                canonical(row)
                if args.json
                else human_rows({**value, "sessions": [row]}, include_children=True)
            )
        elif args.command == "doctor":
            report = diagnostic(value)
            if args.history_census:
                if args.input is not None:
                    raise ContractError("history_census_requires_live_scope")
                from .claude_history import collect_saved_history
                report["historyCensus"] = []
                for source in report["sources"]:
                    if source["provider"] != "claude":
                        continue
                    history = collect_saved_history(Path(source["configHome"]), history_limit=1000)
                    report["historyCensus"].append({
                        "provider": "claude", "namespace": source["namespace"],
                        "sampledAt": time.time_ns() // 1_000_000,
                        "coverage": history["coverage"], "counts": history.get("census"),
                        "errors": history["errors"],
                    })
            if args.json:
                print(canonical(report))
            else:
                print(
                    f"{report['host']['authority']}: {report['sourceHealth']}; {report['sessionCount']} sessions; Observer {VERSION}"
                )
                for source in report["sources"]:
                    runtime_version = source["runtime"]["version"] if source["runtime"] else "unavailable"
                    print(
                        f"{source['provider']}: {source['sourceHealth']}; saved={source['coverage']['saved']['status']}; runtime={source['coverage']['runtime']['status']}; version={runtime_version}; accepted={','.join(supported_versions(source['provider']))}; limits={','.join(source['limitations'])}"
                    )
                    for code in source["errors"]:
                        detail = {
                            "runtime_artifact_not_accepted": "actual runtime image is outside accepted support; inspect its reported version/hash separately from the installed CLI",
                            "runtime_artifact_unavailable": "installed runtime executable could not be read",
                            "runtime_peer_identity_mismatch": "kernel peer does not match the configured managed endpoint owner",
                            "runtime_binary_not_accepted": "owning runtime image differs from the explicitly requested artifact",
                            "runtime_version_mismatch": "runtime release path conflicts with its verified artifact version",
                            "runtime_image_ownership_mismatch": "owning runtime executable path or permissions are unsafe",
                            "saved_metadata_unavailable": "independent saved metadata is unavailable or outside its accepted store schema",
                            "history_ambiguous": "conflicting saved identity metadata was excluded",
                            "native_blocked_phase_unproved": "native blocked job phase is unproved; verified identity facts remain usable",
                            "file_unavailable": "a native metadata file could not be read; check retained target evidence",
                        }.get(code, "observation requirement unavailable")
                        print(f"  {code}: {detail}")
                for census in report.get("historyCensus", []):
                    print(f"claude history census (separate sample): {canonical(census)}")
        else:
            print(canonical(value))
        return 0
    except (ContractError, WireError, ValueError) as exc:
        code = str(exc)
        if not code.replace("_", "").isalnum() or len(code) > 128:
            code = "invalid_request"
        print(canonical({"schemaVersion": SCHEMA_VERSION, "error": code}), file=sys.stderr)
        return 2
    except OSError:
        print(canonical({"schemaVersion": SCHEMA_VERSION, "error": "io_unavailable"}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
