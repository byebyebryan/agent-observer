"""Required registry predicates are independent of provider release labels."""

import unittest

from agent_observer.native_contracts import claude_registry_capabilities


class NativeContractTest(unittest.TestCase):
    def test_foreground_question_requires_exact_interactive_wait_without_job(self):
        record = {"kind": "interactive", "status": "waiting", "statusUpdatedAt": 123,
                  "procStart": "456", "pidDomain": "verified", "jobId": None, "questionWait": True}
        self.assertIn("foreground_question", claude_registry_capabilities(record))
        for changed in ({"kind": "bg"}, {"jobId": "abcdef12"}, {"status": "idle"},
                        {"questionWait": False}, {"procStart": None}, {"pidDomain": None}):
            with self.subTest(changed=changed):
                self.assertNotIn("foreground_question", claude_registry_capabilities({**record, **changed}))
