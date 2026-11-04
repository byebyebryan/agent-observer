"""Headless dashboard behavior over the maintained terminal projection model."""

from __future__ import annotations

import asyncio
import importlib.util
import time
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import patch

from test_terminal_model import identity, lease, read, report, row, source, state

TEXTUAL_AVAILABLE = importlib.util.find_spec("textual") is not None
if TEXTUAL_AVAILABLE:
    from rich.text import Text

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


def _row_with_qualified_status(native_id, status, *, host="fixture"):
    item = row(native_id, title=f"{status} task", host=host)
    if status == "Ready":
        item["phase"].update(value="waiting", health="current")
    elif status == "Blocked":
        item["phase"].update(value="blocked", health="current")
    elif status == "Inactive":
        item["runtime"].update(value="parked", health="current")
        item["phase"].update(value="blocked", health="current")
    elif status == "Unknown":
        item["phase"].update(value="unknown", health="unsupported")
    elif status == "Stale":
        item["phase"].update(value="unknown", health="stale", lastKnownValue="working")
    elif status == "Unavailable":
        item["runtime"].update(value="unknown", health="unavailable")
    return item


def _widget_text(widget):
    content = getattr(widget, "content", None)
    own = [content.plain] if content is not None and hasattr(content, "plain") else []
    return own + [line for child in getattr(widget, "children", ()) for line in _widget_text(child)]


