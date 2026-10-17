#!/usr/bin/env python3
"""Independent stdlib R2 reference model; no codec/cache/schema admission.

This imports neither producer nor the upstream oracle. Toy definitions are
explicit inputs. Mask assertions are not checked against admitted cell state.
Ownership, lifetime, rollback, resource and native-schema gates remain external.
"""

import itertools
import json
import sys
from hashlib import sha256
from pathlib import Path

EPOCH = "00000000-0000-4000-8000-000000000001"
RUNTIME = ["codex", "namespace", "runtime"]
HISTORY = ["codex", "namespace", "history"]
IDENTITIES = {name: ["fixture", "codex", "namespace", "thread", name] for name in "abc"}
DEFINITIONS = {
    "before": {(7, 1): IDENTITIES["a"], (8, 1): IDENTITIES["c"]},
    "after": {(7, 2): IDENTITIES["b"], (8, 1): IDENTITIES["c"]},
}
DICTIONARIES = {"before": [RUNTIME, HISTORY], "after": [HISTORY, RUNTIME]}
REMOVAL = [[0, 7, 1], 1, None, 0]
INSERTION = [None, None, [1, 7, 2], 1]


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("integer")
    return value


def receipt_dictionaries(value):
    if type(value) is not dict or set(value) != {"before", "after"}:
        raise ValueError("dictionaries")
    result = {}
    for side in ("before", "after"):
        rows = value[side]
        if type(rows) is not list or len(rows) > 32:
            raise ValueError("dictionary_capacity")
        keys = []
        for row in rows:
            if type(row) is not list or len(row) != 3 or any(type(x) is not str or not x for x in row):
                raise ValueError("receipt_key")
            key = tuple(row)
            if key in keys:
                raise ValueError("duplicate_receipt")
            keys.append(key)
        result[side] = keys
    return result


def record_ref(raw, side, epoch=EPOCH):
    if type(raw) is not list or len(raw) != 2 or side not in DEFINITIONS or epoch != EPOCH:
        raise ValueError("record_scope")
    alias = integer(raw[0], 1, 2**64 - 1)
    birth = integer(raw[1], 1, 2)
    identity = DEFINITIONS[side].get((alias, birth))
    if identity is None:
        raise ValueError("definition")
    return [identity, [epoch, birth]]


def side_ref(raw, side, dictionaries):
    keys = receipt_dictionaries(dictionaries)
    if type(raw) is not list or len(raw) != 3 or side not in keys:
        raise ValueError("group_side")
    index = integer(raw[0], 0, len(keys[side]) - 1)
    return list(keys[side][index]), record_ref(raw[1:], side)


def group_edit(raw, dictionaries):
    if type(raw) is not list or len(raw) != 4:
        raise ValueError("edit_shape")
    prior_side, prior_mask, target_side, target_mask = raw
    if prior_mask is not None:
        integer(prior_mask, 1, 511)
    integer(target_mask, 0, 511)
    if (prior_side is None) != (prior_mask is None):
        raise ValueError("prior_presence")
    if (target_side is None) != (target_mask == 0):
        raise ValueError("target_presence")
    if prior_side is None and target_side is None:
        raise ValueError("empty_edit")
    resolved = []
    if prior_side is not None:
        resolved.append(side_ref(prior_side, "before", dictionaries))
    if target_side is not None:
        resolved.append(side_ref(target_side, "after", dictionaries))
    if any(value != resolved[0] for value in resolved[1:]):
        raise ValueError("group_identity")
    cohort, record = resolved[0]
    return {"cohort": cohort, "record_ref": record,
            "old_mask": 0 if prior_mask is None else prior_mask, "new_mask": target_mask}


def baseline_group(raw, dictionaries):
    if type(raw) is not list or len(raw) != 2:
        raise ValueError("baseline_shape")
    # An actual baseline has no before dictionary.
    receipt_dictionaries(dictionaries)
    if dictionaries["before"]:
        raise ValueError("baseline_before")
    integer(raw[1], 1, 511)
    return group_edit([None, None, raw[0], raw[1]], dictionaries)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def edit_set(rows, dictionaries):
    by_key = {}
    for row in rows:
        normalized = group_edit(row, dictionaries)
        marker = canonical([normalized["cohort"], normalized["record_ref"]])
        if marker in by_key:
            raise ValueError("duplicate_group")
        by_key[marker] = normalized
    return [by_key[key] for key in sorted(by_key)]


