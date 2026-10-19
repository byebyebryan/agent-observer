#!/usr/bin/env python3
"""Offline fake-boundary tests for the marker-gated Snap orchestrator."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("run-native-working-set-snap.py")
spec = importlib.util.spec_from_file_location("working_set_snap_orchestrator", SCRIPT)
orchestrator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = orchestrator
spec.loader.exec_module(orchestrator)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class FakePipeIO:
    def __init__(self, events=()):
        self.socket_path = Path("/run/user/1000/private-fixture/read.sock")
        self.clock = FakeClock()
        self.events = list(events)
        self.started_qualifier = False
        self.started_candidate = False
        self.marker_seen = False
        self.cleanup_order = []
        self.next_kind = None

    def start_qualifier(self):
        self.started_qualifier = True
        return object()

    def start_candidate(self):
        if not self.marker_seen:
            raise AssertionError("candidate launched before native-before marker")
        self.started_candidate = True
        process = type("RunningProcess", (), {"poll": lambda _self: None})()
        return type("CandidateHandle", (), {"proc": process})()

    def next_event(self, timeout):
        if not self.events:
            self.clock.advance(timeout)
            return None
        delay, kind, value = self.events.pop(0)
        self.clock.advance(delay)
        self.next_kind = kind
        if kind == "qualifier_line" and not self.marker_seen:
            try:
                line = json.loads(value)
                self.marker_seen = line.get("event") == "native_before_complete"
            except Exception:
                pass
        return kind, value

    def cleanup_all(self):
        if self.started_candidate:
            self.cleanup_order.append("candidate")
        if self.started_qualifier:
            self.cleanup_order.append("qualifier")
        return {"workerGroupsRetired": True}


def progress_line(socket_path: Path, *, rows=3, event="native_before_complete") -> bytes:
    return json.dumps(
        {
            "schema": orchestrator.PROGRESS_SCHEMA,
            "event": event,
            "nativeRows": rows,
            "nativeVersion": "0.9.1",
            "nativeExecutableSha256": "a" * 64,
            "candidateServiceSocket": str(socket_path),
        },
        separators=(",", ":"),
    ).encode()


def result_line(**extra) -> bytes:
    value = {
        "schema": orchestrator.RESULT_SCHEMA,
        "status": "match",
        "exitCode": 0,
        "membershipStatus": "match",
        "conditionalMembershipStatus": "none",
        "fieldStatus": "match",
        "counts": {
            "nativeBefore": 3,
            "nativeAfter": 3,
            "candidateBodies": 3,
            "nativeCensusStable": True,
            "nativeComplete": True,
        },
        "fieldCounts": {"kind_checked": 3, "kind_match": 3},
        "sourceK": {
            "status": "independently_recomputed_first_acceptance_set",
            "firstAcceptanceSet": "recomputed",
            "clockBracketAndComponentSampleJoins": "checked",
            "currentComponentClockCensus": "complete",
        },
        "identityDigests": ["b" * 32],
    }
    value.update(extra)
    return json.dumps(value, separators=(",", ":")).encode()


class ProtocolTests(unittest.TestCase):
    def test_candidate_waits_for_exact_native_before_marker(self):
        io = FakePipeIO(
            [
                (
                    0,
                    "qualifier_line",
                    progress_line(Path("/run/user/1000/private-fixture/read.sock")),
                ),
                (0.1, "qualifier_line", result_line()),
                (0, "qualifier_exit", 0),
            ]
        )
        result = orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertTrue(result["candidateStarted"])
        self.assertTrue(io.marker_seen)
        self.assertEqual(io.cleanup_order, ["candidate", "qualifier"])
        self.assertEqual(result["comparison"]["status"], "match")

    def test_qualifier_failure_before_marker_never_starts_candidate(self):
        failure = json.dumps(
            {
                "schema": orchestrator.RESULT_SCHEMA,
                "status": "unsupported",
                "exitCode": 3,
                "reasonCode": "native_endpoint_unavailable",
            }
        ).encode()
        io = FakePipeIO(
            [
                (0, "qualifier_line", failure),
                (0, "qualifier_exit", 3),
            ]
        )
        protocol = orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertFalse(io.started_candidate)
        self.assertEqual(io.cleanup_order, ["qualifier"])
        self.assertFalse(protocol["candidateStarted"])
        self.assertEqual(protocol["comparison"]["status"], "unsupported")
        self.assertEqual(protocol["comparison"]["reasonCode"], "native_endpoint_unavailable")
        self.assertEqual(protocol["comparison"]["exitCode"], 3)

    def test_match_result_before_marker_is_rejected_and_never_starts_candidate(self):
        io = FakePipeIO(
            [
                (0, "qualifier_line", result_line()),
                (0, "qualifier_exit", 0),
            ]
        )
        with self.assertRaises(orchestrator.PlanFailure) as raised:
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertEqual(raised.exception.code, "qualifier_result_before_native_before")
        self.assertFalse(io.started_candidate)
        self.assertEqual(io.cleanup_order, ["qualifier"])

    def test_pre_marker_error_status_and_reason_are_preserved(self):
        failure = json.dumps(
            {
                "schema": orchestrator.RESULT_SCHEMA,
                "status": "error",
                "exitCode": 4,
                "reasonCode": "native_detail_identity_conflict",
            }
        ).encode()
        io = FakePipeIO(
            [
                (0, "qualifier_line", failure),
                (0, "qualifier_exit", 4),
            ]
        )
        protocol = orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertFalse(protocol["candidateStarted"])
        cleanup = {
            "candidate": None,
            "qualifier": {"joined": True, "joinCode": "already_exited"},
            "workerGroupsRetired": True,
            "workerGroupSurvivorCount": 0,
            "unexpectedWorkerCount": 0,
            "candidateSocketRemoved": True,
            "privateRuntimeDirectoryRemoved": True,
        }
        self.assertEqual(
            orchestrator._report_status(protocol, None, cleanup),
            ("failed", 4, "native_detail_identity_conflict"),
        )

    def test_wrong_socket_or_extra_marker_field_never_starts_candidate(self):
        line = json.loads(progress_line(Path("/run/user/1000/private-fixture/read.sock")))
        line["candidateServiceSocket"] = "/different/socket"
        io = FakePipeIO([(0, "qualifier_line", json.dumps(line).encode())])
        with self.assertRaises(orchestrator.PlanFailure):
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertFalse(io.started_candidate)

        line = json.loads(progress_line(io.socket_path))
        line["extra"] = "not-allowed"
        io = FakePipeIO([(0, "qualifier_line", json.dumps(line).encode())])
        with self.assertRaises(orchestrator.PlanFailure):
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertFalse(io.started_candidate)

    def test_no_marker_timeout_is_bounded_and_cleans_qualifier_only(self):
        io = FakePipeIO()
        with self.assertRaises(orchestrator.PlanFailure) as raised:
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=0.11)
        self.assertEqual(raised.exception.code, "orchestrator_deadline")
        self.assertLessEqual(io.clock(), 0.16)
        self.assertFalse(io.started_candidate)
        self.assertEqual(io.cleanup_order, ["qualifier"])

    def test_after_marker_timeout_cleans_started_candidate_and_qualifier(self):
        io = FakePipeIO(
            [
                (
                    0,
                    "qualifier_line",
                    progress_line(Path("/run/user/1000/private-fixture/read.sock")),
                )
            ]
        )
        with self.assertRaises(orchestrator.PlanFailure) as raised:
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=0.11)
        self.assertEqual(raised.exception.code, "orchestrator_deadline")
        self.assertTrue(io.started_candidate)
        self.assertEqual(io.cleanup_order, ["candidate", "qualifier"])

    def test_candidate_exit_before_result_is_failure_and_owned_cleanup_runs(self):
        io = FakePipeIO(
            [
                (
                    0,
                    "qualifier_line",
                    progress_line(Path("/run/user/1000/private-fixture/read.sock")),
                ),
                (0, "candidate_exit", 1),
            ]
        )
        with self.assertRaises(orchestrator.PlanFailure) as raised:
            orchestrator.drive_protocol(io, now=io.clock, deadline_seconds=1)
        self.assertEqual(raised.exception.code, "candidate_exited_before_qualification")
        self.assertTrue(io.started_candidate)
        self.assertEqual(io.cleanup_order, ["candidate", "qualifier"])

    def test_result_projection_redacts_unapproved_fields(self):
        secret = "private-title-must-not-survive"
        line = result_line(
            title=secret,
            cwd=secret,
            rawNative=secret,
            reasonCode="native_detail_identity_conflict",
            prompts=[secret],
            nativeReference={"sessionId": secret},
        )
        marker = {"rows": 3}
        projected = orchestrator._project_result(line, marker)
        encoded = json.dumps(projected, sort_keys=True)
        self.assertNotIn(secret, encoded)
        self.assertNotIn("title", projected)
        self.assertNotIn("rawNative", projected)
        self.assertEqual(projected["identityDigests"], ["b" * 32])
        self.assertEqual(projected["reasonCode"], "native_detail_identity_conflict")

    def test_result_projection_preserves_bounded_codes_and_safe_source_clock_values(self):
        line = result_line(
            reasonCounts={"native_census_changed": 2, "source_clock_samples_missing": 1},
            mismatchCounts={"runtime_mismatch": 1},
            sourceK={
                "status": "producer_asserted_not_independently_proven",
                "firstAcceptanceSet": "unproved",
                "clockBracketAndComponentSampleJoins": "checked",
                "currentComponentClockCensus": "complete",
                "candidateCeiling": 1_800_000_000_000,
                "independentCurrentClockLowerBound": 1_799_999_999_999,
                "recomputedFirstAcceptanceCeiling": None,
                "firstAcceptanceReason": "source_clock_census_incomplete",
                "rawNative": "private title",
            },
            rawNative={"sessionId": "private title"},
        )
        projected = orchestrator._project_result(line, {"rows": 3})
        self.assertEqual(
            projected["reasonCounts"],
            {"native_census_changed": 2, "source_clock_samples_missing": 1},
        )
        self.assertEqual(projected["mismatchCounts"], {"runtime_mismatch": 1})
        self.assertEqual(projected["sourceK"]["candidateCeiling"], 1_800_000_000_000)
        self.assertIsNone(projected["sourceK"]["recomputedFirstAcceptanceCeiling"])
        self.assertEqual(
            projected["sourceK"]["firstAcceptanceReason"],
            "source_clock_census_incomplete",
        )
        encoded = json.dumps(projected, sort_keys=True)
        self.assertNotIn("private title", encoded)
        self.assertNotIn("rawNative", encoded)

    def test_result_projection_rejects_malformed_bounded_diagnostics(self):
        cases = [
            {"reasonCounts": {"private title": 1}},
            {"reasonCounts": {"native_error": True}},
            {"mismatchCounts": {"native_error": orchestrator.MAX_NATIVE_ROWS * 4 + 1}},
            {"reasonCode": "private title"},
            {"sourceK": {"candidateCeiling": True}},
            {"sourceK": {"candidateCeiling": orchestrator._MAX_SAFE_INTEGER + 1}},
            {"sourceK": {"firstAcceptanceReason": None}},
        ]
        too_many = {f"reason_{index}": 0 for index in range(129)}
        cases.append({"reasonCounts": too_many})
        for extra in cases:
            with self.subTest(extra=extra):
                with self.assertRaises(orchestrator.PlanFailure):
                    orchestrator._project_result(result_line(**extra), {"rows": 3})

    def test_observed_prefix_and_projected_status_are_bounded_and_separate(self):
        prefix = {
            "status": "recomputed", "reason": "observed_clock_prefix_recomputed",
            "frames": 3, "acceptedTransitions": 3,
            "baselineCounters": {"runtime": 0, "history": 0},
            "finalCounters": {"runtime": 2, "history": 1},
            "recomputedCeiling": 1_700_000_000_000,
            "finalMetadataFingerprint": "c" * 64,
            "componentStates": {"sampleId": "private title"},
        }
        line = result_line(
            status="unresolved", exitCode=3,
            membershipStatus="match", fieldStatus="unresolved",
            projectedFieldStatus="match", projectionStatus="match",
            sourceK={
                "status": "independently_recomputed_observed_clock_prefix",
                "firstAcceptanceSet": "not_used",
                "firstAcceptanceReason": "observed_clock_prefix_path_selected",
                "recomputedObservedClockPrefixCeiling": 1_700_000_000_000,
                "observedClockPrefix": prefix,
            },
        )
        projected = orchestrator._project_result(line, {"rows": 3})
        self.assertEqual(projected["status"], "unresolved")
        self.assertEqual(projected["exitCode"], 3)
        self.assertEqual(projected["projectionStatus"], "match")
        self.assertEqual(projected["sourceK"]["observedClockPrefix"]["finalCounters"],
                         {"runtime": 2, "history": 1})
        self.assertNotIn("private title", json.dumps(projected))
        for update in ({"frames": 17}, {"acceptedTransitions": True},
                       {"recomputedCeiling": orchestrator._MAX_SAFE_INTEGER + 1},
                       {"finalCounters": {"runtime": True, "history": 1}},
                       {"finalMetadataFingerprint": "private title"}):
            with self.subTest(update=update):
                malformed = dict(prefix, **update)
                with self.assertRaises(orchestrator.PlanFailure):
                    orchestrator._project_result(
                        result_line(sourceK={"observedClockPrefix": malformed}),
                        {"rows": 3},
                    )

    def test_result_rejects_boolean_as_native_row_count(self):
        line = result_line(counts={"nativeBefore": True})
        with self.assertRaises(orchestrator.PlanFailure):
            orchestrator._project_result(line, {"rows": 1})


class CleanupGateTests(unittest.TestCase):
    def test_forced_or_unverified_retirement_cannot_remove_private_paths(self):
        class Process:
            def poll(self):
                return 0

        class CleanupHarness:
            def __init__(self, verified, killed):
                self.candidate = orchestrator.ChildHandle(
                    "candidate", Process(), ("candidate",),
                    identity_verified=verified, kill_sent=killed,
                    join_code="forced_exit" if killed else "already_exited",
                )
                self.qualifier = None
                self.workers = {}
                self.unexpected_worker_count = 0
                self.worker_scan_code = None
                self.socket_identity = None
                self.socket_listener_inode = None
                self.cleanup_receipt = {}
                self.removal_calls = []

            def _stop_handle(self, _handle):
                pass

            def _worker_group_survivors(self):
                return 0, True

            def _remove_private_socket(self):
                self.removal_calls.append("socket")
                return True, "removed_owned_socket"

            def _remove_runtime_dir(self):
                self.removal_calls.append("directory")
                return True

        for verified, killed in ((True, False), (True, True), (False, False)):
            with self.subTest(verified=verified, killed=killed):
                harness = CleanupHarness(verified, killed)
                receipt = orchestrator.RealIO.cleanup_all(harness)
                self.assertTrue(receipt["ownedChildrenRetired"])
                self.assertEqual(receipt["pathRemovalSafe"], verified and not killed)
                self.assertEqual(harness.removal_calls,
                                 ["socket", "directory"] if verified and not killed else [])

    def test_live_owned_child_retains_socket_and_private_directory(self):
        class Process:
            def __init__(self, returncode):
                self.returncode = returncode

            def poll(self):
                return self.returncode

        class CleanupHarness:
            def __init__(self, candidate_returncode=None, worker_scan=(0, True)):
                self.candidate = orchestrator.ChildHandle(
                    "candidate", Process(candidate_returncode), ("candidate",)
                )
                self.qualifier = orchestrator.ChildHandle("qualifier", Process(3), ("qualifier",))
                self.workers = {}
                self.unexpected_worker_count = 0
                self.worker_scan_code = None
                self.socket_identity = None
                self.socket_listener_inode = None
                self.socket_path = Path("/private/read.sock")
                self.cleanup_receipt = {}
                self.removal_calls = []
                self.worker_scan = worker_scan

            def _capture_workers(self):
                pass

            def _observe_candidate_socket(self):
                pass

            def _stop_handle(self, _handle):
                pass

            def _worker_group_survivors(self):
                return self.worker_scan

            def _remove_private_socket(self):
                self.removal_calls.append("socket")
                return True, "removed_owned_socket"

            def _remove_runtime_dir(self):
                self.removal_calls.append("directory")
                return True

        harness = CleanupHarness()
        receipt = orchestrator.RealIO.cleanup_all(harness)
        self.assertEqual(harness.removal_calls, [])
        self.assertFalse(receipt["candidateSocketRemoved"])
        self.assertFalse(receipt["privateRuntimeDirectoryRemoved"])
        self.assertTrue(receipt["liveOwnerRetained"])
        self.assertEqual(receipt["candidateSocketCleanupCode"], "live_owner_retained")
        self.assertFalse(receipt["ownedChildrenRetired"])

    def test_worker_survivor_or_unavailable_scan_retains_paths(self):
        class Process:
            def __init__(self, returncode):
                self.returncode = returncode

            def poll(self):
                return self.returncode

        class CleanupHarness:
            def __init__(self, worker_scan):
                self.candidate = orchestrator.ChildHandle("candidate", Process(0), ("candidate",))
                self.qualifier = orchestrator.ChildHandle("qualifier", Process(3), ("qualifier",))
                self.workers = {}
                self.unexpected_worker_count = 0
                self.worker_scan_code = None
                self.socket_identity = None
                self.socket_listener_inode = None
                self.socket_path = Path("/private/read.sock")
                self.cleanup_receipt = {}
                self.removal_calls = []
                self.worker_scan = worker_scan

            def _capture_workers(self):
                pass

            def _observe_candidate_socket(self):
                pass

            def _stop_handle(self, _handle):
                pass

            def _worker_group_survivors(self):
                return self.worker_scan

            def _remove_private_socket(self):
                self.removal_calls.append("socket")
                return True, "removed_owned_socket"

            def _remove_runtime_dir(self):
                self.removal_calls.append("directory")
                return True

        for worker_scan in ((1, True), (0, False)):
            with self.subTest(worker_scan=worker_scan):
                harness = CleanupHarness(worker_scan)
                receipt = orchestrator.RealIO.cleanup_all(harness)
                self.assertEqual(harness.removal_calls, [])
                self.assertTrue(receipt["ownedChildrenRetired"])
                self.assertTrue(receipt["liveOwnerRetained"])
                self.assertFalse(receipt["candidateSocketRemoved"])
                self.assertFalse(receipt["privateRuntimeDirectoryRemoved"])


def write_fake_proc(
    proc_root: Path,
    *,
    pid: int,
    ppid: int,
    pgrp: int,
    session: int,
    start: int,
    argv: tuple[str, ...],
    exe: Path,
) -> None:
    proc = proc_root / str(pid)
    proc.mkdir(parents=True)
    fields = ["S", str(ppid), str(pgrp), str(session)] + ["0"] * 16
    fields[19] = str(start)
    (proc / "stat").write_text(f"{pid} (fixture process) " + " ".join(fields), encoding="ascii")
    (proc / "status").write_text(
        f"Name:\tfixture\nUid:\t{os.getuid()}\t{os.getuid()}\t{os.getuid()}\t{os.getuid()}\n",
        encoding="ascii",
    )
    (proc / "cmdline").write_bytes(b"\0".join(os.fsencode(arg) for arg in argv) + b"\0")
    (proc / "exe").symlink_to(exe)


class ProcessGuardTests(unittest.TestCase):
    def test_pid_birth_mismatch_prevents_any_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "proc"
            root.mkdir()
            exe = Path(directory) / "python"
            exe.write_bytes(b"fixture executable bytes\n")
            exe.chmod(0o755)
            pid = 4321
            argv = ("/venv/bin/python", "qualifier.py")
            write_fake_proc(
                root, pid=pid, ppid=os.getpid(), pgrp=pid, session=pid, start=99, argv=argv, exe=exe
            )
            identity = orchestrator._validate_process(
                pid,
                argv,
                expected_exe_sha=orchestrator._sha_file(exe)[0],
                expected_uid=os.getuid(),
                expected_device_inode=(exe.stat().st_dev, exe.stat().st_ino),
                expected_parent=os.getpid(),
                proc_root=root,
            )
            fake_process = type("Proc", (), {"pid": pid})()
            handle = orchestrator.ChildHandle("qualifier", fake_process, argv, identity, True)
            # A reused PID with a new birth time is not signaled.
            proc_stat = root / str(pid) / "stat"
            fields = proc_stat.read_text().split(" (fixture process) ", 1)[1].split()
            fields[19] = "100"
            proc_stat.write_text(f"{pid} (fixture process) " + " ".join(fields), encoding="ascii")
            signaled = []
            with self.assertRaises(orchestrator.PlanFailure):
                orchestrator._guarded_signal(
                    handle,
                    15,
                    lambda target, sig: signaled.append((target, sig)),
                    expected_exe_sha=orchestrator._sha_file(exe)[0],
                    expected_uid=os.getuid(),
                    expected_device_inode=(exe.stat().st_dev, exe.stat().st_ino),
                    expected_parent=os.getpid(),
                    proc_root=root,
                )
            self.assertEqual(signaled, [])

    def test_canonical_worker_requires_direct_child_and_owned_group(self):
        worker_path = Path("/private/venv/site-packages/agent_observer/_service_worker.py")
        identity = orchestrator.ProcIdentity(
            pid=600,
            start_ticks=10,
            uid=1000,
            parent_pid=500,
            pgrp=600,
            session=600,
            argv_sha256="a" * 64,
            executable_sha256=None,
            executable_device=7,
            executable_inode=8,
        )
        argv = [str(orchestrator.PYTHON), "-I", "-B", str(worker_path)]
        args = dict(
            candidate_pid=500,
            python_sha=orchestrator.PYTHON_SHA256,
            python_device_inode=(7, 8),
            worker_path=worker_path,
        )
        self.assertTrue(orchestrator._is_canonical_worker(identity, argv, **args))
        self.assertFalse(
            orchestrator._is_canonical_worker(
                dataclasses.replace(identity, parent_pid=501), argv, **args
            )
        )
        self.assertFalse(
            orchestrator._is_canonical_worker(dataclasses.replace(identity, pgrp=500), argv, **args)
        )
        self.assertFalse(
            orchestrator._is_canonical_worker(
                identity, [*argv[:-1], "/other/_service_worker.py"], **args
            )
        )

    def test_listener_socket_requires_unique_path_and_candidate_fd_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            proc_root = Path(directory) / "proc"
            socket_path = Path("/run/user/1000/private/read.sock")
            pid = 777
            fd_root = proc_root / str(pid) / "fd"
            fd_root.mkdir(parents=True)
            (fd_root / "4").symlink_to("socket:[12345]")
            net_root = proc_root / "net"
            net_root.mkdir()
            header = "Num RefCount Protocol Flags Type St Inode Path\n"
            listener = f"00000000: 00000002 00000000 00010000 0001 01 12345 {socket_path}\n"
            (net_root / "unix").write_text(header + listener, encoding="ascii")
            self.assertEqual(
                orchestrator._candidate_listener_inode(socket_path, pid, proc_root), 12345
            )
            self.assertIsNone(
                orchestrator._candidate_listener_inode(socket_path, pid + 1, proc_root)
            )
            ambiguous = listener.replace(" 12345 ", " 12346 ")
            (net_root / "unix").write_text(header + listener + ambiguous, encoding="ascii")
            self.assertIsNone(orchestrator._candidate_listener_inode(socket_path, pid, proc_root))

    def test_candidate_argv_has_only_the_five_reviewed_option_pairs(self):
        argv = orchestrator._candidate_argv(Path("/run/user/1000/private/read.sock"))
        self.assertEqual(argv[2], "serve")
        pairs = list(zip(argv[3::2], argv[4::2], strict=True))
        self.assertEqual(
            [key for key, _ in pairs],
            [
                "--host-scope",
                "--socket",
                "--provider",
                "--codex-home",
                "--working-set-window-hours",
            ],
        )
        self.assertEqual(pairs[0][1], "snap")
        self.assertEqual(pairs[2][1], "codex")
        self.assertEqual(pairs[3][1], "/home/bryan/.codex")
        self.assertEqual(pairs[4][1], "72")
        self.assertNotIn("--native-hints", argv)

    def test_forced_candidate_kill_cannot_be_reported_as_cleanup_pass(self):
        protocol = {
            "comparison": {"status": "match", "exitCode": 0},
        }
        cleanup = {
            "candidate": {"joined": True, "joinCode": "forced_exit"},
            "qualifier": {"joined": True, "joinCode": "already_exited"},
            "workerGroupsRetired": True,
            "workerGroupSurvivorCount": 0,
            "unexpectedWorkerCount": 0,
            "candidateSocketRemoved": True,
            "privateRuntimeDirectoryRemoved": True,
        }
        self.assertEqual(
            orchestrator._report_status(protocol, None, cleanup),
            ("cleanup_unresolved", 4, "owned_cleanup_unresolved"),
        )


class LeaseCleanupTests(unittest.TestCase):
    class Process:
        pid = 98765

        def __init__(self):
            self.returncode = None

        def poll(self):
            return self.returncode

    def make_fixture(self, *, socket_present=True, record_update=None):
        import socket

        directory = tempfile.TemporaryDirectory(prefix="ws-lease-control-")
        runtime_dir = Path(directory.name) / "private"
        runtime_dir.mkdir(mode=0o700)
        os.chmod(runtime_dir, 0o700)
        socket_path = runtime_dir / "read.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        listener.listen(1)
        socket_info = socket_path.lstat()
        record = {
            "pid": self.Process.pid,
            "birth": 24680,
            "device": socket_info.st_dev,
            "inode": socket_info.st_ino,
        }
        if record_update:
            record.update(record_update)
        lease_path = runtime_dir / "read.sock.lock"
        lease_path.write_bytes(orchestrator._lease_record_bytes(record))
        os.chmod(lease_path, 0o600)
        identity = orchestrator.ProcIdentity(
            pid=self.Process.pid,
            start_ticks=24680,
            uid=1000,
            parent_pid=12345,
            pgrp=self.Process.pid,
            session=self.Process.pid,
            argv_sha256="a" * 64,
            executable_sha256="b" * 64,
            executable_device=1,
            executable_inode=2,
        )
        io = object.__new__(orchestrator.RealIO)
        io.runtime_dir = runtime_dir
        runtime_info = runtime_dir.lstat()
        io.runtime_identity = runtime_info.st_dev, runtime_info.st_ino
        io.socket_path = socket_path
        io.socket_identity = socket_info.st_dev, socket_info.st_ino
        io.socket_mode = 0o600
        io.socket_listener_inode = 45678
        io.socket_seen_bad = False
        io.lease_path = lease_path
        io.lease_fd = None
        io.lease_identity = None
        io.lease_record = None
        io.lease_record_verified = False
        io.lease_seen_bad = False
        io.lease_removed = False
        io.lease_cleanup_code = "not_observed"
        io._cleanup_removal_allowed = True
        io.candidate = orchestrator.ChildHandle(
            "candidate",
            self.Process(),
            ("candidate",),
            identity=identity,
            identity_verified=True,
        )
        io.cancel_check = lambda: self.fail("cleanup must not call cancellation callback")
        io._verify_live_child = lambda _handle: None
        if not socket_present:
            socket_path.unlink()
        return directory, io, listener, lease_path

    def capture_fixture(self, io):
        io._capture_private_lease()
        self.assertTrue(io.lease_record_verified)
        self.assertIsNotNone(io.lease_fd)
        io.candidate.proc.returncode = 0
        io.candidate.joined = True
        io.candidate.join_code = "already_exited"

    def finish_fixture(self, directory, io, listener):
        listener.close()
        io._close_private_lease_fd()
        directory.cleanup()

    def test_exact_lease_is_removed_after_endpoint_closed_socket(self):
        directory, io, listener, lease_path = self.make_fixture()
        try:
            self.capture_fixture(io)
            listener.close()
            io.socket_path.unlink()
            ok, code = io._remove_private_socket()
            self.assertTrue(ok)
            self.assertEqual(code, "removed_exact_lease_after_endpoint_close")
            self.assertFalse(lease_path.exists())
            self.assertTrue(io.lease_removed)
            self.assertTrue(io._close_private_lease_fd())
            self.assertTrue(io._remove_runtime_dir())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_exact_lease_removes_still_present_owned_socket_without_callbacks(self):
        directory, io, listener, lease_path = self.make_fixture()
        try:
            self.capture_fixture(io)
            listener.close()
            ok, code = io._remove_private_socket()
            self.assertTrue(ok)
            self.assertEqual(code, "removed_owned_socket_and_lease")
            self.assertFalse(io.socket_path.exists())
            self.assertFalse(lease_path.exists())
            self.assertTrue(io._close_private_lease_fd())
            self.assertTrue(io._remove_runtime_dir())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_mismatched_birth_record_is_retained(self):
        directory, io, listener, lease_path = self.make_fixture(
            record_update={"birth": 24681}
        )
        try:
            with self.assertRaises(orchestrator.PlanFailure) as caught:
                io._capture_private_lease()
            self.assertEqual(caught.exception.code, "candidate_lease_record_mismatch")
            self.assertTrue(lease_path.exists())
            self.assertFalse(io.lease_record_verified)
        finally:
            self.finish_fixture(directory, io, listener)

    def test_record_changed_after_capture_is_retained(self):
        directory, io, listener, lease_path = self.make_fixture()
        try:
            self.capture_fixture(io)
            changed = dict(io.lease_record, birth=24681)
            payload = orchestrator._lease_record_bytes(changed)
            os.pwrite(io.lease_fd, payload, 0)
            os.ftruncate(io.lease_fd, len(payload))
            ok, code = io._remove_private_socket()
            self.assertFalse(ok)
            self.assertEqual(code, "candidate_lease_record_changed")
            self.assertTrue(lease_path.exists())
            self.assertTrue(io.socket_path.exists())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_foreign_lock_metadata_is_rejected_without_unlink(self):
        from unittest import mock

        directory, io, listener, lease_path = self.make_fixture()
        real_fstat = os.fstat

        def foreign_fstat(fd):
            values = list(real_fstat(fd))
            values[4] = 2000
            return os.stat_result(values)

        try:
            with mock.patch.object(orchestrator.os, "fstat", side_effect=foreign_fstat):
                with self.assertRaises(orchestrator.PlanFailure) as caught:
                    io._capture_private_lease()
            self.assertEqual(caught.exception.code, "candidate_lease_identity_changed")
            self.assertTrue(lease_path.exists())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_replaced_lock_inode_is_retained(self):
        directory, io, listener, lease_path = self.make_fixture()
        try:
            self.capture_fixture(io)
            record = io.lease_record
            lease_path.unlink()
            lease_path.write_bytes(orchestrator._lease_record_bytes(record))
            os.chmod(lease_path, 0o600)
            ok, code = io._remove_private_socket()
            self.assertFalse(ok)
            self.assertEqual(code, "candidate_lease_identity_changed")
            self.assertTrue(lease_path.exists())
            self.assertTrue(io.socket_path.exists())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_busy_lock_is_retained(self):
        import fcntl

        directory, io, listener, lease_path = self.make_fixture()
        busy_fd = os.open(lease_path, os.O_RDWR | os.O_CLOEXEC)
        try:
            self.capture_fixture(io)
            fcntl.flock(busy_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ok, code = io._remove_private_socket()
            self.assertFalse(ok)
            self.assertEqual(code, "candidate_lease_busy")
            self.assertTrue(lease_path.exists())
        finally:
            os.close(busy_fd)
            self.finish_fixture(directory, io, listener)

    def test_symlink_lease_is_rejected_and_retained(self):
        directory, io, listener, lease_path = self.make_fixture()
        target = io.runtime_dir / "foreign-record"
        try:
            data = lease_path.read_bytes()
            lease_path.unlink()
            target.write_bytes(data)
            os.chmod(target, 0o600)
            lease_path.symlink_to(target.name)
            with self.assertRaises(orchestrator.PlanFailure) as caught:
                io._capture_private_lease()
            self.assertEqual(caught.exception.code, "candidate_lease_ownership_rejected")
            self.assertTrue(lease_path.is_symlink())
        finally:
            self.finish_fixture(directory, io, listener)

    def test_live_owner_or_forced_kill_cannot_remove_exact_lease(self):
        for state in ("live", "forced"):
            with self.subTest(state=state):
                directory, io, listener, lease_path = self.make_fixture()
                try:
                    self.capture_fixture(io)
                    if state == "live":
                        io.candidate.proc.returncode = None
                        io.candidate.joined = False
                        io.candidate.join_code = "not_joined"
                    else:
                        io.candidate.kill_sent = True
                        io.candidate.join_code = "forced_exit"
                    ok, code = io._remove_private_socket()
                    self.assertFalse(ok)
                    self.assertEqual(code, "candidate_lease_unproved")
                    self.assertTrue(lease_path.exists())
                    self.assertTrue(io.socket_path.exists())
                finally:
                    self.finish_fixture(directory, io, listener)

    def test_never_started_candidate_only_removes_new_empty_directory(self):
        directory = tempfile.TemporaryDirectory(prefix="ws-empty-control-")
        try:
            runtime_dir = Path(directory.name) / "private"
            runtime_dir.mkdir(mode=0o700)
            os.chmod(runtime_dir, 0o700)
            info = runtime_dir.lstat()
            io = object.__new__(orchestrator.RealIO)
            io.runtime_dir = runtime_dir
            io.runtime_identity = info.st_dev, info.st_ino
            io.socket_identity = None
            io.socket_seen_bad = False
            io.lease_seen_bad = False
            io.lease_removed = False
            io.lease_cleanup_code = "not_observed"
            io.candidate = None
            io._cleanup_removal_allowed = True
            ok, code = io._remove_private_socket()
            self.assertTrue(ok)
            self.assertEqual(code, "never_created_empty")
            self.assertTrue(io._remove_runtime_dir())
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
