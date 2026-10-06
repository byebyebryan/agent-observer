"""Host-local collection into the public v2 model; actions are separate."""

from __future__ import annotations

import copy
import os
import socket
import time
import uuid
from pathlib import Path

from .activity import unavailable
from .contract import SOURCE, identity_key, store_namespace, validate_shape, validate_snapshot


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
    config_home = native["configHome"]
    selector = native.get("configHomeKind", "explicit")
    namespace = store_namespace(provider, config_home, selector, native["host"]["uid"])
    runtime = native.get("runtime")
    if runtime:
        runtime = {
            name: runtime.get(name)
            for name in (
                "version",
                "binarySha256",
                "topology",
                "bootId",
                "pid",
                "startTicks",
                "endpoint",
            )
        }
    health = native.get("sourceHealth", "unavailable")
    if health == "current" and native.get("errors"):
        health = "partial"
    coverage = native.get("coverage", {})
    question_supported = provider == "claude" and any(
        "job_question" in row.get("phaseCapabilities", []) for row in native.get("sessions", [])
    )
    result = {
        "provider": provider,
        "namespace": namespace,
        "runtimeNamespace": native.get("namespace"),
        "configHome": config_home,
        "configHomeKind": selector,
        "runtime": runtime,
        "sourceHealth": health,
        "coverage": {
            "saved": _coverage(coverage.get("saved"), health),
            "runtime": _coverage(
                coverage.get("loaded") if provider == "codex" else coverage.get("sessionRegistry"),
                health,
            ),
        },
        "capabilities": {
            "phase": ["working", "blocked", "waiting"]
            if provider != "codex" or coverage.get("work", {}).get("supported") else [],
            "blockedReasons": ["approval", "question"] if question_supported else ["approval"]
            if provider != "codex" or "waitingOnApproval" in coverage.get("work", {}).get("supportedWaitFlags", []) else [],
            "runtime": ["running"]
            if provider != "codex" or coverage.get("loaded", {}).get("complete") else [],
            "activity": native.get("activitySupported") is True,
            "clientBinding": False,
        },
        "errors": list(
            dict.fromkeys(
                item["code"]
                for item in native.get("errors", [])
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            )
        ),
        "limitations": [
            "parked_predicate_unproved",
            "questions_unproved",
            "client_binding_unproved",
        ],
    }
    if not result["capabilities"]["activity"]:
        result["limitations"].append("activity_source_unproved")
    if provider == "codex":
        if result["coverage"]["saved"]["status"] == "unavailable":
            result["limitations"].append("saved_metadata_unavailable")
        result["limitations"].append("offline_runtime_state_unavailable")
        result["limitations"].append("unloaded_work_state_unavailable")
        result["limitations"].append("unbound_tui_contexts_unobserved")
    else:
        result["limitations"].append("interactive_readiness_requires_current_worker_image")
        result["limitations"].append("background_readiness_requires_no_pending_work")
        result["limitations"].extend(reason for reason in native.get("limitations", []) if reason in {
            "history_sdk_candidates_omitted", "history_candidates_unresolved",
            "history_duplicate_companions", "history_invalid_filename_candidates",
        })
    result["coverage"]["runtime"]["scope"] = (
        "loaded_threads" if provider == "codex" else "registered_workers"
    )
    validate_shape(result, SOURCE)
    return result


