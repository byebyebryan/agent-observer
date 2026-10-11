"""Pure Agent state semantics for the optional Mesh SDK v1 reader.

Mesh validates transport envelopes, proofs and leases. These callbacks validate
and project native Service 2 data only; they never acquire provider/service data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mesh_plus.api import SDK_INTERFACE_VERSION, NativeState, ProfileDescriptor, descriptor
from mesh_plus.protocol import check

from .public import identity_key
from .public import interface as read_interface
from .service_public import interface as service_interface
from .service_public import validate_frame

PROFILE_ID = "agent-observer.mesh-candidate.v1"


@dataclass(frozen=True)
class AgentCodec:
    host: str
    source: str
    profile_id: str = PROFILE_ID

    def __post_init__(self):
        check(isinstance(self.host, str) and len(self.host) <= 16384 and
              re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.host), "configured_host_id")
        check(isinstance(self.source, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.source),
              "configured_source_id")
        check(self.profile_id == PROFILE_ID, "profile_descriptor")

    def validate_bridge(self, payload):
        # This domain callback is not a standalone transport/proof validator.
        # Mesh's Reader applies its compulsory generic admission independently.
        check(payload["hostId"] == self.host and payload["sourceId"] == self.source,
              "bridge_source_binding")
        validate_frame(payload["ownerFrame"], expected_host=self.host)

    def inspect_native(self, frame):
        validate_frame(frame, expected_host=self.host)
        match = re.fullmatch(r"time:\[([0-9]+)\]", frame["clockDomain"])
        check(match is not None, "owner_clock_domain")
        snapshot = frame["snapshot"]
        return NativeState(
            owner={"protocol": "agent-observer.snapshot", "version": 4,
                   "metadata": None if snapshot is None else {k: v for k, v in snapshot.items() if k != "sessions"},
                   "service": {k: v for k, v in frame.items() if k != "snapshot"}},
            records=() if snapshot is None else tuple(snapshot["sessions"]),
            clock={"bootId": frame["bootId"], "timeNamespace": "time:" + match[1]},
            publisher=frame["serviceId"], emitted_ms=frame["emittedBoottimeMs"],
            receipts=tuple({"sourceId": source["provider"] + ":" + source["namespace"],
                            "component": item["name"], "accepted": item["accepted"],
                            "health": item["health"], "expiry": item["expiresBoottimeMs"]}
                           for source in frame["sources"] for item in source["components"]),
        )


@dataclass(frozen=True)
class AgentProfile:
    descriptor: ProfileDescriptor = field(default_factory=lambda: descriptor("agent"))

    def __post_init__(self):
        expected = descriptor("agent")
        check(SDK_INTERFACE_VERSION == 1 and self.descriptor == expected
              and expected.native_protocol == "agent-observer.snapshot"
              and expected.native_version == read_interface()["schemas"]["snapshot"]
              and expected.frame_bytes == service_interface()["limits"]["frameBytes"],
              "mesh_sdk_incompatible")

    def bind(self, host, source):
        return AgentCodec(host, source, self.descriptor.profile_id)

    def validate_response(self, response):
        # Mesh validates the packaged aggregate schema and admits each native
        # reconstruction through inspect_native. No extra aggregate rule exists.
        pass

    def restore_native(self, owner, records):
        metadata = owner["metadata"]
        return {**owner["service"], "snapshot": None if metadata is None else {**metadata, "sessions": list(records)}}

    def record_host(self, record):
        return record["identity"]["hostScope"]

    def record_identity(self, record):
        return identity_key(record["identity"])

    def record_receipts(self, record, state):
        source = record["identity"]["provider"] + ":" + record["identity"]["namespace"]
        return frozenset((r["sourceId"], r["component"]) for r in state.receipts
                         if r["sourceId"] == source and r["health"] in {"current", "partial"}) or None

    def record_eligible(self, record, state):
        if record["hasSavedHistory"]:
            return True
        return record["runtime"]["health"] == "current" and any(
            component == "runtime" for _, component in self.record_receipts(record, state) or ())
