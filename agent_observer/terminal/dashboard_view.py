"""Small, optional saved-view state for the terminal dashboard.

The data model and row ordering here are pure. Filesystem operations are only
called by ``dashboard_view_worker``; the async controller owns that isolated
helper and never performs path inspection in the caller's event loop.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import secrets
import stat
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..bounded_json import WireError, decode_document
from .model import IDENTITY_FIELDS, identity_tuple

VERSION = 1
MAX_PINS = 32
MAX_STATE_BYTES = 64 * 1024
SORTS = ("activity", "label", "host")
GROUPS = ("none", "host-home")
APP_DIRECTORY = "agent-observer"
STATE_FILENAME = "dashboard-view.json"

DEFAULT_LOAD_TIMEOUT = 0.250
DEFAULT_SAVE_TIMEOUT = 1.0
DEFAULT_SHUTDOWN_DRAIN = 2.0
DEFAULT_REAP_TIMEOUT = 0.250

_FORMAT_FIELDS = frozenset({"version", "pins", "sort", "group"})
_ERROR_CODES = frozenset(
    {
        "saved_view_state_root_unavailable",
        "saved_view_state_root_unsafe",
        "saved_view_directory_unsafe",
        "saved_view_file_unsafe",
        "saved_view_too_large",
        "saved_view_invalid",
        "saved_view_unsupported_version",
        "saved_view_io_failed",
        "saved_view_pin_limit",
        "saved_view_duplicate_pin",
        "saved_view_helper_failed",
        "saved_view_helper_unavailable",
        "saved_view_load_timeout",
        "saved_view_save_timeout",
        "saved_view_shutdown_timeout",
        "saved_view_cleanup_timeout",
    }
)

IdentityKey = tuple[str, str, str, str, str]


class SavedViewError(ValueError):
    """Content-free validation or storage error code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _key_from_reference(value) -> IdentityKey:
    try:
        key = identity_tuple(value)
    except (KeyError, TypeError, ValueError):
        raise SavedViewError("saved_view_invalid") from None
    if any(not item for item in key):
        raise SavedViewError("saved_view_invalid")
    return key  # type: ignore[return-value]


def _key_from_tuple(value) -> IdentityKey:
    if (
        type(value) is not tuple
        or len(value) != len(IDENTITY_FIELDS)
        or any(type(item) is not str or not item for item in value)
    ):
        raise SavedViewError("saved_view_invalid")
    return value  # type: ignore[return-value]


def _document_bytes(pins: tuple[IdentityKey, ...], sort: str, group: str) -> bytes:
    document = {
        "version": VERSION,
        "pins": [dict(zip(IDENTITY_FIELDS, pin, strict=True)) for pin in pins],
        "sort": sort,
        "group": group,
    }
    try:
        payload = json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", "strict")
    except (UnicodeError, TypeError, ValueError):
        raise SavedViewError("saved_view_invalid") from None
    if len(payload) > MAX_STATE_BYTES:
        raise SavedViewError("saved_view_too_large")
    return payload


@dataclass(frozen=True)
class SavedView:
    """Immutable version-1 display state; pins are ordered exact identities."""

    pins: tuple[IdentityKey, ...] = ()
    sort: str = "activity"
    group: str = "none"

    def __post_init__(self) -> None:
        if type(self.pins) is not tuple or len(self.pins) > MAX_PINS:
            raise SavedViewError("saved_view_pin_limit")
        pins = tuple(_key_from_tuple(pin) for pin in self.pins)
        if len(set(pins)) != len(pins):
            raise SavedViewError("saved_view_duplicate_pin")
        if type(self.sort) is not str or self.sort not in SORTS:
            raise SavedViewError("saved_view_invalid")
        if type(self.group) is not str or self.group not in GROUPS:
            raise SavedViewError("saved_view_invalid")
        object.__setattr__(self, "pins", pins)
        _document_bytes(pins, self.sort, self.group)

    @classmethod
    def from_references(
        cls,
        references: Iterable[dict],
        *,
        sort: str = "activity",
        group: str = "none",
    ) -> SavedView:
        if isinstance(references, (str, bytes, dict)):
            raise SavedViewError("saved_view_invalid")
        pins = []
        try:
            for reference in references:
                if len(pins) >= MAX_PINS:
                    raise SavedViewError("saved_view_pin_limit")
                pins.append(_key_from_reference(reference))
        except TypeError:
            raise SavedViewError("saved_view_invalid") from None
        return cls(tuple(pins), sort, group)

    @property
    def references(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(zip(IDENTITY_FIELDS, pin, strict=True)) for pin in self.pins)


