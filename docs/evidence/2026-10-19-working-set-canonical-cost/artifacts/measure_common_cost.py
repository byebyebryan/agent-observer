"""One fixed 500-row controlled pair of canonical runtime/history workers."""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import importlib
import importlib.util
import json
import os
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from collections import Counter


BASE = Path(__file__).resolve().parent
LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
SOURCE_ROOTS = {
    "a7": Path("/home/bryan/.cache/agent-observer-working-set-20261018/owner-screen-59b1211/a7"),
    "b176": Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06"),
}
SOURCE_COMMITS = {
    "a7": "7807160384ba39b4d438c5c7f1b5f316c3608dcd",
    "b176": "b176ac06b39daeead4be0a33ff9d781304091fe0",
}
SOURCE_MANIFEST = Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06-manifest.json")
SOURCE_MANIFEST_SHA256 = "c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877"
SOURCE_ROUTE_HASHES = {
    "_service_worker.py": "bbebf60b01d53343f719ba0e5c95a8bad2ff3b7d0461e55386caad73aeac86b9",
    "adapters.py": "21511b8de49d91d49a4dde26eae87458db6da5a9babab8421feade7b67e2b276",
    "codex_snapshot.py": "15fe0ba786c976e3518c93346eda8f93a0975b75b56bcd0f8705b008bc993c7c",
    "codex_endpoint.py": "9fce9953f3658186f943c880972ce1416b1f420a3781c446ae2df14dd7c1e1fd",
    "codex_transport.py": "bc18356e71ed831e72e3558bb03a5578c7e96eb4baa9e859047cee448f0f0807",
    "codex_metadata.py": "97531ee14d20ec1396d57c924f97fa83c488ebb016aae2caa68fb1644a6b9a23",
    "activity.py": "f8ad39a1992070347988b0b9c73710bc7acecd3336afb1cf47dcefcbd67bbff1",
    "timing.py": "8748c4285271f39eb50cf9bb1d58074bf76fe276ebf522a05f588ab83ece942d",
    "collection.py": "0457bd251360726a661045103495465e56c7a22434e3c24d77380ab80209e6f9",
    "workspace.py": "4b8a63d362af880b6acd4326e767d32a800df3f5f6e1282e5c4d62d4263ac92e",
    "bounded_json.py": "846a8538de41525359a2147a1f5b71f3958f0028490fd0d23c4041de07b6c0e6",
    "provider.py": "98243e7de42af101951b3ffba9de017a66f78483ecc70b651e5f3d48fe61c7b8",
    "observation_model.py": "21d05a226ecaeda8ee881cb89a9c7f44bc33057bccd6ae8f8005edb0e5613c6c",
    "observation_scheduler.py": "e3850f0c2791e21600e57daca3d8af8756d7e072065afa0b69febcb690896dd6",
}
FIXTURE_SOURCE_ROOT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/final-source-b176ac06")
FIXTURE_SOURCE_COMMIT = "b176ac06b39daeead4be0a33ff9d781304091fe0"
INTERPRETERS = {
    "py311": Path("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"),
    "py314": Path("/home/bryan/code/mesh-plus/.venv/bin/python"),
}
EXPECTED_INTERPRETER_REALPATHS = {
    "py311": Path("/home/bryan/code/agent-observer/.local/cpu-prepared-20261015/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11"),
    "py314": Path("/usr/bin/python3.14"),
}
SERVER = BASE / "fixture_server.py"
EXPECTED_ROWS = 500
LOADED_ROWS = 2
WORKER_TIMEOUT_MS = 10_000
COLLECTOR_TIMEOUT_SECONDS = 10.0
SERVER_STDERR_LIMIT = 65_536
WORKER_DRAIN_TIMEOUT_SECONDS = 10.0
CHILD_REAP_TIMEOUT_SECONDS = 2.0
SERVER_STOP_TIMEOUT_SECONDS = 3.0
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024 - 1024


class ProbeFailure(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_spawn_ast(root: Path) -> str:
    tree = ast.parse((root / "agent_observer/service_runtime.py").read_text(encoding="utf-8"))
    runtime = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Runtime"
    )
    spawn = next(
        node for node in runtime.body
        if isinstance(node, ast.FunctionDef) and node.name == "_spawn"
    )
    return ast.dump(spawn, include_attributes=False)


def verify_source_pins() -> dict:
    try:
        manifest_bytes = SOURCE_MANIFEST.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ProbeFailure("pinned_source_manifest_unavailable") from None
    if sha256(manifest_bytes) != SOURCE_MANIFEST_SHA256 or manifest.get("commit") != SOURCE_COMMITS["b176"]:
        raise ProbeFailure("pinned_source_manifest_mismatch")
    for source, root in SOURCE_ROOTS.items():
        if not root.is_dir():
            raise ProbeFailure("pinned_source_root_missing")
        for name, expected in SOURCE_ROUTE_HASHES.items():
            path = root / "agent_observer" / name
            try:
                actual = sha256(path.read_bytes())
            except OSError:
                raise ProbeFailure("pinned_source_file_missing") from None
            if actual != expected:
                raise ProbeFailure("pinned_source_file_mismatch")
            if source == "b176" and manifest.get("files", {}).get(f"agent_observer/{name}") != expected:
                raise ProbeFailure("pinned_source_manifest_file_mismatch")
    if runtime_spawn_ast(SOURCE_ROOTS["a7"]) != runtime_spawn_ast(SOURCE_ROOTS["b176"]):
        raise ProbeFailure("pinned_parent_spawn_ast_mismatch")
    return {
        "b176ManifestSha256": SOURCE_MANIFEST_SHA256,
        "routeFileSha256": dict(sorted(SOURCE_ROUTE_HASHES.items())),
        "parentSpawnAstEqual": True,
    }


def birth_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    return int(raw[raw.rindex(")") + 2 :].split()[19])


def proc_state(pid: int) -> str:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    return raw[raw.rindex(")") + 2 :].split()[0]


def proc_cmdline(pid: int) -> bytes:
    return Path(f"/proc/{pid}/cmdline").read_bytes()


