"""Private, explicit configuration for the terminal working-set client.

This module is intentionally independent of Mesh and provider APIs. Loading a
configuration only reads and validates the consumer's own source routes.
"""

from __future__ import annotations

import os
import re
import stat
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

MAX_CONFIG_BYTES = 64 * 1024
MAX_SOURCES = 8
MAX_IDENTITIES_PER_SOURCE = 4096
MAX_IDENTITIES_TOTAL = 8192
MAX_PAYLOAD_MIB_TOTAL = 32
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HOST = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\Z")
_HOME = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_SOURCE_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_MESH_SOURCE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class TerminalConfigError(ValueError):
    """Stable bounded error code for rejected terminal configuration."""

    def __init__(self, code: str, detail: str | None = None):
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class TerminalSource:
    id: str
    host: str
    home: str
    label: str
    mesh_source: str
    scope: str
    socket: Path
    namespace: str
    window_hours: int
    max_identities: int = 1024
    max_payload_mib: int = 4

    @property
    def window_ms(self) -> int:
        return self.window_hours * 60 * 60 * 1000

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "host": self.host,
            "home": self.home,
            "label": self.label,
            "meshSource": self.mesh_source,
            "scope": self.scope,
            "socket": str(self.socket),
            "namespace": self.namespace,
            "windowHours": self.window_hours,
            "maxIdentities": self.max_identities,
            "maxPayloadMiB": self.max_payload_mib,
        }


@dataclass(frozen=True)
class TerminalConfig:
    sources: tuple[TerminalSource, ...]
    default_sources: tuple[str, ...]
    path: Path


def default_config_path(*, environ: dict | None = None, home: Path | None = None) -> Path:
    """Return the standard per-user terminal configuration path."""
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    xdg = environ.get("XDG_CONFIG_HOME")
    if xdg:
        root = Path(xdg)
        if not root.is_absolute() or ".." in root.parts:
            raise TerminalConfigError("config_directory")
    else:
        root = home / ".config"
    return root / "agent-observer" / "terminal.toml"


def _read_private_toml(path: Path, uid: int) -> dict:
    if type(uid) is not int or uid < 0:
        raise TerminalConfigError("config_uid")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if type(nofollow) is not int:
        raise TerminalConfigError("config_no_follow_unavailable")
    fd = None
    try:
        fd = os.open(path, flags | nofollow)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise TerminalConfigError("config_file_type")
        if info.st_uid != uid:
            raise TerminalConfigError("config_file_owner")
        permissions = stat.S_IMODE(info.st_mode)
        if permissions & 0o077 or not permissions & 0o400:
            raise TerminalConfigError("config_file_private")
        if info.st_size > MAX_CONFIG_BYTES:
            raise TerminalConfigError("config_file_size")
        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = None
            payload = stream.read(MAX_CONFIG_BYTES + 1)
        if len(payload) > MAX_CONFIG_BYTES:
            raise TerminalConfigError("config_file_size")
    except TerminalConfigError:
        raise
    except FileNotFoundError:
        raise TerminalConfigError("config_missing") from None
    except OSError:
        raise TerminalConfigError("config_file_unavailable") from None
    finally:
        if fd is not None:
            os.close(fd)
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise TerminalConfigError("config_toml") from None
    if type(document) is not dict:
        raise TerminalConfigError("config_shape")
    return document


def _safe_label(value, *, code: str, limit: int = 64) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= limit
        or not value.strip()
        or any(
            not char.isprintable() or unicodedata.category(char).startswith("C") for char in value
        )
    ):
        raise TerminalConfigError(code)
    return value


