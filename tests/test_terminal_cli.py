"""CLI, schema, subprocess, pipe and exit-code tests for sessions v1."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jsonschema import Draft202012Validator

from agent_observer.terminal.config import TerminalSource, load_config
from agent_observer.terminal.output import schema_document
from agent_observer.terminal.sources import TerminalDependencyError

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
NAMESPACE = "sha256:" + "a" * 64


def write_config(directory: Path, *, two_sources=False) -> Path:
    path = directory / "terminal.toml"
    lines = [
        "version = 1",
        'default_sources = ["fixture-default", "fixture-secondary"]'
        if two_sources
        else 'default_sources = ["fixture-default"]',
        "",
        "[[sources]]",
        'id = "fixture-default"',
        'host = "fixture"',
        'home = "default"',
        'label = "Default"',
        'mesh_source = "agent_working_set"',
        'scope = "local"',
        'socket = "/synthetic/mesh.sock"',
        f'namespace = "{NAMESPACE}"',
        "window_hours = 72",
    ]
    if two_sources:
        lines.extend(
            [
                "",
                "[[sources]]",
                'id = "fixture-secondary"',
                'host = "fixture-secondary-host"',
                'home = "secondary"',
                'label = "Secondary"',
                'mesh_source = "agent_working_set_secondary"',
                'scope = "local"',
                'socket = "/synthetic/mesh-secondary.sock"',
                f'namespace = "sha256:{"b" * 64}"',
                "window_hours = 48",
            ]
        )
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)
    return path


def fake_row(native_id="exact-fixture-id", title="Fixture session"):
    return {
        "identity": {
            "hostScope": "fixture",
            "provider": "codex",
            "namespace": NAMESPACE,
            "nativeIdKind": "thread_id",
            "nativeId": native_id,
        },
        "title": title,
        "kind": "user",
        "cwd": "/synthetic/workspace",
        "workspace": {"health": "current", "reason": "mapped", "projectKey": "fixture-project"},
        "metadataIssues": [],
        "blockedReasons": [],
        "runtime": {"value": "running", "health": "current", "reason": "native", "observedAt": 900},
        "phase": {"value": "working", "health": "current", "reason": "native", "observedAt": 900},
        "activity": {"at": 950, "health": "current", "reason": "native_timestamp"},
    }


def fake_state(*, empty=False):
    source = TerminalSource(
        id="fixture-default",
        host="fixture",
        home="default",
        label="Default",
        mesh_source="agent_working_set",
        scope="local",
        socket=Path("/synthetic/mesh.sock"),
        namespace=NAMESPACE,
        window_hours=72,
    )
    row = fake_row()
    rows = [] if empty else [row]
    lease = {
        "identity": row["identity"],
        "activeExpiresAtMs": 1500,
        "recentExpiresAtMs": 1700,
        "membershipExpiresAtMs": 1700,
        "fieldExpiresAtMs": {"runtime": 1500, "phase": 1500, "activity": 1700},
    }
    read = SimpleNamespace(
        context={
            "hosts": [
                {"hostId": "fixture", "delivery": {"status": "ready"}, "viewState": "current"}
            ]
        },
        scopes=[
            {
                "hostScope": "fixture",
                "provider": "codex",
                "namespace": NAMESPACE,
                "serviceId": "fixture-service",
                "contextGeneration": 1,
                "continuity": 1,
                "coverage": {"status": "complete", "reason": None, "expiresAtMs": 2000},
            }
        ],
        members=rows,
        member_leases=[] if empty else [lease],
        uncertain=[],
        nonmembers=[],
    )
    state = {
        "config": source.as_dict(),
        "lifecycle": "observing",
        "reason": None,
        "baseline": True,
        "read": read,
        "capture_boottime_ms": 1000,
        "last_frame_boottime_ms": 950,
        "clock": {
            "kind": "CLOCK_BOOTTIME",
            "bootId": "fixture-boot",
            "timeNamespace": "time:7",
            "clockDomain": "time:[7]",
        },
    }
    clock = {
        "kind": "CLOCK_BOOTTIME",
        "bootId": "fixture-boot",
        "timeNamespace": "time:7",
        "clockDomain": "time:[7]",
        "nowBoottimeMs": 1000,
    }
    return state, clock


class TerminalCliTests(unittest.TestCase):
    def test_help_identifies_the_cached_command_and_local_alias(self):
        from agent_observer.terminal import cli

        self.assertTrue(cli.parser().format_usage().startswith("usage: agent-observer sessions "))
        self.assertTrue(
            cli.parser(prog="agent-observer-cli")
            .format_usage()
            .startswith("usage: agent-observer-cli ")
        )

    def test_repeatable_selectors_merge_across_subcommand_boundary(self):
        from agent_observer.terminal import cli

        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), two_sources=True)
            outputs = []
            with (
                patch.object(cli, "write_stdout", outputs.append),
                patch.object(
                    cli, "read_sources", side_effect=AssertionError("unexpected live read")
                ),
            ):
                status = cli.main(
                    [
                        "--config",
                        str(config_path),
                        "--source",
                        "fixture-default",
                        "--host",
                        "fixture",
                        "--home",
                        "default",
                        "--membership",
                        "active",
                        "--runtime",
                        "running",
                        "--phase",
                        "working",
                        "--query",
                        "alpha",
                        "sources",
                        "--configured",
                        "--format",
                        "json",
                        "--source",
                        "fixture-secondary",
                        "--host",
                        "fixture-secondary-host",
                        "--home",
                        "secondary",
                        "--membership",
                        "recent",
                        "--runtime",
                        "parked",
                        "--phase",
                        "waiting",
                        "--query",
                        "beta",
                    ]
                )
            self.assertEqual(status, 0)
            document = json.loads(outputs[0])
            self.assertEqual(len(document["sources"]), 2)
            self.assertEqual(
                document["filters"]["source"], ["fixture-default", "fixture-secondary"]
            )
            self.assertEqual(document["filters"]["host"], ["fixture", "fixture-secondary-host"])
            self.assertEqual(document["filters"]["home"], ["default", "secondary"])
            self.assertEqual(document["filters"]["membership"], ["active", "recent"])
            self.assertEqual(document["filters"]["runtime"], ["running", "parked"])
            self.assertEqual(document["filters"]["phase"], ["working", "waiting"])
            self.assertEqual(document["filters"]["query"], ["alpha", "beta"])
            reusable = cli.parser()
            self.assertNotIn("_BEFORE_", reusable.format_help())
            self.assertEqual(reusable.parse_args(["--host", "fixture", "list"]).host, ["fixture"])
            self.assertEqual(reusable.parse_args(["list", "--host", "other"]).host, ["other"])

    def test_packaged_schema_validates_fixture_and_rejects_wrong_known_types(self):
        schema = schema_document()
        fixture = json.loads((ROOT / "tests/fixtures/terminal-v1/complete-empty.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(fixture)
        invalid = json.loads(json.dumps(fixture))
        invalid["sources"][0]["clock"] = {"kind": "CLOCK_BOOTTIME", "bootId": 4}
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)))

    def test_overview_list_show_and_sources_commands_keep_exact_identity_contract(self):
        from agent_observer.terminal import cli

        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory))
            state, clock = fake_state()

            async def captured(*_args, **_kwargs):
                return {
                    "states": [state],
                    "clock": clock,
                    "nowBoottimeMs": 1000,
                    "timedOut": False,
                    "exitSignal": 0,
                    "cleanupError": None,
                }

            outputs = []
            errors = []
            with (
                patch("agent_observer.terminal.cli.read_sources", captured),
                patch("agent_observer.terminal.cli.write_stdout", outputs.append),
                patch("agent_observer.terminal.cli.write_stderr", errors.append),
            ):
                self.assertEqual(
                    cli.main(["--config", str(config_path), "overview", "--format", "json"]), 0
                )
                overview = json.loads(outputs.pop())
                Draft202012Validator(schema_document()).validate(overview)
                self.assertEqual(overview["totals"]["members"], 1)
                self.assertEqual(
                    overview["sessions"][0]["identity"]["nativeId"], "exact-fixture-id"
                )

                self.assertEqual(
                    cli.main(["list", "--config", str(config_path), "--query", "fixture"]), 0
                )
                self.assertIn("Fixture session", outputs.pop())

                self.assertEqual(cli.main(["show", "missing", "--config", str(config_path)]), 1)
                self.assertIn("not in the fully observed", outputs.pop())

                full_ref = json.dumps(fake_row()["identity"])
                self.assertEqual(
                    cli.main(["show", "--ref", full_ref, "--config", str(config_path)]), 0
                )
                self.assertIn("exact-fixture-id", outputs.pop())

                self.assertEqual(
                    cli.main(
                        [
                            "show",
                            "--ref",
                            full_ref,
                            "--format",
                            "json",
                            "--config",
                            str(config_path),
                        ]
                    ),
                    0,
                )
                Draft202012Validator(schema_document()).validate(json.loads(outputs.pop()))

                failed_state = dict(state)
                failed_state.update(lifecycle="failed", reason="mesh_unavailable", baseline=False)

                async def degraded_capture(*_args, **_kwargs):
                    return {
                        "states": [failed_state],
                        "clock": clock,
                        "nowBoottimeMs": 1000,
                        "timedOut": False,
                        "exitSignal": 0,
                        "cleanupError": None,
                    }

                with patch("agent_observer.terminal.cli.read_sources", degraded_capture):
                    self.assertEqual(
                        cli.main(["list", "--format", "json", "--config", str(config_path)]),
                        3,
                    )
                degraded = json.loads(outputs.pop())
                Draft202012Validator(schema_document()).validate(degraded)
                self.assertEqual(degraded["result"], "degraded")

                self.assertEqual(cli.main(["sources", "--config", str(config_path)]), 0)
                self.assertIn("namespace expected=", outputs.pop())
            self.assertEqual(errors, [])

    def test_invocation_and_dependency_errors_use_exit_two(self):
        from agent_observer.terminal import cli

        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory))
            errors = []
            with (
                patch("agent_observer.terminal.cli.write_stderr", errors.append),
                patch("agent_observer.terminal.cli.write_stdout") as output,
            ):
                self.assertEqual(
                    cli.main(["list", "--config", str(config_path), "--host", "unknown"]), 2
                )
                output.assert_not_called()
                self.assertTrue(errors)

                with patch(
                    "agent_observer.terminal.cli.read_sources",
                    side_effect=TerminalDependencyError("mesh_dependency_missing_or_incompatible"),
                ):
                    self.assertEqual(cli.main(["list", "--config", str(config_path)]), 2)
                self.assertIn("agent-observer[mesh]", errors[-1])

    def test_window_hours_override_is_a_copy_and_requires_one_selected_source(self):
        from agent_observer.terminal import cli

        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory))
            config = load_config(config_path)
            original_source = config.sources[0]
            state, clock = fake_state()
            selected_sources = []

            async def captured(sources, **_kwargs):
                selected_sources.extend(sources)
                return {
                    "states": [state],
                    "clock": clock,
                    "nowBoottimeMs": 1000,
                    "timedOut": False,
                    "exitSignal": 0,
                    "cleanupError": None,
                }

            with (
                patch("agent_observer.terminal.cli.read_sources", captured),
                patch("agent_observer.terminal.cli.write_stdout"),
                patch("agent_observer.terminal.cli.write_stderr"),
            ):
                self.assertEqual(
                    cli.main(
                        [
                            "list",
                            "--config",
                            str(config_path),
                            "--window-hours",
                            "24",
                            "--format",
                            "json",
                        ]
                    ),
                    0,
                )

            self.assertEqual(len(selected_sources), 1)
            self.assertIsNot(selected_sources[0], original_source)
            self.assertEqual(selected_sources[0].window_hours, 24)
            self.assertEqual(original_source.window_hours, 72)
            self.assertEqual(load_config(config_path).sources[0].window_hours, 72)

            multi_path = Path(directory) / "multi"
            multi_path.mkdir()
            multi_config = write_config(multi_path, two_sources=True)
            errors = []
            with (
                patch("agent_observer.terminal.cli.read_sources") as read_sources,
                patch("agent_observer.terminal.cli.write_stderr", errors.append),
                patch("agent_observer.terminal.cli.write_stdout") as write_stdout,
            ):
                self.assertEqual(
                    cli.main(
                        [
                            "list",
                            "--config",
                            str(multi_config),
                            "--window-hours",
                            "24",
                        ]
                    ),
                    2,
                )
            read_sources.assert_not_called()
            write_stdout.assert_not_called()
            self.assertIn("require exactly one selected source", errors[-1])

    def test_schema_and_configured_inspection_are_lazy_subprocess_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory))
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT)
            script = (
                "import sys; sys.modules['mesh_plus']=None; "
                "from agent_observer.cli import main; "
                "raise SystemExit(main(['sessions','sources','--configured','--format','json','--config',sys.argv[1]]))"
            )
            configured = subprocess.run(
                [str(PYTHON), "-c", script, str(config_path)],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(configured.returncode, 0, configured.stderr)
            value = json.loads(configured.stdout)
            Draft202012Validator(schema_document()).validate(value)
            self.assertEqual(value["result"], "configured")
            self.assertEqual(value["sources"][0]["health"], "configured")

            help_result = subprocess.run(
                [str(PYTHON), "-m", "agent_observer.cli", "sessions", "--help"],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_result.returncode, 0)
            self.assertIn("overview", help_result.stdout)
            self.assertIn("sources", help_result.stdout)

            schema = subprocess.run(
                [str(PYTHON), "-m", "agent_observer.cli", "sessions", "schema"],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(schema.returncode, 0, schema.stderr)
            self.assertEqual(json.loads(schema.stdout)["$id"], schema_document()["$id"])

    def test_configured_pipe_is_plain_and_broken_pipe_returns_141(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory))
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT)
            env["NO_COLOR"] = "1"
            configured = subprocess.run(
                [
                    str(PYTHON),
                    "-m",
                    "agent_observer.cli",
                    "sessions",
                    "sources",
                    "--configured",
                    "--format",
                    "text",
                    "--color",
                    "always",
                    "--config",
                    str(config_path),
                ],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(configured.returncode, 0, configured.stderr)
            self.assertNotIn("\x1b", configured.stdout)
            self.assertIn(NAMESPACE, configured.stdout)

        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            broken = subprocess.run(
                [str(PYTHON), "-m", "agent_observer.cli", "sessions", "schema"],
                cwd=ROOT,
                stdout=write_fd,
                stderr=subprocess.PIPE,
                check=False,
                close_fds=True,
            )
        finally:
            os.close(write_fd)
        self.assertEqual(broken.returncode, 141)


if __name__ == "__main__":
    unittest.main()
