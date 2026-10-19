from __future__ import annotations

import asyncio
import gc
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import stat
import sys
import sysconfig
import time
import zipfile
from pathlib import Path

PACKAGE_ROOT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69")
ROOT = PACKAGE_ROOT / "fixed-ssh-v9"
TESTS = ROOT / "bootstrap" / "fixtures" / "tests"
SNAP_ROOT = "/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69"
SNAP_V9_ROOT = SNAP_ROOT + "/fixed-ssh-v9"
SNAP_VENV = SNAP_ROOT + "/venv-314"
SNAP_FIXTURE = SNAP_V9_ROOT + "/working-set-stdio-fixture-v9.py"
SNAP_CLOSE_CHECKER = SNAP_V9_ROOT + "/verify-working-set-close-receipt-v9.py"
PLAN_PATH = Path("/home/bryan/.cache/agent-observer-working-set-20261018/fixed-ssh-b176-bfa91a69-plan-v9/fixed-ssh-v9-plan.json")
SNAP_EXECUTABLE_SHA256 = "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
OBSERVER_WHEEL_SHA256 = "30a4e30b2fdc1f2bb7c6ee8b6cbf2fe16fdf32fbb7b95932b0d8e5c68eef9e5e"
MESH_WHEEL_SHA256 = "9522a60535766d8310acfa5db5b38400a2dd519276bd3d2344eeb65584ca8f62"
SSH_OPTIONS = [
    "-T",
    "-oBatchMode=yes",
    "-oStrictHostKeyChecking=yes",
    "-oProxyJump=none",
    "-oProxyCommand=none",
    "-oConnectTimeout=5",
    "-oConnectionAttempts=1",
    "-oClearAllForwardings=yes",
    "-oForwardAgent=no",
    "-oRequestTTY=no",
    "-oControlMaster=no",
    "-oControlPath=none",
]
HOST = "fixture"
SOURCE = "working_set_fixture"
WINDOW_MS = 72 * 60 * 60 * 1000
REVISION = "sha256:" + "b" * 64
PROFILE_ID = "agent-observer.mesh-working-set.v1"
PROFILE_DIGEST = "sha256:8b1ab6d4d37c007867c3a005341f58b9b60705f7e65fb0ae86df316638b543e9"


REMOTE_PREFLIGHT_SOURCE = 'import hashlib,json,os,stat,sys\nfrom pathlib import Path\nTARGET=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69")\nV9=TARGET/"fixed-ssh-v9"\nBASE=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0/venv-314/bin/python")\nEXPECTED_BASE="375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"\ndef h(p):\n x=hashlib.sha256()\n with p.open("rb") as f:\n  for b in iter(lambda:f.read(1048576),b""): x.update(b)\n return x.hexdigest()\ndef need(v,c):\n if not v: raise ValueError(c)\ntry:\n need(os.getuid()==1000 and os.uname().nodename=="80H1VV3","remote_identity")\n need(os.path.abspath(sys.executable)==str(TARGET/"venv-314/bin/python") and sys.prefix==str(TARGET/"venv-314") and tuple(sys.version_info[:3])==(3,14,8),"private_python")\n need(h(Path("/proc/self/exe"))==EXPECTED_BASE,"private_executable")\n for p in (TARGET,V9):\n  s=p.lstat(); need(stat.S_ISDIR(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o700,"private_root")\n m=json.loads(sys.stdin.buffer.read(65536))\n need(m["schema"]=="agent-observer.working-set-fixed-ssh-v9-manifest.v1","manifest_schema")\n need(m["source"]=={"observerCommit":"b176ac06b39daeead4be0a33ff9d781304091fe0","meshCommit":"bfa91a6936a089d37c1a83752d3267148ba7dc69"},"source_tuple")\n for name,row in m["artifacts"].items():\n  p=V9/name; s=p.lstat(); need(stat.S_ISREG(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o600 and s.st_size==row["bytes"] and h(p)==row["sha256"],"artifact_pin")\n for name,want in m["fixtureSources"].items():\n  p=V9/name; s=p.lstat(); need(stat.S_ISREG(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o600 and h(p)==want,"fixture_source_pin")\n for name,want in m["wheels"].items():\n  filename="agent_observer-0.7.0a7-py3-none-any.whl" if name=="agent_observer" else "mesh_plus-0.1.0a23-py3-none-any.whl"\n  p=V9/"wheels"/filename; s=p.lstat(); need(stat.S_ISREG(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o600 and h(p)==want,"wheel_pin")\n for rel in ("working-set-fixed-ssh-v9-bootstrap.json","working-set-fixed-ssh-v9-public-surface.json","installed-records-v9-314.json"):\n  p=V9/rel; s=p.lstat(); need(stat.S_ISREG(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o600,"install_receipt_missing")\n bootstrap=json.loads((V9/"working-set-fixed-ssh-v9-bootstrap.json").read_text())\n need(bootstrap.get("schema")=="agent-observer.working-set-fixed-ssh-v9-bootstrap.v1" and bootstrap.get("status")=="pass","bootstrap_not_passed")\n close=V9/"working-set-fixed-ssh-close-receipt-v9.json"\n need(not close.exists() and not close.is_symlink(),"close_receipt_exists")\n print(json.dumps({"schema":"agent-observer.working-set-fixed-ssh-v9-preflight.v1","status":"pass","hostAlias":"snap","hostKeyPolicy":"strict","remoteHost":"80H1VV3","uid":1000,"privateRootMode":"0700","venvVersion":"3.14.8","privateExecutableSha256":EXPECTED_BASE,"wheelHashesExact":True,"sourceFilesExact":True,"offlineInstallVerified":True,"receiptAbsentBeforeRun":True},sort_keys=True))\nexcept Exception:\n print(json.dumps({"schema":"agent-observer.working-set-fixed-ssh-v9-preflight.v1","status":"failed","reasonCode":"remote_preflight_failed"},sort_keys=True))\n raise SystemExit(1) from None\n'

class QualificationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise QualificationError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def boot_ms():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


def reader_clock():
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def proc_start_ticks(pid):
    raw = Path(f"/proc/{pid}/stat").read_text()
    tail = raw[raw.rfind(")") + 2 :].split()
    require(len(tail) > 19, "ssh_process_stat_unavailable")
    return int(tail[19])


def loaded_module_wheel_check(prefix):
    purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
    require(prefix.resolve() in purelib.parents, "candidate_site_packages_mismatch")
    wheels = {
        "agent_observer": ROOT / "wheels" / "agent_observer-0.7.0a7-py3-none-any.whl",
        "mesh_plus": ROOT / "wheels" / "mesh_plus-0.1.0a23-py3-none-any.whl",
    }
    wheel_entries = {}
    wheel_sha = {}
    for package, wheel in wheels.items():
        wheel_sha[package] = digest_file(wheel)
        with zipfile.ZipFile(wheel) as archive:
            wheel_entries[package] = {
                name[len(package) + 1 :]: archive.read(name)
                for name in archive.namelist()
                if name.startswith(package + "/") and not name.endswith("/")
            }
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(("agent_observer", "mesh_plus")):
            continue
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue
        path = Path(origin).resolve()
        require(path.is_relative_to(purelib), "installed_module_shadowed")
        package = "agent_observer" if name.startswith("agent_observer") else "mesh_plus"
        if path.suffix == ".pyc":
            try:
                path = Path(importlib.util.source_from_cache(str(path)))
            except (ValueError, NotImplementedError):
                raise QualificationError("installed_bytecode_origin_unknown") from None
        relative = path.relative_to(purelib).as_posix().split("/", 1)[1]
        expected = wheel_entries[package].get(relative)
        require(expected is not None and digest_file(path) == digest(expected), "loaded_module_wheel_bytes_mismatch")
        modules[name] = str(path)
    require(any(name == "agent_observer" for name in modules), "observer_package_not_loaded")
    require(any(name == "mesh_plus" for name in modules), "mesh_package_not_loaded")
    return {
        "observerModuleCount": sum(name.startswith("agent_observer") for name in modules),
        "meshModuleCount": sum(name.startswith("mesh_plus") for name in modules),
        "loadedModulesUnderPrivateVenvAndWheelExact": True,
        "wheelSha256": wheel_sha,
    }


def fixture_markers(channel):
    markers = []
    prefix = b"AO_WORKING_SET_FIXTURE "
    for line in bytes(channel.stderr_tail).splitlines():
        if not line.startswith(prefix):
            continue
        try:
            value = json.loads(line[len(prefix) :])
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if value.get("schema") == "agent-observer.working-set-stdio-fixture.v9":
            markers.append(value)
    return markers


async def wait_ready(channel, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for item in fixture_markers(channel):
            if item.get("event") == "READY":
                return item
        process = channel.process
        if process is None or process.returncode is not None:
            raise QualificationError("remote_fixture_exited_before_ready")
        await asyncio.sleep(0.025)
    raise QualificationError("remote_fixture_ready_timeout")


async def verify_remote_preflight(ssh_path, manifest):
    source = REMOTE_PREFLIGHT_SOURCE
    command = shlex.join([SNAP_VENV + "/bin/python", "-I", "-B", "-c", source])
    process = await asyncio.create_subprocess_exec(ssh_path, *SSH_OPTIONS, "--", "snap", command,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(json.dumps(manifest).encode()), timeout=15)
    except BaseException:
        if process.returncode is None:
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except BaseException:
            if process.returncode is None:
                process.kill()
            await asyncio.gather(process.wait(), return_exceptions=True)
        raise QualificationError("private_artifact_preflight_timeout") from None
    require(process.returncode == 0 and len(stdout) <= 4096, "private_artifact_preflight_failed")
    try:
        value = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise QualificationError("private_artifact_preflight_output_invalid") from None
    require(isinstance(value, dict) and value.get("schema") == "agent-observer.working-set-fixed-ssh-v9-preflight.v1" and value.get("status") == "pass", "private_artifact_preflight_unverified")
    require(value.get("uid") == 1000 and value.get("remoteHost") == "80H1VV3" and value.get("offlineInstallVerified") is True, "remote_identity_unverified")
    value["sshCommandSha256"] = digest(command.encode())
    value["sshExitCode"] = process.returncode
    value["connectAttempts"] = 1
    return value


def write_private_json_exclusive(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)


async def read_remote_cleanup(ssh_path):
    command = shlex.join([SNAP_VENV + "/bin/python", "-B", SNAP_CLOSE_CHECKER])
    argv = [ssh_path, *SSH_OPTIONS, "--", "snap", command]
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=8)
    except BaseException:
        if process.returncode is None:
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except BaseException:
            if process.returncode is None:
                process.kill()
            await asyncio.gather(process.wait(), return_exceptions=True)
        return {"status": "failed", "reasonCode": "remote_cleanup_check_timeout", "exitCode": process.returncode}
    if len(stdout) > 8192:
        return {"status": "failed", "reasonCode": "remote_cleanup_check_output_limit", "exitCode": process.returncode}
    try:
        value = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "failed", "reasonCode": "remote_cleanup_check_output_invalid", "exitCode": process.returncode}
    if not isinstance(value, dict) or value.get("schema") != "agent-observer.working-set-fixed-ssh-close-check.v9":
        return {"status": "failed", "reasonCode": "remote_cleanup_check_schema", "exitCode": process.returncode}
    if process.returncode != 0 or value.get("status") != "pass":
        return {"status": "failed", "reasonCode": value.get("reasonCode", "remote_cleanup_check_failed"), "exitCode": process.returncode}
    value["sshCommandSha256"] = digest(command.encode())
    value["sshExitCode"] = process.returncode
    value["connectAttempts"] = 1
    return value


