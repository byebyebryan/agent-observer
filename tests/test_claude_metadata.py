"""Synthetic interactive lifecycle, provenance and conflict-guard regressions."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import claude_metadata as module
from agent_observer.claude_metadata import snapshot

SID = "11234567-0123-4567-89ab-0123456789ab"
OTHER = "21234567-0123-4567-89ab-0123456789ab"
DOMAIN = "linux:0123456789abcdef0123456789abcdef:pid:[4026531836]"


class ClaudeMetadataTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "sessions").mkdir()
        (self.root / "jobs").mkdir()

    def record(self, pid=123, **extra):
        record = {"pid": pid, "sessionId": SID, "procStart": "456", "pidDomain": DOMAIN,
                  "kind": "interactive", "jobId": None, "status": "idle", "statusUpdatedAt": 100,
                  "cwd": "/same/checkout", "nameSource": "user", "name": "Native title",
                  "prompt": "PRIVATE_PROMPT", "detail": "PRIVATE_DETAIL", **extra}
        (self.root / "sessions" / f"{pid}.json").write_text(json.dumps(record))
        return record

    def job(self, **extra):
        directory = self.root / "jobs/abcdef12"
        directory.mkdir(exist_ok=True)
        record = {"sessionId": SID, "state": "done", "tempo": "idle",
                  "inFlight": {"tasks": 0, "queued": 0, "drainableMonitors": 0},
                  "prompt": "PRIVATE_PROMPT", "output": "PRIVATE_OUTPUT", **extra}
        (directory / "state.json").write_text(json.dumps(record))

    def read(self, saved=(SID,), probe=("456", "present"), image=(True, "matched"), **extra):
        with (patch.object(module, "_current_pid_domain", return_value=DOMAIN),
              patch.object(module.time, "time_ns", return_value=5_000_000_000),
              patch.object(module, "_linux_proc_start_token", return_value=probe),
              patch.object(module, "_linux_process_uses_supported_binary", return_value=image)):
            return snapshot(self.root, host_scope="snap", namespace="private", runtime_version="2.999.0",
                            binary_sha256="f" * 64, saved_session_ids=saved, **extra)

    def row(self, **kwargs):
        return self.read(**kwargs)["observations"][0]

    def test_empty_healthy_scan_supports_saved_parked_without_terminal_jobs(self):
        result = self.read()
        row = result["observations"][0]
        self.assertTrue(result["parkedSupported"])
        self.assertEqual(row["runtimeDisposition"]["value"], "parked")
        self.assertEqual(row["runtimeDisposition"]["reason"], "interactive_registration_assumed")
        self.assertEqual(row["presence"]["value"], "absent")
        self.assertEqual(row["work"]["value"], "unknown")
        self.assertEqual(self.read(saved=())["observations"], [])
        self.assertNotIn("jobStore", result["coverage"])

    def test_running_and_native_work_clocks_are_independent(self):
        for status, expected in (("busy", "working"), ("shell", "working"), ("idle", "settled")):
            self.record(status=status)
            row = self.row()
            self.assertEqual(row["presence"]["value"], "present")
            self.assertEqual(row["presence"]["observedAt"], 5000)
            self.assertEqual(row["work"]["value"], expected)
            self.assertEqual(row["work"]["observedAt"], 100)
            self.assertEqual(row["nativeIds"], {"sessionId": SID})
            self.assertFalse({"worker", "job", "attachment", "sessionKind"}.intersection(row))
            self.assertNotIn("PRIVATE", json.dumps(row))

    def test_only_exact_question_and_approval_waits_are_supported(self):
        for wait, expected in (("input needed", "question"), ("permission prompt", "approval"),
                               ("dialog:settings", "unknown"), ("dialog open", "unknown"),
                               ("worker request", "unknown")):
            self.record(status="waiting", waitingFor=wait)
            row = self.row()
            self.assertEqual(row["waitReason"], expected)
            self.assertEqual(row["work"]["value"], "needs_input" if expected != "unknown" else "unknown")

    def test_invalid_status_or_clock_preserves_running(self):
        for changed in ({"status": "new"}, {"statusUpdatedAt": None}, {"statusUpdatedAt": True},
                        {"statusUpdatedAt": 5001}, {"statusUpdatedAt": -1}):
            self.record(**changed)
            row = self.row()
            self.assertEqual(row["presence"]["value"], "present")
            self.assertEqual(row["work"]["value"], "unknown")

    def test_dead_or_reused_incarnation_is_parked_only_with_saved_identity(self):
        self.record()
        for probe in ((None, "absent"), ("789", "present")):
            self.assertEqual(self.row(probe=probe)["runtimeDisposition"]["value"], "parked")
            self.assertEqual(self.row(probe=probe, saved=())["runtimeDisposition"]["value"], "unknown")
        for probe in ((None, "unavailable"), (None, "malformed")):
            self.assertEqual(self.row(probe=probe)["runtimeDisposition"]["value"], "unknown")

    def test_pid_domain_birth_and_image_uncertainty_never_prove_exit(self):
        for extra in ({"pidDomain": "foreign"}, {"pidDomain": None}, {"procStart": None}):
            self.record(**extra)
            self.assertEqual(self.row()["presence"]["value"], "unknown")
            self.assertEqual(self.row()["runtimeDisposition"]["value"], "unknown")
        self.record()
        for image in ((False, "different_binary"), (None, "unavailable"), (None, "process_unavailable")):
            self.assertEqual(self.row(image=image)["runtimeDisposition"]["value"], "unknown")

    def test_resume_ignores_dead_old_incarnation_and_duplicates_only_conflict_phase(self):
        self.record(123, status="busy")
        self.record(124, status="idle")
        real = module._presence
        def dead_old(r, domain, observed, cache):
            if r["pid"] == 123:
                return module.Evidence("presence", "absent", observed, "claude_registry", "current", "native_snapshot")
            return real(r, domain, observed, cache)
        with patch.object(module, "_presence", side_effect=dead_old):
            self.assertEqual(self.row()["work"]["value"], "settled")
        row = self.row()
        self.assertEqual(row["presence"]["value"], "present")
        self.assertEqual(row["work"]["health"], "ambiguous")
        self.assertIn("duplicate_live_incarnations", row["metadataIssues"])
        self.record(123, status="idle")
        self.assertEqual(self.row()["work"]["value"], "settled")

    def test_background_records_do_not_supply_supported_runtime(self):
        for extra in ({"kind": "bg"}, {"kind": "daemon"}, {"jobId": "abcdef12"}, {"jobId": "invalid"}):
            self.record(**extra)
            row = self.row()
            self.assertEqual(row["presence"]["value"], "unknown")
            self.assertEqual(row["runtimeDisposition"]["value"], "unknown")
            self.assertIn("noninteractive_conflict", row["metadataIssues"])
        self.assertEqual(self.row(probe=(None, "absent"))["runtimeDisposition"]["value"], "parked")

    def test_background_guard_only_vetoes_negatives(self):
        for extra, parked in (({}, True), ({"state": "working"}, False), ({"tempo": "active"}, False),
                              ({"inFlight": None}, False), ({"inFlight": {"tasks": 0, "queued": 1, "drainableMonitors": 0}}, False)):
            self.job(**extra)
            self.assertEqual(self.row()["runtimeDisposition"]["value"], "parked" if parked else "unknown")
            self.assertEqual(self.read(saved=())["observations"], [])
        self.record()
        self.assertEqual(self.row()["presence"]["value"], "present")

    def test_unreadable_guard_or_registry_invalidates_negatives_preserving_valid_positive(self):
        self.record()
        (self.root / "sessions/124.json").write_text("invalid")
        result = self.read(saved=(SID, OTHER))
        rows = {r["identity"]["nativeId"]: r for r in result["observations"]}
        self.assertEqual(rows[SID]["presence"]["value"], "present")
        self.assertEqual(rows[OTHER]["runtimeDisposition"]["value"], "unknown")
        self.assertFalse(result["parkedSupported"])
        (self.root / "sessions/124.json").unlink()
        self.job()
        (self.root / "jobs/abcdef12/state.json").write_text("invalid")
        self.assertEqual(self.row()["presence"]["value"], "present")
        self.assertFalse(self.read()["parkedSupported"])

    def test_missing_registry_is_not_healthy_empty_but_missing_jobs_is_safe(self):
        (self.root / "sessions").rmdir()
        self.assertEqual(self.row()["runtimeDisposition"]["value"], "unknown")
        (self.root / "sessions").mkdir()
        (self.root / "jobs").rmdir()
        self.assertEqual(self.row()["runtimeDisposition"]["value"], "parked")

    def test_registry_membership_or_content_change_invalidates_sample(self):
        self.record()
        original = module._directory_names
        reads = 0
        def change(fd):
            nonlocal reads
            reads += 1
            if reads == 3:
                self.record(124)
            return original(fd)
        with patch.object(module, "_directory_names", side_effect=change):
            self.assertEqual(self.row()["presence"]["value"], "unknown")
        (self.root / "sessions/124.json").unlink()
        original_read = module._read_json_at
        reads = 0
        def changed_record(fd, name, limit):
            nonlocal reads
            if name == "123.json":
                reads += 1
                if reads == 2:
                    self.record(status="busy")
            return original_read(fd, name, limit)
        with patch.object(module, "_read_json_at", side_effect=changed_record):
            self.assertEqual(self.row()["presence"]["value"], "unknown")

    def test_source_bounds_and_unsafe_files_prevent_parked(self):
        self.record()
        with patch.object(module, "_MAX_REGISTRY_ROWS", 0):
            self.assertEqual(self.row()["runtimeDisposition"]["value"], "unknown")
        with patch.object(module, "_MAX_REGISTRY_TOTAL_BYTES", 1):
            self.assertEqual(self.row()["runtimeDisposition"]["value"], "unknown")
        target = self.root / "sessions/123.json"
        target.unlink()
        target.symlink_to(self.root / "missing")
        self.assertFalse(self.read()["parkedSupported"])
        target.unlink()
        os.mkfifo(target)
        self.assertFalse(self.read()["parkedSupported"])

    def test_wrong_filename_duplicate_keys_and_malformed_identity_are_rejected(self):
        self.record(pid=124)
        (self.root / "sessions/124.json").rename(self.root / "sessions/123.json")
        self.assertFalse(self.read()["parkedSupported"])
        (self.root / "sessions/123.json").write_text('{"sessionId":"' + SID + '","sessionId":"' + SID + '"}')
        self.assertFalse(self.read()["parkedSupported"])
        self.record(sessionId="not-a-uuid")
        self.assertFalse(self.read()["parkedSupported"])

    def test_native_title_requires_user_source_and_optional_path_does_not_break_runtime(self):
        for extra in ({"nameSource": "automatic"}, {"nameSource": None}, {"cwd": "/bad/../path"}):
            self.record(**extra)
            row = self.row()
            self.assertEqual(row["presence"]["value"], "present")
            if extra.get("cwd"):
                self.assertIsNone(row["cwd"])
            else:
                self.assertEqual(row["title"], "Claude " + SID)

    def test_invalid_scope_or_saved_catalog_is_rejected_before_io(self):
        for args in ({"host_scope": []}, {"saved_session_ids": ["invalid"]}, {"binary_sha256": "invalid"}):
            kwargs = dict(host_scope="snap", namespace="private", runtime_version="unknown", binary_sha256=None)
            kwargs.update(args)
            self.assertFalse(snapshot(self.root, **kwargs)["supported"])

    def test_linux_zombie_is_dead_incarnation(self):
        fields = ["Z"] + ["0"] * 18 + ["456"]
        with (patch.object(module.os, "open", return_value=99), patch.object(module.os, "close"),
              patch.object(module.os, "read", return_value=("123 (worker) " + " ".join(fields)).encode())):
            self.assertEqual(module._linux_proc_start_token(123), ("456", "absent"))
