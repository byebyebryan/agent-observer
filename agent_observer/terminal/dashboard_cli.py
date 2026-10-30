"""Open the persistent, read-only dashboard over configured cached sources."""

from __future__ import annotations

import asyncio
import os
import sys

from .cli import _add_common, _error_message, _filters, _overrides, _SessionParser
from .config import TerminalConfigError, load_config, select_sources
from .model import safe_metadata
from .output import write_stderr
from .render import color_enabled, icons_enabled
from .sources import TerminalDependencyError, _dependencies


def parser():
    result = _SessionParser(prog="agent-observer dashboard", description=__doc__)
    _add_common(result, dashboard=True)
    result.set_defaults(_before_sort=None, _before_group=None)
    result.add_argument(
        "--no-saved-view",
        action="store_true",
        help="keep pins, order and grouping only for this dashboard run",
    )
    return result


def terminal_error(*, streams=None, environ=None) -> str | None:
    """Check suitability before constructing a reader or entering raw mode."""
    environ = os.environ if environ is None else environ
    streams = (
        (sys.stdin, sys.stdout, sys.stderr, sys.__stdin__, sys.__stderr__)
        if streams is None
        else streams
    )
    if sys.platform != "linux":
        return "dashboard requires a Linux terminal; use agent-observer sessions list"
    if environ.get("TERM", "") in {"", "dumb"}:
        return "dashboard requires a cursor-capable TERM; use agent-observer sessions list"
    try:
        fds = tuple(stream.fileno() for stream in streams)
        if not all(os.isatty(fd) for fd in fds):
            return "dashboard requires interactive stdin/stdout/stderr; use agent-observer sessions list"
        if len({os.fstat(fd).st_rdev for fd in fds}) != 1:
            return "dashboard stdin/stdout/stderr must share a terminal; use agent-observer sessions list"
    except (AttributeError, OSError, ValueError):
        return "dashboard requires terminal file descriptors; use agent-observer sessions list"
    return None


def dashboard_dependencies():
    # Help, configuration inspection and finite CLI commands never reach these
    # imports. Importing the driver starts no terminal threads or read streams.
    try:
        from .dashboard_output import BoundedLinuxDriver

        if not callable(BoundedLinuxDriver.wait_closed_async):
            raise ImportError
    except (ImportError, AttributeError):
        raise TerminalDependencyError("dashboard_dependency_missing_or_incompatible") from None
    _dependencies()


def main(argv=None) -> int:
    args = parser().parse_args(sys.argv[1:] if argv is None else argv)
    explicit_sort = args.sort is not None
    explicit_group = args.group is not None
    args.sort = args.sort or "activity"
    args.group = args.group or "none"
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
        filters["configPath"] = safe_metadata(str(config.path))
    except TerminalConfigError as error:
        write_stderr(_error_message(error))
        return 2
    try:
        dashboard_dependencies()
    except TerminalDependencyError as error:
        if error.code.startswith("dashboard_"):
            message = "dashboard requires the optional dashboard dependencies; install agent-observer[mesh,dashboard]"
        else:
            message = _error_message(TerminalConfigError(error.code))
        write_stderr(message)
        return 2
    if message := terminal_error():
        write_stderr(message)
        return 2
    view_controller = None
    if not args.no_saved_view:
        from .dashboard_view import SavedViewController

        view_controller = SavedViewController.from_environment()
    from .dashboard_runner import run_dashboard

    try:
        result = asyncio.run(
            run_dashboard(
                selected,
                filters,
                connect_timeout=args.connect_timeout,
                no_color=not color_enabled(args.color, isatty=True),
                icons=icons_enabled(args.icons, isatty=True, encoding=sys.stdout.encoding),
                saved_view_controller=view_controller,
                explicit_sort=explicit_sort,
                explicit_group=explicit_group,
            )
        )
    except TerminalDependencyError as error:
        write_stderr(_error_message(TerminalConfigError(error.code)))
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        write_stderr(f"dashboard failed ({type(error).__name__})")
        return 3
    if result.reason:
        write_stderr(f"dashboard failed ({result.reason})")
    if result.view_warning:
        warning = (safe_metadata(result.view_warning) or "unavailable")[:64]
        write_stderr(
            "dashboard view not saved; pins and display choices were session-only "
            f"({warning})"
        )
    return result.code


if __name__ == "__main__":
    raise SystemExit(main())
