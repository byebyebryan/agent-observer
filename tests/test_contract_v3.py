"""Public conformance and independent reader invariants, using metadata fixtures."""

import copy
import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from agent_observer.collection import _coverage, project_session, project_source
from agent_observer.contract import (
    ContractError,
    canonical,
    MAX_BYTES,
    MAX_SESSIONS,
    MAX_SNAPSHOT_BYTES,
    parse_snapshot,
    parse_watch,
    schema_document,
    store_namespace,
    validate_snapshot,
    validate_watch,
)
from agent_observer.read_client import human_rows, ordered_rows, select
from agent_observer.watch import SampledWatch

FIXTURES = Path(__file__).parent / "fixtures/contract-v3"


def fixture(name="snapshot"):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class ContractV3Test(unittest.TestCase):
    def test_parked_runtime_requires_proved_source_and_preserves_turn_outcome(self):
        value = fixture("claude-ready")
        original = value["sessions"][-1]
        source = copy.deepcopy(value["sources"][-1])
        native = {"identity": original["identity"], "nativeIds": original["nativeIds"],
                  "title": original["title"], "sessionKind": "bg", "job": original["job"],
                  "work": {"value": "settled", "observedAt": 1000, "source": "claude_job_store",
                           "health": "current", "reason": "native_snapshot"},
                  "runtimeDisposition": {"value": "parked", "observedAt": 2000,
                                         "source": "claude_job_store", "health": "current", "reason": "native_snapshot"}}
        self.assertEqual(project_session(native, source)["runtime"]["value"], "unknown")
        source["capabilities"]["runtime"].append("parked")
        row = project_session(native, source)
        self.assertEqual(row["runtime"]["value"], "parked")
        self.assertEqual(row["runtime"]["clock"], "sample")
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["outcome"]["value"], "completed")
        self.assertEqual(row["outcome"]["observedAt"], 1000)
        native["runtimeDisposition"]["health"] = "stale"
        self.assertEqual(project_session(native, source)["runtime"]["value"], "unknown")
        native["runtimeDisposition"]["health"] = "current"
        native["presence"] = {"value": "present", "observedAt": 2100, "source": "claude_registry",
                              "health": "current", "reason": "native_snapshot"}
        self.assertEqual(project_session(native, source)["runtime"]["value"], "running")

    def test_codex_question_requires_a_proved_runtime_source_capability(self):
        value = fixture()
        original = value["sessions"][0]
        source = copy.deepcopy(value["sources"][0])
        native = {"identity": original["identity"], "nativeIds": original["nativeIds"],
                  "title": original["title"], "waitReason": "user_input",
                  "work": {"value": "needs_input", "observedAt": 123,
                           "source": "codex_rpc", "health": "current", "reason": "native_snapshot"}}
        self.assertEqual(project_session(native, source)["phase"]["value"], "unknown")
        source["capabilities"]["blockedReasons"].append("question")
        row = project_session(native, source)
        self.assertEqual(row["phase"]["value"], "blocked")
        self.assertEqual(row["blockedReason"], "question")

    def test_claude_question_requires_the_verified_worker_contract(self):
        value = fixture("claude-ready")
        original = value["sessions"][-1]
        native = {"identity": original["identity"], "nativeIds": original["nativeIds"],
                  "title": original["title"], "waitReason": "question",
                  "work": {"value": "needs_input", "observedAt": 123,
                           "source": "claude_registry", "health": "current", "reason": "native_snapshot"}}
        source = value["sources"][-1]
        self.assertEqual(project_session(native, source)["phase"]["value"], "unknown")
        native["phaseCapabilities"] = ["input_wait", "job_question"]
        row = project_session(native, source)
        self.assertEqual(row["phase"]["value"], "blocked")
        self.assertEqual(row["blockedReason"], "question")
        native["waitReason"] = "user_input"
        generic = project_session(native, source)
        self.assertEqual(generic["phase"]["value"], "unknown")
        self.assertEqual(generic["blockedReason"], "unknown")
        native.update(sessionKind="interactive", phaseCapabilities=["interactive_readiness"],
                      presence={"value": "present", "observedAt": 123, "source": "claude_registry",
                                "health": "current", "reason": "native_snapshot"})
        native["nativeIds"] = {**native["nativeIds"], "jobId": None}
        native["work"]["value"] = "settled"
        self.assertEqual(project_session(native, source)["phase"]["value"], "waiting")
        native["phaseCapabilities"] = []
        self.assertEqual(project_session(native, source)["phase"]["value"], "unknown")

    def test_foreground_claude_question_needs_explicit_worker_predicate(self):
        value = fixture("claude-ready")
        original = value["sessions"][-1]
        native = {"identity": original["identity"], "nativeIds": {**original["nativeIds"], "jobId": None},
                  "title": original["title"], "sessionKind": "interactive", "waitReason": "question",
                  "phaseCapabilities": ["registry_phase", "input_wait", "foreground_question"],
                  "presence": {"value": "present", "observedAt": 123, "source": "claude_registry", "health": "current", "reason": "native_snapshot"},
                  "work": {"value": "needs_input", "observedAt": 123, "source": "claude_registry", "health": "current", "reason": "native_snapshot"}}
        row = project_session(native, value["sources"][-1])
        self.assertEqual((row["phase"]["value"], row["blockedReason"]), ("blocked", "question"))
        native["phaseCapabilities"] = ["registry_phase", "input_wait"]
        self.assertEqual(project_session(native, value["sources"][-1])["phase"]["value"], "unknown")
        native["phaseCapabilities"].append("foreground_question")
        native["waitReason"] = "user_input"
        self.assertEqual(project_session(native, value["sources"][-1])["phase"]["value"], "unknown")

    def test_codex_outcome_does_not_settle_a_failed_runtime(self):
        value = fixture()
        original = value["sessions"][0]
        native = {"identity": original["identity"], "nativeIds": original["nativeIds"],
                  "title": original["title"], "nativeState": {"type": "systemError"},
                  "outcome": {"value": "failed", "observedAt": 120000,
                              "source": "codex_turn_metadata", "health": "current",
                              "reason": "latest_terminal_turn"}}
        row = project_session(native, value["sources"][0])
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["phase"]["reason"], "native_runtime_error")
        self.assertEqual(row["outcome"]["value"], "failed")
        self.assertEqual(row["outcome"]["clock"], "native")
        self.assertEqual(row["outcome"]["observedAt"], 120000)

    def test_failed_saved_dimension_does_not_become_partial_from_healthy_runtime(self):
        self.assertEqual(
            _coverage({"complete": False, "reason": "source_failed"}, "current")["status"],
            "unavailable",
        )
        self.assertEqual(
            _coverage({"complete": False, "reason": "metadata_scan"}, "partial")["status"],
            "partial",
        )
        self.assertEqual(
            _coverage({"complete": False, "reason": "metadata_scan"}, "unavailable")["status"],
            "partial",
        )

    def test_unavailable_claude_runtime_does_not_advertise_phase_or_running(self):
        source = project_source({
            "provider": "claude", "host": {"uid": os.geteuid()},
            "configHome": "/tmp/fixture", "sessions": [], "runtime": None,
            "sourceHealth": "unavailable", "coverage": {"sessionRegistry": "unavailable"},
        })
        self.assertEqual(source["capabilities"]["phase"], [])
        self.assertEqual(source["capabilities"]["runtime"], [])
        self.assertEqual(source["capabilities"]["blockedReasons"], [])

    def test_bundled_schemas_match_public_spec(self):
        root = Path(__file__).parent.parent / "agent_observer/contracts"
        for name in ("snapshot", "watch"):
            self.assertEqual(
                json.loads((root / f"{name}.schema.json").read_text()), schema_document(name)
            )

    def test_both_provider_and_partial_fixtures_conform(self):
        for name in ("snapshot", "partial", "claude-ready"):
            validate_snapshot(fixture(name))
        validate_watch(fixture("gap"))
        rows = fixture()["sessions"]
        completed = rows[-1]
        self.assertEqual(completed["outcome"]["value"], "completed")
        self.assertEqual(completed["phase"]["value"], "unknown")
        self.assertEqual(completed["runtime"]["value"], "unknown")
        self.assertTrue(all(row["activity"]["at"] is None for row in rows))

    def test_claude_waiting_requires_proved_bg_completion_and_current_worker(self):
        value = fixture("claude-ready")
        ready = value["sessions"][-1]
        source = value["sources"][-1]
        native = {
            "identity": ready["identity"],
            "nativeIds": ready["nativeIds"],
            "title": ready["title"],
            "sessionKind": "bg",
            "job": ready["job"],
            "inventory": "live",
            "history": ready["history"],
            "presence": {k: v for k, v in ready["worker"].items() if k != "clock"},
            "work": {
                **{k: v for k, v in ready["outcome"].items() if k != "clock"},
                "value": "settled",
            },
        }
        row = project_session(native, source)
        self.assertEqual(row["phase"]["value"], "waiting")
        self.assertEqual(row["phase"]["clock"], "native")
        self.assertEqual(row["worker"]["clock"], "sample")
        self.assertEqual(row["phase"]["observedAt"], ready["outcome"]["observedAt"])
        for change in (
            lambda n: n["presence"].update(value="absent"),
            lambda n: n.update(sessionKind="interactive"),
            lambda n: n["job"].update(state="working"),
        ):
            changed = copy.deepcopy(native)
            change(changed)
            self.assertEqual(project_session(changed, source)["phase"]["value"], "unknown")

    def test_rejects_private_payloads_schema_and_identity_conflicts(self):
        mutations = [
            lambda v: v.update(schemaVersion=1),
            lambda v: v["sessions"][0].update(prompt="private"),
            lambda v: v["sessions"][0]["identity"].update(hostScope="elsewhere"),
            lambda v: v["sessions"][0]["nativeIds"].update(
                threadId=v["sessions"][1]["nativeIds"]["threadId"]
            ),
            lambda v: v["sessions"].append(copy.deepcopy(v["sessions"][0])),
            lambda v: v["sessions"][0]["phase"].update(observedAt=None),
            lambda v: v["sessions"][0]["activity"].update(at=123),
            lambda v: v["sessions"][0]["phase"].update(health="stale"),
        ]
        for mutate in mutations:
            value = fixture()
            mutate(value)
            with self.assertRaises(ContractError):
                parse_snapshot(canonical(value).encode())

    def test_claude_user_kind_requires_exact_non_sidechain_activity_evidence(self):
        ready = fixture("claude-ready")["sessions"][-1]
        source = fixture("claude-ready")["sources"][-1]
        native = {
            "identity": ready["identity"], "nativeIds": ready["nativeIds"],
            "title": ready["title"], "sessionKind": "bg",
            "activity": {"at": 123, "health": "current",
                         "source": "claude_transcript_message",
                         "reason": "native_conversation_event"},
        }
        self.assertEqual(project_session(native, source)["kind"], "user")
        for change in (
            {"at": None}, {"health": "stale"}, {"source": "file_mtime"},
            {"reason": "unobserved"},
        ):
            changed = copy.deepcopy(native)
            changed["activity"].update(change)
            self.assertEqual(project_session(changed, source)["kind"], "unknown")
        # A child transcript carries its parent's UUID. Runtime kind or that
        # UUID alone must not classify the parent as a child.
        native.update(sessionKind="subagent", activity={})
        self.assertEqual(project_session(native, source)["kind"], "unknown")

    def test_claude_unknown_phases_explain_bounded_native_source_limits(self):
        value = fixture("claude-ready")
        ready, source = value["sessions"][-1], value["sources"][-1]
        native = {"identity": ready["identity"], "nativeIds": ready["nativeIds"],
                  "title": ready["title"], "sessionKind": "bg",
                  "nativeStatus": {"value": "idle"},
                  "job": {"state": "working"}, "work": {"value": "unknown"},
                  "presence": {"value": "present", "health": "current",
                               "observedAt": 123, "source": "claude_registry",
                               "reason": "native_snapshot"}}
        phase = project_session(native, source)["phase"]
        self.assertEqual(phase["reason"], "background_readiness_unproved")
        self.assertEqual(phase["health"], "unsupported")
        native["metadataIssues"] = ["native_blocked_phase_unproved"]
        self.assertEqual(project_session(native, source)["phase"]["reason"],
                         "native_blocked_phase_unproved")

    def test_default_order_attention_unknown_activity_and_child_filter(self):
        value = fixture()
        rows = ordered_rows(value)
        self.assertEqual(
            [row["phase"]["value"] for row in rows], ["blocked", "waiting", "working", "unknown"]
        )
        self.assertEqual(len(ordered_rows(value, include_children=True)), 5)
        row = copy.deepcopy(value["sessions"][2])
        row["kind"] = "unknown"
        value["sessions"][2] = row
        self.assertEqual(len(ordered_rows(value)), 5)
        self.assertEqual(select(value, row["identity"]), row)

    def test_store_reference_does_not_depend_on_runtime_incarnation(self):
        args = ("codex", "/fixture/home", "explicit", 1000)
        self.assertEqual(store_namespace(*args), store_namespace(*args))
        self.assertNotEqual(store_namespace(*args), store_namespace("claude", *args[1:]))
        self.assertNotEqual(store_namespace(*args), store_namespace(*args[:3], 1001))

    def test_watch_unchanged_poll_does_not_manufacture_change(self):
        watch = SampledWatch()
        value = fixture()
        self.assertEqual(watch.sample(value)[0]["kind"], "snapshot")
        value["collectionId"] = "00000000-0000-0000-0000-000000000099"
        value["collectedAt"] += 1000
        for row in value["sessions"]:
            for dimension in ("phase", "runtime"):
                if row[dimension]["clock"] == "sample":
                    row[dimension]["observedAt"] += 1000
        self.assertEqual(watch.sample(value)[0]["kind"], "heartbeat")
        value["sessions"][0]["title"] = "Changed native title"
        self.assertEqual(watch.sample(value)[0]["kind"], "change")

    def test_watch_gap_retains_partial_missing_facts_and_original_age(self):
        watch = SampledWatch()
        before = fixture()
        before["sessions"][-2]["activity"] = {
            "at": 1700000010000, "source": "codex_turn_metadata",
            "health": "current", "reason": "native_conversation_event",
        }
        watch.sample(before)
        frames = watch.sample(fixture("partial"))
        self.assertEqual([frame["kind"] for frame in frames], ["gap", "resync"])
        original = before["sessions"][-2]
        retained = select(frames[-1]["snapshot"], original["identity"])
        self.assertEqual(retained["phase"]["value"], "unknown")
        self.assertEqual(retained["phase"]["lastKnownValue"], "working")
        self.assertEqual(retained["phase"]["observedAt"], original["phase"]["observedAt"])
        self.assertEqual(retained["runtime"]["value"], "unknown")
        self.assertIsNone(retained["activity"]["at"])
        self.assertEqual(retained["activity"]["lastKnownAt"], original["activity"]["at"])
        repeated = watch.sample(fixture("partial"))
        self.assertEqual(select(watch.previous, original["identity"])["activity"]["lastKnownAt"],
                         original["activity"]["at"])
        self.assertIn("stale:", human_rows(watch.previous))
        self.assertEqual(repeated[-1]["kind"], "heartbeat")
        watch.gap("collection_failed")
        self.assertEqual(watch.sample(before)[0]["kind"], "resync")
        self.assertNotIn("lastKnownAt", select(watch.previous, original["identity"])["activity"])

    def test_stale_activity_requires_its_own_provenance_and_v2_is_rejected(self):
        value = fixture()
        row = value["sessions"][0]
        row["activity"] = {"at": None, "lastKnownAt": 123,
                           "health": "stale", "source": "codex_turn_metadata", "reason": "observation_gap"}
        validate_snapshot(value)
        for change in ({"at": 456}, {"health": "current"}, {"source": None}):
            invalid = copy.deepcopy(value)
            invalid["sessions"][0]["activity"].update(change)
            with self.assertRaises(ContractError):
                validate_snapshot(invalid)
        value["schemaVersion"] = 2
        with self.assertRaises(ContractError):
            parse_snapshot(canonical(value).encode())
        value = fixture("claude-ready")
        value["sessions"][-1]["history"]["sdkVersion"] = "9.4.17"
        validate_snapshot(value)

    def test_public_watch_reconciles_child_classification_before_filtering(self):
        from agent_observer.cli import main
        before = fixture()
        before["sourceHealth"] = "partial"
        before["sources"][0]["coverage"]["saved"].update(status="partial", reason="history_limit")
        target = before["sessions"][0]["identity"]
        before["sessions"][0]["kind"] = "unknown"
        confirmed = copy.deepcopy(before)
        confirmed["sessions"][0]["kind"] = "child"
        missing = copy.deepcopy(confirmed)
        missing["sessions"].pop(0)
        frames = []
        with patch("agent_observer.cli._snapshot", side_effect=[before, confirmed, missing]), \
             patch("agent_observer.cli._watch_output", side_effect=frames.append), \
             patch("agent_observer.cli.time.sleep"):
            self.assertEqual(main(["watch", "--input", "-", "--count", "3"]), 0)
        snapshots = [frame["snapshot"] for frame in frames if frame["snapshot"] is not None]
        self.assertTrue(any(row["identity"] == target for row in snapshots[0]["sessions"]))
        self.assertTrue(all(row["identity"] != target for value in snapshots[1:] for row in value["sessions"]))

    @staticmethod
    def many_rows(count, start=1, *, bulky=False):
        value = fixture()
        value["sources"] = value["sources"][:1]
        value["sourceHealth"] = "partial"
        value["sources"][0]["coverage"]["saved"].update(status="partial", reason="history_limit")
        template = value["sessions"][0]
        value["sessions"] = []
        for index in range(start, start + count):
            row = copy.deepcopy(template)
            row["identity"]["nativeId"] = str(uuid.UUID(int=index))
            row["nativeIds"]["threadId"] = row["identity"]["nativeId"]
            row["nativeIds"]["sessionId"] = row["identity"]["nativeId"]
            if bulky:
                row["metadataIssues"] = ["m" * 120 + str(i) for i in range(128)]
            value["sessions"].append(row)
        return value

    def test_maximum_public_inventory_round_trips_snapshot_and_watch(self):
        value = self.many_rows(MAX_SESSIONS)
        data = canonical(value).encode()
        self.assertLess(len(data), MAX_SNAPSHOT_BYTES)
        self.assertEqual(len(parse_snapshot(data)["sessions"]), MAX_SESSIONS)
        frame = SampledWatch().sample(value)[0]
        self.assertEqual(len(parse_watch((canonical(frame) + "\n").encode())["snapshot"]["sessions"]), MAX_SESSIONS)

    def test_watch_churn_eviction_is_bounded_gap_and_recovery(self):
        watch = SampledWatch()
        value = self.many_rows(MAX_SESSIONS)
        watch.sample(value)
        for index in range(3):
            frames = watch.sample(self.many_rows(1, MAX_SESSIONS + index + 1))
            self.assertEqual([frame["kind"] for frame in frames], ["gap", "resync"])
            self.assertEqual(frames[0]["reason"], "retention_limit")
            self.assertIn("retention_limit", frames[-1]["snapshot"]["errors"])
            parsed = parse_watch((canonical(frames[-1]) + "\n").encode())
            self.assertEqual(len(parsed["snapshot"]["sessions"]), MAX_SESSIONS)
            self.assertEqual(watch.previous["sessions"][0]["identity"]["nativeId"], str(uuid.UUID(int=MAX_SESSIONS + index + 1)))
        complete = self.many_rows(1, 10000)
        complete["sources"][0]["coverage"]["saved"].update(status="complete", reason="metadata_scan")
        complete["sourceHealth"] = "current"
        recovered = watch.sample(complete)
        self.assertEqual(len(recovered[-1]["snapshot"]["sessions"]), 1)
        self.assertNotIn("retention_limit", recovered[-1]["snapshot"]["errors"])

    def test_watch_retention_respects_serialized_byte_budget(self):
        watch = SampledWatch()
        watch.sample(self.many_rows(256, bulky=True))
        frames = watch.sample(self.many_rows(256, 257, bulky=True))
        self.assertEqual(frames[0]["reason"], "retention_limit")
        data = (canonical(frames[-1]) + "\n").encode()
        self.assertLessEqual(len(data), MAX_BYTES)
        parsed = parse_watch(data)
        self.assertGreaterEqual(len(parsed["snapshot"]["sessions"]), 256)
        self.assertLess(len(parsed["snapshot"]["sessions"]), 512)

    def test_fixture_cli_does_not_import_provider_or_write_modules(self):
        script = "from agent_observer.cli import main; import sys; code=main(['list','--input',sys.argv[1],'--json']); assert not any(n in sys.modules for n in ['agent_observer.collection','agent_observer.codex_snapshot','agent_observer.claude_snapshot','agent_observer.write_client']); raise SystemExit(code)"
        result = subprocess.run(
            [sys.executable, "-c", script, str(FIXTURES / "snapshot.json")],
            capture_output=True,
            timeout=5,
            env={**os.environ, "CODEX_HOME": "/absent", "CLAUDE_CONFIG_DIR": "/absent"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(parse_snapshot(result.stdout)["sessions"]), 4)


if __name__ == "__main__":
    unittest.main()