def verify(path):
    raw = path.read_bytes()
    fixture = json.loads(raw)
    cases = {case["name"]: case for case in fixture["positiveCases"]}
    first = cases["reorder-and-alias-reuse"]
    assert edit_set(first["raw"], first["receiptRefs"]) == first["normalized"]
    ordered = cases["reordered-input-equivalence"]
    permutations = tuple(itertools.permutations(first["raw"]))
    assert len(permutations) == ordered["permutations"]
    for permutation in permutations:
        assert edit_set(permutation, first["receiptRefs"]) == ordered["normalized"]
    removed = cases["old-receipt-removed-after"]
    assert group_edit(removed["raw"], removed["receiptRefs"]) == removed["normalized"]
    zero = cases["receipt-index-zero-valid"]
    assert list(side_ref([0, 7, 1], "before", DICTIONARIES)) == zero["before"]
    assert list(side_ref([0, 7, 2], "after", DICTIONARIES)) == zero["after"]
    base = cases["baseline-after-only"]
    assert baseline_group(base["raw"], {"before": [], "after": DICTIONARIES["after"]}) == base["normalized"]
    surviving = cases["surviving-row-receipt-reorder"]
    assert group_edit(surviving["raw"], DICTIONARIES) == surviving["normalized"]

    # Independent calls cover all named fixture rejections. Their error category
    # strings are intentionally not used as an oracle for this second model.
    failures = {
        "reuse-combined-in-one-group": lambda: group_edit([[0, 7, 1], 1, [1, 7, 2], 1], DICTIONARIES),
        "wrong-old-birth": lambda: group_edit([[0, 7, 2], 1, None, 0], DICTIONARIES),
        "wrong-new-birth": lambda: group_edit([None, None, [1, 7, 1], 1], DICTIONARIES),
        "foreign-binding": lambda: record_ref([7, 1], "before", "other-owner"),
        "unknown-alias": lambda: record_ref([99, 1], "before"),
        "cross-cohort-index-rebind": lambda: group_edit([[0, 8, 1], 1, [0, 8, 1], 1], DICTIONARIES),
        "duplicate-logical-group": lambda: edit_set([REMOVAL, REMOVAL], DICTIONARIES),
        "old-zero": lambda: group_edit([[0, 7, 1], 0, None, 0], DICTIONARIES),
        "absent-to-zero": lambda: group_edit([None, None, None, 0], DICTIONARIES),
        "new-null": lambda: group_edit([None, None, [1, 7, 2], None], DICTIONARIES),
        "missing-before": lambda: group_edit([None, 1, None, 0], DICTIONARIES),
        "new-side-with-zero": lambda: group_edit([[0, 7, 1], 1, [1, 7, 2], 0], DICTIONARIES),
        "old-fallback-to-after-index": lambda: side_ref([1, 7, 1], "before", {"before": [RUNTIME], "after": [HISTORY, RUNTIME]}),
        "new-fallback-to-before-index": lambda: side_ref([1, 7, 2], "after", {"before": [RUNTIME, HISTORY], "after": [HISTORY]}),
        "duplicate-receipt-key": lambda: receipt_dictionaries({"before": [RUNTIME, RUNTIME], "after": []}),
        "catalog-extra-field": lambda: receipt_dictionaries({"before": [], "after": [], "other": []}),
        "catalog-over-cap": lambda: receipt_dictionaries({"before": [["p", str(i), "runtime"] for i in range(33)], "after": []}),
    }
    for value in (True, False, None, -1, 2):
        failures["receipt-index-" + repr(value)] = lambda value=value: side_ref([value, 7, 1], "before", DICTIONARIES)
    for value in (True, 0, -1, 512):
        failures["baseline-mask-" + repr(value)] = lambda value=value: baseline_group([[1, 7, 2], value], {"before": [], "after": DICTIONARIES["after"]})
    assert set(failures) == {case["name"] for case in fixture["rejectionCases"]}
    for name, operation in failures.items():
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError(name)
    return {"result": "PASS", "fixtureSha256": sha256(raw).hexdigest(),
            "independentPositiveCases": len(cases), "independentRejections": len(failures),
            "permutations": len(permutations), "producerImports": False,
            "nativeSchemaOrRuntimeAdmission": False,
            "scope": "toy sided references and mask syntax; no admitted masks, receipt existence, authority, lifecycle, roots or resource acceptance"}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2, sort_keys=True))
