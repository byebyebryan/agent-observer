"""Candidate one-value compact transforms; no I/O, staging or authority.

Callers validate each complete raw value against the candidate schema before
restoration. Nested literal values remain borrowed from the one current input
row until synchronous pack/serialization; this never builds a detached roster.
Caller-owned plan/row/overlay scratch needs the existing aggregate reservation.
"""

from __future__ import annotations

from .contract import IDENTITY, ContractError, identity_key, validate_shape
from .sync_compact_schema import BODY_FIELDS, MOVED_FIELDS, SUPPORT_FIELDS, TIMING_FIELDS


def check(condition, code):
    if not condition:
        raise ContractError(code)


def _integer(value, maximum, minimum=0):
    return type(value) is int and minimum <= value <= maximum


def _tuple(value, size):
    check(type(value) is list and len(value) == size, "sync_compact_tuple")


class References:
    """Bounded sided dictionaries plus exact keyed caller-provided lookups.

    Lookups return plain one-value JSON under caller-owned scratch. They are
    structural provisional definitions or admitted before values, never authority.
    Receipt existence is checked even for unused dictionary keys.
    """

    def __init__(self, owner_epoch, generation, receipt_refs, *, lookup_record,
                 lookup_alias, receipt_exists, baseline=False):
        check(type(owner_epoch) is str and _integer(generation, 2**64 - 1), "sync_compact_binding")
        check(type(receipt_refs) is dict and set(receipt_refs) == {"before", "after"}, "sync_compact_receipt_refs")
        self.epoch, self.generation = owner_epoch, generation
        self._record, self._alias = lookup_record, lookup_alias
        self._keys = {}
        for side in ("before", "after"):
            keys = receipt_refs[side]
            check(type(keys) is list and len(keys) <= 32, "sync_compact_receipt_refs")
            seen = set()
            for key in keys:
                _tuple(key, 3)
                check(all(type(part) is str for part in key), "sync_compact_receipt_key")
                marker = tuple(key)
                check(marker not in seen and receipt_exists(side, key), "sync_compact_receipt_key")
                seen.add(marker)
            self._keys[side] = tuple(tuple(key) for key in keys)
        check(not baseline or not self._keys["before"], "sync_compact_baseline_before")

    def receipt(self, index, side):
        check(side in self._keys and _integer(index, len(self._keys[side]) - 1), "sync_compact_receipt_index")
        return list(self._keys[side][index])

    def receipt_index(self, key, side):
        check(side in self._keys and type(key) is list, "sync_compact_receipt_index")
        try:
            return self._keys[side].index(tuple(key))
        except ValueError:
            raise ContractError("sync_compact_receipt_index") from None

    def record(self, raw, side):
        _tuple(raw, 2)
        alias, generation = raw
        check(side in self._keys and _integer(alias, 2**64 - 1, 1)
              and _integer(generation, self.generation, 1), "sync_compact_record_ref")
        full = self._alias(side, alias)
        check(type(full) is list and len(full) == 2 and full[1] == [self.epoch, generation],
              "sync_compact_record_birth")
        _tuple(full[0], 5)
        validate_shape(dict(zip(IDENTITY["required"], full[0], strict=True)), IDENTITY)
        return [list(full[0]), list(full[1])]

    def raw_record(self, identity, birth, side):
        check(side in self._keys, "sync_compact_record_ref")
        slot = self._record(side, identity)
        check(type(slot) is dict and slot["birth"] == birth and birth[0] == self.epoch
              and _integer(birth[1], self.generation, 1)
              and _integer(slot["alias"], 2**64 - 1, 1), "sync_compact_record_birth")
        return [slot["alias"], birth[1]]

    def slot(self, identity, side):
        check(side in self._keys, "sync_compact_record_ref")
        value = self._record(side, identity)
        check(type(value) is dict, "sync_compact_record_ref")
        return value


def _timing(value):
    return None if value is None else [value[name] for name in TIMING_FIELDS]


def _restore_timing(value):
    if value is None:
        return None
    _tuple(value, len(TIMING_FIELDS))
    return dict(zip(TIMING_FIELDS, value, strict=True))


