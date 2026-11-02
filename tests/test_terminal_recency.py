"""Recency ordering and column palettes over invented qualified records."""

import importlib.util
import io
import math
import os
import re
import unittest
from unittest.mock import patch

from test_terminal_model import lease, read, report, row, state

from agent_observer.terminal.render import (
    _activity_color,
    _host_color,
    _last_active_text,
    _profile_color,
    _profile_family,
    _workspace_color,
    render,
)

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from rich.color import Color
    from rich.console import Console
    from rich.text import Text
    from test_dashboard import FakeReader

    from agent_observer.terminal.dashboard import DashboardApp

SGR = re.compile(r"\x1b\[[0-9;]*m")


def _luminance(rgb):
    def linear(value):
        value = value / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(color, background):
    foreground = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def mixed_state():
    newest = row("recent-parked", title="Newest parked")
    newest["runtime"]["value"] = "parked"
    newest["phase"] = None
    newest["activity"]["at"] = 950
    middle = row("active-ready", title="Middle ready")
    middle["phase"]["value"] = "waiting"
    middle["activity"]["at"] = 900
    oldest = row("active-working", title="Oldest working")
    oldest["activity"]["at"] = 700
    unknown = row("unknown-age", title="Unknown age")
    unknown["activity"].update(at=None, health="stale", lastKnownAt=999)
    return state(
        current_read=read(
            rows=[oldest, unknown, middle, newest],
            leases=[
                lease("active-working"), lease("unknown-age"), lease("active-ready"),
                lease("recent-parked", active=None),
            ],
        )
    )


