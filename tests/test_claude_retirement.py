"""Retired native paths reject before I/O; reserved wire data remain readable."""

import ast
import contextlib
import hashlib
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent_observer import _service_worker, cli, collection, service_cli
from agent_observer.adapters import adapter_for
from agent_observer.notification_source import NotificationError, normalize
from agent_observer.public import parse_snapshot

ROOT = Path(__file__).resolve().parents[1]


class ClaudeRetirementTest(unittest.TestCase):
    def test_retired_and_mixed_native_selection_never_collect(self):
        with patch("agent_observer.adapters.CodexAdapter.collect") as read:
            for providers in (["claude"], ["codex", "claude"]):
                with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                    collection.collect(host_scope="fixture", providers=providers, codex_home="/absent")
            read.assert_not_called()
        with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
            adapter_for("claude")

    def test_cli_and_service_reject_retired_provider_before_collection(self):
        cases = [(cli.main, ["snapshot", "--host-scope", "fixture", "--provider", "claude"]),
                 (service_cli.serve, ["serve", "--host-scope", "fixture", "--provider", "claude"])]
        with patch("agent_observer.adapters.CodexAdapter.collect") as read:
            for main, argv in cases:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main(argv)
                self.assertEqual(error.exception.code, 2)
            read.assert_not_called()

    def test_removed_private_memo_transport_rejects_before_descriptor_access(self):
        request = {"hostScope": "fixture", "provider": "codex", "component": "runtime",
                   "configHome": "/absent", "configHomeKind": "explicit", "timeoutMs": 1000,
                   "workspaceConfig": None, "claudeMemoFd": 999}
        with patch.object(_service_worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(request).encode()))), \
             patch.object(_service_worker.signal, "signal"), \
             patch.object(_service_worker.signal, "setitimer"), \
             patch.object(_service_worker.os, "close") as close:
            with self.assertRaisesRegex(ValueError, "^service_worker_request$"):
                _service_worker.main()
            close.assert_not_called()

    def test_notification_native_intake_rejects_retired_before_decoding_content(self):
        snapshot = parse_snapshot((ROOT / "tests/fixtures/contract-v5/snapshot.json").read_bytes())
        ref = next(r["identity"] for r in snapshot["sessions"] if r["identity"]["provider"] == "claude")
        with self.assertRaisesRegex(NotificationError, "^unsupported_provider$"):
            normalize(b"invalid private contents", ref)

    def test_reserved_data_and_read_wire_are_preserved_without_native_implementation(self):
        snapshot = parse_snapshot((ROOT / "tests/fixtures/contract-v5/snapshot.json").read_bytes())
        self.assertTrue(any(r["identity"]["provider"] == "claude" for r in snapshot["sessions"]))
        package = ROOT / "agent_observer"
        self.assertFalse(any(p.name.startswith(("claude_", "_claude_")) for p in package.glob("*.py")))
        for p in package.glob("*.py"):
            for node in ast.walk(ast.parse(p.read_text())):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("claude", node.module or "")
                elif isinstance(node, ast.Import):
                    self.assertFalse(any("claude" in a.name for a in node.names))
        # Historical wire 4 a17 bytes stay frozen; wire 5 has a separate schema.
        frozen = {'snapshot.schema.json': '95ba9e3ef4ad5dc059f7a344b5946ea59193a9b061b7d747927d6aceb2eb0e39', 'watch.schema.json': 'c4c4a8e61a85e4260d2791bf9df48c116076232323b76e63c191a137739a4e97', 'service-frame.schema.json': 'f43ebea80a47f9db2379a576ca089fde25994e4229606473e5937f1379cbb984'}
        for name, digest in frozen.items():
            self.assertEqual(digest, hashlib.sha256((ROOT / "tests/fixtures/contract-v4" / name).read_bytes()).hexdigest())
