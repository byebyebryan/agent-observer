"""Passive executable identity; hashes record context, never compatibility.

Historical images below supply diagnostic provenance only. Callers validate
their provider locator/namespace and required native contracts independently.
No provider entrypoint is invoked to inspect an executable.
"""

from __future__ import annotations

import hashlib
import os
import stat
import time
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class Artifact:
    provider: str
    version: str
    sha256: str
    path: str


CODEX = Artifact(
    "codex", "0.160.0",
    "12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad",
    "/opt/openai-codex/bin/codex",
)
CODEX_DAEMON = Artifact(
    "codex", "0.160.1",
    "f34a4d2301892ae96c90097786bfe5dc269f187b6f69faf42a7b357b8c081e35",
    "packages/app-server-daemon/releases/0.160.1-x86_64-unknown-linux-musl/bin/codex",
)
CLAUDE_PREVIOUS = Artifact(
    "claude", "2.1.287",
    "3920489a5109cff5786a1a392c25277408ff22bc796d5edb9c16a60e5a1718f0",
    "/opt/claude-code/bin/claude",
)
CLAUDE = Artifact(
    "claude", "2.1.289",
    "a186b99e4a9c88366cd49df2f7dad56c61fc306ef0140b19ee64b7c42a8d1348",
    "/opt/claude-code/bin/claude",
)
HISTORICAL_IMAGES = (CODEX, CODEX_DAEMON, CLAUDE_PREVIOUS, CLAUDE)


def historical_image(provider, digest):
    return next((a for a in HISTORICAL_IMAGES if a.provider == provider and a.sha256 == digest), None)


@dataclass(frozen=True)
class Inspection:
    stamp: tuple[int, int]
    artifact: Artifact


def _signature(info):
    return (
        info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
        info.st_uid, info.st_mode,
    )


def _inspect_fd(fd, provider, *, timeout, cache=None):
    before = os.fstat(fd)
    if (
        not stat.S_ISREG(before.st_mode) or before.st_mode & 0o022
        or before.st_uid not in {0, os.geteuid()}
        or not 0 < before.st_size <= 512 * 1024 * 1024
    ):
        raise ValueError("runtime_image_ownership_mismatch")
    key = (provider, _signature(before))
    if cache is not None and key in cache:
        artifact = cache[key]
    else:
        digest = hashlib.sha256()
        total = 0
        deadline = time.monotonic() + timeout
        while chunk := os.read(fd, 1024 * 1024):
            total += len(chunk)
            if total > 512 * 1024 * 1024 or time.monotonic() > deadline:
                raise ValueError("runtime_artifact_inspection_limit")
            digest.update(chunk)
        if total != before.st_size:
            raise ValueError("runtime_artifact_changed")
        actual_hash = digest.hexdigest()
        historical = historical_image(provider, actual_hash)
        artifact = Artifact(provider, historical.version if historical else "unknown",
                            actual_hash, "")
        if cache is not None and len(cache) < 32:
            cache[key] = artifact
    if _signature(os.fstat(fd)) != _signature(before):
        raise ValueError("runtime_artifact_changed")
    return Inspection((before.st_dev, before.st_ino), artifact)


def inspect_installed(path: Path, provider: str, *, timeout=3.0):
    try:
        if provider not in {"codex", "claude"} or not path.is_absolute() or path.resolve(strict=True) != path:
            raise ValueError("runtime_image_ownership_mismatch")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError:
        raise ValueError("runtime_artifact_unavailable") from None
    try:
        value = _inspect_fd(fd, provider, timeout=timeout)
        return replace(value, artifact=replace(value.artifact, path=str(path)))
    finally:
        os.close(fd)


def inspect_process(pid: int, provider: str, *, cache=None, expected_path: Path | None = None):
    # /proc/PID/exe is deliberately a kernel symlink. Inspect the open image,
    # including a replaced/deleted executable, rather than the current PATH file.
    if provider not in {"codex", "claude"}:
        raise ValueError("runtime_provider_unsupported")
    process = Path(f"/proc/{pid}")
    expected = expected_path or Path(CODEX.path if provider == "codex" else CLAUDE.path)
    reported = os.readlink(process / "exe")
    if reported.endswith(" (deleted)"):
        reported = reported[:-10]
    if process.stat().st_uid != os.geteuid() or reported != str(expected):
        raise ValueError("runtime_image_ownership_mismatch")
    fd = os.open(process / "exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        value = _inspect_fd(fd, provider, timeout=3.0, cache=cache)
        current = os.stat(f"/proc/{pid}/exe")
        if (current.st_dev, current.st_ino) != value.stamp:
            raise ValueError("runtime_artifact_changed")
        return replace(value, artifact=replace(value.artifact, path=str(expected)))
    finally:
        os.close(fd)
