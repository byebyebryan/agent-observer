"""Review terminal width and grouping with synthetic admitted metadata."""

import json
import re
import unicodedata
import unittest

from test_terminal_model import lease, read, report, row, source, state

from agent_observer.terminal.render import (
    _last_active_text,
    _status_label,
    _status_text,
    _workspace_text,
    color_enabled,
    icons_enabled,
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
        self.assertIn("~", title_line)
        context_line = next(line for line in text.splitlines() if "fixture/default" in line and "·" in line)
        self.assertIn("agent-observer-feature", context_line)
        self.assertTrue(all(screen_width(line) <= 80 for line in text.splitlines()))
        self.assertEqual(json.dumps(document, sort_keys=True), before)

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
        text = render(document, width=80)
        self.assertIn("12 sessions", text)
        self.assertIn("1/1 sources complete", text)
        self.assertIn("Showing 10 of 12 matches.", text)
        for member in document["sessions"]:
            matching = [
                line
                for line in text.splitlines()
                if re.search(re.escape(member["label"]) + r"(?:\s|$)", line)
            ]
            self.assertEqual(len(matching), 1)
            self.assertIn("Working", matching[0])
            self.assertIn("~", matching[0])
            self.assertIn("fixture/default", matching[0])
            self.assertNotIn(member["identity"]["nativeId"], text)
        self.assertTrue(all(screen_width(line) <= 80 for line in text.splitlines()))
        full = render(report(states), mode="list")
        for member in members:
            self.assertIn(member["identity"]["nativeId"], full)
        self.assertIn("fixture-project", full)
        header = next(line for line in full.splitlines() if line.startswith("Status"))
        self.assertLess(header.index("Status"), header.index("Last active"))
        self.assertLess(header.index("Last active"), header.index("Session"))
        self.assertLess(header.index("Session"), header.index("Profile"))
        self.assertLess(header.index("Profile"), header.index("Workspace"))
        id_lines = [line for line in full.splitlines() if line.startswith("  id: ")]
        self.assertEqual(len(id_lines), len(members))
        self.assertEqual(_status_label("Working", True), "● Working")
        self.assertEqual(_status_label("Ready", True), "○ Ready")
        self.assertEqual(_status_label("Blocked", True), "! Blocked")
        self.assertEqual(_status_label("Unavailable", True), "× Unavailable")

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
        self.assertEqual(_last_active_text(item, 1_000), "~1s")

        item["details"] = {
            "workspaceHealth": "current",
            "repo": {"root": "/synthetic/worktrees/topic-feature"},
            "cwd": "/reported/elsewhere/src",
        }
        self.assertEqual(_workspace_text(item), "topic-feature")
        item["details"]["workspaceHealth"] = "stale"
        self.assertEqual(_workspace_text(item), "…/src")
        item["details"]["cwd"] = None
        self.assertEqual(_workspace_text(item), "unknown")

        item["activity"].update(at=None, health="stale", lastKnownAt=950)
        self.assertEqual(_last_active_text(item, 1_000), "Stale")
