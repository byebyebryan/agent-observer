from __future__ import annotations

import argparse
import ast
import asyncio
import base64
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

PLAN_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69")
V9_ROOT = PACKAGE_ROOT / "fixed-ssh-v9"
PLAN_PATH = PLAN_ROOT / "fixed-ssh-v9-plan.json"
OUTPUT_PATH = PLAN_ROOT / "fixed-ssh-v9-execution.json"
READER_RUNNER = PLAN_ROOT / "run-working-set-fixed-ssh-v9-reader.py"
TARGET = "/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69"
BASE_PYTHON = "/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0/venv-314/bin/python"
BASE_PYTHON_SHA256 = "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
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
MAX_PACKET_BYTES = 6 * 1024 * 1024


class PlanError(Exception):
    def __init__(self, code: str, *, phase: str = "local_preflight"):
        self.code = code
        self.phase = phase
        super().__init__(code)


def need(condition: bool, code: str, *, phase: str = "local_preflight") -> None:
    if not condition:
        raise PlanError(code, phase=phase)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def checked_plan(token: str | None) -> tuple[dict, str]:
    node = PLAN_PATH.lstat()
    need(stat.S_ISREG(node.st_mode) and node.st_uid == os.getuid() and stat.S_IMODE(node.st_mode) == 0o600, "plan_file_policy")
    raw = PLAN_PATH.read_bytes()
    digest = sha(raw)
    need(token is None or token == digest, "reviewed_plan_digest_mismatch")
    plan = json.loads(raw)
    need(plan.get("schema") == "agent-observer.fixed-ssh-v9-plan.v1", "plan_schema")
    need(plan.get("status") == "prepared_static_offline", "plan_status")
    need(plan.get("target", {}).get("packageRoot") == TARGET, "plan_target_mismatch")
    need(plan.get("route", {}).get("sshOptions") == SSH_OPTIONS and plan.get("route", {}).get("hostAlias") == "snap", "plan_route_mismatch")
    need(plan.get("source") == {"observerCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0", "meshCommit": "bfa91a6936a089d37c1a83752d3267148ba7dc69"}, "plan_source_tuple")
    need(plan.get("execution", {}).get("driver", {}).get("sha256") == sha_file(Path(__file__)), "execution_driver_digest_mismatch")
    need(plan.get("execution", {}).get("readerRunner", {}).get("sha256") == sha_file(READER_RUNNER), "reader_runner_digest_mismatch")
    reader_tree = ast.parse(READER_RUNNER.read_text(), filename=str(READER_RUNNER))
    reader_preflight = None
    for node in reader_tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "REMOTE_PREFLIGHT_SOURCE" for target in node.targets):
            reader_preflight = ast.literal_eval(node.value)
            break
    need(isinstance(reader_preflight, str) and plan.get("execution", {}).get("remoteSources", {}).get("installedPreflightSha256") == sha(reader_preflight.encode()), "installed_preflight_digest_mismatch")
    manifest_path = V9_ROOT / "working-set-fixed-ssh-v9-manifest.json"
    manifest_stat = manifest_path.lstat()
    need(stat.S_ISREG(manifest_stat.st_mode) and manifest_stat.st_uid == os.getuid() and stat.S_IMODE(manifest_stat.st_mode) == 0o600, "package_manifest_policy")
    need(plan.get("packageManifest", {}).get("sha256") == sha_file(manifest_path), "package_manifest_digest_mismatch")
    need(plan.get("packageManifest", {}).get("bytes") == manifest_path.stat(follow_symlinks=False).st_size, "package_manifest_size_mismatch")
    package_manifest = json.loads(manifest_path.read_bytes())
    manifest_transfer_row = {"path": "fixed-ssh-v9/working-set-fixed-ssh-v9-manifest.json", "bytes": manifest_stat.st_size, "sha256": sha_file(manifest_path), "mode": "0600"}
    expected_transfer = list(package_manifest.get("payloadFiles", [])) + [manifest_transfer_row]
    expected_transfer.sort(key=lambda item: item.get("path", ""))
    need(plan.get("transfer", {}).get("files") == expected_transfer, "transfer_manifest_binding_mismatch")
    need(plan.get("target", {}).get("remoteMustBeAbsentBeforeTransfer") is True, "target_absence_guard_missing")
    expected_files = plan.get("transfer", {}).get("files")
    need(isinstance(expected_files, list) and len(expected_files) == 25, "transfer_inventory_shape")
    names = [item.get("path") for item in expected_files if isinstance(item, dict)]
    need(len(names) == len(expected_files) and len(set(names)) == len(names), "transfer_inventory_duplicate")
    need(all(name.startswith("fixed-ssh-v9/") for name in names), "transfer_path_outside_v9")
    for item in expected_files:
        relative = PurePosixPath(item["path"])
        need(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == item["path"], "transfer_path_invalid")
        path = PACKAGE_ROOT / item["path"]
        current = PACKAGE_ROOT
        for component in relative.parts[:-1]:
            current = current / component
            directory_node = current.lstat()
            need(stat.S_ISDIR(directory_node.st_mode) and directory_node.st_uid == os.getuid() and stat.S_IMODE(directory_node.st_mode) == 0o700, "local_transfer_directory_policy")
        node = path.lstat()
        need(stat.S_ISREG(node.st_mode) and node.st_uid == os.getuid() and stat.S_IMODE(node.st_mode) == 0o600, "local_transfer_file_policy")
        need(node.st_size == item["bytes"] and sha_file(path) == item["sha256"], "local_transfer_file_hash_mismatch")
    need([item["path"] for item in expected_files] == sorted(names), "transfer_inventory_not_sorted")
    v9st = V9_ROOT.lstat()
    need(stat.S_ISDIR(v9st.st_mode) and v9st.st_uid == os.getuid() and stat.S_IMODE(v9st.st_mode) == 0o700, "local_v9_root_policy")
    package_st = PACKAGE_ROOT.lstat()
    need(stat.S_ISDIR(package_st.st_mode) and package_st.st_uid == os.getuid() and stat.S_IMODE(package_st.st_mode) == 0o700, "local_package_root_policy")
    return plan, digest


