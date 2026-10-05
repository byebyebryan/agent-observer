import unittest

from agent_observer.contract import ContractError
from agent_observer.native_cues import background_job, background_receipt, trust_required

ORIGIN = "11111111-1111-4111-8111-111111111111"
ACTUAL = "22222222-2222-4222-8222-222222222222"


def cue(origin=ORIGIN, actual=ACTUAL, original_job="11111111"):
    return (
        "backgrounded · 22222222\n  claude attach 22222222  open in this terminal\n"
        f"note: session {origin} is already running in the background, so this started a copy as {actual}. `claude attach {original_job}` opens the original.\n"
    ).encode()


class NativeCueTest(unittest.TestCase):
    def test_copy_note_retains_full_current_and_original_identity(self):
        receipt = background_receipt(cue())
        self.assertEqual(
            (receipt.job_id, receipt.session_id, receipt.origin_id), ("22222222", ACTUAL, ORIGIN)
        )

    def test_conflicting_copy_ids_and_ambiguous_or_unrecognized_notes_reject(self):
        for value in (
            cue(actual=ORIGIN),
            cue(original_job="33333333"),
            cue() + cue(),
            cue() + b"note: claude attach 33333333 opens another session\n",
        ):
            with self.assertRaises(ContractError):
                background_receipt(value)

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