def toggle_pin(view: SavedView, reference: dict) -> SavedView:
    """Return a new view with the exact identity removed or appended."""

    key = _key_from_reference(reference)
    if key in view.pins:
        return SavedView(tuple(pin for pin in view.pins if pin != key), view.sort, view.group)
    if len(view.pins) >= MAX_PINS:
        raise SavedViewError("saved_view_pin_limit")
    return SavedView((*view.pins, key), view.sort, view.group)


def encode_saved_view(view: SavedView) -> bytes:
    if type(view) is not SavedView:
        raise SavedViewError("saved_view_invalid")
    return _document_bytes(view.pins, view.sort, view.group)


def decode_saved_view(payload: bytes) -> SavedView:
    if type(payload) is not bytes:
        raise SavedViewError("saved_view_invalid")
    if len(payload) > MAX_STATE_BYTES:
        raise SavedViewError("saved_view_too_large")
    try:
        document = decode_document(payload, max_bytes=MAX_STATE_BYTES, max_depth=8, max_nodes=512)
    except WireError as error:
        code = "saved_view_too_large" if str(error) == "byte_limit" else "saved_view_invalid"
        raise SavedViewError(code) from None
    if type(document) is not dict or set(document) != _FORMAT_FIELDS:
        raise SavedViewError("saved_view_invalid")
    version = document["version"]
    if type(version) is not int:
        raise SavedViewError("saved_view_invalid")
    if version != VERSION:
        raise SavedViewError("saved_view_unsupported_version")
    raw_pins = document["pins"]
    if type(raw_pins) is not list or len(raw_pins) > MAX_PINS:
        raise SavedViewError("saved_view_pin_limit")
    pins = tuple(_key_from_reference(reference) for reference in raw_pins)
    try:
        return SavedView(pins, document["sort"], document["group"])
    except SavedViewError:
        raise


def order_pinned_rows(rows: Iterable[dict], view: SavedView) -> list[dict]:
    """Move matching pins first in pin order, preserving every other row order.

    This operates on already-filtered rows and never mutates either input.
    Malformed row identities remain in the ordinary remainder.
    """

    source = list(rows)
    matches: dict[IdentityKey, list[int]] = {}
    for index, row in enumerate(source):
        if type(row) is not dict:
            continue
        try:
            key = _key_from_reference(row.get("identity"))
        except SavedViewError:
            continue
        matches.setdefault(key, []).append(index)
    pinned_indices: set[int] = set()
    result = []
    for key in view.pins:
        for index in matches.get(key, ()):
            if index not in pinned_indices:
                result.append(source[index])
                pinned_indices.add(index)
    result.extend(row for index, row in enumerate(source) if index not in pinned_indices)
    return result


def select_state_root(*, environ: dict | None = None, home: Path | None = None) -> Path:
    """Resolve XDG_STATE_HOME without touching the filesystem."""

    environ = os.environ if environ is None else environ
    configured = environ.get("XDG_STATE_HOME")
    if configured:
        if type(configured) is not str or "\x00" in configured:
            raise SavedViewError("saved_view_state_root_unsafe")
        root = Path(configured)
        if not root.is_absolute() or ".." in root.parts:
            raise SavedViewError("saved_view_state_root_unsafe")
        root = Path(os.path.normpath(configured))
    else:
        home = Path.home() if home is None else Path(home)
        if not home.is_absolute() or ".." in home.parts:
            raise SavedViewError("saved_view_state_root_unsafe")
        root = Path(os.path.normpath(str(home / ".local" / "state")))
    if not root.is_absolute() or ".." in root.parts:
        raise SavedViewError("saved_view_state_root_unsafe")
    return root


