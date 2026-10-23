"""Pure, serialized per-host reads of an admitted Mesh sync view.

Accept is O(1). Keyed reads materialize only the requested bodies; an explicit
all-row read uses the public order index and costs O(R). ``since`` reports the
public ChangeSet and reads its explicit changed identities, without expanding
receipt/cohort changes into N rows. Callers re-query visible/prior identities
when receipts or clocks change. Neither changes nor expiry retire presentation
context. ``snapshot`` is an explicit O(N) diagnostic export, never authority.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from mesh_plus.protocol import check
from mesh_plus.sync.cache import ChangeSet, ResyncRequired, ViewRef, source_binding
from mesh_plus.sync.canonical import canonical
from mesh_plus.sync.commitment import ABSENT, binding_digest
from mesh_plus.sync.model import SourceTag

from .contract import IDENTITY, identity_key, validate_shape
from .mesh_sync_profile import AgentSyncProfile
from .observation_support import SUPPORT_FIELDS
from .projection_fields import mask_fields
from .sync_commitment import native_binding_digest, value_hash
from .sync_contract import join_record
from .sync_native import descriptor
from .sync_projection_schema import SELECTOR

AgentIdentity = tuple[str, str, str, str, str]


@dataclass(frozen=True)
class AgentSyncExceptionContext:
    """Detached native exception, informational unless it is a current negative.

    ``kind`` is ``nonmember`` or ``uncertain``. Expired negatives remain their
    original type; they are never fabricated native UNCERTAIN decisions.
    Presentation retention of these values belongs to the caller.
    """

    identity: AgentIdentity
    kind: str
    fact: dict
    current: bool


@dataclass(frozen=True)
class AgentSyncRead:
    """Detached query output; no presentation-retirement implication.

    ``field_authority`` maps each materialized identity to exact current
    support flags. Admitted field health/value still decide whether that fact
    is known/positive; current support never turns an unknown fact into one.
    The map includes expired active bodies that were omitted from ``sessions``.
    ``scopes[*].currentComplete`` requires current exact completeness support.
    ``uncertain`` contains only native UNCERTAIN facts and has no authority.
    The opaque ``tag`` is the cursor accepted by the public ``changes`` API.
    """

    context: dict | None
    tag: SourceTag | None
    sessions: list[dict]
    field_authority: dict[AgentIdentity, dict[str, bool]]
    scopes: list[dict]
    nonmembers: list[dict]
    uncertain: list[dict]
    exception_context: tuple[AgentSyncExceptionContext, ...]
    changes: ChangeSet | ResyncRequired | None


def _plain(value):
    return value.materialize() if value is not ABSENT else ABSENT


def _identities(keys, host):
    check(type(keys) in {tuple, list} and len(keys) <= 4096, "agent_sync_read_keys")
    result, seen = [], set()
    for key in keys:
        check(type(key) in {tuple, list} and len(key) == 5, "agent_sync_read_identity")
        identity = dict(zip(IDENTITY["required"], key, strict=True))
        validate_shape(identity, IDENTITY)
        check(key[0] == host, "agent_sync_read_identity_host")
        key = tuple(key)
        check(key not in seen, "agent_sync_read_duplicate_identity")
        seen.add(key)
        result.append(key)
    return result


class PreparedAgentSyncRead:
    """No I/O, service ownership, body cache or presentation history.

    A failed read drops the accepted capability. Reader clock monotonicity is
    retained across disconnects; a different reader clock needs a new facade.
    Acquisition owns retired-owner guarding. This facade binds the currently
    proved incarnation exactly and enforces scope continuity within that owner.
    Whole active exceptions use the declared public scope index. Keyed and
    coverage-only (``keys=()``) reads perform no scope or order enumeration.
    """

    def __init__(self, profile, host, source):
        check(type(profile) is AgentSyncProfile, "agent_sync_read_profile")
        self.profile, self.host, self.source = profile, host, source
        self._source_binding = source_binding(host, source, profile.descriptor)
        self._source_digest = binding_digest(self._source_binding, native=False).hex()
        self._view = self._tag = None
        self._last_now = self._clock = self._incarnation = None
        self._scopes = {}

    def accept(self, view):
        try:
            check(type(view) is ViewRef, "agent_sync_read_view")
            tag = view.tag
            check(
                type(tag) is SourceTag and tag.binding == self._source_digest,
                "agent_sync_read_source_binding",
            )
            if self._tag is not None and self._tag.native.binding == tag.native.binding:
                check(
                    tag.native.generation >= self._tag.native.generation
                    and (tag.native.generation != self._tag.native.generation or tag == self._tag),
                    "agent_sync_read_generation",
                )
            self._view, self._tag = view, tag
        except BaseException:
            self.disconnect()
            raise
        return view

    def _binding(self, context, now, clock):
        check(
            type(now) is int and now >= 0 and (self._last_now is None or now >= self._last_now),
            "agent_sync_read_clock",
        )
        encoded_clock = canonical(clock)
        check(self._clock is None or self._clock == encoded_clock, "agent_sync_read_clock")
        check(
            context["status"] == "confirmed"
            and context["host"] == self.host
            and context["source"] == self.source
            and context["profile"] == self.profile.descriptor.profile_id
            and context["tag"] == self._tag.wire(),
            "agent_sync_read_binding",
        )
        binding = context["nativeBinding"]
        selected = descriptor(self.profile.view)
        check(
            all(
                binding[name] == selected[name]
                for name in ("protocol", "version", "schemaDigest", "view")
            )
            and binding["hostScope"] == self.host
            and native_binding_digest(binding) == self._tag.native.binding
            and binding["selector"] == (SELECTOR if self.profile.view == "active" else None),
            "agent_sync_read_native_binding",
        )
        check(
            all(
                context["ownerClock"][name] == binding[name]
                for name in ("bootId", "clockDomain", "ownerEpoch", "uid", "hostScope")
            ),
            "agent_sync_read_incarnation",
        )
        scopes = {
            (s["provider"], s["namespace"]): (s["contextGeneration"], None)
            for s in binding["sourceContexts"]
        }
        if self.profile.view == "active":
            continuity = {tuple(entry[:2]): entry[2] for entry in binding["scopeContinuity"]}
            check(set(continuity) == set(scopes), "agent_sync_read_continuity")
            scopes = {key: (value[0], continuity[key]) for key, value in scopes.items()}
        if self._incarnation == binding["ownerEpoch"]:
            for key, value in scopes.items():
                old = self._scopes.get(key)
                check(
                    old is None
                    or value[0] >= old[0]
                    and (
                        value[1] is None
                        or value[1] >= old[1]
                        and (value[0] == old[0] or value[1] > old[1])
                    ),
                    "agent_sync_read_continuity",
                )
        self._last_now, self._clock = now, encoded_clock
        self._incarnation, self._scopes = binding["ownerEpoch"], scopes
        return binding

    def _receipts(self, view, context, binding, now):
        receipts = {}
        check(len(context["receipts"]) <= 32, "agent_sync_read_receipts")
        for translated in context["receipts"]:
            key = tuple(translated["key"])
            original = _plain(view.lookup("receipts", list(key)))
            check(
                key not in receipts
                and original is not ABSENT
                and translated["valueHash"] == value_hash("receipts", original)
                and translated["accepted"] == original["accepted"]
                and translated["health"] == original["health"]
                and original["serviceId"] == binding["ownerEpoch"]
                and self._scopes[key[:2]][0] == original["contextGeneration"],
                "agent_sync_read_receipt_binding",
            )
            support = {
                "serviceId": original["serviceId"],
                "provider": key[0],
                "namespace": key[1],
                "contextGeneration": original["contextGeneration"],
                "component": key[2],
                **{
                    name: original[name]
                    for name in ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")
                },
            }
            deadline = translated["expiresMs"]
            current = (
                translated["current"] is True
                and original["accepted"] > 0
                and original["health"] in {"current", "partial"}
                and type(deadline) is int
                and now < deadline
            )
            receipts[key] = support, deadline if current else None
        return receipts

    def current(self, now_ms, clock, keys=None, since=None):
        try:
            if self._view is None:
                return AgentSyncRead(None, None, [], {}, [], [], [], (), None)
            view = self._view
            # This must precede every metadata/table/index inspection, including
            # complete-empty scopes and invalid caller clocks/keys.
            context = view.context(now_ms, clock)
            binding = self._binding(context, now_ms, clock)
            service = _plain(view.lookup("metadata", "service"))
            check(
                service is not ABSENT
                and all(
                    service[name] == binding[field]
                    for name, field in (
                        ("serviceId", "ownerEpoch"),
                        ("hostScope", "hostScope"),
                        ("uid", "uid"),
                        ("bootId", "bootId"),
                        ("clockDomain", "clockDomain"),
                    )
                ),
                "agent_sync_read_service",
            )
            ready = service["state"] == "ready"
            receipts = self._receipts(view, context, binding, now_ms)

            def support_deadline(support):
                if not ready or support is None:
                    return None
                key = (support["provider"], support["namespace"], support["component"])
                original = receipts.get(key)
                return original[1] if original is not None and original[0] == support else None

            def current_ref(ref):
                if not ready or ref is None or ref[0] != "cohort":
                    return False
                original = receipts.get(tuple(ref[1]))
                return original is not None and original[1] is not None

            changes = None if since is None else view.changes(since)
            if keys is not None:
                wanted = _identities(keys, self.host)
            elif isinstance(changes, ResyncRequired):
                wanted = []
            elif changes is not None:
                changed = {}
                for space, key, _removed in changes.keys:
                    identity = (
                        key
                        if space == "records"
                        else key[0]
                        if space == "observations"
                        else key[1]
                        if space == "memberships"
                        else key[3]
                        if space == "scopes" and len(key) == 4
                        else None
                    )
                    if identity is not None:
                        changed[tuple(identity)] = None
                wanted = _identities(list(changed), self.host)
            else:
                order = view.index("order")
                wanted = []
                for key in order.iter_keys():
                    check(len(wanted) < 4096, "agent_sync_read_capacity")
                    wanted.append(tuple(_plain(order.get(key))[0]))
            sessions, authority = [], {}
            for identity in wanted:
                slot = _plain(view.lookup("records", list(identity)))
                if slot is ABSENT:
                    continue
                observed = _plain(view.lookup("observations", [list(identity), slot["birth"]]))
                body = _plain(view.lookup("bodies", slot["body"]))
                check(body is not ABSENT and observed is not ABSENT, "agent_sync_read_record")
                row = join_record(body, observed["fields"])
                check(identity_key(row["identity"]) == identity, "agent_sync_read_record")
                fields = observed["supports"]
                flags = {field: current_ref(fields[field]) for field in SUPPORT_FIELDS}
                authority[identity] = flags
                if self.profile.view == "active":
                    member = view.lookup("scopes", [*identity[1:3], "members", list(identity)])
                    if (
                        member is ABSENT
                        or not flags["runtime"]
                        or row["runtime"]["value"] != "running"
                        or row["runtime"]["health"] != "current"
                        or row["kind"] != "unknown"
                        and not flags["kind"]
                    ):
                        continue
                sessions.append(mask_fields(row, fields, current_ref))

            scopes = []
            for scope, (generation, continuity) in self._scopes.items():
                raw = _plain(view.lookup("scopes", [*scope, "coverage"]))
                if raw is ABSENT:
                    continue
                coverage = copy.deepcopy(raw["coverage"])
                if self.profile.view == "active":
                    complete = (
                        ready
                        and coverage["status"] == "complete"
                        and bool(coverage["supports"])
                        and all(support_deadline(s) is not None for s in coverage["supports"])
                    )
                    if coverage["status"] == "complete" and not complete:
                        coverage.update(status="stale", reason="sync_support_expired")
                else:
                    for field in ("runtime", "saved"):
                        if (
                            coverage[field]["status"] == "complete"
                            and support_deadline(raw["supports"][field]) is None
                        ):
                            coverage[field].update(status="stale", reason="sync_support_expired")
                    complete = (
                        ready
                        and raw["censusStatus"] == "complete"
                        and all(
                            coverage[field]["status"] == "complete"
                            for field in ("runtime", "saved")
                        )
                    )
                scopes.append(
                    {
                        "hostScope": self.host,
                        "provider": scope[0],
                        "namespace": scope[1],
                        "contextGeneration": generation,
                        "continuity": continuity,
                        "coverage": coverage,
                        "currentComplete": complete,
                    }
                )

            nonmembers, uncertain, exception_context = [], [], []
            if self.profile.view == "active":
                if keys is None and since is None:
                    exception_keys = (
                        key
                        for scope in self._scopes
                        for kind in ("nonmembers", "uncertain")
                        for key in view.index("scope_keys").iter_keys(prefix=[*scope, kind])
                    )
                else:
                    exception_keys = (
                        [*identity[1:3], kind, list(identity)]
                        for identity in wanted
                        for kind in ("nonmembers", "uncertain")
                    )
                for key in exception_keys:
                    fact = _plain(view.lookup("scopes", key))
                    if fact is ABSENT:
                        continue
                    current = False
                    if key[2] == "nonmembers":
                        deadlines = [support_deadline(support) for support in fact["supports"]]
                        if deadlines and all(deadline is not None for deadline in deadlines):
                            # Both clocks can be unrelated. Attenuate each proved
                            # reader deadline by the original owner's horizon gap.
                            deadline = min(
                                deadline
                                - max(0, support["expiresBoottimeMs"] - fact["horizonBoottimeMs"])
                                for deadline, support in zip(
                                    deadlines, fact["supports"], strict=True
                                )
                            )
                            current = now_ms < deadline
                        if current:
                            nonmembers.append(copy.deepcopy(fact))
                    else:
                        uncertain.append(copy.deepcopy(fact))
                    exception_context.append(
                        AgentSyncExceptionContext(
                            tuple(key[3]),
                            "nonmember" if key[2] == "nonmembers" else "uncertain",
                            copy.deepcopy(fact),
                            current,
                        )
                    )
            return AgentSyncRead(
                copy.deepcopy(context),
                self._tag,
                sessions,
                authority,
                scopes,
                nonmembers,
                uncertain,
                tuple(exception_context),
                changes,
            )
        except BaseException:
            self.disconnect()
            raise

    def snapshot(self):
        """Explicit detached native diagnostic export; grants no authority."""
        try:
            return None if self._view is None else self._view.export_committed()
        except BaseException:
            self.disconnect()
            raise

    def disconnect(self):
        self._view = self._tag = None