async def run():
    gc.disable()
    local_gc_disabled_before_project_imports = not gc.isenabled()
    require(local_gc_disabled_before_project_imports, "local_gc_not_disabled")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONNOUSERSITE"] = "1"
    require(Path(os.path.abspath(sys.prefix)) == Path(os.path.abspath(PACKAGE_ROOT / "venv-314")), "candidate_venv_prefix_mismatch")
    require(tuple(sys.version_info[:3]) == (3, 14, 8), "candidate_python_version_mismatch")
    require(Path(os.path.abspath(sys.executable)) == Path(os.path.abspath(PACKAGE_ROOT / "venv-314" / "bin" / "python")), "candidate_python_entrypoint_mismatch")
    root_stat = ROOT.stat(follow_symlinks=False)
    require(root_stat.st_uid == os.getuid() and root_stat.st_mode & 0o777 == 0o700, "local_private_root_policy")
    require(all(Path(value or "/tmp").resolve() != (PACKAGE_ROOT / "source-observer").resolve() for value in sys.path), "source_package_root_on_sys_path")
    manifest_path = ROOT / "working-set-fixed-ssh-v9-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "agent-observer.working-set-fixed-ssh-v9-manifest.v1", "v9_manifest_schema")
    required_artifacts = {"working-set-stdio-fixture-v9.py", "verify-working-set-close-receipt-v9.py", "verify-installed-records-v9.py", "verify-public-surface-v9.py", "install-remote-v9.py"}
    require(set(manifest.get("artifacts", {})) == required_artifacts, "v9_manifest_artifact_set")
    for name, record in manifest["artifacts"].items():
        require(digest_file(ROOT / name) == record.get("sha256"), "v9_artifact_pin_mismatch")
        require((ROOT / name).stat(follow_symlinks=False).st_mode & 0o777 == 0o600, "v9_artifact_mode")
    require(manifest.get("source", {}).get("observerCommit") == "b176ac06b39daeead4be0a33ff9d781304091fe0" and manifest.get("source", {}).get("meshCommit") == "bfa91a6936a089d37c1a83752d3267148ba7dc69", "v9_source_pin")
    require(manifest.get("wheels") == {"agent_observer": OBSERVER_WHEEL_SHA256, "mesh_plus": MESH_WHEEL_SHA256}, "v9_wheel_pin")
    require(manifest.get("windowMs") == WINDOW_MS and manifest.get("sshOptions") == SSH_OPTIONS, "v9_route_or_window_pin")
    require(manifest.get("gcDisabledBeforeProjectImports") is True, "v9_gc_policy_pin")
    require(manifest.get("localInterpreter", {}).get("version") == "3.14.8" and manifest.get("localInterpreter", {}).get("lexicalEntrypoint") == os.path.abspath(sys.executable) and manifest.get("localInterpreter", {}).get("prefix") == os.path.abspath(sys.prefix) and manifest.get("localInterpreter", {}).get("resolvedExecutableSha256") == digest_file(Path(sys.executable).resolve()), "v9_local_interpreter_pin")
    expected_fixture_sources = {"bootstrap/fixtures/tests/working_set_synthetic_fixture.py", "bootstrap/fixtures/tests/test_service_runtime.py", "bootstrap/fixtures/tests/test_service_state.py", "bootstrap/fixtures/tests/test_service_contract.py", "bootstrap/fixtures/tests/fixtures/service-v4/view.json"}
    require(set(manifest.get("fixtureSources", {})) == expected_fixture_sources, "v9_fixture_source_set")
    for name, expected_hash in manifest.get("fixtureSources", {}).items():
        require(digest_file(ROOT / name) == expected_hash, "v9_fixture_source_pin")
    expected_fixture_copies = {name.replace("bootstrap/fixtures/tests/", "fixture-source/tests/", 1) for name in expected_fixture_sources}
    require(set(manifest.get("fixtureSourceCopies", {})) == expected_fixture_copies, "v9_fixture_copy_set")
    for name, expected_hash in manifest.get("fixtureSourceCopies", {}).items():
        require(digest_file(ROOT / name) == expected_hash, "v9_fixture_copy_pin")
    require(manifest_path.stat(follow_symlinks=False).st_mode & 0o777 == 0o600, "v9_manifest_mode")
    for name in ("working-set-fixed-ssh-v9-preclose.json", "working-set-fixed-ssh-v9-diagnostic.json", "working-set-fixed-ssh-reader-v9.json", "working-set-fixed-ssh-reader-v9-failure.json", "working-set-fixed-ssh-close-receipt-v9.json"):
        require(not (ROOT / name).exists() and not (ROOT / name).is_symlink(), "v9_output_collision")
    require(not gc.isenabled(), "local_gc_reenabled_before_imports")
    sys.path.insert(0, str(TESTS))
    sys.dont_write_bytecode = True
    require(not gc.isenabled(), "local_gc_enabled_at_import")

    from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
    from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch
    from mesh_plus.api import Client, Endpoint
    from mesh_plus.reader import Reader
    from mesh_plus.transport import subprocess_channel
    from working_set_synthetic_fixture import build_fixture, identity_hash


    state, sample, expected = build_fixture()
    expected_hashes = sorted(expected)
    require(len(expected_hashes) == 2, "independent_expected_selection_shape")
    require(WINDOW_MS == 259_200_000, "working_set_window_not_72h")
    profile = WorkingSetAgentProfile(WINDOW_MS)
    require(profile.descriptor.profile_id == PROFILE_ID and profile.descriptor.contract_digest == PROFILE_DIGEST, "candidate_profile_binding_mismatch")
    codec = profile.bind(HOST, SOURCE)

    ssh_path = shutil.which("ssh")
    require(ssh_path is not None and Path(ssh_path).is_absolute(), "ssh_executable_unavailable")
    ssh_path = str(Path(ssh_path).resolve(strict=True))
    command = shlex.join([
        "env",
        f"PYTHONPATH={SNAP_V9_ROOT}/fixture-source/tests",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONNOUSERSITE=1",
        f"{SNAP_VENV}/bin/python",
        "-B",
        SNAP_FIXTURE,
    ])
    command_sha = digest(command.encode())
    ssh_executable_sha = digest_file(ssh_path)
    transfer_check = await verify_remote_preflight(ssh_path, manifest)
    channels = []
    ready = None
    process_identity = None
    connect_attempts = 0

    async def connect():
        nonlocal ready, process_identity, connect_attempts
        connect_attempts += 1
        require(connect_attempts == 1, "unexpected_remote_fixture_restart")
        argv = [ssh_path, *SSH_OPTIONS, "--", "snap", command]
        channel = await subprocess_channel(argv)
        channels.append(channel)
        process = channel.process
        require(process is not None and process.pid > 0, "ssh_process_missing")
        try:
            proc_exe = Path(f"/proc/{process.pid}/exe")
            executable_path = os.readlink(proc_exe)
            executable_hash = digest_file(proc_exe)
            start_ticks = proc_start_ticks(process.pid)
        except OSError:
            raise QualificationError("ssh_process_identity_unavailable") from None
        require(Path(executable_path).resolve() == Path(ssh_path), "ssh_process_executable_mismatch")
        process_identity = {
            "pid": process.pid,
            "startTicks": start_ticks,
            "executablePath": executable_path,
            "executableSha256": executable_hash,
        }
        ready = await wait_ready(channel)
        require(ready.get("host") == HOST and ready.get("source") == SOURCE, "remote_fixture_binding_mismatch")
        require(ready.get("runtimeCollect") is False and ready.get("runtimeSocketReady") is True, "remote_fixture_runtime_not_isolated")
        require(ready.get("gcDisabledBeforeProjectImports") is True, "remote_gc_not_disabled_before_imports")
        require(ready.get("configMode") == "0600" and ready.get("windowMs") == WINDOW_MS, "remote_fixture_config_or_window_mismatch")
        require(ready.get("sourceRows") == 4 and ready.get("expectedSelectedCount") == 2, "remote_fixture_selection_shape_mismatch")
        require(sorted(ready.get("expectedIdentityHashes", [])) == expected_hashes, "remote_fixture_seed_identity_mismatch")
        require(type(ready.get("sourceSampleWallMs")) is int and ready["sourceSampleWallMs"] > 0, "remote_fixture_sample_clock_missing")
        return await Client.connect(channel, host=HOST, source=SOURCE, profile=PROFILE_ID, codec=codec.validate_bridge)

    reader = Reader(
        "agent",
        [Endpoint(HOST, False, REVISION, connect, codec)],
        local_host="starship",
        catalog_revision=REVISION,
        catalog_check=lambda: asyncio.sleep(0, result=REVISION),
        profile=profile,
    )
    request_id = "a" * 32
    stream = reader.watch_admitted(request_id=request_id, proof_interval=0.1, catalog_interval=0.1)
    facade = PreparedWorkingSetAgentWatch(request_id, profile=profile, window_ms=WINDOW_MS)
    nonces = set()
    frame_count = 0
    stream_kinds = {}
    baseline_snapshot_observed = False
    membership_ok = False
    activity_age_checks = 0
    coverage_status = None
    uncertain_count = None
    expected_by_hash = expected
    actual_hashes = []
    actual_detail_checks = 0
    failure = None
    reader_metrics = None
    close_result = {"activeConnectionsZero": False, "streamClosed": False, "channelsClosed": False}
    remote_closed = None
    ssh_return_code = None
    receipt_check = None
    preclose = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            frame = await asyncio.wait_for(anext(stream), timeout=4)
            frame_count += 1
            if isinstance(frame, dict):
                kind = frame.get("mesh", {}).get("kind", "control")
                stream_kinds[kind] = stream_kinds.get(kind, 0) + 1
            facade.accept(frame)
            snapshot = facade.snapshot()
            if snapshot is None:
                continue
            hosts = snapshot.get("mesh", {}).get("hosts", [])
            if len(hosts) != 1:
                continue
            host = hosts[0]
            proof = host.get("delivery", {}).get("proof")
            if isinstance(proof, dict) and isinstance(proof.get("nonce"), str):
                nonces.add(proof["nonce"])
            if host.get("delivery", {}).get("status") != "ready" or host.get("owner") is None:
                continue
            snapshot_mesh = snapshot.get("mesh")
            if isinstance(snapshot_mesh, dict) and snapshot_mesh.get("kind") == "view":
                baseline_snapshot_observed = True
            result = facade.read(boot_ms(), reader_clock())
            coverage_status = result.scopes[0]["coverage"]["status"] if result.scopes else None
            uncertain_count = len(result.uncertain)
            actual_hashes = sorted(identity_hash(row) for row in result.members)
            require(len(actual_hashes) == len(set(actual_hashes)), "duplicate_selected_dto_identity")
            actual_details = {}
            sample_wall = ready["sourceSampleWallMs"]
            for row in result.members:
                row_hash = identity_hash(row)
                age = sample_wall - row["activity"]["at"] if type(row.get("activity", {}).get("at")) is int else None
                actual_details[row_hash] = {
                    "kind": row.get("kind"),
                    "runtime": row.get("runtime", {}).get("value"),
                    "activityAgeMs": age,
                }
            if actual_hashes != expected_hashes:
                raise QualificationError("working_set_membership_mismatch")
            require(actual_details == expected_by_hash, "working_set_dto_field_mismatch")
            actual_detail_checks = len(actual_details)
            activity_age_checks = sum(type(row["activityAgeMs"]) is int for row in actual_details.values())
            require(coverage_status == "complete" and uncertain_count == 0, "working_set_scope_not_complete")
            membership_ok = True
            if len(nonces) >= 2:
                break
        else:
            raise QualificationError("two_remote_proofs_not_observed")
        require(ready is not None, "remote_fixture_ready_missing")
        require(len(nonces) >= 2, "two_remote_proofs_not_observed")
        require(membership_ok and actual_hashes == expected_hashes, "working_set_membership_mismatch")
        require(baseline_snapshot_observed, "baseline_subscription_snapshot_missing")
        require(activity_age_checks == len(expected_hashes), "activity_age_checks_incomplete")
        require(frame_count > 0, "reader_frames_missing")
        preclose_metrics = reader.inspect()
        preclose_operations = (preclose_metrics or {}).get("operations", {})
        preclose_proof_requests = preclose_operations.get("proofRequests", 0)
        require(preclose_proof_requests >= 2, "reader_proof_request_count_low_before_close")
        preclose = {
            "schema": "agent-observer.working-set-fixed-ssh-v9-preclose.v1",
            "phase": "functional_checks_complete_before_sdk_close",
            "functionalChecksComplete": True,
            "frames": frame_count,
            "proofNonceCount": len(nonces),
            "proofRequests": preclose_proof_requests,
            "baselineSubscriptionSnapshotObserved": baseline_snapshot_observed,
            "coverage": coverage_status,
            "uncertainCount": uncertain_count,
            "membershipExact": membership_ok,
            "dtoFieldChecks": actual_detail_checks,
            "activityAgeChecks": activity_age_checks,
            "expectedSelectedCount": len(expected_hashes),
            "actualSelectedCount": len(actual_hashes),
            "gcDisabledBeforeProjectImports": local_gc_disabled_before_project_imports,
        }
        write_private_json_exclusive(ROOT / "working-set-fixed-ssh-v9-preclose.json", preclose)
    except QualificationError as error:
        failure = error.code
    except TimeoutError:
        failure = "reader_frame_timeout"
    except BaseException:
        failure = "working_set_ssh_reader_failed"
    finally:
        facade.disconnect()
        try:
            await asyncio.wait_for(stream.aclose(), timeout=8)
            close_result["streamClosed"] = True
        except BaseException:
            close_result["streamClosed"] = False
        try:
            reader_metrics = reader.inspect()
            close_result["activeConnectionsZero"] = reader_metrics.get("activeConnections") == 0
        except BaseException:
            reader_metrics = None
        for channel in channels:
            try:
                if not channel.closed:
                    await asyncio.wait_for(channel.close(), timeout=4)
                process = channel.process
                if process is not None and process.returncode is None:
                    await asyncio.wait_for(process.wait(), timeout=4)
                close_result["channelsClosed"] = close_result["channelsClosed"] or (channel.closed and process is not None and process.returncode is not None)
                if process is not None:
                    ssh_return_code = process.returncode
                for item in fixture_markers(channel):
                    if item.get("event") == "CLOSED":
                        remote_closed = item
            except BaseException:
                close_result["channelsClosed"] = False

    if connect_attempts == 1:
        receipt_check = await read_remote_cleanup(ssh_path)
    modules = loaded_module_wheel_check(PACKAGE_ROOT / "venv-314")
    runtime_facts = {
        "pythonVersion": ".".join(map(str, sys.version_info[:3])),
        "pythonEntrypoint": str(Path(os.path.abspath(sys.executable))),
        "basePrefix": str(Path(sys.base_prefix).resolve()),
        "resolvedExecutable": str(Path(sys.executable).resolve()),
        "resolvedExecutableSha256": digest_file(Path(sys.executable).resolve()),
    }
    diagnostic = {
        "schema": "agent-observer.working-set-fixed-ssh-diagnostic.v9",
        "failure": failure,
        "readyObserved": ready is not None,
        "remoteClosed": None if remote_closed is None else {
            key: remote_closed.get(key)
            for key in ("status", "reasonCode", "exitPath", "caughtSignal", "runtimeThreadStopped",
                        "runtimePeerCount", "runtimeSelectorClosed", "runtimeSocketAbsent",
                        "privateConfigAbsent", "sourceCleanupComplete")
        },
        "receiptCheck": None if receipt_check is None else {
            key: receipt_check.get(key)
            for key in ("status", "reasonCode", "exitPath", "caughtSignal")
        },
        "sshExitCode": ssh_return_code,
        "sshExitInterpretation": "recorded separately from Bridge success; SDK-owned SSH shutdown may be nonzero",
        "connectAttempts": connect_attempts,
        "artifactPreflight": None if transfer_check is None else {k: transfer_check.get(k) for k in ("status", "hostAlias", "hostKeyPolicy", "remoteHost", "uid", "privateRootMode", "venvVersion", "privateExecutableSha256", "wheelHashesExact", "sourceFilesExact", "receiptAbsentBeforeRun")},
        "precloseFunctionalChecksComplete": preclose is not None,
        "localGcDisabledBeforeProjectImports": local_gc_disabled_before_project_imports,
        "reader": {
            "frames": frame_count,
            "proofNonceCount": len(nonces),
            "coverage": coverage_status,
            "uncertainCount": uncertain_count,
            "membershipExact": membership_ok,
            "baselineSubscriptionSnapshotObserved": baseline_snapshot_observed,
            "activityAgeChecks": activity_age_checks,
            "expectedSelectedCount": len(expected_hashes),
            "actualSelectedCount": len(actual_hashes),
            "proofRequests": ((reader_metrics or {}).get("operations", {})).get("proofRequests", 0),
            "snapshotRequests": ((reader_metrics or {}).get("operations", {})).get("snapshotRequests", 0),
        },
        "cleanup": close_result,
    }
    diagnostic_path = ROOT / "working-set-fixed-ssh-v9-diagnostic.json"
    write_private_json_exclusive(diagnostic_path, diagnostic)
    require(failure is None, failure or "working_set_ssh_reader_failed")
    require(ready is not None, "remote_fixture_ready_missing")
    require(ready.get("pythonVersion") == "3.14.8" and ready.get("pythonEntrypointMatchesPrivateVenv") is True, "remote_private_interpreter_mismatch")
    require(ready.get("processUid") == 1000 and type(ready.get("processId")) is int and type(ready.get("processStartTicks")) is int, "remote_process_birth_missing")
    require(ready.get("processExecutableSha256") == SNAP_EXECUTABLE_SHA256, "remote_executable_identity_mismatch")
    require(ready.get("loadedModuleBytesExact") is True, "remote_loaded_module_bytes_unproved")
    require(isinstance(ready.get("loadedModuleCounts"), dict) and
            type(ready["loadedModuleCounts"].get("observer")) is int and ready["loadedModuleCounts"]["observer"] > 0 and
            type(ready["loadedModuleCounts"].get("mesh")) is int and ready["loadedModuleCounts"]["mesh"] > 0,
            "remote_loaded_module_counts_missing")
    require(ready.get("wheelSha256") == {"agent_observer": OBSERVER_WHEEL_SHA256, "mesh_plus": MESH_WHEEL_SHA256}, "remote_wheel_hash_mismatch")
    require(receipt_check is not None and receipt_check.get("status") == "pass", "remote_fixture_cleanup_unproved")
    remote_process = receipt_check.get("remoteProcess", {})
    require(remote_process.get("pid") == ready["processId"] and remote_process.get("startTicks") == ready["processStartTicks"], "remote_process_birth_changed")
    require(remote_process.get("uid") == ready["processUid"] and remote_process.get("executableSha256") == ready["processExecutableSha256"], "remote_process_identity_changed")
    require(receipt_check.get("loadedModulesInitial", {}).get("installedModuleBytesExact") is True and receipt_check.get("loadedModulesFinal", {}).get("installedModuleBytesExact") is True, "remote_final_loaded_modules_unproved")
    require(receipt_check.get("loadedModulesInitial", {}).get("wheelSha256") == {"agent_observer": OBSERVER_WHEEL_SHA256, "mesh_plus": MESH_WHEEL_SHA256} and receipt_check.get("loadedModulesFinal", {}).get("wheelSha256") == {"agent_observer": OBSERVER_WHEEL_SHA256, "mesh_plus": MESH_WHEEL_SHA256}, "remote_initial_final_wheel_map_mismatch")
    require(preclose is not None and preclose.get("functionalChecksComplete") is True, "preclose_functional_phase_missing")
    require(transfer_check is not None and transfer_check.get("status") == "pass", "remote_artifact_preflight_missing")
    bridge_class = receipt_check.get("bridgeClassification")
    require(bridge_class == "normal_cli_exit", "normal_bridge_cli_exit_required")
    require(ssh_return_code in (0, 1, 255, -15), "ssh_terminal_unclassified")
    require(receipt_check.get("normalCliExitPass") is (bridge_class == "normal_cli_exit"),
            "bridge_success_overclaim")
    require(receipt_check.get("gracefulEofPass") is True and receipt_check.get("normalCliExitPass") is True,
            "normal_bridge_eof_close_unproved")
    require(receipt_check.get("gcDisabledBeforeProjectImports") is True, "remote_gc_flag_missing")
    require(close_result["streamClosed"] and close_result["activeConnectionsZero"] and close_result["channelsClosed"], "reader_transport_cleanup_incomplete")
    operations = (reader_metrics or {}).get("operations", {})
    require(operations.get("proofRequests", 0) >= 2, "reader_proof_request_count_low")
    require(baseline_snapshot_observed, "baseline_subscription_snapshot_missing")

    report = {
        "schema": "agent-observer.working-set-fixed-ssh-installed-reader.v9",
        "status": ("functional_cleanup_and_bridge_pass" if bridge_class == "normal_cli_exit" else "functional_cleanup_pass_transport_terminal") if failure is None else "failed",
        "bridgeExitCode": receipt_check.get("bridgeExitCode"),
        "bridgeStatus": "passed" if bridge_class == "normal_cli_exit" else "failed",
        "sshExitCode": ssh_return_code,
        "sshExitInterpretation": "recorded separately from Bridge success; SDK-owned SSH shutdown may be nonzero",
        "bridgeExitClassification": bridge_class,
        "gracefulEofPass": receipt_check.get("gracefulEofPass"),
        "normalCliExitPass": receipt_check.get("normalCliExitPass"),
        "source": {"observerCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0", "meshCommit": "bfa91a6936a089d37c1a83752d3267148ba7dc69"},
        "localInstalledRuntime": runtime_facts,
        "localInstalledModules": modules,
        "resourceFlags": {"localGcDisabledBeforeProjectImports": local_gc_disabled_before_project_imports, "remoteGcDisabledBeforeProjectImports": ready.get("gcDisabledBeforeProjectImports") is True, "heapOrRssClaim": False},
        "privateArtifactPreflight": transfer_check,
        "precloseFunctionalPhase": preclose,
        "precloseReceiptSha256": digest_file(ROOT / "working-set-fixed-ssh-v9-preclose.json"),
        "profile": {"id": PROFILE_ID, "descriptorSha256": PROFILE_DIGEST, "windowMs": WINDOW_MS},
        "route": {"destinationAlias": "snap", "fixedOptionsExact": True, "sshExecutable": ssh_path,
                  "sshExecutableSha256": ssh_executable_sha, "remoteCommandSha256": command_sha,
                  "remoteCommandHashes": {"fixture": command_sha, "installedPreflight": transfer_check.get("sshCommandSha256"), "closeReceipt": receipt_check.get("sshCommandSha256") if receipt_check else None},
                  "process": process_identity, "exitCode": ssh_return_code, "connectAttempts": connect_attempts, "installedPreflightConnectAttempts": transfer_check.get("connectAttempts"), "closeReceiptConnectAttempts": receipt_check.get("connectAttempts") if receipt_check else None},
        "remoteFixture": {"host": ready.get("host"), "uid": 1000, "runtimeCollectFalse": ready.get("runtimeCollect") is False,
                          "readyObserved": True, "closedObserved": remote_closed is not None,
                          "closeMarkerStatus": None if remote_closed is None else remote_closed.get("status"),
                          "closeReceipt": receipt_check,
                          "bridgeExitClassification": bridge_class,
                          "bridgeExitCode": receipt_check.get("bridgeExitCode"),
                          "gracefulEofPass": receipt_check.get("gracefulEofPass"),
                          "normalCliExitPass": receipt_check.get("normalCliExitPass"),
                          "gcDisabledBeforeProjectImports": ready.get("gcDisabledBeforeProjectImports"),
                          "pythonVersion": ready.get("pythonVersion"),
                          "pythonPrivateEntrypoint": ready.get("pythonEntrypointMatchesPrivateVenv"),
                          "processId": ready.get("processId"), "processStartTicks": ready.get("processStartTicks"),
                          "processExecutableSha256": ready.get("processExecutableSha256"),
                          "loadedModuleCountsInitial": ready.get("loadedModuleCounts"),
                          "loadedModuleCountsFinal": {k: (receipt_check.get("loadedModulesFinal") or {}).get(k) for k in ("observerModuleCount", "meshModuleCount")},
                          "loadedModuleWheelHashesInitial": ready.get("wheelSha256"),
                          "loadedModuleWheelHashesFinal": (receipt_check.get("loadedModulesFinal") or {}).get("wheelSha256"),
                          "loadedModuleBytesExactInitial": ready.get("loadedModuleBytesExact"),
                          "loadedModuleBytesExactFinal": (receipt_check.get("loadedModulesFinal") or {}).get("installedModuleBytesExact"),
                          "wheelSha256": ready.get("wheelSha256")},
        "reader": {"frames": frame_count, "proofNonceCount": len(nonces),
                   "proofRequests": operations.get("proofRequests", 0), "snapshotRequests": operations.get("snapshotRequests", 0),
                   "baselineSubscriptionSnapshotObserved": baseline_snapshot_observed,
                   "meshFrameKinds": stream_kinds,
                   "coverage": coverage_status, "uncertainCount": uncertain_count,
                   "membershipExact": membership_ok, "expectedSelectedCount": len(expected_hashes),
                   "actualSelectedCount": len(actual_hashes), "activityAgeChecks": activity_age_checks,
                   "dtoFieldChecks": actual_detail_checks, "expectedIdentityHashes": expected_hashes,
                   "actualIdentityHashes": actual_hashes},
        "cleanup": close_result,
        "coverageLimits": ["installed synthetic Observer IPC to installed Mesh stdio Bridge over fixed SSH via ordinary SDK Reader",
                           "functional checks are recorded before SDK close; Bridge terminal exceptions are observed without changing CLI behavior; nonzero owned-close/EOF is not normal CLI success",
                           "physical cleanup is established by one independent bounded post-run receipt/process/path read",
                           "GC is disabled before project imports on both ends; this is a resource/transport flag only, with no heap/RSS inference",
                           "collect=False seeded Observer Runtime; no provider/native collection, normal endpoint or live source acceptance"],
    }
    path = ROOT / "working-set-fixed-ssh-reader-v9.json"
    write_private_json_exclusive(path, report)
    return report


