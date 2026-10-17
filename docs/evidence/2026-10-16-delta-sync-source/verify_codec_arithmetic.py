"""Independent stdlib arithmetic over the pinned toy codec review fixtures.

This imports neither producer and accepts no Agent schema or runtime codec.
"""

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path


def require(condition, code):
    if not condition:
        raise ValueError(code)


def scalar_json(value):
    kind = type(value)
    require(kind in (dict, list, str, int, bool, type(None)), "json_type")
    if kind is str:
        require(all(not 0xD800 <= ord(c) <= 0xDFFF for c in value), "json_surrogate")
    elif kind is dict:
        for key, child in value.items():
            require(type(key) is str, "json_key")
            scalar_json(key)
            scalar_json(child)
    elif kind is list:
        for child in value:
            scalar_json(child)


def c(value):
    scalar_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def f(value):
    return len(value).to_bytes(8, "big") + value


def h(*parts):
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.digest()


def root(space, entries):
    # Bit-string prefixes and split positions, independent of either runtime
    # node implementation, registry, insertion algorithm or accounting.
    name, leaves, keys = f(space.encode()), [], set()
    for key, value in entries:
        encoded = c(key)
        require(encoded not in keys, "duplicate_key")
        keys.add(encoded)
        key_hash = h(b"mesh-sync-key\0", name, f(encoded))
        bits = "".join(format(byte, "08b") for byte in key_hash)
        value_hash = h(b"mesh-sync-value\0", name, f(c(value)))
        leaves.append((bits, h(b"mesh-sync-leaf\0", name, key_hash, f(encoded), value_hash)))
    leaves.sort()
    require(len({bits for bits, _ in leaves}) == len(leaves), "key_collision")

    def build(start, stop):
        if stop - start == 1:
            return leaves[start][1]
        first, last = leaves[start][0], leaves[stop - 1][0]
        bit = next(i for i, pair in enumerate(zip(first, last, strict=True)) if pair[0] != pair[1])
        middle = next(i for i in range(start, stop) if leaves[i][0][bit] == "1")
        prefix_bits = first[:bit]
        padded = prefix_bits + "0" * (-bit % 8)
        prefix = bytes(int(padded[i:i + 8], 2) for i in range(0, len(padded), 8))
        return h(b"mesh-sync-branch\0", name, bit.to_bytes(2, "big"), f(prefix),
                 build(start, middle), build(middle, stop))

    return (build(0, len(leaves)) if leaves else h(b"mesh-sync-empty\0", name)).hex()


class Oracle:
    def __init__(self, fixture):
        self.fixture = fixture
        self.binding = fixture["nativeBinding"]
        self.digest = bytes.fromhex(fixture["descriptorDigest"])
        self.fields = fixture["fields"]
        self.cohorts = [key for key, _ in fixture["positiveCases"][0]["logicalTables"]["cohorts"]]

    def aliases(self, rows, generation):
        result, identities = {}, set()
        for row in rows:
            identity, birth, alias = row["identity"], row["birth"], row["alias"]
            require(len(identity) == 5 and identity[0] == self.binding["hostScope"], "alias_scope")
            require(type(alias) is int and 0 < alias < 2**64, "alias_range")
            require(birth[0] == self.binding["ownerEpoch"] and type(birth[1]) is int
                    and 0 < birth[1] <= generation, "alias_birth")
            require(alias not in result and c(identity) not in identities, "alias_duplicate")
            result[alias] = row
            identities.add(c(identity))
        return result

    def resolve(self, rows, ref, generation):
        index = self.aliases(rows, generation)
        alias, birth = ref
        require(type(alias) is int and alias in index, "alias_unknown")
        row = index[alias]
        require(c(row["birth"]) == c(birth), "alias_birth")
        return row

    def rows_after(self, before, edits):
        rows = {c(row["identity"]): row for row in before}
        touched = set()
        for op, identity, value in edits:
            key = c(identity)
            require(key not in touched, "record_duplicate_operation")
            touched.add(key)
            old = rows.get(key)
            if op == "remove":
                require(old is not None and value is None, "record_remove")
                del rows[key]
            else:
                require(op == "put" and value["identity"] == identity, "record_put")
                if old is None:
                    require(value["birth"][1] == 2, "record_new_birth")
                else:
                    require((old["alias"], old["birth"]) == (value["alias"], value["birth"]), "record_rebirth")
                rows[key] = value
        output = list(rows.values())
        self.aliases(output, 2)
        return output

    @staticmethod
    def mask(bits, *, stored=False):
        require(type(bits) is int and int(stored) <= bits <= 511, "mask_range")

    @staticmethod
    def group_key(cohort, row):
        return c([cohort, row["identity"], row["birth"]])

    def groups(self, rows, specs, generation):
        result = {}
        for cohort, alias, birth, bits in specs:
            self.mask(bits, stored=True)
            key = self.group_key(cohort, self.resolve(rows, [alias, birth], generation))
            require(key not in result, "mask_duplicate")
            result[key] = bits
        return result

    def groups_after(self, before, after, old, edits):
        result, touched = dict(old), set()
        for cohort, old_ref, expected, new_ref, mask in edits:
            require((old_ref is None) == (expected is None), "mask_before_ref")
            self.mask(mask)
            require((new_ref is None) == (mask == 0), "mask_after_ref")
            require(expected is not None or mask != 0, "mask_empty")
            old_row = None if old_ref is None else self.resolve(before, old_ref, 1)
            new_row = None if new_ref is None else self.resolve(after, new_ref, 2)
            if old_row is not None and new_row is not None:
                require(self.group_key(cohort, old_row) == self.group_key(cohort, new_row), "mask_reference")
            key = self.group_key(cohort, old_row if old_row is not None else new_row)
            require(key not in touched, "mask_duplicate")
            touched.add(key)
            if expected is None:
                require(key not in old, "mask_expected")
            else:
                self.mask(expected, stored=True)
                require(old.get(key) == expected, "mask_expected")
            if mask:
                result[key] = mask
            else:
                result.pop(key, None)
        return result

    def token(self, row, name):
        return h(b"mesh-sync-field\0", f(self.digest), f(c(row["identity"])), f(c(row["birth"])),
                 f(name.encode()), f(c(row["fields"][name]))).hex()

    def state(self, rows, groups, generation, previous=None):
        tables = {name: [] for name in ("records", "bodies", "observations", "memberships",
                                        "receipts", "cohorts", "scopes", "metadata")}
        by_ref = {c([row["identity"], row["birth"]]): row for row in rows}
        for row in rows:
            identity, birth = row["identity"], row["birth"]
            body = {name: row[name] for name in ("identity", "fields", "title")}
            body_id = h(b"mesh-sync-body\0", f(self.digest), f(c(body))).hex()
            tables["records"].append([identity, {"alias": row["alias"], "birth": birth, "body": body_id,
                                                   "order": [0, identity], "scope": identity[1:3]}])
            tables["bodies"].append([body_id, body])
            tables["observations"].append([[identity, birth], {"reviewOnly": True}])
            tables["scopes"].append([[*identity[1:3], "member", identity], birth])
        for encoded, mask in groups.items():
            cohort, identity, birth = json.loads(encoded)
            row = by_ref.get(c([identity, birth]))
            require(row is not None, "mask_orphan")
            for bit, field in enumerate(self.fields):
                if mask & (1 << bit):
                    tables["memberships"].append([[cohort, identity, birth, field], self.token(row, field)])
        for cohort in self.cohorts:
            members = [[key[1:], value] for key, value in tables["memberships"] if key[0] == cohort]
            seal = [generation, root("cohort-members", members), len(members)]
            if previous is not None:
                prior = next(value["seal"] for key, value in previous["cohorts"] if key == cohort)
                if prior[1:] == seal[1:]:
                    seal[0] = prior[0]
            tables["cohorts"].append([cohort, {"receipt": cohort, "seal": seal}])
            tables["receipts"].append([cohort, {"reviewAccepted": generation}])
        tables["metadata"] = [["reviewGeneration", generation]]
        return tables

    def summary(self, tables, generation):
        roots = [[name, root(name, entries), len(entries)] for name, entries in sorted(tables.items())]
        native = h(b"mesh-sync-native\0", f(c(self.binding)), generation.to_bytes(8, "big"), f(c(roots))).hex()
        return {"tables": roots, "nativeRoot": native}


