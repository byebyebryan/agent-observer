"""Core evidence invalidation and bounded retention shared by direct/service hosts."""

import copy

from .contract import MAX_SESSIONS, MAX_SNAPSHOT_BYTES, canonical, identity_key


class RuntimeOnlyRetention:
    """Host-local deadlines for unsaved observations, never lifecycle facts."""

    def __init__(self):
        self.deadlines = {}

    def observe(self, rows, *, sampled_ms, ttl_ms):
        for row in rows:
            key = identity_key(row["identity"])
            if row["hasSavedHistory"]:
                self.deadlines.pop(key, None)
            elif "retained_after_gap" not in row["metadataIssues"]:
                self.deadlines[key] = sampled_ms + ttl_ms

    def expired(self, row, now):
        return (not row["hasSavedHistory"]
                and self.deadlines.get(identity_key(row["identity"]), now) <= now)

    def prune(self, rows):
        present = {identity_key(row["identity"]) for row in rows}
        self.deadlines = {key: deadline for key, deadline in self.deadlines.items()
                          if key in present}


def stale_row(row, *, runtime=False, metadata=False, reason="service_source_expired",
              metadata_reason="service_history_stale"):
    row = copy.deepcopy(row)
    if runtime:
        row["blockedReasons"] = []
        for name in ("phase", "runtime", "outcome"):
            fact = row[name]
            if fact is None:
                row[name] = fact = {"value": "unknown", "observedAt": None, "source": None, "health": "stale", "reason": reason, "clock": None}
            if fact["source"] is not None:
                if fact["value"] != "unknown":
                    fact["lastKnownValue"] = fact["value"]
                fact.update(value="unknown", health="stale", reason=reason)
    if metadata:
        activity = row["activity"]
        if activity["source"] is not None:
            if activity["at"] is not None:
                activity["lastKnownAt"] = activity["at"]
            activity.update(at=None, health="stale", reason=reason)
        row["workspace"] = None
        row["metadataIssues"] = list(dict.fromkeys(row["metadataIssues"][:126] + [metadata_reason]))
    return row


def retain_missing(previous, current, *, component=None, retention=None, now=None):
    """Partial coverage retains prior identity as stale evidence within byte bounds."""
    present = {identity_key(row["identity"]) for row in current["sessions"]}
    sources = {(s["provider"], s["namespace"]): s for s in current["sources"]}
    used_bytes = len(canonical(current).encode())
    evicted = False
    for old in previous["sessions"]:
        if identity_key(old["identity"]) in present:
            continue
        source = sources.get((old["identity"]["provider"], old["identity"]["namespace"]))
        if source is None:
            continue
        if retention is not None and retention.expired(old, now):
            continue
        if component is None:
            if not old["hasSavedHistory"] and source["coverage"]["runtime"]["status"] == "complete":
                continue
            if all(entry["status"] == "complete" for entry in source["coverage"].values()):
                continue
        else:
            dimension = "saved" if component == "history" else "runtime"
            if source["coverage"][dimension]["status"] == "complete":
                continue
            if component == "history" and not old["hasSavedHistory"]:
                continue
        reason = "observation_gap" if component is None else "service_source_expired"
        retained = stale_row(old, runtime=True, metadata=True, reason=reason,
                             metadata_reason="observation_gap" if component is None else "service_history_stale")
        retained["metadataIssues"] = list(dict.fromkeys(retained["metadataIssues"][:126] + ["retained_after_gap"]))
        row_bytes = len(canonical(retained).encode()) + 1
        if len(current["sessions"]) >= MAX_SESSIONS or used_bytes + row_bytes > MAX_SNAPSHOT_BYTES - 512:
            evicted = True
            continue
        current["sessions"].append(retained)
        used_bytes += row_bytes
    if evicted:
        code = "retention_limit" if component is None else "service_retention_limit"
        current["errors"] = list(dict.fromkeys(current["errors"][:126] + [code]))
    return evicted
