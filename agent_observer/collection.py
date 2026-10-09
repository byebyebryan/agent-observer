"""Host-local collection into the public observation model; actions are separate."""

from __future__ import annotations

import copy
import os
import socket
import time
import uuid
from pathlib import Path

from .activity import unavailable
from .contract import (
    SCHEMA_VERSION,
    SOURCE,
    identity_key,
    store_namespace,
    validate_shape,
    validate_snapshot,
)


def unknown(reason="unobserved", health="unavailable"):
    return {
        "value": "unknown",
        "observedAt": None,
        "source": None,
        "health": health,
        "reason": reason,
        "clock": None,
    }


def fact(original, values, *, sampled=False):
    if not isinstance(original, dict):
        return unknown()
    current = original.get("health") == "current"
    original_value = original.get("value")
    value = values.get(original_value, "unknown") if current else "unknown"
    result = {
        "value": value,
        "observedAt": original.get("observedAt"),
        "source": original.get("source"),
        "health": original.get("health", "unavailable"),
        "reason": original.get("reason", "unobserved"),
        "clock": "sample"
        if (sampled and original.get("source")) or original.get("source") == "codex_rpc"
        else "native"
        if original.get("source")
        else None,
    }
    last_known = values.get(original.get("lastKnownValue"))
    if last_known:
        result["lastKnownValue"] = last_known
    return result


def _coverage(value, health):
    if isinstance(value, dict):
        return {
            "status": "complete"
            if value.get("complete") is True
            else "partial"
            if (health in {"current", "partial"} or value.get("reason") == "metadata_scan")
            and value.get("reason") not in {"source_failed", "not_observed"}
            else "unavailable",
            "reason": value.get("reason", "not_observed"),
        }
    return {
        "status": value
        if value in {"complete", "partial", "unavailable", "unsupported"}
        else "unavailable",
        "reason": "native_snapshot" if value == "complete" else "source_incomplete",
    }


def project_source(native):
    provider = native["provider"]
    if provider != "codex":
        raise ValueError("unsupported_provider")
    selector = native.get("configHomeKind", "explicit")
    namespace = store_namespace(provider, native["configHome"], selector, native["host"]["uid"])
    raw_runtime = native.get("runtime")
    runtime = {name: raw_runtime.get(name) for name in (
        "version", "binarySha256", "topology", "bootId", "pid", "startTicks", "endpoint",
    )} if raw_runtime else None
    health = native.get("sourceHealth", "unavailable")
    if health == "current" and native.get("errors"):
        health = "partial"
    coverage = native.get("coverage", {})
    supported = coverage.get("work", {}).get("supported") is True
    result = {
        "provider": provider, "namespace": namespace,
        "runtimeNamespace": native.get("namespace"), "configHome": native["configHome"],
        "configHomeKind": selector, "runtime": runtime, "sourceHealth": health,
        "discovery": copy.deepcopy(native.get("discovery")),
        "coverage": {
            "saved": _coverage(coverage.get("saved"), health),
            "runtime": {**_coverage(coverage.get("daemon", coverage.get("loaded")), health), "scope": "daemon_threads"},
        },
        "capabilities": {
            "phase": ["working", "blocked", "waiting"] if supported else [],
            "blockedReasons": ["approval", "question"] if supported else [],
            "runtime": ["running", "parked"] if supported else [],
            "activity": native.get("activitySupported") is True,
        },
        "errors": list(dict.fromkeys(item["code"] for item in native.get("errors", [])
                                      if isinstance(item, dict) and isinstance(item.get("code"), str))),
        "limitations": ["one_configured_namespace", "offline_runtime_state_unavailable", "native_status_required"],
    }
    result["limitations"].extend(native.get("limitations", []))
    result["limitations"] = list(dict.fromkeys(result["limitations"]))[:128]
    validate_shape(result, SOURCE)
    return result


