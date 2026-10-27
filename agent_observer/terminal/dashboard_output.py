"""Bounded, ordered terminal output for the standalone Linux dashboard.

Textual's Linux driver owns the terminal input and mode lifecycle. This module
replaces only its output path through the public ``App(driver_class=...)`` hook
and the driver's ``write``/lifecycle methods.
"""

from __future__ import annotations

import asyncio
import math
import os
import select
import signal
import sys
import termios
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from textual.app import App
from textual.drivers.linux_driver import LinuxDriver

DEFAULT_PENDING_LIMIT_BYTES = 512 * 1024
DEFAULT_STALL_TIMEOUT_SECONDS = 2.0
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 3.0
_OUTPUT_WRITE_CHUNK_BYTES = 16 * 1024
_ERROR_MESSAGE_LIMIT = 160


@dataclass(frozen=True)
class OutputFailure:
    """A bounded, actionable terminal output failure for the outer runner."""

    code: str
    message: str
    exit_code: int = 3


class BoundedOutputPump:
    """Write UTF-8 output in order with a fixed pending-byte budget.

    The output descriptor is opened independently through procfs so setting
    ``O_NONBLOCK`` cannot change status flags on the inherited descriptor's
    shared open-file description. Producers only encode and copy into a fixed
    ring buffer; the owned writer thread performs nonblocking writes.
    """

    def __init__(
        self,
        output_fd: int,
        *,
        pending_limit_bytes: int = DEFAULT_PENDING_LIMIT_BYTES,
        stall_timeout_seconds: float = DEFAULT_STALL_TIMEOUT_SECONDS,
        shutdown_timeout_seconds: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
        require_terminal: bool = False,
        input_fd: int | None = None,
        on_failure: Callable[[OutputFailure], None] | None = None,
    ) -> None:
        if pending_limit_bytes <= 0:
            raise ValueError("pending_limit_bytes must be positive")
        if stall_timeout_seconds <= 0:
            raise ValueError("stall_timeout_seconds must be positive")
        if shutdown_timeout_seconds <= 0:
            raise ValueError("shutdown_timeout_seconds must be positive")

        self._output_fd = output_fd
        self._capacity = pending_limit_bytes
        self._stall_timeout = stall_timeout_seconds
        self._shutdown_timeout = shutdown_timeout_seconds
        self._require_terminal = require_terminal
        self._input_fd = input_fd
        self._on_failure = on_failure

        self._buffer = bytearray(pending_limit_bytes)
        self._head = 0
        self._tail = 0
        self._pending_bytes = 0
        self._high_watermark_bytes = 0
        self._lock = threading.Lock()
        self._wake_read_fd: int | None = None
        self._wake_write_fd: int | None = None
        self._owned_output_fd: int | None = None
        self._owned_fd_numbers: tuple[int, ...] = ()
        self._thread: threading.Thread | None = None
        self._started = False
        self._closing = False
        self._close_deadline: float | None = None
        self._last_progress_at: float | None = None
        self._watchdog_suspended = False
        self._failure: OutputFailure | None = None
        self._failure_no_progress_seconds: float | None = None
        self._closed = threading.Event()
        self._screen_reset_attempted = False
        self._screen_reset_pending_bytes: int | None = None
        self._screen_reset_delivered: bool | None = None

    @property
    def failure(self) -> OutputFailure | None:
        with self._lock:
            return self._failure

    @property
    def failure_no_progress_seconds(self) -> float | None:
        with self._lock:
            return self._failure_no_progress_seconds

    @property
    def pending_bytes(self) -> int:
        with self._lock:
            return self._pending_bytes

    @property
    def high_watermark_bytes(self) -> int:
        with self._lock:
            return self._high_watermark_bytes

    @property
    def screen_reset_delivered(self) -> bool | None:
        with self._lock:
            return self._screen_reset_delivered

    @property
    def owned_fd_numbers(self) -> tuple[int, ...]:
        """Return the descriptors owned by the pump, for lifecycle inspection."""

        with self._lock:
            return self._owned_fd_numbers

    @property
    def thread_alive(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def start(self) -> bool:
        """Open owned resources and start the nonblocking output pump once."""

        with self._lock:
            if self._started:
                return self._failure is None and not self._closing and not self._closed.is_set()
            if self._closing:
                return False
            self._started = True

        if self._require_terminal and not os.isatty(self._output_fd):
            self._fail(
                "output_not_terminal",
                "dashboard output requires a terminal on stderr",
                close_without_thread=True,
            )
            return False
        if self._require_terminal and self._input_fd is not None:
            if not os.isatty(self._input_fd):
                self._fail(
                    "input_not_terminal",
                    "dashboard input requires a terminal on stdin",
                    close_without_thread=True,
                )
                return False
            try:
                input_device = os.fstat(self._input_fd).st_rdev
                output_device = os.fstat(self._output_fd).st_rdev
            except OSError as error:
                self._fail(
                    "terminal_check",
                    f"could not verify the dashboard terminal (errno {error.errno})",
                    close_without_thread=True,
                )
                return False
            if input_device != output_device:
                self._fail(
                    "terminal_mismatch",
                    "dashboard input and stderr must use the same terminal",
                    close_without_thread=True,
                )
                return False

        output_fd: int | None = None
        wake_read_fd: int | None = None
        wake_write_fd: int | None = None
        try:
            flags = os.O_WRONLY | os.O_NONBLOCK | os.O_CLOEXEC
            flags |= getattr(os, "O_NOCTTY", 0)
            output_fd = os.open(f"/proc/self/fd/{self._output_fd}", flags)
            wake_read_fd, wake_write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError as error:
            for fd in (wake_read_fd, wake_write_fd, output_fd):
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            self._fail(
                "output_setup",
                f"could not open owned terminal output (errno {error.errno})",
                close_without_thread=True,
            )
            return False

        with self._lock:
            self._owned_output_fd = output_fd
            self._wake_read_fd = wake_read_fd
            self._wake_write_fd = wake_write_fd
            self._owned_fd_numbers = (output_fd, wake_read_fd, wake_write_fd)
            self._thread = threading.Thread(
                target=self._run,
                name="agent-observer-dashboard-output",
                daemon=True,
            )
            thread = self._thread

        try:
            thread.start()
        except RuntimeError as error:
            self._close_owned_fds()
            self._fail(
                "output_setup",
                f"could not start terminal output worker ({type(error).__name__})",
                close_without_thread=True,
            )
            return False
        return True

    def write(self, text: str, *, screen_reset: bool = False) -> bool:
        """Accept one complete encoded write without waiting for the sink."""

        if len(text) > self._capacity:
            self._fail(
                "output_capacity",
                f"terminal output write exceeded the {self._capacity}-byte pending limit",
            )
            return False
        try:
            data = text.encode("utf-8")
        except UnicodeEncodeError:
            self._fail("output_encoding", "terminal output was not valid UTF-8")
            return False
        if not data:
            return True

        code: str | None = None
        message = ""
        with self._lock:
            if screen_reset:
                self._screen_reset_attempted = True
                if self._screen_reset_delivered is None:
                    self._screen_reset_delivered = False

            if self._failure is not None:
                return False
            if not self._started or self._closing or self._closed.is_set():
                code = "output_closed"
                message = "terminal output write arrived outside the driver lifecycle"
            elif len(data) > self._capacity:
                code = "output_capacity"
                message = f"terminal output write exceeded the {self._capacity}-byte pending limit"
            elif len(data) > self._capacity - self._pending_bytes:
                code = "output_capacity"
                message = f"terminal output pending data exceeded the {self._capacity}-byte limit"
            else:
                if self._pending_bytes == 0:
                    self._last_progress_at = time.monotonic()
                self._append_locked(data)
                self._pending_bytes += len(data)
                self._high_watermark_bytes = max(self._high_watermark_bytes, self._pending_bytes)
                if screen_reset:
                    # The marker is reported delivered only after every byte
                    # queued before and within this write reaches the fd.
                    self._screen_reset_pending_bytes = self._pending_bytes

        if code is not None:
            self._fail(code, message)
            return False
        self._wake()
        return True

    def _append_locked(self, data: bytes) -> None:
        first = min(len(data), self._capacity - self._tail)
        self._buffer[self._tail : self._tail + first] = data[:first]
        second = len(data) - first
        if second:
            self._buffer[:second] = data[first:]
        self._tail = (self._tail + len(data)) % self._capacity

    def _consume_locked(self, count: int) -> None:
        self._head = (self._head + count) % self._capacity
        self._pending_bytes -= count
        if self._pending_bytes == 0:
            self._head = self._tail = 0
            self._last_progress_at = None

        if self._screen_reset_pending_bytes is not None:
            self._screen_reset_pending_bytes -= count
            if self._screen_reset_pending_bytes <= 0:
                self._screen_reset_pending_bytes = None
                self._screen_reset_delivered = True

    def suspend_progress_clock(self) -> None:
        """Keep draining, without counting an intentional process suspension."""
        with self._lock:
            self._watchdog_suspended = True
        self._wake()

    def resume_progress_clock(self) -> None:
        """Resume the drain watchdog after the process could not make progress."""
        with self._lock:
            self._watchdog_suspended = False
            if self._failure is None and not self._closing and self._pending_bytes:
                self._last_progress_at = time.monotonic()
        self._wake()

    def close(self) -> None:
        """Request a bounded drain and return without joining the worker."""

        with self._lock:
            if self._closed.is_set() or self._closing:
                return
            self._closing = True
            self._close_deadline = time.monotonic() + self._shutdown_timeout
            no_thread = self._thread is None
        if no_thread:
            self._close_owned_fds()
            self._closed.set()
        else:
            self._wake()

    def wait_closed(self, timeout: float | None = None) -> bool:
        """Join after ``close`` with a finite bound; return whether it stopped."""

        self.close()
        wait_seconds = self._shutdown_timeout + 0.5 if timeout is None else max(0.0, timeout)
        finished = self._closed.wait(wait_seconds)
        thread = self._thread
        if not finished:
            self._fail(
                "output_cleanup",
                "terminal output worker exceeded its bounded shutdown window",
            )
            self._wake()
            finished = self._closed.wait(0.25)
        if thread is not None:
            thread.join(timeout=0.05)
            finished = finished and not thread.is_alive()
        return finished

    async def wait_closed_async(self, timeout: float | None = None) -> bool:
        """Async wrapper for the finite output worker join."""

        return await asyncio.to_thread(self.wait_closed, timeout)

    def _wake(self) -> None:
        # Keep the descriptor pinned until this nonblocking byte write ends;
        # close detaches and closes it under the same lock.
        with self._lock:
            fd = self._wake_write_fd
            if fd is None:
                return
            try:
                os.write(fd, b"\0")
            except (BlockingIOError, OSError):
                # A full wake pipe already has a byte for the worker to consume.
                pass

    def _drain_wake_pipe(self) -> None:
        fd = self._wake_read_fd
        if fd is None:
            return
        while True:
            try:
                if not os.read(fd, 4096):
                    return
            except BlockingIOError:
                return
            except OSError:
                return

    def _fail(
        self,
        code: str,
        message: str,
        *,
        close_without_thread: bool = False,
        no_progress_seconds: float | None = None,
    ) -> None:
        callback: Callable[[OutputFailure], None] | None = None
        failure: OutputFailure | None = None
        with self._lock:
            if self._failure is None:
                failure = OutputFailure(code, message[:_ERROR_MESSAGE_LIMIT])
                self._failure = failure
                self._failure_no_progress_seconds = no_progress_seconds
                callback = self._on_failure
                # Keep already accepted bytes and offsets for the outer
                # runner's failure report. No later write is accepted after
                # failure, so the stranded data remains within the same cap.
                self._screen_reset_pending_bytes = None
                if self._screen_reset_attempted:
                    self._screen_reset_delivered = False
                self._closing = True
                if self._close_deadline is None:
                    self._close_deadline = time.monotonic()
            no_thread = self._thread is None or close_without_thread

        if no_thread:
            self._close_owned_fds()
            self._closed.set()
        else:
            self._wake()
        if failure is not None and callback is not None:
            try:
                callback(failure)
            except Exception:
                # The failure remains visible to the outer runner even if the
                # application loop is already closing.
                pass

    def _failure_from_os_error(self, code: str, error: OSError) -> None:
        self._fail(code, f"terminal output failed (errno {error.errno})")

    def _poll_timeout_ms(self) -> int:
        with self._lock:
            now = time.monotonic()
            deadlines: list[float] = []
            if (
                self._pending_bytes
                and self._last_progress_at is not None
                and not self._watchdog_suspended
            ):
                deadlines.append(self._last_progress_at + self._stall_timeout)
            if self._closing and self._close_deadline is not None:
                deadlines.append(self._close_deadline)
        if not deadlines:
            return -1
        remaining = max(0.0, min(deadlines) - now)
        return max(1, math.ceil(remaining * 1000))

    def _run(self) -> None:
        output_fd = self._owned_output_fd
        wake_read_fd = self._wake_read_fd
        poller: select.poll | None = None
        output_registered = False
        try:
            if output_fd is None or wake_read_fd is None:
                raise RuntimeError("terminal output worker started without fds")
            poller = select.poll()
            poller.register(
                wake_read_fd,
                select.POLLIN | select.POLLERR | select.POLLHUP,
            )
            while True:
                error: OSError | None = None
                should_exit = False
                no_progress_seconds: float | None = None
                code = ""
                message = ""
                with self._lock:
                    if self._failure is not None:
                        should_exit = True
                    elif self._closing and self._pending_bytes == 0:
                        should_exit = True
                    elif self._pending_bytes:
                        now = time.monotonic()
                        if (
                            self._last_progress_at is not None
                            and not self._watchdog_suspended
                            and now - self._last_progress_at >= self._stall_timeout
                        ):
                            no_progress_seconds = now - self._last_progress_at
                            code = "output_stalled"
                            message = (
                                "terminal output made no drain progress for "
                                f"{self._stall_timeout:g} seconds"
                            )
                        elif (
                            self._closing
                            and self._close_deadline is not None
                            and now >= self._close_deadline
                        ):
                            code = "output_cleanup"
                            message = "terminal output did not drain before shutdown deadline"
                        else:
                            code = ""
                            message = ""
                            contiguous = min(
                                self._pending_bytes,
                                self._capacity - self._head,
                                _OUTPUT_WRITE_CHUNK_BYTES,
                            )
                            view = memoryview(self._buffer)[self._head : self._head + contiguous]
                            try:
                                written = os.write(output_fd, view)
                            except BlockingIOError:
                                pass
                            except InterruptedError:
                                pass
                            except OSError as write_error:
                                error = write_error
                            else:
                                if written <= 0:
                                    code = "output_write"
                                    message = "terminal output write made no progress"
                                else:
                                    self._consume_locked(written)
                                    self._last_progress_at = time.monotonic()
                        if code:
                            # The lock is released before callbacks or wakeups.
                            pass
                    else:
                        code = ""
                        message = ""

                    pending = self._pending_bytes > 0 and self._failure is None
                    if should_exit:
                        code = ""
                        message = ""

                if error is not None:
                    self._failure_from_os_error("output_write", error)
                    continue
                if code:
                    self._fail(
                        code,
                        message,
                        no_progress_seconds=no_progress_seconds,
                    )
                    continue
                if should_exit:
                    break
                if not pending:
                    if output_registered:
                        try:
                            assert poller is not None
                            poller.unregister(output_fd)
                        except KeyError:
                            pass
                        output_registered = False
                elif not output_registered:
                    assert poller is not None
                    poller.register(
                        output_fd,
                        select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL,
                    )
                    output_registered = True

                try:
                    assert poller is not None
                    events = poller.poll(self._poll_timeout_ms())
                except OSError as poll_error:
                    self._failure_from_os_error("output_poll", poll_error)
                    continue

                for fd, event in events:
                    if fd == wake_read_fd:
                        self._drain_wake_pipe()
                    elif fd == output_fd and event & (
                        select.POLLERR | select.POLLHUP | select.POLLNVAL
                    ):
                        self._fail(
                            "output_closed",
                            "terminal output peer closed or became unavailable",
                        )
                        break
        except BaseException as error:
            self._fail(
                "output_worker",
                f"terminal output worker failed ({type(error).__name__})",
            )
        finally:
            self._close_owned_fds()
            self._closed.set()

    def _close_owned_fds(self) -> None:
        with self._lock:
            fds = (
                self._owned_output_fd,
                self._wake_read_fd,
                self._wake_write_fd,
            )
            self._owned_output_fd = None
            self._wake_read_fd = None
            self._wake_write_fd = None
        for fd in fds:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass


class BoundedLinuxDriver(LinuxDriver):
    """Textual Linux driver with a separate bounded terminal output pump."""

    pending_limit_bytes = DEFAULT_PENDING_LIMIT_BYTES
    stall_timeout_seconds = DEFAULT_STALL_TIMEOUT_SECONDS
    shutdown_timeout_seconds = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS
    require_terminal_output = True

    def __init__(
        self,
        app: App,
        *,
        debug: bool = False,
        mouse: bool = True,
        size: tuple[int, int] | None = None,
    ) -> None:
        self._original_job_handlers = {
            signum: signal.getsignal(signum) for signum in (signal.SIGTSTP, signal.SIGCONT)
        }
        super().__init__(app, debug=debug, mouse=mouse, size=size)
        self._owner_app = app
        self._owner_loop: asyncio.AbstractEventLoop | None = None
        self._initial_termios: list[object] | None = None
        self._termios_captured = False
        self._application_mode_active = False
        self._job_handlers_installed = False
        self._suspend_poll_handle: asyncio.TimerHandle | None = None
        self._suspend_deadline: float | None = None
        self.terminal_flags_restored: bool | None = None
        self.terminal_restore_seconds: float | None = None
        self.terminal_stop_started_at: float | None = None
        self._driver_close_requested = False
        try:
            output_fd = sys.__stderr__.fileno()
        except (AttributeError, OSError):
            output_fd = -1
        self.output = BoundedOutputPump(
            output_fd,
            pending_limit_bytes=self.pending_limit_bytes,
            stall_timeout_seconds=self.stall_timeout_seconds,
            shutdown_timeout_seconds=self.shutdown_timeout_seconds,
            require_terminal=self.require_terminal_output,
            input_fd=self.fileno,
            on_failure=self._output_failed,
        )
        # The outer runner awaits this owned handle after App.run_async has
        # restored terminal mode and started its other cleanup joins.
        app.output_driver = self

    @property
    def output_failure(self) -> OutputFailure | None:
        return self.output.failure

    @property
    def output_exit_code(self) -> int:
        failure = self.output_failure
        return failure.exit_code if failure is not None else 0

    @property
    def screen_reset_delivered(self) -> bool | None:
        return self.output.screen_reset_delivered

    def _output_failed(self, _failure: OutputFailure) -> None:
        loop = self._owner_loop
        if loop is None or loop.is_closed():
            return
        try:
            # This schedules App.exit without synchronously waiting for the UI
            # loop, so output failure cannot deadlock shutdown.
            loop.call_soon_threadsafe(lambda: self._owner_app.exit(return_code=3))
        except RuntimeError:
            pass

    def start_application_mode(self) -> None:
        self._owner_loop = asyncio.get_running_loop()
        if not self._job_handlers_installed:
            # Python's synchronous signal handlers may interrupt a pump write
            # while its lock is held. Run all mode/queue work on the event loop.
            self._job_handlers_installed = True
            self._owner_loop.add_signal_handler(signal.SIGTSTP, self._suspend_process)
            self._owner_loop.add_signal_handler(signal.SIGCONT, self.resume_application_mode)
        if not self._termios_captured:
            self._termios_captured = True
            try:
                self._initial_termios = termios.tcgetattr(self.fileno)
            except termios.error:
                self._initial_termios = None
        if not self.output.start():
            self._output_failed(
                self.output_failure or OutputFailure("output_setup", "terminal output setup failed")
            )
            return
        # LinuxDriver retains its keyboard parser/thread, resize signal and
        # terminal mode behavior. Its calls to self.write dispatch below.
        super().start_application_mode()
        self._application_mode_active = True

    def _suspend_process(self) -> None:
        if self._driver_close_requested or self._suspend_deadline is not None:
            return
        started = time.monotonic()
        self.suspend_application_mode()
        self._suspend_deadline = started + 2.0
        self._finish_process_suspend()

    def _finish_process_suspend(self) -> None:
        self._suspend_poll_handle = None
        if self._driver_close_requested or self._suspend_deadline is None:
            return
        if self.output_failure is not None:
            self._cancel_process_suspend()
            return
        if self.output.pending_bytes == 0 and self.screen_reset_delivered is True:
            self._cancel_process_suspend()
            self.output.suspend_progress_clock()
            os.kill(os.getpid(), signal.SIGSTOP)
        elif time.monotonic() >= self._suspend_deadline:
            self._cancel_process_suspend()
            self.output._fail(
                "output_suspend", "terminal reset did not drain before the suspension deadline"
            )
        else:
            self._suspend_poll_handle = self._owner_loop.call_later(
                0.01, self._finish_process_suspend
            )

    def _cancel_process_suspend(self) -> None:
        if self._suspend_poll_handle is not None:
            self._suspend_poll_handle.cancel()
            self._suspend_poll_handle = None
        self._suspend_deadline = None

    def suspend_application_mode(self) -> None:
        if self._application_mode_active:
            self.stop_application_mode()
            # The inherited writer is idle; the owned FIFO stays open across
            # suspension, including its ordered terminal reset/start sequences.
            super().close()

    def resume_application_mode(self) -> None:
        if self._driver_close_requested:
            return
        self._cancel_process_suspend()
        if not self._application_mode_active:
            self.output.resume_progress_clock()
            self.start_application_mode()
        # A raw SIGSTOP skips suspend_application_mode. Retain the original
        # input/writer threads and saved terminal flags in that case.
        self._owner_app.post_message(self.SignalResume())

    def write(self, data: str) -> None:
        if self._suspend_deadline is not None:
            # The terminal reset is already queued. The latest model is fully
            # repainted on resume; cosmetic frames must not follow that reset.
            return
        self.output.write(data, screen_reset="\x1b[?1049l" in data)

    def flush(self) -> None:
        # Output is drained asynchronously in FIFO order; waiting here would
        # put sink backpressure back on Textual's event loop.
        return

    def stop_application_mode(self) -> None:
        self._cancel_process_suspend()
        self.terminal_stop_started_at = time.monotonic()
        try:
            super().stop_application_mode()
        finally:
            self._application_mode_active = False
            if self._initial_termios is not None:
                try:
                    termios.tcsetattr(self.fileno, termios.TCSANOW, self._initial_termios)
                    self.terminal_flags_restored = (
                        termios.tcgetattr(self.fileno) == self._initial_termios
                    )
                except termios.error:
                    self.terminal_flags_restored = False
            self.terminal_restore_seconds = time.monotonic() - self.terminal_stop_started_at

    def close(self) -> None:
        if self._driver_close_requested:
            return
        self._driver_close_requested = True
        self._cancel_process_suspend()
        try:
            # The inherited writer is idle because this class overrides write;
            # stopping it releases Textual's own startup resource.
            super().close()
        finally:
            self.output.close()
            if self._job_handlers_installed and self._owner_loop is not None:
                for signum, handler in self._original_job_handlers.items():
                    self._owner_loop.remove_signal_handler(signum)
                    signal.signal(signum, handler)
                self._job_handlers_installed = False

    def wait_closed(self, timeout: float | None = None) -> bool:
        return self.output.wait_closed(timeout)

    async def wait_closed_async(self, timeout: float | None = None) -> bool:
        return await self.output.wait_closed_async(timeout)


__all__ = [
    "BoundedLinuxDriver",
    "BoundedOutputPump",
    "DEFAULT_PENDING_LIMIT_BYTES",
    "DEFAULT_SHUTDOWN_TIMEOUT_SECONDS",
    "DEFAULT_STALL_TIMEOUT_SECONDS",
    "OutputFailure",
]