def verify(fixture):
    oracle = Oracle(fixture)
    before = fixture["beforeRows"]
    old = oracle.groups(before, fixture["beforeGroups"], 1)
    prior = oracle.state(before, old, 1)
    require(oracle.summary(prior, 1) == fixture["before"], "before_roots")
    permutations, touched = 0, []
    old_cells = {c(key): value for key, value in prior["memberships"]}
    for case in fixture["positiveCases"]:
        after = oracle.rows_after(before, case["recordEdits"])
        groups = oracle.groups_after(before, after, old, case["groupChanges"])
        require(groups == oracle.groups(after, case["expectedGroups"], 2), "group_result")
        state = oracle.state(after, groups, 2, prior)
        require(oracle.summary(state, 2) == case["after"], "after_roots")
        for space, entries in state.items():
            actual = {c(key): c(value) for key, value in entries}
            expected = {c(key): c(value) for key, value in case["logicalTables"][space]}
            require(actual == expected, "logical_table_" + space)
        new_cells = {c(key): value for key, value in state["memberships"]}
        changed = sum(old_cells.get(key) != new_cells.get(key) for key in old_cells.keys() | new_cells.keys())
        require(changed == case["logicalMembershipKeysTouched"], "changed_cells")
        touched.append(changed)
        count = 0
        for records in itertools.permutations(case["recordEdits"]):
            for edits in itertools.permutations(case["groupChanges"]):
                rows = oracle.rows_after(before, records)
                require(oracle.groups_after(before, rows, old, edits) == groups, "permutation")
                count += 1
        require(count == case["permutations"], "permutation_count")
        permutations += count
    optional = []
    for case in fixture["optionalValueTokens"]:
        row = copy.deepcopy(before[0])
        row["fields"]["workspace"] = case["value"]
        token = oracle.token(row, "workspace")
        require(token == case["fieldToken"], "optional_token")
        optional.append(token)
    require(len(set(optional)) == 4, "optional_distinction")
    return {"positiveCases": len(fixture["positiveCases"]), "tableRootsPerState": 8,
            "permutations": permutations, "membershipChanges": touched,
            "optionalTokens": len(optional), "outcome": "PASS",
            "exclusions": ["37 rejection cases not independently executed by this script",
                           "toy values are not Agent domain rows", "no runtime codec/storage/ownership/CPU acceptance"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    raw = args.fixture.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == "5a2abd9ecf309acf9fd37de54bcaa05ef636bcfc07e8a96ab6e549e5dd409adb",
            "fixture_hash")
    result = verify(json.loads(raw))
    result["fixtureSha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
