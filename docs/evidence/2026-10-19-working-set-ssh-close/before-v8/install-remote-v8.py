from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
TARGET = Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-b9e8488e")
BASE_PYTHON = Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0/venv-314/bin/python")
EXPECTED_UID = 1000
EXPECTED_HOST = "80H1VV3"
EXPECTED_BASE_PYTHON_SHA256 = "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
EXPECTED_OBSERVER = "30a4e30b2fdc1f2bb7c6ee8b6cbf2fe16fdf32fbb7b95932b0d8e5c68eef9e5e"
EXPECTED_MESH = "1476da94402168b41e8c296044e1579aa3f9584c011d4eca4cddd0106c6cf802"
EXPECTED_DEPENDENCY_MANIFEST = "c3dc47697bc41205120d33f5dd78081207a2331614e17823d9aa425b5974af61"
EXPECTED_REQUIREMENTS = "10cf830034f0bffea89eaa113f14a54e3481c8c068284a898f8860a1ff41b310"
EXPECTED_FILES = {
    "fixed-ssh-v8/working-set-stdio-fixture-v8.py",
    "fixed-ssh-v8/verify-working-set-close-receipt-v8.py",
    "fixed-ssh-v8/verify-installed-records-v8.py",
    "fixed-ssh-v8/verify-public-surface-v8.py",
    "fixed-ssh-v8/install-remote-v8.py",
    "fixed-ssh-v8/wheels/agent_observer-0.7.0a7-py3-none-any.whl",
    "fixed-ssh-v8/wheels/mesh_plus-0.1.0a23-py3-none-any.whl",
    "fixed-ssh-v8/dependencies/requirements-314.txt",
    "fixed-ssh-v8/dependencies/wheelhouse-manifest.json",
    "fixed-ssh-v8/dependencies/wheels-314/attrs-26.1.0-py3-none-any.whl",
    "fixed-ssh-v8/dependencies/wheels-314/jsonschema-4.26.0-py3-none-any.whl",
    "fixed-ssh-v8/dependencies/wheels-314/jsonschema_specifications-2025.9.1-py3-none-any.whl",
    "fixed-ssh-v8/dependencies/wheels-314/referencing-0.37.0-py3-none-any.whl",
    "fixed-ssh-v8/dependencies/wheels-314/rpds_py-2026.9.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
}
for layout in ("bootstrap/fixtures/tests", "fixture-source/tests"):
    EXPECTED_FILES.update({
        f"fixed-ssh-v8/{layout}/working_set_synthetic_fixture.py",
        f"fixed-ssh-v8/{layout}/test_service_runtime.py",
        f"fixed-ssh-v8/{layout}/test_service_state.py",
        f"fixed-ssh-v8/{layout}/test_service_contract.py",
        f"fixed-ssh-v8/{layout}/fixtures/service-v4/view.json",
    })


class InstallError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition: bool, code: str) -> None:
    if not condition:
        raise InstallError(code)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lstat_regular(path: Path, *, uid: int, mode: int) -> None:
    node = path.lstat()
    need(stat.S_ISREG(node.st_mode) and node.st_uid == uid and stat.S_IMODE(node.st_mode) == mode, "private_payload_file_policy")


def strict_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InstallError("duplicate_json_key")
        out[key] = value
    return out


def run_bounded(argv: list[str], env: dict[str, str], timeout: float, code: str) -> tuple[int, bytes, bytes]:
    try:
        result = subprocess.run(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise InstallError(code + "_timeout") from None
    need(len(result.stdout) <= 131072 and len(result.stderr) <= 131072, code + "_output_limit")
    need(result.returncode == 0, code + "_failed")
    return result.returncode, result.stdout, result.stderr


def verify_base() -> dict:
    need(os.getuid() == EXPECTED_UID and os.uname().nodename == EXPECTED_HOST, "remote_identity")
    st = TARGET.parent.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == EXPECTED_UID and not stat.S_IMODE(st.st_mode) & 0o022, "target_parent_policy")
    base_node = BASE_PYTHON.lstat()
    need(stat.S_ISREG(base_node.st_mode) or stat.S_ISLNK(base_node.st_mode), "base_python_shape")
    resolved_base = BASE_PYTHON.resolve(strict=True)
    need(resolved_base.is_file() and sha(resolved_base) == EXPECTED_BASE_PYTHON_SHA256, "base_python_digest")
    need(os.path.abspath(sys.executable) == str(BASE_PYTHON) and tuple(sys.version_info[:3]) == (3, 14, 8), "base_python_identity")
    need(sha(Path("/proc/self/exe")) == EXPECTED_BASE_PYTHON_SHA256, "base_process_digest")
    base_root = BASE_PYTHON.parents[2]
    base_root_stat = base_root.lstat()
    need(stat.S_ISDIR(base_root_stat.st_mode) and base_root_stat.st_uid == EXPECTED_UID and stat.S_IMODE(base_root_stat.st_mode) == 0o700, "base_root_policy")
    return {"host": os.uname().nodename, "uid": os.getuid(), "pythonVersion": "3.14.8", "baseExecutableSha256": EXPECTED_BASE_PYTHON_SHA256}


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    need(name == path.as_posix() and not path.is_absolute() and all(part not in ("", ".", "..") for part in path.parts), "payload_path_invalid")
    return path


