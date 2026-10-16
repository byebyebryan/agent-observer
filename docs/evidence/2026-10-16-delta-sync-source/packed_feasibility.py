"""Split-table size/root feasibility only; no accepted schema or live endpoint."""

import copy
import gc
import hashlib
import json
import sys
import uuid

from bench_sync_producer import native_shaped_snapshot
from test_sync_state import _root

from agent_observer.contract import canonical as legacy_canonical
from agent_observer.observation_support import SUPPORT_FIELDS
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import body_id, canonical, descriptor_digest, native_root, thaw
from agent_observer.sync_contract import field_tokens
from agent_observer.sync_state import SPACES, OwnerSyncCache

n = int(sys.argv[1])
boot, value, wall = native_shaped_snapshot(n)
owner_clock = [15000]
uuid.uuid4 = lambda: uuid.UUID(int=0xF000 + owner_clock[0])
state = ServiceState(
    host_scope="fixture",
    configs={"codex": ("/fixture/codex", "explicit")},
    uid=1000,
    clock=lambda: owner_clock[0],
    boot_id=boot,
    clock_domain="time:[123]",
)
state.wall_clock = lambda: wall + owner_clock[0]
state.attempt("codex", "history")
state.accept("codex", "history", value, sampled_ms=15000, ttl_ms=60000, runtime_ttl_ms=60000)


def pack(commit, descriptor):
    tables = {s: [[thaw(k), thaw(v)] for k, v in commit.tables[s].items()] for s in SPACES}
    receipts = [key for key, _ in tables["receipts"]]
    receipt_numbers = {canonical(key): i for i, key in enumerate(receipts)}
    records = sorted(tables["records"], key=lambda item: item[1]["alias"])
    bodies = {key: value for key, value in tables["bodies"]}
    observations = {canonical(key): value for key, value in tables["observations"]}
    packed = {
        "kind": "baseline",
        "encoding": "agent.tables/1",
        "descriptor": descriptor,
        "nativeBinding": thaw(commit.binding),
        "tag": thaw(commit.tag),
        "cursor": thaw(commit.cursor),
        "records": [],
        "bodies": [],
        "observations": [],
        "memberships": [],
        "tables": {s: tables[s] for s in ("receipts", "cohorts", "scopes", "metadata")},
    }
    for identity, slot in records:
        alias, birth, key = slot["alias"], slot["birth"], slot["body"]
        assert birth[0] == packed["nativeBinding"]["ownerEpoch"]
        packed["records"].append([alias, identity, birth[1], key, slot["order"][0]])
        content = copy.deepcopy(bodies[key])
        content.pop("identity")
        packed["bodies"].append([key, [alias, content]])
        obs = observations[canonical([identity, birth])]
        refs, masks = [], {}
        for bit, field in enumerate(SUPPORT_FIELDS):
            ref = obs["supports"][field]
            if ref is None or ref[0] != "cohort":
                refs.append(ref)
            else:
                number = receipt_numbers[canonical(ref[1])]
                refs.append(number)
                masks[number] = masks.get(number, 0) | (1 << bit)
        packed["observations"].append([alias, [obs["fields"], refs]])
        packed["memberships"].extend(
            [number, alias, mask] for number, mask in sorted(masks.items())
        )
    return packed, tables


