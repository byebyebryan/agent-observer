#!/usr/bin/env python3
"""One-shot private Snap orchestrator for the installed working-set native check.

This file intentionally has no configurable command-line arguments.  It is
bound to the reviewed private wheel pair, lexical interpreter, Codex home,
window, and host scope.  Importing it performs no host or process operations.
"""

from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import importlib.metadata
import json
import os
import re
import secrets
import select
import signal
import socket
import stat
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

PLAN_ROOT = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/native-installed-b176-snap-plan-v2"
)
ORCHESTRATOR = PLAN_ROOT / "run-native-working-set-snap.py"
INSTALL_ROOT = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0"
)
VENV_ROOT = INSTALL_ROOT / "venv-314"
PYTHON = VENV_ROOT / "bin/python"
OBSERVER_CLI = VENV_ROOT / "bin/agent-observer-service"
MESH_CLI = VENV_ROOT / "bin/mesh-plus"
CODEX_HOME = Path("/home/bryan/.codex")
RUNTIME_ROOT = Path("/run/user/1000")
HOST_SCOPE = "snap"
HOSTNAME = "80H1VV3"
WINDOW_HOURS = 72
OBSERVER_WHEEL_SHA256 = "30a4e30b2fdc1f2bb7c6ee8b6cbf2fe16fdf32fbb7b95932b0d8e5c68eef9e5e"
MESH_WHEEL_SHA256 = "287d98c9d16f492a3df43a391b2036f98760c805480a74a7f93b3fcd2d8cf14a"
PYTHON_SHA256 = "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
QUALIFIER_SHA256 = "bb35429a9923e17d5d9354bca008ba57f489d1fb41c4bbeb9020f241479b20c8"
ORACLE_SHA256 = "0205e8ca00e0b8ba8877c1575aa9b35385412e8b51063f7d43a449709a8056ea"
QUALIFIER = PLAN_ROOT / "qualify-working-set-native"
ORACLE = PLAN_ROOT / "evaluate-observation"

PROGRESS_SCHEMA = "agent-observer.working-set-native-qualification.progress.v1"
RESULT_SCHEMA = "agent-observer.working-set-native-qualification.v1"
REPORT_SCHEMA = "agent-observer.working-set-native-orchestrator.v1"
MAX_LINE_BYTES = 32 * 1024
MAX_STDOUT_BYTES = 64 * 1024
MAX_NATIVE_ROWS = 2048
MAX_WORKER_RECORDS = 64
MAX_PROC_SCAN = 16384
QUALIFIER_DEADLINE_SECONDS = 240
SERVICE_WAIT_SECONDS = 90
RPC_TIMEOUT_SECONDS = 12
ORCHESTRATOR_DEADLINE_SECONDS = 250
CHILD_TERM_GRACE_SECONDS = 10
CHILD_KILL_WAIT_SECONDS = 2
POLL_SECONDS = 0.05
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}$")
_CODE = re.compile(r"^[a-z][a-z0-9_]{0,95}$")
_MAX_SAFE_INTEGER = 2**53 - 1
_MAX_REASON_KEYS = 128
MAX_LEASE_BYTES = 4096

COUNT_KEYS = (
    "nativeBefore",
    "nativeAfter",
    "candidateBodies",
    "candidateMembers",
    "candidateNonmembers",
    "candidateUncertain",
    "expectedMembers",
    "expectedNonmembers",
    "membershipUnresolved",
    "membershipMatches",
    "conditionalMemberships",
    "candidateOmittedExpectedNegative",
    "membershipUnresolvedIdentities",
    "fieldUnresolvedIdentities",
    "mismatchedIdentities",
    "independentlyProvenRecentMemberships",
    "projectedFieldComparedIdentities",
    "projectedFieldUnresolvedIdentities",
    "projectedFieldMismatchedIdentities",
    "projectedFieldUnrequestedNonmemberBodies",
)
BOOLEAN_COUNT_KEYS = ("nativeCensusStable", "nativeComplete")
FIELD_KEYS = (
    "runtime_checked",
    "runtime_match",
    "kind_checked",
    "kind_match",
    "activity_match",
    "activity_no_turn_match",
)


class PlanFailure(Exception):
    """A finite internal failure code, safe for a private bounded receipt."""

    def __init__(self, code: str):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code):
            code = "orchestrator_failed"
        self.code = code
        super().__init__(code)


@dataclasses.dataclass(frozen=True)
class ProcIdentity:
    pid: int
    start_ticks: int
    uid: int
    parent_pid: int
    pgrp: int
    session: int
    argv_sha256: str
    executable_sha256: str | None
    executable_device: int
    executable_inode: int

    def receipt(self) -> dict[str, int | str]:
        return {
            "pid": self.pid,
            "startTicks": self.start_ticks,
            "uid": self.uid,
            "parentPid": self.parent_pid,
            "processGroup": self.pgrp,
            "session": self.session,
            "argvSha256": self.argv_sha256,
            "executableSha256": self.executable_sha256,
            "executableDevice": self.executable_device,
            "executableInode": self.executable_inode,
        }


@dataclasses.dataclass
class ChildHandle:
    name: str
    proc: subprocess.Popen[bytes]
    argv: tuple[str, ...]
    identity: ProcIdentity | None = None
    identity_verified: bool = False
    term_sent: bool = False
    kill_sent: bool = False
    joined: bool = False
    join_code: str = "not_joined"

    def receipt(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "identity": self.identity.receipt() if self.identity else None,
            "identityVerified": self.identity_verified,
            "termSent": self.term_sent,
            "killSent": self.kill_sent,
            "joined": self.joined,
            "joinCode": self.join_code,
        }


@dataclasses.dataclass(frozen=True)
class WorkerIdentity:
    pid: int
    start_ticks: int
    uid: int
    pgrp: int
    session: int
    argv_sha256: str
    executable_sha256: str
    executable_device: int
    executable_inode: int

    def receipt(self) -> dict[str, int | str]:
        return {
            "pid": self.pid,
            "startTicks": self.start_ticks,
            "uid": self.uid,
            "processGroup": self.pgrp,
            "session": self.session,
            "argvSha256": self.argv_sha256,
            "executableSha256": self.executable_sha256,
            "executableDevice": self.executable_device,
            "executableInode": self.executable_inode,
        }


def _stable_file(
    path: Path,
    *,
    limit: int = 512 * 1024 * 1024,
    owner_uid: int = 1000,
    executable: bool | None = None,
) -> tuple[bytes, os.stat_result]:
    try:
        if path.is_symlink():
            raise PlanFailure("artifact_symlink_rejected")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except PlanFailure:
        raise
    except OSError:
        raise PlanFailure("artifact_unavailable") from None
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != owner_uid
            or before.st_mode & 0o022
            or before.st_size <= 0
            or before.st_size > limit
            or executable is True
            and not before.st_mode & 0o111
            or executable is False
            and before.st_mode & 0o111
        ):
            raise PlanFailure("artifact_metadata_rejected")
        chunks = bytearray()
        while len(chunks) <= limit:
            block = os.read(fd, min(1024 * 1024, limit + 1 - len(chunks)))
            if not block:
                break
            chunks.extend(block)
        after = os.fstat(fd)
        named = path.lstat()

        def signature(value):
            return (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        if (
            len(chunks) != before.st_size
            or len(chunks) > limit
            or signature(before) != signature(after)
            or signature(before) != signature(named)
        ):
            raise PlanFailure("artifact_changed")
        return bytes(chunks), after
    finally:
        os.close(fd)


def _sha_file(
    path: Path, *, owner_uid: int = 1000, executable: bool | None = None
) -> tuple[str, os.stat_result]:
    data, info = _stable_file(path, owner_uid=owner_uid, executable=executable)
    return hashlib.sha256(data).hexdigest(), info


def _directory_identity(path: Path, *, uid: int, mode: int) -> tuple[int, int]:
    try:
        info = path.lstat()
    except OSError:
        raise PlanFailure("directory_unavailable") from None
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or info.st_uid != uid
        or stat.S_IMODE(info.st_mode) != mode
    ):
        raise PlanFailure("directory_ownership_rejected")
    return info.st_dev, info.st_ino


def _direct_url_wheel_sha(dist: importlib.metadata.Distribution) -> str:
    try:
        raw = dist.read_text("direct_url.json")
        direct = json.loads(raw) if raw else None
    except Exception:
        raise PlanFailure("installed_distribution_metadata_invalid") from None
    if not isinstance(direct, dict) or "dir_info" in direct or "vcs_info" in direct:
        raise PlanFailure("installed_distribution_not_wheel")
    archive = direct.get("archive_info")
    if not isinstance(archive, dict):
        raise PlanFailure("installed_distribution_digest_missing")
    values: list[str] = []
    legacy = archive.get("hash")
    hashes = archive.get("hashes")
    if legacy is not None:
        if not isinstance(legacy, str) or not legacy.startswith("sha256="):
            raise PlanFailure("installed_distribution_digest_invalid")
        values.append(legacy.removeprefix("sha256="))
    if hashes is not None:
        if not isinstance(hashes, dict) or not isinstance(hashes.get("sha256"), str):
            raise PlanFailure("installed_distribution_digest_invalid")
        values.append(hashes["sha256"])
    if (
        not values
        or any(_SHA256.fullmatch(value) is None for value in values)
        or any(value != values[0] for value in values[1:])
    ):
        raise PlanFailure("installed_distribution_digest_invalid")
    return values[0]


