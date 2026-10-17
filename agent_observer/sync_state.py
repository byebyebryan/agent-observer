"""Owner-generation synchronization cache; no Mesh, provider I/O or query renewal.

Normalization is owner publication work. Baseline export is explicitly linear;
head reads and retained transaction lookup never reconstruct a native roster.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain

from .active_contract import SELECTOR
from .contract import ContractError, identity_key, validate_shape
from .observation_support import SUPPORT_FIELDS, empty_support, fact_support
from .sync_commitment import (
    ABSENT,
    ANY,
    AllocationAccount,
    BudgetExceeded,
    PersistentMap,
    canonical,
    descriptor_digest,
    frame,
    freeze,
    native_binding_digest,
    native_root,
    thaw,
    value_hash,
)
from .sync_contract import MOVED_PATHS, _field_values, join_record

SPACES = ("records", "bodies", "observations", "memberships", "receipts",
          "cohorts", "scopes", "metadata")
ENCODED_LIMIT = 32 * 1024 * 1024
JOURNAL_LIMIT = 8 * 1024 * 1024
JOURNAL_GENERATIONS = 4
FRAME_LIMIT = 8_404_992
HEAD_LIMIT = 49_152
MAX_RECORDS = 4096


def _encode_parts(parts, size):
    """Write into one preallocated buffer without join's per-fragment scratch.

    Callers reserve two full buffers before entry, covering implementations
    that copy at getvalue(). Closing precedes release of that copy allowance.
    """
    with io.BytesIO() as output:
        if size:
            output.seek(size - 1)
            output.write(b"\0")
            output.seek(0)
        output.writelines(parts)
        if output.tell() != size:
            raise ContractError("sync_encoding_size")
        return output.getvalue()


class _Stage:
    """Bounded temporary containers and encoded work, released on rejection."""

    def __init__(self, cache):
        self.cache, self.account = cache, cache.account
        self.used, self.encoded = 1024, 0
        self.lease = self.account.reserve(self.used, kind="stage")
        self.working = None
        self.arena = None
        self.work_size = 0
        self.encoding_size = 0
        self.operations = []
        self.encoded_claims = []
        self.tables = []
        if cache.backend == "encoded":
            self.working = self.account.reserve(8192, kind="stage")
            self.arena = self.account.json_arena(kind="stage")

    def row(self):
        self.work_size = 0

    def decoding(self, size):
        if self.working is not None:
            self.work_size += size
            # The previous row's final local references can coexist with the
            # next row's initial reads. Keep the high-water envelope until the
            # entire publication returns; never release it between rows.
            needed = self.work_size * 2 + 8192
            if needed > self.working._size:
                self.working.resize(needed)

    def identity(self, value):
        return freeze(value)

    def encoding_workspace(self, size):
        if size > self.encoding_size:
            self.charge_encoded(size - self.encoding_size)
            self.encoding_size = size

    def retain_operation_bytes(self, buffers):
        ownership = self.cache.encoded_ownership
        if ownership is None:
            self.charge(sys.getsizeof(buffers[0]) + 64)
            return
        values = tuple(value for value in buffers if value is not None)
        self.charge(128)
        ownership.retain(*values)
        self.encoded_claims.append(values)

    def charge(self, size):
        self.lease.resize(self.used + size)
        self.used += size

    def charge_encoded(self, size):
        # Encoded stages share the accepted 32 MiB budget with owner buffers
        # and pinned peer bytes, independently of the decoded 64 MiB ledger.
        self.cache._reserve_encoded(size)
        self.cache.encoded_staged += size
        self.encoded += size

    def release_encoded(self, size):
        self.cache.encoded_staged -= size
        self.encoded -= size

    def close(self):
        for table in self.tables:
            table.close()
        self.tables.clear()
        for operations in self.operations:
            operations.spaces.clear()
        self.operations.clear()
        if self.cache.encoded_ownership is not None:
            for buffers in self.encoded_claims:
                self.cache.encoded_ownership.release(*buffers)
        self.encoded_claims.clear()
        if self.arena is not None:
            self.arena.close()
        if self.working is not None:
            self.working.release()
        self.lease.release()
        self.cache.encoded_staged -= self.encoded


class _Operations:
    def __init__(self, stage, enabled):
        self.stage, self.enabled = stage, enabled
        self.spaces = {name: [] for name in SPACES}
        self.size = 2 + sum(len(canonical(name)) + 4 for name in SPACES)
        stage.operations.append(self)

    def add(self, space, kind, key, expected, encoded=None):
        if not self.enabled:
            return
        if encoded is not None:
            # A changed value transfers to the committed map unchanged. A
            # replacement key may instead reuse the map's earlier equal key;
            # retain this operation's temporary key bytes explicitly.
            self.stage.charge(160 + (sys.getsizeof(expected) if type(expected) is str else 0))
            self.stage.retain_operation_bytes(encoded)
            # The encoded key already carries the complete immutable identity.
            # Keeping a second frozen logical key for every operation would
            # add a large shadow graph to a dense body update.
            key = None
        else:
            self.stage.charge(512)
        self.spaces[space].append((kind, key, expected, encoded))

    def encoded_parts(self, tables):
        # Keep borrowed canonical map buffers separate until the final join.
        # An intermediate operation document duplicates every changed value.
        count = sum(map(len, self.spaces.values()))
        self.stage.charge(8192 + count * 160)
        self.stage.charge_encoded(1024 + count * 66)
        parts = [b"{"]
        for index, space in enumerate(sorted(SPACES)):
            if index:
                parts.append(b",")
            parts.extend((canonical(space), b":["))
            for number, (kind, key, expected, retained) in enumerate(self.spaces[space]):
                if number:
                    parts.append(b",")
                if retained is not None:
                    key_bytes, value_bytes = retained
                elif self.stage.cache.backend == "encoded":
                    self.stage.row()
                    self.stage.decoding(2048 + _json_bound(key) * 8)
                    key_bytes = json.dumps(key, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")).encode("utf-8")
                    value_bytes = None
                    if kind == "put":
                        _, value_bytes = tables[space].lookup_encoded_bytes(
                            key_bytes, trusted=True, scratch=self.stage.working)
                elif kind == "put":
                    key_bytes, value_bytes = tables[space].lookup_encoded(key)
                else:
                    key_bytes, value_bytes = canonical(key), None
                parts.extend((b'["put",' if kind == "put" else b'["remove",',
                              key_bytes, b",", canonical(expected)))
                if kind == "put":
                    parts.extend((b",", value_bytes))
                parts.append(b"]")
            parts.append(b"]")
        parts.append(b"}")
        return parts


@dataclass(slots=True)
class _Pending:
    key: object
    value: object
    expected: object
    removed: bool = False
    encoded: tuple | None = None
    digest: str | None = None


def _json_bound(value):
    """Pre-encode upper bound; only changed bounded JSON is visited."""
    if isinstance(value, str):
        return 2 + 6 * len(value)
    if value is None:
        return 4
    if type(value) is bool:
        return 5
    if type(value) is int:
        return len(str(value))
    if hasattr(value, "items"):
        return 2 + sum(_json_bound(key) + _json_bound(child) + 2 for key, child in value.items())
    return 2 + sum(_json_bound(child) + 1 for child in value)


def _owned_hash(stage, domain, prefix, value):
    """Hash already-admitted engine JSON without refreezing every token input.

    Public admission/commitment helpers stay strict. Here the engine has already
    admitted the complete API 4 row and primitive JSON types. Preflight visits
    this changed value only and reserves both constructor and encoded scratch.
    """
    bound = _json_bound(value)
    encoded_bound = 3 * bound + 8
    with stage.account.reserve(1024 + 4 * bound, kind="stage"):
        stage.charge_encoded(encoded_bound)
        try:
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(encoded) > bound:
                raise ContractError("sync_encoding_bound")
            digest = hashlib.sha256(domain)
            digest.update(prefix)
            digest.update(frame(encoded))
            return digest.hexdigest()
        finally:
            stage.release_encoded(encoded_bound)


class _TableStage:
    """Owner-only sparse overlay; initial maps are built in one bulk pass."""

    def __init__(self, space, stage, base=None):
        self.space, self.stage, self.base = space, stage, base
        self.entries = {}
        self.storage = None
        self.arena = None
        self.storage = stage.account.reserve(1024, kind="stage")
        self.arena = stage.account.json_arena(kind="stage")

    def _pending(self, key):
        return self.entries.get(freeze(key))

    def lookup_entry(self, key):
        pending = self._pending(key)
        if pending is None:
            return ABSENT if self.base is None else self.base.lookup_entry(key)
        if pending.removed:
            return ABSENT
        if pending.digest is None:
            pending.digest = value_hash(self.space, pending.value)
            self.stage.charge(sys.getsizeof(pending.digest))
        key_bytes, value_bytes = self.lookup_encoded(key)
        return pending.key, pending.value, pending.digest, key_bytes, value_bytes

    def removal_entry(self, key):
        found = self.lookup_entry(key)
        return ABSENT if found is ABSENT else (found[0], found[2])

    def lookup_encoded(self, key):
        pending = self._pending(key)
        if pending is None:
            return ABSENT if self.base is None else self.base.lookup_encoded(key)
        if pending.removed:
            return ABSENT
        if pending.encoded is None:
            # This temporary encoding feeds only the atomic wire journal.
            # Retained map entries independently own their canonical bytes.
            reserved = _json_bound(pending.key) + _json_bound(pending.value)
            self.stage.charge_encoded(reserved)
            key_bytes, value_bytes = canonical(pending.key), canonical(pending.value)
            self.stage.release_encoded(reserved - len(key_bytes) - len(value_bytes))
            self.stage.charge(sys.getsizeof(key_bytes) + sys.getsizeof(value_bytes)
                              - len(key_bytes) - len(value_bytes) + 64)
            pending.encoded = key_bytes, value_bytes
        return pending.encoded

    def get(self, key, default=ABSENT):
        pending = self._pending(key)
        if pending is not None:
            return default if pending.removed else pending.value
        return default if self.base is None else self.base.get(key, default)

    def _store(self, key, value, expected, removed, prior=ABSENT):
        key = freeze(key)
        if key in self.entries:
            raise ContractError("sync_duplicate_owner_edit")
        # Reserve dictionary resize overlap and shallow pending objects before
        # installing the next entry. Immutable JSON ownership is shared once.
        size = sys.getsizeof(self.entries)
        self.storage.resize(1024 + max(3 * size, 256 + 128 * (len(self.entries) + 1))
                            + (len(self.entries) + 1) * 128)
        key, value = self.arena.retain_json(key, None if removed else value,
                                          priors=(ABSENT, prior))
        self.entries[key] = _Pending(key, value, expected, removed)
        self.storage.resize(1024 + sys.getsizeof(self.entries) + len(self.entries) * 128)
        return self

    def put(self, key, value, *, expected=ANY, prior=ABSENT):
        if expected is ANY:
            found = ABSENT if self.base is None else self.base.lookup_entry(key)
            expected = None if found is ABSENT else found[2]
        return self._store(key, value, expected, False, prior)

    def remove(self, key, *, expected=ANY):
        if expected is ANY:
            found = ABSENT if self.base is None else self.base.lookup_entry(key)
            if found is ABSENT:
                raise ContractError("sync_missing_owner_edit")
            expected = found[2]
        return self._store(key, None, expected, True)

    def items(self):
        if self.base is not None:
            for key, value in self.base.items():
                if key not in self.entries:
                    yield key, value
        for pending in self.entries.values():
            if not pending.removed:
                yield pending.key, pending.value

    def finish(self):
        try:
            if not self.entries and self.base is not None:
                return self.base
            if self.base is None:
                return PersistentMap(self.space, self.items(), account=self.stage.account)
            return self.base.patch(
                ("remove", item.key, item.expected) if item.removed else
                ("put", item.key, item.expected, item.value)
                for item in self.entries.values())
        finally:
            self.close()

    def close(self):
        self.entries.clear()
        if self.arena is not None:
            self.arena.close()
        if self.storage is not None:
            self.storage.release()

    def __del__(self):
        self.close()


def _same(left, right):
    """Compare mutable owner input with immutable JSON without thawing a roster."""
    if left is right:
        return True
    if hasattr(left, "items") and hasattr(right, "items"):
        # The immutable representation is a compact flat tuple. Iterate it
        # against the native dict's O(1) lookup instead of repeatedly searching
        # that tuple for every native key during the owner scan.
        if type(left) is dict and type(right) is not dict:
            left, right = right, left
        return (len(left) == len(right)
                and all(k in right and _same(v, right[k]) for k, v in left.items()))
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right, strict=True))
    return type(left) is type(right) and left == right


def _split_owned(row):
    # This temporary shallow projection never escapes publication. Changed
    # values are frozen by PersistentMap before they can become retained state.
    content, observed = dict(row), {}
    for name, moved in MOVED_PATHS.items():
        if row[name] is None:
            continue
        content[name] = {k: v for k, v in row[name].items() if k not in moved}
        observed[name] = {k: row[name][k] for k in moved}
    return content, observed


def _put(tables, changes, space, key, value, *, prior=ABSENT):
    table = tables[space]
    if table.stage.cache.backend != "encoded":
        key = freeze(key)
    found = table.lookup_entry(key)
    old = ABSENT if found is ABSENT else found[1]
    if old is not ABSENT and _same(old, value):
        return False
    if found is not ABSENT:
        key = found[0]
    expected = None if found is ABSENT else found[2]
    tables[space] = (table.put(key, value, expected=expected) if prior is ABSENT else
                     table.put(key, value, expected=expected, prior=prior))
    if changes.enabled:
        changes.add(space, "put", key, expected, getattr(tables[space], "last_encoded", None))
    return True


def _remove(tables, changes, space, key):
    table = tables[space]
    found = table.removal_entry(key)
    if found is ABSENT:
        return False
    key, expected = found
    tables[space] = table.remove(key, expected=expected)
    if changes.enabled:
        changes.add(space, "remove", key, expected, getattr(tables[space], "last_encoded", None))
    return True


def _put_changed(tables, changes, space, key, value, found):
    """Install an owner edit whose original value was already compared."""
    if found is not ABSENT:
        key = found[0]
    expected = None if found is ABSENT else found[2]
    if found is not ABSENT and expected is None:
        expected = hashlib.sha256(b"mesh-sync-value\0" + frame(space.encode())
                                  + frame(found[4])).hexdigest()
    tables[space] = tables[space].put(key, value, expected=expected,
                                    prior=ABSENT if found is ABSENT else found[1])
    changes.add(space, "put", key, expected, getattr(tables[space], "last_encoded", None))


def _replace_small(tables, changes, space, desired):
    old_keys = {freeze(key) for key, _ in tables[space].items()}
    for key, value in desired:
        changes.stage.row()
        key = freeze(key)
        old_keys.discard(key)
        _put(tables, changes, space, key, value)
    for key in old_keys:
        changes.stage.row()
        _remove(tables, changes, space, key)


def _table_stage(space, stage, base=None):
    if stage.cache.backend == "encoded":
        from .sync_encoded_state import EncodedTableStage

        return EncodedTableStage(space, stage, base)
    return _TableStage(space, stage, base)


def _empty_map(space, cache):
    if cache.backend == "encoded":
        from .sync_encoded_state import empty_map

        return empty_map(space, cache.account)
    return PersistentMap(space, account=cache.account)


@dataclass(frozen=True, slots=True)
class OwnerCommit:
    binding: object
    generation: int
    tables: dict
    groups: dict
    order: tuple
    tag: tuple
    cursor: tuple
    lease: object


@dataclass
class _Encoded:
    data: bytes
    lease: object
    base: tuple | None = None
    target: tuple | None = None

    def close(self):
        self.lease.release()


class _View:
    def __init__(self, name):
        self.name = name
        self.current = None
        self.previous = None
        self.baseline = None
        self.journal = []
        self.alias = 0
        self.generation = 0
        self.failed = None
        self.seed = None


class _BirthSeed:
    """Small charged identity lifetimes, without old bodies or table roots."""

    def __init__(self, account, current, alias):
        self.rows, self.storage, self.arena = {}, None, None
        self.account, self.continuous = account, True
        self.binding, self.alias = current.binding, alias
        try:
            self.storage = account.reserve(1024, kind="stage")
            self.arena = account.json_arena(kind="stage")
            self.arena.retain_json(self.binding, alias)
            for identity, slot in current.tables["records"].items():
                self.storage.resize(1024 + max(3 * sys.getsizeof(self.rows),
                                               256 + 128 * (len(self.rows) + 1)))
                claim = self.arena.retain_json(identity, slot["birth"], slot["alias"])
                self.rows[claim[0]] = claim
                self.storage.resize(1024 + sys.getsizeof(self.rows))
        except BaseException:
            self.close()
            raise

    def prune(self, rows):
        if not self.continuous:
            raise ContractError("sync_birth_continuity_unavailable")
        try:
            # Reconciliation visits this real owner roster, including during
            # failed material generations. A missed deletion cannot later be
            # silently treated as the same birth after reappearance.
            with self.account.reserve(1024 + len(rows) * 256 + len(self.rows) * 16,
                                      kind="stage"):
                present = {identity_key(row["identity"]) for row in rows}
                removed = [identity for identity in self.rows if identity not in present]
                for identity in removed:
                    del self.rows[identity]
                self.storage.resize(1024 + sys.getsizeof(self.rows))
        except BaseException:
            self.continuous = False
            raise

    def close(self):
        self.rows.clear()
        if self.arena is not None:
            self.arena.close()
        if self.storage is not None:
            self.storage.release()


class OwnerSyncCache:
    """Shared full/active cache, bounded roots and encoded acquisition buffers."""

    def __init__(self, state, *, decoded_limit=64 * 1024 * 1024, backend="frozen"):
        if backend not in {"frozen", "encoded"}:
            raise ContractError("sync_owner_backend")
        self.state = state
        self._closed = False
        self.backend = backend
        self.account = AllocationAccount(decoded_limit)
        self.views = {}
        self.query_buffers = {}
        self.generation = 0
        self.encoded_staged = 0
        self.reserver = None
        self.counts = {"publications": 0, "normalizations": 0, "baselines": 0,
                       "heads": 0, "transactions": 0, "recoveries": 0, "index_cells": 0,
                       "baseline_fallbacks": 0}
        self.encoded_ownership = None
        if backend == "encoded":
            from .sync_encoded_budget import EncodedOwnership

            self.encoded_ownership = EncodedOwnership(self.account, preflight=self._reserve_encoded)
            self.account.encoded_ownership = self.encoded_ownership

    def _descriptor(self, view):
        from .sync_native import descriptor

        return descriptor(view)

    def _source_metadata(self, view):
        return [self.state.source_meta(p) for p in self.state.configs
                if view == "full" or p == "codex"]

    def _binding(self, view, projection):
        desc = self._descriptor(view)
        sources = self._source_metadata(view)
        contexts = []
        for source in sources:
            contexts.append({**{k: v for k, v in source.items() if k != "components"},
                             "runtimeContext": (None if self.state.contexts[source["provider"]] is None
                                                else json.loads(self.state.contexts[source["provider"]]))})
        result = freeze({
            "protocol": desc["protocol"], "version": 1, "schemaDigest": desc["schemaDigest"],
            "hostScope": self.state.host_scope, "uid": self.state.uid,
            "view": view, "selector": None if view == "full" else SELECTOR,
            "ownerEpoch": self.state.service_id, "bootId": self.state.boot_id,
            "clockDomain": self.state.clock_domain, "sourceContexts": contexts,
            # Warming is a configured scope with no membership authority. Its
            # initial continuity is the projector's initial scope continuity;
            # absence of a projection must not drop the source binding.
            "scopeContinuity": ([] if view == "full" else
                                [[s["provider"], s["namespace"], 1] for s in sources]
                                if projection is None else [
                                    [s["provider"], s["namespace"], s["continuity"]]
                                    for s in projection["scopes"]]),
        })
        from .sync_native import NATIVE_BINDING

        validate_shape(thaw(result), NATIVE_BINDING)
        return result

    def _clock(self):
        return {"bootId": self.state.boot_id, "clockDomain": self.state.clock_domain,
                "boottimeMs": self.state.clock(), "ownerEpoch": self.state.service_id,
                "uid": self.state.uid, "hostScope": self.state.host_scope}

    def _receipts(self, sources):
        from .sync_native import RECEIPT

        result = []
        for source in sources:
            for receipt in source["components"]:
                value = {"serviceId": self.state.service_id,
                         "contextGeneration": source["contextGeneration"], **receipt}
                validate_shape(value, RECEIPT)
                if value["health"] in {"current", "partial"} and (
                        value["accepted"] < 1 or value["sampledBoottimeMs"] is None
                        or value["expiresBoottimeMs"] is None
                        or value["sampledBoottimeMs"] >= value["expiresBoottimeMs"]):
                    raise ContractError("sync_receipt_current")
                result.append((freeze([source["provider"], source["namespace"], receipt["name"]]), value))
        return result

    def ensure(self, view):
        if self._closed:
            raise ContractError("sync_owner_closed")
        if view not in {"full", "active"}:
            raise ContractError("sync_view")
        if view == "active" and "codex" not in self.state.configs:
            raise ContractError("sync_active_source_unsupported")
        if view not in self.views:
            self.views[view] = _View(view)
            try:
                self._publish_view(self.views[view])
            except (BudgetExceeded, ContractError, ValueError):
                slot = self.views[view]
                slot.failed = "sync_cache_capacity_or_admission"
                self._clear_encoded(slot)
                slot.previous = slot.current = None
                raise
        slot = self.views[view]
        if slot.failed is not None:
            raise ContractError(slot.failed)
        return slot

    def publish(self, *, diagnostics_only=False):
        # Called once after the existing engine/projector accepted generation.
        if self._closed:
            return
        for slot in tuple(self.views.values()):
            if diagnostics_only and slot.current is None:
                continue
            alias_before = slot.alias
            capacity = False
            try:
                self._publish_view(slot, diagnostics_only=diagnostics_only)
            except BudgetExceeded:
                slot.alias = alias_before
                capacity = True
            except (ContractError, ValueError):
                slot.alias = alias_before
                slot.failed = "sync_cache_capacity_or_admission"
                self._clear_encoded(slot)
                slot.previous = slot.current = None
            # Leave the exception suite before recovery: its traceback would
            # otherwise retain all rejected stage/prior graph references.
            if capacity:
                self._recover_capacity(slot, alias_before)
            if slot.current is not None and slot.seed is not None:
                slot.seed.close()
                slot.seed = None

    def _recover_capacity(self, slot, alias):
        seed = slot.seed
        slot.previous = None
        retry = slot.current is not None
        try:
            if retry:
                seed = _BirthSeed(self.account, slot.current, alias)
                slot.seed = seed
        except (BudgetExceeded, ContractError, ValueError):
            pass
        self._clear_encoded(slot)
        slot.failed = "sync_cache_capacity_or_admission"
        slot.previous = slot.current = None
        if seed is None or not retry:
            return
        try:
            slot.alias = seed.alias
            # One cold rebuild during publication, with the already allocated
            # result generation. Missing transaction history forces an explicit
            # sync baseline; no query retries or legacy route are involved.
            self._publish_view(slot, generation=slot.generation, seed=seed)
            self.counts["recoveries"] += 1
        except (BudgetExceeded, ContractError, ValueError):
            slot.alias = seed.alias
            self._clear_encoded(slot)
            slot.previous = slot.current = None

    def _clear_encoded(self, slot):
        if slot.baseline is not None:
            slot.baseline.close()
            slot.baseline = None
        for item in slot.journal:
            item.close()
        slot.journal.clear()

    def _membership(self, tables, changes, groups, cohort, identity, birth, field, token):
        cohort = freeze(cohort)
        if self.backend == "encoded":
            # Typed owner inputs are serialized before retention. Avoid an
            # additional frozen identity graph for these temporary keys.
            key, grouped = (cohort, identity, birth, field), (identity, birth, field)
        else:
            key, grouped = freeze([cohort, identity, birth, field]), freeze([identity, birth, field])
        if token is None:
            changed = _remove(tables, changes, "memberships", key)
            if changed:
                groups[cohort] = groups[cohort].remove(grouped)
            return
        if _put(tables, changes, "memberships", key, token):
            group = groups.get(cohort)
            if group is None:
                group = _table_stage("cohort-members", tables["memberships"].stage)
            if self.backend == "encoded":
                # Both commitment spaces contain the same canonical token.
                # Share its physical bytes while retaining separate keys,
                # old-value checks, nodes and independently computed roots.
                value_bytes = tables["memberships"].last_encoded[1]
                groups[cohort] = group.put_value_bytes(grouped, value_bytes)
            else:
                groups[cohort] = group.put(grouped, token)

    def _publish_view(self, slot, *, diagnostics_only=False, generation=None, seed=None):
        if generation is None:
            self.generation += 1
            slot.generation += 1
            generation = slot.generation
        if generation >= 2**64:
            raise ContractError("sync_generation_exhausted")
        seed = slot.seed if seed is None else seed
        if seed is not None and not diagnostics_only:
            projection = self.state.active_projection if slot.name == "active" else None
            if not _same(seed.binding, self._binding(slot.name, projection)):
                seed.close()
                slot.seed = seed = None
        if seed is not None and not diagnostics_only:
            if slot.name == "full":
                rows = [] if self.state.snapshot is None else self.state.snapshot["sessions"]
            else:
                projection = self.state.active_projection
                rows = [] if projection is None else projection["sessions"]
            seed.prune(rows)
        stage = _Stage(self)
        try:
            try:
                self._publish_staged(slot, stage, generation, diagnostics_only=diagnostics_only, seed=seed)
            finally:
                stage.close()
        except (ValueError, RecursionError):
            # A caller may retain the rejection. Its traceback cannot keep
            # rejected frame fragments/graphs after their credits retire.
            traceback.clear_frames(sys.exception().__traceback__)
            raise

    def _publish_staged(self, slot, stage, generation, *, diagnostics_only=False, seed=None):
        from .sync_native import validate_message

        prior = slot.current
        diagnostics_only = diagnostics_only and prior is not None
        projection = (self.state.active_projection if slot.name == "active" and not diagnostics_only else None)
        binding = prior.binding if diagnostics_only else self._binding(slot.name, projection)
        if seed is not None and not _same(seed.binding, binding):
            seed.close()
            slot.seed = seed = None
        # The encoded journal retains cursor/tag recovery. An older decoded
        # predecessor has no native authority handle and need not coexist with
        # the next candidate; keep the current root atomic while staging it.
        slot.previous = None
        if slot.baseline is not None:
            slot.baseline.close()
            slot.baseline = None
        while len(slot.journal) >= JOURNAL_GENERATIONS:
            slot.journal.pop(0).close()
        if prior is not None and not _same(prior.binding, binding):
            prior = None
            self._clear_encoded(slot)
            slot.current = slot.previous = None
        tables = {s: _table_stage(s, stage, None if prior is None else prior.tables[s]) for s in SPACES}
        groups = {} if prior is None else {
            key: _table_stage("cohort-members", stage, value) for key, value in prior.groups.items()}
        changes = _Operations(stage, prior is not None)
        desc = self._descriptor(slot.name)
        desc_hash = descriptor_digest(desc)
        sources = self._source_metadata(slot.name)
        by_scope = {(s["provider"], s["namespace"]): s for s in sources}
        receipt_entries = self._receipts(sources)
        if len(receipt_entries) > 32:
            raise ContractError("sync_receipt_capacity")
        _replace_small(tables, changes, "receipts", receipt_entries)
        receipt_keys = {tuple(key): key for key, _ in receipt_entries}
        cohort_refs = {key: freeze(["cohort", key]) for key in receipt_keys.values()}
        if diagnostics_only:
            rows, support_by_key = [], {}
        elif slot.name == "full":
            rows = [] if self.state.snapshot is None else self.state.snapshot["sessions"]
            support_by_key = self.state.projection_support
        else:
            rows = [] if projection is None else projection["sessions"]
            support_by_key = {} if projection is None else {
                identity_key(m["identity"]): m["fieldSupports"]
                for s in projection["scopes"] for m in s["members"]}
        if len(rows) > MAX_RECORDS:
            raise ContractError("sync_record_capacity")
        seen, order, now = set(), [], self.state.clock()
        new_birth = freeze([self.state.service_id, generation])
        # Every current field must name the exact original admitted sample.
        # Its expected tuple is the same bounded per-component object across
        # the scan. Validate the receipt once, then compare all eight original
        # token fields using native dict equality, including provider/scope.
        expected_supports = {
            tuple(key): {"serviceId": value["serviceId"], "provider": key[0], "namespace": key[1],
                         "contextGeneration": value["contextGeneration"], "component": key[2],
                         **{name: value[name] for name in
                            ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")}}
            for key, value in receipt_entries
            if value["health"] in {"current", "partial"}
            and value["sampledBoottimeMs"] <= now < value["expiresBoottimeMs"]
        }
        # Publication may scan N; every point mutation below is persistent and
        # is also the same primitive independently used by sparse receivers.
        with self.account.reserve(1024 + len(rows) * 256, kind="stage"):
            for row in rows:
                stage.row()
                if self.backend == "encoded":
                    # The engine already admitted this exact API 4 identity.
                    # Final order retention freezes/owns its bounded tuple in
                    # one batch; no second regex/schema pass is needed here.
                    native_id = row["identity"]
                    identity = (native_id["hostScope"], native_id["provider"], native_id["namespace"],
                                native_id["nativeIdKind"], native_id["nativeId"])
                else:
                    identity = stage.identity(identity_key(row["identity"]))
                if identity in seen:
                    raise ContractError("sync_duplicate_identity")
                old_entry = (tables["records"].lookup_entry(identity, digest=False)
                             if self.backend == "encoded" else tables["records"].lookup_entry(identity))
                old = ABSENT if old_entry is ABSENT else old_entry[1]
                if old is ABSENT:
                    seeded = None if seed is None else seed.rows.get(identity)
                    if seeded is None:
                        slot.alias += 1
                        if slot.alias >= 2**64:
                            raise ContractError("sync_alias_exhausted")
                        birth, alias = new_birth, slot.alias
                    else:
                        identity, birth, alias = seeded
                    old_content, old_obs = ABSENT, ABSENT
                    old_obs_entry = ABSENT
                else:
                    if self.backend != "encoded":
                        identity = stage.identity(old["order"][1])
                    birth, alias = freeze(old["birth"]), old["alias"]
                    old_content = (ABSENT if self.backend == "encoded" else
                                   tables["bodies"].get(old["body"]))
                    old_obs_entry = tables["observations"].lookup_entry([identity, birth])
                    old_obs = ABSENT if old_obs_entry is ABSENT else old_obs_entry[1]
                seen.add(identity)
                order.append(identity)
                content, observations = _split_owned(row)
                native_content = content
                if self.backend == "encoded":
                    from .sync_encoded_state import encode_row_content

                    content_bytes = encode_row_content(stage, content)
                    old_body = ABSENT if old is ABSENT else tables["bodies"].lookup_encoded(old["body"])
                    body_unchanged = old_body is not ABSENT and old_body[1] == content_bytes
                else:
                    body_unchanged = old_content is not ABSENT and _same(content, old_content)
                tokens_input = None
                old_tokens_input = None
                token_prefix = None
                if not body_unchanged and old is not ABSENT:
                    if self.backend == "encoded" and old_body is not ABSENT:
                        old_content = tables["bodies"]._parse(old_body[1])[0]
                    if old_content is not ABSENT:
                        tokens_input = _field_values(native_content)
                        old_tokens_input = _field_values(old_content)
                if body_unchanged:
                    content_id = old["body"]
                elif self.backend == "encoded":
                    body_hasher = hashlib.sha256(b"mesh-sync-body\0" + frame(bytes.fromhex(desc_hash))
                                                 + len(content_bytes).to_bytes(8, "big"))
                    body_hasher.update(content_bytes)
                    content_id = body_hasher.hexdigest()
                else:
                    content_id = _owned_hash(stage, b"mesh-sync-body\0", frame(bytes.fromhex(desc_hash)), content)
                if not body_unchanged:
                    if self.backend == "encoded":
                        table = tables["bodies"]
                        found = table.lookup_encoded_entry(content_id)
                        if found is ABSENT or found[1] != content_bytes:
                            table.put_value_bytes(content_id, content_bytes,
                                                  expected=None if found is ABSENT else found[2])
                            changes.add("bodies", "put", content_id, None if found is ABSENT else found[2],
                                        table.last_encoded)
                    else:
                        _put(tables, changes, "bodies", content_id, content, prior=old_content)
                if old is not ABSENT and old["body"] != content_id:
                    _remove(tables, changes, "bodies", old["body"])
                supports = support_by_key.get(tuple(identity))
                if supports is None:
                    supports = empty_support()
                refs = {}
                old_refs = {} if old_obs is ABSENT else old_obs["supports"]
                for field in SUPPORT_FIELDS:
                    support = supports.get(field)
                    current = (support is not None and support == expected_supports.get(
                        (identity[1], identity[2], support["component"])))
                    cohort = receipt_keys[(identity[1], identity[2], support["component"])] if current else None
                    previous = old_refs.get(field)
                    same_cohort = (previous is not None and previous[0] == "cohort"
                                   and cohort is not None and tuple(previous[1]) == cohort)
                    if previous and previous[0] == "cohort" and not same_cohort:
                        self._membership(tables, changes, groups, previous[1], identity, birth, field, None)
                    if current:
                        field_unchanged = body_unchanged or (
                            old_tokens_input is not None and
                            (tokens_input[field] == old_tokens_input[field] if self.backend == "encoded"
                             else _same(tokens_input[field], old_tokens_input[field])))
                        if field_unchanged and same_cohort:
                            # Actual support was checked above against this
                            # fresh sample. Its exact content/birth membership
                            # already belongs to the same immutable sealed set.
                            # A same-set renewal must not look up/rewrite every
                            # previously admitted member cell.
                            refs[field] = previous
                            continue
                        key = [cohort, identity, birth, field]
                        # A changed body always derives its exact new token
                        # below. Reading/decoding the old cell here cannot
                        # affect it; _membership still checks the old edit.
                        token = tables["memberships"].get(key) if body_unchanged else ABSENT
                        if token is ABSENT:
                            if tokens_input is None:
                                # This owner-only content comes from the
                                # engine's already validated API 4 snapshot.
                                # Receivers use strict admit_record instead.
                                tokens_input = _field_values(native_content)
                            if token_prefix is None:
                                token_prefix = (frame(bytes.fromhex(desc_hash))
                                                + frame(canonical(identity)) + frame(canonical(birth)))
                            token = _owned_hash(stage, b"mesh-sync-field\0",
                                                token_prefix + frame(field.encode("utf-8")),
                                                tokens_input[field])
                        self._membership(tables, changes, groups, cohort, identity, birth, field, token)
                        refs[field] = previous if same_cohort else cohort_refs[cohort]
                    else:
                        refs[field] = None if support is None else ["context", support]
                observations_unchanged = refs_unchanged = False
                if old_obs is not ABSENT:
                    old_fields = old_obs["fields"]
                    if self.backend == "encoded":
                        # Both sides are already-admitted primitive API 4
                        # observations/support DTOs, with identical field
                        # schemas. Native dict equality avoids a second Python
                        # traversal while preserving exact same-field values.
                        observations_unchanged = observations == old_fields
                        refs_unchanged = old_refs == refs
                    else:
                        observations = {name: old_obs["fields"][name]
                                        if name in old_obs["fields"] and _same(value, old_obs["fields"][name])
                                        else value for name, value in observations.items()}
                        observations_unchanged = (len(observations) == len(old_fields) and all(
                            value is old_fields.get(name) for name, value in observations.items()))
                        refs_unchanged = _same(old_refs, refs)
                    if refs_unchanged:
                        refs = old_refs
                if not observations_unchanged or not refs_unchanged:
                    _put_changed(tables, changes, "observations", freeze([identity, birth]),
                                 {"fields": observations, "supports": refs}, old_obs_entry)
                order_group = int(row["runtime"]["value"] != "running")
                if old is ABSENT or old["body"] != content_id or old["order"][0] != order_group:
                    _put_changed(tables, changes, "records", identity, {
                        "birth": birth, "alias": alias, "body": content_id,
                        "order": [order_group, identity], "scope": [identity[1], identity[2]],
                    }, old_entry)
            if prior is not None and not diagnostics_only:
                for identity in prior.order:
                    stage.row()
                    if identity in seen:
                        continue
                    old = tables["records"].get(identity)
                    old_obs = tables["observations"].get([identity, old["birth"]])
                    for field, ref in old_obs["supports"].items():
                        if ref and ref[0] == "cohort":
                            self._membership(tables, changes, groups, ref[1], identity, old["birth"], field, None)
                    _remove(tables, changes, "observations", [identity, old["birth"]])
                    _remove(tables, changes, "bodies", old["body"])
                    _remove(tables, changes, "records", identity)
        groups = {key: value.finish() for key, value in groups.items()}
        cohort_values = []
        for key, receipt in receipt_entries:
            if receipt["accepted"] < 1 or receipt["sampledBoottimeMs"] is None or receipt["expiresBoottimeMs"] is None:
                continue
            group = groups.get(key)
            if group is None:
                group = groups[key] = _empty_map("cohort-members", self)
            old = tables["cohorts"].get(key)
            seal = ([generation, group.root, group.count] if old is ABSENT
                    or old["seal"][1] != group.root or old["seal"][2] != group.count else old["seal"])
            cohort_values.append((key, {
                "receipt": key, "seal": seal, "accepted": receipt["accepted"],
                "sampledBoottimeMs": receipt["sampledBoottimeMs"],
                "expiresBoottimeMs": receipt["expiresBoottimeMs"],
            }))
        _replace_small(tables, changes, "cohorts", cohort_values)
        if diagnostics_only:
            service = thaw(tables["metadata"].get("service"))
            service["sources"] = sources
            _put(tables, changes, "metadata", "service", service)
            order = prior.order
        else:
            scope_values = self._scopes(slot.name, projection, support_by_key, by_scope)
            _replace_small(tables, changes, "scopes", scope_values)
            metadata = self._metadata(slot.name, projection, sources)
            _replace_small(tables, changes, "metadata", metadata.items())
        tables = {space: value.finish() for space, value in tables.items()}
        summary = [[s, tables[s].root, tables[s].count] for s in sorted(SPACES)]
        root = native_root(binding, generation, summary, expected_spaces=SPACES)
        tag = (native_binding_digest(binding), generation, root)
        cursor = (self.state.service_id, generation, root)
        order = tuple(order)
        # Maps own the row/key/value graphs. These shallow owner containers and
        # the binding are separate retained allocations shared by neither map
        # leases nor encoded buffers. Retain the binding by identity so an
        # unchanged binding can be shared by predecessor and current roots.
        if prior is not None:
            binding = prior.binding
            if _same(order, prior.order):
                order = prior.order
        outer_size = (sys.getsizeof(tables) + sys.getsizeof(groups) + sys.getsizeof(order)
                      + sys.getsizeof(tag) + sys.getsizeof(cursor) + 512)
        if stage.arena is None:
            lease = self.account.retain_json(binding, outer_size)
        else:
            owned = stage.arena.retain_json([binding, order])[0]
            binding, order = owned
            lease = self.account.retain_json(owned, outer_size)
        current = OwnerCommit(binding, generation, tables, groups, order, tag, cursor, lease)
        transaction = None
        transaction_lease = None
        transaction_reservation = 0
        if prior is not None:
            header = {
                "kind": "transaction", "descriptor": desc,
                "nativeBindingDigest": tag[0], "baseTag": prior.tag,
                "resultTag": tag, "baseCursor": prior.cursor, "resultCursor": cursor,
                "operations": {name: [] for name in SPACES},
            }
            # Changed map values have already been frozen, hashed and admitted
            # once. Encode their cached canonical bytes directly; rebuilding a
            # mutable DTO here would duplicate every changed body/observation.
            operations = changes.encoded_parts(tables)
            stage.charge(8192)
            header_parts = {key: canonical(header[key]) for key in header if key != "operations"}

            def encoded_parts():
                yield b"{"
                for number, key in enumerate(sorted(header)):
                    if number:
                        yield b","
                    yield canonical(key)
                    yield b":"
                    if key == "operations":
                        yield from operations
                    else:
                        yield header_parts[key]
                yield b"}"

            unsigned_size = sum(map(len, encoded_parts()))
            digest = hashlib.sha256(b"mesh-sync-transaction\0" + unsigned_size.to_bytes(8, "big"))
            for part in encoded_parts():
                digest.update(part)
            header["transactionId"] = digest.hexdigest()
            header_parts["transactionId"] = canonical(header["transactionId"])
            validate_message(thaw(freeze(header)), slot.name, expected_host=self.state.host_scope)
            frame_size = (unsigned_size + len(canonical("transactionId"))
                          + len(header_parts["transactionId"]) + 3)
            if frame_size <= min(FRAME_LIMIT, JOURNAL_LIMIT):
                # Borrow fragments directly; bytes.join would allocate a large
                # Py_buffer array in addition to its final output. Prepay two
                # buffers even on implementations whose BytesIO shares one.
                frame_reserved = False
                try:
                    stage.charge_encoded(frame_size * 2)
                    frame_reserved = True
                    transaction_lease = self.account.reserve(frame_size * 2 + 8192, kind="encoded")
                except (BudgetExceeded, ContractError) as error:
                    if not isinstance(error, BudgetExceeded) and error.args != ("sync_encoding_limit",):
                        raise
                    if frame_reserved:
                        stage.release_encoded(frame_size * 2)
                    # Material roots are already admitted and paid. Retiring
                    # the change chain forces explicit baseline recovery; an
                    # optional journal frame cannot revoke that valid state.
                else:
                    constructor = transaction_lease
                    try:
                        transaction = _encode_parts(chain(encoded_parts(), (b"\n",)), frame_size)
                        transaction_lease = self.account.retain_bytes(transaction, size=512,
                                                                       credit=constructor)
                    finally:
                        constructor.release()
                    stage.release_encoded(frame_size)
                    transaction_reservation = frame_size
        if slot.baseline is not None:
            slot.baseline.close()
            slot.baseline = None
        if prior is not None and transaction is not None:
            self._append_journal(slot, transaction, prior.tag, tag,
                                 lease=transaction_lease, prepaid=stage,
                                 reserved=transaction_reservation)
            transaction_lease = None
        elif prior is not None:
            self._clear_encoded(slot)
            self.counts["baseline_fallbacks"] += 1
        if transaction_lease is not None:
            transaction_lease.release()
        # No partially admitted material state escapes a failed validation or
        # reservation. Only current + predecessor decoded roots are retained.
        slot.previous, slot.current, slot.failed = prior, current, None
        if prior is not None:
            self.counts["transactions"] += 1
        self.counts["publications"] += 1
        self.counts["normalizations"] += int(not diagnostics_only)

    def _scopes(self, view, projection, supports, sources):
        if view == "full":
            if self.state.snapshot is None:
                return []
            result = []
            for source in self.state.snapshot["sources"]:
                key = source["provider"], source["namespace"]
                original = sources[key]
                census = self.state.projection_census.get(key[0], {})
                saved = fact_support(self.state.service_id, original, "history",
                                     self.state.receipts[key[0]]["history"])
                result.append(([*key, "coverage"], {
                    "coverage": source["coverage"], "sourceHealth": source["sourceHealth"],
                    "contextGeneration": original["contextGeneration"],
                    "supports": {"runtime": census.get("support"), "saved": saved},
                    "censusStatus": census.get("status", "unavailable"),
                }))
            return result
        result = []
        for scope in (projection or {}).get("scopes", []):
            prefix = [scope["provider"], scope["namespace"]]
            result.append((prefix + ["coverage"], {k: v for k, v in scope.items()
                                                     if k not in {"members", "nonmembers", "uncertain"}}))
            for kind in ("members", "nonmembers", "uncertain"):
                for fact in scope[kind]:
                    if kind == "members":
                        # Current refs are independent of the receipt counter.
                        value = {"identity": fact["identity"], "fields": {
                            field: (None if support is None else [support["provider"], support["namespace"], support["component"]])
                            for field, support in fact["fieldSupports"].items()}}
                    else:
                        value = fact
                    result.append((prefix + [kind, identity_key(fact["identity"])], value))
        return result

    def _metadata(self, view, projection, sources):
        snapshot = self.state.snapshot
        service = {"serviceId": self.state.service_id, "bootId": self.state.boot_id,
                   "uid": self.state.uid, "hostScope": self.state.host_scope,
                   "viewRevision": self.state.revision,
                   "state": "warming" if snapshot is None else "ready",
                   "clockDomain": self.state.clock_domain, "sources": sources}
        result = {"service": service}
        if view == "full":
            result["snapshot"] = None if snapshot is None else {k: v for k, v in snapshot.items() if k != "sessions"}
        else:
            result["projection"] = None if projection is None else {k: v for k, v in projection.items() if k not in {"sessions", "scopes"}}
            result["scopeOrder"] = [] if projection is None else [[s["provider"], s["namespace"]] for s in projection["scopes"]]
            result["validationSources"] = [] if snapshot is None else [
                {"provider": s["provider"], "namespace": s["namespace"],
                 "capabilities": {"timing": s["capabilities"]["timing"]}}
                for s in snapshot["sources"] if s["provider"] == "codex"]
        return result

    def _append_journal(self, slot, data, base, target, *, lease=None, prepaid=None, reserved=0):
        while len(slot.journal) >= JOURNAL_GENERATIONS:
            slot.journal.pop(0).close()
        while sum(len(x.data) for v in self.views.values() for x in v.journal) + len(data) > JOURNAL_LIMIT:
            oldest = next((v for v in self.views.values() if v.journal), None)
            if oldest is None:
                return
            oldest.journal.pop(0).close()
        if prepaid is None:
            self._reserve_encoded(len(data))
        elif reserved < len(data) or prepaid.encoded < reserved:
            raise ContractError("sync_encoding_reservation")
        if lease is None:
            lease = self.account.retain_bytes(data, size=512)
        slot.journal.append(_Encoded(data, lease, base, target))
        if prepaid is not None:
            prepaid.release_encoded(reserved)

    def _reserve_encoded(self, size):
        if sum(map(len, self.retained_buffers())) + self.owned_encoded_bytes() + size > ENCODED_LIMIT:
            raise ContractError("sync_encoding_limit")
        reserver = getattr(self.state, "sync_reserver", None) or self.reserver
        if reserver is not None and not reserver(size):
            raise ContractError("sync_encoding_limit")

    @contextmanager
    def _encoded_workspace(self, size):
        self._reserve_encoded(size)
        self.encoded_staged += size
        try:
            yield
        finally:
            self.encoded_staged -= size

    def owned_encoded_bytes(self):
        return self.encoded_staged + (0 if self.encoded_ownership is None else self.encoded_ownership.used)

    def retained_buffers(self):
        return tuple(item.data for slot in self.views.values()
                     for item in ([slot.baseline] if slot.baseline is not None else []) + slot.journal
                     ) + tuple(item.data for item in self.query_buffers.values())

    def pin_buffers(self, parts):
        """Delivery pins share physical heap bytes with cached outputs.

        Runtime owns aggregate encoded preflight and the pin's retirement.
        Pins retain bytes only, never old material roots or authority handles.
        """
        if type(parts) is not tuple or not 1 <= len(parts) <= 5:
            raise ContractError("sync_pin_buffers")
        lease = self.account.retain_bytes(*parts, size=sys.getsizeof(parts) + 128, kind="queue")
        self.discard_query_buffers(parts)
        return lease

    def discard_query_buffers(self, parts):
        """Retire unsent temporary heads/controls without touching material state."""
        for part in parts:
            temporary = self.query_buffers.pop(id(part), None)
            if temporary is not None:
                temporary.close()

    def current_tag(self, view):
        slot = self.views.get(view)
        return None if slot is None or slot.current is None else slot.current.tag

    def cursor(self, view):
        slot = self.views.get(view)
        return None if slot is None or slot.current is None else slot.current.cursor

    def tag_for_cursor(self, view, cursor):
        slot = self.views.get(view)
        if slot is None:
            return None
        for commit in (slot.current, slot.previous):
            if commit is not None and _same(commit.cursor, cursor):
                return commit.tag
        for item in slot.journal:
            for tag in (item.base, item.target):
                if tuple(cursor) == (self.state.service_id, tag[1], tag[2]):
                    return tag
        return None

    def control(self, view, status, reason="sync_control", **extra):
        from .sync_native import MAX_CONTROL_BYTES

        return self._query_output(lambda: {
            "kind": "control", "descriptor": self._descriptor(view),
            "status": status, "reason": reason,
            "tag": self.current_tag(view), "cursor": self.cursor(view),
            "ownerClock": self._clock(), **extra,
        }, MAX_CONTROL_BYTES)

    def _query_output(self, make, limit):
        if self._closed:
            raise ContractError("sync_owner_closed")
        try:
            return self._query_output_staged(make, limit)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            make = None
            raise

    def _query_output_staged(self, make, limit):
        # At most one bounded result per admitted local client. Runtime takes
        # a shared pin and retires this temporary owner before queueing it.
        # Direct diagnostic callers get a bounded FIFO, never unlimited heads.
        while len(self.query_buffers) >= 16:
            self.query_buffers.pop(next(iter(self.query_buffers))).close()
        with self._encoded_workspace(limit * 3):
            with self.account.reserve(131072 + limit * 64, kind="stage") as constructor:
                value = make()
                data = canonical(value) + b"\n"
                value = None
                if len(data) > limit:
                    raise ContractError("sync_query_limit")
                lease = self.account.retain_bytes(data, size=512, credit=constructor)
            self.query_buffers[id(data)] = _Encoded(data, lease)
        return data

    def baseline(self, view):
        try:
            return self._baseline(view)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            raise

    def _baseline(self, view):
        slot = self.ensure(view)
        if slot.baseline is not None:
            return slot.baseline.data
        current = slot.current
        with self.account.reserve(32768, kind="stage") as scratch:
            scratch.resize(32768 + _json_bound(current.binding) * 16)
            return self._baseline_encoded(view, slot, current)

    def _baseline_encoded(self, view, slot, current):
        # O(1) size reservation precedes the explicit full export walk. Cached
        # key/value bytes avoid re-encoding immutable unchanged body values.
        header = {"kind": "baseline", "descriptor": self._descriptor(view),
                  "nativeBinding": current.binding, "tag": current.tag,
                  "cursor": current.cursor}
        needed = len(canonical(header)) + sum(t.encoded_size for t in current.tables.values()) + 512
        if needed > FRAME_LIMIT:
            raise ContractError("sync_frame_limit")
        with self._encoded_workspace(needed * 2):
            constructor = self.account.reserve(needed * 2 + 8192, kind="encoded")
            try:
                return self._baseline_write(slot, current, header, constructor)
            finally:
                constructor.release()

    def _baseline_write(self, slot, current, header, constructor):
        with self.account.reserve(8192 + sum(t.count for t in current.tables.values()) * 64,
                                  kind="stage"):
            values = dict(header, tables=None)
            parts = [b"{"]
            for number, key in enumerate(sorted(values)):
                if number:
                    parts.append(b",")
                parts.extend((canonical(key), b":"))
                if key != "tables":
                    parts.append(canonical(values[key]))
                    continue
                parts.append(b"{")
                for index, space in enumerate(sorted(SPACES)):
                    if index:
                        parts.append(b",")
                    parts.extend((canonical(space), b":["))
                    for entry, (key_bytes, value_bytes) in enumerate(current.tables[space].encoded_items()):
                        if entry:
                            parts.append(b",")
                        parts.extend((b"[", key_bytes, b",", value_bytes, b"]"))
                    parts.append(b"]")
                parts.append(b"}")
            parts.append(b"}\n")
            data = _encode_parts(parts, sum(map(len, parts)))
            parts.clear()
            values.clear()
            header.clear()
        output_lease = self.account.retain_bytes(data, size=512, credit=constructor)
        if len(data) > FRAME_LIMIT:
            output_lease.release()
            raise ContractError("sync_frame_limit")
        slot.baseline = _Encoded(data, output_lease)
        self.counts["baselines"] += 1
        return data

    def changes(self, view, base, target, *, max_transactions=4, max_bytes=JOURNAL_LIMIT):
        slot = self.views.get(view)
        if slot is None or slot.current is None or slot.failed:
            return self.control(view, "baseline_required", "sync_missing_base")
        base, target = tuple(base), tuple(target)
        if base[0] != target[0] or self.tag_for_cursor(view, [self.state.service_id, target[1], target[2]]) != target:
            return self.control(view, "baseline_required", "sync_missing_target")
        terminal = {"tag": target, "cursor": [self.state.service_id, target[1], target[2]],
                    "baseTag": base, "targetTag": target}
        if base == target:
            return (self.control(view, "complete", "sync_complete", **terminal),)
        position, frames, used = base, [], 0
        for item in slot.journal:
            if item.base != position:
                continue
            if len(frames) >= max_transactions or used + len(item.data) > max_bytes:
                return self.control(view, "baseline_required", "sync_catchup_limit")
            frames.append(item.data)
            used += len(item.data)
            position = item.target
            if position == target:
                break
        if position != target:
            return self.control(view, "baseline_required", "sync_missing_base")
        return tuple(frames) + (self.control(view, "complete", "sync_complete", **terminal),)

    def head(self, view, challenge):
        try:
            return self._head(view, challenge)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            challenge = None
            raise

    def _head(self, view, challenge):
        slot = self.views.get(view)
        if slot is None or slot.current is None or slot.failed:
            return self.control(view, "baseline_required", "sync_not_initialized")
        current = slot.current

        def make():
            clock = self._clock()
            receipts = list(current.tables["receipts"].items())
            return {
                "kind": "head", "descriptor": self._descriptor(view),
                "nativeBindingDigest": current.tag[0], "tag": current.tag,
                "challenge": challenge, "ownerClock": clock,
                "originalReceipts": receipts,
                "cohortHeads": [[key, {k: v for k, v in value.items() if k != "receipt"}]
                                for key, value in current.tables["cohorts"].items()],
                "attenuation": [[key, max(0, r["expiresBoottimeMs"] - clock["boottimeMs"])
                                 if r["health"] in {"current", "partial"} and r["expiresBoottimeMs"] is not None else 0]
                                for key, r in receipts],
            }

        data = self._query_output(make, HEAD_LIMIT)
        self.counts["heads"] += 1
        return data

    def export_committed(self, view):
        """Explicit detached diagnostic export; grants no current authority."""
        current = self.ensure(view).current
        records = []
        for identity in current.order:
            slot = current.tables["records"].get(identity)
            observed = current.tables["observations"].get([identity, slot["birth"]])
            records.append(join_record(thaw(current.tables["bodies"].get(slot["body"])), thaw(observed["fields"])))
        if view == "full":
            header = current.tables["metadata"].get("snapshot")
            return None if header is None else {**thaw(header), "sessions": records}
        header = current.tables["metadata"].get("projection")
        if header is None:
            return None
        scopes = {tuple(key): {"provider": key[0], "namespace": key[1],
                               "members": [], "uncertain": [], "nonmembers": []}
                  for key in current.tables["metadata"].get("scopeOrder")}
        for key, value in current.tables["scopes"].items():
            scope = scopes[tuple(key[:2])]
            if key[2] == "coverage":
                scope.update(thaw(value))
            elif key[2] == "members":
                supports = {}
                for field, cohort in value["fields"].items():
                    if cohort is None:
                        supports[field] = None
                        continue
                    receipt = current.tables["receipts"].get(cohort)
                    supports[field] = {"serviceId": receipt["serviceId"],
                                       "provider": cohort[0], "namespace": cohort[1],
                                       "contextGeneration": receipt["contextGeneration"], "component": cohort[2],
                                       **{k: receipt[k] for k in ("accepted", "sampledBoottimeMs", "expiresBoottimeMs")}}
                scope["members"].append({"identity": thaw(value["identity"]), "fieldSupports": supports})
            else:
                scope[key[2]].append(thaw(value))
        result = []
        for key in current.tables["metadata"].get("scopeOrder"):
            scope = scopes[tuple(key)]
            for kind in ("members", "nonmembers", "uncertain"):
                scope[kind].sort(key=lambda r: identity_key(r["identity"]))
            result.append(scope)
        return {**thaw(header), "scopes": result, "sessions": records}

    def close(self):
        if self._closed:
            return
        for item in self.query_buffers.values():
            item.close()
        self.query_buffers.clear()
        for slot in self.views.values():
            self._clear_encoded(slot)
            slot.current = slot.previous = None
            if slot.seed is not None:
                slot.seed.close()
                slot.seed = None
        self.views.clear()
        if self.encoded_ownership is not None:
            self.encoded_ownership.close()
        self._closed = True
        self.state = self.reserver = None
