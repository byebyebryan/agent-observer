"""Small DOM reference model for candidate vectors, never a runtime exporter.

This deliberately rebuilds tiny fixture tables. It is not sparse/streaming,
accounted transport, generic staging, expected-old or producer acceptance.
"""

import copy
import hashlib

from agent_observer.sync_commitment import (
    canonical,
    descriptor_digest,
    field_token,
    frame,
    value_hash,
)
from agent_observer.sync_compact_schema import SUPPORT_FIELDS
from agent_observer.sync_compact_values import (
    References,
    pack_value,
    restore_group,
    restore_value,
    transform_operation,
)
from agent_observer.sync_contract import field_values
from agent_observer.sync_native import TABLES


def sorted_tables(tables):
    return {name: sorted(entries, key=lambda pair: canonical(pair[0])) for name, entries in tables.items()}


def reference_context(binding, generation, receipt_refs, before, after, *, baseline=False):
    states = {"before": before, "after": after}

    def record(side, identity):
        return next((value for key, value in states[side]["records"] if key == identity), None)

    def alias(side, number):
        found = [[key, value["birth"]] for key, value in states[side]["records"] if value["alias"] == number]
        if len(found) != 1:
            raise ValueError("fixture_alias")
        return found[0]

    def receipt_exists(side, key):
        return any(key == existing for existing, _ in states[side]["receipts"])

    return References(binding["ownerEpoch"], generation, receipt_refs, lookup_record=record,
                      lookup_alias=alias, receipt_exists=receipt_exists, baseline=baseline)


def group_masks(tables):
    result = {}
    for (cohort, identity, birth, field), _token in tables["memberships"]:
        key = canonical([cohort, identity, birth])
        if key not in result:
            result[key] = [cohort, identity, birth, 0]
        bit = 1 << SUPPORT_FIELDS.index(field)
        if result[key][3] & bit:
            raise ValueError("fixture_duplicate_cell")
        result[key][3] |= bit
    return result


def pack_baseline(message, *, reverse_receipts=True):
    """Fixture-only whole-message adapter; production must stream one value."""
    before = dict.fromkeys(TABLES, [])
    after = message["tables"]
    keys = [key for key, _ in after["receipts"]]
    receipt_refs = {"before": [], "after": keys[::-1] if reverse_receipts else keys}
    refs = reference_context(message["nativeBinding"], message["tag"][1], receipt_refs,
                             before, after, baseline=True)
    tables = {name: [] for name in TABLES}
    for name in TABLES:
        if name != "memberships":
            tables[name] = [list(pack_value(name, key, value, refs)) for key, value in after[name]]
    for _key, (cohort, identity, birth, mask) in sorted(group_masks(after).items()):
        tables["memberships"].append([[refs.receipt_index(cohort, "after"),
                                       *refs.raw_record(identity, birth, "after")], mask])
    return {**{key: value for key, value in message.items() if key != "tables"},
            "receiptRefs": receipt_refs, "tables": tables}


def restore_baseline(message):
    """Model the declared records first, then independently derive logical cells."""
    tables, binding = {name: [] for name in TABLES}, message["nativeBinding"]
    for identity, (alias, generation, body, order) in message["tables"]["records"]:
        tables["records"].append([identity, {"alias": alias, "birth": [binding["ownerEpoch"], generation],
            "body": body, "order": [order, identity], "scope": identity[1:3]}])
    tables["receipts"] = copy.deepcopy(message["tables"]["receipts"])
    refs = reference_context(binding, message["tag"][1], message["receiptRefs"],
                             dict.fromkeys(TABLES, []), tables, baseline=True)
    for name in TABLES:
        if name not in {"records", "receipts", "memberships"}:
            tables[name] = [list(restore_value(name, key, value, refs))
                            for key, value in message["tables"][name]]
    digest = descriptor_digest(message["descriptor"])
    tokens, rows = {}, []
    for identity, slot in tables["records"]:
        body = next(value for key, value in tables["bodies"] if key == slot["body"])
        inputs = field_values(body)
        tokens[canonical([identity, slot["birth"]])] = {
            name: field_token(digest, identity, slot["birth"], name, inputs[name]) for name in SUPPORT_FIELDS}
        rows.append({"identity": identity, "birth": slot["birth"], "bodyId": slot["body"],
                     "body": body, "fields": inputs,
                     "tokens": tokens[canonical([identity, slot["birth"]])]})
    seen = set()
    for raw in message["tables"]["memberships"]:
        group = restore_group(raw, refs)
        identity, birth = group["after_ref"]
        token = tokens[canonical(group["after_ref"])]
        for bit, name in enumerate(SUPPORT_FIELDS):
            if group["new_mask"] & (1 << bit):
                key = [group["cohort"], identity, birth, name]
                if canonical(key) in seen:
                    raise ValueError("fixture_duplicate_group")
                seen.add(canonical(key))
                tables["memberships"].append([key, token[name]])
    restored = {**{key: value for key, value in message.items() if key not in {"tables", "receiptRefs"}},
                "tables": sorted_tables(tables)}
    return restored, rows