REMOTE_ABSENCE_SOURCE = r"""import hashlib,json,os,stat,sys
from pathlib import Path
TARGET=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69")
BASE=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0/venv-314/bin/python")
EXPECTED="375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
def h(p):
 x=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): x.update(b)
 return x.hexdigest()
def need(v,c):
 if not v: raise ValueError(c)
try:
 need(os.getuid()==1000 and os.uname().nodename=="80H1VV3","remote_identity")
 for p in (Path("/home"),Path("/home/bryan"),Path("/home/bryan/.cache"),Path("/home/bryan/.cache/agent-observer-working-set-20261018")):
  s=p.lstat(); need(stat.S_ISDIR(s.st_mode) and not stat.S_ISLNK(s.st_mode),"parent_component_policy")
 parent=TARGET.parent.lstat(); need(stat.S_ISDIR(parent.st_mode) and parent.st_uid==1000 and not (stat.S_IMODE(parent.st_mode)&0o022),"target_parent_policy")
 need(not os.path.lexists(TARGET),"target_already_exists")
 need(os.path.abspath(sys.executable)==str(BASE) and tuple(sys.version_info[:3])==(3,14,8),"base_python_identity")
 need(h(Path("/proc/self/exe"))==EXPECTED,"base_python_digest")
 base_root=BASE.parents[2].lstat();need(stat.S_ISDIR(base_root.st_mode) and base_root.st_uid==1000 and stat.S_IMODE(base_root.st_mode)==0o700,"base_root_policy")
 print(json.dumps({"schema":"agent-observer.fixed-ssh-v9-remote-absence.v1","status":"pass","host":"80H1VV3","uid":1000,"packageRootAbsent":True,"basePythonVersion":"3.14.8","basePythonExecutableSha256":EXPECTED},sort_keys=True))
except Exception:
 print(json.dumps({"schema":"agent-observer.fixed-ssh-v9-remote-absence.v1","status":"failed","reasonCode":"remote_absence_preflight_failed"},sort_keys=True))
 raise SystemExit(1) from None
"""

