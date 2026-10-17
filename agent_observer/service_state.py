"""Host/service envelope around the reusable passive observation engine."""

from __future__ import annotations

import copy
import os
import socket
import time
import uuid
from pathlib import Path

from .active_feed import ActiveFeedProjector
from .observation_engine import ObservationEngine
from .provider import profile_for
from .service_contract import validate_frame


def boottime_ms():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


class ServiceState(ObservationEngine):
    def __init__(self, *, host_scope, configs, uid=None, clock=boottime_ms,
                 boot_id=None, clock_domain=None, sync_serialization="expanded"):
        from .contract import ContractError

        if type(sync_serialization) is not str or sync_serialization not in {"expanded", "compact"}:
            raise ContractError("sync_owner_serialization")
        self._sync_serialization = sync_serialization
        self.service_id = str(uuid.uuid4())
        self.active_projector = ActiveFeedProjector(service_id=self.service_id)
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
        self.frame("status", 1)

    def publish(self):
        super().publish()
        self.active_projector._accept_owned(
            self.snapshot, self.projection_support, self.projection_census,
            [self.source_meta(provider) for provider in self.configs],
            revision=self.revision, now_ms=self.clock(),
        )
        if self._sync_cache is not None:
            self._sync_cache.publish()

    def attempt(self, provider, component):
        super().attempt(provider, component)
        if self._sync_cache is not None and not self._sync_accepting:
            self._sync_cache.publish(diagnostics_only=True)

    def accept(self, provider, component, value, *, sampled_ms, ttl_ms, runtime_ttl_ms=None):
        # History acceptance can internally attempt/promote runtime. Neither
        # its intermediate receipts nor its half-reconciled roster may escape
        # as a separate sync transaction.
        self._sync_accepting = True
        try:
            accepted = super().accept(provider, component, value, sampled_ms=sampled_ms,
                                      ttl_ms=ttl_ms, runtime_ttl_ms=runtime_ttl_ms)
        finally:
            self._sync_accepting = False
        if not accepted and self._sync_cache is not None:
            self._sync_cache.publish(diagnostics_only=True)
        return accepted

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

    @property
    def active_projection(self):
        return self.active_projector.snapshot()

    def active_frame(self, kind, sequence, *, reason="observed_view", include_projection=None):
        from .active_contract import SELECTOR, SELECTOR_DIGEST
        from .active_contract import validate_frame as validate_active_frame

        now = self.clock()
        self.expire(now)
        sources = [self.source_meta("codex")] if "codex" in self.configs else []
        if not sources:
            kind, reason = "error", "active_source_unsupported"
        include = (include_projection if include_projection is not None
                   else kind in {"view", "resync", "status"})
        projection = self.active_projector.snapshot() if include and sources else None
        return validate_active_frame({
            "activeFeedProtocol": 1, "selector": copy.deepcopy(SELECTOR),
            "selectorDigest": SELECTOR_DIGEST, "serviceId": self.service_id,
            "bootId": self.boot_id, "uid": self.uid, "hostScope": self.host_scope,
            "sequence": sequence, "viewRevision": self.revision, "kind": kind,
            "state": "ready" if self.snapshot is not None else "warming",
            "emittedAt": time.time_ns() // 1_000_000, "emittedBoottimeMs": now,
            "clock": "boottime", "clockDomain": self.clock_domain,
            "reason": reason, "sources": sources, "projection": projection,
        })

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
