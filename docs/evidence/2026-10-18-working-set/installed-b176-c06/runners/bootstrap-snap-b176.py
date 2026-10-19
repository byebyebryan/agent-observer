#!/usr/bin/env python3
"""Offline, private Snap bootstrap and installed-pair verifier.

Run only with the pinned old private 3.14 interpreter after the separate
checksum-bound transfer has populated the target root. This script never starts
an Observer service, provider worker, native RPC, or user-facing client.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
import sysconfig
import zipfile
from email import message_from_bytes
from pathlib import Path
from urllib.parse import unquote, urlsplit

SCHEMA = "agent-observer.private-snap-installed-bootstrap.v1"
EXPECTED_HOST = "80H1VV3"
EXPECTED_UID = 1000
EXPECTED_VERSION = (3, 14, 8)
EXPECTED_BOOTSTRAP_PREFIX = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/"
    "installed-pair-196a8e2b-c06b33e0/venv-314"
)
EXPECTED_ROOT = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/"
    "installed-pair-b176ac06-c06b33e0"
)
EXPECTED_EXE_SHA256 = "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
SELF_RELATIVE = "bootstrap/bootstrap-snap-b176.py"
VENVS_RELATIVE = "venv-314"
MAX_FILES = 32
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PROCESS_OUTPUT = 64 * 1024
MAX_SAVED_DIAGNOSTIC = 8 * 1024
PROCESS_TIMEOUT_SECONDS = 90

OBSERVER_WHEEL = "agent_observer-0.7.0a7-py3-none-any.whl"
MESH_WHEEL = "mesh_plus-0.1.0a23-py3-none-any.whl"
OBSERVER_WHEEL_SHA256 = "30a4e30b2fdc1f2bb7c6ee8b6cbf2fe16fdf32fbb7b95932b0d8e5c68eef9e5e"
MESH_WHEEL_SHA256 = "287d98c9d16f492a3df43a391b2036f98760c805480a74a7f93b3fcd2d8cf14a"

DEPENDENCIES = {
    "attrs": {
        "version": "26.1.0",
        "wheel": "attrs-26.1.0-py3-none-any.whl",
        "sha256": "c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309",
    },
    "jsonschema": {
        "version": "4.26.0",
        "wheel": "jsonschema-4.26.0-py3-none-any.whl",
        "sha256": "d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce",
    },
    "jsonschema-specifications": {
        "version": "2025.9.1",
        "wheel": "jsonschema_specifications-2025.9.1-py3-none-any.whl",
        "sha256": "98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe",
    },
    "referencing": {
        "version": "0.37.0",
        "wheel": "referencing-0.37.0-py3-none-any.whl",
        "sha256": "381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231",
    },
    "rpds-py": {
        "version": "2026.9.1",
        "wheel": (
            "rpds_py-2026.9.1-cp314-cp314-manylinux_2_17_x86_64."
            "manylinux2014_x86_64.whl"
        ),
        "sha256": "eac2f5dbafd585dfe31f86a23ebf0d3ba480a9d49ebc87947267b5608d4ea0cd",
    },
}
APP_DISTRIBUTIONS = {
    "agent-observer": {
        "version": "0.7.0a7",
        "wheel": OBSERVER_WHEEL,
        "sha256": OBSERVER_WHEEL_SHA256,
        "package": "agent_observer",
        "entrypoint": "agent-observer",
    },
    "mesh-plus": {
        "version": "0.1.0a23",
        "wheel": MESH_WHEEL,
        "sha256": MESH_WHEEL_SHA256,
        "package": "mesh_plus",
        "entrypoint": "mesh-plus",
    },
}
SCHEMA_PINS = {
    "frame": (
        "mesh_plus/schemas/agent-working-set-native.schema.json",
        "a87b9661f3436a5894056e94f9b061ae84ecd9c78110d759e9e7d54b70956b95",
    ),
    "request": (
        "mesh_plus/schemas/agent-working-set-request.schema.json",
        "4f9b3f83ce00aab688830a7b452d476111abf26d52aca608548da8aba2318aeb",
    ),
}
EXPECTED_DESCRIPTOR = {
    "profile": "agent-observer.mesh-working-set.v1",
    "digest": "sha256:8b1ab6d4d37c007867c3a005341f58b9b60705f7e65fb0ae86df316638b543e9",
    "sdk": 1,
    "protocol": "agent-observer.working-set",
    "nativeVersion": 1,
    "frameBytes": 8404992,
}

ARTIFACT_PINS = {
    "wheels/" + OBSERVER_WHEEL: OBSERVER_WHEEL_SHA256,
    "wheels/" + MESH_WHEEL: MESH_WHEEL_SHA256,
    **{
        "dependency-wheels-314/" + details["wheel"]: details["sha256"]
        for details in DEPENDENCIES.values()
    },
    "dependency-requirements-314.txt":
        "10cf830034f0bffea89eaa113f14a54e3481c8c068284a898f8860a1ff41b310",
    "package-wheel-requirements.txt":
        "e976f99eefab978d0f01299e26a72f34472f2fa3179e1775fbf4d46616ba8a2b",
    "bootstrap/fixtures/tests/test_service_contract.py":
        "78c340327e737b7cbe66457604a59b0212bb6dcde3cfaf1416fb97b9e9334d18",
    "bootstrap/fixtures/tests/test_service_state.py":
        "e2538cbafa0718774a034b9e4d92980b32c617d3bca4b38da0f021f805b71742",
    "bootstrap/fixtures/tests/test_service_runtime.py":
        "35275647a577f7220bdc205bfe5e31b2017fd7caf5d8cfa64b139aa5dd4853a1",
    "bootstrap/fixtures/tests/fixtures/service-v4/view.json":
        "f657b8847142bbf36084c12527d83d31919a71205b5c5ffc271a424cdf0770a5",
    "bootstrap/fixtures/tests/working_set_synthetic_fixture.py":
        "afa4f4bb4c1a5ac95a7a22f0621046c5954b8aa86d9c8e5ed19109bd621114c6",
}
SOURCE_GIT_BLOBS = {
    "bootstrap/fixtures/tests/test_service_contract.py": "da20ab81719a946a680b52f325b254315bb306e0",
    "bootstrap/fixtures/tests/test_service_state.py": "e82509b947581056c4290a7c5104aee92d26ca54",
    "bootstrap/fixtures/tests/test_service_runtime.py": "c905c0b08f3e42ab4a435c30d0e6116e693ef2e1",
    "bootstrap/fixtures/tests/fixtures/service-v4/view.json": "63e9b31862a4c54da58ae68bcaa4d7fc4ae582d6",
}
ALLOWED_BOOTSTRAP_TOOLS = {"pip", "setuptools"}
PRIMARY_ARTIFACT_PINS = {
    "working-set-stdio-fixture-v5.py":
        "14e3ea24eafaca769cde41ff58bea2d1d1da2d57bb9958927b8324d869cc743c",
    "verify-working-set-close-receipt-v5.py":
        "71eebca3c799d6c767e1272534a8ac5582dce8ae9d7c4378d8202794dbd70afd",
    "run-working-set-fixed-ssh-v5.py":
        "5bc1997d21c9f557848b9c89b63c1bb20df28c468b8a0eef493ccb44116dc985",
}

class BootstrapError(Exception):
    def __init__(self, code: str, stage: str):
        super().__init__(code)
        self.code = code
        self.stage = stage


def fail(code: str, stage: str) -> None:
    raise BootstrapError(code, stage)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _private_file(path: Path, uid: int, *, expected_sha: str | None = None,
                  max_bytes: int = MAX_FILE_BYTES) -> bytes:
    try:
        before = path.lstat()
    except OSError:
        fail("artifact_missing", "artifact_read")
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
            or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
            or before.st_size < 0 or before.st_size > max_bytes):
        fail("artifact_file_policy", "artifact_read")
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        )
        try:
            actual = os.fstat(descriptor)
            if (not stat.S_ISREG(actual.st_mode) or actual.st_uid != uid
                    or actual.st_dev != before.st_dev or actual.st_ino != before.st_ino
                    or actual.st_size != before.st_size):
                fail("artifact_file_raced", "artifact_read")
            chunks = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
        finally:
            os.close(descriptor)
    except BootstrapError:
        raise
    except OSError:
        fail("artifact_read_failed", "artifact_read")
    if len(data) != before.st_size or len(data) > max_bytes:
        fail("artifact_size_changed", "artifact_read")
    if expected_sha is not None and sha256(data) != expected_sha:
        fail("artifact_digest_mismatch", "artifact_read")
    return data


def _owned_directory(path: Path, uid: int, mode: int = 0o700) -> None:
    try:
        info = path.lstat()
    except OSError:
        fail("private_directory_missing", "directory_policy")
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid
            or stat.S_IMODE(info.st_mode) != mode):
        fail("private_directory_policy", "directory_policy")


def _check_identity() -> dict:
    if os.getuid() != EXPECTED_UID or os.geteuid() != EXPECTED_UID:
        fail("snap_uid_mismatch", "identity")
    try:
        node = os.uname().nodename
    except OSError:
        fail("snap_host_identity_unavailable", "identity")
    if node != EXPECTED_HOST:
        fail("snap_host_mismatch", "identity")
    if tuple(sys.version_info[:3]) != EXPECTED_VERSION:
        fail("bootstrap_python_version_mismatch", "identity")
    lexical = Path(sys.executable).absolute()
    expected_lexical = EXPECTED_BOOTSTRAP_PREFIX / "bin" / "python"
    if lexical != expected_lexical or Path(sys.prefix).resolve() != EXPECTED_BOOTSTRAP_PREFIX:
        fail("bootstrap_venv_identity_mismatch", "identity")
    if not getattr(sys, "dont_write_bytecode", False):
        fail("bootstrap_bytecode_policy", "identity")
    try:
        proc_executable = Path("/proc/self/exe").read_bytes()
        base = Path(getattr(sys, "_base_executable", ""))
        base_resolved = base.resolve(strict=True)
        base_bytes = base_resolved.read_bytes()
    except (OSError, RuntimeError):
        fail("bootstrap_executable_unavailable", "identity")
    if sha256(proc_executable) != EXPECTED_EXE_SHA256:
        fail("bootstrap_executable_digest_mismatch", "identity")
    if sha256(base_bytes) != EXPECTED_EXE_SHA256:
        fail("bootstrap_base_executable_digest_mismatch", "identity")
    return {
        "host": node,
        "uid": os.getuid(),
        "pythonVersion": ".".join(map(str, sys.version_info[:3])),
        "lexicalInterpreter": str(lexical),
        "sysPrefix": str(Path(sys.prefix).resolve()),
        "baseExecutable": str(base),
        "resolvedBaseExecutable": str(base_resolved),
        "resolvedBaseExecutableSha256": sha256(base_bytes),
        "processExecutableSha256": sha256(proc_executable),
    }


def _check_root() -> None:
    try:
        info = EXPECTED_ROOT.lstat()
        resolved = EXPECTED_ROOT.resolve(strict=True)
    except OSError:
        fail("target_root_unavailable", "root_policy")
    if (resolved != EXPECTED_ROOT or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != EXPECTED_UID or stat.S_IMODE(info.st_mode) != 0o700):
        fail("target_root_policy", "root_policy")
    if not Path(__file__).is_file() or Path(__file__).is_symlink():
        fail("bootstrap_script_path_invalid", "root_policy")
    script = Path(__file__).absolute()
    if script != EXPECTED_ROOT / SELF_RELATIVE:
        fail("bootstrap_script_path_mismatch", "root_policy")
    try:
        script_info = script.lstat()
    except OSError:
        fail("bootstrap_script_unavailable", "root_policy")
    if (not stat.S_ISREG(script_info.st_mode) or script_info.st_uid != EXPECTED_UID
            or stat.S_IMODE(script_info.st_mode) != 0o600):
        fail("bootstrap_script_policy", "root_policy")


def _required_directories() -> list[str]:
    return [
        "wheels",
        "dependency-wheels-314",
        "bootstrap",
        "bootstrap/fixtures",
        "bootstrap/fixtures/tests",
        "bootstrap/fixtures/tests/fixtures",
        "bootstrap/fixtures/tests/fixtures/service-v4",
    ]


def _verify_artifact_tree() -> dict:
    for relative in _required_directories():
        _owned_directory(EXPECTED_ROOT / relative, EXPECTED_UID)
    all_pins = ARTIFACT_PINS | PRIMARY_ARTIFACT_PINS
    expected_names = set(all_pins) | {SELF_RELATIVE}
    found_names = set()
    found_directories = set()
    for base, dirs, filenames in os.walk(EXPECTED_ROOT, followlinks=False):
        base_path = Path(base)
        for name in list(dirs):
            path = base_path / name
            try:
                info = path.lstat()
            except OSError:
                fail("artifact_directory_raced", "artifact_tree")
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                fail("artifact_tree_contains_link_or_special", "artifact_tree")
            if info.st_uid != EXPECTED_UID or stat.S_IMODE(info.st_mode) != 0o700:
                fail("artifact_directory_policy", "artifact_tree")
            found_directories.add(path.relative_to(EXPECTED_ROOT).as_posix())
        for name in filenames:
            path = base_path / name
            try:
                rel = path.relative_to(EXPECTED_ROOT).as_posix()
            except ValueError:
                fail("artifact_path_outside_root", "artifact_tree")
            if rel not in expected_names:
                fail("unexpected_target_artifact", "artifact_tree")
            found_names.add(rel)
    if not expected_names <= found_names:
        fail("artifact_set_incomplete", "artifact_tree")
    if found_directories != set(_required_directories()):
        fail("artifact_directory_set_mismatch", "artifact_tree")
    total_bytes = 0
    rows = {}
    for relative, expected in sorted(all_pins.items()):
        data = _private_file(EXPECTED_ROOT / relative, EXPECTED_UID,
                             expected_sha=expected)
        total_bytes += len(data)
        git_blob = SOURCE_GIT_BLOBS.get(relative)
        if git_blob is not None:
            object_header = f"blob {len(data)}\0".encode("ascii")
            if hashlib.sha1(object_header + data).hexdigest() != git_blob:
                fail("source_fixture_git_blob_mismatch", "artifact_tree")
        rows[relative] = {"sha256": expected, "bytes": len(data)}
    primary_rows = {
        relative: rows[relative] for relative in sorted(PRIMARY_ARTIFACT_PINS)
    }
    script_data = _private_file(
        EXPECTED_ROOT / SELF_RELATIVE, EXPECTED_UID, max_bytes=MAX_FILE_BYTES
    )
    total_bytes += len(script_data)
    file_count = len(found_names)
    if file_count > MAX_FILES or total_bytes > MAX_TOTAL_BYTES:
        fail("transfer_packet_budget_exceeded", "artifact_tree")
    return {
        "fileCountIncludingBootstrap": file_count,
        "inputFileCount": len(ARTIFACT_PINS),
        "totalBytesIncludingBootstrap": total_bytes,
        "sha256ByRelativePath": rows,
        "primaryOwnedArtifacts": primary_rows,
        "bootstrapScriptBytes": len(script_data),
        "bootstrapScriptSha256": sha256(script_data),
        "sourceFixtureGitBlobsVerified": len(SOURCE_GIT_BLOBS),
    }


def _path_absent(path: Path, stage: str, code: str) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        fail(code, stage)
    fail(code, stage)


def _write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    if len(data) > MAX_TOTAL_BYTES:
        fail("output_limit_exceeded", "receipt")
    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            mode,
        )
        try:
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except BootstrapError:
        raise
    except OSError:
        fail("exclusive_output_write_failed", "receipt")


def _safe_diagnostic(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        text = data[:MAX_PROCESS_OUTPUT].decode("utf-8", "replace")
    else:
        text = data[:MAX_PROCESS_OUTPUT]
    text = re.sub(r"(?i)(https?://)[^/\s:@]+:[^/@\s]+@", r"\1[redacted]@", text)
    text = re.sub(
        r"(?i)\b(password|token|authorization|credential)\s*[:=]\s*[^\s]+",
        r"\1=[redacted]",
        text,
    )
    text = "".join(char for char in text if char in "\n\r\t" or ord(char) >= 0x20)
    return text.encode("utf-8", "replace")[:MAX_SAVED_DIAGNOSTIC]


def _save_setup_diagnostics(stage: str, stdout: bytes, stderr: bytes) -> list[str]:
    names = []
    for stream_name, value in (("stdout", stdout), ("stderr", stderr)):
        name = f"bootstrap-{stage}-{stream_name}.txt"
        path = EXPECTED_ROOT / "bootstrap" / name
        _write_exclusive(path, _safe_diagnostic(value))
        names.append(f"bootstrap/{name}")
    return names


def _safe_environment(tmp: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(EXPECTED_ROOT),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "TMPDIR": str(tmp),
    }


def _run(argv: list[str], *, cwd: Path, env: dict[str, str],
         timeout: int = PROCESS_TIMEOUT_SECONDS) -> tuple[int, bytes, bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            umask=0o022,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        if isinstance(stdout, str):
            stdout = stdout.encode("utf-8", "replace")
        if isinstance(stderr, str):
            stderr = stderr.encode("utf-8", "replace")
        return 124, stdout[:MAX_PROCESS_OUTPUT], stderr[:MAX_PROCESS_OUTPUT]


def _pip_step(label: str, argv: list[str], *, cwd: Path,
              env: dict[str, str]) -> dict:
    return_code, stdout, stderr = _run(argv, cwd=cwd, env=env)
    if len(stdout) > MAX_PROCESS_OUTPUT or len(stderr) > MAX_PROCESS_OUTPUT:
        diagnostics = _save_setup_diagnostics(label, stdout, stderr)
        raise BootstrapError("pip_output_limit", f"pip_{label}").with_traceback(None)
    if return_code != 0:
        diagnostics = _save_setup_diagnostics(label, stdout, stderr)
        raise BootstrapError(f"pip_{label}_failed", f"pip_{label}")
    return {
        "exitCode": return_code,
        "stdoutBytes": len(stdout),
        "stderrBytes": len(stderr),
        "stdoutSha256": sha256(stdout),
        "stderrSha256": sha256(stderr),
        "diagnosticFilesOnFailureOnly": True,
    }


def _venv_step(argv: list[str], *, cwd: Path, env: dict[str, str]) -> dict:
    return_code, stdout, stderr = _run(argv, cwd=cwd, env=env)
    if len(stdout) > MAX_PROCESS_OUTPUT or len(stderr) > MAX_PROCESS_OUTPUT:
        _save_setup_diagnostics("venv-create", stdout, stderr)
        fail("venv_create_output_limit", "venv_create")
    if return_code != 0:
        _save_setup_diagnostics("venv-create", stdout, stderr)
        fail("venv_create_failed", "venv_create")
    return {
        "exitCode": return_code,
        "stdoutBytes": len(stdout),
        "stderrBytes": len(stderr),
        "stdoutSha256": sha256(stdout),
        "stderrSha256": sha256(stderr),
    }


def _distribution_report(python: Path, env: dict[str, str],
                         purelib: Path) -> dict:
    code = r'''import hashlib, importlib.metadata, json, os, re, sys, sysconfig
from pathlib import Path
def canonical(name): return re.sub(r"[-_.]+", "-", name).lower()
def digest(data): return hashlib.sha256(data).hexdigest()
purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
prefix = Path(sys.prefix).resolve()
exe = Path(sys.executable).absolute()
base_executable = Path(getattr(sys, "_base_executable", sys.executable))
base_resolved = base_executable.resolve()
try:
    base_bytes = base_resolved.read_bytes()
except OSError:
    raise SystemExit("base_executable_unavailable")
if exe != prefix / "bin" / "python":
    raise SystemExit("lexical_interpreter_mismatch")
if prefix not in purelib.parents:
    raise SystemExit("site_packages_outside_venv")
if sys.version_info[:3] != (3, 14, 8):
    raise SystemExit("installed_python_version_mismatch")
if not sys.flags.no_user_site:
    raise SystemExit("user_site_enabled")
import agent_observer, mesh_plus
from mesh_plus.api import descriptor
for module in (agent_observer, mesh_plus):
    origin = Path(module.__file__).resolve()
    if prefix not in origin.parents:
        raise SystemExit("module_root_mismatch")
d = descriptor("agent", profile_id="agent-observer.mesh-working-set.v1")
details = {
    "profile": d.profile_id,
    "digest": d.contract_digest,
    "sdk": d.sdk_version,
    "protocol": d.native_protocol,
    "nativeVersion": d.native_version,
    "frameBytes": d.frame_bytes,
}
rows = {}
for dist in importlib.metadata.distributions():
    name = dist.metadata.get("Name") or "unknown"
    key = canonical(name)
    if key in rows:
        raise SystemExit("duplicate_distribution")
    version = dist.version
    location = Path(dist.locate_file("")).resolve()
    if prefix not in location.parents and location != purelib:
        raise SystemExit("distribution_outside_venv")
    record = dist.read_text("RECORD")
    if record is None:
        raise SystemExit("distribution_record_missing")
    direct_text = dist.read_text("direct_url.json")
    direct_kind = "none"
    direct_hash = None
    direct_path = None
    if direct_text is not None:
        direct = json.loads(direct_text)
        archive = direct.get("archive_info")
        if isinstance(archive, dict):
            direct_kind = "archive"
            candidates = []
            legacy = archive.get("hash")
            if isinstance(legacy, str) and legacy.startswith("sha256="):
                candidates.append(legacy.split("=", 1)[1])
            hashes = archive.get("hashes")
            if isinstance(hashes, dict) and isinstance(hashes.get("sha256"), str):
                candidates.append(hashes["sha256"])
            if candidates and any(value != candidates[0] for value in candidates):
                raise SystemExit("direct_url_hash_disagreement")
            direct_hash = candidates[0] if candidates else None
            direct_path = direct.get("url")
        elif isinstance(direct.get("dir_info"), dict):
            direct_kind = "directory"
        else:
            direct_kind = "other"
    rows[key] = {
        "name": name,
        "version": version,
        "recordSha256": digest(record.encode()),
        "recordEntryCount": len(dist.files or ()),
        "directURLKind": direct_kind,
        "directURLSha256": direct_hash,
        "directURL": direct_path,
    }
print(json.dumps({
    "pythonVersion": ".".join(map(str, sys.version_info[:3])),
    "lexicalInterpreter": str(exe),
    "resolvedInterpreter": str(exe.resolve()),
    "sysPrefix": str(prefix),
    "sysBasePrefix": str(Path(sys.base_prefix).resolve()),
    "baseExecutable": str(base_executable),
    "resolvedBaseExecutable": str(base_resolved),
    "resolvedBaseExecutableSha256": digest(base_bytes),
    "purelib": str(purelib),
    "userSiteDisabled": bool(sys.flags.no_user_site),
    "moduleRootsPrivate": True,
    "descriptor": details,
    "distributions": rows,
}, sort_keys=True))'''
    code_result, stdout, stderr = _run(
        [str(python), "-I", "-B", "-c", code],
        cwd=EXPECTED_ROOT,
        env=env,
        timeout=30,
    )
    if code_result != 0 or len(stdout) > MAX_PROCESS_OUTPUT or len(stderr) > MAX_PROCESS_OUTPUT:
        fail("installed_distribution_probe_failed", "installed_inventory")
    try:
        result = json.loads(stdout)
    except (TypeError, ValueError):
        fail("installed_distribution_probe_invalid", "installed_inventory")
    if result.get("purelib") != str(purelib.resolve()):
        fail("installed_site_packages_mismatch", "installed_inventory")
    if result.get("descriptor") != EXPECTED_DESCRIPTOR:
        fail("installed_descriptor_mismatch", "installed_inventory")
    if result.get("moduleRootsPrivate") is not True or result.get("userSiteDisabled") is not True:
        fail("installed_module_root_policy", "installed_inventory")
    return result


def _wheel_package_files(wheel_path: Path, package: str) -> dict[str, str]:
    prefix = package + "/"
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            names = [name for name in archive.namelist()
                     if name.startswith(prefix) and not name.endswith("/")]
            if not names:
                fail("wheel_package_tree_missing", "wheel_inventory")
            return {
                name[len(prefix):]: sha256(archive.read(name))
                for name in names
            }
    except BootstrapError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError):
        fail("wheel_package_archive_invalid", "wheel_inventory")


def _installed_package_files(package_root: Path) -> dict[str, str]:
    try:
        root_info = package_root.lstat()
    except OSError:
        fail("installed_package_missing", "wheel_inventory")
    if (not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode)
            or root_info.st_uid != EXPECTED_UID):
        fail("installed_package_directory_policy", "wheel_inventory")
    result = {}
    for base, dirs, filenames in os.walk(package_root, followlinks=False):
        base_path = Path(base)
        for directory in list(dirs):
            path = base_path / directory
            try:
                info = path.lstat()
            except OSError:
                fail("installed_package_tree_raced", "wheel_inventory")
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                fail("installed_package_tree_has_link", "wheel_inventory")
            if info.st_uid != EXPECTED_UID:
                fail("installed_package_tree_owner", "wheel_inventory")
        for filename in filenames:
            path = base_path / filename
            relative = path.relative_to(package_root).as_posix()
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            try:
                data = _private_or_installed_file(path, EXPECTED_UID)
            except BootstrapError:
                raise
            result[relative] = sha256(data)
    return result


def _private_or_installed_file(path: Path, uid: int) -> bytes:
    try:
        info = path.lstat()
    except OSError:
        fail("installed_package_file_missing", "wheel_inventory")
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != uid:
        fail("installed_package_file_policy", "wheel_inventory")
    if info.st_size < 0 or info.st_size > 2 * 1024 * 1024:
        fail("installed_package_file_size", "wheel_inventory")
    try:
        return path.read_bytes()
    except OSError:
        fail("installed_package_file_read", "wheel_inventory")


def _validate_distributions(inventory: dict, purelib: Path) -> dict:
    expected = {}
    for name, details in APP_DISTRIBUTIONS.items():
        expected[canonical_name(name)] = {
            "version": details["version"],
            "sha256": details["sha256"],
            "origin": "app_wheel_pep610",
        }
    for name, details in DEPENDENCIES.items():
        expected[canonical_name(name)] = {
            "version": details["version"],
            "sha256": details["sha256"],
            "origin": "hash_required_find_links_wheelhouse",
        }
    dist_rows = inventory.get("distributions")
    if not isinstance(dist_rows, dict):
        fail("distribution_inventory_shape", "distribution_validation")
    if not set(expected) <= set(dist_rows):
        fail("required_distribution_missing", "distribution_validation")
    extras = set(dist_rows) - set(expected) - ALLOWED_BOOTSTRAP_TOOLS
    if extras:
        fail("unexpected_distribution_inventory", "distribution_validation")
    report_rows = {}
    for key, details in expected.items():
        row = dist_rows.get(key)
        if not isinstance(row, dict) or row.get("version") != details["version"]:
            fail("required_distribution_version_mismatch", "distribution_validation")
        direct_kind = row.get("directURLKind")
        direct_hash = row.get("directURLSha256")
        if direct_kind in ("directory", "other"):
            fail("nonwheel_distribution_origin", "distribution_validation")
        if direct_kind == "archive" and direct_hash != details["sha256"]:
            fail("distribution_direct_url_digest_mismatch", "distribution_validation")
        if details["origin"] == "app_wheel_pep610":
            if direct_kind != "archive" or direct_hash != details["sha256"]:
                fail("app_wheel_pep610_provenance_mismatch", "distribution_validation")
            parsed = urlsplit(row.get("directURL") or "")
            if parsed.scheme != "file":
                fail("app_wheel_direct_url_not_local", "distribution_validation")
            direct_path = Path(unquote(parsed.path))
            expected_path = EXPECTED_ROOT / "wheels" / (
                APP_DISTRIBUTIONS[key]["wheel"]
            )
            if direct_path.resolve(strict=True) != expected_path.resolve(strict=True):
                fail("app_wheel_direct_url_path_mismatch", "distribution_validation")
        elif direct_kind == "none":
            pass
        report_rows[key] = {
            "version": row["version"],
            "recordSha256": row["recordSha256"],
            "recordEntryCount": row["recordEntryCount"],
            "directURLKind": direct_kind,
            "directURLSha256": direct_hash,
            "wheelInputSha256": details["sha256"],
            "wheelProvenance": (
                "pep610_archive" if direct_kind == "archive" else details["origin"]
            ),
        }
    for name in sorted(set(dist_rows) & ALLOWED_BOOTSTRAP_TOOLS):
        row = dist_rows[name]
        report_rows[name] = {
            "version": row.get("version"),
            "recordSha256": row.get("recordSha256"),
            "recordEntryCount": row.get("recordEntryCount"),
            "directURLKind": row.get("directURLKind"),
            "directURLSha256": row.get("directURLSha256"),
            "tooling": "private_venv_bootstrap",
        }
    if len(report_rows) != len(dist_rows):
        fail("distribution_inventory_not_fully_reported", "distribution_validation")
    return report_rows


def _verify_cli(python: Path, env: dict[str, str]) -> dict:
    rows = {}
    for name in ("agent-observer", "agent-observer-service", "mesh-plus"):
        path = EXPECTED_ROOT / VENVS_RELATIVE / "bin" / name
        try:
            info = path.lstat()
        except OSError:
            fail("installed_cli_missing", "cli_validation")
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != EXPECTED_UID
                or not (stat.S_IMODE(info.st_mode) & 0o111)):
            fail("installed_cli_ownership_or_mode", "cli_validation")
        try:
            body = path.read_bytes()
        except OSError:
            fail("installed_cli_read_failed", "cli_validation")
        if len(body) > 256 * 1024 or not body.startswith(f"#!{python}\n".encode()):
            fail("installed_cli_shebang_mismatch", "cli_validation")
        code, stdout, stderr = _run(
            [str(path), "--help"], cwd=EXPECTED_ROOT,
            env=env, timeout=20,
        )
        if code != 0 or len(stdout) > MAX_PROCESS_OUTPUT or len(stderr) > MAX_PROCESS_OUTPUT:
            fail("installed_cli_help_failed", "cli_validation")
        if b"usage:" not in stdout.lower():
            fail("installed_cli_help_shape", "cli_validation")
        rows[name] = {
            "ownerUid": info.st_uid,
            "mode": stat.S_IMODE(info.st_mode),
            "sha256": sha256(body),
            "shebangExact": True,
            "helpExitCode": code,
            "helpBytes": len(stdout),
            "helpSha256": sha256(stdout),
        }
    return rows


def _verify_schema_cli(env: dict[str, str], mesh_wheel: Path) -> dict:
    cli = EXPECTED_ROOT / VENVS_RELATIVE / "bin" / "agent-observer"
    report = {}
    try:
        with zipfile.ZipFile(mesh_wheel) as archive:
            for kind, (schema_path, raw_sha) in SCHEMA_PINS.items():
                raw_schema = archive.read(schema_path)
                if sha256(raw_schema) != raw_sha:
                    fail("mesh_schema_wheel_pin_mismatch", "schema_validation")
                expected_value = json.loads(raw_schema)
                code, stdout, stderr = _run(
                    [str(cli), "service", "working-set-schema", "--kind", kind],
                    cwd=EXPECTED_ROOT,
                    env=env,
                    timeout=20,
                )
                if code != 0 or len(stdout) > MAX_PROCESS_OUTPUT or len(stderr) > MAX_PROCESS_OUTPUT:
                    fail("observer_schema_cli_failed", "schema_validation")
                try:
                    actual_value = json.loads(stdout)
                except (TypeError, ValueError):
                    fail("observer_schema_cli_invalid_json", "schema_validation")
                actual_canonical = canonical(actual_value)
                expected_canonical = canonical(expected_value)
                if actual_canonical != expected_canonical:
                    fail("observer_mesh_schema_canonical_mismatch", "schema_validation")
                report[kind] = {
                    "canonicalMatch": True,
                    "observerCommandBytes": len(stdout),
                    "observerCommandCanonicalSha256": sha256(actual_canonical),
                    "meshWheelRawSha256": raw_sha,
                }
    except BootstrapError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError, ValueError):
        fail("schema_wheel_validation_failed", "schema_validation")
    return report


def _make_exclusive_receipt(report: dict) -> None:
    data = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(data) > 64 * 1024:
        fail("receipt_size_limit", "receipt")
    _write_exclusive(EXPECTED_ROOT / "bootstrap" / "bootstrap-receipt.json", data)


def _failure_receipt(error: BootstrapError, diagnostics: list[str]) -> None:
    report = {
        "schema": SCHEMA,
        "status": "failed",
        "reasonCode": error.code,
        "stage": error.stage,
        "diagnosticFiles": diagnostics,
        "noNativeOrServiceActions": True,
    }
    try:
        _make_exclusive_receipt(report)
    except BootstrapError:
        pass


def main() -> int:
    diagnostics: list[str] = []
    trusted_root = False
    try:
        if len(sys.argv) != 1:
            fail("unexpected_arguments", "startup")
        identity = _check_identity()
        _check_root()
        trusted_root = True
        _path_absent(EXPECTED_ROOT / VENVS_RELATIVE, "venv_precondition", "candidate_venv_preexisting")
        _path_absent(EXPECTED_ROOT / ".tmp", "tmp_precondition", "private_tmp_preexisting")
        _path_absent(EXPECTED_ROOT / "bootstrap" / "bootstrap-receipt.json",
                     "receipt_precondition", "bootstrap_receipt_preexisting")
        for name in (
            "bootstrap-venv-create-stdout.txt",
            "bootstrap-venv-create-stderr.txt",
            "bootstrap-dependencies-stdout.txt",
            "bootstrap-dependencies-stderr.txt",
            "bootstrap-app-wheels-stdout.txt",
            "bootstrap-app-wheels-stderr.txt",
        ):
            _path_absent(EXPECTED_ROOT / "bootstrap" / name,
                         "diagnostic_precondition", "bootstrap_diagnostic_preexisting")
        artifacts = _verify_artifact_tree()
        tmp = EXPECTED_ROOT / ".tmp"
        tmp.mkdir(mode=0o700)
        _owned_directory(tmp, EXPECTED_UID)
        env = _safe_environment(tmp)
        venv_path = EXPECTED_ROOT / VENVS_RELATIVE
        create_result = _venv_step(
            [str(Path(sys.executable).absolute()), "-m", "venv", "--copies", str(venv_path)],
            cwd=EXPECTED_ROOT,
            env=env,
        )
        try:
            venv_info = venv_path.lstat()
        except OSError:
            fail("candidate_venv_creation_missing", "venv_create")
        if (not stat.S_ISDIR(venv_info.st_mode) or venv_info.st_uid != EXPECTED_UID):
            fail("candidate_venv_directory_policy", "venv_create")
        python = venv_path / "bin" / "python"
        try:
            python_info = python.lstat()
            resolved_python = python.resolve(strict=True)
            python_bytes = resolved_python.read_bytes()
        except OSError:
            fail("candidate_interpreter_unavailable", "venv_create")
        if (not stat.S_ISREG(python_info.st_mode) or stat.S_ISLNK(python_info.st_mode)
                or python_info.st_uid != EXPECTED_UID
                or sha256(python_bytes) != EXPECTED_EXE_SHA256):
            fail("candidate_interpreter_copy_mismatch", "venv_create")
        purelib = (venv_path / "lib" / "python3.14" / "site-packages")
        if not purelib.is_dir():
            fail("candidate_site_packages_missing", "venv_create")
        _owned_directory(purelib.parent, EXPECTED_UID, mode=0o755)
        _owned_directory(purelib, EXPECTED_UID, mode=0o755)
        pip = [str(python), "-B", "-m", "pip", "install",
               "--disable-pip-version-check", "--no-input", "--no-index",
               "--no-deps", "--require-hashes"]
        dep_req = EXPECTED_ROOT / "dependency-requirements-314.txt"
        dep_wheels = EXPECTED_ROOT / "dependency-wheels-314"
        dep_result = _pip_step(
            "dependencies",
            pip + ["--find-links", str(dep_wheels), "-r", str(dep_req)],
            cwd=EXPECTED_ROOT,
            env=env,
        )
        app_req = EXPECTED_ROOT / "package-wheel-requirements.txt"
        app_result = _pip_step(
            "app-wheels",
            pip + ["-r", str(app_req)],
            cwd=EXPECTED_ROOT,
            env=env,
        )
        wheel_paths = {
            "agent-observer": EXPECTED_ROOT / "wheels" / OBSERVER_WHEEL,
            "mesh-plus": EXPECTED_ROOT / "wheels" / MESH_WHEEL,
        }
        package_reports = {}
        for distribution, details in APP_DISTRIBUTIONS.items():
            expected_files = _wheel_package_files(
                wheel_paths[distribution], details["package"]
            )
            installed_files = _installed_package_files(
                purelib / details["package"]
            )
            if expected_files != installed_files:
                fail("installed_package_bytes_mismatch", "wheel_inventory")
            package_reports[distribution] = {
                "version": details["version"],
                "wheelSha256": details["sha256"],
                "fileCount": len(installed_files),
                "packageInventoryExact": True,
                "packageInventorySha256": sha256(canonical(sorted(installed_files.items()))),
            }
        inventory = _distribution_report(python, env, purelib)
        distribution_rows = _validate_distributions(inventory, purelib)
        cli_report = _verify_cli(python, env)
        schema_report = _verify_schema_cli(env, wheel_paths["mesh-plus"])
        if inventory.get("descriptor") != EXPECTED_DESCRIPTOR:
            fail("installed_descriptor_mismatch", "descriptor_validation")
        if inventory.get("pythonVersion") != "3.14.8":
            fail("installed_python_version_mismatch", "descriptor_validation")
        base_resolved = Path(inventory["resolvedBaseExecutable"]).resolve(strict=True)
        base_bytes = base_resolved.read_bytes()
        if sha256(base_bytes) != EXPECTED_EXE_SHA256:
            fail("installed_base_executable_mismatch", "descriptor_validation")
        report = {
            "schema": SCHEMA,
            "status": "pass",
            "host": identity["host"],
            "uid": identity["uid"],
            "source": {
                "observerCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0",
                "meshCommit": "c06b33e058339d9d1d89ecf6844044867d816c58",
                "observerWheelSha256": OBSERVER_WHEEL_SHA256,
                "meshWheelSha256": MESH_WHEEL_SHA256,
            },
            "bootstrapInterpreter": identity,
            "installedInterpreter": {
                "pythonVersion": inventory["pythonVersion"],
                "lexicalInterpreter": inventory["lexicalInterpreter"],
                "resolvedInterpreter": inventory["resolvedInterpreter"],
                "resolvedInterpreterSha256": sha256(python_bytes),
                "sysPrefix": inventory["sysPrefix"],
                "sysBasePrefix": inventory["sysBasePrefix"],
                "baseExecutable": inventory["baseExecutable"],
                "resolvedBaseExecutable": inventory["resolvedBaseExecutable"],
                "resolvedBaseExecutableSha256": inventory["resolvedBaseExecutableSha256"],
                "purelib": inventory["purelib"],
                "userSiteDisabled": inventory["userSiteDisabled"],
                "moduleRootsPrivate": inventory["moduleRootsPrivate"],
            },
            "artifacts": artifacts,
            "packageInventories": package_reports,
            "sourceFixtureGitBlobsVerified": artifacts["sourceFixtureGitBlobsVerified"],
            "primaryOwnedArtifacts": artifacts["primaryOwnedArtifacts"],
            "distributions": distribution_rows,
            "pipInstall": {
                "dependencies": dep_result,
                "appWheels": app_result,
                "networkDisabled": True,
                "noIndex": True,
                "requireHashes": True,
                "cacheDisabled": True,
            },
            "clis": cli_report,
            "descriptor": inventory["descriptor"],
            "workingSetSchemas": schema_report,
            "coverageLimits": [
                "private wheel installation and static public CLI/schema/descriptor checks only",
                "no Observer Runtime, service socket, IPC, provider worker, or native RPC was started",
                "dependency wheel provenance is hash-required private find-links input; PEP 610 is recorded where pip supplies it",
                "source fixture files are staged for a later synthetic transport gate and were not executed here",
            ],
        }
        _make_exclusive_receipt(report)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "pass",
            "pythonVersion": report["installedInterpreter"]["pythonVersion"],
            "distributionCount": len(distribution_rows),
            "installedPackageCount": len(package_reports),
            "schemaKindsCompared": sorted(schema_report),
            "receipt": str(EXPECTED_ROOT / "bootstrap" / "bootstrap-receipt.json"),
        }, sort_keys=True))
        return 0
    except BootstrapError as error:
        if trusted_root:
            for name in (
                "bootstrap-venv-create-stdout.txt",
                "bootstrap-venv-create-stderr.txt",
                "bootstrap-dependencies-stdout.txt",
                "bootstrap-dependencies-stderr.txt",
                "bootstrap-app-wheels-stdout.txt",
                "bootstrap-app-wheels-stderr.txt",
            ):
                path = EXPECTED_ROOT / "bootstrap" / name
                try:
                    info = path.lstat()
                except OSError:
                    continue
                if stat.S_ISREG(info.st_mode) and info.st_uid == EXPECTED_UID:
                    diagnostics.append(f"bootstrap/{name}")
            _failure_receipt(error, diagnostics)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "failed",
            "reasonCode": error.code,
            "stage": error.stage,
        }, sort_keys=True))
        return 1
    except Exception:
        error = BootstrapError("bootstrap_unexpected_failure", "internal")
        if trusted_root:
            _failure_receipt(error, diagnostics)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "failed",
            "reasonCode": error.code,
            "stage": error.stage,
        }, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
