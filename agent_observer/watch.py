"""Sampled, bounded host-local watch. No native event or replay guarantee."""

from __future__ import annotations

import copy
import time
import uuid

from .contract import canonical, identity_key, validate_snapshot, validate_watch

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
    for old in previous["sessions"]:
        if identity_key(old["identity"]) in present:
            continue
        source = sources.get((old["identity"]["provider"], old["identity"]["namespace"]))
        if source is None:
            continue
        if all(entry["status"] == "complete" for entry in source["coverage"].values()):
            continue
        retained = copy.deepcopy(old)
        for name in ("phase", "runtime", "worker", "attachment", "outcome"):
            evidence = retained[name]
            if evidence["value"] != "unknown":
                evidence["lastKnownValue"] = evidence["value"]
            evidence.update(value="unknown", health="stale", reason="observation_gap")
        if retained["activity"]["at"] is not None:
            retained["activity"].update(at=None, health="stale", reason="observation_gap")
        retained["metadataIssues"] = list(
            dict.fromkeys(retained["metadataIssues"] + ["retained_after_gap"])
        )
        current["sessions"].append(retained)


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
                "schemaVersion": 2,
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

    def sample(self, snapshot):
        value = copy.deepcopy(validate_snapshot(snapshot))
        if self.previous:
            _retain_missing(self.previous, value)
        validate_snapshot(value)
        signature = _semantic(value)
        frames = []
        if (
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
                value if kind != "heartbeat" else None,
            )
        )
        self.previous, self.signature, self.gapped = value, signature, False
        return frames
