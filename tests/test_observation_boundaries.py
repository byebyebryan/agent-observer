"""Observation authority checks; no providers, terminals or desktop alerts run."""

import ast
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_observer import _hint_worker, _service_worker, cli, collection
from agent_observer.adapters import adapter_for, select_adapters
from agent_observer.service_runtime import Runtime
from agent_observer.service_hints import Hints
from agent_observer.service_state import ServiceState

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "agent_observer"


def dependencies(root):
    pending, seen = [root], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = PACKAGE / (name + ".py")
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.ImportFrom):
                if node.level == 1:
                    modules = [node.module] if node.module else [a.name for a in node.names]
                elif node.module and node.module.startswith("agent_observer."):
                    modules = [node.module.split(".", 1)[1]]
                elif node.module == "agent_observer":
                    modules = [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                modules = [a.name.split(".", 1)[1] for a in node.names
                           if a.name.startswith("agent_observer.")]
            pending.extend(m for m in modules if m)
    return seen


class ObservationBoundaryTest(unittest.TestCase):
    def test_read_and_service_transitive_imports_exclude_actions_and_alerts(self):
        forbidden = {"write_client", "write_contract", "codex_exact",
                     "notification_client", "notification_source"}
        for root in ("public", "service_public", "cli", "service_runtime",
                     "_service_worker", "_hint_worker", "observation_engine",
                     "observation_scheduler", "observation_evidence"):
            with self.subTest(root=root):
                self.assertFalse(dependencies(root) & forbidden)
        pure_forbidden = {"adapters", "collection", "codex_snapshot", "codex_hints",
                          "service_runtime", "_service_worker", "_hint_worker"}
        for root in ("public", "service_public"):
            self.assertFalse(dependencies(root) & pure_forbidden)

    def test_core_engine_has_no_host_transport_or_adapter_imports(self):
        forbidden = {"adapters", "codex_snapshot", "codex_hints", "service_contract",
                     "service_state", "service_runtime", "service_hints"}
        for root in ("observation_engine", "observation_evidence", "observation_scheduler"):
            self.assertFalse(dependencies(root) & forbidden)
            for node in ast.walk(ast.parse((PACKAGE / (root + ".py")).read_text())):
                if isinstance(node, ast.Import):
                    names = {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    names = {node.module.split(".")[0]}
                else:
                    continue
                self.assertFalse(names & {"os", "socket", "subprocess", "time", "uuid", "pathlib"})

    def test_mixed_selection_rejects_before_collecting_any_provider(self):
        with patch("agent_observer.adapters.CodexAdapter.collect") as collect:
            with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                collection.collect(host_scope="fixture", providers=["codex", "claude"],
                                   codex_home="/fixture/codex", claude_home="/fixture/claude")
            collect.assert_not_called()
        for values in ([], ["codex", "codex"], ["unknown"]):
            with self.assertRaisesRegex(ValueError, "invalid_provider_selection"):
                select_adapters(values)
        self.assertEqual(adapter_for("codex").profile.runtime_scope, "daemon_threads")

    def test_private_collector_rejects_unsupported_before_memo_or_provider_io(self):
        request = {"hostScope": "fixture", "provider": "claude", "component": "runtime",
                   "configHome": "/fixture/claude", "configHomeKind": "explicit",
                   "timeoutMs": 1000, "workspaceConfig": None, "imageMemoFd": 99}
        with patch.object(_service_worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(request).encode()))), \
             patch.object(_service_worker.signal, "signal"), \
             patch.object(_service_worker.signal, "setitimer"), \
             patch.object(_service_worker.os, "getpgrp", return_value=os.getpid()), \
             patch.object(_service_worker.os, "getsid", return_value=os.getpid()), \
             patch.object(_service_worker.socket, "socket") as socket:
            with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                _service_worker.main()
            socket.assert_not_called()

    def test_private_feed_rejects_unsupported_before_process_or_native_checks(self):
        request = {"provider": "claude", "configHome": "/fixture/claude",
                   "epoch": "0" * 36, "parentPid": os.getpid()}
        with patch.object(_hint_worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(request).encode()))), \
             patch.object(_hint_worker.signal, "signal"), \
             patch.object(_hint_worker.signal, "setitimer"), \
             patch.object(_hint_worker.os, "getpgrp") as process_check:
            with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                _hint_worker.main()
            process_check.assert_not_called()

    def test_runtime_rejects_unsupported_before_creating_local_endpoint(self):
        state = ServiceState(host_scope="fixture", configs={"claude": ("/fixture/claude", "explicit")})
        with patch("agent_observer.service_runtime.selectors.DefaultSelector") as selector:
            with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                Runtime(state, "/fixture/never-created.sock")
            selector.assert_not_called()

    def test_feed_host_rejects_unsupported_before_starting_helper(self):
        with patch("agent_observer.service_hints.subprocess.Popen") as launch:
            with self.assertRaisesRegex(ValueError, "^unsupported_provider$"):
                Hints({"claude": ("/fixture/claude", "explicit")}, None, None, None)
            launch.assert_not_called()

    def test_removed_history_diagnostic_never_collects(self):
        with patch.object(collection, "collect") as collect, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli.main(["doctor", "--host-scope", "fixture", "--history-census"])
            self.assertEqual(error.exception.code, 2)
            collect.assert_not_called()