def tighten_venv(path: Path) -> list[dict]:
    links = []
    for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
        base = Path(current)
        for name in list(dirs):
            child = base / name
            node = child.lstat()
            if stat.S_ISLNK(node.st_mode):
                target = os.readlink(child)
                rel = child.relative_to(path).as_posix()
                need(rel == "lib64" and target == "lib" and child.resolve(strict=True).is_relative_to(path.resolve()), "venv_directory_symlink_unexpected")
                links.append({"path": rel, "target": target})
                dirs.remove(name)
            else:
                need(stat.S_ISDIR(node.st_mode) and node.st_uid == EXPECTED_UID, "venv_directory_shape")
                os.chmod(child, 0o700, follow_symlinks=False)
        for name in files:
            child = base / name
            node = child.lstat()
            if stat.S_ISLNK(node.st_mode):
                target = os.readlink(child)
                rel = child.relative_to(path).as_posix()
                need(rel.startswith("bin/") and not target.startswith("/") and ".." not in PurePosixPath(target).parts and child.resolve(strict=True).is_relative_to(path.resolve()), "venv_file_symlink_unexpected")
                links.append({"path": rel, "target": target})
                continue
            need(stat.S_ISREG(node.st_mode) and node.st_uid == EXPECTED_UID, "venv_file_shape")
            os.chmod(child, 0o700 if node.st_mode & 0o111 else 0o600, follow_symlinks=False)
        os.chmod(base, 0o700, follow_symlinks=False)
    return sorted(links, key=lambda x: x["path"])


def write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)


