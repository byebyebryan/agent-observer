"""Bounded local Git metadata enrichment; no Git commands, hooks or networking."""

from __future__ import annotations

import copy
import os
import stat
import time
from pathlib import Path, PurePosixPath

from .contract import SCOPE, array, obj, text, validate_shape

MAX_CONFIG_BYTES = 128 * 1024

CONFIG = obj(
    roots=array(obj(key=text(128, pattern=SCOPE), path=text()), 64),
    projects=array(
        obj(
            rootKey=text(128, pattern=SCOPE),
            relativePath=text(),
            projectKey=text(256, pattern=SCOPE),
        ),
        256,
    ),
)
_CACHE = {}


def load_config(path):
    """Read one bounded regular configuration file; no live reload or stdin."""
    from .bounded_json import decode_document

    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("workspace_config_file_required")
        if info.st_size > MAX_CONFIG_BYTES:
            raise ValueError("workspace_config_limit")
        value = decode_document(stream.read(MAX_CONFIG_BYTES + 1), max_bytes=MAX_CONFIG_BYTES)
    return validate_config(value)


def validate_config(config):
    validate_shape(config, CONFIG)
    keys = set()
    for root in config["roots"]:
        path = Path(root["path"])
        if not path.is_absolute() or ".." in path.parts or root["key"] in keys:
            raise ValueError("invalid_workspace_root")
        keys.add(root["key"])
    mappings = set()
    for mapping in config["projects"]:
        path = PurePosixPath(mapping["relativePath"])
        key = mapping["rootKey"], str(path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or mapping["rootKey"] not in keys
            or key in mappings
        ):
            raise ValueError("invalid_project_mapping")
        mappings.add(key)
    return config


def _small_text(path):
    if not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("git_metadata_unavailable")
    with path.open("rb") as stream:
        data = stream.read(4097)
    if len(data) > 4096:
        raise ValueError("git_metadata_limit")
    return data.decode("utf-8", "strict").strip()


def inspect_git(cwd):
    """Read only .git pointers and commondir, with bounded ancestor depth."""
    now = time.monotonic()
    cached = _CACHE.get(str(cwd))
    if cached and now - cached[0] < 15:
        return copy.deepcopy(cached[1])
    root = cwd
    repo = None
    for _ in range(64):
        marker = root / ".git"
        if marker.is_dir():
            gitdir = marker.resolve(strict=True)
        elif marker.is_file():
            value = _small_text(marker)
            if not value.startswith("gitdir: "):
                raise ValueError("git_metadata_unavailable")
            target = Path(value[8:])
            gitdir = (target if target.is_absolute() else root / target).resolve(strict=True)
            if not gitdir.is_dir():
                raise ValueError("git_metadata_unavailable")
        else:
            if root == root.parent:
                break
            root = root.parent
            continue
        common = gitdir
        if (gitdir / "commondir").exists():
            target = Path(_small_text(gitdir / "commondir"))
            common = (target if target.is_absolute() else gitdir / target).resolve(strict=True)
            if not common.is_dir():
                raise ValueError("git_metadata_unavailable")
        repo = {
            "root": str(root),
            "commonDir": str(common),
            "relativePath": str(cwd.relative_to(root)),
        }
        break
    if len(_CACHE) >= 256:
        _CACHE.clear()
    _CACHE[str(cwd)] = now, repo
    return copy.deepcopy(repo)


def context(cwd, config):
    result = {
        "health": "unavailable",
        "reason": "cwd_unavailable",
        "root": None,
        "rootKey": None,
        "relativePath": None,
        "projectKey": None,
        "repo": None,
    }
    if cwd is None:
        return result
    path = Path(cwd)
    if not path.is_absolute():
        return result
    try:
        path = path.resolve(strict=True)
        if not path.is_dir():
            return result
        candidates = []
        for entry in config["roots"]:
            try:
                root = Path(entry["path"]).resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if path.is_relative_to(root):
                candidates.append((len(root.parts), entry["key"], root))
        if candidates:
            _, key, root = max(candidates)
            relative = path.relative_to(root)
            result.update(root=str(root), rootKey=key, relativePath=str(relative))
            mappings = [
                entry
                for entry in config["projects"]
                if entry["rootKey"] == key
                and relative.is_relative_to(PurePosixPath(entry["relativePath"]))
            ]
            if mappings:
                result["projectKey"] = max(
                    mappings, key=lambda entry: len(PurePosixPath(entry["relativePath"]).parts)
                )["projectKey"]
        result["repo"] = inspect_git(path)
        result.update(health="current", reason="local_metadata")
    except (OSError, ValueError, UnicodeError, RuntimeError):
        result.update(health="unavailable", reason="workspace_unavailable")
    return result


def enrich(snapshot, config):
    validate_config(config)
    deadline = time.monotonic() + 2.0
    contexts = {}
    for row in snapshot["sessions"]:
        cwd = row["cwd"]
        if cwd not in contexts:
            if len(contexts) >= 256 or time.monotonic() > deadline:
                value = context(None, config)
                value["reason"] = "workspace_limit"
            else:
                value = context(cwd, config)
            contexts[cwd] = value
        row["workspace"] = copy.deepcopy(contexts[cwd])
