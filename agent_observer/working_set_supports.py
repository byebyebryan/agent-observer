"""Frame-local FactSupport interning for the unreleased working-set grammar.

Indices are serialization references only.  The table stays paired with its
scope; callers resolve only the entry they are about to validate or return.
"""

from __future__ import annotations

from collections.abc import Mapping

from .active_contract import FACT_SUPPORT, MAX_IDENTITIES
from .contract import ContractError, canonical, validate_shape

MAX_SUPPORT_TABLE = MAX_IDENTITIES * 2 + 2
MAX_SUPPORT_INDEX = MAX_SUPPORT_TABLE - 1
SUPPORT_INDEX = {
    "type": "integer",
    "minimum": 0,
    "maximum": MAX_SUPPORT_INDEX,
}
NULL_SUPPORT_INDEX = {"anyOf": [SUPPORT_INDEX, {"type": "null"}]}

# The owner reserves this for the one-entry pending dictionaries/lists, compact
# copy and canonicalization temporary. The shape allows at most nine nullable
# field refs plus two refs in each positive branch (13 total). Tests exercise
# that maximum with 71-character namespaces and full-width integers on both
# supported Python versions.
SUPPORT_PLAN_SCRATCH_BYTES = 8192

# Additional conservative owner charges beyond the exact canonical scope bytes:
# per unique support includes the retained canonical key, owned eight-field map,
# list/dict slots and resizing slack; per occurrence includes the typed reference
# plus old/new integer and remap overlap. The larger preflight charge also covers
# sorting/index-remap/final table overlap before builder scratch is released.
_SUPPORT_ENTRY_OVERHEAD = 1024
_REFERENCE_OVERHEAD = 64
_REMAP_SLACK = 4
_REMAP_SCRATCH_PER_SUPPORT = 128


def _mapping(value, code="working_set_support_reference"):
    if not isinstance(value, Mapping):
        raise ContractError(code)
    return value


def _owned_support(value):
    """Create the sole frame-owned map copy after preflight succeeds."""
    return dict(value)


def _index(value, table, *, nullable=False):
    if value is None and nullable:
        return None
    if type(value) is not int or value < 0 or value >= len(table):
        raise ContractError("working_set_support_reference")
    return table[value]


def resolve_member(scope, member):
    """Return a one-member shallow adapter with borrowed support-map values."""
    table = scope["supportTable"]
    source = _mapping(member)
    result = dict(source)
    fields = _mapping(source["fieldSupports"])
    result["fieldSupports"] = {
        name: _index(ref, table, nullable=True) for name, ref in fields.items()
    }
    for branch_name in ("active", "recent"):
        branch = source[branch_name]
        if branch is None:
            continue
        branch = _mapping(branch)
        result[branch_name] = {
            **branch,
            "supports": [_index(ref, table) for ref in branch["supports"]],
        }
    return result


def resolve_uncertain(scope, entry):
    table = scope["supportTable"]
    source = _mapping(entry)
    return {
        **source,
        "priorSupport": _index(source["priorSupport"], table, nullable=True),
        "support": _index(source["support"], table, nullable=True),
    }


def resolve_nonmember(scope, entry):
    table = scope["supportTable"]
    source = _mapping(entry)
    recent = source["recent"]
    if recent is not None:
        recent = _mapping(recent)
        recent = {
            **recent,
            "support": _index(recent["support"], table, nullable=True),
        }
    return {
        **source,
        "supports": [_index(ref, table) for ref in source["supports"]],
        "recent": recent,
    }


def resolve_coverage(scope, coverage):
    table = scope["supportTable"]
    source = _mapping(coverage)
    return {
        **source,
        "supports": [_index(ref, table) for ref in source["supports"]],
    }


def _compact_member(member, reference):
    source = _mapping(member)
    result = dict(source)
    result["fieldSupports"] = {
        name: reference(ref) for name, ref in _mapping(source["fieldSupports"]).items()
    }
    for branch_name in ("active", "recent"):
        branch = source[branch_name]
        if branch is not None:
            branch = _mapping(branch)
            result[branch_name] = {
                **branch,
                "supports": [reference(ref) for ref in branch["supports"]],
            }
    return result


def _compact_uncertain(entry, reference):
    source = _mapping(entry)
    return {
        **source,
        "priorSupport": reference(source["priorSupport"]),
        "support": reference(source["support"]),
    }


def _compact_nonmember(entry, reference):
    source = _mapping(entry)
    recent = source["recent"]
    if recent is not None:
        recent = _mapping(recent)
        recent = {**recent, "support": reference(recent["support"])}
    return {
        **source,
        "supports": [reference(ref) for ref in source["supports"]],
        "recent": recent,
    }


