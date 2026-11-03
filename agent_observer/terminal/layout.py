"""Shared terminal-width breakpoints for human session rows."""

MIN_SESSION_WIDTH = 32
MIN_SESSION_HEIGHT = 12
STACKED_WIDTH = 60
TABLE_WIDTH = 110

_ROW_HEIGHTS = {"tiny": 0, "full": 1, "compact": 2, "stacked": 4}
_HEADER_HEIGHTS = {"tiny": 0, "full": 1, "compact": 2, "stacked": 0}


def layout_mode(width: int, height: int | None = None) -> str:
    """Choose row shape from columns; height only controls the minimum guard."""
    if width < MIN_SESSION_WIDTH or (height is not None and height < MIN_SESSION_HEIGHT):
        return "tiny"
    if width >= TABLE_WIDTH:
        return "full"
    if width >= STACKED_WIDTH:
        return "compact"
    return "stacked"


def row_height(mode: str) -> int:
    """Return the number of terminal lines occupied by a session row."""
    return _ROW_HEIGHTS[mode]


def header_height(mode: str) -> int:
    """Return the number of column-heading lines for a row arrangement."""
    return _HEADER_HEIGHTS[mode]


def medium_columns(
    width: int,
    *,
    gutter: int,
    required_left: int,
    preferred_left: int,
    gap: int = 1,
    minimum_right: int = 27,
) -> tuple[int, int, int]:
    """Fit the shared left/right boundary used by both medium row lines.

    ``width`` is the available row width before the selection gutter and
    inter-column gap. The left side must hold the complete status/age cell;
    useful profile context can use up to 32 columns. The right side retains a
    27-column minimum at the 60-column breakpoint when the status/age cell is
    at its 26-column worst case.
    """
    available = max(0, width - gutter - gap)
    left_floor = min(max(0, required_left), available)
    right_floor = min(max(0, minimum_right), max(0, available - left_floor))
    largest_left = max(left_floor, available - right_floor)
    left = min(max(left_floor, min(32, max(0, preferred_left))), largest_left)
    return left, max(0, available - left), gap
