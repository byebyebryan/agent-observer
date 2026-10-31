"""Dashboard integration for exact pins and accepted view choices."""

import asyncio
import importlib.util
import unittest

from test_dashboard import FakeReader, _session_state
from test_terminal_model import identity, row, source

from agent_observer.terminal.dashboard_view import SavedView
from agent_observer.terminal.model import IDENTITY_FIELDS, identity_tuple

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from agent_observer.terminal.dashboard import DashboardApp


def _reader(rows, *, route=None):
    route = source() if route is None else route
    return FakeReader(
        [
            _session_state(
                route,
                rows=rows,
                ids=[item["identity"]["nativeId"] for item in rows],
            )
        ]
    )


def _text(widget):
    content = getattr(widget, "content", None)
    if content is not None:
        value = getattr(content, "plain", content)
        return str(value)
    return "\n".join(_text(child) for child in getattr(widget, "children", ()))


class RecordingController:
    def __init__(self, view=None, *, persisted=None, warning=None, enabled=True):
        self.view = view or SavedView()
        self.persisted_view = self.view if persisted is None else persisted
        self.warning = warning
        self.persistence_enabled = enabled
        self.changed = asyncio.Event()
        self.submissions = []

    def submit(self, view):
        self.view = view
        self.submissions.append(view)
        self.changed.set()


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardSessionBoardTests(unittest.IsolatedAsyncioTestCase):
    async def test_pins_use_all_five_identity_fields_and_return_only_on_exact_match(self):
        pinned = row("same-id", title="Pinned original")
        other = row("other", title="Other")
        saved = SavedView((identity_tuple(pinned["identity"]),))
        reader = _reader([other, pinned])
        app = DashboardApp(reader, {}, saved_view=saved)

        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            self.assertEqual(
                [item["identity"]["nativeId"] for item in app._visible_rows],
                ["same-id", "other"],
            )
            self.assertEqual(app._visible_pin_counts(), (1, 1))

            replacement = row("same-id", title="Replacement title", host="replacement-host")
            replacement_state = _session_state(
                source("replacement", host="replacement-host"),
                rows=[replacement],
                ids=["same-id"],
            )
            reader.replace([replacement_state])
            await pilot.pause(0.1)
            self.assertEqual(app._visible_pin_counts(), (0, 0))
            self.assertEqual(len(app._visible_rows), 1)
            self.assertNotIn("* Replacement title", _text(app.query_one("#content")))

            returned = row("same-id", title="Current admitted title")
            reader.replace([_session_state(rows=[returned], ids=["same-id"])])
            await pilot.pause(0.1)
            self.assertEqual(app._visible_pin_counts(), (1, 1))
            self.assertIn("* Current admitted title", _text(app.query_one("#content")))

    async def test_pinned_region_precedes_stable_sorted_remainder_and_grouping(self):
        rows = [
            row("z", title="Zulu", host="fixture"),
            row("b", title="Bravo", host="fixture"),
            row("a", title="Alpha", host="fixture"),
        ]
        saved = SavedView((identity_tuple(rows[0]["identity"]),), sort="label", group="host-home")
        app = DashboardApp(_reader(rows), {"sort": "label", "group": "host-home"}, saved_view=saved)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            labels = [item["label"] for item in app._visible_rows]
            self.assertEqual(labels, ["Zulu", "Alpha", "Bravo"])
            content = _text(app.query_one("#content"))
            self.assertLess(content.index("Pinned sessions"), content.index("Other sessions"))
            self.assertLess(content.index("Other sessions"), content.index("Alpha"))
            self.assertIn("* Zulu", content)

    async def test_pin_count_excludes_filtered_and_missing_identities_without_fake_rows(self):
        visible = row("visible", title="Visible")
        missing = identity("gone", host="other-host")
        saved = SavedView(
            (identity_tuple(visible["identity"]), identity_tuple(missing))
        )
        app = DashboardApp(_reader([visible]), {"host": ("absent",)}, saved_view=saved)
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            self.assertEqual(app._visible_rows, [])
            self.assertEqual(app._visible_pin_counts(), (0, 0))
            self.assertIn("Pinned 0 in view / 2 this run (unsaved)", app._toolbar_text())
            self.assertNotIn("gone", _text(app.query_one("#content")))

    async def test_pin_toggle_and_panel_keep_input_printable_and_remove_unavailable_pin(self):
        item = row("active", title="Visible session")
        missing = identity("not-loaded", host="saved-host")
        app = DashboardApp(_reader([item]), {}, saved_view=SavedView((identity_tuple(missing),)))
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            self.assertEqual(app.saved_view.pins[-1], identity_tuple(item["identity"]))
            self.assertIn("* Visible session", _text(app.query_one("#content")))

            await pilot.press("P")
            self.assertEqual(app._overlay, "pins")
            panel = _text(app.query_one("#content"))
            self.assertIn("Not in this view · saved-host / not-loaded", panel)
            for field in IDENTITY_FIELDS:
                self.assertIn(field, panel)
            for value in missing.values():
                self.assertIn(value, panel)
            await pilot.press("p")
            self.assertEqual(app.saved_view.pins, (identity_tuple(item["identity"]),))
            self.assertEqual(len(app._visible_rows), 1)

            await pilot.press("escape", "/", "p", "P")
            self.assertEqual(app.query_one("#search").value, "pP")
            self.assertEqual(app.saved_view.pins, (identity_tuple(item["identity"]),))

    async def test_pins_panel_opens_from_details_and_sources_without_changing_view(self):
        app = DashboardApp(_reader([row("active", title="Visible")]), {})
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            self.assertEqual(app._view, "details")
            await pilot.press("P")
            self.assertEqual(app._overlay, "pins")
            await pilot.press("escape")
            self.assertIsNone(app._overlay)
            self.assertEqual(app._view, "details")

            await pilot.press("s")
            self.assertEqual(app._view, "sources")
            await pilot.press("P")
            self.assertEqual(app._overlay, "pins")
            await pilot.press("escape")
            self.assertIsNone(app._overlay)
            self.assertEqual(app._view, "sources")

    async def test_sort_and_group_cancel_restore_preview_and_only_acceptance_submits(self):
        items = [row("beta", title="Beta"), row("alpha", title="Alpha")]
        initial = SavedView()
        controller = RecordingController(initial)
        app = DashboardApp(_reader(items), {}, view_controller=controller)
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            await pilot.press("o", "down")
            self.assertEqual(app.filters["sort"], "label")
            await pilot.press("escape")
            self.assertEqual(app.filters["sort"], "activity")
            self.assertEqual(controller.submissions, [])

            await pilot.press("g", "down", "enter")
            self.assertEqual(app.filters["group"], "host-home")
            self.assertEqual(len(controller.submissions), 1)
            self.assertEqual(controller.submissions[0].group, "host-home")

            await pilot.press("g", "down", "escape")
            self.assertEqual(app.filters["group"], "host-home")
            self.assertEqual(len(controller.submissions), 1)

    async def test_pin_edit_saves_effective_cli_order_but_startup_alone_does_not(self):
        item = row("active", title="Visible session")
        loaded = SavedView((), sort="label", group="host-home")
        controller = RecordingController(loaded)
        app = DashboardApp(
            _reader([item]),
            {"sort": "activity", "group": "none"},
            view_controller=controller,
        )
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            self.assertEqual(controller.submissions, [])
            await pilot.press("p")
            self.assertEqual(controller.submissions[-1].sort, "activity")
            self.assertEqual(controller.submissions[-1].group, "none")

    async def test_pin_marker_survives_full_compact_and_split_rendering_with_selection(self):
        pinned = row("pinned", title="Pinned label")
        other = row("other", title="Other label")
        saved = SavedView((identity_tuple(pinned["identity"]),))
        app = DashboardApp(_reader([other, pinned]), {}, saved_view=saved)
        async with app.run_test(size=(140, 30)) as pilot:
            await pilot.pause()
            for size in ((140, 30), (70, 20)):
                await pilot.resize_terminal(*size)
                await pilot.pause()
                self.assertIn("* Pinned label", _text(app.query_one("#content")))
                self.assertIn(app._selected_key, {app._row_key(item) for item in app._page_rows})

            app._view = "details"
            app._focus = "list"
            await pilot.resize_terminal(120, 30)
            await pilot.pause()
            self.assertTrue(app._split_details())
            self.assertIn("* Pinned label", _text(app.query_one("#content")))
            self.assertIn("fixture/default", _text(app.query_one("#content")))
            self.assertIn(app._selected_key, {app._row_key(item) for item in app._page_rows})

    async def test_grouped_pin_pages_keep_end_selection_visible_after_resize(self):
        route_a = source("route-a", host="north", home="default")
        route_b = source("route-b", host="south", home="work")
        rows_a = [row(f"a-{index}", title=f"North {index}", host="north") for index in range(7)]
        rows_b = [row(f"b-{index}", title=f"South {index}", host="south") for index in range(7)]
        reader = FakeReader(
            [
                _session_state(route_a, rows=rows_a, ids=[item["identity"]["nativeId"] for item in rows_a]),
                _session_state(route_b, rows=rows_b, ids=[item["identity"]["nativeId"] for item in rows_b]),
            ]
        )
        pins = (identity_tuple(rows_a[0]["identity"]), identity_tuple(rows_b[0]["identity"]))
        app = DashboardApp(reader, {"group": "host-home"}, saved_view=SavedView(pins, group="host-home"))
        async with app.run_test(size=(80, 24)) as pilot:
            for size in ((80, 24), (70, 20)):
                await pilot.resize_terminal(*size)
                await pilot.pause()
                await pilot.press("home")
                await pilot.pause()
                self.assertIn("Pinned sessions", _text(app.query_one("#content")))
                await pilot.press("end")
                await pilot.pause()
                self.assertIn(app._selected_key, {app._row_key(item) for item in app._page_rows})
                self.assertIn("Other sessions", _text(app.query_one("#content")))

    async def test_pin_limit_refuses_new_identity_without_evicting(self):
        pins = tuple(
            identity_tuple(identity(f"saved-{index}", host=f"host-{index}"))
            for index in range(32)
        )
        app = DashboardApp(_reader([row("new", title="New")]), {}, saved_view=SavedView(pins))
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            self.assertEqual(app.saved_view.pins, pins)
            self.assertIn("Pin limit reached", app._message)

    async def test_blocked_save_does_not_delay_priority_projection_withdrawal(self):
        class BlockingController(RecordingController):
            def __init__(self):
                super().__init__(warning="saved_view_save_timeout", enabled=False)
                self.save_started = asyncio.Event()
                self.release_save = asyncio.Event()
                self.save_task = None

            def submit(self, view):
                super().submit(view)
                self.save_started.set()
                self.save_task = asyncio.create_task(self.release_save.wait())

        item = row("leased", title="Leased session")
        controller = BlockingController()
        reader = _reader([item])
        app = DashboardApp(reader, {}, view_controller=controller)
        async with app.run_test(size=(100, 28)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await asyncio.wait_for(controller.save_started.wait(), 1)
            self.assertEqual(
                app._status_text(), "View not saved; session only (save_timeout)"
            )
            app._message = "Another dashboard message."
            self.assertEqual(
                app._status_text(), "View not saved; session only (save_timeout)"
            )

            reader.replace([_session_state(lifecycle="failed", baseline=False)])
            for _ in range(20):
                if not app._all_rows:
                    break
                await pilot.pause(0.01)
            self.assertEqual(app._all_rows, [])
            self.assertFalse(controller.release_save.is_set())
            controller.release_save.set()
            await asyncio.wait_for(controller.save_task, 1)


if __name__ == "__main__":
    unittest.main()
