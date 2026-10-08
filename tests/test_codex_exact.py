"""Exact writer preflight is a passive, uncapped native read."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_codex_snapshot import FIRST, SECOND, FakeClient, native

from agent_observer.codex_exact import collect_exact
from agent_observer.codex_metadata import MetadataError


class CodexExactTest(unittest.TestCase):
    def collect(self, client):
        peer = SimpleNamespace(pid=123, uid=1000, endpoint="/endpoint", version="diagnostic",
                               binary_sha256="a" * 64, start_ticks=456)
        with (
            patch("agent_observer.codex_exact.inspect_managed_endpoint", return_value=peer),
            patch("agent_observer.codex_exact._namespace", return_value=("sha256:" + "a" * 64, FIRST)),
            patch("agent_observer.codex_exact.PassiveClient.connect", return_value=client),
            patch("agent_observer.codex_exact.validate_incarnation") as verify,
        ):
            value = collect_exact(Path("/config"), host_scope="host-a", thread_id=FIRST)
            verify.assert_called_once_with(peer)
        return value

    def test_exact_reference_never_lists_or_depends_on_display_cap(self):
        client = FakeClient(None, None)
        client.loaded_threads = lambda **_: self.fail("loaded listing")
        client.list_threads = lambda **_: self.fail("catalog listing")
        client.read_thread = lambda sid: {"thread": {**native(sid), "status": {"type": "notLoaded"}}}
        value = self.collect(client)
        row = value["sessions"][0]
        self.assertEqual(row["identity"]["nativeId"], FIRST)
        self.assertEqual(row["runtime"]["value"], "parked")
        self.assertIsNone(row["phase"])
        self.assertEqual(value["sources"][0]["discovery"]["catalogMode"], "exact_reference")

    def test_returned_other_thread_or_malformed_summary_is_rejected(self):
        for response in ({"thread": native(SECOND)}, None, {"thread": None}):
            with self.subTest(response=response):
                client = FakeClient(None, None)
                client.read_thread = lambda _, response=response: response
                with self.assertRaises(MetadataError):
                    self.collect(client)
