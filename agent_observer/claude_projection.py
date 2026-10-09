"""Claude native evidence into the shared passive model; no provider execution."""

import copy

from .activity import unavailable
from .collection import _coverage, fact, unknown
from .contract import SOURCE, store_namespace, validate_shape


def project_source(native):
    selector = native.get("configHomeKind", "explicit")
    health = native.get("sourceHealth", "unavailable")
    errors = list(dict.fromkeys(e["code"] for e in native.get("errors", [])
                               if isinstance(e, dict) and isinstance(e.get("code"), str)))
    if health == "current" and errors:
        health = "partial"
    coverage = native.get("coverage", {})
    components = [coverage.get(k) for k in ("sessionRegistry", "jobStore", "workerPresence")]
    complete = all(c == "complete" for c in components)
    raw_runtime = native.get("runtime")
    runtime = {k: raw_runtime.get(k) for k in (
        "version", "binarySha256", "topology", "bootId", "pid", "startTicks", "endpoint",
    )} if raw_runtime else None
    value = {
        "provider": "claude",
        "namespace": store_namespace("claude", native["configHome"], selector, native["host"]["uid"]),
        "runtimeNamespace": native.get("namespace"), "configHome": native["configHome"],
        "configHomeKind": selector, "runtime": runtime, "sourceHealth": health,
        "discovery": None,
        "coverage": {
            "saved": _coverage(coverage.get("saved"), health),
            "runtime": {"status": "complete" if complete else "partial" if any(
                c in {"complete", "partial"} for c in components
            ) else "unavailable", "reason": "native_registered_scope" if complete else "source_incomplete",
                        "scope": "provider_sessions"},
        },
        "capabilities": {"phase": ["working", "blocked", "waiting"],
                         "blockedReasons": ["approval", "question"],
                         "runtime": ["running"] + (["parked"] if native.get("parkedSupported") else []),
                         "activity": native.get("activitySupported") is True},
        "errors": errors,
        "limitations": ["one_configured_namespace", "private_required_contract",
                        "saved_only_runtime_unproved", "unregistered_background_runtime_unproved",
                        "generic_dialog_unproved", "saved_child_roster_provider_excluded"],
    }
    validate_shape(value, SOURCE)
    return value


def project_session(native, source):
    identity = copy.deepcopy(native["identity"])
    identity["namespace"] = source["namespace"]
    saved = native.get("savedIdentity") is True or isinstance(native.get("history"), dict)
    presence = native.get("presence") or {}
    work = native.get("work") or {}
    runtime = unknown("native_runtime_unproved", "unsupported")
    phase = unknown("runtime_unavailable", "unsupported")
    reasons = []
    conflicts = {"job_session_conflict", "duplicate_session_job_pair", "invalid_job_reference"}
    if conflicts.intersection(native.get("metadataIssues", [])):
        runtime = unknown("identity_ambiguous", "ambiguous")
    elif presence.get("value") == "present" and presence.get("health") == "current":
        # A stable authenticated registration supplies the current native read,
        # including its status. Process liveness alone cannot refresh phase.
        runtime = fact({**presence, "value": "running"}, {"running": "running"}, sampled=True)
        phase = fact(work, {"working": "working", "needs_input": "blocked", "settled": "waiting"})
        if (type(work.get("observedAt")) is not int or type(presence.get("observedAt")) is not int
                or not 0 <= work["observedAt"] <= presence["observedAt"]):
            phase = unknown("status_clock_unavailable", "unsupported")
        if phase["value"] != "unknown":
            phase.update(source=runtime["source"], observedAt=runtime["observedAt"], clock="sample")
        if phase["value"] == "blocked":
            wait = native.get("waitReason")
            if wait in {"approval", "question"}:
                reasons = [wait]
            else:
                phase = unknown("unsupported_wait_reason", "unsupported")
    elif saved and (native.get("runtimeDisposition") or {}).get("value") == "parked":
        runtime = fact(native["runtimeDisposition"], {"parked": "parked"}, sampled=True)
    if runtime["value"] == "parked":
        phase = None
    activity = copy.deepcopy(native.get("activity", unavailable("activity_source_unproved")))
    kind = native.get("threadKind", "unknown")
    history = native.get("history") or {}
    return {
        "identity": identity, "nativeIds": {"sessionId": native["nativeIds"]["sessionId"]},
        "title": native["title"], "kind": kind,
        "cwd": native.get("cwd"), "cwdSource": native.get("cwdSource"),
        "inventory": "saved" if saved else "live",
        "runtime": runtime, "phase": phase, "blockedReasons": reasons, "hasSavedHistory": saved,
        "outcome": unknown("outcome_source_unproved", "unsupported"),
        "createdAt": history.get("createdAt"), "activity": activity, "workspace": None,
        "metadataIssues": list(native.get("metadataIssues", [])),
    }
