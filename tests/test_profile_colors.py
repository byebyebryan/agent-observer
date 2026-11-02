"""Profile identity colors stay stable without changing observation or plain text."""

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.render import _profile_color, render

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from test_dashboard import FakeReader

    from agent_observer.terminal.dashboard import DashboardApp

SGR = re.compile(r"\x1b\[[0-9;]*m")


def samples():
    result = []
    for index, (host, home) in enumerate(
        (("starship", "default"), ("snap", "default"), ("snap", "work"))
    ):
        item = row(f"fictional-{index}", title=f"Task {index}", host=host)
        result.append(
            state(
                source(f"route-{index}", host=host, home=home),
                current_read=read(
                    rows=[item], leases=[lease(item["identity"]["nativeId"], host=host)], host=host
                ),
            )
        )
    return result


class ProfileColorTests(unittest.TestCase):
    def test_pair_identity_is_stable_and_the_current_three_profiles_are_distinct(self):
        rows = report(samples())["sessions"]
        colors = [_profile_color(item) for item in rows]
        self.assertEqual(len(set(colors)), 3)
        for item, color in zip(rows, colors, strict=True):
            item["source"].update(label="Changed caption", id="another-route")
            item["label"] = "Renamed session"
            self.assertEqual(_profile_color(item), color)
        for item in ({}, {"source": None}, {"source": {"host": "a"}}):
            self.assertIsNone(_profile_color(item))

    def test_colors_do_not_depend_on_python_hash_seed(self):
        script = (
            "from agent_observer.terminal.render import _profile_color; "
            "print(_profile_color({'source': {'host': 'snap', 'home': 'work'}}))"
        )
        values = [
            subprocess.check_output(
                [sys.executable, "-B", "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed},
            )
            for seed in ("11", "73")
        ]
        self.assertEqual(*values)

    def test_finite_colors_survive_width_grouping_and_source_filter_changes(self):
        for mode in ("overview", "list"):
            for group in ("none", "host-home"):
                for width in (60, 140):
                    document = report(samples(), mode=mode, filters={"group": group})
                    before = json.dumps(document, sort_keys=True)
                    colored = render(document, mode=mode, color=True, width=width)
                    plain = render(document, mode=mode, width=width)
                    self.assertEqual(SGR.sub("", colored), plain)
                    self.assertNotIn("\x1b", plain)
                    self.assertIn("\x1b[32mWorking\x1b[0m", colored)
                    for item in document["sessions"]:
                        code, _ = _profile_color(item)
                        profile = f"{item['source']['host']}/{item['source']['home']}"
                        self.assertIn(f"\x1b[{code}m{profile}\x1b[0m", colored)
                        filtered = report(
                            list(reversed(samples())),
                            mode=mode,
                            filters={"source": (item["source"]["id"],), "group": group},
                        )
                        text = render(filtered, mode=mode, color=True, width=width)
                        self.assertIn(f"\x1b[{code}m{profile}\x1b[0m", text)
                        if group == "host-home":
                            self.assertIn(f"\x1b[1;{code}m[{profile}]\x1b[0m", text)
                    self.assertEqual(json.dumps(document, sort_keys=True), before)


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardProfileColorTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_compact_and_split_profile_cells_keep_the_same_color(self):
        app = DashboardApp(FakeReader(samples()), {"group": "host-home"})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            def check_full_rows():
                offset = 2 + sum(app._column_widths(76)[:3])
                for item in app._all_rows:
                    widget = app._line_widgets[app._row_key(item)]
                    color = widget.content.get_style_at_offset(app.console, offset).color
                    self.assertEqual(color.name, _profile_color(item)[1])
                    self.assertEqual(
                        widget.content.get_style_at_offset(app.console, 2).color.name, "green"
                    )

            check_full_rows()
            await pilot.press("down")
            check_full_rows()
            await pilot.resize_terminal(60, 16)
            await pilot.pause()

            def check_compact_rows():
                for key, (age, _, item) in app._age_cells.items():
                    context = age.parent.parent.children[1]
                    profile = context.children[1].content
                    self.assertEqual(
                        profile.get_style_at_offset(app.console, 0).color.name,
                        _profile_color(item)[1],
                    )
                    if key == app._selected_key:
                        self.assertTrue(profile.get_style_at_offset(app.console, 0).bold)

            check_compact_rows()
            await pilot.press("enter")
            await pilot.resize_terminal(140, 36)
            await pilot.pause()
            self.assertTrue(app._split_details())
            check_compact_rows()

    async def test_no_color_retains_colorless_cells_and_selection(self):
        app = DashboardApp(FakeReader(samples()), {}, no_color=True)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            offset = 2 + sum(app._column_widths(76)[:3])
            for item in app._all_rows:
                widget = app._line_widgets[app._row_key(item)]
                style = widget.content.get_style_at_offset(app.console, offset)
                self.assertIsNone(style.color)
                if app._row_key(item) == app._selected_key:
                    self.assertTrue(style.reverse)
            await pilot.resize_terminal(60, 16)
            await pilot.pause()
            for key, (age, _, _) in app._age_cells.items():
                profile = age.parent.parent.children[1].children[1].content
                style = profile.get_style_at_offset(app.console, 0)
                self.assertIsNone(style.color)
                if key == app._selected_key:
                    self.assertTrue(style.reverse)
