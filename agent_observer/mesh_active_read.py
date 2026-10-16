"""Prepared active reads with independent field and membership authority.

Only public Mesh guard methods are used. Retained owner headers are context;
each positive claim requires its exact original native support and Mesh's
translated deadline at the time of the read.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from mesh_plus import api as mesh_api
from mesh_plus.api import PreparedReadGuard
from mesh_plus.protocol import check

from .active_contract import ACTIVE_FEED_PROTOCOL, SELECTOR, SELECTOR_DIGEST, support_matches
from .active_feed import mask_fields
from .contract import canonical, identity_key
from .mesh_active_profile import (
    ACTIVE_PROFILE_ID,
    NATIVE_PROTOCOL,
    ActiveAgentPreparation,
    ActiveAgentProfile,
)

ACTIVE_READ_INTERFACE_VERSION = 1


@dataclass(frozen=True)
class ActiveAgentRead:
    context: dict | None
    members: list
    uncertain: list
    nonmembers: list
    scopes: list

    @property
    def sessions(self):
        return self.members


class PreparedActiveAgentWatch:
    """Serialized pure facade; callers own I/O, reconnect and UI context.

    EOF, liveness/framing failure, cancellation and output failure must call
    ``disconnect``. A new watch is required for reconnection. This object owns
    no presentation history and invents no retirement timeout.
    """

    def __init__(self, request_id, *, host_ids=None, profile=None, preparation=None):
        check(getattr(mesh_api, "ADMISSION_INTERFACE_VERSION", None) == 1
              and callable(getattr(PreparedReadGuard, "context", None)),
              "mesh_prepared_read_incompatible")
        profile = ActiveAgentProfile() if profile is None else profile
        check(profile.descriptor.profile_id == ACTIVE_PROFILE_ID, "profile_descriptor")
        preparation = ActiveAgentPreparation(profile) if preparation is None else preparation
        self._guard = PreparedReadGuard("agent", request_id, host_ids=host_ids,
                                        profile=profile, preparation=preparation)
        self._snapshot = None
        self._rows = {}
        self._scope_bindings = {}
        self._last_now = None

    def _retain(self, snapshot):
        if snapshot is None:
            self._snapshot, self._rows = None, {}
            return
        check(snapshot["protocol"] == ACTIVE_PROFILE_ID, "active_profile_binding")
        bindings = dict(self._scope_bindings)
        for host in snapshot["mesh"]["hosts"]:
            owner = host["owner"]
            if owner is None or owner["metadata"] is None:
                continue
            service = owner["service"]
            for scope in owner["metadata"]["scopes"]:
                key = host["hostId"], scope["provider"], scope["namespace"]
                incarnation = host["delivery"]["epoch"], service["serviceId"]
                current = incarnation, scope["contextGeneration"], scope["continuity"]
                previous = bindings.get(key)
                if previous is not None and previous[0] == incarnation:
                    check(current[1] >= previous[1]
                          and current[2] >= previous[2]
                          and (current[1] == previous[1] or current[2] > previous[2]),
                          "active_scope_continuity")
                bindings[key] = current
        self._scope_bindings = bindings
        # snapshot() is already a detached public export. These dictionaries
        # stay private and are copied/masked before returning any body.
        self._snapshot = snapshot
        self._rows = {identity_key(row["identity"]): row for row in snapshot["sessions"]}

    def accept(self, frame):
        try:
            self._guard.accept(frame)
            if isinstance(frame, dict) and frame.get("mesh", {}).get("kind") == "heartbeat":
                return frame
            self._retain(self._guard.snapshot())
        except BaseException:
            self.disconnect()
            raise
        return frame

    def _support_current(self, support, host, service, source, now):
        if (support is None or host["delivery"]["status"] != "ready"
                or host["viewState"] != "current"
                or not support_matches(support, source, service["serviceId"], service["emittedBoottimeMs"])):
            return False
        key = support["provider"] + ":" + support["namespace"], support["component"]
        receipt = next((r for r in host["receipts"]
                        if (r["sourceId"], r["component"]) == key), None)
        return (receipt is not None and receipt["accepted"] == support["accepted"]
                and receipt["health"] in {"current", "partial"}
                and type(receipt["expiresAtMs"]) is int and receipt["expiresAtMs"] > now)

    def _scope_ready(self, host, owner, scope):
        service = owner["service"]
        if (owner["protocol"] != NATIVE_PROTOCOL or owner["version"] != ACTIVE_FEED_PROTOCOL
                or service["hostScope"] != host["hostId"]
                or service["activeFeedProtocol"] != ACTIVE_FEED_PROTOCOL
                or canonical(service["selector"]) != canonical(SELECTOR)
                or service["selectorDigest"] != SELECTOR_DIGEST):
            return False
        key = host["hostId"], scope["provider"], scope["namespace"]
        return self._scope_bindings.get(key) == (
            (host["delivery"]["epoch"], service["serviceId"]),
            scope["contextGeneration"], scope["continuity"],
        )

    def read(self, now_ms, clock):
        try:
            # Required even for complete-empty scopes: this validates or revokes
            # the generic generation before any metadata is inspected.
            self._guard.current(now_ms, clock)
            current = self._guard.context()
            if current is None or self._snapshot is None:
                self._snapshot, self._rows = None, {}
                return ActiveAgentRead(None, [], [], [], [])
            check(type(now_ms) is int and (self._last_now is None or now_ms >= self._last_now),
                  "active_reader_clock_regression")
            self._last_now = now_ms
            check(current["protocol"] == ACTIVE_PROFILE_ID, "active_profile_binding")
            members, uncertain, nonmembers, scopes = [], [], [], []
            for host in current["mesh"]["hosts"]:
                owner = host["owner"]
                if owner is None or owner["metadata"] is None:
                    continue
                service = owner["service"]
                sources = {(s["provider"], s["namespace"]): s for s in service["sources"]}
                for scope in owner["metadata"]["scopes"]:
                    source = sources.get((scope["provider"], scope["namespace"]))
                    ready = (source is not None and self._scope_ready(host, owner, scope)
                             and scope["contextGeneration"] == source["contextGeneration"])

                    def valid(ref, *, ready=ready, host=host, service=service, source=source):
                        return ready and self._support_current(ref, host, service, source, now_ms)

                    coverage = copy.deepcopy(scope["coverage"])
                    if host["delivery"]["status"] != "ready" or not ready:
                        coverage.update(status="unavailable", reason="active_delivery_unavailable")
                    elif coverage["status"] == "complete" and (
                        not coverage["supports"] or not all(valid(ref) for ref in coverage["supports"])
                    ):
                        coverage.update(status="stale", reason="active_support_expired")
                    scopes.append({
                        "hostScope": host["hostId"], "serviceId": service["serviceId"],
                        **{key: scope[key] for key in (
                            "provider", "namespace", "contextGeneration", "continuity",
                        )},
                        "coverage": coverage,
                    })
                    if not ready:
                        continue
                    # Informational identities carry no positive runtime or
                    # absence authority. Presentation retention is external.
                    uncertain.extend(copy.deepcopy(scope["uncertain"]))
                    for entry in scope["members"]:
                        row = self._rows.get(identity_key(entry["identity"]))
                        if row is None:
                            continue
                        fields = entry["fieldSupports"]
                        if (not valid(fields["runtime"])
                                or row["kind"] != "unknown" and not valid(fields["kind"])):
                            continue
                        members.append(mask_fields(row, fields, valid))
                    for entry in scope["nonmembers"]:
                        if entry["supports"] and all(valid(ref) for ref in entry["supports"]):
                            nonmembers.append(copy.deepcopy(entry))
            return ActiveAgentRead(copy.deepcopy(current["mesh"]), members, uncertain, nonmembers, scopes)
        except BaseException:
            self.disconnect()
            raise

    def snapshot(self):
        """Detached admitted replacement, informational regardless of expiry."""
        try:
            if self._guard.context() is None:
                self._snapshot, self._rows = None, {}
            return copy.deepcopy(self._snapshot)
        except BaseException:
            self.disconnect()
            raise

    def disconnect(self):
        self._snapshot, self._rows = None, {}
        self._scope_bindings = {}
        self._last_now = None
        self._guard.disconnect()
