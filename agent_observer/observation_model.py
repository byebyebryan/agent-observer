"""Source-independent observation invariants for the migration spike.

Keep this model provisional until native provider evidence selects the source
and public representation. No constructor accepts provider payloads or actions.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

_VALUES = {
    "work": frozenset({"working", "needs_input", "settled", "interrupted", "error", "unknown"}),
    "presence": frozenset({"present", "absent", "unknown"}),
    "attachment": frozenset({"attached", "detached", "unknown"}),
}
_HEALTH = frozenset({"current", "stale", "unavailable", "unsupported", "ambiguous"})
_SOURCES = frozenset(
    {"codex_rpc", "claude_registry", "claude_roster", "claude_job_store", "synthetic"}
)
_REASONS = frozenset(
    {
        "unobserved",
        "native_snapshot",
        "native_event",
        "source_unavailable",
        "observation_gap",
        "unsupported",
        "identity_ambiguous",
        "synthetic",
    }
)


def _identity_text(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and not any(unicodedata.category(char).startswith("C") for char in value)
    )


@dataclass(frozen=True)
class NativeIdentity:
    """Explicit scope supplied by a proved source/transport, never inferred."""

    host_scope: str
    provider: str
    namespace: str
    native_id_kind: str
    native_id: str

    def __post_init__(self) -> None:
        if (
            not _identity_text(self.host_scope, 256)
            or not isinstance(self.provider, str)
            or self.provider not in {"codex", "claude"}
            or not _identity_text(self.namespace, 4096)
            or not isinstance(self.native_id_kind, str)
            or self.native_id_kind not in {"thread", "session"}
            or not _identity_text(self.native_id, 256)
        ):
            raise ValueError("invalid_native_identity")

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        return (
            self.host_scope,
            self.provider,
            self.namespace,
            self.native_id_kind,
            self.native_id,
        )


@dataclass(frozen=True)
class Evidence:
    """One dimension and its original evidence clock, independent of liveness."""

    dimension: str
    value: str = "unknown"
    observed_at: int | None = None
    source: str | None = None
    health: str = "unavailable"
    reason: str = "unobserved"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.dimension, str)
            or self.dimension not in _VALUES
            or not isinstance(self.value, str)
            or self.value not in _VALUES[self.dimension]
            or not isinstance(self.health, str)
            or self.health not in _HEALTH
            or not isinstance(self.reason, str)
            or self.reason not in _REASONS
            or (
                self.source is not None
                and (not isinstance(self.source, str) or self.source not in _SOURCES)
            )
        ):
            raise ValueError("invalid_evidence_code")
        if self.observed_at is not None and (
            isinstance(self.observed_at, bool)
            or not isinstance(self.observed_at, int)
            or not 0 <= self.observed_at <= 2**63 - 1
        ):
            raise ValueError("invalid_evidence_time")
        if self.value != "unknown" and (self.observed_at is None or self.source is None):
            raise ValueError("missing_evidence_provenance")

    @property
    def effective_value(self) -> str:
        return self.value if self.health == "current" else "unknown"

    def invalidate(self, reason: str = "observation_gap") -> Evidence:
        """Retain known metadata and its age without claiming current state."""
        return replace(self, health="stale", reason=reason)

    def metadata(self) -> dict[str, object]:
        result: dict[str, object] = {
            "value": self.effective_value,
            "observedAt": self.observed_at,
            "source": self.source,
            "health": self.health,
            "reason": self.reason,
        }
        if self.health != "current" and self.value != "unknown":
            result["lastKnownValue"] = self.value
        return result


@dataclass(frozen=True)
class SessionObservation:
    identity: NativeIdentity
    work: Evidence = Evidence("work")
    presence: Evidence = Evidence("presence")
    attachment: Evidence = Evidence("attachment")

    def __post_init__(self) -> None:
        if (
            not isinstance(self.identity, NativeIdentity)
            or not all(
                isinstance(value, Evidence) for value in (self.work, self.presence, self.attachment)
            )
            or self.work.dimension != "work"
            or self.presence.dimension != "presence"
            or self.attachment.dimension != "attachment"
        ):
            raise ValueError("invalid_observation_dimension")

    def refresh_presence(self, presence: Evidence) -> SessionObservation:
        return replace(self, presence=presence)

    def metadata(self) -> dict[str, object]:
        return {
            "identity": {
                "hostScope": self.identity.host_scope,
                "provider": self.identity.provider,
                "namespace": self.identity.namespace,
                "nativeIdKind": self.identity.native_id_kind,
                "nativeId": self.identity.native_id,
            },
            "work": self.work.metadata(),
            "presence": self.presence.metadata(),
            "attachment": self.attachment.metadata(),
        }


def bounded_native_title(value: object, fallback: str, *, limit: int = 256) -> str:
    """Accept only an explicit native title; callers never pass prompt previews."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 4096:
        raise ValueError("invalid_title_limit")
    if not _identity_text(fallback, 256):
        raise ValueError("invalid_title_fallback")
    if not isinstance(value, str):
        return fallback[:limit]
    clean = "".join(
        " " if unicodedata.category(char).startswith("C") else char for char in value[: limit * 4]
    )
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:limit] if clean else fallback[:limit]