def require_reviewed_plan_token():
    if len(sys.argv) != 3 or sys.argv[1] != "--execute-reviewed-plan":
        raise QualificationError("reviewed_plan_token_required")
    token = sys.argv[2]
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise QualificationError("reviewed_plan_token_invalid")
    try:
        plan_bytes = PLAN_PATH.read_bytes()
        plan = json.loads(plan_bytes)
    except BaseException:
        raise QualificationError("reviewed_plan_unavailable") from None
    require(digest(plan_bytes) == token, "reviewed_plan_digest_mismatch")
    require(plan.get("schema") == "agent-observer.fixed-ssh-v9-plan.v1", "reviewed_plan_schema")
    require(plan.get("execution", {}).get("readerRunner", {}).get("sha256") == digest_file(Path(__file__)), "reader_runner_digest_mismatch")
    manifest_path = ROOT / "working-set-fixed-ssh-v9-manifest.json"
    manifest_stat = manifest_path.lstat()
    require(stat.S_ISREG(manifest_stat.st_mode) and manifest_stat.st_uid == os.getuid() and stat.S_IMODE(manifest_stat.st_mode) == 0o600, "package_manifest_policy")
    require(plan.get("packageManifest", {}).get("sha256") == digest_file(manifest_path), "package_manifest_digest_mismatch")


