"""Fixed dashboard identity and workspace colors, separate from CLI rendering."""

from __future__ import annotations

import hashlib

from .render import _profile_family, _profile_identity, _rgb_color, _workspace_kind

_DARK_PROFILE_COLORS = (
    ("#98b9e8", "#a0bee8", "#a6c2e9", "#abc5ea"),
    ("#beace2", "#c2b3e4", "#c5b7e5", "#c8bbe6"),
    ("#dba5c5", "#dcacca", "#ddb1cd", "#ddb6d0"),
    ("#94c2df", "#9cc6e1", "#a1c9e2", "#a7cce4"),
    ("#afb2e3", "#b4b8e4", "#b8bce5", "#bcc0e7"),
)
_LIGHT_PROFILE_COLORS = (
    ("#354d72", "#344a6c", "#324768", "#314563"),
    ("#574273", "#52406d", "#4f3e68", "#4b3d64"),
    ("#6f3f5e", "#673d5a", "#623c57", "#5d3b54"),
    ("#2e506b", "#2d4c65", "#2d4a61", "#2c475e"),
    ("#454975", "#42466e", "#40446a", "#3e4265"),
)
_DARK_WORKSPACE_COLORS = {
    "repo": "#a8d1bd",
    "dir": "#dac19d",
    "unknown": "#bbc2ca",
}
_LIGHT_WORKSPACE_COLORS = {
    "repo": "#315449",
    "dir": "#624d30",
    "unknown": "#464f5a",
}
_DIRECTORY_PREFIX_DARK = "#b3bdc9"
_DIRECTORY_PREFIX_LIGHT = "#404b59"


def _color(value: str) -> tuple[str, str]:
    return _rgb_color(tuple(int(value[index : index + 2], 16) for index in (1, 3, 5)))


def home_shade_index(home: str) -> int:
    """Return the fixed matrix column for an exact configured home name."""
    if home == "default":
        return 0
    digest = hashlib.sha256(home.encode("utf-8")).digest()
    return 1 + int.from_bytes(digest[:4], "big") % 3


def host_color(row: dict, *, light: bool = False) -> tuple[str, str] | None:
    identity = _profile_identity(row)
    if identity is None:
        return None
    host, _home = identity
    palette = _LIGHT_PROFILE_COLORS if light else _DARK_PROFILE_COLORS
    return _color(palette[_profile_family(host)][0])


def profile_color(row: dict, *, light: bool = False) -> tuple[str, str] | None:
    identity = _profile_identity(row)
    if identity is None:
        return None
    host, home = identity
    palette = _LIGHT_PROFILE_COLORS if light else _DARK_PROFILE_COLORS
    return _color(palette[_profile_family(host)][home_shade_index(home)])


def workspace_color(row: dict, *, light: bool = False) -> tuple[str, str]:
    palette = _LIGHT_WORKSPACE_COLORS if light else _DARK_WORKSPACE_COLORS
    return _color(palette[_workspace_kind(row)])


def directory_prefix_color(*, light: bool = False) -> tuple[str, str]:
    return _color(_DIRECTORY_PREFIX_LIGHT if light else _DIRECTORY_PREFIX_DARK)


def directory_prefix_end(visible_text: str, row: dict) -> int | None:
    """Return the parent-prefix span end for a visible directory label."""
    if _workspace_kind(row) != "dir":
        return None
    separator = visible_text.rfind("/")
    return separator + 1 if separator >= 0 else None