def _distribution(name: str, expected_sha: str) -> tuple[importlib.metadata.Distribution, str]:
    try:
        dist = importlib.metadata.distribution(name)
        location = Path(dist.locate_file("")).resolve(strict=True)
        prefix = VENV_ROOT.resolve(strict=True)
        if prefix not in location.parents:
            raise PlanFailure("installed_distribution_outside_venv")
        digest = _direct_url_wheel_sha(dist)
        if digest != expected_sha:
            raise PlanFailure("installed_distribution_digest_mismatch")
        if not _VERSION.fullmatch(dist.version):
            raise PlanFailure("installed_distribution_version_invalid")
        return dist, dist.version
    except PlanFailure:
        raise
    except Exception:
        raise PlanFailure("installed_distribution_unavailable") from None


def _validate_cli(path: Path, python_path: Path) -> tuple[str, os.stat_result]:
    data, info = _stable_file(path, owner_uid=os.getuid(), executable=True)
    first_line = data.splitlines()[0] if data else b""
    if not first_line.startswith(b"#!"):
        raise PlanFailure("installed_cli_shebang_missing")
    try:
        shebang = first_line[2:].decode("utf-8", "strict").strip()
    except UnicodeDecodeError:
        raise PlanFailure("installed_cli_shebang_invalid") from None
    if shebang != str(python_path):
        raise PlanFailure("installed_cli_interpreter_mismatch")
    if path.parent != python_path.parent:
        raise PlanFailure("installed_cli_location_mismatch")
    return hashlib.sha256(data).hexdigest(), info


def _verify_static_install() -> dict[str, Any]:
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise PlanFailure("uid_mismatch")
    if socket.gethostname().split(".", 1)[0].upper() != HOSTNAME:
        raise PlanFailure("host_mismatch")
    if tuple(sys.version_info[:3]) != (3, 14, 8):
        raise PlanFailure("python_version_mismatch")
    plan_root = Path(__file__).resolve().parent
    if plan_root != PLAN_ROOT or plan_root.is_symlink():
        raise PlanFailure("plan_root_mismatch")
    _directory_identity(plan_root, uid=1000, mode=0o700)
    install_info = _directory_identity(INSTALL_ROOT, uid=1000, mode=0o700)
    del install_info
    try:
        venv_info = VENV_ROOT.lstat()
    except OSError:
        raise PlanFailure("venv_directory_unavailable") from None
    if (
        not stat.S_ISDIR(venv_info.st_mode)
        or stat.S_ISLNK(venv_info.st_mode)
        or venv_info.st_uid != 1000
        or venv_info.st_mode & 0o022
        or VENV_ROOT.resolve(strict=True) != VENV_ROOT
    ):
        raise PlanFailure("venv_directory_rejected")
    if Path(os.path.abspath(__file__)) != ORCHESTRATOR or ORCHESTRATOR.is_symlink():
        raise PlanFailure("orchestrator_path_mismatch")
    if (
        Path(os.path.abspath(sys.prefix)) != VENV_ROOT
        or Path(os.path.abspath(sys.base_prefix)) == VENV_ROOT
    ):
        raise PlanFailure("python_prefix_mismatch")
    try:
        python_image = PYTHON.resolve(strict=True)
    except OSError:
        raise PlanFailure("python_image_unavailable") from None
    python_sha, python_info = _sha_file(
        python_image, owner_uid=python_image.stat().st_uid, executable=True
    )
    if python_sha != PYTHON_SHA256:
        raise PlanFailure("python_digest_mismatch")
    self_exe = Path("/proc/self/exe")
    self_info = self_exe.stat()
    if (self_info.st_dev, self_info.st_ino) != (python_info.st_dev, python_info.st_ino):
        raise PlanFailure("python_running_image_mismatch")
    qualifier_sha, _ = _sha_file(QUALIFIER, owner_uid=1000, executable=False)
    oracle_sha, _ = _sha_file(ORACLE, owner_uid=1000, executable=False)
    if qualifier_sha != QUALIFIER_SHA256 or oracle_sha != ORACLE_SHA256:
        raise PlanFailure("pinned_qualifier_changed")
    observer_dist, observer_version = _distribution("agent-observer", OBSERVER_WHEEL_SHA256)
    mesh_dist, mesh_version = _distribution("mesh-plus", MESH_WHEEL_SHA256)
    observer_cli_sha, observer_cli_info = _validate_cli(OBSERVER_CLI, PYTHON)
    mesh_cli_sha, mesh_cli_info = _validate_cli(MESH_CLI, PYTHON)
    worker_lexical = Path(observer_dist.locate_file("agent_observer/_service_worker.py"))
    if worker_lexical.is_symlink():
        raise PlanFailure("installed_worker_symlink_rejected")
    worker = worker_lexical.resolve(strict=True)
    worker_info = worker.stat()
    if (
        VENV_ROOT.resolve(strict=True) not in worker.parents
        or not stat.S_ISREG(worker_info.st_mode)
        or worker_info.st_uid != 1000
        or worker_info.st_mode & 0o022
    ):
        raise PlanFailure("installed_worker_path_rejected")
    return {
        "pythonSha256": python_sha,
        "pythonDevice": python_info.st_dev,
        "pythonInode": python_info.st_ino,
        "observerWheelSha256": OBSERVER_WHEEL_SHA256,
        "observerVersion": observer_version,
        "meshWheelSha256": MESH_WHEEL_SHA256,
        "meshVersion": mesh_version,
        "observerCliSha256": observer_cli_sha,
        "observerCliDevice": observer_cli_info.st_dev,
        "observerCliInode": observer_cli_info.st_ino,
        "meshCliSha256": mesh_cli_sha,
        "meshCliDevice": mesh_cli_info.st_dev,
        "meshCliInode": mesh_cli_info.st_ino,
        "workerPath": worker,
    }


def _codex_endpoint_preflight() -> tuple[Path, os.stat_result]:
    try:
        home_info = CODEX_HOME.lstat()
        if (
            not stat.S_ISDIR(home_info.st_mode)
            or stat.S_ISLNK(home_info.st_mode)
            or home_info.st_uid != os.getuid()
            or home_info.st_mode & 0o022
        ):
            raise PlanFailure("codex_home_rejected")
        control_dir = CODEX_HOME / "app-server-control"
        control_dir_info = control_dir.lstat()
        if (
            not stat.S_ISDIR(control_dir_info.st_mode)
            or stat.S_ISLNK(control_dir_info.st_mode)
            or control_dir_info.st_uid != os.getuid()
            or control_dir_info.st_mode & 0o022
        ):
            raise PlanFailure("native_control_directory_rejected")
        control = CODEX_HOME / "app-server-control/app-server-control.sock"
        control_info = control.lstat()
        if not stat.S_ISLNK(control_info.st_mode) or control_info.st_uid != os.getuid():
            raise PlanFailure("native_control_link_rejected")
        target = Path(os.readlink(control))
        expected = (
            Path(f"/tmp/codex-daemon-{os.getuid()}")
            / hashlib.sha256(str(control).encode()).hexdigest()
        )
        if target != expected or not target.is_absolute():
            raise PlanFailure("native_endpoint_namespace_mismatch")
        endpoint_info = target.lstat()
        if (
            not stat.S_ISSOCK(endpoint_info.st_mode)
            or endpoint_info.st_uid != os.getuid()
            or stat.S_IMODE(endpoint_info.st_mode) != 0o600
        ):
            raise PlanFailure("native_endpoint_ownership_rejected")
        return target, endpoint_info
    except PlanFailure:
        raise
    except OSError:
        raise PlanFailure("native_endpoint_unavailable") from None


def _make_runtime_dir() -> tuple[Path, Path, tuple[int, int]]:
    _directory_identity(RUNTIME_ROOT, uid=1000, mode=0o700)
    token = secrets.token_hex(8)
    runtime_dir = RUNTIME_ROOT / f"working-set-native-{os.getpid()}-{token}"
    try:
        os.mkdir(runtime_dir, 0o700)
    except FileExistsError:
        raise PlanFailure("private_runtime_collision") from None
    except OSError:
        raise PlanFailure("private_runtime_create_failed") from None
    identity = _directory_identity(runtime_dir, uid=1000, mode=0o700)
    try:
        socket_path = runtime_dir / "read.sock"
        if len(os.fsencode(socket_path)) >= 108:
            raise PlanFailure("private_socket_path_too_long")
        try:
            socket_path.lstat()
        except FileNotFoundError:
            pass
        except OSError:
            raise PlanFailure("private_socket_preflight_failed") from None
        else:
            raise PlanFailure("private_socket_preexisting")
        return runtime_dir, socket_path, identity
    except Exception:
        try:
            if _directory_identity(runtime_dir, uid=1000, mode=0o700) == identity:
                runtime_dir.rmdir()
        except Exception:
            pass
        raise


def _proc_stat(pid: int, proc_root: Path = Path("/proc")) -> tuple[int, int, int, int]:
    try:
        raw = (proc_root / str(pid) / "stat").read_text(encoding="ascii")
        left = raw.index("(")
        right = raw.rindex(")")
        stat_pid = int(raw[:left].strip())
        rest = raw[right + 1 :].split()
        if stat_pid != pid or len(rest) < 20:
            raise ValueError
        # rest[0] is field 3; starttime is field 22 (index 19).
        return int(rest[19]), int(rest[1]), int(rest[2]), int(rest[3])
    except (OSError, ValueError, IndexError):
        raise PlanFailure("process_identity_unavailable") from None


def _proc_uid(pid: int, proc_root: Path = Path("/proc")) -> int:
    try:
        for line in (proc_root / str(pid) / "status").read_text(encoding="ascii").splitlines():
            if line.startswith("Uid:"):
                values = line.split()[1:]
                if len(values) >= 2 and values[0] == values[1]:
                    return int(values[0])
    except (OSError, ValueError, IndexError):
        pass
    raise PlanFailure("process_owner_unavailable")