def raw_transaction_id(message):
    original = {key: value for key, value in message.items() if key != "transactionId"}
    return hashlib.sha256(b"mesh-sync-transaction\0" + frame(canonical(original))).hexdigest()


def pack_transaction(message, before, after, *, equal_assertion=False):
    receipt_refs = {"before": [key for key, _ in before["tables"]["receipts"]],
                    "after": [key for key, _ in after["tables"]["receipts"]][::-1]}
    refs = reference_context(before["nativeBinding"], after["tag"][1], receipt_refs,
                             before["tables"], after["tables"])
    operations = {name: [] for name in TABLES}
    for name in TABLES:
        if name != "memberships":
            operations[name] = [transform_operation(name, operation, refs)
                                for operation in message["operations"][name]]
    old, new = group_masks(before["tables"]), group_masks(after["tables"])
    asserted = False
    for key in sorted(set(old) | set(new)):
        old_mask = old.get(key, [None, None, None, 0])[3]
        new_mask = new.get(key, [None, None, None, 0])[3]
        if old_mask == new_mask and (not equal_assertion or asserted):
            continue
        asserted |= old_mask == new_mask
        cohort, identity, birth = (old if key in old else new)[key][:3]
        prior = None if old_mask == 0 else [refs.receipt_index(cohort, "before"),
                                          *refs.raw_record(identity, birth, "before")]
        target = None if new_mask == 0 else [refs.receipt_index(cohort, "after"),
                                           *refs.raw_record(identity, birth, "after")]
        operations["memberships"].append([prior, old_mask or None, target, new_mask])
    raw = {**{key: value for key, value in message.items() if key != "operations"},
           "receiptRefs": receipt_refs, "operations": operations}
    raw["transactionId"] = raw_transaction_id(raw)
    return raw


def restore_transaction(message, before):
    """Tiny full-map model, including admitted old masks and token-only edits.

    This model explicitly enumerates fixture tables. It is never the generic
    runtime callback/patch writer or a claimed sparse implementation.
    """
    cells = {name: {canonical(key): [key, value] for key, value in values}
             for name, values in before["tables"].items()}

    def apply(space, operation):
        op, key, expected = operation[:3]
        marker = canonical(key)
        previous = cells[space].get(marker)
        actual = None if previous is None else value_hash(space, previous[1])
        if actual != expected or op == "remove" and previous is None:
            raise ValueError("fixture_expected_old")
        if op == "remove":
            del cells[space][marker]
        else:
            cells[space][marker] = [key, operation[3]]

    binding = before["nativeBinding"]

    class Epoch:
        epoch = binding["ownerEpoch"]
        generation = message["resultTag"][1]

    # Records use full identity keys; receipts use full receipt keys. Their
    # definitions can be staged before resolving any compact body/group refs.
    for operation in message["operations"]["records"]:
        op, key, expected = operation[:3]
        if op == "put":
            key, value = restore_value("records", key, operation[3], Epoch())
            apply("records", [op, key, expected, value])
        else:
            apply("records", operation)
    for operation in message["operations"]["receipts"]:
        apply("receipts", operation)
    provisional = {name: list(values.values()) for name, values in cells.items()}
    refs = reference_context(binding, message["resultTag"][1], message["receiptRefs"],
                             before["tables"], provisional)
    for space in TABLES:
        if space not in {"records", "receipts", "memberships"}:
            for operation in message["operations"][space]:
                apply(space, transform_operation(space, operation, refs, restore=True))
    masks = group_masks(before["tables"])
    seen = set()
    for raw in message["operations"]["memberships"]:
        group = restore_group(raw, refs, change=True)
        record = group["after_ref"] if group["after_ref"] is not None else group["before_ref"]
        identity, birth = record
        cohort = group["cohort"]
        key = canonical([cohort, identity, birth])
        if key in seen:
            raise ValueError("fixture_duplicate_group")
        seen.add(key)
        actual = masks.get(key, [None, None, None, 0])[3] or None
        if actual != group["old_mask"]:
            raise ValueError("fixture_old_mask")
        if not group["new_mask"]:
            masks.pop(key)
        else:
            masks[key] = [cohort, identity, birth, group["new_mask"]]
    tables = {name: list(values.values()) for name, values in cells.items()}
    descriptor_hash = descriptor_digest(message["descriptor"])
    memberships = []
    for cohort, identity, birth, mask in masks.values():
        slot = next(value for key, value in tables["records"] if key == identity)
        if slot["birth"] != birth:
            raise ValueError("fixture_old_birth")
        content = next(value for key, value in tables["bodies"] if key == slot["body"])
        inputs = field_values(content)
        for bit, field in enumerate(SUPPORT_FIELDS):
            if mask & 1 << bit:
                memberships.append([[cohort, identity, birth, field],
                    field_token(descriptor_hash, identity, birth, field, inputs[field])])
    tables["memberships"] = memberships
    return {"kind": "baseline", "descriptor": message["descriptor"], "nativeBinding": binding,
            "tag": message["resultTag"], "cursor": message["resultCursor"],
            "tables": sorted_tables(tables)}
