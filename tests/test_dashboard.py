"""Headless dashboard behavior over the maintained terminal projection model."""

from __future__ import annotations

import asyncio
import importlib.util
import unittest
from types import SimpleNamespace

from test_terminal_model import identity, lease, read, report, row, source, state

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from agent_observer.terminal.dashboard import DashboardApp


class FakeReader:
    """Small synchronous facade stand-in; no Mesh, provider, or native calls."""

    def __init__(self, states):
        self.states = list(states)
        self.slots = [SimpleNamespace(source=item["config"]) for item in states]
        self.changed = asyncio.Event()
        self.revision = 1
        self.priority_revision = 1
        self.retry_calls = []
        self.stages = {item["config"]["id"]: "observing" for item in states}
        self._owner = object()
        self.revoke_on_next_fence = None

    def projection(self, filters, *, mode="list", target=None):
        return SimpleNamespace(
            owner=self._owner,
            revision=self.revision,
            priority_revision=self.priority_revision,
            report=report(
                self.states,
                mode=mode,
                filters=filters,
                target=target,
                include_repository=True,
            ),
        )

    def is_current(self, projection):
        if self.revoke_on_next_fence is not None:
            states = self.revoke_on_next_fence
            self.revoke_on_next_fence = None
            self.replace(states)
        return projection.owner is self._owner and projection.revision == self.revision

    def status(self):
        return [
            {
                "id": item["config"]["id"],
                "stage": self.stages.get(item["config"]["id"], "observing"),
                "epoch": self.revision,
                "attempts": 1,
                "retryAtBoottimeMs": None,
                "reason": item.get("reason"),
            }
            for item in self.states
        ]

    def requires_priority_refresh(self, projection):
        return projection is None or projection.priority_revision != self.priority_revision

    def refresh_due(self):
        return None

    def retry(self, source_id):
        self.retry_calls.append(source_id)
        return source_id in self.stages and self.stages[source_id] in {"blocked", "retry-wait"}

    def replace(self, states, *, priority=True):
        self.states = list(states)
        self.slots = [SimpleNamespace(source=item["config"]) for item in states]
        self.revision += 1
        if priority:
            self.priority_revision += 1
        self.changed.set()


