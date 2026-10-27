"""Outer ownership under quit, signals and repeated caller cancellation."""

import asyncio
import os
import signal
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent_observer.terminal.dashboard_runner import run_dashboard


class Reader:
    def __init__(self, *, blocked=False):
        self.events = []
        self.requested = False
        self.close_started = asyncio.Event()
        self.release = asyncio.Event()
        if not blocked:
            self.release.set()
        self.closed = False
        self.close_cancellations = 0
        self.cleanup_error = None

    async def start(self):
        pass

    def request_close(self):
        self.events.append("reader-request-close")
        self.requested = True

    async def close(self):
        self.close_started.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.close_cancellations += 1
            raise
        self.closed = True


class App:
    def __init__(self, *, blocked_restore=False, failure=None):
        self.events = None
        self.started = asyncio.Event()
        self.exit_requested = asyncio.Event()
        self.restoring = asyncio.Event()
        self.release_restore = asyncio.Event()
        if not blocked_restore:
            self.release_restore.set()
        self.callback = None
        self.return_code = 0
        self.restored = False
        self.stopped = False
        self.stop_requested = False
        self.cancellations = 0
        self.failure = failure

    async def run_async(self):
        self.started.set()
        if self.failure:
            raise self.failure
        try:
            await self.exit_requested.wait()
            self.restoring.set()
            await self.release_restore.wait()
        except asyncio.CancelledError:
            self.cancellations += 1
            raise
        self.restored = True

    def exit(self, *, return_code=0):
        self.callback()
        self.return_code = return_code
        self.exit_requested.set()

    def request_stop_updates(self):
        self.stop_requested = True
        if self.events is not None:
            self.events.append("app-stop-request")

    async def stop_updates(self):
        self.stopped = True
        if self.events is not None:
            self.events.append("app-stop-join")


