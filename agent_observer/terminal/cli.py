"""Read cached sessions across configured hosts and homes."""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import re
import shutil
import signal
import sys
import unicodedata
from dataclasses import replace
from pathlib import Path

from ..bounded_json import WireError, decode_document
from .config import TerminalConfigError, load_config, select_sources
from .model import build_report, generated_at_now, identity_tuple, safe_metadata
from .output import OutputError, json_document, schema_document, write_stderr, write_stdout
from .render import color_enabled, render
from .sources import TerminalDependencyError, read_sources


def _timeout(value: str) -> float:
    try:
        result = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 60 seconds") from None
    if not math.isfinite(result) or not 1 <= result <= 60:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 60 seconds")
    return result


def _window_hours(value: str) -> int:
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("window hours must be an integer from 0 to 720") from None
    if not 0 <= result <= 720:
        raise argparse.ArgumentTypeError("window hours must be an integer from 0 to 720")
    return result


class _SessionParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        repeated = {"source", "host", "home", "membership", "runtime", "phase", "query"}
        for name, value in tuple(vars(parsed).items()):
            if not name.startswith("_before_"):
                continue
            target = name.removeprefix("_before_")
            if not hasattr(parsed, target):
                setattr(parsed, target, value)
            elif target in repeated:
                setattr(parsed, target, [*(value or ()), *(getattr(parsed, target) or ())])
            delattr(parsed, name)
        return parsed


def _add_common(parser: argparse.ArgumentParser, *, suppress: bool = False) -> None:
    def add(*flags, **options):
        if not suppress:
            name = flags[0].removeprefix("--").replace("-", "_")
            options["dest"] = "_before_" + name
            if options.get("action") != "store_true":
                choices = options.get("choices")
                options["metavar"] = "{" + ",".join(choices) + "}" if choices else name.upper()
        return parser.add_argument(*flags, **options)

    default = argparse.SUPPRESS if suppress else None
    add("--config", type=Path, default=default, help="private terminal.toml source configuration")
    add(
        "--socket",
        type=Path,
        default=argparse.SUPPRESS if suppress else None,
        help="override one selected local Mesh publisher socket",
    )
    add(
        "--window-hours",
        type=_window_hours,
        default=argparse.SUPPRESS if suppress else None,
        help="override one selected source's fixed publisher window",
    )
    add(
        "--source",
        action="append",
        default=argparse.SUPPRESS if suppress else None,
        help="select an exact configured source ID; repeat to OR values",
    )
    add(
        "--host",
        action="append",
        default=argparse.SUPPRESS if suppress else None,
        help="select an exact configured host; repeat to OR values",
    )
    add(
        "--home",
        action="append",
        default=argparse.SUPPRESS if suppress else None,
        help="select an exact configured home ID; repeat to OR values",
    )
    add(
        "--timeout",
        type=_timeout,
        default=argparse.SUPPRESS if suppress else 10.0,
        help="shared finite read deadline in seconds (1-60; default 10)",
    )
    add("--format", choices=("text", "json"), default=argparse.SUPPRESS if suppress else "text")
    add(
        "--color",
        choices=("auto", "always", "never"),
        default=argparse.SUPPRESS if suppress else "auto",
    )
    add("--include-children", action="store_true", default=argparse.SUPPRESS if suppress else False)
    add("--include-system", action="store_true", default=argparse.SUPPRESS if suppress else False)
    add(
        "--membership",
        choices=("active", "recent", "uncertain", "nonmember"),
        action="append",
        default=argparse.SUPPRESS if suppress else None,
    )
    add(
        "--runtime",
        choices=("running", "parked", "unknown"),
        action="append",
        default=argparse.SUPPRESS if suppress else None,
    )
    add(
        "--phase",
        choices=("working", "blocked", "waiting", "unknown"),
        action="append",
        default=argparse.SUPPRESS if suppress else None,
    )
    add(
        "--query",
        action="append",
        default=argparse.SUPPRESS if suppress else None,
        help="literal case-insensitive metadata search; repeat to OR values",
    )
    add(
        "--sort",
        choices=("activity", "label", "host"),
        default=argparse.SUPPRESS if suppress else "activity",
    )
    add("--group", choices=("none", "host-home"), default=argparse.SUPPRESS if suppress else "none")


