"""Public conformance and independent reader invariants, using metadata fixtures."""

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from agent_observer.collection import project_session
from agent_observer.contract import (
    ContractError,
    canonical,
    parse_snapshot,
    schema_document,
    store_namespace,
    validate_snapshot,
    validate_watch,
)
from agent_observer.read_client import ordered_rows, select
from agent_observer.watch import SampledWatch

FIXTURES = Path(__file__).parent / "fixtures/contract-v2"


def fixture(name="snapshot"):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class ContractV2Test(unittest.TestCase):
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
        watch.sample(before)
        frames = watch.sample(fixture("partial"))
        self.assertEqual([frame["kind"] for frame in frames], ["gap", "resync"])
        retained = frames[-1]["snapshot"]["sessions"][-2]
        original = before["sessions"][-2]
        self.assertEqual(retained["phase"]["value"], "unknown")
        self.assertEqual(retained["phase"]["lastKnownValue"], "working")
        self.assertEqual(retained["phase"]["observedAt"], original["phase"]["observedAt"])
        self.assertEqual(retained["runtime"]["value"], "unknown")
        watch.gap("collection_failed")
        self.assertEqual(watch.sample(before)[0]["kind"], "resync")

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
