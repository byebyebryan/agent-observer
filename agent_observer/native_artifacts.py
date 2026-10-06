"""Exact native capability registrations shared by passive reads and writes.

No provider entrypoints are invoked. A registration is bounded to an inspected
artifact, not an automatic version-range claim or a user-configurable bypass.
"""

from __future__ import annotations

import hashlib
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Artifact:
    provider: str
    version: str
    sha256: str
    path: str
    capabilities: frozenset[str] = frozenset({"entry"})


CODEX = Artifact(
    "codex", "0.160.0",
    "12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad",
    "/opt/openai-codex/bin/codex",
    frozenset({"entry", "managed_entry", "managed_read", "managed_work", "managed_approval", "managed_activity"}),
)
CODEX_DAEMON = Artifact(
    "codex", "0.160.1",
    "f34a4d2301892ae96c90097786bfe5dc269f187b6f69faf42a7b357b8c081e35",
    "packages/app-server-daemon/releases/0.160.1-x86_64-unknown-linux-musl/bin/codex",
    # Independent isolated native source and 0.160.0-client/0.160.1-peer proof.
    # This daemon image is not accepted as a new CLI entry executable.
    frozenset({"managed_entry", "managed_read", "managed_work", "managed_approval", "managed_activity", "completion_only_activity", "managed_outcome", "managed_question"}),
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
    # Monitoring proof: foreground/Stop continuation/held child and input;
    # background later-turn activity, queued-work exclusion and job questions.
    frozenset({"entry", "input_wait", "job_question", "registry_phase", "interactive_readiness"}),
)
ARTIFACTS = (CODEX, CODEX_DAEMON, CLAUDE_PREVIOUS, CLAUDE)


def registered(provider, digest, *, capability=None):
    return next((a for a in ARTIFACTS if a.provider == provider and a.sha256 == digest
                 and (capability is None or capability in a.capabilities)), None)


def supported_versions(provider, *, capability=None):
    return tuple(dict.fromkeys(a.version for a in ARTIFACTS if a.provider == provider
                               and (capability is None or capability in a.capabilities)))


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
        or not 0 < before.st_size <= 512 * 1024 * 1024
    ):
        raise ValueError("runtime_artifact_not_accepted")
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
        artifact = registered(provider, digest.hexdigest())
        if artifact is None:
            raise ValueError("runtime_artifact_not_accepted")
        if cache is not None and len(cache) < 32:
            cache[key] = artifact
    if _signature(os.fstat(fd)) != _signature(before):
        raise ValueError("runtime_artifact_changed")
    return Inspection((before.st_dev, before.st_ino), artifact)


def inspect_installed(path: Path, provider: str, *, timeout=3.0):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError:
        raise ValueError("runtime_artifact_unavailable") from None
    try:
        return _inspect_fd(fd, provider, timeout=timeout)
    finally:
        os.close(fd)


def inspect_process(pid: int, provider: str, *, cache=None):
    # /proc/PID/exe is deliberately a kernel symlink. Inspect the open image,
    # including a replaced/deleted executable, rather than the current PATH file.
    fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        value = _inspect_fd(fd, provider, timeout=3.0, cache=cache)
        current = os.stat(f"/proc/{pid}/exe")
        if (current.st_dev, current.st_ino) != value.stamp:
            raise ValueError("runtime_artifact_changed")
        return value
    finally:
        os.close(fd)
