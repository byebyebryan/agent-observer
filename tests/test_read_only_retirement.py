"""Withdrawal is explicit and preserves the old active membership in working-set."""

import importlib.metadata
import importlib.util
import json
import os
import socket
import unittest
from pathlib import Path

import test_working_set_projection as projection_cases
from test_service_runtime import Running

from agent_observer.contract import store_namespace


class ReadOnlyRetirementTest(unittest.TestCase):
    def test_retired_modules_and_current_writer_entrypoint_are_absent(self):
        for module in (
            "write_client",
            "write_contract",
            "codex_exact",
            "active_contract",
            "active_feed",
            "mesh_active_source",
            "mesh_active_profile",
            "mesh_active_read",
        ):
            with self.subTest(module=module):
                self.assertIsNone(importlib.util.find_spec("agent_observer." + module))
        entries = importlib.metadata.distribution("agent-observer").entry_points
        self.assertNotIn("agent-observer-write", [e.name for e in entries])

    def test_same_canonical_input_preserves_pre_retirement_active_identity_oracle(self):
        oracle = json.loads(
            (Path(__file__).parent / "fixtures/retirement-active-membership.json").read_text()
        )
        self.assertEqual(len(oracle["cases"]), 9)
        for case in oracle["cases"]:
            with self.subTest(activity=case["activityAt"], phase=case["phase"]):
                fixture = projection_cases.WorkingSetProjectionTest()
                fixture.setUp()
                sample = fixture.sample(runtime="running", at=case["activityAt"])
                sample["sessions"][0]["phase"]["value"] = case["phase"]
                sample["sessions"][0]["blockedReasons"] = []
                frame = fixture.accept(sample)
                self.assertEqual(
                    [row["identity"] for row in frame["projection"]["sessions"]], case["activeIds"]
                )
                self.assertTrue(
                    all(
                        member["active"] is not None
                        for member in frame["projection"]["scopes"][0]["members"]
                    )
                )
                self.assertIsNone(fixture.state._sync_projector)
                self.assertFalse(hasattr(fixture.state, "active_frame"))

    def test_retired_native_request_has_an_explicit_negative_without_collection(self):
        fixture = projection_cases.WorkingSetProjectionTest()
        fixture.setUp()
        fixture.state.uid = os.geteuid()
        sample = fixture.sample(runtime="running")
        sample["host"]["uid"] = fixture.state.uid
        namespaces = {}
        for source in sample["sources"]:
            previous = source["namespace"]
            current = store_namespace(
                source["provider"],
                source["configHome"],
                source["configHomeKind"],
                fixture.state.uid,
            )
            source["namespace"] = current
            namespaces[previous] = current
        for row in sample["sessions"]:
            row["identity"]["namespace"] = namespaces[row["identity"]["namespace"]]
        fixture.accept(sample)
        with Running(state=fixture.state) as server:
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(2)
                client.connect(str(server.path))
                client.sendall(
                    b'{"activeFeedProtocol":1,"operation":"watch","hostScope":"fixture"}\n'
                )
                frame = json.loads(client.makefile("rb").readline())
            self.assertEqual((frame["kind"], frame["reason"]), ("error", "active_feed_retired"))
            self.assertIsNone(frame["snapshot"])
            self.assertNotIn("activeFeedProtocol", frame)
            self.assertEqual(server.runtime.counts["workerStarts"], 0)
            self.assertIsNone(server.state._sync_projector)