def project_session(native, source):
    identity = copy.deepcopy(native["identity"])
    identity["namespace"] = source["namespace"]
    provider = identity["provider"]
    ids = native["nativeIds"]
    native_presence = native.get("presence", {})
    runtime = fact(native_presence, {"present": "running"}, sampled=True)
    # Absence of a worker or absence from capped history is not absence of all
    # runtime context. Parked remains unsupported in this source milestone.
    if runtime["value"] == "unknown" and runtime["health"] == "current":
        runtime = unknown("parked_predicate_unproved", "unsupported")
    worker = (
        fact(native_presence, {"present": "present", "absent": "absent"}, sampled=True)
        if provider == "claude"
        else unknown("worker_presence_unproved", "unsupported")
    )
    mapping = {"working": "working", "needs_input": "blocked"}
    if provider == "codex" and runtime["value"] == "running":
        mapping["settled"] = "waiting"
    claude_ready = (
        provider == "claude"
        and native.get("sessionKind") == "bg"
        and worker["value"] == "present"
        and (native.get("job") or {}).get("state") == "done"
        and native.get("work", {}).get("source") == "claude_job_store"
    )
    claude_ready |= (
        provider == "claude" and native.get("sessionKind") == "interactive"
        and worker["value"] == "present" and ids.get("jobId") is None
        and "interactive_readiness" in native.get("phaseCapabilities", [])
        and native.get("work", {}).get("source") == "claude_registry"
    )
    if claude_ready:
        mapping["settled"] = "waiting"
    phase = fact(native.get("work"), mapping)
    question = (provider == "claude" and native.get("waitReason") == "question"
                and "job_question" in native.get("phaseCapabilities", []))
    if phase["value"] == "blocked" and native.get("waitReason") != "approval" and not question:
        phase = unknown("questions_unproved", "unsupported")
    if (
        native.get("work", {}).get("value") == "settled"
        and provider == "claude"
        and not claude_ready
    ):
        phase = unknown("interactive_readiness_unproved", "unsupported")
    if provider == "claude" and phase["value"] == "unknown":
        if "native_blocked_phase_unproved" in native.get("metadataIssues", []):
            phase = unknown("native_blocked_phase_unproved", "unsupported")
        elif (
            native.get("sessionKind") == "bg"
            and runtime["value"] == "running"
            and (native.get("nativeStatus") or {}).get("value") == "idle"
            and (native.get("job") or {}).get("state") == "working"
        ):
            phase = unknown("background_readiness_unproved", "unsupported")
    outcome = unknown("outcome_source_unproved", "unsupported")
    if provider == "codex" and "outcome" in native:
        outcome = fact(native["outcome"], {v: v for v in ("completed", "failed", "cancelled")})
    if provider == "codex" and (native.get("nativeState") or {}).get("type") == "systemError":
        phase = unknown("native_runtime_error", "unsupported")
    if (
        provider == "claude"
        and native.get("work", {}).get("source") == "claude_job_store"
        and native["work"].get("value") == "settled"
    ):
        outcome = fact(native["work"], {"settled": "completed"})
    history = copy.deepcopy(native.get("history"))
    times = native.get("nativeHistoryTimes", {})
    kind = (
        native.get("threadKind", "unknown")
        if provider == "codex"
        else "user"
        if (
            native.get("activity", {}).get("health") == "current"
            and native.get("activity", {}).get("source") == "claude_transcript_message"
            and native.get("activity", {}).get("reason") == "native_conversation_event"
            and native.get("activity", {}).get("at") is not None
        )
        else "unknown"
    )
    return {
        "identity": identity,
        "nativeIds": {
            "threadId": ids.get("threadId"),
            "sessionId": ids["sessionId"],
            "jobId": ids.get("jobId"),
        },
        "title": native["title"],
        "kind": kind,
        "cwd": native.get("cwd"),
        "cwdSource": native.get("cwdSource", "codex_rpc" if native.get("cwd") else None),
        "inventory": native.get("inventory", "registry"),
        "phase": phase,
        "runtime": runtime,
        "worker": worker,
        "attachment": fact(
            native.get("attachment"), {"attached": "attached", "detached": "detached"}
        ),
        "outcome": outcome,
        "blockedReason": ("question" if question else "approval" if native.get("waitReason") == "approval" else "unknown") if phase["value"] == "blocked" else "unknown",
        "createdAt": times.get("createdAt")
        if provider == "codex"
        else history.get("createdAt")
        if history
        else None,
        "activity": copy.deepcopy(
            native.get("activity", unavailable("activity_source_unproved", "unsupported"))
        ),
        "workspace": None,
        "sessionKind": native.get("sessionKind")
        if native.get("sessionKind") in {"interactive", "bg"}
        else "unknown",
        "job": copy.deepcopy(native.get("job")),
        "history": history,
        "metadataIssues": list(native.get("metadataIssues", [])),
    }


def compose_v2(*, host_scope, provider_snapshots):
    result = {
        "schemaVersion": 2,
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
            duplicate = next(
                (
                    old
                    for old in result["sessions"]
                    if identity_key(old["identity"]) == identity_key(projected["identity"])
                ),
                None,
            )
            if duplicate is not None:
                for dimension in ("phase", "runtime", "worker", "attachment", "outcome"):
                    duplicate[dimension] = unknown("identity_ambiguous", "ambiguous")
                duplicate["metadataIssues"] = list(
                    dict.fromkeys(duplicate["metadataIssues"] + ["duplicate_native_identity"])
                )
                source["sourceHealth"] = "partial"
                source["errors"] = list(
                    dict.fromkeys(source["errors"] + ["duplicate_native_identity"])
                )
                continue
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
    from .claude_snapshot import collect_claude
    from .codex_snapshot import collect_codex

    if (
        not providers
        or len(set(providers)) != len(providers)
        or any(p not in {"codex", "claude"} for p in providers)
    ):
        raise ValueError("invalid_provider_selection")
    snapshots = [
        collect_codex(Path(codex_home), host_scope=host_scope)
        if p == "codex"
        else collect_claude(Path(claude_home), host_scope=host_scope)
        for p in providers
    ]
    result = compose_v2(host_scope=host_scope, provider_snapshots=snapshots)
    from .workspace import enrich

    enrich(result, workspace_config or {"roots": [], "projects": []})
    return validate_snapshot(result)
