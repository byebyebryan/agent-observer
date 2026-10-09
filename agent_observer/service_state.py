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
                 boot_id=None, clock_domain=None):
        super().__init__(host_scope=host_scope, configs=configs,
                         uid=os.geteuid() if uid is None else uid, clock=clock,
                         wall_clock=lambda: time.time_ns() // 1_000_000,
                         collection_id=lambda: str(uuid.uuid4()),
                         native_hostname=socket.gethostname(),
                         profiles={p: profile_for(p) for p in configs})
        self.service_id = str(uuid.uuid4())
        self.boot_id = boot_id or Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        self.clock_domain = clock_domain or os.readlink("/proc/self/ns/time")
        self.frame("status", 1)

    def frame(self, kind, sequence, *, reason="observed_view", include_snapshot=None):
        now = self.clock()
        self.expire(now)
        snapshot = self.snapshot if (include_snapshot if include_snapshot is not None else kind in {"view", "resync", "status"}) else None
        return validate_frame({
            "serviceProtocol": 2, "serviceId": self.service_id, "bootId": self.boot_id,
            "uid": self.uid, "hostScope": self.host_scope, "sequence": sequence,
            "viewRevision": self.revision, "kind": kind,
            "state": "ready" if self.snapshot is not None else "warming",
            "emittedAt": time.time_ns() // 1_000_000, "emittedBoottimeMs": now,
            "clock": "boottime", "clockDomain": self.clock_domain, "reason": reason,
            "sources": [self.source_meta(p) for p in self.configs], "snapshot": snapshot,
        })
