"""Explicit reader-only selection/rollback; never stop/restart a service."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

PROTECTED = (
    ".local/bin/agent-observer-service", ".local/bin/agent-observer-write", ".local/bin/mesh-plus",
    ".config/mesh-plus/sources.toml", ".config/systemd/user/agent-observer.service",
    ".config/systemd/user/mesh-plus-agent.service", ".config/systemd/user/mesh-plus-tmux.service",
    ".codex/config.toml", ".config/agent-observer/workspace.json",
)
UNITS = ("agent-observer.service", "mesh-plus-agent.service", "mesh-plus-tmux.service", "rlcd-agent-dashboard.service")


def command(argv):
    return subprocess.run(argv, capture_output=True, check=True, timeout=45, cwd="/tmp").stdout


def protected():
    files = {}
    for name in PROTECTED:
        path = Path.home() / name
        if path.is_symlink():
            files[name] = {"link": os.readlink(path)}
        elif path.exists():
            files[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": path.stat().st_mode & 0o777}
        else:
            files[name] = None
    units = command(["systemctl", "--user", "show", *UNITS, "-p", "Id", "-p", "MainPID", "-p", "NRestarts", "-p", "ActiveState"])
    return {"files": files, "units": units.decode()}


def swap(link, target):
    temporary = link.with_name(link.name + ".prepared-owned-" + str(os.getpid()))
    temporary.symlink_to(target)
    os.replace(temporary, link)


def main(args):
    link = Path.home() / ".local/bin/agent-observer"
    if not link.is_symlink() or link.lstat().st_uid != os.getuid():
        raise ValueError("reader_link_owner")
    prior = os.readlink(link)
    target = command(["chezmoi", "--source", str(args.source), "--refresh-externals=never", "cat", str(link)]).decode().strip()
    if target != str(Path.home() / ".local/share/agent-observer/0.7.0a2-d4a37999bcf5652d-mesh-a18-prepared/bin/agent-observer"):
        raise ValueError("reader_target_binding")
    baseline = protected()
    selected = False
    try:
        swap(link, target)
        selected = True
        new_version = command([str(link), "--version"]).decode().strip()
        if new_version != "agent-observer 0.7.0a2":
            raise ValueError("reader_version")
        command([str(link), "mesh", "watch", "--human", "--prepared", "--scope", "local", "--local-host", args.host, "--count", "2"])
        if protected() != baseline:
            raise ValueError("protected_selection_changed")
        swap(link, prior)
        selected = False
        old_version = command([str(link), "--version"]).decode().strip()
        status = json.loads(command([str(link), "service", "status", "--host-scope", args.host]))
        if old_version != "agent-observer 0.7.0a1" or status["state"] != "ready":
            raise ValueError("reader_rollback_not_ready")
        swap(link, target)
        selected = True
        if protected() != baseline or command([str(link), "--version"]).decode().strip() != new_version:
            raise ValueError("reader_reselection_changed")
    except BaseException:
        if selected and os.readlink(link) == target:
            swap(link, prior)
        raise
    return {"status": "accepted", "host": args.host, "priorReader": prior, "selectedReader": target,
            "priorVersion": old_version, "selectedVersion": new_version, "rollbackReselection": True,
            "protectedBeforeAfter": baseline, "serviceRestarts": 0, "providerActions": 0,
            "onlyLiveTargetChanged": ".local/bin/agent-observer"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("snap", "starship"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(main(args), indent=2) + "\n")
