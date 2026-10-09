"""Reusable passive observation decisions; all host clocks/identity are inputs."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .observation_evidence import retain_missing, stale_row
from .contract import (
    MAX_SESSIONS, MAX_SNAPSHOT_BYTES, ContractError, canonical, identity_key,
    store_namespace, validate_snapshot,
)


@dataclass
class Receipt:
    name: str
    attempts: int = 0
    accepted: int = 0
    sampledBoottimeMs: int | None = None
    expiresBoottimeMs: int | None = None
    health: str = "warming"
    lastResult: str = "not_observed"
    inFlight: bool = False
    data: dict | None = field(default=None, repr=False)

    def public(self):
        return {key: value for key, value in vars(self).items() if key != "data"}

    def current(self):
        return self.health in {"current", "partial"}


class ObservationEngine:
    def __init__(self, *, host_scope, configs, uid, clock, wall_clock,
                 collection_id, native_hostname, profiles):
        self.host_scope, self.uid = host_scope, uid
        self.clock, self.wall_clock = clock, wall_clock
        self.collection_id, self.native_hostname = collection_id, native_hostname
        self.profiles = dict(profiles)
        if set(self.profiles) != set(configs):
            raise ContractError("observation_profile_scope")
        self.configs = copy.deepcopy(configs)
        self.receipts = {provider: {name: Receipt(name) for name in ("runtime", "history")} for provider in configs}
        self.generations = {provider: 0 for provider in configs}
        self.contexts = {provider: None for provider in configs}
        self.context_samples = {provider: -1 for provider in configs}
        self.snapshot = None
        self.revision = 0

    def source_meta(self, provider):
        home, selector = self.configs[provider]
        return {
            "provider": provider, "namespace": store_namespace(provider, home, selector, self.uid),
            "configHome": home, "configHomeKind": selector,
            "contextGeneration": self.generations[provider],
            "components": [r.public() for r in self.receipts[provider].values()],
        }

    def attempt(self, provider, component):
        receipt = self.receipts[provider][component]
        receipt.attempts += 1
        receipt.inFlight = True

    def fail(self, provider, component, reason="collection_failed"):
        receipt = self.receipts[provider][component]
        receipt.inFlight = False
        receipt.lastResult = reason
        receipt.health = "stale" if receipt.data else "unavailable"
        self.publish()

    def accept(self, provider, component, value, *, sampled_ms, ttl_ms, runtime_ttl_ms=None):
        validate_snapshot(value)
        if value["host"]["authority"] != self.host_scope or value["host"]["uid"] != self.uid or len(value["sources"]) != 1:
            raise ContractError("service_worker_scope")
        source = value["sources"][0]
        meta = self.source_meta(provider)
        if any(source[key] != meta[key] for key in ("provider", "namespace", "configHome", "configHomeKind")):
            raise ContractError("service_worker_store")
        if sampled_ms > self.clock() or ttl_ms < 1:
            raise ContractError("service_worker_clock")
        receipt = self.receipts[provider][component]
        if sampled_ms < self.context_samples[provider] or (receipt.sampledBoottimeMs is not None and sampled_ms < receipt.sampledBoottimeMs):
            receipt.inFlight = False
            return False
        context = canonical(source["runtime"]) if source["runtime"] else None
        if context is not None and context != self.contexts[provider]:
            self.contexts[provider] = context
            self.context_samples[provider] = sampled_ms
            self.generations[provider] += 1
            for prior in self.receipts[provider].values():
                if prior.data:
                    prior.health = "stale"
        receipt = self.receipts[provider][component]
        previous = receipt.data
        receipt.data = copy.deepcopy(value)
        receipt.inFlight = False
        receipt.lastResult = "accepted"
        receipt.accepted += 1
        receipt.sampledBoottimeMs = sampled_ms
        receipt.expiresBoottimeMs = sampled_ms + ttl_ms
        dimension = "runtime" if component == "runtime" else "saved"
        coverage = source["coverage"][dimension]["status"]
        receipt.health = "current" if coverage == "complete" else "partial" if coverage == "partial" else "unavailable"
        if receipt.expiresBoottimeMs <= self.clock():
            receipt.health = "stale"
        # Retain evidence belonging to this component across an incomplete read.
        # Only positive saved-history identity is retained by the metadata
        # component. Runtime retention uses its own daemon census coverage.
        if previous and coverage != "complete":
            retain_missing(previous, receipt.data, component=component)
        if component == "history" and source["coverage"]["runtime"]["status"] in {"complete", "partial"}:
            runtime = self.receipts[provider]["runtime"]
            if runtime.sampledBoottimeMs is None or sampled_ms >= runtime.sampledBoottimeMs:
                self.attempt(provider, "runtime")
                self.accept(provider, "runtime", value, sampled_ms=sampled_ms,
                            ttl_ms=runtime_ttl_ms if runtime_ttl_ms is not None else min(ttl_ms, 60000))
        self.publish()
        return True

    def expire(self, now=None):
        now = self.clock() if now is None else now
        changed = False
        for receipts in self.receipts.values():
            for receipt in receipts.values():
                if receipt.current() and receipt.expiresBoottimeMs <= now:
                    receipt.health = "stale"
                    receipt.lastResult = "lease_expired"
                    changed = True
        if changed:
            self.publish()
        return changed

    def _placeholder(self, provider):
        meta = self.source_meta(provider)
        return {
            **{k: meta[k] for k in ("provider", "namespace", "configHome", "configHomeKind")},
            "runtimeNamespace": None, "runtime": None, "discovery": None, "sourceHealth": "unavailable",
            "coverage": {"saved": {"status": "unavailable", "reason": "not_observed"},
                         "runtime": {"status": "unavailable", "reason": "not_observed", "scope": self.profiles[provider].runtime_scope}},
            "capabilities": {"phase": [], "blockedReasons": [], "runtime": [], "activity": False},
            "errors": [], "limitations": ["source_not_observed"],
        }

    def publish(self):
        rows, sources = [], []
        for provider, receipts in self.receipts.items():
            runtime, history = receipts["runtime"], receipts["history"]
            base = runtime.data or history.data
            source = copy.deepcopy(base["sources"][0]) if base else self._placeholder(provider)
            if not runtime.current():
                source["coverage"]["runtime"].update(status="unavailable", reason="service_source_expired")
                source["capabilities"].update(phase=[], blockedReasons=[], runtime=[])
            if history.data and history.current():
                source["coverage"]["saved"] = copy.deepcopy(history.data["sources"][0]["coverage"]["saved"])
                if source["discovery"] is not None:
                    source["discovery"]["historyClocks"] = bool((history.data["sources"][0]["discovery"] or {}).get("historyClocks"))
            else:
                source["coverage"]["saved"].update(status="unavailable", reason="service_history_expired")
            source["errors"] = list(dict.fromkeys(code for receipt in receipts.values() if receipt.data for code in receipt.data["sources"][0]["errors"]))[:128]
            source["sourceHealth"] = "current" if runtime.health == history.health == "current" and not source["errors"] else "partial" if runtime.current() or history.current() else "stale" if base else "unavailable"
            rt_rows = {identity_key(r["identity"]): r for r in runtime.data["sessions"]} if runtime.data else {}
            hi_rows = {identity_key(r["identity"]): r for r in history.data["sessions"]} if history.data else {}
            for key in rt_rows.keys() | hi_rows.keys():
                raw = rt_rows.get(key) or hi_rows[key]
                has_runtime = key in rt_rows
                row = stale_row(raw, runtime=not has_runtime or not runtime.current(),
                                metadata=not (runtime.current() if has_runtime else history.current()))
                # Workspace is collected only by the history component, even
                # when the runtime roster remains healthy.
                row["workspace"] = None
                saved = hi_rows.get(key)
                if saved:
                    saved = stale_row(saved, runtime=True, metadata=not history.current())
                    fallback = self.profiles[provider].display_name + " " + row["identity"]["nativeId"]
                    if row["title"] == fallback or key not in rt_rows or not runtime.current():
                        row["title"] = saved["title"]
                    if row["kind"] == "unknown" and history.current():
                        row["kind"] = saved["kind"]
                    for name in ("activity", "outcome"):
                        current = row[name]
                        candidate = saved[name]
                        if name == "activity":
                            rt_activity = rt_rows[key][name] if key in rt_rows else {}
                            hi_activity = hi_rows[key][name]
                            rt_clock = rt_activity.get("at") if rt_activity.get("at") is not None else rt_activity.get("lastKnownAt")
                            hi_clock = hi_activity.get("at") if hi_activity.get("at") is not None else hi_activity.get("lastKnownAt")
                            rt_known = rt_clock is not None and "retained_after_gap" not in rt_rows[key]["metadataIssues"]
                            hi_known = hi_clock is not None and "retained_after_gap" not in hi_rows[key]["metadataIssues"]
                            # A lease expiry does not move conversation history
                            # backward or promote an older clock to current.
                            if rt_known and (not hi_known or runtime.sampledBoottimeMs >= history.sampledBoottimeMs):
                                continue
                            if hi_known:
                                row[name] = candidate
                                continue
                        if name == "outcome":
                            # In-progress metadata is explicit negative knowledge
                            # about the latest turn, despite its unknown result.
                            # An older component must not restore a terminal
                            # outcome across a subsequently observed new turn.
                            # Expiring the new-turn sample cannot make an older
                            # completion become the latest turn again.
                            rt_observed = key in rt_rows and "retained_after_gap" not in rt_rows[key]["metadataIssues"]
                            hi_observed = "retained_after_gap" not in hi_rows[key]["metadataIssues"]
                            rt_latest = rt_observed and (not hi_observed or runtime.sampledBoottimeMs >= history.sampledBoottimeMs)
                            hi_latest = hi_observed and (not rt_observed or history.sampledBoottimeMs >= runtime.sampledBoottimeMs)
                            pending = (rt_rows[key] if rt_latest and rt_rows[key][name]["reason"] == "turn_in_progress"
                                       else hi_rows[key] if hi_latest and hi_rows[key][name]["reason"] == "turn_in_progress" else None)
                            if pending is not None:
                                row[name] = copy.deepcopy(pending[name])
                                continue
                        # History can establish metadata/outcome, never runtime phase.
                        if name == "outcome" and history.current():
                            candidate = copy.deepcopy(hi_rows[key][name])
                        at_key = "at" if name == "activity" else "observedAt"
                        if current["health"] != "current" or (candidate["health"] == "current" and (candidate.get(at_key) or 0) > (current.get(at_key) or 0)):
                            row[name] = candidate
                    if row["cwd"] is None:
                        row["cwd"], row["cwdSource"] = saved["cwd"], saved["cwdSource"]
                    if history.current() and row["cwd"] == saved["cwd"]:
                        row["workspace"] = saved["workspace"]
                    if row["createdAt"] is None:
                        row["createdAt"] = saved["createdAt"]
                    row["metadataIssues"] = list(dict.fromkeys((row["metadataIssues"] + saved["metadataIssues"])[:128]))
                rows.append(row)
            source["capabilities"]["activity"] = any(r["activity"]["health"] == "current" for r in rows if r["identity"]["provider"] == provider)
            sources.append(source)
        value = {
            "schemaVersion": 4, "collectionId": self.collection_id(), "collectedAt": self.wall_clock(),
            "host": {"authority": self.host_scope, "authoritySource": "caller", "nativeHostname": self.native_hostname, "uid": self.uid},
            "sourceHealth": "current" if all(s["sourceHealth"] == "current" for s in sources) else "partial" if rows or any(s["sourceHealth"] in {"current", "partial"} for s in sources) else "unavailable",
            "sources": sources, "sessions": [], "errors": [], "limitations": ["shared_sampled_service", "no_native_event_replay"],
        }
        used = len(canonical(value).encode()) + 256
        rows.sort(key=lambda r: (r["runtime"]["value"] != "running", identity_key(r["identity"])))
        dropped = False
        for row in rows:
            size = len(canonical(row).encode()) + 1
            if len(value["sessions"]) >= MAX_SESSIONS or used + size > MAX_SNAPSHOT_BYTES:
                dropped = True
                continue
            value["sessions"].append(row)
            used += size
        if dropped:
            value["errors"].append("service_view_limit")
            value["sourceHealth"] = "partial"
            for source in sources:
                source["sourceHealth"] = "partial"
                for coverage in source["coverage"].values():
                    if coverage["status"] == "complete":
                        coverage.update(status="partial", reason="service_view_limit")
        self.snapshot = validate_snapshot(value)
        self.revision += 1
