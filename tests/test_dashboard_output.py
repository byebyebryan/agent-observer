"""Real-PTY checks for the bounded Textual Linux output adapter."""

from __future__ import annotations

import errno
import fcntl
import importlib.util
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None

if TEXTUAL_AVAILABLE:
    from agent_observer.terminal.dashboard_output import BoundedOutputPump


_CHILD = textwrap.dedent(
    r"""
    import asyncio
    import fcntl
    import json
    import os
    import signal
    import sys
    import termios
    import threading

    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import Static

    from agent_observer.terminal.dashboard_output import BoundedLinuxDriver

    case = os.environ["AO_CASE"]
    control_fd = int(os.environ["AO_CONTROL_FD"])

    # Popen starts an isolated session; acquire the passed slave as its
    # controlling terminal so the normal SIGWINCH path is exercised.
    try:
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        os.tcsetpgrp(0, os.getpgrp())
    except OSError:
        pass

    class ProbeDriver(BoundedLinuxDriver):
        if case == "fast_stall":
            stall_timeout_seconds = 0.35
            shutdown_timeout_seconds = 0.6

    class Probe(App):
        BINDINGS = [Binding("q", "quit", "Quit")]
        CSS = "Screen { color: red; } Static { color: red; }"

        def __init__(self):
            no_color = bool(os.environ.get("NO_COLOR"))
            super().__init__(
                driver_class=ProbeDriver,
                ansi_color=True if no_color else None,
            )
            self.tick_count = 0
            self.last_size = None
            self.scheduled_quit = False
            self.quit_by_key = False

        def compose(self) -> ComposeResult:
            yield Static("Dashboard output probe", id="status")

        def on_mount(self):
            if case == "ui":
                self.set_timer(30, self.exit)
            elif case in {"resume", "resume_pending"}:
                if case == "resume_pending":
                    self.output_driver.write("P" * 100_000)
                self.set_interval(0.05, self.tick)
                self.set_timer(30, self.exit)
            elif case == "stall":
                self.output_driver.write("X" * 100_000)
                self.set_interval(0.25, self.tick)
                self.set_timer(1.0, self.scheduled_exit)
            elif case == "capacity":
                self.output_driver.write("A" * (512 * 1024))
                self.output_driver.write("B" * (512 * 1024))
                self.set_interval(0.05, self.tick)
                self.set_timer(30, self.exit)
            elif case == "payload":
                payload = "AΩ🛰Z" * 60_000
                self.output_driver.write("PAYLOAD_BEGIN" + payload + "PAYLOAD_END")
                self.set_timer(2.0, self.exit)
            elif case == "signal":
                asyncio.get_running_loop().add_signal_handler(
                    signal.SIGTERM,
                    lambda: self.exit(return_code=143),
                )
                self.set_timer(30, self.exit)
            elif case == "fast_stall":
                self.output_driver.write("Z" * 100_000)
                self.set_interval(0.05, self.tick)
                self.set_timer(30, self.exit)

        def on_resize(self, event):
            self.last_size = [event.size.width, event.size.height]

        def tick(self):
            self.tick_count += 1
            self.query_one("#status", Static).update(f"ticks {self.tick_count}")

        def scheduled_exit(self):
            self.scheduled_quit = True
            self.exit()

        def action_quit(self):
            self.quit_by_key = True
            self.exit()

    def fd_open(fd):
        try:
            os.fstat(fd)
        except OSError:
            return False
        return True

    async def main():
        original_job_handlers = {
            signum: signal.getsignal(signum) for signum in (signal.SIGTSTP, signal.SIGCONT)
        }
        app = Probe()
        await app.run_async()
        driver = app.output_driver
        wait_closed = await driver.wait_closed_async()
        driver.close()
        driver.close()
        idempotent_close = await driver.wait_closed_async()
        failure = driver.output_failure
        owned_fds = driver.output.owned_fd_numbers
        status = {
            "app_return_code": app.return_code,
            "process_code": driver.output_exit_code or app.return_code or 0,
            "failure": None
            if failure is None
            else {"code": failure.code, "message": failure.message},
            "failure_no_progress_seconds": driver.output.failure_no_progress_seconds,
            "pending_bytes": driver.output.pending_bytes,
            "high_watermark_bytes": driver.output.high_watermark_bytes,
            "screen_reset_delivered": driver.screen_reset_delivered,
            "terminal_flags_restored": driver.terminal_flags_restored,
            "terminal_restore_seconds": driver.terminal_restore_seconds,
            "job_handlers_restored": all(
                signal.getsignal(signum) == handler
                for signum, handler in original_job_handlers.items()
            ),
            "tick_count": app.tick_count,
            "last_size": app.last_size,
            "scheduled_quit": app.scheduled_quit,
            "quit_by_key": app.quit_by_key,
            "wait_closed": wait_closed,
            "idempotent_close": idempotent_close,
            "worker_alive": driver.output.thread_alive,
            "owned_fds": list(owned_fds),
            "owned_fds_closed": all(not fd_open(fd) for fd in owned_fds),
            "textual_threads_alive": [
                thread.name
                for thread in threading.enumerate()
                if thread.is_alive()
                and (thread.name.startswith("textual-")
                     or thread.name.startswith("agent-observer-dashboard-output"))
            ],
        }
        os.write(control_fd, json.dumps(status, separators=(",", ":")).encode() + b"\n")
        os.close(control_fd)
        return status["process_code"]

    sys.exit(asyncio.run(main()))
    """
)

