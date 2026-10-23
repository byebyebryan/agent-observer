"""Human CLI selection and display must preserve existing currentness rules."""

import contextlib
import copy
import io
import unittest
from unittest.mock import patch

from agent_observer import cli, working_set_cli


def summary():
    return {
        "lifecycle": "watching", "source": {"sourceId": "agent_working_set"},
        "clock": {"nowBoottimeMs": 100}, "transport": {"failure": None},
        "view": {
            "state": "complete", "scopes": [], "memberCount": 2,
            "uncertain": [{"reason": "unresolved"}], "nonmembers": [],
            "members": [
                {"identity": {"hostScope": "host", "namespace": "home-a", "nativeId": "loaded"},
                 "runtime": {"value": "running"}, "phase": {"value": "idle"},
                 "membershipLease": {"activeExpiresAtMs": 101}},
                {"identity": {"hostScope": "host", "namespace": "home-b", "nativeId": "recent"},
                 "runtime": {"value": "running"}, "phase": {"value": "unknown"},
                 "membershipLease": {"activeExpiresAtMs": 100, "recentExpiresAtMs": 200}},
            ],
        },
    }


class WorkingSetInspectionTest(unittest.TestCase):
    def test_active_filter_uses_unexpired_membership_not_stored_runtime(self):
        value = summary()
        original = copy.deepcopy(value)
        rendered = "\n".join(working_set_cli.lines(value, active_only=True))
        self.assertIn("home-a loaded membership=active runtime=running phase=idle", rendered)
        self.assertNotIn("home-b recent membership=", rendered)
        self.assertIn("1 uncertain", rendered)
        self.assertEqual(value, original)
        self.assertIn("home-b recent membership=recent", "\n".join(working_set_cli.lines(value)))

    def test_closed_views_never_render_members(self):
        value = summary()
        value["lifecycle"] = "closed"
        self.assertEqual(working_set_cli.lines(value), [])
        value["lifecycle"] = "revoked"
        value["transport"]["failure"] = "mesh_delivery_disconnected"
        self.assertEqual(working_set_cli.lines(value), ["revoked: mesh_delivery_disconnected"])

    def test_public_command_passes_exact_source_scope_and_bounded_lifetime(self):
        captured = []

        async def read(**options):
            captured.append(options)
            options["output"](summary())
            return 0

        with patch("agent_observer.working_set_cli.run_mesh", side_effect=read), contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(["working-set", "list", "--host", "snap", "--source", "agent_working_set_work", "--active"])
        self.assertEqual(code, 0)
        options = captured[0]
        self.assertEqual((options["host"], options["source"], options["scope"]),
                         ("snap", "agent_working_set_work", "hosts"))
        self.assertEqual((options["window_ms"], options["once"], options["duration"]),
                         (259200000, True, 5))
        self.assertNotIn("home-b recent membership=", output.getvalue())

    def test_invalid_duration_is_rejected_before_read_setup(self):
        for value in ("0", "61", "nan", "inf"):
            with self.subTest(duration=value), patch("agent_observer.working_set_cli.run_mesh") as read, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                working_set_cli.main(["watch", "--host", "snap", "--duration", value])
            read.assert_not_called()
