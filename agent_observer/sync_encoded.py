"""Private encoded-only owner tables for the new opt-in sync service family.

The Patricia commitment and sparse-path algorithms are Observer's own
``sync_commitment`` implementation. Leaves retain canonical JSON bytes only.
``get``, ``lookup``, ``lookup_entry`` and ``items`` explicitly parse detached
JSON, whose lifetime/accounting belongs to their caller after return. Encoded
lookups do not parse or expose mutable owned references.

Raw JSON methods and the default encoded methods validate independently.
``trusted=True`` is an internal producer seam: the caller must already have
admitted *exact canonical bytes*. It skips JSON parsing/schema admission, never
expected-value, collision, commitment or allocation checks. This prototype is
not a producer/package acceptance or a new public wire contract.
"""

from __future__ import annotations

import hashlib
import json
import sys
import traceback
from collections.abc import Mapping
from contextlib import contextmanager
from functools import wraps

from . import sync_commitment as _sync

ABSENT, ANY = _sync.ABSENT, _sync.ANY
AllocationAccount = _sync.AllocationAccount
BudgetExceeded = _sync.BudgetExceeded
CommitmentError = _sync.CommitmentError

_CONTROL = 8192
_PATH_SCRATCH = 128 * 1024
_MAX_DEPTH = 256
_PATCH_OP_BYTES = sys.getsizeof(_sync._PatchOp("put", None, b"", b"", None))
_DIGEST_BYTES = sys.getsizeof(bytes(32))
_CLAIM_TUPLE_BYTES = (sys.getsizeof((None,)), sys.getsizeof((None, None)))


def _discard_failed_scratch(method):
    """A held failure must not retain scratch after its budget is released."""
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            args = kwargs = None
            raise
    return call


def _hash_parts(domain, *parts):
    digest = hashlib.sha256(domain)
    for part in parts:
        digest.update(part)
    return digest.digest()


def _reject_number(_value):
    raise CommitmentError("sync_json_type")


def _loads(raw):
    try:
        return json.loads(raw, parse_float=_reject_number, parse_constant=_reject_number)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, CommitmentError):
            raise
        # JSONDecodeError otherwise retains its freshly decoded input string.
        if isinstance(error, json.JSONDecodeError):
            error.doc = ""
        error.__traceback__ = None
        raise CommitmentError("sync_encoded_json") from None


def _parse_bound(raw, *, recanonicalize=False):
    """Scan with scalar state before allocating a decoded JSON graph.

    UTF-8 input and decoded Unicode can coexist. Per-token/container allowances
    include CPython object/dict/list resize overlap; string payloads have a
    separate four-byte-per-input-byte bound. No list of tokens is constructed.
    """
    if type(raw) is not bytes:
        raise CommitmentError("sync_encoded_bytes_required")
    strings, containers, atoms, string_bytes = 0, 0, 0, 0
    quoted = escaped = atom = False
    depth = 0
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
                string_bytes += 1
            elif byte == 92:
                escaped = True
                string_bytes += 1
            elif byte == 34:
                quoted = False
            else:
                string_bytes += 1
            continue
        if byte == 34:
            strings += 1
            quoted, atom = True, False
        elif byte in (91, 123):
            containers += 1
            depth += 1
            if depth > _MAX_DEPTH:
                raise CommitmentError("sync_encoded_depth")
            atom = False
        elif byte in (93, 125):
            depth -= 1
            atom = False
        elif byte in (9, 10, 13, 32, 44, 58):
            atom = False
        elif not atom:
            atoms += 1
            atom = True
    # Recanonicalization also holds JSONEncoder's string and UTF-8 output.
    factor = 12 if recanonicalize else 4
    return (_CONTROL + factor * len(raw) + 4 * string_bytes
            + 256 * (strings + atoms) + 512 * containers)


def decode_bound(raw):
    """Cheap conservative parse scratch for already-admitted canonical bytes.

    This is a budget estimate, not validation. Punctuation inside strings also
    counts, so pathological strings can require more reservation than their
    actual decoded allocation. Strict external admission uses the lexical scan.
    """
    if type(raw) is not bytes:
        raise CommitmentError("sync_encoded_bytes_required")
    tokens = sum(raw.count(token) for token in (b":", b",", b"[", b"{", b'"')) + 1
    return _CONTROL + 8 * len(raw) + 512 * tokens


