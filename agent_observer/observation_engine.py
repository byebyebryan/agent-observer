"""Reusable passive observation decisions; all host clocks/identity are inputs."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from . import timing
from .contract import (
    MAX_SESSIONS,
    MAX_SNAPSHOT_BYTES,
    SCHEMA_VERSION,
    ContractError,
    canonical,
    identity_key,
    store_namespace,
    validate_snapshot,
)
from .observation_evidence import RuntimeOnlyRetention, retain_missing, stale_row
from .observation_support import empty_support, fact_support


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
                 collection_id, native_hostname, profiles, support_incarnation=None):
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
        self.retention = {provider: RuntimeOnlyRetention() for provider in configs}
        self._retirement_dirty = set(configs)
        self._retirement_due = dict.fromkeys(configs)
        self.snapshot = None
        self.revision = 0
        self.support_incarnation = support_incarnation
        self.projection_support = {}
        self.projection_census = {}
        self._component_support = {provider: {name: {} for name in ("runtime", "history")}
                                   for provider in configs}
        self._runtime_census = {}

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
        self._retirement_dirty.add(provider)
        self.publish()

    def accept(self, provider, component, value, *, sampled_ms, ttl_ms, runtime_ttl_ms=None):
        accepted = self._accept_sample(provider, component, value, sampled_ms=sampled_ms,
                                       ttl_ms=ttl_ms, runtime_ttl_ms=runtime_ttl_ms)
        if accepted:
            # A history read can refresh both receipts. Publish their reconciled
            # view once so readers do not lose a revision within one acceptance.
            self.publish()
        return accepted

    def _accept_sample(self, provider, component, value, *, sampled_ms, ttl_ms, runtime_ttl_ms=None, origin=None):
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
        origin = component if origin is None else origin
        for row in value["sessions"]:
            for name in ("lastUpdated", "latestTurn"):
                binding = row[name]["receipt"]
                if binding is None and row[name]["health"] == "current":
                    raise ContractError("service_worker_timing_binding")
                if binding is not None and (binding["component"] != origin or binding["sampledBoottimeMs"] != sampled_ms
                                            or binding["observedBoottimeMs"] > self.clock()):
                    raise ContractError("service_worker_timing_binding")
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
        for row in receipt.data["sessions"]:
            for name in ("lastUpdated", "latestTurn"):
                record = row[name]
                binding = record["receipt"]
                if binding is not None:
                    binding["contextGeneration"] = self.generations[provider]
        self._retirement_dirty.add(provider)
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
        if self.support_incarnation is not None:
            self._capture_support(provider, component, source)
        # Retain evidence belonging to this component across an incomplete read.
        # Only positive saved-history identity is retained by the metadata
        # component. Runtime retention uses its own daemon census coverage.
        retention = self.retention[provider] if component == "runtime" else None
        if retention is not None:
            retention.observe(value["sessions"], sampled_ms=sampled_ms, ttl_ms=ttl_ms)
        if previous and coverage != "complete":
            retain_missing(previous, receipt.data, component=component,
                           retention=retention, now=self.clock())
        if retention is not None:
            retention.prune(receipt.data["sessions"])
        self._prune_support(provider, component)
        if component == "history" and source["coverage"]["runtime"]["status"] in {"complete", "partial"}:
            runtime = self.receipts[provider]["runtime"]
            if runtime.sampledBoottimeMs is None or sampled_ms >= runtime.sampledBoottimeMs:
                self.attempt(provider, "runtime")
                self._accept_sample(provider, "runtime", value, sampled_ms=sampled_ms,
                                    ttl_ms=runtime_ttl_ms if runtime_ttl_ms is not None else min(ttl_ms, 60000), origin="history")
        return True

    def _capture_support(self, provider, component, source):
        """Capture actual inputs before incomplete-read retention mutates rows."""
        receipt = self.receipts[provider][component]
        meta = self.source_meta(provider)
        token = fact_support(self.support_incarnation, meta, component, receipt)
        previous = self._component_support[provider][component]
        captured = {}
        observed = []
        for row in receipt.data["sessions"]:
            key = identity_key(row["identity"])
            if "retained_after_gap" in row["metadataIssues"]:
                # An upstream retained row is context, not an actual new sample.
                captured[key] = copy.deepcopy(previous.get(key, empty_support()))
                continue
            observed.append(key)
            support = empty_support()
            if component == "runtime":
                for name in ("runtime", "phase"):
                    if row[name] is not None and row[name]["health"] == "current":
                        support[name] = token
            support["kind"] = token
            if row["hasSavedHistory"]:
                support["savedIdentity"] = token
            for name in ("activity", "outcome"):
                if ((row[name]["health"] == "current" and row[name]["source"] is not None)
                        or name == "outcome" and row[name]["reason"] == "turn_in_progress"):
                    support[name] = token
            if component == "history" and row["workspace"] is not None:
                support["workspace"] = token
            for name in ("lastUpdated", "latestTurn"):
                binding = row[name]["receipt"]
                if binding is not None and row[name]["health"] == "current":
                    owner = self.receipts[provider][binding["component"]]
                    if (binding["contextGeneration"] == meta["contextGeneration"]
                            and binding["sampledBoottimeMs"] == owner.sampledBoottimeMs):
                        support[name] = fact_support(self.support_incarnation, meta,
                                                     binding["component"], owner)
            captured[key] = copy.deepcopy(support)
        # Retain references only alongside the rows retain_missing may retain.
        # Pruning immediately after that operation removes all unused entries.
        self._component_support[provider][component] = {**previous, **captured}
        if component == "runtime":
            coverage = source["coverage"]["runtime"]
            self._runtime_census[provider] = {
                "status": coverage["status"], "reason": coverage["reason"],
                "support": copy.deepcopy(token), "identities": tuple(sorted(observed)),
            }
            if coverage["status"] == "complete" and (
                    len(observed) != len(receipt.data["sessions"])
                    or any(row["runtime"]["value"] == "unknown" for row in receipt.data["sessions"])
                    or coverage["scope"] == "daemon_threads"
                    and source["coverage"]["saved"]["status"] != "complete"):
                self._runtime_census[provider].update(status="partial", reason="bounded_census")

    def _prune_support(self, provider, component):
        if self.support_incarnation is None:
            return
        data = self.receipts[provider][component].data
        present = {identity_key(row["identity"]) for row in data["sessions"]} if data else set()
        support = self._component_support[provider][component]
        self._component_support[provider][component] = {key: value for key, value in support.items()
                                                        if key in present}

    def expire(self, now=None):
        now = self.clock() if now is None else now
        changed = False
        for provider, receipts in self.receipts.items():
            for receipt in receipts.values():
                if receipt.current() and receipt.expiresBoottimeMs <= now:
                    receipt.health = "stale"
                    receipt.lastResult = "lease_expired"
                    self._retirement_dirty.add(provider)
                    changed = True
        changed = self._retire_runtime_only(now) or changed
        if changed:
            self.publish()
        return changed

    def _retire_runtime_only(self, now):
        changed = False
        for provider, receipts in self.receipts.items():
            due = self._retirement_due[provider]
            if provider not in self._retirement_dirty and (due is None or now < due):
                continue
            runtime = receipts["runtime"]
            keyed = {name: [(identity_key(row["identity"]), row)
                            for row in (receipt.data or {}).get("sessions", [])]
                     for name, receipt in receipts.items()}
            saved = {key for rows in keyed.values() for key, row in rows
                     if row["hasSavedHistory"]}
            current = {key for key, row in keyed["runtime"]
                       if "retained_after_gap" not in row["metadataIssues"]} if runtime.current() else set()
            retention = self.retention[provider]
            protected = saved | current
            candidates = set()
            for name, receipt in receipts.items():
                if receipt.data is None:
                    continue
                rows = receipt.data["sessions"]
                kept = []
                for key, row in keyed[name]:
                    if key in protected:
                        kept.append(row)
                    elif retention.deadlines.get(key, now) > now:
                        kept.append(row)
                        candidates.add(key)
                receipt.data["sessions"] = kept
                self._prune_support(provider, name)
                changed = changed or len(rows) != len(receipt.data["sessions"])
            retention.prune(runtime.data["sessions"] if runtime.data else [])
            # Only unprotected survivors can retire by time alone. Current
            # rows become eligible on receipt replacement/failure/lease expiry.
            # Pruning can remove a history-only survivor's ledger entry; the
            # next call must then use the original immediate-expiry predicate.
            self._retirement_due[provider] = min(
                (retention.deadlines.get(key, now) for key in candidates), default=None)
            self._retirement_dirty.discard(provider)
        return changed

    def _placeholder(self, provider):
        meta = self.source_meta(provider)
        return {
            **{k: meta[k] for k in ("provider", "namespace", "configHome", "configHomeKind")},
            "runtimeNamespace": None, "runtime": None, "discovery": None, "sourceHealth": "unavailable",
            "coverage": {"saved": {"status": "unavailable", "reason": "not_observed"},
                         "runtime": {"status": "unavailable", "reason": "not_observed", "scope": self.profiles[provider].runtime_scope}},
            "capabilities": {"phase": [], "blockedReasons": [], "runtime": [], "activity": False,
                             "timing": {"lastUpdated": False, "latestTurn": False}},
            "errors": [], "limitations": ["source_not_observed"],
        }

    def publish(self):
        self._retire_runtime_only(self.clock())
        rows, sources = [], []
        projected_support = {}
        support_enabled = self.support_incarnation is not None
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
            rt_support, hi_support = (self._component_support[provider][name]
                                      for name in ("runtime", "history"))
            for key in rt_rows.keys() | hi_rows.keys():
                raw = rt_rows.get(key) or hi_rows[key]
                has_runtime = key in rt_rows
                support = (copy.deepcopy((rt_support if has_runtime else hi_support).get(key, empty_support()))
                           if support_enabled else {})
                row = stale_row(raw, runtime=not has_runtime or not runtime.current(),
                                metadata=not (runtime.current() if has_runtime else history.current()))
                # Workspace is collected only by the history component, even
                # when the runtime roster remains healthy.
                row["workspace"] = None
                support["workspace"] = None
                saved = hi_rows.get(key)
                if saved:
                    if saved["hasSavedHistory"] and not row["hasSavedHistory"]:
                        row["hasSavedHistory"] = True
                        row["inventory"] = "saved"
                        support["savedIdentity"] = hi_support.get(key, {}).get("savedIdentity")
                    saved = stale_row(saved, runtime=True, metadata=not history.current())
                    fallback = self.profiles[provider].display_name + " " + row["identity"]["nativeId"]
                    if row["title"] == fallback or key not in rt_rows or not runtime.current():
                        row["title"] = saved["title"]
                    if row["kind"] == "unknown" and history.current():
                        row["kind"] = saved["kind"]
                        support["kind"] = hi_support.get(key, {}).get("kind")
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
                                support[name] = hi_support.get(key, {}).get(name)
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
                            pending_component = ("runtime" if rt_latest and rt_rows[key][name]["reason"] == "turn_in_progress"
                                                 else "history" if hi_latest and hi_rows[key][name]["reason"] == "turn_in_progress" else None)
                            pending = (rt_rows if pending_component == "runtime" else hi_rows).get(key) if pending_component else None
                            if pending is not None:
                                row[name] = copy.deepcopy(pending[name])
                                support[name] = (rt_support if pending_component == "runtime" else hi_support).get(key, {}).get(name)
                                continue
                        # History can establish metadata/outcome, never runtime phase.
                        if name == "outcome" and history.current():
                            candidate = copy.deepcopy(hi_rows[key][name])
                        at_key = "at" if name == "activity" else "observedAt"
                        if current["health"] != "current" or (candidate["health"] == "current" and (candidate.get(at_key) or 0) > (current.get(at_key) or 0)):
                            row[name] = candidate
                            support[name] = hi_support.get(key, {}).get(name)
                    if row["cwd"] is None:
                        row["cwd"], row["cwdSource"] = saved["cwd"], saved["cwdSource"]
                    if history.current() and row["cwd"] == saved["cwd"]:
                        row["workspace"] = saved["workspace"]
                        support["workspace"] = hi_support.get(key, {}).get("workspace")
                    if row["createdAt"] is None:
                        row["createdAt"] = saved["createdAt"]
                    row["metadataIssues"] = list(dict.fromkeys((row["metadataIssues"] + saved["metadataIssues"])[:128]))
                for name in ("lastUpdated", "latestTurn"):
                    candidates = [(r[key][name], receipts[c].expiresBoottimeMs,
                                   self._component_support[provider][c].get(key, {}).get(name))
                                  for c, r in (("runtime", rt_rows), ("history", hi_rows)) if key in r]
                    selected = timing.select([(record, expiry) for record, expiry, _ in candidates], name)
                    # Follow timing.select's observation-order/lease tie choice,
                    # rather than attributing equal values to a newer receipt.
                    if not support_enabled or selected["receipt"] is None:
                        support[name] = None
                    else:
                        def order(item):
                            binding = item[0]["receipt"]
                            return (-1, -1) if binding is None else (binding["sampledBoottimeMs"], binding["observedBoottimeMs"])
                        newest = max(map(order, candidates))
                        winner = min((item for item in candidates if order(item) == newest),
                                     key=lambda item: item[1] if item[1] is not None else -1)
                        support[name] = winner[2]
                    binding = selected["receipt"]
                    owner = receipts[binding["component"]] if binding is not None else None
                    if owner is None or not owner.current() or binding["contextGeneration"] != self.generations[provider] or binding["sampledBoottimeMs"] != owner.sampledBoottimeMs:
                        selected = timing.stale(selected, name, "service_timing_expired")
                    row[name] = selected
                rows.append(row)
                if self.support_incarnation is not None:
                    projected_support[key] = copy.deepcopy(support)
            source["capabilities"]["activity"] = any(r["activity"]["health"] == "current" for r in rows if r["identity"]["provider"] == provider)
            source["capabilities"]["timing"] = {name: any(r[name]["health"] == "current" for r in rows if r["identity"]["provider"] == provider)
                                                for name in ("lastUpdated", "latestTurn")}
            sources.append(source)
        value = {
            "schemaVersion": SCHEMA_VERSION, "collectionId": self.collection_id(), "collectedAt": self.wall_clock(),
            "host": {"authority": self.host_scope, "authoritySource": "caller", "nativeHostname": self.native_hostname, "uid": self.uid},
            "sourceHealth": "current" if all(s["sourceHealth"] == "current" for s in sources) else "partial" if rows or any(s["sourceHealth"] in {"current", "partial"} for s in sources) else "unavailable",
            "sources": sources, "sessions": [], "errors": [], "limitations": ["shared_sampled_service", "no_native_event_replay", "runtime_only_retention_runtime_lease"],
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
        if self.support_incarnation is not None:
            self.projection_support = {identity_key(row["identity"]): projected_support[identity_key(row["identity"])]
                                       for row in value["sessions"]}
            self.projection_census = {}
            for source in sources:
                provider = source["provider"]
                census = copy.deepcopy(self._runtime_census.get(provider, {
                    "status": "unavailable", "reason": "not_observed", "support": None, "identities": (),
                }))
                if not self.receipts[provider]["runtime"].current() and census["status"] != "unsupported":
                    census.update(status="unavailable", reason=source["coverage"]["runtime"]["reason"])
                elif dropped and census["status"] == "complete":
                    census.update(status="partial", reason="service_view_limit")
                self.projection_census[provider] = census
        self.revision += 1
