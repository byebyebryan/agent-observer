"""Opt-in pure Agent compact normalization through public Mesh R2 APIs.

No factory selects this codec. Its ID must come from trusted explicit config;
the candidate schema remains unallocated/unfrozen. Core/parser/owner code stays
Mesh-free. All schema, current-value and lookup-copy storage is prepaid.
"""

from __future__ import annotations

import weakref
from types import SimpleNamespace

from mesh_plus.protocol import check
from mesh_plus.sync import (
    AliasSpec,
    CodecSpec,
    MembershipGroup,
    MembershipGroupChange,
    NormalizedEntry,
    NormalizedOperation,
)
from mesh_plus.sync.commitment import ABSENT

from .sync_acquisition import _retire_failure
from .sync_commitment import descriptor_digest
from .sync_compact_plan import _CompactMaterialPlan, _open_compact_plan
from .sync_compact_schema import SUPPORT_FIELDS
from .sync_compact_validation import COMPACT_SCHEMA_DIGEST, _load_value_schema
from .sync_compact_values import References, restore_group, restore_value, transform_operation
from .sync_native import descriptor
from .sync_transport import AgentSyncTransportCodec


class _Copies:
    def __init__(self, budget):
        self.budget, self.credits = budget, []

    def plain(self, ref):
        if ref is ABSENT:
            return ABSENT
        bound = ref.materialization_bytes
        check(type(bound) is int and bound >= 0, "agent_compact_lookup_bound")
        credit = self.budget.reserve(4096 + 4 * bound)
        self.credits.append(credit)
        return ref.materialize()

    def close(self):
        self.budget = None
        credits, self.credits = self.credits, []
        for credit in credits:
            credit.close()


class _Access:
    def __init__(self, ctx):
        self.ctx, self.copies = ctx, None

    def alias(self, side, alias):
        return self.copies.plain(getattr(self.ctx.aliases, side).get(alias))

    def record(self, side, identity):
        state = self.ctx.before if side == "before" else self.ctx.after_records
        return self.copies.plain(state.lookup("records", identity))

    def receipt_exists(self, side, key):
        state = self.ctx.before if side == "before" else self.ctx.after_records
        return state.lookup("receipts", key) is not ABSENT

    def close(self):
        self.ctx = self.copies = None


class _Iterator:
    def __init__(self, plan, generator, credit):
        self._plan, self._generator, self._credit = weakref.ref(plan), generator, credit

    def __iter__(self):
        return self

    def __next__(self):
        plan = self._plan()
        try:
            check(plan is not None and self._generator is not None, "agent_compact_iterator_closed")
            plan._check()
            return next(self._generator)
        except StopIteration:
            self.close()
            raise
        except BaseException as error:
            _retire_failure(error)
            plan = None
            self.close()
            raise error from None
        finally:
            plan = None

    def close(self):
        generator, self._generator = self._generator, None
        try:
            if generator is not None:
                generator.close()
        finally:
            generator = None
            credit, self._credit = self._credit, None
            if credit is not None:
                credit.close()


class AgentCompactSyncCodec:
    """Explicit unselected full/active native codec, never a transport role."""

    __slots__ = ("_spec", "_view", "_host", "_token", "_head_codec")

    def __setattr__(self, _name, _value):
        raise AttributeError("immutable Agent compact codec")

    def __init__(self, view, *, encoding_id, expected_host=None):
        native = descriptor(view)
        head_codec = AgentSyncTransportCodec(view, encoding_id=encoding_id, expected_host=expected_host)
        object.__setattr__(self, "_view", view)
        object.__setattr__(self, "_host", expected_host)
        object.__setattr__(self, "_head_codec", head_codec)
        object.__setattr__(self, "_token", object())
        object.__setattr__(self, "_spec", CodecSpec(
            encoding_id, COMPACT_SCHEMA_DIGEST, descriptor_digest(native), tuple(SUPPORT_FIELDS),
            AliasSpec("aliases", ("alias",), ("birth",)), ("provisional-memberships/1",),
        ))

    @property
    def spec(self):
        return self._spec

    def open(self, raw, budget):
        schema = plan = None
        try:
            schema = _load_value_schema(budget)
            plan = _open_compact_plan(raw, self._view, budget, validate_value=schema,
                                      expected_host=self._host, _validator_owner=schema)
            schema = None
            plan._codec_owner = self._token
            return plan
        except BaseException as error:
            _retire_failure(error)
            raw = budget = None
            if plan is not None:
                plan.close()
                plan = None
            if schema is not None:
                schema.close()
                schema = None
            raise error from None

    def head(self, raw, budget):
        # Original native LF frame, not a Mesh wrapper or material plan.
        try:
            return self._head_codec.head(raw, budget)
        except BaseException as error:
            _retire_failure(error)
            raw = budget = None
            raise error from None

    def entries(self, plan, space, ctx):
        return self._iterator(plan, space, ctx, baseline=True)

    def operations(self, plan, space, ctx):
        return self._iterator(plan, space, ctx, baseline=False)

    def _iterator(self, plan, space, ctx, *, baseline):
        check(type(plan) is _CompactMaterialPlan and plan._codec_owner is self._token,
              "agent_compact_plan_owner")
        plan._check()
        check((plan._kind == "baseline") == baseline and
              ctx.descriptor.native_descriptor_digest == self.spec.native_descriptor_digest,
              "agent_compact_context")
        credit = ctx.budget.reserve(128 * 1024)
        try:
            return _Iterator(plan, self._values(plan, space, ctx, baseline=baseline), credit)
        except BaseException:
            credit.close()
            raise

    def _values(self, plan, space, ctx, *, baseline):
        rows = access = refs = copies = ticket = credit = raw = value = result = key = None
        try:
            generation = plan._projection.document["tag" if baseline else "resultTag"][1]
            epoch = ctx.binding["ownerEpoch"]
            refs = SimpleNamespace(epoch=epoch, generation=generation)
            if space not in {"records", "receipts", "metadata"}:
                access = _Access(ctx)
                refs = References(epoch, generation, plan._refs, lookup_record=access.record,
                                  lookup_alias=access.alias, receipt_exists=access.receipt_exists,
                                  baseline=baseline)
            rows = plan._values(space, ctx.budget)
            for ticket in rows:
                credit = ctx.budget.reserve(ticket.materialization_bytes)
                copies = _Copies(ctx.budget)
                if access is not None:
                    access.copies = copies
                try:
                    raw = ticket.materialize()
                    if space == "memberships":
                        value = restore_group(raw, refs, change=not baseline)
                        result = (MembershipGroup(value["cohort"], value["after_ref"], value["new_mask"])
                                  if baseline else MembershipGroupChange(
                                      value["cohort"], value["before_ref"], value["old_mask"],
                                      value["after_ref"], value["new_mask"]))
                    elif baseline:
                        key, value = restore_value(space, *raw, refs)
                        result = NormalizedEntry(space, key, ctx.pack(value))
                    else:
                        value = transform_operation(space, raw, refs, restore=True)
                        result = NormalizedOperation(space, value[0], value[1], value[2],
                                                     ctx.pack(value[3]) if value[0] == "put" else None)
                    yield result
                finally:
                    result = raw = value = key = None
                    if access is not None:
                        access.copies = None
                    copies.close()
                    copies = None
                    credit.close()
                    credit = None
                    ticket.close()
                    ticket = None
        finally:
            raw = value = result = key = ticket = copies = credit = refs = None
            if access is not None:
                access.close()
                access = None
            if rows is not None:
                rows.close()
                rows = None
            plan = ctx = None