def _raw_bound(value, scratch):
    active = set()
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > _MAX_DEPTH:
            raise CommitmentError("sync_encoded_depth")
        scratch.resize(max(scratch._size, _CONTROL + depth * 2048))
        if item is None:
            return 4
        if type(item) is bool:
            return 5
        if type(item) is int:
            # Do not allocate a decimal copy merely to preflight its copy.
            return max(1, (item.bit_length() * 30103) // 100000 + 2)
        if type(item) is str:
            _sync._string(item)
            return 2 + 6 * len(item)
        if not isinstance(item, (Mapping, list, tuple)):
            raise CommitmentError("sync_json_type")
        marker = id(item)
        if marker in active:
            raise CommitmentError("sync_json_cycle")
        active.add(marker)
        try:
            if isinstance(item, Mapping):
                total = 2
                for key, child in item.items():
                    _sync._string(key)
                    total += visit(key, depth + 1) + visit(child, depth + 1) + 2
                return total
            return 2 + sum(visit(child, depth + 1) + 1 for child in item)
        finally:
            active.remove(marker)

    bound = visit(value, 0)
    return _CONTROL + 12 * bound + 512 * nodes


class _EncodedLeaf(_sync._Leaf):
    __slots__ = ("encoded_ownership",)

    def _payload_size(self):
        # Key/value bytes use identity ownership, shared across roots/tables.
        return sys.getsizeof(self._hashes)

    def __del__(self):
        account = self._account
        if account is not None:
            object.__setattr__(self, "_account", None)
            account._drop(sys.getsizeof(self), "nodes",
                          {id(self.key_bytes), id(self.value_bytes)},
                          payload=self._payload_size())
            ownership = getattr(self, "encoded_ownership", None)
            if ownership is not None:
                ownership._release_leaf(self.key_bytes, self.value_bytes)


class _EncodedWork(_sync._Work):
    __slots__ = ("scratch",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scratch = None


class EncodedMap(_sync.PersistentMap):
    """Immutable encoded-only Patricia table, with detached decoded queries.

    ``from_encoded``, ``put_encoded`` and ``patch_encoded`` accept canonical
    UTF-8 bytes. Their default is strict; internal ``trusted=True`` avoids all
    JSON work and relies on the producer's completed domain admission.
    """

    __slots__ = ()

    @_discard_failed_scratch
    def __init__(self, space, entries=(), *, account=None):
        self._initialize(space, entries, account, encoded=False, trusted=False)

    @classmethod
    @_discard_failed_scratch
    def from_encoded(cls, space, entries=(), *, account=None, trusted=False):
        result = object.__new__(cls)
        result._initialize(space, entries, account, encoded=True, trusted=trusted)
        return result

    def _initialize(self, space, entries, account, *, encoded, trusted):
        budget = AllocationAccount() if account is None else account
        if not isinstance(budget, AllocationAccount):
            raise CommitmentError("sync_allocation_account")
        if type(space) is not str:
            raise CommitmentError("sync_string_required")
        with budget.reserve(_CONTROL + len(space) * 12, kind="stage"):
            raw_space = _sync._space(space)
            empty = _hash_parts(b"mesh-sync-empty\0", _sync.u64(len(raw_space)), raw_space)
            for name, value in (("space", space), ("account", budget),
                                ("_space", raw_space), ("_empty", empty),
                                ("_storage", _sync._BytesBundle((raw_space, empty))),
                                ("_node", None), ("last_update", _sync.MapStats()),
                                ("meter", _sync.VisitMeter())):
                object.__setattr__(self, name, value)
            self._charge_map()
        work = _EncodedWork(hashes=1)
        entries = entries.items() if isinstance(entries, Mapping) else entries
        leaves = []
        path_scratch = _PATH_SCRATCH + 4 * len(self._space)
        with budget.reserve(path_scratch, kind="stage") as stage:
            work.scratch = stage
            for key, value in entries:
                stage.resize(path_scratch + 48 * (len(leaves) + 1))
                with self._encoding(key, encoded, trusted) as key_bytes:
                    with self._encoding(value, encoded, trusted) as value_bytes:
                        digest = self._key_digest(key_bytes)
                        leaf = self._entry_bytes(key_bytes, digest, value_bytes, work)
                leaves.append(self._leaf(leaf, work))
                work.hashes += 1
                work.enumerated_keys += 1
                work.changed = True
            leaves.sort(key=lambda entry: entry._hashes)
            self._unique(leaves, digest=lambda entry: entry.key_digest,
                         key=lambda entry: entry.key_bytes)
            object.__setattr__(self, "_node", self._build(leaves, 0, len(leaves), work))
        object.__setattr__(self, "last_update", work.stats())

    @staticmethod
    def _unique(entries, *, digest, key):
        for index in range(1, len(entries)):
            left, right = entries[index - 1], entries[index]
            if digest(left) == digest(right):
                raise CommitmentError("sync_duplicate_key" if key(left) == key(right)
                                      else "sync_key_hash_collision")

    @contextmanager
    def _encoding(self, value, encoded, trusted=False):
        if encoded:
            if type(value) is not bytes:
                raise CommitmentError("sync_encoded_bytes_required")
            if trusted:
                yield value
                return
            with self.account.reserve(_CONTROL, kind="stage") as stage:
                stage.resize(_parse_bound(value, recanonicalize=True))
                decoded = _loads(value)
                try:
                    check = json.dumps(decoded, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":"), allow_nan=False).encode("utf-8")
                except (UnicodeError, ValueError, RecursionError) as error:
                    raise CommitmentError("sync_encoded_json") from error
                if check != value:
                    raise CommitmentError("sync_encoded_not_canonical")
                del check, decoded
                yield value
            return
        with self.account.reserve(_CONTROL, kind="stage") as stage:
            stage.resize(_raw_bound(value, stage))
            result = _sync.canonical(value)
            yield result

    def _decode(self, *raws):
        with self.account.reserve(_CONTROL, kind="stage") as stage:
            stage.resize(sum(decode_bound(raw) for raw in raws))
            result = tuple(_loads(raw) for raw in raws)
        return result

    def _key_digest(self, key_bytes):
        return _hash_parts(b"mesh-sync-key\0", _sync.u64(len(self._space)), self._space,
                           _sync.u64(len(key_bytes)), key_bytes)

    def _check_scratch(self, scratch, needed=_CONTROL):
        if (not isinstance(scratch, _sync._Lease) or scratch._account is not self.account
                or scratch._released or scratch._size < needed):
            raise CommitmentError("sync_encoded_scratch")

    def _entry_bytes(self, key_bytes, digest, value_bytes, work, *, credit=None):
        if work.scratch is not None:
            self._check_scratch(work.scratch)
            return self._mint_entry(key_bytes, digest, value_bytes, work, credit=credit)
        with self.account.reserve(_CONTROL, kind="stage"):
            return self._mint_entry(key_bytes, digest, value_bytes, work, credit=credit)

    def _mint_entry(self, key_bytes, digest, value_bytes, work, *, credit):
        ownership = getattr(self.account, "encoded_ownership", None)
        if ownership is not None:
            if getattr(ownership, "account", None) is not self.account:
                raise CommitmentError("sync_encoded_ownership_account")
            ownership.retain(key_bytes, value_bytes)
        try:
            value_digest = _hash_parts(b"mesh-sync-value\0", _sync.u64(len(self._space)),
                                       self._space, _sync.u64(len(value_bytes)), value_bytes)
            leaf_digest = _hash_parts(b"mesh-sync-leaf\0", _sync.u64(len(self._space)),
                                      self._space, digest, _sync.u64(len(key_bytes)),
                                      key_bytes, value_digest)
            entry = _EncodedLeaf(key_bytes, value_bytes, key_bytes, value_bytes,
                                 digest + value_digest + leaf_digest)
            objects = {id(value): (value, sys.getsizeof(value), "value_bytes")
                       for value in (key_bytes, value_bytes)}
            kwargs = ({} if credit is None else
                      {"credit": credit, "credit_keep": credit._size - sys.getsizeof(value_bytes)})
            self.account._acquire(sys.getsizeof(entry), "nodes", objects,
                                  payload=entry._payload_size(), **kwargs)
            object.__setattr__(entry, "_account", self.account)
            object.__setattr__(entry, "encoded_ownership", ownership)
            work.hashes += 2
            return entry
        except BaseException:
            if ownership is not None:
                ownership.release(key_bytes, value_bytes)
            raise

    def _branch(self, split, left, right, work):
        if work.scratch is not None:
            self._check_scratch(work.scratch, _CONTROL + 4 * len(self._space))
            return super()._branch(split, left, right, work)
        with self.account.reserve(_CONTROL + 4 * len(self._space), kind="stage"):
            # Fixed-size hashes/prefixes and aggregates only; no JSON nodes.
            return super()._branch(split, left, right, work)

    def _new(self, node, work):
        if work.scratch is not None:
            self._check_scratch(work.scratch)
            return self._mint_map(node, work)
        with self.account.reserve(_CONTROL, kind="stage"):
            return self._mint_map(node, work)

    def _mint_map(self, node, work):
        result = object.__new__(type(self))
        for name, value in (("space", self.space), ("account", self.account),
                            ("_space", self._space), ("_empty", self._empty),
                            ("_node", node), ("_storage", self._storage),
                            ("last_update", work.stats()), ("meter", _sync.VisitMeter())):
            object.__setattr__(result, name, value)
        result._charge_map()
        return result

    def _lookup_bytes(self, key_bytes, meter, scratch=None):
        if scratch is not None:
            self._check_scratch(scratch)
            return self._find_bytes(key_bytes, meter)
        with self.account.reserve(_CONTROL, kind="stage"):
            return self._find_bytes(key_bytes, meter)

    def _find_bytes(self, key_bytes, meter):
        work = _sync._Work(hashes=1)
        digest = self._key_digest(key_bytes)
        found, _ = self._find(digest, key_bytes, work, record_path=False)
        target = self.meter if meter is None else meter
        target.visits += work.visits
        target.hashes += work.hashes
        target.lookups += 1
        return found if isinstance(found, _sync._Leaf) and found.sample == digest else ABSENT

    def _lookup_entry(self, key, meter):
        with self._encoding(key, False) as encoded:
            return self._lookup_bytes(encoded, meter)

    @_discard_failed_scratch
    def get(self, key, default=ABSENT, *, meter=None):
        entry = self._lookup_entry(key, meter)
        return self._decode(entry.value_bytes)[0] if entry is not ABSENT else default

    @_discard_failed_scratch
    def lookup(self, key, default=ABSENT, *, meter=None):
        entry = self._lookup_entry(key, meter)
        return ((self._decode(entry.value_bytes)[0], entry.value_digest.hex())
                if entry is not ABSENT else default)

    @_discard_failed_scratch
    def lookup_entry(self, key, default=ABSENT, *, meter=None):
        entry = self._lookup_entry(key, meter)
        if entry is ABSENT:
            return default
        owned_key, owned_value = self._decode(entry.key_bytes, entry.value_bytes)
        return owned_key, owned_value, entry.value_digest.hex(), entry.key_bytes, entry.value_bytes

    @_discard_failed_scratch
    def get_hash(self, key, default=ABSENT, *, meter=None):
        return super().get_hash(key, default, meter=meter)

    @_discard_failed_scratch
    def lookup_encoded(self, key, default=ABSENT, *, meter=None):
        return super().lookup_encoded(key, default, meter=meter)

    @_discard_failed_scratch
    def lookup_encoded_bytes(self, key, default=ABSENT, *, trusted=False, meter=None, scratch=None):
        with self._encoding(key, True, trusted) as key_bytes:
            entry = self._lookup_bytes(key_bytes, meter, scratch)
        return (entry.key_bytes, entry.value_bytes) if entry is not ABSENT else default

    @_discard_failed_scratch
    def lookup_encoded_entry(self, key, default=ABSENT, *, trusted=False, meter=None, scratch=None):
        """Return original C(key), C(value), V from one zero-decode traversal.

        Optional ``scratch`` borrows an exclusive live reservation of >=8192
        bytes from this exact account; its caller retains lifetime ownership.
        """
        with self._encoding(key, True, trusted) as key_bytes:
            entry = self._lookup_bytes(key_bytes, meter, scratch)
        return ((entry.key_bytes, entry.value_bytes, entry.value_digest.hex())
                if entry is not ABSENT else default)

    def _entries(self, meter):
        # A DFS frontier contains at most one sibling per <=256-bit path.
        with self.account.reserve(_PATH_SCRATCH, kind="stage"):
            yield from super()._entries(meter)

    def items(self, *, meter=None):
        entries, entry = self._entries(meter), None
        try:
            for entry in entries:
                yield self._decode(entry.key_bytes, entry.value_bytes)
        finally:
            entries.close()
            entries = entry = None

    def encoded_items(self, *, meter=None):
        entries, entry = self._entries(meter), None
        try:
            for entry in entries:
                yield entry.key_bytes, entry.value_bytes
        finally:
            entries.close()
            entries = entry = None

    @_discard_failed_scratch
    def put(self, key, value, *, expected=ANY):
        with self._encoding(key, False) as key_bytes:
            with self._encoding(value, False) as value_bytes:
                return self._put_bytes(key_bytes, value_bytes, expected)

    @_discard_failed_scratch
    def put_encoded(self, key, value, *, expected=ANY, trusted=False):
        with self._encoding(key, True, trusted) as key_bytes:
            with self._encoding(value, True, trusted) as value_bytes:
                return self._put_bytes(key_bytes, value_bytes, expected)

    def _put_bytes(self, key_bytes, value_bytes, expected):
        with self.account.reserve(_PATH_SCRATCH + 4 * len(self._space), kind="stage") as scratch:
            work = _EncodedWork(hashes=1)
            work.scratch = scratch
            digest = self._key_digest(key_bytes)
            found, path = self._find(digest, key_bytes, work)
            current = found if isinstance(found, _sync._Leaf) and found.sample == digest else None
            self._expected(current, expected)
            if current is not None and current.value_bytes == value_bytes:
                return self._new(self._node, work)
            if current is not None:
                key_bytes = current.key_bytes
            leaf = self._entry_bytes(key_bytes, digest, value_bytes, work)
            work.changed = True
            return self._new(self._insert(found, path, leaf, work), work)

    @_discard_failed_scratch
    def remove(self, key, *, expected=ANY):
        with self._encoding(key, False) as key_bytes:
            return self._remove_bytes(key_bytes, expected)

    @_discard_failed_scratch
    def remove_encoded(self, key, *, expected=ANY, trusted=False):
        with self._encoding(key, True, trusted) as key_bytes:
            return self._remove_bytes(key_bytes, expected)

    def _remove_bytes(self, key_bytes, expected):
        with self.account.reserve(_PATH_SCRATCH + 4 * len(self._space), kind="stage") as scratch:
            digest = self._key_digest(key_bytes)
            work = _EncodedWork(hashes=1)
            work.scratch = scratch
            found, path = self._find(digest, key_bytes, work)
            if not isinstance(found, _sync._Leaf) or found.sample != digest:
                raise CommitmentError("sync_key_absent")
            if expected is None:
                raise CommitmentError("sync_remove_expected_absent")
            self._expected(found, expected)
            result = None
            if path:
                parent, right = path.pop()
                result = self._rebuild(path, parent.left if right else parent.right, work)
            work.changed = True
            return self._new(result, work)

    @_discard_failed_scratch
    def patch(self, operations):
        return self._patch(operations, encoded=False, trusted=False)

    @_discard_failed_scratch
    def patch_encoded(self, operations, *, trusted=False):
        return self._patch(operations, encoded=True, trusted=trusted)

    @contextmanager
    def _buffer_stage(self):
        ownership = getattr(self.account, "encoded_ownership", None)
        if ownership is not None and getattr(ownership, "account", None) is not self.account:
            raise CommitmentError("sync_encoded_ownership_account")
        claims = [] if ownership is not None else None
        try:
            yield ownership, claims
        finally:
            if claims is not None:
                for buffers in claims:
                    ownership.release(*buffers)
                claims.clear()

    @staticmethod
    def _stage_buffers(stage, ownership, claims, key_bytes, value_bytes=None, *, changes,
                       expected, accounting):
        # These are the only retained per-edit allocations. The canonical
        # payload is already heap-owned when the optional ledger is enabled.
        metadata = _PATCH_OP_BYTES + _DIGEST_BYTES
        if expected is not None:
            metadata += sys.getsizeof(expected)
        if ownership is not None:
            metadata += _CLAIM_TUPLE_BYTES[value_bytes is not None]
        accounting[1] += metadata
        if ownership is None:
            accounting[2] += sys.getsizeof(key_bytes)
            if value_bytes is not None:
                accounting[2] += sys.getsizeof(value_bytes)
        count = len(changes) + 1
        # List growth may briefly hold old/new pointer arrays. Keyed sort and
        # in-place compaction have separate <=32 pointer bytes/edit scratch.
        pointers = max(3 * sys.getsizeof(changes), 256 + 16 * count)
        if claims is not None:
            pointers += max(3 * sys.getsizeof(claims), 256 + 16 * count)
        stage.resize(sum(accounting) + pointers + 32 * count)
        if ownership is not None:
            buffers = (key_bytes,) if value_bytes is None else (key_bytes, value_bytes)
            ownership.retain(*buffers)
            claims.append(buffers)

    def _patch(self, operations, *, encoded, trusted):
        if isinstance(operations, (str, bytes, Mapping)):
            raise CommitmentError("sync_patch_operations")
        try:
            operations = iter(operations)
        except TypeError as error:
            raise CommitmentError("sync_patch_operations") from error
        changes, work = [], _EncodedWork()
        with (self.account.reserve(_PATH_SCRATCH + 4 * len(self._space), kind="stage") as stage,
              self._buffer_stage() as (ownership, claims)):
            work.scratch = stage
            accounting = [stage._size, 0, 0]  # Control, edit objects, unowned payload.
            for operation in operations:
                if not isinstance(operation, (tuple, list)) or not operation:
                    raise CommitmentError("sync_patch_operation")
                kind = operation[0]
                if (type(kind) is not str or kind not in ("put", "remove")
                        or len(operation) != (4 if kind == "put" else 3)):
                    raise CommitmentError("sync_patch_operation")
                expected = operation[2]
                if expected is None:
                    if kind == "remove":
                        raise CommitmentError("sync_remove_expected_absent")
                else:
                    expected = _sync._hex_bytes(expected)
                with self._encoding(operation[1], encoded, trusted) as key_bytes:
                    if kind == "put":
                        with self._encoding(operation[3], encoded, trusted) as value_bytes:
                            self._stage_buffers(stage, ownership, claims, key_bytes, value_bytes,
                                                changes=changes, expected=expected,
                                                accounting=accounting)
                            changes.append(_sync._PatchOp(kind, key_bytes, key_bytes,
                                           self._key_digest(key_bytes), expected, value_bytes))
                    else:
                        self._stage_buffers(stage, ownership, claims, key_bytes, changes=changes,
                                            expected=expected, accounting=accounting)
                        changes.append(_sync._PatchOp(kind, key_bytes, key_bytes,
                                       self._key_digest(key_bytes), expected))
                work.hashes += 1
                work.enumerated_keys += 1
            key_bytes = value_bytes = None
            changes.sort(key=lambda change: change.digest)
            self._unique(changes, digest=lambda change: change.digest,
                         key=lambda change: change.key_bytes)
            # Expected Vs are all checked before any replacement leaf exists.
            self._patch_visit(self._node, changes, 0, len(changes), work, apply=False)
            for change in changes:
                if change.kind == "remove":
                    continue
                if change.old is not None and change.old.value_bytes == change.value:
                    value_size = sys.getsizeof(change.value)
                    change.new, change.value = change.old, None
                    if ownership is None:
                        stage.resize(stage._size - value_size)
                else:
                    original_key = change.old.key_bytes if change.old is not None else change.key_bytes
                    change.new = self._leaf(self._entry_bytes(original_key, change.digest,
                                           change.value, work,
                                           credit=stage if ownership is None else None), work)
            write = 0
            for change in changes:
                if change.new is not change.old:
                    changes[write] = change
                    write += 1
            del changes[write:]
            work.changed = bool(changes)
            node = self._patch_visit(self._node, changes, 0, len(changes), work, apply=True)
            return self._new(node, work)
