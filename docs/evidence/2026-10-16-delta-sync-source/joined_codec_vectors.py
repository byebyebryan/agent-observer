"""Small synthetic native join/token fixtures, independent hash calculations.

No compact codec, provider, transport, storage or authority is exercised.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from bench_sync_producer import native_shaped_snapshot  # noqa: E402

from agent_observer.contract import ContractError, identity_key  # noqa: E402
from agent_observer.sync_commitment import body_id, descriptor_digest  # noqa: E402
from agent_observer.sync_contract import admit_record, field_tokens, split_record  # noqa: E402
from agent_observer.sync_native import descriptor  # noqa: E402


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def framed(value):
    return len(value).to_bytes(8, "big") + value


def partition(row):
    # Independent literal nine-input/moved-path extraction; do not call the
    # implementation's MOVED_PATHS or _field_values to construct expectations.
    body, observations = copy.deepcopy(row), {}
    paths = {"runtime": ("health", "observedAt"), "phase": ("health", "observedAt"),
             "activity": ("health",), "outcome": ("health",),
             "lastUpdated": ("health", "observedAt", "receipt"),
             "latestTurn": ("health", "observedAt", "receipt")}
    for field, moved in paths.items():
        if body[field] is not None:
            observations[field] = {name: body[field].pop(name) for name in moved}
    inputs = {"runtime": body["runtime"],
              "phase": None if body["phase"] is None else
              {"phase": body["phase"], "blockedReasons": body["blockedReasons"]},
              "kind": body["kind"],
              "savedIdentity": {"inventory": body["inventory"], "hasSavedHistory": body["hasSavedHistory"]},
              "activity": body["activity"], "outcome": body["outcome"],
              "workspace": {"workspace": body["workspace"], "cwd": body["cwd"], "cwdSource": body["cwdSource"]},
              "lastUpdated": body["lastUpdated"], "latestTurn": body["latestTurn"]}
    return body, observations, inputs


def vectors():
    _, snapshot, _ = native_shaped_snapshot(1)
    sources = {(s["provider"], s["namespace"]): s for s in snapshot["sources"]}
    row = snapshot["sessions"][0]
    cases = [("running", row)]
    parked = copy.deepcopy(row)
    parked["runtime"]["value"], parked["phase"], parked["blockedReasons"] = "parked", None, []
    cases.append(("parked-null-phase", parked))
    refreshed = copy.deepcopy(row)
    for name in ("runtime", "phase", "lastUpdated", "latestTurn"):
        if refreshed[name] is not None:
            refreshed[name]["observedAt"] += 1000
    for name in ("lastUpdated", "latestTurn"):
        refreshed[name]["receipt"]["observedBoottimeMs"] += 1
    cases.append(("observation-only-refresh", refreshed))
    changed = copy.deepcopy(row)
    changed["lastUpdated"]["at"] += 1000
    cases.append(("native-lastUpdated-value-change", changed))
    birth = ["00000000-0000-4000-8000-000000000001", 1]
    output, rejections = [], []
    for view in ("full", "active"):
        digest = descriptor_digest(descriptor(view))
        previous = None
        for name, current in cases:
            identity = list(identity_key(current["identity"]))
            body, observed, inputs = partition(current)
            assert split_record(current) == (body, observed)
            joined, admitted_inputs = admit_record(body, observed, "fixture", sources)
            assert joined == current and admitted_inputs == inputs
            expected_body = hashlib.sha256(b"mesh-sync-body\0" + framed(bytes.fromhex(digest))
                                           + framed(canonical(body))).hexdigest()
            assert body_id(digest, body) == expected_body
            expected_tokens = {}
            for field, value in inputs.items():
                raw = (b"mesh-sync-field\0" + framed(bytes.fromhex(digest)) + framed(canonical(identity))
                       + framed(canonical(birth)) + framed(field.encode()) + framed(canonical(value)))
                expected_tokens[field] = hashlib.sha256(raw).hexdigest()
            assert field_tokens(digest, identity, birth, body) == expected_tokens
            record = {"name": name, "view": view, "nativeDescriptorDigest": digest,
                      "identity": identity, "birth": birth, "body": body, "observations": observed,
                      "fieldInputs": inputs, "bodyId": expected_body, "tokens": expected_tokens}
            if name == "running":
                previous = record
            elif name == "observation-only-refresh":
                assert record["bodyId"] == previous["bodyId"] and record["tokens"] == previous["tokens"]
            elif name == "native-lastUpdated-value-change":
                assert record["bodyId"] != previous["bodyId"]
                assert [k for k in expected_tokens if expected_tokens[k] != previous["tokens"][k]] == ["lastUpdated"]
            output.append(record)
        body, observed, _ = partition(row)
        for name, broken in (("missing-runtime-observation", {k: v for k, v in observed.items() if k != "runtime"}),
                             ("null-runtime-observation", {**observed, "runtime": None})):
            try:
                admit_record(body, broken, "fixture", sources)
            except ContractError as error:
                rejections.append({"view": view, "name": name, "error": str(error)})
            else:
                raise AssertionError("accepted bad partition")
    return {"scope": "synthetic joined native body/observation/token vectors; no compact runtime/admission/authority or storage acceptance",
            "cases": output, "rejections": rejections,
            "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                       [ROOT / "tests/fixtures/service-v4/view.json", ROOT / "tests/bench_sync_producer.py",
                        ROOT / "agent_observer/sync_contract.py", ROOT / "agent_observer/sync_native.py",
                        ROOT / "agent_observer/contract.py", Path(__file__).resolve()]}}


if __name__ == "__main__":
    print(json.dumps(vectors(), sort_keys=True, ensure_ascii=False, indent=2))
