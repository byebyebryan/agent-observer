"""Inspect an existing, contract-bound managed endpoint without launching it."""

from __future__ import annotations

import hashlib
import os
import re
import socket
import stat
import struct
import time
from dataclasses import dataclass
from pathlib import Path



class EndpointError(ValueError):
    """Bounded ownership/availability reason; never includes inspected text."""

    def __init__(self, code, *, identity=None):
        super().__init__(code)
        self.identity = identity


@dataclass(frozen=True)
class RuntimeIdentity:
    config_home: str
    endpoint: str
    pid: int
    uid: int
    start_ticks: int
    executable: str
    executable_device: int
    executable_inode: int
    version: str
    binary_sha256: str
    listener_inode: int
    endpoint_device: int
    endpoint_inode: int


def _bounded_text(path, size):
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if len(data) > size:
        raise EndpointError("metadata_limit")
    try:
        return data.decode("utf-8", "strict")
    except UnicodeError:
        raise EndpointError("invalid_runtime_metadata") from None


def _birth(proc_path):
    value = _bounded_text(proc_path / "stat", 8192)
    try:
        fields = value[value.rindex(")") + 2 :].split()
        return int(fields[19])
    except (ValueError, IndexError):
        raise EndpointError("invalid_runtime_metadata") from None


def _fingerprint(path, *, deadline):
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > 512 * 1024 * 1024 or time.monotonic() > deadline:
                raise EndpointError("binary_inspection_limit")
            digest.update(chunk)
    return digest.hexdigest()