def _proc_argv(pid: int, proc_root: Path = Path("/proc")) -> tuple[list[str], bytes]:
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except OSError:
        raise PlanFailure("process_argv_unavailable") from None
    if not raw or len(raw) > 64 * 1024 or not raw.endswith(b"\0"):
        raise PlanFailure("process_argv_invalid")
    try:
        argv = [os.fsdecode(value) for value in raw[:-1].split(b"\0")]
    except UnicodeError:
        raise PlanFailure("process_argv_invalid") from None
    return argv, raw


def _proc_executable(
    pid: int, *, hash_executable: bool = True, proc_root: Path = Path("/proc")
) -> tuple[str, str | None, os.stat_result]:
    path = proc_root / str(pid) / "exe"
    fd = -1
    try:
        target = os.readlink(path)
        if target.endswith(" (deleted)"):
            raise PlanFailure("process_executable_deleted")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid not in {0, os.getuid()}
            or not info.st_mode & 0o111
            or not 0 < info.st_size <= 512 * 1024 * 1024
        ):
            raise PlanFailure("process_executable_rejected")
        digest = hashlib.sha256()
        if hash_executable:
            while True:
                block = os.read(fd, 1024 * 1024)
                if not block:
                    break
                digest.update(block)
        after = os.fstat(fd)
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise PlanFailure("process_executable_changed")
        return target, digest.hexdigest() if hash_executable else None, after
    except PlanFailure:
        raise
    except OSError:
        raise PlanFailure("process_executable_unavailable") from None
    finally:
        if fd >= 0:
            os.close(fd)


def _observe_process(
    pid: int, *, hash_executable: bool = True, proc_root: Path = Path("/proc")
) -> tuple[ProcIdentity, list[str]]:
    start, ppid, pgrp, session = _proc_stat(pid, proc_root)
    uid = _proc_uid(pid, proc_root)
    argv, raw = _proc_argv(pid, proc_root)
    _target, executable_sha, executable_info = _proc_executable(
        pid, hash_executable=hash_executable, proc_root=proc_root
    )
    return ProcIdentity(
        pid=pid,
        start_ticks=start,
        uid=uid,
        parent_pid=ppid,
        pgrp=pgrp,
        session=session,
        argv_sha256=hashlib.sha256(raw).hexdigest(),
        executable_sha256=executable_sha,
        executable_device=executable_info.st_dev,
        executable_inode=executable_info.st_ino,
    ), argv


def _validate_process(
    pid: int,
    expected_argv: tuple[str, ...],
    *,
    expected_exe_sha: str,
    expected_uid: int,
    expected_birth: int | None = None,
    expected_device_inode: tuple[int, int] | None = None,
    expected_parent: int | None = None,
    hash_executable: bool = True,
    proc_root: Path = Path("/proc"),
) -> ProcIdentity:
    identity, argv = _observe_process(pid, hash_executable=hash_executable, proc_root=proc_root)
    if (
        identity.uid != expected_uid
        or tuple(argv) != expected_argv
        or hash_executable
        and identity.executable_sha256 != expected_exe_sha
        or identity.pgrp != pid
        or identity.session != pid
        or expected_birth is not None
        and identity.start_ticks != expected_birth
        or expected_parent is not None
        and identity.parent_pid != expected_parent
        or expected_device_inode is not None
        and (identity.executable_device, identity.executable_inode) != expected_device_inode
    ):
        raise PlanFailure("process_identity_mismatch")
    return identity


def _is_canonical_worker(
    identity: ProcIdentity,
    argv: list[str],
    *,
    candidate_pid: int,
    python_sha: str,
    python_device_inode: tuple[int, int],
    worker_path: Path,
) -> bool:
    return (
        identity.parent_pid == candidate_pid
        and identity.uid == 1000
        and tuple(argv) == (str(PYTHON), "-I", "-B", str(worker_path))
        and (identity.executable_device, identity.executable_inode) == python_device_inode
        and identity.pgrp == identity.pid
        and identity.session == identity.pid
        and python_sha == PYTHON_SHA256
    )


def _candidate_listener_inode(
    socket_path: Path, pid: int, proc_root: Path = Path("/proc")
) -> int | None:
    """Return a unique listener inode only when the exact PID owns its fd."""
    try:
        raw = (proc_root / "net/unix").read_text(encoding="ascii")
    except OSError:
        return None
    if len(raw) > 1024 * 1024:
        return None
    listeners = set()
    for line in raw.splitlines()[1:]:
        fields = line.split(maxsplit=7)
        if len(fields) != 8 or fields[7] != str(socket_path):
            continue
        try:
            if int(fields[3], 16) & 0x10000 and int(fields[4], 16) == 1:
                listeners.add(int(fields[6]))
        except ValueError:
            return None
    if len(listeners) != 1:
        return None
    listener_inode = next(iter(listeners))
    try:
        with os.scandir(proc_root / str(pid) / "fd") as entries:
            for index, entry in enumerate(entries):
                if index >= 4096:
                    return None
                try:
                    if os.readlink(entry.path) == f"socket:[{listener_inode}]":
                        return listener_inode
                except FileNotFoundError:
                    continue
    except OSError:
        return None
    return None


