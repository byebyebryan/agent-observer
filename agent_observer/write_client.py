"""Explicit New/Resume client. Never imported by passive observation or reads."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
import time
from pathlib import Path

from .bounded_json import WireError, decode_document
from .contract import ContractError, canonical, store_namespace
from .native_artifacts import CODEX
from .read_client import select as select_session
from .write_contract import schema_document, validate_plan, validate_request, validate_result

EXECUTABLES = {"codex": CODEX.path}
_OBSERVATION_ONLY_ISSUES = frozenset(
    {
        "native_history_time_unavailable",
    }
)


def _digest(path, limit, timeout=3, *, executable=False):
    digest = hashlib.sha256()
    deadline = time.monotonic() + timeout
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode) or before.st_size > limit or before.st_mode & 0o022
            or before.st_uid not in {0, os.geteuid()}
            or executable and (not before.st_mode & 0o111 or not os.access(path, os.X_OK))
        ):
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


def _directory(value, *, owned=False, unavailable_code="directory_unavailable"):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ContractError("noncanonical_directory")
    try:
        resolved = path.resolve(strict=True)
        info = path.stat()
    except OSError:
        raise ContractError(unavailable_code) from None
    if resolved != path:
        raise ContractError("noncanonical_directory")
    if not stat.S_ISDIR(info.st_mode) or (owned and info.st_uid != os.geteuid()):
        raise ContractError(unavailable_code)
    return {"device": info.st_dev, "inode": info.st_ino}


def _collect(request):
    from .codex_exact import collect_exact

    try:
        return collect_exact(request["configHome"], host_scope=request["hostScope"],
                             thread_id=request["reference"]["nativeId"])
    except ValueError:
        raise ContractError("resume_evidence_unavailable") from None


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
        or set(row["metadataIssues"]) - _OBSERVATION_ONLY_ISSUES
        or source["configHome"] != request["configHome"]
        or source["configHomeKind"] != request["configHomeKind"]
        or source["runtime"] is None
        or source["sourceHealth"] not in {"current", "partial"}
    ):
        raise ContractError("resume_evidence_unavailable")
    if request["provider"] == "codex":
        if source["coverage"].get("runtime", {}).get("status") == "unavailable":
            raise ContractError("resume_evidence_unavailable")
    expected = store_namespace(
        request["provider"], request["configHome"], request["configHomeKind"], os.geteuid()
    )
    if source["namespace"] != expected or row["cwd"] != request["cwd"]:
        raise ContractError("resume_context_changed")
    if row["runtime"]["health"] in {"stale", "ambiguous"} or row["phase"] is not None and row["phase"]["health"] == "ambiguous":
        raise ContractError("resume_evidence_unavailable")
    if row["nativeIds"]["threadId"] != row["nativeIds"]["sessionTreeRootId"]:
        raise ContractError("session_tree_entry_unproved")
    return row, source


def prepare(request):
    validate_request(request)
    provider = request["provider"]
    if provider != "codex":
        raise ContractError("unsupported_provider")
    cwd = _directory(request["cwd"], unavailable_code="cwd_unavailable")
    config = _directory(request["configHome"], owned=True, unavailable_code="config_home_unavailable")
    if provider == "codex" and request["configHomeKind"] != "explicit":
        raise ContractError("unsupported_config_selector")
    executable = EXECUTABLES[provider]
    binary_hash, binary = _digest(Path(executable), 512 * 1024 * 1024, executable=True)
    settings = Path(request["configHome"]) / "config.toml"
    settings_hash = _digest(settings, 1024 * 1024)[0] if settings.exists() else None
    runtime_token = None
    if request["operation"] == "new":
        route = "codex_new"
    else:
        row, source = _target(request)
        runtime_token = hashlib.sha256(
            canonical([source["runtimeNamespace"], source["runtime"],
                       row["identity"], row["cwd"]]).encode()
        ).hexdigest()
        route = "codex_resume"
    plan = {
        "schemaVersion": 2,
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


def invocation(plan):
    """Derive native argv locally; caller cannot supply executable/arguments."""
    request = plan["request"]
    provider = request["provider"]
    argv = [EXECUTABLES[provider]]
    env = os.environ.copy()
    if provider == "codex":
        env["CODEX_HOME"] = request["configHome"]
        if plan["route"] == "codex_resume":
            row, _ = _target(request)
            argv.extend(["resume", "--all", row["nativeIds"]["threadId"]])
    return argv, env


def result(plan, status, reason, effect="none", resulting=None, handoff=None, pending=False):
    return validate_result(
        {
            "schemaVersion": 2,
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
    # Preparation has no provider effect. The foreground client owns entry.
    fresh = revalidate(plan)
    return result(fresh, "prepared", "tty_handoff_required", handoff=fresh,
                  pending=fresh["route"] == "codex_new")


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
        inputs = item.add_mutually_exclusive_group(required=True)
        inputs.add_argument(flag, type=Path, help="public JSON file, or - for stdin")
        inputs.add_argument(
            flag + "-json", help="bounded literal public JSON; no shell interpretation"
        )
        if command == "execute":
            item.add_argument("--timeout", type=float, default=30)
    schema = commands.add_parser("schema")
    schema.add_argument("--kind", choices=("request", "plan", "result"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(canonical(schema_document(args.kind)))
            return 0
        literal = args.request_json if args.command == "prepare" else args.plan_json
        path = args.request if args.command == "prepare" else args.plan
        if literal is not None:
            data = literal.encode("utf-8")
        elif str(path) == "-":
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
        print(canonical({"schemaVersion": 2, "error": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print('{"schemaVersion":2,"error":"write_context_unavailable"}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
