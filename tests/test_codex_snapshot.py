"""Controlled read-source fixtures; native acceptance remains separate."""

import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.codex_endpoint import EndpointError, RuntimeIdentity
from agent_observer.codex_snapshot import collect_codex
from agent_observer.native_artifacts import CODEX, CODEX_DAEMON
from agent_observer.codex_transport import TransportError

FIRST = "01234567-0123-4567-89ab-0123456789ab"
SECOND = "11234567-0123-4567-89ab-0123456789ab"


def native(identifier):
    return {
        "id": identifier,
        "sessionId": identifier,
        "name": "Synthetic native name",
        "cwd": "/project",
        "source": "vscode",
        "threadSource": "user",
        "status": {"type": "idle"},
    }


class FakeClient:
    ignored_messages = 0
    timeout = 1

    def __init__(self, loaded, saved):
        self.loaded = loaded
        self.saved = saved
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def initialize(self):
        self.calls.append("initialize")
        return {"codexHome": "/config"}

    def loaded_threads(self, **kwargs):
        self.calls.append("loaded")
        return self.loaded

    def list_threads(self, **kwargs):
        self.calls.append("saved")
        if kwargs.get("cursor") is not None:
            return {"data": [], "nextCursor": None}
        return self.saved

    def latest_turn(self, identifier):
        return {"data": [], "nextCursor": None}

    def read_thread(self, identifier):
        self.calls.append(("read", identifier))
        return {"thread": native(identifier)}