@unittest.skipUnless(TEXTUAL_AVAILABLE, "optional dashboard dependencies required")
class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_staggered_sources_keep_healthy_rows_in_scheduled_frames_at_each_layout(self):
        configurations = [
            source(f"fixture-{name}", host=f"fixture-{name}")
            for name in ("alpha", "beta", "gamma")
        ]

        def ready(index):
            item = row(
                f"fictional-{index}",
                title=f"Fictional {('alpha', 'beta', 'gamma')[index]}",
                host=configurations[index]["host"],
            )
            return _session_state(
                configurations[index], rows=[item], ids=[item["identity"]["nativeId"]]
            )

        def failed(index):
            return _session_state(configurations[index], lifecycle="failed", baseline=False)

        for width in (106, 80, 40):
            with self.subTest(width=width):
                current = [ready(0), failed(1), failed(2)]
                reader = FakeReader(current)
                app = DashboardApp(reader, {}, no_color=True)
                frames = []
                stage_box = {"value": "initial"}
                started = time.monotonic()
                original_display = app._display

                def capture_display(
                    self,
                    screen,
                    renderable,
                    *,
                    frames=frames,
                    stage_box=stage_box,
                    started=started,
                    original_display=original_display,
                ):
                    if renderable is not None and not self._batch_count:
                        text = "\n".join(
                            "".join(segment.text for segment in strip)
                            for strip in screen._compositor.render_strips()
                        )
                        frames.append(
                            {
                                "seconds": time.monotonic() - started,
                                "stage": stage_box["value"],
                                "text": text,
                                "content_displayed": (
                                    self._content.display if self._content is not None else None
                                ),
                            }
                        )
                    return original_display(screen, renderable)

                app._display = MethodType(capture_display, app)

                async with app.run_test(size=(width, 24)) as pilot:
                    async def wait_for(predicate, message):
                        for _ in range(100):
                            if predicate():
                                return
                            await pilot.pause(0.02)
                        self.fail(message)

                    await wait_for(
                        lambda frames=frames: any(
                            "Fictional alpha" in frame["text"] for frame in frames
                        ),
                        f"alpha row did not paint at {width} columns",
                    )
                    self.assertIn("Sources 3", app._source_ribbon())

                    for index in (1, 2):
                        stage_box["value"] = f"source-{index}-setup-epoch"
                        current = list(current)
                        current[index] = _session_state(
                            configurations[index], lifecycle="warming", baseline=False
                        )
                        reader.replace(current, priority=True)
                        source_id = configurations[index]["id"]
                        await wait_for(
                            lambda app=app, reader=reader, source_id=source_id: (
                                reader.is_current(app._projection)
                                and any(
                                    item["id"] == source_id
                                    and item["health"] == "warming"
                                    for item in app._report.get("sources", ())
                                )
                            ),
                            f"source {index} setup epoch was not projected",
                        )
                        await pilot.pause(0.04)

                        stage_box["value"] = f"source-{index}-baseline"
                        current[index] = ready(index)
                        reader.replace(current, priority=False)
                        expected = f"Fictional {('alpha', 'beta', 'gamma')[index]}"
                        await wait_for(
                            lambda frames=frames, expected=expected: any(
                                expected in frame["text"] for frame in frames
                            ),
                            f"source {index} baseline did not paint",
                        )

                    for name in ("alpha", "beta", "gamma"):
                        self.assertIn(f"Fictional {name}", frames[-1]["text"])
                    seen_alpha = False
                    observed_setup = set()
                    for frame in frames:
                        if "Fictional alpha" in frame["text"]:
                            seen_alpha = True
                        if frame["stage"].endswith("setup-epoch") and seen_alpha:
                            observed_setup.add(frame["stage"])
                        if seen_alpha:
                            self.assertTrue(
                                frame["content_displayed"],
                                f"content hidden at {width} columns during {frame['stage']}",
                            )
                            self.assertIn(
                                "Fictional alpha",
                                frame["text"],
                                f"healthy alpha row missing at {width} columns during {frame['stage']}",
                            )
                    self.assertEqual(
                        observed_setup,
                        {"source-1-setup-epoch", "source-2-setup-epoch"},
                    )
                    for setup_stage in observed_setup:
                        setup_frames = [
                            frame for frame in frames if frame["stage"] == setup_stage
                        ]
                        self.assertTrue(
                            any(
                                "Sources 3" in frame["text"]
                                and "warming" in frame["text"].lower()
                                for frame in setup_frames
                            ),
                            f"source health or denominator missing during {setup_stage}",
                        )

    async def test_priority_baseline_page_shift_keeps_selected_admitted_row_visible(self):
        source_alpha = source("fixture-alpha", host="fixture-alpha")
        source_beta = source("fixture-beta", host="fixture-beta", home="second")
        alpha_rows = [
            row(f"alpha-{index}", title=f"Alpha{index}", host="fixture-alpha")
            for index in range(12)
        ]
        for item in alpha_rows:
            item["activity"]["at"] = 950
        beta_state = _session_state(source_beta, lifecycle="warming", baseline=False)
        reader = FakeReader(
            [
                _session_state(
                    source_alpha,
                    rows=alpha_rows,
                    ids=[item["identity"]["nativeId"] for item in alpha_rows],
                ),
                beta_state,
            ]
        )
        app = DashboardApp(reader, {}, no_color=True)
        frames = []
        stage = {"value": "initial"}
        original_display = app._display

        def capture_display(self, screen, renderable, *, frames=frames, stage=stage):
            if renderable is not None and not self._batch_count:
                text = "\n".join(
                    "".join(segment.text for segment in strip)
                    for strip in screen._compositor.render_strips()
                )
                frames.append(
                    {
                        "stage": stage["value"],
                        "text": text,
                        "content_displayed": self._content.display,
                    }
                )
            return original_display(screen, renderable)

        app._display = MethodType(capture_display, app)

        async with app.run_test(size=(106, 12)) as pilot:
            async def wait_for(predicate, message):
                for _ in range(100):
                    if predicate():
                        return
                    await pilot.pause(0.02)
                self.fail(message)

            await wait_for(
                lambda: any("Alpha0" in frame["text"] for frame in frames),
                "initial selected row did not paint",
            )
            self.assertEqual(app._selected_label, "Alpha0")
            self.assertEqual(app._page_size(), 6)
            selected_key = app._selected_key
            selected_identity = dict(app._selected_identity)

            page_size = app._page_size()
            beta_rows = [
                row(f"beta-{index}", title=f"Beta{index}", host="fixture-beta")
                for index in range(page_size - 1)
            ]
            for item in beta_rows:
                item["activity"]["at"] = 960
            stage["value"] = "coalesced-setup-and-baseline"
            # One priority revision models setup epoch and baseline admission
            # coalesced into the same dirty notification.
            reader.replace(
                [
                    _session_state(
                        source_alpha,
                        rows=alpha_rows,
                        ids=[item["identity"]["nativeId"] for item in alpha_rows],
                    ),
                    _session_state(
                        source_beta,
                        rows=beta_rows,
                        ids=[item["identity"]["nativeId"] for item in beta_rows],
                    ),
                ],
                priority=True,
            )
            await wait_for(
                lambda: (
                    reader.is_current(app._projection)
                    and all(
                        f"Beta{index}" in " ".join(_widget_text(app.query_one("#content")))
                        for index in range(page_size - 1)
                    )
                ),
                "new source baseline rows did not reach the dashboard",
            )
            await pilot.pause()

            self.assertTrue(app.query_one("#content").display)
            self.assertEqual(app._selected_key, selected_key)
            self.assertEqual(app._selected_identity, selected_identity)
            self.assertEqual(app._selected_label, "Alpha0")
            self.assertTrue(app._selection_available)
            self.assertIn(selected_key, {app._row_key(item) for item in app._visible_rows})
            self.assertIn(selected_key, {app._row_key(item) for item in app._page_rows})
            self.assertTrue(any(f"Beta{page_size - 2}" in frame["text"] for frame in frames))

            seen_alpha = False
            for frame in frames:
                if "Alpha0" in frame["text"]:
                    seen_alpha = True
                if seen_alpha:
                    self.assertTrue(frame["content_displayed"])
                    self.assertIn("Alpha0", frame["text"])

    async def test_revocation_during_delayed_staging_hides_old_rows_and_recovers_sibling(self):
        source_alpha = source("route-alpha", host="alpha-host")
        source_beta = source("route-beta", host="beta-host", home="second")
        for width in (106, 80, 40):
            with self.subTest(width=width):
                alpha = row("alpha", title="Alpha current", host="alpha-host")
                beta = row("beta", title="Beta current", host="beta-host")
                reader = FakeReader(
                    [
                        _session_state(source_alpha, rows=[alpha], ids=["alpha"]),
                        _session_state(source_beta, rows=[beta], ids=["beta"]),
                    ]
                )
                app = DashboardApp(reader, {})

                async with app.run_test(size=(width, 24)) as pilot:
                    await pilot.pause()
                    container = app.query_one("#content")
                    original_mount = container.mount
                    mount_started = asyncio.Event()
                    release_mount = asyncio.Event()

                    async def delayed_mount(
                        *children,
                        mount_started=mount_started,
                        release_mount=release_mount,
                        original_mount=original_mount,
                        **kwargs,
                    ):
                        mount_started.set()
                        await release_mount.wait()
                        return await original_mount(*children, **kwargs)

                    container.mount = delayed_mount
                    alpha_refreshed = row("alpha", title="Alpha refreshed", host="alpha-host")
                    row_delta = row("charlie", title="Beta addition", host="beta-host")
                    reader.replace(
                        [
                            _session_state(
                                source_alpha, rows=[alpha_refreshed], ids=["alpha"]
                            ),
                            _session_state(
                                source_beta, rows=[beta, row_delta], ids=["beta", "charlie"]
                            ),
                        ],
                        priority=False,
                    )
                    paint_task = asyncio.create_task(app._paint())
                    try:
                        await asyncio.wait_for(mount_started.wait(), 1)
                        self.assertTrue(container.display)
                        row_ids = {key[-1] for key in app._visible_row_widgets}
                        self.assertIn("beta", row_ids)
                        if width >= 100:
                            self.assertIn("Alpha refreshed", " ".join(_widget_text(container)))
                            self.assertNotIn("Alpha current", " ".join(_widget_text(container)))
                            self.assertIn("alpha", row_ids)
                        else:
                            # A compound card is hidden if its admitted facts
                            # changed; the unchanged sibling stays visible.
                            self.assertNotIn("alpha", row_ids)
                            self.assertIn("Beta current", " ".join(_widget_text(container)))

                        reader.replace(
                            [
                                _session_state(
                                    source_alpha, lifecycle="failed", baseline=False
                                ),
                                _session_state(
                                    source_beta,
                                    rows=[beta, row_delta],
                                    ids=["beta", "charlie"],
                                ),
                            ],
                            priority=True,
                        )
                        for _ in range(100):
                            if (
                                app._projection is not None
                                and reader.is_current(app._projection)
                                and app._projection.revision == reader.revision
                            ):
                                break
                            await asyncio.sleep(0.01)
                        row_ids = {key[-1] for key in app._visible_row_widgets}
                        self.assertNotIn("alpha", row_ids)
                        current_ids = [row["identity"]["nativeId"] for row in app._all_rows]
                        self.assertNotIn("alpha", current_ids)
                        self.assertIn("beta", current_ids)
                        if width >= 100:
                            self.assertFalse(container.display)
                        else:
                            self.assertTrue(container.display)
                            self.assertIn("beta", row_ids)
                            self.assertIn("Beta current", " ".join(_widget_text(container)))
                    finally:
                        release_mount.set()

                    await asyncio.wait_for(paint_task, 2)
                    container.mount = original_mount
                    for _ in range(100):
                        visible = "\n".join(
                            "".join(segment.text for segment in strip)
                            for strip in app.screen._compositor.render_strips()
                        )
                        if container.display and "Beta current" in visible and "Beta addition" in visible:
                            break
                        await pilot.pause(0.02)
                    self.assertTrue(container.display)
                    await pilot.pause()
                    visible = "\n".join(
                        "".join(segment.text for segment in strip)
                        for strip in app.screen._compositor.render_strips()
                    )
                    self.assertNotIn("Alpha refreshed", visible)
                    self.assertNotIn("Alpha current", visible)
                    self.assertIn("Beta current", visible)
                    self.assertIn("Beta addition", visible)

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
                self.assertNotIn("1 session", str(app.query_one("#header").render()))
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
            self.assertFalse(app.query_one("#content").display)
            await pilot.pause()
            self.assertTrue(app.query_one("#content").display)
            self.assertNotIn(
                "Fixture session", " ".join(_widget_text(app.query_one("#content")))
            )

    async def test_paint_resuming_after_shutdown_ignores_removed_chrome(self):
        app = DashboardApp(FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])]), {})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.stop_updates()
            app._updates_stopped = False
            container = app.query_one("#content")
            remove_children = container.remove_children
            app._overlay = "help"  # Exercise the guarded replacement path.
            app._content_signature_value = None

            async def shutdown_during_removal(*args, **kwargs):
                await remove_children(*args, **kwargs)
                # Textual clears is_running before pruning screen children;
                # the app's Unmount handler has not run at this point.
                app._running = False
                await app.query_one("#toolbar").remove()

            container.remove_children = shutdown_during_removal
            try:
                await app._paint()
                self.assertTrue(app._mounted)
                self.assertFalse(app.is_running)
                self.assertEqual(len(container.children), 0)
                app._paint_chrome()
                app._request_render()
                self.assertIsNone(app._render_timer)
            finally:
                container.remove_children = remove_children
                app._running = True
                await app.stop_updates()

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
        async with app.run_test(size=(110, 24)) as pilot:
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
            await pilot.press("q", "j", "k", "a")
            self.assertEqual(app.query_one("#search").value, "qjkaalpha")
            self.assertIsNone(app.return_code)
            await pilot.pause(0.2)
            self.assertEqual(app.filters["query"], ("qjkaalpha",))
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(app.filters["query"], ("alpha",))

            await pilot.press("?")
            self.assertEqual(app._overlay, "help")
            await pilot.pause()
            help_text = "\n".join(
                widget.content.plain for widget in app.query_one("#content").children
            )
            self.assertIn("current cached repository paths", help_text)
            self.assertIn("age fades new→old", help_text)
            self.assertIn("Profile: hue=host · shade=profile", help_text)
            self.assertIn("Workspace: teal=repo · orange=directory", help_text)
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
            self.assertEqual(app._layout_mode(), "stacked")
            await pilot.resize_terminal(31, 12)
            await pilot.pause()
            self.assertEqual(app._layout_mode(), "tiny")
            await pilot.press("ctrl+c")
            self.assertEqual(app.return_code, 130)

    async def test_search_repaints_page_count_when_first_row_is_unchanged(self):
        rows = [
            row(
                f"search-{index:02}",
                title=f"{'Layout' if index < 3 else 'Task'} {index:02}",
            )
            for index in range(12)
        ]
        app = DashboardApp(
            FakeReader([_session_state(rows=rows, ids=[item["identity"]["nativeId"] for item in rows])]),
            {},
        )

        async with app.run_test(size=(32, 12)) as pilot:
            await pilot.pause()
            selected = app._selected_key
            before = app._footer_text().rsplit(" ", 1)[-1]
            self.assertEqual(len(app._visible_rows), 12)
            await pilot.press("/", "l", "a", "y")
            await pilot.pause(0.3)
            self.assertEqual(app.filters["query"], ("lay",))
            self.assertEqual(app._selected_key, selected)
            self.assertEqual(len(app._visible_rows), 3)
            self.assertIn("3 matches", app._header_text())
            await pilot.press("enter")
            await pilot.pause()
            after = app._footer_text().rsplit(" ", 1)[-1]
            self.assertNotEqual(before, after)
            self.assertEqual(after, f"1/{(3 + app._page_size() - 1) // app._page_size()}")

    async def test_profile_and_workspace_columns_keep_a_flexible_title(self):
        item = row("alpha", title="A session title that should remain readable")
        app = DashboardApp(FakeReader([_session_state(rows=[item], ids=["alpha"])]), {})

        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            header = app.query_one("#content").children[0]
            self.assertIn("STATUS", str(header.content))
            self.assertIn("STATUS", str(header.content))
            self.assertIn("PROFILE", str(header.content))
            self.assertIn("WORKSPACE", str(header.content))
            self.assertEqual(len(app._column_widths(106)), 4)
            self.assertGreaterEqual(app._column_widths(106)[1], 28)

            await pilot.resize_terminal(120, 30)
            await pilot.pause()
            self.assertIn("WORKSPACE", str(app.query_one("#content").children[0].content))

    async def test_responsive_cards_wrap_metadata_and_keep_selection_visible_across_resize(self):
        from agent_observer.terminal.dashboard_view import SavedView
        from agent_observer.terminal.model import identity_tuple

        laptop = source("laptop-default", host="laptop", home="default")
        server = source("server-work", host="server", home="work")
        offline = source("offline-default", host="offline", home="default")
        long_path = "/reported/" + "界" * 36 + "/workspace"
        rows = []
        for index in range(8):
            host = "laptop" if index < 4 else "server"
            title = f"Review task {index:02}"
            if index == 0:
                title = "界" * 16 + " cafe\u0301 renderer search result"
            elif index == 4:
                title = "界 alternate search result"
            item = row(f"responsive-{index}", title=title, host=host)
            if index == 0:
                item["cwd"] = long_path
                item["runtime"].update(value="unknown", health="unavailable")
                item["activity"].update(at=None, health="unavailable", reason="fixture")
            elif index == 1:
                item["cwd"] = None
                item["workspace"]["health"] = "unavailable"
            rows.append(item)
        states = [
            _session_state(laptop, rows=rows[:4], ids=[item["identity"]["nativeId"] for item in rows[:4]]),
            _session_state(server, rows=rows[4:], ids=[item["identity"]["nativeId"] for item in rows[4:]]),
            _session_state(offline, lifecycle="failed", baseline=False),
        ]
        saved = SavedView((identity_tuple(rows[0]["identity"]),), group="host-home")
        app = DashboardApp(
            FakeReader(states),
            {"query": ("界",), "group": "host-home"},
            icons=True,
            saved_view=saved,
        )

        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            projected = {
                item["identity"]["nativeId"]: item for item in app._all_rows
            }
            self.assertEqual(app._layout_mode(), "full")
            self.assertEqual(app._selected_key, app._row_key(projected["responsive-0"]))
            self.assertIn("Sources 3", app._source_ribbon())
            self.assertIn("offline/Default unavailable", app._source_ribbon())

            await pilot.resize_terminal(32, 12)
            await pilot.pause()
            self.assertEqual(app._layout_mode(), "stacked")
            self.assertFalse(app.query_one("#toolbar").display)
            pinned_card = next(
                widget
                for widget in app.query_one("#content").children
                if "stacked-row" in widget.classes and widget.has_class("selected-row")
            )
            status_age = pinned_card.children[0]
            self.assertEqual(status_age.children[1].content.plain.strip(), "× Unavailable")
            self.assertEqual(status_age.children[3].content.plain.strip(), "Unavailable")
            self.assertTrue(pinned_card.children[1].children[1].content.plain.startswith("* "))
            footer = app._footer_text()
            self.assertIn("↑↓", footer)
            self.assertIn("↵", footer)
            self.assertIn("/", footer)
            self.assertIn("?", footer)
            self.assertIn("q", footer)
            self.assertLessEqual(Text(footer).cell_len, 28)

            app._select_row(projected["responsive-4"])
            await pilot.pause()
            self.assertIn("server/work", "\n".join(_widget_text(app.query_one("#content"))))
            selected_key = app._selected_key
            self.assertEqual(selected_key, app._row_key(projected["responsive-4"]))
            selected_card = next(
                widget
                for widget in app.query_one("#content").children
                if "stacked-row" in widget.classes and widget.has_class("selected-row")
            )
            viewport = app.query_one("#content").scrollable_content_region
            self.assertGreaterEqual(selected_card.region.y, viewport.y)
            self.assertLessEqual(selected_card.region.bottom, viewport.bottom)
            self.assertIn("2/2", app._footer_text())

            await pilot.press("/")
            self.assertTrue(app._search_open)
            self.assertLessEqual(Text(app._footer_text()).cell_len, 28)
            await pilot.press("x")
            await pilot.pause(0.2)
            self.assertEqual(app.filters["query"], ("x",))
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(app.filters["query"], ("界",))
            self.assertEqual(app._selected_key, selected_key)

            await pilot.press("f")
            await pilot.press("right")
            await pilot.pause()
            filter_heading = app.query_one("#content").children[0]
            self.assertIn("[Source]", filter_heading.content.plain)
            self.assertIn("Source filter", app.query_one("#header").content.plain)
            option = app.query_one("#filter-option-current")
            viewport = app.query_one("#content").scrollable_content_region
            self.assertGreaterEqual(filter_heading.region.y, viewport.y)
            self.assertLessEqual(filter_heading.region.bottom, viewport.bottom)
            self.assertGreaterEqual(option.region.y, viewport.y)
            self.assertLess(option.region.bottom, viewport.bottom)
            self.assertLessEqual(Text(app._footer_text()).cell_len, 28)
            await pilot.press("escape")

            await pilot.press("?")
            await pilot.pause()
            help_text = "\n".join(
                line for widget in app.query_one("#content").children for line in _widget_text(widget)
            )
            self.assertIn("Keyboard help", help_text)
            self.assertLessEqual(Text(app._footer_text()).cell_len, 28)
            await pilot.press("escape")

            await pilot.press("s")
            await pilot.press("end")
            await pilot.press("tab")
            await pilot.pause()
            evidence_heading = app.query_one("#source-evidence-start")
            viewport = app.query_one("#content").scrollable_content_region
            self.assertGreaterEqual(evidence_heading.region.y, viewport.y)
            self.assertLess(evidence_heading.region.bottom, viewport.bottom)
            visible_source_text = "\n".join(
                line
                for widget in app.query_one("#content").children
                if widget.region.y >= viewport.y and widget.region.bottom <= viewport.bottom
                for line in _widget_text(widget)
            )
            self.assertIn("offline/Default", visible_source_text)
            self.assertIn("Health: unavailable", visible_source_text)
            await pilot.press("escape")

            await pilot.press("P")
            self.assertEqual(app._overlay, "pins")
            await pilot.press("p")
            self.assertEqual(app.saved_view.pins, ())
            await pilot.press("escape")
            app._select_row(projected["responsive-4"])
            await pilot.press("p")
            self.assertEqual(app.saved_view.pins, (identity_tuple(rows[4]["identity"]),))

            app._select_row(projected["responsive-0"])
            await pilot.press("enter")
            await pilot.pause()
            wrapped = app._wrapped_detail_lines()
            self.assertTrue(any(long_path.rsplit("/", 1)[-1] in line for line in wrapped))
            await pilot.press("down")
            await pilot.pause()
            self.assertGreater(app._scroll_offset, 0)
            app._scroll_offset = 0
            page_height = app._content_height_budget()
            for offset in range(0, len(wrapped), page_height):
                app._scroll_offset = offset
                visible = [widget.content.plain for widget in app._detail_widgets()]
                self.assertEqual(visible, wrapped[offset : offset + page_height])
            await pilot.press("escape")

            for size, mode in (
                ((40, 12), "stacked"),
                ((60, 16), "compact"),
                ((80, 24), "compact"),
                ((120, 16), "full"),
                ((120, 30), "full"),
            ):
                await pilot.resize_terminal(*size)
                await pilot.pause()
                self.assertEqual(app._layout_mode(), mode)
                self.assertEqual(app._selected_key, app._row_key(projected["responsive-0"]))
                self.assertIn(app._selected_key, {app._row_key(item) for item in app._page_rows})
                if mode == "stacked":
                    selected_widget = next(
                        widget
                        for widget in app.query_one("#content").children
                        if "stacked-row" in widget.classes and widget.has_class("selected-row")
                    )
                elif mode == "compact":
                    selected_widget = app._age_cells[app._selected_key][0].parent.parent
                else:
                    selected_widget = app._line_widgets[app._selected_key]
                viewport = app.query_one("#content").scrollable_content_region
                self.assertGreaterEqual(selected_widget.region.y, viewport.y)
                self.assertLessEqual(selected_widget.region.bottom, viewport.bottom)

        no_color = DashboardApp(
            FakeReader(
                [
                    _session_state(
                        laptop,
                        rows=[rows[0]],
                        ids=[rows[0]["identity"]["nativeId"]],
                    )
                ]
            ),
            {},
            no_color=True,
            icons=False,
        )
        async with no_color.run_test(size=(32, 12)) as pilot:
            await pilot.pause()
            card = next(
                widget
                for widget in no_color.query_one("#content").children
                if "stacked-row" in widget.classes
            )
            self.assertEqual(card.children[0].children[1].content.plain.strip(), "Unavailable")
            self.assertEqual(card.children[0].children[3].content.plain.strip(), "Unavailable")
            marker = card.children[0].children[0]
            self.assertTrue(marker.content.get_style_at_offset(no_color.console, 0).reverse)

    async def test_four_cell_order_and_age_tick_only_updates_the_age_span(self):
        item = row("alpha", title="Alpha task")
        app = DashboardApp(FakeReader([_session_state(rows=[item], ids=["alpha"])]), {})
        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            header = app.query_one("#content").children[0].content.plain
            self.assertIn("STATUS", header)
            self.assertNotIn("LAST ACTIVE", header)
            self.assertLess(header.index("STATUS"), header.index("SESSION"))
            self.assertLess(header.index("SESSION"), header.index("PROFILE"))
            self.assertLess(header.index("PROFILE"), header.index("WORKSPACE"))

            widget = app._line_widgets[app._selected_key]
            self.assertEqual(widget._cell_values[1], "Working")
            self.assertRegex(widget._cell_values[2], r"^\d+[smhd]$")
            self.assertEqual(widget._cell_values[3], "Alpha task")
            self.assertEqual(widget._cell_values[4], "fixture/default")
            self.assertEqual(widget._cell_values[5], "…/workspace")

            prior_workspace = widget._cell_values[5]
            app._display_now_ms = lambda: 5_000_000
            app._refresh_age_cells()
            self.assertEqual(widget._cell_values[2], app._activity_age(app._all_rows[0], 5_000_000))
            self.assertNotEqual(widget._cell_values[2], "20751d")
            self.assertEqual(widget._cell_values[5], prior_workspace)

        unavailable = row("unavailable", title="Unavailable runtime")
        unavailable["runtime"].update(value="unknown", health="unavailable")
        icon_app = DashboardApp(
            FakeReader([_session_state(rows=[unavailable], ids=["unavailable"])]),
            {},
            icons=True,
        )
        async with icon_app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            self.assertEqual(
                icon_app._line_widgets[icon_app._selected_key]._cell_values[1],
                "× Unavailable",
            )

    async def test_partial_source_keeps_row_status_and_runtime_expiry_keeps_activity_age(self):
        item = row("alpha", title="Alpha task")
        reader = FakeReader([_session_state(rows=[item], ids=["alpha"])])
        original_projection = reader.projection

        def partial_projection(filters, *, mode="list", target=None):
            projection = original_projection(filters, mode=mode, target=target)
            projection.report["sources"][0]["health"] = "partial"
            projection.report["totals"]["completeSources"] = 0
            projection.report["totals"]["partialSources"] = 1
            return projection

        reader.projection = partial_projection
        app = DashboardApp(reader, {})
        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            self.assertIn("partial", app._source_ribbon())
            self.assertEqual(app._line_widgets[app._selected_key]._cell_values[1], "Working")
            prior_age = app._line_widgets[app._selected_key]._cell_values[2]

            expired = row("alpha", title="Alpha task")
            expired["runtime"].update(value="unknown", health="stale", lastKnownValue="running")
            reader.replace([_session_state(rows=[expired], ids=["alpha"])])
            app._refresh_projection()
            await app._paint()
            refreshed = app._line_widgets[app._selected_key]
            self.assertEqual(refreshed._cell_values[1], "Stale")
            self.assertEqual(refreshed._cell_values[2], prior_age)

            phase_expired = row("alpha", title="Alpha task")
            phase_expired["phase"].update(value="unknown", health="stale", lastKnownValue="working")
            reader.replace([_session_state(rows=[phase_expired], ids=["alpha"])])
            app._refresh_projection()
            await app._paint()
            refreshed = app._line_widgets[app._selected_key]
            self.assertEqual(refreshed._cell_values[1], "Stale")
            self.assertEqual(refreshed._cell_values[2], prior_age)

    async def test_compact_and_split_pages_charge_two_lines_per_session(self):
        items = [row(f"id-{index}", title=f"Task {index}") for index in range(20)]
        app = DashboardApp(
            FakeReader([_session_state(rows=items, ids=[item["identity"]["nativeId"] for item in items])]),
            {},
        )
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause()
            self.assertEqual(app._page_size(), 4)
            compact_age = app._age_cells[app._selected_key][0]
            compact_row = compact_age.parent.parent
            self.assertEqual(compact_row.children[0].children[1].content.plain.strip(), "Working")
            self.assertRegex(compact_row.children[0].children[3].content.plain.strip(), r"^\d+[smhd]$")
            self.assertIn("Task 0", compact_row.children[0].children[5].content.plain)
            self.assertIn("fixture/default", compact_row.children[1].children[1].content.plain)
            self.assertIn("workspace", compact_row.children[1].children[3].content.plain)
            await pilot.press("enter")
            await pilot.resize_terminal(120, 30)
            await pilot.pause()
            self.assertTrue(app._split_details())
            self.assertEqual(app._page_size(), 11)
            split_age = app._age_cells[app._selected_key][0]
            split_row = split_age.parent.parent
            self.assertEqual(split_row.children[0].children[1].content.plain.strip(), "Working")
            self.assertRegex(split_row.children[0].children[3].content.plain.strip(), r"^\d+[smhd]$")
            self.assertIn("Task 0", split_row.children[0].children[5].content.plain)

    async def test_split_list_repaints_for_unselected_rows_and_filter_geometry(self):
        source_a = source("fictional-a", host="fictional-a")
        source_b = source("fictional-b", host="fictional-b")
        alpha = row("alpha", title="Alpha selected", host="fictional-a")
        beta = row("beta", title="Beta initial", host="fictional-b")
        reader = FakeReader(
            [
                _session_state(source_a, rows=[alpha], ids=["alpha"]),
                _session_state(source_b, rows=[beta], ids=["beta"]),
            ]
        )
        app = DashboardApp(reader, {"sort": "label"}, icons=True)

        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            self.assertEqual(app._selected_detail_row["identity"]["nativeId"], "alpha")
            selected_key = app._selected_key
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app._split_details())

            changed_beta = row("beta", title="Beta changed", host="fictional-b")
            changed_beta["phase"].update(value="blocked", health="current")
            changed_source_b = source("fictional-b", host="fictional-b", home="analysis")
            reader.replace(
                [
                    _session_state(source_a, rows=[alpha], ids=["alpha"]),
                    _session_state(changed_source_b, rows=[changed_beta], ids=["beta"]),
                ],
                priority=False,
            )
            app._refresh_projection()
            await app._paint()
            await pilot.pause(0.3)

            split_list = app.query_one("#split-list")
            displayed = "\n".join(_widget_text(split_list))
            self.assertIn("Beta changed", displayed)
            self.assertIn("! Blocked", displayed)
            self.assertIn("fictional-b/analysis", displayed)
            self.assertNotIn("Beta initial", displayed)
            self.assertEqual(app._selected_key, selected_key)
            self.assertEqual(app._selected_detail_row["identity"]["nativeId"], "alpha")

            app.filters["query"] = ("Beta changed",)
            app.filters["group"] = "host-home"
            app._refresh_projection()
            await app._paint()
            await pilot.pause(0.3)
            split_list = app.query_one("#split-list")
            displayed = "\n".join(_widget_text(split_list))
            self.assertEqual(
                [item["identity"]["nativeId"] for item in app._visible_rows],
                ["beta"],
            )
            self.assertIn("fictional-b/analysis", displayed)
            self.assertIn("Beta changed", displayed)
            self.assertEqual(app._selected_key, selected_key)
            self.assertTrue(app._selection_hidden)

    async def test_medium_grid_shares_edges_and_right_aligns_mixed_ages(self):
        active = row("grid-active", title="Active medium task")
        unavailable = row("grid-unavailable", title="Unavailable medium task")
        unavailable["activity"].update(health="unavailable", at=None, reason="read_unavailable")
        app = DashboardApp(
            FakeReader(
                [
                    _session_state(
                        rows=[active, unavailable],
                        ids=["grid-active", "grid-unavailable"],
                    )
                ]
            ),
            {},
        )

        async with app.run_test(size=(60, 24)) as pilot:
            await pilot.pause()
            for width in (60, 80, 99):
                await pilot.resize_terminal(width, 24)
                await pilot.pause()
                self.assertEqual(app._layout_mode(), "compact")
                content = app.query_one("#content")
                session_header, workspace_header = content.children[:2]
                self.assertEqual(
                    session_header.children[3].region.x,
                    workspace_header.children[3].region.x,
                )
                rows = [widget for widget in content.children if "compact-row" in widget.classes]
                self.assertEqual(len(rows), 2)
                for entry in rows:
                    first, second = entry.children
                    title = first.children[-1]
                    workspace = second.children[-1]
                    self.assertEqual(title.region.x, workspace.region.x)
                    self.assertEqual(title.region.x, session_header.children[3].region.x)
                    self.assertEqual(first.children[3].region.right, first.children[4].region.x)
                    self.assertEqual(first.children[3].region.right, second.children[2].region.x)
                for age_cell, age, _row in app._age_cells.values():
                    self.assertEqual(
                        age_cell.content.plain.rfind(age) + len(age),
                        age_cell.region.width,
                    )

                if width == 60:
                    active_key = next(
                        key
                        for key, (_widget, _age, entry) in app._age_cells.items()
                        if entry["identity"]["nativeId"] == "grid-active"
                    )
                    age_cell, previous, entry = app._age_cells[active_key]
                    with patch.object(app, "_display_now_ms", return_value=1_700_000_000_000):
                        entry["activity"].update(at=1_699_999_000_000, health="current")
                        app._refresh_age_cells()
                    refreshed = app._age_cells[active_key][1]
                    self.assertNotEqual(refreshed, previous)
                    self.assertEqual(
                        age_cell.content.plain.rfind(refreshed) + len(refreshed),
                        age_cell.region.width,
                    )

    async def test_100_column_table_survives_resize_with_qualified_status_and_exact_selection(self):
        active = row("boundary-active", title="Long title " + "界" * 40)
        unavailable = row("boundary-unavailable", title="Boundary task")
        unavailable["runtime"].update(value="unknown", health="unavailable", reason="read_unavailable")
        unavailable["activity"].update(at=None, health="unavailable", reason="read_unavailable")
        app = DashboardApp(
            FakeReader([_session_state(rows=[active, unavailable], ids=["boundary-active", "boundary-unavailable"])]),
            {},
            icons=True,
        )
        async with app.run_test(size=(99, 24)) as pilot:
            await pilot.pause()
            await pilot.press("end")
            selected = app._selected_key
            for width, height, mode in ((99, 24, "compact"), (100, 24, "full"), (106, 75, "full"), (100, 16, "full"), (99, 16, "compact")):
                await pilot.resize_terminal(width, height)
                await pilot.pause()
                self.assertEqual(app._layout_mode(), mode)
                self.assertEqual(app._selected_key, selected)
                self.assertIn(selected, {app._row_key(item) for item in app._page_rows})
                self.assertEqual(app._report["totals"]["selectedSources"], 1)
                if mode == "full":
                    self.assertLessEqual(2 + sum(app._column_widths(width - 4)), width - 4)
                    line = app._line_widgets[selected]
                    self.assertEqual(line._cell_values[1], "× Unavailable")
                    self.assertEqual(line._cell_values[2], "Unavailable")
                    self.assertEqual(line.content.plain.count("Unavailable"), 2)
                    self.assertLessEqual(line.content.cell_len, line.region.width)

    async def test_small_card_keeps_full_unavailable_status_and_age_at_32_columns(self):
        item = row("small-unavailable", title="Small card")
        item["runtime"].update(value="unknown", health="unavailable", reason="read_unavailable")
        item["activity"].update(at=None, health="unavailable", reason="read_unavailable")
        app = DashboardApp(
            FakeReader([_session_state(rows=[item], ids=["small-unavailable"])]),
            {},
            icons=True,
        )
        async with app.run_test(size=(32, 12)) as pilot:
            await pilot.pause()
            card = next(
                widget
                for widget in app.query_one("#content").children
                if "stacked-row" in widget.classes
            )
            status_age = card.children[0]
            self.assertEqual(status_age.children[1].content.plain.strip(), "× Unavailable")
            self.assertEqual(status_age.children[3].content.plain.strip(), "Unavailable")
            self.assertEqual(status_age.children[2].region.width, 2)

        numeric = row("small-numeric", title="Numeric card")
        numeric_app = DashboardApp(
            FakeReader([_session_state(rows=[numeric], ids=["small-numeric"])]),
            {},
            icons=True,
        )
        async with numeric_app.run_test(size=(40, 12)) as pilot:
            await pilot.pause()
            age_cell, age, _entry = numeric_app._age_cells[numeric_app._selected_key]
            self.assertNotEqual(age, "Unavailable")
            self.assertGreater(age_cell.region.width, len(age))
            self.assertEqual(
                age_cell.content.plain.rfind(age) + len(age),
                age_cell.region.width,
            )

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

        async with app.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            for size in ((120, 30), (80, 24), (60, 16)):
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
                    selected_text = selected_widget.children[0].children[5].content.plain
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
            self.assertTrue(compact.has_class("selected-row"))
            self.assertFalse(compact.children[0].has_class("selected-row"))
            self.assertFalse(compact.children[1].has_class("selected-row"))
            self.assertTrue(compact.children[0].styles.background.is_transparent)
            self.assertTrue(compact.children[1].styles.background.is_transparent)

            await pilot.press("enter")
            await pilot.resize_terminal(130, 40)
            await pilot.pause()
            self.assertTrue(app._split_details())
            selected = next(
                widget
                for widget in app.query_one("#split-list").children
                if widget.has_class("selected-row")
            )
            self.assertIn(app._selected_label, selected.children[0].children[5].content.plain)
            self.assertIn("Details · ↑↓ scroll · P pins · Tab list", app._footer_text())
            self.assertTrue(app.query_one("#split-detail").has_class("details-focused"))
            await pilot.press("tab")
            await pilot.pause()
            self.assertIn("List · ↑↓ select · p pin · P pins · Tab details", app._footer_text())
            await pilot.resize_terminal(100, 40)
            await pilot.pause()
            self.assertIn("↑↓ scroll · P pins · Esc", app._footer_text())

        no_color = DashboardApp(
            FakeReader([_session_state(rows=[row("alpha")], ids=["alpha"])]), {}, no_color=True
        )
        async with no_color.run_test(size=(110, 24)) as pilot:
            await pilot.pause()
            selected = no_color._line_widgets[no_color._selected_key]
            self.assertFalse(selected.has_class("selected-row"))
            self.assertTrue(
                selected.content.get_style_at_offset(no_color.console, 0).reverse
            )
            age_offset = selected.content.plain[: 2 + selected._cell_widths[1]].rfind(
                selected._cell_values[2]
            )
            age_style = no_color._line_widgets[no_color._selected_key].content.get_style_at_offset(
                no_color.console, age_offset
            )
            self.assertIsNone(age_style.color)

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
            self.assertIn("Status: Working", joined)
            self.assertRegex(joined, r"Last active: \d+[smhd]")
            self.assertIn("Profile: fixture/default", joined)
            self.assertIn("Workspace: …/workspace", joined)
            self.assertIn("Activity evidence: current", joined)
            self.assertIn("Raw observation facts", joined)
            self.assertIn("Runtime: running", joined)
            self.assertIn("Phase: working", joined)
            self.assertIn("Configured profile: default", joined)
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
            self.assertIn("WORKSPACE", header)
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
            self.assertIn("…/workspace", rows["current-none"])
            self.assertIn("…/workspace", rows["stale-repo"])
            self.assertNotIn("old-root", rows["stale-repo"])
            self.assertIn("unknown", rows["missing-workspace"])

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

    async def test_keyed_repository_search_tracks_same_identity_updates_and_recovery(self):
        def repository_row(root):
            item = row("stable-search-id", title="Stable identity")
            item["workspace"]["repo"] = {
                "root": root,
                "commonDir": "/synthetic/repositories/shared.git",
                "relativePath": "src",
            }
            return item

        def state_with_root(root):
            return _session_state(
                rows=[repository_row(root)], ids=["stable-search-id"]
            )

        reader = FakeReader([state_with_root("/synthetic/worktrees/before")])
        app = DashboardApp(reader, {})

        async def wait_for_reader_projection():
            async with asyncio.timeout(1):
                while (
                    app._projection is None
                    or app._projection.revision != reader.revision
                ):
                    await asyncio.sleep(0.005)

        async with app.run_test(size=(100, 24)) as pilot:
            try:
                await pilot.pause()
                selected_key = app._selected_key
                selected_identity = dict(app._selected_identity)

                await pilot.press("/", "ctrl+a")
                await pilot.press("a", "f", "t", "e", "r")
                await pilot.pause(0.2)
                self.assertEqual(app.filters["query"], ("after",))
                self.assertEqual(app._visible_rows, [])
                self.assertEqual(app._report["totals"]["members"], 1)
                self.assertEqual(len(app._report["sources"]), 1)
                self.assertTrue(app._selection_hidden)
                self.assertTrue(app._selection_available)
                await pilot.press("enter")

                reader.replace([state_with_root("/synthetic/worktrees/after")])
                await wait_for_reader_projection()
                self.assertEqual(len(app._visible_rows), 1)
                self.assertEqual(app._selected_key, selected_key)
                self.assertEqual(app._selected_identity, selected_identity)
                self.assertFalse(app._selection_hidden)

                reader.replace([state_with_root("/synthetic/worktrees/elsewhere")])
                await wait_for_reader_projection()
                self.assertEqual(app._visible_rows, [])
                self.assertTrue(app._selection_hidden)
                self.assertTrue(app._selection_available)

                reader.replace([state_with_root("/synthetic/worktrees/after")])
                await wait_for_reader_projection()
                self.assertEqual(len(app._visible_rows), 1)
                self.assertEqual(app._selected_key, selected_key)
                self.assertEqual(app._selected_identity, selected_identity)
                self.assertFalse(app._selection_hidden)
            finally:
                await app.stop_updates()

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
            await pilot.press("right")
            await pilot.pause()
            displayed = "\n".join(
                line for widget in app.query_one("#content").children for line in _widget_text(widget)
            )
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
            narrow._filter_dimension_index = 6
            await narrow._paint()
            heading = str(narrow.query_one("#content").children[0].content)
            self.assertIn("[Phase]", heading)
            self.assertIn("7/8", heading)

    async def test_status_filter_uses_qualified_facts_and_ands_with_cached_filters(self):
        from agent_observer.terminal.dashboard_view import SavedView
        from agent_observer.terminal.model import identity_tuple
        from agent_observer.terminal.render import _status_text

        route = source("laptop-default", host="laptop", home="default")
        offline = source("offline-default", host="offline", home="default")
        status_names = (
            "Working",
            "Ready",
            "Blocked",
            "Inactive",
            "Unknown",
            "Stale",
            "Unavailable",
        )
        rows = [
            _row_with_qualified_status(f"{index}-{status.lower()}", status, host="laptop")
            for index, status in enumerate(status_names)
        ]
        reader = FakeReader(
            [
                _session_state(
                    route,
                    rows=rows,
                    ids=[item["identity"]["nativeId"] for item in rows],
                ),
                _session_state(offline, lifecycle="failed", baseline=False),
            ]
        )
        saved = SavedView((identity_tuple(rows[0]["identity"]),))
        app = DashboardApp(reader, {"status": ("Blocked",)}, saved_view=saved)

        async with app.run_test(size=(110, 30)) as pilot:
            await pilot.pause()
            self.assertEqual(app._filter_options("status"), status_names)
            self.assertEqual(app._status_filter, set(status_names))
            self.assertNotIn("status", app.filters)
            self.assertNotIn("status", app._projection_filters())
            self.assertNotIn("status", app.saved_view.__dataclass_fields__)
            self.assertEqual(
                {
                    item["identity"]["nativeId"]: _status_text(item)
                    for item in app._all_rows
                },
                {
                    item["identity"]["nativeId"]: status
                    for item, status in zip(rows, status_names, strict=True)
                },
            )
            self.assertEqual(len(app._visible_rows), len(status_names))
            self.assertEqual(app._report["totals"]["selectedSources"], 2)
            self.assertIn("Sources 2", app._source_ribbon())
            self.assertIn("offline/Default unavailable", app._source_ribbon())

            for status, item in zip(status_names, rows, strict=True):
                app._status_filter = {status}
                app._refresh_projection()
                self.assertEqual(
                    [row_["identity"]["nativeId"] for row_ in app._visible_rows],
                    [item["identity"]["nativeId"]],
                )

            app._status_filter = {"Working", "Ready"}
            app._refresh_projection()
            self.assertEqual(
                {item["identity"]["nativeId"] for item in app._visible_rows},
                {rows[0]["identity"]["nativeId"], rows[1]["identity"]["nativeId"]},
            )
            app.filters["runtime"] = ("running",)
            app.filters["phase"] = ("waiting",)
            app._refresh_projection()
            self.assertEqual(
                [item["identity"]["nativeId"] for item in app._visible_rows],
                [rows[1]["identity"]["nativeId"]],
            )
            self.assertEqual(app._selected_identity, rows[0]["identity"])
            self.assertTrue(app._selection_hidden)
            self.assertEqual(app._report["totals"]["selectedSources"], 2)
            self.assertIn("offline/Default unavailable", app._source_ribbon())
            self.assertNotIn(rows[0]["identity"]["nativeId"], {
                item["identity"]["nativeId"] for item in app._visible_rows
            })

    async def test_status_all_none_reset_and_narrow_filter_panel(self):
        rows = [
            _row_with_qualified_status("working", "Working"),
            _row_with_qualified_status("ready", "Ready"),
        ]
        app = DashboardApp(
            FakeReader([_session_state(rows=rows, ids=["working", "ready"])]), {}
        )

        async with app.run_test(size=(32, 12)) as pilot:
            await pilot.pause()
            await pilot.press("f")
            await pilot.pause()
            panel = " ".join(
                line
                for widget in app.query_one("#content").children
                for line in _widget_text(widget)
            )
            self.assertIn("[Status] 1/8", panel)
            self.assertIn("Working", panel)
            self.assertIn(
                "a selects none or restores all statuses", " ".join(panel.split())
            )
            self.assertLessEqual(Text(app._footer_text()).cell_len, 28)

            await pilot.press("a")
            await pilot.pause(0.3)
            self.assertEqual(app._status_filter, set())
            self.assertEqual(app._visible_rows, [])
            self.assertIn("status=none", app._toolbar_text())
            self.assertIn("No statuses selected", app._status_text())
            self.assertIn("Status none", app._header_text())

            await pilot.press("space")
            await pilot.pause(0.3)
            self.assertEqual(app._status_filter, {"Working"})
            self.assertEqual(
                [item["identity"]["nativeId"] for item in app._visible_rows],
                ["working"],
            )
            await pilot.press("a")
            await pilot.pause(0.3)
            self.assertEqual(app._status_filter, {
                "Working", "Ready", "Blocked", "Inactive", "Unknown", "Stale", "Unavailable"
            })
            await pilot.press("a")
            await pilot.pause(0.3)
            self.assertEqual(app._status_filter, set())

            await pilot.press("r")
            await pilot.pause(0.3)
            self.assertEqual(len(app._visible_rows), 2)
            self.assertEqual(
                app._status_filter,
                {"Working", "Ready", "Blocked", "Inactive", "Unknown", "Stale", "Unavailable"},
            )

    async def test_status_filter_revokes_working_after_update_and_reclassifies_expiry(self):
        from agent_observer.terminal.render import _status_text

        working = _row_with_qualified_status("alpha", "Working")
        reader = FakeReader([_session_state(rows=[working], ids=["alpha"])])
        app = DashboardApp(reader, {})

        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            app._status_filter = {"Working"}
            app._refresh_projection()
            self.assertEqual(len(app._visible_rows), 1)
            identity_before = dict(app._selected_identity)

            blocked = _row_with_qualified_status("alpha", "Blocked")
            reader.replace([_session_state(rows=[blocked], ids=["alpha"])])
            app._refresh_projection()
            self.assertEqual(app._visible_rows, [])
            self.assertEqual(app._selected_identity, identity_before)
            self.assertTrue(app._selection_hidden)

            expired = _row_with_qualified_status("alpha", "Working")
            expired["phase"].update(
                value="unknown", health="stale", lastKnownValue="working"
            )
            reader.replace([_session_state(rows=[expired], ids=["alpha"])])
            app._status_filter = {"Stale"}
            app._refresh_projection()
            self.assertEqual(len(app._visible_rows), 1)
            self.assertEqual(_status_text(app._visible_rows[0]), "Stale")

    async def test_status_filter_withdraws_working_on_quiet_field_expiry(self):
        from test_dashboard_watch import Harness, until
        from test_terminal_sources import terminal_source

        from agent_observer.terminal.watch import PersistentSources

        harness = Harness()
        harness.field_deadline = 1100
        dependencies = harness.dependencies()
        guard_type = dependencies["PreparedWorkingSetAgentWatch"]

        class ExpiringRuntimeGuard(guard_type):
            def read(self, now, clock):
                value = super().read(now, clock)
                if now >= harness.field_deadline:
                    # Model the public facade masking expired runtime support.
                    for item in value.members:
                        item["runtime"].update(
                            value="unknown", health="stale", lastKnownValue="running"
                        )
                return value

        dependencies["PreparedWorkingSetAgentWatch"] = ExpiringRuntimeGuard
        reader = PersistentSources(
            (terminal_source("default", mesh_source="working"),),
            dependencies=dependencies,
            setup_interval=0,
        )
        await reader.start()
        try:
            await harness.baseline(reader)
            app = DashboardApp(reader, {})
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                selected = dict(app._selected_identity)
                await pilot.press("f", "a", "space", "escape")
                await pilot.pause(0.3)
                self.assertEqual(len(app._visible_rows), 1)
                frames = reader.metrics["frames"]

                harness.now = harness.field_deadline
                reader.refresh_due()
                await until(lambda: not app._visible_rows)
                await pilot.pause()

                self.assertEqual(reader.metrics["frames"], frames)
                self.assertEqual(app._selected_identity, selected)
                self.assertTrue(app._selection_hidden)
                self.assertEqual(app._report["totals"]["members"], 1)
                self.assertEqual(len(app._report["sources"]), 1)
                self.assertNotEqual(app._report["totals"]["state"], "complete-empty")
        finally:
            await reader.close()

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
            self.assertIn("Configured profile: default", joined)
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
            app._filter_dimension_index = 4  # membership
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
            self.assertIn("Sources 2", summary)
            self.assertIn("unavailable 1", summary)
            self.assertIn("1 match", app._header_text())
            self.assertIn("uncertain", app._header_text())
            self.assertFalse(app.query_one("#toolbar").display)
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