def _observations(value, refs, side):
    fields, supports = value["fields"], value["supports"]
    moved = []
    for name in MOVED_FIELDS:
        if name == "phase" and name not in fields:
            moved.append(None)
        elif name in {"activity", "outcome"}:
            moved.append(fields[name]["health"])
        else:
            fact = fields[name]
            moved.append([fact["health"], fact["observedAt"]]
                         + ([_timing(fact["receipt"])] if name in {"lastUpdated", "latestTurn"} else []))
    check(set(supports) == set(SUPPORT_FIELDS), "sync_compact_supports")
    encoded_supports = []
    for name in SUPPORT_FIELDS:
        support = supports[name]
        if type(support) is list and len(support) == 2 and support[0] == "cohort":
            encoded_supports.append(refs.receipt_index(support[1], side))
        else:
            check(support is None or type(support) is list and len(support) == 2 and support[0] == "context",
                  "sync_compact_supports")
            encoded_supports.append(support)
    return [moved, encoded_supports]


def _restore_observations(value, refs, side):
    _tuple(value, 2)
    moved, raw_supports = value
    _tuple(moved, len(MOVED_FIELDS))
    _tuple(raw_supports, len(SUPPORT_FIELDS))
    fields, supports = {}, {}
    for name, item in zip(MOVED_FIELDS, moved, strict=True):
        if name == "phase" and item is None:
            continue
        if name in {"activity", "outcome"}:
            fields[name] = {"health": item}
        else:
            _tuple(item, 3 if name in {"lastUpdated", "latestTurn"} else 2)
            fields[name] = {"health": item[0], "observedAt": item[1]}
            if len(item) == 3:
                fields[name]["receipt"] = _restore_timing(item[2])
    for name, item in zip(SUPPORT_FIELDS, raw_supports, strict=True):
        if type(item) is int:
            supports[name] = ["cohort", refs.receipt(item, side)]
        else:
            check(item is None or type(item) is list and len(item) == 2 and item[0] == "context",
                  "sync_compact_supports")
            supports[name] = item
    return {"fields": fields, "supports": supports}


def _scope_key(key, refs, side, *, restore=False):
    if restore:
        if len(key) == 2 and key[0] == "members":
            identity, _birth = refs.record(key[1], side)
            return [*identity[1:3], "members", identity]
    elif len(key) == 4 and key[2] == "members":
        identity = key[3]
        check(key[:2] == identity[1:3], "sync_compact_scope_identity")
        return ["members", refs.raw_record(identity, refs.slot(identity, side)["birth"], side)]
    return key


def pack_value(space, key, value, refs, *, side="after"):
    """Transform one valid logical value; literal children stay borrowed."""
    if space == "records":
        check(value["order"] == [value["order"][0], key] and value["scope"] == key[1:3]
              and value["birth"][0] == refs.epoch
              and _integer(value["birth"][1], refs.generation, 1)
              and _integer(value["alias"], 2**64 - 1, 1)
              and _integer(value["order"][0], 1), "sync_compact_slot")
        return key, [value["alias"], value["birth"][1], value["body"], value["order"][0]]
    if space == "bodies":
        identity = list(identity_key(value["identity"]))
        raw = refs.raw_record(identity, refs.slot(identity, side)["birth"], side)
        return key, [raw if name == "identity" else value[name] for name in BODY_FIELDS]
    if space == "observations":
        return refs.raw_record(*key, side), _observations(value, refs, side)
    if space == "cohorts":
        check(value["receipt"] == key, "sync_compact_cohort_receipt")
        return refs.receipt_index(key, side), [value[name] for name in
            ("seal", "accepted", "sampledBoottimeMs", "expiresBoottimeMs")]
    if space == "scopes":
        raw_key = _scope_key(key, refs, side)
        if len(key) == 4 and key[2] == "members":
            check(list(identity_key(value["identity"])) == key[3]
                  and set(value["fields"]) == set(SUPPORT_FIELDS), "sync_compact_scope_identity")
            value = [None if value["fields"][name] is None
                     else refs.receipt_index(value["fields"][name], side) for name in SUPPORT_FIELDS]
        return raw_key, value
    check(space in {"receipts", "metadata"}, "sync_compact_space")
    return key, value


