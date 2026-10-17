"""Mesh-free compact serialization of an already committed owner generation.

Material tables remain logical. Only the explicitly selected journal/baseline
serializer changes. Each walk decodes and packs one value under prepaid scratch;
no expanded frame, detached roster or per-cell membership document is built.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import closing

from .contract import ContractError
from .sync_commitment import ABSENT, _FrozenObject, thaw
from .sync_compact_schema import SUPPORT_FIELDS
from .sync_compact_values import References, pack_value, transform_operation


def _json_default(value):
    # The JSON encoder handles native lists/dicts and immutable array tuples.
    # Only committed immutable objects need a shallow adapter. Re-freezing
    # already admitted packed rows would construct another complete row graph
    # before immediately thawing it again; the existing row scratch remains
    # reserved for the encoder and these bounded temporary object dictionaries.
    if type(value) is _FrozenObject:
        return dict(value.items())
    raise TypeError("unsupported compact export value")


class _Export:
    def __init__(self, cache, current, before=None):
        self.cache, self.current, self.before = cache, current, before
        self.work = cache.account.reserve(16384, kind="stage")
        self.decoded = self.encoded = 0
        self.row_bytes = 0
        self.refs = None

    def initialize(self):
        self.row()
        dictionaries = {}
        for side, commit in (("before", self.before), ("after", self.current)):
            dictionaries[side] = []
            if commit is not None:
                with closing(commit.tables["receipts"].encoded_items()) as entries:
                    for key, _value in entries:
                        dictionaries[side].append(self.decode(key))
        self.refs = References(
            self.current.binding["ownerEpoch"], self.current.generation, dictionaries,
            lookup_record=lambda side, identity: self.lookup(side, "records", identity),
            lookup_alias=self._no_alias_scan,
            receipt_exists=lambda side, key: self.entry(side, "receipts", key) is not ABSENT,
            baseline=self.before is None,
        )
        self.dictionaries = dictionaries
        # References/dictionary containers coexist with each row's scratch.
        self.fixed = 16384 + self.row_bytes * 2
        self.work.resize(self.fixed + self.decoded * 2 + self.encoded * 2)

    @staticmethod
    def _no_alias_scan(_side, _alias):
        raise ContractError("sync_compact_export_alias_scan")

    def _commit(self, side):
        return self.before if side == "before" else self.current

    def row(self):
        self.row_bytes = 0

    def decode(self, raw):
        self.row_bytes += 1024 + len(raw) * 64
        self.decoded = max(self.decoded, self.row_bytes)
        # A suspended yield's previous value can coexist with the next decode.
        self.work.resize(getattr(self, "fixed", 16384) + self.decoded * 2 + self.encoded * 2)
        return json.loads(raw)

    def entry(self, side, space, key):
        commit = self._commit(side)
        if commit is None:
            return ABSENT
        # Prepay the canonical query key in both caps before constructing it.
        # The encoded lookup borrows our live scratch and decodes no value.
        encoded = self.encode(key)
        return commit.tables[space].lookup_encoded_bytes(encoded, trusted=True, scratch=self.work)

    def lookup(self, side, space, key):
        entry = self.entry(side, space, key)
        return None if entry is ABSENT else self.decode(entry[1])

    def encode(self, value):
        from .sync_state import _json_bound

        bound = _json_bound(value)
        self.row_bytes += 1024 + bound * 64
        self.decoded = max(self.decoded, self.row_bytes)
        needed = bound * 6 + 8192
        if needed > self.encoded:
            delta = needed - self.encoded
            self.cache._reserve_encoded(delta)
            self.cache.encoded_staged += delta
            self.encoded = needed
        # Python encoder string/chunks plus final UTF-8 copy are heap charged
        # as well as encoded charged. Previous yielded bytes stay covered.
        self.work.resize(getattr(self, "fixed", 16384) + self.decoded * 2 + self.encoded * 2)
        return json.dumps(value, default=_json_default, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")

    def masks(self, side, identity, birth, observations=None):
        if observations is None:
            observations = self.lookup(side, "observations", [identity, birth])
        masks = {}
        if observations is not None:
            for bit, name in enumerate(SUPPORT_FIELDS):
                support = observations["supports"][name]
                if support is not None and support[0] == "cohort":
                    cohort = tuple(support[1])
                    masks[cohort] = masks.get(cohort, 0) | (1 << bit)
        return masks

    def membership_entries(self):
        # Authoritative membership is created from these exact current support
        # references by the owner's normalizer. No nine-cell payload is copied.
        with closing(self.current.tables["observations"].encoded_items()) as entries:
            for key_bytes, value_bytes in entries:
                self.row()
                identity, birth = self.decode(key_bytes)
                observations = self.decode(value_bytes)
                for cohort, mask in sorted(self.masks("after", identity, birth, observations).items()):
                    yield [[self.refs.receipt_index(list(cohort), "after"),
                            *self.refs.raw_record(identity, birth, "after")], mask]

    def membership_changes(self, changes):
        # A token-only body change has no mask edit; generic expansion derives
        # the new tokens after admission. Changed observations are the sparse
        # set of possible support/group changes, including row removal/birth.
        for _kind, key, _expected, encoded in changes.spaces["observations"]:
            self.row()
            if encoded is not None:
                key = self.decode(encoded[0])
            else:
                key = thaw(key)
            identity, birth = key
            old = self.masks("before", identity, birth)
            new = self.masks("after", identity, birth)
            for cohort in sorted(old.keys() | new.keys()):
                old_mask, new_mask = old.get(cohort, 0), new.get(cohort, 0)
                if old_mask == new_mask:
                    continue
                before = None if not old_mask else [self.refs.receipt_index(list(cohort), "before"),
                                                     *self.refs.raw_record(identity, birth, "before")]
                after = None if not new_mask else [self.refs.receipt_index(list(cohort), "after"),
                                                   *self.refs.raw_record(identity, birth, "after")]
                yield [before, old_mask or None, after, new_mask]

    def entries(self, space, changes):
        if space == "memberships":
            yield from self.membership_entries() if changes is None else self.membership_changes(changes)
        elif changes is None:
            with closing(self.current.tables[space].encoded_items()) as entries:
                for key_bytes, value_bytes in entries:
                    self.row()
                    yield list(pack_value(space, self.decode(key_bytes), self.decode(value_bytes), self.refs))
        else:
            for kind, key, expected, encoded in changes.spaces[space]:
                self.row()
                if encoded is None:
                    key = thaw(key)
                    value = None if kind == "remove" else self.lookup("after", space, key)
                else:
                    key = self.decode(encoded[0])
                    value = None if kind == "remove" else self.decode(encoded[1])
                operation = [kind, key, expected] + ([value] if kind == "put" else [])
                yield transform_operation(space, operation, self.refs)

    def parts(self, header, changes=None):
        space_key = "tables" if changes is None else "operations"
        yield b"{"
        for number, key in enumerate(sorted((*header, space_key, "receiptRefs"))):
            if number:
                yield b","
            self.row()
            yield self.encode(key)
            yield b":"
            if key == "receiptRefs":
                yield self.encode(self.dictionaries)
            elif key != space_key:
                yield self.encode(header[key])
            else:
                yield b"{"
                for index, space in enumerate(sorted(self.current.tables)):
                    if index:
                        yield b","
                    yield self.encode(space)
                    yield b":["
                    with closing(self.entries(space, changes)) as entries:
                        for number, entry in enumerate(entries):
                            if number:
                                yield b","
                            yield self.encode(entry)
                            entry = None
                    yield b"]"
                yield b"}"
        yield b"}"

    def close(self):
        # Break the temporary reference callbacks before releasing scratch,
        # including with cyclic GC disabled and a saved rejection traceback.
        self.refs = None
        self.dictionaries = None
        self.current = self.before = None
        self.work.release()
        self.cache.encoded_staged -= self.encoded
        self.cache = None


def baseline(cache, view, slot, current):
    from .sync_state import FRAME_LIMIT, _encode_parts, _Encoded

    with closing(_Export(cache, current)) as export:
        export.initialize()
        header = {"kind": "baseline", "descriptor": cache._descriptor(view),
                  "nativeBinding": current.binding, "tag": current.tag, "cursor": current.cursor}
        with closing(export.parts(header)) as parts:
            size = sum(map(len, parts)) + 1
        if size > FRAME_LIMIT:
            raise ContractError("sync_frame_limit")
        with cache._encoded_workspace(size * 2):
            with cache.account.reserve(size * 2 + 8192, kind="encoded") as constructor:
                with closing(export.parts(header)) as parts:
                    data = _encode_parts(_newline(parts), size)
                lease = cache.account.retain_bytes(data, size=512, credit=constructor)
                # Publish the output's retained encoded owner before either
                # construction allowance retires; there is no transfer gap.
                slot.baseline = _Encoded(data, lease)
                cache.counts["baselines"] += 1
    return data


def _newline(parts):
    yield from parts
    yield b"\n"


def _transaction_parts(parts, unsigned_size):
    # transactionId sorts after every unsigned header field. Hash the unsigned
    # closing brace, then replace it with the final ID field and transport LF.
    # This combines hashing and final output without retaining a document or
    # performing a third transformation of every changed row.
    digest = hashlib.sha256(b"mesh-sync-transaction\0" + unsigned_size.to_bytes(8, "big"))
    remaining = unsigned_size
    try:
        for part in parts:
            remaining -= len(part)
            digest.update(part)
            if remaining > 0:
                yield part
            elif remaining == 0 and part == b"}":
                yield b',"transactionId":"'
                yield digest.hexdigest().encode("ascii")
                yield b'"}\n'
            else:
                raise ContractError("sync_compact_transaction_size")
        if remaining:
            raise ContractError("sync_compact_transaction_size")
    finally:
        # Saved failures must not retain the previous encoded row or iterator.
        part = parts = digest = None


def transaction(cache, stage, before, current, changes):
    from .sync_state import FRAME_LIMIT, JOURNAL_LIMIT, _encode_parts

    with closing(_Export(cache, current, before)) as export:
        export.initialize()
        header = {"kind": "transaction", "descriptor": cache._descriptor(current.binding["view"]),
                  "nativeBindingDigest": current.tag[0], "baseTag": before.tag,
                  "resultTag": current.tag, "baseCursor": before.cursor, "resultCursor": current.cursor}
        with closing(export.parts(header, changes)) as parts:
            unsigned_size = sum(map(len, parts))
        size = unsigned_size + len(b',"transactionId":"') + 64 + len(b'"') + 1
        if size > min(FRAME_LIMIT, JOURNAL_LIMIT):
            return None, None, 0
        stage.charge_encoded(size * 2)
        try:
            with cache.account.reserve(size * 2 + 8192, kind="encoded") as constructor:
                with closing(export.parts(header, changes)) as parts:
                    with closing(_transaction_parts(parts, unsigned_size)) as signed:
                        data = _encode_parts(signed, size)
                lease = cache.account.retain_bytes(data, size=512, credit=constructor)
        except BaseException:
            stage.release_encoded(size * 2)
            raise
        stage.release_encoded(size)
    return data, lease, size