def parser(*, prog: str = "agent-observer sessions") -> argparse.ArgumentParser:
    root = _SessionParser(prog=prog, description=__doc__)
    _add_common(root)
    commands = root.add_subparsers(dest="command", parser_class=argparse.ArgumentParser)
    for name, description in (
        ("overview", "show a concise fleet summary (also the default)"),
        ("list", "list matching members and uncertain identities"),
        ("sources", "inspect source health and expected namespace binding"),
    ):
        selected = commands.add_parser(name, help=description, description=description)
        _add_common(selected, suppress=True)
        if name == "sources":
            selected.add_argument(
                "--configured",
                action="store_true",
                help="inspect routes without importing Mesh or connecting",
            )
    show = commands.add_parser("show", help="show one exact thread ID or full JSON identity")
    _add_common(show, suppress=True)
    show.add_argument(
        "id", nargs="?", help="full native thread ID; prefix and title matching are not used"
    )
    show.add_argument(
        "--ref", help="full JSON identity with hostScope/provider/namespace/nativeIdKind/nativeId"
    )
    commands.add_parser("schema", help="emit the packaged terminal JSON v1 schema")
    return root


def _validate_query(values) -> tuple[str, ...]:
    result = tuple(values or ())
    for value in result:
        if not 1 <= len(value) <= 256 or any(
            unicodedata.category(char).startswith("C") for char in value
        ):
            raise TerminalConfigError("query_length_or_control")
    return result


def _filters(args) -> dict:
    return {
        "source": tuple(args.source or ()),
        "host": tuple(args.host or ()),
        "home": tuple(args.home or ()),
        "membership": tuple(args.membership or ()),
        "runtime": tuple(args.runtime or ()),
        "phase": tuple(args.phase or ()),
        "query": _validate_query(args.query),
        "includeChildren": args.include_children,
        "includeSystem": args.include_system,
        "sort": args.sort,
        "group": args.group,
    }


def _configured_report(config, selected, filters) -> dict:
    source_docs = []
    for item in selected:
        source_docs.append(
            {
                **item.as_dict(),
                "meshSource": item.mesh_source,
                "expectedNamespace": item.namespace,
                "observedNamespace": None,
                "baseline": False,
                "delivery": "not_connected",
                "health": "configured",
                "reason": "configuration_only",
                "reasons": ["configuration_only"],
                "lastFrameBoottimeMs": None,
                "captureBoottimeMs": None,
                "scopes": [],
                "clock": None,
            }
        )
    return {
        "interface": "agent-observer.terminal",
        "version": 1,
        "generatedAt": generated_at_now(),
        "selection": {
            "sources": [
                {
                    "id": item.id,
                    "host": item.host,
                    "home": item.home,
                    "label": item.label,
                    "meshSource": item.mesh_source,
                    "namespace": item.namespace,
                }
                for item in selected
            ],
            "config": safe_metadata(str(config.path)),
        },
        "filters": {
            "source": list(filters["source"]),
            "host": list(filters["host"]),
            "home": list(filters["home"]),
            "membership": list(filters["membership"]),
            "runtime": list(filters["runtime"]),
            "phase": list(filters["phase"]),
            "query": list(filters["query"]),
            "includeChildren": filters["includeChildren"],
            "includeSystem": filters["includeSystem"],
            "sort": filters["sort"],
            "group": filters["group"],
        },
        "clock": None,
        "totals": {
            "selectedSources": len(selected),
            "completeSources": 0,
            "partialSources": 0,
            "failedSources": 0,
            "members": 0,
            "uncertain": 0,
            "nonmembers": 0,
            "hiddenKinds": 0,
            "displayedMatches": 0,
            "shown": 0,
            "state": "configured",
        },
        "sources": source_docs,
        "sessions": [],
        "uncertain": [],
        "nonmembers": [],
        "result": "configured",
        "error": None,
    }