def _lease_record_bytes(record: dict[str, int]) -> bytes:
    return json.dumps(
        record, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("ascii")


def _lease_stat_signature(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_uid,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _parse_lease_record(raw: bytes) -> dict[str, int]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_LEASE_BYTES:
        raise PlanFailure("candidate_lease_record_size_invalid")
    try:
        value = json.loads(raw.decode("ascii", "strict"))
    except (UnicodeError, json.JSONDecodeError):
        raise PlanFailure("candidate_lease_record_invalid") from None
    expected_keys = {"pid", "birth", "device", "inode"}
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise PlanFailure("candidate_lease_record_shape_invalid")
    if any(type(value[key]) is not int for key in expected_keys):
        raise PlanFailure("candidate_lease_record_type_invalid")
    if (
        value["pid"] < 1
        or value["birth"] < 1
        or value["device"] < 0
        or value["inode"] < 1
        or any(value[key] > _MAX_SAFE_INTEGER for key in expected_keys)
        or _lease_record_bytes(value) != raw
    ):
        raise PlanFailure("candidate_lease_record_noncanonical")
    return value


def _guarded_signal(
    handle: ChildHandle,
    signum: int,
    signaler,
    *,
    expected_exe_sha: str,
    expected_uid: int,
    expected_device_inode: tuple[int, int],
    expected_parent: int,
    proc_root: Path = Path("/proc"),
) -> None:
    if not handle.identity_verified or handle.identity is None:
        raise PlanFailure("process_identity_unverified_no_signal")
    _validate_process(
        handle.proc.pid,
        handle.argv,
        expected_exe_sha=expected_exe_sha,
        expected_uid=expected_uid,
        expected_birth=handle.identity.start_ticks,
        expected_device_inode=expected_device_inode,
        expected_parent=expected_parent,
        hash_executable=False,
        proc_root=proc_root,
    )
    signaler(handle.proc.pid, signum)


def _argv_hash(argv: tuple[str, ...]) -> str:
    raw = b"".join(os.fsencode(value) + b"\0" for value in argv)
    return hashlib.sha256(raw).hexdigest()


def _progress(line: bytes, socket_path: Path) -> dict[str, Any]:
    if len(line) > MAX_LINE_BYTES:
        raise PlanFailure("qualifier_progress_limit")
    try:
        value = json.loads(line)
    except (UnicodeError, json.JSONDecodeError):
        raise PlanFailure("qualifier_progress_invalid") from None
    expected_keys = {
        "schema",
        "event",
        "nativeRows",
        "nativeVersion",
        "nativeExecutableSha256",
        "candidateServiceSocket",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise PlanFailure("qualifier_progress_shape_invalid")
    version = value.get("nativeVersion")
    rows = value.get("nativeRows")
    if (
        value.get("schema") != PROGRESS_SCHEMA
        or value.get("event") != "native_before_complete"
        or type(rows) is not int
        or not 0 <= rows <= MAX_NATIVE_ROWS
        or not isinstance(version, str)
        or not _VERSION.fullmatch(version)
        or not isinstance(value.get("nativeExecutableSha256"), str)
        or not _SHA256.fullmatch(value["nativeExecutableSha256"])
        or value.get("candidateServiceSocket") != str(socket_path)
    ):
        raise PlanFailure("native_before_marker_invalid")
    return {
        "rows": rows,
        "versionSha256": hashlib.sha256(version.encode()).hexdigest(),
        "executableSha256": value["nativeExecutableSha256"],
    }


def _project_code_counts(value: Any, *, error_code: str) -> dict[str, int]:
    if not isinstance(value, dict) or len(value) > _MAX_REASON_KEYS:
        raise PlanFailure(error_code)
    projected: dict[str, int] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not _CODE.fullmatch(key)
            or type(item) is not int
            or not 0 <= item <= MAX_NATIVE_ROWS * 4
        ):
            raise PlanFailure(error_code)
        projected[key] = item
    return projected


def _project_clock_prefix(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanFailure("qualifier_clock_prefix_invalid")
    result = {}
    for key in ("status", "reason"):
        item = value.get(key)
        if type(item) is not str or not _CODE.fullmatch(item):
            raise PlanFailure("qualifier_clock_prefix_invalid")
        if key == "status" and item not in {"recomputed", "unproved"}:
            raise PlanFailure("qualifier_clock_prefix_invalid")
        result[key] = item
    for key, maximum in (("frames", 16), ("acceptedTransitions", 32)):
        item = value.get(key)
        if type(item) is not int or not 0 <= item <= maximum:
            raise PlanFailure("qualifier_clock_prefix_invalid")
        result[key] = item
    for key in ("baselineCounters", "finalCounters"):
        item = value.get(key)
        if item is not None and (
            not isinstance(item, dict)
            or set(item) != {"runtime", "history"}
            or any(type(count) is not int or not 0 <= count <= _MAX_SAFE_INTEGER
                   for count in item.values())
        ):
            raise PlanFailure("qualifier_clock_prefix_invalid")
        result[key] = item
    ceiling = value.get("recomputedCeiling")
    if ceiling is not None and (type(ceiling) is not int or abs(ceiling) > _MAX_SAFE_INTEGER):
        raise PlanFailure("qualifier_clock_prefix_invalid")
    result["recomputedCeiling"] = ceiling
    fingerprint = value.get("finalMetadataFingerprint")
    if fingerprint is not None and (type(fingerprint) is not str or not _SHA256.fullmatch(fingerprint)):
        raise PlanFailure("qualifier_clock_prefix_invalid")
    result["finalMetadataFingerprint"] = fingerprint
    return result


def _project_result(line: bytes, marker: dict[str, Any] | None) -> dict[str, Any]:
    if len(line) > MAX_LINE_BYTES:
        raise PlanFailure("qualifier_result_limit")
    try:
        value = json.loads(line)
    except (UnicodeError, json.JSONDecodeError):
        raise PlanFailure("qualifier_result_invalid") from None
    if not isinstance(value, dict) or value.get("schema") != RESULT_SCHEMA:
        raise PlanFailure("qualifier_result_shape_invalid")
    status = value.get("status")
    exit_code = value.get("exitCode")
    expected_exit = {"match": 0, "mismatch": 2, "unresolved": 3, "unsupported": 3}
    if status in expected_exit:
        if type(exit_code) is not int or expected_exit[status] != exit_code:
            raise PlanFailure("qualifier_status_exit_mismatch")
    elif status in {"error", "failed"}:
        if type(exit_code) is not int or exit_code != 4:
            raise PlanFailure("qualifier_status_exit_mismatch")
    else:
        raise PlanFailure("qualifier_status_invalid")

    result: dict[str, Any] = {"status": status, "exitCode": exit_code}
    reason_code = value.get("reasonCode")
    if "reasonCode" in value:
        if not isinstance(reason_code, str) or not _CODE.fullmatch(reason_code):
            raise PlanFailure("qualifier_reason_code_invalid")
        result["reasonCode"] = reason_code
    for key in ("reasonCounts", "mismatchCounts"):
        if key in value:
            result[key] = _project_code_counts(value[key], error_code=f"qualifier_{key}_invalid")
    counts = value.get("counts")
    if counts is not None:
        if not isinstance(counts, dict):
            raise PlanFailure("qualifier_counts_invalid")
        projected_counts: dict[str, int | bool] = {}
        for key in COUNT_KEYS:
            if key not in counts:
                continue
            item = counts[key]
            if type(item) is not int or not 0 <= item <= MAX_NATIVE_ROWS * 4:
                raise PlanFailure("qualifier_count_out_of_range")
            projected_counts[key] = item
        for key in BOOLEAN_COUNT_KEYS:
            if key not in counts:
                continue
            if type(counts[key]) is not bool:
                raise PlanFailure("qualifier_boolean_count_invalid")
            projected_counts[key] = counts[key]
        if (
            marker is not None
            and "nativeBefore" in projected_counts
            and projected_counts["nativeBefore"] != marker["rows"]
        ):
            raise PlanFailure("native_before_count_mismatch")
        result["counts"] = projected_counts

    fields = value.get("fieldCounts")
    if fields is not None:
        if not isinstance(fields, dict):
            raise PlanFailure("qualifier_field_counts_invalid")
        projected_fields = {}
        for key in FIELD_KEYS:
            if key not in fields:
                continue
            item = fields[key]
            if type(item) is not int or not 0 <= item <= MAX_NATIVE_ROWS * 4:
                raise PlanFailure("qualifier_field_count_out_of_range")
            projected_fields[key] = item
        result["fieldCounts"] = projected_fields

    membership = value.get("membershipStatus")
    field_status = value.get("fieldStatus")
    if membership is not None:
        if membership not in {"match", "mismatch", "unresolved"}:
            raise PlanFailure("qualifier_membership_status_invalid")
        result["membershipStatus"] = membership
    if field_status is not None:
        if field_status not in {"match", "mismatch", "unresolved"}:
            raise PlanFailure("qualifier_field_status_invalid")
        result["fieldStatus"] = field_status
    for key in ("projectedFieldStatus", "projectionStatus"):
        if key in value:
            item = value[key]
            if type(item) is not str or item not in {"match", "mismatch", "unresolved"}:
                raise PlanFailure("qualifier_projection_status_invalid")
            result[key] = item
    conditional = value.get("conditionalMembershipStatus")
    if conditional is not None:
        if conditional not in {"none", "producer_clock_ceiling_dependent"}:
            raise PlanFailure("qualifier_conditional_status_invalid")
        result["conditionalMembershipStatus"] = conditional
    source_k = value.get("sourceK")
    if source_k is not None:
        if not isinstance(source_k, dict):
            raise PlanFailure("qualifier_clock_status_invalid")
        safe_source_k = {}
        for key in (
            "status",
            "firstAcceptanceSet",
            "clockBracketAndComponentSampleJoins",
            "currentComponentClockCensus",
        ):
            item = source_k.get(key)
            if item is not None:
                allowed = {
                    "status": {
                        "producer_asserted_not_independently_proven",
                        "independently_recomputed_first_acceptance_set",
                        "independently_recomputed_observed_clock_prefix",
                    },
                    "firstAcceptanceSet": {"recomputed", "unproved", "not_used"},
                    "clockBracketAndComponentSampleJoins": {"checked", "unresolved"},
                    "currentComponentClockCensus": {"complete", "incomplete"},
                }[key]
                if item not in allowed:
                    raise PlanFailure("qualifier_clock_status_invalid")
                safe_source_k[key] = item
        for key in (
            "candidateCeiling",
            "independentCurrentClockLowerBound",
            "recomputedFirstAcceptanceCeiling",
            "recomputedObservedClockPrefixCeiling",
        ):
            if key not in source_k:
                continue
            item = source_k[key]
            if item is not None and (type(item) is not int or abs(item) > _MAX_SAFE_INTEGER):
                raise PlanFailure("qualifier_clock_value_invalid")
            safe_source_k[key] = item
        first_reason = source_k.get("firstAcceptanceReason")
        if "firstAcceptanceReason" in source_k:
            if not isinstance(first_reason, str) or not _CODE.fullmatch(first_reason):
                raise PlanFailure("qualifier_clock_reason_invalid")
            safe_source_k["firstAcceptanceReason"] = first_reason
        if "observedClockPrefix" in source_k:
            safe_source_k["observedClockPrefix"] = _project_clock_prefix(source_k["observedClockPrefix"])
        result["sourceK"] = safe_source_k
    digests = value.get("identityDigests")
    if digests is not None:
        if (
            not isinstance(digests, list)
            or len(digests) > 512
            or any(not isinstance(item, str) or not _HEX32.fullmatch(item) for item in digests)
        ):
            raise PlanFailure("qualifier_identity_digest_invalid")
        result["identityDigests"] = digests
    return result


def _candidate_argv(socket_path: Path) -> tuple[str, ...]:
    return (
        str(PYTHON),
        str(OBSERVER_CLI),
        "serve",
        "--host-scope",
        HOST_SCOPE,
        "--socket",
        str(socket_path),
        "--provider",
        "codex",
        "--codex-home",
        str(CODEX_HOME),
        "--working-set-window-hours",
        str(WINDOW_HOURS),
    )


def _qualifier_argv(socket_path: Path, endpoint: Path, install: dict[str, Any]) -> tuple[str, ...]:
    observer_dist, observer_version = _distribution("agent-observer", OBSERVER_WHEEL_SHA256)
    mesh_dist, mesh_version = _distribution("mesh-plus", MESH_WHEEL_SHA256)
    del observer_dist, mesh_dist
    return (
        str(PYTHON),
        str(QUALIFIER),
        "--codex-home",
        str(CODEX_HOME),
        "--native-endpoint",
        str(endpoint),
        "--host-scope",
        HOST_SCOPE,
        "--window-hours",
        str(WINDOW_HOURS),
        "--service-socket",
        str(socket_path),
        "--candidate-python",
        str(PYTHON),
        "--candidate-python-sha256",
        install["pythonSha256"],
        "--observer-service-cli",
        str(OBSERVER_CLI),
        "--observer-service-cli-sha256",
        install["observerCliSha256"],
        "--mesh-cli",
        str(MESH_CLI),
        "--mesh-cli-sha256",
        install["meshCliSha256"],
        "--observer-wheel-sha256",
        OBSERVER_WHEEL_SHA256,
        "--mesh-wheel-sha256",
        MESH_WHEEL_SHA256,
        "--observer-version",
        observer_version,
        "--mesh-version",
        mesh_version,
        "--deadline-seconds",
        str(QUALIFIER_DEADLINE_SECONDS),
        "--service-wait-seconds",
        str(SERVICE_WAIT_SECONDS),
        "--rpc-timeout-seconds",
        str(RPC_TIMEOUT_SECONDS),
        "--max-native-rows",
        str(MAX_NATIVE_ROWS),
    )


def _child_environment() -> dict[str, str]:
    return {
        "HOME": "/home/bryan",
        "PATH": "/usr/bin:/bin",
        "XDG_RUNTIME_DIR": str(RUNTIME_ROOT),
        "LANG": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


class RealIO:
    """Actual process/file adapter; creation is only from main after preflight."""

    def __init__(
        self,
        *,
        endpoint: Path,
        runtime_dir: Path,
        socket_path: Path,
        runtime_identity: tuple[int, int],
        install: dict[str, Any],
        cancel_check,
    ):
        self.endpoint = endpoint
        self.runtime_dir = runtime_dir
        self.socket_path = socket_path
        self.runtime_identity = runtime_identity
        self.install = install
        self.cancel_check = cancel_check
        self.qualifier: ChildHandle | None = None
        self.candidate: ChildHandle | None = None
        self.qualifier_buffer = bytearray()
        self.qualifier_stdout_total = 0
        self.events: deque[tuple[str, Any]] = deque()
        self.qualifier_eof = False
        self.qualifier_exit_reported = False
        self.candidate_exit_reported = False
        self.workers: dict[tuple[int, int], WorkerIdentity] = {}
        self.unexpected_worker_count = 0
        self.socket_identity: tuple[int, int] | None = None
        self.socket_mode: int | None = None
        self.socket_listener_inode: int | None = None
        self.socket_seen_bad = False
        self.lease_path = socket_path.with_name(socket_path.name + ".lock")
        self.lease_fd: int | None = None
        self.lease_identity: tuple[int, int] | None = None
        self.lease_record: dict[str, int] | None = None
        self.lease_record_verified = False
        self.lease_seen_bad = False
        self.lease_removed = False
        self.lease_cleanup_code = "not_observed"
        self._cleanup_removal_allowed = False
        self.worker_scan_code: str | None = None
        self.cleanup_receipt: dict[str, Any] = {}
        self._expected_worker = install["workerPath"]
        python_info = Path("/proc/self/exe").stat()
        self._python_devino = (python_info.st_dev, python_info.st_ino)
        self._python_sha = install["pythonSha256"]

    def start_qualifier(self) -> ChildHandle:
        argv = _qualifier_argv(self.socket_path, self.endpoint, self.install)
        handle = ChildHandle(
            "qualifier",
            subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=str(CODEX_HOME),
                env=_child_environment(),
                close_fds=True,
                start_new_session=True,
                bufsize=0,
            ),
            argv,
        )
        self.qualifier = handle
        self._verify_new_child(handle)
        if handle.proc.stdout is None:
            raise PlanFailure("qualifier_pipe_unavailable")
        os.set_blocking(handle.proc.stdout.fileno(), False)
        return handle

    def start_candidate(self) -> ChildHandle:
        argv = _candidate_argv(self.socket_path)
        handle = ChildHandle(
            "candidate",
            subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(CODEX_HOME),
                env=_child_environment(),
                close_fds=True,
                start_new_session=True,
            ),
            argv,
        )
        self.candidate = handle
        self._verify_new_child(handle)
        self._observe_candidate_socket()
        return handle

    def _verify_new_child(self, handle: ChildHandle) -> None:
        try:
            identity = _validate_process(
                handle.proc.pid,
                handle.argv,
                expected_exe_sha=self._python_sha,
                expected_uid=1000,
                expected_device_inode=self._python_devino,
                expected_parent=os.getpid(),
            )
        except PlanFailure:
            handle.join_code = "identity_unverified"
            raise PlanFailure(f"{handle.name}_process_identity_unverified") from None
        handle.identity = identity
        handle.identity_verified = True

    def _verify_live_child(self, handle: ChildHandle) -> None:
        if handle.proc.poll() is not None:
            return
        if not handle.identity_verified or handle.identity is None:
            raise PlanFailure(f"{handle.name}_process_identity_unverified")
        _validate_process(
            handle.proc.pid,
            handle.argv,
            expected_exe_sha=self._python_sha,
            expected_uid=1000,
            expected_birth=handle.identity.start_ticks,
            expected_device_inode=self._python_devino,
            expected_parent=os.getpid(),
            hash_executable=False,
        )

    def _read_qualifier(self) -> None:
        handle = self.qualifier
        if handle is None or handle.proc.stdout is None or self.qualifier_eof:
            return
        try:
            data = os.read(handle.proc.stdout.fileno(), 65536)
        except BlockingIOError:
            return
        except OSError:
            raise PlanFailure("qualifier_pipe_read_failed") from None
        if not data:
            self.qualifier_eof = True
            if self.qualifier_buffer:
                raise PlanFailure("qualifier_line_unterminated")
            return
        self.qualifier_stdout_total += len(data)
        if self.qualifier_stdout_total > MAX_STDOUT_BYTES:
            raise PlanFailure("qualifier_stdout_limit")
        self.qualifier_buffer.extend(data)
        if len(self.qualifier_buffer) > MAX_LINE_BYTES and b"\n" not in self.qualifier_buffer:
            raise PlanFailure("qualifier_line_limit")
        while b"\n" in self.qualifier_buffer:
            line, _, remaining = self.qualifier_buffer.partition(b"\n")
            self.qualifier_buffer = bytearray(remaining)
            if len(line) > MAX_LINE_BYTES:
                raise PlanFailure("qualifier_line_limit")
            self.events.append(("qualifier_line", bytes(line)))

    def _children(self, pid: int) -> list[int]:
        path = Path(f"/proc/{pid}/task/{pid}/children")
        try:
            raw = path.read_text(encoding="ascii")
        except OSError:
            if not Path(f"/proc/{pid}").exists():
                return []
            raise PlanFailure("candidate_child_list_unavailable") from None
        if len(raw) > 4096:
            raise PlanFailure("candidate_child_list_limit")
        try:
            values = [int(part) for part in raw.split()]
        except ValueError:
            raise PlanFailure("candidate_child_list_invalid") from None
        if len(values) > MAX_WORKER_RECORDS:
            raise PlanFailure("candidate_child_count_limit")
        return values

    def _capture_workers(self) -> None:
        handle = self.candidate
        if handle is None or handle.proc.poll() is not None:
            return
        self._verify_live_child(handle)
        for pid in self._children(handle.proc.pid):
            try:
                identity, argv = _observe_process(pid, hash_executable=False)
            except PlanFailure as exc:
                # A child that exits between the kernel children snapshot and
                # procfs read has no live group left for cleanup.
                if not Path(f"/proc/{pid}").exists():
                    continue
                self.worker_scan_code = exc.code
                raise PlanFailure("candidate_worker_identity_unavailable") from None
            if not _is_canonical_worker(
                identity,
                argv,
                candidate_pid=handle.proc.pid,
                python_sha=self._python_sha,
                python_device_inode=self._python_devino,
                worker_path=self._expected_worker,
            ):
                self.unexpected_worker_count += 1
                self.worker_scan_code = "candidate_child_not_canonical_worker"
                raise PlanFailure("candidate_child_not_canonical_worker")
            key = (pid, identity.start_ticks)
            if key not in self.workers:
                if len(self.workers) >= MAX_WORKER_RECORDS:
                    raise PlanFailure("candidate_worker_record_limit")
                self.workers[key] = WorkerIdentity(
                    pid,
                    identity.start_ticks,
                    identity.uid,
                    identity.pgrp,
                    identity.session,
                    identity.argv_sha256,
                    self._python_sha,
                    identity.executable_device,
                    identity.executable_inode,
                )

    def _observe_candidate_socket(self) -> None:
        try:
            info = self.socket_path.lstat()
        except FileNotFoundError:
            return
        except OSError:
            self.socket_seen_bad = True
            raise PlanFailure("candidate_socket_stat_failed") from None
        if (
            not stat.S_ISSOCK(info.st_mode)
            or info.st_uid != 1000
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            self.socket_seen_bad = True
            raise PlanFailure("candidate_socket_ownership_rejected")
        current = (info.st_dev, info.st_ino)
        if self.socket_identity is not None and self.socket_identity != current:
            self.socket_seen_bad = True
            raise PlanFailure("candidate_socket_incarnation_changed")
        self.socket_identity = current
        self.socket_mode = stat.S_IMODE(info.st_mode)
        if self.candidate is not None and self.candidate.identity_verified:
            try:
                self._verify_live_child(self.candidate)
                listener_inode = _candidate_listener_inode(
                    self.socket_path, self.candidate.proc.pid
                )
            except PlanFailure:
                listener_inode = None
            if listener_inode is not None:
                if (
                    self.socket_listener_inode is not None
                    and self.socket_listener_inode != listener_inode
                ):
                    self.socket_seen_bad = True
                    raise PlanFailure("candidate_listener_incarnation_changed")
                self.socket_listener_inode = listener_inode
                self._capture_private_lease()

    def _capture_private_lease(self) -> None:
        handle = self.candidate
        if (
            handle is None
            or not handle.identity_verified
            or handle.identity is None
            or self.socket_identity is None
            or self.socket_listener_inode is None
            or self.socket_seen_bad
            or self.lease_seen_bad
        ):
            self.lease_seen_bad = True
            raise PlanFailure("candidate_lease_capture_unproved")
        opened_here = False
        fd = self.lease_fd
        try:
            self._verify_live_child(handle)
            try:
                socket_info = self.socket_path.lstat()
            except OSError:
                raise PlanFailure("candidate_socket_unavailable_during_lease_capture") from None
            if (
                not stat.S_ISSOCK(socket_info.st_mode)
                or socket_info.st_uid != 1000
                or stat.S_IMODE(socket_info.st_mode) != 0o600
                or (socket_info.st_dev, socket_info.st_ino) != self.socket_identity
            ):
                raise PlanFailure("candidate_socket_changed_during_lease_capture")
            try:
                path_info = self.lease_path.lstat()
            except OSError:
                raise PlanFailure("candidate_lease_unavailable") from None
            if (
                not stat.S_ISREG(path_info.st_mode)
                or stat.S_ISLNK(path_info.st_mode)
                or path_info.st_uid != 1000
                or stat.S_IMODE(path_info.st_mode) != 0o600
                or path_info.st_nlink != 1
                or path_info.st_size < 1
                or path_info.st_size > MAX_LEASE_BYTES
            ):
                raise PlanFailure("candidate_lease_ownership_rejected")
            if fd is None:
                try:
                    fd = os.open(
                        self.lease_path,
                        os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                    )
                except OSError:
                    raise PlanFailure("candidate_lease_open_failed") from None
                opened_here = True
            before = os.fstat(fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != 1000
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_nlink != 1
                or (before.st_dev, before.st_ino)
                != (path_info.st_dev, path_info.st_ino)
                or before.st_size < 1
                or before.st_size > MAX_LEASE_BYTES
            ):
                raise PlanFailure("candidate_lease_identity_changed")
            raw = os.pread(fd, MAX_LEASE_BYTES + 1, 0)
            after = os.fstat(fd)
            if (
                len(raw) != before.st_size
                or _lease_stat_signature(before) != _lease_stat_signature(after)
                or (after.st_dev, after.st_ino) != (path_info.st_dev, path_info.st_ino)
            ):
                raise PlanFailure("candidate_lease_changed_during_read")
            record = _parse_lease_record(raw)
            expected_record = {
                "pid": handle.identity.pid,
                "birth": handle.identity.start_ticks,
                "device": self.socket_identity[0],
                "inode": self.socket_identity[1],
            }
            if record != expected_record:
                raise PlanFailure("candidate_lease_record_mismatch")
            lease_identity = (before.st_dev, before.st_ino)
            if (
                self.lease_identity is not None
                and self.lease_identity != lease_identity
                or self.lease_record is not None
                and self.lease_record != record
            ):
                raise PlanFailure("candidate_lease_incarnation_changed")
            if self.lease_fd is None:
                self.lease_fd = fd
                opened_here = False
            self.lease_identity = lease_identity
            self.lease_record = record
            self.lease_record_verified = True
            self.lease_cleanup_code = "captured_exact_owner_record"
        except PlanFailure:
            self.lease_seen_bad = True
            raise
        except OSError:
            self.lease_seen_bad = True
            raise PlanFailure("candidate_lease_io_failed") from None
        finally:
            if opened_here and fd is not None:
                os.close(fd)

    def next_event(self, timeout: float) -> tuple[str, Any] | None:
        if self.cancel_check():
            return "cancel", None
        if self.events:
            return self.events.popleft()
        if self.qualifier is not None and self.qualifier.proc.poll() is None:
            self._verify_live_child(self.qualifier)
        if self.candidate is not None and self.candidate.proc.poll() is None:
            self._capture_workers()
            self._observe_candidate_socket()
        if self.qualifier is not None and not self.qualifier_eof:
            stdout = self.qualifier.proc.stdout
            if stdout is not None:
                ready, _, _ = select.select([stdout], [], [], max(0.0, min(timeout, POLL_SECONDS)))
                if ready:
                    self._read_qualifier()
                    if self.events:
                        return self.events.popleft()
        else:
            time.sleep(max(0.0, min(timeout, POLL_SECONDS)))
        if self.cancel_check():
            return "cancel", None
        if (
            self.candidate is not None
            and self.candidate.proc.poll() is not None
            and not self.candidate_exit_reported
        ):
            self.candidate_exit_reported = True
            return "candidate_exit", self.candidate.proc.returncode
        if (
            self.qualifier is not None
            and self.qualifier.proc.poll() is not None
            and not self.qualifier_exit_reported
        ):
            if not self.qualifier_eof:
                self._read_qualifier()
                if self.events:
                    return self.events.popleft()
            self.qualifier_exit_reported = True
            return "qualifier_exit", self.qualifier.proc.returncode
        return None

    def _stop_handle(self, handle: ChildHandle | None) -> None:
        if handle is None:
            return
        proc = handle.proc
        if proc.poll() is not None:
            handle.joined = True
            handle.join_code = "already_exited"
            return
        if not handle.identity_verified or handle.identity is None:
            handle.join_code = "identity_unverified_no_signal"
            return
        try:
            _guarded_signal(
                handle,
                signal.SIGTERM,
                os.kill,
                expected_exe_sha=self._python_sha,
                expected_uid=1000,
                expected_device_inode=self._python_devino,
                expected_parent=os.getpid(),
            )
            handle.term_sent = True
        except ProcessLookupError:
            pass
        except PlanFailure:
            handle.join_code = "identity_changed_no_signal"
            return
        deadline = time.monotonic() + CHILD_TERM_GRACE_SECONDS
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                if handle.name == "candidate":
                    self._capture_workers()
                    self._observe_candidate_socket()
            except PlanFailure:
                # Cleanup still waits for the owned CLI. The failure is
                # retained as cleanup evidence and no unknown process is signaled.
                self.worker_scan_code = "candidate_cleanup_scan_failed"
            time.sleep(min(POLL_SECONDS, max(0.001, deadline - time.monotonic())))
        if proc.poll() is None:
            try:
                _guarded_signal(
                    handle,
                    signal.SIGKILL,
                    os.kill,
                    expected_exe_sha=self._python_sha,
                    expected_uid=1000,
                    expected_device_inode=self._python_devino,
                    expected_parent=os.getpid(),
                )
                handle.kill_sent = True
            except ProcessLookupError:
                pass
            except PlanFailure:
                handle.join_code = "identity_changed_no_kill"
                return
        try:
            proc.wait(timeout=CHILD_KILL_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            handle.join_code = "join_timeout"
            return
        handle.joined = True
        if handle.kill_sent:
            handle.join_code = "forced_exit"
        elif handle.term_sent:
            handle.join_code = "terminated"
        else:
            handle.join_code = "already_exited"

    def cleanup_all(self) -> dict[str, Any]:
        # The candidate exits first so Runtime owns its worker and socket cleanup.
        if self.candidate is not None and self.candidate.proc.poll() is None:
            try:
                self._capture_workers()
                self._observe_candidate_socket()
            except PlanFailure:
                self.worker_scan_code = "candidate_precleanup_scan_failed"
        self._stop_handle(self.candidate)
        self._stop_handle(self.qualifier)
        if self.candidate is not None and self.candidate.proc.poll() is not None:
            self.candidate.joined = True
        if self.qualifier is not None and self.qualifier.proc.poll() is not None:
            self.qualifier.joined = True
        worker_survivors, worker_scan_ok = self._worker_group_survivors()
        child_handles = (self.candidate, self.qualifier)
        children_retired = all(
            handle is None or (handle.joined and handle.proc.poll() is not None)
            for handle in child_handles
        )
        workers_retired = (
            worker_scan_ok
            and worker_survivors == 0
            and self.unexpected_worker_count == 0
            and self.worker_scan_code is None
        )
        child_retirement_proved = all(
            handle is None
            or (
                handle.identity_verified
                and not handle.kill_sent
                and handle.join_code in {"already_exited", "terminated"}
            )
            for handle in child_handles
        )
        removal_safe = children_retired and workers_retired and child_retirement_proved
        self._cleanup_removal_allowed = removal_safe
        if removal_safe:
            socket_removed, socket_code = self._remove_private_socket()
            runtime_removed = self._remove_runtime_dir() if socket_removed else False
        else:
            socket_removed, socket_code = False, "live_owner_retained"
            runtime_removed = False
        lease_fd_closed = RealIO._close_private_lease_fd(self)
        lease_identity = getattr(self, "lease_identity", None)
        self.cleanup_receipt = {
            "candidate": self.candidate.receipt() if self.candidate else None,
            "qualifier": self.qualifier.receipt() if self.qualifier else None,
            "workerCount": len(self.workers),
            "workers": [
                worker.receipt()
                for worker in sorted(
                    self.workers.values(), key=lambda item: (item.pid, item.start_ticks)
                )
            ],
            "unexpectedWorkerCount": self.unexpected_worker_count,
            "workerGroupsRetired": workers_retired,
            "workerGroupSurvivorCount": worker_survivors,
            "ownedChildrenRetired": children_retired,
            "childRetirementProved": child_retirement_proved,
            "pathRemovalSafe": removal_safe,
            "liveOwnerRetained": not removal_safe,
            "workerScanCode": self.worker_scan_code
            or ("ok" if worker_scan_ok else "worker_scan_unavailable"),
            "candidateSocketSeen": self.socket_identity is not None,
            "candidateSocketDevice": self.socket_identity[0] if self.socket_identity else None,
            "candidateSocketInode": self.socket_identity[1] if self.socket_identity else None,
            "candidateListenerInode": self.socket_listener_inode,
            "candidateSocketRemoved": socket_removed,
            "candidateSocketCleanupCode": socket_code,
            "candidateLeaseSeen": lease_identity is not None,
            "candidateLeaseDevice": lease_identity[0] if lease_identity else None,
            "candidateLeaseInode": lease_identity[1] if lease_identity else None,
            "candidateLeaseRecordVerified": getattr(self, "lease_record_verified", False),
            "candidateLeaseRemoved": getattr(self, "lease_removed", False),
            "candidateLeaseCleanupCode": getattr(self, "lease_cleanup_code", "not_observed"),
            "candidateLeaseFdClosed": lease_fd_closed,
            "privateRuntimeDirectoryRemoved": runtime_removed,
        }
        return self.cleanup_receipt

    def _close_private_lease_fd(self) -> bool:
        fd = getattr(self, "lease_fd", None)
        self.lease_fd = None
        if fd is None:
            return True
        try:
            os.close(fd)
            return True
        except OSError:
            self.lease_cleanup_code = "lease_fd_close_failed"
            return False

    def _worker_group_survivors(self) -> tuple[int, bool]:
        groups = {worker.pgrp for worker in self.workers.values()}
        if not groups:
            return 0, True
        seen = 0
        survivors = 0
        try:
            with os.scandir("/proc") as entries:
                for entry in entries:
                    if not entry.name.isdecimal():
                        continue
                    seen += 1
                    if seen > MAX_PROC_SCAN:
                        return survivors, False
                    try:
                        _start, _ppid, pgrp, session = _proc_stat(int(entry.name))
                    except PlanFailure:
                        continue
                    if pgrp in groups or session in groups:
                        survivors += 1
        except OSError:
            return survivors, False
        return survivors, True

    def _remove_private_socket(self) -> tuple[bool, str]:
        if self._cleanup_removal_allowed is not True:
            self.lease_cleanup_code = "owner_retirement_unproved"
            return False, self.lease_cleanup_code
        try:
            dir_fd = os.open(
                self.runtime_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
            )
        except OSError:
            self.lease_cleanup_code = "runtime_directory_open_failed"
            return False, "runtime_directory_open_failed"
        try:
            dir_info = os.fstat(dir_fd)
            if (
                dir_info.st_uid != 1000
                or stat.S_IMODE(dir_info.st_mode) != 0o700
                or (dir_info.st_dev, dir_info.st_ino) != self.runtime_identity
            ):
                self.lease_cleanup_code = "runtime_directory_identity_changed"
                return False, "runtime_directory_identity_changed"
            try:
                socket_info = os.stat("read.sock", dir_fd=dir_fd, follow_symlinks=False)
            except FileNotFoundError:
                socket_info = None
            except OSError:
                self.lease_cleanup_code = "socket_stat_failed"
                return False, self.lease_cleanup_code
            if self.socket_identity is None:
                if (
                    self.candidate is not None
                    or socket_info is not None
                    or self.socket_seen_bad
                    or self.lease_seen_bad
                ):
                    self.lease_cleanup_code = "unobserved_candidate_path"
                    return False, self.lease_cleanup_code
                try:
                    os.stat("read.sock.lock", dir_fd=dir_fd, follow_symlinks=False)
                except FileNotFoundError:
                    self.lease_removed = True
                    self.lease_cleanup_code = "never_created"
                    return True, "never_created_empty"
                except OSError:
                    self.lease_cleanup_code = "unexpected_lease_stat_failed"
                    return False, self.lease_cleanup_code
                self.lease_cleanup_code = "unexpected_lease_present"
                return False, self.lease_cleanup_code

            handle = self.candidate
            if (
                handle is None
                or not handle.identity_verified
                or handle.identity is None
                or not handle.joined
                or handle.proc.poll() is None
                or handle.kill_sent
                or handle.join_code not in {"already_exited", "terminated"}
                or self.socket_listener_inode is None
                or self.socket_seen_bad
                or self.lease_seen_bad
                or not self.lease_record_verified
                or self.lease_fd is None
                or self.lease_identity is None
                or self.lease_record is None
            ):
                self.lease_cleanup_code = "candidate_lease_unproved"
                return False, self.lease_cleanup_code
            if socket_info is not None and (
                not stat.S_ISSOCK(socket_info.st_mode)
                or socket_info.st_uid != 1000
                or stat.S_IMODE(socket_info.st_mode) != 0o600
                or (socket_info.st_dev, socket_info.st_ino) != self.socket_identity
            ):
                self.lease_cleanup_code = "socket_identity_changed"
                return False, self.lease_cleanup_code

            try:
                lease_path_info = os.stat(
                    "read.sock.lock", dir_fd=dir_fd, follow_symlinks=False
                )
            except OSError:
                self.lease_cleanup_code = "candidate_lease_path_unavailable"
                return False, self.lease_cleanup_code
            try:
                fd_info = os.fstat(self.lease_fd)
            except OSError:
                self.lease_cleanup_code = "candidate_lease_fd_unavailable"
                return False, self.lease_cleanup_code
            if (
                not stat.S_ISREG(lease_path_info.st_mode)
                or stat.S_ISLNK(lease_path_info.st_mode)
                or lease_path_info.st_uid != 1000
                or stat.S_IMODE(lease_path_info.st_mode) != 0o600
                or lease_path_info.st_nlink != 1
                or not stat.S_ISREG(fd_info.st_mode)
                or fd_info.st_uid != 1000
                or stat.S_IMODE(fd_info.st_mode) != 0o600
                or fd_info.st_nlink != 1
                or (lease_path_info.st_dev, lease_path_info.st_ino) != self.lease_identity
                or (fd_info.st_dev, fd_info.st_ino) != self.lease_identity
            ):
                self.lease_cleanup_code = "candidate_lease_identity_changed"
                return False, self.lease_cleanup_code
            try:
                fcntl.flock(self.lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lease_cleanup_code = "candidate_lease_busy"
                return False, self.lease_cleanup_code
            except OSError:
                self.lease_cleanup_code = "candidate_lease_lock_failed"
                return False, self.lease_cleanup_code

            try:
                path_again = os.stat("read.sock.lock", dir_fd=dir_fd, follow_symlinks=False)
                fd_again = os.fstat(self.lease_fd)
                raw = os.pread(self.lease_fd, MAX_LEASE_BYTES + 1, 0)
                fd_final = os.fstat(self.lease_fd)
                record = _parse_lease_record(raw)
            except (OSError, PlanFailure):
                self.lease_cleanup_code = "candidate_lease_recheck_failed"
                return False, self.lease_cleanup_code
            expected_record = {
                "pid": handle.identity.pid,
                "birth": handle.identity.start_ticks,
                "device": self.socket_identity[0],
                "inode": self.socket_identity[1],
            }
            if (
                (path_again.st_dev, path_again.st_ino) != self.lease_identity
                or (fd_again.st_dev, fd_again.st_ino) != self.lease_identity
                or _lease_stat_signature(fd_again) != _lease_stat_signature(fd_final)
                or _lease_stat_signature(path_again) != _lease_stat_signature(fd_final)
                or record != expected_record
                or record != self.lease_record
                or _lease_record_bytes(record) != raw
            ):
                self.lease_cleanup_code = "candidate_lease_record_changed"
                return False, self.lease_cleanup_code
            if socket_info is not None:
                try:
                    socket_again = os.stat("read.sock", dir_fd=dir_fd, follow_symlinks=False)
                except OSError:
                    self.lease_cleanup_code = "socket_identity_changed"
                    return False, self.lease_cleanup_code
                if (
                    not stat.S_ISSOCK(socket_again.st_mode)
                    or socket_again.st_uid != 1000
                    or stat.S_IMODE(socket_again.st_mode) != 0o600
                    or (socket_again.st_dev, socket_again.st_ino) != self.socket_identity
                ):
                    self.lease_cleanup_code = "socket_identity_changed"
                    return False, self.lease_cleanup_code
                try:
                    os.unlink("read.sock", dir_fd=dir_fd)
                except OSError:
                    self.lease_cleanup_code = "socket_unlink_failed"
                    return False, self.lease_cleanup_code
            try:
                lock_final = os.stat("read.sock.lock", dir_fd=dir_fd, follow_symlinks=False)
                if (
                    (lock_final.st_dev, lock_final.st_ino) != self.lease_identity
                    or _lease_stat_signature(lock_final) != _lease_stat_signature(fd_final)
                ):
                    self.lease_cleanup_code = "candidate_lease_identity_changed"
                    return False, self.lease_cleanup_code
                os.unlink("read.sock.lock", dir_fd=dir_fd)
            except OSError:
                self.lease_cleanup_code = "candidate_lease_unlink_failed"
                return False, self.lease_cleanup_code
            self.lease_removed = True
            self.lease_cleanup_code = "removed_exact_idle_lease"
            if socket_info is None:
                return True, "removed_exact_lease_after_endpoint_close"
            return True, "removed_owned_socket_and_lease"
        except OSError:
            self.lease_cleanup_code = "socket_unlink_failed"
            return False, "socket_unlink_failed"
        finally:
            os.close(dir_fd)

    def _remove_runtime_dir(self) -> bool:
        try:
            identity = _directory_identity(self.runtime_dir, uid=1000, mode=0o700)
            if identity != self.runtime_identity:
                return False
            self.runtime_dir.rmdir()
            return True
        except OSError:
            return False
        except PlanFailure:
            return False


def drive_protocol(
    io, *, now, deadline_seconds: float = ORCHESTRATOR_DEADLINE_SECONDS
) -> dict[str, Any]:
    """Run the marker-gated protocol against an injected pipe/process adapter."""
    candidate = None
    marker = None
    projected = None
    pre_marker_result = None
    qualifier_exit = None
    error: PlanFailure | None = None
    deadline = now() + deadline_seconds
    try:
        if getattr(io, "cancel_check", lambda: False)():
            raise PlanFailure("orchestrator_cancelled")
        io.start_qualifier()
        while qualifier_exit is None:
            remaining = deadline - now()
            if remaining <= 0:
                raise PlanFailure("orchestrator_deadline")
            event = io.next_event(min(POLL_SECONDS, remaining))
            if event is None:
                continue
            kind, value = event
            if kind == "cancel":
                raise PlanFailure("orchestrator_cancelled")
            if kind == "qualifier_line":
                if marker is None:
                    if pre_marker_result is not None:
                        raise PlanFailure("qualifier_extra_output")
                    if len(value) > MAX_LINE_BYTES:
                        raise PlanFailure("qualifier_line_limit")
                    try:
                        line_value = json.loads(value)
                    except (UnicodeError, json.JSONDecodeError):
                        line_value = None
                    if isinstance(line_value, dict) and line_value.get("schema") == RESULT_SCHEMA:
                        pre_marker_result = _project_result(value, None)
                        if pre_marker_result["status"] not in {
                            "unresolved",
                            "unsupported",
                            "error",
                            "failed",
                        }:
                            raise PlanFailure("qualifier_result_before_native_before")
                        io.pre_marker_result = pre_marker_result
                    else:
                        marker = _progress(value, io.socket_path)
                        io.observed_marker = marker
                        candidate = io.start_candidate()
                elif projected is None:
                    projected = _project_result(value, marker)
                    io.projected_result = projected
                else:
                    raise PlanFailure("qualifier_extra_output")
            elif kind == "candidate_exit":
                raise PlanFailure("candidate_exited_before_qualification")
            elif kind == "qualifier_exit":
                qualifier_exit = value
                io.qualifier_exit = value
                break
            else:
                raise PlanFailure("orchestrator_event_invalid")
        if marker is None:
            if pre_marker_result is None:
                raise PlanFailure("qualifier_exited_before_native_before")
            if type(qualifier_exit) is not int or qualifier_exit != pre_marker_result["exitCode"]:
                raise PlanFailure("qualifier_process_exit_mismatch")
            return {
                "marker": None,
                "comparison": pre_marker_result,
                "preMarkerResult": pre_marker_result,
                "qualifierExitCode": qualifier_exit,
                "candidateStarted": False,
            }
        if projected is None:
            raise PlanFailure("qualifier_exit_without_result")
        if type(qualifier_exit) is not int or qualifier_exit != projected["exitCode"]:
            raise PlanFailure("qualifier_process_exit_mismatch")
        if candidate is None:
            raise PlanFailure("candidate_not_started_after_marker")
        if candidate.proc.poll() is not None:
            raise PlanFailure("candidate_exited_before_cleanup")
        return {
            "marker": marker,
            "comparison": projected,
            "qualifierExitCode": qualifier_exit,
            "candidateStarted": True,
        }
    except PlanFailure as exc:
        error = exc
    except Exception:
        error = PlanFailure("orchestrator_failed")
    finally:
        io.cleanup_all()
    if error is not None:
        raise error
    raise PlanFailure("orchestrator_failed")


def _report_status(
    protocol: dict[str, Any] | None, error_code: str | None, cleanup: dict[str, Any] | None
) -> tuple[str, int, str]:
    if not isinstance(cleanup, dict):
        return "cleanup_unresolved", 4, "cleanup_receipt_missing"
    clean = _cleanup_is_clean(cleanup)
    if not clean:
        return "cleanup_unresolved", 4, "owned_cleanup_unresolved"
    if error_code is not None:
        return "failed", 4, error_code
    if protocol is None:
        return "failed", 4, "orchestrator_failed"
    comparison = protocol["comparison"]
    code = comparison["exitCode"]
    status = comparison["status"]
    if protocol.get("candidateStarted") is False:
        reason = comparison.get("reasonCode")
        if not isinstance(reason, str) or not _CODE.fullmatch(reason):
            reason = "qualification_unresolved"
        if status in {"unresolved", "unsupported"} and code == 3:
            return status, code, reason
        if status in {"error", "failed"} and code == 4:
            return "failed", code, reason
        return "failed", 4, "pre_marker_result_invalid"
    if status == "match" and code == 0:
        return "match", 0, "qualification_match"
    if status == "mismatch" and code == 2:
        return "mismatch", 2, "qualification_mismatch"
    if status in {"unresolved", "unsupported"} and code == 3:
        return "unresolved", 3, "qualification_unresolved"
    return "failed", 4, "qualification_failed"


def _cleanup_is_clean(cleanup: dict[str, Any]) -> bool:
    child_handles_ok = True
    candidate = cleanup.get("candidate")
    candidate_lease_ok = candidate is None or (
        cleanup.get("candidateLeaseRecordVerified") is True
        and cleanup.get("candidateLeaseRemoved") is True
        and cleanup.get("candidateLeaseFdClosed") is True
    )
    for key in ("candidate", "qualifier"):
        child = cleanup.get(key)
        if child is not None and (
            child.get("joined") is not True
            or child.get("joinCode") not in {"already_exited", "terminated"}
        ):
            child_handles_ok = False
    return (
        cleanup.get("workerGroupsRetired") is True
        and cleanup.get("workerGroupSurvivorCount") == 0
        and cleanup.get("unexpectedWorkerCount") == 0
        and cleanup.get("candidateSocketRemoved") is True
        and cleanup.get("privateRuntimeDirectoryRemoved") is True
        and candidate_lease_ok
        and child_handles_ok
    )


def _write_report(report: dict[str, Any]) -> str:
    _directory_identity(PLAN_ROOT, uid=1000, mode=0o700)
    name = f"snap-native-run-{secrets.token_hex(8)}.json"
    path = PLAN_ROOT / name
    raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > 64 * 1024:
        raise PlanFailure("report_size_limit")
    try:
        fd = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600
        )
    except FileExistsError:
        raise PlanFailure("report_collision") from None
    except OSError:
        raise PlanFailure("report_create_failed") from None
    try:
        info = os.fstat(fd)
        if info.st_uid != 1000 or stat.S_IMODE(info.st_mode) != 0o600:
            raise PlanFailure("report_permissions_rejected")
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PlanFailure("report_write_failed")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return name


_CANCELLED = False


def _request_cancel(_signum, _frame):
    global _CANCELLED
    _CANCELLED = True


def main() -> int:
    old_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        old_handlers[signum] = signal.signal(signum, _request_cancel)
    protocol = None
    error_code = None
    cleanup = None
    endpoint_device = None
    endpoint_inode = None
    marker = None
    install = None
    runtime_dir = None
    socket_path = None
    runtime_identity = None
    io = None
    runtime_removed = None
    try:
        if _CANCELLED:
            raise PlanFailure("orchestrator_cancelled")
        install = _verify_static_install()
        endpoint, endpoint_info = _codex_endpoint_preflight()
        endpoint_device, endpoint_inode = endpoint_info.st_dev, endpoint_info.st_ino
        runtime_dir, socket_path, runtime_identity = _make_runtime_dir()
        io = RealIO(
            endpoint=endpoint,
            runtime_dir=runtime_dir,
            socket_path=socket_path,
            runtime_identity=runtime_identity,
            install=install,
            cancel_check=lambda: _CANCELLED,
        )
        protocol = drive_protocol(io, now=time.monotonic)
        marker = protocol["marker"]
    except PlanFailure as exc:
        error_code = exc.code
    except Exception:
        error_code = "orchestrator_failed"
    finally:
        if io is not None:
            marker = getattr(io, "observed_marker", marker)
        if io is not None and io.cleanup_receipt:
            cleanup = io.cleanup_receipt
        elif io is not None:
            try:
                cleanup = io.cleanup_all()
            except Exception:
                cleanup = {
                    "workerGroupsRetired": False,
                    "workerGroupSurvivorCount": 0,
                    "candidateSocketRemoved": False,
                    "privateRuntimeDirectoryRemoved": False,
                    "candidate": None,
                    "qualifier": None,
                    "unexpectedWorkerCount": 0,
                    "cleanupCode": "cleanup_failed",
                }
        elif runtime_dir is not None and runtime_identity is not None:
            # A preflight failure after mkdir owns only this empty private dir.
            try:
                if _directory_identity(runtime_dir, uid=1000, mode=0o700) == runtime_identity:
                    runtime_dir.rmdir()
                    runtime_removed = True
                else:
                    runtime_removed = False
            except Exception:
                runtime_removed = False
        if io is None:
            cleanup = {
                "candidate": None,
                "qualifier": None,
                "workerCount": 0,
                "workers": [],
                "unexpectedWorkerCount": 0,
                "workerGroupsRetired": True,
                "workerGroupSurvivorCount": 0,
                "workerScanCode": "no_candidate_started",
                "candidateSocketSeen": False,
                "candidateSocketRemoved": True,
                "candidateSocketCleanupCode": "never_created",
                "privateRuntimeDirectoryRemoved": (
                    True if runtime_dir is None else runtime_removed is True
                ),
            }
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)

    if error_code is not None:
        status, exit_code, reason = _report_status(None, error_code, cleanup)
    else:
        status, exit_code, reason = _report_status(protocol, None, cleanup)
    if _CANCELLED and status == "match":
        status, exit_code, reason = "failed", 4, "orchestrator_cancelled"
    report = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "exitCode": exit_code,
        "reasonCode": reason,
        "hostScope": HOST_SCOPE,
        "uid": 1000,
        "windowHours": WINDOW_HOURS,
        "observerWheelSha256": OBSERVER_WHEEL_SHA256,
        "meshWheelSha256": MESH_WHEEL_SHA256,
        "pythonVersion": "3.14.8",
        "observerVersion": install.get("observerVersion") if install else None,
        "meshVersion": install.get("meshVersion") if install else None,
        "pythonSha256": install.get("pythonSha256") if install else None,
        "observerCliSha256": install.get("observerCliSha256") if install else None,
        "meshCliSha256": install.get("meshCliSha256") if install else None,
        "nativeEndpointDevice": endpoint_device,
        "nativeEndpointInode": endpoint_inode,
        "nativeBefore": marker,
        "candidateStarted": (
            protocol.get("candidateStarted")
            if protocol is not None
            else bool(io is not None and io.candidate is not None)
        ),
        "preMarkerResult": (
            protocol.get("preMarkerResult")
            if protocol is not None
            else getattr(io, "pre_marker_result", None)
            if io
            else None
        ),
        "comparison": (
            protocol.get("comparison")
            if protocol
            else getattr(io, "projected_result", None)
            if io
            else None
        ),
        "qualifierExitCode": (
            protocol.get("qualifierExitCode")
            if protocol
            else getattr(io, "qualifier_exit", None)
            if io
            else None
        ),
        "orchestratorErrorCode": error_code,
        "cleanup": cleanup,
    }
    try:
        report_name = _write_report(report)
    except PlanFailure as exc:
        report_name = None
        status, exit_code, reason = "failed", 4, exc.code
    print(
        json.dumps(
            {
                "schema": REPORT_SCHEMA,
                "status": status,
                "exitCode": exit_code,
                "reasonCode": reason,
                "report": report_name,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return exit_code


if __name__ == "__main__":
    if len(sys.argv) != 1:
        print('{"status":"failed","exitCode":4,"reasonCode":"arguments_not_allowed"}')
        raise SystemExit(4)
    raise SystemExit(main())