def unpack(packed):
    """A deliberately simple detached oracle, not a budgeted production codec."""
    tables = {s: [] for s in SPACES}
    tables.update(copy.deepcopy(packed["tables"]))
    refs = [key for key, _ in tables["receipts"]]
    definitions, body_slots = {}, {}
    epoch = packed["nativeBinding"]["ownerEpoch"]
    for alias, identity, generation, body, group in packed["records"]:
        if alias in definitions or body in body_slots:
            raise ValueError("duplicate definition")
        birth = [epoch, generation]
        definitions[alias] = identity, birth
        body_slots[body] = alias
        tables["records"].append(
            [
                identity,
                {
                    "alias": alias,
                    "birth": birth,
                    "body": body,
                    "order": [group, identity],
                    "scope": identity[1:3],
                },
            ]
        )
    bodies = {}
    for key, (alias, bare) in packed["bodies"]:
        if key in bodies or body_slots.get(key) != alias or "identity" in bare:
            raise ValueError("body alias mismatch")
        identity, birth = definitions[alias]
        content = {
            **bare,
            "identity": dict(
                zip(
                    ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId"),
                    identity,
                    strict=True,
                )
            ),
        }
        if body_id(descriptor_digest(packed["descriptor"]), content) != key:
            raise ValueError("body digest mismatch")
        bodies[key] = content
        tables["bodies"].append([key, content])
    if set(bodies) != set(body_slots):
        raise ValueError("missing body")
    observed, masks = set(), {}
    for alias, (fields, supports) in packed["observations"]:
        if alias not in definitions or alias in observed or len(supports) != len(SUPPORT_FIELDS):
            raise ValueError("observation alias mismatch")
        observed.add(alias)
        identity, birth = definitions[alias]
        normalized = {}
        for bit, (field, ref) in enumerate(zip(SUPPORT_FIELDS, supports, strict=True)):
            if type(ref) is int:
                if not 0 <= ref < len(refs):
                    raise ValueError("unknown receipt")
                normalized[field] = ["cohort", refs[ref]]
                masks[ref, alias] = masks.get((ref, alias), 0) | (1 << bit)
            else:
                normalized[field] = ref
        tables["observations"].append(
            [[identity, birth], {"fields": fields, "supports": normalized}]
        )
    if observed != set(definitions):
        raise ValueError("missing observation")
    groups = {(number, alias): mask for number, alias, mask in packed["memberships"]}
    if len(groups) != len(packed["memberships"]) or groups != masks:
        raise ValueError("membership mask mismatch")
    tokens = {}
    for key, alias in body_slots.items():
        identity, birth = definitions[alias]
        tokens[alias] = field_tokens(
            descriptor_digest(packed["descriptor"]), identity, birth, bodies[key]
        )
    for (number, alias), mask in groups.items():
        identity, birth = definitions[alias]
        for bit, field in enumerate(SUPPORT_FIELDS):
            if mask & (1 << bit):
                tables["memberships"].append(
                    [[refs[number], identity, birth, field], tokens[alias][field]]
                )
    return tables


owner = OwnerSyncCache(state, backend="encoded")
results = []
for view in ("full", "active"):
    owner.ensure(view)
    current = owner.views[view].current
    packed, original = pack(current, owner._descriptor(view))
    encoded = canonical(packed) + b"\n"
    restored = unpack(json.loads(encoded))
    for space in SPACES:
        assert {canonical(k): canonical(v) for k, v in original[space]} == {
            canonical(k): canonical(v) for k, v in restored[space]
        }, space
    summary = [
        [s, _root(s, {canonical(k): v for k, v in restored[s]}), len(restored[s])]
        for s in sorted(SPACES)
    ]
    rebuilt = native_root(
        packed["nativeBinding"], current.generation, summary, expected_spaces=SPACES
    )
    assert rebuilt == current.tag[2]
    frame = state.frame("view", 1) if view == "full" else state.active_frame("view", 1)
    old = len(legacy_canonical(frame).encode()) + 1
    # Mutate only declared structural positions; no native/domain semantics inferred.
    rejected = 0
    if packed["records"]:
        bad = copy.deepcopy(packed)
        bad["records"].append(bad["records"][0])
        try:
            unpack(bad)
        except ValueError:
            rejected += 1
        bad = copy.deepcopy(packed)
        bad["bodies"][0][1][0] = 2**63
        try:
            unpack(bad)
        except (ValueError, KeyError):
            rejected += 1
        bad = copy.deepcopy(packed)
        bad["observations"][0][0] = 2**63
        try:
            unpack(bad)
        except ValueError:
            rejected += 1
        bad = copy.deepcopy(packed)
        bad["memberships"][0][2] ^= 1
        try:
            unpack(bad)
        except ValueError:
            rejected += 1
        assert rejected == 4
    results.append(
        {
            "view": view,
            "records": len(packed["records"]),
            "legacyBytes": old,
            "packedBytes": len(encoded),
            "coldIncrease": len(encoded) / old - 1,
            "frameFits": len(encoded) <= 8404992,
            "allTablesEqual": True,
            "independentNativeRootEqual": True,
            "badReferencesRejected": rejected,
            "packedSha256": hashlib.sha256(encoded).hexdigest(),
        }
    )
del current
owner.close()
gc.collect()
assert owner.account.snapshot()["used"] == owner.account.snapshot()["base"]
assert owner.account.snapshot()["objects"] == 0
print(
    json.dumps(
        {
            "rows": n,
            "results": results,
            "closedAccount": owner.account.snapshot(),
            "scope": "synthetic split-table feasibility, not emitted schema/runtime/acceptance",
        },
        sort_keys=True,
    )
)
