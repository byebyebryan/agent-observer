"""Bounded prior-positive context for the working-set projector.

The ledger binds one four-field identity prefix and stores native IDs as its
only per-identity keys.  Values point at interned, complete FactSupport maps;
the map's expiry is the informational retention horizon.  Frame-local support
table indices are deliberately never retained here.

This module is private to the Observer projector.  It does not decide current
membership and it never turns a retained positive into current authority.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .projection_support import FACT_SUPPORT, MAX_IDENTITIES
from .contract import DIGEST, SCOPE, UUID, ContractError, validate_shape

SUPPORT_KEY_FIELDS = (
    "serviceId",
    "provider",
    "namespace",
    "contextGeneration",
    "component",
    "accepted",
    "sampledBoottimeMs",
    "expiresBoottimeMs",
)

# A plan holds one support tuple, one prefix slice and one fixed update record.
# The caller reserves this once alongside the existing SUPPORT_PLAN_SCRATCH.
LEDGER_PLAN_SCRATCH_BYTES = 1024

# CPython dict tables can resize while a key is inserted.  The candidate owner
# already charges its current table; at a predicted growth point it additionally
# prepays a new table bounded by twice the current table plus a fixed header
# margin.  Both supported interpreters' observed table sizes are covered by the
# focused resize-vector test.
_DICT_GROWTH_MARGIN = 512
_DICT_COPY_MARGIN = 512
# The slotted owner/atom sizes include their object references, not the
# separately allocated integer values stored in those slots.  Reserve the
# largest supported safe-integer representation for the owner's charge and
# two resize thresholds; each support atom also charges its own `charge` int.
_OWNER_SCALAR_CHARGE = 3 * sys.getsizeof(2**53 - 1)


def _owned_ascii(value: str) -> str:
    """Copy an admitted ASCII string so the owner does not retain caller maps."""

    return value.encode("ascii").decode("ascii")


def _prefix_charge(prefix: tuple[str, str, str, str] | None) -> int:
    if prefix is None:
        return 0
    return sys.getsizeof(prefix) + sum(sys.getsizeof(value) for value in prefix)


def _support_atom_charge(atom: _SupportAtom) -> int:
    support = atom.value
    return (
        sys.getsizeof(atom)
        + sys.getsizeof(atom.charge)
        + sys.getsizeof(atom.key)
        + sum(sys.getsizeof(value) for value in atom.key)
        + sys.getsizeof(support)
        + sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in support.items())
    )


def _record_charge(record: tuple[_SupportAtom, int]) -> int:
    return sys.getsizeof(record) + sys.getsizeof(record[1])


@dataclass(frozen=True, slots=True, eq=False)
class _SupportAtom:
    """One full support map and its canonical eight-value tuple key."""

    key: tuple[Any, ...]
    value: Mapping[str, object]
    charge: int


@dataclass(frozen=True, slots=True)
class LedgerUpdate:
    """Preflight plan for one identity's latest positive support."""

    identity: tuple[str, str, str, str, str]
    support_key: tuple[Any, ...]
    existing_atom: _SupportAtom | None
    previous_atom: _SupportAtom | None
    needs_prefix: bool
    needs_native_id: bool
    peak_additional_bytes: int


