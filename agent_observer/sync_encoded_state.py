"""Canonical-byte staging for the new opt-in sync service family.

This is an internal producer implementation, independent of wire packing.
Every retained table has the same logical keys, values and Patricia roots as
the frozen reference backend. Point reads parse detached JSON under the owner
publication's working reservation; pending writes retain canonical bytes only.
"""

from __future__ import annotations

import hashlib
import json
import sys

from .active_contract import FACT_SUPPORT, MEMBER, NONMEMBER, UNCERTAIN
from .contract import SESSION, ContractError
from .sync_commitment import ABSENT, ANY, canonical, frame
from .sync_contract import MOVED_PATHS
from .sync_encoded import EncodedMap, decode_bound


def _default(value):
    return dict(value.items())


def _schema_bound(spec):
    """Compile a canonical-byte bound from the unchanged finite row schema."""
    if "anyOf" in spec:
        return max(map(_schema_bound, spec["anyOf"]))
    if "enum" in spec:
        return max(len(canonical(value)) for value in spec["enum"])
    kind = spec["type"]
    if type(kind) is list:
        return max(_schema_bound(dict(spec, type=value)) for value in kind)
    if kind == "null":
        return 4
    if kind == "boolean":
        return 5
    if kind == "integer":
        return max(len(str(spec["minimum"])), len(str(spec["maximum"])))
    if kind == "string":
        return 2 + 6 * spec["maxLength"]
    if kind == "array":
        return 2 + spec["maxItems"] * (_schema_bound(spec["items"]) + 1)
    if kind == "object":
        return 2 + sum(len(canonical(key)) + _schema_bound(child) + 2
                       for key, child in spec["properties"].items())
    raise ValueError("unbounded row schema")


MAX_ROW_BYTES = _schema_bound(SESSION)


def _empty_string_shape(value):
    if type(value) is list:
        return [_empty_string_shape(child) for child in value]
    if type(value) is dict:
        return {key: 0 if key == "maxLength" else _empty_string_shape(child)
                for key, child in value.items()}
    return value


_ROW_FIXED_BYTES = _schema_bound(_empty_string_shape(SESSION))


def row_content_bound(content):
    """Bound an admitted finite row using actual string lengths, not maxima.

    The compiled full-row overhead pays all possible containers, keys, enum
    values and integer digits. Only bounded string leaves vary per row. This
    is an owner-only size calculation; it does not replace public validation.
    """
    pending = [content]
    characters = 0
    while pending:
        value = pending.pop()
        if type(value) is str:
            characters += len(value)
        elif type(value) is dict:
            pending.extend(value.values())
        elif type(value) in (list, tuple):
            pending.extend(value)
    return _ROW_FIXED_BYTES + 6 * characters


def _moved_bound():
    size = 2
    for name, fields in MOVED_PATHS.items():
        original = SESSION["properties"][name]
        if "anyOf" in original:
            original = original["anyOf"][0]
        shape = dict(original, properties={key: original["properties"][key] for key in fields})
        size += len(canonical(name)) + _schema_bound(shape) + 2
    return size


_SUPPORT_BYTES = _schema_bound(FACT_SUPPORT)
_OBS_BYTES = 64 + _moved_bound() + 9 * (_SUPPORT_BYTES + 64)
_SCOPES_BYTES = 4096 + max(map(_schema_bound, (MEMBER, NONMEMBER, UNCERTAIN)))
_TABLE_BYTES = {
    "records": 4096, "observations": _OBS_BYTES,
    "memberships": 2048, "cohort-members": 2048, "cohorts": 4096,
    "receipts": 8192, "scopes": _SCOPES_BYTES, "bodies": MAX_ROW_BYTES,
}
_PENDING_SIZE = sys.getsizeof((None, None, None, None))


