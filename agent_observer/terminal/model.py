"""Pure terminal presentation model over the public working-set facade."""

from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from pathlib import PurePath

IDENTITY_FIELDS = ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
MEMBERSHIPS = ("active", "recent", "uncertain", "nonmember")
RUNTIMES = ("running", "parked", "unknown")
PHASES = ("working", "blocked", "waiting", "unknown")


def identity_tuple(identity: dict) -> tuple[str, ...]:
    if type(identity) is not dict or set(identity) != set(IDENTITY_FIELDS):
        raise ValueError("identity_shape")
    values = tuple(identity[name] for name in IDENTITY_FIELDS)
    if any(type(value) is not str for value in values):
        raise ValueError("identity_shape")
    return values


def safe_metadata(value) -> str | None:
    """Keep untrusted metadata literal and visible without terminal controls."""
    if type(value) is not str:
        return None
    output = []
    for char in value:
        category = unicodedata.category(char)
        if category.startswith("C") or category in {"Zl", "Zp"}:
            output.append(f"\\u{ord(char):04X}")
        else:
            output.append(char)
    return "".join(output)


def _bounded_reason(value) -> str | None:
    return value if type(value) is str and len(value) <= 128 else None


def _fact(value, *, parked: bool = False) -> dict:
    if type(value) is not dict:
        if parked:
            return {"value": None, "health": "not_applicable", "reason": None, "observedAt": None}
        return {
            "value": "unknown",
            "health": "unavailable",
            "reason": "fact_missing",
            "observedAt": None,
        }
    health = value.get("health")
    if health not in {"current", "stale", "unavailable", "unsupported", "ambiguous"}:
        health = "unavailable"
    current = health == "current"
    result = {
        "value": value.get("value") if current else "unknown",
        "health": health,
        "reason": _bounded_reason(value.get("reason")),
        "observedAt": value.get("observedAt"),
    }
    last_known = value.get("lastKnownValue")
    if not current and last_known is not None:
        result["lastKnownValue"] = last_known
    return result


def _activity(value) -> dict:
    if type(value) is not dict:
        return {
            "at": None,
            "health": "unavailable",
            "reason": "activity_missing",
            "lastKnownAt": None,
        }
    health = value.get("health")
    if health not in {"current", "stale", "unavailable", "unsupported", "ambiguous"}:
        health = "unavailable"
    current = health == "current"
    return {
        "at": value.get("at") if current else None,
        "health": health,
        "reason": _bounded_reason(value.get("reason")),
        "lastKnownAt": None if current else value.get("lastKnownAt"),
    }


def _source_context(source: dict) -> dict:
    return {
        "id": source["id"],
        "host": source["host"],
        "home": source["home"],
        "label": source["label"],
        "meshSource": source["meshSource"],
    }