class SnapshotCollectionTest(unittest.TestCase):
    def unclassified(self, identifier):
        row = native(identifier)
        del row["threadSource"]
        return row

    def test_saved_detail_establishes_kind_without_runtime_or_clock_claim(self):
        client = FakeClient({"data": [], "nextCursor": None},
                            {"data": [self.unclassified(SECOND)], "nextCursor": None})
        result = self.collect(client)
        row = result["sessions"][0]
        self.assertEqual(row["threadKind"], "user")
        self.assertEqual(row["inventory"], "saved")
        self.assertEqual(row["presence"]["value"], "unknown")
        self.assertEqual(row["work"]["value"], "unknown")
        self.assertNotIn("nativeState", row)
        self.assertIsNone(row["activity"]["at"])
        self.assertIn(("read", SECOND), client.calls)

    def test_saved_detail_classifies_explicit_child_without_loading_it(self):
        client = FakeClient({"data": [], "nextCursor": None},
                            {"data": [self.unclassified(SECOND)], "nextCursor": None})
        client.read_thread = lambda identifier: {"thread": {**native(identifier), "threadSource": "subagent"}}
        row = self.collect(client)["sessions"][0]
        self.assertEqual(row["threadKind"], "child")
        self.assertEqual(row["inventory"], "saved")
        self.assertEqual(row["presence"]["value"], "unknown")

    def test_optional_saved_detail_failure_keeps_catalog_and_live_sibling(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None},
                            {"data": [self.unclassified(SECOND)], "nextCursor": None})
        def read(identifier):
            if identifier == SECOND:
                raise TransportError("rpc_error")
            return {"thread": native(identifier)}
        client.read_thread = read
        result = self.collect(client)
        rows = {r["identity"]["nativeId"]: r for r in result["sessions"]}
        self.assertEqual(rows[SECOND]["threadKind"], "unknown")
        self.assertEqual(rows[FIRST]["presence"]["value"], "present")
        self.assertEqual(result["coverage"]["saved"]["complete"], True)
        self.assertIn("saved_classification_unavailable", result["limitations"])

    def test_saved_detail_identity_conflict_invalidates_live_authority(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None},
                            {"data": [self.unclassified(SECOND)], "nextCursor": None})
        client.read_thread = lambda identifier: {"thread": native(FIRST)}
        result = self.collect(client)
        self.assertIn({"code": "native_identity_mapping_conflict"}, result["errors"])
        self.assertEqual(result["sessions"][0]["presence"]["value"], "unknown")
        self.assertEqual(result["sessions"][0]["presence"]["health"], "stale")

    def test_saved_detail_budget_leaves_remaining_kind_unknown(self):
        client = FakeClient({"data": [], "nextCursor": None},
                            {"data": [self.unclassified(FIRST), self.unclassified(SECOND)], "nextCursor": None})
        with patch("agent_observer.codex_snapshot.MAX_SAVED_CLASSIFICATIONS", 1):
            result = self.collect(client)
        self.assertEqual([r["threadKind"] for r in result["sessions"]], ["user", "unknown"])
        self.assertIn("saved_classification_limit", result["limitations"])
        self.assertEqual(sum(isinstance(c, tuple) and c[0] == "read" for c in client.calls), 1)

    def test_saved_detail_source_conflict_does_not_promote_user(self):
        client = FakeClient({"data": [], "nextCursor": None},
                            {"data": [self.unclassified(SECOND)], "nextCursor": None})
        client.read_thread = lambda identifier: {"thread": {**native(identifier), "source": {"subAgent": "review"}, "threadSource": "subagent"}}
        row = self.collect(client)["sessions"][0]
        self.assertEqual(row["threadKind"], "unknown")
        self.assertIn("thread_classification_conflict", row["metadataIssues"])

    def test_runtime_cadence_never_scans_saved_catalog(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None},
                            {"data": [native(SECOND)], "nextCursor": None})
        result = self.collect(client, include_history=False)
        self.assertNotIn("saved", client.calls)
        self.assertEqual([r["identity"]["nativeId"] for r in result["sessions"]], [FIRST])
        self.assertEqual(result["coverage"]["saved"]["reason"], "not_observed")
        self.assertEqual(result["sessions"][0]["work"]["value"], "settled")

    def collect(self, client, *, artifact=CODEX, **changes):
        identity = RuntimeIdentity(
            "/config",
            "/endpoint",
            123,
            1000,
            456,
            "/binary",
            1,
            2,
            artifact.version,
            artifact.sha256,
            3,
            4,
            5,
        )
        with (
            patch("agent_observer.codex_snapshot.inspect_managed_endpoint", return_value=identity),
            patch("agent_observer.codex_snapshot._namespace", return_value=("namespace", FIRST)),
            patch("agent_observer.codex_snapshot.PassiveClient.connect", return_value=client),
            patch("agent_observer.codex_snapshot.validate_incarnation") as validate,
        ):
            result = collect_codex(Path("/config"), host_scope="host-a", **changes)
            if result["sourceHealth"] == "current":
                validate.assert_called_once_with(identity)
        return result

    def test_known_question_flags_do_not_depend_on_daemon_hash(self):
        class QuestionClient(FakeClient):
            def read_thread(self, identifier):
                row = native(identifier)
                row["status"] = {"type": "active", "activeFlags": ["waitingOnUserInput"]}
                return {"thread": row}
        for artifact, expected in ((CODEX, "needs_input"), (CODEX_DAEMON, "needs_input")):
            client = QuestionClient({"data": [FIRST], "nextCursor": None},
                                    {"data": [native(FIRST)], "nextCursor": None})
            result = self.collect(client, artifact=artifact)
            self.assertEqual(result["sessions"][0]["work"]["value"], expected)

    def test_live_inventory_survives_history_display_limit(self):
        client = FakeClient(
            {"data": [FIRST], "nextCursor": None},
            {"data": [native(SECOND)], "nextCursor": "next"},
        )
        result = self.collect(client, history_limit=1)
        self.assertEqual(
            {row["identity"]["nativeId"] for row in result["sessions"]}, {FIRST, SECOND}
        )
        self.assertTrue(result["coverage"]["loaded"]["complete"])
        self.assertTrue(result["coverage"]["saved"]["complete"])
        self.assertEqual(client.calls[:2], ["initialize", "loaded"])
        self.assertEqual(result["sourceHealth"], "current")

    def test_activity_ordering_precedes_display_cap_without_dropping_live_rows(self):
        client = FakeClient(
            {"data": [FIRST], "nextCursor": None},
            {"data": [native(FIRST), native(SECOND)], "nextCursor": None},
        )
        client.latest_turn = lambda identifier: {
            "data": [
                {
                    "items": [],
                    "itemsView": "notLoaded",
                    "startedAt": 100,
                    "completedAt": 200 if identifier == SECOND else 110,
                }
            ]
        }
        result = self.collect(client, history_limit=1)
        self.assertEqual(
            {row["identity"]["nativeId"] for row in result["sessions"]}, {FIRST, SECOND}
        )
        self.assertEqual(result["coverage"]["saved"]["reason"], "history_limit")
        self.assertEqual(
            next(row for row in result["sessions"] if row["identity"]["nativeId"] == SECOND)[
                "activity"
            ]["at"],
            200_000,
        )

    def test_public_snapshot_keeps_saved_and_loaded_child_observations(self):
        def child(identifier, status):
            return {
                **native(identifier),
                "source": {
                    "subAgent": {
                        "thread_spawn": {
                            "parent_thread_id": "21234567-0123-4567-89ab-0123456789ab",
                            "depth": 1,
                            "agent_path": "root/worker",
                            "agent_nickname": "worker",
                            "agent_role": "reviewer",
                        }
                    }
                },
                "threadSource": "subagent",
                "status": status,
            }

        client = FakeClient(
            {"data": [FIRST], "nextCursor": None},
            {"data": [child(SECOND, {"type": "notLoaded"})], "nextCursor": None},
        )
        client.read_thread = lambda identifier: {"thread": child(identifier, {"type": "idle"})}
        result = self.collect(client)

        rows = {row["identity"]["nativeId"]: row for row in result["sessions"]}
        self.assertEqual({FIRST, SECOND}, set(rows))
        self.assertEqual("child", rows[FIRST]["threadKind"])
        self.assertEqual("subagent", rows[FIRST]["sourceKind"])
        self.assertEqual("live", rows[FIRST]["inventory"])
        self.assertEqual("child", rows[SECOND]["threadKind"])
        self.assertEqual("subagent", rows[SECOND]["sourceKind"])
        self.assertEqual("saved", rows[SECOND]["inventory"])
        self.assertNotIn("thread_spawn", str(result["sessions"]))
        self.assertEqual("current", result["sourceHealth"])

    def test_native_work_proof_gate_cannot_be_bypassed_by_fixture_idle(self):
        with patch("agent_observer.codex_snapshot.WORK_STATE_ACCEPTED", False):
            result = self.collect(
                FakeClient(
                    {"data": [FIRST], "nextCursor": None},
                    {"data": [], "nextCursor": None},
                )
            )
        row = result["sessions"][0]
        self.assertEqual(row["nativeState"]["type"], "idle")
        self.assertEqual(row["work"]["value"], "unknown")
        self.assertFalse(result["coverage"]["work"]["supported"])
        self.assertFalse(result["coverage"]["workerPresence"]["supported"])
        self.assertEqual(row["presenceKind"], "server_thread_loaded")

    def test_unproved_wait_and_error_states_remain_unknown(self):
        for status in (
            {"type": "active", "activeFlags": ["futureFlag"]},
            {"type": "systemError"},
        ):
            client = FakeClient(
                {"data": [FIRST], "nextCursor": None}, {"data": [], "nextCursor": None}
            )
            client.read_thread = lambda identifier, status=status: {
                "thread": {**native(identifier), "status": status}
            }
            result = self.collect(client)
            self.assertEqual(result["sessions"][0]["work"]["value"], "unknown")
            self.assertEqual(result["sessions"][0]["work"]["health"], "unsupported")
            self.assertEqual(result["sessions"][0]["waitReason"], "unknown")

    def test_proved_approval_is_distinct_from_unproved_input_wait(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None}, {"data": [], "nextCursor": None})
        client.read_thread = lambda identifier: {
            "thread": {
                **native(identifier),
                "status": {"type": "active", "activeFlags": ["waitingOnApproval"]},
            }
        }
        result = self.collect(client)
        row = result["sessions"][0]
        self.assertEqual(row["work"]["value"], "needs_input")
        self.assertEqual(row["waitReason"], "approval")
        self.assertEqual(result["coverage"]["work"]["supportedWaitFlags"], ["waitingOnApproval", "waitingOnUserInput"])

    def test_live_limit_is_incomplete_and_never_silently_empty(self):
        result = self.collect(
            FakeClient(
                {"data": [FIRST, SECOND], "nextCursor": None},
                {"data": [], "nextCursor": None},
            ),
            live_limit=1,
        )
        self.assertEqual(len(result["sessions"]), 1)
        self.assertEqual(result["coverage"]["loaded"], {"complete": False, "reason": "live_limit"})

    def test_duplicate_loaded_identity_rejected(self):
        result = self.collect(
            FakeClient(
                {"data": [FIRST, FIRST], "nextCursor": None},
                {"data": [], "nextCursor": None},
            )
        )
        self.assertEqual(result["errors"], [{"code": "loaded_identity_ambiguous"}, {"code": "saved_metadata_unavailable"}])
        self.assertEqual(result["sourceHealth"], "unavailable")

    def test_history_failure_preserves_independent_live_facts(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None}, {"data": "malformed"})
        result = self.collect(client)
        row = result["sessions"][0]
        self.assertEqual(row["presence"]["value"], "present")
        self.assertIsInstance(row["presence"]["observedAt"], int)
        self.assertEqual(row["presence"]["health"], "current")
        self.assertEqual(result["sourceHealth"], "partial")
        self.assertTrue(result["coverage"]["loaded"]["complete"])
        self.assertFalse(result["coverage"]["saved"]["complete"])

    def test_one_malformed_loaded_identity_keeps_healthy_sibling_evidence(self):
        client = FakeClient({"data": [FIRST, SECOND], "nextCursor": None}, {"data": [], "nextCursor": None})
        def read(identifier):
            return {"thread": {**native(identifier), "sessionId": FIRST if identifier == FIRST else "malformed"}}
        client.read_thread = read
        result = self.collect(client)
        self.assertEqual(result["sourceHealth"], "partial")
        self.assertEqual(result["coverage"]["loaded"], {"complete": False, "reason": "loaded_row_unavailable"})
        self.assertEqual(result["errors"], [{"code": "invalid_native_identity"}])
        self.assertEqual(result["sessions"][0]["identity"]["nativeId"], FIRST)
        self.assertEqual(result["sessions"][0]["presence"]["value"], "present")
        self.assertEqual(result["sessions"][0]["presence"]["health"], "current")
        self.assertEqual(result["sessions"][0]["work"]["value"], "settled")

    def test_new_state_variant_preserves_logical_identity_with_unknown_facts(self):
        client = FakeClient({"data": [FIRST], "nextCursor": None}, {"data": [], "nextCursor": None})
        client.read_thread = lambda identifier: {"thread": {**native(identifier), "status": {"type": "futureState"}}}
        result = self.collect(client)
        row = result["sessions"][0]
        self.assertEqual(row["identity"]["nativeId"], FIRST)
        self.assertEqual(row["presence"]["value"], "unknown")
        self.assertEqual(row["work"]["value"], "unknown")
        self.assertIn("unsupported_status_schema", row["metadataIssues"])

    def test_loaded_identity_conflict_invalidates_prior_sibling_evidence(self):
        client = FakeClient({"data": [FIRST, SECOND], "nextCursor": None}, {"data": [], "nextCursor": None})
        client.read_thread = lambda identifier: {"thread": native(FIRST)}
        result = self.collect(client)
        self.assertIn({"code": "loaded_read_identity_conflict"}, result["errors"])
        self.assertEqual(result["sessions"][0]["presence"]["value"], "unknown")
        self.assertEqual(result["sessions"][0]["presence"]["health"], "stale")

    def test_conflicting_session_mapping_is_not_first_match(self):
        conflicting = {**native(FIRST), "sessionId": SECOND}
        result = self.collect(
            FakeClient(
                {"data": [FIRST], "nextCursor": None},
                {"data": [conflicting], "nextCursor": None},
            )
        )
        self.assertEqual(result["errors"], [{"code": "native_identity_mapping_conflict"}, {"code": "saved_metadata_unavailable"}])
        self.assertEqual(result["sessions"][0]["presence"]["value"], "unknown")

    def test_absent_runtime_reports_failed_coverage_without_connecting(self):
        with (
            patch(
                "agent_observer.codex_snapshot.inspect_managed_endpoint",
                side_effect=EndpointError("endpoint_unavailable"),
            ),
            patch("agent_observer.codex_snapshot.PassiveClient.connect") as connect,
        ):
            result = collect_codex(Path("/config"), host_scope="host-a")
        connect.assert_not_called()
        self.assertEqual(result["sessions"], [])
        self.assertEqual(result["sourceHealth"], "unavailable")
        self.assertEqual(result["errors"], [{"code": "endpoint_unavailable"}, {"code": "saved_metadata_unavailable"}])
        self.assertFalse(result["coverage"]["saved"]["complete"])
