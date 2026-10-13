"""Offline normalized-metadata model; not a runtime module or wire validator.

One tracker belongs to one observer/boot/time-namespace lifetime. All clocks,
provider-owned facts and admitted source generations are explicit caller inputs.
No IO, production imports, native predicates, networking or durable ledger.
"""

from collections import OrderedDict
from dataclasses import dataclass

MAX_CLOCK = 2**63 - 1
MAX_EPOCH = 4_000_000_000_000
PHASES = frozenset({"working", "blocked", "waiting"})
STATUSES = frozenset({"in_progress", "completed", "failed", "cancelled", "unknown"})


def integer(value, maximum=MAX_CLOCK):
    return type(value) is int and 0 <= value <= maximum


def text(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and all(32 <= ord(c) < 127 for c in value)


@dataclass(frozen=True)
class Ref:
    host: str
    provider: str
    namespace: str
    id_kind: str
    native_id: str

    def __post_init__(self):
        if not all(text(v) for v in vars(self).values()):
            raise ValueError("identity_invalid")

    @property
    def source(self):
        return self.host, self.provider, self.namespace


@dataclass(frozen=True)
class Stamp:
    generation: int
    sampled_ms: int
    seen_ms: int
    wall_ms: int
    expires_ms: int
    observer_id: str = "observer-a"
    clock_domain: str = "boot-a:ns-a"

    def __post_init__(self):
        if (not all(integer(v) for v in (self.generation, self.sampled_ms, self.seen_ms,
                                      self.wall_ms, self.expires_ms))
                or not text(self.observer_id) or not text(self.clock_domain)
                or self.wall_ms > MAX_EPOCH
                or not self.sampled_ms <= self.seen_ms or self.expires_ms <= self.sampled_ms):
            raise ValueError("stamp_invalid")

    def current(self, now):
        return self.seen_ms <= now < self.expires_ms


@dataclass(frozen=True)
class PhaseRow:
    ref: Ref
    runtime: str
    phase: str | None
    turn_id: str | None = None

    def __post_init__(self):
        if (not isinstance(self.ref, Ref) or not isinstance(self.runtime, str)
                or self.runtime not in {"running", "parked", "unknown"}
                or self.phase is not None and (not isinstance(self.phase, str) or self.phase not in PHASES)
                or self.runtime != "running" and self.phase is not None
                or self.turn_id is not None and not text(self.turn_id)):
            raise ValueError("phase_row_invalid")


@dataclass(frozen=True)
class Batch:
    source: tuple[str, str, str]
    stamp: Stamp
    rows: tuple[PhaseRow, ...]
    healthy: bool = True
    complete: bool = True

    def __post_init__(self):
        if (not isinstance(self.source, tuple) or len(self.source) != 3
                or not all(text(v) for v in self.source) or not isinstance(self.stamp, Stamp)
                or not isinstance(self.rows, tuple) or len(self.rows) > 1512
                or type(self.healthy) is not bool or type(self.complete) is not bool
                or not all(isinstance(r, PhaseRow) and r.ref.source == self.source for r in self.rows)
                or len({r.ref for r in self.rows}) != len(self.rows)):
            raise ValueError("batch_invalid")


@dataclass(frozen=True)
class Streak:
    phase: str
    turn_id: str | None
    first_ms: int
    first_wall_ms: int
    last_seen_ms: int
    expires_ms: int
    generation: int
    series: int


class PhaseTracker:
    """Bounded observed series; fresh runtime batches are the only renewal input."""

    def __init__(self, *, observer_id, clock_domain, sources, capacity=512):
        if (not text(observer_id) or not text(clock_domain) or not isinstance(sources, dict)
                or not 1 <= len(sources) <= 32 or not integer(capacity, 1512) or capacity == 0
                or any(not isinstance(k, tuple) or len(k) != 3 or not all(text(v) for v in k)
                       or not integer(v) for k, v in sources.items())):
            raise ValueError("tracker_config_invalid")
        self.observer_id, self.clock_domain = observer_id, clock_domain
        self.generations, self.capacity = dict(sources), capacity
        self.watermarks = dict.fromkeys(sources, -1)
        self.entries = OrderedDict()
        self.now, self.series, self.terminal = -1, 0, False

    def _clock(self, now):
        if self.terminal:
            raise ValueError("tracker_terminal")
        if not integer(now) or now < self.now:
            self.entries.clear()
            self.terminal = True
            raise ValueError("clock_invalid")
        self.now = now
        for ref in list(self.entries):
            if self.entries[ref].expires_ms <= now:
                del self.entries[ref]

    def advance_generation(self, source, generation, *, now):
        self._clock(now)
        if source not in self.generations or not integer(generation) or generation <= self.generations[source]:
            raise ValueError("generation_invalid")
        self.generations[source], self.watermarks[source] = generation, -1
        for ref in list(self.entries):
            if ref.source == source:
                del self.entries[ref]

    def accept_runtime(self, batch, *, now):
        self._clock(now)
        if not isinstance(batch, Batch) or batch.source not in self.generations:
            raise ValueError("source_invalid")
        if (batch.stamp.observer_id, batch.stamp.clock_domain) != (self.observer_id, self.clock_domain):
            raise ValueError("observation_scope")
        if batch.stamp.generation != self.generations[batch.source]:
            return {"accepted": False, "reason": "generation_mismatch"}
        if batch.stamp.seen_ms > now:
            raise ValueError("future_observation")
        previous = self.watermarks[batch.source]
        if batch.stamp.sampled_ms < previous:
            return {"accepted": False, "reason": "late_sample"}
        # Equal start times cannot order separate worker reads. Invalidate the
        # optional timer conservatively; a repeated carrier frame is not an
        # engine acceptance and must never call this method again.
        if batch.stamp.sampled_ms == previous:
            self._clear_source(batch.source)
            return {"accepted": False, "reason": "equal_order_ambiguous"}
        self.watermarks[batch.source] = batch.stamp.sampled_ms
        if not batch.healthy or not batch.stamp.current(now):
            self._clear_source(batch.source)
            return {"accepted": True, "reason": "source_gap"}
        present = {row.ref for row in batch.rows}
        # Missing rows in complete or partial batches break observed continuity;
        # they supply no parked assertion. Positive sibling series can continue.
        for ref in list(self.entries):
            if ref.source == batch.source and ref not in present:
                del self.entries[ref]
        skipped = 0
        # Protect existing admitted series ahead of newly seen identities.
        rows = sorted(batch.rows, key=lambda row: row.ref not in self.entries)
        for row in rows:
            if row.runtime != "running" or row.phase not in PHASES:
                self.entries.pop(row.ref, None)
                continue
            prior = self.entries.get(row.ref)
            if prior is None and len(self.entries) >= self.capacity:
                skipped += 1
                continue
            same = prior is not None and (prior.phase, prior.turn_id) == (row.phase, row.turn_id)
            if not same:
                self.series += 1
            self.entries[row.ref] = Streak(
                row.phase, row.turn_id,
                prior.first_ms if same else batch.stamp.seen_ms,
                prior.first_wall_ms if same else batch.stamp.wall_ms,
                batch.stamp.seen_ms, batch.stamp.expires_ms, batch.stamp.generation,
                prior.series if same else self.series,
            )
        return {"accepted": True, "reason": "capacity" if skipped else "observed", "skipped": skipped}

    def _clear_source(self, source):
        for ref in list(self.entries):
            if ref.source == source:
                del self.entries[ref]

    def view(self, ref, *, now):
        self._clock(now)
        value = self.entries.get(ref)
        if value is None:
            return None
        return {
            "basis": "observed_series", "observerId": self.observer_id,
            "clockDomain": self.clock_domain, "generation": value.generation,
            "series": value.series, "phase": value.phase, "turnId": value.turn_id,
            "firstObservedAt": value.first_wall_ms,
            "observedSpanMs": now - value.first_ms, "expiresMs": value.expires_ms,
        }


@dataclass(frozen=True)
class Turn:
    id: str | None
    status: str
    start_ms: int | None
    end_ms: int | None
    duration_ms: int | None = None
    precision_ms: int = 1000

    def __post_init__(self):
        if (self.id is not None and not text(self.id)
                or not isinstance(self.status, str) or self.status not in STATUSES
                or not integer(self.precision_ms, 60_000) or self.precision_ms == 0
                or any(v is not None and not integer(v, MAX_EPOCH) for v in (self.start_ms, self.end_ms))
                or self.duration_ms is not None and not integer(self.duration_ms, MAX_EPOCH)
                or self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms
                or self.status == "in_progress" and (self.end_ms is not None or self.duration_ms is not None)):
            raise ValueError("turn_invalid")


@dataclass(frozen=True)
class TurnSample:
    ref: Ref
    stamp: Stamp
    component: str
    turn: Turn | None
    healthy: bool = True
    admitted: bool = True

    def __post_init__(self):
        if (not isinstance(self.ref, Ref) or not isinstance(self.stamp, Stamp)
                or not isinstance(self.component, str) or self.component not in {"runtime", "history"}
                or self.turn is not None and not isinstance(self.turn, Turn)
                or type(self.healthy) is not bool or type(self.admitted) is not bool):
            raise ValueError("turn_sample_invalid")


def select_latest(samples, *, ref, generation, observer_id, clock_domain, now):
    """Newest receipt first; expiry/unknown does not revive an older completion."""
    if (not isinstance(samples, tuple) or len(samples) > 2 or not integer(now) or not isinstance(ref, Ref)
            or not integer(generation) or not text(observer_id) or not text(clock_domain)):
        raise ValueError("selection_invalid")
    if any(not isinstance(sample, TurnSample) or sample.ref != ref for sample in samples):
        raise ValueError("selection_scope")
    if len({sample.component for sample in samples}) != len(samples):
        raise ValueError("selection_components")
    matching = [sample for sample in samples if sample.stamp.generation == generation
                and sample.stamp.observer_id == observer_id and sample.stamp.clock_domain == clock_domain]
    if not matching:
        return {"sample": None, "health": "unavailable", "reason": "source_context"}
    newest = max(sample.stamp.sampled_ms for sample in matching)
    winners = [sample for sample in matching if sample.stamp.sampled_ms == newest]
    if len(winners) == 2 and winners[0].turn != winners[1].turn:
        return {"sample": None, "health": "ambiguous", "reason": "equal_order_conflict"}
    # Same observation bound to two leases is conservatively admitted under
    # the earlier deadline; there is no longer-lease tie-breaking shortcut.
    sample = min(winners, key=lambda item: item.stamp.expires_ms)
    if sample.stamp.seen_ms > now:
        raise ValueError("future_observation")
    if not sample.healthy or not sample.stamp.current(now):
        return {"sample": sample, "health": "stale", "reason": "receipt_expired_or_failed"}
    if not sample.admitted:
        return {"sample": sample, "health": "unavailable", "reason": "native_timing_unproved"}
    return {"sample": sample, "health": "current", "reason": "native_metadata"}


def current_turn_age(selection, *, row, runtime_stamp, now):
    """A compatible latest observed ongoing turn, never exact phase duration."""
    if not integer(now) or not isinstance(row, PhaseRow) or not isinstance(runtime_stamp, Stamp):
        raise ValueError("timer_input_invalid")
    sample = selection["sample"]
    if (selection["health"] != "current" or sample is None or sample.ref != row.ref
            or sample.turn is None or sample.turn.status != "in_progress"
            or sample.stamp.generation != runtime_stamp.generation
            or (sample.stamp.observer_id, sample.stamp.clock_domain) != (runtime_stamp.observer_id, runtime_stamp.clock_domain)
            or not runtime_stamp.current(now) or row.runtime != "running"
            or row.phase not in {"working", "blocked"}):
        return {"ageMs": None, "reason": "samples_incompatible_or_unavailable"}
    turn = sample.turn
    if row.turn_id is not None and row.turn_id != turn.id:
        return {"ageMs": None, "reason": "turn_identity_race"}
    if turn.start_ms is None:
        return {"ageMs": None, "reason": "start_unavailable"}
    # A start definitely later than the status observation cannot describe the
    # turn that supplied that earlier status; allow the declared quantization.
    if turn.start_ms > runtime_stamp.wall_ms + turn.precision_ms:
        return {"ageMs": None, "reason": "turn_started_after_status"}
    age_at_sample = sample.stamp.wall_ms - turn.start_ms
    if age_at_sample < 0:
        return {"ageMs": None, "reason": "clock_delta_invalid"}
    return {
        "ageMs": age_at_sample + now - sample.stamp.seen_ms,
        "precisionMs": turn.precision_ms,
        "basis": "native_turn_start", "association": "compatible_non_atomic_samples",
    }