def listener_inode(endpoint: Path) -> int:
    matches = set()
    for line in Path("/proc/net/unix").read_text(encoding="ascii").splitlines()[1:]:
        fields = line.split(maxsplit=7)
        if len(fields) != 8 or fields[7] != str(endpoint):
            continue
        if int(fields[3], 16) & 0x10000 and int(fields[4], 16) == 1:
            matches.add(int(fields[6]))
    if len(matches) != 1:
        raise ProbeFailure("listener_ambiguous")
    return next(iter(matches))


def owned_process_record(
    process: subprocess.Popen,
    expected_argv: list[str],
    binary: Path,
    *,
    expected_start_ticks: int | None = None,
) -> dict:
    """Verify identity without polling/reaping the direct child."""
    pid = process.pid
    if process.returncode is not None or process.args != expected_argv:
        raise ProbeFailure("process_handle_identity_mismatch")
    start = birth_ticks(pid)
    if expected_start_ticks is not None and start != expected_start_ticks:
        raise ProbeFailure("process_birth_identity_mismatch")
    state = proc_state(pid)
    actual_argv = proc_cmdline(pid)
    expected_cmdline = b"\0".join(os.fsencode(arg) for arg in expected_argv) + b"\0"
    executable = Path(os.readlink(f"/proc/{pid}/exe"))
    expected_executable = binary.resolve(strict=True)
    actual_stat, expected_stat = executable.stat(), expected_executable.stat()
    command_matches = actual_argv == expected_cmdline or (not actual_argv and state == "Z")
    if (
        not command_matches
        or executable != expected_executable
        or (actual_stat.st_dev, actual_stat.st_ino) != (expected_stat.st_dev, expected_stat.st_ino)
        or os.getpgid(pid) != pid
        or birth_ticks(pid) != start
    ):
        raise ProbeFailure("process_ownership_mismatch")
    return {
        "pid": pid,
        "startTicks": start,
        "stateAtCheck": state,
        "argvExact": True,
        "executable": str(executable),
        "executableDevice": actual_stat.st_dev,
        "executableInode": actual_stat.st_ino,
    }


def verify_process_still_owned(
    process: subprocess.Popen,
    record: dict,
    expected_argv: list[str],
    binary: Path,
) -> bool:
    if process.returncode is not None:
        return False
    pid = record["pid"]
    try:
        state = proc_state(pid)
        actual_argv = proc_cmdline(pid)
        executable = Path(os.readlink(f"/proc/{pid}/exe"))
        actual_stat = executable.stat()
        expected_stat = binary.resolve(strict=True).stat()
        return (
            process.args == expected_argv
            and birth_ticks(pid) == record["startTicks"]
            and (actual_argv == b"\0".join(os.fsencode(arg) for arg in expected_argv) + b"\0"
                 or (not actual_argv and state == "Z"))
            and executable == Path(record["executable"])
            and (actual_stat.st_dev, actual_stat.st_ino)
            == (record["executableDevice"], record["executableInode"])
            and (actual_stat.st_dev, actual_stat.st_ino)
            == (expected_stat.st_dev, expected_stat.st_ino)
            and os.getpgid(pid) == pid
        )
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, ValueError):
        return False


def acquire_shared_lock() -> int:
    try:
        fd = os.open(LOCK, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        raise ProbeFailure("shared_lock_unavailable") from None
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
        os.close(fd)
        raise ProbeFailure("shared_lock_ownership_mismatch")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise ProbeFailure("shared_lock_busy") from None
    return fd


def synthetic_rows(output_path: Path) -> tuple[list[dict], dict[str, dict]]:
    # Importing the fixture test module also imports its Observer package.
    # Compile only this reviewed pure dictionary factory, never that module.
    fixture_path = FIXTURE_SOURCE_ROOT / "tests/test_codex_snapshot.py"
    tree = ast.parse(fixture_path.read_text())
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "native")
    if len(factory.body) != 1 or not isinstance(factory.body[0], ast.Return) or not isinstance(factory.body[0].value, ast.Dict):
        raise ProbeFailure("snapshot_fixture_factory_changed")
    namespace = {"__builtins__": {}}
    exec(compile(ast.Module(body=[factory], type_ignores=[]), str(fixture_path), "exec"), namespace)
    native = namespace["native"]
    rows, expected = [], {}
    for index in range(EXPECTED_ROWS):
        thread_num = index + 1
        root_num = index + 10_001
        thread_id = f"{thread_num:08x}-1234-4234-8234-{thread_num:012x}"
        session_root_id = f"{root_num:08x}-5678-4678-8678-{root_num:012x}"
        status_type = "active" if index == 0 else "idle" if index == 1 else "notLoaded"
        row = native(thread_id)
        row["sessionId"] = session_root_id
        row["status"] = {
            "type": status_type,
            **({"activeFlags": []} if status_type == "active" else {}),
        }
        row["createdAt"] = 1_800_000_000 + index
        row["updatedAt"] = 1_800_000_123 + index
        row.pop("name", None)
        if set(row) != {
            "id", "sessionId", "cwd", "source", "threadSource", "ephemeral",
            "status", "createdAt", "updatedAt",
        }:
            raise ProbeFailure("snapshot_fixture_shape_changed")
        if thread_id == session_root_id:
            raise ProbeFailure("synthetic_identity_collision")
        rows.append(row)
        expected[thread_id] = {
            "sessionTreeRootId": session_root_id,
            "nativeStatus": status_type,
            "runtime": "running" if index < LOADED_ROWS else "parked",
            "phase": "working" if index == 0 else "waiting" if index == 1 else None,
        }
    content = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if any(token in content for token in (b"\"name\"", b"\"title\"", b"\"prompt\"", b"\"preview\"", b"\"turns\"", b"\"tool")):
        raise ProbeFailure("fixture_contains_content_fields")
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb", closefd=True) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return rows, expected


