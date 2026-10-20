"""Private, explicit route configuration tests; no service or daemon access."""

import ast
import io
import json
import os
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import agent_observer.home_profiles as home_profiles
from agent_observer.contract import store_namespace
from agent_observer.home_profiles import (
    DEFAULT_WINDOW_MS,
    HomeProfileConfigError,
    _validate_route_set,
    load_home_profiles,
    routes_document,
    select_home_profiles,
)


def toml_document(profiles, *, host="snap", version="1"):
    lines = [f"version = {version}", f"host = {json.dumps(host)}", ""]
    for profile_id, (label, home) in profiles:
        lines.extend(
            [
                f"[profiles.{profile_id}]",
                f"label = {json.dumps(label)}",
                f"codex_home = {json.dumps(str(home))}",
                "",
            ]
        )
    return "\n".join(lines)


class HomeProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="home-profiles-")
        self.root = Path(self.temp.name)
        self.runtime = self.root / "run"
        self.runtime.mkdir(mode=0o700)
        self.uid = os.getuid()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, content, name="profiles.toml", mode=0o600):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        path.chmod(mode)
        return path

    def load(self, content, *, name="profiles.toml", mode=0o600):
        return load_home_profiles(
            self.write(content, name=name, mode=mode),
            uid=self.uid,
            runtime_dir=self.runtime,
        )

    def test_default_and_work_routes_keep_existing_bindings_and_stay_separate(self):
        default_home = self.root / "codex-default"
        work_home = self.root / "codex-work"
        default_only = self.load(toml_document([("default", ("Default", default_home))]))
        default = default_only.routes[0]
        self.assertEqual(default.profile_id, "default")
        self.assertEqual(default.collector_unit, "agent-observer.service")
        self.assertEqual(default.collector_socket, self.runtime / "agent-observer" / "read.sock")
        self.assertEqual(default.mesh_source, "agent_working_set")
        self.assertEqual(
            default.publisher_unit,
            "mesh-plus-agent-working-set.service",
        )
        self.assertEqual(
            default.publisher_socket,
            self.runtime / "mesh-plus-agent-working-set" / "read.sock",
        )
        self.assertEqual(default.codex_home, str(default_home))
        self.assertEqual(
            default.namespace,
            store_namespace("codex", str(default_home), "explicit", self.uid),
        )
        self.assertEqual(default.window_ms, DEFAULT_WINDOW_MS)

        with_work = self.load(
            toml_document(
                [
                    ("default", ("Default", default_home)),
                    ("work", ("Work", work_home)),
                ]
            )
        )
        self.assertEqual(with_work.routes[0], default)
        work = with_work.routes[1]
        self.assertEqual(work.collector_unit, "agent-observer-profile-work.service")
        self.assertEqual(
            work.collector_socket,
            self.runtime / "agent-observer-profile-work" / "read.sock",
        )
        self.assertEqual(work.mesh_source, "agent_working_set_work")
        self.assertEqual(work.publisher_unit, "mesh-plus-agent-working-set-work.service")
        self.assertEqual(
            work.publisher_socket,
            self.runtime / "mesh-plus-agent-working-set-work" / "read.sock",
        )
        self.assertEqual(work.namespace, store_namespace("codex", str(work_home), "explicit", self.uid))
        owned = (
            default.collector_runtime_dir,
            default.publisher_runtime_dir,
            work.collector_runtime_dir,
            work.publisher_runtime_dir,
        )
        self.assertEqual(len(owned), len(set(owned)))
        for left in owned:
            for right in owned:
                if left != right:
                    self.assertFalse(left.is_relative_to(right))
        self.assertFalse(default_home.exists())
        self.assertFalse(work_home.exists())

    def test_selection_returns_all_exact_subsets_and_empty_without_reordering(self):
        manifest = self.load(
            toml_document(
                [
                    ("default", ("Default", self.root / "default")),
                    ("work", ("Work", self.root / "work")),
                ]
            )
        )
        self.assertEqual(select_home_profiles(manifest), manifest.routes)
        self.assertEqual(select_home_profiles(manifest, ["work"]), (manifest.routes[1],))
        self.assertEqual(select_home_profiles(manifest, ["work", "default"]), manifest.routes)
        self.assertEqual(select_home_profiles(manifest, []), ())
        self.assertEqual(routes_document(manifest, ["work"])["profiles"][0]["id"], "work")
        with self.assertRaisesRegex(HomeProfileConfigError, "profile_not_configured"):
            select_home_profiles(manifest, ["missing"])
        with self.assertRaisesRegex(HomeProfileConfigError, "profile_selection_duplicate"):
            select_home_profiles(manifest, ["work", "work"])

    def test_missing_default_missing_home_and_fixed_window_are_explicit(self):
        missing = self.root / "not-created" / "codex"
        with self.assertRaisesRegex(HomeProfileConfigError, "config_default_required"):
            self.load(toml_document([("work", ("Work", missing))]))
        manifest = self.load(toml_document([("default", ("Default", missing))]))
        self.assertEqual(manifest.routes[0].codex_home, str(missing))
        self.assertEqual(manifest.routes[0].window_ms, 259_200_000)
        self.assertFalse(missing.exists())
        self.assertFalse(missing.parent.exists())

    def test_configured_path_identity_is_preserved_and_labels_do_not_change_routes(self):
        configured_home = f"{self.root}/home//."
        original = self.load(
            toml_document([("default", ("Default", configured_home))])
        ).routes[0]
        relabeled = self.load(
            toml_document([("default", ("Renamed", configured_home))])
        ).routes[0]
        self.assertEqual(original.codex_home, configured_home)
        self.assertEqual(
            original.namespace,
            store_namespace("codex", configured_home, "explicit", self.uid),
        )
        self.assertEqual(original.label, "Default")
        self.assertEqual(relabeled.label, "Renamed")
        self.assertEqual(replace(original, label=relabeled.label), relabeled)
        self.assertNotEqual(
            original.namespace,
            store_namespace("codex", str(Path(configured_home).resolve()), "explicit", self.uid),
        )
        self.assertFalse(Path(configured_home).exists())

    def test_duplicate_physical_homes_include_symlink_aliases(self):
        home = self.root / "homes" / "codex"
        home.parent.mkdir()
        alias = self.root / "codex-alias"
        alias.symlink_to(home, target_is_directory=True)
        content = toml_document(
            [
                ("default", ("Default", home)),
                ("work", ("Work", alias)),
            ]
        )
        with self.assertRaisesRegex(HomeProfileConfigError, "duplicate_home"):
            self.load(content)
        self.assertFalse(home.exists())

    def test_invalid_root_profile_path_and_label_fields_are_rejected(self):
        cases = (
            (toml_document([("default", ("Default", self.root / "home"))], version="true"), "config_version"),
            (toml_document([("default", ("Default", self.root / "home"))], version="1.0"), "config_version"),
            (toml_document([("default", ("Default", self.root / "home"))], host="Snap"), "config_host"),
            (
                toml_document(
                    [
                        ("default", ("Default", self.root / "default")),
                        ("work", ("Work", self.root / "work")),
                        ("extra", ("Extra", self.root / "extra")),
                    ]
                ),
                "config_profiles",
            ),
            (
                toml_document([("default", ("Default", self.root / "relative"))]).replace(
                    json.dumps(str(self.root / "relative")), json.dumps("relative")
                ),
                "profile_home",
            ),
            (
                toml_document([("default", ("Default", self.root / "with-parent"))]).replace(
                    json.dumps(str(self.root / "with-parent")), json.dumps("/tmp/../with-parent")
                ),
                "profile_home",
            ),
            (toml_document([("default", ("", self.root / "home"))]), "profile_label"),
            (toml_document([("default", (" \t ", self.root / "home"))]), "profile_label"),
            (toml_document([("default", ("\u007f", self.root / "home"))]), "profile_label"),
            (toml_document([("default", ("\u200b", self.root / "home"))]), "profile_label"),
            (toml_document([("default", ("x" * 33, self.root / "home"))]), "profile_label"),
            (
                toml_document(
                    [
                        ("default", ("Default", self.root / "default")),
                        ("Work", ("Work", self.root / "work")),
                    ]
                ),
                "profile_id",
            ),
            (
                toml_document([("default", ("Default", self.root / "home"))]).replace(
                    'codex_home = ', 'enabled = true\ncodex_home = '
                ),
                "profile_fields",
            ),
            (
                toml_document([("default", ("Default", self.root / "home"))]).replace(
                    'host = "snap"', 'host = "snap"\nextra = true'
                ),
                "config_fields",
            ),
        )
        for content, error in cases:
            with self.subTest(error=error, content=content), self.assertRaisesRegex(
                HomeProfileConfigError, error
            ):
                self.load(content)

        class StringSubclass(str):
            pass

        with self.assertRaisesRegex(HomeProfileConfigError, "profile_label"):
            home_profiles._route(
                "snap",
                self.uid,
                self.runtime,
                "default",
                {"label": StringSubclass("Default"), "codex_home": str(self.root / "home")},
            )

    def test_labels_accept_printable_nonblank_values_through_32_characters(self):
        route = self.load(
            toml_document([("default", ("x" * 32, self.root / "home"))])
        ).routes[0]
        self.assertEqual(route.label, "x" * 32)

    def test_duplicate_toml_keys_and_ids_are_rejected(self):
        duplicate_key = (
            'version = 1\nversion = 1\nhost = "snap"\n'
            '[profiles.default]\nlabel = "Default"\ncodex_home = "/tmp/home"\n'
        )
        duplicate_id = (
            'version = 1\nhost = "snap"\n'
            '[profiles.default]\nlabel = "Default"\ncodex_home = "/tmp/home"\n'
            '[profiles.work]\nlabel = "Work"\ncodex_home = "/tmp/work"\n'
            '[profiles.work]\nlabel = "Again"\ncodex_home = "/tmp/other"\n'
        )
        for content in (duplicate_key, duplicate_id):
            with self.subTest(content=content), self.assertRaisesRegex(
                HomeProfileConfigError, "config_toml"
            ):
                self.load(content)

    def test_config_file_is_private_regular_bounded_and_not_a_symlink(self):
        valid = toml_document([("default", ("Default", self.root / "home"))])
        with self.assertRaisesRegex(HomeProfileConfigError, "config_file_private"):
            self.load(valid, mode=0o644)

        actual = self.write(valid, name="actual.toml")
        link = self.root / "linked.toml"
        link.symlink_to(actual)
        with self.assertRaises(HomeProfileConfigError):
            load_home_profiles(link, uid=self.uid, runtime_dir=self.runtime)

        oversized = self.write("x" * (64 * 1024 + 1), name="oversized.toml")
        with self.assertRaisesRegex(HomeProfileConfigError, "config_file_size"):
            load_home_profiles(oversized, uid=self.uid, runtime_dir=self.runtime)

        with self.assertRaisesRegex(HomeProfileConfigError, "config_file_type"):
            load_home_profiles(self.root, uid=self.uid, runtime_dir=self.runtime)
        with self.assertRaisesRegex(HomeProfileConfigError, "config_file_owner"):
            load_home_profiles(actual, uid=self.uid + 1, runtime_dir=self.runtime)

        fifo = self.root / "pipe.toml"
        os.mkfifo(fifo, 0o600)
        errors = []

        def load_fifo():
            try:
                load_home_profiles(fifo, uid=self.uid, runtime_dir=self.runtime)
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=load_fifo, daemon=True)
        thread.start()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive(), "non-regular config path must not block")
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], HomeProfileConfigError)
        self.assertEqual(errors[0].code, "config_file_type")

    def test_module_imports_no_mesh_or_native_collection_layer(self):
        source = Path(home_profiles.__file__).read_text(encoding="utf-8")
        imports = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        forbidden = {
            "socket",
            "subprocess",
            "mesh_plus",
            "agent_observer.collection",
            "agent_observer.service_state",
            "agent_observer.service_runtime",
            "agent_observer.providers",
            "agent_observer.codex_snapshot",
        }
        self.assertFalse(forbidden.intersection(imports), imports)

    def test_route_collision_guard_rejects_shared_sockets(self):
        manifest = self.load(
            toml_document(
                [
                    ("default", ("Default", self.root / "default")),
                    ("work", ("Work", self.root / "work")),
                ]
            )
        )
        default, work = manifest.routes
        duplicate = replace(work, collector_socket=default.collector_socket)
        with self.assertRaisesRegex(HomeProfileConfigError, "route_collision"):
            _validate_route_set((default, duplicate))


    def test_profiles_cli_lists_resolved_routes_without_native_reads(self):
        from agent_observer.cli import main

        path = self.write(
            toml_document(
                [
                    ("default", ("Default", self.root / "default")),
                    ("work", ("Work", self.root / "work")),
                ]
            )
        )
        stdout = io.StringIO()
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)}), patch(
            "sys.stdout", stdout
        ):
            self.assertEqual(main(["profiles", "--config", str(path), "--json"]), 0)
        full = json.loads(stdout.getvalue())
        self.assertEqual(full["host"], "snap")
        self.assertEqual([entry["id"] for entry in full["profiles"]], ["default", "work"])
        self.assertEqual(full["profiles"][0]["collector"]["unit"], "agent-observer.service")

        stdout = io.StringIO()
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)}), patch(
            "sys.stdout", stdout
        ):
            self.assertEqual(
                main(["profiles", "--config", str(path), "--profile", "work", "--json"]),
                0,
            )
        selected = json.loads(stdout.getvalue())
        self.assertEqual([entry["id"] for entry in selected["profiles"]], ["work"])
        self.assertEqual(selected["profiles"][0]["mesh"]["source"], "agent_working_set_work")

    def test_profiles_cli_uses_uid_runtime_fallback_without_xdg_runtime_dir(self):
        from agent_observer.cli import main

        path = self.write(toml_document([("default", ("Default", self.root / "home"))]))
        stdout = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", stdout):
            self.assertEqual(main(["profiles", "--config", str(path), "--json"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["runtimeDir"], f"/run/user/{os.getuid()}")

    def test_profiles_cli_accepts_explicit_runtime_dir_override(self):
        from agent_observer.cli import main

        path = self.write(toml_document([("default", ("Default", self.root / "home"))]))
        runtime = self.root / "runtime-override"
        stdout = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", stdout):
            self.assertEqual(
                main([
                    "profiles", "--config", str(path), "--runtime-dir", str(runtime), "--json"
                ]),
                0,
            )
        self.assertEqual(json.loads(stdout.getvalue())["runtimeDir"], str(runtime))


if __name__ == "__main__":
    unittest.main()