def main() -> int:
    try:
        identity = verify_base()
        target_st = TARGET.lstat()
        need(stat.S_ISDIR(target_st.st_mode) and target_st.st_uid == EXPECTED_UID and stat.S_IMODE(target_st.st_mode) == 0o700, "target_root_policy")
        root_st = ROOT.lstat()
        need(stat.S_ISDIR(root_st.st_mode) and root_st.st_uid == EXPECTED_UID and stat.S_IMODE(root_st.st_mode) == 0o700, "v8_root_policy")
        for current, dirs, _files in os.walk(ROOT, followlinks=False):
            for name in dirs:
                child = Path(current) / name
                node = child.lstat()
                need(stat.S_ISDIR(node.st_mode) and node.st_uid == EXPECTED_UID and stat.S_IMODE(node.st_mode) == 0o700, "payload_directory_policy")
        manifest_path = ROOT / "working-set-fixed-ssh-v8-manifest.json"
        lstat_regular(manifest_path, uid=EXPECTED_UID, mode=0o600)
        manifest = json.loads(manifest_path.read_text(), object_pairs_hook=strict_object)
        need(manifest.get("schema") == "agent-observer.working-set-fixed-ssh-v8-manifest.v1", "manifest_schema")
        need(manifest.get("target", {}).get("packageRoot") == str(TARGET), "manifest_target_mismatch")
        need(manifest.get("source") == {"observerCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0", "meshCommit": "b9e8488e0f0fa438119e36848ac7c9887038ea1c"}, "manifest_source_tuple")
        need(manifest.get("wheels") == {"agent_observer": EXPECTED_OBSERVER, "mesh_plus": EXPECTED_MESH}, "manifest_wheel_tuple")
        need(manifest.get("dependencies", {}).get("manifestSha256") == EXPECTED_DEPENDENCY_MANIFEST and manifest["dependencies"].get("requirementsSha256") == EXPECTED_REQUIREMENTS, "manifest_dependency_pin")
        rows = manifest.get("payloadFiles")
        need(isinstance(rows, list) and len(rows) == len(EXPECTED_FILES), "payload_inventory_shape")
        names = [row.get("path") for row in rows if isinstance(row, dict)]
        need(len(names) == len(rows) and len(set(names)) == len(names) and set(names) == EXPECTED_FILES, "payload_inventory_mismatch")
        for row in rows:
            name = row["path"]
            safe_relative(name)
            path = TARGET / name
            lstat_regular(path, uid=EXPECTED_UID, mode=0o600)
            need(path.stat(follow_symlinks=False).st_size == row.get("bytes") and sha(path) == row.get("sha256"), "payload_hash_mismatch")
        need(sha(ROOT / "install-remote-v8.py") == next(row["sha256"] for row in rows if row["path"] == "fixed-ssh-v8/install-remote-v8.py"), "installer_self_hash_mismatch")
        fixtures = manifest.get("fixtureSources", {})
        copies = manifest.get("fixtureSourceCopies", {})
        need(len(fixtures) == 5 and len(copies) == 5, "fixture_layout_shape")
        for original, expected in fixtures.items():
            copy_name = original.replace("bootstrap/fixtures/tests/", "fixture-source/tests/", 1)
            need(copies.get(copy_name) == expected, "fixture_layout_hash_binding")
            copy_path = ROOT / copy_name
            lstat_regular(copy_path, uid=EXPECTED_UID, mode=0o600)
            need(sha(copy_path) == expected, "fixture_layout_copy_hash_mismatch")
        requirements = ROOT / "dependencies/requirements-314.txt"
        need(sha(requirements) == EXPECTED_REQUIREMENTS, "requirements_hash_mismatch")
        wheelhouse_manifest = ROOT / "dependencies/wheelhouse-manifest.json"
        need(sha(wheelhouse_manifest) == EXPECTED_DEPENDENCY_MANIFEST, "wheelhouse_manifest_hash_mismatch")
        v8manifest = json.loads(wheelhouse_manifest.read_text(), object_pairs_hook=strict_object)
        dependency_rows = v8manifest.get("versions", {}).get("314")
        need(isinstance(dependency_rows, list) and len(dependency_rows) == 5, "dependency_manifest_shape")
        dependency_wheels = ROOT / "dependencies/wheels-314"
        for row in dependency_rows:
            wheel = dependency_wheels / row["wheel"]
            lstat_regular(wheel, uid=EXPECTED_UID, mode=0o600)
            need(wheel.stat(follow_symlinks=False).st_size == row["bytes"] and sha(wheel) == row["sha256"], "dependency_wheel_hash_mismatch")
        observer_wheel = ROOT / "wheels/agent_observer-0.7.0a7-py3-none-any.whl"
        mesh_wheel = ROOT / "wheels/mesh_plus-0.1.0a23-py3-none-any.whl"
        need(sha(observer_wheel) == EXPECTED_OBSERVER and sha(mesh_wheel) == EXPECTED_MESH, "project_wheel_hash_mismatch")
        venv = PACKAGE_ROOT / "venv-314"
        need(not venv.exists() and not venv.is_symlink(), "target_venv_exists")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(ROOT), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PIP_CONFIG_FILE": os.devnull, "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_COMPILE": "1"}
        run_bounded([str(BASE_PYTHON), "-I", "-B", "-m", "venv", "--copies", str(venv)], env, 25, "venv_create")
        python = venv / "bin/python"
        need(python.is_file(), "copied_venv_python_missing")
        dependency_args = [str(python), "-I", "-B", "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--no-cache-dir", "--no-compile", "--find-links", str(dependency_wheels), "--require-hashes", "-r", str(requirements)]
        run_bounded(dependency_args, env, 40, "dependency_install")
        project_args = [str(python), "-I", "-B", "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--no-cache-dir", "--no-deps", "--no-compile", str(observer_wheel), str(mesh_wheel)]
        run_bounded(project_args, env, 40, "project_install")
        _, pip_check, pip_check_stderr = run_bounded([str(python), "-I", "-B", "-m", "pip", "check"], env, 15, "pip_check")
        check_text = pip_check.decode("utf-8", "replace").strip()
        need(check_text == "No broken requirements found." and not pip_check_stderr.strip(), "pip_check_text")
        probe_code = "import hashlib,json,os,sys; from pathlib import Path; p=Path(sys.prefix); x=hashlib.sha256(Path('/proc/self/exe').read_bytes()).hexdigest(); r=str(Path(sys.executable).resolve()); print(json.dumps({'version':'.'.join(map(str,sys.version_info[:3])),'executable':os.path.abspath(sys.executable),'resolvedExecutable':r,'prefix':str(p),'basePrefix':sys.base_prefix,'exeSha256':x},sort_keys=True))"
        _, probe_out, probe_err = run_bounded([str(python), "-I", "-B", "-c", probe_code], env, 10, "venv_identity_probe")
        probe = json.loads(probe_out)
        need(not probe_err and probe.get("version") == "3.14.8" and probe.get("executable") == str(python) and probe.get("prefix") == str(venv) and probe.get("exeSha256") == EXPECTED_BASE_PYTHON_SHA256, "copied_venv_identity")
        need(Path(probe.get("resolvedExecutable", "")).is_relative_to(venv.resolve()), "copied_python_escaped_venv")
        pep610_code = "import importlib.metadata,json; names=('agent-observer','mesh-plus'); print(json.dumps({name: importlib.metadata.distribution(name).read_text('direct_url.json') for name in names},sort_keys=True))"
        _, pep610_out, pep610_err = run_bounded([str(python), "-I", "-B", "-c", pep610_code], env, 10, "pep610_probe")
        need(not pep610_err, "pep610_probe_stderr")
        pep610_rows = json.loads(pep610_out)
        direct_urls = {}
        for distribution, expected_wheel, wheel_name in (("agent-observer", EXPECTED_OBSERVER, observer_wheel.name), ("mesh-plus", EXPECTED_MESH, mesh_wheel.name)):
            raw = pep610_rows.get(distribution)
            need(isinstance(raw, str), "pep610_missing")
            direct = json.loads(raw, object_pairs_hook=strict_object)
            hashes = direct.get("archive_info", {}).get("hashes", {})
            need(hashes.get("sha256") == expected_wheel and direct.get("url", "").endswith("/fixed-ssh-v8/wheels/" + wheel_name), "pep610_source_mismatch")
            direct_urls[distribution] = {"wheelSha256": hashes["sha256"], "wheelName": wheel_name}
        record_script = ROOT / "verify-installed-records-v8.py"
        surface_script = ROOT / "verify-public-surface-v8.py"
        _, record_out, record_err = run_bounded([str(python), "-I", "-B", str(record_script)], env, 20, "record_verify")
        record_result = json.loads(record_out)
        need(not record_err and record_result.get("status") == "pass", "record_verify_result")
        _, surface_out, surface_err = run_bounded([str(python), "-I", "-B", str(surface_script)], env, 20, "public_surface_verify")
        surface_result = json.loads(surface_out)
        need(not surface_err and surface_result.get("status") == "pass" and surface_result.get("descriptorExact") is True and surface_result.get("schemaCanonicalMatches") is True, "public_surface_result")
        links = tighten_venv(venv)
        result = {
            "schema": "agent-observer.working-set-fixed-ssh-v8-bootstrap.v1",
            "status": "pass",
            "host": EXPECTED_HOST,
            "uid": EXPECTED_UID,
            "packageRoot": str(TARGET),
            "privateRootMode": "0700",
            "payloadHashesExact": True,
            "venv": {"copyMode": True, "version": probe["version"], "lexicalEntrypoint": probe["executable"], "prefix": probe["prefix"], "resolvedExecutable": probe["resolvedExecutable"], "resolvedExecutableSha256": probe["exeSha256"], "internalGeneratedLinks": links},
            "offlineDependencies": {"noIndex": True, "requireHashes": True, "requirementsSha256": EXPECTED_REQUIREMENTS, "wheelhouseManifestSha256": EXPECTED_DEPENDENCY_MANIFEST, "pipCheck": "pass"},
            "projectWheels": {"installMode": "no-deps", "sha256": {"agent_observer": EXPECTED_OBSERVER, "mesh_plus": EXPECTED_MESH}, "pep610": direct_urls},
            "installedRecordCheck": record_result,
            "installedPublicSurface": surface_result,
            "source": manifest["source"],
            "coverageLimits": ["fresh private copied 3.14.8 venv and exact offline wheels; no source build or network package lookup", "schema, descriptor, CLI argument parsing, PEP 610, installed RECORD and pip dependency checks only; no service IPC or provider/native call"],
        }
        receipt = ROOT / "working-set-fixed-ssh-v8-bootstrap.json"
        write_exclusive(receipt, (json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
        print(json.dumps({"schema": result["schema"], "status": "pass", "host": EXPECTED_HOST, "uid": EXPECTED_UID, "wheelHashesExact": True, "pipCheck": "pass", "recordCheck": "pass", "publicSurface": "pass", "receipt": str(receipt)}, sort_keys=True))
        return 0
    except InstallError as error:
        print(json.dumps({"schema": "agent-observer.working-set-fixed-ssh-v8-bootstrap.v1", "status": "failed", "reasonCode": error.code}, sort_keys=True))
        return 1
    except BaseException:
        print(json.dumps({"schema": "agent-observer.working-set-fixed-ssh-v8-bootstrap.v1", "status": "failed", "reasonCode": "bootstrap_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
