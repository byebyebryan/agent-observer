"""Profile identity colors stay stable without changing observation or plain text."""

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.render import (
    _activity_color,
    _host_color,
    _profile_ansi,
    _profile_color,
    _profile_family,
    _workspace_color,
    render,
)

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from rich.cells import cell_len
    from rich.style import Style
    from test_dashboard import FakeReader

    from agent_observer.terminal.dashboard import DashboardApp

SGR = re.compile(r"\x1b\[[0-9;]*m")


def _rgb_tuple(color):
    triplet = color.get_truecolor()
    return triplet.red, triplet.green, triplet.blue


def _contrast_ratio(foreground, background):
    def luminance(rgb):
        linear = []
        for value in rgb:
            normalized = value / 255
            linear.append(
                normalized / 12.92
                if normalized <= 0.04045
                else ((normalized + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def samples():
    result = []
    for index, (host, home) in enumerate(
        (
            ("starship", "default"),
            ("snap", "default"),
            ("snap", "work"),
            ("carbon", "default"),
        )
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
    def test_host_families_and_home_shades_are_stable_and_order_independent(self):
        rows = report(samples())["sessions"]
        identity_colors = {
            (item["source"]["host"], item["source"]["home"]): (
                _host_color(item),
                _profile_color(item),
            )
            for item in rows
        }
        host_colors = {
            host: _host_color(next(item for item in rows if item["source"]["host"] == host))
            for host in ("starship", "snap", "carbon")
        }
        self.assertEqual(len(set(host_colors.values())), 3)
        self.assertEqual(
            _host_color(
                next(
                    item
                    for item in rows
                    if item["source"]["home"] == "default" and item["source"]["host"] == "snap"
                )
            ),
            _host_color(next(item for item in rows if item["source"]["home"] == "work")),
        )
        self.assertNotEqual(
            identity_colors[("snap", "default")][1], identity_colors[("snap", "work")][1]
        )
        reversed_rows = report(list(reversed(samples())))["sessions"]
        self.assertEqual(
            {
                (item["source"]["host"], item["source"]["home"]): (
                    _host_color(item),
                    _profile_color(item),
                )
                for item in reversed_rows
            },
            identity_colors,
        )
        for item in rows:
            color = _profile_color(item)
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
                        self.assertIn(_profile_ansi(item, True), colored)
                        filtered = report(
                            list(reversed(samples())),
                            mode=mode,
                            filters={"source": (item["source"]["id"],), "group": group},
                        )
                        text = render(filtered, mode=mode, color=True, width=width)
                        self.assertIn(_profile_ansi(item, True), text)
                        if group == "host-home":
                            self.assertIn(_profile_ansi(item, True, bracketed=True), text)
                    self.assertEqual(json.dumps(document, sort_keys=True), before)


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardProfileColorTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_compact_and_split_profile_cells_keep_the_same_color(self):
        app = DashboardApp(FakeReader(samples()), {"group": "host-home"})
        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()

            def check_full_rows():
                widths = app._column_widths(106)
                profile_offset = 2 + sum(widths[:2])
                for item in app._all_rows:
                    widget = app._line_widgets[app._row_key(item)]
                    host = item["source"]["host"]
                    host_color = widget.content.get_style_at_offset(
                        app.console, profile_offset
                    ).color
                    home_color = widget.content.get_style_at_offset(
                        app.console, profile_offset + len(host) + 1
                    ).color
                    self.assertEqual(host_color.name, _host_color(item)[1])
                    self.assertEqual(
                        bool(
                            widget.content.get_style_at_offset(app.console, profile_offset).bold
                        ),
                        app._row_key(item) == app._selected_key,
                    )
                    self.assertEqual(home_color.name, _profile_color(item)[1])
                    self.assertEqual(
                        widget.content.get_style_at_offset(app.console, 2).color.name, "green"
                    )
                    workspace_offset = 2 + sum(widths[:3])
                    workspace_color = widget.content.get_style_at_offset(
                        app.console, workspace_offset
                    ).color
                    self.assertEqual(workspace_color.name, _workspace_color(item)[1])

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
                        _host_color(item)[1],
                    )
                    self.assertEqual(
                        profile.get_style_at_offset(
                            app.console, len(item["source"]["host"]) + 1
                        ).color.name,
                        _profile_color(item)[1],
                    )
                    status = age.parent.parent.children[0].children[1].content
                    self.assertEqual(status.get_style_at_offset(app.console, 0).color.name, "green")
                    workspace = context.children[3].content
                    self.assertEqual(
                        workspace.get_style_at_offset(app.console, 0).color.name,
                        _workspace_color(item)[1],
                    )
                    if key == app._selected_key:
                        self.assertTrue(profile.get_style_at_offset(app.console, 0).bold)

            check_compact_rows()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.resize_terminal(140, 36)
            await pilot.pause()
            self.assertTrue(app._split_details())
            check_compact_rows()

    async def test_rendered_selection_surface_is_single_layer_in_all_layouts_and_themes(self):
        layouts = (
            (110, 24, False),
            (80, 24, False),
            (60, 16, False),
            (40, 16, False),
            (140, 36, True),
        )
        surface_by_theme = {}

        def rendered_style_at(strips, x, y):
            offset = 0
            for segment in strips[y]._segments:
                width = cell_len(segment.text)
                if width and offset <= x < offset + width:
                    return segment.style
                offset += width
            self.fail(f"no rendered segment at ({x}, {y})")

        def colors_in_region(strips, region):
            colors = []
            for y in range(region.y, region.bottom):
                offset = 0
                for segment in strips[y]._segments:
                    width = cell_len(segment.text)
                    if width and offset < region.right and offset + width > region.x:
                        self.assertIsNotNone(segment.style.bgcolor)
                        colors.append(_rgb_tuple(segment.style.bgcolor))
                    offset += width
            return colors

        def hex_rgb(value):
            return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))

        for theme in ("textual-dark", "textual-light"):
            light = theme == "textual-light"
            for size, height, split in layouts:
                with self.subTest(theme=theme, size=(size, height), split=split):
                    filters = {"group": "host-home"} if size >= 60 else {}
                    app = DashboardApp(FakeReader(samples()), filters)
                    app.theme = theme
                    async with app.run_test(size=(size, height)) as pilot:
                        await pilot.pause()
                        if split:
                            await pilot.press("enter")
                            await pilot.pause()

                        key = app._selected_key
                        full_table = size >= 110 and not split
                        selected = (
                            app._line_widgets[key]
                            if full_table
                            else app._age_cells[key][0].parent.parent
                        )
                        item = next(row for row in app._all_rows if app._row_key(row) == key)
                        selection_style = selected.styles.background
                        self.assertAlmostEqual(selection_style.a, 0.08)
                        self.assertEqual(selection_style.r, selection_style.g)
                        self.assertEqual(selection_style.g, selection_style.b)
                        strips = app.screen._compositor.render_strips()
                        rendered_backgrounds = colors_in_region(strips, selected.region)
                        self.assertTrue(rendered_backgrounds)
                        if full_table:
                            unselected = next(
                                widget
                                for row_key, widget in app._line_widgets.items()
                                if row_key != key
                            )
                        else:
                            unselected_key = next(
                                row_key for row_key in app._age_cells if row_key != key
                            )
                            unselected = app._age_cells[unselected_key][0].parent.parent
                        base_backgrounds = colors_in_region(strips, unselected.region)
                        self.assertTrue(base_backgrounds)
                        self.assertEqual(len(set(base_backgrounds)), 1)
                        base_background = base_backgrounds[0]
                        alpha = selection_style.a
                        tint = (selection_style.r, selection_style.g, selection_style.b)
                        selected_background = tuple(
                            int(foreground * alpha + background * (1 - alpha))
                            for foreground, background in zip(tint, base_background, strict=True)
                        )
                        self.assertEqual(set(rendered_backgrounds), {selected_background})
                        if not full_table:
                            for child in selected.children:
                                self.assertTrue(child.styles.background.is_transparent)

                        if full_table:
                            widths = app._column_widths(size - 4)
                            x = selected.region.x + 2
                            profile_x = x + sum(widths[:2])
                            palette_points = (
                                (
                                    "age",
                                    selected.region.x + selected.content.plain[: 2 + widths[0]].rfind(
                                        selected._cell_values[2]
                                    ),
                                    selected.region.y,
                                ),
                                ("host", profile_x, selected.region.y),
                                (
                                    "profile",
                                    profile_x + len(item["source"]["host"]) + 1,
                                    selected.region.y,
                                ),
                                ("workspace", x + sum(widths[:3]), selected.region.y),
                            )
                            status_point = ("status", x, selected.region.y)
                        elif size < 60:
                            first, _title, profile_row, workspace_row = selected.children
                            profile = profile_row.children[1]
                            palette_points = (
                                (
                                    "age",
                                    app._age_cells[key][0].region.x,
                                    app._age_cells[key][0].region.y,
                                ),
                                ("host", profile.region.x, profile.region.y),
                                (
                                    "profile",
                                    profile.region.x + len(item["source"]["host"]) + 1,
                                    profile.region.y,
                                ),
                                (
                                    "workspace",
                                    workspace_row.children[1].region.x,
                                    workspace_row.children[1].region.y,
                                ),
                            )
                            status_point = (
                                "status", first.children[1].region.x, first.children[1].region.y
                            )
                        else:
                            first, second = selected.children
                            profile = second.children[1]
                            palette_points = (
                                (
                                    "age",
                                    app._age_cells[key][0].region.x,
                                    app._age_cells[key][0].region.y,
                                ),
                                ("host", profile.region.x, profile.region.y),
                                (
                                    "profile",
                                    profile.region.x + len(item["source"]["host"]) + 1,
                                    profile.region.y,
                                ),
                                (
                                    "workspace",
                                    second.children[3].region.x,
                                    second.children[3].region.y,
                                ),
                            )
                            status_point = (
                                "status", first.children[1].region.x, first.children[1].region.y
                            )

                        if light:
                            palette_points = (status_point, *palette_points)

                        for name, x, y in palette_points:
                            style = rendered_style_at(strips, x, y)
                            self.assertIsNotNone(style.color)
                            self.assertGreaterEqual(
                                _contrast_ratio(
                                    _rgb_tuple(style.color), selected_background
                                ),
                                4.5,
                                f"{name}: {style.color!r} on {selected_background!r}",
                            )

                        previous = surface_by_theme.setdefault(theme, selected_background)
                        self.assertEqual(selected_background, previous)

                        family_hosts = {}
                        candidate = 0
                        while len(family_hosts) < 5:
                            host = f"render-contrast-{candidate}"
                            family_hosts.setdefault(_profile_family(host), host)
                            candidate += 1
                        palette_colors = []
                        for host in family_hosts.values():
                            for home in ("default", "work", "oss", "research"):
                                identity = {"source": {"host": host, "home": home}}
                                palette_colors.append(_host_color(identity, light=light)[1])
                                palette_colors.append(_profile_color(identity, light=light)[1])
                        for workspace in (
                            {
                                "details": {
                                    "workspaceHealth": "current",
                                    "repo": {"root": "/synthetic/repo"},
                                }
                            },
                            {"details": {"cwd": "/reported/directory"}},
                            {"details": {"workspaceHealth": "stale", "cwd": None}},
                        ):
                            palette_colors.append(_workspace_color(workspace, light=light)[1])
                        palette_colors.extend(
                            (
                                _activity_color(
                                    {"activity": {"health": "current", "at": 0}},
                                    0,
                                    light=light,
                                )[1],
                                _activity_color(
                                    {"activity": {"health": "current", "at": 0}},
                                    86_400_000,
                                    light=light,
                                )[1],
                                _activity_color(
                                    {"activity": {"health": "stale", "at": 0}},
                                    0,
                                    light=light,
                                )[1],
                            )
                        )
                        for color in palette_colors:
                            self.assertGreaterEqual(
                                _contrast_ratio(hex_rgb(color), selected_background), 4.5
                            )
                        if light:
                            for status in (
                                "Working", "Ready", "Blocked", "Inactive", "Unknown",
                                "Stale", "Unavailable",
                            ):
                                color = Style.parse(app._semantic_style(status)).color
                                self.assertIsNotNone(color)
                                self.assertGreaterEqual(
                                    _contrast_ratio(_rgb_tuple(color), selected_background), 4.5,
                                    status,
                                )

    async def test_no_color_retains_colorless_cells_and_selection(self):
        app = DashboardApp(FakeReader(samples()), {}, no_color=True)
        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            offset = 2 + sum(app._column_widths(106)[:2])
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
            await pilot.resize_terminal(32, 12)
            await pilot.pause()
            card = app._age_cells[app._selected_key][0].parent.parent
            profile = card.children[2].children[1].content
            style = profile.get_style_at_offset(app.console, 0)
            self.assertIsNone(style.color)
            self.assertTrue(style.reverse)
