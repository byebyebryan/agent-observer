"""Independent stdlib compact restoration/commitments over synthetic vectors.

Imports neither producer nor Mesh. This is a deliberately small whole-map model,
not strict JSON Schema validation, streaming/sparse staging, lifetime/resource,
native proof, installed codec or authority acceptance.
"""

import copy
import json
import sys
from pathlib import Path

from verify_codec_arithmetic import c, f, h, require, root

BODY = ("identity", "nativeIds", "title", "kind", "cwd", "cwdSource", "inventory",
        "hasSavedHistory", "phase", "runtime", "outcome", "blockedReasons", "createdAt",
        "activity", "lastUpdated", "latestTurn", "workspace", "metadataIssues")
FIELDS = ("runtime", "phase", "kind", "savedIdentity", "activity", "outcome", "workspace",
          "lastUpdated", "latestTurn")
MOVED = ("runtime", "phase", "activity", "outcome", "lastUpdated", "latestTurn")
TIMING = ("component", "sampledBoottimeMs", "observedBoottimeMs", "contextGeneration")
SPACES = ("records", "bodies", "observations", "memberships", "receipts", "cohorts", "scopes", "metadata")


def fields(body):
    return {"runtime": body["runtime"], "phase": None if body["phase"] is None else
            {"phase": body["phase"], "blockedReasons": body["blockedReasons"]},
            "kind": body["kind"], "savedIdentity": {"inventory": body["inventory"], "hasSavedHistory": body["hasSavedHistory"]},
            "activity": body["activity"], "outcome": body["outcome"],
            "workspace": {"workspace": body["workspace"], "cwd": body["cwd"], "cwdSource": body["cwdSource"]},
            "lastUpdated": body["lastUpdated"], "latestTurn": body["latestTurn"]}


def joined_rows(message):
    """Independent lossless partition join; no API 4 semantic admission."""
    tables = message["tables"]
    bodies = dict(tables["bodies"])
    observations = {c(key): value for key, value in tables["observations"]}
    joined = []
    for identity, record in tables["records"]:
        body = bodies[record["body"]]
        moved = observations[c([identity, record["birth"]])]["fields"]
        require(set(moved) == set(MOVED) - ({"phase"} if body["phase"] is None else set()), "join_partition")
        row = copy.deepcopy(body)
        for name, values in moved.items():
            require(type(row[name]) is dict and not (set(row[name]) & set(values)), "join_partition")
            row[name].update(copy.deepcopy(values))
        joined.append({"identity": identity, "birth": record["birth"], "row": row, "fieldInputs": fields(body)})
    return sorted(joined, key=lambda value: c(value["identity"]))


class Context:
    def __init__(self, message, binding, before, after):
        self.epoch = binding["ownerEpoch"]
        self.generation = message.get("tag", message.get("resultTag"))[1]
        self.keys = message["receiptRefs"]
        require(set(self.keys) == {"before", "after"}, "dictionary_keys")
        self.aliases = {}
        for side, state in (("before", before), ("after", after)):
            keys = self.keys[side]
            require(len(keys) <= 32 and len({c(key) for key in keys}) == len(keys), "dictionary_keys")
            actual = {c(key) for key, _ in state["receipts"]}
            require(all(c(key) in actual for key in keys), "dictionary_existence")
            self.aliases[side] = {}
            for identity, slot in state["records"]:
                alias = slot["alias"]
                require(type(alias) is int and 1 <= alias < 2**64 and alias not in self.aliases[side], "alias")
                self.aliases[side][alias] = [identity, slot["birth"]]

    def record(self, value, side):
        require(type(value) is list and len(value) == 2, "reference")
        alias, generation = value
        require(type(alias) is int and type(generation) is int and 1 <= generation <= self.generation, "reference")
        require(alias in self.aliases[side], "alias")
        full = self.aliases[side][alias]
        require(full[1] == [self.epoch, generation], "birth")
        return full

    def receipt(self, value, side):
        require(type(value) is int and 0 <= value < len(self.keys[side]), "receipt_index")
        return self.keys[side][value]