class DashboardRunnerTests(unittest.IsolatedAsyncioTestCase):
    def launch(self, reader=None, app=None, **kwargs):
        reader = reader or Reader()
        app = app or App()
        app.events = reader.events

        def factory(_reader, _filters, **options):
            self.assertIs(_reader, reader)
            app.callback = options["on_exit_requested"]
            app.options = options
            return app

        def reader_factory(sources, **options):
            reader.options = options
            return reader

        task = asyncio.create_task(
            run_dashboard(
                (),
                {},
                reader_factory=reader_factory,
                app_factory=factory,
                install_signals=kwargs.pop("install_signals", False),
                **kwargs,
            )
        )
        return task, reader, app

    async def test_quit_revokes_and_starts_reader_cleanup_before_ui_restoration(self):
        task, reader, app = self.launch(Reader(blocked=True), App(blocked_restore=True))
        await app.started.wait()
        app.exit(return_code=0)
        self.assertTrue(reader.requested)
        await reader.close_started.wait()
        await app.restoring.wait()
        self.assertFalse(app.restored)
        self.assertFalse(task.done())
        app.release_restore.set()
        reader.release.set()
        result = await task
        self.assertEqual(result.code, 0)
        self.assertTrue(reader.closed and app.restored and app.stopped)
        self.assertTrue(app.stop_requested)
        self.assertEqual(
            reader.events[:2], ["app-stop-request", "reader-request-close"]
        )
        self.assertIn("app-stop-join", reader.events)

    async def test_legacy_app_factory_without_sync_stop_hook_still_cleans_up(self):
        app = App()
        app.request_stop_updates = None
        task, reader, app = self.launch(app=app)
        await app.started.wait()
        app.exit()
        result = await task
        self.assertEqual(result.code, 0)
        self.assertTrue(reader.closed and app.restored and app.stopped)
        self.assertNotIn("app-stop-request", reader.events)
        self.assertIn("app-stop-join", reader.events)

    async def test_sync_stop_hook_failure_does_not_skip_reader_or_app_join(self):
        app = App()

        def fail_stop():
            raise RuntimeError("synthetic UI stop failure")

        app.request_stop_updates = fail_stop
        task, reader, app = self.launch(app=app)
        await app.started.wait()
        app.exit()
        result = await task
        self.assertEqual(result.code, 3)
        self.assertEqual(result.reason, "ui_stop_request_failed")
        self.assertIn("ui_stop_request_failed", result.failures)
        self.assertTrue(reader.closed and app.restored and app.stopped)

    async def test_repeated_cancel_never_cancels_ui_restore_or_owned_reader_join(self):
        task, reader, app = self.launch(Reader(blocked=True), App(blocked_restore=True))
        await app.started.wait()
        task.cancel()
        await app.restoring.wait()
        await reader.close_started.wait()
        for _ in range(4):
            task.cancel()
            await asyncio.sleep(0)
        self.assertEqual(app.cancellations, 0)
        self.assertEqual(reader.close_cancellations, 0)
        app.release_restore.set()
        await asyncio.sleep(0)
        for _ in range(4):
            task.cancel()
            await asyncio.sleep(0)
        reader.release.set()
        result = await task
        self.assertEqual(result.code, 130)
        self.assertTrue(reader.closed and app.restored and app.stopped)
        self.assertEqual(reader.close_cancellations, 0)

    async def test_ui_failure_still_joins_owned_reader(self):
        task, reader, app = self.launch(app=App(failure=RuntimeError("not disclosed")))
        result = await task
        self.assertEqual(result.code, 3)
        self.assertEqual(result.reason, "dashboard_RuntimeError")
        self.assertTrue(reader.closed and app.stopped)

    async def test_framework_error_code_is_an_internal_dashboard_failure(self):
        task, reader, app = self.launch()
        await app.started.wait()
        app.exit(return_code=1)
        result = await task
        self.assertEqual((result.code, result.reason), (3, "dashboard_exit_failed"))
        self.assertTrue(reader.closed and app.restored)

    async def test_cancelled_update_cleanup_does_not_skip_reader_or_output(self):
        task, reader, app = self.launch()

        async def stop():
            raise asyncio.CancelledError

        app.stop_updates = stop
        await app.started.wait()
        app.exit()
        result = await task
        self.assertEqual(result.code, 3)
        self.assertEqual(result.reason, "ui_cleanup_failed")
        self.assertTrue(reader.closed)

    async def test_output_failure_overrides_success_and_reports_flags_separately(self):
        task, reader, app = self.launch()
        joined = []

        async def wait():
            joined.append(True)
            return True

        app.output_driver = SimpleNamespace(
            wait_closed_async=wait,
            output_failure=SimpleNamespace(code="output_stalled"),
            terminal_flags_restored=True,
            terminal_restore_seconds=0.01,
            screen_reset_delivered=False,
        )
        await app.started.wait()
        app.exit()
        result = await task
        self.assertEqual((result.code, result.reason), (3, "output_stalled"))
        self.assertTrue(result.terminal_flags_restored)
        self.assertFalse(result.screen_reset_delivered)
        self.assertTrue(joined and reader.closed)

    async def test_output_reason_survives_simultaneous_cleanup_failure_and_interrupt(self):
        task, reader, app = self.launch(Reader(blocked=True))

        async def stop():
            raise RuntimeError("bounded UI cleanup fault")

        async def wait():
            return True

        app.stop_updates = stop
        app.output_driver = SimpleNamespace(
            wait_closed_async=wait,
            output_failure=SimpleNamespace(code="output_stalled"),
            terminal_flags_restored=True,
            terminal_restore_seconds=0.01,
            screen_reset_delivered=False,
        )
        await app.started.wait()
        app.exit(return_code=130)
        await reader.close_started.wait()
        task.cancel()
        reader.cleanup_error = "owned_reader_fault"
        reader.release.set()
        result = await task
        self.assertEqual((result.code, result.reason), (3, "output_stalled"))
        self.assertIn("ui_cleanup_failed", result.failures)
        self.assertIn("owned_reader_fault", result.failures)
        self.assertTrue(reader.closed and app.restored)

    async def test_signal_handlers_request_exit_and_restore_previous_handlers(self):
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signum=signum):
                callbacks = {}
                previous = signal.getsignal(signum)

                def register(sig, callback, *args, callbacks=callbacks):
                    callbacks[sig] = lambda: callback(*args)

                with (
                    patch.object(loop, "add_signal_handler", side_effect=register),
                    patch.object(loop, "remove_signal_handler") as remove,
                    patch("signal.signal") as restore,
                ):
                    task, reader, app = self.launch(install_signals=True)
                    await app.started.wait()
                    callbacks[signum]()
                    self.assertTrue(reader.requested)
                    result = await task
                    self.assertEqual(result.code, 128 + signum)
                    self.assertTrue(reader.closed and app.restored)
                    remove.assert_any_call(signum)
                    restore.assert_any_call(signum, previous)

    async def test_no_color_normalized_during_app_and_restored_after_cleanup(self):
        with patch.dict(os.environ, {"NO_COLOR": "old"}):
            task, reader, app = self.launch(no_color=True, icons=True, connect_timeout=17)
            await app.started.wait()
            self.assertEqual(os.environ["NO_COLOR"], "1")
            self.assertTrue(app.options["no_color"] and app.options["icons"])
            self.assertEqual(reader.options["connect_timeout"], 17)
            app.exit()
            self.assertEqual((await task).code, 0)
            self.assertEqual(os.environ["NO_COLOR"], "old")