def _base_session(
    row: dict,
    source: dict,
    lease: dict,
    now_boottime_ms: int,
    *,
    include_repository: bool = False,
    repository_now_boottime_ms: int | None = None,
) -> dict:
    identity = row["identity"]
    identity_tuple(identity)
    active_expiry = lease.get("activeExpiresAtMs")
    recent_expiry = lease.get("recentExpiresAtMs")
    active = type(active_expiry) is int and active_expiry > now_boottime_ms
    recent = type(recent_expiry) is int and recent_expiry > now_boottime_ms
    membership = "active" if active else "recent" if recent else "unqualified"
    raw_title = safe_metadata(row.get("title"))
    title = raw_title.strip() if raw_title else ""
    if not title:
        title = f"Codex {identity['nativeId']}"
    workspace = row.get("workspace") if type(row.get("workspace")) is dict else {}
    workspace_current = workspace.get("health") == "current"
    cwd = safe_metadata(row.get("cwd"))
    runtime = _fact(row.get("runtime"))
    is_parked = runtime["value"] == "parked"
    phase = _fact(row.get("phase"), parked=is_parked and runtime["health"] == "current")
    metadata_issues = row.get("metadataIssues")
    if type(metadata_issues) is not list:
        metadata_issues = []
    workspace_expiry = (lease.get("fieldExpiresAtMs") or {}).get("workspace")
    repository_support_current = (
        type(workspace_expiry) is int
        and type(repository_now_boottime_ms) is int
        and workspace_expiry > repository_now_boottime_ms
    )
    project_key = (
        safe_metadata(workspace.get("projectKey"))
        if workspace_current and (not include_repository or repository_support_current)
        else None
    )
    context = project_key or (
        safe_metadata(PurePath(row["cwd"]).name) if type(row.get("cwd")) is str else None
    )
    details = {
        "title": title,
        "cwd": cwd,
        "projectKey": project_key,
        "workspaceHealth": workspace.get("health"),
        "workspaceReason": _bounded_reason(workspace.get("reason")),
        "fieldExpiresAtBoottimeMs": {
            name: (lease.get("fieldExpiresAtMs") or {}).get(name)
            for name in (
                "runtime",
                "phase",
                "kind",
                "savedIdentity",
                "activity",
                "outcome",
                "workspace",
                "lastUpdated",
                "latestTurn",
            )
        },
        "metadataIssues": [
            safe_metadata(item) for item in metadata_issues if type(item) is str
        ],
        "blockedReasons": list(row.get("blockedReasons", ()))[:2],
    }
    if include_repository:
        repository_current = workspace_current and repository_support_current
        raw_repository = workspace.get("repo") if repository_current else None
        details["repo"] = (
            None
            if type(raw_repository) is not dict
            else {
                name: safe_metadata(raw_repository.get(name))
                for name in ("root", "commonDir", "relativePath")
            }
        )
        if workspace_current and not repository_support_current:
            details["workspaceHealth"] = "unavailable"
            details["workspaceReason"] = (
                "workspace_support_expired"
                if type(workspace_expiry) is int
                and type(repository_now_boottime_ms) is int
                and workspace_expiry <= repository_now_boottime_ms
                else "workspace_support_unavailable"
            )
    return {
        "identity": {key: identity[key] for key in IDENTITY_FIELDS},
        "source": _source_context(source),
        "label": title,
        "context": context,
        "kind": row.get("kind", "unknown"),
        "membership": membership,
        "membershipBranches": {
            "activeExpiresAtBoottimeMs": active_expiry,
            "recentExpiresAtBoottimeMs": recent_expiry,
            "membershipExpiresAtBoottimeMs": lease.get("membershipExpiresAtMs"),
        },
        "runtime": runtime,
        "phase": phase,
        "activity": _activity(row.get("activity")),
        "details": details,
    }


def _host_views(read) -> list[dict]:
    context = getattr(read, "context", None)
    if type(context) is not dict:
        return []
    hosts = context.get("hosts", ())
    return list(hosts) if type(hosts) in {list, tuple} else []


def _scope_doc(scope: dict, now_boottime_ms: int) -> dict:
    coverage = scope.get("coverage", {})
    status = coverage.get("status", "unavailable")
    expires = coverage.get("expiresAtMs")
    if status == "complete" and (type(expires) is not int or expires <= now_boottime_ms):
        status = "stale"
    return {
        "host": scope.get("hostScope"),
        "provider": scope.get("provider"),
        "namespace": scope.get("namespace"),
        "serviceId": scope.get("serviceId"),
        "contextGeneration": scope.get("contextGeneration"),
        "continuity": scope.get("continuity"),
        "coverage": {
            "status": status,
            "reason": _bounded_reason(coverage.get("reason")),
            "expiresAtBoottimeMs": expires,
        },
    }


