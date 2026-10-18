"""Bounded accepted-sample clock authority for the working-set owner.

This pure store keeps clocks for the current source context and constant-size
clock-incarnation metadata. It does not accept snapshots, capture clocks, or
grant activity/current-row authority; its caller installs a clock only after
the canonical worker snapshot has actually been accepted.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .observation_support import support_matches
from .working_set_policy import SampleClock

_MAX_SAFE_INTEGER = 2**53 - 1
_MAX_WALL_MS = 4_000_000_000_000
_UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
_COMPONENTS = frozenset({"runtime", "history"})


@dataclass(frozen=True, slots=True)
class _Binding:
    accepted: int
    clock: SampleClock


def _uuid(value: object) -> bool:
    return isinstance(value, str) and _UUID.fullmatch(value) is not None


def _bounded_text(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    )


def _safe_nonnegative_int(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_SAFE_INTEGER


def _copy_clock(clock: SampleClock) -> SampleClock:
    return SampleClock(
        sample_id=clock.sample_id,
        origin_component=clock.origin_component,
        service_id=clock.service_id,
        provider=clock.provider,
        namespace=clock.namespace,
        context_generation=clock.context_generation,
        boot_id=clock.boot_id,
        clock_domain=clock.clock_domain,
        lower_boottime_ms=clock.lower_boottime_ms,
        wall_ms=clock.wall_ms,
        upper_boottime_ms=clock.upper_boottime_ms,
    )


def _source_context(source: object) -> tuple[str, str, int] | None:
    if not isinstance(source, Mapping):
        return None
    try:
        provider = source.get("provider")
        namespace = source.get("namespace")
        generation = source.get("contextGeneration")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if (
        not _bounded_text(provider, 64)
        or not _bounded_text(namespace, 128)
        or not _safe_nonnegative_int(generation)
    ):
        return None
    return provider, namespace, generation


def _source_receipts(source: object) -> dict[str, Mapping[str, object]] | None:
    if not isinstance(source, Mapping):
        return None
    try:
        components = source.get("components")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if not isinstance(components, (list, tuple)) or len(components) > 2:
        return None

    receipts: dict[str, Mapping[str, object]] = {}
    for receipt in components:
        if not isinstance(receipt, Mapping):
            return None
        try:
            component = receipt.get("name")
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        if (
            type(component) is not str
            or component not in _COMPONENTS
            or component in receipts
        ):
            return None
        receipts[component] = receipt
    return receipts


def _safe_support(support: Mapping[str, object]) -> bool:
    try:
        context_generation = support.get("contextGeneration")
        accepted = support.get("accepted")
        sampled = support.get("sampledBoottimeMs")
        expires = support.get("expiresBoottimeMs")
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return (
        _safe_nonnegative_int(context_generation)
        and type(accepted) is int
        and 1 <= accepted <= _MAX_SAFE_INTEGER
        and _safe_nonnegative_int(sampled)
        and _safe_nonnegative_int(expires)
        and sampled < expires
    )


def _validated_clock(
    clock: object,
    *,
    service_id: str,
    boot_id: str,
    clock_domain: str,
) -> tuple[SampleClock, tuple[str, str, int], tuple[int, int], int]:
    if type(clock) is not SampleClock:
        raise ValueError("working_set_clock_invalid")
    try:
        owned = _copy_clock(clock)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("working_set_clock_invalid") from None

    if (
        not _uuid(owned.sample_id)
        or not isinstance(owned.origin_component, str)
        or owned.origin_component not in _COMPONENTS
        or not _uuid(owned.service_id)
        or not _bounded_text(owned.provider, 64)
        or not _bounded_text(owned.namespace, 128)
        or not _safe_nonnegative_int(owned.context_generation)
        or not _uuid(owned.boot_id)
        or not _bounded_text(owned.clock_domain, 128)
        or not _safe_nonnegative_int(owned.lower_boottime_ms)
        or not _safe_nonnegative_int(owned.upper_boottime_ms)
        or type(owned.wall_ms) is not int
        or not 0 <= owned.wall_ms <= _MAX_WALL_MS
        or owned.lower_boottime_ms > owned.upper_boottime_ms
        or owned.service_id != service_id
        or owned.boot_id != boot_id
        or owned.clock_domain != clock_domain
    ):
        raise ValueError("working_set_clock_invalid")

    interval = (
        owned.wall_ms - owned.upper_boottime_ms - 1,
        owned.wall_ms - owned.lower_boottime_ms + 1,
    )
    ceiling_candidate = interval[1]
    if any(not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER for value in interval):
        raise ValueError("working_set_clock_invalid")
    context = owned.provider, owned.namespace, owned.context_generation
    return owned, context, interval, ceiling_candidate


class WorkingSetClocks:
    """Store current component clocks and monotonic clock-incarnation state.

    At most the runtime/history bindings for one source context are retained.
    The ceiling, last outward interval, last sample and discontinuity generation
    are global to this instance's service/boot/clock-domain incarnation and
    survive source-context retirement.
    """

    def __init__(self, service_id: str, boot_id: str, clock_domain: str):
        if (
            not _uuid(service_id)
            or not _uuid(boot_id)
            or not _bounded_text(clock_domain, 128)
        ):
            raise ValueError("working_set_clock_incarnation_invalid")
        self._service_id = service_id
        self._boot_id = boot_id
        self._clock_domain = clock_domain
        self._context: tuple[str, str, int] | None = None
        self._bindings: dict[str, _Binding] = {}
        self._ceiling: int | None = None
        self._last_interval: tuple[int, int] | None = None
        self._last_clock: SampleClock | None = None
        self._generation = 0

    @property
    def ceiling(self) -> int | None:
        """Maximum accepted ``W-L+1`` for this clock incarnation."""

        return self._ceiling

    @property
    def generation(self) -> int:
        """Detected wall/BOOTTIME discontinuity epoch for this incarnation."""

        return self._generation

    def accept(self, clock: SampleClock, *, component: str, accepted: int) -> None:
        """Install a clock for one actually accepted source component receipt.

        Invalid, regressed or reused binding inputs raise ``ValueError`` and
        leave all state unchanged. A mirrored copy of a known sample may add a
        component binding but does not advance the global clock sequence.
        """

        if type(component) is not str or component not in _COMPONENTS:
            raise ValueError("working_set_clock_invalid")
        if type(accepted) is not int or not 1 <= accepted <= _MAX_SAFE_INTEGER:
            raise ValueError("working_set_clock_invalid")
        owned, context, interval, ceiling_candidate = _validated_clock(
            clock,
            service_id=self._service_id,
            boot_id=self._boot_id,
            clock_domain=self._clock_domain,
        )

        same_context = context == self._context
        current = self._bindings if same_context else {}
        prior = current.get(component)
        if prior is not None:
            if accepted < prior.accepted:
                raise ValueError("working_set_clock_regression")
            if accepted == prior.accepted:
                if owned == prior.clock:
                    return
                raise ValueError("working_set_clock_regression")
            if owned.sample_id == prior.clock.sample_id:
                raise ValueError("working_set_clock_regression")

        known_sample = False
        for binding in current.values():
            if binding.clock.sample_id == owned.sample_id:
                if binding.clock != owned:
                    raise ValueError("working_set_clock_invalid")
                known_sample = True
        if self._last_clock is not None and self._last_clock.sample_id == owned.sample_id:
            if self._last_clock != owned:
                raise ValueError("working_set_clock_invalid")
            known_sample = True

        next_generation = self._generation
        next_ceiling = self._ceiling
        next_interval = self._last_interval
        next_clock = self._last_clock
        if not known_sample:
            if self._last_interval is not None:
                old_lower, old_upper = self._last_interval
                new_lower, new_upper = interval
                if new_upper < old_lower or new_lower > old_upper:
                    next_generation += 1
                    if next_generation > _MAX_SAFE_INTEGER:
                        raise ValueError("working_set_clock_invalid")
            next_ceiling = (
                ceiling_candidate
                if next_ceiling is None
                else max(next_ceiling, ceiling_candidate)
            )
            next_interval = interval
            next_clock = owned

        next_bindings = dict(current)
        next_bindings[component] = _Binding(accepted=accepted, clock=owned)

        # Commit only after every validation, regression and arithmetic check.
        self._context = context
        self._bindings = next_bindings
        self._ceiling = next_ceiling
        self._last_interval = next_interval
        self._last_clock = next_clock
        self._generation = next_generation

    def get(
        self,
        support: Mapping[str, object] | None,
        source: Mapping[str, object] | None,
        *,
        sample_id: object,
    ) -> SampleClock | None:
        """Return a detached clock for its exact receipt and expected snapshot ID.

        ``sample_id`` is the caller's expected accepted-snapshot collectionId;
        timestamps and receipt counters cannot stand in for that join.
        """

        context = _source_context(source)
        receipts = _source_receipts(source)
        if (
            context is None
            or context != self._context
            or receipts is None
            or not _uuid(sample_id)
        ):
            return None
        if not isinstance(support, Mapping):
            return None
        try:
            component = support.get("component")
            binding = self._bindings.get(component)
            if (
                binding is None
                or component not in receipts
                or sample_id != binding.clock.sample_id
                or support.get("accepted") != binding.accepted
                or support.get("sampledBoottimeMs") != binding.clock.lower_boottime_ms
                or not _safe_support(support)
                or not support_matches(
                    support,
                    source,
                    service_id=self._service_id,
                )
            ):
                return None
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        return _copy_clock(binding.clock)

    def export(self, source: Mapping[str, object] | None) -> list[dict[str, object]]:
        """Export detached clock DTOs that match current source receipts."""

        context = _source_context(source)
        receipts = _source_receipts(source)
        if context is None or context != self._context or receipts is None:
            return []

        result: list[dict[str, object]] = []
        for component in sorted(self._bindings):
            binding = self._bindings[component]
            receipt = receipts.get(component)
            if receipt is None:
                continue
            try:
                health = receipt.get("health")
                accepted = receipt.get("accepted")
                sampled = receipt.get("sampledBoottimeMs")
                expires = receipt.get("expiresBoottimeMs")
            except (AttributeError, KeyError, TypeError, ValueError):
                return []
            if (
                not isinstance(health, str)
                or health not in {"current", "partial"}
                or type(accepted) is not int
                or not 1 <= accepted <= _MAX_SAFE_INTEGER
                or not _safe_nonnegative_int(sampled)
                or not _safe_nonnegative_int(expires)
                or sampled >= expires
                or accepted != binding.accepted
                or sampled != binding.clock.lower_boottime_ms
            ):
                continue
            clock = binding.clock
            result.append(
                {
                    "component": component,
                    "accepted": accepted,
                    "sampleId": clock.sample_id,
                    "originComponent": clock.origin_component,
                    "sampledBoottimeMs": clock.lower_boottime_ms,
                    "wallMs": clock.wall_ms,
                    "acceptedBoottimeMs": clock.upper_boottime_ms,
                }
            )
        return result
