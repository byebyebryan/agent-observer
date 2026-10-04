"""Synthetic tests for the isolated RLCD frame candidate."""

from __future__ import annotations

import copy
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from examples import rlcd_bridge

HOST = "snap"
COLLECTION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CODEX_SOURCE_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CLAUDE_SOURCE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def native_id(number: int) -> str:
    return f"{number:08x}-1234-4234-8234-{number:012x}"


def source(
    provider: str,
    namespace: str,
    *,
    health: str = "current",
    errors: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if provider == "codex":
        coverage: dict[str, object] = {
            "saved": {"complete": True, "reason": "native_snapshot"},
            "loaded": {"complete": health == "current", "reason": "native_snapshot"},
            "work": {
                "supported": True,
                "reason": "native_proof",
                "supportedValues": ["working", "needs_input", "settled"],
            },
        }
        collection_id = CODEX_SOURCE_ID
    else:
        coverage = {
            "sessionRegistry": "complete" if health == "current" else "partial",
            "jobStore": "complete" if health == "current" else "partial",
            "workerPresence": "complete" if health == "current" else "partial",
            "attachment": "unsupported",
        }
        collection_id = CLAUDE_SOURCE_ID
    return {
        "schemaVersion": 1,
        "collectionId": collection_id,
        "collectedAt": 1_800_000_000_000,
        "provider": provider,
        "namespace": namespace,
        **({"configHomeKind": "explicit"} if provider == "claude" else {}),
        "sourceHealth": health,
        "coverage": coverage,
        "errors": errors or [],
        "runtime": {"privateEndpoint": "must not be copied"},
    }


def row(
    provider: str = "codex",
    namespace: str = "codex-home",
    *,
    number: int = 1,
    work_value: str = "working",
    work_at: int | None = 1_700_000_000_000,
    presence_value: str = "present",
    presence_at: int | None = 1_700_000_000_100,
    title: str = "Project session",
    work_health: str = "current",
    presence_health: str = "current",
) -> dict[str, object]:
    kind = "thread" if provider == "codex" else "session"
    work_source = "codex_rpc" if provider == "codex" else "claude_registry"
    presence_source = work_source
    return {
        "identity": {
            "hostScope": HOST,
            "provider": provider,
            "namespace": namespace,
            "nativeIdKind": kind,
            "nativeId": native_id(number),
        },
        "title": title,
        "cwd": "/private/path/must/not/be/copied",
        "inventory": "live" if presence_value == "present" else "registry",
        "presenceKind": "server_thread_loaded" if provider == "codex" else "os_worker",
        "work": {
            "value": work_value,
            "health": work_health,
            "observedAt": work_at,
            "source": work_source if work_at is not None else None,
            "reason": (
                "observation_gap"
                if work_health == "stale"
                else "unsupported"
                if work_health == "unsupported"
                else "source_unavailable"
                if work_health == "unavailable"
                else "native_snapshot"
            ),
            **({"lastKnownValue": "working"} if work_health == "stale" else {}),
        },
        "presence": {
            "value": presence_value,
            "health": presence_health,
            "observedAt": presence_at,
            "source": presence_source if presence_at is not None else None,
            "reason": (
                "source_unavailable"
                if presence_health == "unavailable"
                else "unsupported"
                if presence_health == "unsupported"
                else "native_snapshot"
            ),
        },
        "nativeHistoryTimes": (
            {"createdAt": 1_600_000_000_000, "updatedAt": 1_650_000_000_000}
            if provider == "codex"
            else None
        ),
        "waitReason": "approval" if work_value == "needs_input" else "unknown",
        "preview": "private prompt must not be copied",
        "providerPayload": {"toolOutput": "private output must not be copied"},
    }


def document(
    sessions: list[dict[str, object]] | None = None,
    *,
    sources: list[dict[str, object]] | None = None,
    source_health: str = "current",
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "collectionId": COLLECTION_ID,
        "collectedAt": 1_800_000_000_000,
        "host": {
            "authority": HOST,
            "authoritySource": "caller",
            "nativeHostname": "private-hostname",
            "uid": 1000,
        },
        "sources": sources
        if sources is not None
        else [
            source("codex", "codex-home"),
            source("claude", "claude-home"),
        ],
        "sessions": sessions if sessions is not None else [row()],
        "errors": [],
        "limitations": ["private limitation text is ignored"],
        "sourceHealth": source_health,
        "durationMs": 1.25,
    }


def encoded(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n").encode()


class RlcdBridgeTest(unittest.TestCase):
    def project(self, value: object, *, row_limit: int = 6):
        return rlcd_bridge.project_bytes(encoded(value), row_limit=row_limit)

    def test_keeps_full_identity_and_projects_only_bounded_metadata(self) -> None:
        frame = self.project(document())
        self.assertEqual(1, frame["rowCount"])
        session = frame["sessions"][0]
        self.assertEqual(
            {
                "hostScope": HOST,
                "provider": "codex",
                "namespace": "codex-home",
                "nativeIdKind": "thread",
                "nativeId": native_id(1),
            },
            session["identity"],
        )
        self.assertTrue(session["displayId"].startswith("S-"))
        self.assertTrue(session["liveSelected"])
        self.assertEqual("server_thread_loaded", session["presenceKind"])
        source_kinds = {item["provider"]: item["configHomeKind"] for item in frame["sources"]}
        self.assertEqual({"codex": "unknown", "claude": "explicit"}, source_kinds)
        serialized = json.dumps(frame)
        for private_value in (
            "private prompt",
            "private output",
            "privateEndpoint",
            "/private/path",
            "private-hostname",
            "private limitation",
        ):
            self.assertNotIn(private_value, serialized)

    def test_partial_provider_failure_preserves_healthy_live_rows_and_finite_errors(self) -> None:
        claude = source(
            "claude",
            "claude-home",
            health="unavailable",
            errors=[
                {
                    "code": "config_root_unavailable",
                    "jobId": "abcdef01",
                    "detail": "private task text",
                },
                {"code": "arbitrary_private_payload"},
            ],
        )
        frame = self.project(
            document(
                [row()],
                sources=[source("codex", "codex-home"), claude],
                source_health="partial",
            )
        )
        self.assertEqual("partial", frame["feedHealth"])
        self.assertEqual("live_rows", frame["emptyState"])
        self.assertEqual(1, frame["liveRowCount"])
        self.assertEqual("working", frame["sessions"][0]["work"]["value"])
        claude_source = next(item for item in frame["sources"] if item["provider"] == "claude")
        self.assertEqual(
            ["config_root_unavailable", "unrecognized_source_error"],
            claude_source["errors"],
        )
        self.assertNotIn("abcdef01", json.dumps(frame))
        self.assertNotIn("private task text", json.dumps(frame))

    def test_empty_feed_is_exhaustive_only_with_both_complete_live_inventories(self) -> None:
        complete = self.project(document(sessions=[]))
        self.assertEqual("current", complete["feedHealth"])
        self.assertEqual("complete", complete["liveInventory"])
        self.assertEqual("no_live_sessions", complete["emptyState"])

        incomplete = self.project(
            document(
                sessions=[],
                sources=[
                    source("codex", "codex-home"),
                    source(
                        "claude",
                        "claude-home",
                        health="unavailable",
                        errors=[{"code": "jobs_unavailable"}],
                    ),
                ],
                source_health="partial",
            )
        )
        self.assertEqual("partial", incomplete["feedHealth"])
        self.assertEqual("partial_or_unknown", incomplete["liveInventory"])
        self.assertEqual("partial_or_unknown", incomplete["emptyState"])

        one_provider = self.project(document(sessions=[], sources=[source("codex", "codex-home")]))
        self.assertEqual("partial", one_provider["feedHealth"])
        self.assertEqual("partial_or_unknown", one_provider["emptyState"])

    def test_fresh_presence_does_not_renew_stale_work_evidence(self) -> None:
        item = row(
            work_value="unknown",
            work_at=1_700_000_000_000,
            work_health="stale",
            presence_value="present",
            presence_at=1_800_000_000_000,
        )
        frame = self.project(document([item]))
        session = frame["sessions"][0]
        self.assertEqual(
            {
                "value": "unknown",
                "health": "stale",
                "observedAt": 1_700_000_000_000,
                "source": "codex_rpc",
                "reason": "observation_gap",
            },
            session["work"],
        )
        self.assertEqual(1_800_000_000_000, session["presence"]["observedAt"])
        self.assertEqual("current", session["presence"]["health"])
        self.assertTrue(session["liveSelected"])

    def test_unsupported_and_unknown_facts_stay_unknown(self) -> None:
        item = row(
            work_value="unknown",
            work_at=None,
            work_health="unsupported",
            presence_value="unknown",
            presence_at=None,
            presence_health="unavailable",
        )
        frame = self.project(document([item]))
        session = frame["sessions"][0]
        self.assertEqual(
            ("unknown", "unsupported"),
            (
                session["work"]["value"],
                session["work"]["health"],
            ),
        )
        self.assertEqual(
            ("unknown", "unavailable"),
            (
                session["presence"]["value"],
                session["presence"]["health"],
            ),
        )
        self.assertFalse(session["liveSelected"])

    def test_missing_facts_become_unavailable_unknown_not_idle(self) -> None:
        item = row(number=15)
        item.pop("work")
        item.pop("presence")
        frame = self.project(document([item]))
        session = frame["sessions"][0]
        self.assertEqual(
            ("unknown", "unavailable", None),
            (
                session["work"]["value"],
                session["work"]["health"],
                session["work"]["observedAt"],
            ),
        )
        self.assertEqual(
            ("unknown", "unavailable", None),
            (
                session["presence"]["value"],
                session["presence"]["health"],
                session["presence"]["observedAt"],
            ),
        )
        self.assertFalse(session["liveSelected"])
        self.assertEqual("partial_or_unknown", frame["emptyState"])

    def test_exact_full_key_duplicates_remain_separate_and_ambiguous(self) -> None:
        duplicate = row(number=5)
        second = copy.deepcopy(duplicate)
        second["title"] = "Other duplicate row"
        frame = self.project(document([duplicate, second]))
        self.assertEqual(2, frame["rowCount"])
        self.assertEqual(2, len(frame["sessions"]))
        self.assertEqual(
            {session["displayId"] for session in frame["sessions"]},
            {frame["sessions"][0]["displayId"]},
        )
        for session in frame["sessions"]:
            self.assertEqual("ambiguous", session["identityHealth"])
            self.assertEqual("unknown", session["work"]["value"])
            self.assertEqual("ambiguous", session["work"]["health"])
            self.assertFalse(session["liveSelected"])
        self.assertIn("duplicate_native_identity", frame["issues"])
        self.assertEqual("partial", frame["feedHealth"])

    def test_same_native_id_in_different_namespaces_remains_distinct(self) -> None:
        sources = [
            source("codex", "codex-home-a"),
            source("codex", "codex-home-b"),
            source("claude", "claude-home"),
        ]
        first = row(namespace="codex-home-a", number=8)
        second = row(namespace="codex-home-b", number=8)
        frame = self.project(document([first, second], sources=sources))
        codex_rows = [
            session for session in frame["sessions"] if session["identity"]["provider"] == "codex"
        ]
        self.assertEqual(2, len(codex_rows))
        self.assertEqual(
            {"codex-home-a", "codex-home-b"}, {x["identity"]["namespace"] for x in codex_rows}
        )
        self.assertEqual(2, len({x["displayId"] for x in codex_rows}))
        self.assertTrue(all(x["namespaceCollision"] for x in codex_rows))
        self.assertTrue(all(x["identityHealth"] == "current" for x in codex_rows))
        self.assertIn("native_id_multiple_namespaces", frame["issues"])
        self.assertEqual("current", frame["feedHealth"])

    def test_attention_then_explicit_work_time_and_identity_order_is_deterministic(self) -> None:
        newest_work = row(number=12, work_value="working", work_at=900)
        older_work = row(number=11, work_value="working", work_at=800)
        needs_input = row(number=10, work_value="needs_input", work_at=100)
        values = document([older_work, newest_work, needs_input])
        first = self.project(values)
        values["sessions"].reverse()
        second = self.project(values)
        self.assertEqual(
            [
                needs_input["identity"]["nativeId"],
                newest_work["identity"]["nativeId"],
                older_work["identity"]["nativeId"],
            ],
            [session["identity"]["nativeId"] for session in first["sessions"]],
        )
        self.assertEqual(
            [session["displayId"] for session in first["sessions"]],
            [session["displayId"] for session in second["sessions"]],
        )

    def test_saved_history_cannot_displace_a_current_live_row(self) -> None:
        saved = [
            row(
                number=index,
                work_value="unknown",
                work_at=None,
                presence_value="unknown",
                presence_at=None,
            )
            for index in range(1, 8)
        ]
        live = row("claude", "claude-home", number=8, work_value="settled")
        frame = self.project(document([*saved, live]), row_limit=1)
        self.assertEqual(live["identity"]["nativeId"], frame["sessions"][0]["identity"]["nativeId"])
        self.assertTrue(frame["sessions"][0]["liveSelected"])
        self.assertEqual("settled", frame["sessions"][0]["work"]["value"])
        self.assertEqual(live["work"]["observedAt"], frame["sessions"][0]["work"]["observedAt"])

    def test_default_six_and_hard_maximum_twenty_four_rows_with_bounded_titles(self) -> None:
        rows = [
            row(number=index, title=("long\nlabel " * 30) if index == 1 else f"Session {index}")
            for index in range(1, 27)
        ]
        default = self.project(document(rows))
        self.assertEqual(26, default["rowCount"])
        self.assertEqual(6, default["visibleRowCount"])
        self.assertTrue(default["truncated"])
        self.assertTrue(all(len(session["title"]) <= 48 for session in default["sessions"]))
        self.assertTrue(all("\n" not in session["title"] for session in default["sessions"]))
        maximum = self.project(document(rows), row_limit=24)
        self.assertEqual(24, maximum["visibleRowCount"])
        with self.assertRaisesRegex(rlcd_bridge.BridgeError, "^invalid_limit$"):
            rlcd_bridge.project_document(document(rows), row_limit=25)

    def test_codex_history_clock_can_order_rows_but_presence_clock_cannot(self) -> None:
        old_work = row(
            number=30,
            work_value="unknown",
            work_at=None,
            presence_value="unknown",
            presence_at=None,
        )
        new_history = row(
            number=31,
            work_value="unknown",
            work_at=None,
            presence_value="unknown",
            presence_at=None,
        )
        old_work["nativeHistoryTimes"] = {"createdAt": 1_700, "updatedAt": 1_800}
        new_history["nativeHistoryTimes"] = {"createdAt": 1_900, "updatedAt": 2_000}
        old_work["presence"]["observedAt"] = 9_000_000
        frame = self.project(document([old_work, new_history]))
        self.assertEqual(
            [new_history["identity"]["nativeId"], old_work["identity"]["nativeId"]],
            [session["identity"]["nativeId"] for session in frame["sessions"]],
        )
        self.assertIsNone(frame["sessions"][0]["presence"]["observedAt"])
        self.assertEqual(2_000, frame["sessions"][0]["history"]["updatedAt"])

    def test_invalid_and_oversized_documents_make_finite_content_free_frames(self) -> None:
        samples = (
            (
                b'{"schemaVersion":1,"schemaVersion":1,"secret":"private raw value"}',
                "duplicate_key",
            ),
            (b'{"n":NaN,"secret":"private raw value"}', "nonfinite_number"),
            (b" " * (rlcd_bridge.MAX_INPUT_BYTES + 1), "byte_limit"),
            (b"[" * 40 + b"0" + b"]" * 40, "depth_limit"),
        )
        for payload, code in samples:
            with self.subTest(code=code), self.assertRaises(rlcd_bridge.BridgeError) as raised:
                rlcd_bridge.project_bytes(payload)
            frame = rlcd_bridge._error_frame(raised.exception.code)
            serialized = json.dumps(frame, allow_nan=False)
            self.assertEqual(code, frame["error"]["code"])
            self.assertNotIn("private raw value", serialized)
            self.assertNotIn("secret", serialized)

        bad_schema = document()
        bad_schema["schemaVersion"] = 2
        with self.assertRaisesRegex(rlcd_bridge.BridgeError, "^unsupported_schema$"):
            self.project(bad_schema)
        wrong_host = document()
        wrong_host["sessions"][0]["identity"]["hostScope"] = "other"
        with self.assertRaisesRegex(rlcd_bridge.BridgeError, "^invalid_provenance$"):
            self.project(wrong_host)

    def test_cli_invalid_input_returns_only_a_finite_error_frame(self) -> None:
        stdout = io.StringIO()
        fake_stdin = SimpleNamespace(buffer=io.BytesIO(b'{"secret":"private raw value","n":NaN}'))
        with (
            patch.object(rlcd_bridge.sys, "stdin", fake_stdin),
            patch.object(rlcd_bridge.sys, "stdout", stdout),
        ):
            status = rlcd_bridge.main([])
        self.assertEqual(2, status)
        frame = json.loads(stdout.getvalue())
        self.assertEqual("nonfinite_number", frame["error"]["code"])
        self.assertNotIn("private raw value", stdout.getvalue())
        self.assertNotIn("secret", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
