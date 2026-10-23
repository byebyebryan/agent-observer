"""Private projection retained only for the default-off sync experiment.

No I/O, Mesh, provider reads or presentation-context timeout.  Only the owning
engine publishes generations; status/proof/timer reads never mutate this ledger.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import partial

from .contract import MAX_BYTES, ContractError, _admitted_identity_key, canonical, validate_snapshot
from .observation_support import SUPPORT_FIELDS, empty_support, support_matches
from .projection_fields import _unique_supports as _unique_supports
from .projection_fields import mask_fields as mask_fields
from .projection_support import MAX_IDENTITIES, MAX_LEDGER_BYTES


@dataclass
class _Scope:
    context: int
    continuity: int = 1
    ledger: dict = field(default_factory=dict)
    failed: bool = False


class _SyncProjection:
    """Single fixed-selector cache, with exact original evidence support.

    Public ``accept`` validates arbitrary full input. ServiceState uses the
    private synchronous owned path immediately after engine validation; no
    borrowed mutable input becomes retained projection authority.
    """

    def __init__(self, *, service_id, max_identities=MAX_IDENTITIES,
                 max_ledger_bytes=MAX_LEDGER_BYTES):
        if (type(max_identities) is not int or not 1 <= max_identities <= MAX_IDENTITIES
                or type(max_ledger_bytes) is not int
                or not 1 <= max_ledger_bytes <= MAX_LEDGER_BYTES):
            raise ContractError("active_projector_limits")
        self.service_id = service_id
        self.max_identities, self.max_ledger_bytes = max_identities, max_ledger_bytes
        self._scopes = {}
        self._encoded = None
        self.revision = None
        self.generations = 0

    def snapshot(self):
        """Owned export of the cached projected body; no query-time authority."""
        if self._encoded is None:
            return None
        from .bounded_json import decode_document

        return decode_document(self._encoded, max_bytes=MAX_BYTES, max_nodes=2_000_000,
                               max_depth=34)

    def accept(self, snapshot, supports, census, sources, *, revision, now_ms):
        validate_snapshot(snapshot)
        return self._accept_owned(snapshot, supports, census, sources,
                                  revision=revision, now_ms=now_ms)

    def _classify(self, row, fields, source, now):
        valid = partial(support_matches, source=source, service_id=self.service_id, now_ms=now)
        runtime = row["runtime"]
        runtime_live = (runtime["health"] == "current" and valid(fields.get("runtime")))
        if runtime_live and runtime["value"] == "parked":
            saved = fields.get("savedIdentity")
            if (row["hasSavedHistory"] and valid(saved)
                    and saved == fields.get("runtime")):
                return "parked", _unique_supports((fields["runtime"], saved))
            return "uncertain", []
        kind = row["kind"]
        kind_live = kind == "unknown" or valid(fields.get("kind"))
        if kind in {"child", "system"} and kind_live:
            return "excluded_kind", _unique_supports((fields["kind"],))
        if runtime_live and runtime["value"] == "running" and kind_live:
            return "member", _unique_supports((fields["runtime"],
                                                fields.get("kind") if kind != "unknown" else None))
        return "uncertain", []

    def _ledger_size(self, override_key=None, override=None):
        # This object is the ledger accounting unit, not a sum of identity-key
        # string lengths. Scope failure metadata is separately frame bounded.
        value = {"scopes": []}
        count = 0
        for key in sorted(self._scopes):
            state = self._scopes[key]
            ledger = override if key == override_key else state.ledger
            entries = [ledger[identity] for identity in sorted(ledger)]
            count += len(entries)
            value["scopes"].append({"provider": key[0], "namespace": key[1],
                                     "contextGeneration": state.context,
                                     "continuity": state.continuity, "entries": entries})
        return count, len(canonical(value).encode())

    def _failed_scope(self, key, source, state, reason):
        if not state.failed:
            state.continuity += 1
        state.failed = True
        # This is a declared discontinuity, never silent eviction/removal.
        state.ledger = {}
        return {"provider": key[0], "namespace": key[1],
                "contextGeneration": source["contextGeneration"],
                "continuity": state.continuity,
                "coverage": {"status": "unavailable", "reason": reason, "supports": []},
                "members": [], "uncertain": [], "nonmembers": []}

    def _accept_owned(self, snapshot, supports, census, sources, *, revision, now_ms):
        if self.revision is not None and revision <= self.revision:
            if revision == self.revision:
                return self.snapshot()
            raise ContractError("active_projection_regression")
        if type(now_ms) is not int or now_ms < 0:
            raise ContractError("active_projection_clock")
        rows = {_admitted_identity_key(row["identity"]): row for row in snapshot["sessions"]
                if row["identity"]["provider"] == "codex"}
        source_snapshots = {(s["provider"], s["namespace"]): s for s in snapshot["sources"]}
        projection = {"scopes": [], "sessions": []}
        for source in sources:
            if source["provider"] != "codex":
                continue
            key = source["provider"], source["namespace"]
            generation = source["contextGeneration"]
            state = self._scopes.get(key)
            if state is None:
                state = self._scopes[key] = _Scope(generation)
            elif state.context != generation:
                state.context = generation
                state.continuity += 1
                state.ledger = {}
                state.failed = False
            ledger = {identity: copy.deepcopy(entry) for identity, entry in state.ledger.items()
                      if entry["horizonBoottimeMs"] > now_ms}
            local = {identity: row for identity, row in rows.items() if identity[1:3] == key}
            decisions = {}
            for identity, row in local.items():
                fields = supports.get(identity, empty_support())
                decisions[identity] = self._classify(row, fields, source, now_ms)
            members, selected = [], []
            for identity in sorted(decisions):
                decision, required = decisions[identity]
                if decision != "member":
                    continue
                row, fields = local[identity], supports.get(identity, empty_support())
                horizon = min(ref["expiresBoottimeMs"] for ref in required)
                # A current new native positive may renew itself, never an old
                # field merely carried under a new same-key receipt.
                ledger[identity] = {
                    "identity": copy.deepcopy(row["identity"]),
                    "priorSupport": copy.deepcopy(fields["runtime"]),
                    "positiveSupports": copy.deepcopy(required),
                    "horizonBoottimeMs": horizon,
                    "fieldSupports": copy.deepcopy(fields),
                    "decision": {"kind": "member", "supports": copy.deepcopy(required)},
                }
                valid = partial(support_matches, source=source, service_id=self.service_id,
                                now_ms=now_ms)
                clean = mask_fields(row, fields, valid)
                # Only current support is exported for body fields. Old refs
                # remain exclusively context metadata in the recent ledger.
                clean_fields = {name: copy.deepcopy(fields.get(name)) if valid(fields.get(name))
                                else None for name in SUPPORT_FIELDS}
                members.append({"identity": copy.deepcopy(row["identity"]),
                                "fieldSupports": clean_fields})
                selected.append(clean)
            scope_census = census.get(source["provider"], {})
            census_support = scope_census.get("support")
            complete = (scope_census.get("status") == "complete"
                        and support_matches(census_support, source, service_id=self.service_id,
                                            now_ms=now_ms)
                        and source_snapshots[key]["coverage"]["runtime"]["status"] == "complete")
            coverage_supports = [census_support] if complete else []
            if complete:
                for identity in scope_census.get("identities", ()):
                    row = local.get(tuple(identity))
                    fields = supports.get(tuple(identity), empty_support())
                    decision, required = decisions.get(tuple(identity), ("uncertain", []))
                    # Even excluded kinds cannot upgrade an unresolved runtime
                    # in the underlying exhaustive daemon census.
                    if (row is None or row["runtime"]["value"] == "unknown"
                            or not support_matches(fields.get("runtime"), source,
                                                   service_id=self.service_id, now_ms=now_ms)
                            or decision == "uncertain"):
                        complete = False
                        break
                    coverage_supports.extend(required)
            runtime = next(c for c in source["components"] if c["name"] == "runtime")
            status = "complete" if complete else (
                "partial" if runtime["health"] in {"current", "partial"} else runtime["health"])
            scope = {"provider": key[0], "namespace": key[1],
                     "contextGeneration": generation, "continuity": state.continuity,
                     "coverage": {"status": status,
                                  "reason": "complete_native_census" if complete else
                                  "membership_incomplete" if status == "partial" else
                                  "runtime_" + status,
                                  "supports": _unique_supports(coverage_supports) if complete else []},
                     "members": members, "uncertain": [], "nonmembers": []}
            for identity in sorted(ledger):
                entry = ledger[identity]
                if decisions.get(identity, (None,))[0] == "member":
                    continue
                row = local.get(identity)
                decision, required = decisions.get(identity, ("uncertain", []))
                if decision in {"parked", "excluded_kind"}:
                    fact = {"identity": copy.deepcopy(entry["identity"]),
                            "reason": decision,
                            "value": "parked" if decision == "parked" else row["kind"],
                            "supports": required,
                            "horizonBoottimeMs": entry["horizonBoottimeMs"]}
                    scope["nonmembers"].append(fact)
                    entry["decision"] = {"kind": decision, "supports": copy.deepcopy(required)}
                elif not complete:
                    fields = supports.get(identity, {})
                    scope["uncertain"].append({
                        "identity": copy.deepcopy(entry["identity"]),
                        "reason": "membership_unresolved",
                        "priorSupport": copy.deepcopy(entry["priorSupport"]),
                        "support": copy.deepcopy(fields.get("runtime")),
                        "horizonBoottimeMs": entry["horizonBoottimeMs"],
                    })
                    entry["decision"] = {"kind": "uncertain", "supports": []}
            count, size = self._ledger_size(key, ledger)
            if count > self.max_identities or size > self.max_ledger_bytes:
                scope = self._failed_scope(key, source, state, "projection_tracking_capacity")
                selected = []
            else:
                if state.failed:
                    state.continuity += 1
                    scope["continuity"] = state.continuity
                state.failed = False
                state.ledger = ledger
            projection["scopes"].append(scope)
            projection["sessions"].extend(selected)
        encoded = canonical(projection).encode()
        if len(encoded) > MAX_BYTES:
            projection = {"scopes": [self._failed_scope(
                (source["provider"], source["namespace"]), source,
                self._scopes[source["provider"], source["namespace"]],
                "projection_frame_capacity") for source in sources if source["provider"] == "codex"],
                "sessions": []}
            encoded = canonical(projection).encode()
        self._encoded = encoded
        self.revision = revision
        self.generations += 1
        return self.snapshot()
