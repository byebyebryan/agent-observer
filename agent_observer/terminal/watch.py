"""Persistent cached working-set consumers; no provider or framework ownership.

Every attempt owns a public reader/guard pair. Receiving-clock deadlines wake
the facade, not a second implementation of membership or field expiry rules.
The latest slots and a single dirty event replace any presentation event queue.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field

from .config import MAX_IDENTITIES_TOTAL, MAX_PAYLOAD_MIB_TOTAL, MAX_SOURCES, TerminalSource
from .model import build_report, generated_at_now
from .sources import (
    _check_source_binding,
    _delivery_error,
    _dependencies,
    _failure_code,
    _failure_code_from_frame,
    _FinalRequested,
    _frame_kind,
    _frame_size_and_identity_count,
    _frame_snapshot,
    _new_state,
    _or_final,
    _SourceFailure,
)


def next_deadline(read, now_ms: int) -> int | None:
    """Earliest *public receiving* deadline, including absence and field proofs."""
    values = []
    for lease in read.member_leases:
        values.extend(
            lease.get(key)
            for key in ("activeExpiresAtMs", "recentExpiresAtMs", "membershipExpiresAtMs")
        )
        values.extend(lease.get("fieldExpiresAtMs", {}).values())
    values.extend(scope.get("coverage", {}).get("expiresAtMs") for scope in read.scopes)
    context = read.context or {}
    values.extend(
        receipt.get("expiresAtMs")
        for host in context.get("hosts", ())
        for receipt in host.get("receipts", ())
    )
    return min((v for v in values if type(v) is int and v > now_ms), default=None)


def blocking_failure(code: str) -> bool:
    """Block explicit policy/contract faults, never infer one from channel_failed."""
    return code in {"scope_changed", "catalog_monitor_required", "identity_conflict"} or any(
        part in code
        for part in (
            "binding",
            "namespace",
            "window",
            "unsupported",
            "capacity",
            "invalid",
            "shape",
            "sequence",
            "regression",
            "continuity",
            "policy_failure",
        )
    )


async def _join_owned(task):
    """Wait without forwarding repeated cancellation into owned cleanup."""
    interrupted = False
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            interrupted = True
    return task.result(), interrupted


@dataclass
class _Slot:
    source: TerminalSource
    state: dict
    epoch: int = 0
    guard: object | None = None
    clock: dict = field(default_factory=dict)
    deadline: int | None = None
    retry_at: int | None = None
    stage: str = "connecting"
    attempts: int = 0
    failure_step: int = 0
    stable_since: int | None = None
    last_manual: int | None = None
    restart_reason: str | None = None
    cleanup_failed: bool = False
    wake: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass(frozen=True)
class WatchProjection:
    """Internal handoff fence; not an extension to finite terminal JSON v1."""

    owner: object = field(repr=False)
    revision: int
    epochs: tuple[tuple[str, int], ...]
    report: dict = field(repr=False)
    next_deadline_boottime_ms: int | None = None
    priority_revision: int = 0


class PersistentSources:
    """One outer-owned supervisor and one attempt/source, on one asyncio loop.

    ``report`` and ``refresh_due`` are synchronous and must run on this same
    loop. Views never own streams. Call ``request_close`` once on quit, then
    await ``close`` outside the UI lifetime; timeout is not successful cleanup.
    """

    def __init__(
        self,
        sources: tuple[TerminalSource, ...],
        *,
        connect_timeout: float = 15.0,
        dependencies: dict | None = None,
        setup_interval: float = 1.0,
        retry_steps: tuple[float, ...] = (1, 2, 4, 8, 16, 30),
        jitter=None,
    ):
        if (
            not 1 <= len(sources) <= MAX_SOURCES
            or len({s.id for s in sources}) != len(sources)
            or sum(s.max_identities for s in sources) > MAX_IDENTITIES_TOTAL
            or sum(s.max_payload_mib for s in sources) > MAX_PAYLOAD_MIB_TOTAL
            or not 1 <= connect_timeout <= 60
            or setup_interval < 0
            or not retry_steps
            or any(v <= 0 or v > 30 for v in retry_steps)
        ):
            raise ValueError("dashboard_source_configuration")
        self.dependencies = _dependencies() if dependencies is None else dependencies
        self.clock_binding = self.dependencies["clock_domain"]()
        self.connect_timeout = connect_timeout
        self.setup_interval = setup_interval
        self.retry_steps = retry_steps
        self.jitter = jitter or (lambda: random.uniform(0.8, 1.0))
        self.slots = [_Slot(s, _new_state(s, self.clock_binding)) for s in sources]
        self.changed = asyncio.Event()
        self._stop = asyncio.Event()
        self._setup_slots = asyncio.Semaphore(4)
        self._start_lock = asyncio.Lock()
        self._next_start = 0.0
        self._tasks: list[asyncio.Task] = []
        self._closing = False
        self._closed = False
        self._last_now = self.now()
        self.revision = 0
        self._priority_revision = 0
        self.cleanup_error: str | None = None
        self.metrics = {
            "frames": 0,
            "guardReads": 0,
            "guardCpuSeconds": 0.0,
            "reports": 0,
            "reportCpuSeconds": 0.0,
            "peakFrameBytes": 0,
        }
        self._report_key = None
        self._report = None
        self._projection_owner = object()
        self._last_manual: int | None = None

    def now(self) -> int:
        return self.dependencies["boottime_ms"]()

    @property
    def states(self) -> list[dict]:
        return [slot.state for slot in self.slots]

    def _dirty(self):
        self.revision += 1
        self.changed.set()
        self._report = None

    async def start(self):
        if self._tasks or self._closing:
            raise RuntimeError("dashboard_watch_already_started")
        self._tasks = [asyncio.create_task(self._worker(slot)) for slot in self.slots]
        self._tasks.append(asyncio.create_task(self._clock_worker()))
        self._dirty()

    def _revoke(self, slot: _Slot, code: str, *, blocked=False):
        slot.epoch += 1
        slot.deadline = None
        slot.stable_since = None
        slot.stage = "blocked" if blocked else "revoked"
        slot.state.update(
            lifecycle="blocked" if blocked else "failed",
            reason=code,
            baseline=False,
            read=None,
            capture_boottime_ms=self.now(),
            epoch=slot.epoch,
        )
        if slot.guard is not None:
            try:
                slot.guard.disconnect()
            except Exception as error:
                self.cleanup_error = _failure_code(error)
                slot.cleanup_failed = True
                slot.stage = "blocked"
                slot.state.update(
                    lifecycle="blocked",
                    reason="source_cleanup_failed",
                    cleanup_error=_failure_code(error),
                )
        self._dirty()

    def _evaluate(self, slot: _Slot, now: int):
        if slot.deadline is not None and slot.deadline <= now:
            # Latch a crossed deadline even if the UI has not yet received the
            # frame that introduced it, or read() replaces it with a future one.
            self._priority_revision += 1
        started = time.process_time()
        try:
            read = slot.guard.read(now, slot.clock)
        finally:
            self.metrics["guardReads"] += 1
            self.metrics["guardCpuSeconds"] += time.process_time() - started
        observed = _check_source_binding(read, slot.state["config"])
        if observed is not None:
            slot.state["observed_namespace"] = observed
        context = read.context
        delivery_error = _delivery_error(context, slot.source.host)
        if delivery_error:
            slot.state["delivery_error"] = delivery_error
        hosts = [] if context is None else context.get("hosts", ())
        if any(
            h.get("delivery", {}).get("status") in {"unavailable", "disconnected"} for h in hosts
        ):
            code = delivery_error or "mesh_delivery_disconnected"
            raise _SourceFailure(code, blocked=blocking_failure(code))
        settled = bool(hosts) and all(
            h.get("delivery", {}).get("status") != "connecting" for h in hosts
        )
        slot.state.update(
            read=read,
            capture_boottime_ms=now,
            baseline=bool(context and settled),
            lifecycle="observing" if context and settled else "warming",
            reason=None,
        )
        slot.stage = "observing" if context and settled else "warming"
        slot.deadline = next_deadline(read, now)
        if slot.state["baseline"]:
            slot.stable_since = slot.stable_since if slot.stable_since is not None else now
            if now - slot.stable_since >= 60_000:
                slot.failure_step = 0
        self._dirty()

    def refresh_due(self):
        """Cheap before-paint/quiet check; evaluate only a changed clock or due lease."""
        if self._closing:
            return
        now = self.now()
        binding = self.dependencies["clock_domain"]()
        changed_clock = binding != self.clock_binding
        regressed = now < self._last_now
        self._last_now = now
        if changed_clock or regressed:
            self.clock_binding = binding
            self._last_manual = None
            for slot in self.slots:
                slot.last_manual = None
                if slot.guard is not None or (
                    slot.attempts and slot.stage in {"connecting", "warming"}
                ):
                    code = (
                        "receiving_clock_changed" if changed_clock else "receiving_clock_regression"
                    )
                    slot.restart_reason = code
                    self._revoke(slot, code, blocked=regressed)
                    slot.wake.set()
            return
        for slot in self.slots:
            if slot.stage == "retry-wait" and slot.retry_at is not None and slot.retry_at <= now:
                slot.wake.set()
            if slot.guard is None or slot.deadline is None or slot.deadline > now:
                continue
            try:
                self._evaluate(slot, now)
            except Exception as error:
                code = _failure_code(error)
                slot.restart_reason = code
                self._revoke(
                    slot,
                    code,
                    blocked=isinstance(error, _SourceFailure)
                    and error.blocked
                    or not isinstance(error, _SourceFailure),
                )
                slot.wake.set()

    async def _clock_worker(self):
        try:
            while not self._stop.is_set():
                self.refresh_due()
                now = self.now()
                delay = min(
                    (
                        max(0.001, (slot.deadline - now) / 1000)
                        for slot in self.slots
                        if slot.deadline is not None
                    ),
                    default=0.1,
                )
                await asyncio.sleep(min(0.1, delay))
        except asyncio.CancelledError:
            raise
        except Exception:
            self.cleanup_error = "receiving_clock_unavailable"
            self.request_close()

    async def _start_slot(self):
        await self._setup_slots.acquire()
        try:
            async with self._start_lock:
                loop = asyncio.get_running_loop()
                await asyncio.sleep(max(0, self._next_start - loop.time()))
                self._next_start = loop.time() + self.setup_interval
        except BaseException:
            self._setup_slots.release()
            raise

    async def _worker(self, slot: _Slot):
        while not self._stop.is_set():
            acquired = False
            pending = wake = stream = reader = frame = None
            code = None
            blocked = cancelled = False
            try:
                await self._start_slot()
                acquired = True
                slot.wake.clear()
                slot.restart_reason = None
                slot.retry_at = None
                slot.epoch += 1
                epoch = slot.epoch
                slot.attempts += 1
                slot.cleanup_failed = False
                slot.stage = "connecting"
                slot.clock = dict(self.clock_binding)
                slot.state.update(
                    lifecycle="warming",
                    baseline=False,
                    reason=None,
                    delivery_error=None,
                    read=None,
                    capture_boottime_ms=self.now(),
                    epoch=slot.epoch,
                )
                slot.state["clock"] = {
                    "kind": "CLOCK_BOOTTIME",
                    **slot.clock,
                    "clockDomain": "time:[" + slot.clock["timeNamespace"].split(":", 1)[-1] + "]",
                }
                self._dirty()
                loop = asyncio.get_running_loop()
                deadline = loop.time() + self.connect_timeout
                profile = self.dependencies["WorkingSetAgentProfile"](slot.source.window_ms)
                reader = await _or_final(
                    asyncio.wait_for(
                        self.dependencies["configured_reader"](
                            "agent",
                            source=slot.source.mesh_source,
                            socket=slot.source.socket,
                            scope=slot.source.scope,
                            hosts=[slot.source.host] if slot.source.scope == "hosts" else [],
                            local_host=slot.source.host if slot.source.scope == "local" else None,
                            report_routes=False,
                            profile=profile,
                        ),
                        max(0, deadline - loop.time()),
                    ),
                    slot.wake,
                )
                if slot.epoch != epoch or slot.clock != self.clock_binding:
                    raise _SourceFailure(
                        slot.restart_reason or "receiving_clock_changed",
                        blocked=slot.state["lifecycle"] == "blocked",
                    )
                request_id = uuid.uuid4().hex
                slot.guard = self.dependencies["PreparedWorkingSetAgentWatch"](
                    request_id,
                    host_ids=[slot.source.host] if slot.source.scope == "hosts" else None,
                    window_ms=slot.source.window_ms,
                    profile=profile,
                )
                stream = reader.execute_admitted(
                    {
                        "meshProtocol": 1,
                        "requestId": request_id,
                        "operation": "watch",
                        "profile": profile.descriptor.profile_id,
                        "access": "cached",
                        "selection": {
                            "mode": slot.source.scope,
                            "hostIds": [slot.source.host] if slot.source.scope == "hosts" else [],
                        },
                        "extensions": {},
                    }
                )
                slot.stage = "warming"
                pending = asyncio.create_task(anext(stream))
                wake = asyncio.create_task(slot.wake.wait())
                while not self._stop.is_set():
                    timeout = max(0, deadline - loop.time()) if acquired else None
                    done, _ = await asyncio.wait(
                        {pending, wake}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                    )
                    if wake in done or slot.epoch != epoch:
                        raise _SourceFailure(
                            slot.restart_reason or "source_restarted",
                            blocked=slot.state["lifecycle"] == "blocked",
                        )
                    if not done:
                        raise _SourceFailure("baseline_timeout")
                    frame = pending.result()
                    pending = None
                    if type(frame) is dict and type(frame.get("error")) is dict:
                        reason = _failure_code_from_frame(frame)
                        raise _SourceFailure(reason, blocked=blocking_failure(reason))
                    admitted = self.dependencies["AdmittedResponse"]
                    if not isinstance(frame, admitted) and type(frame) is not dict:
                        raise _SourceFailure("frame_not_admitted", blocked=True)
                    context = (
                        frame.context() if isinstance(frame, admitted) else frame.get("mesh", {})
                    )
                    delivery = _delivery_error(context, slot.source.host)
                    if delivery:
                        slot.state["delivery_error"] = delivery
                    kind = _frame_kind(frame, admitted)
                    if kind in {"gap", "resync"}:
                        reason = delivery or ("mesh_gap" if kind == "gap" else "mesh_resync")
                        raise _SourceFailure(reason, blocked=blocking_failure(reason))
                    if kind != "heartbeat":
                        size, count = _frame_size_and_identity_count(
                            _frame_snapshot(frame, admitted)
                        )
                        self.metrics["peakFrameBytes"] = max(self.metrics["peakFrameBytes"], size)
                        if count > slot.source.max_identities:
                            raise _SourceFailure("source_identity_capacity", blocked=True)
                        if size > slot.source.max_payload_mib * 1024 * 1024:
                            raise _SourceFailure("source_payload_capacity", blocked=True)
                    try:
                        slot.guard.accept(frame)
                    except Exception as error:
                        raise _SourceFailure(_failure_code(error), blocked=True) from None
                    self.metrics["frames"] += 1
                    slot.state["last_frame_boottime_ms"] = self.now()
                    if kind != "heartbeat":
                        self._evaluate(slot, self.now())
                    if slot.state["baseline"] and acquired:
                        self._setup_slots.release()
                        acquired = False
                    frame = None
                    pending = asyncio.create_task(anext(stream))
            except asyncio.CancelledError:
                cancelled = True
            except StopAsyncIteration:
                code = "mesh_stream_ended"
            except TimeoutError:
                code = "baseline_timeout"
            except _FinalRequested:
                code = slot.restart_reason or "source_restarted"
                blocked = slot.state["lifecycle"] == "blocked"
            except _SourceFailure as error:
                code, blocked = error.code, error.blocked
            except Exception as error:
                code = _failure_code(error)
                blocked = blocking_failure(code)
            finally:
                if (code is not None and slot.state.get("read") is not None) or cancelled:
                    self._revoke(slot, code or "closed", blocked=blocked)
                elif code is not None and slot.stage not in {"revoked", "blocked"}:
                    self._revoke(slot, code, blocked=blocked)
                slot.stage = "retiring"
                self._dirty()
                if acquired:
                    self._setup_slots.release()
                for task in (pending, wake):
                    if task is not None and not task.done():
                        task.cancel()
                if pending is not None or wake is not None:
                    joined = asyncio.gather(
                        *(t for t in (pending, wake) if t is not None), return_exceptions=True
                    )
                    await _join_owned(joined)
                if slot.guard is not None:
                    try:
                        slot.guard.disconnect()
                    except Exception as error:
                        self.cleanup_error = _failure_code(error)
                        slot.cleanup_failed = True
                        blocked = True
                        slot.state.update(
                            lifecycle="blocked",
                            reason="source_cleanup_failed",
                            cleanup_error=_failure_code(error),
                        )
                    slot.guard = None
                if stream is not None:
                    try:
                        closing = asyncio.create_task(stream.aclose())
                        await _join_owned(closing)
                    except Exception as error:
                        self.cleanup_error = _failure_code(error)
                        blocked = True
                        self._revoke(slot, "source_cleanup_failed", blocked=True)
                pending = wake = stream = reader = frame = None
                blocked = blocked or slot.cleanup_failed
            if cancelled or self._stop.is_set():
                slot.stage = "closed"
                return
            slot.stage = "blocked" if blocked else "retry-wait"
            slot.wake.clear()
            self._dirty()
            if blocked:
                await slot.wake.wait()
                slot.failure_step = 0
            else:
                step = self.retry_steps[min(slot.failure_step, len(self.retry_steps) - 1)]
                delay = step * min(1.0, max(0.8, self.jitter()))
                slot.failure_step = min(slot.failure_step + 1, len(self.retry_steps) - 1)
                slot.retry_at = self.now() + int(delay * 1000)
                self._dirty()
                try:
                    await asyncio.wait_for(slot.wake.wait(), delay)
                except TimeoutError:
                    pass

    def retry(self, source_id: str) -> bool:
        slot = next((s for s in self.slots if s.source.id == source_id), None)
        now = self.now()
        if (
            self._closing
            or slot is None
            or slot.stage not in {"blocked", "retry-wait"}
            or self._last_manual is not None
            and now - self._last_manual < 1000
            or slot.last_manual is not None
            and now - slot.last_manual < 1000
        ):
            return False
        slot.last_manual = now
        self._last_manual = now
        slot.wake.set()
        return True

    def status(self) -> list[dict]:
        return [
            {
                "id": s.source.id,
                "stage": s.stage,
                "epoch": s.epoch,
                "attempts": s.attempts,
                "retryAtBoottimeMs": s.retry_at,
                "reason": s.state.get("reason"),
                "cleanupError": s.state.get("cleanup_error"),
            }
            for s in self.slots
        ]

    def report(self, filters: dict, *, mode="list", target=None) -> dict:
        self.refresh_due()
        key = (self.revision, mode, repr(target), repr(sorted(filters.items())))
        if self._report is None or key != self._report_key:
            now = self.now()
            clock = {
                "kind": "CLOCK_BOOTTIME",
                **self.clock_binding,
                "clockDomain": "time:["
                + self.clock_binding["timeNamespace"].split(":", 1)[-1]
                + "]",
                "nowBoottimeMs": now,
            }
            started = time.process_time()
            report = build_report(
                self.states,
                now_boottime_ms=now,
                generated_at=generated_at_now(),
                clock=clock,
                mode=mode,
                filters=filters,
                target=target,
            )
            for source in report["sources"]:
                if source["reason"] == "identity_conflict":
                    slot = next(s for s in self.slots if s.source.id == source["id"])
                    slot.restart_reason = "identity_conflict"
                    self._revoke(slot, "identity_conflict", blocked=True)
                    slot.wake.set()
            self._report = report
            self.metrics["reports"] += 1
            self.metrics["reportCpuSeconds"] += time.process_time() - started
            self._report_key = key
        return self._report

    def projection(self, filters: dict, *, mode="list", target=None) -> WatchProjection:
        report = self.report(filters, mode=mode, target=target)
        deadlines = [slot.deadline for slot in self.slots if slot.deadline is not None]
        return WatchProjection(
            self._projection_owner,
            self.revision,
            tuple((s.source.id, s.epoch) for s in self.slots),
            report,
            min(deadlines) if deadlines else None,
            self._priority_revision,
        )

    def requires_priority_refresh(self, projection: WatchProjection | None) -> bool:
        """Revoked generations and crossed leases bypass cosmetic UI throttling."""
        self.refresh_due()
        if (
            projection is None
            or not isinstance(projection, WatchProjection)
            or projection.owner is not self._projection_owner
        ):
            return True
        return (
            projection.epochs != tuple((slot.source.id, slot.epoch) for slot in self.slots)
            or projection.priority_revision != self._priority_revision
            or projection.next_deadline_boottime_ms is not None
            and projection.next_deadline_boottime_ms <= self.now()
        )

    def is_current(self, projection: WatchProjection) -> bool:
        self.refresh_due()
        return (
            not self._closing
            and isinstance(projection, WatchProjection)
            and projection.owner is self._projection_owner
            and projection.revision == self.revision
            and projection.epochs == tuple((s.source.id, s.epoch) for s in self.slots)
        )

    def request_close(self):
        if self._closing:
            return
        self._closing = True
        self._stop.set()
        for slot in self.slots:
            self._revoke(slot, "closed")
        for task in self._tasks:
            if not task.done():
                task.cancel()

    async def close(self):
        if self._closed:
            return
        self.request_close()
        started = asyncio.get_running_loop().time()
        joined = asyncio.gather(*self._tasks, return_exceptions=True)
        results, interrupted = await _join_owned(joined)
        if asyncio.get_running_loop().time() - started > 5:
            self.cleanup_error = self.cleanup_error or "cleanup_timeout"
        if any(
            isinstance(r, BaseException) and not isinstance(r, asyncio.CancelledError)
            for r in results
        ):
            self.cleanup_error = self.cleanup_error or "source_worker_failed"
        self._tasks.clear()
        for slot in self.slots:
            slot.stage = "closed"
        self._closed = True
        if interrupted:
            raise asyncio.CancelledError
