"""Opt-in active-feed wire 1; pure validation with original receipt bindings.

This is a projected native contract, not a shortened Service 4 snapshot.  A
complete scope is an explicit, independently leased claim, including when it
contains no selected session bodies.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import PurePosixPath

from .bounded_json import decode_document
from .contract import (
    MAX_NODES,
    ContractError,
    array,
    canonical,
    choice,
    identity_key,
    obj,
    validate_shape,
)
from .projection_support import FACT_SUPPORT as FACT_SUPPORT
from .projection_support import FIELD_SUPPORTS as FIELD_SUPPORTS
from .projection_support import MAX_FRAME_BYTES as MAX_FRAME_BYTES
from .projection_support import MAX_IDENTITIES as MAX_IDENTITIES
from .projection_support import MAX_LEDGER_BYTES as MAX_LEDGER_BYTES
from .projection_support import MAX_OVERHEAD_BYTES as MAX_OVERHEAD_BYTES
from .projection_support import MAX_REQUEST_BYTES as MAX_REQUEST_BYTES
from .projection_support import MEMBER as MEMBER
from .projection_support import NONMEMBER as NONMEMBER
from .projection_support import NULL_SUPPORT as NULL_SUPPORT
from .projection_support import POSITIVE_INTEGER as POSITIVE_INTEGER
from .projection_support import PROJECTION as PROJECTION
from .projection_support import SCOPE as SCOPE
from .projection_support import UNCERTAIN as UNCERTAIN
from .projection_support import _current_support as _current_support
from .projection_support import _identity as _identity
from .projection_support import _sources as _sources
from .projection_support import _support_scope as _support_scope
from .projection_support import _support_set as _support_set
from .projection_support import support_matches as support_matches
from .service_contract import FRAME as SERVICE_FRAME
from .service_contract import SOURCE

ACTIVE_FEED_PROTOCOL = 1
OPERATIONS = ("status", "snapshot", "watch")
SELECTOR = {
    "version": 1,
    "providers": ["codex"],
    "kinds": ["unknown", "user"],
    "runtimeValues": ["running"],
    "runtimeHealths": ["current"],
}
SELECTOR_DIGEST = "sha256:" + hashlib.sha256(canonical(SELECTOR).encode()).hexdigest()
SELECTOR_SCHEMA = {"const": copy.deepcopy(SELECTOR)}
REQUEST = obj(
    activeFeedProtocol={"const": ACTIVE_FEED_PROTOCOL},
    operation=choice(*OPERATIONS),
    hostScope=copy.deepcopy(SERVICE_FRAME["properties"]["hostScope"]),
    selector=SELECTOR_SCHEMA,
    selectorDigest={"const": SELECTOR_DIGEST},
)
FRAME = copy.deepcopy(SERVICE_FRAME)
FRAME["properties"].pop("serviceProtocol")
FRAME["properties"].pop("snapshot")
FRAME["properties"].update(
    activeFeedProtocol={"const": ACTIVE_FEED_PROTOCOL},
    selector=SELECTOR_SCHEMA,
    selectorDigest={"const": SELECTOR_DIGEST},
    projection={"anyOf": [PROJECTION, {"type": "null"}]},
    sources=array(SOURCE, 1),
)
FRAME["required"] = list(FRAME["properties"])


def interface():
    return {
        "activeFeedProtocol": ACTIVE_FEED_PROTOCOL, "stability": "prerelease",
        "observationApiVersion": 4, "hostLocal": True,
        "operations": list(OPERATIONS), "selector": copy.deepcopy(SELECTOR),
        "selectorDigest": SELECTOR_DIGEST,
        "nativeEventReplay": False, "durableReplay": False,
        "limits": {"requestBytes": MAX_REQUEST_BYTES, "frameBytes": MAX_FRAME_BYTES,
                   "envelopeBytes": MAX_OVERHEAD_BYTES, "ledgerBytes": MAX_LEDGER_BYTES,
                   "identities": MAX_IDENTITIES},
    }


def schema_document(kind):
    if kind not in {"request", "frame"}:
        raise ContractError("active_schema_kind")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:active-{kind}:{ACTIVE_FEED_PROTOCOL}",
        **copy.deepcopy(REQUEST if kind == "request" else FRAME),
    }


def validate_request(value):
    validate_shape(value, REQUEST)
    if canonical(value["selector"]) != canonical(SELECTOR):
        raise ContractError("active_selector_mismatch")
    if len(canonical(value).encode()) + 1 > MAX_REQUEST_BYTES:
        raise ContractError("active_request_limit")
    return value


def parse_request(data):
    return validate_request(decode_document(
        data, max_bytes=MAX_REQUEST_BYTES, max_nodes=128, max_depth=6, line_framed=True,
    ))














def _session(row):
    """API 4 row semantics, without manufacturing a full-inventory snapshot."""
    identity, ids = row["identity"], row["nativeIds"]
    if (identity["provider"] != "codex" or identity["nativeIdKind"] != "thread"
            or set(ids) != {"threadId", "sessionTreeRootId"}
            or identity["nativeId"] != ids.get("threadId")):
        raise ContractError("native_identity_conflict")
    if row["cwd"] is not None:
        path = PurePosixPath(row["cwd"])
        if not path.is_absolute() or ".." in path.parts:
            raise ContractError("invalid_cwd_path")
    for name in ("phase", "runtime", "outcome"):
        fact = row[name]
        if fact is not None and fact["value"] != "unknown" and (
            fact["health"] != "current" or fact["observedAt"] is None
            or fact["source"] is None or fact["clock"] is None
        ):
            raise ContractError("missing_evidence_provenance")
    activity = row["activity"]
    if activity["at"] is not None and (activity["source"] is None or activity["health"] != "current"):
        raise ContractError("missing_activity_provenance")
    if activity.get("lastKnownAt") is not None and (
        activity["at"] is not None or activity["health"] != "stale" or activity["source"] is None
    ):
        raise ContractError("invalid_last_known_activity")
    for name in ("lastUpdated", "latestTurn"):
        record = row[name]
        key = "at" if name == "lastUpdated" else "value"
        known = "lastKnownAt" if name == "lastUpdated" else "lastKnownValue"
        if record["health"] == "current" and (record["source"] is None or record["observedAt"] is None):
            raise ContractError("missing_timing_provenance")
        if record["health"] != "current" and record[key] is not None:
            raise ContractError("invalid_current_timing")
        if known in record and (record["health"] != "stale" or record[key] is not None
                                or record[known] is None or record["source"] is None
                                or record["observedAt"] is None):
            raise ContractError("invalid_last_known_timing")
        if name == "lastUpdated":
            if (record["at"] is None) != (record["timestampPrecisionMs"] is None):
                raise ContractError("timing_precision_conflict")
            if ("lastKnownAt" in record) != ("lastKnownTimestampPrecisionMs" in record) or (
                "lastKnownAt" in record and record["lastKnownTimestampPrecisionMs"] is None
            ):
                raise ContractError("timing_precision_conflict")
        else:
            for turn in (record["value"], record.get("lastKnownValue")):
                if turn is None:
                    continue
                start, end = turn["startedAt"], turn["completedAt"]
                if (start is not None and end is not None and end < start
                        or (start is None and end is None) != (turn["timestampPrecisionMs"] is None)
                        or turn["id"] == ""
                        or turn["status"] == "in_progress" and (end is not None or turn["durationMs"] is not None)):
                    raise ContractError("invalid_turn_timing")
        receipt = record["receipt"]
        if receipt is not None and (record["observedAt"] is None
                                   or receipt["observedBoottimeMs"] < receipt["sampledBoottimeMs"]):
            raise ContractError("invalid_timing_receipt")
    if row["runtime"]["value"] != "running" or row["runtime"]["health"] != "current":
        raise ContractError("active_member_runtime")
    if row["kind"] not in {"unknown", "user"}:
        raise ContractError("active_member_kind")
    phase = row["phase"]
    if phase is None:
        raise ContractError("parked_phase_conflict")
    if phase["value"] != "unknown" and (
        phase["source"] != row["runtime"]["source"]
        or phase["observedAt"] != row["runtime"]["observedAt"]
        or phase["clock"] != row["runtime"]["clock"]
    ):
        raise ContractError("phase_runtime_conflict")
    reasons = row["blockedReasons"]
    if len(reasons) != len(set(reasons)):
        raise ContractError("duplicate_blocked_reason")
    if phase["value"] == "blocked" and not reasons:
        raise ContractError("missing_blocked_reason")
    if phase["value"] != "blocked" and reasons:
        raise ContractError("unexpected_blocked_reason")


def _member(row, metadata, source, scope, value):
    fields = metadata["fieldSupports"]
    runtime = fields["runtime"]
    if runtime is None or runtime["component"] != "runtime":
        raise ContractError("active_runtime_support_missing")
    required = {
        "kind": row["kind"] != "unknown",
        "phase": row["phase"]["value"] != "unknown",
        "activity": row["activity"]["health"] == "current" and row["activity"]["at"] is not None,
        "outcome": row["outcome"]["value"] != "unknown",
        "workspace": row["workspace"] is not None and row["workspace"]["health"] == "current",
        "lastUpdated": row["lastUpdated"]["health"] == "current",
        "latestTurn": row["latestTurn"]["health"] == "current",
    }
    if any(needed and fields[name] is None for name, needed in required.items()):
        raise ContractError("active_field_support_missing")
    _current_support(runtime, source, scope, value)
    for name, support in fields.items():
        if support is not None:
            if required.get(name, False):
                _current_support(support, source, scope, value)
            else:
                _support_scope(support, scope, value)
    if required["phase"] and fields["phase"] != runtime:
        raise ContractError("active_phase_support_conflict")
    if fields["workspace"] is not None and fields["workspace"]["component"] != "history":
        raise ContractError("active_workspace_support_conflict")
    for name in ("lastUpdated", "latestTurn"):
        binding, support = row[name]["receipt"], fields[name]
        if row[name]["health"] != "current":
            continue
        if (binding is None or any(binding[key] != support[key] for key in (
            "component", "sampledBoottimeMs", "contextGeneration",
        )) or not support["sampledBoottimeMs"] <= binding["observedBoottimeMs"]
                <= value["emittedBoottimeMs"] or binding["observedBoottimeMs"] >= support["expiresBoottimeMs"]):
            raise ContractError("active_timing_support_conflict")


def validate_frame(value, *, expected_host=None, expected_uid=None):
    validate_shape(value, FRAME)
    if canonical(value["selector"]) != canonical(SELECTOR):
        raise ContractError("active_selector_mismatch")
    if value["sequence"] < 1 or value["emittedAt"] is None:
        raise ContractError("active_sequence_invalid")
    if expected_host is not None and value["hostScope"] != expected_host:
        raise ContractError("active_host_mismatch")
    if expected_uid is not None and value["uid"] != expected_uid:
        raise ContractError("active_uid_mismatch")
    sources = _sources(value)
    projection = value["projection"]
    if value["kind"] in {"view", "resync"} and projection is None:
        raise ContractError("active_view_missing")
    if value["kind"] in {"heartbeat", "gap", "error"} and projection is not None:
        raise ContractError("active_view_unexpected")
    if value["state"] == "warming" and projection is not None:
        raise ContractError("active_warming_projection")
    if projection is not None:
        scopes, rows, metadata = {}, {}, {}
        for scope in projection["scopes"]:
            key = scope["provider"], scope["namespace"]
            if key in scopes or scope["provider"] not in sources:
                raise ContractError("active_scope_invalid")
            source = sources[scope["provider"]]
            if (scope["namespace"], scope["contextGeneration"]) != (
                source["namespace"], source["contextGeneration"],
            ):
                raise ContractError("active_scope_context")
            scopes[key] = scope
            coverage = scope["coverage"]
            _support_set(coverage["supports"], source, scope, value,
                         runtime=coverage["status"] == "complete")
            if coverage["status"] == "complete" and scope["uncertain"]:
                raise ContractError("active_complete_uncertain")
            seen = set()
            for kind in ("members", "uncertain", "nonmembers"):
                for entry in scope[kind]:
                    identity = _identity(entry["identity"], scope, value)
                    if identity in seen:
                        raise ContractError("active_duplicate_identity")
                    seen.add(identity)
                    if kind == "members":
                        metadata[identity] = entry
                    elif kind == "uncertain":
                        for name in ("priorSupport", "support"):
                            if entry[name] is not None:
                                _support_scope(entry[name], scope, value)
                        prior = entry["priorSupport"]
                        if prior is not None and (prior["component"] != "runtime"
                                                  or entry["horizonBoottimeMs"] > prior["expiresBoottimeMs"]):
                            raise ContractError("active_uncertain_horizon")
                    else:
                        _support_set(entry["supports"], source, scope, value,
                                     runtime=entry["reason"] == "parked")
                        if not entry["supports"] or (entry["reason"] == "parked") != (entry["value"] == "parked"):
                            raise ContractError("active_negative_invalid")
            if len(seen) > MAX_IDENTITIES:
                raise ContractError("active_identity_limit")
        if set(scopes) != {(s["provider"], s["namespace"]) for s in sources.values()}:
            raise ContractError("active_scopes_missing")
        if len(canonical(projection["scopes"]).encode()) > MAX_LEDGER_BYTES:
            raise ContractError("active_ledger_limit")
        for row in projection["sessions"]:
            key = identity_key(row["identity"])
            scope = scopes.get((row["identity"]["provider"], row["identity"]["namespace"]))
            if scope is None:
                raise ContractError("active_identity_scope")
            _identity(row["identity"], scope, value)
            if key in rows:
                raise ContractError("active_duplicate_identity")
            rows[key] = row
            if key not in metadata:
                raise ContractError("active_member_body_mismatch")
            _session(row)
            _member(row, metadata[key], sources[scope["provider"]], scope, value)
        if set(rows) != set(metadata):
            raise ContractError("active_member_body_mismatch")
    if len(canonical({**value, "projection": None}).encode()) + 1 > MAX_OVERHEAD_BYTES:
        raise ContractError("active_overhead_limit")
    if len(canonical(value).encode()) + 1 > MAX_FRAME_BYTES:
        raise ContractError("active_frame_limit")
    return value


def parse_frame(data, *, expected_host=None, expected_uid=None):
    return validate_frame(decode_document(
        data, max_bytes=MAX_FRAME_BYTES, max_nodes=MAX_NODES + 4096,
        max_depth=34, line_framed=True,
    ), expected_host=expected_host, expected_uid=expected_uid)


class StreamGuard:
    """Strict active stream order; reconnect requires a new guard/baseline."""

    def __init__(self, *, expected_host=None, expected_uid=None):
        self.expected_host, self.expected_uid = expected_host, expected_uid
        self.service_id, self.sequence, self.revision = None, 0, 0
        self.binding, self.emitted = None, 0
        self.gapped = False

    def parse(self, data):
        return self.accept(decode_document(
            data, max_bytes=MAX_FRAME_BYTES, max_nodes=MAX_NODES + 4096,
            max_depth=34, line_framed=True,
        ))

    def accept(self, value):
        validate_frame(value, expected_host=self.expected_host, expected_uid=self.expected_uid)
        if self.service_id is None:
            if value["kind"] not in {"status", "view", "error"}:
                raise ContractError("active_initial_frame")
            self.service_id = value["serviceId"]
        binding = (
            value["hostScope"], value["uid"], value["bootId"], value["clockDomain"],
            value["selectorDigest"],
            tuple(sorted((s["provider"], s["namespace"], s["configHome"], s["configHomeKind"])
                         for s in value["sources"])),
        )
        if self.binding is not None and binding != self.binding:
            raise ContractError("active_stream_scope_changed")
        if value["emittedBoottimeMs"] < self.emitted:
            raise ContractError("active_stream_clock_changed")
        if (value["serviceId"] != self.service_id or value["sequence"] != self.sequence + 1
                or value["viewRevision"] < self.revision):
            raise ContractError("active_stream_order")
        if self.gapped and value["kind"] not in {"resync", "error", "status"}:
            raise ContractError("active_resync_required")
        self.gapped = value["kind"] == "gap" or (self.gapped and value["kind"] == "status")
        self.sequence, self.revision = value["sequence"], value["viewRevision"]
        self.binding, self.emitted = binding, value["emittedBoottimeMs"]
        return value