def make_config_home(run_dir: Path) -> tuple[Path, Path, Path, str, Path, str, os.stat_result, bool]:
    home = run_dir / "codex-home"
    home.mkdir(mode=0o700)
    control_dir = home / "app-server-control"
    control_dir.mkdir(mode=0o700)
    control = control_dir / "app-server-control.sock"
    endpoint = Path(f"/tmp/codex-daemon-{os.geteuid()}") / hashlib.sha256(str(control).encode()).hexdigest()
    if os.path.lexists(endpoint):
        raise ProbeFailure("endpoint_target_present")

    source_executable = Path(sys.executable).resolve(strict=True)
    if not source_executable.is_file() or source_executable.read_bytes()[:4] != b"\x7fELF":
        raise ProbeFailure("python_executable_unusable")
    binary = home / "packages/app-server-daemon/releases/0.0.0-x86_64-unknown-linux-musl/bin/codex"
    binary.parent.mkdir(parents=True, mode=0o700)
    shutil.copyfile(source_executable, binary)
    os.chmod(binary, 0o755)
    binary_digest = sha256(binary.read_bytes())
    release_root = binary.parent.parent
    venv_config = release_root / "pyvenv.cfg"
    venv_bytes = (
        f"home = {Path(sys.base_prefix) / 'bin'}\n"
        "include-system-site-packages = false\n"
        f"version = {sys.version.split()[0]}\n"
        f"executable = {sys.executable}\n"
    ).encode("utf-8")
    fd = os.open(venv_config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, "wb", closefd=True) as stream:
        stream.write(venv_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    venv_info = venv_config.lstat()
    if (
        not stat.S_ISREG(venv_info.st_mode)
        or venv_info.st_uid != os.geteuid()
        or stat.S_IMODE(venv_info.st_mode) != 0o600
        or venv_config.read_bytes() != venv_bytes
    ):
        raise ProbeFailure("fake_interpreter_config_mismatch")
    venv_digest = sha256(venv_bytes)
    control.symlink_to(endpoint)
    if control.lstat().st_uid != os.geteuid() or control.resolve(strict=False) != endpoint:
        raise ProbeFailure("control_symlink_mismatch")
    try:
        endpoint_root_stat = endpoint.parent.lstat()
        if (
            not stat.S_ISDIR(endpoint_root_stat.st_mode)
            or endpoint_root_stat.st_uid != os.geteuid()
            or stat.S_IMODE(endpoint_root_stat.st_mode) != 0o700
        ):
            raise ProbeFailure("endpoint_directory_ownership_mismatch")
        created_endpoint_root = False
    except FileNotFoundError:
        endpoint.parent.mkdir(mode=0o700)
        endpoint_root_stat = endpoint.parent.lstat()
        created_endpoint_root = True
    return home, endpoint, binary, binary_digest, venv_config, venv_digest, endpoint_root_stat, created_endpoint_root


def cleanup_endpoint_root(endpoint: Path, original_stat, created: bool) -> bool:
    if not created:
        return True
    try:
        current = endpoint.parent.lstat()
        if (
            current.st_dev != original_stat.st_dev
            or current.st_ino != original_stat.st_ino
            or current.st_uid != os.geteuid()
            or not stat.S_ISDIR(current.st_mode)
        ):
            return False
        endpoint.parent.rmdir()
        return True
    except OSError:
        return False


def server_file_limit() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (SERVER_STDERR_LIMIT, SERVER_STDERR_LIMIT))


def stderr_digest(path: Path) -> dict:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"bytes": 0, "sha256": sha256(b""), "truncated": False}
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_size > SERVER_STDERR_LIMIT
    ):
        raise ProbeFailure("fixture_stderr_file_untrusted")
    data = path.read_bytes()
    if len(data) != info.st_size:
        raise ProbeFailure("fixture_stderr_file_changed")
    return {"bytes": len(data), "sha256": sha256(data), "truncated": len(data) == SERVER_STDERR_LIMIT}


def drain_worker(process: subprocess.Popen, *, timeout: float = WORKER_DRAIN_TIMEOUT_SECONDS) -> bytes:
    import select

    if process.stdout is None:
        raise ProbeFailure("worker_stdout_missing")
    fd = process.stdout.fileno()
    deadline = time.monotonic() + timeout
    raw = bytearray()
    oversized = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProbeFailure("worker_pipe_timeout")
        readable, _, _ = select.select([fd], [], [], min(remaining, 0.25))
        if not readable:
            continue
        chunk = os.read(fd, 65_536)
        if not chunk:
            break
        if not oversized:
            if len(raw) + len(chunk) <= MAX_SNAPSHOT_BYTES:
                raw.extend(chunk)
            else:
                oversized = True
                raw.clear()
    if oversized:
        raise ProbeFailure("worker_snapshot_limit")
    return bytes(raw)


def close_worker_resources(runtime, process: subprocess.Popen) -> None:
    for stream in (process.stdout, process.stdin):
        if stream is not None and not stream.closed:
            stream.close()
    runtime._close_memo_channel(process)


def install_wait4_status(process: subprocess.Popen, pid: int, status: int, usage) -> tuple[int, dict]:
    if pid != process.pid:
        raise ProbeFailure("wait4_unexpected_pid")
    process._handle_exitstatus(status)
    translated = os.waitstatus_to_exitcode(status)
    if process.returncode != translated:
        raise ProbeFailure("popen_wait4_status_mismatch")
    return translated, {
        "waitedPid": pid,
        "waitStatusExitCode": translated,
        "popenReturnCode": process.returncode,
        "userCpuNs": int(round(usage.ru_utime * 1_000_000_000)),
        "systemCpuNs": int(round(usage.ru_stime * 1_000_000_000)),
    }


def reap_owned_child_if_exited(process: subprocess.Popen) -> tuple[int, dict] | None:
    """Reap only this unreaped Popen child if it has already exited."""
    if process.returncode is not None:
        return None
    with process._waitpid_lock:
        if process.returncode is not None:
            return None
        try:
            pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        except ChildProcessError:
            raise ProbeFailure("direct_child_already_reaped") from None
        if pid == 0:
            return None
        return install_wait4_status(process, pid, status, usage)


