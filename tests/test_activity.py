import unittest

from agent_observer.activity import codex_activity


class ActivityTest(unittest.TestCase):
    def test_latest_turn_uses_completion_then_start_and_never_creation(self):
        turn = {"items": [], "itemsView": "notLoaded", "startedAt": 100, "completedAt": 120}
        self.assertEqual(codex_activity({"data": [turn]})["at"], 120_000)
        self.assertEqual(codex_activity({"data": [{**turn, "completedAt": None}]})["at"], 100_000)
        self.assertIsNone(codex_activity({"data": []})["at"])

    def test_content_and_invalid_clocks_fail_without_fallback(self):
        turn = {"items": [], "itemsView": "notLoaded", "startedAt": 100, "completedAt": 120}
        for changes in (
            {"items": [{"text": "private"}]},
            {"itemsView": "full"},
            {"startedAt": True},
            {"completedAt": 99},
            {"startedAt": None},
            {"completedAt": 4_000_000_001},
        ):
            self.assertIsNone(codex_activity({"data": [{**turn, **changes}]})["at"])
