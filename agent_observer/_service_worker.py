"""Owned single-provider metadata collector; never a native provider launcher."""

import os
import signal
import socket
import sys
from pathlib import Path

# Invoked by an installed/source absolute file with Python -I. Import only its
# own package tree, never the working directory or user Python search path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    def deadline(*_args):
        # This entry is invoked only as an owned session/group leader. The
        # private helper group survives publisher SIGKILL, so its own deadline
        # must still stop every nested metadata helper.
        if os.getpgrp() == os.getpid() and os.getsid(0) == os.getpid():
            os.killpg(os.getpid(), signal.SIGKILL)
        raise SystemExit(2)
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 1)
    from agent_observer.bounded_json import decode_document
    from agent_observer.collection import compose_snapshot
    from agent_observer.contract import canonical
    from agent_observer.workspace import MAX_CONFIG_BYTES, enrich, validate_config

    request_limit = MAX_CONFIG_BYTES + 16384
    request = decode_document(sys.stdin.buffer.read(request_limit + 1), max_bytes=request_limit)
    keys = {"hostScope", "provider", "component", "configHome", "configHomeKind", "timeoutMs", "workspaceConfig"}
    if set(request) not in (keys, keys | {"imageMemoFd"}):
        raise ValueError("service_worker_request")
    if type(request["timeoutMs"]) is not int or not 1000 <= request["timeoutMs"] <= 30000:
        raise ValueError("service_worker_timeout")
    if os.getpgrp() != os.getpid() or os.getsid(0) != os.getpid():
        raise ValueError("service_worker_ownership")
    signal.setitimer(signal.ITIMER_REAL, request["timeoutMs"] / 1000)
    provider, component = request["provider"], request["component"]
    if provider not in {"codex", "claude"} or component not in {"runtime", "history"}:
        raise ValueError("service_worker_request")
    if component == "history":
        validate_config(request["workspaceConfig"])
        if len(canonical(request["workspaceConfig"]).encode()) > MAX_CONFIG_BYTES:
            raise ValueError("service_worker_workspace_limit")
    elif request["workspaceConfig"] is not None:
        raise ValueError("service_worker_workspace_scope")
    home = Path(request["configHome"])
    if request["configHomeKind"] not in {"explicit", "default"}:
        raise ValueError("service_worker_request")
    memo, channel = None, None
    try:
        if "imageMemoFd" in request:
            from agent_observer._image_memo import ImageMemo, receive, send
            descriptor = request['imageMemoFd']
            if type(descriptor) is not int or not 3 <= descriptor <= 1048576:
                raise ValueError("service_worker_memo_descriptor")
            channel = socket.socket(fileno=descriptor)
            os.set_inheritable(descriptor, False)
            if channel.family != socket.AF_UNIX or channel.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
                raise ValueError("service_worker_memo_channel")
            channel.settimeout(.5)
            try:
                memo = receive(channel, provider)
            except (ValueError, OSError):
                memo = ImageMemo(provider)
        image_args = {"image_cache": memo} if memo is not None else {}
        if provider == "codex":
            if request["configHomeKind"] != "explicit":
                raise ValueError("service_worker_selector")
            from agent_observer.codex_snapshot import collect_codex
            native = collect_codex(home, host_scope=request["hostScope"], include_history=component == "history", **image_args)
        else:
            if request["configHomeKind"] == "explicit":
                os.environ["CLAUDE_CONFIG_DIR"] = str(home)
            else:
                if home != Path.home() / ".claude":
                    raise ValueError("service_worker_selector")
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            from agent_observer.claude_snapshot import collect_claude
            native = collect_claude(home, host_scope=request["hostScope"], include_history=component == "history", owned_worker_group=True, **image_args)
        value = compose_snapshot(host_scope=request["hostScope"], provider_snapshots=[native])
        if component == "history":
            enrich(value, request["workspaceConfig"])
        if channel is not None:
            try:
                send(channel, memo)
            except (ValueError, OSError):
                pass
        sys.stdout.write(canonical(value))
        return 0
    finally:
        if memo is not None:
            memo.close()
        if channel is not None:
            channel.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # No exception details or raw native contents cross this private pipe.
        raise SystemExit(2) from None