def _directory_flags() -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if type(nofollow) is not int or not hasattr(os, "O_DIRECTORY"):
        raise SavedViewError("saved_view_state_root_unsafe")
    return os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | nofollow


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute() or ".." in path.parts or Path(os.path.normpath(str(path))) != path:
        raise SavedViewError("saved_view_state_root_unsafe")
    flags = _directory_flags()
    try:
        current = os.open("/", flags)
    except OSError:
        raise SavedViewError("saved_view_state_root_unavailable") from None
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = next_fd
        info = os.fstat(current)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o022
        ):
            raise SavedViewError("saved_view_state_root_unsafe")
        return current
    except SavedViewError:
        os.close(current)
        raise
    except FileNotFoundError:
        os.close(current)
        raise SavedViewError("saved_view_state_root_unavailable") from None
    except OSError:
        os.close(current)
        raise SavedViewError("saved_view_state_root_unsafe") from None


def _open_application_directory(root_fd: int, *, create: bool) -> int | None:
    flags = _directory_flags()
    created = False
    try:
        try:
            app_fd = os.open(APP_DIRECTORY, flags, dir_fd=root_fd)
        except FileNotFoundError:
            if not create:
                return None
            try:
                os.mkdir(APP_DIRECTORY, mode=0o700, dir_fd=root_fd)
                created = True
            except FileExistsError:
                pass
            app_fd = os.open(APP_DIRECTORY, flags, dir_fd=root_fd)
    except OSError:
        raise SavedViewError("saved_view_directory_unsafe") from None
    info = os.fstat(app_fd)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o022
    ):
        os.close(app_fd)
        raise SavedViewError("saved_view_directory_unsafe")
    if created:
        try:
            os.fchmod(app_fd, 0o700)
        except OSError:
            os.close(app_fd)
            raise SavedViewError("saved_view_directory_unsafe") from None
    return app_fd


def _read_at(app_fd: int) -> bytes | None:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(STATE_FILENAME, flags, dir_fd=app_fd)
    except FileNotFoundError:
        return None
    except OSError:
        raise SavedViewError("saved_view_file_unsafe") from None
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise SavedViewError("saved_view_file_unsafe")
        if info.st_size > MAX_STATE_BYTES:
            raise SavedViewError("saved_view_too_large")
        result = bytearray()
        while len(result) <= MAX_STATE_BYTES:
            chunk = os.read(fd, min(8192, MAX_STATE_BYTES + 1 - len(result)))
            if not chunk:
                break
            result.extend(chunk)
        if len(result) > MAX_STATE_BYTES:
            raise SavedViewError("saved_view_too_large")
        payload = bytes(result)
        decode_saved_view(payload)
        return payload
    except SavedViewError:
        raise
    except OSError:
        raise SavedViewError("saved_view_io_failed") from None
    finally:
        os.close(fd)


def load_view_bytes(state_root: Path) -> bytes | None:
    """Read and validate the optional state file; missing state is normal."""

    root_fd = _open_absolute_directory(Path(state_root))
    try:
        app_fd = _open_application_directory(root_fd, create=False)
        if app_fd is None:
            return None
        try:
            return _read_at(app_fd)
        finally:
            os.close(app_fd)
    finally:
        os.close(root_fd)


def save_view_bytes(state_root: Path, payload: bytes) -> None:
    """Validate and atomically save a complete view under a verified app dir."""

    view = decode_saved_view(payload)
    payload = encode_saved_view(view)
    root_fd = _open_absolute_directory(Path(state_root))
    try:
        app_fd = _open_application_directory(root_fd, create=True)
        assert app_fd is not None
        try:
            # A save may not replace a file that became corrupt or unsafe since
            # startup. Valid concurrent views remain complete last-writer-wins.
            _read_at(app_fd)
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0)
            )
            fd = None
            temp_name = None
            try:
                for _ in range(4):
                    candidate = f".{STATE_FILENAME}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
                    try:
                        fd = os.open(candidate, flags, 0o600, dir_fd=app_fd)
                    except FileExistsError:
                        continue
                    except OSError:
                        raise SavedViewError("saved_view_io_failed") from None
                    temp_name = candidate
                    break
                if fd is None or temp_name is None:
                    raise SavedViewError("saved_view_io_failed")
                os.fchmod(fd, 0o600)
                offset = 0
                while offset < len(payload):
                    written = os.write(fd, payload[offset:])
                    if written <= 0:
                        raise SavedViewError("saved_view_io_failed")
                    offset += written
                closing_fd, fd = fd, None
                os.close(closing_fd)

                # Recheck the destination immediately before replacement.
                _read_at(app_fd)
                os.replace(
                    temp_name,
                    STATE_FILENAME,
                    src_dir_fd=app_fd,
                    dst_dir_fd=app_fd,
                )
                temp_name = None
            except SavedViewError:
                raise
            except OSError:
                raise SavedViewError("saved_view_io_failed") from None
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                if temp_name:
                    try:
                        os.unlink(temp_name, dir_fd=app_fd)
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
        finally:
            os.close(app_fd)
    finally:
        os.close(root_fd)


