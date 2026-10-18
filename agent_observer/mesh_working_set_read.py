"""Prepared working-set reads with independently expiring A OR R branches.

Public Mesh admission is mandatory. The detached native rows are retained once;
Mesh's conjunctive row filter is never used as the domain union or age policy.
No I/O, presentation history or implicit full-history fallback is owned here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from mesh_plus import api as mesh_api
from mesh_plus.api import PreparedReadGuard
from mesh_plus.protocol import check

from .active_contract import support_matches
from .active_feed import mask_fields
from .contract import canonical, identity_key
from .mesh_working_set_profile import (
    NATIVE_PROTOCOL,
    WORKING_SET_PROFILE_ID,
    WorkingSetAgentPreparation,
    WorkingSetAgentProfile,
)
from .working_set_contract import WORKING_SET_PROTOCOL, selector, selector_digest
from .working_set_policy import DEFAULT_WINDOW_MS

WORKING_SET_READ_INTERFACE_VERSION = 1


@dataclass(frozen=True)
class WorkingSetAgentRead:
    context: dict | None
    members: list
    uncertain: list
    nonmembers: list
    scopes: list

    @property
    def sessions(self):
        return self.members


class _WorkingSetSelection:
    """Domain policy over already admitted, detached public SDK exports.

    This helper confers no admission capability. The facade calls it only after
    current(now, clock) and context(); tests may exercise its arithmetic without
    fabricating an SDK profile descriptor or claiming Reader admission.
    """

    def __init__(self, window_ms):
        self._selector = selector(window_ms)
        self._digest = selector_digest(self._selector)
        self.clear()

    def clear(self):
        """Terminal watch retirement; a new watch owns a new reader clock."""
        self.revoke()
        self.bindings = {}
        self.clocks = {}
        self.last_now = None

    def revoke(self):
        """Drop current material without forgetting this watch's watermarks."""
        self.snapshot = None
        self.rows = {}

    def retain(self, snapshot):
        if snapshot is None:
            self.revoke()
            return
        check(snapshot["protocol"] == WORKING_SET_PROFILE_ID, "working_set_profile_binding")
        # One current scope and clock binding per admitted host/provider. Do not
        # accumulate retired namespace/service keys as a watch runs indefinitely.
        bindings, clocks = dict(self.bindings), dict(self.clocks)
        for host in snapshot["mesh"]["hosts"]:
            owner = host["owner"]
            if owner is None:
                continue
            service = owner["service"]
            self._policy(host, owner)
            incarnation = service["serviceId"], service["bootId"], service["clockDomain"]
            previous = clocks.get(host["hostId"])
            ceiling, generation = service["clockCeiling"], service["clockGeneration"]
            if previous is not None and previous[0] == incarnation:
                check((previous[1] is None or ceiling is not None and ceiling >= previous[1])
                      and generation >= previous[2], "working_set_clock_regression")
            clocks[host["hostId"]] = incarnation, ceiling, generation
            if owner["metadata"] is None:
                continue
            for scope in owner["metadata"]["scopes"]:
                key = host["hostId"], scope["provider"]
                scope_incarnation = host["delivery"]["epoch"], service["serviceId"]
                binding = (scope_incarnation, scope["namespace"],
                           scope["contextGeneration"], scope["continuity"])
                old = bindings.get(key)
                if old is not None and old[0] == scope_incarnation and old[1] == binding[1]:
                    check(binding[2] >= old[2] and binding[3] >= old[3]
                          and (binding[2] == old[2] or binding[3] > old[3]),
                          "working_set_scope_continuity")
                bindings[key] = binding
        present = {host["hostId"] for host in snapshot["mesh"]["hosts"]}
        self.bindings = {key: value for key, value in bindings.items() if key[0] in present}
        self.clocks = {key: value for key, value in clocks.items() if key in present}
        self.snapshot = snapshot
        self.rows = {identity_key(row["identity"]): row for row in snapshot["sessions"]}

    def _policy(self, host, owner):
        service = owner["service"]
        check(owner["protocol"] == NATIVE_PROTOCOL
              and owner["version"] == WORKING_SET_PROTOCOL
              and service["hostScope"] == host["hostId"]
              and service["workingSetProtocol"] == WORKING_SET_PROTOCOL
              and canonical(service["selector"]) == canonical(self._selector)
              and service["selectorDigest"] == self._digest, "working_set_policy_binding")

    def _ready(self, host, owner, scope, source):
        self._policy(host, owner)
        return (source is not None and scope["contextGeneration"] == source["contextGeneration"]
                and self.bindings.get((host["hostId"], scope["provider"])) == (
                    (host["delivery"]["epoch"], owner["service"]["serviceId"]),
                    scope["namespace"], scope["contextGeneration"], scope["continuity"],
                ))

    @staticmethod
    def _uncertain(entry, reason):
        refs = entry.get("supports", ())
        if "fieldSupports" in entry:
            refs = [ref for ref in entry["fieldSupports"].values() if ref is not None]
        prior = max(refs, key=lambda ref: ref["expiresBoottimeMs"], default=None)
        return {
            "identity": copy.deepcopy(entry["identity"]), "reason": reason,
            "priorSupport": copy.deepcopy(prior), "support": None,
            "horizonBoottimeMs": 0 if prior is None else prior["expiresBoottimeMs"],
        }

    def evaluate(self, current, now_ms):
        check(type(now_ms) is int and now_ms >= 0
              and (self.last_now is None or now_ms >= self.last_now),
              "working_set_reader_clock_regression")
        self.last_now = now_ms
        if current is None or self.snapshot is None:
            self.revoke()
            return WorkingSetAgentRead(None, [], [], [], [])
        check(current["protocol"] == WORKING_SET_PROFILE_ID, "working_set_profile_binding")
        members, uncertain, nonmembers, scopes = [], [], [], []
        for host in current["mesh"]["hosts"]:
            owner = host["owner"]
            if owner is None or owner["metadata"] is None:
                continue
            service = owner["service"]
            sources = {(s["provider"], s["namespace"]): s for s in service["sources"]}
            receipts = {(r["sourceId"], r["component"]): r for r in host["receipts"]}
            for scope in owner["metadata"]["scopes"]:
                source = sources.get((scope["provider"], scope["namespace"]))
                ready = self._ready(host, owner, scope, source)
                delivery = host["delivery"]["status"] == "ready" and host["viewState"] == "current"

                def horizon(ref, *, ready=ready, delivery=delivery, source=source,
                            service=service, receipts=receipts):
                    if (not ready or not delivery or ref is None or not support_matches(
                        ref, source, service["serviceId"], service["emittedBoottimeMs"]
                    )):
                        return None
                    receipt = receipts.get((ref["provider"] + ":" + ref["namespace"], ref["component"]))
                    if (receipt is None or receipt["accepted"] != ref["accepted"]
                            or receipt["health"] not in {"current", "partial"}
                            or type(receipt["expiresAtMs"]) is not int
                            or receipt["expiresAtMs"] <= now_ms):
                        return None
                    return receipt["expiresAtMs"]

                def valid(ref, *, horizon=horizon):
                    return horizon(ref) is not None

                def branch(refs, *, horizon=horizon):
                    values = [horizon(ref) for ref in refs]
                    return min(values) if values and all(v is not None for v in values) else None

                coverage = copy.deepcopy(scope["coverage"])
                uncertain.extend(copy.deepcopy(scope["uncertain"]))
                all_selected = True
                for entry in scope["members"]:
                    row = self.rows.get(identity_key(entry["identity"]))
                    fields = entry["fieldSupports"]
                    eligible = row is not None and (row["kind"] == "unknown" or valid(fields["kind"]))
                    active = None if entry["active"] is None else branch(entry["active"]["supports"])
                    recent = None
                    if entry["recent"] is not None:
                        recent = branch(entry["recent"]["supports"])
                        ref = fields["activity"]
                        translated = horizon(ref)
                        if recent is not None and translated is not None:
                            # Positive-only attenuation against the SAME original
                            # native expiry and its Mesh-translated deadline. Dhi
                            # is never translated into an absence decision.
                            cutoff = translated - max(
                                0, ref["expiresBoottimeMs"] - entry["recent"]["lowerBoottimeMs"]
                            )
                            recent = min(recent, cutoff)
                        else:
                            recent = None
                    positive = [value for value in (active, recent) if value is not None and value > now_ms]
                    if not eligible or not positive:
                        all_selected = False
                        uncertain.append(self._uncertain(entry, "working_set_membership_unresolved"))
                        continue
                    clean = mask_fields(row, fields, valid)
                    if clean["runtime"]["value"] != "parked" and clean["phase"] is None:
                        clean["phase"] = {
                            "value": "unknown", "observedAt": None, "source": None,
                            "health": "stale", "reason": "working_set_support_expired", "clock": None,
                        }
                    members.append(clean)
                for entry in scope["nonmembers"]:
                    if entry["supports"] and all(valid(ref) for ref in entry["supports"]):
                        # This is an already admitted native negative; no new
                        # negative can be inferred from a local positive timeout.
                        nonmembers.append(copy.deepcopy(entry))
                    else:
                        all_selected = False
                        uncertain.append(self._uncertain(entry, "working_set_negative_expired"))
                if not ready or not delivery:
                    coverage.update(status="unavailable", reason="working_set_delivery_unavailable")
                elif coverage["status"] == "complete" and (
                    not coverage["supports"] or not all(valid(ref) for ref in coverage["supports"])
                    or not all_selected
                ):
                    coverage.update(status="partial", reason="working_set_membership_unresolved")
                scopes.append({
                    "hostScope": host["hostId"], "serviceId": service["serviceId"],
                    **{key: scope[key] for key in (
                        "provider", "namespace", "contextGeneration", "continuity",
                    )}, "coverage": coverage,
                })
        return WorkingSetAgentRead(copy.deepcopy(current["mesh"]), members, uncertain, nonmembers, scopes)


