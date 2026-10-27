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
        self.retry_calls = []
        self.stages = {item["config"]["id"]: "observing" for item in states}
        self._owner = object()
        self.revoke_on_next_fence = None

    def projection(self, filters, *, mode="list", target=None):
        return SimpleNamespace(
            owner=self._owner,
            revision=self.revision,
            report=report(self.states, mode=mode, filters=filters, target=target),
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

    def refresh_due(self):
        return None

    def retry(self, source_id):
        self.retry_calls.append(source_id)
        return source_id in self.stages and self.stages[source_id] in {"blocked", "retry-wait"}

    def replace(self, states):
        self.states = list(states)
        self.slots = [SimpleNamespace(source=item["config"]) for item in states]
        self.revision += 1
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
            self.assertIn("List focus", app._footer_text())
            await pilot.press("tab")
            self.assertIn("Details focus", app._footer_text())

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
            app.reader.replace([_session_state(rows=rows, ids=["alpha", "beta"])])
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
            self.assertIn("Unavailable 1", summary)
            self.assertIn("Complete 1", summary)
            await pilot.press("?")
            self.assertEqual(app._overlay, "help")
            await pilot.press("q")
            self.assertEqual(app.return_code, 0)


if __name__ == "__main__":
    unittest.main()
