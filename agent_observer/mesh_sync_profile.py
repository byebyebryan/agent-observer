"""Pure logical Agent sync admission against Mesh's public staging interface.

This draft admits material state only.  It does not confer current authority,
implement compact wire normalization, or export through private cache objects.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from mesh_plus.protocol import check
from mesh_plus.sync.canonical import Atom, canonical
from mesh_plus.sync.commitment import ABSENT
from mesh_plus.sync.model import (
    DomainIndexPatch,
    FieldTokenWrite,
    HeadRules,
    IndexRemove,
    IndexSpec,
    IndexWrite,
    OriginalReceipt,
    SyncDescriptor,
)

from .active_contract import FACT_SUPPORT, MAX_LEDGER_BYTES, NONMEMBER, UNCERTAIN
from .active_contract import SCOPE as ACTIVE_SCOPE
from .contract import (
    IDENTITY,
    SNAPSHOT,
    identity_key,
    validate_shape,
)
from .observation_support import SUPPORT_FIELDS, support_matches
from .service_contract import SOURCE as SERVICE_SOURCE
from .sync_commitment import field_token, native_binding_digest, value_hash
from .sync_contract import OBSERVATIONS, admit_record, join_record
from .sync_native import (
    COHORT,
    MAX_HEAD_BYTES,
    RECEIPT,
    TABLES,
    validate_message,
)
from .sync_native import (
    descriptor as native_descriptor,
)

FULL_PROFILE_ID = "agent-observer.mesh-sync.v1"
ACTIVE_PROFILE_ID = "agent-observer.mesh-active-sync.v1"


def _plain(value):
    if value is ABSENT:
        return ABSENT
    materialize = getattr(value, "materialize", None)
    return materialize() if materialize is not None else value


def _key(value):
    return canonical(value)


def _closed(value, keys, code):
    check(type(value) is dict and set(value) == set(keys), code)


def _identity(value, binding):
    check(type(value) is list and len(value) == 5, "agent_sync_identity")
    shaped = dict(zip(IDENTITY["required"], value, strict=True))
    validate_shape(shaped, IDENTITY)
    check(value[0] == binding["hostScope"], "agent_sync_identity_scope")
    return shaped


def _integer(value, minimum=0, maximum=2**64 - 1):
    return type(value) is int and minimum <= value <= maximum


def _receipt_key(value):
    check(type(value) is list and len(value) == 3 and all(type(v) is str for v in value),
          "agent_sync_receipt_key")
    return tuple(value)


def _spec(name, key, value, *, maximum=36864, ordered=False):
    return IndexSpec(name, canonical(key), canonical(value), max_entries=maximum,
                     max_value_bytes=16384, ordered=ordered)


def _tuple_schema(*items):
    return {"type": "array", "minItems": len(items), "maxItems": len(items),
            "prefixItems": list(items), "items": False}


_COUNT = {"type": "integer", "minimum": 0, "maximum": 2**64 - 1}
_IDENTITY = _tuple_schema(*(IDENTITY["properties"][name] for name in IDENTITY["required"]))
_SCOPE = _tuple_schema(*(_IDENTITY["prefixItems"][i] for i in (1, 2)))
_BIRTH = _tuple_schema({"type": "string", "format": "uuid"}, {**_COUNT, "minimum": 1})
_REF = _tuple_schema(_IDENTITY, _BIRTH)
_RECEIPT_KEY = _tuple_schema(*_SCOPE["prefixItems"], {"enum": ["runtime", "history"]})
_SCOPE_KEY = {"anyOf": [
    _tuple_schema(*_SCOPE["prefixItems"], {"const": "coverage"}),
    _tuple_schema(*_SCOPE["prefixItems"], {"enum": ["members", "nonmembers", "uncertain"]}, _IDENTITY),
]}


def _counts(*names):
    return {"type": "object", "additionalProperties": False,
            "properties": dict.fromkeys(names, _COUNT)}


INDEX_SPECS = (
    _spec("aliases", {**_COUNT, "minimum": 1}, _REF, maximum=4096),
    _spec("order", _tuple_schema({"type": "integer", "minimum": 0, "maximum": 1}, _IDENTITY),
          _REF, maximum=4096, ordered=True),
    _spec("row_rules", _REF, {"type": "integer", "minimum": 0, "maximum": 65535}, maximum=4096),
    _spec("scope_stats", _SCOPE, _counts("records", "members", "nonmembers", "uncertain"), maximum=2),
    _spec("capability_counts", _tuple_schema(*_SCOPE["prefixItems"],
          {"enum": ["lastUpdated", "latestTurn"]}), _COUNT, maximum=4),
    _spec("scope_sizes", _SCOPE, _counts("members", "nonmembers", "uncertain"), maximum=2),
    _spec("support_counts", _RECEIPT_KEY, _COUNT, maximum=32),
    _spec("scope_keys", _SCOPE_KEY, {"type": "null"}, maximum=8192, ordered=True),
)

# Stable content was fully admitted once.  These bits preserve precisely the
# stable predicates that can interact with the moved observation paths; they
# do not copy body text, native timing values or another per-field graph.
_RUNTIME_KNOWN = 1 << 0
_RUNNING = 1 << 1
_PHASE = 1 << 2
_PHASE_KNOWN = 1 << 3
_OUTCOME_KNOWN = 1 << 4
_ACTIVITY = 1 << 5
_LAST_ACTIVITY = 1 << 6
_UPDATED_SOURCE = 1 << 7
_UPDATED_VALUE = 1 << 8
_UPDATED_LAST = 1 << 9
_TURN_SOURCE = 1 << 10
_TURN_VALUE = 1 << 11
_TURN_LAST = 1 << 12
_WORKSPACE = 1 << 13
_KIND = 1 << 14
_SELECTED = 1 << 15


def _row_rule(row):
    flags = (
        (_RUNTIME_KNOWN, row["runtime"]["value"] != "unknown"),
        (_RUNNING, row["runtime"]["value"] == "running"),
        (_PHASE, row["phase"] is not None),
        (_PHASE_KNOWN, row["phase"] is not None and row["phase"]["value"] != "unknown"),
        (_OUTCOME_KNOWN, row["outcome"]["value"] != "unknown"),
        (_ACTIVITY, row["activity"]["at"] is not None),
        (_LAST_ACTIVITY, row["activity"].get("lastKnownAt") is not None),
        (_UPDATED_SOURCE, row["lastUpdated"]["source"] is not None),
        (_UPDATED_VALUE, row["lastUpdated"]["at"] is not None),
        (_UPDATED_LAST, "lastKnownAt" in row["lastUpdated"]),
        (_TURN_SOURCE, row["latestTurn"]["source"] is not None),
        (_TURN_VALUE, row["latestTurn"]["value"] is not None),
        (_TURN_LAST, "lastKnownValue" in row["latestTurn"]),
        (_WORKSPACE, row["workspace"] is not None and row["workspace"]["health"] == "current"),
        (_KIND, row["kind"] != "unknown"),
        (_SELECTED, row["kind"] in {"user", "unknown"}),
    )
    return sum(bit for bit, present in flags if present)


def _observation_rule(fields, rule, source):
    """Admit changed facets using already-admitted stable predicates only."""
    validate_shape(fields, OBSERVATIONS)
    check(("phase" in fields) == bool(rule & _PHASE), "sync_phase_split")
    for name, bit in (("runtime", _RUNTIME_KNOWN), ("phase", _PHASE_KNOWN)):
        if rule & bit:
            check(fields[name]["health"] == "current" and fields[name]["observedAt"] is not None,
                  "missing_evidence_provenance")
    check(not rule & _OUTCOME_KNOWN or fields["outcome"]["health"] == "current",
          "missing_evidence_provenance")
    check(not rule & _ACTIVITY or fields["activity"]["health"] == "current",
          "missing_activity_provenance")
    check(not rule & _LAST_ACTIVITY or fields["activity"]["health"] == "stale",
          "invalid_last_known_activity")
    if rule & _PHASE_KNOWN:
        check(fields["phase"]["observedAt"] == fields["runtime"]["observedAt"],
              "phase_runtime_conflict")
    for name, source_bit, value_bit, last_bit in (
        ("lastUpdated", _UPDATED_SOURCE, _UPDATED_VALUE, _UPDATED_LAST),
        ("latestTurn", _TURN_SOURCE, _TURN_VALUE, _TURN_LAST),
    ):
        facet = fields[name]
        if facet["health"] == "current":
            check(rule & source_bit and facet["observedAt"] is not None,
                  "missing_timing_provenance")
            check(source["capabilities"]["timing"][name], "timing_capability_missing")
        else:
            check(not rule & value_bit, "invalid_current_timing")
        if rule & last_bit:
            check(facet["health"] == "stale" and facet["observedAt"] is not None,
                  "invalid_last_known_timing")
        receipt = facet["receipt"]
        check(receipt is None or facet["observedAt"] is not None and
              receipt["observedBoottimeMs"] >= receipt["sampledBoottimeMs"],
              "invalid_timing_receipt")


class _Patch:
    def __init__(self, ctx):
        self.ctx, self.values, self.tokens = ctx, {}, {}

    def get(self, name, key):
        marker = name, _key(key)
        if marker in self.values:
            return self.values[marker][1]
        return _plain(self.ctx.index(name).get(key))

    def put(self, name, key, value):
        old = self.get(name, key)
        if old is ABSENT or old != value:
            self.values[name, _key(key)] = key, value

    def remove(self, name, key):
        if self.get(name, key) is not ABSENT:
            self.values[name, _key(key)] = key, ABSENT

    def add(self, name, key, amount):
        old = self.get(name, key)
        value = (0 if old is ABSENT else old) + amount
        check(_integer(value), "agent_sync_index_count")
        self.put(name, key, value)

    def result(self, scopes):
        writes, removes = [], []
        for (name, _), (key, value) in self.values.items():
            if value is ABSENT:
                removes.append(IndexRemove(name, key))
            else:
                writes.append(IndexWrite(name, key, value))
        return DomainIndexPatch(writes=tuple(writes), removes=tuple(removes),
                                field_tokens=tuple(self.tokens.values()),
                                affected_scopes=tuple(scopes))


@dataclass(frozen=True, init=False)
class AgentSyncProfile:
    """Explicit unqualified profile for one full or active native descriptor.

    ``profile_schema_digest`` must be supplied while the packaged Mesh lock is
    pending.  Construction cannot imply packaged/profile/runtime acceptance.
    """

    descriptor: SyncDescriptor
    view: str

    def __init__(self, *, profile_schema_digest, view="full", native=None):
        check(view in {"full", "active"}, "agent_sync_view")
        selected = native_descriptor(view)
        if native is not None:
            check(canonical(native) == canonical(selected), "agent_sync_native_descriptor")
        object.__setattr__(self, "view", view)
        object.__setattr__(self, "descriptor", SyncDescriptor(
            FULL_PROFILE_ID if view == "full" else ACTIVE_PROFILE_ID,
            profile_schema_digest, selected["protocol"], selected["version"],
            selected["schemaDigest"], canonical(selected), indexes=INDEX_SPECS,
        ))

    def admit_baseline(self, ctx):
        check(ctx.base_tag is None, "agent_sync_baseline_context")
        return self._admit(ctx)

    def stage_delta(self, ctx):
        check(ctx.base_tag is not None, "agent_sync_delta_context")
        check(ctx.proposed_tag.generation == ctx.base_tag.generation + 1,
              "agent_sync_transaction_generation")
        return self._admit(ctx)

    def check_head(self, ctx, head):
        """Restrict a proof's exact original receipts; never mint authority."""
        check(ctx is not None and ctx.descriptor is self.descriptor, "agent_sync_commit_context")
        # Public refs currently have no encoded-size/pre-copy budget operation.
        # Head/native-binding ceilings provide an explicit conservative staging
        # envelope here; a future size seam must replace this before profiling
        # can claim precise public materialization allocation accounting.
        with ctx.budget.reserve(16 * (MAX_HEAD_BYTES + 16 * 1024)):
            original = _plain(head)
            binding = _plain(ctx.binding)
            validate_message(original, self.view, binding["hostScope"])
            check(original["kind"] == "head" and
                  original["tag"] == ctx.tag.native.wire() and
                  original["nativeBindingDigest"] == native_binding_digest(binding),
                  "agent_sync_head_tag")
            clock = original["ownerClock"]
            check(all(clock[key] == binding[key] for key in
                      ("bootId", "clockDomain", "uid", "hostScope", "ownerEpoch")),
                  "agent_sync_head_clock")
            check(_plain(ctx.original_receipts) == original["originalReceipts"],
                  "agent_sync_head_receipts")
            expected = {(*scope, component)
                        for scope in ((s["provider"], s["namespace"]) for s in binding["sourceContexts"])
                        for component in ("runtime", "history")}
            receipts = {_receipt_key(key): value for key, value in original["originalReceipts"]}
            cohorts = {_receipt_key(key): value for key, value in original["cohortHeads"]}
            check(len(expected) <= 32 and set(receipts) == expected, "agent_sync_head_receipt_coverage")
            projected = []
            for key, receipt in receipts.items():
                admitted = _plain(ctx.view.lookup("receipts", list(key)))
                check(admitted is not ABSENT and admitted == receipt, "agent_sync_head_receipt_match")
                cohort = _plain(ctx.view.lookup("cohorts", list(key)))
                claimed = cohorts.get(key, ABSENT)
                if cohort is ABSENT:
                    check(claimed is ABSENT, "agent_sync_head_cohort_match")
                else:
                    check(claimed is not ABSENT and cohort == {**claimed, "receipt": list(key)},
                          "agent_sync_head_cohort_match")
                projected.append(OriginalReceipt(Atom.own(list(key)), value_hash("receipts", receipt),
                                                  receipt["accepted"], receipt["health"],
                                                  receipt["expiresBoottimeMs"]))
            check(set(cohorts) <= expected, "agent_sync_head_cohort_coverage")
            service = ctx.view.lookup("metadata", "service")
            allowed = None if service["state"] == "ready" else ()
            return HeadRules(tuple(projected), allowed_receipts=allowed)

    def export_committed(self, view):
        """Explicit detached O(N) diagnostics, retaining original native bytes.

        This performs no clock query and grants no current-field, membership,
        negative or completeness authority, including after original expiry.
        """
        check(view is not None and callable(getattr(view, "lookup", None)), "agent_sync_export_view")
        name = "snapshot" if self.view == "full" else "projection"
        header = _plain(view.lookup("metadata", name))
        check(header is not ABSENT, "agent_sync_export_metadata")
        if header is None:
            return None
        rows = []
        order = view.index("order")
        for key in order.iter_keys():
            ref = _plain(order.get(key))
            slot = _plain(view.lookup("records", ref[0]))
            check(slot is not ABSENT and slot["birth"] == ref[1], "agent_sync_export_record")
            body = _plain(view.lookup("bodies", slot["body"]))
            observed = _plain(view.lookup("observations", ref))
            check(body is not ABSENT and observed is not ABSENT, "agent_sync_export_record")
            rows.append(join_record(body, observed["fields"]))
        if self.view == "full":
            return {**header, "sessions": rows}
        scope_order = _plain(view.lookup("metadata", "scopeOrder"))
        scopes = {tuple(key): {"provider": key[0], "namespace": key[1],
                               "members": [], "uncertain": [], "nonmembers": []}
                  for key in scope_order}
        supports = {}
        for key in view.index("scope_keys").iter_keys():
            value = _plain(view.lookup("scopes", key))
            scope = scopes[tuple(key[:2])]
            if key[2] == "coverage":
                scope.update(value)
            elif key[2] == "members":
                fields = {}
                for field, cohort in value["fields"].items():
                    if cohort is None:
                        fields[field] = None
                    else:
                        cohort_key = tuple(cohort)
                        if cohort_key not in supports:
                            receipt = _plain(view.lookup("receipts", cohort))
                            supports[cohort_key] = {"serviceId": receipt["serviceId"], "provider": cohort[0],
                                             "namespace": cohort[1], "contextGeneration": receipt["contextGeneration"],
                                             "component": cohort[2], **{name: receipt[name] for name in
                                                 ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")}}
                        fields[field] = dict(supports[cohort_key])
                scope["members"].append({"identity": value["identity"], "fieldSupports": fields})
            else:
                scope[key[2]].append(value)
        result = []
        for key in scope_order:
            scope = scopes[tuple(key)]
            for kind in ("members", "nonmembers", "uncertain"):
                scope[kind].sort(key=lambda value: identity_key(value["identity"]))
            result.append(scope)
        return {**header, "sessions": rows, "scopes": result}

    def _admit(self, ctx):
        check(ctx.descriptor is self.descriptor, "agent_sync_descriptor_instance")
        # Public materialization is explicit. Reserve conservative staging for
        # operation descriptors before detached changed-value copies are made.
        ctx.budget.charge(2048 + len(ctx.operations) * 384)
        operations = []
        for op in ctx.operations:
            key, value = _plain(op.key), _plain(op.value)
            ctx.budget.charge(len(canonical([key, value])) * 6 + 256)
            operations.append((op.space, op.op, key, value))
        binding = _plain(ctx.binding)
        empty = {name: [] for name in TABLES}
        validate_message({"kind": "baseline", "descriptor": native_descriptor(self.view),
                          "nativeBinding": binding, "tag": ctx.proposed_tag.wire(),
                          "cursor": [binding["ownerEpoch"], ctx.proposed_tag.generation,
                                     ctx.proposed_tag.root], "tables": empty}, self.view,
                         binding["hostScope"])
        sources, validation, metadata = self._metadata(ctx, binding, operations)
        receipts = self._receipts(ctx, binding, sources, operations)
        self._cohorts(ctx, receipts, operations)
        patch = _Patch(ctx)
        affected, changed_bodies, changed_observations = {}, {}, {}
        for space, op, key, value in operations:
            if space == "records":
                identity = key
            elif space == "bodies":
                changed_bodies[key] = value if op == "put" else ABSENT
                if op == "remove":
                    previous = ctx.before.lookup("bodies", key)
                    check(previous is not ABSENT, "agent_sync_removed_body")
                    # Only a removed body's identity projection is needed;
                    # unchanged bodies are never fetched or materialized.
                    identity = list(identity_key(_plain(previous["identity"])))
                else:
                    check(type(value) is dict and "identity" in value, "agent_sync_body")
                    identity = list(identity_key(value["identity"]))
            elif space == "observations":
                check(type(key) is list and len(key) == 2, "agent_sync_observation_key")
                identity = key[0]
                changed_observations[_key(key)] = value if op == "put" else ABSENT
            elif space == "memberships":
                check(type(key) is list and len(key) == 4, "agent_sync_membership_key")
                _receipt_key(key[0])
                check(key[3] in SUPPORT_FIELDS, "agent_sync_membership_field")
                identity = key[1]
            elif space == "scopes":
                check(type(key) is list and len(key) in {3, 4}, "agent_sync_scope_key")
                if len(key) == 3:
                    continue
                identity = key[3]
            else:
                continue
            _identity(identity, binding)
            check(tuple(identity[1:3]) in sources, "agent_sync_record_source")
            affected[_key(identity)] = identity
        previous_slots = {}
        for encoded, identity in affected.items():
            old = _plain(ctx.before.lookup("records", identity))
            previous_slots[encoded] = old
            if old is not ABSENT and ctx.after.lookup("records", identity) is ABSENT:
                patch.remove("aliases", old["alias"])
                patch.remove("order", old["order"] if self.view == "full" else [0, identity])
        for encoded, identity in affected.items():
            slot = _plain(ctx.after.lookup("records", identity))
            old = previous_slots[encoded]
            if slot is ABSENT:
                if old is not ABSENT:
                    self._removed(ctx, patch, identity, old)
                continue
            self._slot(slot, identity, old, binding, ctx.proposed_tag.generation,
                       baseline=ctx.base_tag is None)
            if old is not ABSENT and slot["body"] != old["body"]:
                check(ctx.after.lookup("bodies", old["body"]) is ABSENT,
                      "agent_sync_replaced_body_retained")
            ref = [identity, slot["birth"]]
            if old is ABSENT:
                existing = patch.get("aliases", slot["alias"])
                check(existing is ABSENT or existing == ref, "agent_sync_duplicate_reference")
                patch.put("aliases", slot["alias"], ref)
            observed = self._observed(ctx, ref, changed_observations)
            check(observed is not ABSENT, "agent_sync_dangling_record")
            _closed(observed, ("fields", "supports"), "agent_sync_observation")
            check(type(observed["supports"]) is dict and
                  set(observed["supports"]) == set(SUPPORT_FIELDS), "agent_sync_field_supports")
            body = changed_bodies.get(slot["body"], ABSENT)
            body_changed = body is not ABSENT
            if body_changed:
                row, values = admit_record(body, observed["fields"], binding["hostScope"], validation)
                check(list(identity_key(row["identity"])) == identity, "agent_sync_body_identity")
                rule = _row_rule(row)
                patch.put("row_rules", ref, rule)
            else:
                check(old is not ABSENT and slot["body"] == old["body"], "agent_sync_unadmitted_body")
                rule = patch.get("row_rules", ref)
                check(rule is not ABSENT, "agent_sync_row_rule_missing")
                _observation_rule(observed["fields"], rule, validation[tuple(identity[1:3])])
            check(canonical(slot["order"]) == canonical([int(not rule & _RUNNING), identity]),
                  "agent_sync_order_key")
            if old is ABSENT or old["order"] != slot["order"]:
                # The active contract currently admits one configured scope;
                # its source ordinal is therefore exactly zero. Full order
                # keeps the reviewed runtime group then five-part identity.
                if old is not ABSENT:
                    patch.remove("order", old["order"] if self.view == "full" else [0, identity])
                patch.put("order", slot["order"] if self.view == "full" else [0, identity], ref)
            previous_observed = (None if old is ABSENT else
                                 _plain(ctx.before.lookup("observations", [identity, old["birth"]])))
            for field in SUPPORT_FIELDS:
                support_ref = observed["supports"][field]
                current = type(support_ref) is list and len(support_ref) == 2 and support_ref[0] == "cohort"
                old_token = ctx.field_token(ref, field) if body_changed or current else None
                if body_changed:
                    token = field_token(self.descriptor.native_descriptor_digest, identity, slot["birth"],
                                        field, values[field])
                    if old_token is ABSENT or old_token != token:
                        patch.tokens[_key(ref), field] = FieldTokenWrite(ref, field, token)
                else:
                    check(not current or old_token is not ABSENT, "agent_sync_field_token_missing")
                    token = old_token
                previous_ref = None if previous_observed is None else previous_observed["supports"][field]
                self._field(ctx, binding, sources, receipts, identity, slot["birth"],
                            field, observed["supports"][field], token, previous_ref)
            for name in ("lastUpdated", "latestTurn"):
                support = observed["supports"][name]
                if observed["fields"][name]["health"] != "current" or support is None or support[0] != "cohort":
                    continue
                original = observed["fields"][name]["receipt"]
                receipt = receipts[tuple(support[1])]
                check(original is not None and original["component"] == support[1][2]
                      and original["contextGeneration"] == receipt["contextGeneration"]
                      and original["sampledBoottimeMs"] == receipt["sampledBoottimeMs"]
                      and receipt["sampledBoottimeMs"] <= original["observedBoottimeMs"]
                      < receipt["expiresBoottimeMs"], "agent_sync_timing_support")
            self._capabilities(patch, identity, None if previous_observed is None else
                               previous_observed["fields"], observed["fields"])
            if self.view == "active":
                check(rule & _RUNNING and observed["fields"]["runtime"]["health"] == "current"
                      and rule & _SELECTED, "agent_sync_active_member")
                refs = observed["supports"]
                check(refs["runtime"] == ["cohort", [*identity[1:3], "runtime"]],
                      "agent_sync_active_runtime_support")
                if rule & _KIND:
                    check(refs["kind"] is not None and refs["kind"][0] == "cohort",
                          "agent_sync_active_kind_support")
                required = {
                    "phase": bool(rule & _PHASE_KNOWN),
                    "activity": bool(rule & _ACTIVITY),
                    "outcome": bool(rule & _OUTCOME_KNOWN),
                    "workspace": bool(rule & _WORKSPACE),
                    "lastUpdated": observed["fields"]["lastUpdated"]["health"] == "current",
                    "latestTurn": observed["fields"]["latestTurn"]["health"] == "current",
                }
                check(all(not needed or refs[field] is not None and refs[field][0] == "cohort"
                          for field, needed in required.items()), "agent_sync_active_field_support")
                check(not required["phase"] or refs["phase"] == refs["runtime"],
                      "agent_sync_active_phase_support")
                member = _plain(ctx.after.lookup("scopes", [*identity[1:3], "members", identity]))
                check(member is not ABSENT, "agent_sync_active_member_missing")
                self._scope_fact(ctx, binding, sources, [*identity[1:3], "members", identity], member,
                                 observed=observed)
        for space, op, key, _value in operations:
            if space != "memberships" or op != "put":
                continue
            slot = _plain(ctx.after.lookup("records", key[1]))
            check(slot is not ABSENT and slot["birth"] == key[2], "agent_sync_orphan_membership")
            observed = self._observed(ctx, key[1:3], changed_observations)
            check(observed["supports"].get(key[3]) == ["cohort", key[0]],
                  "agent_sync_unreferenced_membership")
        for digest, body in changed_bodies.items():
            if body is ABSENT:
                continue
            identity = list(identity_key(body["identity"]))
            slot = _plain(ctx.after.lookup("records", identity))
            check(slot is not ABSENT and slot["body"] == digest, "agent_sync_orphan_body")
        for space, _, ref, _ in operations:
            if space == "observations":
                actual = changed_observations[_key(ref)]
                slot = _plain(ctx.after.lookup("records", ref[0]))
                check(actual is ABSENT or slot is not ABSENT and slot["birth"] == ref[1],
                      "agent_sync_orphan_observation")
        scopes = self._scopes(ctx, binding, sources, receipts, metadata, operations, patch)
        for key, source in validation.items():
            for field in ("lastUpdated", "latestTurn"):
                count = patch.get("capability_counts", [*key, field])
                check(source["capabilities"]["timing"][field] or count is ABSENT or count == 0,
                      "timing_capability_missing")
        return patch.result(scopes)

    def _observed(self, ctx, ref, changed):
        key = _key(ref)
        return changed[key] if key in changed else _plain(ctx.after.lookup("observations", ref))

    def _metadata(self, ctx, binding, operations):
        names = {"service", "snapshot"} if self.view == "full" else {
            "service", "projection", "scopeOrder", "validationSources"}
        check(all(space != "metadata" or type(key) is str and key in names for space, _, key, _ in operations),
              "agent_sync_metadata_key")
        metadata = {name: _plain(ctx.after.lookup("metadata", name)) for name in names}
        check(all(value is not ABSENT for value in metadata.values()), "agent_sync_metadata_missing")
        service = metadata["service"]
        _closed(service, ("serviceId", "bootId", "uid", "hostScope", "viewRevision", "state",
                          "clockDomain", "sources"), "agent_sync_service")
        check(all(service[k] == binding[b] for k, b in (
            ("serviceId", "ownerEpoch"), ("bootId", "bootId"), ("uid", "uid"),
            ("hostScope", "hostScope"), ("clockDomain", "clockDomain"))), "agent_sync_service_binding")
        check(type(service["uid"]) is int and _integer(service["viewRevision"])
              and service["state"] in {"warming", "ready"},
              "agent_sync_service_state")
        contexts = {(s["provider"], s["namespace"]): s for s in binding["sourceContexts"]}
        sources = {}
        check(type(service["sources"]) is list and len(service["sources"]) == len(contexts),
              "agent_sync_sources")
        for source in service["sources"]:
            validate_shape(source, SERVICE_SOURCE)
            key = source["provider"], source["namespace"]
            check(key in contexts and key not in sources and
                  all(source[k] == contexts[key][k] for k in source if k != "components"),
                  "agent_sync_source_binding")
            check(len(source["components"]) == 2 and
                  {r["name"] for r in source["components"]} == {"runtime", "history"},
                  "agent_sync_components")
            sources[key] = source
        validation = {}
        if self.view == "full":
            header = metadata["snapshot"]
            check((header is None) == (service["state"] == "warming"), "agent_sync_readiness")
            if header is not None:
                spec = copy.deepcopy(SNAPSHOT)
                del spec["properties"]["sessions"]
                spec["required"].remove("sessions")
                validate_shape(header, spec)
                check(header["host"]["authority"] == binding["hostScope"] and
                      header["host"]["uid"] == binding["uid"], "agent_sync_snapshot_host")
                validation = {(s["provider"], s["namespace"]): s for s in header["sources"]}
                check(len(validation) == len(header["sources"]) and set(validation) == set(sources),
                      "agent_sync_snapshot_sources")
                for key, source in validation.items():
                    check(all(source[k] == sources[key][k] for k in
                              ("provider", "namespace", "configHome", "configHomeKind")),
                          "agent_sync_snapshot_source")
        else:
            check(metadata["projection"] in (None, {}) and
                  (metadata["projection"] is None) == (service["state"] == "warming"),
                  "agent_sync_projection_metadata")
            order = metadata["scopeOrder"]
            check(type(order) is list and len(order) <= 1 and
                  len({_key(k) for k in order}) == len(order) and
                  (not order if metadata["projection"] is None else
                   set(map(tuple, order)) == set(sources)), "agent_sync_scope_order")
            check(type(metadata["validationSources"]) is list, "agent_sync_validation_sources")
            for source in metadata["validationSources"]:
                _closed(source, ("provider", "namespace", "capabilities"), "agent_sync_validation_source")
                key = source["provider"], source["namespace"]
                _closed(source["capabilities"], ("timing",), "agent_sync_capabilities")
                _closed(source["capabilities"]["timing"], ("lastUpdated", "latestTurn"), "agent_sync_capabilities")
                check(key in sources and key not in validation and
                      all(type(v) is bool for v in source["capabilities"]["timing"].values()),
                      "agent_sync_validation_source")
                validation[key] = source
        return sources, validation, metadata

    def _receipts(self, ctx, binding, sources, operations):
        expected = {(*scope, name) for scope in sources for name in ("runtime", "history")}
        check(all(space != "receipts" or _receipt_key(key) in expected for space, _, key, _ in operations),
              "agent_sync_receipt_key")
        receipts = {}
        validator = Draft202012Validator(RECEIPT)
        for key in expected:
            value = _plain(ctx.after.lookup("receipts", list(key)))
            check(value is not ABSENT, "agent_sync_receipt_missing")
            validator.validate(value)
            source = sources[key[:2]]
            original = next(c for c in source["components"] if c["name"] == key[2])
            check(value == {"serviceId": binding["ownerEpoch"],
                            "contextGeneration": source["contextGeneration"], **original},
                  "agent_sync_receipt_binding")
            sample, expiry = value["sampledBoottimeMs"], value["expiresBoottimeMs"]
            check((sample is None) == (expiry is None) and
                  (sample is None or sample <= expiry) and
                  (value["health"] not in {"current", "partial"} or
                   sample is not None and sample < expiry and value["accepted"] > 0),
                  "agent_sync_receipt_clock")
            old = _plain(ctx.before.lookup("receipts", list(key)))
            if old is not ABSENT:
                check(value["accepted"] >= old["accepted"] and
                      (old["sampledBoottimeMs"] is None or sample is not None and sample >= old["sampledBoottimeMs"]),
                      "agent_sync_receipt_regression")
                if value["accepted"] == old["accepted"]:
                    check(all(value[k] == old[k] for k in ("sampledBoottimeMs", "expiresBoottimeMs")),
                          "agent_sync_receipt_renewal_without_accept")
            receipts[key] = value
        return receipts

    def _cohorts(self, ctx, receipts, operations):
        check(all(space != "cohorts" or _receipt_key(key) in receipts for space, _, key, _ in operations),
              "agent_sync_cohort_key")
        validator = Draft202012Validator(COHORT)
        for key, receipt in receipts.items():
            value = _plain(ctx.after.lookup("cohorts", list(key)))
            usable = receipt["accepted"] > 0 and receipt["sampledBoottimeMs"] is not None
            check((value is not ABSENT) == usable, "agent_sync_cohort_missing")
            if value is ABSENT:
                continue
            validator.validate(value)
            check(value["receipt"] == list(key) and all(value[k] == receipt[k] for k in
                  ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")), "agent_sync_cohort_receipt")
            old = _plain(ctx.before.lookup("cohorts", list(key)))
            if old is not ABSENT:
                changed_set = value["seal"][1:] != old["seal"][1:]
                check(value["seal"][0] == (ctx.proposed_tag.generation if changed_set else old["seal"][0]),
                      "agent_sync_seal_generation")

    def _slot(self, slot, identity, old, binding, generation, *, baseline):
        _closed(slot, ("birth", "alias", "body", "order", "scope"), "agent_sync_slot")
        birth = slot["birth"]
        check(type(birth) is list and len(birth) == 2 and birth[0] == binding["ownerEpoch"]
              and _integer(birth[1], 1, generation) and _integer(slot["alias"], 1)
              and type(slot["body"]) is str and len(slot["body"]) == 64
              and slot["scope"] == identity[1:3], "agent_sync_slot_binding")
        if old is not ABSENT:
            check(slot["birth"] == old["birth"] and slot["alias"] == old["alias"],
                  "agent_sync_slot_rebirth")
        elif not baseline:
            check(birth[1] == generation, "agent_sync_new_birth")

    def _context_support(self, support, identity, binding, source=None):
        validate_shape(support, FACT_SUPPORT)
        context = next(s for s in binding["sourceContexts"] if
                       [s["provider"], s["namespace"]] == identity[1:3])
        check(support["serviceId"] == binding["ownerEpoch"] and
              [support["provider"], support["namespace"]] == identity[1:3] and
              support["contextGeneration"] <= context["contextGeneration"] and
              support["sampledBoottimeMs"] < support["expiresBoottimeMs"],
              "agent_sync_context_support")
        if source is not None and support["contextGeneration"] == source["contextGeneration"]:
            receipt = next(r for r in source["components"] if r["name"] == support["component"])
            check(support["accepted"] <= receipt["accepted"] and
                  receipt["sampledBoottimeMs"] is not None and
                  support["sampledBoottimeMs"] <= receipt["sampledBoottimeMs"],
                  "agent_sync_future_context_support")

    def _field(self, ctx, binding, sources, receipts, identity, birth, field, ref, token, old):
        if old is not None and old[0] == "cohort" and old != ref:
            check(ctx.after.lookup("memberships", [old[1], identity, birth, field]) is ABSENT,
                  "agent_sync_unreferenced_membership")
        if ref is not None:
            check(type(ref) is list and len(ref) == 2, "agent_sync_support_ref")
            if ref[0] == "context":
                self._context_support(ref[1], identity, binding, sources[tuple(identity[1:3])])
            else:
                check(ref[0] == "cohort" and type(ref[1]) is list and len(ref[1]) == 3
                      and all(type(v) is str for v in ref[1])
                      and ref[1][:2] == identity[1:3] and tuple(ref[1]) in receipts,
                      "agent_sync_current_support")
                receipt = receipts[tuple(ref[1])]
                check(receipt["health"] in {"current", "partial"} and receipt["accepted"] > 0,
                      "agent_sync_current_receipt")
                actual = ctx.after.lookup("memberships", [ref[1], identity, birth, field])
                check(actual is not ABSENT and actual == token, "agent_sync_member_token")
                if field == "workspace":
                    check(ref[1][2] == "history", "agent_sync_workspace_support")
                if field == "runtime":
                    check(ref[1][2] == "runtime", "agent_sync_runtime_support")

    def _removed(self, ctx, patch, identity, old):
        ref = [identity, old["birth"]]
        observed = _plain(ctx.before.lookup("observations", ref))
        check(ctx.after.lookup("bodies", old["body"]) is ABSENT and
              ctx.after.lookup("observations", ref) is ABSENT, "agent_sync_removed_references")
        for field in SUPPORT_FIELDS:
            previous = observed["supports"][field]
            if previous is not None and previous[0] == "cohort":
                key = [previous[1], identity, old["birth"], field]
                check(ctx.after.lookup("memberships", key) is ABSENT, "agent_sync_removed_membership")
            if ctx.field_token(ref, field) is not ABSENT:
                patch.tokens[_key(ref), field] = FieldTokenWrite(ref, field, None)
        patch.remove("row_rules", ref)
        if self.view == "active":
            check(ctx.after.lookup("scopes", [*identity[1:3], "members", identity]) is ABSENT,
                  "agent_sync_removed_active_member")
        self._capabilities(patch, identity, observed["fields"], None)

    def _capabilities(self, patch, identity, previous, row):
        for field in ("lastUpdated", "latestTurn"):
            amount = int(row is not None and row[field]["health"] == "current") - int(
                previous is not None and previous[field]["health"] == "current")
            if amount or (previous is None and
                          patch.get("capability_counts", [*identity[1:3], field]) is ABSENT):
                patch.add("capability_counts", [*identity[1:3], field], amount)

    def _scopes(self, ctx, binding, sources, receipts, metadata, operations, patch):
        affected = set()
        baseline_scopes = {}
        for space, _, key, _value in operations:
            if space == "records":
                scope = tuple(key[1:3])
                before = ctx.before.lookup("records", key)
                after = ctx.after.lookup("records", key)
                self._scope_count(patch, scope, "records", int(after is not ABSENT) - int(before is not ABSENT))
            elif space == "scopes":
                check(type(key) is list and len(key) in {3, 4}
                      and all(type(v) is str for v in key[:3]) and tuple(key[:2]) in sources,
                      "agent_sync_scope_key")
                scope = tuple(key[:2])
                before, after = ctx.before.lookup("scopes", key), ctx.after.lookup("scopes", key)
                if self.view == "full":
                    check(len(key) == 3 and key[2] == "coverage", "agent_sync_full_scope_key")
                elif len(key) == 4:
                    check(key[2] in {"members", "nonmembers", "uncertain"}, "agent_sync_scope_fact")
                    self._scope_count(patch, scope, key[2], int(after is not ABSENT) - int(before is not ABSENT))
                    self._scope_size(patch, scope, key[2], _plain(before), -1)
                    self._scope_size(patch, scope, key[2], _plain(after), 1)
                    if after is not ABSENT:
                        self._scope_fact(ctx, binding, sources, key, _plain(after))
                        if ctx.base_tag is None:
                            baseline_scopes.setdefault(scope, {}).setdefault(key[2], []).append(_plain(after))
                else:
                    check(key[2] == "coverage", "agent_sync_scope_key")
                if before is ABSENT and after is not ABSENT:
                    patch.put("scope_keys", key, None)
                elif before is not ABSENT and after is ABSENT:
                    patch.remove("scope_keys", key)
            else:
                continue
            affected.add(scope)
        ready = metadata["service"]["state"] == "ready"
        for scope, source in sources.items():
            value = _plain(ctx.after.lookup("scopes", [*scope, "coverage"]))
            check((value is not ABSENT) == ready, "agent_sync_scope_coverage_missing")
            if not ready:
                stats = patch.get("scope_stats", list(scope))
                check(stats is ABSENT or not any(stats.values()), "agent_sync_warming_records")
                continue
            if self.view == "active":
                _closed(value, ("provider", "namespace", "contextGeneration", "continuity", "coverage"),
                        "agent_sync_coverage")
                validate_shape(value["coverage"], ACTIVE_SCOPE["properties"]["coverage"])
                continuity = next(c[2] for c in binding["scopeContinuity"] if c[:2] == list(scope))
                check((value["provider"], value["namespace"]) == scope and
                      value["contextGeneration"] == source["contextGeneration"] and
                      value["continuity"] == continuity, "agent_sync_scope_binding")
                coverage = value["coverage"]
                _closed(coverage, ("status", "reason", "supports"), "agent_sync_coverage")
                check(coverage["status"] in {"complete", "partial", "warming", "stale", "unavailable", "unsupported"},
                      "agent_sync_coverage_status")
                self._support_set(coverage["supports"], source, binding,
                                  runtime=coverage["status"] == "complete")
                stats = patch.get("scope_stats", list(scope))
                stats = {} if stats is ABSENT else stats
                check(stats.get("records", 0) == stats.get("members", 0) and
                      sum(stats.get(k, 0) for k in ("members", "nonmembers", "uncertain")) <= 4096,
                      "agent_sync_scope_counts")
                check(coverage["status"] != "complete" or stats.get("uncertain", 0) == 0,
                      "agent_sync_complete_uncertain")
                total = self._ledger_bytes(patch, scope, value, sources, binding)
                check(total + 2 <= MAX_LEDGER_BYTES, "agent_sync_ledger_capacity")
                if ctx.base_tag is None:
                    facts = baseline_scopes.get(scope, {})
                    oracle = {**value, "members": [], "nonmembers": facts.get("nonmembers", []),
                              "uncertain": facts.get("uncertain", [])}
                    for member in facts.get("members", []):
                        fields = {field: None if cohort is None else self._fact_support(
                            sources[scope], binding, cohort[2]) for field, cohort in member["fields"].items()}
                        oracle["members"].append({"identity": member["identity"], "fieldSupports": fields})
                    check(total == len(canonical(oracle)), "agent_sync_ledger_accounting")
            else:
                _closed(value, ("coverage", "sourceHealth", "contextGeneration", "supports", "censusStatus"),
                        "agent_sync_full_coverage")
                check(value["censusStatus"] in {"complete", "partial", "warming", "stale", "unavailable", "unsupported"},
                      "agent_sync_census_status")
                original = next(s for s in metadata["snapshot"]["sources"] if
                                (s["provider"], s["namespace"]) == scope)
                check(value["coverage"] == original["coverage"] and
                      value["sourceHealth"] == original["sourceHealth"] and
                      value["contextGeneration"] == source["contextGeneration"], "agent_sync_full_coverage")
                _closed(value["supports"], ("runtime", "saved"), "agent_sync_full_support")
                for component, name in (("runtime", "runtime"), ("history", "saved")):
                    support = value["supports"][name]
                    if support is not None:
                        self._context_support(support, [binding["hostScope"], *scope, "thread", "context"], binding)
                        check(support["component"] == component, "agent_sync_census_component")
                if (value["censusStatus"] == "complete"
                        and value["coverage"]["runtime"]["status"] == "complete"):
                    self._support_set([value["supports"]["runtime"]], source, binding, runtime=True)
                if value["coverage"]["saved"]["status"] == "complete":
                    self._support_set([value["supports"]["saved"]], source, binding)
        return tuple(list(scope) for scope in sorted(affected))

    def _scope_count(self, patch, scope, kind, amount):
        stats = patch.get("scope_stats", list(scope))
        stats = {} if stats is ABSENT else dict(stats)
        stats[kind] = stats.get(kind, 0) + amount
        check(_integer(stats[kind], 0, 4096), "agent_sync_scope_count")
        patch.put("scope_stats", list(scope), stats)

    def _scope_size(self, patch, scope, kind, value, direction):
        if value is ABSENT:
            return
        sizes = patch.get("scope_sizes", list(scope))
        sizes = {} if sizes is ABSENT else dict(sizes)
        basis = value
        if kind == "members":
            basis = {"identity": value["identity"], "fieldSupports": dict.fromkeys(SUPPORT_FIELDS)}
            for cohort in value["fields"].values():
                if cohort is not None:
                    patch.add("support_counts", cohort, direction)
        sizes[kind] = sizes.get(kind, 0) + direction * len(canonical(basis))
        check(sizes[kind] >= 0, "agent_sync_ledger_accounting")
        patch.put("scope_sizes", list(scope), sizes)

    def _fact_support(self, source, binding, component):
        receipt = next(r for r in source["components"] if r["name"] == component)
        return {"serviceId": binding["ownerEpoch"], "provider": source["provider"],
                "namespace": source["namespace"], "contextGeneration": source["contextGeneration"],
                "component": component, **{k: receipt[k] for k in
                    ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")}}

    def _ledger_bytes(self, patch, scope, header, sources, binding):
        stats = patch.get("scope_stats", list(scope))
        sizes = patch.get("scope_sizes", list(scope))
        stats = {} if stats is ABSENT else stats
        sizes = {} if sizes is ABSENT else sizes
        result = len(canonical({**header, "members": [], "nonmembers": [], "uncertain": []}))
        result += sum(sizes.values()) + sum(max(0, stats.get(k, 0) - 1)
                                          for k in ("members", "nonmembers", "uncertain"))
        for component in ("runtime", "history"):
            count = patch.get("support_counts", [*scope, component])
            if count is not ABSENT and count:
                support = self._fact_support(sources[scope], binding, component)
                result += count * (len(canonical(support)) - 4)
        return result

    def _support_set(self, supports, source, binding, *, runtime=False):
        check(type(supports) is list and len(supports) <= 2, "agent_sync_support_set")
        components = set()
        for support in supports:
            validate_shape(support, FACT_SUPPORT)
            check(support_matches(support, source, service_id=binding["ownerEpoch"]),
                  "agent_sync_exact_support")
            check(support["component"] not in components, "agent_sync_duplicate_support")
            components.add(support["component"])
        check(not runtime or "runtime" in components, "agent_sync_complete_support")

    def _scope_fact(self, ctx, binding, sources, key, value, *, observed=None):
        scope = tuple(key[:2])
        identity = key[3]
        _identity(identity, binding)
        check(tuple(identity[1:3]) == scope and type(value) is dict and
              list(identity_key(value["identity"])) == identity, "agent_sync_scope_identity")
        if key[2] == "members":
            _closed(value, ("identity", "fields"), "agent_sync_scope_member")
            check(type(value["fields"]) is dict and set(value["fields"]) == set(SUPPORT_FIELDS),
                  "agent_sync_scope_fields")
            slot = _plain(ctx.after.lookup("records", identity))
            check(slot is not ABSENT, "agent_sync_orphan_scope_member")
            if observed is None:
                observed = _plain(ctx.after.lookup("observations", [identity, slot["birth"]]))
            for field, cohort in value["fields"].items():
                check((None if cohort is None else ["cohort", cohort]) == observed["supports"][field],
                      "agent_sync_scope_support")
        elif key[2] == "nonmembers":
            validate_shape(value, NONMEMBER)
            check(value["supports"] and
                  (value["reason"] == "parked") == (value["value"] == "parked"),
                  "agent_sync_negative")
            self._support_set(value["supports"], sources[scope], binding,
                              runtime=value["reason"] == "parked")
        else:
            validate_shape(value, UNCERTAIN)
            for name in ("priorSupport", "support"):
                if value[name] is not None:
                    self._context_support(value[name], identity, binding, sources[scope])
            prior = value["priorSupport"]
            check(prior is None or prior["component"] == "runtime" and
                  value["horizonBoottimeMs"] <= prior["expiresBoottimeMs"],
                  "agent_sync_uncertain_horizon")
        if key[2] != "members":
            check(ctx.after.lookup("records", identity) is ABSENT, "agent_sync_scope_overlap")
            other = "nonmembers" if key[2] == "uncertain" else "uncertain"
            check(ctx.after.lookup("scopes", [*scope, other, identity]) is ABSENT,
                  "agent_sync_scope_overlap")


SyncProfile = AgentSyncProfile