def wait4_owned_child(process: subprocess.Popen, *, timeout: float) -> tuple[int, dict]:
    """Wait/reap only this Popen child and install status on its Popen handle."""
    deadline = time.monotonic() + timeout
    while True:
        result = reap_owned_child_if_exited(process)
        if result is not None:
            return result
        if process.returncode is not None:
            raise ProbeFailure("direct_child_already_reconciled")
        if time.monotonic() >= deadline:
            raise ProbeFailure("direct_child_wait4_timeout")
        time.sleep(0.005)


def stop_owned_server(process: subprocess.Popen, record: dict, expected_argv: list[str], binary: Path) -> tuple[int, dict]:
    if process.returncode is None:
        reaped = reap_owned_child_if_exited(process)
        if reaped is not None:
            return reaped
        if not verify_process_still_owned(process, record, expected_argv, binary):
            reaped = reap_owned_child_if_exited(process)
            if reaped is not None:
                return reaped
            raise ProbeFailure("server_process_ownership_lost")
        try:
            process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            reaped = reap_owned_child_if_exited(process)
            if reaped is not None:
                return reaped
            raise ProbeFailure("server_process_signal_target_lost") from None
    try:
        return wait4_owned_child(process, timeout=SERVER_STOP_TIMEOUT_SECONDS)
    except ProbeFailure as error:
        if str(error) != "direct_child_wait4_timeout":
            raise
        reaped = reap_owned_child_if_exited(process)
        if reaped is not None:
            return reaped
        if not verify_process_still_owned(process, record, expected_argv, binary):
            reaped = reap_owned_child_if_exited(process)
            if reaped is not None:
                return reaped
            raise ProbeFailure("server_process_ownership_lost") from None
        try:
            process.send_signal(signal.SIGKILL)
        except ProcessLookupError:
            reaped = reap_owned_child_if_exited(process)
            if reaped is not None:
                return reaped
            raise ProbeFailure("server_process_signal_target_lost") from None
        return wait4_owned_child(process, timeout=CHILD_REAP_TIMEOUT_SECONDS)


