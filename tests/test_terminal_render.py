"""Review terminal width and grouping with synthetic admitted metadata."""

import re
import unicodedata
import unittest

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.render import color_enabled, render

SGR = re.compile(r"\x1b\[[0-9;]*m")


def screen_width(line):
    plain = SGR.sub("", line)
    return sum(
        0
        if unicodedata.combining(char)
        else 2
        if unicodedata.east_asian_width(char) in {"W", "F"}
        else 1
        for char in plain
    )


class TerminalRenderTests(unittest.TestCase):
    def test_long_and_wide_metadata_wraps_in_all_tty_views_without_losing_text(self):
        native_id = "00000000-0000-4000-8000-000000000123"
        title = "界" * 80 + " cafe\u0301 " + "a" * 100
        document = report(
            [
                state(
                    current_read=read(rows=[row(native_id, title=title)], leases=[lease(native_id)])
                )
            ]
        )
        for width in (40, 60, 80, 120, 180):
            for mode in ("overview", "list", "show", "sources"):
                for color in (False, True):
                    with self.subTest(width=width, mode=mode, color=color):
                        text = render(document, mode=mode, color=color, width=width)
                        self.assertTrue(
                            all(screen_width(line) <= width for line in text.splitlines())
                        )
                        if mode != "sources":
                            self.assertEqual(text.count("界"), 80)
        piped = render(document, mode="list")
        self.assertIn(title, piped)
        self.assertIn(native_id, piped)
        self.assertNotIn("\x1b", piped)

    def test_overview_keeps_ordinary_rows_on_one_line_and_full_identity_in_list(self):
        members = [row(f"full-native-id-{index}", title=f"Session {index}") for index in range(12)]
        states = [
            state(
                current_read=read(
                    rows=members,
                    leases=[lease(member["identity"]["nativeId"]) for member in members],
                )
            )
        ]
        document = report(states, mode="overview")
        text = render(document, width=80)
        self.assertIn("12 sessions", text)
        self.assertIn("1/1 sources complete", text)
        self.assertIn("Showing 10 of 12 matches.", text)
        for member in document["sessions"]:
            matching = [
                line for line in text.splitlines() if line.startswith(member["label"] + " ")
            ]
            self.assertEqual(len(matching), 1)
            self.assertIn("fixture/Default", matching[0])
            self.assertIn("active", matching[0])
            self.assertIn("running", matching[0])
            self.assertIn("working", matching[0])
            self.assertNotIn(member["identity"]["nativeId"], text)
        self.assertTrue(all(screen_width(line) <= 80 for line in text.splitlines()))
        full = render(report(states), mode="list")
        for member in members:
            self.assertIn(member["identity"]["nativeId"], full)
        self.assertIn("fixture-project", full)

    def test_filtered_overview_keeps_failed_source_and_unfiltered_counts_visible(self):
        states = [
            state(current_read=read(rows=[row("healthy-id")], leases=[lease("healthy-id")])),
            state(
                source("offline-work", host="offline", home="work"),
                lifecycle="failed",
                baseline=False,
                reason="transport_failure",
            ),
        ]
        document = report(states, mode="overview", filters={"query": ("no-match",)})
        text = render(document, width=80)
        self.assertIn("1 session", text)
        self.assertIn("1/2 sources complete", text)
        self.assertIn("offline/Work: unavailable", text)
        self.assertIn("host transport is unavailable", text)
        self.assertIn("0 matches", text)
        self.assertNotIn("complete current coverage", text)

        stale_member = row("stale-id", title="Stale session")
        stale_member["runtime"].update(value="unknown", health="stale", lastKnownValue="running")
        stale_member["phase"].update(value="unknown", health="unavailable")
        stale_member["activity"].update(at=None, health="stale", lastKnownAt=950)
        stale = report(
            [state(current_read=read(rows=[stale_member], leases=[lease("stale-id")]))],
            mode="overview",
        )
        for width in (40, 80, 120):
            text = render(stale, width=width)
            self.assertIn("unknown (stale)", text)
            self.assertIn("unknown (unavailable)", text)
            self.assertNotIn("running", text)
            self.assertNotIn("working", text)

    def test_grouping_is_contiguous_in_json_model_and_human_output(self):
        states = []
        for host, activities in (("alpha", (950, 800)), ("bravo", (900, 850))):
            rows = [row(f"{host}-{index}", host=host) for index in range(2)]
            for member, activity in zip(rows, activities, strict=True):
                member["activity"]["at"] = activity
            states.append(
                state(
                    source(f"{host}-default", host=host),
                    current_read=read(
                        rows=rows,
                        leases=[
                            lease(member["identity"]["nativeId"], host=host) for member in rows
                        ],
                        host=host,
                    ),
                )
            )
        document = report(states, filters={"group": "host-home"})
        self.assertEqual(
            [member["source"]["host"] for member in document["sessions"]],
            ["alpha", "alpha", "bravo", "bravo"],
        )
        text = render(document)
        self.assertEqual(text.count("[alpha/Default]"), 1)
        self.assertEqual(text.count("[bravo/Default]"), 1)

    def test_no_color_and_pipes_override_terminal_color_requests(self):
        self.assertFalse(color_enabled("always", environ={"NO_COLOR": "1"}, isatty=True))
        self.assertFalse(color_enabled("always", environ={}, isatty=False))
        self.assertFalse(color_enabled("auto", environ={"TERM": "dumb"}, isatty=True))
        self.assertTrue(color_enabled("auto", environ={"TERM": "xterm"}, isatty=True))
