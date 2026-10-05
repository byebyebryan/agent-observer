"""Current-store fallback identity/clock/passivity; no native provider calls."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import codex_saved
from agent_observer.codex_endpoint import EndpointError
from agent_observer.codex_snapshot import collect_codex
from agent_observer.collection import compose_v2

THREAD = "11111111-1111-4111-8111-111111111111"
SESSION = "22222222-2222-4222-8222-222222222222"


class SavedStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.rollout = self.home / "sessions/rollout.jsonl"
        self.rollout.parent.mkdir()
        self.rollout.write_text(json.dumps({"type": "session_meta", "payload": {
            "id": THREAD, "session_id": SESSION, "cwd": "/project", "base_instructions": "never export this",
        }}) + "\n")
        self.fingerprint = hashlib.sha256(json.dumps([[1, "ff", 1]], separators=(",", ":")).encode()).hexdigest()
        for name in codex_saved.MIGRATIONS:
            with sqlite3.connect(self.home / name) as db:
                db.execute("CREATE TABLE _sqlx_migrations(version INTEGER,checksum BLOB,success INTEGER)")
                db.execute("INSERT INTO _sqlx_migrations VALUES(1,?,1)", (b"\xff",))
                if name == "state_5.sqlite":
                    db.execute("CREATE TABLE threads(id TEXT,rollout_path TEXT,source TEXT,thread_source TEXT,name TEXT,cwd TEXT,created_at INTEGER,updated_at INTEGER,archived INTEGER)")
                    db.execute("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?)", (THREAD, str(self.rollout), "cli", "user", "explicit title", "/project", 10, 15, 0))
                else:
                    db.execute("CREATE TABLE thread_turns(thread_id TEXT,started_at INTEGER,completed_at INTEGER,rollout_ordinal INTEGER)")
                    db.execute("INSERT INTO thread_turns VALUES(?,NULL,120,1)", (THREAD,))
        patcher = patch.dict(codex_saved.MIGRATIONS, {name: self.fingerprint for name in codex_saved.MIGRATIONS})
        patcher.start()
        self.addCleanup(patcher.stop)

    def collect(self):
        return codex_saved.collect_saved(self.home, host_scope="fixture", namespace="fixture-native")

    def test_saved_identity_and_completion_clock_are_independent_of_liveness(self):
        before = {p: p.read_bytes() for p in self.home.glob("*.sqlite")}
        result = self.collect()
        row = result["sessions"][0]
        self.assertEqual(row["nativeIds"], {"threadId": THREAD, "sessionId": SESSION})
        self.assertEqual(row["activity"]["at"], 120_000)
        self.assertEqual(row["activity"]["source"], "codex_saved_turn_metadata")
        self.assertEqual(row["cwdSource"], "codex_session_metadata")
        self.assertEqual(row["presence"]["value"], "unknown")
        self.assertEqual(row["work"]["value"], "unknown")
        self.assertNotIn("never export", json.dumps(result))
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertFalse(list(self.home.glob("*-shm")))

    def test_schema_drift_is_rejected_instead_of_selecting_a_legacy_database(self):
        with sqlite3.connect(self.home / "state_5.sqlite") as db:
            db.execute("UPDATE _sqlx_migrations SET checksum=?", (b"new-schema",))
        with self.assertRaisesRegex(ValueError, "saved_store_schema_unsupported"):
            self.collect()

    def test_mismatched_head_and_external_or_symlink_rollout_are_not_identified(self):
        self.rollout.write_text(json.dumps({"type": "session_meta", "payload": {"id": SESSION, "session_id": SESSION}}) + "\n")
        self.assertEqual(self.collect()["sessions"], [])
        real = self.home / "external.jsonl"
        self.rollout.rename(real)
        self.rollout.symlink_to(real)
        self.assertEqual(self.collect()["sessions"], [])

    def test_missing_store_does_not_create_a_database(self):
        (self.home / "thread_history_1.sqlite").unlink()
        with self.assertRaises(FileNotFoundError):
            self.collect()
        self.assertFalse((self.home / "thread_history_1.sqlite").exists())

    def test_session_cwd_is_authoritative_when_catalog_context_is_older(self):
        with sqlite3.connect(self.home / "state_5.sqlite") as db:
            db.execute("UPDATE threads SET cwd='/old-project'")
        self.assertEqual(self.collect()["sessions"][0]["cwd"], "/project")

    def test_incomplete_wal_state_is_rejected_without_creating_sidecars(self):
        wal = self.home / "state_5.sqlite-wal"
        wal.write_bytes(b"inflight")
        with self.assertRaisesRegex(ValueError, "saved_store_wal_unavailable"):
            self.collect()
        self.assertFalse((self.home / "state_5.sqlite-shm").exists())

    def test_age_ordering_precedes_display_limit_and_excludes_children(self):
        child = "33333333-3333-4333-8333-333333333333"
        with sqlite3.connect(self.home / "state_5.sqlite") as db:
            db.execute("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?)", (child, str(self.rollout), "unknown", "subagent", "child", "/project", 10, 20, 0))
        self.assertEqual(len(self.collect()["sessions"]), 1)

    def test_missing_peer_preserves_history_without_creating_monitoring_evidence(self):
        with patch("agent_observer.codex_snapshot.inspect_managed_endpoint", side_effect=EndpointError("endpoint_unavailable")), patch("agent_observer.codex_snapshot.PassiveClient.connect") as connect:
            native = collect_codex(self.home, host_scope="fixture")
        connect.assert_not_called()
        snapshot = compose_v2(host_scope="fixture", provider_snapshots=[native])
        self.assertEqual(snapshot["sourceHealth"], "partial")
        self.assertEqual(snapshot["sources"][0]["coverage"]["saved"]["status"], "partial")
        self.assertEqual(snapshot["sources"][0]["coverage"]["runtime"]["status"], "unavailable")
        self.assertEqual(snapshot["sources"][0]["capabilities"]["phase"], [])
        row = snapshot["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertEqual(row["phase"]["value"], "unknown")
        self.assertEqual(row["activity"]["at"], 120_000)
