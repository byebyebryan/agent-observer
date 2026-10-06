"""Bounded current-store metadata fallback, independent of a live Codex peer.

Only the required typed thread/session/turn projections are accepted. Unrelated
additions do not change compatibility. No provider invocation or conversation SQL is
used. Missing/changing metadata remains partial and never establishes presence.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path

from .activity import codex_activity, ordering
from .bounded_json import decode_document
from .codex_metadata import saved_thread_metadata
PROJECTIONS = {
    "state_5.sqlite": ("threads", {
        "id": "TEXT", "rollout_path": "TEXT", "source": "TEXT",
        "thread_source": "TEXT", "name": "TEXT", "created_at": "INTEGER",
        "updated_at": "INTEGER", "archived": "INTEGER",
    }),
    "thread_history_1.sqlite": ("thread_turns", {
        "thread_id": "TEXT", "started_at": "INTEGER", "completed_at": "INTEGER",
        "rollout_ordinal": "INTEGER",
    }),
}


def _regular(path, limit):
    info = path.lstat()
    if (
        path.resolve(strict=True) != path or not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid() or info.st_mode & 0o022 or info.st_size > limit
    ):
        raise ValueError("saved_store_ownership_mismatch")
    return info.st_dev, info.st_ino


def store_home(home):
    if home.resolve(strict=True) != home or home.stat().st_uid != os.geteuid():
        raise ValueError("saved_store_ownership_mismatch")
    config = home / "config.toml"
    if config.exists():
        _regular(config, 1024 * 1024)
        value = tomllib.loads(config.read_text()).get("sqlite_home")
        if value is not None:
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError("saved_store_selector_unsupported")
            root = Path(value)
            if root.resolve(strict=True) != root or root.stat().st_uid != os.geteuid():
                raise ValueError("saved_store_ownership_mismatch")
            return root
    return home


@contextmanager
def database(path, *, deadline):
    stamp = _regular(path, 16 * 1024 * 1024 * 1024)
    # WAL readers must not create ordinary sidecars. Accept existing owned
    # sidecars or a clean checkpointed DB; reject incomplete WAL state.
    wal, shm = Path(str(path) + "-wal"), Path(str(path) + "-shm")
    if wal.exists() != shm.exists():
        raise ValueError("saved_store_wal_unavailable")
    for sidecar in (wal, shm):
        if sidecar.exists():
            _regular(sidecar, 512 * 1024 * 1024)
    sidecars = (wal.exists(), shm.exists())
    uri = path.as_uri() + "?mode=ro" + ("&immutable=1" if not sidecars[0] else "")
    connection = sqlite3.connect(uri, uri=True, timeout=0.1)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        connection.execute("BEGIN")
        table, required = PROJECTIONS[path.name]
        kind = connection.execute(
            "SELECT type FROM sqlite_schema WHERE name=?", (table,)
        ).fetchone()
        columns = connection.execute("PRAGMA table_info(" + table + ")").fetchall()
        actual = {row[1]: row[2].upper() for row in columns}
        if kind != ("table",) or len(columns) > 256 or any(
            actual.get(name) != declared for name, declared in required.items()
        ):
            raise ValueError("saved_store_schema_unsupported")
        yield connection
        if _regular(path, 16 * 1024 * 1024 * 1024) != stamp:
            raise ValueError("saved_store_incarnation_changed")
        if (wal.exists(), shm.exists()) != sidecars:
            raise ValueError("saved_store_wal_changed")
    finally:
        connection.close()


def session_metadata(path, home, thread_id):
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("saved_rollout_unavailable")
    path = Path(path)
    if not path.is_relative_to(home / "sessions") or path.resolve(strict=True) != path:
        raise ValueError("saved_rollout_scope_mismatch")
    stamp = _regular(path, 512 * 1024 * 1024)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) != stamp:
            raise ValueError("saved_rollout_incarnation_changed")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            line = stream.readline(64 * 1024 + 1)
        if not line.endswith(b"\n") or len(line) > 64 * 1024:
            raise ValueError("saved_identity_metadata_limit")
        value = decode_document(line, max_bytes=64 * 1024)
        payload = value.get("payload") if isinstance(value, dict) else None
        if not isinstance(value, dict) or value.get("type") != "session_meta" or not isinstance(payload, dict) or payload.get("id") != thread_id:
            raise ValueError("saved_identity_conflict")
        sid = payload.get("session_id")
        if _regular(path, 512 * 1024 * 1024) != stamp:
            raise ValueError("saved_rollout_incarnation_changed")
        return sid, payload.get("cwd")
    finally:
        os.close(fd)


def collect_saved(home, *, host_scope, namespace, history_limit=100, timeout=3.0):
    deadline = time.monotonic() + timeout
    root = store_home(home)
    rows, issues = [], []
    with database(root / "state_5.sqlite", deadline=deadline) as catalog, database(
        root / "thread_history_1.sqlite", deadline=deadline
    ) as history:
        records = catalog.execute(
            "SELECT id, rollout_path, source, thread_source, name, created_at, updated_at "
            "FROM threads WHERE archived=0 AND thread_source='user' LIMIT 1001"
        ).fetchall()
        if len(records) > 1000:
            issues.append("saved_catalog_limit")
        for identifier, path, source, kind, name, created, updated in records[:1000]:
            if time.monotonic() > deadline:
                issues.append("saved_metadata_timeout")
                break
            try:
                turn = history.execute(
                    "SELECT started_at, completed_at FROM thread_turns WHERE thread_id=? "
                    "ORDER BY rollout_ordinal DESC LIMIT 1", (identifier,)
                ).fetchone()
                # This source covers persisted conversation history, not blank
                # store placeholders. Live discovery retains current blank IDs.
                if turn is None:
                    continue
                sid, recorded_cwd = session_metadata(path, home, identifier)
                row = saved_thread_metadata({
                    "id": identifier, "sessionId": sid, "name": name, "cwd": recorded_cwd,
                    "source": source if source in {"cli", "vscode", "exec", "appServer"} else "unknown",
                    "threadSource": kind, "createdAt": created, "updatedAt": updated,
                }, host_scope=host_scope, namespace=namespace, runtime_version="unknown")
                row["cwdSource"] = "codex_session_metadata"
                row["activity"] = codex_activity({"data": [{
                    "itemsView": "notLoaded", "items": [], "startedAt": turn[0], "completedAt": turn[1],
                }]}, completion_only=True)
                if row["activity"]["at"] is not None:
                    row["activity"]["source"] = "codex_saved_turn_metadata"
                rows.append(row)
            except (ValueError, OSError):
                issues.append("saved_row_metadata_unavailable")
        selected = sorted(rows, key=ordering)[:history_limit]
        if len(rows) > history_limit:
            issues.append("saved_history_limit")
    return {"sessions": selected, "coverage": {"complete": False, "reason": "saved_metadata_scan"},
            "issues": list(dict.fromkeys(issues)), "activitySupported": True}
