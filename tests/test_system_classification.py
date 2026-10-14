"""System helpers remain observable without entering ordinary rosters."""

import copy
import json
import runpy
import tempfile
import unittest
from pathlib import Path

import test_codex_metadata as native_fixture

from agent_observer.codex_metadata import live_thread_metadata, saved_thread_metadata
from agent_observer.public import ContractError, listing, select, validate_snapshot
from agent_observer.watch import SampledWatch

ROOT = Path(__file__).resolve().parents[1]


class SystemClassificationTest(unittest.TestCase):
    def test_native_system_and_user_are_independent_of_ephemeral(self):
        fixture = native_fixture.CodexMetadataTest()
        fixture.setUp()
        for ephemeral in (False, True):
            for tag, kind in (("user", "user"), ("system", "system"), ("thread_title", "system")):
                payload = {**fixture.row, "threadSource": tag, "ephemeral": ephemeral}
                saved = saved_thread_metadata(payload, **fixture.scope)
                live = live_thread_metadata(payload, **fixture.scope, observed_at=100)
                self.assertEqual(saved["threadKind"], kind)
                self.assertEqual(live["threadKind"], kind)
                self.assertEqual(live["runtimeDisposition"]["value"], "running")
                self.assertEqual(live["work"]["value"], "settled")
                self.assertNotIn("synthetic_private", json.dumps(live))
        future = saved_thread_metadata({**fixture.row, "threadSource": "future_label"}, **fixture.scope)
        self.assertEqual(future["threadKind"], "unknown")
        self.assertIn("thread_classification_unsupported", future["metadataIssues"])

    def test_title_helper_tag_retains_child_precedence_and_unknown_boundaries(self):
        fixture = native_fixture.CodexMetadataTest()
        fixture.setUp()
        child = saved_thread_metadata(
            {**fixture.row, "source": {"subAgent": "review"}, "threadSource": "thread_title"},
            **fixture.scope,
        )
        self.assertEqual(child["threadKind"], "child")
        malformed = saved_thread_metadata(
            {**fixture.row, "source": {"subAgent": {}}, "threadSource": "thread_title"},
            **fixture.scope,
        )
        self.assertEqual(malformed["threadKind"], "unknown")
        for tag in ("future_feature", ["thread_title"], {"feature": "thread_title"}):
            with self.subTest(tag=tag):
                value = saved_thread_metadata({**fixture.row, "threadSource": tag}, **fixture.scope)
                self.assertEqual(value["threadKind"], "unknown")
                self.assertIn("thread_classification_unsupported", value["metadataIssues"])

    def fixture(self):
        value = json.loads((ROOT / "tests/fixtures/contract-v6/snapshot.json").read_text())
        value["sessions"][0]["kind"] = "system"
        value["sessions"][1]["kind"] = "unknown"
        return value

    def test_raw_and_exact_selection_preserve_system_default_roster_hides_only_known(self):
        value = self.fixture()
        validate_snapshot(value)
        target = value["sessions"][0]["identity"]
        self.assertEqual(select(value, target)["kind"], "system")
        normal = listing(value)
        self.assertTrue(any(row["kind"] == "unknown" for row in normal["sessions"]))
        self.assertFalse(any(row["kind"] == "system" for row in normal["sessions"]))
        self.assertTrue(any(row["kind"] == "system" for row in listing(value, include_system=True)["sessions"]))
        old = copy.deepcopy(value)
        old["schemaVersion"] = 5
        with self.assertRaises(ContractError):
            validate_snapshot(old)

    def test_watch_reclassifies_retained_unknown_before_presentation_filter(self):
        value = self.fixture()
        target = value["sessions"][0]["identity"]
        value["sourceHealth"] = "partial"
        value["sources"][0]["coverage"]["saved"].update(status="partial", reason="history_limit")
        value["sessions"][0]["kind"] = "unknown"
        watch = SampledWatch()
        self.assertTrue(any(row["identity"] == target for row in watch.sample(value, include_system=False)[0]["snapshot"]["sessions"]))
        value["sessions"][0]["kind"] = "system"
        frames = watch.sample(value, include_system=False)
        self.assertTrue(all(row["identity"] != target for frame in frames if frame["snapshot"] for row in frame["snapshot"]["sessions"]))
        value["sessions"].pop(0)
        frames = watch.sample(value, include_system=False)
        self.assertTrue(all(row["identity"] != target for frame in frames if frame["snapshot"] for row in frame["snapshot"]["sessions"]))

    def test_candidate_manifest_requires_coordinated_successor(self):
        helper = runpy.run_path(str(ROOT / "scripts/candidate-artifact"))
        value = helper["document"](ROOT / "artifacts/observer-0.6.0a2.json")
        value.update(manifestVersion=5, apiVersion=4, schemas={"snapshot": 6, "watch": 6}, service={"protocol": 4, "schemas": {"request": 4, "frame": 4}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(value))
            self.assertEqual(helper["document"](path)["write"], {"schema": 2})
            value["service"]["protocol"] = 3
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                helper["document"](path)