if __name__ == "__main__":
    try:
        require_reviewed_plan_token()
        result = asyncio.run(run())
        print(json.dumps({"status": result["status"], "proofNonceCount": result["reader"]["proofNonceCount"],
                          "expectedSelectedCount": result["reader"]["expectedSelectedCount"],
                          "actualSelectedCount": result["reader"]["actualSelectedCount"],
                          "remoteClosed": result["remoteFixture"]["closedObserved"],
                          "bridgeExitClassification": result["bridgeExitClassification"],
                          "bridgeExitCode": result["bridgeExitCode"],
                          "sshExitCode": result["sshExitCode"],
                          "report": str(ROOT / "working-set-fixed-ssh-reader-v9.json")}, sort_keys=True))
        raise SystemExit(0)
    except SystemExit:
        raise
    except QualificationError as error:
        safe = {"status": "failed", "reasonCode": error.code}
        failure_path = ROOT / "working-set-fixed-ssh-reader-v9-failure.json"
        try:
            write_private_json_exclusive(failure_path, safe)
        except FileExistsError:
            pass
        print(json.dumps(safe, sort_keys=True))
        raise SystemExit(1) from None
    except BaseException:
        safe = {"status": "failed", "reasonCode": "working_set_ssh_reader_failed"}
        failure_path = ROOT / "working-set-fixed-ssh-reader-v9-failure.json"
        try:
            write_private_json_exclusive(failure_path, safe)
        except FileExistsError:
            pass
        print(json.dumps(safe, sort_keys=True))
        raise SystemExit(1) from None
