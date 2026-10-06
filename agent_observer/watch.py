"""Sampled, bounded host-local watch. No native event or replay guarantee."""

from __future__ import annotations

import copy
import time
import uuid

from .contract import (
    MAX_SESSIONS, MAX_SNAPSHOT_BYTES, SCHEMA_VERSION, canonical, identity_key,
    validate_snapshot, validate_watch,
)
from .read_client import listing

MIN_INTERVAL = 1.0


def _semantic(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop("collectionId")
    value.pop("collectedAt")
    value["sources"].sort(key=lambda source: (source["provider"], source["namespace"]))
    value["sessions"].sort(key=lambda row: identity_key(row["identity"]))
    for row in value["sessions"]:
        for name in ("phase", "runtime", "worker", "attachment", "outcome"):
            if row[name]["clock"] == "sample":
                row[name]["observedAt"] = None
    return canonical(value)


def _retain_missing(previous, current):
    """A partial/capped roster cannot remove prior rows or prove parked."""
    present = {identity_key(row["identity"]) for row in current["sessions"]}
    sources = {(source["provider"], source["namespace"]): source for source in current["sources"]}
    used_bytes = len(canonical(current).encode())
    evicted = False
    for old in previous["sessions"]:
        if identity_key(old["identity"]) in present:
            continue
        source = sources.get((old["identity"]["provider"], old["identity"]["namespace"]))
        if source is None:
            continue
        if all(entry["status"] == "complete" for entry in source["coverage"].values()):
            continue
        retained = copy.deepcopy(old)
        retained["blockedReason"] = "unknown"
        for name in ("phase", "runtime", "worker", "attachment", "outcome"):
            evidence = retained[name]
            if evidence["value"] != "unknown":
                evidence["lastKnownValue"] = evidence["value"]
            evidence.update(value="unknown", health="stale", reason="observation_gap")
        if retained["activity"]["at"] is not None:
            retained["activity"].update(
                lastKnownAt=retained["activity"]["at"], at=None,
                health="stale", reason="observation_gap",
            )
        retained["metadataIssues"] = [
            issue for issue in retained["metadataIssues"] if issue != "retained_after_gap"
        ][:127] + ["retained_after_gap"]
        row_bytes = len(canonical(retained).encode()) + 1
        if (
            len(current["sessions"]) >= MAX_SESSIONS
            or used_bytes + row_bytes > MAX_SNAPSHOT_BYTES - 512
        ):
            evicted = True
            continue
        current["sessions"].append(retained)
        used_bytes += row_bytes
    if evicted:
        current["errors"] = [code for code in current["errors"] if code != "retention_limit"][:127] + ["retention_limit"]
    return evicted


class SampledWatch:
    def __init__(self):
        self.stream_id = str(uuid.uuid4())
        self.revision = 0
        self.previous = None
        self.signature = None
        self.gapped = False

    def frame(self, kind, reason, snapshot=None):
        self.revision += 1
        return validate_watch(
            {
                "schemaVersion": SCHEMA_VERSION,
                "streamId": self.stream_id,
                "revision": self.revision,
                "kind": kind,
                "sampledAt": time.time_ns() // 1_000_000,
                "reason": reason,
                "snapshot": snapshot,
            }
        )

    def gap(self, reason="collection_failed"):
        self.gapped = True
        return self.frame("gap", reason)

    def sample(self, snapshot, *, include_children=True, providers=None, order="activity"):
        value = copy.deepcopy(validate_snapshot(snapshot))
        evicted = False
        if self.previous:
            evicted = _retain_missing(self.previous, value)
        validate_snapshot(value)
        projected = listing(value, include_children=include_children, providers=providers, order=order)
        signature = _semantic(projected)
        frames = []
        if evicted:
            frames.append(self.gap("retention_limit"))
        elif (
            self.previous
            and self.previous["sourceHealth"] == "current"
            and value["sourceHealth"] != "current"
        ):
            frames.append(self.gap("source_incomplete"))
        if self.previous is None:
            kind = "snapshot"
        elif self.gapped:
            kind = "resync"
        elif signature != self.signature:
            kind = "change"
        else:
            kind = "heartbeat"
        frames.append(
            self.frame(
                kind,
                "sampled_snapshot" if kind != "heartbeat" else "unchanged",
                projected if kind != "heartbeat" else None,
            )
        )
        self.previous, self.signature, self.gapped = value, signature, False
        return frames