REMOTE_RECEIVER_TEMPLATE = r"""import base64,hashlib,json,os,stat,sys
from pathlib import Path,PurePosixPath
TARGET=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-bfa91a69")
BASE=Path("/home/bryan/.cache/agent-observer-working-set-20261018/installed-pair-b176ac06-c06b33e0/venv-314/bin/python")
EXPECTED_BASE="375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b"
EXPECTED=__EXPECTED_MAP__
MAX_BYTES=6291456
DIR_FLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW
def sha(data): return hashlib.sha256(data).hexdigest()
def strict(pairs):
 d={}
 for k,v in pairs:
  if k in d: raise ValueError("duplicate_key")
  d[k]=v
 return d
def need(v,c):
 if not v: raise ValueError(c)
def safe(name):
 p=PurePosixPath(name)
 need(name==p.as_posix() and not p.is_absolute() and ".." not in p.parts and all(x not in ("",".") for x in p.parts),"bad_path")
 return p
def open_absolute_directory(path):
 fd=os.open("/",DIR_FLAGS)
 try:
  for component in PurePosixPath(path).parts[1:]:
   next_fd=os.open(component,DIR_FLAGS,dir_fd=fd)
   os.close(fd);fd=next_fd
  st=os.fstat(fd)
  need(stat.S_ISDIR(st.st_mode) and st.st_uid==1000 and not (stat.S_IMODE(st.st_mode)&0o022),"target_parent_policy")
  return fd
 except BaseException:
  os.close(fd);raise
def hash_fd(fd):
 h=hashlib.sha256()
 while True:
  b=os.read(fd,1048576)
  if not b:break
  h.update(b)
 return h.hexdigest()
try:
 need(os.getuid()==1000 and os.uname().nodename=="80H1VV3","remote_identity")
 need(os.path.abspath(sys.executable)==str(BASE) and tuple(sys.version_info[:3])==(3,14,8),"base_python_identity")
 exe_fd=os.open("/proc/self/exe",os.O_RDONLY|os.O_CLOEXEC)
 try: need(hash_fd(exe_fd)==EXPECTED_BASE,"base_python_digest")
 finally: os.close(exe_fd)
 base_root=BASE.parents[2].lstat();need(stat.S_ISDIR(base_root.st_mode) and base_root.st_uid==1000 and stat.S_IMODE(base_root.st_mode)==0o700,"base_root_policy")
 parent_fd=open_absolute_directory(TARGET.parent)
 raw=sys.stdin.buffer.read(MAX_BYTES+1);need(len(raw)<=MAX_BYTES,"packet_too_large")
 packet=json.loads(raw,object_pairs_hook=strict)
 need(set(packet)=={"schema","target","files"} and packet["schema"]=="agent-observer.fixed-ssh-v9-transfer-packet.v1" and packet["target"]==str(TARGET),"packet_binding")
 rows=packet["files"];need(isinstance(rows,list) and len(rows)==len(EXPECTED),"packet_inventory_shape")
 names=[row.get("path") for row in rows if isinstance(row,dict)]
 need(len(names)==len(rows) and len(set(names))==len(names) and set(names)==set(EXPECTED),"packet_inventory_mismatch")
 decoded=[];total=0
 for row in rows:
  need(set(row)=={"path","bytes","sha256","content"},"packet_row_shape")
  path=safe(row["path"]);expected=EXPECTED[row["path"]]
  need(row["bytes"]==expected["bytes"] and row["sha256"]==expected["sha256"],"packet_expected_metadata")
  content=base64.b64decode(row["content"],validate=True)
  need(base64.b64encode(content).decode()==row["content"] and len(content)==row["bytes"] and sha(content)==row["sha256"],"packet_content_hash")
  total+=len(content);need(total<=MAX_BYTES,"packet_payload_limit");decoded.append((path,content))
 os.mkdir(TARGET.name,0o700,dir_fd=parent_fd)
 root_fd=os.open(TARGET.name,DIR_FLAGS,dir_fd=parent_fd)
 os.fchmod(root_fd,0o700)
 root_stat=os.fstat(root_fd);need(root_stat.st_uid==1000 and stat.S_IMODE(root_stat.st_mode)==0o700,"created_target_policy")
 dirfds={():root_fd}
 try:
  for path,data in decoded:
   prefix=()
   parent=root_fd
   for component in path.parts[:-1]:
    prefix=prefix+(component,)
    if prefix not in dirfds:
     os.mkdir(component,0o700,dir_fd=parent)
     child=os.open(component,DIR_FLAGS,dir_fd=parent)
     st=os.fstat(child);need(stat.S_ISDIR(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o700,"created_directory_policy")
     dirfds[prefix]=child
    parent=dirfds[prefix]
   leaf=path.parts[-1]
   fd=os.open(leaf,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_CLOEXEC|os.O_NOFOLLOW,0o600,dir_fd=parent)
   try:
    os.fchmod(fd,0o600)
    view=memoryview(data)
    while view:
     written=os.write(fd,view)
     need(written>0,"short_write")
     view=view[written:]
    os.fsync(fd)
   finally: os.close(fd)
   verify_fd=os.open(leaf,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=parent)
   try:
    st=os.fstat(verify_fd);need(stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_size==len(data) and hash_fd(verify_fd)==EXPECTED[path.as_posix()]["sha256"],"written_file_verification")
   finally: os.close(verify_fd)
  for fd in dirfds.values(): os.fsync(fd)
 finally:
  for fd in set(dirfds.values()): os.close(fd)
 os.fsync(parent_fd)
 print(json.dumps({"schema":"agent-observer.fixed-ssh-v9-transfer.v1","status":"pass","host":"80H1VV3","uid":1000,"packageRootMode":"0700","fileCount":len(decoded),"byteCount":total,"allFilesRegular600":True,"allDirectories700":True,"noLinks":True,"allHashesExact":True},sort_keys=True))
except Exception:
 print(json.dumps({"schema":"agent-observer.fixed-ssh-v9-transfer.v1","status":"failed","reasonCode":"transfer_receiver_failed"},sort_keys=True))
 raise SystemExit(1) from None
"""