class WorkingSetLedger:
    """One scoped, bounded, copy-on-write prior-positive owner.

    ``entries`` maps an owned ASCII native ID to a shared support atom.  The
    support index owns each full eight-field map once, regardless of how many
    identities refer to it.  Counts are immutable values inside the index so
    a candidate can change them without mutating the still-live old root.
    """

    __slots__ = (
        "context",
        "prefix",
        "_entries",
        "_supports",
        "_charge",
        "_entry_resize_at",
        "_support_resize_at",
        "_fallback",
    )

    def __init__(
        self,
        context: tuple[str, str, int] | None = None,
        *,
        prefix: tuple[str, str, str, str] | None = None,
        _entries: dict[str, _SupportAtom] | None = None,
        _supports: dict[tuple[Any, ...], tuple[_SupportAtom, int]] | None = None,
        _fallback: WorkingSetLedger | None = None,
    ) -> None:
        if context is not None and (
            type(context) is not tuple
            or len(context) != 3
            or context[0] != "codex"
            or type(context[1]) is not str
            or len(context[1]) != 71
            or not context[1].isascii()
            or type(context[2]) is not int
            or not 0 <= context[2] <= 2**53 - 1
            or re.fullmatch(DIGEST, context[1]) is None
        ):
            raise ContractError("working_set_ledger_context")
        if prefix is not None and (
            type(prefix) is not tuple
            or len(prefix) != 4
            or any(type(value) is not str or not value.isascii() for value in prefix)
            or not 1 <= len(prefix[0]) <= 256
            or re.fullmatch(SCOPE, prefix[0]) is None
            or prefix[1] != "codex"
            or len(prefix[2]) != 71
            or re.fullmatch(DIGEST, prefix[2]) is None
            or prefix[3] != "thread"
        ):
            raise ContractError("working_set_ledger_identity")
        if context is not None and prefix is not None and prefix[2] != context[1]:
            raise ContractError("working_set_ledger_context")
        self.context = context
        self.prefix = prefix
        self._entries = {} if _entries is None else _entries
        self._supports = {} if _supports is None else _supports
        self._entry_resize_at = max(1, len(self._entries) + 1)
        self._support_resize_at = max(1, len(self._supports) + 1)
        self._fallback = _fallback
        self._charge = self._measure_charge()

    @classmethod
    def empty(
        cls,
        context: tuple[str, str, int] | None = None,
        *,
        fallback: WorkingSetLedger | None = None,
    ) -> WorkingSetLedger:
        return cls(context, _fallback=fallback)

    @classmethod
    def empty_upper_charge(cls, context: tuple[str, str, int] | None) -> int:
        """Bound an empty candidate owner without allocating its dictionaries."""

        return (
            cls.__basicsize__
            + 2 * sys.getsizeof({})
            + (sys.getsizeof(context) + sum(sys.getsizeof(value) for value in context)
               if context is not None else 0)
            + _OWNER_SCALAR_CHARGE
            + 1024
        )

    @staticmethod
    def _validate_identity(
        identity: object,
    ) -> tuple[tuple[str, str, str, str], str]:
        if type(identity) is not tuple or len(identity) != 5:
            raise ContractError("working_set_ledger_identity")
        if any(type(value) is not str or not value.isascii() for value in identity):
            raise ContractError("working_set_ledger_identity")
        if (
            not 1 <= len(identity[0]) <= 256
            or re.fullmatch(SCOPE, identity[0]) is None
            or identity[1] != "codex"
            or len(identity[2]) != 71
            or re.fullmatch(DIGEST, identity[2]) is None
            or identity[3] != "thread"
            or len(identity[4]) != 36
            or re.fullmatch(UUID, identity[4]) is None
        ):
            raise ContractError("working_set_ledger_identity")
        return identity[:4], identity[4]

    def _support_key(self, value: Mapping[str, object]) -> tuple[Any, ...]:
        if not isinstance(value, Mapping):
            raise ContractError("working_set_ledger_support")
        validate_shape(value, FACT_SUPPORT)
        if self.context is not None and (
            value["provider"],
            value["namespace"],
            value["contextGeneration"],
        ) != self.context:
            raise ContractError("working_set_ledger_context")
        return tuple(value[name] for name in SUPPORT_KEY_FIELDS)

    def _measure_charge(self) -> int:
        """Measure this owner graph conservatively, without canonical JSON copies."""

        total = (
            sys.getsizeof(self)
            + sys.getsizeof(self._entries)
            + sys.getsizeof(self._supports)
            + _OWNER_SCALAR_CHARGE
            + _prefix_charge(self.prefix)
        )
        if self.context is not None:
            total += sys.getsizeof(self.context)
            total += sum(sys.getsizeof(value) for value in self.context)
        for native_id in self._entries:
            total += sys.getsizeof(native_id)
        for key, (atom, count) in self._supports.items():
            # The atom owns both the exact canonical key tuple and the complete
            # map.  The dict key is the same tuple object, so charge it once.
            if key is not atom.key:
                total += sys.getsizeof(key) + sum(sys.getsizeof(value) for value in key)
            total += atom.charge + _record_charge((atom, count))
        return total

    @property
    def charge(self) -> int:
        """Conservative live graph charge for this owner root."""

        return self._charge

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def support_count(self) -> int:
        return len(self._supports)

    def clone_upper_charge(self) -> int:
        """Upper bound for a copied candidate root before allocating it."""

        # Copying duplicates the owner roots and dict tables, but intentionally
        # shares immutable keys, atoms and support maps.  The margin covers the
        # dict headers if a supported interpreter compacts a copied table.
        return self._charge + 2 * _DICT_COPY_MARGIN

    def clone_live(self, now_ms: int) -> WorkingSetLedger:
        """Copy the current root and retire expired entries in the candidate.

        The caller must preflight ``self.charge + clone_upper_charge()`` before
        invoking this method.  Old maps/keys remain owned by ``self`` until the
        candidate commits or unwinds.
        """

        if type(now_ms) is not int or now_ms < 0:
            raise ContractError("working_set_ledger_time")
        entries = self._entries.copy()
        supports = self._supports.copy()
        candidate = WorkingSetLedger(
            self.context,
            prefix=self.prefix,
            _entries=entries,
            _supports=supports,
            _fallback=self,
        )
        # A copied dict has no more used keys than the source.  If its table is
        # smaller, use an early probe boundary until an observed resize updates
        # the threshold; this can reserve early but never late.
        if sys.getsizeof(entries) < sys.getsizeof(self._entries):
            candidate._entry_resize_at = len(entries) + 1
        else:
            candidate._entry_resize_at = self._entry_resize_at
        if sys.getsizeof(supports) < sys.getsizeof(self._supports):
            candidate._support_resize_at = len(supports) + 1
        else:
            candidate._support_resize_at = self._support_resize_at

        expired_entries = False
        for native_id, atom in self._entries.items():
            if atom.value["expiresBoottimeMs"] <= now_ms:
                del candidate._entries[native_id]
                candidate._charge -= sys.getsizeof(native_id)
                expired_entries = True
        expired_supports = False
        for key, (atom, _count) in self._supports.items():
            if atom.value["expiresBoottimeMs"] <= now_ms:
                record = candidate._supports.pop(key)
                candidate._charge -= atom.charge + _record_charge(record)
                expired_supports = True
        if not candidate._entries:
            before = sys.getsizeof(candidate._entries)
            candidate._entries.clear()
            candidate._charge += sys.getsizeof(candidate._entries) - before
        if not candidate._supports:
            before = sys.getsizeof(candidate._supports)
            candidate._supports.clear()
            candidate._charge += sys.getsizeof(candidate._supports) - before
        if expired_entries:
            candidate._entry_resize_at = len(candidate._entries) + 1
        if expired_supports:
            candidate._support_resize_at = len(candidate._supports) + 1
        candidate._fallback = self
        return candidate

    def _validate_bound_identity(
        self, identity: object, *, allow_unbound: bool = False
    ) -> tuple[str, tuple[str, str, str, str]]:
        prefix, native_id = self._validate_identity(identity)
        if self.prefix is None:
            if not allow_unbound and self._entries:
                raise ContractError("working_set_ledger_identity")
        elif prefix != self.prefix:
            raise ContractError("working_set_ledger_prefix")
        full = (*prefix, native_id)
        if full != identity:
            raise ContractError("working_set_ledger_identity")
        return native_id, prefix

    def get(self, identity: object) -> tuple[Mapping[str, object], int] | None:
        """Return a prior map/horizon only for the exact complete identity."""

        native_id, prefix = self._validate_bound_identity(identity)
        if self.prefix is None or prefix != self.prefix:
            return None
        atom = self._entries.get(native_id)
        if atom is None:
            return None
        if (*self.prefix, native_id) != identity:
            return None
        horizon = atom.value["expiresBoottimeMs"]
        if type(horizon) is not int:
            raise ContractError("working_set_ledger_support")
        return atom.value, horizon

    def support_for(self, support: Mapping[str, object]) -> Mapping[str, object] | None:
        """Borrow an exact current owner map for SupportTableBuilder reuse."""

        key = self._support_key(support)
        record = self._supports.get(key)
        if record is None and self._fallback is not None:
            record = self._fallback._supports.get(key)
        if record is None:
            return None
        atom = record[0]
        if tuple(atom.value[name] for name in SUPPORT_KEY_FIELDS) != atom.key:
            raise ContractError("working_set_ledger_support")
        return atom.value

    def plan_put(
        self,
        identity: object,
        support: Mapping[str, object],
        *,
        current_charge: int = 0,
        limit: int = 1024 * 1024,
    ) -> LedgerUpdate:
        """Plan the exact update and resize reserve without retaining new data."""

        if (
            type(current_charge) is not int
            or current_charge < 0
            or type(limit) is not int
            or limit < 1
        ):
            raise ContractError("working_set_ledger_capacity")
        native_id, prefix = self._validate_bound_identity(identity, allow_unbound=True)
        needs_prefix = self.prefix is None
        key = self._support_key(support)
        current_record = self._supports.get(key)
        fallback_record = (
            self._fallback._supports.get(key)
            if current_record is None and self._fallback is not None
            else None
        )
        target_atom = (
            current_record[0]
            if current_record is not None
            else fallback_record[0]
            if fallback_record is not None
            else None
        )
        previous_atom = self._entries.get(native_id)
        needs_native_id = previous_atom is None
        if needs_native_id and len(self._entries) >= MAX_IDENTITIES:
            raise ContractError("working_set_ledger_capacity")
        peak = 0
        if needs_prefix:
            peak += sys.getsizeof(prefix) + sum(sys.getsizeof(value) for value in prefix)
        if needs_native_id:
            peak += sys.getsizeof(native_id)
            peak += 12  # iteration list growth (sorted-ID pointer and Timsort slot)
            if len(self._entries) + 1 >= self._entry_resize_at:
                peak += self._resize_table_bound(self._entries)
        if target_atom is None:
            # The support map is already admitted/owned by SupportTableBuilder;
            # the ledger still prepays its intern tuple, atom and registry cell.
            peak += sys.getsizeof(key) + sum(sys.getsizeof(value) for value in key)
            peak += self._new_atom_bound(support, key)
            peak += self._record_bound(1)
            removes_last_previous = False
            if previous_atom is not None:
                previous_record = self._supports.get(previous_atom.key)
                removes_last_previous = previous_record is not None and previous_record[1] == 1
            if (
                len(self._supports) + 1 >= self._support_resize_at
                or removes_last_previous
            ):
                peak += self._resize_table_bound(self._supports)
        else:
            count = current_record[1] if current_record is not None else 0
            if current_record is None:
                peak += target_atom.charge
                peak += self._record_bound(count + 1)
                removes_last_previous = False
                if previous_atom is not None:
                    previous_record = self._supports.get(previous_atom.key)
                    removes_last_previous = previous_record is not None and previous_record[1] == 1
                if (
                    len(self._supports) + 1 >= self._support_resize_at
                    or removes_last_previous
                ):
                    peak += self._resize_table_bound(self._supports)
            if previous_atom is not target_atom or previous_atom is None:
                if current_record is not None:
                    peak += self._record_bound(count + 1)
        if previous_atom is not None and previous_atom is not target_atom:
            old_record = self._supports.get(previous_atom.key)
            if old_record is None:
                raise ContractError("working_set_ledger_support")
            if old_record[1] > 1:
                peak += self._record_bound(old_record[1] - 1)
            elif target_atom is not None and current_record is None:
                # Delete-plus-insert may compact a table based on used slots
                # even when the final entry count is unchanged.
                peak += self._resize_table_bound(self._supports)
        if current_charge + peak > limit:
            raise ContractError("working_set_ledger_capacity")
        return LedgerUpdate(
            identity=identity,
            support_key=target_atom.key if target_atom is not None else key,
            existing_atom=target_atom,
            previous_atom=previous_atom,
            needs_prefix=needs_prefix,
            needs_native_id=needs_native_id,
            peak_additional_bytes=peak,
        )

    @staticmethod
    def _resize_table_bound(table: dict[object, object]) -> int:
        # Prepay a new table while the current table remains live. This is used
        # only at an observed/early lower-bound growth threshold, not per row.
        return 2 * sys.getsizeof(table) + _DICT_GROWTH_MARGIN

    @staticmethod
    def _new_atom_bound(support: Mapping[str, object], key: tuple[Any, ...]) -> int:
        return (
            sys.getsizeof(_SupportAtom(key, support, 0))
            + sys.getsizeof(2**53 - 1)  # the atom's separately owned charge integer
            + sys.getsizeof(support)
        ) + sum(
            sys.getsizeof(name) + sys.getsizeof(value) for name, value in support.items()
        )

    @staticmethod
    def _record_bound(count: int) -> int:
        return sys.getsizeof((None, count)) + sys.getsizeof(count)

    def _observe_resize(
        self,
        table: dict[object, object],
        *,
        before_size: int,
        count: int,
        entry_table: bool,
    ) -> None:
        if sys.getsizeof(table) != before_size:
            threshold = max(1, 2 * count - 1)
        else:
            threshold = count + 1
        if entry_table:
            self._entry_resize_at = threshold
        else:
            self._support_resize_at = threshold

    def put(self, update: LedgerUpdate, support: Mapping[str, object]) -> int:
        """Commit a preflighted update, returning the owner charge delta.

        ``support`` must be the detached full map returned by the successful
        SupportTableBuilder member preflight. The call is synchronous; a plan
        cannot be committed after any other candidate mutation.
        """

        if not isinstance(update, LedgerUpdate):
            raise ContractError("working_set_ledger_plan")
        native_id, prefix = self._validate_bound_identity(update.identity, allow_unbound=True)
        key = self._support_key(support)
        if key != update.support_key:
            raise ContractError("working_set_ledger_plan")
        current_entry_atom = self._entries.get(native_id)
        if current_entry_atom is not update.previous_atom:
            raise ContractError("working_set_ledger_plan")
        before_entries = sys.getsizeof(self._entries)
        before_supports = sys.getsizeof(self._supports)
        if update.needs_prefix:
            self.prefix = tuple(_owned_ascii(part) for part in prefix)
            self._charge += _prefix_charge(self.prefix)
        if self.prefix != prefix:
            raise ContractError("working_set_ledger_prefix")

        current_record = self._supports.get(key)
        atom = current_record[0] if current_record is not None else update.existing_atom
        if atom is None:
            shell = _SupportAtom(update.support_key, support, 0)
            atom = _SupportAtom(update.support_key, support, _support_atom_charge(shell))

        # Move the identity's one reference from its former atom before adding
        # the new reference. Support records are immutable; old-root records
        # therefore remain unchanged until the owner swaps roots.
        support_deleted = False
        support_inserted = False
        if current_entry_atom is not None and current_entry_atom is not atom:
            old_record = self._supports.get(current_entry_atom.key)
            if old_record is None or old_record[1] < 1:
                raise ContractError("working_set_ledger_support")
            old_atom, old_count = old_record
            if old_count == 1:
                del self._supports[old_atom.key]
                self._charge -= old_atom.charge + _record_charge(old_record)
                support_deleted = True
            else:
                next_count = old_count - 1
                reusable = self._fallback._supports.get(old_atom.key) if self._fallback else None
                next_record = (
                    reusable
                    if reusable is not None
                    and reusable[0] is old_atom
                    and reusable[1] == next_count
                    else (old_atom, next_count)
                )
                self._supports[old_atom.key] = next_record
                self._charge += _record_charge(next_record) - _record_charge(old_record)

        current_record = self._supports.get(atom.key)
        if current_record is None:
            record = (atom, 1)
            self._supports[atom.key] = record
            self._charge += atom.charge + _record_charge(record)
            support_inserted = True
        elif current_record[0] is not atom:
            raise ContractError("working_set_ledger_support")
        elif current_entry_atom is not atom:
            count = current_record[1] + 1
            reusable = self._fallback._supports.get(atom.key) if self._fallback else None
            record = (
                reusable
                if reusable is not None and reusable[0] is atom and reusable[1] == count
                else (atom, count)
            )
            self._supports[atom.key] = record
            self._charge += _record_charge(record) - _record_charge(current_record)

        stored_native_id = native_id
        if update.needs_native_id:
            stored_native_id = _owned_ascii(native_id)
            self._entries[stored_native_id] = atom
            self._charge += sys.getsizeof(stored_native_id)
        else:
            self._entries[native_id] = atom
        after_entries = sys.getsizeof(self._entries)
        self._charge += after_entries - before_entries
        if update.needs_native_id:
            self._observe_resize(
                self._entries,
                before_size=before_entries,
                count=len(self._entries),
                entry_table=True,
            )

        after_supports = sys.getsizeof(self._supports)
        self._charge += after_supports - before_supports
        if support_inserted or support_deleted:
            self._observe_resize(
                self._supports,
                before_size=before_supports,
                count=len(self._supports),
                entry_table=False,
            )

        return self._charge

    def iter_items(self):
        """Yield deterministic full identities and borrowed map/horizon pairs."""

        if self.prefix is None:
            if self._entries:
                raise ContractError("working_set_ledger_prefix")
            return
        for native_id in sorted(self._entries):
            atom = self._entries[native_id]
            identity = (*self.prefix, native_id)
            if identity[:4] != self.prefix or identity[4] != native_id:
                raise ContractError("working_set_ledger_identity")
            yield identity, atom.value, atom.value["expiresBoottimeMs"]

    def identities(self):
        """Yield full five-field identities in canonical native-ID order."""

        for identity, _support, _horizon in self.iter_items():
            yield identity

    @property
    def iteration_scratch_bytes(self) -> int:
        """Bound sorted-key and one full-identity tuple scratch for iteration."""

        # sorted(dict) retains one pointer per identity and Timsort uses at
        # most half that many temporary pointers.  The fixed header margin
        # includes the current five-field identity tuple.
        return 512 + 12 * len(self._entries)

    def detach_fallback(self) -> None:
        """Drop the previous owner reference after commit or terminal failure."""

        self._fallback = None
