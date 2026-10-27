"""Real terminal restoration through the outer runner, with invented UI text."""

import errno
import importlib.util
import json
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import textwrap
import time
import unittest
from pathlib import Path

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
ROOT = Path(__file__).resolve().parents[1]

CHILD = textwrap.dedent(
    r"""
    import asyncio,fcntl,json,os,sys,termios
    from textual.app import App,ComposeResult
    from textual.widgets import Static
    from agent_observer.terminal.dashboard_output import BoundedLinuxDriver
    from agent_observer.terminal.dashboard_runner import run_dashboard
    case=sys.argv[1]; control=int(sys.argv[2]); owner=None
    fcntl.ioctl(0,termios.TIOCSCTTY,0)
    os.tcsetpgrp(0,os.getpgrp())
    def notify(value):
        os.write(control,(json.dumps(value)+'\n').encode())
    class Reader:
        cleanup_error=None
        closed=False
        cancelled=0
        async def start(self): pass
        def request_close(self): pass
        async def close(self):
            try: await asyncio.sleep(.15)
            except asyncio.CancelledError:
                self.cancelled+=1
                raise
            self.closed=True
    reader=Reader()
    def factory(_reader,_filters,*,no_color,icons,on_exit_requested):
        class Probe(App):
            BINDINGS=[('q','quit','Quit')]
            ENABLE_COMMAND_PALETTE=False
            def __init__(self):
                super().__init__(driver_class=BoundedLinuxDriver)
                self.stopped=False
            def compose(self)->ComposeResult:
                yield Static('Invented dashboard lifecycle fixture')
            def on_mount(self):
                notify({'ready':True})
                if case=='cancel':
                    async def cancel_many():
                        for _ in range(7):
                            await asyncio.sleep(.02)
                            owner.cancel()
                    asyncio.create_task(cancel_many())
                if case=='stall': self.output_driver.write('X'*100_000)
            def exit(self,*args,**kwargs):
                on_exit_requested()
                return super().exit(*args,**kwargs)
            async def stop_updates(self): self.stopped=True
        return Probe()
    async def main():
        global owner
        owner=asyncio.create_task(run_dashboard((),{},reader_factory=lambda *_a,**_k:reader,app_factory=factory))
        result=await owner
        notify({'code':result.code,'reason':result.reason,'flagsRestored':result.terminal_flags_restored,'screenResetDelivered':result.screen_reset_delivered,'cleanupSeconds':result.cleanup_seconds,'readerClosed':reader.closed,'readerCancellations':reader.cancelled})
        return result.code
    raise SystemExit(asyncio.run(main()))
    """
)


@unittest.skipUnless(
    TEXTUAL_AVAILABLE and sys.platform == "linux", "dashboard extra/Linux required"
)
class DashboardLifecycleTests(unittest.TestCase):
    def run_case(self, case, *, signum=None, expected=0):
        master, slave = pty.openpty()
        control_read, control_write = os.pipe()
        initial = termios.tcgetattr(slave)
        process = subprocess.Popen(
            [sys.executable, "-c", CHILD, case, str(control_write)],
            cwd=ROOT,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            pass_fds=(control_write,),
            start_new_session=True,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(control_write)
        pending = b""
        messages = []
        ready = False
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                reads = [control_read] if case == "stall" else [control_read, master]
                available, _, _ = select.select(reads, [], [], 0.05)
                for fd in available:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            chunk = b""
                        else:
                            raise
                    if fd == control_read and chunk:
                        pending += chunk
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            messages.append(json.loads(line))
                if not ready and any(m.get("ready") for m in messages):
                    ready = True
                    if signum is not None:
                        process.send_signal(signum)
                    elif case == "quit":
                        os.write(master, b"q")
                if any("code" in message for message in messages):
                    break
                if process.poll() is not None and not available:
                    break
            self.assertTrue(ready, messages)
            result = next((m for m in messages if "code" in m), None)
            self.assertIsNotNone(result, messages)
            self.assertEqual(result["code"], expected, result)
            self.assertTrue(result["readerClosed"], result)
            self.assertEqual(result["readerCancellations"], 0, result)
            self.assertTrue(result["flagsRestored"], result)
            self.assertEqual(termios.tcgetattr(slave), initial)
            self.assertLess(result["cleanupSeconds"], 5)
            process.wait(timeout=3)
            self.assertEqual(process.returncode, expected)
            return result
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for fd in (master, slave, control_read):
                os.close(fd)

    def test_quit_and_repeated_outer_cancellation_restore_actual_terminal(self):
        self.run_case("quit")
        self.run_case("cancel", expected=130)

    def test_interrupt_terminate_and_hangup_restore_actual_terminal(self):
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signum=signum):
                self.run_case("signal", signum=signum, expected=128 + signum)

    def test_stalled_output_returns_three_and_restores_flags_without_sink_drain(self):
        result = self.run_case("stall", expected=3)
        self.assertFalse(result["screenResetDelivered"], result)
        self.assertEqual(result["reason"], "output_stalled")