def slot(key, value, epoch):
    alias, birth, body, order = value
    return {"birth": [epoch, birth], "alias": alias, "body": body,
            "order": [order, key], "scope": key[1:3]}


def decode(space, key, value, ctx, side):
    if space == "records":
        return key, slot(key, value, ctx.epoch)
    if space == "bodies":
        require(len(value) == len(BODY), "body")
        body = dict(zip(BODY, value, strict=True))
        full = ctx.record(body["identity"], side)
        body["identity"] = dict(zip(("hostScope", "provider", "namespace", "nativeIdKind", "nativeId"), full[0], strict=True))
        return key, body
    if space == "observations":
        moved, supported = value
        require(len(moved) == 6 and len(supported) == 9, "observations")
        observed = {}
        for name, item in zip(MOVED, moved, strict=True):
            if name == "phase" and item is None:
                continue
            if name in ("activity", "outcome"):
                observed[name] = {"health": item}
            else:
                observed[name] = {"health": item[0], "observedAt": item[1]}
                if name in ("lastUpdated", "latestTurn"):
                    observed[name]["receipt"] = None if item[2] is None else dict(zip(TIMING, item[2], strict=True))
        support = {name: ["cohort", ctx.receipt(item, side)] if type(item) is int else item
                   for name, item in zip(FIELDS, supported, strict=True)}
        return ctx.record(key, side), {"fields": observed, "supports": support}
    if space == "cohorts":
        cohort = ctx.receipt(key, side)
        return cohort, {"receipt": cohort, **dict(zip(
            ("seal", "accepted", "sampledBoottimeMs", "expiresBoottimeMs"), value, strict=True))}
    if space == "scopes" and len(key) == 2 and key[0] == "members":
        identity, _birth = ctx.record(key[1], side)
        return [*identity[1:3], "members", identity], {
            "identity": dict(zip(("hostScope", "provider", "namespace", "nativeIdKind", "nativeId"), identity, strict=True)),
            "fields": {name: None if item is None else ctx.receipt(item, side)
                       for name, item in zip(FIELDS, value, strict=True)}}
    return key, value


def decode_key(space, key, ctx, side):
    if space == "observations":
        return ctx.record(key, side)
    if space == "cohorts":
        return ctx.receipt(key, side)
    if space == "scopes" and len(key) == 2 and key[0] == "members":
        identity, _birth = ctx.record(key[1], side)
        return [*identity[1:3], "members", identity]
    return key


def masks(tables):
    result = {}
    for (cohort, identity, birth, field), _token in tables["memberships"]:
        key = c([cohort, identity, birth])
        if key not in result:
            result[key] = [cohort, identity, birth, 0]
        bit = 1 << FIELDS.index(field)
        require(not result[key][3] & bit, "duplicate_cell")
        result[key][3] |= bit
    return result


def resolve_group(value, ctx, *, change=False):
    def side(raw, name):
        require(type(raw) is list and len(raw) == 3, "group_side")
        return [ctx.receipt(raw[0], name), *ctx.record(raw[1:], name)]

    if not change:
        raw, mask = value
        require(type(mask) is int and 1 <= mask <= 511, "mask")
        return [*side(raw, "after"), None, mask]
    old, old_mask, new, new_mask = value
    require((old is None) == (old_mask is None) and type(new_mask) is int and 0 <= new_mask <= 511,
            "mask")
    require((new is None) == (new_mask == 0) and not (old is None and new is None), "mask")
    require(old_mask is None or type(old_mask) is int and 1 <= old_mask <= 511, "mask")
    before, after = None if old is None else side(old, "before"), None if new is None else side(new, "after")
    require(before is None or after is None or before == after, "group_identity")
    return [*(before if after is None else after), old_mask, new_mask]


