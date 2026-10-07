"""Owned single-provider metadata collector; never a native provider launcher."""

from pathlib import Path
import os
import sys

# Invoked by an installed/source absolute file with Python -I. Import only its
# own package tree, never the working directory or user Python search path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    from agent_observer.bounded_json import decode_document
    from agent_observer.collection import compose_snapshot
    from agent_observer.contract import canonical

    request = decode_document(sys.stdin.buffer.read(16385), max_bytes=16384)
    if set(request) != {"hostScope", "provider", "component", "configHome", "configHomeKind"}:
        raise ValueError("service_worker_request")
    provider, component = request["provider"], request["component"]
    if provider not in {"codex", "claude"} or component not in {"runtime", "history"}:
        raise ValueError("service_worker_request")
    home = Path(request["configHome"])
    if request["configHomeKind"] not in {"explicit", "default"}:
        raise ValueError("service_worker_request")
    if provider == "codex":
        if request["configHomeKind"] != "explicit":
            raise ValueError("service_worker_selector")
        from agent_observer.codex_snapshot import collect_codex
        native = collect_codex(home, host_scope=request["hostScope"], include_history=component == "history")
    else:
        if request["configHomeKind"] == "explicit":
            os.environ["CLAUDE_CONFIG_DIR"] = str(home)
        else:
            if home != Path.home() / ".claude":
                raise ValueError("service_worker_selector")
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        from agent_observer.claude_snapshot import collect_claude
        native = collect_claude(home, host_scope=request["hostScope"], include_history=component == "history")
    value = compose_snapshot(host_scope=request["hostScope"], provider_snapshots=[native])
    if component == "history":
        from agent_observer.workspace import enrich
        enrich(value, {"roots": [], "projects": []})
    sys.stdout.write(canonical(value))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # No exception details or raw native contents cross this private pipe.
        raise SystemExit(2) from None
