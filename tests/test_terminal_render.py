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
            for mode in ("list", "show", "sources"):
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
