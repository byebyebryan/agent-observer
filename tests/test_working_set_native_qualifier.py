"""Synthetic-only controls for the bounded installed native qualifier."""

import copy
import gc
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import time
import types
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

from test_active_service_delivery import local_uid
from test_working_set_contract import fixture, outside

from agent_observer.contract import canonical
from agent_observer.working_set_contract import validate_frame

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qualify-working-set-native"
LOADER = importlib.machinery.SourceFileLoader("qualify_working_set_native", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
qualifier = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = qualifier
LOADER.exec_module(qualifier)

HOME = Path("/fixture/codex")
WINDOW_MS = 72 * 60 * 60 * 1000
WALL_MS = 1_700_000_020_000
BOOT_MS = 10_001


def working_frame(*, recent=True, active=True):
    value = local_uid(fixture(recent=recent, active=active, window=WINDOW_MS))
    namespace = qualifier._native_namespace(HOME, os.getuid())
    source = value["sources"][0]
    source.update(configHome=str(HOME), configHomeKind="explicit", namespace=namespace)
    scope = value["projection"]["scopes"][0]
    scope["namespace"] = namespace
    for row in value["projection"]["sessions"]:
        row["identity"]["namespace"] = namespace
    for collection in ("members", "nonmembers", "uncertain"):
        for entry in scope[collection]:
            entry["identity"]["namespace"] = namespace
    value["emittedAt"] = WALL_MS
    if recent:
        member = scope["members"][0]
        activity_at = member["recent"]["activityAt"]
        clock = scope["clocks"][0]
        member["recent"]["lowerBoottimeMs"] = activity_at + WINDOW_MS - value["clockCeiling"]
        member["recent"]["upperBoottimeMs"] = (
            clock["acceptedBoottimeMs"] + WINDOW_MS - (clock["wallMs"] - activity_at) + 1
        )
    validate_frame(value, expected_host="fixture", expected_uid=os.getuid(),
                    expected_window_ms=WINDOW_MS)
    return value


def native_sample(frame, *, runtime="running", kind=None, activity=None, status=None,
                  has_saved=True, loaded=True, title="SENSITIVE_NATIVE_TITLE"):
    row = frame["projection"]["sessions"][0]
    native_id = row["identity"]["nativeId"]
    candidate_activity = row["activity"].get("at")
    activity = candidate_activity if activity is None else activity
    kind = row["kind"] if kind is None else kind
    if status is None:
        status = "active" if runtime == "running" else "notLoaded" if runtime == "parked" else None
    native_row = {
        "kind": kind,
        "runtime": runtime,
        "activity": activity,
        "activityReason": "native_turn_metadata" if type(activity) is int else "native_turn_read_unavailable",
        "hasSavedHistory": has_saved,
        "sessionTreeRootId": row["nativeIds"]["sessionTreeRootId"],
        "latestTurn": {"id": "SENSITIVE_TURN_ID"},
        "status": status,
        "title": title,
        "cwd": "/sensitive/native/cwd",
    }
    loaded_ids = [native_id] if loaded else []
    return {
        "sampleAt": WALL_MS,
        "rows": {native_id: native_row},
        "loaded": loaded_ids,
        "loadedAfter": list(loaded_ids),
        "saved": [native_id] if has_saved else [],
        "runtimeGaps": [],
    }


def compare(frame, before=None, after=None):
    sample = native_sample(frame) if before is None else before
    after = sample if after is None else after
    clocks = frame["projection"]["scopes"][0]["clocks"]
    walls = [frame["emittedAt"], *(clock["wallMs"] for clock in clocks)]
    boots = [frame["emittedBoottimeMs"], *(clock[name] for clock in clocks
                                               for name in ("sampledBoottimeMs", "acceptedBoottimeMs"))]
    return qualifier.compare_frame(
        sample, frame, after, host="fixture", home=HOME, window_ms=WINDOW_MS,
        start_wall_ms=min(walls) - 10, end_wall_ms=max(walls) + 10,
        start_boot_ms=min(boots) - 10, end_boot_ms=max(boots) + 10,
        hash_key=b"qualification-test-key",
    )


def no_turn_working_frame():
    frame = working_frame(recent=True, active=False)
    entry = outside(frame)
    entry["reason"] = "no_activity"
    entry["recent"].update(
        kind="no_activity",
        activityAt=None,
        lowerBoottimeMs=None,
        upperBoottimeMs=None,
        absence={
            "field": "latestTurn",
            "activity": {
                "at": None,
                "source": None,
                "health": "unavailable",
                "reason": "no_conversation_activity",
            },
            "latestTurn": {
                "value": None,
                "observedAt": 1_700_000_020_000,
                "source": "codex_rpc",
                "health": "current",
                "reason": "no_native_turn",
                "receipt": {
                    "component": "runtime",
                    "sampledBoottimeMs": 10_000,
                    "observedBoottimeMs": 10_001,
                    "contextGeneration": 1,
                },
            },
        },
    )
    validate_frame(frame, expected_host="fixture", expected_uid=os.getuid(),
                   expected_window_ms=WINDOW_MS)
    return frame


def add_history_clock(frame, *, wall_ms=None, accepted_boottime_ms=None, sample_id=None):
    source = next(item for item in frame["sources"] if item["provider"] == "codex")
    history = next(item for item in source["components"] if item["name"] == "history")
    runtime_clock = next(
        item for item in frame["projection"]["scopes"][0]["clocks"]
        if item["component"] == "runtime"
    )
    clock = copy.deepcopy(runtime_clock)
    clock.update(
        component="history",
        accepted=history["accepted"],
        sampledBoottimeMs=history["sampledBoottimeMs"],
    )
    if wall_ms is not None:
        clock["wallMs"] = wall_ms
    if accepted_boottime_ms is not None:
        clock["acceptedBoottimeMs"] = accepted_boottime_ms
    if sample_id is not None:
        clock["sampleId"] = sample_id
    frame["projection"]["scopes"][0]["clocks"].append(clock)
    validate_frame(frame, expected_host="fixture", expected_uid=os.getuid(),
                   expected_window_ms=WINDOW_MS)
    return clock


class FakeConnection:
    def __init__(self, payload):
        self.payload = payload
        self.request = bytearray()
        self.closed = False

    def settimeout(self, _seconds):
        pass

    def sendall(self, value):
        self.request.extend(value)

    def recv(self, count):
        value = self.payload[:count]
        self.payload = self.payload[count:]
        return value

    def close(self):
        self.closed = True


class FakeRPCSocket:
    def __init__(self):
        self.timeout = 5.0

    def gettimeout(self):
        return self.timeout

    def settimeout(self, value):
        self.timeout = value


class FakeRPC:
    def __init__(self):
        self.buffer = bytearray()
        self.sock = FakeRPCSocket()
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"data": [], "nextCursor": None}

    def recv(self, _count):
        raise AssertionError("fake RPC unexpectedly read a socket")

    def pages(self, method):
        return ["original", method]


