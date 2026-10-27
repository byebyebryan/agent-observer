"""Own dashboard reads and cleanup outside Textual's worker lifetime."""

from __future__ import annotations

import asyncio
import os
import signal
import time
from dataclasses import dataclass

from .watch import PersistentSources, _join_owned


@dataclass(frozen=True)
class DashboardResult:
    code: int
    reason: str | None
    cleanup_seconds: float
    terminal_flags_restored: bool | None
    screen_reset_delivered: bool | None
    failures: tuple[str, ...] = ()


def _app_factory(reader, filters, *, no_color, icons, on_exit_requested):
    from .dashboard import DashboardApp

    class OwnedDashboardApp(DashboardApp):
        def exit(self, *args, **kwargs):
            on_exit_requested()
            return super().exit(*args, **kwargs)

    return OwnedDashboardApp(reader, filters, no_color=no_color, icons=icons)


async def run_dashboard(
    sources,
    filters,
    *,
    connect_timeout=15.0,
    no_color=False,
    icons=False,
    reader_factory=PersistentSources,
    app_factory=_app_factory,
    install_signals=True,
):
    """Return only after UI restoration and all owned cleanup have joined.

    A quit revokes the reader immediately and starts its join independently of
    App.run_async's terminal restoration. Repeated cancellation never reaches
    that owned join. A five-second miss fails acceptance; it cannot justify
    abandoning a still-live owned task.
    """
    reader = reader_factory(sources, connect_timeout=connect_timeout)
    cleanup = None
    app = None
    installed = []
    requested_signal = None
    code, reason = 0, None
    started_cleanup = None
    previous_no_color = os.environ.get("NO_COLOR")
    if no_color:
        os.environ["NO_COLOR"] = "1"

    def begin_cleanup():
        nonlocal cleanup, started_cleanup
        reader.request_close()
        if cleanup is None:
            started_cleanup = time.monotonic()
            cleanup = asyncio.create_task(reader.close())

    def on_signal(signum):
        nonlocal requested_signal
        if requested_signal is None:
            requested_signal = 128 + signum
        begin_cleanup()
        if app is not None:
            app.exit(return_code=requested_signal)

    try:
        app = app_factory(
            reader,
            filters,
            no_color=no_color,
            icons=icons,
            on_exit_requested=begin_cleanup,
        )
        if install_signals:
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                previous = signal.getsignal(signum)
                loop.add_signal_handler(signum, on_signal, signum)
                installed.append((signum, previous))
        await reader.start()
        running = asyncio.create_task(app.run_async())
        interrupted = False
        while not running.done():
            try:
                # Do not forward caller cancellation into Textual's own
                # restoration/shutdown. Request its ordinary exit and join.
                await asyncio.wait({running})
            except asyncio.CancelledError:
                interrupted = True
                begin_cleanup()
                app.exit(return_code=requested_signal or 130)
        running.result()
        code = requested_signal or (130 if interrupted else app.return_code or 0)
        if code not in {0, 3, 129, 130, 143}:
            code, reason = 3, "dashboard_exit_failed"
    except asyncio.CancelledError:
        code = requested_signal or 130
    except Exception as error:
        code, reason = 3, "dashboard_" + type(error).__name__
    finally:
        begin_cleanup()

        async def finish():
            failures = []
            if app is not None:
                try:
                    await app.stop_updates()
                except (Exception, asyncio.CancelledError):
                    failures.append("ui_cleanup_failed")
            try:
                await cleanup
            except (Exception, asyncio.CancelledError):
                failures.append("reader_cleanup_failed")
            driver = getattr(app, "output_driver", None)
            if driver is not None:
                try:
                    if not await driver.wait_closed_async():
                        failures.append("output_cleanup_failed")
                    if driver.output_failure is not None:
                        failures.insert(0, driver.output_failure.code)
                    if driver.terminal_flags_restored is False:
                        failures.append("terminal_flags_not_restored")
                    if (
                        driver.terminal_restore_seconds is not None
                        and driver.terminal_restore_seconds > 2
                    ):
                        failures.append("terminal_restore_timeout")
                except (Exception, asyncio.CancelledError):
                    failures.append("output_cleanup_failed")
            return failures

        try:
            failures, cancelled = await _join_owned(asyncio.create_task(finish()))
            elapsed = time.monotonic() - started_cleanup
            if reader.cleanup_error:
                failures.append(reader.cleanup_error)
            if elapsed > 5:
                failures.append("cleanup_timeout")
            if failures:
                code, reason = 3, failures[0]
            elif cancelled:
                code = requested_signal or 130
        finally:
            for signum, previous in installed:
                asyncio.get_running_loop().remove_signal_handler(signum)
                signal.signal(signum, previous)
            if no_color:
                if previous_no_color is None:
                    os.environ.pop("NO_COLOR", None)
                else:
                    os.environ["NO_COLOR"] = previous_no_color
    driver = getattr(app, "output_driver", None)
    return DashboardResult(
        code,
        reason,
        elapsed,
        getattr(driver, "terminal_flags_restored", None),
        getattr(driver, "screen_reset_delivered", None),
        tuple(failures),
    )
