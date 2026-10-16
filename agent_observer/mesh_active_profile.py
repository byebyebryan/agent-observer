"""Pure projected Agent profile; transport proofs remain Mesh's authority."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mesh_plus.api import (
    PREPARATION_INTERFACE_VERSION,
    SDK_INTERFACE_VERSION,
    NativeState,
    PreparationDescriptor,
    PreparedRule,
    ProfileDescriptor,
    descriptor,
)
from mesh_plus.protocol import check

from .active_contract import ACTIVE_FEED_PROTOCOL, MAX_FRAME_BYTES, support_matches, validate_frame
from .contract import identity_key

ACTIVE_PROFILE_ID = "agent-observer.mesh-active.v1"
NATIVE_PROTOCOL = "agent-observer.active-feed"
PREPARATION_ID = "agent-observer.active-v1.static-rules.v1"


def active_descriptor():
    return descriptor("agent", profile_id=ACTIVE_PROFILE_ID)


def _identity(record):
    # Preparation receives immutable mappings, while the public identity
    # validator deliberately admits only ordinary wire dictionaries.
    return identity_key(dict(record["identity"]))


def _members(owner):
    metadata = owner["metadata"]
    return {} if metadata is None else {
        _identity(member): member
        for scope in metadata["scopes"] for member in scope["members"]
    }


def _required(member, service):
    if member is None:
        return None
    sources = {(s["provider"], s["namespace"]): s for s in service["sources"]}
    result = set()
    for support in member["fieldSupports"].values():
        if support is None:
            continue
        source = sources.get((support["provider"], support["namespace"]))
        if source is None:
            continue
        # Only these small receipt DTOs need thawing. No selected body or
        # whole-ledger reconstruction occurs during immutable preparation.
        plain_source = {**source, "components": [dict(c) for c in source["components"]]}
        if support_matches(dict(support), plain_source, service["serviceId"], service["emittedBoottimeMs"]):
            result.add((support["provider"] + ":" + support["namespace"], support["component"]))
    return frozenset(result) or None


@dataclass(frozen=True)
class ActiveAgentCodec:
    host: str
    source: str
    profile_id: str = ACTIVE_PROFILE_ID

    def __post_init__(self):
        check(isinstance(self.host, str) and len(self.host) <= 16384
              and re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.host), "configured_host_id")
        check(isinstance(self.source, str)
              and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.source), "configured_source_id")
        check(self.profile_id == ACTIVE_PROFILE_ID, "profile_descriptor")

    def _binding(self, payload):
        check(payload["hostId"] == self.host and payload["sourceId"] == self.source,
              "bridge_source_binding")

    def validate_bridge(self, payload):
        self._binding(payload)
        self.inspect_native(payload["ownerFrame"])

    def admit_bridge(self, payload):
        self._binding(payload)
        return self.inspect_native(payload["ownerFrame"])

    def inspect_native(self, frame):
        validate_frame(frame, expected_host=self.host)
        match = re.fullmatch(r"time:\[([0-9]+)\]", frame["clockDomain"])
        check(match is not None, "owner_clock_domain")
        projection = frame["projection"]
        receipts = []
        for source in frame["sources"]:
            for item in source["components"]:
                health = item["health"]
                if projection is None and health in {"current", "partial"}:
                    health = "warming" if frame["state"] == "warming" else "stale"
                receipts.append({
                    "sourceId": source["provider"] + ":" + source["namespace"],
                    "component": item["name"], "accepted": item["accepted"],
                    "health": health, "expiry": item["expiresBoottimeMs"],
                })
        return NativeState(
            owner={
                "protocol": NATIVE_PROTOCOL, "version": ACTIVE_FEED_PROTOCOL,
                "metadata": None if projection is None else {
                    k: v for k, v in projection.items() if k != "sessions"
                },
                "service": {k: v for k, v in frame.items() if k != "projection"},
            },
            records=() if projection is None else tuple(projection["sessions"]),
            clock={"bootId": frame["bootId"], "timeNamespace": "time:" + match[1]},
            publisher=frame["serviceId"], emitted_ms=frame["emittedBoottimeMs"],
            receipts=tuple(receipts),
        )


@dataclass(frozen=True)
class ActiveAgentProfile:
    descriptor: ProfileDescriptor = field(default_factory=active_descriptor)

    def __post_init__(self):
        expected = active_descriptor()
        check(SDK_INTERFACE_VERSION == 1 and self.descriptor == expected
              and expected.native_protocol == NATIVE_PROTOCOL
              and expected.native_version == ACTIVE_FEED_PROTOCOL
              and expected.frame_bytes == MAX_FRAME_BYTES, "mesh_sdk_incompatible")

    def bind(self, host, source):
        return ActiveAgentCodec(host, source, self.descriptor.profile_id)

    def validate_response(self, response):
        # Mesh's compulsory packaged profile schema and native reconstruction
        # perform full admission independently of this pure callback.
        pass

    def restore_native(self, owner, records):
        metadata = owner["metadata"]
        return {**owner["service"], "projection": None if metadata is None else {
            **metadata, "sessions": list(records),
        }}

    def record_host(self, record):
        return record["identity"]["hostScope"]

    def record_identity(self, record):
        return _identity(record)

    def record_receipts(self, record, state):
        return _required(_members(state.owner).get(_identity(record)), state.owner["service"])

    def record_eligible(self, record, state):
        return (record["runtime"]["value"] == "running"
                and record["runtime"]["health"] == "current"
                and record["kind"] in {"unknown", "user"}
                and _identity(record) in _members(state.owner))


@dataclass(frozen=True)
class ActiveAgentPreparation:
    profile: ActiveAgentProfile = field(default_factory=ActiveAgentProfile)
    descriptor: PreparationDescriptor = field(init=False)

    def __post_init__(self):
        check(PREPARATION_INTERFACE_VERSION == 1, "preparation_interface")
        object.__setattr__(self, "descriptor", PreparationDescriptor(
            1, self.profile.descriptor, PREPARATION_ID,
        ))

    def prepare_rules(self, state):
        members = _members(state.owner)
        service = state.owner["service"]
        return tuple(PreparedRule(
            _identity(row), _required(members.get(_identity(row)), service),
            row["runtime"]["value"] == "running" and row["runtime"]["health"] == "current"
            and row["kind"] in {"unknown", "user"} and _identity(row) in members,
        ) for row in state.records)