class PreparedWorkingSetAgentWatch:
    """Serialized, explicit working-set facade; disconnect on all transport loss."""

    def __init__(self, request_id, *, host_ids=None, window_ms=DEFAULT_WINDOW_MS,
                 profile=None, preparation=None):
        check(getattr(mesh_api, "ADMISSION_INTERFACE_VERSION", None) == 1
              and callable(getattr(PreparedReadGuard, "context", None)),
              "mesh_prepared_read_incompatible")
        profile = WorkingSetAgentProfile(window_ms) if profile is None else profile
        check(type(profile) is WorkingSetAgentProfile and profile.window_ms == window_ms,
              "working_set_policy_binding")
        preparation = WorkingSetAgentPreparation(profile) if preparation is None else preparation
        check(type(preparation) is WorkingSetAgentPreparation and preparation.profile == profile,
              "working_set_preparation_binding")
        self._guard = PreparedReadGuard("agent", request_id, host_ids=host_ids,
                                        profile=profile, preparation=preparation)
        self._selection = _WorkingSetSelection(window_ms)

    def accept(self, frame):
        try:
            self._guard.accept(frame)
            if isinstance(frame, dict) and frame.get("mesh", {}).get("kind") == "heartbeat":
                return frame
            self._selection.retain(self._guard.snapshot())
        except BaseException:
            self.disconnect()
            raise
        return frame

    def read(self, now_ms, clock):
        try:
            self._guard.current(now_ms, clock)
            return self._selection.evaluate(self._guard.context(), now_ms)
        except BaseException:
            self.disconnect()
            raise

    def snapshot(self):
        """Detached admitted diagnostic replacement; supplies no current claim."""
        try:
            if self._guard.context() is None:
                self._selection.revoke()
            return copy.deepcopy(self._selection.snapshot)
        except BaseException:
            self.disconnect()
            raise

    def disconnect(self):
        self._selection.clear()
        self._guard.disconnect()
