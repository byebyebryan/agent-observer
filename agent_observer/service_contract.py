"""Prerelease local service protocol 2; pure, bounded and provider independent."""

from __future__ import annotations

import copy
from pathlib import PurePosixPath

from .bounded_json import decode_document
from .contract import (
    CODE,
    DIGEST,
    INTEGER,
    MAX_BYTES,
    MAX_NODES,
    PROVIDER,
    SCOPE,
    SNAPSHOT,
    TIME,
    UUID,
    ContractError,
    array,
    canonical,
    choice,
    obj,
    store_namespace,
    text,
    validate_shape,
    validate_snapshot,
)

SERVICE_PROTOCOL = 2
MAX_REQUEST_BYTES = 16 * 1024
MAX_OVERHEAD_BYTES = 16 * 1024
MAX_FRAME_BYTES = MAX_BYTES + MAX_OVERHEAD_BYTES
OPERATIONS = ("status", "snapshot", "watch")
REQUEST = obj(
    serviceProtocol={"const": SERVICE_PROTOCOL},
    operation=choice(*OPERATIONS),
    hostScope=text(256, pattern=SCOPE),
)
COMPONENT = obj(
    name=choice("runtime", "history"),
    attempts=INTEGER,
    accepted=INTEGER,
    sampledBoottimeMs=TIME,
    expiresBoottimeMs=TIME,
    health=choice("warming", "current", "partial", "stale", "unavailable"),
    lastResult=text(128, pattern=CODE),
    inFlight={"type": "boolean"},
)
SOURCE = obj(
    provider=PROVIDER,
    namespace=text(71, pattern=DIGEST),
    configHome=text(),
    configHomeKind=choice("default", "explicit"),
    contextGeneration=INTEGER,
    components=array(COMPONENT, 2),
)
FRAME = obj(
    serviceProtocol={"const": SERVICE_PROTOCOL},
    serviceId=text(36, pattern=UUID),
    bootId=text(36, pattern=UUID),
    uid=INTEGER,
    hostScope=text(256, pattern=SCOPE),
    sequence=INTEGER,
    viewRevision=INTEGER,
    kind=choice("status", "view", "heartbeat", "gap", "resync", "error"),
    state=choice("warming", "ready", "stopping"),
    emittedAt=TIME,
    emittedBoottimeMs=INTEGER,
    clock=choice("boottime"),
    clockDomain=text(128),
    reason=text(128, pattern=CODE),
    sources=array(SOURCE, 2),
    snapshot={"anyOf": [SNAPSHOT, {"type": "null"}]},
)
_FRAME_META = copy.deepcopy(FRAME)
_FRAME_META["properties"]["snapshot"] = {"type": ["object", "null"]}


def interface():
    return {
        "serviceProtocol": SERVICE_PROTOCOL, "stability": "prerelease",
        "observationApiVersion": 2, "embeddedSnapshotVersion": 4,
        "hostLocal": True, "operations": list(OPERATIONS),
        "nativeEventReplay": False, "durableReplay": False,
        "limits": {"requestBytes": MAX_REQUEST_BYTES, "frameBytes": MAX_FRAME_BYTES,
                   "envelopeBytes": MAX_OVERHEAD_BYTES},
    }


def schema_document(kind):
    if kind not in {"request", "frame"}:
        raise ContractError("service_schema_kind")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:service-{kind}:{SERVICE_PROTOCOL}",
        **copy.deepcopy(REQUEST if kind == "request" else FRAME),
    }


def validate_request(value):
    validate_shape(value, REQUEST)
    if len(canonical(value).encode()) + 1 > MAX_REQUEST_BYTES:
        raise ContractError("service_request_limit")
    return value


def parse_request(data):
    return validate_request(decode_document(
        data, max_bytes=MAX_REQUEST_BYTES, max_nodes=128, max_depth=4, line_framed=True,
    ))


