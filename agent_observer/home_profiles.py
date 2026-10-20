"""Private, explicit Codex home routes for existing one-home services.

This module validates local configuration only. It does not create homes,
start services, contact Mesh, or inspect a native Codex daemon.

The bounded local format is versioned independently of all provider and wire
contracts::

    version = 1
    host = "snap"

    [profiles.default]
    label = "Default"
    codex_home = "/home/bryan/.codex"

    [profiles.work]
    label = "Work"
    codex_home = "/home/bryan/.codex-work"
"""

from __future__ import annotations

import os
import re
import stat
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .contract import store_namespace
from .working_set_policy import DEFAULT_WINDOW_MS

MAX_CONFIG_BYTES = 64 * 1024
MAX_PROFILES = 2
_PROFILE_ID = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
_HOST_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\Z")


class HomeProfileConfigError(ValueError):
    """A stable, bounded error code for a rejected local manifest."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class HomeProfileRoute:
    host: str
    profile_id: str
    label: str
    codex_home: str
    namespace: str
    collector_unit: str
    collector_runtime_dir: Path
    collector_socket: Path
    mesh_source: str
    publisher_unit: str
    publisher_runtime_dir: Path
    publisher_socket: Path
    window_ms: int = DEFAULT_WINDOW_MS

    def as_dict(self) -> dict:
        """Return a detached, JSON-ready description of this startup route."""
        return {
            "id": self.profile_id,
            "label": self.label,
            "codexHome": self.codex_home,
            "namespace": self.namespace,
            "windowMs": self.window_ms,
            "collector": {
                "unit": self.collector_unit,
                "runtimeDir": str(self.collector_runtime_dir),
                "socket": str(self.collector_socket),
            },
            "mesh": {
                "source": self.mesh_source,
                "publisherUnit": self.publisher_unit,
                "runtimeDir": str(self.publisher_runtime_dir),
                "socket": str(self.publisher_socket),
            },
        }


@dataclass(frozen=True)
class HomeProfileManifest:
    host: str
    uid: int
    runtime_dir: Path
    routes: tuple[HomeProfileRoute, ...]


def _fail(condition: bool, code: str) -> None:
    if not condition:
        raise HomeProfileConfigError(code)


def _validate_uid(uid: int) -> None:
    _fail(type(uid) is int and uid >= 0, "config_uid")


def _runtime_root(value: str | os.PathLike[str]) -> Path:
    try:
        raw = os.fspath(value)
    except TypeError:
        raise HomeProfileConfigError("runtime_dir") from None
    _fail(type(raw) is str and bool(raw), "runtime_dir")
    path = Path(raw)
    _fail(path.is_absolute() and ".." not in path.parts, "runtime_dir")
    return path


def _home(value) -> tuple[str, Path]:
    _fail(type(value) is str and 0 < len(value) <= 4096, "profile_home")
    _fail(value.startswith("/") and ".." not in Path(value).parts, "profile_home")
    _fail(not any(unicodedata.category(char).startswith("C") for char in value), "profile_home")
    try:
        physical = Path(value).resolve(strict=False)
    except (OSError, RuntimeError):
        raise HomeProfileConfigError("profile_home_resolution") from None
    # Keep `value` unchanged for the existing store_namespace calculation.
    return value, physical


def _private_toml(path: str | os.PathLike[str], uid: int) -> dict:
    _validate_uid(uid)
    try:
        raw_path = os.fspath(path)
    except TypeError:
        raise HomeProfileConfigError("config_file") from None
    _fail(type(raw_path) is str and bool(raw_path), "config_file")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    _fail(type(nofollow) is int, "config_no_follow_unavailable")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | nofollow
    )
    fd = None
    try:
        fd = os.open(raw_path, flags)
        info = os.fstat(fd)
        _fail(stat.S_ISREG(info.st_mode), "config_file_type")
        _fail(info.st_uid == uid, "config_file_owner")
        permissions = stat.S_IMODE(info.st_mode)
        _fail(permissions & 0o077 == 0 and permissions & 0o400 != 0, "config_file_private")
        _fail(info.st_size <= MAX_CONFIG_BYTES, "config_file_size")
        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = None
            payload = stream.read(MAX_CONFIG_BYTES + 1)
        _fail(len(payload) <= MAX_CONFIG_BYTES, "config_file_size")
    except HomeProfileConfigError:
        raise
    except OSError:
        raise HomeProfileConfigError("config_file_unavailable") from None
    finally:
        if fd is not None:
            os.close(fd)
    try:
        text = payload.decode("utf-8")
        document = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise HomeProfileConfigError("config_toml") from None
    _fail(type(document) is dict, "config_shape")
    return document


def _route(
    host: str,
    uid: int,
    runtime_dir: Path,
    profile_id: str,
    values: dict,
) -> tuple[HomeProfileRoute, Path]:
    _fail(_PROFILE_ID.fullmatch(profile_id) is not None, "profile_id")
    _fail(type(values) is dict and set(values) == {"label", "codex_home"}, "profile_fields")
    label = values["label"]
    _fail(
        type(label) is str
        and 1 <= len(label) <= 32
        and bool(label.strip())
        and all(char.isprintable() and not unicodedata.category(char).startswith("C") for char in label),
        "profile_label",
    )
    configured_home, physical_home = _home(values["codex_home"])
    namespace = store_namespace("codex", configured_home, "explicit", uid)

    if profile_id == "default":
        collector_runtime = runtime_dir / "agent-observer"
        collector_unit = "agent-observer.service"
        collector_socket = collector_runtime / "read.sock"
        mesh_source = "agent_working_set"
        publisher_runtime = runtime_dir / "mesh-plus-agent-working-set"
        publisher_unit = "mesh-plus-agent-working-set.service"
        publisher_socket = publisher_runtime / "read.sock"
    else:
        collector_runtime = runtime_dir / f"agent-observer-profile-{profile_id}"
        collector_unit = f"agent-observer-profile-{profile_id}.service"
        collector_socket = collector_runtime / "read.sock"
        mesh_source = f"agent_working_set_{profile_id}"
        publisher_runtime = runtime_dir / f"mesh-plus-agent-working-set-{profile_id}"
        publisher_unit = f"mesh-plus-agent-working-set-{profile_id}.service"
        publisher_socket = publisher_runtime / "read.sock"

    _fail(
        re.fullmatch(r"[a-z][a-z0-9_]{0,127}", mesh_source) is not None,
        "mesh_source_id",
    )
    _fail(
        all(len(os.fsencode(path)) <= 100 for path in (collector_socket, publisher_socket)),
        "socket_path_limit",
    )
    route = HomeProfileRoute(
        host=host,
        profile_id=profile_id,
        label=label,
        codex_home=configured_home,
        namespace=namespace,
        collector_unit=collector_unit,
        collector_runtime_dir=collector_runtime,
        collector_socket=collector_socket,
        mesh_source=mesh_source,
        publisher_unit=publisher_unit,
        publisher_runtime_dir=publisher_runtime,
        publisher_socket=publisher_socket,
    )
    return route, physical_home


def _validate_route_set(routes: tuple[HomeProfileRoute, ...]) -> None:
    route_fields = (
        (route.collector_unit for route in routes),
        (str(route.collector_socket) for route in routes),
        (route.mesh_source for route in routes),
        (route.publisher_unit for route in routes),
        (str(route.publisher_socket) for route in routes),
    )
    for values in route_fields:
        values = tuple(values)
        _fail(len(values) == len(set(values)), "route_collision")

    sockets = [str(route.collector_socket) for route in routes]
    sockets.extend(str(route.publisher_socket) for route in routes)
    _fail(len(sockets) == len(set(sockets)), "socket_collision")

    runtime_dirs = [route.collector_runtime_dir for route in routes]
    runtime_dirs.extend(route.publisher_runtime_dir for route in routes)
    _fail(len(runtime_dirs) == len(set(runtime_dirs)), "runtime_dir_collision")
    for index, left in enumerate(runtime_dirs):
        for right in runtime_dirs[index + 1 :]:
            _fail(
                not left.is_relative_to(right) and not right.is_relative_to(left),
                "runtime_dir_nesting",
            )


def load_home_profiles(
    path: str | os.PathLike[str],
    *,
    uid: int,
    runtime_dir: str | os.PathLike[str],
) -> HomeProfileManifest:
    """Load one bounded private TOML manifest and resolve its local routes.

    ``uid`` and ``runtime_dir`` are explicit so callers and tests cannot infer
    service ownership or runtime placement from ambient process state here.
    """
    _validate_uid(uid)
    root = _runtime_root(runtime_dir)
    document = _private_toml(path, uid)
    _fail(set(document) == {"version", "host", "profiles"}, "config_fields")
    _fail(type(document["version"]) is int and document["version"] == 1, "config_version")
    host = document["host"]
    _fail(type(host) is str and _HOST_ID.fullmatch(host) is not None, "config_host")
    profiles = document["profiles"]
    _fail(type(profiles) is dict and 1 <= len(profiles) <= MAX_PROFILES, "config_profiles")
    _fail("default" in profiles, "config_default_required")

    routed = [_route(host, uid, root, profile_id, values) for profile_id, values in profiles.items()]
    routed.sort(key=lambda item: (item[0].profile_id != "default", item[0].profile_id))
    result = tuple(route for route, _physical in routed)

    physical_homes = [physical for _route_value, physical in routed]
    _fail(len(physical_homes) == len(set(physical_homes)), "duplicate_home")
    _validate_route_set(result)
    return HomeProfileManifest(host, uid, root, result)


def select_home_profiles(
    manifest: HomeProfileManifest,
    profile_ids: tuple[str, ...] | list[str] | None = None,
) -> tuple[HomeProfileRoute, ...]:
    """Select all configured routes or an exact subset in manifest order."""
    if profile_ids is None:
        return manifest.routes
    _fail(type(profile_ids) in {tuple, list}, "profile_selection")
    requested = tuple(profile_ids)
    _fail(all(type(profile_id) is str for profile_id in requested), "profile_selection")
    _fail(len(requested) == len(set(requested)), "profile_selection_duplicate")
    by_id = {route.profile_id: route for route in manifest.routes}
    _fail(all(profile_id in by_id for profile_id in requested), "profile_not_configured")
    selected = set(requested)
    return tuple(route for route in manifest.routes if route.profile_id in selected)


def routes_document(
    manifest: HomeProfileManifest,
    profile_ids: tuple[str, ...] | list[str] | None = None,
) -> dict:
    """List selected resolved routes without reading a collector or daemon."""
    return {
        "host": manifest.host,
        "uid": manifest.uid,
        "runtimeDir": str(manifest.runtime_dir),
        "profiles": [route.as_dict() for route in select_home_profiles(manifest, profile_ids)],
    }
