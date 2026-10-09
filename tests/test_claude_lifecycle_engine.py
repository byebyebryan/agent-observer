"""Adapter/runtime/history boundary and short lifecycle lease regressions."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.claude_snapshot import collect_claude
from agent_observer.collection import compose_snapshot
from agent_observer.native_artifacts import CLAUDE, Inspection
from agent_observer.observation_engine import ObservationEngine
from agent_observer.provider import profile_for

SID = "01234567-0123-4567-89ab-0123456789ab"
DOMAIN = "linux:0123456789abcdef0123456789abcdef:pid:[4026531836]"


class ClaudeLifecycleEngineTest(unittest.TestCase):
    def test_cold_runtime_exit_and_resume_refresh_without_sdk_and_do_not_refresh_age(self):
        with tempfile.TemporaryDirectory() as scratch:
            home = Path(scratch)
            (home / "sessions").mkdir()
            (home / "projects/project").mkdir(parents=True)
            (home / "projects/project" / (SID + ".jsonl")).write_text(json.dumps({"sessionId": SID, "type": "mode"}) + "\n")
            binary = home / "binary"
            binary.write_bytes(b"synthetic image")
            now = [10000]
            engine = ObservationEngine(host_scope="fixture", configs={"claude": (str(home), "explicit")},
                                       uid=os.geteuid(), clock=lambda: now[0], wall_clock=lambda: 50000,
                                       collection_id=lambda: "00000000-0000-4000-8000-000000000001",
                                       native_hostname="fixture", profiles={"claude": profile_for("claude")})
            history = {"coverage": {"complete": False, "reason": "metadata_scan"}, "errors": [], "rows": [
                {"session_id": SID, "custom_title": "Saved title", "cwd": str(home), "kind": "user",
                 "created_at": 100, "last_modified": 99999,
                 "activity": {"at": 200, "source": "claude_transcript_message", "health": "current", "reason": "native_conversation_event"}}]}
            with (patch("agent_observer.claude_snapshot._verify_artifact", return_value=Inspection((binary.stat().st_dev, binary.stat().st_ino), CLAUDE)),
                  patch("agent_observer.claude_snapshot.collect_saved_history", return_value=history) as sdk,
                  patch("agent_observer.claude_metadata._current_pid_domain", return_value=DOMAIN),
                  patch("agent_observer.claude_metadata._linux_proc_start_token", return_value=("456", "present")),
                  patch("agent_observer.claude_metadata._linux_process_uses_supported_binary", return_value=(True, "matched"))):
                def accept(component):
                    native = collect_claude(home, host_scope="fixture", executable=binary,
                                            config_home_kind="explicit", include_history=component == "history")
                    view = compose_snapshot(host_scope="fixture", provider_snapshots=[native])
                    engine.accept("claude", component, view, sampled_ms=now[0], ttl_ms=60000 if component == "history" else 1000,
                                  runtime_ttl_ms=1000)
                    return engine.snapshot["sessions"][0]
                cold = accept("runtime")
                self.assertEqual(cold["runtime"]["value"], "parked")
                self.assertIsNone(cold["phase"])
                self.assertIsNone(cold["activity"]["at"])
                sdk.assert_not_called()
                enriched = accept("history")
                self.assertEqual(enriched["activity"]["at"], 200)
                self.assertEqual(enriched["title"], "Saved title")
                record = {"sessionId": SID, "pid": 123, "procStart": "456", "pidDomain": DOMAIN,
                          "kind": "interactive", "status": "idle", "statusUpdatedAt": 100}
                path = home / "sessions/123.json"
                path.write_text(json.dumps(record))
                now[0] += 1
                live = accept("runtime")
                self.assertEqual(live["runtime"]["value"], "running")
                self.assertEqual(live["phase"]["value"], "waiting")
                self.assertEqual(live["activity"]["at"], 200)
                path.unlink()
                now[0] += 1
                parked = accept("runtime")
                self.assertEqual(parked["runtime"]["value"], "parked")
                self.assertIsNone(parked["phase"])
                self.assertEqual(parked["activity"]["at"], 200)
                sdk.assert_called_once()
                original_clock = parked["runtime"]["observedAt"]
                now[0] += 1001
                engine.expire()
                stale = engine.snapshot["sessions"][0]
                self.assertEqual(stale["runtime"]["value"], "unknown")
                self.assertEqual(stale["runtime"]["lastKnownValue"], "parked")
                self.assertEqual(stale["runtime"]["observedAt"], original_clock)
                self.assertEqual(stale["activity"]["at"], 200)
