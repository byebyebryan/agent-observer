"""Explicit Agent selection over admitted facts, without presentation policy."""

from dataclasses import dataclass

from .contract import ContractError


@dataclass(frozen=True)
class AgentRecordSummary:
    identity: tuple[str, str, str, str, str]
    kind: str
    runtime_value: str
    runtime_health: str


@dataclass(frozen=True)
class AgentSelection:
    """Generation-static filters; None accepts every admitted value of a field."""

    providers: frozenset[str] | None = None
    kinds: frozenset[str] | None = None
    runtime_values: frozenset[str] | None = None
    runtime_healths: frozenset[str] | None = None

    def __post_init__(self):
        for value, allowed in (
            (self.providers, {"codex", "claude"}),
            (self.kinds, {"user", "child", "system", "unknown"}),
            (self.runtime_values, {"running", "parked", "unknown"}),
            (self.runtime_healths, {"current", "stale", "unavailable", "unsupported", "ambiguous"}),
        ):
            if value is not None and (type(value) is not frozenset or not value <= allowed):
                raise ContractError("agent_selection")

    def matches(self, summary):
        return all(allowed is None or value in allowed for allowed, value in (
            (self.providers, summary.identity[1]),
            (self.kinds, summary.kind),
            (self.runtime_values, summary.runtime_value),
            (self.runtime_healths, summary.runtime_health),
        ))


def summarize(record):
    """Called only for fully admitted records; it grants no freshness authority."""
    identity = record["identity"]
    return AgentRecordSummary(
        tuple(identity[key] for key in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")),
        record["kind"], record["runtime"]["value"], record["runtime"]["health"],
    )


@dataclass(frozen=True)
class AgentClassifier:
    """Observer-owned adapter for Mesh's generation-static selection callback."""

    selection: AgentSelection

    def __call__(self, record):
        from mesh_plus.api import SelectionRule

        summary = summarize(record)
        return SelectionRule(self.selection.matches(summary), {
            "identity": list(summary.identity), "kind": summary.kind,
            "runtimeValue": summary.runtime_value, "runtimeHealth": summary.runtime_health,
        })
