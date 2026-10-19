"""Pure Mesh SDK 1 profile candidate for the active-plus-recent feed.

The Observer wire contract is implemented independently of Mesh registration.
The public Mesh descriptor remains the gate for constructing the profile and
preparation until this candidate is registered there.
"""

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
)
from mesh_plus.api import (
    descriptor as mesh_descriptor,
)

from .active_contract import MAX_FRAME_BYTES, support_matches
from .contract import ContractError, identity_key
from .working_set_contract import WORKING_SET_PROTOCOL, selector, validate_frame
from .working_set_policy import DEFAULT_WINDOW_MS
from .working_set_supports import resolve_member

WORKING_SET_PROFILE_ID = "agent-observer.mesh-working-set.v1"
NATIVE_PROTOCOL = "agent-observer.working-set"
PREPARATION_ID = "agent-observer.working-set.static-rules.v1"


def _check(condition, code):
    if not condition:
        raise ContractError(code)


def _identity(record):
    # Mesh preparation supplies immutable mappings, while the public identity
    # validator deliberately admits only ordinary wire dictionaries.
    return identity_key(dict(record["identity"]))


def _members(owner):
    metadata = owner["metadata"]
    return {} if metadata is None else {
        _identity(member): (scope, member)
        for scope in metadata["scopes"]
        for member in scope["members"]
    }


def _required(member, service):
    """Return generic conjunction receipt bookkeeping for one admitted row."""
    if member is None:
        return None
    sources = {}
    for source in service["sources"]:
        plain_source = {
            **source,
            "components": [dict(component) for component in source["components"]],
        }
        sources[(source["provider"], source["namespace"])] = plain_source
    result = set()
    for support in member["fieldSupports"].values():
        if support is None:
            continue
        source = sources.get((support["provider"], support["namespace"]))
        if source is None:
            continue
        if support_matches(
            dict(support), source, service["serviceId"], service["emittedBoottimeMs"]
        ):
            result.add((support["provider"] + ":" + support["namespace"], support["component"]))
    return frozenset(result) or None


def _record_eligible(record, members):
    """Eligibility is exact projection membership plus the admitted kind."""
    return record["kind"] in {"unknown", "user"} and _identity(record) in members


def _prepare_rules(state):
    """Compile one detached rule tuple without retaining generation data."""
    members = _members(state.owner)
    service = state.owner["service"]
    rules = []
    for row in state.records:
        identity = _identity(row)
        indexed = members.get(identity)
        member = None if indexed is None else resolve_member(*indexed)
        rules.append(
            PreparedRule(
                identity,
                _required(member, service),
                _record_eligible(row, members),
            )
        )
    return tuple(rules)


def restore_working_set_native(owner, records):
    """Reconstruct the exact Observer frame split by ``inspect_native``."""
    metadata = owner["metadata"]
    if metadata is None:
        if records:
            raise ContractError("working_set_records_without_metadata")
        projection = None
    else:
        projection = {**metadata, "sessions": list(records)}
    return {**owner["service"], "projection": projection}


