"""Read-only, keyboard-driven view over persistent working-set projections."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime
from typing import Any

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.timer import Timer
from textual.widgets import Input, Static

from .dashboard_output import BoundedLinuxDriver
from .model import IDENTITY_FIELDS, identity_tuple, safe_metadata
from .render import _activity_text

_MEMBERSHIPS = ("active", "recent", "uncertain", "nonmember")
_RUNTIMES = ("running", "parked", "unknown")
_PHASES = ("working", "blocked", "waiting", "unknown")
_FILTER_DIMENSIONS = ("source", "host", "home", "membership", "runtime", "phase", "kind")
_SINGLE_ROW_MIN_WIDTH = 80
_SPLIT_WIDTH = 120
_SPLIT_HEIGHT = 30
_WIDE_COLUMNS_WIDTH = 140
_COMPACT_MIN_WIDTH = 60
_COMPACT_MIN_HEIGHT = 16
_MAX_PAGE_ROWS = 200
_MIN_PAINT_INTERVAL = 0.25


class SessionLine(Static):
    """One terminal row, with bounded literal cells and no per-cell DOM nodes."""

    def __init__(self, values, widths, *, selected, header, style_for, surface_selection=True):
        self._cell_values = list(values)
        self._cell_widths = widths
        self._selected_row = selected
        self._header_row = header
        self._surface_selection = surface_selection
        self._style_for_cell = style_for
        classes = ["row"]
        if header:
            classes.append("table-heading")
        if selected and surface_selection:
            classes.append("selected-row")
        super().__init__(self._line(), markup=False, classes=" ".join(classes))

    def _line(self) -> Text:
        line = Text(no_wrap=True, overflow="ellipsis")
        for index, (value, width) in enumerate(
            zip(self._cell_values, self._cell_widths, strict=True)
        ):
            if index == 0 and not self._header_row:
                value = "> " if self._selected_row else "  "
            cell = Text(
                value,
                style=self._style_for_cell(index, value, self._selected_row, self._header_row),
            )
            cell.truncate(max(1, width - (1 if width > 2 else 0)), overflow="ellipsis")
            cell.pad_right(max(0, width - cell.cell_len))
            line.append_text(cell)
        return line

    def select_row(self, selected: bool) -> None:
        if selected != self._selected_row:
            self._selected_row = selected
            if selected and self._surface_selection:
                self.add_class("selected-row")
            elif self._surface_selection:
                self.remove_class("selected-row")
            self.update(self._line())

    def update_age(self, value: str) -> None:
        self._cell_values[-1] = value
        self.update(self._line())


class DashboardApp(App[None]):
    """Persistent TUI that never owns the reader or its terminal lifetime."""

    TITLE = "Agent Observer"
    ENABLE_COMMAND_PALETTE = False
    ALLOW_SELECT = False
    BINDINGS = []
    CSS_PATH = "dashboard.tcss"

    def __init__(
        self,
        reader,
        filters: dict,
        *,
        no_color: bool = False,
        icons: bool = False,
        driver_class=None,
    ) -> None:
        super().__init__(
            driver_class=driver_class or BoundedLinuxDriver,
            ansi_color=True if no_color else None,
        )
        self.animation_level = "none"
        self.reader = reader
        self.no_color = bool(no_color)
        self.icons = bool(icons)
        self.filters = self._copy_filters(filters)
        self._startup_filters = self._copy_filters(self.filters)
        self._empty_dimensions: set[str] = set()

        self._projection = None
        self._report: dict[str, Any] = {}
        self._all_rows: list[dict] = []
        self._visible_rows: list[dict] = []
        self._page_rows: list[dict] = []
        self._age_cells: dict[tuple[str, ...], tuple[Static, str, dict]] = {}
        self._line_widgets: dict[tuple[str, ...], SessionLine] = {}
        self._painted_selection = None
        self._source_age_cells: dict[str, tuple[Static, str]] = {}
        self._selection_initialized = False
        self._selected_key: tuple[str, ...] | None = None
        self._selected_identity: dict | None = None
        self._selected_source_id: str | None = None
        self._selected_label = ""
        self._selected_detail_row: dict | None = None
        self._selection_hidden = False
        self._selection_available = False
        self._view = "list"
        self._return_view = "list"
        self._overlay: str | None = None
        self._help_return_overlay: str | None = None
        self._focus = "list"
        self._focused_source_id: str | None = None
        self._filter_dimension_index = 0
        self._filter_option_index = 0
        self._scroll_offset = 0
        self._message = ""
        self._search_open = False
        self._search_original: tuple[str, ...] = ()
        self._search_timer: Timer | None = None
        self._projection_timer: Timer | None = None
        self._render_timer: Timer | None = None
        self._projection_requested = False
        self._last_projection_at = 0.0
        self._last_paint_at = 0.0
        self._last_age_wall_ms = 0
        self._age_anchor_monotonic = time.monotonic()
        self._update_tasks: list[asyncio.Task] = []
        self._updates_stopped = False
        self._mounted = False
        self._render_values: dict[str, str] = {}
        self._content = None
        self._content_signature_value = None

    @staticmethod
    def _copy_filters(filters: dict) -> dict:
        copied = {}
        for key, value in (filters or {}).items():
            copied[key] = tuple(value) if isinstance(value, (tuple, list)) else value
        copied.setdefault("source", ())
        copied.setdefault("host", ())
        copied.setdefault("home", ())
        copied.setdefault("membership", ())
        copied.setdefault("runtime", ())
        copied.setdefault("phase", ())
        copied.setdefault("query", ())
        copied.setdefault("includeChildren", False)
        copied.setdefault("includeSystem", False)
        copied.setdefault("sort", "activity")
        copied.setdefault("group", "none")
        return copied

    def compose(self) -> ComposeResult:
        yield Static("Agent Observer", id="header", markup=False)
        yield Static("Sources: connecting", id="sources", markup=False)
        yield Static(
            "Search off · default filters · activity · no grouping", id="toolbar", markup=False
        )
        yield Input(placeholder="Search sessions", max_length=256, id="search")
        yield VerticalScroll(id="content")
        yield Static("", id="status", markup=False)
        yield Static(
            "↑↓ move · Enter details · / find · f filters · s sources · ? help · q quit",
            id="footer",
            markup=False,
        )

    async def on_mount(self) -> None:
        self._mounted = True
        self._content = self.query_one("#content", VerticalScroll)
        search = self.query_one("#search", Input)
        search.can_focus = False
        search.cursor_blink = False
        self.set_focus(None)
        if self._updates_stopped:
            return
        self.app_resume_signal.subscribe(self, self._resume_refresh)
        self._refresh_projection(initial=True)
        self._update_tasks = [
            asyncio.create_task(self._reader_updates(), name="dashboard-reader-updates"),
            asyncio.create_task(self._age_updates(), name="dashboard-age-updates"),
        ]
        self._request_render(immediate=True)

    async def on_unmount(self) -> None:
        self._mounted = False
        await self.stop_updates()

    def request_stop_updates(self) -> None:
        """Synchronously prevent new app updates before reader revocation."""
        if self._updates_stopped:
            return
        self._updates_stopped = True
        for attribute in ("_search_timer", "_projection_timer", "_render_timer"):
            timer = getattr(self, attribute)
            if timer is not None:
                timer.stop()
                setattr(self, attribute, None)
        self._projection_requested = False

    async def stop_updates(self) -> None:
        """Stop only the app-owned reader notification and age tasks."""
        self.request_stop_updates()
        tasks = tuple(self._update_tasks)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._update_tasks = [task for task in self._update_tasks if not task.done()]

    async def _reader_updates(self) -> None:
        changed = self.reader.changed
        while True:
            await changed.wait()
            if self._updates_stopped:
                return
            changed.clear()
            if self.reader.requires_priority_refresh(self._projection):
                self._withdraw_visible_projection()
                if self._projection_timer is not None:
                    self._projection_timer.stop()
                    self._projection_timer = None
                self._projection_requested = False
                self._refresh_projection()
                if self._projection is not None and self.reader.is_current(self._projection):
                    self._paint_chrome()
                self._request_render(immediate=True)
            else:
                self._queue_projection()

    async def _age_updates(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            if self._updates_stopped:
                return
            self.reader.refresh_due()
            if not self._ensure_current_projection():
                continue
            self._refresh_age_cells()
            self._refresh_source_countdowns()

    def _ensure_current_projection(self) -> bool:
        projection = self._projection
        if projection is not None and self.reader.is_current(projection):
            return True
        priority = self.reader.requires_priority_refresh(projection)
        if priority:
            self._withdraw_visible_projection()
        self._refresh_projection()
        if self._projection is not None and self.reader.is_current(self._projection):
            if priority:
                self._paint_chrome()
            self._rebind_age_cells()
            self._request_render(immediate=True)
            return True
        self._queue_projection()
        self._request_render(immediate=True)
        return False

    def _projection_filters(self) -> dict:
        return self._copy_filters(self.filters)

    def _refresh_projection(self, *, initial: bool = False) -> None:
        projection = self.reader.projection(self._projection_filters())
        if not self.reader.is_current(projection):
            self._discard_projection()
            self._projection_requested = True
            return
        self._last_projection_at = time.monotonic()
        self._apply_projection(projection)
        if self._projection is not None and self._message == "Refreshing current source state.":
            self._message = ""

    def _queue_projection(self) -> None:
        if self._updates_stopped:
            return
        self._projection_requested = True
        if self._projection_timer is not None:
            return
        delay = max(0.001, _MIN_PAINT_INTERVAL - (time.monotonic() - self._last_projection_at))
        self._projection_timer = self.set_timer(delay, self._run_queued_projection)

    async def _run_queued_projection(self) -> None:
        self._projection_timer = None
        if not self._projection_requested or self._updates_stopped:
            return
        self._projection_requested = False
        self._refresh_projection()
        self._request_render(cosmetic=True)
        if self._projection_requested:
            self._queue_projection()

    def _apply_projection(self, projection) -> None:
        if not self.reader.is_current(projection):
            self._discard_projection()
            self._projection_requested = True
            return
        self._projection = projection
        self._report = projection.report
        self._all_rows = self._rows_from_report(self._report)
        self._visible_rows = self._filter_presentation_rows(self._all_rows)
        self._last_age_wall_ms = self._report_wall_ms(self._report)
        self._age_anchor_monotonic = time.monotonic()

        if not self._selection_initialized and self._visible_rows:
            self._selection_initialized = True
            self._select_row(self._visible_rows[0], repaint=False)
        elif self._selected_key is not None:
            current = self._find_row(self._all_rows, self._selected_key)
            if current is None:
                current = self._find_identity_row(self._all_rows, self._selected_identity)
                if current is not None:
                    self._selected_key = self._row_key(current)
                    self._selected_source_id = self._selected_key[0]
            if current is not None:
                self._selected_detail_row = current
                self._selected_label = self._safe(current.get("label"))
                self._selection_available = True
                self._selection_hidden = (
                    self._find_row(self._visible_rows, self._selected_key) is None
                )
            else:
                self._resolve_pinned_selection(projection)

        self._sync_page_rows()

    def _resolve_pinned_selection(self, list_projection) -> None:
        identity = self._selected_identity
        if identity is None:
            self._selected_detail_row = None
            self._selection_available = False
            self._selection_hidden = False
            return
        target_projection = self.reader.projection(
            self._projection_filters(), mode="show", target=identity
        )
        if not self.reader.is_current(target_projection):
            self._selected_detail_row = None
            self._selection_available = False
            self._selection_hidden = False
            self._projection_requested = True
            return
        if target_projection.revision != list_projection.revision:
            self._selected_detail_row = None
            self._selection_available = False
            self._selection_hidden = False
            self._projection_requested = True
            return
        rows = self._rows_from_report(target_projection.report)
        current = self._find_row(rows, self._selected_key)
        if current is None:
            current = self._find_identity_row(rows, self._selected_identity)
        self._selection_hidden = current is not None
        self._selection_available = current is not None
        self._selected_detail_row = current
        if current is not None:
            self._selected_key = self._row_key(current)
            self._selected_source_id = self._selected_key[0]
            self._selected_label = self._safe(current.get("label"))

    @staticmethod
    def _find_identity_row(rows: list[dict], identity: dict | None) -> dict | None:
        if identity is None:
            return None
        try:
            wanted = identity_tuple(identity)
        except (KeyError, TypeError, ValueError):
            return None
        matches = []
        for row in rows:
            try:
                if identity_tuple(row.get("identity")) == wanted:
                    matches.append(row)
            except (KeyError, TypeError, ValueError):
                continue
        return matches[0] if len(matches) == 1 else None

    def _discard_projection(self) -> None:
        self._projection = None
        self._report = {}
        self._all_rows = []
        self._visible_rows = []
        self._page_rows = []
        self._selected_detail_row = None
        self._selection_available = False
        self._selection_hidden = False
        self._age_cells = {}
        self._line_widgets = {}
        self._content_signature_value = None
        self._source_age_cells = {}
        self._message = "Refreshing current source state."

    def _withdraw_visible_projection(self) -> None:
        """Withdraw authority without waiting for framework widget teardown."""
        self._discard_projection()
        if not self._mounted or self._updates_stopped:
            return
        container = self._content or self.query_one("#content", VerticalScroll)
        container.display = False
        self._paint_chrome()

    @staticmethod
    def _rows_from_report(report: dict) -> list[dict]:
        rows = [
            *report.get("sessions", ()),
            *report.get("uncertain", ()),
            *report.get("nonmembers", ()),
        ]
        return [row for row in rows if type(row) is dict and type(row.get("identity")) is dict]

    @staticmethod
    def _row_key(row: dict) -> tuple[str, ...]:
        return (str(row.get("source", {}).get("id", "")), *identity_tuple(row["identity"]))

    @staticmethod
    def _find_row(rows: list[dict], key: tuple[str, ...] | None) -> dict | None:
        if key is None:
            return None
        for row in rows:
            try:
                if DashboardApp._row_key(row) == key:
                    return row
            except (KeyError, TypeError, ValueError):
                continue
        return None

    def _filter_presentation_rows(self, rows: list[dict]) -> list[dict]:
        if self._empty_dimensions:
            return []
        result = []
        source_filter = set(self.filters.get("source", ()))
        host_filter = set(self.filters.get("host", ()))
        home_filter = set(self.filters.get("home", ()))
        for row in rows:
            source = row.get("source", {})
            if source_filter and source.get("id") not in source_filter:
                continue
            if host_filter and source.get("host") not in host_filter:
                continue
            if home_filter and source.get("home") not in home_filter:
                continue
            result.append(row)
        return result

    def _select_row(self, row: dict, *, repaint: bool = True) -> None:
        try:
            key = self._row_key(row)
            identity = {field: row["identity"][field] for field in IDENTITY_FIELDS}
        except (KeyError, TypeError, ValueError):
            return
        self._selection_initialized = True
        self._selected_key = key
        self._selected_identity = identity
        self._selected_source_id = key[0]
        self._selected_label = self._safe(row.get("label"))
        self._selected_detail_row = row
        self._selection_hidden = False
        self._selection_available = True
        self._scroll_offset = 0
        self._sync_page_rows()
        if repaint:
            self._request_render()

    def _clear_selection(self) -> None:
        self._selection_initialized = True
        self._selected_key = None
        self._selected_identity = None
        self._selected_source_id = None
        self._selected_label = ""
        self._selected_detail_row = None
        self._selection_hidden = False
        self._selection_available = False
        self._request_render()

    def _layout_mode(self) -> str:
        width, height = self.size.width, self.size.height
        if width < _COMPACT_MIN_WIDTH or height < _COMPACT_MIN_HEIGHT:
            return "tiny"
        if width < _SINGLE_ROW_MIN_WIDTH or height < 24:
            return "compact"
        return "full"

    def _split_details(self) -> bool:
        return (
            self._view == "details"
            and self._overlay is None
            and self.size.width >= _SPLIT_WIDTH
            and self.size.height >= _SPLIT_HEIGHT
        )

    def _page_size(self) -> int:
        mode = self._layout_mode()
        line_budget = max(1, self.size.height - 5 - int(self._search_open))
        row_height = 2 if mode == "compact" else 1
        header_lines = int(mode == "full")
        if self._split_details():
            header_lines = 1
        group_lines = 0
        if self.filters.get("group") == "host-home":
            group_lines = len(
                {
                    (row.get("source", {}).get("host"), row.get("source", {}).get("home"))
                    for row in self._visible_rows
                }
            )
        page_line = int(bool(self._visible_rows))
        available = max(1, (line_budget - header_lines - group_lines - page_line) // row_height)
        return max(1, min(_MAX_PAGE_ROWS, available))

    def _sync_page_rows(self) -> None:
        if not self._visible_rows:
            self._page_rows = []
            return
        page_size = self._page_size()
        selected_index = next(
            (
                i
                for i, row in enumerate(self._visible_rows)
                if self._row_key(row) == self._selected_key
            ),
            0,
        )
        page_start = selected_index // page_size * page_size
        self._page_rows = self._visible_rows[page_start : page_start + page_size]

    def _request_render(self, *, immediate: bool = True, cosmetic: bool = False) -> None:
        if not self._mounted or self._updates_stopped:
            return
        immediate = immediate and not cosmetic
        if self._render_timer is not None:
            if not immediate:
                return
            self._render_timer.stop()
            self._render_timer = None
        delay = (
            0.001
            if immediate
            else max(0.001, _MIN_PAINT_INTERVAL - (time.monotonic() - self._last_paint_at))
        )
        self._render_timer = self.set_timer(delay, self._paint)

    async def _paint(self) -> None:
        self._render_timer = None
        if not self._mounted or self._updates_stopped:
            return
        if not self._ensure_current_projection():
            await self._paint_pending()
            return
        self._sync_page_rows()
        render_projection = self._projection
        signature = self._content_signature()
        content_changed = signature != self._content_signature_value
        children = self._content_widgets() if content_changed else []
        container = self._content or self.query_one("#content", VerticalScroll)
        if content_changed:
            await container.remove_children()
            if not self._mounted or self._updates_stopped:
                return
            if render_projection is not None and not self.reader.is_current(render_projection):
                if not self._ensure_current_projection():
                    await self._paint_pending()
                    return
                self._sync_page_rows()
                render_projection = self._projection
                signature = self._content_signature()
                children = self._content_widgets()
            if render_projection is not None and self.reader.is_current(render_projection):
                self._rebind_age_cells()
        elif not self._ensure_current_projection():
            await self._paint_pending()
            return

        # This is the paint fence: no cached row or health document is applied
        # until the reader confirms this exact projection is still current.
        if render_projection is not None and not self.reader.is_current(render_projection):
            self._discard_projection()
            await self._paint_pending()
            return
        self._paint_chrome()
        if content_changed:
            if children:
                await container.mount(*children)
                if not self._mounted or self._updates_stopped:
                    return
            self._content_signature_value = signature
            self._rebind_age_cells()
        else:
            self._rebind_age_cells()
            for key in (self._painted_selection, self._selected_key):
                if key in self._line_widgets:
                    self._line_widgets[key].select_row(key == self._selected_key)
            self._refresh_age_cells()
            self._refresh_source_countdowns()
        if render_projection is not None and not self.reader.is_current(render_projection):
            await self._paint_pending()
            self._queue_projection()
            return
        container.display = True
        self._painted_selection = self._selected_key
        self._last_paint_at = time.monotonic()

    async def _paint_pending(self) -> None:
        """Clear invalid cached facts and paint an explicit no-current-state view."""
        self._withdraw_visible_projection()
        if not self._mounted or self._updates_stopped:
            return
        container = self._content or self.query_one("#content", VerticalScroll)
        await container.remove_children()
        if not self._mounted or self._updates_stopped:
            return
        # Reader updates may replace the report while framework operations
        # yield. This fallback must never pick up facts from that mutable state.
        if self._overlay == "help":
            children = self._overlay_widgets()
        elif self._layout_mode() == "tiny":
            children = self._plain_lines(
                ["Resize to at least 60×16 to view sessions.", "Use ? for keys · q quits."]
            )
        else:
            children = self._plain_lines(
                ["Waiting for a current projection; coverage is not yet known."]
            )
        if children:
            await container.mount(*children)
            if not self._mounted or self._updates_stopped:
                return
        container.display = True
        self._content_signature_value = None
        self._last_paint_at = time.monotonic()

    def _paint_chrome(self) -> None:
        if not self._mounted or self._updates_stopped:
            return
        self._update_static("header", self._header_text())
        self._update_static("sources", self._source_ribbon())
        self._update_static("toolbar", self._toolbar_text())
        self._update_static("status", self._status_text())
        self._update_static("footer", self._footer_text())

    def _update_static(self, widget_id: str, value: str) -> None:
        if self._render_values.get(widget_id) == value:
            return
        text = self._as_text(value)
        if widget_id == "footer":
            for match in re.finditer(r"(?:^| · )([^ ]+)", value):
                text.stylize("bold", match.start(1), match.end(1))
        elif not self.no_color and widget_id == "sources":
            palette = {
                "complete": "green",
                "partial": "yellow",
                "stale": "yellow",
                "warming": "yellow",
                "unavailable": "bold red",
                "blocked": "yellow",
                "refreshing": "yellow",
            }
            for match in re.finditer(
                r"\b(complete|partial|stale|warming|unavailable|blocked|refreshing)\b",
                value,
                re.I,
            ):
                text.stylize(palette[match.group().lower()], match.start(), match.end())
        self.query_one(f"#{widget_id}", Static).update(text)
        self._render_values[widget_id] = value

    @staticmethod
    def _as_text(value: str) -> Text:
        return Text(value, no_wrap=True, overflow="ellipsis")

    def _content_widgets(self) -> list[Any]:
        children: list[Any] = []
        self._age_cells = {}
        self._line_widgets = {}
        self._source_age_cells = {}
        if self._overlay == "help":
            children = self._overlay_widgets()
        elif self._layout_mode() == "tiny":
            children = self._plain_lines(
                [
                    "Resize to at least 60×16 to view sessions.",
                    "Readers continue to expire evidence and recover independently.",
                    "Use ? for keys · q quits · Ctrl+C interrupts.",
                ]
            )
        elif self._overlay is not None:
            children = self._overlay_widgets()
        elif self._view == "sources":
            children = self._source_widgets()
        elif self._view == "details":
            if self._split_details():
                children = self._split_widgets()
            else:
                children = self._detail_widgets()
        else:
            children = self._list_widgets()
        return children

    def _content_signature(self):
        base = (
            self._view,
            self._overlay,
            self._layout_mode(),
            self.size.width,
            self.size.height,
            self._focus,
            self._scroll_offset,
            self._selected_key
            if self._view != "list" or self._layout_mode() == "compact"
            else None,
            self._selection_hidden,
            self._selection_available,
        )
        if self._projection is None:
            return (*base, "no-current-projection")
        if self._layout_mode() == "tiny":
            return (*base, "resize-guidance")
        if self._overlay == "help":
            return (*base, "help")
        if self._overlay == "filters":
            dimension = _FILTER_DIMENSIONS[self._filter_dimension_index]
            return (
                *base,
                dimension,
                self._filter_option_index,
                tuple(
                    sorted(
                        self._effective_filter_values(dimension, self._filter_options(dimension))
                    )
                ),
                tuple(sorted(self._empty_dimensions)),
            )
        if self._overlay in {"sort", "group"}:
            key = "sort" if self._overlay == "sort" else "group"
            return (*base, self.filters[key])
        if self._view == "sources":
            sources = {item.get("id"): item for item in self._report.get("sources", ())}
            statuses = {item.get("id"): item for item in self.reader.status()}
            return (
                *base,
                self._focused_source_id,
                tuple(self._source_signature(source) for source in sources.values()),
                tuple(
                    (key, value.get("stage"), value.get("retryAtBoottimeMs"), value.get("reason"))
                    for key, value in statuses.items()
                ),
            )
        if self._view == "details":
            row = self._selected_detail_row if self._selection_available else None
            detail_lines = []
            for line in self._detail_lines():
                if line.startswith("Activity: "):
                    line = "Activity: <age>"
                elif line.startswith("Baseline: ") and " · Frame age: " in line:
                    line = line.split(" · Frame age: ", 1)[0] + " · Frame age: <age>"
                detail_lines.append(line)
            return (
                *base,
                self._row_signature(row) if row else self._selected_label,
                self._source_signature(self._source_for_row(row)) if row else None,
                tuple(detail_lines),
                self._split_details(),
            )
        rows = tuple(self._row_signature(row) for row in self._page_rows)
        return (
            *base,
            rows,
            self.filters.get("group", "none"),
            self._report.get("totals", {}).get("state", "unknown"),
            tuple(sorted(self._empty_dimensions)),
        )

    @staticmethod
    def _fact_signature(fact: Any) -> tuple:
        if type(fact) is not dict:
            return ("unknown",)
        return (
            fact.get("value"),
            fact.get("health"),
            fact.get("lastKnownValue"),
            fact.get("reason"),
        )

    def _row_signature(self, row: dict | None) -> tuple | None:
        if row is None:
            return None
        source = row.get("source", {})
        details = row.get("details", {})
        activity = row.get("activity", {})
        return (
            self._row_key(row),
            row.get("label"),
            row.get("context"),
            source.get("host"),
            source.get("home"),
            row.get("membership"),
            row.get("kind"),
            self._fact_signature(row.get("runtime")),
            self._fact_signature(row.get("phase")),
            activity.get("health"),
            activity.get("lastKnownAt"),
            row.get("reason"),
            details.get("projectKey"),
            details.get("cwd"),
            details.get("workspaceHealth"),
            tuple(details.get("metadataIssues", ())),
            tuple(details.get("blockedReasons", ())),
        )

    def _source_for_row(self, row: dict | None) -> dict | None:
        if row is None:
            return None
        source_id = row.get("source", {}).get("id")
        return next(
            (item for item in self._report.get("sources", ()) if item.get("id") == source_id),
            None,
        )

    def _source_signature(self, source: dict | None) -> tuple | None:
        if not source:
            return None
        scopes = tuple(
            (
                scope.get("hostScope"),
                scope.get("provider"),
                scope.get("namespace"),
                scope.get("coverage", {}).get("status"),
                scope.get("coverage", {}).get("reason"),
                scope.get("coverage", {}).get("expiresAtBoottimeMs"),
            )
            for scope in source.get("scopes", ())
        )
        clock = source.get("clock") or {}
        return (
            source.get("id"),
            source.get("health"),
            source.get("delivery"),
            source.get("baseline"),
            source.get("reason"),
            tuple(source.get("reasons", ())),
            source.get("expectedNamespace"),
            source.get("observedNamespace"),
            scopes,
            clock.get("kind"),
            clock.get("clockDomain"),
            clock.get("bootId"),
        )

    def _rebind_age_cells(self) -> None:
        visible = {self._row_key(row): row for row in self._page_rows}
        for key, (widget, previous, _old_row) in tuple(self._age_cells.items()):
            if key in visible:
                self._age_cells[key] = (widget, previous, visible[key])
            else:
                del self._age_cells[key]
        self._line_widgets = {
            key: widget for key, widget in self._line_widgets.items() if key in visible
        }

    def _plain_lines(self, lines: list[str]) -> list[Static]:
        return [
            Static(self._as_text(self._fit_line(line, max(1, self.size.width - 4))), markup=False)
            for line in lines
        ]

    def _overlay_widgets(self) -> list[Static]:
        if self._overlay == "help":
            if self._layout_mode() == "tiny":
                return self._plain_lines(
                    [
                        "Keyboard help",
                        "Esc or ? back · q quit · Ctrl+C exit",
                        "Resize to 60×16 for session controls.",
                    ]
                )
            widgets = self._plain_lines(
                [
                    "Keyboard help",
                    "Navigation",
                    "↑↓/j/k move · PgUp/PgDn page · Home/End jump",
                    "Views",
                    "Enter details · Tab focus · Esc back/clear",
                    "Search and filters",
                    "/ find one term · f filters · o order · g grouping",
                    "Sources and exit",
                    "s sources · r retry · q quit · Ctrl+C exit",
                    "Search input keeps printable keys, including q/j/k.",
                ]
            )
            for index in (0, 1, 3, 5, 7):
                widgets[index].add_class("section-heading")
            return widgets
        if self._overlay == "filters":
            return self._filter_widgets()
        if self._overlay in {"sort", "group"}:
            values = (
                ("activity", "label", "host") if self._overlay == "sort" else ("none", "host-home")
            )
            current = self.filters["sort"] if self._overlay == "sort" else self.filters["group"]
            title = "Order" if self._overlay == "sort" else "Group"
            lines = [
                title,
                "↑/↓ choose · Enter apply · Esc returns",
                "Use f for filters · r resets from the Filters menu.",
            ]
            lines.extend(("> " if item == current else "  ") + item for item in values)
            return self._plain_lines(lines)
        return self._plain_lines(["No overlay"])

    def _filter_options(self, dimension: str) -> tuple[str, ...]:
        if dimension == "source":
            return tuple(
                dict.fromkeys(self._config_value(item, "id") for item in self._source_configs())
            )
        if dimension == "host":
            return tuple(
                dict.fromkeys(self._config_value(item, "host") for item in self._source_configs())
            )
        if dimension == "home":
            return tuple(
                dict.fromkeys(self._config_value(item, "home") for item in self._source_configs())
            )
        if dimension == "membership":
            return _MEMBERSHIPS
        if dimension == "runtime":
            return _RUNTIMES
        if dimension == "phase":
            return _PHASES
        return ("children", "system")

    def _effective_filter_values(self, dimension: str, options: tuple[str, ...]) -> set[str]:
        if dimension in self._empty_dimensions:
            return set()
        if dimension == "kind":
            selected = set()
            if self.filters.get("includeChildren"):
                selected.add("children")
            if self.filters.get("includeSystem"):
                selected.add("system")
            return selected
        current = set(self.filters.get(dimension, ()))
        if current:
            return current
        if dimension == "membership":
            return {"active", "recent", "uncertain"}
        return set(options)

    def _filter_widgets(self) -> list[Static]:
        dimension = _FILTER_DIMENSIONS[self._filter_dimension_index]
        options = self._filter_options(dimension)
        selected = self._effective_filter_values(dimension, options)
        labels = {
            "source": "Source",
            "host": "Host",
            "home": "Home",
            "membership": "Member",
            "runtime": "Runtime",
            "phase": "Phase",
            "kind": "Kind",
        }
        if self.size.width < 80:
            active_label = labels[dimension]
            heading = Text(
                f"Filters · [{active_label}] "
                f"{self._filter_dimension_index + 1}/{len(_FILTER_DIMENSIONS)}",
                style="bold underline",
            )
        else:
            heading = Text("Filters  ", style="bold")
            for index, name in enumerate(_FILTER_DIMENSIONS):
                if index:
                    heading.append("  ")
                label = labels[name]
                heading.append(f"[{label}]" if index == self._filter_dimension_index else label)
                if index == self._filter_dimension_index:
                    heading.stylize("bold underline", len(heading) - len(label) - 2, len(heading))
                else:
                    heading.stylize("dim", len(heading) - len(label), len(heading))
        widgets = [Static(heading, markup=False, classes="filter-tabs")]
        lines = [
            "←/→ or Tab: dimension · ↑/↓: option · Space/Enter: toggle",
        ]
        if not options:
            lines.append("No configured values for this dimension.")
        for index, option in enumerate(options):
            marker = ">" if index == self._filter_option_index else " "
            checked = "[x]" if option in selected else "[ ]"
            lines.append(f"{marker} {checked} {self._filter_option_label(dimension, option)}")
        lines.append("")
        lines.append("r resets filters and kind inclusion to defaults.")
        lines.append("Display filters only.")
        lines.append("All watched sources stay counted.")
        widgets.extend(self._plain_lines(lines))
        return widgets

    def _filter_option_label(self, dimension: str, option: str) -> str:
        if dimension != "source":
            return self._safe(option)
        config = next(
            (item for item in self._source_configs() if self._config_value(item, "id") == option),
            None,
        )
        if config is None:
            return self._safe(option)
        friendly = self._filter_source_label(config)
        matches = [
            item
            for item in self._source_configs()
            if self._filter_source_label(item) == friendly
        ]
        if len(matches) > 1:
            friendly += f" ({self._safe(option)})"
        return friendly

    def _filter_source_label(self, config: Any) -> str:
        host = self._safe(self._config_value(config, "host"))
        home = self._safe(self._config_value(config, "home"))
        label = self._safe(self._config_value(config, "label"))
        return f"{host}/{label or home}"

    def _source_configs(self) -> list[Any]:
        slots = getattr(self.reader, "slots", ())
        result = []
        for index, slot in enumerate(slots):
            source = getattr(slot, "source", None)
            if source is None:
                states = getattr(self.reader, "states", ())
                if index < len(states) and type(states[index]) is dict:
                    source = states[index].get("config")
            if source is not None:
                result.append(source)
        return result

    @staticmethod
    def _config_value(source: Any, name: str) -> str:
        if isinstance(source, dict):
            value = source.get(name, source.get({"mesh_source": "meshSource"}.get(name, ""), ""))
        else:
            value = getattr(source, name, "")
        return str(value)

    def _source_widgets(self) -> list[Static]:
        report_sources = {item.get("id"): item for item in self._report.get("sources", ())}
        statuses = {item.get("id"): item for item in self.reader.status()}
        configs = self._source_configs()
        lines: list[Static] = [
            Static(
                self._as_text(
                    f"Watched sources · {max(len(configs), len(report_sources))} configured"
                ),
                markup=False,
                classes="section-heading",
            ),
            Static(
                self._as_text(
                    "Source evidence · ↑↓ scroll · Tab returns to source list"
                    if self._focus == "source-details"
                    else "Source list · ↑↓ select · Tab opens selected source evidence"
                ),
                markup=False,
            ),
        ]
        option_labels = {
            source_id: self._filter_source_label(config)
            for config in configs
            if (source_id := self._config_value(config, "id"))
        }
        self._source_age_cells = {}
        selected_evidence: list[Static] = []
        for config in configs:
            source_id = self._config_value(config, "id")
            source = report_sources.get(source_id, {})
            status = statuses.get(source_id, {})
            selected = source_id == self._focused_source_id
            name = option_labels.get(source_id, self._filter_source_label(config))
            summary = self._source_summary_text(source, status)
            prefix = "> " if selected else "  "
            lines.append(
                Static(
                    self._as_text(self._fit_line(prefix + name, self.size.width - 4)), markup=False
                )
            )
            status_widget = Static(
                self._source_summary_display(source, status),
                markup=False,
            )
            lines.append(status_widget)
            if source.get("lastFrameBoottimeMs") is not None:
                self._source_age_cells[source_id] = (status_widget, summary)
            if selected:
                selected_evidence = self._source_detail_widgets(
                    source, config=config, status=status
                )
        if not configs:
            lines.append(
                Static(self._as_text("No source configuration is available."), markup=False)
            )
        lines.extend(selected_evidence)
        return lines

    def _source_summary_text(self, source: dict, status: dict) -> str:
        health = source.get("health", "refreshing" if self._projection is None else "warming")
        retry = self._retry_text(status)
        stage = self._safe(status.get("stage", "unknown"))
        coverage_states = tuple(
            dict.fromkeys(
                str(scope.get("coverage", {}).get("status", "unknown"))
                for scope in source.get("scopes", ())
            )
        )
        coverage = ", ".join(coverage_states) or "unknown"
        freshness = self._frame_age_text(source)
        recovery = retry or f"reader {stage}"
        return f"{health} · {recovery} · coverage {coverage} · frame age {freshness}"

    def _source_summary_display(self, source: dict, status: dict) -> Text:
        prefix = "  "
        value = self._fit_line(
            prefix + self._source_summary_text(source, status),
            max(1, self.size.width - 4),
        )
        text = self._as_text(value)
        health = str(
            source.get("health", "refreshing" if self._projection is None else "warming")
        )
        if not self.no_color:
            style = self._semantic_style(health)
            if style:
                text.stylize(style, len(prefix), min(len(value), len(prefix) + len(health)))
        return text

    def _source_detail_widgets(
        self, source: dict, *, config: Any | None = None, status: dict | None = None
    ) -> list[Static]:
        label = (
            self._filter_source_label(config)
            if config is not None
            else self._safe(source.get("id", "unknown"))
        )
        lines = [f"Selected source evidence · {label}"]
        wrap_width = max(1, self.size.width - 9)
        for detail in self._source_detail_text(source, config=config, status=status):
            lines.extend(
                "    " + part.plain
                for part in Text(detail).wrap(self.console, wrap_width, overflow="fold")
            )
        return [
            Static(
                self._as_text(line),
                markup=False,
                classes="section-heading" if index == 0 else "source-evidence",
            )
            for index, line in enumerate(lines)
        ]

    def _list_widgets(self, *, width: int | None = None, split: bool = False) -> list[Any]:
        self._age_cells = {}
        self._sync_page_rows()
        mode = self._layout_mode()
        render_width = width or self.size.width
        widgets: list[Any] = []
        total = len(self._visible_rows)
        page_size = self._page_size()
        start = (
            next(
                (
                    i
                    for i, row in enumerate(self._visible_rows)
                    if self._row_key(row) == self._selected_key
                ),
                0,
            )
            // page_size
            * page_size
            if total
            else 0
        )
        stop = min(total, start + page_size)
        if mode == "full" and not split:
            wide = render_width >= _WIDE_COLUMNS_WIDTH
            widths = self._column_widths(render_width - 4, wide=wide)
            headers = (
                ("SESSION", "CONTEXT", "HOST/HOME", "MEMBER", "RUNTIME", "PHASE", "ACTIVITY")
                if wide
                else ("SESSION", "HOST/HOME", "MEMBER", "RUNTIME / PHASE", "ACTIVITY")
            )
            header, _ = self._row_widget(headers, widths, selected=False, header=True)
            widgets.append(header)
        elif split:
            widgets.append(
                Static(
                    self._as_text(
                        self._fit_line(
                            "SESSION · MEMBER · LIST FOCUS"
                            if self._focus == "list"
                            else "SESSION · MEMBER",
                            render_width - 4,
                        )
                    ),
                    markup=False,
                )
            )
        if self.filters.get("group") == "host-home":
            prior_group = None
            for index in range(start, stop):
                row = self._visible_rows[index]
                group = (row.get("source", {}).get("host"), row.get("source", {}).get("home"))
                if group != prior_group:
                    prior_group = group
                    widgets.append(
                        Static(
                            self._as_text(
                                self._fit_line(
                                    f"{self._safe(group[0])}/{self._safe(group[1])}",
                                    render_width - 4,
                                )
                            ),
                            markup=False,
                        )
                    )
                widgets.extend(
                    self._session_widgets(row, index - start, mode, width=render_width, split=split)
                )
        else:
            for index in range(start, stop):
                widgets.extend(
                    self._session_widgets(
                        self._visible_rows[index],
                        index - start,
                        mode,
                        width=render_width,
                        split=split,
                    )
                )
        if not self._visible_rows:
            widgets.extend(
                self._plain_lines(
                    [
                        "No matching sessions.",
                        self._empty_state_text(),
                    ]
                )
            )
        if total > page_size:
            widgets.append(
                Static(
                    self._as_text(
                        f"Page {start // page_size + 1}/{(total + page_size - 1) // page_size} · {total} matching rows"
                    ),
                    markup=False,
                )
            )
        return widgets

    def _session_widgets(
        self,
        row: dict,
        page_index: int,
        mode: str,
        *,
        width: int,
        split: bool = False,
    ) -> list[Any]:
        selected = self._row_key(row) == self._selected_key
        key = self._row_key(row)
        if split:
            label_width = max(12, width - 34)
            selected_style = "reverse bold" if selected and self.no_color else ""
            item = Horizontal(
                self._cell(
                    "> " if selected else "  ",
                    2,
                    selected_style,
                    selection_marker=selected,
                ),
                self._cell(
                    self._safe(row.get("label")), label_width, selected_style
                ),
                self._cell(
                    self._safe(row.get("membership", "unknown")),
                    28,
                    selected_style
                    if selected
                    else self._semantic_style(self._safe(row.get("membership", "unknown"))),
                ),
                classes=self._row_classes(selected),
            )
            return [item]
        if mode == "compact":
            label = self._safe(row.get("label"))
            membership = self._safe(row.get("membership", "unknown"))
            selected_style = "reverse bold" if selected and self.no_color else ""
            first = Horizontal(
                self._cell(
                    "> " if selected else "  ",
                    2,
                    selected_style,
                    selection_marker=selected,
                ),
                self._cell(label, max(12, width - 22), selected_style),
                self._cell(
                    membership,
                    18,
                    selected_style if selected else self._semantic_style(membership),
                ),
                classes=self._row_classes(selected),
            )
            source = row.get("source", {})
            runtime = self._fact_text(row.get("runtime"))
            phase = self._phase_text(row.get("phase"))
            age = self._activity_age(row)
            second_text = (
                f"{self._safe(source.get('host'))}/{self._safe(source.get('home'))} · "
                f"{runtime}/{phase} · "
            )
            age = self._activity_age(row)
            age_cell = self._cell(
                age,
                10,
                selected_style if selected else "dim",
                widget_id=f"age-{page_index}",
            )
            second = Horizontal(
                self._cell("  ", 2),
                self._cell(
                    second_text,
                    max(12, width - 14),
                    selected_style
                    if selected
                    else self._semantic_style(f"{runtime}/{phase}"),
                ),
                age_cell,
                classes=self._row_classes(selected),
            )
            self._age_cells[key] = (age_cell, age, row)
            return [Vertical(first, second, classes="compact-row")]

        wide = width >= _WIDE_COLUMNS_WIDTH
        widths = self._column_widths(width - 4, wide=wide)
        source = row.get("source", {})
        cells = (
            self._safe(row.get("label")),
            f"{self._safe(source.get('host'))}/{self._safe(source.get('label') or source.get('home'))}",
            self._safe(row.get("membership", "unknown")),
            f"{self._fact_text(row.get('runtime'))}/{self._phase_text(row.get('phase'))}",
            self._activity_age(row),
        )
        if wide:
            cells = (
                cells[0],
                self._safe(row.get("context")) if row.get("context") else "—",
                cells[1],
                cells[2],
                self._fact_text(row.get("runtime")),
                self._phase_text(row.get("phase")),
                cells[-1],
            )
        row_widget, age_cell = self._row_widget(
            cells,
            widths,
            selected=selected,
            marker="> " if selected else "  ",
            last_cell_id=f"age-{page_index}",
        )
        self._age_cells[key] = (age_cell, cells[-1], row)
        self._line_widgets[key] = row_widget
        return [row_widget]

    def _row_classes(self, selected: bool) -> str:
        return "row selected-row" if selected and not self.no_color else "row"

    def _phase_text(self, fact: dict | None) -> str:
        label = self._fact_text(fact)
        if not self.icons or not isinstance(fact, dict) or fact.get("health") == "not_applicable":
            return label
        current = fact.get("value") if fact.get("health") == "current" else "unknown"
        glyph = {"working": "●", "waiting": "○", "blocked": "!", "unknown": "?"}.get(current)
        return f"{glyph} {label}" if glyph else label

    def _row_widget(
        self,
        cells: tuple[str, ...],
        widths: tuple[int, ...],
        *,
        selected: bool,
        header: bool = False,
        marker: str = "  ",
        last_cell_id: str | None = None,
    ) -> tuple[SessionLine, Static]:
        values = (marker, *cells)
        all_widths = (2, *widths)
        roles = (
            ("marker", "label", "context", "host", "state", "state", "state", "age")
            if len(cells) == 7
            else ("marker", "label", "host", "state", "state", "age")
        )

        def style_for(index, value, selected_row, header_row):
            role = roles[index]
            if header_row:
                return "bold"
            if selected_row:
                if self.no_color:
                    return "reverse bold"
                if role == "state":
                    semantic = self._semantic_style(value)
                    return f"bold {semantic}" if semantic else "bold"
                return "bold"
            if role == "state":
                return self._semantic_style(value)
            if role == "label":
                return "bold"
            return "dim"

        line = SessionLine(
            values,
            all_widths,
            selected=selected,
            header=header,
            style_for=style_for,
            surface_selection=not self.no_color,
        )
        return line, line

    @staticmethod
    def _column_widths(width: int, *, wide: bool = False) -> tuple[int, ...]:
        width = max(72, width)
        if wide:
            # Preserve a readable label and state words before adding context.
            return max(16, width - 76), 16, 18, 9, 9, 12, 10
        age = min(12, max(9, width // 12))
        membership = 10
        runtime_phase = min(24, max(18, width // 5))
        host_home = max(17, min(24, width // 5))
        title = max(8, width - 2 - age - membership - runtime_phase - host_home)
        return title, host_home, membership, runtime_phase, age

    def _semantic_style(self, value: str) -> str:
        normalized = value.casefold()
        if any(
            token in normalized for token in ("unavailable", "not currently available", "failed")
        ):
            return "bold red" if not self.no_color else "bold"
        if any(
            token in normalized
            for token in ("partial", "stale", "warming", "blocked", "unknown", "uncertain")
        ):
            return "bold yellow" if not self.no_color else "bold"
        if "working" in normalized or normalized in {"complete", "active"}:
            return "green" if not self.no_color else "bold"
        if "waiting" in normalized:
            return "cyan" if not self.no_color else "bold"
        if normalized in {"parked", "recent", "nonmember"}:
            return "dim"
        return ""

    def _cell(
        self,
        value: str,
        width: int,
        style: str = "",
        *,
        widget_id: str | None = None,
        selection_marker: bool = False,
    ) -> Static:
        safe_value = self._safe(value)
        text = Text(safe_value, style=style or None, no_wrap=True, overflow="ellipsis")
        text.truncate(max(1, width - (1 if width > 2 else 0)), overflow="ellipsis")
        text.pad_right(max(1, width))
        classes = "cell selection-marker" if selection_marker else "cell"
        widget = Static(text, markup=False, id=widget_id, classes=classes)
        widget.styles.width = max(1, width)
        return widget

    def _detail_width(self) -> int:
        if self._split_details():
            width = max(1, self.size.width - 6)
            left = max(55, int(width * 0.57))
            # The split pane reserves its border, padding, and stable scrollbar.
            return max(1, width - left - 6)
        return max(1, self.size.width - 4)

    def _wrapped_detail_lines(self) -> list[str]:
        # Exact IDs, namespaces and admitted paths must remain fully readable
        # in narrow/split details, even though list cells are ellipsized.
        width = self._detail_width()
        return [
            part.plain
            for line in self._detail_lines()
            for part in Text(line).wrap(self.console, width, overflow="fold")
        ]

    def _detail_widgets(self) -> list[Static]:
        lines = self._wrapped_detail_lines()
        start = self._scroll_offset
        visible = lines[start : start + max(1, self.size.height - 7)]
        result = []
        section_headings = {
            "Session summary",
            "Project and activity",
            "Observation reasons",
            "Source health and coverage",
            "Native identity and lease diagnostics",
        }
        for line in visible:
            widget_id = None
            if line.startswith("Activity: "):
                widget_id = "detail-activity"
            elif line.startswith("Baseline: ") and " · Frame age: " in line:
                widget_id = "detail-frame-age"
            result.append(
                Static(
                    self._as_text(line),
                    markup=False,
                    id=widget_id,
                    classes=(
                        "section-heading"
                        if line in section_headings
                        else "detail-title"
                        if line == (self._selected_label or "Selected session")
                        else ""
                    ),
                )
            )
        if any(widget.id == "detail-activity" for widget in result):
            self._render_values["detail-activity"] = self._activity_age(
                self._selected_detail_row if self._selection_available else None
            )
        if any(widget.id == "detail-frame-age" for widget in result):
            source = self._source_for_row(
                self._selected_detail_row if self._selection_available else None
            ) or {}
            self._render_values["detail-frame-age"] = (
                f"Baseline: {'yes' if source.get('baseline') else 'no'} · "
                f"Frame age: {self._frame_age_text(source)}"
            )
        return result

    def _split_widgets(self) -> list[Horizontal]:
        width = max(1, self.size.width - 6)
        left_width = max(55, int(width * 0.57))
        right_width = max(1, width - left_width - 2)
        list_widgets = self._list_widgets(width=left_width, split=True)
        left_panel = VerticalScroll(*list_widgets, id="split-list")
        detail_widgets = self._detail_widgets()
        right_panel = VerticalScroll(*detail_widgets, id="split-detail")
        if self._focus == "details":
            right_panel.add_class("details-focused")
        left_panel.styles.width = left_width
        right_panel.styles.width = right_width
        left_panel.styles.height = "1fr"
        right_panel.styles.height = "1fr"
        return [Horizontal(left_panel, right_panel, id="split-content")]

    def _detail_lines(self) -> list[str]:
        row = self._selected_detail_row if self._selection_available else None
        if row is None:
            status = (
                "selected session hidden by filters"
                if self._selection_hidden
                else "not currently available"
            )
            if self._selected_key is None:
                return ["No session selected.", "Use ↑/↓ to select a visible row."]
            return [
                self._selected_label or "Selected session",
                "Selection status",
                status,
                "Native identity and lease diagnostics",
                "Pinned identity (source provenance)",
                *self._identity_lines(self._selected_identity or {}),
            ]
        source = row.get("source", {})
        runtime = row.get("runtime", {})
        phase = row.get("phase", {})
        activity = row.get("activity", {})
        detail = row.get("details", {})
        source_doc = next(
            (
                item
                for item in self._report.get("sources", ())
                if item.get("id") == source.get("id")
            ),
            {},
        )
        statuses = {item.get("id"): item for item in self.reader.status()}
        config = next(
            (
                item
                for item in self._source_configs()
                if self._config_value(item, "id") == source.get("id")
            ),
            None,
        )
        lines = [
            self._safe(row.get("label")),
            *( ["selected session hidden by filters"] if self._selection_hidden else []),
            "Session summary",
            f"{self._safe(source.get('host'))}/{self._safe(source.get('label') or source.get('home'))}",
            f"Membership: {self._safe(row.get('membership', 'unknown'))}",
            f"Runtime: {self._fact_text(runtime)}{self._fact_reason(runtime)}",
            f"Phase: {self._fact_text(phase)}{self._fact_reason(phase)}",
            "",
            "Project and activity",
        ]
        if detail.get("projectKey"):
            lines.append(f"Project context: {self._safe(detail['projectKey'])}")
        if detail.get("cwd"):
            lines.append(f"Admitted path metadata: {self._safe(detail['cwd'])}")
        if detail.get("workspaceHealth"):
            lines.append(
                f"Workspace metadata: {self._safe(detail['workspaceHealth'])}"
                + (
                    f" · {self._safe(detail.get('workspaceReason'))}"
                    if detail.get("workspaceReason")
                    else ""
                )
            )
        lines.append(f"Activity: {self._activity_age(row)}")
        if activity.get("health") == "current":
            lines.append(f"Activity time: {self._wall_time(activity.get('at'))}")

        reason_lines = []
        if row.get("reason"):
            reason_lines.append(f"Membership reason: {self._safe(row.get('reason'))}")
        for fact_name, fact in (("Runtime", runtime), ("Phase", phase), ("Activity", activity)):
            if type(fact) is dict and fact.get("health") != "current" and fact.get("reason"):
                reason_lines.append(f"{fact_name} reason: {self._safe(fact['reason'])}")
        if runtime.get("health") != "current" and runtime.get("lastKnownValue") is not None:
            reason_lines.append(
                f"Last-known runtime (not current): {self._safe(runtime['lastKnownValue'])}"
            )
        if phase.get("health") != "current" and phase.get("lastKnownValue") is not None:
            reason_lines.append(
                f"Last-known phase (not current): {self._safe(phase['lastKnownValue'])}"
            )
        if activity.get("health") != "current" and activity.get("lastKnownAt") is not None:
            reason_lines.append(
                f"Last-known activity (not current): {self._wall_time(activity['lastKnownAt'])}"
            )
        if detail.get("metadataIssues"):
            reason_lines.append(
                "Metadata issues: "
                + ", ".join(self._safe(item) for item in detail["metadataIssues"])
            )
        if detail.get("blockedReasons"):
            reason_lines.append(
                "Bounded reasons: "
                + ", ".join(self._safe(item) for item in detail["blockedReasons"])
            )
        if reason_lines:
            lines.extend(("", "Observation reasons", *reason_lines))
        lines.extend(("", "Source health and coverage"))
        lines.extend(
            self._source_detail_text(
                source_doc,
                config=config,
                status=statuses.get(source.get("id"), {}),
            )
        )
        lines.extend(("", "Native identity and lease diagnostics", "Exact identity"))
        lines.extend(self._identity_lines(row.get("identity", {})))
        lines.append(f"Kind: {self._safe(row.get('kind', 'unknown'))}")
        lines.extend(self._membership_expiry_lines(row))
        return lines

    def _fact_reason(self, fact: dict) -> str:
        if type(fact) is not dict or fact.get("health") == "current" or not fact.get("reason"):
            return ""
        return f" · reason {self._safe(fact['reason'])}"

    def _identity_lines(self, identity: dict) -> list[str]:
        names = ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
        return [f"  {name}: {self._safe(identity.get(name, 'unknown'))}" for name in names]

    def _membership_expiry_lines(self, row: dict) -> list[str]:
        branches = row.get("membershipBranches", {})
        result = []
        for key, label in (
            ("activeExpiresAtBoottimeMs", "Active deadline"),
            ("recentExpiresAtBoottimeMs", "Recent deadline"),
            ("membershipExpiresAtBoottimeMs", "Membership deadline"),
        ):
            value = branches.get(key)
            if value is not None:
                result.append(f"{label} (receiving clock): {value}")
        details = row.get("details", {}).get("fieldExpiresAtBoottimeMs", {})
        expiries = [
            f"{self._safe(key)}={value}" for key, value in details.items() if value is not None
        ]
        if expiries:
            result.append("Field deadlines (receiving clock): " + ", ".join(expiries))
        return result

    def _source_detail_text(
        self, source: dict, *, config: Any | None = None, status: dict | None = None
    ) -> list[str]:
        status = status or {}
        lines = [
            f"Health: {self._safe(source.get('health', 'unknown'))} · delivery {self._safe(source.get('delivery', 'unknown'))}",
            f"Baseline: {'yes' if source.get('baseline') else 'no'} · Frame age: {self._frame_age_text(source)}",
        ]
        if status.get("stage") is not None:
            lines.append(f"Reader stage: {self._safe(status['stage'])}")
        retry = self._retry_text(status)
        if retry:
            lines.append(f"Retry: {retry}")
        reasons = source.get("reasons") or ([source["reason"]] if source.get("reason") else [])
        if reasons:
            lines.append("Source reasons: " + ", ".join(self._safe(reason) for reason in reasons))
        for scope in source.get("scopes", ()):
            coverage = scope.get("coverage", {})
            lines.append(
                f"Coverage {self._safe(scope.get('host'))}/{self._safe(scope.get('provider'))}: "
                f"{self._safe(coverage.get('status', 'unknown'))} · reason {self._safe(coverage.get('reason') or 'none')}"
            )
            if coverage.get("expiresAtBoottimeMs") is not None:
                lines.append(
                    f"  Coverage deadline (receiving clock): {coverage['expiresAtBoottimeMs']}"
                )
        source_id = (
            self._config_value(config, "id") if config is not None else source.get("id", "unknown")
        )
        if config is not None:
            lines.append(f"Configured host: {self._safe(self._config_value(config, 'host'))}")
            lines.append(f"Configured home: {self._safe(self._config_value(config, 'home'))}")
        lines.append(f"Configured source ID: {self._safe(source_id)}")
        lines.append(f"Expected namespace: {self._safe(source.get('expectedNamespace'))}")
        lines.append(
            "Observed namespace: "
            + (
                self._safe(source.get("observedNamespace"))
                if source.get("observedNamespace")
                else "unknown"
            )
        )
        clock = source.get("clock") or {}
        if clock:
            lines.append(
                f"Receiving clock: {self._safe(clock.get('kind'))} · {self._safe(clock.get('clockDomain'))} · "
                f"boot {self._safe(clock.get('bootId'))}"
            )
        return lines

    def _overlay_filter_dimension(self, delta: int) -> None:
        self._filter_dimension_index = (self._filter_dimension_index + delta) % len(
            _FILTER_DIMENSIONS
        )
        options = self._filter_options(_FILTER_DIMENSIONS[self._filter_dimension_index])
        self._filter_option_index = min(self._filter_option_index, max(0, len(options) - 1))
        self._request_render()

    def _toggle_filter_option(self) -> None:
        dimension = _FILTER_DIMENSIONS[self._filter_dimension_index]
        options = self._filter_options(dimension)
        if not options:
            return
        option = options[self._filter_option_index % len(options)]
        if dimension == "kind":
            name = "includeChildren" if option == "children" else "includeSystem"
            self.filters[name] = not bool(self.filters.get(name))
        else:
            if dimension in self._empty_dimensions:
                current = set()
                self._empty_dimensions.discard(dimension)
            else:
                current = set(self.filters.get(dimension, ()))
                if dimension == "membership" and not current:
                    current = {"active", "recent", "uncertain"}
                elif not current:
                    current = set(options)
            if option in current:
                current.remove(option)
            else:
                current.add(option)
            default = (
                {"active", "recent", "uncertain"} if dimension == "membership" else set(options)
            )
            if not current:
                self._empty_dimensions.add(dimension)
                self.filters[dimension] = ()
            else:
                self._empty_dimensions.discard(dimension)
                self.filters[dimension] = (
                    ()
                    if current == default
                    else tuple(value for value in options if value in current)
                )
        self._queue_projection()
        self._message = f"Updated {dimension} filter."
        self._request_render()

    def _reset_filters(self) -> None:
        self.filters["source"] = ()
        self.filters["host"] = ()
        self.filters["home"] = ()
        self.filters["membership"] = ()
        self.filters["runtime"] = ()
        self.filters["phase"] = ()
        self.filters["query"] = ()
        self.filters["includeChildren"] = False
        self.filters["includeSystem"] = False
        self._empty_dimensions.clear()
        self._queue_projection()
        self._message = "Dashboard filters reset to default values."
        self._request_render()

    def _available_sort(self) -> tuple[str, ...]:
        return ("activity", "label", "host")

    def _source_statuses(self) -> tuple[dict[str, dict], dict[str, dict]]:
        return (
            {item.get("id"): item for item in self._report.get("sources", ())},
            {item.get("id"): item for item in self.reader.status()},
        )

    def _current_source_id(self) -> str | None:
        if self._view == "sources":
            return self._focused_source_id
        if self._selected_key is not None:
            return self._selected_source_id
        return None

    def _retry_focused_source(self) -> None:
        source_id = self._current_source_id()
        if source_id is None:
            self._message = "Select a session or source before retrying."
        else:
            statuses = {item.get("id"): item for item in self.reader.status()}
            status = statuses.get(source_id, {})
            if status.get("stage") not in {"blocked", "retry-wait"}:
                self._message = f"{source_id}: source is not waiting for retry."
            elif self.reader.retry(source_id):
                self._message = f"Retry requested for {source_id}."
            else:
                self._message = f"Retry for {source_id} is rate-limited or unavailable."
        self._request_render()

    def _open_sources(self) -> None:
        if self._view == "sources":
            self._view = self._return_view
            self._focus = "list" if self._view == "list" else "details"
        else:
            self._return_view = self._view
            self._view = "sources"
            self._focus = "sources"
            source_docs, statuses = self._source_statuses()
            configs = self._source_configs()
            order = [self._config_value(item, "id") for item in configs]
            failed = next(
                (
                    source_id
                    for source_id in order
                    if statuses.get(source_id, {}).get("stage") in {"blocked", "retry-wait"}
                ),
                None,
            )
            self._focused_source_id = failed or (order[0] if order else None)
        self._request_render()

    def _move_source(self, delta: int) -> None:
        ids = [self._config_value(item, "id") for item in self._source_configs()]
        if not ids:
            return
        try:
            index = ids.index(self._focused_source_id)
        except ValueError:
            index = 0
        self._focused_source_id = ids[max(0, min(len(ids) - 1, index + delta))]
        self._request_render()

    def _move_rows(self, delta: int) -> None:
        if not self._visible_rows:
            return
        current = next(
            (
                i
                for i, row in enumerate(self._visible_rows)
                if self._row_key(row) == self._selected_key
            ),
            None,
        )
        if current is None:
            index = 0 if delta >= 0 else len(self._visible_rows) - 1
        else:
            index = max(0, min(len(self._visible_rows) - 1, current + delta))
        self._select_row(self._visible_rows[index])

    def _move_page(self, direction: int) -> None:
        if self._visible_rows:
            self._move_rows(direction * self._page_size())

    def _jump_row(self, end: bool) -> None:
        if self._visible_rows:
            self._select_row(self._visible_rows[-1 if end else 0])

    def _scroll_details(self, delta: int) -> None:
        visible = max(1, self.size.height - 7)
        maximum = max(0, len(self._wrapped_detail_lines()) - visible)
        self._scroll_offset = max(0, min(maximum, self._scroll_offset + delta))
        self._request_render()

    def _scroll_source_page(self, delta: int) -> None:
        if self._content is not None:
            self._content.scroll_relative(y=delta, animate=False, immediate=True)

    def _toggle_details(self) -> None:
        if self._view == "details":
            self._view = "list"
            self._focus = "list"
        elif self._selected_key is None:
            self._message = "Select a session first."
        else:
            self._view = "details"
            self._focus = "details"
            self._scroll_offset = 0
        self._request_render()

    def _open_search(self) -> None:
        if self._search_open:
            return
        self._search_open = True
        self._search_original = tuple(self.filters.get("query", ()))
        widget = self.query_one("#search", Input)
        widget.value = " ".join(self._search_original)
        widget.can_focus = True
        widget.display = True
        widget.focus()
        self._request_render()

    def _on_search_changed(self, value: str) -> None:
        cleaned = safe_metadata(value) or ""
        if cleaned != value:
            widget = self.query_one("#search", Input)
            widget.value = cleaned
            return
        if self._search_timer is not None:
            self._search_timer.stop()
        self._search_timer = self.set_timer(0.15, self._debounced_search_update)

    def _close_search(self) -> None:
        self._search_open = False
        widget = self.query_one("#search", Input)
        widget.display = False
        widget.blur()
        widget.can_focus = False

    def _apply_search_value(self, value: str) -> None:
        term = (safe_metadata(value) or "").strip()
        self.filters["query"] = (term,) if term else ()
        self._queue_projection()

    async def _commit_search_draft(self) -> None:
        if self._updates_stopped:
            return
        if self._search_timer is not None:
            self._search_timer.stop()
        self._search_timer = None
        if not self._search_open:
            return
        widget = self.query_one("#search", Input)
        self._apply_search_value(widget.value)
        self._close_search()
        self._message = "Search applied."
        self._request_render()

    async def _debounced_search_update(self) -> None:
        self._search_timer = None
        if self._updates_stopped or not self._search_open:
            return
        widget = self.query_one("#search", Input)
        self._apply_search_value(widget.value)
        self._request_render()

    async def _cancel_search(self) -> None:
        if self._updates_stopped:
            return
        if self._search_timer is not None:
            self._search_timer.stop()
            self._search_timer = None
        self.filters["query"] = self._search_original
        self._close_search()
        self._queue_projection()
        self._message = "Search edit cancelled."
        self._request_render()

    def _open_sort_or_group(self, overlay: str) -> None:
        self._overlay = overlay
        self._request_render()

    def _choose_sort_or_group(self, delta: int) -> None:
        options = self._available_sort() if self._overlay == "sort" else ("none", "host-home")
        key = "sort" if self._overlay == "sort" else "group"
        current = self.filters[key]
        index = options.index(current) if current in options else 0
        self.filters[key] = options[max(0, min(len(options) - 1, index + delta))]
        self._queue_projection()
        self._request_render()

    def _accept_sort_or_group(self) -> None:
        self._overlay = None
        self._request_render()

    def _handle_key(self, event: events.Key) -> None:
        key = event.key
        character = event.character or ""
        if key in {"ctrl+c", "ctrl+shift+c"}:
            event.stop()
            event.prevent_default()
            self.exit(return_code=130)
            return

        if self._updates_stopped:
            return

        focused = self.focused
        if isinstance(focused, Input):
            if key == "escape":
                event.stop()
                self.call_later(self._cancel_search)
            elif key == "enter":
                event.stop()
                self.call_later(self._commit_search_draft)
            return

        if key in {"q", "Q"} or character.lower() == "q":
            event.stop()
            event.prevent_default()
            self.exit(return_code=0)
            return

        if (key in {"?", "question_mark"} or character == "?") and self._overlay != "help":
            self._help_return_overlay = self._overlay
            self._overlay = "help"
            self._request_render()
            event.stop()
            return

        if key in {"escape", "ctrl+["}:
            event.stop()
            if self._overlay is not None:
                self._overlay = self._help_return_overlay if self._overlay == "help" else None
                self._help_return_overlay = None
            elif self._search_open:
                self.call_later(self._cancel_search)
            elif self._view == "sources":
                self._open_sources()
            elif self._view == "details":
                self._view = "list"
                self._focus = "list"
            else:
                self._clear_selection()
            self._request_render()
            return

        if self._overlay == "filters":
            event.stop()
            if key in {"left", "shift+tab"}:
                self._overlay_filter_dimension(-1)
            elif key in {"right", "tab"}:
                self._overlay_filter_dimension(1)
            elif key in {"up", "k"}:
                options = self._filter_options(_FILTER_DIMENSIONS[self._filter_dimension_index])
                self._filter_option_index = max(0, self._filter_option_index - 1)
                self._request_render()
            elif key in {"down", "j"}:
                options = self._filter_options(_FILTER_DIMENSIONS[self._filter_dimension_index])
                self._filter_option_index = min(
                    max(0, len(options) - 1), self._filter_option_index + 1
                )
                self._request_render()
            elif key in {"enter", "space"} or character == " ":
                self._toggle_filter_option()
            elif key in {"r", "R"} or character in {"r", "R"}:
                self._reset_filters()
            return

        if self._overlay in {"sort", "group"}:
            event.stop()
            if key in {"up", "k"}:
                self._choose_sort_or_group(-1)
            elif key in {"down", "j"}:
                self._choose_sort_or_group(1)
            elif key in {"enter", "space"}:
                self._accept_sort_or_group()
            return

        if self._overlay == "help":
            event.stop()
            if key in {"?", "escape", "enter"} or character == "?":
                self._overlay = self._help_return_overlay
                self._help_return_overlay = None
                self._request_render()
            return

        if key in {"tab", "shift+tab"}:
            event.stop()
            if self._view == "sources":
                self._focus = "source-list" if self._focus == "source-details" else "source-details"
            elif self._view == "details":
                if self._split_details():
                    self._focus = "list" if self._focus == "details" else "details"
                else:
                    self._focus = "details"
            else:
                self._focus = "list"
            self._request_render()
            return
        if key in {"up", "k"}:
            event.stop()
            if self._view == "sources":
                if self._focus == "source-details":
                    self._scroll_source_page(-1)
                else:
                    self._move_source(-1)
            elif self._view == "details" and self._focus == "details":
                self._scroll_details(-1)
            else:
                self._move_rows(-1)
            return
        if key in {"down", "j"}:
            event.stop()
            if self._view == "sources":
                if self._focus == "source-details":
                    self._scroll_source_page(1)
                else:
                    self._move_source(1)
            elif self._view == "details" and self._focus == "details":
                self._scroll_details(1)
            else:
                self._move_rows(1)
            return
        if key == "pageup":
            event.stop()
            if self._view == "list" or (self._view == "details" and self._focus == "list"):
                self._move_page(-1)
            elif self._view == "sources":
                if self._focus == "source-details":
                    self._scroll_source_page(-self._page_size())
                else:
                    self._move_source(-5)
            else:
                self._scroll_details(-self._page_size())
            return
        if key == "pagedown":
            event.stop()
            if self._view == "list" or (self._view == "details" and self._focus == "list"):
                self._move_page(1)
            elif self._view == "sources":
                if self._focus == "source-details":
                    self._scroll_source_page(self._page_size())
                else:
                    self._move_source(5)
            else:
                self._scroll_details(self._page_size())
            return
        if key == "home":
            event.stop()
            self._move_source(-100) if self._view == "sources" else self._jump_row(False)
            return
        if key == "end":
            event.stop()
            self._move_source(100) if self._view == "sources" else self._jump_row(True)
            return
        if key == "enter":
            event.stop()
            if self._view == "sources":
                self._focus = "source-details"
                self._request_render()
            else:
                self._toggle_details()
            return
        if key == "slash" or character == "/":
            event.stop()
            event.prevent_default()
            self._open_search()
            return
        if key in {"f", "F"} or character.lower() == "f":
            event.stop()
            self._overlay = "filters"
            self._filter_dimension_index = 0
            self._filter_option_index = 0
            self._request_render()
            return
        if key in {"o", "O"} or character.lower() == "o":
            event.stop()
            self._open_sort_or_group("sort")
            return
        if key in {"g", "G"} or character.lower() == "g":
            event.stop()
            self._open_sort_or_group("group")
            return
        if key in {"s", "S"} or character.lower() == "s":
            event.stop()
            self._open_sources()
            return
        if key in {"r", "R"} or character.lower() == "r":
            event.stop()
            self._retry_focused_source()
            return

    async def on_key(self, event: events.Key) -> None:
        self._handle_key(event)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if not self._updates_stopped and event.input.id == "search":
            self._on_search_changed(event.value)

    def on_resize(self, _event: events.Resize) -> None:
        if self._mounted and not self._updates_stopped:
            self.reader.refresh_due()
            self._ensure_current_projection()
            self._sync_page_rows()
        self._request_render(immediate=True)

    def _resume_refresh(self, _app) -> None:
        if self._mounted and not self._updates_stopped:
            self.reader.refresh_due()
            self._ensure_current_projection()
            self._request_render(immediate=True)

    def copy_to_clipboard(self, text: str) -> None:
        """Query editing and metadata views never emit terminal clipboard writes."""
        return None

    def open_url(self, url: str, *, new_tab: bool = True) -> None:
        """Admitted metadata remains literal and cannot launch a link."""
        return None

    def _header_text(self) -> str:
        if self._projection is None:
            label = "Observer" if self.size.width < 60 else "Agent Observer"
            suffix = " · refreshing source state"
            if self.size.width < 80:
                return self._fit_line(label + suffix, max(1, self.size.width - 2))
            return f"{label} · {self._view_label()} · refreshing source state"
        totals = self._report.get("totals", {})
        members = totals.get("members", 0)
        uncertain = totals.get("uncertain", 0)
        label = "Agent Observer"
        if self.icons and self.size.width >= 80:
            label = "◈ " + label
        if self.size.width < 80:
            label = "Observer" if self.size.width < 60 else "Agent Observer"
            value = f"{label} · {members} members, {uncertain} uncertain"
            if Text(value).cell_len <= max(1, self.size.width - 2):
                return value
            return self._fit_line(
                f"{members} members · {uncertain} uncertain", max(1, self.size.width - 2)
            )
        return f"{label} · {self._view_label()} · {members} members · {uncertain} uncertain"

    def _view_label(self) -> str:
        if self._overlay == "help":
            return "Help"
        if self._overlay == "filters":
            return "Filters"
        if self._overlay == "sort":
            return "Order"
        if self._overlay == "group":
            return "Group"
        return {"list": "Sessions", "details": "Details", "sources": "Sources"}.get(
            self._view, "Sessions"
        )

    def _source_ribbon(self) -> str:
        available = max(1, self.size.width - 4)
        configs = self._source_configs()
        sources = self._report.get("sources", ()) if self._projection is not None else ()
        source_docs = {item.get("id"): item for item in sources}
        details = []
        health_counts: dict[str, int] = {}
        configured_ids = set()
        for config in configs:
            source_id = self._config_value(config, "id")
            configured_ids.add(source_id)
            source = source_docs.get(source_id, {})
            health = source.get(
                "health", "refreshing" if self._projection is None else "warming"
            )
            details.append(f"{self._filter_source_label(config)} {health}")
            health_counts[health] = health_counts.get(health, 0) + 1
        for source in sources:
            source_id = source.get("id")
            if source_id in configured_ids:
                continue
            health = source.get("health", "unknown")
            details.append(f"{self._safe(source_id)} {health}")
            health_counts[health] = health_counts.get(health, 0) + 1

        total = len(details) if self._projection is not None else max(len(configs), 0)
        if self._projection is None:
            health_counts["refreshing"] = total
            details = [f"{self._filter_source_label(config)} refreshing" for config in configs]
        named = f"Sources {total} · " + " · ".join(details) if details else "Sources 0"
        if Text(named).cell_len <= available:
            return named

        aggregate = "Sources " + str(total)
        categories = ("complete", "partial", "stale", "warming", "blocked", "unavailable")
        for category in (*categories, *sorted(set(health_counts) - set(categories))):
            count = health_counts.get(category, 0)
            if count:
                aggregate += f" · {category} {count}"
        if Text(aggregate).cell_len <= available:
            return aggregate

        priority = next(
            (
                (category, health_counts[category])
                for category in (
                    "unavailable",
                    "blocked",
                    "stale",
                    "partial",
                    "warming",
                    "refreshing",
                    "complete",
                )
                if health_counts.get(category, 0)
            ),
            None,
        )
        if priority is None:
            short = f"{total} sources · s sources"
        else:
            category, count = priority
            short = f"{total} src · {category} {count} · s sources"
        if Text(short).cell_len <= available:
            return short
        shorter = (
            f"{total} src · {priority[0]} {priority[1]} · s"
            if priority is not None
            else f"{total} src · s"
        )
        return self._fit_line(shorter, available)

    def _toolbar_text(self) -> str:
        query = " ".join(self.filters.get("query", ()))
        active = []
        for dimension in ("source", "host", "home", "membership", "runtime", "phase"):
            if dimension in self._empty_dimensions:
                active.append(f"{dimension}=none")
                continue
            values = self.filters.get(dimension, ())
            if values:
                labels = (
                    self._filter_option_label(dimension, value)
                    for value in values
                )
                active.append(f"{dimension}={','.join(labels)}")
        if self.filters.get("includeChildren"):
            active.append("children")
        if self.filters.get("includeSystem"):
            active.append("system")
        order = self.filters.get("sort", "activity")
        group = self.filters.get("group", "none")
        if not query and not active and order == "activity" and group == "none":
            default = "Default view · / search · f filters · o order · g group"
            if self.size.width < 80:
                default = "Default · / search · f filters"
            return self._fit_line(default, max(1, self.size.width - 4))
        parts = [f"Search {self._safe(query)}" if query else "Search off"]
        parts.append(f"Filters {', '.join(active)}" if active else "default filters")
        if order != "activity":
            parts.append(f"Order {order}")
        if group != "none":
            parts.append("Group host/home" if group == "host-home" else f"Group {group}")
        return self._fit_line(" · ".join(parts), max(1, self.size.width - 4))

    def _status_text(self) -> str:
        if self._projection is None:
            return "Refreshing current source state; no empty-state verdict."
        report_totals = self._report.get("totals", {})
        total = len(self._visible_rows)
        hidden_presentation = max(0, len(self._all_rows) - total)
        state = report_totals.get("state", "warming")
        status = f"{total} matches"
        if self._empty_dimensions:
            status += " · no values selected for " + ", ".join(sorted(self._empty_dimensions))
        elif hidden_presentation:
            status += f" · {hidden_presentation} hidden by source/host/home filters"
        hidden_kinds = report_totals.get("hiddenKinds", 0)
        if hidden_kinds:
            status += f" · {hidden_kinds} hidden by kind"
        if state != "complete":
            status += f" · coverage {self._safe(state)}"
        if self._selected_key is not None and self._selection_hidden:
            status += " · selected session hidden by filters"
        elif self._selected_key is not None and not self._selection_available:
            status += " · selected session not currently available"
        if self._message:
            status += " · " + self._safe(self._message)
        return self._fit_line(status, max(1, self.size.width - 4))

    def _footer_text(self) -> str:
        if self.focused is not None and isinstance(self.focused, Input):
            if self.size.width < 60:
                return "Esc cancel · Ctrl+C exit"
            return "Type search · Enter apply · Esc restore · Ctrl+C exit"
        if self._overlay == "help":
            if self._layout_mode() == "tiny":
                return "Esc or ? back · q quit · Ctrl+C exit"
            return "? or Esc close · q quit · Ctrl+C exit"
        if self._layout_mode() == "tiny":
            return "? help · q quit · Ctrl+C exit"
        if self._overlay == "filters":
            if self.size.width < 80:
                return "Space toggle · r reset · Esc back · q quit"
            return "←→ field · ↑↓ option · Space toggle · r reset · Esc · ? help · q quit"
        if self._overlay == "sort" or self._overlay == "group":
            return "↑↓ choose · Enter apply · Esc back · ? help · q quit"
        if self._view == "sources":
            if self._focus == "source-details":
                if self.size.width < 80:
                    return "Evidence · Tab list · Esc back · q quit"
                return "Evidence · ↑↓ scroll · Tab list · Esc back · ? help · q quit"
            if self.size.width < 80:
                return "↑↓ select · Tab evidence · r retry · q quit"
            return "↑↓ select · Tab evidence · r retry · ? help · q quit"
        if self._view == "details":
            if self._split_details():
                if self._focus == "list":
                    return "List · ↑↓ select · Tab details · Esc back · ? help · q quit"
                return "Details · ↑↓ scroll · Tab list · Esc back · ? help · q quit"
            if self.size.width < 80:
                return "↑↓ scroll · Esc back · q quit"
            return "↑↓ scroll · Esc back · ? help · q quit"
        if self.size.width < 80:
            return "↑↓ move · Enter view · / find · ? help · q quit"
        return "↑↓ move · Enter details · / find · f filters · s sources · ? help · q quit"

    def _empty_state_text(self) -> str:
        if self._projection is None:
            return "Waiting for a current projection; coverage is not yet known."
        state = self._report.get("totals", {}).get("state", "warming")
        if state == "complete-empty":
            return "Sources currently report complete empty coverage."
        return f"No current matches; source coverage is {self._safe(state)}. Check s for source health."

    def _source_countdown_text(self, source_id: str, status: dict) -> str:
        if status.get("stage") == "blocked":
            return "manual correction required"
        retry_at = status.get("retryAtBoottimeMs")
        if retry_at is None:
            return ""
        now = self._receiving_now_ms()
        seconds = max(0, (retry_at - now + 999) // 1000)
        return f"retry in {seconds}s"

    def _retry_text(self, status: dict) -> str:
        return self._source_countdown_text(str(status.get("id", "")), status)

    def _refresh_source_countdowns(self) -> None:
        if not self._mounted or self._view != "sources" or self._overlay is not None:
            return
        if self._projection is None or not self.reader.is_current(self._projection):
            self._ensure_current_projection()
            return
        statuses = {item.get("id"): item for item in self.reader.status()}
        report_sources = {item.get("id"): item for item in self._report.get("sources", ())}
        for source_id, (widget, previous) in tuple(self._source_age_cells.items()):
            status = statuses.get(source_id, {})
            source = report_sources.get(source_id, {})
            current = self._source_summary_text(source, status)
            if current != previous:
                widget.update(self._source_summary_display(source, status))
                self._source_age_cells[source_id] = (widget, current)

    def _refresh_age_cells(self) -> None:
        if not self._mounted:
            return
        if self._projection is None or not self.reader.is_current(self._projection):
            self._ensure_current_projection()
            return
        age_now = self._display_now_ms()
        for key, (widget, previous, row) in tuple(self._age_cells.items()):
            current = self._activity_age(row, age_now)
            if current != previous:
                if isinstance(widget, SessionLine):
                    widget.update_age(current)
                    self._age_cells[key] = (widget, current, row)
                    continue
                style = (
                    "reverse bold"
                    if self.no_color and key == self._selected_key
                    else "" if key == self._selected_key else "dim"
                )
                width = widget.region.width or max(1, len(current))
                updated = Text(current, style=style or None, no_wrap=True, overflow="ellipsis")
                updated.truncate(width, overflow="ellipsis")
                updated.pad_right(width)
                widget.update(updated)
                self._age_cells[key] = (widget, current, row)
        # Details are stable widgets; refresh the activity line only when its text changes.
        if self._view == "details" and self._overlay is None:
            try:
                widget = self.query_one("#detail-activity", Static)
            except Exception:
                widget = None
            if widget is not None:
                row = self._selected_detail_row if self._selection_available else None
                value = self._activity_age(row, age_now) if row else "unknown"
                if self._render_values.get("detail-activity") != value:
                    widget.update(self._as_text("Activity: " + value))
                    self._render_values["detail-activity"] = value
            try:
                frame_widget = self.query_one("#detail-frame-age", Static)
            except Exception:
                frame_widget = None
            if frame_widget is not None:
                source = self._source_for_row(
                    self._selected_detail_row if self._selection_available else None
                ) or {}
                value = (
                    f"Baseline: {'yes' if source.get('baseline') else 'no'} · "
                    f"Frame age: {self._frame_age_text(source)}"
                )
                if self._render_values.get("detail-frame-age") != value:
                    frame_widget.update(self._as_text(value))
                    self._render_values["detail-frame-age"] = value

    def _activity_age(self, row: dict | None, now_ms: int | None = None) -> str:
        if row is None:
            return "unknown"
        label = _activity_text(row, self._display_now_ms() if now_ms is None else now_ms)
        return label.replace("approx. ", "~").removesuffix(" ago")

    @staticmethod
    def _report_wall_ms(report: dict) -> int:
        try:
            return int(
                datetime.fromisoformat(report["generatedAt"].replace("Z", "+00:00"))
                .astimezone(UTC)
                .timestamp()
                * 1000
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            return 0

    def _display_now_ms(self) -> int:
        return self._last_age_wall_ms + max(
            0, int((time.monotonic() - self._age_anchor_monotonic) * 1000)
        )

    def _receiving_now_ms(self) -> int:
        clock = self._report.get("clock", {})
        base = clock.get("nowBoottimeMs", 0)
        return base + max(0, int((time.monotonic() - self._age_anchor_monotonic) * 1000))

    def _frame_age_text(self, source: dict) -> str:
        frame = source.get("lastFrameBoottimeMs")
        if type(frame) is not int:
            return "unknown"
        age = max(0, self._receiving_now_ms() - frame)
        if age < 60_000:
            return f"{max(1, age // 1000)}s"
        if age < 3_600_000:
            return f"{age // 60_000}m"
        return f"{age // 3_600_000}h"

    @staticmethod
    def _wall_time(value: Any) -> str:
        if type(value) is not int:
            return "unknown"
        try:
            return (
                datetime.fromtimestamp(value / 1000, UTC)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
        except (OverflowError, OSError, ValueError):
            return "invalid timestamp"

    @classmethod
    def _fact_text(cls, fact: Any) -> str:
        if type(fact) is not dict:
            return "unknown (unavailable)"
        health = cls._safe(fact.get("health", "unavailable"))
        if health == "not_applicable":
            return "—"
        value = fact.get("value") if health == "current" else "unknown"
        return f"{cls._safe(value)} ({health})" if health != "current" else cls._safe(value)

    @staticmethod
    def _safe(value: Any) -> str:
        if value is None:
            return "unknown"
        if type(value) is not str:
            value = str(value)
        safe = safe_metadata(value)
        return (safe or "")[:1024]

    @staticmethod
    def _fit_line(value: str, width: int) -> str:
        text = Text(value, no_wrap=True, overflow="ellipsis")
        text.truncate(max(1, width), overflow="ellipsis")
        return text.plain


__all__ = ["DashboardApp"]
