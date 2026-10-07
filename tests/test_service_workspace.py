"""Startup configuration, owned-worker projection and history lease boundaries."""

import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_service_runtime import scoped_snapshot

from agent_observer import _service_worker
from agent_observer.contract import canonical, parse_snapshot
from agent_observer.service_cli import serve
from agent_observer.service_runtime import Runtime
from agent_observer.service_scheduler import Job
from agent_observer.service_state import ServiceState
from agent_observer.workspace import MAX_CONFIG_BYTES, enrich, load_config


class ServiceWorkspaceTest(unittest.TestCase):
    def state(self, clock=None):
        options = {"clock": clock} if clock else {}
        return ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")}, **options)

    def worker(self, request, snapshot):
        output = io.StringIO()
        with patch.object(_service_worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(canonical(request).encode()))), \
             patch.object(_service_worker.sys, "stdout", output), \
             patch.object(_service_worker.signal, "signal"), \
             patch.object(_service_worker.signal, "setitimer"), \
             patch.object(_service_worker.os, "getpgrp", return_value=os.getpid()), \
             patch.object(_service_worker.os, "getsid", return_value=os.getpid()), \
             patch("agent_observer.codex_snapshot.collect_codex", return_value={}) as collect, \
             patch("agent_observer.collection.compose_snapshot", return_value=copy.deepcopy(snapshot)):
            self.assertEqual(_service_worker.main(), 0)
        return parse_snapshot(output.getvalue().encode()), collect

    def request(self, component, config):
        return {"hostScope": "fixture", "provider": "codex", "component": component,
                "configHome": "/fixture/codex", "configHomeKind": "explicit",
                "timeoutMs": 1000, "workspaceConfig": config}

    def test_history_worker_matches_direct_mapping_and_runtime_cannot_renew_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            (repo / ".git").mkdir(parents=True)
            cwd = repo / "src"
            cwd.mkdir()
            config = {"roots": [{"key": "code", "path": directory}],
                      "projects": [{"rootKey": "code", "relativePath": "repo", "projectKey": "observer"}]}
            value = scoped_snapshot()
            value["sessions"][0]["cwd"] = str(cwd)
            value["sessions"][0]["workspace"] = None
            direct = copy.deepcopy(value)
            enrich(direct, config)
            history, collect = self.worker(self.request("history", config), value)
            self.assertEqual(history["sessions"][0]["workspace"], direct["sessions"][0]["workspace"])
            self.assertEqual(history["sessions"][0]["workspace"]["projectKey"], "observer")
            self.assertEqual(history["sessions"][0]["workspace"]["relativePath"], "repo/src")
            self.assertEqual(history["sessions"][0]["workspace"]["repo"]["root"], str(repo))
            self.assertTrue(collect.call_args.kwargs["include_history"])
            runtime, collect = self.worker(self.request("runtime", None), value)
            self.assertIsNone(runtime["sessions"][0]["workspace"])
            self.assertFalse(collect.call_args.kwargs["include_history"])
            now = [15000]
            state = self.state(lambda: now[0])
            state.attempt("codex", "history")
            state.accept("codex", "history", history, sampled_ms=now[0], ttl_ms=1000)
            state.attempt("codex", "runtime")
            state.accept("codex", "runtime", runtime, sampled_ms=now[0], ttl_ms=5000)
            self.assertEqual(state.snapshot["sessions"][0]["workspace"], direct["sessions"][0]["workspace"])
            now[0] += 1001
            state.attempt("codex", "runtime")
            state.accept("codex", "runtime", runtime, sampled_ms=now[0], ttl_ms=5000)
            self.assertIsNone(state.frame("view", 1)["snapshot"]["sessions"][0]["workspace"])

    def test_startup_value_is_frozen_and_large_configuration_fits_worker_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            config = {"roots": [{"key": "r" + str(n), "path": "/" + "x" * 900 + "/" + str(n)} for n in range(32)], "projects": []}
            path.write_text(json.dumps(config))
            loaded = load_config(path)
            runtime = Runtime(self.state(), "/unused/read.sock", collect=False, workspace_config=loaded)
            try:
                loaded["roots"].clear()
                path.write_text('{"roots":[],"projects":[]}')
                process = Mock()
                with patch("agent_observer.service_runtime.subprocess.Popen", return_value=process):
                    runtime._spawn(Job("codex", "history", 0, 1000, 0, 0))
                wire = process.stdin.write.call_args.args[0]
                self.assertGreater(len(wire), 16384)
                self.assertLess(len(wire), MAX_CONFIG_BYTES + 16384)
                self.assertEqual(json.loads(wire)["workspaceConfig"], config)
                projected, _ = self.worker(json.loads(wire), scoped_snapshot())
                self.assertEqual(len(projected["sessions"]), len(scoped_snapshot()["sessions"]))
                process.reset_mock()
                with patch("agent_observer.service_runtime.subprocess.Popen", return_value=process):
                    runtime._spawn(Job("codex", "runtime", 0, 1000, 0, 0))
                self.assertIsNone(json.loads(process.stdin.write.call_args.args[0])["workspaceConfig"])
            finally:
                runtime.selector.close()

    def test_invalid_configuration_fails_before_endpoint_or_provider_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "workspace.json"
            config.write_text('{"roots":[],"projects":[{"rootKey":"absent","relativePath":"repo","projectKey":"bad"}]}')
            socket = root / "read.sock"
            error = io.StringIO()
            with patch("agent_observer.service_runtime.Runtime") as runtime, patch("sys.stderr", error):
                code = serve(["serve", "--host-scope", "fixture", "--provider", "codex",
                              "--workspace-config", str(config), "--socket", str(socket)])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(error.getvalue())["error"], "invalid_project_mapping")
            runtime.assert_not_called()
            self.assertFalse(socket.exists())

    def test_oversized_or_nonregular_config_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            path.write_bytes(b" " * (MAX_CONFIG_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "workspace_config_limit"):
                load_config(path)
            path.unlink()
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, "workspace_config_file_required"):
                load_config(path)

    def test_untrusted_runtime_workspace_is_rejected_before_native_read(self):
        request = self.request("runtime", {"roots": [], "projects": []})
        with patch("agent_observer.codex_snapshot.collect_codex") as collect:
            with self.assertRaisesRegex(ValueError, "service_worker_workspace_scope"):
                self.worker(request, scoped_snapshot())
        collect.assert_not_called()