_SGR = re.compile(rb"\x1b\[([0-9;:]*)m")


def _has_color(data: bytes) -> bool:
    color_codes = set(range(30, 38)) | set(range(40, 48))
    color_codes |= set(range(90, 98)) | set(range(100, 108)) | {38, 48, 58}
    for match in _SGR.finditer(data):
        codes = [int(value) for value in re.split(rb"[;:]", match.group(1)) if value]
        if color_codes.intersection(codes):
            return True
    return False


class _PTYProbe:
    def __init__(self, case: str, *, no_color: bool = False, stderr_pipe: bool = False):
        self.master_fd, self.slave_fd = pty.openpty()
        fcntl.ioctl(
            self.master_fd,
            termios.TIOCSWINSZ,
            struct.pack("HHHH", 24, 80, 0, 0),
        )
        self.original_termios = termios.tcgetattr(self.slave_fd)
        self.original_fd_flags = fcntl.fcntl(self.slave_fd, fcntl.F_GETFL)
        self.control_read_fd, control_write_fd = os.pipe()
        self.stderr_read_fd = None
        self.stderr_write_fd = None
        if stderr_pipe:
            self.stderr_read_fd, self.stderr_write_fd = os.pipe()

        env = dict(os.environ)
        env.update(
            {
                "AO_CASE": case,
                "AO_CONTROL_FD": str(control_write_fd),
                "TERM": "xterm-256color",
            }
        )
        env.pop("COLUMNS", None)
        env.pop("LINES", None)
        if no_color:
            env["NO_COLOR"] = "1"
        else:
            env.pop("NO_COLOR", None)

        self.process = subprocess.Popen(
            [sys.executable, "-c", _CHILD],
            cwd=ROOT,
            env=env,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.stderr_write_fd if stderr_pipe else self.slave_fd,
            pass_fds=(control_write_fd,),
            start_new_session=True,
            close_fds=True,
        )
        os.close(control_write_fd)
        if self.stderr_write_fd is not None:
            os.close(self.stderr_write_fd)
            self.stderr_write_fd = None
        os.set_blocking(self.master_fd, False)
        os.set_blocking(self.control_read_fd, False)
        self.output = bytearray()
        self.control = bytearray()
        self.status: dict[str, object] | None = None
        self._closed = False

    def _read_fd(self, fd: int, destination: bytearray) -> None:
        while True:
            try:
                data = os.read(fd, 65_536)
            except BlockingIOError:
                return
            except OSError as error:
                if error.errno in {errno.EIO, errno.EBADF}:
                    return
                raise
            if not data:
                return
            destination.extend(data)

    def poll(self, *, drain_output: bool = True) -> None:
        readers = [self.control_read_fd]
        if drain_output:
            readers.append(self.master_fd)
        ready, _, _ = select.select(readers, [], [], 0)
        if self.control_read_fd in ready:
            self._read_fd(self.control_read_fd, self.control)
            if b"\n" in self.control:
                self.status = json.loads(self.control.split(b"\n", 1)[0])
        if drain_output and self.master_fd in ready:
            self._read_fd(self.master_fd, self.output)

    def wait_for_raw_mode(self, timeout: float = 2.0, *, drain_output: bool = True) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if termios.tcgetattr(self.slave_fd) != self.original_termios:
                    return True
            except termios.error:
                return False
            self.poll(drain_output=drain_output)
            time.sleep(0.01)
        return False

    def wait_for_output(self, marker: bytes, timeout: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.poll()
            if marker in self.output:
                return True
            select.select([self.master_fd, self.control_read_fd], [], [], 0.02)
        return marker in self.output

    def wait_for_exit(
        self, timeout: float = 8.0, *, drain_output: bool = True
    ) -> dict[str, object]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.poll(drain_output=drain_output)
            if self.process.poll() is not None and self.status is not None:
                break
            readers = [self.control_read_fd]
            if drain_output:
                readers.append(self.master_fd)
            select.select(readers, [], [], 0.02)
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=2)
            raise AssertionError("PTY probe did not exit within its bound")
        self.poll(drain_output=drain_output)
        if self.status is None:
            raise AssertionError("PTY probe exited without its status receipt")
        if drain_output:
            self.poll(drain_output=True)
        return self.status

    def current_termios(self):
        try:
            return termios.tcgetattr(self.slave_fd)
        except termios.error:
            return None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=2)
        for fd in (
            self.master_fd,
            self.slave_fd,
            self.control_read_fd,
            self.stderr_read_fd,
        ):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass


