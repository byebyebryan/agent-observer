"""Controlled write-client effects, guards and provider-owned lifetime tests."""

import copy
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.contract import ContractError, store_namespace
from agent_observer.native_artifacts import CODEX
from agent_observer.write_client import execute, invocation, main, prepare, revalidate
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
        self.binary.chmod(0o700)
        self.artifacts = {
            p: (str(self.binary), hashlib.sha256(self.binary.read_bytes()).hexdigest())
            for p in ("codex", "claude")
        }
        self.patch = patch("agent_observer.write_client.EXECUTABLES", {p: a[0] for p, a in self.artifacts.items()})
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
            "schemaVersion": 2,
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
                    "runtime": {"bootId": "fixture-boot", "binarySha256": CODEX.sha256},
                    "coverage": {"saved": {"status": "complete"}},
                }
            ],
            "sessions": [
                {
                    "identity": reference,
                    "kind": "unknown",
                    "metadataIssues": [],
                    "cwd": str(self.cwd),
                    "nativeIds": {"threadId": reference["nativeId"], "sessionTreeRootId": reference["nativeId"]},
                    "phase": None if saved else {"health": "current"},
                    "runtime": {"health": "current"},
                    "inventory": "saved" if saved else "live",
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

    def test_missing_directories_report_exact_context_without_effects(self):
        for field, expected in (("cwd", "cwd_unavailable"), ("configHome", "config_home_unavailable")):
            with self.subTest(field=field):
                request = self.request()
                request[field] = str(self.root / "missing")
                with (patch("agent_observer.write_client._digest") as digest,
                      patch("agent_observer.write_client._collect") as collect,
                      patch("agent_observer.write_client.os.execve") as launch):
                    with self.assertRaisesRegex(ContractError, "^" + expected + "$"):
                        prepare(request)
                    digest.assert_not_called()
                    collect.assert_not_called()
                    launch.assert_not_called()

    def test_missing_context_does_not_relax_canonical_directory_guard(self):
        link = self.root / "alias"
        link.symlink_to(self.cwd, target_is_directory=True)
        request = self.request()
        request["cwd"] = str(link)
        with self.assertRaisesRegex(ContractError, "^noncanonical_directory$"):
            prepare(request)

    def test_public_write_fixtures_and_false_effect_claims(self):
        root = Path(__file__).parent / "fixtures/write-v2"
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
            patch("agent_observer.write_client.os.execve") as launch,
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


    def test_prepared_result_rejects_false_targets_and_inconsistent_routes(self):
        root = Path(__file__).parent / "fixtures/write-v2"
        prepared = json.loads((root / "result.json").read_text())
        for mutate in (
            lambda v: v.update(resultingIdentity=self.request(operation="resume")["reference"]),
            lambda v: v.update(requestedIdentity=self.request(operation="resume")["reference"]),
            lambda v: v.update(identityPending=False),
            lambda v: v.update(status="rejected"),
            lambda v: v["handoff"].update(route="claude_new"),
            lambda v: v["handoff"].update(createdAt=None),
        ):
            changed = copy.deepcopy(prepared)
            mutate(changed)
            with self.assertRaises(ContractError):
                validate_result(changed)

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
            with patch("agent_observer.write_client.os.execve") as launch:
                with self.assertRaises(ContractError):
                    execute(plan)
                launch.assert_not_called()
        self.binary.write_bytes(b"fixture binary")
        plan = prepare(self.request())
        plan["route"] = "claude_attach"
        with self.assertRaises(ContractError):
            revalidate(plan)

    def test_exact_codex_resume_uses_thread_id(self):
        request = self.request(operation="resume")
        snapshot = self.snapshot(request)
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
                snapshot["sessions"][0]["nativeIds"]["threadId"],
            ],
        )














    def test_literal_json_public_prepare_execute_and_non_tty_entry(self):
        request = self.request()
        output = io.StringIO()
        with patch("sys.stdout", output):
            self.assertEqual(main(["prepare", "--request-json", json.dumps(request)]), 0)
        plan = json.loads(output.getvalue())
        output = io.StringIO()
        with patch("sys.stdout", output), patch("agent_observer.write_client.os.execve") as launch:
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

    def test_distinct_tree_root_tui_target_requires_separate_native_proof(self):
        request = self.request(operation="resume")
        snapshot = self.snapshot(request)
        snapshot["sessions"][0]["nativeIds"]["sessionTreeRootId"] = "00000000-0000-0000-0000-000000000099"
        collect, select = self.targeted(request, snapshot)
        with collect, select, patch("agent_observer.write_client.os.execve") as launch:
            with self.assertRaisesRegex(ContractError, "^session_tree_entry_unproved$"):
                prepare(request)
            launch.assert_not_called()

    def test_claude_and_old_writer_wire_are_rejected_before_observation(self):
        with patch("agent_observer.write_client._collect") as collect:
            with self.assertRaisesRegex(ContractError, "^unsupported_provider$"):
                prepare(self.request("claude"))
            old = self.request()
            old["schemaVersion"] = 1
            with self.assertRaises(ContractError):
                prepare(old)
            collect.assert_not_called()

    def test_runtime_disposition_change_does_not_invalidate_exact_identity_guard(self):
        request = self.request(operation="resume")
        collect, select = self.targeted(request)
        with collect, select:
            plan = prepare(request)
        collect, select = self.targeted(request, self.snapshot(request, saved=True))
        with collect, select:
            revalidate(plan)
