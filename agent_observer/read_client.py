"""Pure public snapshot consumer. No provider homes, filesystem or actions."""

from __future__ import annotations

import copy

from .contract import SCHEMA_VERSION, ContractError, identity_key, validate_snapshot

_ATTENTION = {"blocked": 0, "waiting": 1, "working": 2, "unknown": 3}


def _activity_time(row):
    evidence = row["activity"]
    return evidence["at"] if evidence["health"] == "current" else evidence.get("lastKnownAt")


def ordered_rows(snapshot, *, include_children=False, providers=None, order="activity"):
    return ordered_snapshots([snapshot], include_children=include_children, providers=providers, order=order)


def ordered_snapshots(snapshots, *, include_children=False, providers=None, order="activity"):
    """Order independently validated host snapshots for a presentation client."""
    for snapshot in snapshots:
        validate_snapshot(snapshot)
    if order not in {"activity", "created"}:
        raise ContractError("invalid_order")
    rows = [
        copy.deepcopy(row)
        for snapshot in snapshots
        for row in snapshot["sessions"]
        if (include_children or row["kind"] != "child")
        and (not providers or row["identity"]["provider"] in providers)
    ]

    def key(row):
        clock = _activity_time(row) if order == "activity" else row["createdAt"]
        return (
            _ATTENTION[row["phase"]["value"] if row["phase"] else "unknown"],
            clock is None,
            -(clock or 0),
            identity_key(row["identity"]),
        )

    return sorted(rows, key=key)


def select(snapshot, reference):
    key = identity_key(reference)
    rows = [
        row
        for row in ordered_rows(snapshot, include_children=True)
        if identity_key(row["identity"]) == key
    ]
    if len(rows) != 1:
        raise ContractError("session_unavailable")
    return copy.deepcopy(rows[0])


def listing(snapshot, **options):
    result = copy.deepcopy(snapshot)
    result["sessions"] = ordered_rows(snapshot, **options)
    return result


def diagnostic(snapshot):
    validate_snapshot(snapshot)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "host": snapshot["host"],
        "sourceHealth": snapshot["sourceHealth"],
        "sources": copy.deepcopy(snapshot["sources"]),
        "sessionCount": len(snapshot["sessions"]),
        "limitations": list(snapshot["limitations"]),
    }


def human_rows(snapshot, *, now_ms=None, **options):
    # Callers supply display time; deterministic pure consumers may use the
    # receipt time. Neither changes native evidence or the snapshot itself.
    now_ms = snapshot["collectedAt"] if now_ms is None else now_ms
    return human_snapshots([snapshot], now_ms=now_ms, **options)


def human_snapshots(snapshots, *, now_ms, **options):
    """Human-only cross-host view; never rewrites a transport envelope."""
    if type(now_ms) is not int or now_ms < 0:
        raise ContractError("invalid_display_time")
    lines = ["HOST  PROVIDER  PHASE  RUNTIME  AGE  ID  TITLE"]
    for row in ordered_snapshots(snapshots, **options):
        identity = row["identity"]
        at = _activity_time(row)
        if at is None:
            activity = "unknown"
        elif at > now_ms:
            activity = "clock-ahead"
        else:
            seconds = (now_ms - at) // 1000
            activity = next(
                f"{seconds // unit}{label}"
                for unit, label in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s"))
                if seconds >= unit or unit == 1
            )
        if at is not None and row["activity"]["health"] == "stale":
            activity = "stale:" + activity
        runtime = row["runtime"]["value"]
        if row["inventory"] == "saved" and runtime == "unknown":
            runtime = "saved/unknown"
        lines.append(f"{identity['hostScope']}  {identity['provider']}  {row['phase']['value'] if row['phase'] else '-'}  {runtime}  {activity}  {identity['nativeId']}  {row['title']}")
    return "\n".join(lines)
