"""Pure help, argument/config validation and pre-raw terminal admission."""

import contextlib
import io
import os
import pty
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_terminal_cli import write_config

from agent_observer.terminal import dashboard_cli as cli
from agent_observer.terminal.dashboard_runner import DashboardResult


class DashboardCliTests(unittest.TestCase):
    def test_help_needs_no_optional_modules_or_config_and_rejects_finite_options(self):
        root = Path(__file__).resolve().parents[1]
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from agent_observer.cli import main; main(['dashboard','--help'])"
        )
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-c", code, str(root)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--connect-timeout", completed.stdout)
        self.assertNotIn("--format", completed.stdout)
        for options in (("--format", "json"), ("--timeout", "5"), ("--connect-timeout", "nan")):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                cli.parser().parse_args(options)
            self.assertEqual(error.exception.code, 2)

    def test_bad_config_does_not_import_dependencies_or_start_a_reader(self):
        with (
            patch.object(
                cli, "dashboard_dependencies", side_effect=AssertionError("dependency I/O")
            ),
            patch.object(cli, "write_stderr"),
        ):
            self.assertEqual(cli.main(["--config", "/nonexistent/dashboard-fixture.toml"]), 2)

    def test_terminal_admission_requires_same_interactive_terminal_and_capable_term(self):
        master, slave = pty.openpty()
        other_master, other_slave = pty.openpty()
        try:
            stream = SimpleNamespace(fileno=lambda: slave)
            streams = (stream,) * 3
            self.assertIsNone(cli.terminal_error(streams=streams, environ={"TERM": "xterm"}))
            self.assertIn(
                "cursor-capable", cli.terminal_error(streams=streams, environ={"TERM": "dumb"})
            )
            mismatch = (stream, stream, SimpleNamespace(fileno=lambda: other_slave))
            self.assertIn(
                "share a terminal", cli.terminal_error(streams=mismatch, environ={"TERM": "xterm"})
            )
            with tempfile.TemporaryFile() as redirected:
                self.assertIn(
                    "interactive",
                    cli.terminal_error(
                        streams=(stream, redirected, stream), environ={"TERM": "xterm"}
                    ),
                )
        finally:
            for fd in (master, slave, other_master, other_slave):
                os.close(fd)

    def test_invalid_terminal_is_rejected_before_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            config = write_config(Path(directory))
            with (
                patch.object(cli, "dashboard_dependencies"),
                patch.object(cli, "terminal_error", return_value="fixture requires terminal"),
                patch.object(cli, "write_stderr") as message,
                patch(
                    "agent_observer.terminal.dashboard_runner.run_dashboard",
                    side_effect=AssertionError("reader started"),
                ),
            ):
                self.assertEqual(cli.main(["--config", str(config)]), 2)
                message.assert_called_once_with("fixture requires terminal")

    def test_preflight_checks_the_original_streams_used_by_the_linux_driver(self):
        master, slave = pty.openpty()
        try:
            terminal = SimpleNamespace(fileno=lambda: slave)
            with (
                tempfile.TemporaryFile() as redirected,
                patch.object(sys, "stdin", terminal),
                patch.object(sys, "stdout", terminal),
                patch.object(sys, "stderr", terminal),
                patch.object(sys, "__stdin__", terminal),
                patch.object(sys, "__stderr__", redirected),
            ):
                error = cli.terminal_error(environ={"TERM": "xterm"})
            self.assertIn("interactive", error)
        finally:
            os.close(master)
            os.close(slave)

    def test_selectors_overrides_filters_and_no_color_reach_persistent_runner(self):
        calls = []

        async def run(sources, filters, **options):
            calls.append((sources, filters, options))
            return DashboardResult(0, None, 0.01, True, True)

        with tempfile.TemporaryDirectory() as directory:
            config = write_config(Path(directory), two_sources=True)
            with (
                patch.object(cli, "dashboard_dependencies"),
                patch.object(cli, "terminal_error", return_value=None),
                patch("agent_observer.terminal.dashboard_runner.run_dashboard", side_effect=run),
                patch.dict(os.environ, {"NO_COLOR": "1"}),
            ):
                self.assertEqual(
                    cli.main(
                        [
                            "--config",
                            str(config),
                            "--source",
                            "fixture-secondary",
                            "--socket",
                            "/fixture/override.sock",
                            "--connect-timeout",
                            "12",
                            "--color",
                            "always",
                            "--query",
                            "test",
                            "--membership",
                            "uncertain",
                        ]
                    ),
                    0,
                )
        sources, filters, options = calls[0]
        self.assertEqual([s.id for s in sources], ["fixture-secondary"])
        self.assertEqual(sources[0].socket, Path("/fixture/override.sock"))
        self.assertEqual(filters["query"], ("test",))
        self.assertEqual(filters["membership"], ("uncertain",))
        self.assertEqual(options["connect_timeout"], 12)
        self.assertTrue(options["no_color"])