def remote_receiver_source(files: list[dict]) -> str:
    expected = {item["path"]: {"bytes": item["bytes"], "sha256": item["sha256"]} for item in files}
    literal = repr(expected)
    return REMOTE_RECEIVER_TEMPLATE.replace("__EXPECTED_MAP__", literal)


def local_payload(plan: dict) -> bytes:
    rows = []
    for item in plan["transfer"]["files"]:
        path = PACKAGE_ROOT / item["path"]
        data = path.read_bytes()
        rows.append({"path": item["path"], "bytes": len(data), "sha256": sha(data), "content": base64.b64encode(data).decode("ascii")})
    packet = {"schema": "agent-observer.fixed-ssh-v9-transfer-packet.v1", "target": TARGET, "files": rows}
    raw = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    need(len(raw) <= MAX_PACKET_BYTES, "transfer_packet_too_large")
    return raw


async def ssh_call(ssh_path: str, remote_command: str, *, input_data: bytes | None, timeout: float, output_limit: int, phase: str) -> tuple[int, bytes]:
    argv = [ssh_path, *SSH_OPTIONS, "--", "snap", remote_command]
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE if input_data is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _stderr = await asyncio.wait_for(process.communicate(input_data), timeout=timeout)
    except BaseException:
        if process.returncode is None:
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except BaseException:
            if process.returncode is None:
                process.kill()
            await asyncio.gather(process.wait(), return_exceptions=True)
        raise PlanError(phase + "_timeout", phase=phase) from None
    need(len(stdout) <= output_limit, phase + "_output_limit", phase=phase)
    return process.returncode, stdout


def parse_remote_json(code: int, output: bytes, schema: str, phase: str) -> dict:
    need(code == 0, phase + "_remote_exit", phase=phase)
    try:
        value = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PlanError(phase + "_output_invalid", phase=phase) from None
    need(isinstance(value, dict) and value.get("schema") == schema and value.get("status") == "pass", phase + "_remote_failed", phase=phase)
    return value


def write_exclusive(path: Path, value: dict) -> None:
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd >= 0:
            os.close(fd)