def _endpoint_peer(target: Path, *, deadline: float) -> tuple[int, int]:
    """Read kernel peer credentials from an already existing Unix listener."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(max(0.001, deadline - time.monotonic()))
        connection.connect(str(target))
        pid, uid, _gid = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
    if pid <= 0 or uid < 0:
        raise EndpointError("runtime_peer_unavailable")
    return pid, uid


def inspect_managed_endpoint(
    config_home: Path,
    *,
    release: str | None = None,
    binary_sha256: str | None = None,
    version: str | None = None,
    proc_root: Path = Path("/proc"),
    timeout: float = 3.0,
) -> RuntimeIdentity:
    """Verify the configured managed endpoint's owning executable incarnation.

    An explicit fingerprint selects an operator proof's exact expected image;
    the default reads the owning peer instead of assuming the CLI's release.

    Kernel socket inode and filesystem inode are distinct. The listener's
    exact kernel inode must be held by the kernel-identified peer process.
    Basename, pidfile, cwd and PID alone cannot establish runtime ownership.
    """
    if (
        not isinstance(config_home, Path)
        or not config_home.is_absolute()
        or (
            any(value is not None for value in (release, binary_sha256, version))
            and (
                not isinstance(release, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", release)
                or not isinstance(binary_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", binary_sha256)
                or not isinstance(version, str)
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
            )
        )
        or type(timeout) not in (int, float)
        or not 0 < timeout <= 10
    ):
        raise EndpointError("invalid_inspection_scope")
    deadline = time.monotonic() + timeout
    uid = os.geteuid()
    try:
        # Only the proved ordinary absolute namespace form is supported yet.
        if config_home.resolve(strict=True) != config_home or ".." in config_home.parts:
            raise EndpointError("unsupported_namespace")
        control = config_home / "app-server-control/app-server-control.sock"
        if not control.is_symlink() or control.lstat().st_uid != uid:
            raise EndpointError("endpoint_unavailable")
        expected = (
            Path(f"/tmp/codex-daemon-{uid}") / hashlib.sha256(str(control).encode()).hexdigest()
        )
        target = Path(os.readlink(control))
        if target != expected:
            raise EndpointError("endpoint_namespace_mismatch")
        socket_stat = target.stat()
        if (
            not stat.S_ISSOCK(socket_stat.st_mode)
            or socket_stat.st_uid != uid
            or stat.S_IMODE(socket_stat.st_mode) != 0o600
        ):
            raise EndpointError("endpoint_ownership_mismatch")
        listeners = set()
        for line in _bounded_text(proc_root / "net/unix", 4 * 1024 * 1024).splitlines()[1:]:
            fields = line.split(maxsplit=7)
            if len(fields) != 8 or fields[7] != str(target):
                continue
            try:
                if int(fields[3], 16) & 0x10000 and int(fields[4], 16) == 1:
                    listeners.add(int(fields[6]))
            except ValueError:
                raise EndpointError("invalid_runtime_metadata") from None
        if len(listeners) != 1:
            raise EndpointError("listener_ambiguous")
        listener = next(iter(listeners))
        pid, peer_uid = _endpoint_peer(target, deadline=deadline)
        if peer_uid != uid:
            raise EndpointError("runtime_peer_identity_mismatch")
        process = proc_root / str(pid)
        birth = _birth(process)
        executable = Path(os.readlink(process / "exe"))
        release_root = config_home / "packages/app-server-daemon/releases"
        match = re.fullmatch(
            re.escape(str(release_root)) + r"/(\d+\.\d+\.\d+)-x86_64-unknown-linux-musl/bin/codex",
            str(executable),
        )
        if process.stat().st_uid != uid or match is None:
            raise EndpointError("runtime_peer_identity_mismatch")
        expected_stat = executable.stat()
        if (
            not stat.S_ISREG(expected_stat.st_mode) or expected_stat.st_uid != uid
            or expected_stat.st_mode & 0o022 or executable.resolve(strict=True) != executable
        ):
            raise EndpointError("runtime_image_ownership_mismatch")
        running_stat = (process / "exe").stat()
        if (running_stat.st_dev, running_stat.st_ino) != (
            expected_stat.st_dev,
            expected_stat.st_ino,
        ):
            raise EndpointError("runtime_peer_identity_mismatch")
        actual_digest = _fingerprint(process / "exe", deadline=deadline)
        matches = False
        for index, fd in enumerate((process / "fd").iterdir()):
            if index >= 4096 or time.monotonic() > deadline:
                raise EndpointError("process_inspection_limit")
            try:
                if os.readlink(fd) == f"socket:[{listener}]":
                    matches = True
                    break
            except FileNotFoundError:
                continue
        if not matches or birth != _birth(process):
            raise EndpointError("runtime_owner_ambiguous")
        identity = RuntimeIdentity(
            str(config_home),
            str(target),
            pid,
            uid,
            birth,
            str(executable),
            expected_stat.st_dev,
            expected_stat.st_ino,
            match.group(1),
            actual_digest,
            listener,
            socket_stat.st_dev,
            socket_stat.st_ino,
        )
        validate_incarnation(identity, proc_root=proc_root)
        if release is not None:
            expected = release_root / release / "bin/codex"
            if executable != expected or actual_digest != binary_sha256:
                raise EndpointError("runtime_binary_not_accepted", identity=identity)
            if version != match.group(1):
                raise EndpointError("runtime_version_mismatch", identity=identity)
        return identity
    except EndpointError:
        raise
    except FileNotFoundError:
        raise EndpointError("endpoint_unavailable") from None
    except (OSError, UnicodeError):
        raise EndpointError("runtime_visibility_unavailable") from None


def validate_incarnation(identity: RuntimeIdentity, *, proc_root=Path("/proc")):
    """Recheck after a read so PID reuse/updater replacement cannot look fresh."""
    try:
        process = proc_root / str(identity.pid)
        executable_stat = (process / "exe").stat()
        endpoint_stat = Path(identity.endpoint).stat()
        control = Path(identity.config_home) / "app-server-control/app-server-control.sock"
        if os.readlink(control) != identity.endpoint or (
            endpoint_stat.st_dev,
            endpoint_stat.st_ino,
        ) != (identity.endpoint_device, identity.endpoint_inode):
            raise EndpointError("endpoint_incarnation_changed")
        if (
            _birth(process) != identity.start_ticks
            or os.readlink(process / "exe") != identity.executable
            or (executable_stat.st_dev, executable_stat.st_ino)
            != (identity.executable_device, identity.executable_inode)
        ):
            raise EndpointError("runtime_incarnation_changed")
    except EndpointError:
        raise
    except OSError:
        raise EndpointError("runtime_incarnation_unavailable") from None