def _configured_text(config, selected) -> str:
    lines = [f"Configured sources: {len(selected)} selected; no connections opened."]
    lines.extend(
        f"{item.host}/{item.label} [{item.id}]: home={item.home} mesh={item.mesh_source} "
        f"scope={item.scope} window={item.window_hours}h namespace={item.namespace} socket={item.socket}"
        for item in selected
    )
    lines.append(f"Config: {safe_metadata(str(config.path))}")
    return "\n".join(lines)


def _parse_ref(value: str) -> dict:
    try:
        identity = decode_document(value.encode("utf-8"), max_bytes=8192)
        if type(identity) is not dict:
            raise ValueError
        identity_tuple(identity)
        if identity["provider"] != "codex" or any(not value for value in identity.values()):
            raise ValueError
        if re.fullmatch(r"sha256:[0-9a-f]{64}", identity["namespace"]) is None:
            raise ValueError
        return identity
    except (WireError, UnicodeError, ValueError, TypeError):
        raise TerminalConfigError("show_reference_invalid") from None


def _show_target(args, selected):
    if bool(args.id) == bool(args.ref):
        raise TerminalConfigError("show_requires_exact_target")
    if args.id:
        if not 1 <= len(args.id) <= 128 or any(
            char.isspace() or unicodedata.category(char).startswith("C") for char in args.id
        ):
            raise TerminalConfigError("show_id_invalid")
        if len(selected) != 1:
            raise TerminalConfigError("show_select_one_source")
        return args.id
    identity = _parse_ref(args.ref)
    if not any(
        item.host == identity["hostScope"] and item.namespace == identity["namespace"]
        for item in selected
    ):
        raise TerminalConfigError("show_reference_outside_selection")
    return identity


def _overrides(args, selected):
    if args.socket is None and args.window_hours is None:
        return selected
    if len(selected) != 1:
        raise TerminalConfigError("source_override_requires_one")
    source = selected[0]
    if args.socket is not None:
        socket = args.socket
        if source.scope != "local":
            raise TerminalConfigError("source_socket_remote")
        if (
            not socket.is_absolute()
            or ".." in socket.parts
            or any(unicodedata.category(char).startswith("C") for char in os.fspath(socket))
        ):
            raise TerminalConfigError("source_socket")
        source = replace(source, socket=socket)
    if args.window_hours is not None:
        source = replace(source, window_hours=args.window_hours)
    return (source,)


def _error_message(error: TerminalConfigError) -> str:
    messages = {
        "config_missing": "terminal configuration is missing; create the private terminal.toml described in docs/guides/sessions-cli.md",
        "source_selection_empty": "no configured source matched the explicit selectors",
        "source_selector_unknown": f"unknown configured {error.detail or 'source'} selector",
        "show_select_one_source": "show ID needs exactly one selected source; use --source or --host and --home",
        "show_requires_exact_target": "show requires exactly one full positional ID or --ref JSON",
        "show_reference_outside_selection": "the full identity host and namespace are outside the selected sources",
        "source_override_requires_one": "--socket and --window-hours require exactly one selected source",
        "source_socket_remote": "--socket can override a local source only",
        "mesh_dependency_missing_or_incompatible": "sessions reads require the optional compatible Mesh dependency; install agent-observer[mesh]",
        "mesh_dependency_incompatible": "the installed Mesh or working-set interfaces are incompatible with this reader",
        "query_length_or_control": "each query must be 1-256 characters and contain no control characters",
    }
    return messages.get(error.code, f"invalid terminal configuration or selector ({error.code})")


