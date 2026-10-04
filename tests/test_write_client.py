"""Controlled write-client effects, guards and provider-owned lifetime tests."""

import copy
import hashlib
import io
import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.contract import ContractError, store_namespace
from agent_observer.write_client import _launch, execute, invocation, main, prepare, revalidate
from agent_observer.write_contract import (
    schema_document,
    validate_plan,
    validate_request,
    validate_result,
)


class WriteClientTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cwd = self.root / "project"
        self.cwd.mkdir()
        self.home = self.root / "config"
        self.home.mkdir()
        self.binary = self.root / "native"
        self.binary.write_bytes(b"fixture binary")
        self.artifacts = {
            p: (str(self.binary), hashlib.sha256(self.binary.read_bytes()).hexdigest())
            for p in ("codex", "claude")
        }
        self.patch = patch("agent_observer.write_client.ARTIFACTS", self.artifacts)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def request(self, provider="codex", operation="new"):
        reference = (
            {
                "hostScope": "fixture",
                "provider": provider,
                "namespace": store_namespace(provider, str(self.home), "explicit", os.geteuid()),
                "nativeIdKind": "thread" if provider == "codex" else "session",
                "nativeId": "00000000-0000-0000-0000-000000000001",
            }
            if operation == "resume"
            else None
        )
        return {
            "schemaVersion": 1,
            "operation": operation,
            "hostScope": "fixture",
            "provider": provider,
            "configHome": str(self.home),
            "configHomeKind": "explicit",
            "cwd": str(self.cwd),
            "reference": reference,
        }

    def snapshot(self, request, *, saved=False, actual=None):
        reference = (
            actual
            or request["reference"]
            or {
                **self.request("claude", "resume")["reference"],
                "nativeId": "00000000-0000-0000-0000-000000000002",
            }
        )
        return {
            "sources": [
                {
                    "provider": request["provider"],
                    "namespace": reference["namespace"],
                    "runtimeNamespace": "fixture-runtime",
                    "configHome": str(self.home),
                    "configHomeKind": "explicit",
                    "sourceHealth": "current",
                    "runtime": {"bootId": "fixture-boot"},
                    "coverage": {"saved": {"status": "complete"}},
                }
            ],
            "sessions": [
                {
                    "identity": reference,
                    "kind": "unknown",
                    "metadataIssues": [],
                    "cwd": str(self.cwd),
                    "nativeIds": {
                        "threadId": reference["nativeId"]
                        if request["provider"] == "codex"
                        else None,
                        "sessionId": reference["nativeId"],
                        "jobId": None if saved or request["provider"] == "codex" else "abcd1234",
                    },
                    "phase": {"health": "current"},
                    "runtime": {"health": "current"},
                    "worker": {"value": "unknown" if saved else "present", "health": "current"},
                    "sessionKind": "unknown" if saved else "bg",
                    "inventory": "saved" if saved else "live",
                    "history": {"source": "claude_sdk"} if saved else None,
                    "job": None,
                }
            ],
        }

    def targeted(self, request, snapshot=None):
        # The write layer consumes a previously validated public snapshot. The
        # select test double avoids conflating these guards with schema tests.
        value = snapshot or self.snapshot(request)
        return patch("agent_observer.write_client._collect", return_value=value), patch(
            "agent_observer.write_client.select_session", return_value=value["sessions"][0]
        )

    def test_bundled_write_schemas_and_request_constraints(self):
        root = Path(__file__).parent.parent / "agent_observer/contracts"
        for name in ("request", "plan", "result"):
            self.assertEqual(
                json.loads((root / f"write-{name}.schema.json").read_text()), schema_document(name)
            )
        request = self.request()
        validate_request(request)
        request["reference"] = self.request(operation="resume")["reference"]
        with self.assertRaises(ContractError):
            validate_request(request)

    def test_public_write_fixtures_and_false_effect_claims(self):
        root = Path(__file__).parent / "fixtures/write-v1"
        request = json.loads((root / "request.json").read_text())
        plan = json.loads((root / "plan.json").read_text())
        output = json.loads((root / "result.json").read_text())
        validate_request(request)
        validate_plan(plan)
        validate_result(output)
        for mutate in (
            lambda v: v.update(effect="confirmed"),
            lambda v: v.update(effect="uncertain"),
            lambda v: v.update(status="ready"),
        ):
            value = copy.deepcopy(output)
            mutate(value)
            with self.assertRaises(ContractError):
                validate_result(value)

    def test_new_without_any_rows_is_passive_until_native_tty_entry(self):
        with (
            patch("agent_observer.write_client._collect") as collect,
            patch("agent_observer.write_client._launch") as launch,
        ):
            plan = prepare(self.request())
            output = execute(plan)
            self.assertEqual(output["status"], "prepared")
            self.assertEqual(output["effect"], "none")
            self.assertTrue(output["identityPending"])
            validate_result(output)
            collect.assert_not_called()
            launch.assert_not_called()
        argv, env = invocation(plan)
        self.assertEqual(argv, [str(self.binary)])
        self.assertEqual(env["CODEX_HOME"], str(self.home))

    def test_changed_binary_cwd_settings_or_injected_route_rejected_before_dispatch(self):
        mutations = [
            lambda: self.binary.write_bytes(b"replacement"),
            lambda: (self.cwd.rename(self.root / "old"), self.cwd.mkdir()),
            lambda: (self.home / "config.toml").write_text("changed=true\n"),
        ]
        for mutate in mutations:
            self.binary.write_bytes(b"fixture binary")
            (self.home / "config.toml").unlink(missing_ok=True)
            plan = prepare(self.request())
            mutate()
            with patch("agent_observer.write_client._launch") as launch:
                with self.assertRaises(ContractError):
                    execute(plan)
                launch.assert_not_called()
        self.binary.write_bytes(b"fixture binary")
        plan = prepare(self.request())
        plan["route"] = "claude_attach"
        with self.assertRaises(ContractError):
            revalidate(plan)

    def test_exact_codex_resume_uses_native_session_field_and_absolute_binary(self):
        request = self.request(operation="resume")
        snapshot = self.snapshot(request)
        snapshot["sessions"][0]["nativeIds"]["sessionId"] = "00000000-0000-0000-0000-000000000099"
        collect, select = self.targeted(request, snapshot)
        with collect, select:
            plan = prepare(request)
            argv, _ = invocation(plan)
        self.assertEqual(
            argv,
            [
                str(self.binary),
                "resume",
                "--all",
                snapshot["sessions"][0]["nativeIds"]["sessionId"],
            ],
        )

    def test_live_claude_attaches_typed_job_and_does_not_create(self):
        request = self.request("claude", "resume")
        collect, select = self.targeted(request)
        with collect, select, patch("agent_observer.write_client._launch") as launch:
            plan = prepare(request)
            output = execute(plan)
            argv, _ = invocation(plan)
            self.assertEqual(argv[-2:], ["attach", "abcd1234"])
            self.assertEqual(output["effect"], "none")
            launch.assert_not_called()

    def test_background_timeout_or_post_launch_failure_is_uncertain_and_never_retried(self):
        plan = prepare(self.request("claude"))
        for outcome in (
            (
                0,
                "backgrounded · abcd1234\n  claude attach abcd1234  open in this terminal\n".encode(),
                "launcher_timeout",
            ),
            (1, b"", None),
            (0, b"ambiguous", None),
        ):
            with patch("agent_observer.write_client._launch", return_value=outcome) as launch:
                result = execute(plan, timeout=1)
                self.assertEqual(result["status"], "uncertain")
                self.assertEqual(result["effect"], "uncertain")
                launch.assert_called_once()
        with (
            patch(
                "agent_observer.write_client._launch",
                return_value=(
                    0,
                    "backgrounded · abcd1234\n  claude attach abcd1234  open in this terminal\n".encode(),
                    None,
                ),
            ) as launch,
            patch(
                "agent_observer.write_client._collect",
                side_effect=ContractError("source_unavailable"),
            ),
        ):
            result = execute(plan, timeout=1)
            self.assertEqual(result["effect"], "uncertain")
            launch.assert_called_once()

    def test_saved_resume_preserves_requested_and_copied_result_identity(self):
        request = self.request("claude", "resume")
        saved = self.snapshot(request, saved=True)
        collect, select = self.targeted(request, saved)
        with collect, select:
            plan = prepare(request)
            self.assertEqual(plan["route"], "claude_saved_resume")
            argv, _ = invocation(plan, background=True)
            self.assertEqual(argv[-3:], ["--resume", request["reference"]["nativeId"], "--bg"])
        actual = {**request["reference"], "nativeId": "00000000-0000-0000-0000-000000000099"}
        created = self.snapshot(request, actual=actual)
        with (
            patch("agent_observer.write_client.revalidate", return_value=plan),
            patch(
                "agent_observer.write_client._launch",
                return_value=(
                    0,
                    "backgrounded · abcd1234\n  claude attach abcd1234  open in this terminal\n".encode(),
                    None,
                ),
            ) as launch,
            patch("agent_observer.write_client._collect", return_value=created),
            patch(
                "agent_observer.write_client.select_session", return_value=created["sessions"][0]
            ),
        ):
            result = execute(plan, timeout=1)
            self.assertEqual(result["requestedIdentity"], request["reference"])
            self.assertEqual(result["resultingIdentity"], actual)
            self.assertEqual(result["effect"], "confirmed")
            launch.assert_called_once()

    def test_launcher_timeout_preserves_descendant_outside_launcher_ownership(self):
        marker = self.root / "owned-child.pid"
        program = "import subprocess,sys,time; from pathlib import Path; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(30)"
        code, _, reason = _launch(
            [sys.executable, "-c", program, str(marker)], os.environ.copy(), str(self.cwd), 0.3
        )
        self.assertEqual(reason, "launcher_timeout")
        child = int(marker.read_text())
        try:
            os.kill(child, 0)
        finally:
            os.kill(child, signal.SIGKILL)

    def test_handoff_failure_after_verified_creation_keeps_confirmed_effect(self):
        request = self.request("claude")
        plan = prepare(request)
        created = self.snapshot(request)
        with (
            patch("agent_observer.write_client.revalidate", return_value=plan),
            patch(
                "agent_observer.write_client._launch",
                return_value=(
                    0,
                    "backgrounded · abcd1234\n  claude attach abcd1234  open in this terminal\n".encode(),
                    None,
                ),
            ) as launch,
            patch("agent_observer.write_client._collect", return_value=created),
            patch(
                "agent_observer.write_client.prepare", side_effect=ContractError("artifact_changed")
            ),
        ):
            output = execute(plan, timeout=1)
        self.assertEqual(output["effect"], "confirmed")
        self.assertEqual(output["reason"], "handoff_unavailable")
        self.assertEqual(output["resultingIdentity"], created["sessions"][0]["identity"])
        self.assertIsNone(output["handoff"])
        self.assertFalse(output["identityPending"])
        launch.assert_called_once()

    def test_io_failure_after_possible_dispatch_cannot_claim_no_effect(self):
        plan = prepare(self.request("claude"))
        with patch(
            "agent_observer.write_client._launch",
            side_effect=OSError("private output must not leak"),
        ) as launch:
            output = execute(plan, timeout=1)
        self.assertEqual(output["effect"], "uncertain")
        self.assertEqual(output["reason"], "launcher_io_failed")
        launch.assert_called_once()

    def test_literal_json_public_prepare_execute_and_non_tty_entry(self):
        request = self.request()
        output = io.StringIO()
        with patch("sys.stdout", output):
            self.assertEqual(main(["prepare", "--request-json", json.dumps(request)]), 0)
        plan = json.loads(output.getvalue())
        output = io.StringIO()
        with patch("sys.stdout", output), patch("agent_observer.write_client._launch") as launch:
            self.assertEqual(main(["execute", "--plan-json", json.dumps(plan)]), 0)
            launch.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["effect"], "none")
        output = io.StringIO()
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stderr", output),
            patch("os.execve") as native,
        ):
            self.assertEqual(main(["enter", "--plan-json", json.dumps(plan)]), 2)
            native.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["error"], "tty_required")
