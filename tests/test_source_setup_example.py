"""Isolated checks for the version-bound first-source launcher and route."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/mesh_plus_agent_working_set.py"
FIXTURES = ROOT / "tests/fixtures/source-setup"


def _launcher_at(directory: Path):
    path = directory / "mesh_plus_agent_working_set.py"
    path.write_bytes(EXAMPLE.read_bytes())
    path.chmod(0o700)
    spec = importlib.util.spec_from_file_location("source_setup_launcher", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, path


def _sources_config(directory: Path, *, domain="agent", source="agent_working_set") -> Path:
    path = directory / "mesh-sources.toml"
    path.write_text(
        f'version = 1\nhost = "fixture"\n\n'
        f'[sources.{source}]\ndomain = "{domain}"\n'
        f'socket = "{directory / "collector.sock"}"\n',
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def _mesh_module(descriptor, calls):
    package = types.ModuleType("mesh_plus")
    package.__path__ = []
    cli = types.ModuleType("mesh_plus.cli")
    cli.configured_descriptor = descriptor

    def main(**kwargs):
        calls.append((list(sys.argv[1:]), kwargs))
        return 17

    cli.main = main
    return package, cli


class SourceSetupLauncherTests(unittest.TestCase):
    def test_authority_and_unrelated_dispatch_keep_normal_mesh_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            calls = []
            descriptor_calls = []

            def descriptor(*args):
                descriptor_calls.append(args)
                raise AssertionError("unrelated dispatch inspected Observer config")

            package, cli = _mesh_module(descriptor, calls)
            with patch.dict(
                sys.modules,
                {
                    "mesh_plus": package,
                    "mesh_plus.cli": cli,
                    "agent_observer": None,
                    "agent_observer.mesh_working_set_publisher": None,
                },
            ):
                self.assertEqual(launcher.main(["mesh", "list", "--json"]), 17)
                authority_args, authority_kwargs = calls.pop()
                self.assertEqual(authority_args, ["mesh", "list", "--json"])
                self.assertEqual(authority_kwargs, {})

                self.assertEqual(
                    launcher.main(["bridge", "--source", "tmux_default", "--stdio"]), 17
                )
                other_args, other_kwargs = calls.pop()
                self.assertEqual(other_args, ["bridge", "--source", "tmux_default", "--stdio"])
                self.assertEqual(other_kwargs, {})
                self.assertEqual(
                    launcher.main(["read", "--domain", "agent", "--source", "other"]), 17
                )
                read_args, read_kwargs = calls.pop()
                self.assertEqual(read_args[0], "read")
                self.assertEqual(read_kwargs, {})

            self.assertEqual(descriptor_calls, [])

    def test_default_sidecar_binding_and_equals_flags_use_static_factory_hook(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            config = _sources_config(root)
            calls = []
            descriptor_calls = []

            def descriptor(path, source):
                descriptor_calls.append((Path(path), source))
                self.assertEqual(Path(path), config)
                self.assertEqual(source, "agent_working_set")
                return "fixture", "agent", str(root / "collector.sock")

            package, cli = _mesh_module(descriptor, calls)
            original_argv = sys.argv
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                result = launcher.main(
                    [
                        "serve",
                        "--source=agent_working_set",
                        "--socket=mesh-output.sock",
                    ]
                )
            self.assertEqual(result, 17)
            self.assertIs(sys.argv, original_argv)
            self.assertEqual(descriptor_calls, [(config, "agent_working_set")])
            received, kwargs = calls[0]
            self.assertEqual(received[:3], ["serve", "--config", str(config)])
            self.assertEqual(
                received[3:], ["--source=agent_working_set", "--socket=mesh-output.sock"]
            )
            self.assertEqual(set(kwargs["publisher_factories"]), {"agent"})
            self.assertIs(
                kwargs["publisher_factories"]["agent"], launcher.make_working_set_publisher
            )

    def test_explicit_config_stays_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            sidecar = _sources_config(root)
            explicit = root / "explicit.toml"
            explicit.write_text(sidecar.read_text(encoding="utf-8"), encoding="utf-8")
            explicit.chmod(0o600)
            calls = []

            def descriptor(path, source):
                self.assertEqual(Path(path), explicit)
                self.assertEqual(source, "agent_working_set")
                return "fixture", "agent", str(root / "collector.sock")

            package, cli = _mesh_module(descriptor, calls)
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                result = launcher.main(
                    [
                        "bridge",
                        "--source=agent_working_set",
                        "--stdio",
                        f"--config={explicit}",
                    ]
                )
            self.assertEqual(result, 17)
            received, kwargs = calls[0]
            self.assertEqual(
                received,
                ["bridge", "--source=agent_working_set", "--stdio", f"--config={explicit}"],
            )
            self.assertEqual(set(kwargs["publisher_factories"]), {"agent"})

    def test_invalid_or_mismatched_binding_fails_without_reference_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            calls = []
            package, cli = _mesh_module(
                lambda *_args: (_ for _ in ()).throw(ValueError("bad descriptor")), calls
            )
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                with contextlib.redirect_stderr(io.StringIO()):
                    result = launcher.main(
                        ["serve", "--source=agent_working_set", "--socket", "out.sock"]
                    )
            self.assertEqual(result, 2)
            self.assertEqual(calls, [])

            calls.clear()
            package, cli = _mesh_module(
                lambda *_args: ("fixture", "tmux", "/tmp/input.sock"), calls
            )
            _sources_config(root)
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                with contextlib.redirect_stderr(io.StringIO()):
                    result = launcher.main(["bridge", "--source", "agent_working_set", "--stdio"])
            self.assertEqual(result, 2)
            self.assertEqual(calls, [])

    def test_ambiguous_target_bindings_fail_before_mesh_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            _sources_config(root)
            calls = []
            package, cli = _mesh_module(
                lambda *_args: ("fixture", "agent", "/tmp/input.sock"), calls
            )
            candidates = (
                ["serve", "--source", "agent_working_set", "--source", "other"],
                ["serve", "--source", "agent_working_set", "--config", "a", "--config", "b"],
            )
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                for arguments in candidates:
                    with (
                        self.subTest(arguments=arguments),
                        contextlib.redirect_stderr(io.StringIO()),
                    ):
                        self.assertEqual(launcher.main(arguments), 2)
            self.assertEqual(calls, [])

    def test_abbreviated_source_or_config_flags_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            _sources_config(root)
            calls = []
            package, cli = _mesh_module(
                lambda *_args: ("fixture", "agent", "/tmp/input.sock"), calls
            )
            candidates = (
                ["bridge", "--sou", "agent_working_set", "--stdio"],
                ["bridge", "--sou=agent_working_set", "--stdio"],
                ["bridge", "--source", "agent_working_set", "--stdio", "--conf", "explicit.toml"],
                ["bridge", "--source=agent_working_set", "--stdio", "--conf=explicit.toml"],
            )
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                for arguments in candidates:
                    with (
                        self.subTest(arguments=arguments),
                        contextlib.redirect_stderr(io.StringIO()),
                    ):
                        self.assertEqual(launcher.main(arguments), 2)
            self.assertEqual(calls, [])

    def test_factory_constructs_the_registered_working_set_profile(self):
        from mesh_test_support import require_working_set_sdk

        require_working_set_sdk()
        with tempfile.TemporaryDirectory() as temporary:
            launcher, _path = _launcher_at(Path(temporary))
            publisher = launcher.make_working_set_publisher(
                "fixture", "agent_working_set", "/private/fixture/collector.sock"
            )
        self.assertEqual(publisher.host, "fixture")
        self.assertEqual(publisher.source, "agent_working_set")
        self.assertEqual(publisher.profile, "agent-observer.mesh-working-set.v1")

    def test_real_private_mesh_descriptor_binds_wrapper_without_fallback(self):
        from mesh_test_support import require_working_set_sdk

        require_working_set_sdk()
        from mesh_plus.cli import configured_descriptor

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher, _path = _launcher_at(root)
            config = _sources_config(root)
            calls = []
            package, cli = _mesh_module(configured_descriptor, calls)
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                self.assertEqual(
                    launcher.main(
                        ["serve", "--source", "agent_working_set", "--socket", "out.sock"]
                    ),
                    17,
                )
            self.assertEqual(calls[0][0][:3], ["serve", "--config", str(config)])

            wrong_source = root / "wrong-source.toml"
            wrong_source.write_text(
                f'version = 1\nhost = "fixture"\n\n'
                f'[sources.other]\ndomain = "agent"\nsocket = "{root / "collector.sock"}"\n',
                encoding="utf-8",
            )
            wrong_source.chmod(0o600)
            calls.clear()
            with patch.dict(sys.modules, {"mesh_plus": package, "mesh_plus.cli": cli}):
                with contextlib.redirect_stderr(io.StringIO()):
                    result = launcher.main(
                        [
                            "bridge",
                            "--source",
                            "agent_working_set",
                            "--stdio",
                            "--config",
                            str(wrong_source),
                        ]
                    )
            self.assertEqual(result, 2)
            self.assertEqual(calls, [])


class SourceSetupRemoteFixtureTests(unittest.TestCase):
    def test_synthetic_outgoing_route_and_fixed_remote_bridge_argv(self):
        from mesh_test_support import require_working_set_sdk

        require_working_set_sdk()
        from mesh_plus.authority import load_config
        from mesh_plus.transport import ssh_argv

        reader = load_config(
            FIXTURES / "reader-authority.toml", hostname=("reader.invalid", "reader")
        )
        self.assertEqual(reader.local_host_id, "reader")
        self.assertEqual(len(reader.remote_hosts), 1)
        self.assertEqual(reader.remote_hosts[0].id, "source")
        self.assertEqual(
            [route.destination for route in reader.remote_hosts[0].routes],
            ["source-fixture.invalid"],
        )
        # No source-side authority is supplied, so this outgoing route says
        # nothing about reciprocal permission on the other endpoint.

        self.assertEqual(
            ssh_argv("source-fixture.invalid", "agent_working_set"),
            [
                "ssh",
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "ClearAllForwardings=yes",
                "-o",
                "ForwardAgent=no",
                "-o",
                "RequestTTY=no",
                "-o",
                "ConnectTimeout=2",
                "-o",
                "ConnectionAttempts=1",
                "-o",
                "ServerAliveInterval=5",
                "-o",
                "ServerAliveCountMax=2",
                "-o",
                "ControlMaster=no",
                "-o",
                "ControlPath=none",
                "--",
                "source-fixture.invalid",
                "mesh-plus bridge --source agent_working_set --stdio",
            ],
        )


if __name__ == "__main__":
    unittest.main()