class TerminalRecencyTests(unittest.TestCase):
    def test_activity_and_host_order_have_no_membership_or_runtime_partition(self):
        for sort, group in (("activity", "none"), ("activity", "host-home"), ("host", "none")):
            document = report([mixed_state()], filters={"sort": sort, "group": group})
            rows = document["sessions"]
            self.assertEqual(
                [item["identity"]["nativeId"] for item in rows],
                ["recent-parked", "active-ready", "active-working", "unknown-age"],
            )
            self.assertEqual(rows[0]["membership"], "recent")
            self.assertEqual(rows[0]["runtime"]["value"], "parked")
            self.assertEqual(document["totals"]["members"], 4)
            text = render(document, mode="list", width=80)
            self.assertLess(text.index("Newest parked"), text.index("Oldest working"))

    def test_recency_ties_use_exact_identity_and_label_order_remains_explicit(self):
        earlier = row("a-recent", title="Zulu")
        later = row("z-active", title="Alpha")
        sample = state(
            current_read=read(
                rows=[later, earlier],
                leases=[lease("z-active"), lease("a-recent", active=None)],
            )
        )
        activity = report([sample])["sessions"]
        self.assertEqual([item["identity"]["nativeId"] for item in activity], ["a-recent", "z-active"])
        labels = report([sample], filters={"sort": "label"})["sessions"]
        self.assertEqual([item["label"] for item in labels], ["Alpha", "Zulu"])

    def test_age_fade_is_neutral_bounded_and_can_change_without_text_changing(self):
        item = {"activity": {"health": "current", "at": 0}}
        ages = (0, 30_000, 60_000, 300_000, 1_800_000, 7_200_000, 86_400_000)
        dark = [_activity_color(item, age)[1] for age in ages]
        light = [_activity_color(item, age, light=True)[1] for age in ages]
        self.assertEqual(dark[0], "#ffe49a")
        self.assertEqual(dark[-1], "#819fc7")
        self.assertEqual(light[0], "#6c4b00")
        self.assertEqual(light[-1], "#31527a")
        dark_rgb = [
            tuple(int(color[index : index + 2], 16) for index in (1, 3, 5)) for color in dark
        ]
        light_rgb = [
            tuple(int(color[index : index + 2], 16) for index in (1, 3, 5)) for color in light
        ]
        self.assertTrue(
            all(
                before[0] >= after[0] and before[1] >= after[1] and before[2] <= after[2]
                for before, after in zip(dark_rgb, dark_rgb[1:], strict=False)
            )
        )
        self.assertTrue(
            all(
                before[0] >= after[0]
                for before, after in zip(light_rgb, light_rgb[1:], strict=False)
            )
        )
        self.assertTrue(
            all(
                before[1] <= after[1]
                for before, after in zip(light_rgb, light_rgb[1:], strict=False)
            )
        )
        self.assertTrue(
            all(
                before[2] <= after[2]
                for before, after in zip(light_rgb, light_rgb[1:], strict=False)
            )
        )
        self.assertGreater(len(set(dark)), 4)
        progress_1m = math.log1p(1) / math.log1p(1_440)
        expected_1m = tuple(
            round(start + (end - start) * progress_1m)
            for start, end in zip((255, 228, 154), (129, 159, 199), strict=True)
        )
        self.assertEqual(dark[2], "#" + "".join(f"{component:02x}" for component in expected_1m))
        self.assertEqual(_activity_color(item, 86_400_000), _activity_color(item, 7 * 86_400_000))
        self.assertEqual(_last_active_text(item, 61_000), _last_active_text(item, 119_000))
        self.assertNotEqual(_activity_color(item, 61_000), _activity_color(item, 119_000))
        newest = _activity_color(item, 0)
        self.assertEqual(_activity_color(item, 86_400_000), ("38;2;129;159;199", "#819fc7"))
        neutral = _activity_color({"activity": {"health": "stale", "at": 0}}, 0)
        self.assertEqual(neutral, ("38;2;169;178;187", "#a9b2bb"))
        for health, at in (("stale", 0), ("unavailable", 0), ("current", None), ("current", 1)):
            uncertain = {"activity": {"health": health, "at": at}}
            self.assertNotEqual(_activity_color(uncertain, 0), newest)

    @unittest.skipUnless(TEXTUAL_AVAILABLE, "Rich is supplied by the optional dashboard extra")
    def test_rich_downgrades_truecolor_age_styles_for_256_color_terminals(self):
        output = io.StringIO()
        with patch.dict(os.environ):
            os.environ.pop("NO_COLOR", None)
            console = Console(file=output, color_system="256", force_terminal=True)
            console.print(
                Text(
                    "activity",
                    style=_activity_color({"activity": {"health": "current", "at": 0}}, 60_000)[1],
                )
            )
        self.assertRegex(output.getvalue(), r"\x1b\[38;5;\d+mactivity\x1b\[0m")

    def test_palette_text_colors_keep_contrast_on_dark_and_light_selection_surfaces(self):
        hosts = {}
        candidate = 0
        while len(hosts) < 5:
            host = f"palette-host-{candidate}"
            hosts.setdefault(_profile_family(host), host)
            candidate += 1
        profile_rows = [
            {"source": {"host": host, "home": home}}
            for host in hosts.values()
            for home in ("default", "work", "oss", "research")
        ]
        repo = {
            "details": {
                "workspaceHealth": "current",
                "repo": {"root": "/synthetic/worktree"},
            }
        }
        directory = {"details": {"cwd": "/reported/work"}}
        unknown_workspace = {"details": {"workspaceHealth": "stale", "cwd": None}}

        for light, surfaces in (
            (False, ((30, 30, 30), (45, 45, 45))),
            (True, ((216, 216, 216), (201, 201, 201))),
        ):
            colors = []
            for item in profile_rows:
                colors.extend(
                    (_host_color(item, light=light)[1], _profile_color(item, light=light)[1])
                )
            colors.extend(
                _workspace_color(item, light=light)[1]
                for item in (repo, directory, unknown_workspace)
            )
            colors.extend(
                _activity_color({"activity": {"health": "current", "at": 0}}, age, light=light)[1]
                for age in (0, 60_000, 3_600_000, 86_400_000)
            )
            colors.extend(
                (
                    _activity_color({"activity": {"health": "stale", "at": 0}}, 0, light=light)[1],
                    _activity_color({"activity": {"health": "current", "at": 1}}, 0, light=light)[
                        1
                    ],
                )
            )
            for color in colors:
                for surface in surfaces:
                    self.assertGreaterEqual(_contrast(color, surface), 4.5, (light, color, surface))

    def test_profile_age_and_ready_use_separate_palettes(self):
        item = row("ready")
        item["phase"]["value"] = "waiting"
        item["activity"]["at"] = 0
        document = report([state(current_read=read(rows=[item], leases=[lease("ready")]))])
        document["sessions"][0]["source"]["home"] = "work"
        for width in (60, 140):
            colored = render(document, color=True, width=width)
            self.assertIn("\x1b[36mReady\x1b[0m", colored)
            profile = _profile_color(document["sessions"][0])[0]
            self.assertTrue(profile.startswith("38;2;"))
            self.assertNotEqual(profile, _host_color(document["sessions"][0])[0])
            self.assertEqual(SGR.sub("", colored), render(document, width=width))


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardRecencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_newly_active_parked_row_leads_and_selection_remains_exact(self):
        app = DashboardApp(FakeReader([mixed_state()]), {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            self.assertEqual(app._visible_rows[0]["identity"]["nativeId"], "recent-parked")
            self.assertEqual(app._line_widgets[app._selected_key]._cell_values[1], "Inactive")
            await pilot.press("down")
            selected = app._selected_key
            app.filters["sort"] = "label"
            app._refresh_projection()
            await app._paint()
            self.assertEqual(app._selected_key, selected)

    async def test_age_color_ticks_in_full_compact_and_details_without_renewing_facts(self):
        for size in ((80, 24), (60, 16)):
            item = row("ready")
            item["phase"]["value"] = "waiting"
            item["activity"]["at"] = 0
            reader = FakeReader([state(current_read=read(rows=[item], leases=[lease("ready")]))])
            app = DashboardApp(reader, {})
            clock = {"now": 61_000}
            app._display_now_ms = lambda clock=clock: clock["now"]
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                widget, previous, projected = app._age_cells[app._selected_key]
                expected = _activity_color(projected, 61_000)[1]
                age_index = 2 + app._column_widths(76)[0] if size[0] == 80 else 0
                self.assertEqual(
                    widget.content.get_style_at_offset(app.console, age_index).color.name, expected
                )
                if size[0] == 60:
                    profile_widget = widget.parent.parent.children[1].children[1]
                    age_color = next(
                        segment.style.color
                        for segment in widget.render_line(0)
                        if segment.text.strip()
                    )
                    self.assertEqual(
                        age_color.get_truecolor(), Color.parse(expected).get_truecolor()
                    )
                    self.assertEqual(
                        profile_widget.content.get_style_at_offset(app.console, 0).color.name,
                        _host_color(projected)[1],
                    )
                    self.assertEqual(
                        profile_widget.content.get_style_at_offset(
                            app.console, len(projected["source"]["host"]) + 1
                        ).color.name,
                        _profile_color(projected)[1],
                    )
                before_profile = _profile_color(projected)
                clock["now"] = 119_000
                app._refresh_age_cells()
                widget, current, projected = app._age_cells[app._selected_key]
                self.assertEqual(current, previous)
                self.assertEqual(projected["activity"]["at"], 0)
                self.assertEqual(reader.revision, 1)
                self.assertEqual(_profile_color(projected), before_profile)
                self.assertEqual(
                    widget.content.get_style_at_offset(app.console, age_index).color.name,
                    _activity_color(projected, 119_000)[1],
                )
                if size[0] == 60:
                    actual = next(
                        segment.style.color
                        for segment in widget.render_line(0)
                        if segment.text.strip()
                    )
                    self.assertEqual(
                        actual.get_truecolor(),
                        Color.parse(_activity_color(projected, 119_000)[1]).get_truecolor(),
                    )
                await pilot.press("enter")
                await pilot.pause()
                detail = app.query_one("#detail-last-active")
                old = detail.content.plain
                clock["now"] = 300_000
                app._refresh_age_cells()
                self.assertNotEqual(detail.content.plain, old)
                self.assertEqual(
                    detail.content.get_style_at_offset(
                        app.console, len("Last active: ")
                    ).color.name,
                    _activity_color(projected, 300_000)[1],
                )

    async def test_split_selection_keeps_semantic_columns_when_age_color_ticks(self):
        item = row("split-ready")
        item["phase"]["value"] = "waiting"
        item["activity"]["at"] = 0
        app = DashboardApp(
            FakeReader([state(current_read=read(rows=[item], leases=[lease("split-ready")]))]),
            {},
        )
        clock = {"now": 61_000}
        app._display_now_ms = lambda: clock["now"]
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app._split_details())

            def check_selected_columns():
                widget, label, projected = app._age_cells[app._selected_key]
                compact_row = widget.parent.parent
                self.assertTrue(compact_row.has_class("selected-row"))
                status = compact_row.children[0].children[1].content
                profile = compact_row.children[1].children[1].content
                workspace = compact_row.children[1].children[3].content
                self.assertEqual(status.get_style_at_offset(app.console, 0).color.name, "cyan")
                self.assertEqual(
                    profile.get_style_at_offset(app.console, 0).color.name,
                    _host_color(projected)[1],
                )
                self.assertEqual(
                    workspace.get_style_at_offset(app.console, 0).color.name,
                    _workspace_color(projected)[1],
                )
                return widget, label, projected

            widget, previous, projected = check_selected_columns()
            before = widget.content.get_style_at_offset(app.console, 0).color.name
            clock["now"] = 119_000
            app._refresh_age_cells()
            widget, current, projected = check_selected_columns()
            self.assertEqual(current, previous)
            self.assertNotEqual(
                before, widget.content.get_style_at_offset(app.console, 0).color.name
            )
            self.assertEqual(
                widget.content.get_style_at_offset(app.console, 0).color.name,
                _activity_color(projected, 119_000)[1],
            )

    async def test_light_theme_uses_readable_neutral_ages_and_darker_profile_variants(self):
        item = row("ready")
        item["activity"]["at"] = 0
        app = DashboardApp(FakeReader([state(current_read=read(rows=[item], leases=[lease("ready")]))]), {})
        app.theme = "textual-light"
        app._display_now_ms = lambda: 119_000
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            item = app._all_rows[0]
            widget = app._line_widgets[app._selected_key]
            widths = app._column_widths(76)
            age = widget.content.get_style_at_offset(app.console, 2 + widths[0]).color.name
            profile_offset = 2 + sum(widths[:3])
            host = item["source"]["host"]
            host_color = widget.content.get_style_at_offset(app.console, profile_offset).color.name
            profile = widget.content.get_style_at_offset(
                app.console, profile_offset + len(host) + 1
            ).color.name
            self.assertEqual(age, _activity_color(item, 119_000, light=True)[1])
            self.assertEqual(host_color, _host_color(item, light=True)[1])
            self.assertEqual(profile, _profile_color(item, light=True)[1])
            self.assertNotEqual(profile, _profile_color(item)[1])
