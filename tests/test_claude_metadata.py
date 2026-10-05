"""Synthetic tests for the provisional, private Claude metadata projection."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import claude_metadata
from agent_observer.claude_metadata import (
    SUPPORTED_SHA256,
    SUPPORTED_VERSION,
    linux_pid_domain,
    snapshot,
)


class ClaudeMetadataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sessions").mkdir()
        (self.root / "jobs").mkdir()
        self.scope = {
            "host_scope": "snap-host",
            "namespace": "private-config",
            "runtime_version": SUPPORTED_VERSION,
            "binary_sha256": SUPPORTED_SHA256,
        }
        self.domain = "linux:0123456789abcdef0123456789abcdef:pid:[4026531836]"

    def tearDown(self):
        self.temp.cleanup()

    def write_session(
        self,
        *,
        pid=23145,
        session_id="11234567-0123-4567-89ab-0123456789ab",
        job_id=None,
        status="busy",
        status_updated_at=111,
        proc_start="67890",
        pid_domain=None,
        **extra,
    ):
        row = {
            "pid": pid,
            "sessionId": session_id,
            "procStart": proc_start,
            "pidDomain": pid_domain or self.domain,
            "kind": "interactive" if job_id is None else "bg",
            "status": status,
            "statusUpdatedAt": status_updated_at,
            "updatedAt": 999999,
            "cwd": "/same/checkout",
            "name": "SYNTHETIC_PRIVATE_NAME",
            "detail": "SYNTHETIC_PRIVATE_DETAIL",
            "prompt": "SYNTHETIC_PRIVATE_PROMPT",
            "needs": {"question": "SYNTHETIC_PRIVATE_NEED"},
            "waitingFor": "dialog:SYNTHETIC_PRIVATE_QUESTION",
            **extra,
        }
        if job_id is not None:
            row["jobId"] = job_id
        self.write_json(self.root / "sessions" / f"{pid}.json", row)
        return row

    def write_job(
        self,
        job_id="abcdef01",
        *,
        session_id="11234567-0123-4567-89ab-0123456789ab",
        state="working",
        tempo="active",
        **extra,
    ):
        row = {
            "sessionId": session_id,
            "state": state,
            "tempo": tempo,
            "updatedAt": 999999,
            "createdAt": "2026-10-02T00:00:00Z",
            "cwd": "/same/checkout",
            "name": "SYNTHETIC_PRIVATE_JOB_NAME",
            "detail": "SYNTHETIC_PRIVATE_JOB_DETAIL",
            "providerEnv": {"TOKEN": "SYNTHETIC_PRIVATE_CREDENTIAL"},
            "prompt": "SYNTHETIC_PRIVATE_JOB_PROMPT",
            "needs": {"secret": "SYNTHETIC_PRIVATE_NEED"},
            "output": "SYNTHETIC_PRIVATE_OUTPUT",
            "block": {"questions": ["SYNTHETIC_PRIVATE_QUESTION"]},
            "tool": {"arguments": "SYNTHETIC_PRIVATE_TOOL_ARGUMENT"},
            **extra,
        }
        directory = self.root / "jobs" / job_id
        directory.mkdir()
        self.write_json(directory / "state.json", row)
        return row

    @staticmethod
    def write_json(path, row):
        path.write_text(json.dumps(row), encoding="utf-8")

    def read(self, *, executable_match=True):
        with (
            patch("agent_observer.claude_metadata._current_pid_domain", return_value=self.domain),
            patch("agent_observer.claude_metadata.time.time_ns", return_value=5_000_000_000),
            patch(
                "agent_observer.claude_metadata._linux_process_uses_supported_binary",
                return_value=(
                    executable_match,
                    "matched" if executable_match else "different_binary",
                ),
            ),
        ):
            return snapshot(self.root, **self.scope)

    def test_runtime_gate_refuses_unknown_version_or_digest_before_reads(self):
        result = snapshot(
            self.root / "does-not-exist",
            **{**self.scope, "runtime_version": "2.1.288"},
        )
        self.assertFalse(result["supported"])
        self.assertEqual(result["errors"], [{"code": "unsupported_runtime_version"}])
        result = snapshot(
            self.root / "does-not-exist",
            **{**self.scope, "binary_sha256": "0" * 64},
        )
        self.assertFalse(result["supported"])
        self.assertEqual(result["errors"], [{"code": "unsupported_runtime_digest"}])

    def test_linux_pid_domain_matches_exact_installed_formula(self):
        self.assertEqual(
            linux_pid_domain("0123456789abcdef0123456789abcdef", "pid:[4026531836]"),
            self.domain,
        )
        self.assertEqual(
            linux_pid_domain("", "pid:[4026531836]"),
            "linux::pid:[4026531836]",
        )
        self.assertIsNone(linux_pid_domain("not-a-machine-id", "pid:[4026531836]"))
        self.assertIsNone(linux_pid_domain("0" * 32, "pid:[bad]"))
        with (
            patch("agent_observer.claude_metadata.sys.platform", "linux"),
            patch("agent_observer.claude_metadata.os.open", side_effect=FileNotFoundError),
            patch("agent_observer.claude_metadata.os.readlink", return_value="pid:[4026531836]"),
        ):
            self.assertEqual(
                claude_metadata._current_pid_domain(),
                "linux::pid:[4026531836]",
            )

    def test_live_status_clock_is_preserved_and_payload_text_is_filtered(self):
        self.write_session(status="busy", status_updated_at=111)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            result = self.read()
        item = result["observations"][0]
        self.assertEqual(item["work"]["value"], "working")
        self.assertEqual(item["work"]["observedAt"], 111)
        self.assertEqual(item["presence"]["observedAt"], 5000)
        self.assertEqual(item["attachment"]["value"], "unknown")
        self.assertEqual(item["title"], "Claude 11234567-0123-4567-89ab-0123456789ab")
        self.assertEqual(item["nativeStatus"]["observedAt"], 111)
        self.assertEqual(item["cwd"], "/same/checkout")
        self.assertEqual(item["cwdSource"], "claude_registry")
        encoded = json.dumps(result)
        for secret in (
            "SYNTHETIC_PRIVATE_NAME",
            "SYNTHETIC_PRIVATE_DETAIL",
            "SYNTHETIC_PRIVATE_PROMPT",
            "SYNTHETIC_PRIVATE_NEED",
            "SYNTHETIC_PRIVATE_QUESTION",
            "SYNTHETIC_PRIVATE_CREDENTIAL",
            "SYNTHETIC_PRIVATE_OUTPUT",
            "SYNTHETIC_PRIVATE_TOOL_ARGUMENT",
            "999999",
        ):
            self.assertNotIn(secret, encoded)

    def test_user_assigned_registry_title_is_bounded_without_changing_identity(self):
        self.write_session(name="  Native\nSession\x00Name  " + "x" * 300, nameSource="user")
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            result = self.read()
        item = result["observations"][0]
        self.assertTrue(item["title"].startswith("Native Session Name "))
        self.assertEqual(len(item["title"]), 256)
        self.assertEqual(item["identity"]["nativeId"], "11234567-0123-4567-89ab-0123456789ab")
        self.assertEqual(item["work"]["observedAt"], 111)
        self.assertNotIn("SYNTHETIC_PRIVATE_PROMPT", json.dumps(result))

    def test_unproved_name_sources_and_empty_names_keep_id_fallback(self):
        for source in (None, "auto", "derived", "collision", "peer", "hook", "unknown", []):
            with self.subTest(source=source):
                self.write_session(name="SYNTHETIC_PRIVATE_TASK_NAME", nameSource=source)
                result = self.read()
                self.assertEqual(
                    result["observations"][0]["title"],
                    "Claude 11234567-0123-4567-89ab-0123456789ab",
                )
                self.assertNotIn("SYNTHETIC_PRIVATE_TASK_NAME", json.dumps(result))
        for name in (None, True, [], "", " \n\x00\t "):
            with self.subTest(name=name):
                self.write_session(name=name, nameSource="user")
                self.assertEqual(
                    self.read()["observations"][0]["title"],
                    "Claude 11234567-0123-4567-89ab-0123456789ab",
                )

    def test_user_job_title_requires_exact_session_link_and_registry_name_wins(self):
        self.write_session(job_id="abcdef01", nameSource="auto")
        self.write_job(name="User job title", nameSource="user")
        result = self.read()
        self.assertEqual(result["observations"][0]["title"], "User job title")
        self.write_session(job_id="abcdef01", name="User registry title", nameSource="user")
        self.assertEqual(self.read()["observations"][0]["title"], "User registry title")
        path = self.root / "jobs" / "abcdef01" / "state.json"
        job = json.loads(path.read_text())
        job["sessionId"] = "21234567-0123-4567-89ab-0123456789ab"
        self.write_json(path, job)
        self.write_session(job_id="abcdef01", nameSource="auto")
        for item in self.read()["observations"]:
            self.assertEqual(item["title"], "Claude " + item["identity"]["nativeId"])

    def test_retained_job_user_title_does_not_require_a_running_registry_record(self):
        self.write_job(
            name="Retained user title",
            nameSource="user",
            state="done",
            tempo="idle",
            lastTerminalAt="2026-10-02T00:00:01.000Z",
        )
        result = self.read()
        self.assertEqual(result["observations"][0]["title"], "Retained user title")
        self.assertEqual(result["observations"][0]["work"]["value"], "settled")

    def test_user_rename_during_read_refreshes_title_without_changing_work_clock(self):
        self.write_session(name="First title", nameSource="user", job_id="abcdef01")
        self.write_job(name="First job title", nameSource="user")
        original_read = claude_metadata._read_json_at
        renamed: set[str] = set()

        def rename_after_first_read(directory_fd, name, limit):
            value = original_read(directory_fd, name, limit)
            if name in {"23145.json", "state.json"} and name not in renamed:
                renamed.add(name)
                path = (
                    self.root / "sessions" / name
                    if name == "23145.json"
                    else self.root / "jobs" / "abcdef01" / name
                )
                row = json.loads(path.read_text())
                row["name"] = "Second title" if name == "23145.json" else "Second job title"
                row["updatedAt"] = 888888
                self.write_json(path, row)
            return value

        with (
            patch(
                "agent_observer.claude_metadata._read_json_at", side_effect=rename_after_first_read
            ),
            patch(
                "agent_observer.claude_metadata._linux_proc_start_token",
                return_value=("67890", "present"),
            ),
        ):
            result = self.read()
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["observations"][0]["title"], "Second title")
        self.assertEqual(result["observations"][0]["work"]["observedAt"], 111)
        self.assertEqual(result["coverage"]["sessionRegistry"], "complete")
        self.assertEqual(result["coverage"]["jobStore"], "complete")
        self.assertNotIn("metadata_changed_during_snapshot", json.dumps(result["errors"]))

    def test_cwd_is_optional_metadata_and_never_an_identity_join(self):
        self.write_session(status="busy", status_updated_at=111, cwd="relative/path")
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            row = self.read()["observations"][0]
        self.assertIsNone(row["cwd"])
        self.assertIsNone(row["cwdSource"])
        self.assertEqual(row["identity"]["nativeId"], "11234567-0123-4567-89ab-0123456789ab")

    def test_pid_reuse_never_confirms_presence_or_current_registry_work(self):
        self.write_session(status="busy", status_updated_at=111)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("99999", "present"),
        ):
            item = self.read()["observations"][0]
        self.assertEqual(item["presence"]["value"], "absent")
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertIsNone(item["work"]["observedAt"])

    def test_pid_reuse_during_executable_check_never_confirms_presence(self):
        self.write_session(status="busy", status_updated_at=111)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            side_effect=[("67890", "present"), ("99999", "present")],
        ) as start_reader:
            item = self.read()["observations"][0]
        self.assertEqual(start_reader.call_count, 2)
        self.assertEqual(item["presence"]["value"], "absent")
        self.assertEqual(item["work"]["value"], "unknown")

    def test_background_idle_and_general_updated_at_do_not_settle_job(self):
        self.write_session(job_id="abcdef01", status="idle", status_updated_at=222)
        self.write_job(state="working", tempo="active")
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            item = self.read()["observations"][0]
        self.assertEqual(item["job"]["state"], "working")
        self.assertEqual(item["job"]["tempo"], "active")
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertIsNone(item["work"]["observedAt"])
        self.assertEqual(item["nativeStatus"]["observedAt"], 222)

    def test_missing_linked_job_does_not_fall_back_to_registry_idle(self):
        self.write_session(job_id="abcdef01", status="idle", status_updated_at=222)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            item = self.read()["observations"][0]
        self.assertEqual(item["job"]["retained"], False)
        self.assertEqual(item["work"]["value"], "unknown")

    def test_terminal_state_requires_nonactive_tempo_and_terminal_clock(self):
        self.write_session(job_id="abcdef01", status="idle", status_updated_at=100)
        self.write_job(
            state="done",
            tempo="active",
            lastTerminalAt="1970-01-01T00:00:00.450Z",
            firstTerminalAt="1970-01-01T00:00:00.400Z",
        )
        active_item = self.read()["observations"][0]
        self.assertEqual(active_item["work"]["value"], "unknown")

        (self.root / "jobs" / "abcdef01" / "state.json").unlink()
        self.write_json(
            self.root / "jobs" / "abcdef01" / "state.json",
            {
                "sessionId": "11234567-0123-4567-89ab-0123456789ab",
                "state": "done",
                "tempo": "idle",
                "updatedAt": 999999,
                "lastTerminalAt": "1970-01-01T00:00:00.450Z",
            },
        )
        terminal_item = self.read()["observations"][0]
        self.assertEqual(terminal_item["work"]["value"], "settled")
        self.assertEqual(terminal_item["work"]["observedAt"], 450)

    def test_later_idle_registry_status_does_not_invalidate_terminal_job(self):
        self.write_session(job_id="abcdef01", status="idle", status_updated_at=460)
        self.write_job(
            state="done",
            tempo="idle",
            lastTerminalAt="1970-01-01T00:00:00.450Z",
        )
        item = self.read()["observations"][0]
        self.assertEqual(item["work"]["value"], "settled")
        self.assertEqual(item["work"]["observedAt"], 450)
        self.assertNotIn("status_after_terminal_clock", item["metadataIssues"])

    def test_later_active_registry_status_keeps_terminal_job_ambiguous(self):
        self.write_session(job_id="abcdef01", status="busy", status_updated_at=460)
        self.write_job(
            state="done",
            tempo="idle",
            lastTerminalAt="1970-01-01T00:00:00.450Z",
        )
        item = self.read()["observations"][0]
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertEqual(item["work"]["health"], "ambiguous")
        self.assertIn("status_after_terminal_clock", item["metadataIssues"])

    def test_terminal_state_without_proven_clock_stays_unknown(self):
        self.write_job(state="done", tempo="idle")
        item = self.read()["observations"][0]
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertIsNone(item["work"]["observedAt"])
        self.assertIn("terminal_clock_unavailable", item["metadataIssues"])

    def test_cross_id_conflict_is_explicit_and_never_merges_terminal_work(self):
        first = "11234567-0123-4567-89ab-0123456789ab"
        second = "21234567-0123-4567-89ab-0123456789ab"
        self.write_session(job_id="abcdef01", session_id=first)
        self.write_job(
            session_id=second,
            state="done",
            tempo="idle",
            lastTerminalAt="1970-01-01T00:00:00.450Z",
        )
        result = self.read()
        by_session = {item["nativeIds"]["sessionId"]: item for item in result["observations"]}
        self.assertEqual(set(by_session), {first, second})
        self.assertEqual(by_session[first]["work"]["health"], "ambiguous")
        self.assertEqual(by_session[second]["work"]["health"], "ambiguous")
        self.assertIn("job_session_conflict", json.dumps(result["errors"]))

    def test_duplicate_session_job_bindings_are_not_resolved_by_pid_order(self):
        session_id = "11234567-0123-4567-89ab-0123456789ab"
        self.write_session(pid=23145, job_id="abcdef01", session_id=session_id)
        self.write_session(pid=23146, job_id="abcdef01", session_id=session_id)
        self.write_job("abcdef01", session_id=session_id)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            result = self.read()
        self.assertEqual(len(result["observations"]), 2)
        self.assertTrue(
            all(item["work"]["health"] == "ambiguous" for item in result["observations"])
        )
        self.assertIn("duplicate_session_job_pair", json.dumps(result["errors"]))

    def test_same_cwd_does_not_collapse_independent_retained_jobs(self):
        first = "11234567-0123-4567-89ab-0123456789ab"
        second = "21234567-0123-4567-89ab-0123456789ab"
        self.write_job("abcdef01", session_id=first)
        self.write_job("abcdef02", session_id=second)
        result = self.read()
        self.assertEqual(len(result["observations"]), 2)
        self.assertEqual(
            {item["nativeIds"]["jobId"] for item in result["observations"]},
            {"abcdef01", "abcdef02"},
        )
        self.assertEqual(
            {item["nativeIds"]["sessionId"] for item in result["observations"]},
            {first, second},
        )
        self.assertTrue(
            all(item["presence"]["value"] == "unknown" for item in result["observations"])
        )

    def test_waiting_status_maps_only_reason_code_not_dialog_text(self):
        self.write_session(status="waiting", status_updated_at=333)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            result = self.read()
        item = result["observations"][0]
        self.assertEqual(item["work"]["value"], "needs_input")
        self.assertEqual(item["waitReason"], "user_input")
        self.assertNotIn("SYNTHETIC_PRIVATE_QUESTION", json.dumps(result))

    def test_blocked_job_waiting_and_idle_have_distinct_work_semantics(self):
        self.write_session(
            job_id="abcdef01",
            status="waiting",
            status_updated_at=333,
            waitingFor="permission prompt",
        )
        self.write_job(state="working", tempo="blocked")
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            waiting = self.read()["observations"][0]
        self.assertEqual(waiting["work"]["value"], "needs_input")
        self.assertEqual(waiting["work"]["observedAt"], 333)
        self.assertEqual(waiting["waitReason"], "approval")

        session_path = self.root / "sessions" / "23145.json"
        row = json.loads(session_path.read_text(encoding="utf-8"))
        row.update(status="idle", statusUpdatedAt=444)
        self.write_json(session_path, row)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            idle = self.read()["observations"][0]
        self.assertEqual(idle["work"]["value"], "unknown")
        self.assertEqual(idle["work"]["health"], "unavailable")

    def test_supported_waiting_for_vocabulary_is_finite(self):
        expected = {
            "input needed": "user_input",
            "permission prompt": "approval",
            "worker request": "worker_request",
            "sandbox request": "sandbox_request",
            "dialog open": "user_input",
            "dialog:mcp_elicitation": "user_input",
            "goal proposal": "unknown",
        }
        for native_reason, reason_code in expected.items():
            self.write_session(status="waiting", status_updated_at=333, waitingFor=native_reason)
            with patch(
                "agent_observer.claude_metadata._linux_proc_start_token",
                return_value=("67890", "present"),
            ):
                item = self.read()["observations"][0]
            self.assertEqual(item["waitReason"], reason_code)

    def test_native_blocked_job_is_recognized_without_inventing_phase(self):
        self.write_job(state="blocked", tempo="blocked")
        item = self.read()["observations"][0]
        self.assertEqual(item["job"]["state"], "unknown")
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertIn("native_blocked_phase_unproved", item["metadataIssues"])
        self.assertNotIn("unknown_job_state", item["metadataIssues"])

    def test_different_live_executable_is_unsupported_not_worker_exit(self):
        self.write_session(status="busy", status_updated_at=111)
        with patch(
            "agent_observer.claude_metadata._linux_proc_start_token",
            return_value=("67890", "present"),
        ):
            item = self.read(executable_match=False)["observations"][0]
        self.assertEqual(item["presence"]["value"], "unknown")
        self.assertEqual(item["presence"]["health"], "unsupported")
        self.assertEqual(item["work"]["value"], "unknown")

    def test_malformed_and_unrecognized_records_are_bounded_and_private(self):
        self.write_job(state="SYNTHETIC_PRIVATE_ARBITRARY_STATE", tempo="active")
        (self.root / "sessions" / "123.json").write_text(
            '{"pid":123,"sessionId":"SYNTHETIC_PRIVATE_BAD_ID",', encoding="utf-8"
        )
        result = self.read()
        self.assertEqual(len(result["observations"]), 1)
        item = result["observations"][0]
        self.assertEqual(item["job"]["state"], "unknown")
        self.assertEqual(item["work"]["value"], "unknown")
        self.assertIn("unknown_job_state", json.dumps(result["errors"]))
        encoded = json.dumps(result)
        self.assertNotIn("SYNTHETIC_PRIVATE_ARBITRARY_STATE", encoded)
        self.assertNotIn("SYNTHETIC_PRIVATE_BAD_ID", encoded)
        self.assertNotIn("providerEnv", encoded)
        self.assertNotIn("SYNTHETIC_PRIVATE_PROMPT", encoded)

    def test_fifo_is_rejected_without_opening_a_blocking_reader(self):
        self.write_job(state="working", tempo="active")
        state_path = self.root / "jobs" / "abcdef01" / "state.json"
        state_path.unlink()
        os.mkfifo(state_path)
        result = self.read()
        self.assertFalse(result["observations"])
        self.assertIn("not_regular_file", json.dumps(result["errors"]))

    def test_symlinked_state_file_is_rejected(self):
        self.write_job(state="working", tempo="active")
        state_path = self.root / "jobs" / "abcdef01" / "state.json"
        state_path.unlink()
        target = self.root / "private-source.json"
        self.write_json(target, {"prompt": "SYNTHETIC_PRIVATE_PROMPT"})
        state_path.symlink_to(target)
        result = self.read()
        self.assertFalse(result["observations"])
        self.assertIn("symlink_rejected", json.dumps(result["errors"]))
        self.assertNotIn("SYNTHETIC_PRIVATE_PROMPT", json.dumps(result))

    def test_registry_change_between_reads_is_reported_and_excluded(self):
        self.write_session(status="busy", status_updated_at=111)
        original_read = claude_metadata._read_json_at
        calls = 0

        def change_after_first_read(directory_fd, name, limit):
            nonlocal calls
            value = original_read(directory_fd, name, limit)
            if name == "23145.json":
                calls += 1
                if calls == 1:
                    self.write_json(
                        self.root / "sessions" / name,
                        {
                            "pid": 23145,
                            "sessionId": "21234567-0123-4567-89ab-0123456789ab",
                            "procStart": "67890",
                            "pidDomain": self.domain,
                            "kind": "interactive",
                            "status": "busy",
                            "statusUpdatedAt": 111,
                        },
                    )
            return value

        with (
            patch(
                "agent_observer.claude_metadata._read_json_at",
                side_effect=change_after_first_read,
            ),
            patch("agent_observer.claude_metadata._current_pid_domain", return_value=self.domain),
            patch("agent_observer.claude_metadata.time.time_ns", return_value=5_000_000_000),
            patch(
                "agent_observer.claude_metadata._linux_proc_start_token",
                return_value=("67890", "present"),
            ),
            patch(
                "agent_observer.claude_metadata._linux_process_uses_supported_binary",
                return_value=(True, "matched"),
            ),
        ):
            result = snapshot(self.root, **self.scope)
        self.assertFalse(result["observations"])
        self.assertEqual(result["coverage"]["sessionRegistry"], "partial")
        self.assertIn("metadata_changed_during_snapshot", json.dumps(result["errors"]))

    def test_unrelated_metadata_update_does_not_invalidate_projected_state(self):
        self.write_session(status="busy", status_updated_at=111)
        original_read = claude_metadata._read_json_at
        calls = 0

        def update_unprojected_fields(directory_fd, name, limit):
            nonlocal calls
            value = original_read(directory_fd, name, limit)
            if name == "23145.json":
                calls += 1
                if calls == 1:
                    path = self.root / "sessions" / name
                    row = json.loads(path.read_text(encoding="utf-8"))
                    row["updatedAt"] = 888888
                    row["name"] = "SYNTHETIC_PRIVATE_RENAMED"
                    self.write_json(path, row)
            return value

        with (
            patch(
                "agent_observer.claude_metadata._read_json_at",
                side_effect=update_unprojected_fields,
            ),
            patch("agent_observer.claude_metadata._current_pid_domain", return_value=self.domain),
            patch("agent_observer.claude_metadata.time.time_ns", return_value=5_000_000_000),
            patch(
                "agent_observer.claude_metadata._linux_proc_start_token",
                return_value=("67890", "present"),
            ),
            patch(
                "agent_observer.claude_metadata._linux_process_uses_supported_binary",
                return_value=(True, "matched"),
            ),
        ):
            result = snapshot(self.root, **self.scope)
        self.assertEqual(result["observations"][0]["work"]["value"], "working")
        self.assertEqual(result["observations"][0]["work"]["observedAt"], 111)
        self.assertEqual(result["coverage"]["sessionRegistry"], "complete")


if __name__ == "__main__":
    unittest.main()