def _source_doc(
    source_state: dict, now_boottime_ms: int, *, include_repository: bool = False
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    config = source_state["config"]
    read = source_state.get("read")
    source_now_ms = source_state.get("capture_boottime_ms")
    if type(source_now_ms) is not int:
        source_now_ms = now_boottime_ms
    scopes = [] if read is None else [_scope_doc(item, source_now_ms) for item in read.scopes]
    hosts = [] if read is None else _host_views(read)
    expected_host_views = [item for item in hosts if item.get("hostId") == config["host"]]
    delivery_states = [item.get("delivery", {}).get("status") for item in expected_host_views]
    delivery = delivery_states[0] if len(delivery_states) == 1 else "unavailable"
    observed_namespaces = sorted(
        {
            item.get("namespace")
            for item in scopes
            if item.get("provider") == "codex" and type(item.get("namespace")) is str
        }
    )
    observed_namespace = observed_namespaces[0] if len(observed_namespaces) == 1 else None
    lifecycle = source_state.get("lifecycle", "warming")
    reason = _bounded_reason(source_state.get("reason"))
    scope_complete = bool(scopes) and all(
        item["coverage"]["status"] == "complete" for item in scopes
    )
    if lifecycle == "blocked":
        health = "blocked"
    elif lifecycle in {"failed", "timed_out", "terminated"}:
        health = "unavailable"
    elif (
        lifecycle == "observing"
        and source_state.get("baseline") is True
        and delivery == "ready"
        and scope_complete
        and observed_namespace == config["namespace"]
        and reason is None
    ):
        health = "complete"
    elif not source_state.get("baseline"):
        health = "warming"
    elif any(item["coverage"]["status"] == "stale" for item in scopes):
        health = "stale"
    else:
        health = "partial"
    reasons = []
    if reason:
        reasons.append(reason)
    delivery_error = _bounded_reason(source_state.get("delivery_error"))
    if delivery_error and delivery_error not in reasons:
        reasons.append(delivery_error)
    for item in scopes:
        why = item["coverage"].get("reason")
        if why and why not in reasons:
            reasons.append(why)
    if not expected_host_views and "delivery_unavailable" not in reasons:
        reasons.append("delivery_unavailable")
    source_doc = {
        **_source_context(config),
        "scope": config["scope"],
        "expectedNamespace": config["namespace"],
        "observedNamespace": observed_namespace,
        "baseline": bool(source_state.get("baseline")),
        "delivery": delivery,
        "health": health,
        "reason": reason,
        "deliveryError": delivery_error,
        "reasons": reasons,
        "lastFrameBoottimeMs": source_state.get("last_frame_boottime_ms"),
        "captureBoottimeMs": source_now_ms,
        "scopes": scopes,
        "clock": source_state.get("clock"),
    }
    if read is None or lifecycle in {"blocked", "failed", "timed_out", "terminated"}:
        return source_doc, [], [], []
    leases = {identity_tuple(item["identity"]): item for item in read.member_leases}
    sessions = []
    for row in read.members:
        lease = leases.get(identity_tuple(row["identity"]), {})
        session = _base_session(
            row,
            config,
            lease,
            source_now_ms,
            include_repository=include_repository,
            repository_now_boottime_ms=now_boottime_ms,
        )
        if session["membership"] == "unqualified":
            # The public facade should remove expired positives on read. Do not
            # manufacture an uncertain/nonmember outcome from a local expiry.
            source_doc["health"] = "stale"
            if "membership_lease_unavailable" not in source_doc["reasons"]:
                source_doc["reasons"].append("membership_lease_unavailable")
            continue
        sessions.append(session)
    uncertain = [
        {
            "identity": {key: item["identity"][key] for key in IDENTITY_FIELDS},
            "source": _source_context(config),
            "label": f"Codex {item['identity']['nativeId']}",
            "context": None,
            "kind": "unknown",
            "membership": "uncertain",
            "reason": _bounded_reason(item.get("reason")) or "membership_unresolved",
        }
        for item in read.uncertain
    ]
    nonmembers = [
        {
            "identity": {key: item["identity"][key] for key in IDENTITY_FIELDS},
            "source": _source_context(config),
            "label": f"Codex {item['identity']['nativeId']}",
            "context": None,
            "kind": "unknown",
            "membership": "nonmember",
            "reason": _bounded_reason(item.get("reason")) or "known_nonmember",
        }
        for item in read.nonmembers
    ]
    return source_doc, sessions, uncertain, nonmembers


def _matches_query(row: dict, query) -> bool:
    if not query:
        return True
    identity = row["identity"]
    source = row["source"]
    details = row.get("details", {})
    repository = details.get("repo")
    repository_fields = (
        tuple(repository.get(name) for name in ("root", "commonDir", "relativePath"))
        if type(repository) is dict
        else ()
    )
    fields = (
        row.get("label"),
        row.get("context"),
        details.get("cwd"),
        details.get("projectKey"),
        source.get("host"),
        source.get("home"),
        identity.get("nativeId"),
        *repository_fields,
    )
    needles = (query,) if isinstance(query, str) else tuple(query)
    return any(
        isinstance(needle, str)
        and any(type(item) is str and needle.casefold() in item.casefold() for item in fields)
        for needle in needles
    )


def _row_sort_key(row: dict, sort: str) -> tuple:
    ident = identity_tuple(row["identity"])
    category = {"active": 0, "recent": 1, "uncertain": 2, "nonmember": 3}.get(row["membership"], 4)
    activity = row.get("activity", {}).get("at")
    age_key = (activity is None, -(activity or 0))
    if sort == "label":
        return (row.get("label", "").casefold(), ident)
    if sort == "host":
        source = row["source"]
        return (source["host"], source["home"], category, *age_key, ident)
    return (category, *age_key, ident)


def sort_rows(rows: list[dict], sort: str, group: str = "none") -> list[dict]:
    """Apply the maintained activity/label/host ordering to detached rows."""

    def key(row):
        order = _row_sort_key(row, sort)
        if group == "host-home":
            return (row["source"]["host"], row["source"]["home"], *order)
        return order

    return sorted(rows, key=key)


def _selector_list(values) -> list:
    return list(values or ())


def build_report(
    source_states: list[dict],
    *,
    now_boottime_ms: int,
    generated_at: str,
    clock: dict,
    mode: str,
    filters: dict,
    target: dict | str | None = None,
    include_repository: bool = False,
) -> dict:
    """Project a finite public-facade capture into terminal v1.

    Repository metadata is an opt-in dashboard-only enrichment. The default
    keeps the published finite CLI report unchanged.
    """
    source_docs = []
    all_sessions, all_uncertain, all_nonmembers = [], [], []
    for source_state in source_states:
        source_doc, sessions, uncertain, nonmembers = _source_doc(
            source_state,
            now_boottime_ms,
            include_repository=include_repository,
        )
        source_docs.append(source_doc)
        all_sessions.extend(sessions)
        all_uncertain.extend(uncertain)
        all_nonmembers.extend(nonmembers)

    # Exact identities are never merged across route claims. Duplicate claims
    # invalidate every claimant instead of choosing whichever arrived last.
    claimed = {}
    for row in [*all_sessions, *all_uncertain, *all_nonmembers]:
        key = identity_tuple(row["identity"])
        claimed.setdefault(key, []).append(row)
    conflicts = {key for key, rows in claimed.items() if len(rows) > 1}
    if conflicts:
        blocked_source_ids = {row["source"]["id"] for key in conflicts for row in claimed[key]}
        for source in source_docs:
            if source["id"] in blocked_source_ids:
                source["health"] = "blocked"
                source["reason"] = "identity_conflict"
                source["reasons"] = list(dict.fromkeys([*source["reasons"], "identity_conflict"]))
        all_sessions = [
            row for row in all_sessions if row["source"]["id"] not in blocked_source_ids
        ]
        all_uncertain = [
            row for row in all_uncertain if row["source"]["id"] not in blocked_source_ids
        ]
        all_nonmembers = [
            row for row in all_nonmembers if row["source"]["id"] not in blocked_source_ids
        ]

    membership_filter = tuple(filters.get("membership", ()))
    runtime_filter = tuple(filters.get("runtime", ()))
    phase_filter = tuple(filters.get("phase", ()))
    query = tuple(filters.get("query", ()))
    include_children = filters.get("includeChildren") is True
    include_system = filters.get("includeSystem") is True
    visible_members = [
        row
        for row in all_sessions
        if (
            row["kind"] not in {"child", "system"}
            or row["kind"] == "child"
            and include_children
            or row["kind"] == "system"
            and include_system
        )
    ]
    hidden_kinds = len(all_sessions) - len(visible_members)
    candidates = []
    candidates.extend(visible_members)
    candidates.extend(all_uncertain)
    if membership_filter and "nonmember" in membership_filter:
        candidates.extend(all_nonmembers)
    else:
        # Nonmembers are inspectable only on explicit membership selection.
        pass
    if membership_filter:
        candidates = [row for row in candidates if row["membership"] in membership_filter]
    elif mode != "show":
        candidates = [
            row for row in candidates if row["membership"] in {"active", "recent", "uncertain"}
        ]
    if runtime_filter:
        candidates = [
            row
            for row in candidates
            if row["membership"] in {"active", "recent"}
            and row.get("runtime", {}).get("value", "unknown") in runtime_filter
        ]
    if phase_filter:
        candidates = [
            row
            for row in candidates
            if row["membership"] in {"active", "recent"}
            and row.get("phase", {}).get("value") in phase_filter
        ]
    if mode != "show":
        candidates = [row for row in candidates if _matches_query(row, query)]
    sort = filters.get("sort", "activity")
    candidates = sort_rows(candidates, sort, filters.get("group", "none"))

    target_row = None
    target_unresolved = False
    not_found = False
    if mode == "show":
        if isinstance(target, dict):
            target_key = identity_tuple(target)
            matches = [
                row
                for row in [*all_sessions, *all_uncertain, *all_nonmembers]
                if identity_tuple(row["identity"]) == target_key
            ]
        else:
            matches = [
                row
                for row in [*all_sessions, *all_uncertain, *all_nonmembers]
                if row["identity"]["nativeId"] == target
            ]
        if matches:
            target_row = matches[0]
            target_unresolved = target_row["membership"] == "uncertain"
            candidates = [target_row]
        else:
            candidates = []
            not_found = True

    totals_members = len(all_sessions)
    totals_uncertain = len(all_uncertain)
    totals_nonmembers = len(all_nonmembers)
    filtered_matches = len(candidates)
    output_limit = 10 if mode == "overview" else None
    shown = candidates if output_limit is None else candidates[:output_limit]
    shown_sessions = [row for row in shown if row["membership"] in {"active", "recent"}]
    shown_uncertain = [row for row in shown if row["membership"] == "uncertain"]
    shown_nonmembers = [row for row in shown if row["membership"] == "nonmember"]

    source_complete = bool(source_docs) and all(
        source["health"] == "complete" for source in source_docs
    )
    complete_empty = (
        source_complete and not all_sessions and not all_uncertain and not all_nonmembers
    )
    state = "complete-empty" if complete_empty else "complete" if source_complete else "degraded"
    result = "complete" if source_complete else "degraded"
    error = None
    if mode == "show" and target_unresolved:
        result = "degraded"
        state = "degraded"
        error = {
            "code": "target_unresolved",
            "message": "The exact identity is present but its membership is unresolved.",
        }
    elif mode == "show" and not_found:
        if source_complete:
            result = "not_found"
            state = "not_found"
            error = {
                "code": "exact_target_not_in_projection",
                "message": "The exact identity is not present in the selected current projection.",
            }
        else:
            result = "degraded"
            error = {
                "code": "target_unresolved",
                "message": "Selected source coverage is incomplete, so the exact target could not be resolved.",
            }

    selection = [
        {
            "id": source["id"],
            "host": source["host"],
            "home": source["home"],
            "label": source["label"],
            "meshSource": source["meshSource"],
            "namespace": source["expectedNamespace"],
        }
        for source in source_docs
    ]
    totals = {
        "selectedSources": len(source_docs),
        "completeSources": sum(source["health"] == "complete" for source in source_docs),
        "partialSources": sum(
            source["health"] in {"partial", "stale", "warming"} for source in source_docs
        ),
        "failedSources": sum(
            source["health"] in {"unavailable", "blocked"} for source in source_docs
        ),
        "members": totals_members,
        "uncertain": totals_uncertain,
        "nonmembers": totals_nonmembers,
        "hiddenKinds": hidden_kinds,
        "displayedMatches": filtered_matches,
        "shown": len(shown),
        "state": state,
    }
    output_sources = source_docs
    if mode == "sources":
        shown_sessions, shown_uncertain, shown_nonmembers = [], [], []
        totals["displayedMatches"] = 0
        totals["shown"] = 0
    return {
        "interface": "agent-observer.terminal",
        "version": 1,
        "generatedAt": generated_at,
        "selection": {"sources": selection, "config": filters.get("configPath")},
        "filters": {
            "source": _selector_list(filters.get("source")),
            "host": _selector_list(filters.get("host")),
            "home": _selector_list(filters.get("home")),
            "membership": _selector_list(membership_filter),
            "runtime": _selector_list(runtime_filter),
            "phase": _selector_list(phase_filter),
            "query": list(query),
            "includeChildren": include_children,
            "includeSystem": include_system,
            "sort": sort,
            "group": filters.get("group", "none"),
        },
        "clock": clock,
        "totals": totals,
        "sources": output_sources,
        "sessions": shown_sessions,
        "uncertain": shown_uncertain,
        "nonmembers": shown_nonmembers,
        "result": result,
        "error": error,
    }


def generated_at_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