class WorkingSetNativeQualifierTest(unittest.TestCase):
    def test_stable_active_match_is_sanitized(self):
        frame = working_frame(recent=True, active=True)
        result = compare(frame)
        encoded = json.dumps(result, sort_keys=True)
        self.assertEqual(result["status"], "match")
        self.assertEqual(result["membershipStatus"], "match")
        self.assertEqual(result["fieldStatus"], "match")
        self.assertEqual(result["counts"]["nativeComplete"], True)
        for secret in (frame["projection"]["sessions"][0]["identity"]["nativeId"],
                       "SENSITIVE_NATIVE_TITLE", "SENSITIVE_TURN_ID", "/sensitive/native/cwd"):
            self.assertNotIn(secret, encoded)

    def test_runtime_mismatch_is_reported_and_native_race_is_unresolved(self):
        parked_frame = working_frame(recent=True, active=False)
        mismatch = compare(
            parked_frame,
            native_sample(parked_frame, runtime="running", status="active", loaded=True),
        )
        self.assertEqual(mismatch["status"], "mismatch")
        self.assertEqual(mismatch["mismatchCounts"]["runtime_mismatch"], 1)

        frame = working_frame(recent=True, active=True)
        before = native_sample(frame)
        after = copy.deepcopy(before)
        native_id = next(iter(after["rows"]))
        after["rows"][native_id]["activity"] += 1
        raced = compare(frame, before, after)
        self.assertEqual(raced["membershipStatus"], "unresolved")
        self.assertEqual(raced["status"], "unresolved")
        self.assertGreater(raced["reasonCounts"].get("native_row_raced_or_missing", 0), 0)

    def test_unknown_kind_and_runtime_can_select_on_independently_positive_recent(self):
        frame = working_frame(recent=True, active=True)
        row = frame["projection"]["sessions"][0]
        frame["projection"]["scopes"][0]["members"][0]["active"] = None
        row["kind"] = "unknown"
        row["runtime"].update(
            value="unknown", observedAt=None, source=None, clock=None,
            health="unavailable", reason="not_observed",
        )
        row["phase"].update(
            value="unknown", observedAt=None, source=None, clock=None,
            health="unavailable", reason="not_observed",
        )
        row["blockedReasons"] = []
        validate_frame(frame, expected_host="fixture", expected_uid=os.getuid(),
                        expected_window_ms=WINDOW_MS)
        native = native_sample(frame, runtime="unknown", kind="unknown", status=None,
                               loaded=False)
        result = compare(frame, native)
        self.assertEqual(result["membershipStatus"], "unresolved")
        self.assertEqual(result["counts"]["expectedMembers"], 1)
        self.assertEqual(result["counts"]["conditionalMemberships"], 1)
        self.assertEqual(result["conditionalMembershipStatus"], "producer_clock_ceiling_dependent")
        self.assertEqual(result["status"], "unresolved")
        self.assertGreater(result["reasonCounts"].get("candidate_runtime_not_current", 0), 0)

    def test_r_only_positive_at_current_clock_floor_is_conditional_on_historical_k(self):
        frame = working_frame(recent=True, active=False)
        scope = frame["projection"]["scopes"][0]
        independent_floor = max(
            clock["wallMs"] - clock["sampledBoottimeMs"] + 1
            for clock in scope["clocks"]
        )
        frame["clockCeiling"] = independent_floor
        validate_frame(frame, expected_host="fixture", expected_uid=os.getuid(),
                       expected_window_ms=WINDOW_MS)
        native = native_sample(frame, runtime="parked", status="notLoaded", loaded=False)
        result = compare(frame, native)
        self.assertEqual(result["membershipStatus"], "unresolved")
        self.assertEqual(result["conditionalMembershipStatus"],
                         "producer_clock_ceiling_dependent")
        self.assertEqual(result["counts"]["conditionalMemberships"], 1)
        self.assertEqual(result["counts"]["membershipMatches"], 0)
        self.assertEqual(result["fieldStatus"], "match")
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["exitCode"], 3)

    def test_native_active_positive_keeps_membership_independent_when_activity_is_unknown(self):
        frame = working_frame(recent=False, active=True)
        row = frame["projection"]["sessions"][0]
        row["activity"].update(
            at=None, source=None, health="unavailable", reason="metadata_unavailable",
        )
        frame["projection"]["scopes"][0]["members"][0]["fieldSupports"]["activity"] = None
        validate_frame(frame, expected_host="fixture", expected_uid=os.getuid(),
                       expected_window_ms=WINDOW_MS)
        native = native_sample(frame, runtime="running", activity=0)
        native_id = next(iter(native["rows"]))
        native["rows"][native_id].update(
            activity=None, activityReason="native_turn_read_unavailable",
            latestTurn={"id": "SENSITIVE_TURN_WITHOUT_CLOCK"},
        )
        result = compare(frame, native)
        self.assertEqual(result["membershipStatus"], "match")
        self.assertEqual(result["conditionalMembershipStatus"], "none")
        self.assertEqual(result["counts"]["expectedMembers"], 1)
        self.assertEqual(result["counts"]["conditionalMemberships"], 0)
        self.assertEqual(result["status"], "unresolved")

    def test_complete_scope_omits_never_selected_old_parked_without_negative_dto(self):
        frame = working_frame(recent=True, active=True)
        add_history_clock(frame)
        before = native_sample(frame)
        old_id = "00000000-0000-0000-0000-000000000099"
        old_activity = WALL_MS - 8 * 24 * 60 * 60 * 1000
        before["rows"][old_id] = {
            "kind": "user", "runtime": "parked", "activity": old_activity,
            "activityReason": "native_turn_metadata", "hasSavedHistory": True,
            "sessionTreeRootId": "00000000-0000-0000-0000-000000000098",
            "latestTurn": {"id": "SENSITIVE_OLD_TURN"}, "status": "notLoaded",
            "title": "SENSITIVE_OLD_TITLE", "cwd": "/sensitive/old/cwd",
        }
        before["saved"].append(old_id)
        after = copy.deepcopy(before)
        result = compare(frame, before, after)
        self.assertEqual(result["status"], "match")
        self.assertEqual(result["membershipStatus"], "match")
        self.assertEqual(result["counts"]["candidateOmittedExpectedNegative"], 1)
        self.assertEqual(result["counts"]["expectedNonmembers"], 1)
        self.assertNotIn(old_id, json.dumps(result, sort_keys=True))

    def test_omitted_row_requires_both_current_component_clocks_before_using_later_dhi(self):
        frame = working_frame(recent=True, active=True)
        runtime_clock = frame["projection"]["scopes"][0]["clocks"][0]
        history_wall = runtime_clock["wallMs"] - 48 * 60 * 60 * 1000
        activity_at = history_wall - (WINDOW_MS - 60 * 60 * 1000)
        history_clock = add_history_clock(
            frame,
            wall_ms=history_wall,
            sample_id="00000000-0000-0000-0000-000000000077",
        )
        old_id = "00000000-0000-0000-0000-000000000099"
        before = native_sample(frame)
        before["rows"][old_id] = {
            "kind": "user", "runtime": "parked", "activity": activity_at,
            "activityReason": "native_turn_metadata", "hasSavedHistory": True,
            "sessionTreeRootId": "SENSITIVE_OLD_ROOT", "latestTurn": {"id": "SENSITIVE_OLD_TURN"},
            "status": "notLoaded",
        }
        before["saved"].append(old_id)
        after = copy.deepcopy(before)

        one_clock = copy.deepcopy(frame)
        one_clock["projection"]["scopes"][0]["clocks"] = [
            clock for clock in one_clock["projection"]["scopes"][0]["clocks"]
            if clock["component"] == "runtime"
        ]
        runtime_only, runtime_reason = qualifier._recent_decision(
            before["rows"][old_id], None, None, None, None, one_clock, WINDOW_MS,
            one_clock["clockCeiling"], clock_bracket_ok=True,
            scope=one_clock["projection"]["scopes"][0], clock_census_complete=True,
        )
        self.assertFalse(runtime_only)
        self.assertEqual(runtime_reason, "outside_window_from_scope_clock_census")

        incomplete = compare(one_clock, before, after)
        self.assertEqual(incomplete["counts"]["expectedNonmembers"], 0)
        self.assertEqual(incomplete["counts"]["candidateOmittedExpectedNegative"], 0)
        self.assertEqual(incomplete["counts"]["membershipUnresolved"], 1)
        self.assertGreater(incomplete["reasonCounts"].get("activity_clock_census_incomplete", 0), 0)

        complete = compare(frame, before, after)
        self.assertEqual(complete["counts"]["expectedNonmembers"], 0)
        self.assertEqual(complete["counts"]["candidateOmittedExpectedNegative"], 0)
        self.assertEqual(complete["counts"]["membershipUnresolved"], 1)
        self.assertGreater(complete["reasonCounts"].get("clock_bracket_overlap", 0), 0)
        self.assertEqual(history_clock["wallMs"], history_wall)
        self.assertEqual(complete["conditionalMembershipStatus"], "none")

    def test_loaded_and_saved_not_loaded_qualification_stays_conservative(self):
        frame = working_frame(recent=False, active=True)
        row = frame["projection"]["sessions"][0]
        native_id = row["identity"]["nativeId"]
        parked = native_sample(frame, runtime="parked", status="notLoaded", loaded=False)
        rows, loaded, saved, gaps = qualifier._native_semantics(
            parked, "fixture", qualifier._native_namespace(HOME, os.getuid()))
        normalized = next(iter(rows.values()))
        self.assertEqual((normalized["runtime"], loaded, saved), ("parked", set(), {native_id}))
        self.assertEqual(gaps, [])

        stale = copy.deepcopy(parked)
        stale["saved"] = []
        rows, _loaded, _saved, gaps = qualifier._native_semantics(
            stale, "fixture", qualifier._native_namespace(HOME, os.getuid()))
        self.assertEqual(next(iter(rows.values()))["runtime"], "unknown")
        self.assertIn("native_not_loaded_identity_unproved", gaps)

    def test_native_empty_turn_is_distinct_from_nonempty_turn_without_timestamps(self):
        frame = no_turn_working_frame()
        empty_id = frame["projection"]["scopes"][0]["nonmembers"][0]["identity"]["nativeId"]

        def parked_sample(latest_turn):
            return {
                "sampleAt": WALL_MS,
                "rows": {
                    empty_id: {
                        "kind": "user",
                        "runtime": "parked",
                        "activity": None,
                        "activityReason": "no_native_turn_clock",
                        "hasSavedHistory": True,
                        "sessionTreeRootId": "SENSITIVE_ROOT_ID",
                        "latestTurn": latest_turn,
                        "status": "notLoaded",
                    },
                },
                "loaded": [],
                "loadedAfter": [],
                "saved": [empty_id],
                "runtimeGaps": [],
            }

        empty = parked_sample(None)
        empty_rows, _loaded, _saved, empty_gaps = qualifier._native_semantics(
            empty, "fixture", qualifier._native_namespace(HOME, os.getuid()))
        empty_native = next(iter(empty_rows.values()))
        self.assertTrue(empty_native["nativeNoTurn"])
        self.assertEqual(empty_gaps, [])
        empty_result = compare(frame, empty, copy.deepcopy(empty))
        self.assertEqual(empty_result["fieldCounts"].get("activity_no_turn_match"), 1)
        self.assertEqual(empty_result["counts"]["expectedNonmembers"], 1)
        self.assertEqual(empty_result["membershipStatus"], "match")

        missing_clock = parked_sample({"id": "SENSITIVE_TURN_ID"})
        missing_rows, _loaded, _saved, missing_gaps = qualifier._native_semantics(
            missing_clock, "fixture", qualifier._native_namespace(HOME, os.getuid()))
        missing_native = next(iter(missing_rows.values()))
        self.assertFalse(missing_native["nativeNoTurn"])
        self.assertEqual(missing_gaps, [])
        missing_result = compare(frame, missing_clock, copy.deepcopy(missing_clock))
        self.assertEqual(missing_result["fieldCounts"].get("activity_no_turn_match", 0), 0)
        self.assertEqual(missing_result["counts"]["expectedNonmembers"], 0)
        self.assertEqual(missing_result["counts"]["candidateOmittedExpectedNegative"], 0)
        self.assertEqual(missing_result["counts"]["membershipUnresolved"], 1)
        self.assertEqual(missing_result["membershipStatus"], "unresolved")
        self.assertGreater(missing_result["reasonCounts"].get("activity_unproved", 0), 0)
        self.assertNotIn("SENSITIVE_TURN_ID", json.dumps(missing_result, sort_keys=True))

    def test_three_valued_union_preserves_positive_branch(self):
        self.assertIsNone(qualifier._three_or(None, False))
        self.assertTrue(qualifier._three_or(None, True))
        self.assertTrue(qualifier._three_and(True, True))
        self.assertTrue(qualifier._three_and(True, qualifier._three_or(None, True)))
        self.assertIsNone(qualifier._three_and(True, None))
        self.assertFalse(qualifier._three_and(None, False))

    def test_private_fake_endpoint_uses_strict_parser_and_closes_only_reader(self):
        frame = working_frame(recent=True, active=True)
        payload = (canonical(frame) + "\n").encode()
        connection = FakeConnection(payload)
        fake_peer = {"socketPath": "/private/fixture.sock", "pid": 1234}
        with patch.object(qualifier, "_service_peer", return_value=(connection, fake_peer)), \
                patch.object(qualifier, "_recheck_service"):
            accepted, peer = qualifier._read_candidate(
                Path("/private/fixture.sock"), host="fixture", window_ms=WINDOW_MS,
                expected_python=Path("/venv/bin/python"), expected_python_sha="0" * 64,
                observer_cli=Path("/venv/bin/observer-service"), home=HOME,
                deadline=time.monotonic() + 1,
            )
        self.assertEqual(accepted["sequence"], frame["sequence"])
        self.assertEqual(peer["pid"], 1234)
        self.assertTrue(connection.closed)
        request = json.loads(connection.request)
        self.assertEqual(request["operation"], "watch")
        self.assertEqual(request["selector"]["recent"]["windowMs"], WINDOW_MS)

    def test_absent_candidate_socket_wait_is_read_only_and_does_not_autostart(self):
        with tempfile.TemporaryDirectory(prefix="ws-native-private-") as raw:
            runtime = Path(raw)
            private = runtime / "private"
            private.mkdir(mode=0o700)
            private.chmod(0o700)
            path = private / "read.sock"
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}):
                with self.assertRaises(qualifier.QualificationError) as caught:
                    qualifier._wait_for_candidate_socket(path, time.monotonic() + 0.03)
            self.assertEqual(caught.exception.code, "candidate_socket_wait_timeout")
            self.assertFalse(path.exists())

    def test_service_process_guard_accepts_cli_path_string_and_rejects_extra_modes(self):
        with tempfile.TemporaryDirectory(prefix="ws-native-proc-") as raw:
            proc = Path(raw) / "1234"
            proc.mkdir()
            args = [
                str(Path(sys.executable)), str(SCRIPT), "serve",
                "--host-scope", "fixture", "--socket", "/tmp/fixture.sock",
                "--provider", "codex", "--codex-home", str(HOME),
                "--working-set-window-hours", "72",
            ]
            cmdline = proc / "cmdline"
            cmdline.write_bytes(b"\0".join(os.fsencode(value) for value in args) + b"\0")
            qualifier._service_arguments(
                Path(raw), 1234, python_entrypoint=Path(sys.executable),
                cli_entrypoint=str(SCRIPT), host="fixture", home=HOME,
                service_socket=Path("/tmp/fixture.sock"), window_hours=72,
            )
            cmdline.write_bytes(os.fsencode(args[0]) + b"\0" + os.fsencode(args[1])
                                + b"\0" + b"\0".join(os.fsencode(value) for value in args[2:])
                                + b"\0--native-hints\0")
            with self.assertRaises(qualifier.QualificationError) as caught:
                qualifier._service_arguments(
                    Path(raw), 1234, python_entrypoint=Path(sys.executable),
                    cli_entrypoint=str(SCRIPT), host="fixture", home=HOME,
                    service_socket=Path("/tmp/fixture.sock"), window_hours=72,
                )
            self.assertEqual(caught.exception.code, "candidate_process_extra_configuration")

    def test_bounded_native_wrappers_are_restored_without_a_client_cycle(self):
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            for fail in (False, True):
                client = FakeRPC()
                weak_client = weakref.ref(client)
                original_timeout = client.sock.gettimeout()

                def reference(value, should_fail=fail):
                    if should_fail:
                        raise ValueError("private_title")
                    return value.pages("thread/list")

                module = types.SimpleNamespace(codex_reference=reference)
                if fail:
                    with self.assertRaises(qualifier.QualificationError) as caught:
                        qualifier._bounded_native_reference(
                            module, client, deadline=time.monotonic() + 5,
                            rpc_timeout_seconds=2, max_rows=10,
                        )
                    failure_code = caught.exception.code
                    del caught
                    self.assertEqual(failure_code, "native_reference_failed")
                else:
                    self.assertEqual(qualifier._bounded_native_reference(
                        module, client, deadline=time.monotonic() + 5,
                        rpc_timeout_seconds=2, max_rows=10,
                    ), [])
                self.assertIs(client.call.__func__, FakeRPC.call)
                self.assertIs(client.recv.__func__, FakeRPC.recv)
                self.assertIs(client.pages.__func__, FakeRPC.pages)
                self.assertEqual(client.sock.gettimeout(), original_timeout)
                del client
                self.assertIsNone(weak_client())
        finally:
            if gc_enabled:
                gc.enable()

    def test_existing_native_oracle_loads_without_invoking_it(self):
        module, digest = qualifier._load_native_oracle()
        self.assertEqual(len(digest), 64)
        self.assertTrue(callable(module.NativeRPC))
        self.assertTrue(callable(module.codex_reference))

    def test_thread_read_empty_turns_placeholder_is_discarded_and_nonempty_rejected(self):
        thread_id = "00000000-0000-0000-0000-000000000001"

        class EmptyTurnsRPC(FakeRPC):
            def call(self, _method, _params):
                return {"thread": {"id": thread_id, "turns": []}}

        client = EmptyTurnsRPC()
        module = types.SimpleNamespace(
            codex_reference=lambda value: value.call(
                "thread/read", {"threadId": "00000000-0000-0000-0000-000000000001",
                                "includeTurns": False}),
        )
        result = qualifier._bounded_native_reference(
            module, client, deadline=time.monotonic() + 5,
            rpc_timeout_seconds=2, max_rows=10,
        )
        self.assertEqual(result, {"thread": {"id": thread_id}})
        self.assertIs(client.call.__func__, EmptyTurnsRPC.call)
        self.assertIs(client.pages.__func__, FakeRPC.pages)

        class NonemptyTurnsRPC(FakeRPC):
            def call(self, _method, _params):
                return {"thread": {"turns": [{"id": "SENSITIVE_TURN_CONTENT"}]}}

        client = NonemptyTurnsRPC()
        module = types.SimpleNamespace(
            codex_reference=lambda value: value.call(
                "thread/read", {"threadId": thread_id, "includeTurns": False}),
        )
        with self.assertRaises(qualifier.QualificationError) as caught:
            qualifier._bounded_native_reference(
                module, client, deadline=time.monotonic() + 5,
                rpc_timeout_seconds=2, max_rows=10,
            )
        self.assertEqual(caught.exception.code, "native_content_read_unexpected")
        self.assertIs(client.call.__func__, NonemptyTurnsRPC.call)
        self.assertIs(client.pages.__func__, FakeRPC.pages)

    def test_native_exception_reason_codes_are_allowlisted(self):
        self.assertEqual(
            qualifier._reason_code(ValueError("private_title"), "native_reference_failed"),
            "native_reference_failed",
        )
        self.assertEqual(
            qualifier._reason_code(ValueError("native_rpc_timeout"), "native_reference_failed"),
            "native_rpc_timeout",
        )
        self.assertEqual(
            qualifier._reason_code(
                ValueError("native_saved_detail_unavailable:SENSITIVE_NATIVE_ID"),
                "native_reference_failed",
            ),
            "native_saved_detail_unavailable",
        )

    def test_uv_archive_hashes_and_legacy_pep610_digest_are_bound_to_expected_wheel(self):
        expected = "a" * 64
        with tempfile.TemporaryDirectory(prefix="ws-native-dist-") as raw:
            prefix = Path(raw)
            install = prefix / "lib" / "python" / "site-packages"
            install.mkdir(parents=True)

            class Distribution:
                version = "1.2.3"

                def __init__(self, direct):
                    self.direct = direct

                def read_text(self, name):
                    self.assert_direct_url_name = name
                    return json.dumps(self.direct)

                def locate_file(self, _path):
                    return install

            cases = [
                {"archive_info": {"hashes": {"sha256": expected}}},
                {"archive_info": {"hash": f"sha256={expected}"}},
                {"archive_info": {"hash": f"sha256={expected}",
                                  "hashes": {"sha256": expected}}},
            ]
            for direct in cases:
                with patch.object(qualifier.importlib.metadata, "distribution",
                                  return_value=Distribution(direct)):
                    result = qualifier._distribution("agent-observer", "1.2.3", expected, prefix)
                self.assertEqual(result["wheelSha256"], expected)

            rejected = [
                {"archive_info": {"hashes": {"sha256": "b" * 64}}},
                {"archive_info": {"hash": f"sha256={expected}",
                                  "hashes": {"sha256": "b" * 64}}},
                {"archive_info": {}},
                {"dir_info": {"editable": True}},
                {"dir_info": {"editable": False}, "archive_info": {"hashes": {"sha256": expected}}},
            ]
            for direct in rejected:
                with patch.object(qualifier.importlib.metadata, "distribution",
                                  return_value=Distribution(direct)):
                    with self.assertRaises(qualifier.QualificationError):
                        qualifier._distribution("agent-observer", "1.2.3", expected, prefix)

    def test_same_binary_through_another_venv_does_not_satisfy_entrypoint_identity(self):
        binary = Path(sys.executable).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="ws-native-venvs-") as raw:
            root = Path(raw)
            paths = []
            for name in ("candidate", "other"):
                bindir = root / name / "bin"
                bindir.mkdir(parents=True)
                python = bindir / "python"
                python.symlink_to(binary)
                paths.append(python)
            self.assertEqual(paths[0].resolve(), paths[1].resolve())
            exact, prefix = qualifier._candidate_python_identity(
                paths[0], paths[0], str(paths[0].parent.parent), str(root / "base"))
            self.assertEqual(exact, paths[0])
            self.assertEqual(prefix, root / "candidate")
            with self.assertRaises(qualifier.QualificationError) as caught:
                qualifier._candidate_python_identity(
                    paths[0], paths[1], str(paths[0].parent.parent), str(root / "base"))
            self.assertEqual(caught.exception.code, "candidate_python_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