def encode_row_content(stage, content):
    # Stable content is a subset of the already-admitted API 4 row. A fixed
    # schema-derived envelope avoids traversing that whole row merely to
    # discover a reservation on every owner generation.
    stage.decoding(32768)  # the finite row's traversal stack, before allocating
    bound = min(MAX_ROW_BYTES, row_content_bound(content))
    stage.decoding(8192 + bound * 8)
    stage.encoding_workspace(bound * 6)
    result = json.dumps(content, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(result) > MAX_ROW_BYTES:
        raise ContractError("sync_encoding_bound")
    return result


class EncodedTableStage:
    def __init__(self, space, stage, base=None):
        self.space, self.stage, self.base = space, stage, base
        self.entries = {}
        self.storage = None
        self.last_encoded = None
        self.read_storage = None
        self.read_index = None
        self.ownership = stage.cache.encoded_ownership
        self._closed = False
        stage.tables.append(self)
        self.storage = stage.account.reserve(1024, kind="stage")
        self.bytes = 0
        if base is not None and space in {"records", "bodies", "observations"}:
            # Native publication already scans N. One explicit linear pass of
            # immutable byte references avoids N log N point traversals; no
            # bodies are parsed or duplicated. Receivers use sparse lookups.
            self.read_storage = stage.account.reserve(1024 + base.count * 192, kind="stage")
            self.read_index = {key: (key, value) for key, value in base.encoded_items()}
            stage.cache.counts["index_cells"] += base.count

    def _encode(self, value, *, key=False):
        from .sync_state import _json_bound

        # These primitives came from the validated engine or the owner's
        # closed table constructors. External bytes use strict admission.
        bound = 1024 if key else _TABLE_BYTES.get(self.space)
        if bound is None:
            bound = _json_bound(value)
        self.stage.decoding(2048 + bound * 8)
        self.stage.encoding_workspace(bound * 6 + 16)
        result = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False,
                            default=_default).encode("utf-8")
        if len(result) > bound:
            raise ContractError("sync_encoding_bound")
        if key and self.read_index is not None:
            previous = self.read_index.get(result)
            if previous is not None:
                return previous[0]
        return result

    def _parse(self, *values):
        self.stage.decoding(sum(decode_bound(value) for value in values))
        return tuple(json.loads(value) for value in values)

    def _found(self, key, *, digest=True):
        encoded = self._encode(key, key=True)
        pending = self.entries.get(encoded)
        if pending is not None:
            key_bytes, value_bytes, expected, removed = pending
            if removed:
                return ABSENT
        elif self.base is None:
            return ABSENT
        elif self.read_index is not None:
            previous = self.read_index.get(encoded, ABSENT)
            if previous is ABSENT:
                return ABSENT
            key_bytes, value_bytes = previous
        else:
            return self.base.lookup_encoded_entry(encoded, trusted=True,
                                                  scratch=self.stage.working)
        value_digest = (hashlib.sha256(b"mesh-sync-value\0" + frame(self.space.encode())
                                      + frame(value_bytes)).hexdigest() if digest else None)
        return key_bytes, value_bytes, value_digest

    def lookup_entry(self, key, *, digest=True):
        found = self._found(key, digest=digest)
        if found is ABSENT:
            return ABSENT
        key_bytes, value_bytes, digest = found
        parsed_value = self._parse(value_bytes)[0]
        return key, parsed_value, digest, key_bytes, value_bytes

    def lookup_encoded(self, key):
        found = self._found(key, digest=False)
        return ABSENT if found is ABSENT else found[:2]

    def lookup_encoded_entry(self, key):
        return self._found(key)

    def get(self, key, default=ABSENT):
        found = self._found(key, digest=False)
        return default if found is ABSENT else self._parse(found[1])[0]

    def _store(self, key, value, expected, removed):
        key_bytes = self._encode(key, key=True)
        if key_bytes in self.entries:
            raise ContractError("sync_duplicate_owner_edit")
        value_bytes = None if removed else self._encode(value)
        return self._retain(key_bytes, value_bytes, expected, removed)

    def _retain(self, key_bytes, value_bytes, expected, removed):
        size = _PENDING_SIZE + (sys.getsizeof(expected) if type(expected) is str else 0)
        if self.ownership is None:
            size += sys.getsizeof(key_bytes) + (0 if removed else sys.getsizeof(value_bytes))
        # Charge the dictionary resize overlap and all canonical payloads
        # before retaining them. Map adoption subsequently shares those exact
        # byte objects; this temporary reservation ends only after adoption.
        self.storage.resize(1024 + self.bytes + size + max(
            3 * sys.getsizeof(self.entries), 256 + 256 * (len(self.entries) + 1)))
        buffers = (key_bytes,) if removed else (key_bytes, value_bytes)
        if self.ownership is None:
            self.stage.charge_encoded(sum(map(len, buffers)))
        else:
            self.ownership.retain(*buffers)
        self.bytes += size
        try:
            self.entries[key_bytes] = (key_bytes, value_bytes, expected, removed)
        except BaseException:
            if self.ownership is not None:
                self.ownership.release(*buffers)
            raise
        self.last_encoded = key_bytes, value_bytes
        self.storage.resize(1024 + self.bytes + sys.getsizeof(self.entries)
                            + len(self.entries) * 64)
        return self

    def put(self, key, value, *, expected=ANY, prior=ABSENT):
        if expected is ANY:
            found = self._found(key)
            expected = None if found is ABSENT else found[2]
        return self._store(key, value, expected, False)

    def put_value_bytes(self, key, value, *, expected):
        key_bytes = self._encode(key, key=True)
        if key_bytes in self.entries:
            raise ContractError("sync_duplicate_owner_edit")
        return self._retain(key_bytes, value, expected, False)

    def remove(self, key, *, expected=ANY):
        if expected is ANY:
            found = self._found(key)
            if found is ABSENT:
                raise ContractError("sync_missing_owner_edit")
            expected = found[2]
        return self._store(key, None, expected, True)

    def items(self):
        if self.base is not None:
            for key_bytes, value_bytes in self.base.encoded_items():
                if key_bytes not in self.entries:
                    yield self._parse(key_bytes, value_bytes)
        for key_bytes, value_bytes, _, removed in self.entries.values():
            if not removed:
                yield self._parse(key_bytes, value_bytes)

    def finish(self):
        try:
            if not self.entries and self.base is not None:
                return self.base
            if self.base is None:
                return EncodedMap.from_encoded(
                    self.space,
                    ((key, value) for key, value, _, removed in self.entries.values()
                     if not removed), account=self.stage.account, trusted=True)
            return self.base.patch_encoded(
                (("remove", key, expected) if removed else
                 ("put", key, expected, value)
                 for key, value, expected, removed in self.entries.values()), trusted=True)
        finally:
            self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.ownership is not None:
            for key, value, _, removed in self.entries.values():
                # Forced account teardown may precede a cycle's finalizer;
                # explicit normal stage close still releases each live claim.
                self.ownership._release_leaf(key) if removed else self.ownership._release_leaf(key, value)
        self.entries.clear()
        self.bytes = 0
        self.last_encoded = None
        self.read_index = None
        if self.read_storage is not None:
            self.read_storage.release()
        if self.storage is not None:
            self.storage.release()

    def __del__(self):
        self.close()


def empty_map(space, account):
    return EncodedMap(space, account=account)
