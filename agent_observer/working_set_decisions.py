"""Pure working-set row decisions with a bounded event-key continuity guard.

The caller supplies an admitted row, its borrowed FactSupport references, the
current source metadata, and the private accepted-sample clock. This module
does not read providers, retain rows/support/clocks, or publish a projection.
Only full identity strings and the last accepted activity timestamp/clock epoch
are retained. A real source-context change must be applied with
``reset_context`` before rows from that context can receive recency authority.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from .observation_support import support_matches
from .working_set_policy import (
    DEFAULT_WINDOW_MS,
    MAX_WINDOW_MS,
    PolicyResult,
    SampleClock,
    combine_membership,
    recent_activity,
)

MAX_IDENTITIES = 4096
MAX_GUARD_BYTES = 1024 * 1024
_DICT_TABLE_BASE = 512
_DICT_ENTRY_RESERVE = 128
_MAX_SAFE_INTEGER = 2**53 - 1
_MAX_WALL_MS = 4_000_000_000_000
_UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
_SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$")
_COMPONENTS = frozenset({"runtime", "history"})
_PROVIDER_KINDS = {"codex": "thread", "claude": "session"}


@dataclass(frozen=True, slots=True)
class WorkingSetDecision:
    """Synchronous decision and the exact borrowed supports used by branches.

    ``active_supports`` and ``recent_supports`` describe each positive branch,
    including current user-kind eligibility support when that dependency is
    needed. A false branch carries only its own negative evidence; the
    deduplicated ``negative_supports`` also includes eligibility support.
    ``negative_supports`` is the deduplicated set needed for the reported
    ``negative_kind``. Support mappings are borrowed read-only inputs: callers
    must consume them synchronously and must not mutate them. No mapping is
    retained by ``WorkingSetDecisions``.
    """

    eligibility: bool | None
    active: bool | None
    recent: PolicyResult
    selected: bool | None
    active_supports: tuple[Mapping[str, object], ...]
    recent_supports: tuple[Mapping[str, object], ...]
    negative_kind: str | None
    negative_supports: tuple[Mapping[str, object], ...]


def _uuid(value: object) -> bool:
    return isinstance(value, str) and _UUID.fullmatch(value) is not None


def _text(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    )


def _safe_nonnegative(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_SAFE_INTEGER


def _safe_signed(value: object) -> bool:
    return type(value) is int and -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER


def _unknown(reason: str) -> PolicyResult:
    return PolicyResult(None, reason)


def _source_context(source: object) -> tuple[str, str, int] | None:
    if not isinstance(source, Mapping):
        return None
    try:
        provider = source.get("provider")
        namespace = source.get("namespace")
        generation = source.get("contextGeneration")
        components = source.get("components")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if (
        not isinstance(provider, str)
        or provider not in _PROVIDER_KINDS
        or not _text(namespace, 128)
        or not _safe_nonnegative(generation)
        or not isinstance(components, (list, tuple))
        or len(components) > 2
    ):
        return None
    names: set[str] = set()
    for receipt in components:
        if not isinstance(receipt, Mapping):
            return None
        try:
            name = receipt.get("name")
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        if not isinstance(name, str) or name not in _COMPONENTS or name in names:
            return None
        names.add(name)
    return provider, namespace, generation


def _identity_parts(
    row: object, context: tuple[str, str, int]
) -> tuple[tuple[str, str, str, str], str] | None:
    if not isinstance(row, Mapping):
        return None
    try:
        identity = row.get("identity")
        if not isinstance(identity, Mapping):
            return None
        host_scope = identity.get("hostScope")
        provider = identity.get("provider")
        namespace = identity.get("namespace")
        native_id_kind = identity.get("nativeIdKind")
        native_id = identity.get("nativeId")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if (
        not isinstance(host_scope, str)
        or _SCOPE.fullmatch(host_scope) is None
        or not isinstance(provider, str)
        or provider != context[0]
        or not isinstance(namespace, str)
        or namespace != context[1]
        or not namespace.isascii()
        or not isinstance(native_id_kind, str)
        or _PROVIDER_KINDS.get(provider) != native_id_kind
        or not _uuid(native_id)
    ):
        return None
    return (host_scope, provider, namespace, native_id_kind), native_id


def _current_support(
    support: object,
    source: object,
    *,
    service_id: str,
    now_ms: int | None,
) -> bool:
    if not isinstance(support, Mapping) or now_ms is None:
        return False
    try:
        return support_matches(support, source, service_id=service_id, now_ms=now_ms)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _unique_supports(values: tuple[object, ...]) -> tuple[Mapping[str, object], ...]:
    result: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        try:
            duplicate = any(value == previous for previous in result)
        except (AttributeError, TypeError, ValueError):
            continue
        if not duplicate:
            result.append(value)
    return tuple(result)


def _valid_clock(clock: object) -> bool:
    if type(clock) is not SampleClock:
        return False
    return (
        _uuid(clock.sample_id)
        and isinstance(clock.origin_component, str)
        and clock.origin_component in _COMPONENTS
        and _uuid(clock.service_id)
        and _text(clock.provider, 64)
        and _text(clock.namespace, 128)
        and _safe_nonnegative(clock.context_generation)
        and _uuid(clock.boot_id)
        and _text(clock.clock_domain, 128)
        and _safe_nonnegative(clock.lower_boottime_ms)
        and type(clock.wall_ms) is int
        and 0 <= clock.wall_ms <= _MAX_WALL_MS
        and _safe_nonnegative(clock.upper_boottime_ms)
        and clock.lower_boottime_ms <= clock.upper_boottime_ms
    )


def _sample_join_reason(
    support: object,
    clock: object,
    source: object,
    *,
    service_id: str,
    now_ms: int,
    expected_sample_id: object,
) -> str | None:
    """Validate a current FactSupport against the exact accepted sample."""

    if not _valid_clock(clock):
        return "clock_unproved" if type(clock) is not SampleClock else "clock_invalid"
    assert isinstance(clock, SampleClock)
    if clock.service_id != service_id:
        return "clock_incarnation_mismatch"
    context = _source_context(source)
    if context is None:
        return "clock_scope_unproved"
    if (clock.provider, clock.namespace, clock.context_generation) != context:
        return "clock_context_mismatch"
    if not _uuid(expected_sample_id) or clock.sample_id != expected_sample_id:
        return "clock_sample_mismatch"
    if clock.upper_boottime_ms > now_ms:
        return "clock_from_future"
    if (
        not isinstance(support, Mapping)
        or support.get("sampledBoottimeMs") != clock.lower_boottime_ms
    ):
        return "activity_support_unproved"
    if not _current_support(support, source, service_id=service_id, now_ms=now_ms):
        return "activity_support_unproved"
    return None


def _no_turn_absence(
    row: object,
    fields: object,
    source: object,
    clock: object,
    *,
    service_id: str,
    now_ms: int,
    expected_sample_id: object,
) -> tuple[bool, Mapping[str, object] | None, str | None]:
    """Return only the explicit current empty-turn negative, never a guess."""

    if not isinstance(row, Mapping) or not isinstance(fields, Mapping):
        return False, None, None
    activity = row.get("activity")
    latest_turn = row.get("latestTurn")
    if not isinstance(activity, Mapping) or not isinstance(latest_turn, Mapping):
        return False, None, None
    try:
        is_empty_activity = (
            activity.get("health") == "unavailable"
            and activity.get("at") is None
            and activity.get("source") is None
            and activity.get("reason") == "no_conversation_activity"
        )
        is_empty_turn = (
            latest_turn.get("health") == "current"
            and latest_turn.get("value") is None
            and latest_turn.get("reason") == "no_native_turn"
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False, None, None
    if not is_empty_activity or not is_empty_turn:
        return False, None, None

    support = fields.get("latestTurn")
    reason = _sample_join_reason(
        support,
        clock,
        source,
        service_id=service_id,
        now_ms=now_ms,
        expected_sample_id=expected_sample_id,
    )
    if reason is not None:
        return False, None, reason

    # The public timing receipt and the private FactSupport must name the same
    # source component, sample time and source context. The expected collection
    # ID above separately binds that support to the canonical accepted input.
    receipt = latest_turn.get("receipt")
    if not isinstance(receipt, Mapping):
        return False, None, "latest_turn_support_unproved"
    try:
        if (
            receipt.get("component") != support.get("component")
            or receipt.get("sampledBoottimeMs") != support.get("sampledBoottimeMs")
            or receipt.get("contextGeneration") != support.get("contextGeneration")
            or not _safe_nonnegative(receipt.get("observedBoottimeMs"))
            or not clock.lower_boottime_ms
            <= receipt["observedBoottimeMs"]
            <= clock.upper_boottime_ms
            or latest_turn.get("source") is None
            or not _safe_nonnegative(latest_turn.get("observedAt"))
            or "lastKnownValue" in latest_turn
        ):
            return False, None, "latest_turn_support_unproved"
    except (AttributeError, KeyError, TypeError, ValueError):
        return False, None, "latest_turn_support_unproved"
    return True, support, None


class WorkingSetDecisions:
    """Classify one current source context with a bounded last-T guard.

    Call ``reset_context`` on initial binding and only after an actual
    provider/namespace/context-generation change. A new context clears the
    event guard and capacity latch, but never resets the global monotonic clock
    generation observed by this instance. New identities first seen after a
    detected clock discontinuity stay recency-unknown until their activity
    timestamp strictly advances.
    """

    def __init__(
        self,
        service_id: str,
        window_ms: int = DEFAULT_WINDOW_MS,
        max_identities: int = MAX_IDENTITIES,
        max_guard_bytes: int = MAX_GUARD_BYTES,
    ):
        if not _uuid(service_id):
            raise ValueError("working_set_service_id_invalid")
        if type(window_ms) is not int or not 0 <= window_ms <= MAX_WINDOW_MS:
            raise ValueError("working_set_window_invalid")
        if (
            type(max_identities) is not int
            or not 1 <= max_identities <= MAX_IDENTITIES
            or type(max_guard_bytes) is not int
            or not 1 <= max_guard_bytes <= MAX_GUARD_BYTES
        ):
            raise ValueError("working_set_guard_limits_invalid")
        self.service_id = service_id
        self.window_ms = window_ms
        self.max_identities = max_identities
        self.max_guard_bytes = max_guard_bytes
        self._context: tuple[str, str, int] | None = None
        # ``_identity_prefix`` is the exact shared host/provider/namespace/kind
        # boundary for this context. The dictionary retains only an owned
        # native-ID string per guard, after each row has matched that prefix.
        self._guards: dict[str, tuple[int, int]] = {}
        self._identity_prefix: tuple[str, str, str, str] | None = None
        self._prefix_bytes = 0
        self._guard_entries_bytes = 0
        self._guard_bytes = 0
        self._latched = False
        self._last_clock_generation = 0

    @property
    def latched(self) -> bool:
        """Whether recency is disabled after an event-guard capacity failure."""

        return self._latched

    @property
    def guard_count(self) -> int:
        """Number of retained full-identity timestamp guards."""

        return len(self._guards)

    @property
    def guard_bytes(self) -> int:
        """Conservative key/value heap plus prepaid dictionary-table bound."""

        return self._guard_bytes

    def reset_context(self, provider: str, namespace: str, context_generation: int) -> bool:
        """Bind a source context; clear guards only when the binding changes.

        Returns ``True`` for the initial binding or an actual context change.
        The global clock-discontinuity generation is intentionally retained.
        """

        if (
            not isinstance(provider, str)
            or provider not in _PROVIDER_KINDS
            or not _text(namespace, 128)
            or not namespace.isascii()
            or not _safe_nonnegative(context_generation)
        ):
            raise ValueError("working_set_context_invalid")
        context = provider, namespace, context_generation
        if context == self._context:
            return False
        if (
            self._context is not None
            and provider == self._context[0]
            and namespace == self._context[1]
            and context_generation < self._context[2]
        ):
            raise ValueError("working_set_context_regression")
        self._context = context
        self._guards.clear()
        self._identity_prefix = None
        self._prefix_bytes = 0
        self._guard_entries_bytes = 0
        self._guard_bytes = 0
        self._latched = False
        return True

    def classify(
        self,
        row: Mapping[str, object],
        fields: Mapping[str, object],
        source: Mapping[str, object],
        *,
        clock: SampleClock | None,
        clock_generation: int,
        clock_ceiling: int | None,
        now_ms: int,
        expected_sample_id: str | None,
    ) -> WorkingSetDecision:
        """Return E, A, R and their three-valued union for one admitted row.

        ``clock`` and ``expected_sample_id`` are canonical worker-private
        inputs supplied by the accepted-sample clock store. No public DTO can
        create them. ``clock_ceiling`` is the shared K for this service clock
        incarnation; it may shorten R-positive authority but never changes
        the current sample's upper/negative deadline. R1's older-event guard
        and R2's global K are separate: this instance retains one last T and
        epoch per full identity, but no event history or clock/support bank.
        """

        if not _safe_nonnegative(clock_generation):
            raise ValueError("working_set_clock_generation_invalid")
        if clock_generation < self._last_clock_generation:
            raise ValueError("working_set_clock_generation_regression")

        # Zero-window policy is a direct R=false rule and does not consult a
        # clock, activity value, receipt, timestamp guard or capacity latch.
        disabled_recent = PolicyResult(False, "window_disabled")
        now_valid = _safe_nonnegative(now_ms)
        context = _source_context(source)
        if context is None or context != self._context:
            return self._unresolved(
                "source_context_unproved",
                recent=disabled_recent if self.window_ms == 0 else None,
            )
        self._last_clock_generation = clock_generation

        identity = _identity_parts(row, context)
        if identity is None or not isinstance(row, Mapping) or not isinstance(fields, Mapping):
            return self._unresolved(
                "identity_unproved",
                recent=disabled_recent if self.window_ms == 0 else None,
            )
        identity_prefix, native_id = identity

        eligibility, eligibility_support = self._eligibility(
            row, fields, source, now_ms=now_ms if now_valid else None
        )
        active, active_core = self._active(
            row, fields, source, now_ms=now_ms if now_valid else None
        )

        if self.window_ms == 0:
            recent, recent_core = disabled_recent, ()
        elif eligibility is False:
            recent, recent_core = _unknown("eligibility_excluded"), ()
        elif not now_valid:
            recent, recent_core = _unknown("reader_clock_invalid"), ()
        else:
            recent, recent_core = self._recent(
                identity_prefix,
                native_id,
                row,
                fields,
                source,
                clock,
                clock_generation=clock_generation,
                clock_ceiling=clock_ceiling,
                now_ms=now_ms,
                expected_sample_id=expected_sample_id,
            )

        active_supports = active_core
        recent_supports = recent_core
        if eligibility is True and eligibility_support is not None:
            if active is True:
                active_supports = _unique_supports((*active_core, eligibility_support))
            if recent.decision is True:
                recent_supports = _unique_supports((*recent_core, eligibility_support))

        membership = combine_membership(eligibility, active, recent.decision)
        negative_kind: str | None = None
        negative_supports: tuple[Mapping[str, object], ...] = ()
        if membership.decision is False:
            if eligibility is False:
                negative_kind = "excluded_kind"
                negative_supports = _unique_supports((eligibility_support,))
            elif eligibility is True and active is False and recent.decision is False:
                negative_kind = (
                    "no_activity" if recent.reason == "no_native_turn" else "outside_window"
                )
                negative_supports = _unique_supports(
                    (*active_supports, *recent_supports, eligibility_support)
                )

        return WorkingSetDecision(
            eligibility=eligibility,
            active=active,
            recent=recent,
            selected=membership.decision,
            active_supports=active_supports,
            recent_supports=recent_supports,
            negative_kind=negative_kind,
            negative_supports=negative_supports,
        )

    def _unresolved(
        self,
        reason: str,
        *,
        recent: PolicyResult | None = None,
    ) -> WorkingSetDecision:
        result = _unknown(reason) if recent is None else recent
        return WorkingSetDecision(
            eligibility=None,
            active=None,
            recent=result,
            selected=None,
            active_supports=(),
            recent_supports=(),
            negative_kind=None,
            negative_supports=(),
        )

    def _eligibility(
        self,
        row: Mapping[str, object],
        fields: Mapping[str, object],
        source: Mapping[str, object],
        *,
        now_ms: int | None,
    ) -> tuple[bool | None, Mapping[str, object] | None]:
        kind = row.get("kind")
        if kind == "unknown":
            return True, None
        support = fields.get("kind")
        if (
            isinstance(kind, str)
            and kind in {"user", "child", "system"}
            and _current_support(support, source, service_id=self.service_id, now_ms=now_ms)
        ):
            return kind == "user", support
        return None, None

    def _active(
        self,
        row: Mapping[str, object],
        fields: Mapping[str, object],
        source: Mapping[str, object],
        *,
        now_ms: int | None,
    ) -> tuple[bool | None, tuple[Mapping[str, object], ...]]:
        runtime = row.get("runtime")
        runtime_support = fields.get("runtime")
        if (
            not isinstance(runtime, Mapping)
            or runtime.get("health") != "current"
            or not _current_support(
                runtime_support,
                source,
                service_id=self.service_id,
                now_ms=now_ms,
            )
        ):
            return None, ()
        if runtime.get("value") == "running":
            return True, _unique_supports((runtime_support,))
        if runtime.get("value") != "parked" or row.get("hasSavedHistory") is not True:
            return None, ()
        saved_support = fields.get("savedIdentity")
        if (
            not _current_support(
                saved_support,
                source,
                service_id=self.service_id,
                now_ms=now_ms,
            )
            or saved_support != runtime_support
        ):
            return None, ()
        return False, _unique_supports((runtime_support, saved_support))

    def _recent(
        self,
        identity_prefix: tuple[str, str, str, str],
        native_id: str,
        row: Mapping[str, object],
        fields: Mapping[str, object],
        source: Mapping[str, object],
        clock: SampleClock | None,
        *,
        clock_generation: int,
        clock_ceiling: int | None,
        now_ms: int,
        expected_sample_id: str | None,
    ) -> tuple[PolicyResult, tuple[Mapping[str, object], ...]]:
        if self._latched:
            return _unknown("recent_tracking_capacity"), ()

        no_turn, latest_turn_support, no_turn_reason = _no_turn_absence(
            row,
            fields,
            source,
            clock,
            service_id=self.service_id,
            now_ms=now_ms,
            expected_sample_id=expected_sample_id,
        )
        if no_turn:
            return PolicyResult(False, "no_native_turn"), _unique_supports((latest_turn_support,))
        if no_turn_reason is not None and _is_empty_no_turn_row(row):
            return _unknown(no_turn_reason), ()

        activity = row.get("activity")
        activity_support = fields.get("activity")
        candidate = recent_activity(
            activity if isinstance(activity, Mapping) else None,
            activity_support if isinstance(activity_support, Mapping) else None,
            clock,
            source,
            service_id=self.service_id,
            boot_id=clock.boot_id if isinstance(clock, SampleClock) else None,
            clock_domain=clock.clock_domain if isinstance(clock, SampleClock) else None,
            now_boottime_ms=now_ms,
            expected_sample_id=expected_sample_id,
            window_ms=self.window_ms,
        )
        lower = candidate.deadline_lower_boottime_ms
        upper = candidate.deadline_upper_boottime_ms
        if lower is None or upper is None:
            return candidate, ()
        if (
            not _safe_signed(clock_ceiling)
            or not isinstance(clock, SampleClock)
            or clock_ceiling < clock.wall_ms - clock.lower_boottime_ms + 1
        ):
            return _unknown("clock_ceiling_unproved"), ()

        event_at = activity.get("at") if isinstance(activity, Mapping) else None
        effective_lower = event_at + self.window_ms - clock_ceiling
        if not _safe_signed(effective_lower):
            return _unknown("cutoff_out_of_range"), ()

        guard_reason = self._guard_event(identity_prefix, native_id, event_at, clock_generation)
        if guard_reason is not None:
            return _unknown(guard_reason), ()

        if now_ms < effective_lower:
            decision, reason = True, "recent"
        elif now_ms >= upper:
            decision, reason = False, "outside_window"
        else:
            decision, reason = None, "clock_bracket_overlap"
        result = PolicyResult(decision, reason, effective_lower, upper)
        if decision is None:
            return result, ()
        return result, _unique_supports((activity_support,))

    @staticmethod
    def _owned_ascii(value: str) -> str:
        return value.encode("ascii").decode("ascii")

    @classmethod
    def _owned_prefix(cls, identity_prefix: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
        return tuple(cls._owned_ascii(part) for part in identity_prefix)  # type: ignore[return-value]

    @staticmethod
    def _prefix_charge(prefix: tuple[str, str, str, str]) -> int:
        # The prefix strings and tuple are owned once per active source context.
        # Count both their ASCII encoding and interpreter heap representation.
        return (
            sum(len(part.encode("ascii")) + 1 for part in prefix)
            + sys.getsizeof(prefix)
            + sum(sys.getsizeof(part) for part in prefix)
        )

    @staticmethod
    def _guard_entry_charge(native_id: str, event_at: int, epoch: int) -> int:
        # The exact identity prefix is owned once per context. Each entry owns
        # only its native-ID string plus timestamp/epoch value and event pair.
        # Dictionary capacity is prepaid separately before growth.
        event = (event_at, epoch)
        return (
            len(native_id.encode("ascii"))
            + sys.getsizeof(native_id)
            + sys.getsizeof(event)
            + sys.getsizeof(event_at)
            + sys.getsizeof(epoch)
        )

    @staticmethod
    def _dict_table_reserve(identity_count: int) -> int:
        # This bound covers the mapping header/table plus old-and-new table
        # overlap during any CPython resize up to the configured identity cap.
        return _DICT_TABLE_BASE + _DICT_ENTRY_RESERVE * identity_count

    def _refresh_guard_bytes(self) -> int:
        self._guard_bytes = (
            self._prefix_bytes
            + self._guard_entries_bytes
            + self._dict_table_reserve(len(self._guards))
        )
        return self._guard_bytes

    def _latch_capacity(self) -> str:
        self._latched = True
        self._guards.clear()
        self._identity_prefix = None
        self._prefix_bytes = 0
        self._guard_entries_bytes = 0
        self._guard_bytes = 0
        return "recent_tracking_capacity"

    def _guard_event(
        self,
        identity_prefix: tuple[str, str, str, str],
        native_id: str,
        event_at: object,
        clock_generation: int,
    ) -> str | None:
        if type(event_at) is not int or not 0 <= event_at <= _MAX_SAFE_INTEGER:
            return "activity_unavailable"
        if self._latched:
            return "recent_tracking_capacity"

        if self._identity_prefix is not None and self._identity_prefix != identity_prefix:
            return "identity_scope_mismatch"

        # This row's exact prefix was compared above. The per-context map can
        # therefore use only the native ID without widening identity scope.
        # The fixed table-base reserve includes lookup/encoding scratch.
        previous = self._guards.get(native_id)
        if previous is not None:
            previous_at, confirmed_generation = previous
            if event_at < previous_at:
                return "activity_timestamp_regression"
            if event_at == previous_at:
                if clock_generation > confirmed_generation:
                    return "clock_discontinuity"
                return None
            old_charge = self._guard_entry_charge(
                native_id, previous_at, confirmed_generation
            )
        else:
            if len(self._guards) >= self.max_identities:
                return self._latch_capacity()
            old_charge = 0

        # A first event after a clock discontinuity is retained as a key but
        # remains unconfirmed; only a strictly newer supported T can reopen R.
        epoch = clock_generation if previous is not None or clock_generation == 0 else -1
        new_charge = self._guard_entry_charge(native_id, event_at, epoch)
        prefix_bytes = (
            self._prefix_bytes
            if self._identity_prefix is not None
            else self._prefix_charge(identity_prefix)
        )
        next_count = len(self._guards) + (previous is None)
        # Existing value credit remains charged while a replacement tuple is
        # created. A new identity also prepays its table slot before either
        # owned strings or a dictionary resize can occur.
        projected_entries = self._guard_entries_bytes + new_charge
        projected = prefix_bytes + projected_entries + self._dict_table_reserve(next_count)
        if projected > self.max_guard_bytes:
            return self._latch_capacity()

        owned_prefix = self._identity_prefix
        if owned_prefix is None:
            owned_prefix = self._owned_prefix(identity_prefix)
        # Existing-key assignment replaces only its event value; CPython keeps
        # the stored owned key object. New keys are copied only after quota
        # preflight succeeds.
        guard_key = native_id if previous is not None else self._owned_ascii(native_id)
        self._guards[guard_key] = event_at, epoch
        if self._identity_prefix is None:
            self._identity_prefix = owned_prefix
            self._prefix_bytes = prefix_bytes
        self._guard_entries_bytes = self._guard_entries_bytes - old_charge + new_charge
        if self._refresh_guard_bytes() > self.max_guard_bytes:
            # The preflight bound is tested on each supported interpreter. Keep
            # this fail-closed check if a future mapping topology changes.
            return self._latch_capacity()
        if previous is None and clock_generation > 0:
            return "clock_discontinuity"
        return None


def _is_empty_no_turn_row(row: object) -> bool:
    if not isinstance(row, Mapping):
        return False
    activity = row.get("activity")
    latest_turn = row.get("latestTurn")
    if not isinstance(activity, Mapping) or not isinstance(latest_turn, Mapping):
        return False
    return (
        activity.get("health") == "unavailable"
        and activity.get("at") is None
        and activity.get("source") is None
        and activity.get("reason") == "no_conversation_activity"
        and latest_turn.get("health") == "current"
        and latest_turn.get("value") is None
        and latest_turn.get("reason") == "no_native_turn"
    )