def cells_from_masks(tables, groups, descriptor):
    digest = h(c(descriptor))
    records = {c(identity): slot for identity, slot in tables["records"]}
    bodies = dict(tables["bodies"])
    tokens, count = {}, 0
    for identity, record in tables["records"]:
        body = bodies[record["body"]]
        require(record["body"] == h(b"mesh-sync-body\0", f(digest), f(c(body))).hex(), "body_id")
        values = fields(body)
        tokens[c([identity, record["birth"]])] = {
            name: h(b"mesh-sync-field\0", f(digest), f(c(identity)), f(c(record["birth"])),
                    f(name.encode()), f(c(value))).hex() for name, value in values.items()}
        count += 9
    cells = []
    for cohort, identity, birth, mask in groups.values():
        require(records[c(identity)]["birth"] == birth, "group_birth")
        values = tokens[c([identity, birth])]
        cells.extend([[cohort, identity, birth, field], values[field]]
                     for bit, field in enumerate(FIELDS) if mask & 1 << bit)
    return cells, count


def baseline(message):
    binding = message["nativeBinding"]
    tables = {name: [] for name in SPACES}
    tables["records"] = [[key, slot(key, value, binding["ownerEpoch"])] for key, value in message["tables"]["records"]]
    tables["receipts"] = message["tables"]["receipts"]
    require(message["receiptRefs"]["before"] == [], "baseline_before")
    ctx = Context(message, binding, {name: [] for name in SPACES}, tables)
    for space in SPACES:
        if space not in ("records", "receipts", "memberships"):
            tables[space] = [list(decode(space, key, value, ctx, "after")) for key, value in message["tables"][space]]
    groups = {}
    for raw in message["tables"]["memberships"]:
        cohort, identity, birth, _old, mask = resolve_group(raw, ctx)
        key = c([cohort, identity, birth])
        require(key not in groups, "duplicate_group")
        groups[key] = [cohort, identity, birth, mask]
    tables["memberships"], tokens = cells_from_masks(tables, groups, message["descriptor"])
    return {"nativeBinding": binding, "descriptor": message["descriptor"], "tag": message["tag"],
            "cursor": message["cursor"], "tables": tables}, tokens


def transaction(message, before):
    require(message["transactionId"] == h(b"mesh-sync-transaction\0", f(c({
        key: value for key, value in message.items() if key != "transactionId"}))).hex(), "transaction_id")
    require(message["baseTag"] == before["tag"] and message["baseCursor"] == before["cursor"], "base")
    tables = {name: {c(key): [key, value] for key, value in rows} for name, rows in before["tables"].items()}

    def apply(space, raw, ctx=None):
        op, key, expected = raw[:3]
        if space == "records" and op == "put":
            value = slot(key, raw[3], before["nativeBinding"]["ownerEpoch"])
        elif op == "put":
            key, value = (key, raw[3]) if ctx is None else decode(space, key, raw[3], ctx, "after")
        elif ctx is not None:
            key = decode_key(space, key, ctx, "before")
        marker = c(key)
        prior = tables[space].get(marker)
        actual = None if prior is None else h(b"mesh-sync-value\0", f(space.encode()), f(c(prior[1]))).hex()
        require(expected == actual and (op != "remove" or prior is not None), "expected_old")
        if op == "remove":
            tables[space].pop(marker)
        else:
            tables[space][marker] = [key, value]

    for space in ("records", "receipts"):
        for raw in message["operations"][space]:
            apply(space, raw)
    provisional = {name: list(values.values()) for name, values in tables.items()}
    ctx = Context(message, before["nativeBinding"], before["tables"], provisional)
    for space in SPACES:
        if space not in ("records", "receipts", "memberships"):
            for raw in message["operations"][space]:
                apply(space, raw, ctx)
    groups, seen = masks(before["tables"]), set()
    for raw in message["operations"]["memberships"]:
        cohort, identity, birth, old_mask, new_mask = resolve_group(raw, ctx, change=True)
        key = c([cohort, identity, birth])
        require(key not in seen, "duplicate_group")
        seen.add(key)
        require((groups.get(key, [None, None, None, 0])[3] or None) == old_mask, "old_mask")
        if new_mask:
            groups[key] = [cohort, identity, birth, new_mask]
        else:
            groups.pop(key)
    restored = {name: list(values.values()) for name, values in tables.items()}
    restored["memberships"], tokens = cells_from_masks(restored, groups, message["descriptor"])
    return {"nativeBinding": before["nativeBinding"], "descriptor": message["descriptor"],
            "tag": message["resultTag"], "cursor": message["resultCursor"], "tables": restored}, tokens