def _session_state(source_config=None, *, rows=(), ids=(), lifecycle="observing", baseline=True):
    config = source() if source_config is None else source_config
    return state(
        config,
        current_read=read(
            rows=list(rows),
            leases=[lease(native_id, host=config["host"]) for native_id in ids],
            host=config["host"],
        ),
        lifecycle=lifecycle,
        baseline=baseline,
    )


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_stop_blocks_reader_wakeup_and_async_stop_still_joins_tasks(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            projection_count = 0
            original_projection = reader.projection

            def count_projection(*args, **kwargs):
                nonlocal projection_count
                projection_count += 1
                return original_projection(*args, **kwargs)

            reader.projection = count_projection
            existing_projections = projection_count
            reader._priority_checks = 0
            original_priority_check = reader.requires_priority_refresh

            def count_priority_checks(projection):
                reader._priority_checks += 1
                return original_priority_check(projection)

            reader.requires_priority_refresh = count_priority_checks
            app._projection_requested = True
            app._search_timer = app.set_timer(60, app._debounced_search_update)
            app._projection_timer = app.set_timer(60, app._run_queued_projection)
            app._render_timer = app.set_timer(60, app._paint)
            owned_tasks = tuple(app._update_tasks)

            app.request_stop_updates()
            self.assertTrue(app._updates_stopped)
            self.assertIsNone(app._search_timer)
            self.assertIsNone(app._projection_timer)
            self.assertIsNone(app._render_timer)
            self.assertFalse(app._projection_requested)
            self.assertTrue(all(not task.done() for task in owned_tasks))

            reader.replace([_session_state(lifecycle="failed", baseline=False)])
            await asyncio.wait_for(owned_tasks[0], 1)
            self.assertEqual(reader._priority_checks, 0)
            self.assertEqual(projection_count, existing_projections)

            await app.stop_updates()
            self.assertTrue(all(task.done() for task in owned_tasks))
            self.assertEqual(app._update_tasks, [])

    async def test_quit_stop_and_reader_wakeup_fence_pending_paint_resume(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            container = app.query_one("#content")
            original_remove = container.remove_children
            original_mount = container.mount
            removal_started = asyncio.Event()
            release_removal = asyncio.Event()
            mount_calls = []

            async def delayed_remove():
                removal_started.set()
                await release_removal.wait()
                return await original_remove()

            async def track_mount(*children, **kwargs):
                mount_calls.append(len(children))
                return await original_mount(*children, **kwargs)

            container.remove_children = delayed_remove
            container.mount = track_mount
            paint_task = asyncio.create_task(app._paint_pending())
            try:
                await asyncio.wait_for(removal_started.wait(), 1)
                self.assertFalse(container.display)
                app.request_stop_updates()
                reader.replace([_session_state(lifecycle="failed", baseline=False)])
                reader_task = app._update_tasks[0]
                await asyncio.wait_for(reader_task, 1)
            finally:
                release_removal.set()
            await asyncio.wait_for(paint_task, 1)
            self.assertFalse(container.display)
            self.assertEqual(mount_calls, [])

            owned_tasks = tuple(app._update_tasks)
            await app.stop_updates()
            self.assertTrue(all(task.done() for task in owned_tasks))

    async def test_revoked_facts_are_hidden_while_widget_removal_is_blocked(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            container = app.query_one("#content")
            remove_children = container.remove_children
            removal_started = asyncio.Event()
            release_removal = asyncio.Event()

            async def delayed_removal():
                removal_started.set()
                await release_removal.wait()
                return await remove_children()

            container.remove_children = delayed_removal
            reader.replace([_session_state(lifecycle="failed", baseline=False)])
            try:
                await asyncio.wait_for(removal_started.wait(), 1)
                # Revocation must withdraw visible authority before waiting for
                # framework unmount/remount work, which can exceed the budget.
                self.assertFalse(container.display)
                self.assertNotIn("1 members", str(app.query_one("#header").render()))
            finally:
                release_removal.set()
            await pilot.pause()
            self.assertTrue(container.display)
            self.assertEqual(app._all_rows, [])
            self.assertFalse(app._selection_available)

    async def test_pending_view_cannot_adopt_facts_arriving_during_unmount(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.stop_updates()
            # Keep the asynchronous update loops joined while exercising the
            # pending renderer directly as an isolated UI operation.
            app._updates_stopped = False
            container = app.query_one("#content")
            remove_children = container.remove_children

            async def update_during_removal():
                await remove_children()
                reader.replace([_session_state(rows=[row("bravo")], ids=["bravo"])])
                app._refresh_projection()

            container.remove_children = update_during_removal
            await app._paint_pending()
            self.assertTrue(reader.is_current(app._projection))
            self.assertEqual(app._line_widgets, {})
            self.assertIsNone(app._content_signature_value)
            self.assertTrue(container.display)

    async def test_last_age_update_cannot_unhide_a_revoked_projection(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.stop_updates()
            app._updates_stopped = False
            refresh_ages = app._refresh_age_cells

            def revoke_after_ages():
                refresh_ages()
                reader.replace([_session_state(lifecycle="failed", baseline=False)])

            app._refresh_age_cells = revoke_after_ages
            await app._paint()
            self.assertEqual(app._line_widgets, {})
            self.assertIsNone(app._content_signature_value)
            self.assertTrue(app.query_one("#content").display)

    async def test_revoked_generation_bypasses_an_existing_cosmetic_timer(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app._projection_timer = app.set_timer(60, app._run_queued_projection)
            app._projection_requested = True
            reader.replace([_session_state(lifecycle="failed", baseline=False)])
            for _ in range(100):
                if not app._all_rows and app._projection_timer is None:
                    break
                await asyncio.sleep(0.01)
            self.assertEqual(app._all_rows, [])
            self.assertFalse(app._selection_available)
            self.assertIsNone(app._projection_timer)
            self.assertTrue(reader.is_current(app._projection))

    async def test_input_cut_does_not_write_clipboard_and_ctrl_c_remains_global(self):
        app = DashboardApp(FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])]), {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("/", "a", "b", "c", "ctrl+a", "ctrl+x")
            self.assertEqual(app.clipboard, "")
            self.assertFalse(app.ALLOW_SELECT)
            await pilot.press("ctrl+c")
            self.assertEqual(app.return_code, 130)

    async def test_help_is_available_inside_menus_and_source_focus_is_visible(self):
        app = DashboardApp(FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])]), {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            for key, overlay in (("f", "filters"), ("o", "sort"), ("g", "group")):
                await pilot.press(key, "?")
                self.assertEqual(app._overlay, "help")
                await pilot.press("escape")
                self.assertEqual(app._overlay, overlay)
                await pilot.press("escape")
            await pilot.press("s")
            await pilot.pause()
            source_text = "\n".join(
                widget.content.plain for widget in app.query_one("#content").children
            )
            self.assertIn("Source list", source_text)
            await pilot.press("tab")
            await pilot.pause()
            source_text = "\n".join(
                widget.content.plain for widget in app.query_one("#content").children
            )
            self.assertIn("Source evidence", source_text)

    async def test_revocation_during_mount_drops_the_just_mounted_projection(self):
        item = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[item], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            container = app.query_one("#content")
            original_mount = container.mount
            revoke = True

            async def mount(*children, **kwargs):
                nonlocal revoke
                result = await original_mount(*children, **kwargs)
                if revoke:
                    revoke = False
                    reader.replace([_session_state()])
                return result

            container.mount = mount
            item["title"] = "Changed alpha"
            reader.replace([_session_state(rows=[item], ids=["alpha"])])
            app._refresh_projection()
            await app._paint()
            self.assertFalse(app._selection_available)
            self.assertEqual(app._all_rows, [])
            self.assertEqual(app._line_widgets, {})

    async def test_framework_resume_revalidates_before_reusing_old_session_facts(self):
        reader = FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])])
        app = DashboardApp(reader, {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            reader.replace([_session_state(lifecycle="failed", baseline=False)])
            app.app_resume_signal.publish(app)
            await pilot.pause()
            self.assertFalse(app._selection_available)
            self.assertEqual(app._all_rows, [])
            self.assertTrue(reader.is_current(app._projection))

    async def test_navigation_and_age_refresh_preserve_rows_and_visible_metadata(self):
        rows = [row("alpha", title="Alpha task"), row("beta", title="Beta task")]
        app = DashboardApp(FakeReader([_session_state(rows=rows, ids=["alpha", "beta"])]), {})
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            original = tuple(app.query_one("#content").children)
            # An admitted replacement with identical display values must not
            # lose the registry used to repaint an explicit selection change.
            app.reader.replace(
                [_session_state(rows=rows, ids=["alpha", "beta"])], priority=False
            )
            self.assertFalse(app.reader.requires_priority_refresh(app._projection))
            self.assertTrue(app._ensure_current_projection())
            await pilot.press("j")
            await pilot.pause()
            self.assertEqual(app._selected_label, "Beta task")
            self.assertEqual(tuple(app.query_one("#content").children), original)
            self.assertTrue(app._line_widgets[app._selected_key]._selected_row)
            self.assertEqual(sum(w._selected_row for w in app._line_widgets.values()), 1)
            app._last_age_wall_ms += 86_400_000
            app._refresh_age_cells()
            await pilot.pause()
            svg = app.export_screenshot()
            self.assertIn("Alpha", svg)
            self.assertIn("Beta", svg)

    async def test_selection_is_exact_and_survives_reorder_hide_revoke_and_restore(self):
        alpha = row("alpha", title="Alpha task")
        beta = row("beta", title="Beta task")
        reader = FakeReader([_session_state(rows=[alpha, beta], ids=["alpha", "beta"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            selected = app._selected_key
            self.assertEqual(selected, ("fixture-default", *identity("alpha").values()))
            self.assertEqual(app._selected_label, "Alpha task")

            alpha["activity"]["at"] = 900
            beta["activity"]["at"] = 990
            reader.replace([_session_state(rows=[beta, alpha], ids=["beta", "alpha"])])
            app._refresh_projection()
            self.assertEqual(app._selected_key, selected)
            self.assertEqual(app._selected_label, "Alpha task")

            app.filters["query"] = ("beta",)
            app._refresh_projection()
            self.assertTrue(app._selection_hidden)
            self.assertTrue(app._selection_available)
            self.assertIn("selected session hidden by filters", " ".join(app._detail_lines()))

            reader.replace([_session_state(rows=[beta], ids=["beta"])])
            app._refresh_projection()
            self.assertFalse(app._selection_available)
            self.assertIsNone(app._selected_detail_row)
            self.assertEqual(app._selected_identity, identity("alpha"))
            self.assertIn("not currently available", " ".join(app._detail_lines()))

            alpha["activity"]["at"] = 995
            reader.replace([_session_state(rows=[alpha, beta], ids=["alpha", "beta"])])
            app._refresh_projection()
            self.assertTrue(app._selection_available)
            self.assertEqual(app._selected_key, selected)
            await pilot.pause()

    async def test_untrusted_labels_are_literal_and_controls_are_visible(self):
        unsafe = row("literal", title="[bold]literal\x1b[31m")
        reader = FakeReader([_session_state(rows=[unsafe], ids=["literal"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            self.assertIn(r"\u001B", app._selected_label)
            self.assertIn("[bold]", app._selected_label)
            self.assertIn("[bold]", " ".join(app._detail_lines()))
            self.assertIn(r"\u001B", " ".join(app._detail_lines()))

    async def test_complete_empty_and_source_filter_keep_full_health_denominator(self):
        route_a = source("route-a", host="a", home="default", mesh="work_a")
        route_b = source("route-b", host="b", home="default", mesh="work_b")
        healthy_empty = _session_state(route_a)
        second = _session_state(route_b, rows=[row("visible", host="b")], ids=["visible"])
        reader = FakeReader([healthy_empty, second])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            self.assertEqual(app._report["totals"]["selectedSources"], 2)
            self.assertEqual(app._report["totals"]["state"], "complete")
            app.filters["source"] = ("route-a",)
            app._refresh_projection()
            self.assertEqual(len(app._visible_rows), 0)
            self.assertEqual(len(app._report["sources"]), 2)
            self.assertIn("a/Default complete", app._source_ribbon())
            self.assertIn("b/Default complete", app._source_ribbon())
            self.assertIn("complete", app._empty_state_text())
            self.assertIn("0 matches", app._status_text())
            reader.replace([healthy_empty])
            app._refresh_projection()
            self.assertEqual(app._report["totals"]["state"], "complete-empty")
            await pilot.pause()

    async def test_search_input_owns_qjk_and_help_filter_source_keys_work(self):
        item = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[item], ids=["alpha"])])
        reader.stages["fixture-default"] = "blocked"
        app = DashboardApp(reader, {"query": ("alpha",)})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            await pilot.press("/")
            await pilot.press("ctrl+a")
            await pilot.press("q", "j", "k")
            self.assertEqual(app.query_one("#search").value, "qjkalpha")
            self.assertIsNone(app.return_code)
            await pilot.pause(0.2)
            self.assertEqual(app.filters["query"], ("qjkalpha",))
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(app.filters["query"], ("alpha",))

            await pilot.press("?")
            self.assertEqual(app._overlay, "help")
            await pilot.press("escape")
            await pilot.press("f")
            self.assertEqual(app._overlay, "filters")
            await pilot.press("right")
            self.assertEqual(app._filter_dimension_index, 1)
            await pilot.press("escape")
            await pilot.press("s")
            self.assertEqual(app._view, "sources")
            self.assertEqual(app._focused_source_id, "fixture-default")
            await pilot.press("r")
            self.assertEqual(reader.retry_calls, ["fixture-default"])
            await pilot.press("q")
            self.assertEqual(app.return_code, 0)

    async def test_layout_modes_keep_selection_and_ctrl_c_exit_code(self):
        item = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[item], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(70, 20)) as pilot:
            await pilot.pause()
            key = app._selected_key
            self.assertEqual(app._layout_mode(), "compact")
            await pilot.press("enter")
            self.assertEqual(app._view, "details")
            await pilot.resize_terminal(130, 40)
            await pilot.pause()
            self.assertTrue(app._split_details())
            self.assertEqual(app._selected_key, key)
            await pilot.resize_terminal(50, 15)
            await pilot.pause()
            self.assertEqual(app._layout_mode(), "tiny")
            await pilot.press("ctrl+c")
            self.assertEqual(app.return_code, 130)

    async def test_context_columns_start_at_140_and_titles_keep_20_columns_at_80(self):
        item = row("alpha", title="A session title that should remain readable")
        app = DashboardApp(FakeReader([_session_state(rows=[item], ids=["alpha"])]), {})

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            header = app.query_one("#content").children[0]
            self.assertNotIn("CONTEXT", str(header.content))
            self.assertGreaterEqual(app._column_widths(76)[0], 20)

            await pilot.resize_terminal(120, 30)
            await pilot.pause()
            self.assertNotIn("CONTEXT", str(app.query_one("#content").children[0].content))
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app._split_details())
            self.assertTrue(app.query_one("#split-detail").display)

            await pilot.press("escape")
            await pilot.pause()
            await pilot.resize_terminal(140, 30)
            await pilot.pause()
            self.assertIn("REPO", str(app.query_one("#content").children[0].content))

    async def test_grouped_30_row_pages_keep_last_selected_row_visible_at_full_and_compact_sizes(self):
        route_a = source("route-a", host="laptop", home="default")
        route_b = source("route-b", host="workstation", home="work")
        rows_a = [row(f"a-{index:02}", title=f"Laptop task {index:02}", host="laptop") for index in range(15)]
        rows_b = [
            row(f"b-{index:02}", title=f"Workstation task {index:02}", host="workstation")
            for index in range(15)
        ]
        reader = FakeReader(
            [
                _session_state(route_a, rows=rows_a, ids=[item["identity"]["nativeId"] for item in rows_a]),
                _session_state(route_b, rows=rows_b, ids=[item["identity"]["nativeId"] for item in rows_b]),
            ]
        )
        app = DashboardApp(reader, {"group": "host-home"})

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            for size in ((80, 24), (60, 16)):
                await pilot.resize_terminal(*size)
                await pilot.pause()
                page_size = app._page_size()
                current_index = next(
                    index
                    for index, item in enumerate(app._visible_rows)
                    if app._row_key(item) == app._selected_key
                )
                page_start = current_index // page_size * page_size
                target = min(len(app._visible_rows) - 1, page_start + page_size - 1)
                app._select_row(app._visible_rows[target])
                await pilot.pause()

                self.assertIn(
                    app._selected_key,
                    {app._row_key(item) for item in app._page_rows},
                )
                if app._layout_mode() == "compact":
                    age_cell = app._age_cells[app._selected_key][0]
                    selected_widget = age_cell.parent.parent
                    selected_text = selected_widget.children[0].children[1].content.plain
                else:
                    selected_widget = app._line_widgets[app._selected_key]
                    selected_text = selected_widget.content.plain
                self.assertIn(app._selected_label, selected_text)
                content = app.query_one("#content")
                region = selected_widget.region
                viewport = content.scrollable_content_region
                self.assertGreaterEqual(region.y, viewport.y)
                self.assertLessEqual(region.bottom, viewport.bottom)

    async def test_selection_surface_is_consistent_and_no_color_uses_reverse(self):
        item = row("alpha", title="Alpha task")
        app = DashboardApp(FakeReader([_session_state(rows=[item], ids=["alpha"])]), {})

        async with app.run_test(size=(70, 20)) as pilot:
            await pilot.pause()
            compact = next(
                widget
                for widget in app.query_one("#content").children
                if "compact-row" in widget.classes
            )
            self.assertTrue(compact.children[0].has_class("selected-row"))
            self.assertTrue(compact.children[1].has_class("selected-row"))

            await pilot.press("enter")
            await pilot.resize_terminal(130, 40)
            await pilot.pause()
            self.assertTrue(app._split_details())
            selected = next(
                widget
                for widget in app.query_one("#split-list").children
                if widget.has_class("selected-row")
            )
            self.assertIn(app._selected_label, selected.children[1].content.plain)
            self.assertIn("Details · ↑↓ scroll · Tab list", app._footer_text())
            self.assertTrue(app.query_one("#split-detail").has_class("details-focused"))
            await pilot.press("tab")
            await pilot.pause()
            self.assertIn("List · ↑↓ select · Tab details", app._footer_text())
            await pilot.resize_terminal(100, 40)
            await pilot.pause()
            self.assertIn("↑↓ scroll · Esc back", app._footer_text())

        no_color = DashboardApp(
            FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])]), {}, no_color=True
        )
        async with no_color.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            selected = no_color._line_widgets[no_color._selected_key]
            self.assertFalse(selected.has_class("selected-row"))
            self.assertTrue(
                selected.content.get_style_at_offset(no_color.console, 0).reverse
            )

    async def test_details_are_summary_first_and_keep_exact_source_and_identity_evidence(self):
        item = row("alpha", title="Alpha task")
        app = DashboardApp(FakeReader([_session_state(rows=[item], ids=["alpha"])]), {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            lines = app._detail_lines()
            self.assertEqual(lines[0], "Alpha task")
            self.assertLess(lines.index("Session summary"), lines.index("Workspace and activity"))
            self.assertLess(lines.index("Workspace and activity"), lines.index("Source health and coverage"))
            self.assertNotIn("Observation reasons", lines)
            self.assertLess(
                lines.index("Source health and coverage"),
                lines.index("Native identity and lease diagnostics"),
            )
            joined = "\n".join(lines)
            self.assertIn("Project context: fixture-project", joined)
            self.assertIn("Working directory: /synthetic/workspace", joined)
            self.assertIn("Repository: none reported", joined)
            self.assertIn("Workspace metadata: current", joined)
            self.assertIn("Activity: ", joined)
            self.assertIn("Configured home: default", joined)
            self.assertIn("Configured source ID: fixture-default", joined)
            self.assertIn("namespace: sha256:", joined)

            item["blockedReasons"] = ["native_reason"]
            app.reader.replace([_session_state(rows=[item], ids=["alpha"])])
            app._refresh_projection()
            reason_lines = app._detail_lines()
            self.assertLess(
                reason_lines.index("Observation reasons"),
                reason_lines.index("Source health and coverage"),
            )
            self.assertIn("Bounded reasons: native_reason", reason_lines)

    async def test_repository_column_and_details_keep_linked_worktree_paths(self):
        worktree_root = "/synthetic/worktrees/topic-feature"
        common_dir = "/synthetic/repositories/main/.git\x1b"
        displayed_common_dir = r"/synthetic/repositories/main/.git\u001B"
        relative_path = "packages/tool"
        item = row("linked-worktree", title="Linked worktree")
        item["cwd"] = f"{worktree_root}/{relative_path}"
        item["workspace"] = {
            "health": "current",
            "reason": "mapped",
            "root": worktree_root,
            "rootKey": "workspace-topic-feature",
            "relativePath": relative_path,
            "projectKey": "independent-project-context",
            "repo": {
                "root": worktree_root,
                "commonDir": common_dir,
                "relativePath": relative_path,
            },
        }
        app = DashboardApp(
            FakeReader([_session_state(rows=[item], ids=["linked-worktree"])]), {}
        )

        async with app.run_test(size=(150, 24)) as pilot:
            await pilot.pause()
            header = app.query_one("#content").children[0].content.plain
            self.assertIn("REPO", header)
            selected = app._line_widgets[app._selected_key]
            self.assertIn("topic-feature", selected.content.plain)

            await pilot.press("enter")
            await pilot.pause()
            lines = app._detail_lines()
            joined = "\n".join(lines)
            self.assertLess(lines.index("Workspace and activity"), lines.index("Source health and coverage"))
            self.assertLess(
                lines.index(f"Working directory: {worktree_root}/{relative_path}"),
                lines.index(f"Repository root: {worktree_root}"),
            )
            self.assertIn(f"Path in repository: {relative_path}", joined)
            self.assertIn("Project context: independent-project-context", joined)
            self.assertIn("Workspace metadata: current", joined)
            self.assertIn(f"Shared Git directory: {displayed_common_dir}", joined)
            self.assertLess(
                lines.index("Native identity and lease diagnostics"),
                lines.index(f"Shared Git directory: {displayed_common_dir}"),
            )

            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            path_pages = []
            max_offset = max(
                0, len(app._wrapped_detail_lines()) - max(1, app.size.height - 7)
            )
            for _ in range(max_offset + 2):
                path_pages.extend(widget.content.plain for widget in app.query_one("#content").children)
                if app._scroll_offset >= max_offset:
                    break
                await pilot.press("down")
                await pilot.pause(0.01)
            joined_pages = "".join(path_pages)
            for path in (
                worktree_root,
                f"{worktree_root}/{relative_path}",
                displayed_common_dir,
            ):
                self.assertIn(path, joined_pages)

    async def test_repository_column_marks_current_none_and_hides_noncurrent_root(self):
        current_none = row("current-none", title="No Git repository")
        stale = row("stale-repo", title="Stale repository")
        stale["workspace"] = {
            "health": "stale",
            "reason": "workspace_support_expired",
            "repo": {
                "root": "/synthetic/old-root",
                "commonDir": "/synthetic/old-root/.git",
                "relativePath": "src",
            },
        }
        missing = row("missing-workspace", title="Missing workspace")
        missing["workspace"] = None
        missing.pop("cwd")
        items = [current_none, stale, missing]
        ids = [item["identity"]["nativeId"] for item in items]
        app = DashboardApp(FakeReader([_session_state(rows=items, ids=ids)]), {})

        async with app.run_test(size=(150, 24)) as pilot:
            await pilot.pause()
            rows = {
                item["identity"]["nativeId"]: app._line_widgets[app._row_key(item)].content.plain
                for item in app._all_rows
            }
            self.assertIn("none", rows["current-none"])
            self.assertIn("stale", rows["stale-repo"])
            self.assertNotIn("old-root", rows["stale-repo"])
            self.assertIn("unavailable", rows["missing-workspace"])

            stale_row = next(
                item
                for item in app._all_rows
                if item["identity"]["nativeId"] == "stale-repo"
            )
            app._select_row(stale_row, repaint=False)
            stale_details = "\n".join(app._detail_lines())
            self.assertIn("Repository: stale · workspace_support_expired", stale_details)
            self.assertNotIn("old-root", stale_details)

            missing_row = next(
                item
                for item in app._all_rows
                if item["identity"]["nativeId"] == "missing-workspace"
            )
            app._select_row(missing_row, repaint=False)
            missing_details = "\n".join(app._detail_lines())
            self.assertIn("Working directory: unavailable", missing_details)
            self.assertIn("Repository: unavailable", missing_details)

    async def test_same_identity_repository_change_repaints_list_and_details(self):
        old_root = "/synthetic/worktrees/before"
        new_root = "/synthetic/worktrees/after"

        def repository_row(root):
            item = row("stable-id", title="Stable identity")
            item["workspace"]["repo"] = {
                "root": root,
                "commonDir": "/synthetic/repositories/shared/.git",
                "relativePath": "src",
            }
            return item

        reader = FakeReader(
            [_session_state(rows=[repository_row(old_root)], ids=["stable-id"])]
        )
        app = DashboardApp(reader, {})
        async with app.run_test(size=(150, 24)) as pilot:
            await pilot.pause()
            row_widget = app._line_widgets[app._selected_key]
            self.assertIn("before", row_widget.content.plain)
            old_signature = app._content_signature()

            reader.replace(
                [_session_state(rows=[repository_row(new_root)], ids=["stable-id"])]
            )
            app._refresh_projection()
            self.assertNotEqual(old_signature, app._content_signature())
            await app._paint()
            self.assertIn("after", app._line_widgets[app._selected_key].content.plain)

            await pilot.press("enter")
            await pilot.pause()
            self.assertIn(f"Repository root: {new_root}", app._detail_lines())

    async def test_split_detail_wraps_fit_scrollable_width_and_preserve_exact_values(self):
        native_id = "thread-" + "x" * 96
        admitted_path = "/synthetic/" + "long-directory/" * 12
        item = row(native_id, title="Long identity task")
        item["cwd"] = admitted_path
        reader = FakeReader([_session_state(rows=[item], ids=[native_id])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(130, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            pane = app.query_one("#split-detail")
            self.assertTrue(app._split_details())
            content_width = pane.scrollable_content_region.width
            self.assertGreater(content_width, 0)
            self.assertEqual(app._detail_width(), content_width)
            visible_pages = []
            for _ in range(len(app._wrapped_detail_lines()) + 2):
                pane = app.query_one("#split-detail")
                visible_pages.append("".join(widget.content.plain for widget in pane.children))
                visible_lines = len(app._wrapped_detail_lines())
                maximum = max(0, visible_lines - max(1, app.size.height - 7))
                if app._scroll_offset >= maximum:
                    break
                await pilot.press("down")
                await pilot.pause(0.02)
            pane = app.query_one("#split-detail")
            self.assertTrue(any(native_id in page for page in visible_pages))
            self.assertTrue(any(admitted_path in page for page in visible_pages))
            self.assertEqual(
                pane.children[-1].content.plain,
                app._wrapped_detail_lines()[-1],
            )
            self.assertLessEqual(
                pane.children[-1].region.bottom,
                pane.scrollable_content_region.bottom,
            )
            self.assertTrue(
                all(
                    widget.content.cell_len <= content_width for widget in pane.children
                )
            )

    async def test_filter_source_choices_are_friendly_but_toggle_exact_ids(self):
        route_a = source("route-a", host="laptop", home="default")
        route_b = source("route-b", host="workstation", home="work")
        app = DashboardApp(
            FakeReader([_session_state(route_a), _session_state(route_b)]), {}
        )

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            await pilot.press("f")
            await pilot.pause()
            displayed = "\n".join(str(widget.content) for widget in app.query_one("#content").children)
            self.assertIn("[Source]", displayed)
            self.assertIn("laptop/Default", displayed)
            self.assertIn("workstation/Work", displayed)
            self.assertIn("Display filters only.", displayed)
            self.assertIn("All watched sources stay counted.", displayed)
            self.assertNotIn("route-a", displayed)
            await pilot.press("space")
            self.assertEqual(app.filters["source"], ("route-b",))

        narrow = DashboardApp(
            FakeReader([_session_state(route_a), _session_state(route_b)]), {}
        )
        async with narrow.run_test(size=(60, 24)) as pilot:
            await pilot.pause()
            await pilot.press("f")
            narrow._filter_dimension_index = 5
            await narrow._paint()
            heading = str(narrow.query_one("#content").children[0].content)
            self.assertIn("[Phase]", heading)
            self.assertIn("6/7", heading)

    async def test_sources_list_summaries_before_selected_exact_evidence(self):
        route_a = source("route-a", host="laptop", home="default")
        route_b = source("route-b", host="workstation", home="work")
        reader = FakeReader([_session_state(route_a), _session_state(route_b)])
        reader.stages["route-a"] = "blocked"
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            app._open_sources()
            await pilot.pause()
            widgets = app._source_widgets()
            texts = [widget.content.plain for widget in widgets]
            second_source_index = next(
                index for index, line in enumerate(texts) if "workstation/Work" in line
            )
            evidence_index = next(
                index for index, line in enumerate(texts) if "Selected source evidence" in line
            )
            self.assertLess(second_source_index, evidence_index)
            joined = "\n".join(texts)
            self.assertIn("route-a", joined)
            self.assertIn("Configured home: default", joined)
            self.assertIn("Reader stage: blocked", joined)
            self.assertIn("manual correction required", joined)

    async def test_queued_paint_and_age_tick_revoke_before_reusing_cached_rows(self):
        alpha = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            self.assertEqual(app._selected_label, "Alpha task")
            reader.revoke_on_next_fence = [_session_state()]
            await app._paint()
            self.assertTrue(reader.is_current(app._projection))
            self.assertEqual(app._all_rows, [])
            self.assertFalse(app._selection_available)
            self.assertIn("not currently available", " ".join(app._detail_lines()))

    async def test_revocation_during_widget_replacement_is_rechecked_before_mount(self):
        alpha = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)):
            try:
                container = app.query_one("#content")
                remove_children = container.remove_children

                async def revoke_during_mount_prep():
                    await remove_children()
                    reader.replace([_session_state()])

                container.remove_children = revoke_during_mount_prep
                app._view = "details"
                await app._paint()
                self.assertNotIn("alpha", [row["identity"]["nativeId"] for row in app._all_rows])
                self.assertFalse(app._selection_available)
                self.assertTrue(reader.is_current(app._projection))
                self.assertIn("not currently available", " ".join(app._detail_lines()))
            finally:
                # The raw app test bypasses the public runner exit hook. Stop
                # updates before Textual removes the screen, as that owner does.
                await app.stop_updates()

    async def test_age_only_refresh_checks_projection_before_updating_cells(self):
        alpha = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            reader.revoke_on_next_fence = [_session_state()]
            app._refresh_age_cells()
            self.assertTrue(reader.is_current(app._projection))
            self.assertEqual(app._all_rows, [])
            self.assertEqual(app._age_cells, {})
            self.assertFalse(app._selection_available)

    async def test_same_exact_identity_restores_with_new_single_source_provenance(self):
        route_a = source("route-a", host="fixture", home="default", mesh="work_a")
        route_b = source("route-b", host="fixture", home="default", mesh="work_b")
        alpha = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(route_a, rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            identity_key = tuple(app._selected_identity.values())
            reader.replace([_session_state(route_b, rows=[alpha], ids=["alpha"])])
            app._refresh_projection()
            self.assertEqual(tuple(app._selected_identity.values()), identity_key)
            self.assertEqual(app._selected_source_id, "route-b")
            self.assertTrue(app._selection_available)

    async def test_activity_only_projection_update_keeps_existing_row_widgets(self):
        alpha = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            content = app.query_one("#content")
            children_before = tuple(id(child) for child in content.children)
            alpha["activity"]["at"] = 925
            reader.replace([_session_state(rows=[alpha], ids=["alpha"])])
            app._refresh_projection()
            await app._paint()
            children_after = tuple(id(child) for child in content.children)
            self.assertEqual(children_after, children_before)
            self.assertEqual(app._age_cells[app._selected_key][2]["activity"]["at"], 925)

    async def test_empty_filter_dimension_shows_zero_and_reset_restores_defaults(self):
        alpha = row("alpha", title="Alpha task")
        filters = {
            "query": ("alpha",),
            "phase": ("working",),
            "includeChildren": True,
        }
        reader = FakeReader([_session_state(rows=[alpha], ids=["alpha"])])
        app = DashboardApp(reader, filters)

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            app._filter_dimension_index = 3  # membership
            for option_index in range(3):
                app._filter_option_index = option_index
                app._toggle_filter_option()
            app._refresh_projection()
            self.assertIn("membership", app._empty_dimensions)
            self.assertEqual(app._visible_rows, [])
            self.assertEqual(len(app._report["sources"]), 1)
            self.assertIn("0 matches", app._status_text())

            app._reset_filters()
            app._refresh_projection()
            self.assertEqual(app._empty_dimensions, set())
            self.assertEqual(app.filters["query"], ())
            self.assertEqual(app.filters["phase"], ())
            self.assertFalse(app.filters["includeChildren"])
            self.assertEqual(len(app._visible_rows), 1)

    async def test_q_quits_from_help_overlay_and_tiny_health_summary_keeps_all_counts(self):
        route_a = source("route-a", host="a", home="default", mesh="work_a")
        route_b = source("route-b", host="b", home="default", mesh="work_b")
        alpha = row("alpha", host="b")
        states = [
            _session_state(route_a, lifecycle="failed", baseline=False),
            _session_state(route_b, rows=[alpha], ids=["alpha"]),
        ]
        reader = FakeReader(states)
        app = DashboardApp(reader, {})

        async with app.run_test(size=(40, 10)) as pilot:
            await pilot.pause()
            summary = app._source_ribbon()
            self.assertIn("2 src", summary)
            self.assertIn("unavailable 1", summary)
            self.assertIn("s sources", summary)
            self.assertIn("Observer", app._header_text())
            self.assertIn("members", app._header_text())
            self.assertIn("uncertain", app._header_text())
            self.assertIn("Default", app._toolbar_text())
            await pilot.press("?")
            self.assertEqual(app._overlay, "help")
            await pilot.pause()
            content = app.query_one("#content")
            help_text = "\n".join(str(widget.content) for widget in content.children)
            self.assertTrue(content.display)
            self.assertIn("Keyboard help", help_text)
            self.assertIn("q quit", help_text)
            self.assertIn("Ctrl+C", help_text)
            await pilot.press("q")
            self.assertEqual(app.return_code, 0)


if __name__ == "__main__":
    unittest.main()