def project_session(native, source):
    identity = copy.deepcopy(native["identity"])
    identity["namespace"] = source["namespace"]
    if identity["provider"] != "codex":
        raise ValueError("unsupported_provider")
    ids = native["nativeIds"]
    runtime = fact(native.get("runtimeDisposition"), {"running": "running", "parked": "parked"}, sampled=True)
    phase = fact(native.get("work"), {"working": "working", "needs_input": "blocked", "settled": "waiting"})
    reasons = []
    if runtime["value"] == "parked":
        phase = None
    elif runtime["value"] != "running":
        phase = unknown("runtime_unavailable", runtime["health"])
    elif (native.get("nativeState") or {}).get("type") == "systemError":
        phase = unknown("native_runtime_error", "unsupported")
    elif phase["value"] == "blocked":
        flags = (native.get("nativeState") or {}).get("activeFlags", [])
        valid = isinstance(flags, list) and all(isinstance(f, str) and f in {"waitingOnApproval", "waitingOnUserInput"} for f in flags)
        reasons = sorted({{"waitingOnApproval": "approval", "waitingOnUserInput": "question"}[f] for f in flags}) if valid else []
        if not reasons or not set(reasons) <= set(source["capabilities"]["blockedReasons"]):
            phase, reasons = unknown("unsupported_wait_flags", "unsupported"), []
    times = native.get("nativeHistoryTimes", {})
    return {
        "identity": identity,
        "nativeIds": {"threadId": ids["threadId"], "sessionTreeRootId": ids["sessionId"]},
        "title": native["title"], "kind": native.get("threadKind", "unknown"),
        "cwd": native.get("cwd"), "cwdSource": native.get("cwdSource", "codex_rpc" if native.get("cwd") else None),
        "inventory": native.get("inventory", "saved"), "phase": phase, "runtime": runtime,
        "hasSavedHistory": native.get("savedIdentity", native.get("inventory") == "saved"),
        "outcome": fact(native.get("outcome"), {v: v for v in ("completed", "failed", "cancelled")}),
        "blockedReasons": reasons, "createdAt": times.get("createdAt"),
        "activity": copy.deepcopy(native.get("activity", unavailable("activity_source_unproved", "unsupported"))),
        "workspace": None, "metadataIssues": list(native.get("metadataIssues", [])),
    }


def compose_snapshot(*, host_scope, provider_snapshots):
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "collectionId": str(uuid.uuid4()),
        "collectedAt": time.time_ns() // 1_000_000,
        "host": {
            "authority": host_scope,
            "authoritySource": "caller",
            "nativeHostname": socket.gethostname(),
            "uid": os.geteuid(),
        },
        "sourceHealth": "unavailable",
        "sources": [],
        "sessions": [],
        "errors": [],
        "limitations": [
            "prerelease_contract",
            "host_local_only",
            "sampled_watch",
            "no_native_event_replay",
        ],
    }
    identities = {}
    for native in provider_snapshots:
        if native.get("host", {}).get("authority") != host_scope:
            raise ValueError("source_provenance_mismatch")
        source = project_source(native)
        result["sources"].append(source)
        for row in native["sessions"]:
            if (
                row["identity"]["namespace"] != native.get("namespace")
                or row["identity"]["provider"] != native["provider"]
            ):
                raise ValueError("session_provenance_mismatch")
            projected = project_session(row, source)
            key = identity_key(projected["identity"])
            duplicate = identities.get(key)
            if duplicate is not None:
                for dimension in ("phase", "runtime", "outcome"):
                    duplicate[dimension] = unknown("identity_ambiguous", "ambiguous")
                duplicate["metadataIssues"] = list(
                    dict.fromkeys(duplicate["metadataIssues"] + ["duplicate_native_identity"])
                )
                source["sourceHealth"] = "partial"
                source["errors"] = list(
                    dict.fromkeys(source["errors"] + ["duplicate_native_identity"])
                )
                continue
            identities[key] = projected
            result["sessions"].append(projected)
    result["sourceHealth"] = (
        "current"
        if result["sources"]
        and all(source["sourceHealth"] == "current" for source in result["sources"])
        else "partial"
        if result["sessions"]
        or any(source["sourceHealth"] == "current" for source in result["sources"])
        else "unavailable"
    )
    return validate_snapshot(result)


def collect(*, host_scope, providers, codex_home, claude_home, workspace_config=None):
    # Imports belong to the collecting path, not the public fixture reader.
    from .adapters import select_adapters

    adapters = select_adapters(providers)
    homes = {"codex": codex_home, "claude": claude_home}
    snapshots = [
        adapter.collect(Path(homes[adapter.provider]), host_scope=host_scope)
        for adapter in adapters
    ]
    result = compose_snapshot(host_scope=host_scope, provider_snapshots=snapshots)
    from .workspace import enrich

    enrich(result, workspace_config or {"roots": [], "projects": []})
    return validate_snapshot(result)
