"""Private consumer config and exact source-selection tests."""

import os
import tempfile
import unittest
from pathlib import Path

from agent_observer.terminal.config import (
    TerminalConfigError,
    load_config,
    parse_config,
    select_sources,
)


def source(index=0, **updates):
    values = {
        "id": f"source-{index}",
        "host": f"host-{index}",
        "home": "default",
        "label": f"Home {index}",
        "mesh_source": f"agent_working_set_{index}",
        "scope": "local",
        "socket": f"/run/user/1000/mesh-{index}.sock",
        "namespace": "sha256:" + f"{index:064x}",
        "window_hours": 72,
    }
    values.update(updates)
    return values


def document(sources=None, defaults=None):
    sources = [source()] if sources is None else sources
    return {
        "version": 1,
        "default_sources": [item["id"] for item in sources] if defaults is None else defaults,
        "sources": sources,
    }


class TerminalConfigTests(unittest.TestCase):
    def test_explicit_sources_defaults_and_or_and_selection(self):
        routes = [source(0), source(1, home="work", scope="hosts")]
        config = parse_config(document(routes, ["source-0"]), path=Path("/fixture/config.toml"))
        self.assertEqual([item.id for item in select_sources(config)], ["source-0"])
        self.assertEqual(
            [item.id for item in select_sources(config, source_ids=("source-0", "source-1"))],
            ["source-0", "source-1"],
        )
        self.assertEqual(
            [item.id for item in select_sources(config, hosts=("host-1",), homes=("work",))],
            ["source-1"],
        )

    def test_malformed_scope_and_socket_values_are_stable_config_errors(self):
        for updates, code in (
            ({"scope": []}, "source_scope"),
            ({"scope": {}}, "source_scope"),
            ({"socket": "/run/user/1000/mesh\x00.sock"}, "source_socket"),
            ({"socket": "relative.sock"}, "source_socket"),
        ):
            with self.subTest(code=code, value=updates):
                with self.assertRaises(TerminalConfigError) as caught:
                    parse_config(document([source(**updates)]), path=Path("/fixture/config.toml"))
                self.assertEqual(caught.exception.code, code)

    def test_route_identity_and_aggregate_reservations_are_bounded(self):
        duplicate_home = [source(0), source(1, host="host-0", mesh_source="other")]
        with self.assertRaisesRegex(TerminalConfigError, "config_duplicate_host_home"):
            parse_config(document(duplicate_home), path=Path("/fixture/config.toml"))

        duplicate_route = [
            source(0),
            source(1, host="host-0", home="work", mesh_source="agent_working_set_0"),
        ]
        with self.assertRaisesRegex(TerminalConfigError, "config_duplicate_route"):
            parse_config(document(duplicate_route), path=Path("/fixture/config.toml"))

        too_many = [source(index, max_identities=2048) for index in range(5)]
        with self.assertRaisesRegex(TerminalConfigError, "config_identity_budget"):
            parse_config(document(too_many), path=Path("/fixture/config.toml"))

        eight = [source(index) for index in range(8)]
        config = parse_config(document(eight), path=Path("/fixture/config.toml"))
        self.assertEqual(len(config.sources), 8)

    def test_unknown_and_empty_selection_fail_closed(self):
        config = parse_config(
            document([source(0), source(1, home="work")]), path=Path("/fixture/config.toml")
        )
        with self.assertRaisesRegex(TerminalConfigError, "source_selector_unknown"):
            select_sources(config, hosts=("unconfigured",))
        with self.assertRaisesRegex(TerminalConfigError, "source_selection_empty"):
            select_sources(config, source_ids=("source-0",), homes=("work",))

    def test_private_file_loading_and_symlink_rejection(self):
        text = """version = 1\ndefault_sources = ["source-0"]\n\n[[sources]]\nid = "source-0"\nhost = "host-0"\nhome = "default"\nlabel = "Home"\nmesh_source = "agent_working_set"\nscope = "local"\nsocket = "/run/user/1000/mesh.sock"\nnamespace = "sha256:0000000000000000000000000000000000000000000000000000000000000000"\nwindow_hours = 72\n"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terminal.toml"
            path.write_text(text)
            path.chmod(0o600)
            loaded = load_config(path, uid=os.geteuid())
            self.assertEqual(loaded.sources[0].mesh_source, "agent_working_set")
            link = Path(directory) / "linked.toml"
            link.symlink_to(path)
            with self.assertRaises(TerminalConfigError):
                load_config(link, uid=os.geteuid())


if __name__ == "__main__":
    unittest.main()
