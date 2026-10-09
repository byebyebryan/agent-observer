"""Sampled, bounded host-local watch. No native event or replay guarantee."""

from __future__ import annotations

import copy
import time
import uuid

from .contract import (
    SCHEMA_VERSION, canonical, identity_key,
    validate_snapshot, validate_watch,
)
from .read_client import listing
from .observation_evidence import retain_missing

MIN_INTERVAL = 1.0


def _semantic(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop("collectionId")
    value.pop("collectedAt")
    value["sources"].sort(key=lambda source: (source["provider"], source["namespace"]))
    value["sessions"].sort(key=lambda row: identity_key(row["identity"]))
    for row in value["sessions"]:
        for name in ("phase", "runtime", "outcome"):
            if row[name] and row[name]["clock"] == "sample":
                row[name]["observedAt"] = None
    return canonical(value)


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
            evicted = retain_missing(self.previous, value)
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