@dataclass(frozen=True)
class WorkingSetAgentCodec:
    host: str
    source: str
    window_ms: int = DEFAULT_WINDOW_MS
    profile_id: str = WORKING_SET_PROFILE_ID

    def __post_init__(self):
        _check(
            isinstance(self.host, str)
            and len(self.host) <= 16384
            and re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.host) is not None,
            "configured_host_id",
        )
        _check(
            isinstance(self.source, str)
            and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.source) is not None,
            "configured_source_id",
        )
        _check(self.profile_id == WORKING_SET_PROFILE_ID, "profile_descriptor")
        selector(self.window_ms)

    def _binding(self, payload):
        _check(
            payload["hostId"] == self.host and payload["sourceId"] == self.source,
            "bridge_source_binding",
        )

    def validate_bridge(self, payload):
        self._binding(payload)
        self.inspect_native(payload["ownerFrame"])

    def admit_bridge(self, payload):
        self._binding(payload)
        return self.inspect_native(payload["ownerFrame"])

    def inspect_native(self, frame):
        validate_frame(
            frame,
            expected_host=self.host,
            expected_window_ms=self.window_ms,
        )
        match = re.fullmatch(r"time:\[([0-9]+)\]", frame["clockDomain"])
        _check(match is not None, "owner_clock_domain")
        projection = frame["projection"]
        receipts = []
        for source in frame["sources"]:
            for item in source["components"]:
                health = item["health"]
                if projection is None and health in {"current", "partial"}:
                    health = "warming" if frame["state"] == "warming" else "stale"
                receipts.append(
                    {
                        "sourceId": source["provider"] + ":" + source["namespace"],
                        "component": item["name"],
                        "accepted": item["accepted"],
                        "health": health,
                        "expiry": item["expiresBoottimeMs"],
                    }
                )
        return NativeState(
            owner={
                "protocol": NATIVE_PROTOCOL,
                "version": WORKING_SET_PROTOCOL,
                "metadata": None
                if projection is None
                else {key: value for key, value in projection.items() if key != "sessions"},
                "service": {key: value for key, value in frame.items() if key != "projection"},
            },
            records=() if projection is None else tuple(projection["sessions"]),
            clock={"bootId": frame["bootId"], "timeNamespace": "time:" + match[1]},
            publisher=frame["serviceId"],
            emitted_ms=frame["emittedBoottimeMs"],
            receipts=tuple(receipts),
        )


def _candidate_descriptor():
    # Use only Mesh's supported public descriptor API. A pending SDK registration
    # intentionally raises here; no local descriptor or schema is fabricated.
    return mesh_descriptor("agent", profile_id=WORKING_SET_PROFILE_ID)


@dataclass(frozen=True)
class WorkingSetAgentProfile:
    window_ms: int = DEFAULT_WINDOW_MS
    descriptor: ProfileDescriptor | None = None

    def __post_init__(self):
        selector(self.window_ms)
        expected = _candidate_descriptor()
        actual = expected if self.descriptor is None else self.descriptor
        _check(
            SDK_INTERFACE_VERSION == 1
            and type(actual) is ProfileDescriptor
            and actual == expected
            and expected.native_protocol == NATIVE_PROTOCOL
            and expected.native_version == WORKING_SET_PROTOCOL
            and expected.frame_bytes == MAX_FRAME_BYTES,
            "mesh_sdk_incompatible",
        )
        object.__setattr__(self, "descriptor", actual)

    def bind(self, host, source):
        return WorkingSetAgentCodec(host, source, self.window_ms, self.descriptor.profile_id)

    def validate_response(self, response):
        # Mesh's compulsory packaged profile schema and native reconstruction
        # perform full admission independently of this pure callback.
        pass

    def restore_native(self, owner, records):
        return restore_working_set_native(owner, records)

    def record_host(self, record):
        return record["identity"]["hostScope"]

    def record_identity(self, record):
        return _identity(record)

    def record_receipts(self, record, state):
        indexed = _members(state.owner).get(_identity(record))
        member = None if indexed is None else resolve_member(*indexed)
        return _required(member, state.owner["service"])

    def record_eligible(self, record, state):
        return _record_eligible(record, _members(state.owner))


@dataclass(frozen=True)
class WorkingSetAgentPreparation:
    profile: WorkingSetAgentProfile = field(default_factory=WorkingSetAgentProfile)
    descriptor: PreparationDescriptor = field(init=False)

    def __post_init__(self):
        _check(PREPARATION_INTERFACE_VERSION == 1, "preparation_interface")
        _check(type(self.profile) is WorkingSetAgentProfile, "preparation_profile")
        object.__setattr__(
            self,
            "descriptor",
            PreparationDescriptor(1, self.profile.descriptor, PREPARATION_ID),
        )

    def prepare_rules(self, state):
        return _prepare_rules(state)
