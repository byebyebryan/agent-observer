"""Review terminal width and grouping with synthetic admitted metadata."""

import json
import re
import unicodedata
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.model import enrich_repository_presentation
from agent_observer.terminal.render import (
    _compact_cwd,
    _last_active_text,
    _main_column_widths,
    _status_label,
    _status_text,
    _workspace_color,
    _workspace_kind,
    _workspace_text,
    color_enabled,
    icons_enabled,
    light_background,
    render,
)

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
    def test_explicit_light_background_hint_and_palette_keep_plain_output_identical(self):
        self.assertTrue(light_background(environ={"COLORFGBG": "0;15"}))
        self.assertTrue(light_background(environ={"COLORFGBG": "0;default;7"}))
        for value in ("", "15;0", "garbage", "0;999", None):
            self.assertFalse(light_background(environ={"COLORFGBG": value}))
        item = row("light-palette")
        document = report([state(current_read=read(rows=[item], leases=[lease("light-palette")]))])
        for mode in ("overview", "list"):
            for width in (60, 140):
                light = render(document, mode=mode, color=True, light=True, width=width)
                dark = render(document, mode=mode, color=True, width=width)
                plain = render(document, mode=mode, width=width)
                self.assertNotEqual(light, dark)
                self.assertEqual(SGR.sub("", light), plain)
                self.assertEqual(render(document, mode=mode, light=True, width=width), plain)
                self.assertIn("\x1b[38;2;128;69;0m", light)
        from agent_observer.terminal.cli import _emit

        output = []
        tty = SimpleNamespace(isatty=lambda: True, encoding="utf-8")
        args = SimpleNamespace(format="text", color="always", icons="never")
        with (
            patch("agent_observer.terminal.cli.sys.stdout", tty),
            patch("agent_observer.terminal.cli.write_stdout", output.append),
            patch.dict("os.environ", {"COLORFGBG": "0;15", "NO_COLOR": ""}),
        ):
            self.assertEqual(_emit(document, args, "overview"), 0)
        self.assertIn("\x1b[38;2;128;69;0m", output[0])

    def test_home_workspace_shorthand_preserves_reported_paths_and_json(self):
        for value, expected in (
            ("/home/alice", "~"),
            ("/home/remote-user/code/widget", "~/code/widget"),
            ("/home/alice/projects/界面", "~/projects/界面"),
            ("/home", "/home"),
            ("/home/../widget", "…/widget"),
            ("/opt/projects/widget", "…/widget"),
        ):
            with self.subTest(value=value):
                self.assertEqual(_compact_cwd(value), expected)
        item = row("home-path", title="Workspace review")
        item["cwd"] = "/home/remote-user/code/widget"
        document = report([state(current_read=read(rows=[item], leases=[lease("home-path")]))])
        before = json.dumps(document, sort_keys=True)
        for width in (32, 60, 110):
            with self.subTest(width=width):
                text = render(document, width=width)
                self.assertIn("~/code/widget", text)
                self.assertNotIn(item["cwd"], text)
        self.assertEqual(document["sessions"][0]["details"]["cwd"], item["cwd"])
        self.assertEqual(json.dumps(document, sort_keys=True), before)

    def test_status_colors_survive_padding_in_the_wide_table(self):
        items = [row(f"id-{index}", title=f"Task {index}") for index in range(3)]
        for item, phase in zip(items, ("working", "waiting", "blocked"), strict=True):
            item["phase"]["value"] = phase
        document = report(
            [state(current_read=read(rows=items, leases=[lease(item["identity"]["nativeId"]) for item in items]))]
        )
        colored = render(document, width=140, color=True, icons=True)
        self.assertIn("\x1b[32m● Working\x1b[0m", colored)
        self.assertIn("\x1b[36m○ Ready\x1b[0m", colored)
        self.assertIn("\x1b[33m! Blocked\x1b[0m", colored)
        self.assertEqual(SGR.sub("", colored), render(document, width=140, icons=True))

    def test_long_workspace_uses_compact_rows_without_splitting_identifiers(self):
        item = row("full-id", title="Review the observer CLI layout")
        item["cwd"] = "/reported/worktrees/agent-observer-feature"
        document = report([state(current_read=read(rows=[item], leases=[lease("full-id")]))])
        before = json.dumps(document, sort_keys=True)
        text = render(document, width=80, icons=True)
        title_line = next(line for line in text.splitlines() if item["title"] in line)
        self.assertIn("Working", title_line)
        self.assertRegex(title_line, r"Working\s+\d+[smhd]")
        context_line = next(line for line in text.splitlines() if "fixture/default" in line)
        self.assertIn("…/agent-observer-feature", context_line)
        self.assertIn("agent-observer-feature", context_line)
        self.assertTrue(all(screen_width(line) <= 80 for line in text.splitlines()))
        self.assertNotIn("\x1b", render(document, width=80))
        self.assertEqual(json.dumps(document, sort_keys=True), before)

    def test_finite_rows_keep_field_priority_across_responsive_widths(self):
        item = row("layout-id", title="Renderer review")
        document = report(
            [state(current_read=read(rows=[item], leases=[lease("layout-id")]))]
        )

        widths = _main_column_widths(document["sessions"], 1_000, 100, False)
        self.assertIsNotNone(widths)
        self.assertEqual(len(widths), 4)
        self.assertGreaterEqual(widths[1], 28)
        full = render(document, mode="list", width=100)
        header = next(line for line in full.splitlines() if line.startswith("Status"))
        for left, right in zip(
            ("Status", "Session", "Profile"),
            ("Session", "Profile", "Workspace"),
            strict=True,
        ):
            self.assertLess(header.index(left), header.index(right))

        compact = render(document, mode="list", width=80).splitlines()
        session_heading = next(line for line in compact if line.startswith("STATUS"))
        workspace_heading = next(line for line in compact if line.startswith("PROFILE"))
        session_x = session_heading.index("SESSION")
        workspace_x = workspace_heading.index("WORKSPACE")
        self.assertEqual(session_x, workspace_x)
        title_index = next(index for index, line in enumerate(compact) if "Renderer review" in line)
        self.assertIn("Working", compact[title_index])
        self.assertRegex(compact[title_index], r"Working\s+\d+[smhd]")
        self.assertEqual(compact[title_index].index("Renderer review"), session_x)
        self.assertIn("fixture/default", compact[title_index + 1])
        self.assertEqual(compact[title_index + 1].index("…/workspace"), workspace_x)

        stacked = render(document, mode="list", width=32).splitlines()
        title_index = next(index for index, line in enumerate(stacked) if line == "Renderer review")
        self.assertIn("Working", stacked[title_index - 1])
        self.assertRegex(stacked[title_index - 1], r"Working\s+\d+[smhd]")
        self.assertEqual(stacked[title_index + 1], "fixture/default")
        self.assertIn("workspace", stacked[title_index + 2])

    def test_full_table_fits_unavailable_status_and_age_at_100_columns(self):
        item = row("boundary-id", title="Boundary task")
        item["runtime"].update(value="unknown", health="unavailable", reason="read_unavailable")
        item["activity"].update(at=None, health="unavailable", reason="read_unavailable")
        document = report([state(current_read=read(rows=[item], leases=[lease("boundary-id")]))])

        for width in (100, 106):
            for icons in (False, True):
                with self.subTest(width=width, icons=icons):
                    text = render(document, width=width, icons=icons)
                    heading = next(line for line in text.splitlines() if line.startswith("Status"))
                    for field in ("Session", "Profile", "Workspace"):
                        self.assertIn(field, heading)
                    entry = next(line for line in text.splitlines() if "Boundary task" in line)
                    self.assertEqual(entry.count("Unavailable"), 2)
                    self.assertIn("fixture/default", entry)
                    self.assertIn("workspace", entry)
                    self.assertTrue(all(screen_width(line) <= width for line in text.splitlines()))
                    colored = render(document, width=width, color=True, icons=icons)
                    self.assertEqual(SGR.sub("", colored), text)

    def test_medium_grid_shares_column_edges_and_right_aligns_mixed_ages(self):
        active = row("medium-active", title="Active medium task")
        unavailable = row("medium-unavailable", title="Unavailable medium task")
        unavailable["activity"].update(health="unavailable", at=None, reason="read_unavailable")
        document = report(
            [
                state(
                    current_read=read(
                        rows=[active, unavailable],
                        leases=[lease("medium-active"), lease("medium-unavailable")],
                    )
                )
            ]
        )

        for mode in ("overview", "list"):
            for width in (60, 80, 99):
                with self.subTest(mode=mode, width=width):
                    lines = render(document, mode=mode, width=width, icons=True).splitlines()
                    session_heading = next(
                        line for line in lines if line.startswith("STATUS")
                    )
                    workspace_heading = next(
                        line for line in lines if line.startswith("PROFILE")
                    )
                    right_edge = session_heading.index("SESSION")
                    self.assertEqual(workspace_heading.index("WORKSPACE"), right_edge)
                    title_lines = [line for line in lines if " medium task" in line]
                    workspace_lines = [line for line in lines if "workspace" in line]
                    self.assertEqual(len(title_lines), 2)
                    self.assertEqual(len(workspace_lines), 2)
                    for line in title_lines:
                        title = (
                            "Active medium task"
                            if "Active medium task" in line
                            else "Unavailable medium task"
                        )
                        self.assertEqual(line.index(title), right_edge)
                        status_age = line[:right_edge].rstrip()
                        age = re.search(r"(?:Unavailable|\d+[smhd]+)$", status_age)
                        self.assertIsNotNone(age)
                        self.assertEqual(age.end(), right_edge - 1)
                    for line in workspace_lines:
                        self.assertEqual(line.index("…/workspace"), right_edge)
                    self.assertTrue(all(screen_width(line) <= width for line in lines))

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
        for width in (32, 40, 59, 60, 80, 99, 100, 106, 110, 120, 180):
            for mode in ("overview", "list", "show", "sources"):
                for color, icons in ((False, False), (True, True), (False, True)):
                    with self.subTest(width=width, mode=mode, color=color, icons=icons):
                        text = render(document, mode=mode, color=color, icons=icons, width=width)
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
        text = render(document, width=120)
        self.assertIn("12 sessions total", text)
        self.assertIn("10 shown / 12 matching", text)
        self.assertIn("1/1 sources complete", text)
        self.assertNotIn("Showing 10 of 12", text)
        for member in document["sessions"]:
            matching = [
                line
                for line in text.splitlines()
                if re.search(re.escape(member["label"]) + r"(?:\s|$)", line)
            ]
            self.assertEqual(len(matching), 1)
            self.assertIn("Working", matching[0])
            self.assertRegex(matching[0], r"Working\s+\d+[smhd]")
            self.assertIn("fixture/default", matching[0])
            self.assertNotIn(member["identity"]["nativeId"], text)
        self.assertTrue(all(screen_width(line) <= 120 for line in text.splitlines()))
        full = render(report(states), mode="list")
        for member in members:
            self.assertIn(member["identity"]["nativeId"], full)
        self.assertIn("fixture-project", full)
        header = next(line for line in full.splitlines() if line.startswith("Status"))
        self.assertIn("Status", header)
        self.assertNotIn("Last active", header)
        self.assertLess(header.index("Status"), header.index("Session"))
        self.assertLess(header.index("Session"), header.index("Profile"))
        self.assertLess(header.index("Profile"), header.index("Workspace"))
        id_lines = [line for line in full.splitlines() if line.startswith("  id: ")]
        self.assertEqual(len(id_lines), len(members))
        self.assertEqual(_status_label("Working", True), "● Working")
        self.assertEqual(_status_label("Ready", True), "○ Ready")
        self.assertEqual(_status_label("Blocked", True), "! Blocked")
        self.assertEqual(_status_label("Unavailable", True), "× Unavailable")

    def test_show_leads_with_human_summary_then_keeps_full_diagnostics_and_source_health(self):
        member = row("show-full-thread-id", title="Review the renderer rollout")
        member["cwd"] = "/home/remote-user/worktrees/topic/src"
        member["workspace"]["repo"] = {
            "root": "/synthetic/worktrees/topic",
            "commonDir": "/synthetic/repositories/shared.git",
            "relativePath": "src",
        }
        healthy_state = state(
            current_read=read(rows=[member], leases=[lease("show-full-thread-id")])
        )
        failed_state = state(
            source("offline-work", host="offline", home="work"),
            current_read=None,
            lifecycle="failed",
            baseline=False,
            reason="transport_failure",
        )
        document = report(
            [healthy_state, failed_state], mode="show", target="show-full-thread-id"
        )
        enrich_repository_presentation(document, [healthy_state, failed_state], now_boottime_ms=1_000)

        plain = render(document, mode="show")
        lines = plain.splitlines()
        divider = lines.index("Diagnostics")
        self.assertEqual(lines[0], "Review the renderer rollout")
        self.assertIn("Status: Working · Activity: approx.", lines[1])
        self.assertIn("ago", lines[1])
        self.assertEqual(lines[2], "Profile: fixture/default")
        self.assertEqual(lines[3], "Workspace: topic")
        self.assertEqual(lines[4], "ID: show-full-thread-id")
        self.assertLess(4, divider)
        self.assertIn("Identity: fixture/codex/" + "sha256:" + "a" * 64 + "/thread_id/show-full-thread-id", plain)
        self.assertIn("Runtime: running (current; reason=native)", plain)
        self.assertIn("Phase: working (current; reason=native)", plain)
        self.assertIn("Path: /home/remote-user/worktrees/topic/src", plain)
        self.assertIn("Repository: root=/synthetic/worktrees/topic", plain)
        self.assertIn("Field leases (receiving CLOCK_BOOTTIME):", plain)
        self.assertIn("Source diagnostics:", plain)
        self.assertIn("Binding: id=fixture-default host=fixture home=default", plain)
        self.assertIn("Source clock: CLOCK_BOOTTIME bootId=fixture-boot", plain)
        self.assertIn("Frame/capture CLOCK_BOOTTIME: lastFrame=1000 capture=1000", plain)
        self.assertIn("Scope: fixture/codex/sha256:", plain)
        self.assertIn("offline/Work [offline-work]: unavailable", plain)
        self.assertIn("reason=transport_failure", plain)
        self.assertNotIn("\x1b", plain)

        styled = render(document, mode="show", color=True, icons=True, width=120)
        self.assertIn("\x1b[1;36mReview the renderer rollout\x1b[0m", styled)
        self.assertIn("\x1b[32m● Working\x1b[0m", styled)
        self.assertEqual(SGR.sub("", styled), render(document, mode="show", icons=True, width=120))

        for width in (32, 60, 80, 110, 120):
            with self.subTest(width=width):
                wrapped = render(document, mode="show", width=width)
                self.assertTrue(all(screen_width(line) <= width for line in wrapped.splitlines()))
                self.assertIn("show-full-thread-id", wrapped)

    def test_unresolved_show_qualifies_membership_and_never_invents_runtime_status(self):
        unresolved = read(
            uncertain=[
                {
                    "identity": row("unresolved-thread")["identity"],
                    "reason": "membership_unresolved",
                }
            ]
        )
        document = report(
            [state(current_read=unresolved)], mode="show", target="unresolved-thread"
        )
        text = render(document, mode="show", width=80)
        summary = text.split("Diagnostics", maxsplit=1)[0]
        self.assertIn("Membership: uncertain · Status: Unknown (not established by membership)", summary)
        self.assertIn("Profile: fixture/default", summary)
        self.assertIn("Workspace: unknown", summary)
        self.assertIn("ID: unresolved-thread", summary)
        self.assertNotIn("Working", summary)
        self.assertNotIn("Inactive", summary)
        self.assertIn("Reason: membership_unresolved", text)
        self.assertIn("Source diagnostics:", text)
        self.assertIn("fixture/Default", text)

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
        self.assertIn("1 session total", text)
        self.assertIn("0 shown / 0 matching", text)
        self.assertIn("1/2 sources complete", text)
        self.assertIn("offline/Work: unavailable", text)
        self.assertIn("host transport is unavailable", text)
        self.assertIn("No rows match the filters", text)
        self.assertNotIn("complete current coverage", text)

        complete_empty = render(
            report([state(current_read=read())], mode="overview"), width=80
        )
        self.assertIn("Complete current coverage contains no session outcomes.", complete_empty)
        known_nonmember = read(
            nonmembers=[
                {
                    "identity": row("known-nonmember")["identity"],
                    "reason": "known_nonmember",
                }
            ]
        )
        nonmember_text = render(
            report([state(current_read=known_nonmember)], mode="overview"), width=80
        )
        self.assertIn("No qualifying member rows; known nonmembers remain separately classified.", nonmember_text)
        self.assertIn("1 known nonmembers", nonmember_text)

        stale_member = row("stale-id", title="Stale session")
        stale_member["runtime"].update(value="running", health="current")
        stale_member["phase"].update(value="unknown", health="unavailable")
        stale_member["activity"].update(at=None, health="stale", lastKnownAt=950)
        stale = report(
            [state(current_read=read(rows=[stale_member], leases=[lease("stale-id")]))],
            mode="overview",
        )
        for width in (40, 80, 120):
            text = render(stale, width=width)
            self.assertIn("Unavailable", text)
            self.assertIn("Stale", text)
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
        self.assertEqual(text.count("[alpha/default]"), 1)
        self.assertEqual(text.count("[bravo/default]"), 1)

    def test_no_color_and_pipes_override_terminal_color_requests(self):
        self.assertFalse(color_enabled("always", environ={"NO_COLOR": "1"}, isatty=True))
        self.assertFalse(color_enabled("always", environ={}, isatty=False))
        self.assertFalse(color_enabled("auto", environ={"TERM": "dumb"}, isatty=True))
        self.assertTrue(color_enabled("auto", environ={"TERM": "xterm"}, isatty=True))

    def test_icons_fall_back_for_pipes_basic_terminals_and_unsupported_encodings(self):
        self.assertTrue(icons_enabled("auto", environ={"TERM": "xterm"}, isatty=True))
        self.assertFalse(icons_enabled("always", environ={}, isatty=False))
        self.assertFalse(icons_enabled("auto", environ={"TERM": "dumb"}, isatty=True))
        self.assertFalse(icons_enabled("never", environ={}, isatty=True))
        for encoding in (None, "ascii", "invalid-encoding"):
            self.assertFalse(icons_enabled("auto", isatty=True, encoding=encoding))
        self.assertTrue(icons_enabled("auto", environ={"NO_COLOR": "1"}, isatty=True))

    def test_status_labels_keep_unknown_facts_conservative_and_readable_without_color(self):
        member = row("exact-id", title="Session")
        member["runtime"].update(value="unknown", health="stale", lastKnownValue="running")
        member["phase"].update(value="unknown", health="stale", lastKnownValue="working")
        document = report(
            [state(current_read=read(rows=[member], leases=[lease("exact-id")]))],
            mode="overview",
        )
        plain = render(document, icons=True, width=80)
        self.assertIn("Stale", plain)
        self.assertNotIn("● working", plain)
        self.assertNotIn("running", plain)
        self.assertNotIn("\x1b", plain)
        styled = render(document, color=True, icons=True, width=80)
        self.assertIn("Stale", styled)
        self.assertEqual(SGR.sub("", styled), plain)

    def test_status_is_current_runtime_then_phase_not_membership(self):
        item = row("status-id")
        self.assertEqual(_status_text(item), "Working")

        item["runtime"].update(value="parked", health="current")
        item["phase"].update(value="waiting", health="current")
        self.assertEqual(_status_text(item), "Inactive")

        item["membership"] = "recent"
        item["runtime"].update(value="unknown", health="current")
        item["phase"].update(value="working", health="current")
        self.assertEqual(_status_text(item), "Unknown")

        item["runtime"].update(value="unknown", health="unavailable")
        self.assertEqual(_status_text(item), "Unavailable")

        item["runtime"].update(value="running", health="current")
        item["phase"].update(value="working", health="stale")
        self.assertEqual(_status_text(item), "Stale")
        item["phase"].update(value="unknown", health="unavailable")
        self.assertEqual(_status_text(item), "Unavailable")
        item["phase"].update(value="unknown", health="unsupported")
        self.assertEqual(_status_text(item), "Unknown")

        item["membership"] = "recent"
        item["phase"].update(value="waiting", health="current")
        self.assertEqual(_status_text(item), "Ready")

    def test_activity_age_is_independent_and_workspace_falls_back_without_reusing_stale_repo(self):
        item = row("status-id")
        item["runtime"].update(value="parked", health="current")
        item["phase"].update(value="waiting", health="current")
        self.assertEqual(_status_text(item), "Inactive")
        self.assertEqual(_last_active_text(item, 1_000), "1s")

        item["details"] = {
            "workspaceHealth": "current",
            "repo": {"root": "/synthetic/worktrees/topic-feature"},
            "cwd": "/reported/elsewhere/src",
        }
        self.assertEqual(_workspace_kind(item), "repo")
        self.assertEqual(_workspace_text(item), "topic-feature")
        self.assertEqual(_workspace_color(item), ("38;2;85;215;175", "#55d7af"))
        self.assertEqual(_workspace_color(item, light=True), ("38;2;0;93;73", "#005d49"))
        item["details"]["workspaceHealth"] = "stale"
        self.assertEqual(_workspace_kind(item), "dir")
        self.assertEqual(_workspace_text(item), "…/src")
        self.assertEqual(_workspace_color(item), ("38;2;240;181;111", "#f0b56f"))
        self.assertEqual(_workspace_color(item, light=True), ("38;2;128;69;0", "#804500"))
        item["details"]["cwd"] = None
        self.assertEqual(_workspace_kind(item), "unknown")
        self.assertEqual(_workspace_text(item), "unknown")
        self.assertEqual(_workspace_color(item, light=True), ("38;2;75;83;94", "#4b535e"))

        item["activity"].update(at=None, health="stale", lastKnownAt=950)
        self.assertEqual(_last_active_text(item, 1_000), "Stale")