@dataclass(frozen=True)
class _ChildResult:
    output: bytes | None
    error: str | None = None
    timed_out: bool = False


async def _join_owned(task: asyncio.Task):
    """Join an owned task despite repeated caller cancellation."""

    interrupted = False
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            interrupted = True
    try:
        return task.result(), interrupted
    except (Exception, asyncio.CancelledError) as error:
        return error, interrupted


class SavedViewController:
    """Async isolated state I/O with one coalesced serial save queue."""

    def __init__(
        self,
        state_root: Path | None,
        *,
        initial_error: str | None = None,
        helper_path: Path | None = None,
        python: str | None = None,
        load_timeout: float = DEFAULT_LOAD_TIMEOUT,
        save_timeout: float = DEFAULT_SAVE_TIMEOUT,
        shutdown_drain: float = DEFAULT_SHUTDOWN_DRAIN,
        reap_timeout: float = DEFAULT_REAP_TIMEOUT,
    ) -> None:
        if any(
            not _finite_positive(value)
            for value in (load_timeout, save_timeout, shutdown_drain, reap_timeout)
        ):
            raise ValueError("saved_view_timeout")
        selected_root = Path(state_root) if state_root is not None else None
        if selected_root is not None and (
            not selected_root.is_absolute() or ".." in selected_root.parts
        ):
            selected_root = None
            initial_error = initial_error or "saved_view_state_root_unsafe"
        self.state_root = selected_root
        self.helper_path = (
            Path(os.path.abspath(__file__)).with_name("dashboard_view_worker.py")
            if helper_path is None
            else Path(helper_path)
        )
        self.python = python or sys.executable
        self.load_timeout = float(load_timeout)
        self.save_timeout = float(save_timeout)
        self.shutdown_drain = float(shutdown_drain)
        self.reap_timeout = float(reap_timeout)
        self.view = SavedView()
        self.persisted_view: SavedView | None = None
        self.changed = asyncio.Event()
        self.persistence_enabled = selected_root is not None and initial_error is None
        self.warning = initial_error
        self.cleanup_error: str | None = None
        self._load_attempted = False
        self._loaded = False
        self._closed = False
        self._pending: bytes | None = None
        self._save_task: asyncio.Task | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._spawn_task: asyncio.Task | None = None
        self._starting_process = False
        self._abort_requested = False

    @classmethod
    def from_environment(
        cls,
        *,
        environ: dict | None = None,
        home: Path | None = None,
        **options,
    ) -> SavedViewController:
        try:
            root = select_state_root(environ=environ, home=home)
        except SavedViewError as error:
            return cls(None, initial_error=error.code, **options)
        return cls(root, **options)

    async def load(self) -> SavedView:
        if self._load_attempted:
            return self.view
        self._load_attempted = True
        if not self.persistence_enabled or self.state_root is None:
            self._loaded = True
            return self.view
        result = await self._invoke("load", None, self.load_timeout)
        if result.error is not None:
            self._disable(result.error)
            self._loaded = True
            return self.view
        output = result.output or b""
        if output == b"MISSING\n":
            self.persisted_view = SavedView()
            self._loaded = True
            return self.view
        if not output.startswith(b"OK\n"):
            self._disable(_parse_worker_error(output) or "saved_view_helper_failed")
            self._loaded = True
            return self.view
        try:
            self.view = decode_saved_view(output[3:])
            self.persisted_view = self.view
        except SavedViewError as error:
            self._disable(error.code)
        self._loaded = True
        return self.view

    def submit(self, view: SavedView) -> None:
        """Queue one accepted complete view without doing synchronous I/O."""

        if type(view) is not SavedView:
            raise SavedViewError("saved_view_invalid")
        if not self._loaded:
            raise RuntimeError("saved_view_not_loaded")
        self.view = view
        self.changed.set()
        if self._closed or not self.persistence_enabled:
            return
        try:
            self._pending = encode_saved_view(view)
        except SavedViewError as error:
            self._disable(error.code)
            return
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(self._save_loop(), name="dashboard-saved-view")

    async def _save_loop(self) -> None:
        while (
            self._pending is not None
            and self.persistence_enabled
            and not self._abort_requested
        ):
            payload, self._pending = self._pending, None
            try:
                result = await self._invoke("save", payload, self.save_timeout)
            except Exception:
                self.cleanup_error = self.cleanup_error or "saved_view_internal_failure"
                self._disable("saved_view_internal_failure")
                return
            if result.error is not None:
                self._disable(result.error)
                return
            output = result.output or b""
            if output != b"OK\n":
                self._disable(_parse_worker_error(output) or "saved_view_helper_failed")
                return
            self.persisted_view = decode_saved_view(payload)
            self.changed.set()

    async def _invoke(self, operation: str, payload: bytes | None, timeout: float) -> _ChildResult:
        if self.state_root is None:
            return _ChildResult(None, "saved_view_state_root_unsafe")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        self._starting_process = True
        spawn = asyncio.create_task(
            asyncio.create_subprocess_exec(
                self.python,
                "-I",
                "-B",
                str(self.helper_path),
                operation,
                str(self.state_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        )
        self._spawn_task = spawn
        spawn_timed_out = False
        interrupted = False
        try:
            try:
                await asyncio.wait_for(asyncio.shield(spawn), max(0.0, deadline - loop.time()))
            except TimeoutError:
                spawn_timed_out = True
            except asyncio.CancelledError:
                spawn_timed_out = True
                interrupted = True
            except Exception:
                pass
            if spawn_timed_out:
                # The spawn operation itself is owned. If it crosses the
                # operation deadline, wait for its handle so a late child can
                # be killed and reaped instead of orphaned.
                reap_deadline = loop.time() + self.reap_timeout
                while not spawn.done():
                    remaining = reap_deadline - loop.time()
                    if remaining <= 0:
                        self.cleanup_error = self.cleanup_error or "saved_view_cleanup_timeout"
                        break
                    try:
                        await asyncio.wait_for(asyncio.shield(spawn), remaining)
                    except TimeoutError:
                        self.cleanup_error = self.cleanup_error or "saved_view_cleanup_timeout"
                        break
                    except asyncio.CancelledError:
                        interrupted = True
            if spawn_timed_out and not spawn.done():
                while not spawn.done():
                    try:
                        await asyncio.wait({spawn})
                    except asyncio.CancelledError:
                        interrupted = True
            try:
                process = spawn.result()
            except Exception:
                if interrupted:
                    raise asyncio.CancelledError from None
                if spawn_timed_out:
                    return _ChildResult(None, _timeout_code(operation), True)
                return _ChildResult(None, "saved_view_helper_unavailable")
        except asyncio.CancelledError:
            interrupted = True
            if not spawn.done():
                while not spawn.done():
                    try:
                        await asyncio.wait({spawn})
                    except asyncio.CancelledError:
                        pass
            try:
                process = spawn.result()
            except Exception:
                self._starting_process = False
                self._spawn_task = None
                raise asyncio.CancelledError from None
        finally:
            self._starting_process = False
            self._spawn_task = None
        self._process = process
        communication = asyncio.create_task(process.communicate(payload))
        reap = asyncio.create_task(process.wait())
        if spawn_timed_out or self._abort_requested:
            reaped_cancelled = await self._kill_and_join(process, communication, reap)
            self._process = None
            if interrupted or reaped_cancelled:
                raise asyncio.CancelledError from None
            return _ChildResult(None, _timeout_code(operation), True)
        try:
            output, _ = await asyncio.wait_for(
                asyncio.shield(communication), max(0.0, deadline - loop.time())
            )
        except TimeoutError:
            interrupted = await self._kill_and_join(process, communication, reap)
            if interrupted:
                raise asyncio.CancelledError from None
            return _ChildResult(
                None,
                _timeout_code(operation),
                True,
            )
        except asyncio.CancelledError:
            await self._kill_and_join(process, communication, reap)
            raise
        except Exception:
            await self._kill_and_join(process, communication, reap)
            return _ChildResult(None, "saved_view_helper_failed")
        finally:
            if self._process is process:
                self._process = None
        try:
            await asyncio.shield(reap)
        except asyncio.CancelledError:
            await self._kill_and_join(process, communication, reap)
            raise
        if process.returncode != 0:
            return _ChildResult(None, "saved_view_helper_failed")
        if len(output) > MAX_STATE_BYTES + 16:
            return _ChildResult(None, "saved_view_helper_failed")
        return _ChildResult(output)

    async def _kill_and_join(
        self,
        process: asyncio.subprocess.Process,
        communication: asyncio.Task,
        reap: asyncio.Task,
    ) -> bool:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        deadline = asyncio.get_running_loop().time() + self.reap_timeout
        over_budget = False
        interrupted = False
        owned = {communication, reap}
        pending = {task for task in owned if not task.done()}
        while pending:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                over_budget = True
                break
            try:
                done, pending = await asyncio.wait(
                    pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED
                )
                if not done and pending:
                    over_budget = True
                    break
            except TimeoutError:
                over_budget = True
                break
            except asyncio.CancelledError:
                interrupted = True
                pending = {task for task in owned if not task.done()}
        if over_budget and pending:
            self.cleanup_error = self.cleanup_error or "saved_view_cleanup_timeout"
            try:
                process.kill()
            except ProcessLookupError:
                pass
            while pending:
                try:
                    _, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                except asyncio.CancelledError:
                    interrupted = True
                pending = {task for task in owned if not task.done()}
        for task in owned:
            if task.done():
                try:
                    task.result()
                except Exception:
                    pass
        return interrupted

    async def close(self) -> None:
        """Drain accepted saves briefly, then kill and join the owned helper."""

        self._closed = True
        task = self._save_task
        if task is None:
            return
        if task.done():
            self._observe_save_task(task)
            return
        interrupted = False
        deadline = asyncio.get_running_loop().time() + self.shutdown_drain
        while not task.done():
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                self._disable("saved_view_shutdown_timeout")
                self._pending = None
                self._abort_requested = True
                process = self._process
                if process is not None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                reap_deadline = asyncio.get_running_loop().time() + self.reap_timeout
                while not task.done():
                    reap_remaining = reap_deadline - asyncio.get_running_loop().time()
                    if reap_remaining <= 0:
                        self.cleanup_error = self.cleanup_error or "saved_view_cleanup_timeout"
                        break
                    try:
                        await asyncio.wait_for(asyncio.shield(task), reap_remaining)
                    except TimeoutError:
                        self.cleanup_error = self.cleanup_error or "saved_view_cleanup_timeout"
                        break
                    except asyncio.CancelledError:
                        interrupted = True
                    except Exception:
                        break
                break
            try:
                await asyncio.wait_for(asyncio.shield(task), remaining)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                interrupted = True
            except Exception:
                break
        if not task.done():
            _, cancelled = await _join_owned(task)
            interrupted = interrupted or cancelled
        self._observe_save_task(task)
        if interrupted:
            raise asyncio.CancelledError

    def _observe_save_task(self, task: asyncio.Task) -> None:
        if task.cancelled():
            self.cleanup_error = self.cleanup_error or "saved_view_internal_failure"
            self._disable("saved_view_internal_failure")
            return
        try:
            failure = task.exception()
        except asyncio.CancelledError:
            failure = True
        if failure:
            self.cleanup_error = self.cleanup_error or "saved_view_internal_failure"
            self._disable("saved_view_internal_failure")

    def _disable(self, code: str) -> None:
        self.persistence_enabled = False
        self._pending = None
        self.changed.set()
        if self.warning is None:
            self.warning = (
                code
                if code in _ERROR_CODES or code.startswith("saved_view_")
                else "saved_view_unavailable"
            )


def _parse_worker_error(output: bytes) -> str | None:
    if not output.startswith(b"ERROR\n"):
        return None
    code = output[6:].strip().decode("ascii", "ignore")
    return (
        code
        if code in _ERROR_CODES and len(code) <= 64
        else "saved_view_helper_failed"
    )


def _finite_positive(value) -> bool:
    if type(value) not in {int, float} or value <= 0:
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _timeout_code(operation: str) -> str:
    return "saved_view_load_timeout" if operation == "load" else "saved_view_save_timeout"
