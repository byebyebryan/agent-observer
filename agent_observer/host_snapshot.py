"""Provisional common command boundary for consumer-fit fixtures.

Provider failures stay independent. This command only calls passive study
collectors and does not start providers or perform consumer actions.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import socket
import time
import uuid
from pathlib import Path

from .claude_snapshot import collect_claude
from .codex_snapshot import collect_codex

_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}\Z", re.ASCII)
_PROVIDERS = frozenset({"codex", "claude"})


def compose(*, host_scope: str, provider_snapshots: list[dict]):
    """Compose already filtered facts without guessing or dropping ambiguity."""
    if not isinstance(host_scope, str) or not _SCOPE.fullmatch(host_scope):
        raise ValueError("invalid_host_scope")
    result = {
        "schemaVersion": 1,
        "collectionId": str(uuid.uuid4()),
        "collectedAt": time.time_ns() // 1_000_000,
        "host": {
            "authority": host_scope,
            "authoritySource": "caller",
            "nativeHostname": socket.gethostname(),
            "uid": os.geteuid(),
        },
        "sources": [],
        "sessions": [],
        "errors": [],
        "limitations": [
            "prerelease_contract",
            "host_local_only",
            "no_watch",
            "consumer_actions_not_provided",
        ],
    }
    seen_providers = set()
    keys: dict[tuple, list[dict]] = {}
    for native in provider_snapshots:
        provider = native.get("provider")
        if (
            not isinstance(provider, str)
            or provider not in _PROVIDERS
            or provider in seen_providers
        ):
            raise ValueError("invalid_provider_source")
        seen_providers.add(provider)
        if (
            native.get("schemaVersion") != 1
            or native.get("host", {}).get("authority") != host_scope
        ):
            raise ValueError("source_provenance_mismatch")
        source = copy.deepcopy(
            {key: value for key, value in native.items() if key not in {"sessions", "host"}}
        )
        result["sources"].append(source)
        for native_row in native["sessions"]:
            row = copy.deepcopy(native_row)
            identity = row.get("identity", {})
            if (
                identity.get("hostScope") != host_scope
                or identity.get("provider") != provider
                or identity.get("namespace") != native.get("namespace")
            ):
                raise ValueError("session_provenance_mismatch")
            key = tuple(
                identity.get(field)
                for field in (
                    "hostScope",
                    "provider",
                    "namespace",
                    "nativeIdKind",
                    "nativeId",
                )
            )
            if any(not isinstance(part, str) or not part for part in key):
                raise ValueError("invalid_session_identity")
            keys.setdefault(key, []).append(row)
            result["sessions"].append(row)
    for key, rows in keys.items():
        if len(rows) <= 1:
            continue
        result["errors"].append(
            {
                "code": "duplicate_native_identity",
                "provider": key[1],
                "namespace": key[2],
                "nativeId": key[4],
            }
        )
        for row in rows:
            for dimension in ("work", "presence"):
                evidence = row[dimension]
                if evidence.get("value") != "unknown":
                    evidence["lastKnownValue"] = evidence["value"]
                evidence.update(value="unknown", health="ambiguous", reason="identity_ambiguous")
    result["sourceHealth"] = (
        "current"
        if result["sources"]
        and not result["errors"]
        and all(source["sourceHealth"] == "current" for source in result["sources"])
        else "partial"
        if result["sessions"]
        or any(source["sourceHealth"] == "current" for source in result["sources"])
        else "unavailable"
    )
    return result


def collect_host(*, host_scope, providers, codex_home, claude_home):
    if (
        not providers
        or any(provider not in _PROVIDERS for provider in providers)
        or len(set(providers)) != len(providers)
    ):
        raise ValueError("invalid_provider_selection")
    started = time.monotonic()
    snapshots = []
    for provider in providers:
        collector, root = (
            (collect_codex, codex_home) if provider == "codex" else (collect_claude, claude_home)
        )
        snapshots.append(collector(root, host_scope=host_scope))
    result = compose(host_scope=host_scope, provider_snapshots=snapshots)
    result["durationMs"] = round((time.monotonic() - started) * 1000, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-scope", required=True)
    parser.add_argument("--provider", choices=sorted(_PROVIDERS), action="append")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
    )
    parser.add_argument(
        "--claude-home",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))),
    )
    args = parser.parse_args()
    try:
        value = collect_host(
            host_scope=args.host_scope,
            providers=args.provider or ["codex", "claude"],
            codex_home=args.codex_home,
            claude_home=args.claude_home,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(value, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