def restore_value(space, key, value, refs, *, side="after"):
    """Restore one schema-checked value for immediate caller-owned packing."""
    if space == "records":
        _tuple(value, 4)
        check(_integer(value[0], 2**64 - 1, 1) and _integer(value[1], refs.generation, 1)
              and _integer(value[3], 1), "sync_compact_slot")
        return key, {"alias": value[0], "birth": [refs.epoch, value[1]], "body": value[2],
                     "order": [value[3], key], "scope": key[1:3]}
    if space == "bodies":
        _tuple(value, len(BODY_FIELDS))
        result = dict(zip(BODY_FIELDS, value, strict=True))
        identity, _birth = refs.record(result["identity"], side)
        result["identity"] = dict(zip(IDENTITY["required"], identity, strict=True))
        return key, result
    if space == "observations":
        return refs.record(key, side), _restore_observations(value, refs, side)
    if space == "cohorts":
        _tuple(value, 4)
        cohort = refs.receipt(key, side)
        return cohort, {"receipt": cohort, **dict(zip(
            ("seal", "accepted", "sampledBoottimeMs", "expiresBoottimeMs"), value, strict=True))}
    if space == "scopes":
        full_key = _scope_key(key, refs, side, restore=True)
        if len(key) == 2 and key[0] == "members":
            _tuple(value, len(SUPPORT_FIELDS))
            value = {"identity": dict(zip(IDENTITY["required"], full_key[3], strict=True)),
                     "fields": {name: None if index is None else refs.receipt(index, side)
                                for name, index in zip(SUPPORT_FIELDS, value, strict=True)}}
        return full_key, value
    check(space in {"receipts", "metadata"}, "sync_compact_space")
    return key, value


def transform_key(space, key, refs, *, side, restore=False):
    if space == "observations":
        return refs.record(key, side) if restore else refs.raw_record(*key, side)
    if space == "cohorts":
        return refs.receipt(key, side) if restore else refs.receipt_index(key, side)
    if space == "scopes":
        return _scope_key(key, refs, side, restore=restore)
    check(space in {"records", "bodies", "receipts", "metadata"}, "sync_compact_space")
    return key


def transform_operation(space, operation, refs, *, restore=False):
    op, key, expected = operation[:3]
    check(op in {"put", "remove"}, "sync_compact_operation")
    side = "before" if op == "remove" else "after"
    if op == "remove":
        return [op, transform_key(space, key, refs, side=side, restore=restore), expected]
    function = restore_value if restore else pack_value
    key, value = function(space, key, operation[3], refs, side=side)
    return [op, key, expected, value]


def restore_group(raw, refs, *, change=False):
    """Return a provisional resolved group; generic expansion is independent."""
    def resolve(side, value):
        _tuple(value, 3)
        return refs.receipt(value[0], side), refs.record(value[1:], side)

    if not change:
        _tuple(raw, 2)
        check(_integer(raw[1], 511, 1), "sync_compact_mask")
        cohort, record = resolve("after", raw[0])
        return {"cohort": cohort, "before_ref": None, "old_mask": None,
                "after_ref": record, "new_mask": raw[1]}
    _tuple(raw, 4)
    old, old_mask, new, new_mask = raw
    check((old is None) == (old_mask is None) and _integer(new_mask, 511)
          and (new is None) == (new_mask == 0) and not (old is None and new is None),
          "sync_compact_mask")
    check(old_mask is None or _integer(old_mask, 511, 1), "sync_compact_mask")
    before = None if old is None else resolve("before", old)
    after = None if new is None else resolve("after", new)
    check(before is None or after is None or before == after, "sync_compact_group_identity")
    cohort = (before if after is None else after)[0]
    return {"cohort": cohort, "before_ref": None if before is None else before[1],
            "old_mask": old_mask, "after_ref": None if after is None else after[1], "new_mask": new_mask}