@unittest.skipUnless(
    sys.platform.startswith("linux") and TEXTUAL_AVAILABLE, "Linux Textual is optional"
)
class DashboardOutputPTYTests(unittest.TestCase):
    def test_job_control_and_raw_stop_resume_keep_output_and_restore_terminal(self):
        for stop_signal, case in (
            (signal.SIGTSTP, "resume"),
            (signal.SIGSTOP, "resume"),
            (signal.SIGTSTP, "resume_pending"),
        ):
            with self.subTest(stop_signal=stop_signal, case=case):
                probe = _PTYProbe(case)
                try:
                    self.assertTrue(probe.wait_for_raw_mode(drain_output=case != "resume_pending"))
                    if case == "resume_pending":
                        time.sleep(0.2)
                    else:
                        self.assertTrue(probe.wait_for_output(b"ticks"))
                    for _ in range(2):
                        probe.process.send_signal(stop_signal)
                        deadline = time.monotonic() + 2
                        while time.monotonic() < deadline:
                            state = Path(f"/proc/{probe.process.pid}/stat").read_text().rsplit(") ", 1)[1].split()[0]
                            if state == "T":
                                break
                            probe.poll()
                            time.sleep(0.01)
                        self.assertEqual(state, "T", "owned probe did not stop")
                        if stop_signal == signal.SIGTSTP:
                            probe.poll()
                            self.assertEqual(probe.current_termios(), probe.original_termios)
                            self.assertGreater(
                                probe.output.rfind(b"\x1b[?1049l"),
                                probe.output.rfind(b"\x1b[?1049h"),
                                "alt screen reset must drain before the kernel stop",
                            )
                        # Exceed the active-output watchdog while the process
                        # has no opportunity to drain its owned queue.
                        end = time.monotonic() + 2.2
                        while time.monotonic() < end:
                            probe.poll()
                            time.sleep(0.02)
                        previous_bytes = len(probe.output)
                        probe.process.send_signal(signal.SIGCONT)
                        deadline = time.monotonic() + 2
                        while time.monotonic() < deadline:
                            probe.poll()
                            if len(probe.output) > previous_bytes + 50:
                                break
                            self.assertIsNone(probe.process.poll(), "resume ended the dashboard")
                            time.sleep(0.02)
                        self.assertGreater(len(probe.output), previous_bytes + 50)
                        self.assertTrue(probe.wait_for_raw_mode())
                    os.write(probe.master_fd, b"q")
                    status = probe.wait_for_exit()
                    self.assertEqual(status["process_code"], 0)
                    self.assertTrue(status["quit_by_key"])
                    self.assertIsNone(status["failure"])
                    self.assertTrue(status["terminal_flags_restored"])
                    self.assertTrue(status["job_handlers_restored"])
                    self.assertTrue(status["screen_reset_delivered"])
                    self.assertTrue(status["owned_fds_closed"])
                    self.assertFalse(status["worker_alive"])
                    self.assertEqual(status["textual_threads_alive"], [])
                    self.assertEqual(probe.current_termios(), probe.original_termios)
                finally:
                    if probe.process.poll() is None:
                        probe.process.send_signal(signal.SIGCONT)
                    probe.close()

    def test_job_control_with_undrained_output_fails_without_stopping_process(self):
        probe = _PTYProbe("resume_pending")
        try:
            self.assertTrue(probe.wait_for_raw_mode(drain_output=False))
            time.sleep(0.2)
            probe.process.send_signal(signal.SIGTSTP)
            status = probe.wait_for_exit(timeout=6, drain_output=False)
            self.assertEqual(status["process_code"], 3)
            self.assertIn(status["failure"]["code"], {"output_suspend", "output_stalled"})
            self.assertTrue(status["terminal_flags_restored"])
            self.assertFalse(status["screen_reset_delivered"])
            self.assertTrue(status["job_handlers_restored"])
            self.assertTrue(status["owned_fds_closed"])
            self.assertFalse(status["worker_alive"])
            self.assertEqual(status["textual_threads_alive"], [])
            self.assertEqual(probe.current_termios(), probe.original_termios)
        finally:
            if probe.process.poll() is None:
                probe.process.send_signal(signal.SIGCONT)
            probe.close()

    def test_pty_input_resize_color_and_no_color_restore_terminal(self):
        for no_color in (False, True):
            with self.subTest(no_color=no_color):
                probe = _PTYProbe("ui", no_color=no_color)
                try:
                    self.assertTrue(probe.wait_for_raw_mode())
                    fcntl.ioctl(
                        probe.master_fd,
                        termios.TIOCSWINSZ,
                        struct.pack("HHHH", 30, 100, 0, 0),
                    )
                    time.sleep(0.2)
                    probe.poll()
                    os.write(probe.master_fd, b"q")
                    status = probe.wait_for_exit()

                    self.assertEqual(status["process_code"], 0)
                    self.assertTrue(status["quit_by_key"])
                    self.assertEqual(status["last_size"], [100, 30])
                    self.assertTrue(status["terminal_flags_restored"])
                    self.assertTrue(status["screen_reset_delivered"])
                    self.assertTrue(status["wait_closed"])
                    self.assertTrue(status["idempotent_close"])
                    self.assertFalse(status["worker_alive"])
                    self.assertTrue(status["owned_fds_closed"])
                    self.assertEqual(status["textual_threads_alive"], [])
                    self.assertEqual(
                        fcntl.fcntl(probe.slave_fd, fcntl.F_GETFL),
                        probe.original_fd_flags,
                    )
                    self.assertEqual(probe.current_termios(), probe.original_termios)
                    self.assertIn(b"\x1b[?1049h", probe.output)
                    self.assertIn(b"\x1b[?1049l", probe.output)
                    self.assertEqual(_has_color(probe.output), not no_color)
                finally:
                    probe.close()

    def test_stalled_pty_keeps_four_hz_loop_live_and_scheduled_quit_bounded(self):
        probe = _PTYProbe("stall")
        try:
            self.assertTrue(probe.wait_for_raw_mode(drain_output=False))
            status = probe.wait_for_exit(timeout=5.0, drain_output=False)
            self.assertEqual(status["failure"]["code"], "output_stalled")
            self.assertGreaterEqual(status["failure_no_progress_seconds"], 2.0)
            self.assertEqual(status["process_code"], 3)
            self.assertTrue(status["scheduled_quit"])
            self.assertGreaterEqual(status["tick_count"], 3)
            self.assertGreater(status["high_watermark_bytes"], 64 * 1024)
            self.assertLessEqual(status["high_watermark_bytes"], 512 * 1024)
            self.assertGreater(status["pending_bytes"], 0)
            self.assertLessEqual(status["pending_bytes"], 512 * 1024)
            self.assertTrue(status["terminal_flags_restored"])
            self.assertLess(status["terminal_restore_seconds"], 2.0)
            self.assertFalse(status["screen_reset_delivered"])
            self.assertTrue(status["wait_closed"])
            self.assertTrue(status["idempotent_close"])
            self.assertFalse(status["worker_alive"])
            self.assertTrue(status["owned_fds_closed"])
            self.assertEqual(status["textual_threads_alive"], [])
            self.assertEqual(probe.current_termios(), probe.original_termios)
            self.assertEqual(fcntl.fcntl(probe.slave_fd, fcntl.F_GETFL), probe.original_fd_flags)
        finally:
            probe.close()

    def test_capacity_overflow_fails_without_exceeding_pending_byte_budget(self):
        probe = _PTYProbe("capacity")
        try:
            self.assertTrue(probe.wait_for_raw_mode(drain_output=False))
            status = probe.wait_for_exit(drain_output=False)
            self.assertEqual(status["failure"]["code"], "output_capacity")
            self.assertEqual(status["process_code"], 3)
            self.assertLessEqual(status["high_watermark_bytes"], 512 * 1024)
            self.assertGreater(status["pending_bytes"], 0)
            self.assertLessEqual(status["pending_bytes"], 512 * 1024)
            self.assertTrue(status["terminal_flags_restored"])
            self.assertFalse(status["screen_reset_delivered"])
            self.assertTrue(status["wait_closed"])
            self.assertTrue(status["idempotent_close"])
            self.assertFalse(status["worker_alive"])
            self.assertTrue(status["owned_fds_closed"])
        finally:
            probe.close()

    def test_real_pty_preserves_utf8_bytes_and_fifo_order(self):
        probe = _PTYProbe("payload")
        try:
            self.assertTrue(probe.wait_for_raw_mode())
            status = probe.wait_for_exit(timeout=8.0)
            expected = ("AΩ🛰Z" * 60_000).encode("utf-8")
            start = probe.output.index(b"PAYLOAD_BEGIN") + len(b"PAYLOAD_BEGIN")
            end = probe.output.index(b"PAYLOAD_END", start)
            self.assertEqual(probe.output[start:end], expected)
            self.assertEqual(status["process_code"], 0)
            self.assertIsNone(status["failure"])
            self.assertLessEqual(status["high_watermark_bytes"], 512 * 1024)
            self.assertTrue(status["screen_reset_delivered"])
            self.assertTrue(status["terminal_flags_restored"])
            self.assertTrue(status["wait_closed"])
            self.assertTrue(status["idempotent_close"])
            self.assertTrue(status["owned_fds_closed"])
        finally:
            probe.close()

    def test_non_tty_stderr_is_reported_before_raw_terminal_mode(self):
        probe = _PTYProbe("ui", stderr_pipe=True)
        try:
            status = probe.wait_for_exit(timeout=5.0, drain_output=False)
            self.assertEqual(status["failure"]["code"], "output_not_terminal")
            self.assertEqual(status["process_code"], 3)
            self.assertTrue(status["terminal_flags_restored"])
            self.assertEqual(probe.current_termios(), probe.original_termios)
            self.assertTrue(status["wait_closed"])
            self.assertFalse(status["worker_alive"])
            self.assertTrue(status["owned_fds_closed"])
        finally:
            probe.close()

    def test_closed_pty_peer_fails_writer_and_releases_owned_resources(self):
        master_fd, slave_fd = pty.openpty()
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        original_fd_flags = fcntl.fcntl(slave_fd, fcntl.F_GETFL)
        pump = BoundedOutputPump(
            slave_fd,
            pending_limit_bytes=64 * 1024,
            stall_timeout_seconds=2.0,
        )
        try:
            self.assertTrue(pump.start())
            owned_fds = pump.owned_fd_numbers
            self.assertTrue(fcntl.fcntl(owned_fds[0], fcntl.F_GETFL) & os.O_NONBLOCK)
            self.assertEqual(fcntl.fcntl(slave_fd, fcntl.F_GETFL), original_fd_flags)
            os.close(master_fd)
            pump.write("trigger broken terminal output")
            self.assertTrue(pump.wait_closed(timeout=1.0))
            self.assertIn(pump.failure.code, {"output_write", "output_closed"})
            self.assertLessEqual(pump.pending_bytes, 64 * 1024)
            self.assertFalse(pump.thread_alive)
            self.assertTrue(all(not _fd_is_open(fd) for fd in owned_fds))
            self.assertEqual(fcntl.fcntl(slave_fd, fcntl.F_GETFL), original_fd_flags)
        finally:
            pump.close()
            pump.wait_closed(timeout=1.0)
            for fd in (master_fd, slave_fd):
                try:
                    os.close(fd)
                except OSError:
                    pass

    def test_ring_wrap_preserves_order_after_partial_nonblocking_writes(self):
        master_fd, slave_fd = pty.openpty()
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        os.set_blocking(master_fd, False)
        pump = BoundedOutputPump(
            slave_fd,
            pending_limit_bytes=64 * 1024,
            stall_timeout_seconds=2.0,
            shutdown_timeout_seconds=3.0,
        )
        first = b"A" * (48 * 1024)
        second = b"B" * (20 * 1024)
        received = bytearray()
        try:
            self.assertTrue(pump.start())
            self.assertTrue(pump.write(first.decode("ascii")))
            deadline = time.monotonic() + 1.0
            while pump.pending_bytes == len(first) and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertGreater(pump.pending_bytes, 0)
            self.assertLess(pump.pending_bytes, len(first))
            self.assertTrue(pump.write(second.decode("ascii")))
            self.assertGreater(pump.high_watermark_bytes, len(first))
            self.assertLessEqual(pump.high_watermark_bytes, 64 * 1024)
            pump.close()

            deadline = time.monotonic() + 3.5
            while not pump.closed and time.monotonic() < deadline:
                try:
                    received.extend(os.read(master_fd, 65_536))
                except BlockingIOError:
                    time.sleep(0.005)
            while True:
                try:
                    data = os.read(master_fd, 65_536)
                except BlockingIOError:
                    break
                if not data:
                    break
                received.extend(data)

            self.assertTrue(pump.wait_closed(timeout=0.1))
            self.assertEqual(received, first + second)
            self.assertIsNone(pump.failure)
            self.assertFalse(pump.thread_alive)
        finally:
            pump.close()
            pump.wait_closed(timeout=0.1)
            for fd in (master_fd, slave_fd):
                try:
                    os.close(fd)
                except OSError:
                    pass

    def test_wake_pins_descriptor_until_nonblocking_write_finishes(self):
        pump = BoundedOutputPump(-1)
        owned_output_fd = os.open(os.devnull, os.O_WRONLY | os.O_CLOEXEC)
        wake_read_fd, wake_write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        pump._owned_output_fd = owned_output_fd
        pump._wake_read_fd = wake_read_fd
        pump._wake_write_fd = wake_write_fd
        pump._owned_fd_numbers = (owned_output_fd, wake_read_fd, wake_write_fd)

        close_lock_attempted = threading.Event()
        close_lock_acquired = threading.Event()
        closed = threading.Event()
        write_entered = threading.Event()
        release_write = threading.Event()
        original_lock = pump._lock

        class ObservedLock:
            def __enter__(self):
                if threading.current_thread().name == "pump-fd-close":
                    close_lock_attempted.set()
                original_lock.acquire()
                if threading.current_thread().name == "pump-fd-close":
                    close_lock_acquired.set()
                return self

            def __exit__(self, _exc_type, _exc_value, _traceback):
                original_lock.release()

        pump._lock = ObservedLock()

        def close_owned_fds():
            pump._close_owned_fds()
            closed.set()

        real_write = os.write

        def gated_write(fd, data):
            if fd == wake_write_fd and threading.current_thread().name == "pump-fd-wake":
                write_entered.set()
                release_write.wait(timeout=2.0)
            return real_write(fd, data)

        with tempfile.TemporaryDirectory() as directory:
            unrelated_path = Path(directory) / "unrelated-fd"
            unrelated_path.write_bytes(b"")
            with patch("agent_observer.terminal.dashboard_output.os.write", gated_write):
                wake_thread = threading.Thread(target=pump._wake, name="pump-fd-wake")
                wake_thread.start()
                self.assertTrue(write_entered.wait(timeout=1.0))

                close_thread = threading.Thread(
                    target=close_owned_fds,
                    name="pump-fd-close",
                )
                close_thread.start()
                self.assertTrue(close_lock_attempted.wait(timeout=1.0))
                acquired_before_write = close_lock_acquired.wait(timeout=0.2)
                if acquired_before_write:
                    self.assertTrue(closed.wait(timeout=1.0))
                closed_before_write = closed.is_set()

                reused_fd = None
                fillers = []
                if closed_before_write:
                    reused_fd, fillers = self._open_at_fd(
                        unrelated_path,
                        wake_write_fd,
                    )

                release_write.set()
                wake_thread.join(timeout=1.0)
                close_thread.join(timeout=1.0)
                self.assertFalse(wake_thread.is_alive())
                self.assertFalse(close_thread.is_alive())
                self.assertTrue(closed.is_set())

            if reused_fd is None:
                reused_fd, fillers = self._open_at_fd(unrelated_path, wake_write_fd)
            try:
                self.assertFalse(closed_before_write)
                self.assertEqual(os.fstat(reused_fd).st_size, 0)
                self.assertEqual(os.pread(reused_fd, 1, 0), b"")
            finally:
                os.close(reused_fd)
                for fd in fillers:
                    os.close(fd)

    @staticmethod
    def _open_at_fd(path: Path, target_fd: int) -> tuple[int, list[int]]:
        fillers = []
        while True:
            fd = os.open(os.devnull, os.O_RDONLY | os.O_CLOEXEC)
            if fd == target_fd:
                os.close(fd)
                break
            fillers.append(fd)
        target = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        return target, fillers

    def test_signal_quit_restores_terminal_and_drains_screen_reset(self):
        probe = _PTYProbe("signal")
        try:
            self.assertTrue(probe.wait_for_raw_mode())
            self.assertTrue(probe.wait_for_output(b"Dashboard output probe"))
            probe.process.send_signal(signal.SIGTERM)
            status = probe.wait_for_exit()
            self.assertEqual(status["process_code"], 143)
            self.assertIsNone(status["failure"])
            self.assertTrue(status["terminal_flags_restored"])
            self.assertTrue(status["screen_reset_delivered"])
            self.assertEqual(probe.current_termios(), probe.original_termios)
            self.assertTrue(status["wait_closed"])
            self.assertFalse(status["worker_alive"])
            self.assertTrue(status["owned_fds_closed"])
        finally:
            probe.close()


def _fd_is_open(fd: int) -> bool:
    try:
        os.fstat(fd)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    unittest.main()
