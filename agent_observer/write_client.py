"""Explicit New/Resume client. Never imported by passive observation or reads."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from pathlib import Path

from .bounded_json import WireError, decode_document
from .contract import ContractError, canonical, store_namespace
from .read_client import select as select_session
from .write_contract import schema_document, validate_plan, validate_request, validate_result

ARTIFACTS = {
    "codex": (
        "/opt/openai-codex/bin/codex",
        "12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad",
    ),
    "claude": (
        "/opt/claude-code/bin/claude",
        "3920489a5109cff5786a1a392c25277408ff22bc796d5edb9c16a60e5a1718f0",
    ),
}
BG_SETTINGS = '{"worktree":{"bgIsolation":"none"}}'


def _digest(path, limit, timeout=3):
    digest = hashlib.sha256()
    deadline = time.monotonic() + timeout
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit or before.st_mode & 0o022:
            raise ContractError("artifact_unavailable")
        total = 0
        while chunk := os.read(fd, 1024 * 1024):
            total += len(chunk)
            if total > limit or time.monotonic() > deadline:
                raise ContractError("artifact_inspection_limit")
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ContractError("artifact_changed")
        return digest.hexdigest(), {"device": before.st_dev, "inode": before.st_ino}
    finally:
        os.close(fd)


def _directory(value, *, owned=False):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.resolve(strict=True) != path:
        raise ContractError("noncanonical_directory")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or (owned and info.st_uid != os.geteuid()):
        raise ContractError("directory_unavailable")
    return {"device": info.st_dev, "inode": info.st_ino}


def _collect(request):
    from .collection import collect

    return collect(
        host_scope=request["hostScope"],
        providers=[request["provider"]],
        codex_home=Path(request["configHome"]),
        claude_home=Path(request["configHome"]),
    )


def _target(request):
    snapshot = _collect(request)
    row = select_session(snapshot, request["reference"])
    source = next(
        source
        for source in snapshot["sources"]
        if source["provider"] == request["provider"]
        and source["namespace"] == row["identity"]["namespace"]
    )
    if (
        row["kind"] == "child"
        or row["metadataIssues"]
        or source["configHome"] != request["configHome"]
        or source["configHomeKind"] != request["configHomeKind"]
        or source["runtime"] is None
        or source["sourceHealth"] not in {"current", "partial"}
    ):
        raise ContractError("resume_evidence_unavailable")
    expected = store_namespace(
        request["provider"], request["configHome"], request["configHomeKind"], os.geteuid()
    )
    if source["namespace"] != expected or row["cwd"] != request["cwd"]:
        raise ContractError("resume_context_changed")
    if row["runtime"]["health"] in {"stale", "ambiguous"} or row["phase"]["health"] == "ambiguous":
        raise ContractError("resume_evidence_unavailable")
    return row, source


def prepare(request):
    validate_request(request)
    provider = request["provider"]
    cwd = _directory(request["cwd"])
    config = _directory(request["configHome"], owned=True)
    if provider == "codex" and request["configHomeKind"] != "explicit":
        raise ContractError("unsupported_config_selector")
    if (
        provider == "claude"
        and request["configHomeKind"] == "default"
        and (
            request["configHome"] != str(Path.home() / ".claude")
            or "CLAUDE_CONFIG_DIR" in os.environ
        )
    ):
        raise ContractError("unsupported_config_selector")
    executable, accepted_hash = ARTIFACTS[provider]
    binary_hash, binary = _digest(Path(executable), 512 * 1024 * 1024)
    if binary_hash != accepted_hash:
        raise ContractError("runtime_artifact_not_accepted")
    settings = Path(request["configHome"]) / (
        "config.toml" if provider == "codex" else "settings.json"
    )
    settings_hash = _digest(settings, 1024 * 1024)[0] if settings.exists() else None
    runtime_token = None
    if request["operation"] == "new":
        route = "codex_new" if provider == "codex" else "claude_new"
    else:
        row, source = _target(request)
        runtime_token = hashlib.sha256(
            canonical([source["runtimeNamespace"], source["runtime"]]).encode()
        ).hexdigest()
        if provider == "codex":
            route = "codex_resume"
        elif (
            row["sessionKind"] == "bg"
            and row["worker"]["value"] == "present"
            and row["worker"]["health"] == "current"
            and row["nativeIds"]["jobId"]
        ):
            route = "claude_attach"
        elif (
            row["history"] is not None
            and source["coverage"]["saved"]["status"] in {"complete", "partial"}
            and (
                row["inventory"] == "saved"
                or row["inventory"] == "retained_job"
                and row["job"] is not None
                and row["job"]["retained"] is True
                and row["job"]["state"] in {"done", "failed", "stopped"}
                and row["worker"]["value"] != "present"
            )
        ):
            route = "claude_saved_resume"
        else:
            raise ContractError("unsupported_resume_route")
    plan = {
        "schemaVersion": 1,
        "request": request,
        "guard": {
            "uid": os.geteuid(),
            "cwd": cwd,
            "config": config,
            "binary": binary,
            "binarySha256": binary_hash,
            "settingsSha256": settings_hash,
            "runtimeToken": runtime_token,
        },
        "route": route,
        "createdAt": time.time_ns() // 1_000_000,
    }
    return validate_plan(plan)


def revalidate(plan):
    validate_plan(plan)
    fresh = prepare(plan["request"])
    if fresh["guard"] != plan["guard"] or fresh["route"] != plan["route"]:
        raise ContractError("handoff_context_changed")
    return fresh


def invocation(plan, *, background=False):
    """Derive native argv locally; caller cannot supply executable/arguments."""
    request = plan["request"]
    provider = request["provider"]
    argv = [ARTIFACTS[provider][0]]
    env = os.environ.copy()
    if provider == "codex":
        env["CODEX_HOME"] = request["configHome"]
        if plan["route"] == "codex_resume":
            row, _ = _target(request)
            argv.extend(["resume", "--all", row["nativeIds"]["sessionId"]])
    else:
        if request["configHomeKind"] == "default":
            env.pop("CLAUDE_CONFIG_DIR", None)
        else:
            env["CLAUDE_CONFIG_DIR"] = request["configHome"]
        if plan["route"] == "claude_attach":
            row, _ = _target(request)
            argv.extend(["attach", row["nativeIds"]["jobId"]])
        elif background:
            argv.extend(["--settings", BG_SETTINGS])
            if plan["route"] == "claude_saved_resume":
                argv.extend(["--resume", request["reference"]["nativeId"]])
            argv.append("--bg")
        else:
            raise ContractError("background_preparation_required")
    return argv, env


def _launch(argv, env, cwd, timeout):
    """Own the launcher only. Never kill a group containing provider jobs."""
    process = subprocess.Popen(
        argv,
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    buffers = [bytearray(), bytearray()]
    deadline = time.monotonic() + timeout
    reason = None
    try:
        with selectors.DefaultSelector() as poller:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                poller.register(stream, selectors.EVENT_READ, index)
            while poller.get_map():
                if time.monotonic() >= deadline:
                    reason = "launcher_timeout"
                    break
                for key, _ in poller.select(max(0, min(0.2, deadline - time.monotonic()))):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        poller.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(chunk)
                    if len(buffers[key.data]) > 64 * 1024:
                        reason = "launcher_output_limit"
                        break
                if reason:
                    break
        if reason:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
            process.wait(timeout=1)
        else:
            try:
                process.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                reason = "launcher_timeout"
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        return process.returncode, bytes(buffers[0]) + b"\n" + bytes(buffers[1]), reason
    except BaseException:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise
    finally:
        process.stdout.close()
        process.stderr.close()


def result(plan, status, reason, effect="none", resulting=None, handoff=None, pending=False):
    return validate_result(
        {
            "schemaVersion": 1,
            "operation": plan["request"]["operation"],
            "status": status,
            "reason": reason,
            "effect": effect,
            "requestedIdentity": plan["request"]["reference"],
            "resultingIdentity": resulting,
            "identityPending": pending,
            "handoff": handoff,
        }
    )


def execute(plan, *, timeout=30):
    fresh = revalidate(plan)
    if fresh["route"] not in {"claude_new", "claude_saved_resume"}:
        return result(
            fresh,
            "prepared",
            "tty_handoff_required",
            handoff=fresh,
            pending=fresh["route"] == "codex_new",
        )
    argv, env = invocation(fresh, background=True)
    try:
        code, output, failure = _launch(argv, env, fresh["request"]["cwd"], timeout)
    except OSError:
        return result(fresh, "rejected", "launcher_unavailable")
    except KeyboardInterrupt:
        return result(fresh, "uncertain", "launcher_interrupted", effect="uncertain", pending=True)
    cues = set(re.findall(rb"\bclaude attach ([0-9a-f]{8})\b", output))
    if failure or code != 0 or len(cues) != 1:
        return result(
            fresh,
            "uncertain",
            failure or "native_launch_uncertain",
            effect="uncertain",
            pending=True,
        )
    job = next(iter(cues)).decode("ascii")
    deadline = time.monotonic() + min(timeout, 15)
    while time.monotonic() < deadline:
        try:
            snapshot = _collect(fresh["request"])
            rows = [
                row
                for row in snapshot["sessions"]
                if row["nativeIds"]["jobId"] == job
                and row["cwd"] == fresh["request"]["cwd"]
                and row["worker"]["value"] == "present"
                and not row["metadataIssues"]
            ]
            if len(rows) == 1:
                actual = rows[0]["identity"]
                request = {**fresh["request"], "operation": "resume", "reference": actual}
                try:
                    handoff = prepare(request)
                except (ContractError, ValueError, OSError):
                    return result(
                        fresh,
                        "uncertain",
                        "handoff_unavailable",
                        effect="confirmed",
                        resulting=actual,
                    )
                if handoff["route"] != "claude_attach":
                    return result(
                        fresh,
                        "uncertain",
                        "handoff_unavailable",
                        effect="confirmed",
                        resulting=actual,
                    )
                return result(
                    fresh,
                    "ready",
                    "native_identity_verified",
                    effect="confirmed",
                    resulting=actual,
                    handoff=handoff,
                )
        except (ContractError, ValueError, OSError):
            break
        time.sleep(0.2)
    return result(
        fresh, "uncertain", "post_launch_identity_unavailable", effect="uncertain", pending=True
    )


def enter(plan):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ContractError("tty_required")
    fresh = revalidate(plan)
    argv, env = invocation(fresh)
    os.chdir(fresh["request"]["cwd"])
    os.execve(argv[0], argv, env)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command, flag in (("prepare", "--request"), ("execute", "--plan"), ("enter", "--plan")):
        item = commands.add_parser(command)
        item.add_argument(flag, type=Path, required=True, help="public JSON file, or - for stdin")
        if command == "execute":
            item.add_argument("--timeout", type=float, default=30)
    schema = commands.add_parser("schema")
    schema.add_argument("--kind", choices=("request", "plan", "result"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(canonical(schema_document(args.kind)))
            return 0
        path = args.request if args.command == "prepare" else args.plan
        if str(path) == "-":
            data = sys.stdin.buffer.read(32769)
        else:
            with path.open("rb") as stream:
                data = stream.read(32769)
        value = decode_document(data, max_bytes=32768)
        if args.command == "prepare":
            print(canonical(prepare(value)))
        elif args.command == "execute":
            if not 1 <= args.timeout <= 60:
                raise ContractError("invalid_write_timeout")
            output = execute(value, timeout=args.timeout)
            print(canonical(output))
            return 0 if output["status"] in {"prepared", "ready"} else 3
        else:
            enter(value)
        return 0
    except (ContractError, WireError):
        # Finite codes from the strictly controlled local exception classes.
        exc = sys.exc_info()[1]
        print(canonical({"schemaVersion": 1, "error": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print('{"schemaVersion":1,"error":"write_context_unavailable"}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
