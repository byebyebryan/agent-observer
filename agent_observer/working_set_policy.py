"""Pure recency and active/recent union decisions for a bounded working set.

The caller supplies a trusted private clock bracket tied to the accepted source
snapshot. This module does not capture clocks, own state, renew support, or keep
an established cutoff across later generations.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .observation_support import support_matches

DEFAULT_WINDOW_MS = 72 * 60 * 60 * 1000
MAX_WINDOW_MS = 30 * 24 * 60 * 60 * 1000
_UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
_COMPONENTS = frozenset({"runtime", "history"})


@dataclass(frozen=True)
class SampleClock:
    """Private clock bracket for one accepted source snapshot.

    ``sample_id`` is the source snapshot's collectionId. ``origin_component``
    identifies the worker job that made it; it may differ from a current
    FactSupport component when the history sample is mirrored into runtime.
    ``lower_boottime_ms`` (L), ``wall_ms`` (W), and ``upper_boottime_ms`` (U)
    are trusted capture metadata, not fields admitted from a native DTO.
    """

    sample_id: str
    origin_component: str
    service_id: str
    provider: str
    namespace: str
    context_generation: int
    boot_id: str
    clock_domain: str
    lower_boottime_ms: int
    wall_ms: int
    upper_boottime_ms: int


@dataclass(frozen=True)
class PolicyResult:
    """Three-valued result; deadline fields are absent when not safely usable."""

    decision: bool | None
    reason: str
    deadline_lower_boottime_ms: int | None = None
    deadline_upper_boottime_ms: int | None = None


def _exact_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _uuid(value: object) -> bool:
    return isinstance(value, str) and _UUID.fullmatch(value) is not None


def _bounded_text(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    )


def _unknown(reason: str) -> PolicyResult:
    return PolicyResult(None, reason)


def recent_activity(
    activity: Mapping[str, object] | None,
    activity_support: Mapping[str, object] | None,
    sample_clock: SampleClock | None,
    source: Mapping[str, object] | None,
    *,
    service_id: object,
    boot_id: object,
    clock_domain: object,
    now_boottime_ms: object,
    expected_sample_id: object,
    window_ms: int = DEFAULT_WINDOW_MS,
) -> PolicyResult:
    """Classify current activity against a trusted, floored clock bracket.

    Current recent membership is proved only before the conservative lower
    deadline. Outside-window is proved only at or after the conservative upper
    deadline. The interval between them remains unknown. A one-millisecond
    outward allowance accounts for floored wall and BOOTTIME capture values.
    The published integer activity.at value is the policy timestamp; this helper
    does not add sub-second event uncertainty.

    This is stateless by design. A later accepted sample with the same activity
    timestamp can produce a later bracket; a future cache must preserve the
    established event-key cutoff across generations.
    """

    if type(window_ms) is not int or not 0 <= window_ms <= MAX_WINDOW_MS:
        raise ValueError("working_set_window_invalid")
    if window_ms == 0:
        return PolicyResult(False, "window_disabled")

    if not _exact_nonnegative_int(now_boottime_ms):
        return _unknown("reader_clock_invalid")
    if (
        not isinstance(activity, Mapping)
        or activity.get("health") != "current"
        or not _exact_nonnegative_int(activity.get("at"))
        or not _bounded_text(activity.get("source"), 128)
    ):
        return _unknown("activity_unavailable")
    if not isinstance(sample_clock, SampleClock):
        return _unknown("clock_unproved")
    if (
        not _uuid(sample_clock.sample_id)
        or not _bounded_text(sample_clock.origin_component, 32)
        or sample_clock.origin_component not in _COMPONENTS
        or not _uuid(sample_clock.service_id)
        or not _bounded_text(sample_clock.provider, 64)
        or not _bounded_text(sample_clock.namespace, 128)
        or not _exact_nonnegative_int(sample_clock.context_generation)
        or not _uuid(sample_clock.boot_id)
        or not _bounded_text(sample_clock.clock_domain, 128)
        or not _exact_nonnegative_int(sample_clock.lower_boottime_ms)
        or not _exact_nonnegative_int(sample_clock.wall_ms)
        or not _exact_nonnegative_int(sample_clock.upper_boottime_ms)
        or sample_clock.lower_boottime_ms > sample_clock.upper_boottime_ms
    ):
        return _unknown("clock_invalid")

    if (
        not _uuid(service_id)
        or not _uuid(boot_id)
        or not _bounded_text(clock_domain, 128)
        or not isinstance(source, Mapping)
    ):
        return _unknown("clock_scope_unproved")
    if (
        sample_clock.service_id != service_id
        or sample_clock.boot_id != boot_id
        or sample_clock.clock_domain != clock_domain
    ):
        return _unknown("clock_incarnation_mismatch")
    if (
        sample_clock.provider != source.get("provider")
        or sample_clock.namespace != source.get("namespace")
        or sample_clock.context_generation != source.get("contextGeneration")
    ):
        return _unknown("clock_context_mismatch")
    if not _uuid(expected_sample_id) or sample_clock.sample_id != expected_sample_id:
        return _unknown("clock_sample_mismatch")
    if (
        not isinstance(activity_support, Mapping)
        or activity_support.get("sampledBoottimeMs") != sample_clock.lower_boottime_ms
    ):
        return _unknown("activity_support_unproved")
    try:
        support_current = support_matches(
            activity_support,
            source,
            service_id=service_id,
            now_ms=now_boottime_ms,
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        support_current = False
    if not support_current:
        return _unknown("activity_support_unproved")
    if sample_clock.upper_boottime_ms > now_boottime_ms:
        return _unknown("clock_from_future")

    age_ms = sample_clock.wall_ms - activity["at"]
    if age_ms < 0:
        return _unknown("activity_in_future")

    # Inputs are floored to integer milliseconds. Subtract one millisecond from
    # the positive bound and add one to the negative bound; never compare raw
    # owner BOOTTIME to a remote clock here.
    lower = sample_clock.lower_boottime_ms + window_ms - age_ms - 1
    upper = sample_clock.upper_boottime_ms + window_ms - age_ms + 1
    now = now_boottime_ms
    if now < lower:
        decision, reason = True, "recent"
    elif now >= upper:
        decision, reason = False, "outside_window"
    else:
        decision, reason = None, "clock_bracket_overlap"
    return PolicyResult(decision, reason, lower, upper)


def combine_membership(
    eligible: bool | None,
    active: bool | None,
    recent: bool | None,
) -> PolicyResult:
    """Evaluate E AND (A OR R) with strong three-valued evidence.

    A proved positive branch wins despite an unknown sibling branch. Unknown
    eligibility cannot produce a positive result, and exclusion requires the
    active and recent alternatives both to be proved false.
    """

    if any(value is not None and type(value) is not bool for value in (eligible, active, recent)):
        raise ValueError("working_set_evidence_invalid")
    if eligible is False:
        return PolicyResult(False, "ineligible")
    if active is True or recent is True:
        if eligible is True:
            return PolicyResult(True, "selected")
        return PolicyResult(None, "eligibility_unproved")
    if active is False and recent is False:
        return PolicyResult(False, "no_membership_branch")
    return PolicyResult(None, "membership_unresolved")
