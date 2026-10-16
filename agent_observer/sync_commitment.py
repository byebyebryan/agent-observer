"""Mesh-free exact sync commitments and persistent compressed Patricia maps.

Framing and domain tags follow the reviewed a376bc84 appendix. Point mutations
visit at most 256 branch ancestors and one leaf; only that path is rebuilt.
Explicit ``items``/``encoded_items`` exports enumerate the map and are metered.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field

U64_MAX = (1 << 64) - 1
DEFAULT_ALLOCATION_LIMIT = 64 * 1024 * 1024
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_SURROGATE = re.compile(r"[\ud800-\udfff]")


class CommitmentError(ValueError):
    pass


class BudgetExceeded(CommitmentError):
    pass


class _Sentinel:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


ABSENT, ANY = _Sentinel("ABSENT"), _Sentinel("ANY")


class _FrozenObject(Mapping):
    __slots__ = ("_items",)

    def __new__(cls, value=()):
        result = freeze(value)
        if not isinstance(result, cls):
            raise CommitmentError("sync_object_required")
        return result

    def __init__(self, value=()):
        pass

    def __setattr__(self, name, value):
        raise AttributeError("immutable JSON object")

    def __delattr__(self, name):
        raise AttributeError("immutable JSON object")

    def __getitem__(self, key):
        for index in range(0, len(self._items), 2):
            if self._items[index] == key:
                return self._items[index + 1]
        raise KeyError(key)

    def __iter__(self):
        return (self._items[index] for index in range(0, len(self._items), 2))

    def __len__(self):
        return len(self._items) // 2

    def items(self):
        return (
            (self._items[index], self._items[index + 1]) for index in range(0, len(self._items), 2)
        )

    def values(self):
        return (self._items[index] for index in range(1, len(self._items), 2))

    def __repr__(self):
        return "FrozenObject(" + repr(dict(self.items())) + ")"


class _FrozenArray(tuple):
    __slots__ = ()

    def __new__(cls, values=()):
        return tuple.__new__(cls, (freeze(value) for value in values))


def _string(value):
    if type(value) is not str:
        raise CommitmentError("sync_string_required")
    # Validate scalars without allocating a second, potentially large UTF-8
    # copy merely to inspect an already-owned string.
    if _SURROGATE.search(value) is not None:
        raise CommitmentError("sync_unicode_scalar_required")
    return value


def freeze(value):
    """Own immutable JSON; previously minted frozen subvalues are reused."""

    def visit(item, active):
        if item is None or type(item) in (bool, int):
            return item
        if type(item) is str:
            return _string(item)
        if type(item) in (_FrozenObject, _FrozenArray):
            return item
        if not isinstance(item, (Mapping, list, tuple)):
            raise CommitmentError("sync_json_type")
        marker = id(item)
        if marker in active:
            raise CommitmentError("sync_json_cycle")
        active.add(marker)
        try:
            if isinstance(item, Mapping):
                owned = {}
                for key, child in item.items():
                    _string(key)
                    if key in owned:
                        raise CommitmentError("sync_duplicate_key")
                    owned[key] = visit(child, active)
                result = object.__new__(_FrozenObject)
                # Native facts are small objects. A flat immutable tuple avoids
                # one dict, mapping proxy and cached-size integer per fact.
                object.__setattr__(
                    result, "_items", tuple(child for pair in owned.items() for child in pair)
                )
                return result
            return tuple.__new__(_FrozenArray, (visit(child, active) for child in item))
        finally:
            active.remove(marker)

    return visit(value, set())


def freeze_reusing(value, prior):
    """Own JSON while reusing exactly equal immutable prior subtrees.

    Comparison follows canonical JSON types (bool differs from int; tuple/list
    both represent arrays). No cross-row intern pool, provenance inference or
    mutable references are introduced. Changed inputs are visited explicitly;
    unchanged already-minted subtrees are reused immediately by identity.
    This pure helper does not reserve construction memory; bounded callers
    cover temporary/new containers before retaining the result in an account.
    """
    prior = ABSENT if prior is ABSENT else freeze(prior)

    def visit(item, old, active):
        if item is None or type(item) in (bool, int, str):
            if type(item) is str:
                _string(item)
            return old if type(item) is type(old) and item == old else item
        if type(item) in (_FrozenObject, _FrozenArray) and (item is old or old is ABSENT):
            return item
        if not isinstance(item, (Mapping, list, tuple)):
            raise CommitmentError("sync_json_type")
        marker = id(item)
        if marker in active:
            raise CommitmentError("sync_json_cycle")
        active.add(marker)
        try:
            if isinstance(item, Mapping):
                previous = dict(old.items()) if type(old) is _FrozenObject else {}
                owned, same = {}, type(old) is _FrozenObject
                for key, child in item.items():
                    _string(key)
                    if key in owned:
                        raise CommitmentError("sync_duplicate_key")
                    earlier = previous.get(key, ABSENT)
                    owned[key] = visit(child, earlier, active)
                    same = same and earlier is not ABSENT and owned[key] is earlier
                if same and len(owned) == len(previous):
                    return old
                result = object.__new__(_FrozenObject)
                object.__setattr__(
                    result, "_items", tuple(child for pair in owned.items() for child in pair)
                )
                return result
            previous = old if type(old) is _FrozenArray else ()
            owned, same = [], type(old) is _FrozenArray
            for index, child in enumerate(item):
                earlier = previous[index] if index < len(previous) else ABSENT
                owned.append(visit(child, earlier, active))
                same = same and earlier is not ABSENT and owned[-1] is earlier
            if same and len(owned) == len(previous):
                return old
            return tuple.__new__(_FrozenArray, owned)
        finally:
            active.remove(marker)

    return visit(value, prior, set())


def thaw(value):
    """Detached mutable JSON export; never returns an owned mutable reference."""

    def visit(item):
        if isinstance(item, _FrozenObject):
            return {key: visit(child) for key, child in item.items()}
        if isinstance(item, _FrozenArray):
            return [visit(child) for child in item]
        return item

    return visit(freeze(value))


def canonical(value):
    """Exact integer-only canonical UTF-8 JSON, with no surrogate acceptance."""

    def mapping(item):
        if isinstance(item, _FrozenObject):
            # JSONEncoder understands immutable tuple arrays already. Convert
            # only the current object header, rather than thawing the complete
            # retained value graph before encoding it a second time.
            return dict(item.items())
        raise CommitmentError("sync_json_type")

    try:
        return json.dumps(
            freeze(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
            default=mapping,
        ).encode("utf-8")
    except (TypeError, UnicodeError, RecursionError, ValueError) as error:
        if isinstance(error, CommitmentError):
            raise
        raise CommitmentError("sync_canonical_json") from error


def parse(raw, *, require_canonical=False):
    """Strict JSON admission, including duplicate keys, floats and negative zero."""
    if type(raw) is not bytes:
        raise CommitmentError("sync_json_bytes_required")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise CommitmentError("sync_duplicate_key")
            result[key] = value
        return result

    def integer(text):
        if text == "-0":
            raise CommitmentError("sync_negative_zero")
        return int(text)

    def reject(text):
        raise CommitmentError("sync_json_number")

    try:
        value = freeze(
            json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=pairs,
                parse_int=integer,
                parse_float=reject,
                parse_constant=reject,
            )
        )
        if require_canonical and canonical(value) != raw:
            raise CommitmentError("sync_noncanonical_json")
        return value
    except (UnicodeError, RecursionError, ValueError) as error:
        if isinstance(error, CommitmentError):
            raise
        raise CommitmentError("sync_invalid_json") from error


def u64(value):
    if type(value) is not int or not 0 <= value <= U64_MAX:
        raise CommitmentError("sync_u64")
    return value.to_bytes(8, "big")


def u16(value):
    if type(value) is not int or not 0 <= value <= 65535:
        raise CommitmentError("sync_u16")
    return value.to_bytes(2, "big")


def frame(value):
    if type(value) is not bytes:
        raise CommitmentError("sync_frame_bytes_required")
    return u64(len(value)) + value


def unframe(value):
    if (
        type(value) is not bytes
        or len(value) < 8
        or int.from_bytes(value[:8], "big") != len(value) - 8
    ):
        raise CommitmentError("sync_invalid_frame")
    return value[8:]


def _hex_bytes(value):
    if type(value) is not str or _HEX.fullmatch(value) is None:
        raise CommitmentError("sync_digest_hex")
    return bytes.fromhex(value)


def _space(value):
    return _string(value).encode("utf-8")


def _hash(value):
    return hashlib.sha256(value).digest()


def _key_digest(space, key_bytes):
    return _hash(b"mesh-sync-key\0" + frame(space) + frame(key_bytes))


def _value_digest(space, value_bytes):
    return _hash(b"mesh-sync-value\0" + frame(space) + frame(value_bytes))


def key_hash(space, key):
    return _key_digest(_space(space), canonical(key)).hex()


def value_hash(space, value):
    return _value_digest(_space(space), canonical(value)).hex()


def empty_root(space):
    return _hash(b"mesh-sync-empty\0" + frame(_space(space))).hex()


def descriptor_digest(descriptor):
    return _hash(canonical(descriptor)).hex()


def native_binding_digest(binding):
    return _hash(b"mesh-sync-native-binding\0" + frame(canonical(binding))).hex()


def source_binding_digest(binding):
    return _hash(b"mesh-sync-source-binding\0" + frame(canonical(binding))).hex()


def native_root(binding, generation, tables_summary, *, expected_spaces=None):
    """Commit an already computed, complete and strictly sorted table summary."""
    u64(generation)
    previous, names = None, []
    if not isinstance(tables_summary, (list, tuple)):
        raise CommitmentError("sync_table_summary")
    for item in tables_summary:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise CommitmentError("sync_table_summary")
        space, root, count = item
        _space(space)
        _hex_bytes(root)
        u64(count)
        if previous is not None and space <= previous:
            raise CommitmentError("sync_table_order")
        if (count == 0) != (root == empty_root(space)):
            raise CommitmentError("sync_table_empty_count")
        names.append(space)
        previous = space
    if expected_spaces is not None and tuple(names) != tuple(sorted(expected_spaces)):
        raise CommitmentError("sync_table_registry")
    return _hash(
        b"mesh-sync-native\0"
        + frame(canonical(binding))
        + u64(generation)
        + frame(canonical(tables_summary))
    ).hex()


def source_root(binding, native_root_hex):
    return _hash(
        b"mesh-sync-source\0" + frame(canonical(binding)) + _hex_bytes(native_root_hex)
    ).hex()


def body_id(descriptor_digest_hex, content):
    return _hash(
        b"mesh-sync-body\0" + frame(_hex_bytes(descriptor_digest_hex)) + frame(canonical(content))
    ).hex()


def field_token(descriptor_digest_hex, identity, birth, field_name, field_value):
    if (
        not isinstance(identity, (list, tuple))
        or len(identity) != 5
        or not isinstance(birth, (list, tuple))
        or len(birth) != 2
    ):
        raise CommitmentError("sync_field_identity_birth")
    for value in identity:
        _string(value)
    _string(birth[0])
    u64(birth[1])
    return _hash(
        b"mesh-sync-field\0"
        + frame(_hex_bytes(descriptor_digest_hex))
        + frame(canonical(identity))
        + frame(canonical(birth))
        + frame(_string(field_name).encode("utf-8"))
        + frame(canonical(field_value))
    ).hex()


@dataclass(slots=True)
class _Held:
    value: object
    refs: int


@dataclass(slots=True)
class _EncodedHeld(_Held):
    encoded: bytes


_SMALL_REFS = tuple(range(257))


def _ref_bytes(count):
    return sys.getsizeof(count) if count > 256 else 0


class _IdentityIndex(Mapping):
    """Fixed shard directory; point changes never scan/rebuild the full index."""

    __slots__ = ("_shards", "_count", "storage_size")

    def __init__(self):
        self._shards = tuple({} for _ in range(256))
        self._count = 0
        self.storage_size = (
            sys.getsizeof(self)
            + sys.getsizeof(self._shards)
            + sum(map(sys.getsizeof, self._shards))
        )

    @staticmethod
    def _bucket(marker):
        return ((marker >> 4) ^ (marker >> 13) ^ (marker >> 23)) & 255

    def __getitem__(self, marker):
        return self._shards[self._bucket(marker)][marker]

    def __setitem__(self, marker, value):
        shard = self._shards[self._bucket(marker)]
        before = sys.getsizeof(shard)
        self._count += marker not in shard
        shard[marker] = value
        self.storage_size += sys.getsizeof(shard) - before

    def __delitem__(self, marker):
        shard = self._shards[self._bucket(marker)]
        before = sys.getsizeof(shard)
        del shard[marker]
        self._count -= 1
        self.storage_size += sys.getsizeof(shard) - before

    def __len__(self):
        return self._count

    def __iter__(self):
        return (marker for shard in self._shards for marker in shard)

    def growth_bound(self, markers):
        """Conservative CPython insertion/resize scratch, only touched shards.

        The bound includes an old/new dictionary overlap at resize and spare
        capacity for all new entries. The exact resulting capacity replaces
        this temporary reservation immediately after insertion.
        """
        touched = {}
        for marker in markers:
            bucket = self._bucket(marker)
            touched[bucket] = touched.get(bucket, 0) + 1
        return sum(
            max(
                3 * sys.getsizeof(self._shards[bucket]),
                256 + 128 * (len(self._shards[bucket]) + count),
            )
            - sys.getsizeof(self._shards[bucket])
            for bucket, count in touched.items()
        )

    def clear(self):
        for shard in self._shards:
            before = sys.getsizeof(shard)
            shard.clear()
            self.storage_size += sys.getsizeof(shard) - before
        self._count = 0


class _BytesBundle(tuple):
    """One fresh owned payload, whose raw bytes are cached by its entry/node."""

    __slots__ = ()


class _Lease:
    __slots__ = ("_account", "_size", "_kind", "_objects", "_released")

    def __init__(self):
        self._account = None
        self._released = False

    def release(self):
        if self._account is not None and not self._released:
            self._released = True
            self._account._release(self._size, self._kind, self._objects)

    def resize(self, size):
        """Adjust one caller reservation without allocating another lease."""
        if type(size) is not int or size < 0 or self._account is None or self._released:
            raise CommitmentError("sync_allocation_reservation")
        account = self._account
        with account._lock:
            difference = size - self._size
            if account._used + difference > account.limit:
                raise BudgetExceeded("sync_allocation_limit")
            account._used += difference
            account._peak = max(account._peak, account._used)
            account._totals[self._kind] += difference
            self._size = size

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass


class AllocationAccount:
    """Incremental retained-allocation budget shared by maps and owner buffers.

    Nodes own their allocation directly; maps and caller buffers use leases.
    Immutable payload objects are indexed
    by identity and charged once across retained roots and full/active maps.
    Reclamation releases only the allocation being destroyed; no cache scan.
    Sizes include sys.getsizeof containers plus conservative index/lease overhead.
    Temporary parsing/canonicalization belongs to the caller's staging envelope.
    """

    # _Held (two slots) and its integer identity key. Non-small reference
    # counters are charged at their actual allocation size on each transition.
    # Size/kind are derived from the immutable value, not duplicate sidecars.
    INDEX_OVERHEAD = sys.getsizeof(_Held(None, 0)) + sys.getsizeof(id(None))
    ENCODED_OVERHEAD = sys.getsizeof(_EncodedHeld(None, 0, b"")) - sys.getsizeof(_Held(None, 0))
    LEASE_OVERHEAD = 128
    KINDS = (
        "nodes",
        "value_bytes",
        "containers",
        "external",
        "encoded",
        "queue",
        "stage",
        "accounting",
    )

    def __init__(self, limit=DEFAULT_ALLOCATION_LIMIT):
        if type(limit) is not int or limit < 1:
            raise CommitmentError("sync_allocation_limit")
        self._limit = limit
        self._held = _IdentityIndex()
        self._registry_base = self._held.storage_size
        self._totals = dict.fromkeys(self.KINDS, 0)
        self._lock = threading.RLock()
        self._base = (
            sys.getsizeof(self)
            + sys.getsizeof(self.__dict__)
            + self._held.storage_size
            + sys.getsizeof(self._totals)
            + sys.getsizeof(self._lock)
            + 1024
            + sys.getsizeof(_SMALL_REFS)
            + sum(map(sys.getsizeof, _SMALL_REFS))
        )
        if self._base > limit:
            raise BudgetExceeded("sync_allocation_limit")
        self._used = self._peak = self._base
        self._totals["accounting"] = self._base
        self._created = self._reclaimed = self._leases = self._objects_created = 0
        self._sidecars = 0
        self._registry_slots = 0
        self._registry_reserved = 0

    @property
    def limit(self):
        return self._limit

    def reserve(self, size, *, kind="external"):
        """Reserve a caller-owned buffer once; keep/share its lease until release."""
        return self._retain(size, kind, ())

    def retain_json(self, value, size=0, *, kind="external"):
        """Retain immutable JSON once across maps and caller-owned generations.

        The lease owns its frozen copy; callers that also need the value should
        call ``freeze`` once and pass that immutable result here and elsewhere.
        ``size`` additionally reserves a caller's shallow enclosing allocation.
        """
        return self._retain(size, kind, _owned_objects((freeze(value),)))

    def retain_bytes(self, *buffers, size=0, kind="encoded", credit=None):
        """Share exact immutable buffers across cache and delivery lifetimes.

        Equal copied buffers remain separate allocations. Optional constructor
        credit transfers atomically after construction; caller metadata and
        the returned lease are separately paid. This does not grant authority
        or reserve an independent encoded-byte budget.
        """
        try:
            if any(type(value) is not bytes for value in buffers):
                raise CommitmentError("sync_allocation_bytes")
            return self._retain(size, kind,
                                ((value, sys.getsizeof(value), "value_bytes") for value in buffers),
                                credit=credit)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            buffers = credit = None
            raise

    def json_arena(self, *, kind="stage"):
        """Incrementally own JSON roots with one arena, without per-row leases."""
        return _JSONArena(self, kind)

    def _retain(self, size, kind, objects, *, credit=None):
        if type(size) is not int or size < 0 or kind not in self.KINDS:
            raise CommitmentError("sync_allocation_reservation")
        unique = {
            id(value): (value, value_size, value_kind) for value, value_size, value_kind in objects
        }
        lease = _Lease()
        markers = tuple(unique)
        overhead = (
            sys.getsizeof(lease)
            + self.LEASE_OVERHEAD
            + sys.getsizeof(markers)
            + sum(sys.getsizeof(marker) for marker in markers)
        )
        self._acquire(size, kind, unique, overhead=overhead, credit=credit)
        lease._account, lease._size, lease._kind = self, size, kind
        lease._objects = (markers, overhead)
        with self._lock:
            self._sidecars += 1
        return lease

    def _encoding(self, value):
        if type(value) is str:
            with self._lock:
                held = self._held.get(id(value))
                if isinstance(held, _EncodedHeld):
                    return held.encoded
        return None

    def _acquire(
        self, size, kind, unique, *, overhead=0, payload=0, encodings=(), credit=None, credit_keep=0
    ):
        """Own one allocation, without a sidecar lease for tree nodes.

        Fresh canonical/hash bytes belong to their immutable node and need no
        identity registry entry. Only reusable JSON graphs enter that registry.
        """
        with self._lock:
            credit_size = 0
            if credit is not None:
                if (
                    credit._account is not self
                    or credit._released
                    or type(credit_keep) is not int
                    or not 0 <= credit_keep <= credit._size
                ):
                    raise CommitmentError("sync_allocation_credit")
                credit_size = credit._size - credit_keep
            planned, pending = {}, list(unique.values())
            while pending:
                value, value_size, value_kind = pending.pop()
                marker = id(value)
                if marker in self._held or marker in planned:
                    continue
                children = {id(child): child for child in _owned_children(value)}
                planned[marker] = (value, value_size, value_kind)
                pending.extend(_owned_objects(children.values()))
            increments = dict.fromkeys(unique, 1)
            for value, _, _ in planned.values():
                for marker in {id(child) for child in _owned_children(value)}:
                    increments[marker] = increments.get(marker, 0) + 1
            ref_growth = sum(
                _ref_bytes((self._held[marker].refs if marker in self._held else 0) + count)
                - _ref_bytes(self._held[marker].refs if marker in self._held else 0)
                for marker, count in increments.items()
            )
            new_encodings = {
                marker: encoded
                for marker, encoded in dict(encodings).items()
                if not isinstance(self._held.get(marker), _EncodedHeld)
            }
            encoding_bytes = sum(map(sys.getsizeof, new_encodings.values()))
            encoding_overhead = len(new_encodings) * self.ENCODED_OVERHEAD
            added = (
                size
                + payload
                + overhead
                + sum(value_size + self.INDEX_OVERHEAD for _, value_size, _ in planned.values())
            )
            added += ref_growth
            added += encoding_bytes + encoding_overhead
            registry_before = self._held.storage_size
            registry_growth = self._held.growth_bound(planned)
            added += registry_growth
            if self._used + added - credit_size > self.limit:
                raise BudgetExceeded("sync_allocation_limit")
            # New containers/claim slots were already backed while they were
            # constructed. Reclassify that reservation under the same lock;
            # remaining caller scratch stays reserved through this method.
            self._used += added - credit_size
            if credit is not None:
                credit._size -= credit_size
                self._totals[credit._kind] -= credit_size
            self._peak = max(self._peak, self._used)
            self._totals[kind] += size
            self._totals["value_bytes"] += payload
            self._totals["value_bytes"] += encoding_bytes
            self._totals["accounting"] += overhead
            self._totals["accounting"] += ref_growth
            self._totals["accounting"] += encoding_overhead
            self._totals["accounting"] += registry_growth
            for marker, (value, value_size, value_kind) in planned.items():
                self._held[marker] = _Held(value, 0)
                self._totals[value_kind] += value_size
                self._totals["accounting"] += self.INDEX_OVERHEAD
                self._objects_created += 1
            for marker, encoded in new_encodings.items():
                held = self._held[marker]
                self._held[marker] = _EncodedHeld(held.value, held.refs, encoded)
            for marker, count in increments.items():
                refs = self._held[marker].refs + count
                self._held[marker].refs = _SMALL_REFS[refs] if refs <= 256 else refs
            actual_growth = self._held.storage_size - registry_before
            if actual_growth > registry_growth:
                raise AssertionError("identity index growth bound")
            refund = registry_growth - actual_growth
            self._used -= refund
            self._totals["accounting"] -= refund
            self._registry_reserved = self._held.storage_size - self._registry_base
            self._registry_slots = max(self._registry_slots, len(self._held))
            self._created += 1
            self._leases += 1

    def _release(self, size, kind, objects):
        markers, overhead = objects
        self._drop(size, kind, markers, overhead=overhead)
        with self._lock:
            self._sidecars -= 1

    def _drop(self, size, kind, markers, *, overhead=0, payload=0):
        with self._lock:
            registry_before = self._held.storage_size
            self._used -= size + payload + overhead
            self._totals[kind] -= size
            self._totals["value_bytes"] -= payload
            self._totals["accounting"] -= overhead
            pending = list(markers)
            while pending:
                marker = pending.pop()
                held = self._held[marker]
                refs = held.refs - 1
                difference = _ref_bytes(refs) - _ref_bytes(held.refs)
                self._used += difference
                self._totals["accounting"] += difference
                held.refs = _SMALL_REFS[refs] if refs <= 256 else refs
                if held.refs == 0:
                    _, value_size, value_kind = next(_owned_objects((held.value,)))
                    self._used -= value_size + self.INDEX_OVERHEAD
                    self._totals[value_kind] -= value_size
                    self._totals["accounting"] -= self.INDEX_OVERHEAD
                    if isinstance(held, _EncodedHeld):
                        encoded_size = sys.getsizeof(held.encoded)
                        self._used -= encoded_size + self.ENCODED_OVERHEAD
                        self._totals["value_bytes"] -= encoded_size
                        self._totals["accounting"] -= self.ENCODED_OVERHEAD
                    pending.extend({id(child) for child in _owned_children(held.value)})
                    del self._held[marker]
            if not self._held and self._registry_slots:
                # Dict deletion retains capacity. Exact shard capacity stays
                # charged until the index empties, when all shards are cleared.
                self._held.clear()
                self._registry_slots = 0
            capacity_change = self._held.storage_size - registry_before
            self._used += capacity_change
            self._totals["accounting"] += capacity_change
            self._registry_reserved = self._held.storage_size - self._registry_base
            self._reclaimed += 1
            self._leases -= 1

    def snapshot(self):
        with self._lock:
            return {
                "limit": self.limit,
                "used": self._used,
                "peak": self._peak,
                "base": self._base,
                "leases": self._sidecars,
                "allocations": self._leases,
                "objects": len(self._held),
                "created": self._created,
                "reclaimed": self._reclaimed,
                "objectsCreated": self._objects_created,
                "registrySlots": self._registry_slots,
                "registryReserved": self._registry_reserved,
                "registryBase": self._registry_base,
                "registryBytes": self._held.storage_size,
                "byKind": dict(self._totals),
            }


class _FreezePlan:
    __slots__ = ("object", "children", "fresh_size")

    def __init__(self, object_value, children, fresh_size):
        self.object, self.children, self.fresh_size = object_value, children, fresh_size


_POINTER_SIZE = sys.getsizeof((None,)) - sys.getsizeof(())
_TUPLE_SIZE = sys.getsizeof(())
_FROZEN_OBJECT_SIZE = sys.getsizeof(object.__new__(_FrozenObject))
_FREEZE_PLAN_SIZE = sys.getsizeof(_FreezePlan(False, None, 0)) + 32


def _materialize_plan(value):
    if not isinstance(value, _FreezePlan):
        return value
    children = value.children
    for index in range(1 if value.object else 0, len(children), 2 if value.object else 1):
        children[index] = _materialize_plan(children[index])
    if value.object:
        result = object.__new__(_FrozenObject)
        object.__setattr__(result, "_items", tuple(children))
        return result
    return tuple.__new__(_FrozenArray, children)


class _JSONConstruction:
    """Prepaid value-local plan, then one atomic graph ownership transfer.

    Analysis creates no Frozen containers. Scratch is prepaid in 4 KiB blocks,
    including recursion, list/dict/set resize overlap and retained plan nodes.
    Acquire scratch is separately retained through adoption: 4096 control bytes
    plus 512 per unowned node and 384 per distinct parent-child edge. This covers
    planned/increments/pending/children dictionaries and tuples on CPython 3.11+;
    immutable source payloads and existing indexed subtrees are not copied.
    """

    BASE = 4096
    BLOCK = 4096
    FRAME = 1024

    __slots__ = (
        "account",
        "lease",
        "live",
        "fresh",
        "array_scratch",
        "max_depth",
        "nodes",
        "edges",
        "active",
        "active_credit",
        "future",
        "future_credit",
    )

    def __init__(self, account, priors):
        self.account, self.live, self.fresh, self.array_scratch, self.max_depth = (
            account,
            0,
            0,
            0,
            0,
        )
        self.nodes = self.edges = 0
        # This same planning lease pins exact owned priors throughout analysis
        # and construction, including callbacks from arbitrary Mapping inputs.
        self.lease = account._retain(
            self.BASE, "stage", _owned_objects(prior for prior in priors if prior is not ABSENT)
        )
        self.active, self.future = set(), set()
        self.active_credit = sys.getsizeof(self.active)
        self.future_credit = sys.getsizeof(self.future)

    def grow(self, amount):
        needed = self.BASE + self.live + amount
        if needed > self.lease._size:
            self.lease.resize(((needed + self.BLOCK - 1) // self.BLOCK) * self.BLOCK)
        self.live += amount

    def release(self, amount):
        self.live -= amount

    def _add_set(self, values, marker, credit):
        needed = max(3 * sys.getsizeof(values), 256 + 128 * (len(values) + 1))
        if needed > credit:
            self.grow(needed - credit)
            credit = needed
        self.grow(sys.getsizeof(marker))
        values.add(marker)
        return credit

    def note(self, value):
        marker = id(value)
        if marker in self.account._held or marker in self.future:
            return False
        self.future_credit = self._add_set(self.future, marker, self.future_credit)
        self.nodes += 1
        return True

    def child_edges(self, children):
        seen, credit, markers = set(), 0, 0
        try:
            self.grow(sys.getsizeof(seen))
            credit = sys.getsizeof(seen)
            for child in children:
                marker = id(child)
                if marker not in seen:
                    credit = self._add_set(seen, marker, credit)
                    markers += sys.getsizeof(marker)
            self.edges += len(seen)
        finally:
            seen.clear()
            self.release(credit + markers)

    def existing(self, value, depth):
        self.grow(self.FRAME)
        try:
            self.max_depth = max(self.max_depth, depth)
            if self.note(value):
                children = _owned_children(value)
                self.child_edges(children)
                for child in children:
                    self.existing(child, depth + 1)
        finally:
            self.release(self.FRAME)

    def append(self, children, values, credit):
        needed = max(3 * sys.getsizeof(children), 128 + 16 * (len(children) + len(values)))
        if needed > credit:
            self.grow(needed - credit)
            credit = needed
        children.extend(values)
        actual = sys.getsizeof(children)
        self.release(credit - actual)
        return actual

    def visit(self, item, old, depth=1):
        self.grow(self.FRAME)
        self.max_depth = max(self.max_depth, depth)
        marker, entered = None, False
        previous_credit = children_credit = seen_credit = seen_markers = 0
        children, seen = None, None
        keep_children = False
        try:
            if item is None or type(item) in (bool, int, str):
                if type(item) is str:
                    _string(item)
                result = old if type(item) is type(old) and item == old else item
                self.note(result)
                return result
            if type(item) in (_FrozenObject, _FrozenArray) and (item is old or old is ABSENT):
                self.existing(item, depth)
                return item
            if not isinstance(item, (Mapping, list, tuple)):
                raise CommitmentError("sync_json_type")
            marker = id(item)
            if marker in self.active:
                raise CommitmentError("sync_json_cycle")
            self.active_credit = self._add_set(self.active, marker, self.active_credit)
            entered = True
            object_value = isinstance(item, Mapping)
            if object_value:
                if type(old) is _FrozenObject:
                    previous_credit = 256 + 128 * len(old)
                    self.grow(previous_credit)
                    previous = dict(old.items())
                else:
                    previous = {}
                same = type(old) is _FrozenObject
                if type(item) not in (dict, _FrozenObject):
                    seen = set()
                    seen_credit = sys.getsizeof(seen)
                    self.grow(seen_credit)
            else:
                previous = old if type(old) is _FrozenArray else ()
                same = type(old) is _FrozenArray
            children = []
            children_credit = sys.getsizeof(children)
            self.grow(children_credit)
            if object_value:
                for key, child in item.items():
                    _string(key)
                    if seen is not None:
                        if key in seen:
                            raise CommitmentError("sync_duplicate_key")
                        # Seen mapping keys are borrowed strings; only the set
                        # slots are new, unlike integer identity markers.
                        needed = max(3 * sys.getsizeof(seen), 256 + 128 * (len(seen) + 1))
                        if needed > seen_credit:
                            self.grow(needed - seen_credit)
                            seen_credit = needed
                        seen.add(key)
                    earlier = previous.get(key, ABSENT)
                    result = self.visit(child, earlier, depth + 1)
                    same = same and earlier is not ABSENT and result is earlier
                    children_credit = self.append(children, (key, result), children_credit)
                same = same and len(children) == 2 * len(previous)
            else:
                for index, child in enumerate(item):
                    earlier = previous[index] if index < len(previous) else ABSENT
                    result = self.visit(child, earlier, depth + 1)
                    same = same and earlier is not ABSENT and result is earlier
                    children_credit = self.append(children, (result,), children_credit)
                same = same and len(children) == len(previous)
            if same:
                return old
            self.grow(_FREEZE_PLAN_SIZE)
            fresh_size = _TUPLE_SIZE + _POINTER_SIZE * len(children)
            if object_value:
                fresh_size += _FROZEN_OBJECT_SIZE
                for index in range(0, len(children), 2):
                    self.note(children[index])
            else:
                # CPython tuple subclass construction holds an intermediate
                # plain tuple alongside the resulting FrozenArray.
                self.array_scratch = max(self.array_scratch, fresh_size)
            plan = _FreezePlan(object_value, children, fresh_size)
            self.note(plan)
            self.child_edges(children)
            self.fresh += fresh_size
            keep_children = True
            return plan
        finally:
            if entered:
                self.active.remove(marker)
                self.release(sys.getsizeof(marker))
            if children is not None and not keep_children:
                children.clear()
                self.release(children_credit)
            if seen is not None:
                seen.clear()
            self.release(previous_credit + seen_credit + seen_markers + self.FRAME)

    def acquire_scratch(self, root_count):
        return self.BASE + 512 * (self.nodes + root_count) + 384 * self.edges

    def before_build(self, claim_size, root_count):
        # All final containers and the largest constructor copy are backed
        # before the first Frozen object is allocated.
        build = (
            self.BASE
            + self.live
            + self.fresh
            + self.array_scratch
            + self.FRAME * self.max_depth
            + claim_size
        )
        adopt = self.acquire_scratch(root_count) + self.fresh + claim_size
        self.lease.resize(max(build, adopt))

    def before_adopt(self, claim_size, root_count):
        self.active.clear()
        self.future.clear()
        scratch = self.acquire_scratch(root_count)
        self.lease.resize(scratch + self.fresh + claim_size)
        return scratch

    def close(self):
        self.active.clear()
        self.future.clear()
        self.lease.release()


class _JSONArena:
    """Bounded staging ownership; additions touch only the supplied JSON.

    Each claim stores one shallow tuple of frozen roots. JSON graphs share the
    account's exact identity ledger with maps and other claims; no JSON wrapper
    is created or registered merely to own multiple roots. Close releases all
    claims explicitly in O(number of claims plus reclaimed JSON).
    """

    __slots__ = ("_account", "_kind", "_claims", "_lease", "_closed", "_lock")

    def __init__(self, account, kind):
        self._account, self._kind = account, kind
        self._claims, self._lease, self._closed = [], None, True
        self._lock = threading.RLock()
        self._lease = account.reserve(self._storage_size(), kind=kind)
        self._closed = False

    def _storage_size(self):
        return sys.getsizeof(self) + sys.getsizeof(self._lock) + sys.getsizeof(self._claims)

    def retain_json(self, *values, priors=None):
        """Return frozen roots, owned until close or another owner retains them.

        Fresh frozen containers, analysis/construction/acquire scratch and root
        slots are reserved before construction/adoption. Optional priors are
        an exact-length tuple of ABSENT or immutable roots already owned by this
        account. Exact unchanged subtrees are shared without freshness inference.
        A rejected addition leaves earlier claims intact.
        Returned roots are immutable; retaining them beyond this arena's life
        requires their caller/map to keep its own ownership claim.
        """
        with self._lock, self._account._lock:
            if self._closed or not values:
                raise CommitmentError("sync_json_arena_closed_or_empty")
            if priors is not None:
                if type(priors) is not tuple or len(priors) != len(values):
                    raise CommitmentError("sync_json_arena_priors")
                for prior in priors:
                    if prior is ABSENT:
                        continue
                    if (
                        type(prior) not in (_FrozenObject, _FrozenArray, str, int, bool, type(None))
                        or id(prior) not in self._account._held
                    ):
                        raise CommitmentError("sync_json_arena_priors")
            before = self._storage_size()
            header = sys.getsizeof(self) + sys.getsizeof(self._lock)
            # Covers old/new list-buffer overlap, root tuple and one pointer
            # slot before append. Replace scratch with actual capacity below.
            capacity = max(3 * sys.getsizeof(self._claims), 128 + 16 * (len(self._claims) + 1))
            self._lease.resize(header + capacity)
            acquired, claim, construction, plans, objects = False, None, None, None, None
            try:
                construction = _JSONConstruction(self._account, () if priors is None else priors)
                construction.grow(128 + 16 * len(values))
                plans = [None] * len(values)
                for index, value in enumerate(values):
                    plans[index] = construction.visit(
                        value, ABSENT if priors is None else priors[index]
                    )
                construction.before_build(sys.getsizeof(values), len(values))
                claim = tuple(_materialize_plan(plan) for plan in plans)
                plans.clear()
                scratch = construction.before_adopt(sys.getsizeof(claim), len(claim))
                objects = {
                    id(value): (value, size, kind) for value, size, kind in _owned_objects(claim)
                }
                self._account._acquire(
                    sys.getsizeof(claim),
                    self._kind,
                    objects,
                    credit=construction.lease,
                    credit_keep=scratch,
                )
                acquired = True
                self._claims.append(claim)
            except BaseException as error:
                # Internal traceback frames otherwise keep rejected plans,
                # new Frozen containers and acquire dictionaries alive after
                # their construction reservation is released. The stable
                # error type/code remains available to the caller.
                error.__traceback__ = None
                if acquired:
                    self._account._drop(
                        sys.getsizeof(claim), self._kind, {id(value) for value in claim}
                    )
                claim = plans = objects = None
                if construction is not None:
                    construction.close()
                    construction = None
                self._lease.resize(before)
                raise error from None
            finally:
                if construction is not None:
                    construction.close()
            self._lease.resize(self._storage_size())
            return claim

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                while self._claims:
                    claim = self._claims.pop()
                    self._account._drop(
                        sys.getsizeof(claim), self._kind, {id(value) for value in claim}
                    )
                self._lease.release()

    def __enter__(self):
        if self._closed:
            raise CommitmentError("sync_json_arena_closed_or_empty")
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def _owned_objects(values):
    for value in values:
        if isinstance(value, _FrozenObject):
            yield value, sys.getsizeof(value) + sys.getsizeof(value._items), "containers"
        elif isinstance(value, _FrozenArray):
            yield value, sys.getsizeof(value), "containers"
        elif isinstance(value, _BytesBundle):
            children = {id(child): child for child in value}
            yield (
                value,
                sys.getsizeof(value) + sum(sys.getsizeof(child) for child in children.values()),
                "value_bytes",
            )
        else:
            yield value, sys.getsizeof(value), "value_bytes"


def _owned_children(value):
    if isinstance(value, _FrozenObject):
        return value._items
    if isinstance(value, _FrozenArray):
        return value
    return ()


@dataclass(frozen=True, slots=True)
class MapStats:
    visits: int = 0
    path_visits: int = 0
    leaf_visits: int = 0
    hashes: int = 0
    created_nodes: int = 0
    enumerated_keys: int = 0
    changed: bool = False


@dataclass(slots=True)
class VisitMeter:
    visits: int = 0
    hashes: int = 0
    lookups: int = 0
    iterations: int = 0


@dataclass(slots=True)
class _Work:
    visits: int = 0
    path_visits: int = 0
    leaf_visits: int = 0
    hashes: int = 0
    created_nodes: int = 0
    enumerated_keys: int = 0
    changed: bool = False

    def stats(self):
        return MapStats(
            self.visits,
            self.path_visits,
            self.leaf_visits,
            self.hashes,
            self.created_nodes,
            self.enumerated_keys,
            self.changed,
        )


@dataclass(slots=True)
class _PatchOp:
    kind: str
    key: object
    key_bytes: bytes
    digest: bytes
    expected: bytes | None
    value: object = None
    old: object = None
    new: object = None


@dataclass(frozen=True, slots=True)
class _Leaf:
    key: object
    value: object
    key_bytes: bytes
    value_bytes: bytes
    _hashes: bytes
    _account: object = field(default=None, repr=False, compare=False)

    @property
    def entry(self):
        # Kept as a private alias to avoid duplicate entry/leaf containers.
        return self

    @property
    def sample(self):
        return self.key_digest

    @property
    def key_digest(self):
        return self._hashes[:32]

    @property
    def value_digest(self):
        return self._hashes[32:64]

    @property
    def digest(self):
        return self._hashes[64:]

    @property
    def count(self):
        return 1

    @property
    def nodes(self):
        return 1

    @property
    def pair_bytes(self):
        return len(self.key_bytes) + len(self.value_bytes) + 3

    def _payload_size(self):
        # String values have a bounded account-local canonical atom shared by
        # global/grouped cells. V stays per space; no owner/digest domains merge.
        values = (self.key_bytes, self._hashes)
        if type(self.value) is not str:
            values += (self.value_bytes,)
        return sum(
            sys.getsizeof(value) for value in {id(value): value for value in values}.values()
        )

    def __del__(self):
        account = self._account
        if account is not None:
            account._drop(
                sys.getsizeof(self),
                "nodes",
                {id(self.key), id(self.value)},
                payload=self._payload_size(),
            )


@dataclass(frozen=True, slots=True)
class _Branch:
    split: int
    _hashes: bytes
    left: object
    right: object
    _sample: object = field(repr=False, compare=False)
    count: int
    nodes: int
    pair_bytes: int
    _account: object = field(default=None, repr=False, compare=False)

    @property
    def sample(self):
        return self._sample.key_digest

    @property
    def prefix(self):
        return self._hashes[:-32]

    @property
    def digest(self):
        return self._hashes[-32:]

    def _own_size(self):
        # Aggregates outside the interpreter's shared small-integer pool are
        # new allocations belonging to this node, unlike its borrowed sample.
        return sys.getsizeof(self) + sum(
            sys.getsizeof(value)
            for value in {
                id(value): value
                for value in (self.count, self.nodes, self.pair_bytes)
                if value > 256
            }.values()
        )

    def _payload_size(self):
        return sys.getsizeof(self._hashes)

    def __del__(self):
        account = self._account
        if account is not None:
            account._drop(self._own_size(), "nodes", (), payload=self._payload_size())


def _common_bits(left, right):
    return 256 - (int.from_bytes(left, "big") ^ int.from_bytes(right, "big")).bit_length()


def _bit(value, position):
    return (value[position // 8] >> (7 - position % 8)) & 1


def _prefix(value, length):
    whole, remainder = divmod(length, 8)
    return value[:whole] + (bytes((value[whole] & (255 << (8 - remainder)),)) if remainder else b"")


class PersistentMap:
    """Immutable map; ANY upserts, None expects absence, hex expects exact V.

    ``encoded_size`` is exactly C([[key,value],...]) in hash-key traversal order:
    each pair contributes len(Ckey)+len(Cvalue)+3, plus outer brackets/commas.
    Baseline construction explicitly sorts N hashes, then creates each leaf and
    branch once. Point mutations never export, sort or walk the full roster.
    ``last_update`` reports its bounded path work.
    """

    __slots__ = (
        "space",
        "account",
        "_space",
        "_empty",
        "_storage",
        "_node",
        "last_update",
        "meter",
        "_lease",
    )

    def __setattr__(self, name, value):
        raise AttributeError("immutable PersistentMap")

    def __init__(self, space, entries=(), *, account=None):
        raw_space = _space(space)
        budget = account if account is not None else AllocationAccount()
        if not isinstance(budget, AllocationAccount):
            raise CommitmentError("sync_allocation_account")
        object.__setattr__(self, "space", space)
        object.__setattr__(self, "account", budget)
        object.__setattr__(self, "_space", raw_space)
        object.__setattr__(self, "_empty", _hash(b"mesh-sync-empty\0" + frame(raw_space)))
        object.__setattr__(self, "_storage", _BytesBundle((raw_space, self._empty)))
        object.__setattr__(self, "_node", None)
        work = _Work(hashes=1)
        object.__setattr__(self, "last_update", work.stats())
        object.__setattr__(self, "meter", VisitMeter())
        self._charge_map()
        entries = entries.items() if isinstance(entries, Mapping) else entries
        leaves = []
        with budget.reserve(sys.getsizeof(leaves), kind="stage") as stage:
            for key, value in entries:
                # Covers list growth and sort's key/value pointer scratch space
                # before the next append; no second tree or mutable DTO copy.
                stage.resize(sys.getsizeof(leaves) + 32 * (len(leaves) + 1))
                work.changed = True
                work.enumerated_keys += 1
                frozen_key = freeze(key)
                key_bytes = canonical(frozen_key)
                digest = _key_digest(raw_space, key_bytes)
                work.hashes += 1
                entry = self._entry(frozen_key, key_bytes, digest, value, work)
                leaves.append(self._leaf(entry, work))
            stage.resize(sys.getsizeof(leaves) + 32 * len(leaves))
            # The initial 32 bytes are K; use the owned blob directly so sort
            # does not allocate one sliced key per entry.
            leaves.sort(key=lambda entry: entry._hashes)
            for index in range(1, len(leaves)):
                if leaves[index - 1].key_digest == leaves[index].key_digest:
                    reason = (
                        "sync_duplicate_key"
                        if leaves[index - 1].key_bytes == leaves[index].key_bytes
                        else "sync_key_hash_collision"
                    )
                    raise CommitmentError(reason)
            object.__setattr__(self, "_node", self._build(leaves, 0, len(leaves), work))
        object.__setattr__(self, "last_update", work.stats())

    def _build(self, leaves, start, stop, work):
        if start == stop:
            return None
        if stop - start == 1:
            return leaves[start]
        split = _common_bits(leaves[start].key_digest, leaves[stop - 1].key_digest)
        low, high = start + 1, stop - 1
        while low < high:
            middle = (low + high) // 2
            if _bit(leaves[middle].key_digest, split):
                high = middle
            else:
                low = middle + 1
        return self._branch(
            split, self._build(leaves, start, low, work), self._build(leaves, low, stop, work), work
        )

    def _charge_map(self):
        lease = self.account._retain(
            sys.getsizeof(self) + sys.getsizeof(self.last_update) + sys.getsizeof(self.meter),
            "containers",
            _owned_objects((self.space, self._storage)),
        )
        object.__setattr__(self, "_lease", lease)

    def _new(self, node, work):
        result = object.__new__(PersistentMap)
        for name, value in (
            ("space", self.space),
            ("account", self.account),
            ("_space", self._space),
            ("_empty", self._empty),
            ("_node", node),
            ("_storage", self._storage),
            ("last_update", work.stats()),
            ("meter", VisitMeter()),
        ):
            object.__setattr__(result, name, value)
        result._charge_map()
        return result

    @property
    def root(self):
        return (self._node.digest if self._node is not None else self._empty).hex()

    @property
    def count(self):
        return self._node.count if self._node is not None else 0

    @property
    def node_count(self):
        return self._node.nodes if self._node is not None else 0

    @property
    def encoded_size(self):
        return self._node.pair_bytes + self.count + 1 if self._node is not None else 2

    def __len__(self):
        return self.count

    def _find(self, digest, key_bytes, work, *, record_path=True):
        node, path = self._node, []
        while node is not None:
            work.visits += 1
            if isinstance(node, _Leaf):
                work.leaf_visits += 1
                if node.sample == digest and node.entry.key_bytes != key_bytes:
                    raise CommitmentError("sync_key_hash_collision")
                return node, path
            work.path_visits += 1
            if _common_bits(digest, node.sample) < node.split:
                return node, path
            right = _bit(digest, node.split)
            if record_path:
                path.append((node, right))
            node = node.right if right else node.left
        return None, path

    def _entry(self, key, key_bytes, digest, value, work, prepared=None):
        frozen, value_bytes = prepared if prepared is not None else (freeze(value), None)
        cached = self.account._encoding(frozen)
        value_bytes = (
            cached
            if cached is not None
            else canonical(frozen)
            if value_bytes is None
            else value_bytes
        )
        value_digest = _value_digest(self._space, value_bytes)
        leaf_digest = _hash(
            b"mesh-sync-leaf\0" + frame(self._space) + digest + frame(key_bytes) + value_digest
        )
        work.hashes += 2
        entry = _Leaf(key, frozen, key_bytes, value_bytes, digest + value_digest + leaf_digest)
        objects = {
            id(item): (item, size, kind) for item, size, kind in _owned_objects((key, frozen))
        }
        encodings = {id(frozen): value_bytes} if type(frozen) is str else ()
        self.account._acquire(
            sys.getsizeof(entry),
            "nodes",
            objects,
            payload=entry._payload_size(),
            encodings=encodings,
        )
        object.__setattr__(entry, "_account", self.account)
        return entry

    def _leaf(self, entry, work):
        work.created_nodes += 1
        return entry

    def _branch(self, split, left, right, work):
        if not 0 <= split <= 255 or left is None or right is None:
            raise CommitmentError("sync_invalid_branch")
        prefix = _prefix(left.sample, split)
        digest = _hash(
            b"mesh-sync-branch\0"
            + frame(self._space)
            + u16(split)
            + frame(prefix)
            + left.digest
            + right.digest
        )
        work.hashes += 1
        sample = left if isinstance(left, _Leaf) else left._sample
        result = _Branch(
            split,
            prefix + digest,
            left,
            right,
            sample,
            left.count + right.count,
            left.nodes + right.nodes + 1,
            left.pair_bytes + right.pair_bytes,
        )
        self.account._acquire(result._own_size(), "nodes", {}, payload=result._payload_size())
        object.__setattr__(result, "_account", self.account)
        work.created_nodes += 1
        return result

    def _rebuild(self, path, result, work):
        for parent, right in reversed(path):
            result = self._branch(
                parent.split,
                parent.left if right else result,
                result if right else parent.right,
                work,
            )
        return result

    def _insert(self, found, path, entry, work):
        result = self._leaf(entry, work)
        if found is not None and found.sample != entry.key_digest:
            split = _common_bits(found.sample, entry.key_digest)
            result = (
                self._branch(split, found, result, work)
                if _bit(entry.key_digest, split)
                else self._branch(split, result, found, work)
            )
        return self._rebuild(path, result, work)

    @staticmethod
    def _expected(found, expected):
        if expected is ANY:
            return
        if expected is None:
            if found is not None:
                raise CommitmentError("sync_expected_absent")
            return
        expected_bytes = _hex_bytes(expected)
        if found is None or found.entry.value_digest != expected_bytes:
            raise CommitmentError("sync_expected_value")

    def _lookup_entry(self, key, meter):
        key_bytes = canonical(key)
        work = _Work(hashes=1)
        digest = _key_digest(self._space, key_bytes)
        found, _ = self._find(digest, key_bytes, work, record_path=False)
        target = self.meter if meter is None else meter
        target.visits += work.visits
        target.hashes += work.hashes
        target.lookups += 1
        return found.entry if isinstance(found, _Leaf) and found.sample == digest else ABSENT

    def get(self, key, default=ABSENT, *, meter=None):
        entry = self._lookup_entry(key, meter)
        return entry.value if entry is not ABSENT else default

    def lookup(self, key, default=ABSENT, *, meter=None):
        """One keyed traversal returns immutable value and its cached V digest."""
        entry = self._lookup_entry(key, meter)
        return (entry.value, entry.value_digest.hex()) if entry is not ABSENT else default

    def get_hash(self, key, default=ABSENT, *, meter=None):
        entry = self._lookup_entry(key, meter)
        return entry.value_digest.hex() if entry is not ABSENT else default

    def lookup_encoded(self, key, default=ABSENT, *, meter=None):
        """Point lookup of the cached C(key), C(value) bytes, without export."""
        entry = self._lookup_entry(key, meter)
        return (entry.key_bytes, entry.value_bytes) if entry is not ABSENT else default

    def lookup_entry(self, key, default=ABSENT, *, meter=None):
        """Owned key/value, cached V and canonical bytes from one point lookup."""
        entry = self._lookup_entry(key, meter)
        return (
            (entry.key, entry.value, entry.value_digest.hex(), entry.key_bytes, entry.value_bytes)
            if entry is not ABSENT
            else default
        )

    def _patch_key_size(self, key):
        """Temporary new key graph; already owned frozen subgraphs cost zero."""
        pending, seen, size = [key], set(), 0
        with self.account._lock:
            while pending:
                value = pending.pop()
                marker = id(value)
                if marker in seen or marker in self.account._held:
                    continue
                seen.add(marker)
                _, amount, _ = next(_owned_objects((value,)))
                size += amount
                pending.extend(_owned_children(value))
        return size

    @staticmethod
    def _patch_boundary(changes, start, stop, split):
        while start < stop:
            middle = (start + stop) // 2
            if _bit(changes[middle].digest, split):
                stop = middle
            else:
                start = middle + 1
        return start

    @staticmethod
    def _patch_expected(change, found):
        if found is None:
            if change.kind == "remove":
                raise CommitmentError("sync_key_absent")
            if change.expected is not None:
                raise CommitmentError("sync_expected_value")
        else:
            if found.key_bytes != change.key_bytes:
                raise CommitmentError("sync_key_hash_collision")
            if change.expected is None:
                raise CommitmentError("sync_expected_absent")
            if found.value_digest != change.expected:
                raise CommitmentError("sync_expected_value")
        change.old = found

    def _patch_visit(self, node, changes, start, stop, work, *, apply):
        if start == stop:
            return node
        if node is None:
            if not apply:
                for index in range(start, stop):
                    self._patch_expected(changes[index], None)
                return None
            if stop - start == 1:
                return changes[start].new
            split = _common_bits(changes[start].digest, changes[stop - 1].digest)
        else:
            work.visits += 1
            leaf = isinstance(node, _Leaf)
            if leaf:
                work.leaf_visits += 1
            else:
                work.path_visits += 1
            sample = node.sample
            depth = 256 if leaf else node.split
            split = min(
                depth,
                _common_bits(sample, changes[start].digest),
                _common_bits(sample, changes[stop - 1].digest),
            )
            if split == 256:
                if apply:
                    return changes[start].new
                self._patch_expected(changes[start], node)
                return node
        middle = self._patch_boundary(changes, start, stop, split)
        if node is None:
            left = right = None
        elif isinstance(node, _Branch) and split == node.split:
            left, right = node.left, node.right
        elif _bit(node.sample, split):
            left, right = None, node
        else:
            left, right = node, None
        updated_left = self._patch_visit(left, changes, start, middle, work, apply=apply)
        updated_right = self._patch_visit(right, changes, middle, stop, work, apply=apply)
        if not apply:
            return node
        if updated_left is None:
            return updated_right
        if updated_right is None:
            return updated_left
        if (
            isinstance(node, _Branch)
            and split == node.split
            and updated_left is node.left
            and updated_right is node.right
        ):
            return node
        return self._branch(split, updated_left, updated_right, work)

    def patch(self, operations):
        """Atomically apply a strict batch against the original root.

        Operations are ("put", key, expected_V_or_None, value) or
        ("remove", key, expected_V). None requires absence; ANY is not accepted.
        Duplicate canonical keys and observed K collisions are rejected. Only
        K operation hashes are sorted; unchanged subtrees are never enumerated.
        All expected values are checked before creating nodes. Validation and
        application visit the union of affected paths; each resulting ancestor
        is rebuilt once. ``visits`` includes both traversals; ``enumerated_keys``
        counts only supplied operations. Staging and new allocations share the
        same account and a failed batch never changes the original map.
        """
        if isinstance(operations, (str, bytes, Mapping)):
            raise CommitmentError("sync_patch_operations")
        try:
            operations = iter(operations)
        except TypeError as error:
            raise CommitmentError("sync_patch_operations") from error
        changes, metadata, work = [], 0, _Work()
        with self.account.reserve(sys.getsizeof(changes), kind="stage") as stage:
            for operation in operations:
                if not isinstance(operation, (tuple, list)) or not operation:
                    raise CommitmentError("sync_patch_operation")
                kind = operation[0]
                if type(kind) is not str or kind not in ("put", "remove"):
                    raise CommitmentError("sync_patch_operation")
                if len(operation) != (4 if kind == "put" else 3):
                    raise CommitmentError("sync_patch_operation")
                expected = operation[2]
                if expected is None:
                    if kind == "remove":
                        raise CommitmentError("sync_remove_expected_absent")
                else:
                    expected = _hex_bytes(expected)
                key = freeze(operation[1])
                key_bytes = canonical(key)
                digest = _key_digest(self._space, key_bytes)
                change = _PatchOp(
                    kind, key, key_bytes, digest, expected, operation[3] if kind == "put" else None
                )
                metadata += (
                    sys.getsizeof(change)
                    + sys.getsizeof(key_bytes)
                    + sys.getsizeof(digest)
                    + (sys.getsizeof(expected) if expected is not None else 0)
                    + self._patch_key_size(key)
                )
                stage.resize(sys.getsizeof(changes) + metadata + 32 * (len(changes) + 1))
                changes.append(change)
                work.hashes += 1
                work.enumerated_keys += 1
            stage.resize(sys.getsizeof(changes) + metadata + 32 * len(changes))
            changes.sort(key=lambda change: change.digest)
            for index in range(1, len(changes)):
                if changes[index - 1].digest == changes[index].digest:
                    reason = (
                        "sync_duplicate_key"
                        if changes[index - 1].key_bytes == changes[index].key_bytes
                        else "sync_key_hash_collision"
                    )
                    raise CommitmentError(reason)
            self._patch_visit(self._node, changes, 0, len(changes), work, apply=False)
            for change in changes:
                if change.kind == "remove":
                    continue
                frozen = freeze(change.value)
                encoded = canonical(frozen)
                if change.old is not None and change.old.value_bytes == encoded:
                    change.new = change.old
                else:
                    key = change.old.key if change.old is not None else change.key
                    change.new = self._leaf(
                        self._entry(
                            key,
                            change.key_bytes,
                            change.digest,
                            frozen,
                            work,
                            prepared=(frozen, encoded),
                        ),
                        work,
                    )
            changes[:] = [change for change in changes if change.new is not change.old]
            work.changed = bool(changes)
            node = self._patch_visit(self._node, changes, 0, len(changes), work, apply=True)
            result = self._new(node, work)
        return result

    def put(self, key, value, *, expected=ANY):
        frozen_key = freeze(key)
        key_bytes = canonical(frozen_key)
        digest = _key_digest(self._space, key_bytes)
        work = _Work(hashes=1)
        found, path = self._find(digest, key_bytes, work)
        current = found if isinstance(found, _Leaf) and found.sample == digest else None
        self._expected(current, expected)
        frozen_value = freeze(value)
        value_bytes = canonical(frozen_value)
        if current is not None and current.entry.value_bytes == value_bytes:
            return self._new(self._node, work)
        entry = self._entry(
            frozen_key, key_bytes, digest, value, work, prepared=(frozen_value, value_bytes)
        )
        work.changed = True
        return self._new(self._insert(found, path, entry, work), work)

    def remove(self, key, *, expected=ANY):
        key_bytes = canonical(key)
        digest = _key_digest(self._space, key_bytes)
        work = _Work(hashes=1)
        found, path = self._find(digest, key_bytes, work)
        if not isinstance(found, _Leaf) or found.sample != digest:
            raise CommitmentError("sync_key_absent")
        if expected is None:
            raise CommitmentError("sync_remove_expected_absent")
        self._expected(found, expected)
        if not path:
            result = None
        else:
            parent, right = path.pop()
            result = parent.left if right else parent.right
            result = self._rebuild(path, result, work)
        work.changed = True
        return self._new(result, work)

    def _entries(self, meter):
        target = self.meter if meter is None else meter
        pending = [self._node] if self._node is not None else []
        while pending:
            node = pending.pop()
            target.visits += 1
            if isinstance(node, _Leaf):
                target.iterations += 1
                yield node.entry
            else:
                pending.extend((node.right, node.left))

    def items(self, *, meter=None):
        for entry in self._entries(meter):
            yield entry.key, entry.value

    def encoded_items(self, *, meter=None):
        for entry in self._entries(meter):
            yield entry.key_bytes, entry.value_bytes

    def check_summary(self, root, count):
        _hex_bytes(root)
        if type(count) is not int or count != self.count or root != self.root:
            raise CommitmentError("sync_map_summary_mismatch")
        return True
