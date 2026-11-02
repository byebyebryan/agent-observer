"""Recency ordering and column palettes over invented qualified records."""

import importlib.util
import re
import unittest

from test_terminal_model import lease, read, report, row, state

from agent_observer.terminal.render import (
    _activity_color,
    _last_active_text,
    _profile_color,
    render,
)

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from rich.color import Color
    from test_dashboard import FakeReader

    from agent_observer.terminal.dashboard import DashboardApp

SGR = re.compile(r"\x1b\[[0-9;]*m")


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
        ages = (0, 30_000, 119_000, 300_000, 1_800_000, 7_200_000, 86_400_000)
        dark = [int(_activity_color(item, age)[0].split(";")[-1]) for age in ages]
        light = [int(_activity_color(item, age, light=True)[0].split(";")[-1]) for age in ages]
        self.assertEqual(dark, sorted(dark, reverse=True))
        self.assertEqual(light, sorted(light))
        self.assertGreater(len(set(dark)), 4)
        self.assertTrue(all(232 <= color <= 255 for color in dark + light))
        self.assertEqual(_activity_color(item, 86_400_000), _activity_color(item, 7 * 86_400_000))
        self.assertEqual(_last_active_text(item, 118_000), _last_active_text(item, 119_000))
        self.assertNotEqual(_activity_color(item, 118_000), _activity_color(item, 119_000))
        newest = _activity_color(item, 0)
        for health, at in (("stale", 0), ("unavailable", 0), ("current", None), ("current", 1)):
            uncertain = {"activity": {"health": health, "at": at}}
            self.assertNotEqual(_activity_color(uncertain, 0), newest)

    def test_profile_age_and_ready_use_separate_palettes(self):
        item = row("ready")
        item["phase"]["value"] = "waiting"
        item["activity"]["at"] = 0
        document = report([state(current_read=read(rows=[item], leases=[lease("ready")]))])
        for width in (60, 140):
            colored = render(document, color=True, width=width)
            self.assertIn("\x1b[36mReady\x1b[0m", colored)
            profile = _profile_color(document["sessions"][0])[0]
            self.assertTrue(profile.startswith("38;5;"))
            self.assertLess(int(profile.split(";")[-1]), 232)
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
            clock = {"now": 118_000}
            app._display_now_ms = lambda clock=clock: clock["now"]
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                widget, previous, projected = app._age_cells[app._selected_key]
                expected = _activity_color(projected, 118_000)[1]
                age_index = 2 + app._column_widths(76)[0] if size[0] == 80 else 0
                self.assertEqual(widget.content.get_style_at_offset(app.console, age_index).color.name, expected)
                if size[0] == 60:
                    profile_widget = widget.parent.parent.children[1].children[1]
                    for cell, expected_color in (
                        (widget, expected),
                        (profile_widget, _profile_color(projected)[1]),
                    ):
                        actual = next(segment.style.color for segment in cell.render_line(0) if segment.text.strip())
                        self.assertEqual(actual.get_truecolor(), Color.parse(expected_color).get_truecolor())
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
                    actual = next(segment.style.color for segment in widget.render_line(0) if segment.text.strip())
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
                    detail.content.get_style_at_offset(app.console, len("Last active: ")).color.name,
                    _activity_color(projected, 300_000)[1],
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
            profile = widget.content.get_style_at_offset(app.console, 2 + sum(widths[:3])).color.name
            self.assertEqual(age, _activity_color(item, 119_000, light=True)[1])
            self.assertEqual(profile, _profile_color(item, light=True)[1])
            self.assertNotEqual(profile, _profile_color(item)[1])
