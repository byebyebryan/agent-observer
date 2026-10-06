import unittest

from agent_observer.activity import codex_activity, codex_outcome


class ActivityTest(unittest.TestCase):
    def test_outcome_is_latest_explicit_terminal_status_with_independent_clock(self):
        turn = {"items": [], "itemsView": "notLoaded", "startedAt": 100, "completedAt": 120}
        for status, outcome in (("completed", "completed"), ("failed", "failed"), ("interrupted", "cancelled")):
            result = codex_outcome({"data": [{**turn, "status": status}]})
            self.assertEqual(result["value"], outcome)
            self.assertEqual(result["observedAt"], 120000)
        for changes in ({"status": "inProgress", "completedAt": None},
                        {"status": "systemError"}, {"status": "failed", "completedAt": None},
                        {"status": "failed", "items": [{"text": "private"}]}):
            self.assertEqual(codex_outcome({"data": [{**turn, **changes}]})["value"], "unknown")
        self.assertEqual(codex_outcome({"data": [{**turn, "status": "failed", "startedAt": None}]},
                                       completion_only=True)["value"], "failed")

    def test_latest_turn_uses_completion_then_start_and_never_creation(self):
        turn = {"items": [], "itemsView": "notLoaded", "startedAt": 100, "completedAt": 120}
        self.assertEqual(codex_activity({"data": [turn]})["at"], 120_000)
        self.assertEqual(codex_activity({"data": [{**turn, "completedAt": None}]})["at"], 100_000)
        self.assertIsNone(codex_activity({"data": []})["at"])
        completion = {"data": [{**turn, "startedAt": None}]}
        self.assertEqual(codex_activity(completion, completion_only=True)["at"], 120_000)
        self.assertIsNone(codex_activity(completion)["at"])

    def test_content_and_invalid_clocks_fail_without_fallback(self):
        turn = {"items": [], "itemsView": "notLoaded", "startedAt": 100, "completedAt": 120}
        for changes in (
            {"items": [{"text": "private"}]},
            {"itemsView": "full"},
            {"startedAt": True},
            {"completedAt": 99},
            {"startedAt": None, "completedAt": None},
            {"completedAt": 4_000_000_001},
        ):
            self.assertIsNone(codex_activity({"data": [{**turn, **changes}]})["at"])
