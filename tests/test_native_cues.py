import unittest

from agent_observer.contract import ContractError
from agent_observer.native_cues import background_job, trust_required


class NativeCueTest(unittest.TestCase):
    def test_styled_pinned_output_requires_matching_exact_unique_cues(self):
        output = "\x1b[32mbackgrounded · abcd1234\x1b[0m\n  claude attach abcd1234  open in this terminal\n".encode()
        self.assertEqual(background_job(output), "abcd1234")
        for altered in (
            output.replace(b"abcd1234", b"11223344", 1),
            output + b"  claude attach abcd1234  open in this terminal\n",
            b"claude attach abcd1234",
            output + b"\x1b[2J",
        ):
            with self.assertRaises(ContractError):
                background_job(altered)

    def test_exact_trust_gate_and_other_errors_stay_distinct(self):
        message = b"Workspace not trusted. Run `claude` in /fixture once and accept the trust prompt, then retry.\n"
        self.assertTrue(trust_required(message, "/fixture"))
        self.assertFalse(trust_required(message, "/elsewhere"))
        self.assertFalse(trust_required(message + b"other error", "/fixture"))
