"""Generate bounded synthetic candidate raw-schema/restoration inputs.

Uses source helpers and tiny whole-table fixture models, not a runtime codec,
exporter, native provider, generic staging or a resource/performance gate.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from compact_vectors_support import (  # noqa: E402
    pack_baseline,
    pack_transaction,
    raw_transaction_id,
    restore_baseline,
    restore_transaction,
    sorted_tables,
)
from jsonschema import Draft202012Validator  # noqa: E402
from test_sync_compact import expanded_apply, owner_fixture  # noqa: E402
from verify_compact_raw_vectors import c, f, fields, h, root, summary  # noqa: E402

from agent_observer.contract import ContractError, identity_key  # noqa: E402
from agent_observer.sync_commitment import descriptor_digest  # noqa: E402
from agent_observer.sync_compact_schema import CANDIDATE_ENCODING_ID, schema_document  # noqa: E402
from agent_observer.sync_contract import admit_record  # noqa: E402
from agent_observer.sync_native import parse_message  # noqa: E402


def source_binding(view, descriptor):
    return {"host": "fixture", "source": f"agents.{view}",
            "profile": "agent-observer.mesh-sync.v1" if view == "full" else "agent-observer.mesh-active-sync.v1",
            "profileSchema": "a" * 64, "nativeDescriptor": descriptor_digest(descriptor)}


def updated(snapshot, now, kind):
    value = copy.deepcopy(snapshot)
    for row in value["sessions"]:
        if kind == "parked-null-phase":
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        elif kind == "lastUpdated-value-change":
            row["lastUpdated"]["at"] += 1000
        elif kind == "observation-only-refresh":
            for field in ("runtime", "phase", "lastUpdated", "latestTurn"):
                if row[field] is not None:
                    row[field]["observedAt"] += 1000
        for field in ("lastUpdated", "latestTurn"):
            row[field]["receipt"].update(sampledBoottimeMs=now, observedBoottimeMs=now)
    return value


def joined_rows(logical, sources):
    tables = logical["tables"]
    rows = []
    for identity, slot in tables["records"]:
        body = next(value for key, value in tables["bodies"] if key == slot["body"])
        observed = next(value for key, value in tables["observations"] if key == [identity, slot["birth"]])
        row, values = admit_record(body, observed["fields"], "fixture", sources)
        rows.append({"identity": identity, "birth": slot["birth"], "row": row, "fieldInputs": values})
    return sorted(rows, key=lambda row: c(row["identity"]))


def reborn_target(before):
    """Invariants-preserving synthetic alias reuse, not native occurrence proof."""
    result = copy.deepcopy(before)
    tables, generation = result["tables"], result["tag"][1] + 1
    old_identity, slot = tables["records"][0]
    identity = [*old_identity[:4], "00000000-0000-0000-0000-000000000099"]
    birth = [result["nativeBinding"]["ownerEpoch"], generation]
    body = tables["bodies"][0][1]
    body["identity"]["nativeId"] = body["nativeIds"]["threadId"] = identity[4]
    # sessionTreeRootId deliberately stays distinct from the new thread ID.
    digest = bytes.fromhex(descriptor_digest(result["descriptor"]))
    body_hash = h(b"mesh-sync-body\0", f(digest), f(c(body))).hex()
    tables["bodies"][0][0] = body_hash
    tables["records"][0] = [identity, {**slot, "birth": birth, "body": body_hash,
                                      "order": [slot["order"][0], identity]}]
    tables["observations"][0][0] = [identity, birth]
    values = fields(body)
    for entry in tables["memberships"]:
        cohort, _old_identity, _old_birth, field = entry[0]
        entry[0] = [cohort, identity, birth, field]
        entry[1] = h(b"mesh-sync-field\0", f(digest), f(c(identity)), f(c(birth)),
                     f(field.encode()), f(c(values[field]))).hex()
    for key, value in tables["scopes"]:
        if len(key) == 4 and key[2] == "members":
            key[3] = identity
            value["identity"]["nativeId"] = identity[4]
    for cohort, value in tables["cohorts"]:
        members = [[key[1:], token] for key, token in tables["memberships"] if key[0] == cohort]
        member_root = root("cohort-members", members)
        if value["seal"][1:] != [member_root, len(members)]:
            value["seal"] = [generation, member_root, len(members)]
    summaries = [[name, root(name, rows), len(rows)] for name, rows in sorted(tables.items())]
    native = h(b"mesh-sync-native\0", f(c(result["nativeBinding"])), generation.to_bytes(8, "big"),
               f(c(summaries))).hex()
    result["tag"][1:] = [generation, native]
    result["cursor"][1:] = [generation, native]
    return result


def logical_delta(before, after):
    operations = {}
    for space in before["tables"]:
        old = {c(key): (key, value) for key, value in before["tables"][space]}
        new = {c(key): (key, value) for key, value in after["tables"][space]}
        rows = []
        for key in sorted(set(old) | set(new)):
            previous, current = old.get(key), new.get(key)
            if previous == current:
                continue
            expected = None if previous is None else h(b"mesh-sync-value\0", f(space.encode()),
                                                       f(c(previous[1]))).hex()
            rows.append(["remove", previous[0], expected] if current is None else
                        ["put", current[0], expected, current[1]])
        operations[space] = rows
    message = {"kind": "transaction", "descriptor": before["descriptor"],
               "nativeBindingDigest": before["tag"][0], "baseTag": before["tag"],
               "resultTag": after["tag"], "baseCursor": before["cursor"],
               "resultCursor": after["cursor"], "operations": operations}
    message["transactionId"] = raw_transaction_id(message)
    return message


def vectors():
    validator = Draft202012Validator(schema_document())
    baselines, transactions = [], []
    for kind in ("running", "parked-null-phase", "observation-only-refresh", "lastUpdated-value-change"):
        owner, snapshot, now = owner_fixture(1)
        try:
            if kind != "running":
                now[0] += 10
                value = updated(snapshot, now[0], kind)
                owner.attempt("codex", "history")
                owner.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
            sources = {(source["provider"], source["namespace"]): source for source in owner.snapshot["sources"]}
            for view in ("full", "active"):
                original = parse_message(owner.sync_baseline(view), view, "fixture")
                raw = pack_baseline(original)
                validator.validate(raw)
                restored, _tokens = restore_baseline(raw)
                assert restored["tables"] == sorted_tables(original["tables"])
                binding = source_binding(view, original["descriptor"])
                joined = joined_rows(restored, sources)
                expected_rows = owner.snapshot["sessions"] if view == "full" else owner.active_projection["sessions"]
                assert [record["row"] for record in joined] == sorted(expected_rows, key=lambda row: identity_key(row["identity"]))
                baselines.append({"name": f"{view}-{kind}", "raw": raw, "expected": restored,
                                  "sourceBinding": binding, "summary": summary(restored, binding),
                                  "joined": joined})
        finally:
            if owner._sync_cache is not None:
                owner._sync_cache.close()
    # Each independent chain starts from the same deterministic running fixture.
    for kind in ("lastUpdated-value-change", "parked-null-phase"):
        owner, snapshot, now = owner_fixture(1)
        try:
            before = {view: parse_message(owner.sync_baseline(view), view, "fixture") for view in ("full", "active")}
            now[0] += 10
            value = updated(snapshot, now[0], kind)
            owner.attempt("codex", "history")
            owner.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
            for view in ("full", "active"):
                target = parse_message(owner.sync_baseline(view), view, "fixture")
                current, previous = before[view], f"{view}-running"
                for index, encoded in enumerate(owner.sync_changes(view, current["tag"], target["tag"])):
                    message = parse_message(encoded, view, "fixture")
                    if message["kind"] == "control":
                        continue
                    after = expanded_apply(current, message)
                    raw = pack_transaction(message, current, after)
                    validator.validate(raw)
                    restored = restore_transaction(raw, current)
                    assert restored["tables"] == sorted_tables(after["tables"])
                    binding = source_binding(view, message["descriptor"])
                    name = f"{view}-{kind}-delta-{index}"
                    transactions.append({"name": name, "before": previous, "raw": raw,
                                         "expected": restored, "sourceBinding": binding,
                                         "summary": summary(restored, binding)})
                    current, previous = after, name
                assert current["tag"] == target["tag"]
        finally:
            owner._sync_cache.close()
    for view in ("full", "active"):
        before = next(case["expected"] for case in baselines if case["name"] == f"{view}-running")
        target = reborn_target(before)
        raw = pack_transaction(logical_delta(before, target), before, target)
        validator.validate(raw)
        restored = restore_transaction(raw, before)
        assert restored["tables"] == sorted_tables(target["tables"])
        binding = source_binding(view, target["descriptor"])
        transactions.append({"name": f"{view}-alias-reuse", "before": f"{view}-running", "raw": raw,
                             "expected": restored, "sourceBinding": binding,
                             "summary": summary(restored, binding),
                             "scope": "synthetic invariant-preserving old-A/new-B same alias and new birth; no native occurrence evidence"})
    rejection_base = next(case for case in transactions if case["name"] == "active-alias-reuse")
    rejections = []
    for name in ("wrong-before-birth", "wrong-after-birth", "combined-rebirth-group", "wrong-old-mask",
                 "duplicate-group", "wrong-expected-old", "wrong-body-id", "wrong-cohort-seal"):
        raw = copy.deepcopy(rejection_base["raw"])
        groups = raw["operations"]["memberships"]
        removal = next(group for group in groups if group[2] is None)
        insertion = next(group for group in groups if group[0] is None)
        if name == "wrong-before-birth":
            removal[0][2] = insertion[2][2]
        elif name == "wrong-after-birth":
            insertion[2][2] = removal[0][2]
        elif name == "combined-rebirth-group":
            groups.remove(removal)
            groups.remove(insertion)
            groups.append([removal[0], removal[1], insertion[2], insertion[3]])
        elif name == "wrong-old-mask":
            removal[1] = 1 if removal[1] != 1 else 2
        elif name == "duplicate-group":
            groups.append(copy.deepcopy(removal))
        elif name == "wrong-expected-old":
            next(op for op in raw["operations"]["records"] if op[0] == "remove")[2] = "f" * 64
        elif name == "wrong-body-id":
            next(op for op in raw["operations"]["bodies"] if op[0] == "put")[3][2] = "changed-title"
        else:
            next(op for op in raw["operations"]["cohorts"] if op[0] == "put")[3][0][1] = "f" * 64
        raw["transactionId"] = raw_transaction_id(raw)
        validator.validate(raw)  # These are beyond JSON Schema, not type errors.
        before = next(case["expected"] for case in baselines if case["name"] == rejection_base["before"])
        try:
            restored = restore_transaction(raw, before)
            summary(restored, rejection_base["sourceBinding"])
        except (ContractError, ValueError, KeyError, StopIteration):
            pass
        else:
            raise AssertionError(name)
        rejections.append({"name": name, "before": rejection_base["before"], "raw": raw,
                           "sourceBinding": rejection_base["sourceBinding"], "schemaValid": True})
    schema_raw = (ROOT / "agent_observer/contracts/sync-compact-frame.schema.json").read_bytes()
    return {"status": "candidate schema/encoding, no allocation or compatibility freeze",
            "encodingIdProposal": CANDIDATE_ENCODING_ID, "schemaSha256": h(schema_raw).hex(),
            "schemaIdProposal": "urn:agent-observer:sync-compact-frame:1",
            "scope": "bounded source-generated native-shaped synthetic rows, tiny whole-map restoration model and independent arithmetic; no runtime codec/exporter/native/resource/performance acceptance",
            "baselines": baselines, "transactions": transactions, "rejections": rejections}


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True, indent=2, ensure_ascii=False))