def summary(message, source_binding):
    tables = message["tables"]
    result = [[name, root(name, tables[name]), len(tables[name])] for name in sorted(SPACES)]
    native = h(b"mesh-sync-native\0", f(c(message["nativeBinding"])),
               message["tag"][1].to_bytes(8, "big"), f(c(result))).hex()
    require(message["tag"][0] == h(b"mesh-sync-native-binding\0", f(c(message["nativeBinding"]))).hex(),
            "native_binding")
    require(message["cursor"] == [message["nativeBinding"]["ownerEpoch"], message["tag"][1], native],
            "cursor")
    require(native == message["tag"][2], "native_root")
    for cohort, value in tables["cohorts"]:
        members = [[key[1:], token] for key, token in tables["memberships"] if key[0] == cohort]
        require(value["seal"][1:] == [root("cohort-members", members), len(members)], "cohort_root")
    return {"tables": result, "nativeRoot": native,
            "sourceRoot": h(b"mesh-sync-source\0", f(c(source_binding)), bytes.fromhex(native)).hex()}


def verify(path):
    fixture = json.loads(path.read_text())
    states, total_tokens, total_joined = {}, 0, 0
    for case in fixture["baselines"]:
        restored, tokens = baseline(case["raw"])
        require(all(sorted(restored["tables"][name], key=lambda pair: c(pair[0])) ==
                    sorted(case["expected"]["tables"][name], key=lambda pair: c(pair[0])) for name in SPACES), "tables")
        require(summary(restored, case["sourceBinding"]) == case["summary"], "summary")
        joined = joined_rows(restored)
        require(joined == case["joined"], "joined_api4_bytes")
        total_joined += len(joined)
        states[case["name"]] = restored
        total_tokens += tokens
    for case in fixture["transactions"]:
        before = copy.deepcopy(states[case["before"]])
        stable = c(before)
        restored, tokens = transaction(case["raw"], before)
        require(c(before) == stable, "prior_mutated")
        require(all(sorted(restored["tables"][name], key=lambda pair: c(pair[0])) ==
                    sorted(case["expected"]["tables"][name], key=lambda pair: c(pair[0])) for name in SPACES), "tables")
        require(summary(restored, case["sourceBinding"]) == case["summary"], "summary")
        states[case["name"]] = restored
        total_tokens += tokens
    for case in fixture.get("rejections", []):
        before = copy.deepcopy(states[case["before"]])
        stable = c(before)
        try:
            restored, _tokens = transaction(case["raw"], before)
            summary(restored, case["sourceBinding"])
        except (ValueError, KeyError, StopIteration):
            pass
        else:
            raise AssertionError(case["name"])
        require(c(before) == stable, "failed_model_mutated_prior")
    return {"result": "PASS", "baselines": len(fixture["baselines"]),
            "transactions": len(fixture["transactions"]), "independentFieldTokens": total_tokens,
            "independentJoinedBaselineRows": total_joined,
            "independentModelRejections": len(fixture.get("rejections", [])),
            "fixtureSha256": h(path.read_bytes()).hex(), "producerImports": False,
            "scope": "synthetic whole-map restoration/expected-old/masks/body+token/eight-table/cohort/native/source arithmetic; no schema/runtime/sparse/lifetime/resource/native authority acceptance"}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), sort_keys=True, indent=2))
