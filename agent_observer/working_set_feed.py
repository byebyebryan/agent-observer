"""One opt-in, bounded active-or-recent complete-replacement cache.

No I/O, provider access, Mesh or caller-controlled predicates. The owner calls
refresh on an observation or a scheduled quiet cutoff, never on every read.
The last-T guard remains separate from bounded prior-positive presentation
context: dropping old context is not evidence that a session left the view.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from functools import partial

from .bounded_json import decode_document
from .contract import MAX_BYTES, ContractError, _admitted_identity_key, canonical, validate_snapshot
from .observation_support import SUPPORT_FIELDS, empty_support, support_matches
from .projection_fields import _unique_supports, mask_fields
from .working_set_contract import MAX_IDENTITIES, MAX_LEDGER_BYTES, selector
from .working_set_decisions import WorkingSetDecisions
from .working_set_ledger import LEDGER_PLAN_SCRATCH_BYTES, WorkingSetLedger
from .working_set_policy import PolicyResult, combine_membership
from .working_set_supports import SUPPORT_PLAN_SCRATCH_BYTES, SupportTableBuilder


def _identity_mapping(identity):
    """Reconstruct one detached API identity from a checked full identity key."""

    return {
        "hostScope": identity[0],
        "provider": identity[1],
        "namespace": identity[2],
        "nativeIdKind": identity[3],
        "nativeId": identity[4],
    }


class WorkingSetProjector:
    def __init__(
        self,
        *,
        service_id,
        clocks,
        window_ms,
        max_identities=MAX_IDENTITIES,
        max_ledger_bytes=MAX_LEDGER_BYTES,
    ):
        selector(window_ms)
        if (
            type(max_identities) is not int
            or not 1 <= max_identities <= MAX_IDENTITIES
            or type(max_ledger_bytes) is not int
            or not 1 <= max_ledger_bytes <= MAX_LEDGER_BYTES
        ):
            raise ContractError("working_set_projector_limits")
        self.service_id, self.clocks, self.window_ms = service_id, clocks, window_ms
        self.max_identities, self.max_ledger_bytes = max_identities, max_ledger_bytes
        self.decisions = WorkingSetDecisions(
            service_id,
            window_ms,
            max_identities=max_identities,
            max_guard_bytes=max(1, max_ledger_bytes - SUPPORT_PLAN_SCRATCH_BYTES),
        )
        self._context = None
        self._ledger = WorkingSetLedger.empty()
        self._encoded = None
        self._clock_state = None
        self._failed, self._continuity = False, 1
        self._capacity_blocked = False
        self.revision = self.generations = 0
        self.observation_revision = None
        self.next_deadline_ms = None

    def snapshot(self):
        return (
            None
            if self._encoded is None or self._capacity_blocked
            else decode_document(
                self._encoded,
                max_bytes=MAX_BYTES,
                max_nodes=2_000_000,
                max_depth=36,
            )
        )

    def due(self, now_ms):
        return self.next_deadline_ms is not None and now_ms >= self.next_deadline_ms

    def refuse_capacity(self, source, *, observation_revision):
        """Mark the projection unavailable without allocating another buffer.

        Keep the last committed bytes physically owned and accounted, but make
        them unavailable to readers. Guard/K and accepted-context state survive.
        """
        clock_state = self.clocks.ceiling, self.clocks.generation
        first_block = not self._capacity_blocked
        if not self._failed:
            self._continuity += 1
            self._failed = True
        self._ledger = WorkingSetLedger.empty(self._context)
        if first_block or clock_state != self._clock_state:
            self.revision += 1
            self.generations += 1
        self._capacity_blocked = True
        self._clock_state = clock_state
        self.observation_revision, self.next_deadline_ms = observation_revision, None

    def accept(
        self, snapshot, supports, census, sources, *, observation_revision, now_ms, sample_ids
    ):
        validate_snapshot(snapshot)
        self._accept_owned(
            snapshot,
            supports,
            census,
            sources,
            observation_revision=observation_revision,
            now_ms=now_ms,
            sample_ids=sample_ids,
        )
        return self.snapshot()

    def _failure(self, scope, reason):
        if not self._failed:
            self._continuity += 1
        self._failed = True
        self._ledger = WorkingSetLedger.empty(self._context)
        scope.update(
            continuity=self._continuity,
            supportTable=[],
            members=[],
            uncertain=[],
            nonmembers=[],
            coverage={"status": "unavailable", "reason": reason, "supports": []},
        )
        return {"scopes": [scope], "sessions": []}

    def _accept_owned(
        self, snapshot, supports, census, sources, *, observation_revision, now_ms, sample_ids
    ):
        if (
            type(now_ms) is not int
            or now_ms < 0
            or type(observation_revision) is not int
            or observation_revision < 0
            or self.observation_revision is not None
            and observation_revision < self.observation_revision
        ):
            raise ContractError("working_set_projection_regression")
        original = next((s for s in snapshot["sources"] if s["provider"] == "codex"), None)
        source = next((s for s in sources if s["provider"] == "codex"), None)
        if original is None or source is None:
            raise ContractError("working_set_projection_source")
        context = source["provider"], source["namespace"], source["contextGeneration"]
        if context != self._context:
            if self._context is not None:
                self._continuity += 1
            self._context, self._ledger, self._failed = (
                context,
                WorkingSetLedger.empty(context),
                False,
            )
            self.decisions.reset_context(*context)
        valid = partial(support_matches, source=source, service_id=self.service_id, now_ms=now_ms)
        rows = {
            _admitted_identity_key(r["identity"]): r
            for r in snapshot["sessions"]
            if (r["identity"]["provider"], r["identity"]["namespace"]) == context[:2]
        }
        classified, members, bodies, deadlines = {}, [], [], []
        for identity in sorted(rows):
            row, fields = rows[identity], supports.get(identity, empty_support())
            ref = fields.get("activity")
            if row["activity"]["at"] is None:
                ref = fields.get("latestTurn")
            sample_id = sample_ids.get(ref["component"]) if ref is not None else None
            clock = self.clocks.get(ref, source, sample_id=sample_id)
            decision = self.decisions.classify(
                row,
                fields,
                source,
                clock=clock,
                clock_generation=self.clocks.generation,
                clock_ceiling=self.clocks.ceiling,
                now_ms=now_ms,
                expected_sample_id=sample_id,
            )
            classified[identity] = decision
        if self.decisions.latched:
            for identity, decision in classified.items():
                classified[identity] = replace(
                    decision,
                    recent=PolicyResult(None, "recency_tracking_capacity"),
                    recent_supports=(),
                    selected=combine_membership(
                        decision.eligibility,
                        decision.active,
                        None,
                    ).decision,
                    negative_kind=("excluded_kind" if decision.eligibility is False else None),
                    negative_supports=(
                        decision.negative_supports if decision.eligibility is False else ()
                    ),
                )
        old_ledger = self._ledger
        old_ledger_bytes = old_ledger.charge
        first_identity = next(iter(rows), None)
        requested_prefix = first_identity[:4] if first_identity is not None else None
        prefix_changed = (
            requested_prefix is not None
            and old_ledger.prefix is not None
            and requested_prefix != old_ledger.prefix
        )
        candidate_upper = (
            WorkingSetLedger.empty_upper_charge(context)
            if prefix_changed
            else old_ledger.clone_upper_charge()
        )
        candidate_scratch = (
            512 + 12 * (0 if prefix_changed else old_ledger.count)
        )
        tracking_bytes = (
            self.decisions.guard_bytes
            + old_ledger_bytes
            + candidate_upper
            + SUPPORT_PLAN_SCRATCH_BYTES
            + LEDGER_PLAN_SCRATCH_BYTES
            + candidate_scratch
            + 1024
        )
        tracking_capacity = tracking_bytes > self.max_ledger_bytes
        ledger = None
        if not tracking_capacity:
            ledger = (
                WorkingSetLedger.empty(context, fallback=old_ledger)
                if prefix_changed
                else old_ledger.clone_live(now_ms)
            )
            tracking_bytes = (
                self.decisions.guard_bytes
                + old_ledger_bytes
                + ledger.charge
                + SUPPORT_PLAN_SCRATCH_BYTES
                + LEDGER_PLAN_SCRATCH_BYTES
                + ledger.iteration_scratch_bytes
                + 1024
            )
        support_table = SupportTableBuilder(
            limit=self.max_ledger_bytes,
            support_lookup=ledger.support_for if ledger is not None else None,
        )
        for identity in sorted(rows):
            row, fields = rows[identity], supports.get(identity, empty_support())
            decision = classified[identity]
            recent = decision.recent
            for deadline in (recent.deadline_lower_boottime_ms, recent.deadline_upper_boottime_ms):
                if deadline is not None and deadline > now_ms:
                    deadlines.append(deadline)
            if decision.selected is not True:
                continue
            if tracking_capacity:
                continue
            active = (
                {"supports": list(decision.active_supports)} if decision.active is True else None
            )
            recent_branch = None
            if recent.decision is True:
                ref = fields["activity"]
                recent_branch = {
                    "supports": list(decision.recent_supports),
                    "activityAt": row["activity"]["at"],
                    "clock": {"component": ref["component"], "accepted": ref["accepted"]},
                    "lowerBoottimeMs": recent.deadline_lower_boottime_ms,
                    "upperBoottimeMs": recent.deadline_upper_boottime_ms,
                }
            clean = mask_fields(row, fields, valid)
            if clean["runtime"]["value"] != "parked" and clean["phase"] is None:
                clean["phase"] = {
                    "value": "unknown",
                    "observedAt": None,
                    "source": None,
                    "health": "stale",
                    "reason": "working_set_support_expired",
                    "clock": None,
                }
            clean_fields = {
                name: fields.get(name) if valid(fields.get(name)) else None
                for name in SUPPORT_FIELDS
            }
            metadata = {
                "identity": copy.deepcopy(row["identity"]),
                "fieldSupports": clean_fields,
                "active": active,
                "recent": recent_branch,
            }
            required = _unique_supports(
                (
                    *(decision.active_supports if decision.active is True else ()),
                    *(decision.recent_supports if recent.decision is True else ()),
                )
            )
            prior = max(required, key=lambda s: s["expiresBoottimeMs"])
            # Informational context retention only, not hSelected. Keeping
            # context beyond Dlo is needed during the Dlo..Dhi uncertainty
            # interval. Positive authority is always the separate A/R proof.
            if ledger is None:
                tracking_capacity = True
                continue
            if ledger.count >= self.max_identities and ledger.get(identity) is None:
                tracking_capacity = True
                continue
            try:
                update = ledger.plan_put(
                    identity,
                    prior,
                    current_charge=tracking_bytes,
                    limit=self.max_ledger_bytes,
                )
            except ContractError as exc:
                if str(exc) != "working_set_ledger_capacity":
                    raise
                tracking_capacity = True
                continue
            try:
                compact_metadata = support_table.member(
                    metadata,
                    additional_charge=update.peak_additional_bytes,
                    current_charge=tracking_bytes,
                )
            except ContractError as exc:
                if str(exc) not in {
                    "working_set_support_capacity",
                    "working_set_support_table_limit",
                }:
                    raise
                tracking_capacity = True
                continue
            prior_owned = support_table.owned_support(prior)
            previous_ledger_bytes = ledger.charge
            previous_iteration_scratch = ledger.iteration_scratch_bytes
            ledger.put(update, prior_owned)
            tracking_bytes += (
                len(canonical(compact_metadata).encode())
                + ledger.charge
                - previous_ledger_bytes
                + ledger.iteration_scratch_bytes
                - previous_iteration_scratch
            )
            if tracking_bytes + support_table.preflight_charge > self.max_ledger_bytes:
                tracking_capacity = True
                continue
            members.append(compact_metadata)
            bodies.append(clean)
        native_census = census.get("codex", {})
        census_support = native_census.get("support")
        complete = (
            native_census.get("status") == "complete"
            and valid(census_support)
            and original["coverage"]["runtime"]["status"] == "complete"
            and not self.decisions.latched
        )
        coverage_supports = [census_support] if complete else []
        if complete and not tracking_capacity:
            for identity in native_census.get("identities", ()):
                identity = tuple(identity)
                decision = classified.get(identity)
                if decision is None or decision.selected is None:
                    complete = False
                    break
                coverage_supports.extend(
                    decision.active_supports if decision.active is True else ()
                )
                coverage_supports.extend(
                    decision.recent_supports if decision.recent.decision is True else ()
                )
                coverage_supports.extend(
                    decision.negative_supports if decision.selected is False else ()
                )
        runtime = next(r for r in source["components"] if r["name"] == "runtime")
        status = (
            "complete"
            if complete
            else ("partial" if runtime["health"] in {"current", "partial"} else runtime["health"])
        )
        scope = {
            "provider": context[0],
            "namespace": context[1],
            "contextGeneration": context[2],
            "continuity": self._continuity,
            "supportTable": [],
            "clocks": self.clocks.export(source),
            "coverage": {
                "status": status,
                "reason": "complete_native_census"
                if complete
                else "recency_tracking_capacity"
                if self.decisions.latched
                else "membership_incomplete",
                "supports": [],
            },
            "members": members,
            "uncertain": [],
            "nonmembers": [],
        }
        if complete and not tracking_capacity:
            coverage = {
                **scope["coverage"],
                "supports": _unique_supports(coverage_supports),
            }
            try:
                scope["coverage"] = support_table.coverage(
                    coverage,
                    current_charge=tracking_bytes,
                )
                tracking_bytes += len(canonical(scope["coverage"]).encode())
            except ContractError as exc:
                if str(exc) not in {
                    "working_set_support_capacity",
                    "working_set_support_table_limit",
                }:
                    raise
                tracking_capacity = True
        for identity, prior_support, horizon in ledger.iter_items() if ledger is not None else ():
            if tracking_capacity:
                break
            decision = classified.get(identity)
            if decision is not None and decision.selected is True:
                continue
            if (
                decision is not None
                and decision.selected is False
                and decision.negative_kind is not None
            ):
                row = rows[identity]
                recent = decision.recent
                negative = None
                reason = decision.negative_kind
                if reason != "excluded_kind":
                    disabled = recent.reason == "window_disabled"
                    no_activity = reason == "no_activity"
                    fields = supports.get(identity, {})
                    ref = (
                        None
                        if disabled
                        else fields.get("latestTurn" if no_activity else "activity")
                    )
                    negative = {
                        "kind": "window_disabled"
                        if disabled
                        else "no_activity"
                        if no_activity
                        else "outside_window",
                        "support": ref,
                        "clock": None
                        if disabled
                        else {"component": ref["component"], "accepted": ref["accepted"]},
                        "activityAt": None if disabled or no_activity else row["activity"]["at"],
                        "lowerBoottimeMs": recent.deadline_lower_boottime_ms,
                        "upperBoottimeMs": recent.deadline_upper_boottime_ms,
                        "absence": {
                            "field": "latestTurn",
                            "latestTurn": copy.deepcopy(row["latestTurn"]),
                            "activity": copy.deepcopy(row["activity"]),
                        }
                        if no_activity
                        else None,
                    }
                candidate = {
                    "identity": _identity_mapping(identity),
                    "reason": reason,
                    "value": row["kind"] if reason == "excluded_kind" else "parked",
                    "supports": list(decision.negative_supports),
                    "recent": negative,
                    "horizonBoottimeMs": horizon,
                }
                try:
                    compact = support_table.nonmember(
                        candidate,
                        current_charge=tracking_bytes,
                    )
                except ContractError as exc:
                    if str(exc) not in {
                        "working_set_support_capacity",
                        "working_set_support_table_limit",
                    }:
                        raise
                    tracking_capacity = True
                    continue
                tracking_bytes += len(canonical(compact).encode())
                if tracking_bytes + support_table.preflight_charge > self.max_ledger_bytes:
                    tracking_capacity = True
                    continue
                scope["nonmembers"].append(compact)
            elif not complete:
                fields = supports.get(identity, {})
                candidate = {
                    "identity": _identity_mapping(identity),
                    "reason": "membership_unresolved",
                    "priorSupport": prior_support,
                    "support": fields.get("runtime"),
                    "horizonBoottimeMs": horizon,
                }
                try:
                    compact = support_table.uncertain(
                        candidate,
                        current_charge=tracking_bytes,
                    )
                except ContractError as exc:
                    if str(exc) not in {
                        "working_set_support_capacity",
                        "working_set_support_table_limit",
                    }:
                        raise
                    tracking_capacity = True
                    continue
                tracking_bytes += len(canonical(compact).encode())
                if tracking_bytes + support_table.preflight_charge > self.max_ledger_bytes:
                    tracking_capacity = True
                    continue
                scope["uncertain"].append(compact)
        if not tracking_capacity:
            support_table.finalize(scope)
        # Guard state survives prior-positive retirement. Count both, plus all
        # native scope metadata, in the single tracking limit.
        tracked_count = len(rows)
        if ledger is not None:
            for identity in ledger.identities():
                if identity not in rows:
                    tracked_count += 1
        combined = (
            len(canonical([scope]).encode())
            + self.decisions.guard_bytes
            + (ledger.charge if ledger is not None else 0)
            + old_ledger_bytes
            + SUPPORT_PLAN_SCRATCH_BYTES
            + LEDGER_PLAN_SCRATCH_BYTES
            + (ledger.iteration_scratch_bytes if ledger is not None else 512)
            + 1024
            + support_table.overhead_charge
        )
        projection = {"scopes": [scope], "sessions": bodies}
        encoded = None
        if (
            tracking_capacity
            or tracked_count > self.max_identities
            or combined > self.max_ledger_bytes
        ):
            projection = self._failure(scope, "projection_tracking_capacity")
        else:
            recovering = self._failed
            if recovering:
                # Measure the continuity value recovery would publish, but do
                # not commit it until the final candidate passes its size cap.
                scope["continuity"] = self._continuity + 1
            encoded = canonical(projection).encode()
            if len(encoded) > MAX_BYTES:
                projection = self._failure(scope, "projection_frame_capacity")
                encoded = None
            else:
                if recovering:
                    self._continuity = scope["continuity"]
                if ledger is None:
                    raise ContractError("working_set_ledger_missing")
                ledger.detach_fallback()
                self._failed, self._ledger = False, ledger
        for _identity, _support, horizon in self._ledger.iter_items():
            if horizon > now_ms:
                deadlines.append(horizon)
        if encoded is None:
            encoded = canonical(projection).encode()
        clock_state = self.clocks.ceiling, self.clocks.generation
        if (
            encoded != self._encoded
            or clock_state != self._clock_state
            or self._capacity_blocked
        ):
            self._encoded = encoded
            self._clock_state = clock_state
            self.revision += 1
            self.generations += 1
        # Only a fully constructed and committed replacement releases a
        # capacity refusal. A failed encode/validation path leaves it blocked.
        self._capacity_blocked = False
        self.observation_revision = observation_revision
        self.next_deadline_ms = min(deadlines, default=None)