def load_other_contract(package_name: str, root: Path):
    package_dir = root / "agent_observer"
    spec = importlib.util.spec_from_file_location(
        package_name,
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise ProbeFailure("peer_parser_package_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return importlib.import_module(f"{package_name}.contract")


def parser_digest(contract_module, parsed: dict) -> str:
    return sha256(contract_module.canonical(parsed).encode("utf-8"))


def verify_join(parsed: dict, expected_rows: dict[str, dict]) -> dict:
    sessions = parsed["sessions"]
    by_id = {row["identity"]["nativeId"]: row for row in sessions}
    if len(by_id) != EXPECTED_ROWS or set(by_id) != set(expected_rows):
        raise ProbeFailure("canonical_identity_set_mismatch")
    counts = Counter()
    for thread_id, expected in expected_rows.items():
        row = by_id[thread_id]
        if (
            row["identity"]["nativeId"] != thread_id
            or row["nativeIds"]["threadId"] != thread_id
            or row["nativeIds"]["sessionTreeRootId"] != expected["sessionTreeRootId"]
            or thread_id == expected["sessionTreeRootId"]
            or row["runtime"]["value"] != expected["runtime"]
            or (row["phase"]["value"] if row["phase"] is not None else None) != expected["phase"]
            or row["hasSavedHistory"] is not True
        ):
            raise ProbeFailure("canonical_identity_status_join_mismatch")
        counts[row["runtime"]["value"]] += 1
    if counts != Counter({"running": LOADED_ROWS, "parked": EXPECTED_ROWS - LOADED_ROWS}):
        raise ProbeFailure("canonical_status_census_mismatch")
    ids_digest = sha256("\n".join(sorted(by_id)).encode("ascii"))
    expected_digest = sha256("\n".join(sorted(expected_rows)).encode("ascii"))
    if ids_digest != expected_digest:
        raise ProbeFailure("canonical_id_digest_mismatch")
    return {
        "joinedRows": len(by_id),
        "identityAndStatusJoins": True,
        "runningRows": counts["running"],
        "parkedRows": counts["parked"],
        "outputIdSetSha256": ids_digest,
        "expectedIdSetSha256": expected_digest,
        "distinctSessionRootIds": len({row["sessionTreeRootId"] for row in expected_rows.values()}),
    }


def run_trial(source: str, replicate: int, interpreter: str) -> dict:
    if replicate not in {1, 2}:
        raise ProbeFailure("replicate_out_of_bounds")
    output = BASE / f"{interpreter}-{source}-r{replicate}.json"
    if os.path.lexists(output):
        raise ProbeFailure("receipt_already_exists")
    if Path(sys.executable).resolve(strict=True) != EXPECTED_INTERPRETER_REALPATHS[interpreter]:
        raise ProbeFailure("interpreter_identity_mismatch")
    if not SOURCE_ROOTS[source].is_dir() or not SERVER.is_file():
        raise ProbeFailure("pinned_source_missing")
    lock_fd = acquire_shared_lock()
    run_dir = None
    run_dir_identity = None
    server = worker = None
    server_record = worker_record = None
    expected_server_argv = expected_worker_argv = None
    server_start_ticks = worker_start_ticks = None
    stderr_path = endpoint = binary = config_home = None
    stats_path = rows_path = None
    endpoint_root_stat = None
    created_endpoint_root = False
    endpoint_record = None
    runtime = state = None
    job = None
    retain_private = False
    stage = "create_private_run_directory"
    result = {
        "schema": "observer-canonical-worker-measurement-v6",
        "status": "failed",
        "source": source,
        "sourceCommit": SOURCE_COMMITS[source],
        "sourceRoot": str(SOURCE_ROOTS[source]),
        "interpreter": interpreter,
        "interpreterExecutable": sys.executable,
        "interpreterRealpath": str(Path(sys.executable).resolve(strict=True)),
        "interpreterVersion": sys.version.split()[0],
        "replicate": replicate,
        "rows": EXPECTED_ROWS,
        "loadedRows": LOADED_ROWS,
        "workerTimeoutMs": WORKER_TIMEOUT_MS,
        "collectorTimeoutSeconds": COLLECTOR_TIMEOUT_SECONDS,
        "runtimeAndHistoryRunInDefaultSchedulerOrder": False,
        "cleanup": {},
    }
    try:
        stage = "verify_pinned_sources"
        result["sourcePinVerification"] = verify_source_pins()
        run_dir = Path(tempfile.mkdtemp(prefix=f"{interpreter}-{source}-r{replicate}-", dir=BASE))
        run_dir_identity = run_dir.lstat()
        rows_path = run_dir / "synthetic-rows.json"
        stats_path = run_dir / "server-stats.json"
        stderr_path = run_dir / "fixture-server.stderr"

        stage = "prepare_synthetic_rows"
        rows, expected_rows = synthetic_rows(rows_path)
        fixture_bytes = rows_path.read_bytes()
        result["fixtureInputSha256"] = sha256(fixture_bytes)
        result["fixtureInputBytes"] = len(fixture_bytes)
        result["fixtureContentFree"] = True
        result["fixtureSourceRoot"] = str(FIXTURE_SOURCE_ROOT)
        result["fixtureSourceCommit"] = FIXTURE_SOURCE_COMMIT
        result["expectedIdSetSha256"] = sha256("\n".join(sorted(expected_rows)).encode("ascii"))

        stage = "verify_selected_parent_imports"
        if any(name == "agent_observer" or name.startswith("agent_observer.") for name in sys.modules):
            raise ProbeFailure("observer_package_imported_before_source_selection")
        sys.path.insert(0, str(SOURCE_ROOTS[source]))
        import agent_observer.service_runtime as selected_runtime
        import agent_observer.contract as selected_contract
        expected_package = (SOURCE_ROOTS[source] / "agent_observer").resolve()
        if Path(selected_runtime.__file__).resolve() != expected_package / "service_runtime.py" or Path(selected_contract.__file__).resolve() != expected_package / "contract.py":
            raise ProbeFailure("selected_parent_import_path_mismatch")
        result["selectedParentImportsExact"] = True
        result["selectedParentModuleHashes"] = {
            name: sha256(Path(module.__file__).read_bytes())
            for name, module in (("service_runtime.py", selected_runtime), ("contract.py", selected_contract))
        }

        stage = "prepare_fake_managed_endpoint"
        (
            config_home, endpoint, binary, binary_digest, venv_config, venv_digest,
            endpoint_root_stat, created_endpoint_root,
        ) = make_config_home(run_dir)
        result["fakeExecutableSha256"] = binary_digest
        result["fakeInterpreterConfigSha256"] = venv_digest
        result["fakeInterpreterConfigPath"] = str(venv_config)
        result["endpointTarget"] = str(endpoint)
        result["endpointWasAbsentBeforeBind"] = not os.path.lexists(endpoint)
        if not result["endpointWasAbsentBeforeBind"]:
            raise ProbeFailure("endpoint_target_present")

        expected_server_argv = [
            str(binary), "-I", "-B", str(SERVER),
            "--endpoint", str(endpoint),
            "--config-home", str(config_home),
            "--rows-file", str(rows_path),
            "--stats-file", str(stats_path),
        ]
        stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(stderr_fd, "wb", closefd=True) as stderr_stream:
            server = subprocess.Popen(
                expected_server_argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_stream,
                cwd=run_dir,
                start_new_session=True,
                preexec_fn=server_file_limit,
            )
        server_start_ticks = birth_ticks(server.pid)
        stage = "verify_fixture_server_process_identity"
        server_record = owned_process_record(
            server, expected_server_argv, binary, expected_start_ticks=server_start_ticks,
        )
        result["fixtureServerProcess"] = server_record

        stage = "wait_for_fixture_endpoint_bind"
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if proc_state(server.pid) == "Z":
                raise ProbeFailure("fixture_server_exit_before_bind")
            try:
                info = endpoint.lstat()
                if stat.S_ISSOCK(info.st_mode):
                    break
            except FileNotFoundError:
                pass
            time.sleep(0.01)
        else:
            raise ProbeFailure("fixture_server_bind_timeout")
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ProbeFailure("endpoint_socket_ownership_mismatch")
        endpoint_record = {"device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid, "mode": stat.S_IMODE(info.st_mode)}
        inode = listener_inode(endpoint)
        if not any(os.readlink(fd) == f"socket:[{inode}]" for fd in Path(f"/proc/{server.pid}/fd").iterdir()):
            raise ProbeFailure("fixture_listener_fd_unowned")
        endpoint_record["listenerInode"] = inode
        result["fixtureServer"] = {**server_record, "endpointDevice": info.st_dev, "endpointInode": info.st_ino, "listenerInode": inode, "listenerFdOwned": True}

        stage = "qualify_managed_endpoint"
        sys.path.insert(0, str(SOURCE_ROOTS[source]))
        from agent_observer.codex_endpoint import inspect_managed_endpoint
        from agent_observer.contract import MAX_SNAPSHOT_BYTES as SOURCE_MAX_SNAPSHOT_BYTES
        from agent_observer.service_runtime import Runtime, Worker
        from agent_observer.service_state import ServiceState

        if SOURCE_MAX_SNAPSHOT_BYTES != MAX_SNAPSHOT_BYTES:
            raise ProbeFailure("source_snapshot_limit_changed")
        identity = inspect_managed_endpoint(config_home)
        if (
            identity.pid != server.pid
            or identity.start_ticks != server_record["startTicks"]
            or identity.endpoint != str(endpoint)
            or identity.binary_sha256 != binary_digest
            or identity.listener_inode != inode
            or identity.endpoint_inode != info.st_ino
            or identity.version != "0.0.0"
        ):
            raise ProbeFailure("managed_endpoint_qualification_mismatch")
        result["managedEndpointQualified"] = True
        result["runtimeIdentity"] = {
            "pid": identity.pid,
            "startTicks": identity.start_ticks,
            "version": identity.version,
            "binarySha256": identity.binary_sha256,
            "endpoint": identity.endpoint,
            "listenerInode": identity.listener_inode,
            "endpointInode": identity.endpoint_inode,
        }

        peer_source = "b176" if source == "a7" else "a7"
        peer_contract = load_other_contract(f"_observer_{peer_source}_strict", SOURCE_ROOTS[peer_source])
        active_contract = importlib.import_module("agent_observer.contract")
        state = ServiceState(host_scope="fixture", configs={"codex": (str(config_home), "explicit")})
        runtime = Runtime(state, run_dir / "unused-read.sock", collect=True)
        if runtime.scheduler.timeout != WORKER_TIMEOUT_MS or runtime.scheduler.intervals != {"runtime": 2000, "history": 60000}:
            raise ProbeFailure("default_scheduler_configuration_changed")
        result["schedulerDefaults"] = {"timeoutMs": runtime.scheduler.timeout, "intervalsMs": dict(runtime.scheduler.intervals)}

        for component in ("runtime", "history"):
            stage = f"spawn_{component}_worker"
            jobs = runtime.scheduler.start_due(state.clock())
            if len(jobs) != 1 or jobs[0].component != component:
                raise ProbeFailure("default_scheduler_component_order_mismatch")
            job = jobs[0]
            expected_worker_argv = [
                sys.executable, "-I", "-B",
                str(SOURCE_ROOTS[source] / "agent_observer/_service_worker.py"),
            ]
            start = time.process_time_ns()
            worker = runtime._spawn(job)
            spawn_cpu_ns = time.process_time_ns() - start
            worker_start_ticks = birth_ticks(worker.pid)
            result.setdefault("spawnedChildHandles", []).append({
                "pid": worker.pid, "startTicks": worker_start_ticks,
                "actualArgv": list(worker.args), "expectedArgvExact": worker.args == expected_worker_argv,
            })
            worker_record = owned_process_record(
                worker, expected_worker_argv, Path(sys.executable),
                expected_start_ticks=worker_start_ticks,
            )
            result.setdefault("components", {})[component] = {
                "component": component,
                "jobDeadlineMs": job.deadline - job.started,
                "workerProcess": worker_record,
                "parentSpawnCpuNs": spawn_cpu_ns,
            }

            stage = f"drain_and_wait_{component}_worker"
            start = time.process_time_ns()
            raw = drain_worker(worker, timeout=WORKER_TIMEOUT_MS / 1000)
            worker_exit, worker_rusage = wait4_owned_child(worker, timeout=CHILD_REAP_TIMEOUT_SECONDS)
            parent_drain_wait_cpu_ns = time.process_time_ns() - start
            component_result = result["components"][component]
            component_result.update({
                "workerExitStatus": worker_exit,
                "workerOutputBytes": len(raw),
                "workerOutputSha256": sha256(raw),
                "workerDirectChildRusage": worker_rusage,
                "parentDrainAndWaitCpuNs": parent_drain_wait_cpu_ns,
            })
            if worker_exit != 0:
                raise ProbeFailure("canonical_worker_failed")
            close_worker_resources(runtime, worker)
            worker = None
            worker_record = None
            worker_start_ticks = None

            stage = f"parse_{component}_snapshot"
            start = time.process_time_ns()
            parsed = active_contract.parse_snapshot(raw)
            source_parse_cpu_ns = time.process_time_ns() - start
            start = time.process_time_ns()
            peer_parsed = peer_contract.parse_snapshot(raw)
            peer_parse_cpu_ns = time.process_time_ns() - start
            active_digest = parser_digest(active_contract, parsed)
            peer_digest = parser_digest(peer_contract, peer_parsed)
            if active_digest != peer_digest:
                raise ProbeFailure("strict_parser_dto_semantics_differ")
            if parsed["schemaVersion"] != 6 or peer_parsed["schemaVersion"] != 6:
                raise ProbeFailure("api4_schema_mismatch")
            if parsed["sourceHealth"] != "current":
                raise ProbeFailure("source_health_not_current")
            source_record = parsed["sources"][0]
            coverage = source_record["coverage"]
            if coverage["saved"]["status"] != "complete" or coverage["runtime"]["status"] != "complete":
                raise ProbeFailure("canonical_coverage_incomplete")
            joins = verify_join(parsed, expected_rows)
            peer_joins = verify_join(peer_parsed, expected_rows)
            if joins != peer_joins:
                raise ProbeFailure("strict_parser_identity_join_mismatch")
            source_runtime = source_record["runtime"]
            if any(source_runtime.get(key) != identity_value for key, identity_value in (
                ("pid", identity.pid), ("startTicks", identity.start_ticks),
                ("endpoint", identity.endpoint), ("version", identity.version),
                ("binarySha256", identity.binary_sha256),
            )):
                raise ProbeFailure("snapshot_runtime_identity_mismatch")
            component_result.update({
                "schemaVersion": parsed["schemaVersion"],
                "sourceHealth": parsed["sourceHealth"],
                "coverage": {"saved": coverage["saved"]["status"], "runtime": coverage["runtime"]["status"]},
                "sourceParserCpuNs": source_parse_cpu_ns,
                "peerParserCpuNsForParityOnly": peer_parse_cpu_ns,
                "sourceParserDigest": active_digest,
                "peerParserDigest": peer_digest,
                "exactSameRawParserDtoEquality": True,
                **joins,
                "runtimeProvenanceJoined": True,
            })
            del raw, parsed, peer_parsed
            if state.revision != 0 or runtime.workers:
                raise ProbeFailure("state_acceptance_was_invoked")
            runtime.scheduler.finish(job, state.clock(), success=True)
            job = None
            result["runtimeAndHistoryRunInDefaultSchedulerOrder"] = True

        stage = "stop_fixture_server"
        server_exit, server_rusage = stop_owned_server(server, server_record, expected_server_argv, binary)
        result["fixtureServerExitStatus"] = server_exit
        result["fixtureServerDirectChildRusage"] = server_rusage
        if server_exit != 0:
            raise ProbeFailure("fixture_server_shutdown_failed")
        server = None

        stage = "verify_fixture_protocol"
        if not stats_path.is_file():
            raise ProbeFailure("fixture_stats_missing")
        stats_info = stats_path.lstat()
        if not stat.S_ISREG(stats_info.st_mode) or stats_info.st_uid != os.geteuid() or stat.S_IMODE(stats_info.st_mode) != 0o600:
            raise ProbeFailure("fixture_stats_file_untrusted")
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        result["serverProtocol"] = stats
        expected_method_counts = {
            "initialize": 2,
            "initialized": 2,
            "thread/loaded/list": 2,
            "thread/list": 10,
            "thread/read": 1004,
            "thread/turns/list": 502,
        }
        if (
            stats["hardFail"]
            or stats["methodCounts"] != expected_method_counts
            or stats["threadListPageSizes"] != [100] * 10
            or stats["acceptedConnections"] != 5
        ):
            raise ProbeFailure("fixture_server_protocol_failed")
        result["fixtureServerStderr"] = stderr_digest(stderr_path)
        result["status"] = "passed"
    except ProbeFailure as error:
        result["failureStage"] = stage
        result["failureReason"] = str(error)
    except Exception as error:
        result["failureStage"] = stage
        result["failureClass"] = type(error).__name__
        code = str(error)
        if (
            type(error).__name__ == "EndpointError"
            and code
            and len(code) <= 96
            and code.isascii()
            and all(char.islower() or char.isdigit() or char == "_" for char in code)
        ):
            result["failureReason"] = code
        else:
            result["failureReason"] = type(error).__name__
    finally:
        cleanup = result.setdefault("cleanup", {})
        if worker is not None:
            try:
                if worker.returncode is None:
                    reaped = reap_owned_child_if_exited(worker)
                    if reaped is not None:
                        result["canonicalWorkerExitStatus"], result["canonicalWorkerDirectChildRusage"] = reaped
                    if runtime is None or job is None or expected_worker_argv is None or worker_start_ticks is None:
                        if worker.returncode is None:
                            raise ProbeFailure("worker_cleanup_identity_unavailable")
                    if worker.returncode is None:
                        if worker_record is None:
                            try:
                                worker_record = owned_process_record(
                                    worker, expected_worker_argv, Path(sys.executable),
                                    expected_start_ticks=worker_start_ticks,
                                )
                            except Exception:
                                reaped = reap_owned_child_if_exited(worker)
                                if reaped is None:
                                    raise
                                result["canonicalWorkerExitStatus"], result["canonicalWorkerDirectChildRusage"] = reaped
                        if worker.returncode is None and not verify_process_still_owned(
                            worker, worker_record, expected_worker_argv, Path(sys.executable),
                        ):
                            reaped = reap_owned_child_if_exited(worker)
                            if reaped is None:
                                raise ProbeFailure("worker_cleanup_ownership_unverified")
                            result["canonicalWorkerExitStatus"], result["canonicalWorkerDirectChildRusage"] = reaped
                        if worker.returncode is None:
                            runtime._stop_worker(Worker(job, worker))
                cleanup["canonicalWorkerReaped"] = worker.returncode is not None
                if not cleanup["canonicalWorkerReaped"]:
                    retain_private = True
            except Exception as error:
                cleanup["canonicalWorkerReaped"] = worker.returncode is not None
                cleanup["canonicalWorkerCleanupReason"] = str(error) if isinstance(error, ProbeFailure) else type(error).__name__
                if not cleanup["canonicalWorkerReaped"]:
                    retain_private = True
            finally:
                for stream in (worker.stdout, worker.stdin):
                    try:
                        if stream is not None and not stream.closed:
                            stream.close()
                    except OSError:
                        cleanup["workerPipeCloseFailed"] = True
                if runtime is not None:
                    try:
                        runtime._close_memo_channel(worker)
                    except OSError:
                        cleanup["workerMemoCloseFailed"] = True
        else:
            cleanup["canonicalWorkerReaped"] = True

        if runtime is not None:
            try:
                for memo in runtime.image_memos.values():
                    memo.close()
                runtime.selector.close()
            except Exception as error:
                cleanup["runtimeResourceCleanupReason"] = type(error).__name__

        if server is not None:
            try:
                if server.returncode is None:
                    reaped = reap_owned_child_if_exited(server)
                    if reaped is not None:
                        result["fixtureServerExitStatus"], result["fixtureServerDirectChildRusage"] = reaped
                    if server.returncode is None:
                        if expected_server_argv is None or binary is None or server_start_ticks is None:
                            raise ProbeFailure("fixture_server_cleanup_identity_unavailable")
                        if server_record is None:
                            try:
                                server_record = owned_process_record(
                                    server, expected_server_argv, binary,
                                    expected_start_ticks=server_start_ticks,
                                )
                            except Exception:
                                reaped = reap_owned_child_if_exited(server)
                                if reaped is None:
                                    raise
                                result["fixtureServerExitStatus"], result["fixtureServerDirectChildRusage"] = reaped
                        if server.returncode is None:
                            server_exit, server_rusage = stop_owned_server(
                                server, server_record, expected_server_argv, binary,
                            )
                            result["fixtureServerExitStatus"] = server_exit
                            result["fixtureServerDirectChildRusage"] = server_rusage
                cleanup["fixtureServerReaped"] = server.returncode is not None
                if not cleanup["fixtureServerReaped"]:
                    retain_private = True
            except Exception as error:
                cleanup["fixtureServerReaped"] = server.returncode is not None
                cleanup["fixtureServerCleanupReason"] = str(error) if isinstance(error, ProbeFailure) else type(error).__name__
                if not cleanup["fixtureServerReaped"]:
                    retain_private = True
        else:
            cleanup["fixtureServerReaped"] = True

        if stderr_path is not None and cleanup.get("fixtureServerReaped"):
            try:
                result["fixtureServerStderr"] = stderr_digest(stderr_path)
            except Exception as error:
                cleanup["fixtureServerStderrReason"] = str(error) if isinstance(error, ProbeFailure) else type(error).__name__
                retain_private = True
        else:
            result["fixtureServerStderr"] = {"captured": False}

        if endpoint is not None:
            if not cleanup.get("fixtureServerReaped", False):
                cleanup["ownedEndpointRemoved"] = False
                if os.path.lexists(endpoint):
                    cleanup["endpointRetainedReason"] = "process_ownership_or_liveness_unresolved"
            elif os.path.lexists(endpoint):
                try:
                    current = endpoint.lstat()
                    if (
                        endpoint_record is None
                        or current.st_dev != endpoint_record["device"]
                        or current.st_ino != endpoint_record["inode"]
                        or current.st_uid != os.geteuid()
                        or not stat.S_ISSOCK(current.st_mode)
                    ):
                        raise ProbeFailure("endpoint_cleanup_identity_unavailable")
                    endpoint.unlink()
                    cleanup["ownedEndpointRemoved"] = True
                except Exception as error:
                    cleanup["ownedEndpointRemoved"] = False
                    cleanup["endpointCleanupReason"] = str(error) if isinstance(error, ProbeFailure) else type(error).__name__
                    retain_private = True
            else:
                cleanup["ownedEndpointRemoved"] = True
        else:
            cleanup["ownedEndpointRemoved"] = True

        endpoint_absent = endpoint is None or not os.path.lexists(endpoint)
        if endpoint is not None and endpoint_root_stat is not None and endpoint_absent:
            cleanup["endpointDirectoryRemoved"] = cleanup_endpoint_root(endpoint, endpoint_root_stat, created_endpoint_root)
        elif endpoint is not None:
            cleanup["endpointDirectoryRemoved"] = not created_endpoint_root

        processes_reaped = (worker is None or worker.returncode is not None) and (server is None or server.returncode is not None)
        if run_dir is not None and run_dir.exists() and not retain_private and processes_reaped and endpoint_absent:
            try:
                current = run_dir.lstat()
                if (
                    run_dir_identity is None
                    or current.st_dev != run_dir_identity.st_dev
                    or current.st_ino != run_dir_identity.st_ino
                    or current.st_uid != os.geteuid()
                    or not stat.S_ISDIR(current.st_mode)
                ):
                    raise ProbeFailure("private_run_directory_identity_unavailable")
                shutil.rmtree(run_dir)
                cleanup["privateConfigHomeRemoved"] = not run_dir.exists()
            except Exception as error:
                cleanup["privateConfigHomeRemoved"] = False
                cleanup["privateDirectoryCleanupReason"] = str(error) if isinstance(error, ProbeFailure) else type(error).__name__
                retain_private = True
        else:
            cleanup["privateConfigHomeRemoved"] = run_dir is None or not run_dir.exists()
            if run_dir is not None and run_dir.exists():
                cleanup["privateDirectoryRetained"] = True

        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            cleanup["sharedLockReleased"] = True
        except OSError as error:
            cleanup["sharedLockReleased"] = False
            cleanup["sharedLockReleaseReason"] = type(error).__name__
            result["status"] = "failed"

        if retain_private:
            result["status"] = "failed"
            if "failureStage" not in result:
                result["failureStage"] = "cleanup"
                result["failureReason"] = "owned_process_or_endpoint_not_safely_reaped"
        if not all(cleanup.get(key, False) for key in (
            "canonicalWorkerReaped", "fixtureServerReaped", "ownedEndpointRemoved",
            "privateConfigHomeRemoved", "sharedLockReleased",
        )):
            result["status"] = "failed"
        if created_endpoint_root and cleanup.get("endpointDirectoryRemoved") is not True:
            result["status"] = "failed"
        if any(key.endswith("Reason") or key.endswith("Failed") for key in cleanup):
            result["status"] = "failed"
        if result["status"] != "passed" and "failureStage" not in result:
            result["failureStage"] = "cleanup"
            result["failureReason"] = "cleanup_incomplete"

        parent_cpu_ns = sum(
            sum(result.get("components", {}).get(component, {}).get(key, 0) for key in (
                "parentSpawnCpuNs", "parentDrainAndWaitCpuNs", "sourceParserCpuNs",
            ))
            for component in ("runtime", "history")
        )
        worker_cpu_ns = sum(
            sum(result.get("components", {}).get(component, {}).get("workerDirectChildRusage", {}).get(key, 0) for key in ("userCpuNs", "systemCpuNs"))
            for component in ("runtime", "history")
        )
        server_cpu_ns = sum(result.get("fixtureServerDirectChildRusage", {}).get(key, 0) for key in ("userCpuNs", "systemCpuNs"))
        result["accounting"] = {
            "parentMeasuredSlicesCpuNs": parent_cpu_ns,
            "canonicalWorkerDirectChildCpuNs": worker_cpu_ns,
            "fixtureServerDirectChildCpuNsAddedOnce": server_cpu_ns,
            "conservativeComponentPairCpuNs": parent_cpu_ns + worker_cpu_ns + server_cpu_ns,
            "qualification": "controlled runtime/history component-pair accounting; State.accept and the joined service pipeline are excluded",
        }
        if os.path.lexists(output):
            result["status"] = "failed"
            result["receiptWriteReason"] = "receipt_already_exists"
        else:
            try:
                with output.open("x", encoding="utf-8") as stream:
                    stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
                os.chmod(output, 0o600)
            except OSError as error:
                result["status"] = "failed"
                result["receiptWriteReason"] = type(error).__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=tuple(SOURCE_ROOTS), required=True)
    parser.add_argument("--interpreter", choices=tuple(INTERPRETERS), required=True)
    parser.add_argument("--replicate", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    try:
        result = run_trial(args.source, args.replicate, args.interpreter)
    except ProbeFailure as error:
        print(json.dumps({"status": "not_run_or_failed", "reason": str(error)}, sort_keys=True))
        return 75 if str(error) in {"shared_lock_busy", "shared_lock_unavailable"} else 1
    print(json.dumps({key: value for key, value in result.items() if key != "components"}, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
