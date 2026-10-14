"""Explicit generation-static Agent rules; optional Mesh interface 1 only."""

from dataclasses import dataclass, field

from mesh_plus.api import PREPARATION_INTERFACE_VERSION, PreparationDescriptor, PreparedRule
from mesh_plus.protocol import check

from .mesh_profile import AgentProfile
from .public import identity_key

IMPLEMENTATION_ID = "agent-observer.agent-v3.static-rules.v1"


@dataclass(frozen=True)
class AgentPreparation:
    profile: AgentProfile = field(default_factory=AgentProfile)
    descriptor: PreparationDescriptor = field(init=False)

    def __post_init__(self):
        check(PREPARATION_INTERFACE_VERSION == 1, "preparation_interface")
        object.__setattr__(self, "descriptor", PreparationDescriptor(
            1, self.profile.descriptor, IMPLEMENTATION_ID))

    def prepare_rules(self, state):
        # Compilation sees deeply immutable, completely admitted facts. Group
        # once without thawing the whole native frame or retaining borrowed DTOs.
        grouped = {}
        for receipt in state.receipts:
            if receipt["health"] in {"current", "partial"}:
                grouped.setdefault(receipt["sourceId"], set()).add(
                    (receipt["sourceId"], receipt["component"]))
        required_by_source = {source: frozenset(keys) for source, keys in grouped.items()}
        rules = []
        for row in state.records:
            identity = row["identity"]
            source = identity["provider"] + ":" + identity["namespace"]
            required = required_by_source.get(source)
            eligible = row["hasSavedHistory"] or (
                row["runtime"]["health"] == "current" and
                (source, "runtime") in (required or ()))
            rules.append(PreparedRule(identity_key(dict(identity)), required, eligible))
        return tuple(rules)