def _positive_int(value, *, code: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise TerminalConfigError(code)
    return value


def _parse_source(value) -> TerminalSource:
    required = {
        "id",
        "host",
        "home",
        "label",
        "mesh_source",
        "scope",
        "socket",
        "namespace",
        "window_hours",
    }
    optional = {"max_identities", "max_payload_mib"}
    if type(value) is not dict or not required <= set(value) or set(value) - required - optional:
        raise TerminalConfigError("source_fields")
    source_id = value["id"]
    host = value["host"]
    home = value["home"]
    mesh_source = value["mesh_source"]
    scope = value["scope"]
    namespace = value["namespace"]
    if type(source_id) is not str or _SOURCE_ID.fullmatch(source_id) is None:
        raise TerminalConfigError("source_id")
    if type(host) is not str or _HOST.fullmatch(host) is None:
        raise TerminalConfigError("source_host")
    if type(home) is not str or _HOME.fullmatch(home) is None:
        raise TerminalConfigError("source_home")
    if type(mesh_source) is not str or _MESH_SOURCE.fullmatch(mesh_source) is None:
        raise TerminalConfigError("source_mesh_id")
    if type(scope) is not str or scope not in {"local", "hosts"}:
        raise TerminalConfigError("source_scope")
    if type(namespace) is not str or _DIGEST.fullmatch(namespace) is None:
        raise TerminalConfigError("source_namespace")
    if type(value["socket"]) is not str or not value["socket"]:
        raise TerminalConfigError("source_socket")
    if any(unicodedata.category(char).startswith("C") for char in value["socket"]):
        raise TerminalConfigError("source_socket")
    try:
        socket = Path(value["socket"])
    except (TypeError, ValueError):
        raise TerminalConfigError("source_socket") from None
    if not socket.is_absolute() or ".." in socket.parts:
        raise TerminalConfigError("source_socket")
    window_hours = _positive_int(
        value["window_hours"], code="source_window_hours", minimum=0, maximum=720
    )
    max_identities = _positive_int(
        value.get("max_identities", 1024),
        code="source_identity_limit",
        minimum=1,
        maximum=MAX_IDENTITIES_PER_SOURCE,
    )
    max_payload_mib = _positive_int(
        value.get("max_payload_mib", 4),
        code="source_payload_limit",
        minimum=1,
        maximum=MAX_PAYLOAD_MIB_TOTAL,
    )
    return TerminalSource(
        id=source_id,
        host=host,
        home=home,
        label=_safe_label(value["label"], code="source_label"),
        mesh_source=mesh_source,
        scope=scope,
        socket=socket,
        namespace=namespace,
        window_hours=window_hours,
        max_identities=max_identities,
        max_payload_mib=max_payload_mib,
    )


def parse_config(document: dict, *, path: Path) -> TerminalConfig:
    """Validate a detached TOML document; no filesystem or Mesh discovery."""
    if type(document) is not dict or set(document) != {"version", "default_sources", "sources"}:
        raise TerminalConfigError("config_fields")
    if type(document["version"]) is not int or document["version"] != 1:
        raise TerminalConfigError("config_version")
    raw_sources = document["sources"]
    if type(raw_sources) is not list or not 1 <= len(raw_sources) <= MAX_SOURCES:
        raise TerminalConfigError("config_source_count")
    sources = tuple(_parse_source(item) for item in raw_sources)
    ids = [item.id for item in sources]
    pairs = [(item.host, item.home) for item in sources]
    routes = [(item.host, item.mesh_source) for item in sources]
    if len(ids) != len(set(ids)):
        raise TerminalConfigError("config_duplicate_source_id")
    if len(pairs) != len(set(pairs)):
        raise TerminalConfigError("config_duplicate_host_home")
    if len(routes) != len(set(routes)):
        raise TerminalConfigError("config_duplicate_route")
    if sum(item.max_identities for item in sources) > MAX_IDENTITIES_TOTAL:
        raise TerminalConfigError("config_identity_budget")
    if sum(item.max_payload_mib for item in sources) > MAX_PAYLOAD_MIB_TOTAL:
        raise TerminalConfigError("config_payload_budget")
    defaults = document["default_sources"]
    if (
        type(defaults) is not list
        or not 1 <= len(defaults) <= MAX_SOURCES
        or any(type(item) is not str for item in defaults)
        or len(defaults) != len(set(defaults))
        or not set(defaults) <= set(ids)
    ):
        raise TerminalConfigError("config_default_sources")
    return TerminalConfig(sources=sources, default_sources=tuple(defaults), path=Path(path))


def load_config(
    path: str | os.PathLike[str] | None = None, *, uid: int | None = None
) -> TerminalConfig:
    """Load one owner-private terminal config without discovery or side effects."""
    selected_path = default_config_path() if path is None else Path(path)
    return parse_config(
        _read_private_toml(selected_path, os.geteuid() if uid is None else uid),
        path=selected_path,
    )


def select_sources(
    config: TerminalConfig,
    *,
    source_ids: tuple[str, ...] = (),
    hosts: tuple[str, ...] = (),
    homes: tuple[str, ...] = (),
) -> tuple[TerminalSource, ...]:
    """Resolve explicit source/host/home selectors or the configured defaults."""
    if not any((source_ids, hosts, homes)):
        chosen = tuple(item for item in config.sources if item.id in config.default_sources)
        if chosen:
            return chosen
        raise TerminalConfigError("source_selection_empty")
    known = {
        "source": {item.id for item in config.sources},
        "host": {item.host for item in config.sources},
        "home": {item.home for item in config.sources},
    }
    for label, values in (("source", source_ids), ("host", hosts), ("home", homes)):
        if any(value not in known[label] for value in values):
            raise TerminalConfigError("source_selector_unknown", label)
    selected = tuple(
        item
        for item in config.sources
        if (not source_ids or item.id in source_ids)
        and (not hosts or item.host in hosts)
        and (not homes or item.home in homes)
    )
    if not selected:
        raise TerminalConfigError("source_selection_empty")
    return selected