def _compact_coverage(coverage, reference):
    source = _mapping(coverage)
    return {**source, "supports": [reference(ref) for ref in source["supports"]]}


class SupportTableBuilder:
    """Transactional per-entry interner with a bounded source-owner charge."""

    def __init__(self, *, limit, support_lookup=None):
        if type(limit) is not int or limit < 1:
            raise ContractError("working_set_support_capacity")
        self.limit = limit
        self._support_lookup = support_lookup
        self._keys = []
        self._table = []
        self._indices = {}
        self.references = 0
        self.preflight_charge = 0
        self.overhead_charge = 0

    def _plan(self, transform, additional_charge, current_charge):
        if type(additional_charge) is not int or additional_charge < 0:
            raise ContractError("working_set_support_capacity")
        if type(current_charge) is not int or current_charge < 0:
            raise ContractError("working_set_support_capacity")
        pending = {}
        pending_values = []
        reference_count = 0

        def reference(support):
            nonlocal reference_count
            if support is None:
                return None
            if not isinstance(support, Mapping):
                raise ContractError("working_set_support_reference")
            support_value = support if type(support) is dict else dict(support)
            validate_shape(support_value, FACT_SUPPORT)
            key = canonical(support_value)
            index = self._indices.get(key)
            if index is None:
                index = pending.get(key)
            if index is None:
                index = len(self._table) + len(pending_values)
                pending[key] = index
                # Borrow the map in the bounded current-entry plan. The owned
                # support copy is made only after the full plan fits.
                borrowed = (
                    self._support_lookup(support_value)
                    if self._support_lookup is not None
                    else None
                )
                if borrowed is not None:
                    validate_shape(borrowed, FACT_SUPPORT)
                    if canonical(borrowed) != key:
                        raise ContractError("working_set_support_reference")
                pending_values.append((key, support_value, borrowed))
            reference_count += 1
            return index

        compact = transform(reference)
        serialized = len(canonical(compact).encode("utf-8"))
        delta_preflight = (
            reference_count * (_REFERENCE_OVERHEAD + _REMAP_SLACK)
            + sum(
                2 * len(key.encode("utf-8")) + _SUPPORT_ENTRY_OVERHEAD + 1
                + _REMAP_SCRATCH_PER_SUPPORT
                for key, _support, _borrowed in pending_values
            )
        )
        if len(self._table) + len(pending_values) > MAX_SUPPORT_TABLE:
            raise ContractError("working_set_support_table_limit")
        if (
            current_charge
            + serialized
            + additional_charge
            + self.preflight_charge
            + delta_preflight
            > self.limit
        ):
            raise ContractError("working_set_support_capacity")

        # No retained key/map or table growth occurs before the complete
        # current-entry and incremental table charge has passed.
        for key, support, borrowed in pending_values:
            index = len(self._table)
            self._indices[key] = index
            self._keys.append(key)
            self._table.append(borrowed if borrowed is not None else _owned_support(support))
        self.references += reference_count
        self.preflight_charge += delta_preflight
        self.overhead_charge += reference_count * _REFERENCE_OVERHEAD + sum(
            len(key.encode("utf-8")) + _SUPPORT_ENTRY_OVERHEAD
            for key, _support, _borrowed in pending_values
        )
        return compact

    def owned_support(self, support):
        """Return the map already owned by this builder after a successful plan."""

        if not isinstance(support, Mapping):
            raise ContractError("working_set_support_reference")
        validate_shape(support, FACT_SUPPORT)
        index = self._indices.get(canonical(support))
        if index is None or index < 0 or index >= len(self._table):
            raise ContractError("working_set_support_reference")
        return self._table[index]

    def member(self, member, *, additional_charge=0, current_charge):
        return self._plan(
            lambda reference: _compact_member(member, reference),
            additional_charge,
            current_charge,
        )

    def uncertain(self, entry, *, additional_charge=0, current_charge):
        return self._plan(
            lambda reference: _compact_uncertain(entry, reference),
            additional_charge,
            current_charge,
        )

    def nonmember(self, entry, *, additional_charge=0, current_charge):
        return self._plan(
            lambda reference: _compact_nonmember(entry, reference),
            additional_charge,
            current_charge,
        )

    def coverage(self, coverage, *, additional_charge=0, current_charge):
        return self._plan(
            lambda reference: _compact_coverage(coverage, reference),
            additional_charge,
            current_charge,
        )

    def finalize(self, scope):
        ordered = sorted(
            range(len(self._table)),
            key=lambda index: self._keys[index].encode("utf-8"),
        )
        remap = [0] * len(ordered)
        table = []
        for new_index, old_index in enumerate(ordered):
            remap[old_index] = new_index
            table.append(self._table[old_index])

        def ref(value):
            if value is None:
                return None
            if type(value) is not int or value < 0 or value >= len(remap):
                raise ContractError("working_set_support_reference")
            return remap[value]

        scope["coverage"]["supports"] = [
            ref(value) for value in scope["coverage"]["supports"]
        ]
        for member in scope["members"]:
            fields = member["fieldSupports"]
            for name, value in fields.items():
                fields[name] = ref(value)
            for branch_name in ("active", "recent"):
                branch = member[branch_name]
                if branch is not None:
                    branch["supports"] = [ref(value) for value in branch["supports"]]
        for entry in scope["uncertain"]:
            entry["priorSupport"] = ref(entry["priorSupport"])
            entry["support"] = ref(entry["support"])
        for entry in scope["nonmembers"]:
            entry["supports"] = [ref(value) for value in entry["supports"]]
            if entry["recent"] is not None:
                entry["recent"]["support"] = ref(entry["recent"]["support"])
        scope["supportTable"] = table
        self._keys, self._table, self._indices = [], [], {}
        return scope


