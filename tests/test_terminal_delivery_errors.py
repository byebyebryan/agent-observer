"""Source-specific failure metadata never supplies a positive observation."""

import unittest

from test_terminal_model import report, source, state

from agent_observer.terminal.sources import _delivery_error


class TerminalDeliveryErrorTests(unittest.TestCase):
    def test_failed_source_keeps_lifecycle_and_original_delivery_code(self):
        context = {
            "hosts": [
                {
                    "hostId": "fixture",
                    "delivery": {
                        "error": {
                            "code": "source_not_configured",
                            "message": "unretained transport text",
                        }
                    },
                }
            ]
        }
        code = _delivery_error(context, "fixture")
        self.assertEqual(_delivery_error({"mesh": context}, "fixture"), code)
        failed = state(source(), lifecycle="failed", baseline=False, reason="mesh_resync")
        failed["delivery_error"] = code
        document = report([failed])
        self.assertEqual(document["sources"][0]["deliveryError"], "source_not_configured")
        self.assertIn("mesh_resync", document["sources"][0]["reasons"])
        self.assertIn("source_not_configured", document["sources"][0]["reasons"])
        self.assertEqual(document["sessions"], [])
        self.assertEqual(document["result"], "degraded")
        self.assertNotIn("unretained transport text", str(document))
        self.assertIsNone(_delivery_error(context, "another-host"))
        context["hosts"][0]["delivery"]["error"]["code"] = "raw error text\n"
        self.assertIsNone(_delivery_error(context, "fixture"))