async def _live_report(args, config, selected, filters, mode: str, target):
    loop = asyncio.get_running_loop()
    interrupted = asyncio.Event()
    terminated = asyncio.Event()
    installed = []
    for signum, event in ((signal.SIGINT, interrupted), (signal.SIGTERM, terminated)):
        try:
            previous = signal.getsignal(signum)
            loop.add_signal_handler(signum, event.set)
            installed.append((signum, previous))
        except (NotImplementedError, RuntimeError, ValueError):
            pass
    try:
        captured = await read_sources(
            tuple(selected),
            timeout=args.timeout,
            interrupt_event=interrupted,
            terminate_event=terminated,
        )
    finally:
        for signum, previous in installed:
            loop.remove_signal_handler(signum)
            signal.signal(signum, previous)
    if captured["exitSignal"]:
        return captured["exitSignal"], None
    filters["configPath"] = safe_metadata(str(config.path))
    report = build_report(
        captured["states"],
        now_boottime_ms=captured["nowBoottimeMs"],
        generated_at=generated_at_now(),
        clock=captured["clock"],
        mode=mode,
        filters=filters,
        target=target,
    )
    if captured["timedOut"]:
        report["result"] = "degraded"
        report["totals"]["state"] = "degraded"
        if report["error"] is None:
            report["error"] = {
                "code": "finite_timeout",
                "message": "At least one selected source did not settle before the shared deadline.",
            }
    if captured["cleanupError"]:
        report["result"] = "degraded"
        report["totals"]["state"] = "degraded"
        report["error"] = {
            "code": "cleanup_failed",
            "message": "A source guard or stream did not close cleanly.",
        }
    if report["result"] == "not_found":
        status = 1
    elif report["result"] == "complete":
        status = 0
    else:
        status = 3
    return status, report


def _emit(
    report: dict, args, mode: str, *, configured=False, command="agent-observer sessions"
) -> int:
    try:
        if args.format == "json":
            document = json_document(report)
        elif configured:
            # Caller supplies the already rendered source setup text.
            document = report["_text"]
        else:
            enabled = color_enabled(args.color, isatty=sys.stdout.isatty())
            width = (
                shutil.get_terminal_size(fallback=(80, 24)).columns if sys.stdout.isatty() else None
            )
            document = render(report, mode=mode, color=enabled, width=width, command=command)
        write_stdout(document)
    except OutputError as error:
        if str(error) == "broken_pipe":
            return 141
        write_stderr(f"sessions output failed ({str(error)})")
        return 3
    return 0


def main(argv=None, *, prog: str = "agent-observer sessions") -> int:
    arguments = sys.argv[1:] if argv is None else argv
    args = parser(prog=prog).parse_args(arguments)
    mode = args.command or "overview"
    if mode == "schema":
        try:
            write_stdout(json_document(schema_document()))
            return 0
        except OutputError as error:
            return 141 if str(error) == "broken_pipe" else 3

    try:
        config = load_config(args.config)
        filters = _filters(args)
        selected = select_sources(
            config,
            source_ids=filters["source"],
            hosts=filters["host"],
            homes=filters["home"],
        )
        selected = _overrides(args, selected)
        if mode == "show":
            target = _show_target(args, selected)
        else:
            target = None
    except TerminalConfigError as error:
        write_stderr(_error_message(error))
        return 2

    if mode == "sources" and args.configured:
        report = _configured_report(config, selected, filters)
        if args.format == "json":
            return _emit(report, args, mode, command=prog)
        report["_text"] = _configured_text(config, selected)
        return _emit(report, args, mode, configured=True, command=prog)

    try:
        status, report = asyncio.run(_live_report(args, config, selected, filters, mode, target))
    except TerminalDependencyError as error:
        write_stderr(_error_message(TerminalConfigError(error.code)))
        return 2
    except KeyboardInterrupt:
        return 130
    if report is None:
        return status
    output_status = _emit(report, args, mode, command=prog)
    return status if output_status == 0 else output_status


if __name__ == "__main__":
    raise SystemExit(main())
