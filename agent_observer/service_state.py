"""Host/service envelope around the reusable passive observation engine."""

from __future__ import annotations

import os
import socket
import time
import uuid
from pathlib import Path

from .observation_engine import ObservationEngine
from .provider import profile_for
from .service_contract import validate_frame


def boottime_ms():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


class ServiceState(ObservationEngine):
    def __init__(self, *, host_scope, configs, uid=None, clock=boottime_ms,
                 boot_id=None, clock_domain=None, sync_serialization="expanded",
                 working_set_window_ms=None):
        from .contract import ContractError

        if type(sync_serialization) is not str or sync_serialization not in {"expanded", "compact"}:
            raise ContractError("sync_owner_serialization")
        self._sync_serialization = sync_serialization
        if working_set_window_ms is not None:
            from .working_set_contract import selector

            selector(working_set_window_ms)
        self._working_set_window_ms = working_set_window_ms
        self.working_set_clocks = None
        self.working_set_projector = None
        self.working_set_reserver = None
        self._working_set_blocked_sample = None
        self.service_id = str(uuid.uuid4())
        self._sync_projector = None
        # Sync is opt-in. A cold baseline can initialize its shared cache;
        # proofs/heads never trigger a roster normalization or provider read.
        self._sync_cache = None
        self._sync_accepting = False
        self.sync_reserver = None
        super().__init__(host_scope=host_scope, configs=configs,
                         uid=os.geteuid() if uid is None else uid, clock=clock,
                         wall_clock=lambda: time.time_ns() // 1_000_000,
                         collection_id=lambda: str(uuid.uuid4()),
                         native_hostname=socket.gethostname(),
                         profiles={p: profile_for(p) for p in configs},
                         support_incarnation=self.service_id)
        self.boot_id = boot_id or Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        self.clock_domain = clock_domain or os.readlink("/proc/self/ns/time")
        if working_set_window_ms is not None:
            from .working_set_clocks import WorkingSetClocks
            from .working_set_feed import WorkingSetProjector

            self.working_set_clocks = WorkingSetClocks(self.service_id, self.boot_id, self.clock_domain)
            self.working_set_projector = WorkingSetProjector(
                service_id=self.service_id, clocks=self.working_set_clocks,
                window_ms=working_set_window_ms,
            )
        self.frame("status", 1)

    def publish(self):
        super().publish()
        if self._sync_projector is not None:
            self._update_sync_projection()
        if self._sync_cache is not None:
            self._sync_cache.publish()
        if self.working_set_projector is not None and not self._sync_accepting:
            self._refresh_working_set(self.clock())

    def attempt(self, provider, component):
        super().attempt(provider, component)
        if self._sync_cache is not None and not self._sync_accepting:
            self._sync_cache.publish(diagnostics_only=True)

    def accept(self, provider, component, value, *, sampled_ms, ttl_ms, runtime_ttl_ms=None,
               accepted_boottime_ms=None):
        # History acceptance can internally attempt/promote runtime. Neither
        # its intermediate receipts nor its half-reconciled roster may escape
        # as a separate sync transaction.
        self._sync_accepting = True
        try:
            accepted = super().accept(provider, component, value, sampled_ms=sampled_ms,
                                      ttl_ms=ttl_ms, runtime_ttl_ms=runtime_ttl_ms)
        finally:
            self._sync_accepting = False
        if accepted and self.working_set_clocks is not None and accepted_boottime_ms is not None:
            self._capture_working_clock(provider, component, value,
                                        sampled_ms=sampled_ms, accepted_ms=accepted_boottime_ms)
        if accepted and self.working_set_projector is not None:
            self._refresh_working_set(self.clock())
        if not accepted and self._sync_cache is not None:
            self._sync_cache.publish(diagnostics_only=True)
        return accepted

    def _refresh_working_set(self, now):
        if self.snapshot is None or "codex" not in self.configs:
            return
        samples = {name: receipt.data["collectionId"] if receipt.data is not None else None
                   for name, receipt in self.receipts["codex"].items()}
        source = self.source_meta("codex")
        sample_key = (
            source["provider"], source["namespace"], source["contextGeneration"],
            tuple(
                (name, receipt.accepted, samples[name])
                for name, receipt in sorted(self.receipts["codex"].items())
            ),
        )
        projector = self.working_set_projector
        if projector._capacity_blocked:
            # Do not retry the same accepted generation from unrelated publish
            # or expiry work. Recovery must be triggered by a new accepted
            # sample and a successful reservation.
            if sample_key == self._working_set_blocked_sample or self.working_set_reserver is None:
                return
        if self.working_set_reserver is not None:
            from .working_set_contract import MAX_FRAME_BYTES, MAX_LEDGER_BYTES

            if not self.working_set_reserver(MAX_FRAME_BYTES + 2 * MAX_LEDGER_BYTES):
                projector.refuse_capacity(source, observation_revision=self.revision)
                self._working_set_blocked_sample = sample_key
                return
        projector._accept_owned(
            self.snapshot, self.projection_support, self.projection_census,
            [source], observation_revision=self.revision,
            now_ms=now, sample_ids=samples,
        )
        if not projector._capacity_blocked:
            self._working_set_blocked_sample = None

    def expire(self, now=None):
        now = self.clock() if now is None else now
        changed = super().expire(now)
        if (self.working_set_projector is not None and self.snapshot is not None
                and self.working_set_projector.due(now)):
            self._refresh_working_set(now)
        return changed

    @property
    def working_set_revision(self):
        return 0 if self.working_set_projector is None else self.working_set_projector.revision

    @property
    def working_set_window_ms(self):
        """Startup-fixed policy; a different policy requires a new owner."""
        return self._working_set_window_ms

    def working_set_retained_buffers(self):
        """Actual encoded owner buffers for opt-in shared delivery accounting."""
        if self.working_set_projector is None:
            return ()
        return tuple(value for value in (
            self.working_set_projector._encoded,
        ) if value is not None)

    def working_set_frame(self, kind, sequence, *, reason="observed_view", include_projection=None):
        from .contract import ContractError
        from .working_set_contract import selector, selector_digest
        from .working_set_contract import validate_frame as validate_working_set_frame

        if self.working_set_projector is None:
            raise ContractError("working_set_disabled")
        now = self.clock()
        self.expire(now)
        sources = [self.source_meta("codex")] if "codex" in self.configs else []
        if not sources:
            kind, reason = "error", "working_set_source_unsupported"
        include = (include_projection if include_projection is not None
                   else kind in {"view", "resync", "status"})
        projection = self.working_set_projector.snapshot() if include and sources else None
        if self.working_set_projector._capacity_blocked:
            kind, reason, projection = "error", "projection_encoding_capacity", None
        policy = selector(self.working_set_window_ms)
        return validate_working_set_frame({
            "workingSetProtocol": 1, "selector": policy, "selectorDigest": selector_digest(policy),
            "serviceId": self.service_id, "bootId": self.boot_id, "uid": self.uid,
            "hostScope": self.host_scope, "sequence": sequence,
            "viewRevision": self.working_set_revision, "observationRevision": self.revision,
            "clockCeiling": self.working_set_clocks.ceiling,
            "clockGeneration": self.working_set_clocks.generation, "kind": kind,
            "state": "ready" if self.snapshot is not None else "warming",
            "emittedAt": time.time_ns() // 1_000_000, "emittedBoottimeMs": now,
            "clock": "boottime", "clockDomain": self.clock_domain,
            "reason": reason, "sources": sources, "projection": projection,
        })

    def _capture_working_clock(self, provider, origin, value, *, sampled_ms, accepted_ms):
        """Install only an actually accepted, exact original worker sample.

        Called synchronously before control returns to local delivery. History
        can mirror the same original sample into runtime; each binding still
        names its own accepted counter. Invalid/unavailable clock metadata
        supplies no recency authority and never marks a newer receipt failed.
        """
        from .working_set_policy import SampleClock

        if provider != "codex" or type(accepted_ms) is not int or accepted_ms > self.clock():
            return
        source = self.source_meta(provider)
        clock = SampleClock(
            sample_id=value["collectionId"], origin_component=origin,
            service_id=self.service_id, provider=provider, namespace=source["namespace"],
            context_generation=source["contextGeneration"], boot_id=self.boot_id,
            clock_domain=self.clock_domain, lower_boottime_ms=sampled_ms,
            wall_ms=value["collectedAt"], upper_boottime_ms=accepted_ms,
        )
        for component, receipt in self.receipts[provider].items():
            if (receipt.data is None or receipt.data["collectionId"] != clock.sample_id
                    or receipt.sampledBoottimeMs != sampled_ms):
                continue
            try:
                self.working_set_clocks.accept(clock, component=component, accepted=receipt.accepted)
            except ValueError:
                # The old binding cannot join this receipt's accepted counter,
                # so classification is unknown; K is never reset as recovery.
                continue

    def _sync_owner(self):
        if self._sync_cache is None:
            from .sync_state import OwnerSyncCache

            self._sync_cache = OwnerSyncCache(self, backend="encoded",
                                              serialization=self._sync_serialization)
        return self._sync_cache

    def sync_baseline(self, view):
        return self._sync_owner().baseline(view)

    def sync_head(self, view, challenge):
        return self._sync_owner().head(view, challenge)

    def sync_changes(self, view, base_tag, target_tag, *, max_transactions=4,
                     max_bytes=8 * 1024 * 1024):
        return self._sync_owner().changes(view, base_tag, target_tag,
                                          max_transactions=max_transactions,
                                          max_bytes=max_bytes)

    def sync_current_tag(self, view):
        return None if self._sync_cache is None else self._sync_cache.current_tag(view)

    def sync_cursor(self, view):
        return None if self._sync_cache is None else self._sync_cache.cursor(view)

    def sync_tag_for_cursor(self, view, cursor):
        return None if self._sync_cache is None else self._sync_cache.tag_for_cursor(view, cursor)

    def sync_control(self, view, status, reason="sync_control"):
        return self._sync_owner().control(view, status, reason)

    def sync_retained_buffers(self):
        return () if self._sync_cache is None else self._sync_cache.retained_buffers()

    def sync_owned_encoded_bytes(self):
        return 0 if self._sync_cache is None else self._sync_cache.owned_encoded_bytes()

    def sync_pin_buffers(self, parts):
        return self._sync_owner().pin_buffers(parts)

    def sync_discard_buffers(self, parts):
        if self._sync_cache is not None:
            self._sync_cache.discard_query_buffers(parts)

    def sync_retained_bytes(self):
        return sum(map(len, self.sync_retained_buffers()))



    def _update_sync_projection(self):
        if self.snapshot is None:
            return
        self._sync_projector._accept_owned(
            self.snapshot, self.projection_support, self.projection_census,
            [self.source_meta(provider) for provider in self.configs],
            revision=self.revision, now_ms=self.clock(),
        )

    @property
    def sync_active_projection(self):
        """Private opt-in sync state; ordinary publication allocates no cache."""
        if self._sync_projector is None:
            from .sync_projection import _SyncProjection

            self._sync_projector = _SyncProjection(service_id=self.service_id)
            self._update_sync_projection()
        return self._sync_projector.snapshot()

    def frame(self, kind, sequence, *, reason="observed_view", include_snapshot=None):
        now = self.clock()
        self.expire(now)
        snapshot = self.snapshot if (include_snapshot if include_snapshot is not None else kind in {"view", "resync", "status"}) else None
        return validate_frame({
            "serviceProtocol": 4, "serviceId": self.service_id, "bootId": self.boot_id,
            "uid": self.uid, "hostScope": self.host_scope, "sequence": sequence,
            "viewRevision": self.revision, "kind": kind,
            "state": "ready" if self.snapshot is not None else "warming",
            "emittedAt": time.time_ns() // 1_000_000, "emittedBoottimeMs": now,
            "clock": "boottime", "clockDomain": self.clock_domain, "reason": reason,
            "sources": [self.source_meta(p) for p in self.configs], "snapshot": snapshot,
        })