def validate_frame(value, *, expected_host=None, expected_uid=None):
    validate_shape(value, _FRAME_META)
    if value["sequence"] < 1 or value["emittedAt"] is None:
        raise ContractError("service_sequence_invalid")
    if expected_host is not None and value["hostScope"] != expected_host:
        raise ContractError("service_host_mismatch")
    if expected_uid is not None and value["uid"] != expected_uid:
        raise ContractError("service_uid_mismatch")
    sources = {}
    for source in value["sources"]:
        provider = source["provider"]
        home = PurePosixPath(source["configHome"])
        if not home.is_absolute() or ".." in home.parts:
            raise ContractError("service_store_invalid")
        if provider in sources or source["namespace"] != store_namespace(
            provider, source["configHome"], source["configHomeKind"], value["uid"],
        ):
            raise ContractError("service_source_invalid")
        components = {item["name"]: item for item in source["components"]}
        if len(components) != 2 or set(components) != {"runtime", "history"}:
            raise ContractError("service_components_invalid")
        for item in components.values():
            sample, expiry = item["sampledBoottimeMs"], item["expiresBoottimeMs"]
            if item["accepted"] > item["attempts"] or (sample is None) != (expiry is None):
                raise ContractError("service_receipt_invalid")
            if sample is not None and (sample > value["emittedBoottimeMs"] or expiry < sample):
                raise ContractError("service_clock_invalid")
            if item["health"] in {"current", "partial"} and (
                sample is None or expiry <= value["emittedBoottimeMs"] or item["accepted"] < 1
            ):
                raise ContractError("service_lease_expired")
        sources[provider] = source
    if not sources:
        raise ContractError("service_sources_missing")
    snapshot = value["snapshot"]
    if value["kind"] in {"view", "resync"} and snapshot is None:
        raise ContractError("service_view_missing")
    if value["kind"] in {"heartbeat", "gap", "error"} and snapshot is not None:
        raise ContractError("service_view_unexpected")
    if snapshot is not None:
        validate_snapshot(snapshot)
        if snapshot["host"]["authority"] != value["hostScope"] or snapshot["host"]["uid"] != value["uid"]:
            raise ContractError("service_snapshot_scope")
        if {(s["provider"], s["namespace"]) for s in snapshot["sources"]} != {
            (s["provider"], s["namespace"]) for s in sources.values()
        }:
            raise ContractError("service_snapshot_sources")
        for source in snapshot["sources"]:
            components = {c["name"]: c for c in sources[source["provider"]]["components"]}
            for dimension, component in (("runtime", "runtime"), ("saved", "history")):
                if source["coverage"][dimension]["status"] in {"complete", "partial"} and components[component]["health"] not in {"current", "partial"}:
                    raise ContractError("service_coverage_without_lease")
        for row in snapshot["sessions"]:
            components = {item["name"]: item for item in sources[row["identity"]["provider"]]["components"]}
            runtime = components["runtime"]
            if any(row[name] is not None and row[name]["value"] != "unknown" for name in ("phase", "runtime")) and runtime["health"] not in {"current", "partial"}:
                raise ContractError("service_runtime_without_lease")
            if row["workspace"] is not None and components["history"]["health"] not in {"current", "partial"}:
                raise ContractError("service_workspace_without_lease")
            if (row["activity"]["health"] == "current" or row["outcome"]["value"] != "unknown") and not any(c["health"] in {"current", "partial"} for c in components.values()):
                raise ContractError("service_metadata_without_lease")
    if len(canonical({**value, "snapshot": None}).encode()) + 1 > MAX_OVERHEAD_BYTES:
        raise ContractError("service_overhead_limit")
    if len(canonical(value).encode()) + 1 > MAX_FRAME_BYTES:
        raise ContractError("service_frame_limit")
    return value


def parse_frame(data, *, expected_host=None, expected_uid=None):
    return validate_frame(decode_document(
        data, max_bytes=MAX_FRAME_BYTES, max_nodes=MAX_NODES + 4096,
        max_depth=34, line_framed=True,
    ), expected_host=expected_host, expected_uid=expected_uid)


class StreamGuard:
    """Strict transport order; reconnect must create a new guard and initial view."""

    def __init__(self, *, expected_host=None, expected_uid=None):
        self.expected_host, self.expected_uid = expected_host, expected_uid
        self.service_id, self.sequence, self.revision = None, 0, 0
        self.binding, self.emitted = None, 0
        self.gapped = False

    def accept(self, value):
        validate_frame(value, expected_host=self.expected_host, expected_uid=self.expected_uid)
        if self.service_id is None:
            if value["kind"] not in {"status", "view", "error"}:
                raise ContractError("service_initial_frame")
            self.service_id = value["serviceId"]
        binding = (
            value["hostScope"], value["uid"], value["bootId"], value["clockDomain"],
            tuple(sorted((s["provider"], s["namespace"], s["configHome"], s["configHomeKind"]) for s in value["sources"])),
        )
        if self.binding is not None and binding != self.binding:
            raise ContractError("service_stream_scope_changed")
        if value["emittedBoottimeMs"] < self.emitted:
            raise ContractError("service_stream_clock_changed")
        if value["serviceId"] != self.service_id or value["sequence"] != self.sequence + 1 or value["viewRevision"] < self.revision:
            raise ContractError("service_stream_order")
        if self.gapped and value["kind"] not in {"resync", "error", "status"}:
            raise ContractError("service_resync_required")
        self.gapped = value["kind"] == "gap" or (self.gapped and value["kind"] == "status")
        self.sequence, self.revision = value["sequence"], value["viewRevision"]
        self.binding, self.emitted = binding, value["emittedBoottimeMs"]
        return value
