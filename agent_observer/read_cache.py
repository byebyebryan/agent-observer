"""Pure local Service 2 consumer cache; no transport, collectors or alert policy."""

from __future__ import annotations

import copy
import re

from .contract import ContractError
from .observation_evidence import stale_row
from .service_contract import StreamGuard


class ReadCache:
    """Scoped replacement views and independent evidence expiry.

    BOOTTIME and its boot/time-namespace identity are supplied by the caller.
    StreamGuard admits frames; current() applies leases without altering the
    original view. A terminal/invalid stream requires reset before reuse.
    This helper cannot validate remote clocks or Mesh proof envelopes.
    """

    def __init__(self, *, host_scope, uid, boot_id, clock_domain):
        self.host_scope, self.uid = host_scope, uid
        self.boot_id, self.clock_domain = boot_id, clock_domain
        self.reset()

    def reset(self):
        self.guard = StreamGuard(expected_host=self.host_scope, expected_uid=self.uid)
        self._frame, self._usable, self._terminal = None, False, False
        self._reason, self._now = "read_warming", None
        self._revoked = set()
        self._generations = {}

    def _clock(self, now_ms):
        if type(now_ms) is not int or now_ms < 0 or self._now is not None and now_ms < self._now:
            self.invalidate("read_clock_invalid")
            raise ContractError("read_clock_invalid")
        self._now = now_ms

    def invalidate(self, reason="read_disconnected"):
        if not isinstance(reason, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason) is None:
            raise ContractError("read_reason_invalid")
        self._usable, self._terminal, self._reason = False, True, reason

    def accept(self, frame, *, now_ms):
        self._clock(now_ms)
        if self._terminal:
            raise ContractError("read_terminal")
        try:
            self.guard.accept(frame)
            if (frame["bootId"] != self.boot_id or frame["clockDomain"] != self.clock_domain
                    or frame["emittedBoottimeMs"] > now_ms):
                raise ContractError("read_clock_context")
            for source in frame["sources"]:
                key = source["provider"], source["namespace"]
                generation = source["contextGeneration"]
                if generation < self._generations.get(key, generation):
                    raise ContractError("read_context_regression")
                self._generations[key] = generation
            kind = frame["kind"]
            if kind == "error" or frame["state"] == "stopping":
                self.invalidate("read_stream_error" if kind == "error" else "read_stopping")
            elif kind == "gap" or self.guard.gapped:
                self._usable, self._reason = False, "read_gap"
            elif frame["snapshot"] is not None:
                # A heartbeat or null status supplies no replacement receipts.
                self._frame = copy.deepcopy(frame)
                self._usable, self._reason = True, "read_view"
                self._revoked.clear()
            elif self._frame is not None:
                prior = {(s["provider"], s["namespace"]): s for s in self._frame["sources"]}
                for source in frame["sources"]:
                    key = source["provider"], source["namespace"]
                    changed = source["contextGeneration"] != prior[key]["contextGeneration"]
                    for receipt in source["components"]:
                        if changed or receipt["health"] not in {"current", "partial"}:
                            self._revoked.add((*key, receipt["name"]))
        except (ValueError, TypeError, KeyError):
            self.invalidate("read_invalid_frame")
            raise
        return self.current(now_ms)

    @property
    def last_known(self):
        """Original admitted view, explicitly without current authority."""
        return copy.deepcopy(self._frame)

    def current(self, now_ms):
        self._clock(now_ms)
        if not self._usable or self._frame is None:
            return {"snapshot": None, "health": "unavailable" if self._terminal or self._frame is not None else "warming",
                    "reason": self._reason, "components": [], "nextExpiryBoottimeMs": None}
        frame = self._frame
        snapshot = copy.deepcopy(frame["snapshot"])
        leases, components, deadlines = {}, [], []
        for source in frame["sources"]:
            current = {}
            for receipt in source["components"]:
                live = (receipt["health"] in {"current", "partial"} and receipt["expiresBoottimeMs"] > now_ms
                        and (source["provider"], source["namespace"], receipt["name"]) not in self._revoked)
                current[receipt["name"]] = live
                components.append({"provider": source["provider"], "namespace": source["namespace"],
                                   "component": receipt["name"], "current": live,
                                   "health": receipt["health"] if live else "stale" if receipt["sampledBoottimeMs"] is not None else receipt["health"],
                                   "expiresBoottimeMs": receipt["expiresBoottimeMs"]})
                if live:
                    deadlines.append(receipt["expiresBoottimeMs"])
            leases[source["provider"], source["namespace"]] = current
        rows = []
        for raw in snapshot["sessions"]:
            identity = raw["identity"]
            lease = leases[identity["provider"], identity["namespace"]]
            if not raw["hasSavedHistory"] and not lease["runtime"]:
                continue
            row = stale_row(raw, runtime=not lease["runtime"],
                            # The wire does not attribute merged activity to a
                            # component. Do not guess when either lease expires.
                            metadata=not all(lease.values()), reason="read_cache_expired",
                            metadata_reason="read_cache_metadata_expired")
            if lease["history"]:
                row["workspace"] = copy.deepcopy(raw["workspace"])
            if not all(lease.values()) and row["outcome"]["source"] is not None:
                outcome = row["outcome"]
                if outcome["value"] != "unknown":
                    outcome["lastKnownValue"] = outcome["value"]
                outcome.update(value="unknown", health="stale", reason="read_cache_expired")
            rows.append(row)
        snapshot["sessions"] = rows
        for source in snapshot["sources"]:
            lease = leases[source["provider"], source["namespace"]]
            if not lease["runtime"]:
                source["coverage"]["runtime"].update(status="unavailable", reason="read_cache_expired")
                source["capabilities"].update(phase=[], blockedReasons=[], runtime=[])
            if not lease["history"]:
                source["coverage"]["saved"].update(status="unavailable", reason="read_cache_expired")
            if not all(lease.values()):
                source["sourceHealth"] = "partial" if any(lease.values()) else "stale"
        live_count = sum(item["current"] for item in components)
        snapshot["sourceHealth"] = (snapshot["sourceHealth"] if live_count == len(components)
                                    else "partial" if live_count else "stale")
        return {"snapshot": snapshot, "health": snapshot["sourceHealth"],
                "reason": "read_context_revoked" if self._revoked else "read_view" if live_count == len(components) else "read_cache_expired",
                "components": components, "nextExpiryBoottimeMs": min(deadlines, default=None)}
