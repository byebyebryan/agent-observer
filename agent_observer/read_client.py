"""Pure public snapshot consumer. No provider homes, filesystem or actions."""

from __future__ import annotations

import copy

from .contract import SCHEMA_VERSION, ContractError, identity_key, validate_snapshot

_ATTENTION = {"blocked": 0, "waiting": 1, "working": 2, "unknown": 3}


def _activity_time(row):
    evidence = row["activity"]
    return evidence["at"] if evidence["health"] == "current" else evidence.get("lastKnownAt")


def ordered_rows(snapshot, *, include_children=False, providers=None, order="activity"):
    validate_snapshot(snapshot)
    if order not in {"activity", "created"}:
        raise ContractError("invalid_order")
    rows = [
        copy.deepcopy(row)
        for row in snapshot["sessions"]
        if (include_children or row["kind"] != "child")
        and (not providers or row["identity"]["provider"] in providers)
    ]

    def key(row):
        clock = _activity_time(row) if order == "activity" else row["createdAt"]
        return (
            _ATTENTION[row["phase"]["value"]],
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


def human_rows(snapshot, **options):
    lines = ["HOST  PROVIDER  PHASE  RUNTIME  AGE  ID  TITLE"]
    for row in ordered_rows(snapshot, **options):
        identity = row["identity"]
        at = _activity_time(row)
        if at is None:
            activity = "unknown"
        elif at > snapshot["collectedAt"]:
            activity = "clock-ahead"
        else:
            seconds = (snapshot["collectedAt"] - at) // 1000
            activity = next(
                f"{seconds // unit}{label}"
                for unit, label in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s"))
                if seconds >= unit or unit == 1
            )
        if at is not None and row["activity"]["health"] == "stale":
            activity = "stale:" + activity
        lines.append(
            f"{identity['hostScope']}  {identity['provider']}  {row['phase']['value']}  {row['runtime']['value']}  {activity}  {identity['nativeId']}  {row['title']}"
        )
    return "\n".join(lines)