def compact_scope(scope, *, limit=1024 * 1024):
    """Build a compact scope from internal map-form data for bounded fixtures.

    Production uses the same builder incrementally so each candidate member is
    admitted before its owned support maps and references are retained.
    """
    builder = SupportTableBuilder(limit=limit)
    charge = SUPPORT_PLAN_SCRATCH_BYTES
    original_coverage = scope["coverage"]
    compact_coverage = builder.coverage(
        original_coverage,
        additional_charge=0,
        current_charge=charge,
    )
    charge += len(canonical(compact_coverage).encode("utf-8"))
    members = []
    for member in scope["members"]:
        compact = builder.member(
            member,
            additional_charge=0,
            current_charge=charge,
        )
        charge += len(canonical(compact).encode("utf-8"))
        members.append(compact)
    uncertain = []
    for entry in scope["uncertain"]:
        compact = builder.uncertain(
            entry,
            additional_charge=0,
            current_charge=charge,
        )
        charge += len(canonical(compact).encode("utf-8"))
        uncertain.append(compact)
    nonmembers = []
    for entry in scope["nonmembers"]:
        compact = builder.nonmember(
            entry,
            additional_charge=0,
            current_charge=charge,
        )
        charge += len(canonical(compact).encode("utf-8"))
        nonmembers.append(compact)
    result = {
        **scope,
        "coverage": compact_coverage,
        "members": members,
        "uncertain": uncertain,
        "nonmembers": nonmembers,
    }
    return builder.finalize(result)


def validate_support_table(scope):
    """Validate canonical table ordering and that every local entry is used."""
    table = scope["supportTable"]
    if type(table) not in {list, tuple} or len(table) > MAX_SUPPORT_TABLE:
        raise ContractError("working_set_support_table_limit")
    prior = None
    for support in table:
        validate_shape(support, FACT_SUPPORT)
        key = canonical(support).encode("utf-8")
        if prior is not None and key <= prior:
            raise ContractError("working_set_support_table_order")
        prior = key
    used = bytearray((len(table) + 7) // 8)

    def mark(reference):
        if type(reference) is not int or reference < 0 or reference >= len(table):
            raise ContractError("working_set_support_reference")
        used[reference >> 3] |= 1 << (reference & 7)

    for reference in scope["coverage"]["supports"]:
        mark(reference)
    for member in scope["members"]:
        for reference in member["fieldSupports"].values():
            if reference is not None:
                mark(reference)
        for branch_name in ("active", "recent"):
            branch = member[branch_name]
            if branch is not None:
                for reference in branch["supports"]:
                    mark(reference)
    for entry in scope["uncertain"]:
        for name in ("priorSupport", "support"):
            reference = entry[name]
            if reference is not None:
                mark(reference)
    for entry in scope["nonmembers"]:
        for reference in entry["supports"]:
            mark(reference)
        recent = entry["recent"]
        if recent is not None and recent["support"] is not None:
            mark(recent["support"])
    if any(not byte for byte in used):
        raise ContractError("working_set_support_table_unused")
    # A partly filled last byte must contain every actual index bit that was
    # referenced; the loop above also rejects every wholly unused entry.
    for index in range(len(table)):
        if not used[index >> 3] & (1 << (index & 7)):
            raise ContractError("working_set_support_table_unused")
    return table