async def execute(plan: dict, token: str) -> dict:
    need(not OUTPUT_PATH.exists() and not OUTPUT_PATH.is_symlink(), "execution_output_collision", phase="preflight")
    need(not (V9_ROOT / "working-set-fixed-ssh-v9-bootstrap.json").exists(), "bootstrap_receipt_collision", phase="preflight")
    need(not (V9_ROOT / "working-set-fixed-ssh-v9-preclose.json").exists(), "preclose_output_collision", phase="preflight")
    need(not (V9_ROOT / "working-set-fixed-ssh-v9-diagnostic.json").exists(), "diagnostic_output_collision", phase="preflight")
    need(not (V9_ROOT / "working-set-fixed-ssh-reader-v9.json").exists(), "reader_output_collision", phase="preflight")
    need(not (V9_ROOT / "working-set-fixed-ssh-reader-v9-failure.json").exists(), "reader_failure_collision", phase="preflight")
    ssh_path = shutil.which("ssh")
    need(ssh_path is not None and Path(ssh_path).is_absolute(), "ssh_executable_unavailable", phase="preflight")
    ssh_path = str(Path(ssh_path).resolve(strict=True))
    ssh_hash = sha_file(Path(ssh_path))
    receiver = remote_receiver_source(plan["transfer"]["files"])
    packet = local_payload(plan)
    absence_command = shlex.join([BASE_PYTHON, "-I", "-B", "-c", REMOTE_ABSENCE_SOURCE])
    absence_code, absence_stdout = await ssh_call(ssh_path, absence_command, input_data=None, timeout=15, output_limit=4096, phase="remote_absence_preflight")
    absence = parse_remote_json(absence_code, absence_stdout, "agent-observer.fixed-ssh-v9-remote-absence.v1", "remote_absence_preflight")
    receiver_command = shlex.join([BASE_PYTHON, "-I", "-B", "-c", receiver])
    transfer_code, transfer_stdout = await ssh_call(ssh_path, receiver_command, input_data=packet, timeout=30, output_limit=4096, phase="remote_transfer")
    transfer = parse_remote_json(transfer_code, transfer_stdout, "agent-observer.fixed-ssh-v9-transfer.v1", "remote_transfer")
    install_command = shlex.join([BASE_PYTHON, "-I", "-B", TARGET + "/fixed-ssh-v9/install-remote-v9.py"])
    install_code, install_stdout = await ssh_call(ssh_path, install_command, input_data=None, timeout=120, output_limit=8192, phase="remote_install")
    install = parse_remote_json(install_code, install_stdout, "agent-observer.working-set-fixed-ssh-v9-bootstrap.v1", "remote_install")
    child_env = {"PATH": "/usr/bin:/bin", "HOME": str(PLAN_ROOT), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    local_python = PACKAGE_ROOT / "venv-314/bin/python"
    need(local_python.is_file(), "local_private_python_missing", phase="installed_reader")
    try:
        child = subprocess.run([str(local_python), "-B", str(READER_RUNNER), "--execute-reviewed-plan", token], cwd=PLAN_ROOT, env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        raise PlanError("reader_runner_timeout", phase="installed_reader") from None
    need(len(child.stdout) <= 16384 and len(child.stderr) <= 16384, "reader_runner_output_limit", phase="installed_reader")
    need(child.returncode == 0, "reader_runner_failed", phase="installed_reader")
    try:
        child_summary = json.loads(child.stdout.splitlines()[-1])
    except (UnicodeDecodeError, json.JSONDecodeError, IndexError):
        raise PlanError("reader_runner_summary_invalid", phase="installed_reader") from None
    need(child_summary.get("status") == "functional_cleanup_and_bridge_pass", "normal_bridge_cleanup_pass_required", phase="installed_reader")
    reader_path = V9_ROOT / "working-set-fixed-ssh-reader-v9.json"
    need(reader_path.is_file() and not reader_path.is_symlink(), "reader_report_missing", phase="installed_reader")
    reader = json.loads(reader_path.read_text())
    need(reader.get("source", {}).get("meshCommit") == "bfa91a6936a089d37c1a83752d3267148ba7dc69" and reader.get("status") == child_summary["status"], "reader_report_binding", phase="installed_reader")
    result = {
        "schema": "agent-observer.fixed-ssh-v9-execution.v1",
        "status": child_summary["status"],
        "claim": "installed synthetic collect=False Observer IPC to installed Mesh stdio Bridge over fixed SSH through ordinary Reader; no provider/native collection",
        "reviewedPlanSha256": token,
        "source": plan["source"],
        "route": {"hostAlias": "snap", "strictHostKeyChecking": True, "sshOptionsExact": True, "sshExecutableSha256": ssh_hash, "remoteCommandHashes": {"absence": sha(absence_command.encode()), "transferReceiver": sha(receiver.encode()), "installer": sha(install_command.encode()), "readerFixture": reader.get("route", {}).get("remoteCommandHashes", {}).get("fixture"), "readerInstalledPreflight": reader.get("route", {}).get("remoteCommandHashes", {}).get("installedPreflight"), "readerCloseReceipt": reader.get("route", {}).get("remoteCommandHashes", {}).get("closeReceipt")}, "connectAttempts": {"absence": 1, "transfer": 1, "install": 1, "installedPreflight": reader.get("route", {}).get("installedPreflightConnectAttempts"), "reader": reader.get("route", {}).get("connectAttempts"), "closeCheck": reader.get("route", {}).get("closeReceiptConnectAttempts")}},
        "remoteAbsencePreflight": absence,
        "transfer": transfer,
        "install": install,
        "reader": {"status": reader["status"], "proofNonceCount": reader.get("reader", {}).get("proofNonceCount"), "selectedCount": reader.get("reader", {}).get("actualSelectedCount"), "coverage": reader.get("reader", {}).get("coverage"), "uncertainCount": reader.get("reader", {}).get("uncertainCount"), "closeReceipt": reader.get("remoteFixture", {}).get("closeReceipt"), "bridgeExitClassification": reader.get("bridgeExitClassification"), "bridgeExitCode": reader.get("bridgeExitCode"), "sshExitCode": reader.get("sshExitCode")},
        "outputs": {"readerReport": str(reader_path), "preclose": str(V9_ROOT / "working-set-fixed-ssh-v9-preclose.json"), "diagnostic": str(V9_ROOT / "working-set-fixed-ssh-v9-diagnostic.json"), "closeReceipt": str(V9_ROOT / "working-set-fixed-ssh-close-receipt-v9.json")},
        "coverageLimits": reader.get("coverageLimits", []),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--execute-reviewed-plan", metavar="SHA256")
    args = parser.parse_args()
    token = args.execute_reviewed_plan
    try:
        plan, digest = checked_plan(token)
        receiver = remote_receiver_source(plan["transfer"]["files"])
        remote_sources = plan.get("execution", {}).get("remoteSources", {})
        need(remote_sources.get("absencePreflightSha256") == sha(REMOTE_ABSENCE_SOURCE.encode()), "absence_source_digest_mismatch")
        need(remote_sources.get("transferReceiverTemplateSha256") == sha(REMOTE_RECEIVER_TEMPLATE.encode()), "receiver_template_digest_mismatch")
        need(remote_sources.get("transferReceiverBoundSourceSha256") == sha(receiver.encode()), "receiver_bound_source_digest_mismatch")
        if args.plan_only:
            print(json.dumps({"status": "ready_for_primary_review", "planSha256": digest, "driverSha256": sha_file(Path(__file__)), "readerRunnerSha256": sha_file(READER_RUNNER), "manifestSha256": sha_file(V9_ROOT / "working-set-fixed-ssh-v9-manifest.json"), "remoteReceiverSha256": sha(receiver.encode()), "sshExecuted": False, "transferPerformed": False}, sort_keys=True))
            return 0
        need(token == digest, "reviewed_plan_token_required", phase="authorization")
        result = asyncio.run(execute(plan, digest))
        write_exclusive(OUTPUT_PATH, result)
        print(json.dumps({"status": result["status"], "planSha256": digest, "proofNonceCount": result["reader"].get("proofNonceCount"), "readerReport": result["outputs"]["readerReport"], "executionReport": str(OUTPUT_PATH)}, sort_keys=True))
        return 0
    except PlanError as error:
        result = {"schema": "agent-observer.fixed-ssh-v9-execution.v1", "status": "failed", "phase": error.phase, "reasonCode": error.code, "remoteExecutionStarted": error.phase not in {"local_preflight", "authorization", "preflight"}}
        if args.execute_reviewed_plan and not OUTPUT_PATH.exists() and not OUTPUT_PATH.is_symlink():
            try:
                write_exclusive(OUTPUT_PATH, result)
            except FileExistsError:
                pass
        print(json.dumps({"status": "failed", "phase": error.phase, "reasonCode": error.code}, sort_keys=True))
        return 1
    except BaseException:
        result = {"schema": "agent-observer.fixed-ssh-v9-execution.v1", "status": "failed", "phase": "unknown", "reasonCode": "execution_failed", "remoteExecutionStarted": True}
        if args.execute_reviewed_plan and not OUTPUT_PATH.exists() and not OUTPUT_PATH.is_symlink():
            try:
                write_exclusive(OUTPUT_PATH, result)
            except FileExistsError:
                pass
        print(json.dumps({"status": "failed", "phase": "unknown", "reasonCode": "execution_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
