"""Metadata privacy, event authority, bounded duplicate suppression and transport."""

import base64
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_observer.notification_client import RecentEvents, render
from agent_observer.notification_source import (
    NotificationError,
    normalize,
    parse_event,
    validate_event,
)
from agent_observer.public import ContractError, WireError

FIXTURE = Path(__file__).parent / "fixtures/contract-v4/snapshot.json"
TURN = "99999999-1234-1234-1234-123456789abc"
RECEIPT = "88888888-1234-1234-1234-123456789abc"


class NotificationTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(FIXTURE.read_text())
        self.row = next(
            r
            for r in self.snapshot["sessions"]
            if r["identity"]["provider"] == "codex" and r["kind"] != "child"
        )
        self.ref = self.row["identity"]

    def event(self, payload=None, **options):
        payload = payload or {
            "type": "agent-turn-complete",
            "thread-id": self.ref["nativeId"],
            "turn-id": TURN,
        }
        return normalize(
            json.dumps(payload).encode(),
            self.ref,
            snapshot=self.snapshot,
            received_at=100,
            receipt_id=RECEIPT,
            **options,
        )

    def claude(self, **payload):
        ref = next(
            r["identity"]
            for r in self.snapshot["sessions"]
            if r["identity"]["provider"] == "claude"
        )
        return normalize(
            json.dumps(
                {
                    "session_id": ref["nativeId"],
                    "hook_event_name": "Notification",
                    "prompt_id": TURN,
                    **payload,
                }
            ).encode(),
            ref,
            snapshot=self.snapshot,
            received_at=100,
        )

    def test_callback_content_is_discarded_and_exact_public_title_kind_are_reused(self):
        payload = {
            "type": "agent-turn-complete",
            "thread-id": self.ref["nativeId"],
            "turn-id": TURN,
            "last-assistant-message": "PRIVATE_RESPONSE",
            "input-messages": ["PRIVATE_PROMPT"],
            "cwd": "PRIVATE_PATH",
            "title": "PRIVATE_CAPTION",
            "tool_input": "PRIVATE_TOOL",
        }
        event = self.event(payload)
        self.assertNotIn("PRIVATE", json.dumps(event))
        self.assertEqual(event["title"], self.row["title"])
        self.assertEqual(event["body"], "Turn complete")
        payload["thread-id"] = TURN
        with self.assertRaises(NotificationError):
            self.event(payload)
        event = normalize(
            json.dumps({**payload, "thread-id": self.ref["nativeId"]}).encode(),
            self.ref,
            received_at=100,
        )
        self.assertEqual(
            (event["kind"], event["disposition"], event["titleSource"]),
            ("unknown", "notify", "fallback"),
        )
        self.row["kind"] = "child"
        self.assertEqual(self.event()["reason"], "child_suppressed")

    def test_claude_response_end_background_and_child_callbacks_never_claim_completion(self):
        for event_name in ("Stop", "UserPromptSubmit"):
            event = self.claude(
                hook_event_name=event_name,
                last_assistant_message="PRIVATE_RESPONSE",
                stop_hook_active=False,
            )
            self.assertEqual(event["disposition"], "wake")
            self.assertEqual(render(event, "claude-hook"), "{}\n")
        for kind in ("agent_completed", "agent_needs_input"):
            self.assertEqual(
                self.claude(notification_type=kind)["reason"], "background_target_unproved"
            )
        for child in ({"agent_id": "native-child"}, {"hook_event_name": "SubagentStop"}):
            self.assertEqual(
                self.claude(notification_type="idle_prompt", **child)["reason"], "child_suppressed"
            )
        event = self.claude(notification_type="permission_prompt", agent_type="custom-top-level")
        self.assertEqual((event["disposition"], event["body"]), ("notify", "Permission needed"))
        for kind in ("auth_success", "quota_warning", "future_signal"):
            self.assertEqual(self.claude(notification_type=kind)["disposition"], "ignore")
        for changes in ({"notification_type": []}, {"hook_event_name": {}}):
            with self.assertRaises(NotificationError):
                self.claude(**changes)

    def test_deduplication_distinguishes_turn_host_store_and_receipt(self):
        seen = RecentEvents(2)
        first = self.event()
        self.assertTrue(seen.accept(first))
        replay = copy.deepcopy(first)
        replay["receiptId"] = TURN
        self.assertFalse(seen.accept(replay))
        other = copy.deepcopy(self.ref)
        other["hostScope"] = "other"
        event = normalize(
            json.dumps(
                {"type": "agent-turn-complete", "thread-id": other["nativeId"], "turn-id": TURN}
            ).encode(),
            other,
            received_at=100,
        )
        self.assertTrue(seen.accept(event))
        other["namespace"] = "sha256:" + "f" * 64
        scoped = normalize(
            json.dumps(
                {"type": "agent-turn-complete", "thread-id": other["nativeId"], "turn-id": TURN}
            ).encode(),
            other,
            received_at=100,
        )
        self.assertTrue(seen.accept(scoped))
        self.assertTrue(seen.accept(self.claude(notification_type="permission_prompt")))
        self.assertEqual(len(seen.keys), 2)
        self.assertTrue(seen.accept(first))  # Eviction deliberately loses prior suppression.
        self.assertTrue(RecentEvents().accept(first))  # Restart has no native replay receipt.
        a, b = (
            self.claude(notification_type="permission_prompt"),
            self.claude(notification_type="permission_prompt"),
        )
        self.assertEqual(a["correlation"]["nativeId"], b["correlation"]["nativeId"])
        self.assertIsNone(a["correlation"]["dedupeKey"])
        self.assertTrue(seen.accept(a))
        self.assertTrue(seen.accept(b))

    def test_ignored_exec_callback_does_not_consume_visible_completion_key(self):
        seen = RecentEvents()
        ignored = self.event(
            {
                "type": "agent-turn-complete",
                "thread-id": self.ref["nativeId"],
                "turn-id": TURN,
                "client": "codex_exec",
            }
        )
        self.assertEqual(ignored["disposition"], "ignore")
        self.assertTrue(seen.accept(ignored))
        self.assertTrue(seen.accept(self.event()))
        self.assertFalse(seen.accept(self.event()))

    def test_kitty_protocol_separates_sender_title_body_and_keeps_native_focus_policy(self):
        sequence = render(self.event())
        frames = sequence.split("\x1b\\")[:-1]
        self.assertEqual(len(frames), 2)
        ids = []
        for frame in frames:
            meta, encoded = frame.removeprefix("\x1b]99;").split(";", 1)
            fields = dict(part.split("=", 1) for part in meta.split(":"))
            self.assertEqual(base64.b64decode(fields["f"]), b"Codex")
            self.assertEqual((fields["o"], fields["a"], fields["e"]), ("unfocused", "focus", "1"))
            ids.append(fields["i"])
            expected = self.row["title"] if fields["d"] == "0" else "Turn complete"
            self.assertEqual(base64.b64decode(encoded).decode(), expected)
            self.assertLess(len(encoded), 4096)
        self.assertEqual(ids[0], ids[1])
        wrapped = render(self.event(), tmux_passthrough=True)
        self.assertEqual(wrapped, "\x1bPtmux;" + sequence.replace("\x1b", "\x1b\x1b") + "\x1b\\")
        with self.assertRaises(NotificationError):
            render(
                self.claude(notification_type="idle_prompt"), "claude-hook", tmux_passthrough=True
            )
        event = self.claude(notification_type="idle_prompt")
        hook = json.loads(render(event, "claude-hook"))
        self.assertEqual(set(hook), {"terminalSequence"})
        self.assertNotIn("decision", hook)
        self.assertIn("99;", hook["terminalSequence"])

    def test_bounded_input_false_semantics_and_raw_error_privacy(self):
        with self.assertRaises(WireError):
            normalize(b'{"session_id":1,"session_id":2}', self.ref)
        with self.assertRaises(WireError):
            normalize(b" " * (1024 * 1024 + 1), self.ref)
        for change in (
            {"body": "PRIVATE_RESPONSE"},
            {"sourceEvent": "Stop"},
            {"disposition": "wake"},
            {"title": "bad\x1b]99;"},
            {"correlation": {"nativeId": TURN, "scope": "native_turn", "dedupeKey": None}},
        ):
            with self.subTest(change=change), self.assertRaises((NotificationError, ContractError)):
                validate_event({**self.event(), **change})
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "agent_observer.notification_client", "render"],
            input=b'{"PRIVATE_RESPONSE":"bad"}',
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, b"")
        self.assertNotIn(b"PRIVATE", proc.stderr)

    def test_stream_normalized_frames_are_bounded_and_duplicate_aware(self):
        line = json.dumps(self.event()).encode() + b"\n"
        self.assertEqual(parse_event(line, framed=True), self.event())
        with self.assertRaises(WireError):
            parse_event(line[:-1], framed=True)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "agent_observer.notification_client", "stream"],
            input=line * 3,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, line)

    def test_native_capture_failure_outside_isolation_is_quiet_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as scratch:
            env = dict(os.environ)
            env["NATIVE_PROOF_ROOT"] = scratch
            env["PYTHONPATH"] = str(Path(__file__).parent.parent)
            script = Path(__file__).parent.parent / "scripts/capture-native-notifications"
            proc = subprocess.run(
                [sys.executable, "-B", str(script), "claude"],
                input=b'{"message":"PRIVATE_CALLBACK"}',
                env=env,
                capture_output=True,
            )
            self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"{}\n", b""))
            self.assertEqual(list(Path(scratch).iterdir()), [])
