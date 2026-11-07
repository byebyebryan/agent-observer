"""Profile identity colors stay stable without changing observation or plain text."""

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.dashboard_palette import (
    directory_prefix_color as _directory_prefix_color,
)
from agent_observer.terminal.dashboard_palette import (
    directory_prefix_end as _directory_prefix_end,
)
from agent_observer.terminal.dashboard_palette import (
    home_shade_index as _dashboard_home_shade_index,
)
from agent_observer.terminal.dashboard_palette import (
    host_color as _dashboard_host_color,
)
from agent_observer.terminal.dashboard_palette import (
    profile_color as _dashboard_profile_color,
)
from agent_observer.terminal.dashboard_palette import (
    workspace_color as _dashboard_workspace_color,
)
from agent_observer.terminal.render import (
    _activity_color,
    _host_color,
    _profile_ansi,
    _profile_color,
    _profile_family,
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


class DashboardPaletteTests(unittest.TestCase):
    def test_approved_five_family_four_shade_matrices_are_fixed(self):
        expected = {
            False: (
                ("#98b9e8", "#a0bee8", "#a6c2e9", "#abc5ea"),
                ("#beace2", "#c2b3e4", "#c5b7e5", "#c8bbe6"),
                ("#dba5c5", "#dcacca", "#ddb1cd", "#ddb6d0"),
                ("#94c2df", "#9cc6e1", "#a1c9e2", "#a7cce4"),
                ("#afb2e3", "#b4b8e4", "#b8bce5", "#bcc0e7"),
            ),
            True: (
                ("#354d72", "#344a6c", "#324768", "#314563"),
                ("#574273", "#52406d", "#4f3e68", "#4b3d64"),
                ("#6f3f5e", "#673d5a", "#623c57", "#5d3b54"),
                ("#2e506b", "#2d4c65", "#2d4a61", "#2c475e"),
                ("#454975", "#42466e", "#40446a", "#3e4265"),
            ),
        }
        family_hosts = {}
        candidate = 0
        while len(family_hosts) < 5 and candidate < 10_000:
            host = f"approved-palette-family-{candidate}"
            family_hosts.setdefault(_profile_family(host), host)
            candidate += 1
        self.assertEqual(set(family_hosts), set(range(5)))

        homes = ("default", "oss", "work", "palette-one")
        self.assertEqual(
            [_dashboard_home_shade_index(home) for home in homes], [0, 1, 2, 3]
        )
        for light, matrix in expected.items():
            for family, host in family_hosts.items():
                for shade, home in enumerate(homes):
                    identity = {"source": {"host": host, "home": home}}
                    self.assertEqual(
                        _dashboard_profile_color(identity, light=light)[1],
                        matrix[family][shade],
                    )
                    self.assertEqual(
                        _dashboard_host_color(identity, light=light)[1], matrix[family][0]
                    )

    def test_fixed_workspace_colors_and_directory_prefix_are_typed(self):
        examples = {
            "repo": {
                "details": {
                    "workspaceHealth": "current",
                    "repo": {"root": "/synthetic/repository"},
                }
            },
            "dir": {
                "details": {
                    "workspaceHealth": "current",
                    "repo": None,
                    "cwd": "/home/alice/code/project",
                }
            },
            "unknown": {
                "details": {"workspaceHealth": "stale", "repo": None, "cwd": None}
            },
        }
        expected = {
            False: {"repo": "#a8d1bd", "dir": "#dac19d", "unknown": "#bbc2ca"},
            True: {"repo": "#315449", "dir": "#624d30", "unknown": "#464f5a"},
        }
        for light, colors in expected.items():
            for kind, row_data in examples.items():
                self.assertEqual(
                    _dashboard_workspace_color(row_data, light=light)[1], colors[kind]
                )
            prefix = _directory_prefix_color(light=light)[1]
            self.assertEqual(prefix, "#404b59" if light else "#b3bdc9")
        self.assertEqual(_directory_prefix_end("~/code/project", examples["dir"]), 7)
        self.assertIsNone(_directory_prefix_end("repository", examples["repo"]))
        self.assertIsNone(_directory_prefix_end("unknown", examples["unknown"]))

    def test_dashboard_identity_colors_reject_invalid_identity_and_ignore_hash_seed(self):
        for item in ({}, {"source": None}, {"source": {"host": "snap"}}):
            self.assertIsNone(_dashboard_host_color(item))
            self.assertIsNone(_dashboard_profile_color(item))
        script = (
            "from agent_observer.terminal.dashboard_palette import profile_color; "
            "print(profile_color({'source': {'host': 'snap', 'home': 'work'}}))"
        )
        values = [
            subprocess.check_output(
                [sys.executable, "-B", "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed},
            )
            for seed in ("11", "73")
        ]
        self.assertEqual(*values)


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardProfileColorTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_compact_and_split_profile_cells_keep_the_same_color(self):
        app = DashboardApp(FakeReader(samples()), {"group": "host-home"})
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()

            def check_full_rows():
                widths = app._column_widths(app.size.width - 4)
                profile_offset = 2 + sum(widths[:2])
                for item in app._all_rows:
                    widget = app._line_widgets[app._row_key(item)]
                    host = item["source"]["host"]
                    host_color = widget.content.get_style_at_offset(
                        app.console, profile_offset
                    ).color
                    self.assertEqual(host_color.name, _dashboard_host_color(item)[1])
                    self.assertEqual(
                        bool(
                            widget.content.get_style_at_offset(app.console, profile_offset).bold
                        ),
                        app._row_key(item) == app._selected_key,
                    )
                    if item["source"]["home"] != "default":
                        home_color = widget.content.get_style_at_offset(
                            app.console, profile_offset + len(host) + 1
                        ).color
                        self.assertEqual(home_color.name, _dashboard_profile_color(item)[1])
                    self.assertEqual(
                        widget.content.get_style_at_offset(app.console, 2).color.name, "green"
                    )
                    workspace_offset = 2 + sum(widths[:3])
                    workspace_text = widget.content.plain[
                        workspace_offset : workspace_offset + widths[3]
                    ].rstrip()
                    prefix_end = _directory_prefix_end(workspace_text, item)
                    expected_workspace = _dashboard_workspace_color(item)[1]
                    if prefix_end is None:
                        workspace_color = widget.content.get_style_at_offset(
                            app.console, workspace_offset
                        ).color
                        self.assertEqual(workspace_color.name, expected_workspace)
                    else:
                        prefix_color = widget.content.get_style_at_offset(
                            app.console, workspace_offset
                        ).color
                        component_color = widget.content.get_style_at_offset(
                            app.console, workspace_offset + prefix_end
                        ).color
                        self.assertEqual(
                            prefix_color.name,
                            _directory_prefix_color(light=not app.current_theme.dark)[1],
                        )
                        self.assertEqual(component_color.name, expected_workspace)

            check_full_rows()
            await pilot.press("down")
            check_full_rows()
            await pilot.resize_terminal(60, 16)
            await pilot.pause()

            def check_compact_rows():
                for _key, (age, _, item) in app._age_cells.items():
                    context = age.parent._context_line
                    profile = context.content
                    profile_offset = 6
                    self.assertEqual(
                        profile.get_style_at_offset(app.console, profile_offset).color.name,
                        _dashboard_host_color(item)[1],
                    )
                    if item["source"]["home"] != "default":
                        self.assertEqual(
                            profile.get_style_at_offset(
                                app.console, profile_offset + len(item["source"]["host"]) + 1
                            ).color.name,
                            _dashboard_profile_color(item)[1],
                        )
                    primary = age.content
                    self.assertEqual(
                        primary.get_style_at_offset(app.console, 2).color.name, "green"
                    )
                    workspace_offset = profile.plain.index(":") + 2
                    workspace_text = profile.plain[workspace_offset:].rstrip()
                    prefix_end = _directory_prefix_end(workspace_text, item)
                    workspace_color = _dashboard_workspace_color(item)[1]
                    if prefix_end is None:
                        self.assertEqual(
                            profile.get_style_at_offset(
                                app.console, workspace_offset
                            ).color.name,
                            workspace_color,
                        )
                    else:
                        self.assertEqual(
                            profile.get_style_at_offset(
                                app.console, workspace_offset
                            ).color.name,
                            _directory_prefix_color(light=not app.current_theme.dark)[1],
                        )
                        self.assertEqual(
                            profile.get_style_at_offset(
                                app.console, workspace_offset + prefix_end
                            ).color.name,
                            workspace_color,
                        )
                    rendered = context.render_line(0)
                    self.assertFalse(any(segment.style.bold for segment in rendered._segments if segment.text.strip()))

            check_compact_rows()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.resize_terminal(140, 36)
            await pilot.pause()
            self.assertTrue(app._split_details())
            check_compact_rows()

    async def test_directory_parent_span_tracks_visible_truncation_at_dashboard_widths(self):
        path = "/home/alice/projects/" + "long-final-directory-" * 8

        def directory_states():
            result = samples()
            for item_state in result:
                item_state["read"].members[0]["cwd"] = path
            return result

        for theme in ("textual-dark", "textual-light"):
            app = DashboardApp(FakeReader(directory_states()), {})
            app.theme = theme
            async with app.run_test(size=(100, 24)) as pilot:
                for width, height in ((32, 12), (60, 16), (100, 24)):
                    await pilot.resize_terminal(width, height)
                    await pilot.pause()
                    mode = "full" if width >= 100 else "compact"
                    for item in app._all_rows[:2]:
                        key = app._row_key(item)
                        for selected in (False, True):
                            with self.subTest(theme=theme, width=width, selected=selected):
                                app._selected_key = key if selected else ("no-selection",)
                                widget = app._session_widgets(item, 0, mode, width=app.size.width)[
                                    0
                                ]
                                if mode == "full":
                                    content = widget.content
                                    widths = app._column_widths(app.size.width - 4)
                                    workspace_start = 2 + sum(widths[:3])
                                    visible = content.plain[
                                        workspace_start : workspace_start + widths[3]
                                    ].rstrip()
                                else:
                                    content = widget._context_line.content
                                    workspace_start = content.plain.index(" : ") + 3
                                    visible = content.plain[workspace_start:].rstrip()

                                prefix_end = _directory_prefix_end(visible, item)
                                self.assertIsNotNone(prefix_end)
                                self.assertLess(prefix_end, len(visible))
                                prefix_style = content.get_style_at_offset(
                                    app.console, workspace_start
                                )
                                component_style = content.get_style_at_offset(
                                    app.console, workspace_start + prefix_end
                                )
                                light = theme == "textual-light"
                                self.assertEqual(
                                    prefix_style.color.name,
                                    _directory_prefix_color(light=light)[1],
                                )
                                self.assertEqual(
                                    component_style.color.name,
                                    _dashboard_workspace_color(item, light=light)[1],
                                )
                                if mode == "full":
                                    self.assertEqual(bool(prefix_style.bold), selected)
                                    self.assertEqual(bool(component_style.bold), selected)
                                else:
                                    self.assertFalse(prefix_style.bold)
                                    self.assertFalse(component_style.bold)

        app = DashboardApp(FakeReader(directory_states()), {}, no_color=True)
        async with app.run_test(size=(100, 24)) as pilot:
            for width, height in ((32, 12), (60, 16), (100, 24)):
                await pilot.resize_terminal(width, height)
                await pilot.pause()
                mode = "full" if width >= 100 else "compact"
                for item in app._all_rows[:2]:
                    key = app._row_key(item)
                    for selected in (False, True):
                        app._selected_key = key if selected else ("no-selection",)
                        widget = app._session_widgets(item, 0, mode, width=app.size.width)[0]
                        if mode == "full":
                            content = widget.content
                            widths = app._column_widths(app.size.width - 4)
                            workspace_start = 2 + sum(widths[:3])
                            visible = content.plain[
                                workspace_start : workspace_start + widths[3]
                            ].rstrip()
                        else:
                            content = widget._context_line.content
                            workspace_start = content.plain.index(" : ") + 3
                            visible = content.plain[workspace_start:].rstrip()
                        prefix_end = _directory_prefix_end(visible, item)
                        self.assertIsNotNone(prefix_end)
                        self.assertLess(prefix_end, len(visible))
                        self.assertIsNone(
                            content.get_style_at_offset(app.console, workspace_start).color
                        )
                        self.assertIsNone(
                            content.get_style_at_offset(
                                app.console, workspace_start + prefix_end
                            ).color
                        )

    async def test_session_line_path_style_survives_selection_adoption_and_age_updates(self):
        app = DashboardApp(FakeReader(samples()), {})
        app.theme = "textual-dark"
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            item = app._all_rows[0]
            item["details"].update(
                workspaceHealth="current",
                repo=None,
                cwd="/home/alice/projects/long-directory-name",
            )
            key = app._row_key(item)
            app._selected_key = key
            line = app._session_widgets(item, 0, "full", width=100)[0]
            workspace_start = 2 + sum(app._column_widths(96)[:3])
            self.assertEqual(line._workspace_prefix_style, "#b3bdc9")

            line.select_row(False)
            line.update_age("9m")
            self.assertEqual(
                line.content.get_style_at_offset(app.console, workspace_start).color.name,
                "#b3bdc9",
            )

            app.theme = "textual-light"
            candidate = app._session_widgets(item, 0, "full", width=100)[0]
            line.adopt_row(candidate)
            self.assertEqual(line._workspace_prefix_style, "#404b59")
            line.select_row(True)
            line.update_age("10m")
            self.assertEqual(
                line.content.get_style_at_offset(app.console, workspace_start).color.name,
                "#404b59",
            )

    async def test_rendered_selection_surface_is_single_layer_in_all_layouts_and_themes(self):
        layouts = (
            (100, 24, False),
            (99, 24, False),
            (80, 24, False),
            (60, 16, False),
            (40, 16, False),
            (32, 12, False),
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
                        full_table = size >= 100 and not split
                        selected = (
                            app._line_widgets[key]
                            if full_table
                            else app._age_cells[key][0].parent
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
                            unselected = app._age_cells[unselected_key][0].parent
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
                            context = selected._context_line
                            for y in range(context.region.y, context.region.bottom):
                                offset = 0
                                for segment in strips[y]._segments:
                                    segment_width = cell_len(segment.text)
                                    if (
                                        segment.text.strip()
                                        and offset < context.region.right
                                        and offset + segment_width > context.region.x
                                    ):
                                        self.assertFalse(segment.style.bold)
                                    offset += segment_width

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
                        else:
                            primary = selected._primary_line
                            context = selected._context_line
                            activity_age = app._age_cells[key][1]
                            age_offset = cell_len(primary.content.plain[: primary.content.plain.rfind(activity_age)])
                            context_text = context.content.plain
                            host_offset = 6
                            workspace_offset = context_text.index(":") + 2
                            palette_points = [
                                ("age", primary.region.x + age_offset, primary.region.y),
                                ("host", context.region.x + host_offset, context.region.y),
                                (
                                    "workspace",
                                    context.region.x + workspace_offset,
                                    context.region.y,
                                ),
                            ]
                            if item["source"]["home"] != "default":
                                palette_points.insert(
                                    2,
                                    (
                                        "profile",
                                        context.region.x + host_offset + len(item["source"]["host"]) + 1,
                                        context.region.y,
                                    ),
                                )
                            status_point = ("status", primary.region.x + 2, primary.region.y)

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
                                palette_colors.append(_dashboard_host_color(identity, light=light)[1])
                                palette_colors.append(_dashboard_profile_color(identity, light=light)[1])
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
                            palette_colors.append(
                                _dashboard_workspace_color(workspace, light=light)[1]
                            )
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
        async with app.run_test(size=(100, 24)) as pilot:
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
                context = age.parent._context_line
                profile = context.content
                style = profile.get_style_at_offset(app.console, 6)
                self.assertIsNone(style.color)
                self.assertTrue(style.italic)
                if key == app._selected_key:
                    self.assertFalse(style.reverse)
                    self.assertFalse(style.bold)
            await pilot.resize_terminal(32, 12)
            await pilot.pause()
            compact_row = app._age_cells[app._selected_key][0].parent
            profile = compact_row._context_line.content
            style = profile.get_style_at_offset(app.console, 6)
            self.assertIsNone(style.color)
            self.assertTrue(style.italic)
            self.assertFalse(style.reverse)
            self.assertFalse(style.bold)
            marker_style = compact_row._primary_line.content.get_style_at_offset(app.console, 0)
            self.assertTrue(marker_style.reverse)
