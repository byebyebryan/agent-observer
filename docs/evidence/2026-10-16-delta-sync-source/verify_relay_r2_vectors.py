"""Independent stdlib checks of R2 toy binding/splice/attenuation fixtures.

Imports neither producer. Fixture roots/descriptors are unadmitted inputs.
Byte-fragment splicing is distinct from actual native/LineChannel framing.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path


def c(value):
    def strict(item):
        kind = type(item)
        assert kind in (dict, list, str, int, bool, type(None))
        if kind is dict:
            for key, child in item.items():
                assert type(key) is str
                strict(key)
                strict(child)
        elif kind is list:
            for child in item:
                strict(child)
        elif kind is str:
            assert not any(0xD800 <= ord(char) <= 0xDFFF for char in item)

    strict(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def h(raw):
    return hashlib.sha256(raw).hexdigest()


def f(raw):
    return len(raw).to_bytes(8, "big") + raw


def source(binding, native):
    return {
        "native": native,
        "binding": h(b"mesh-sync-source-binding\0" + f(c(binding))),
        "root": h(b"mesh-sync-source\0" + f(c(binding)) + bytes.fromhex(native[2])),
    }


def lease(values):
    amount, native, bridge, sent, received = values
    if not all(type(value) is int and value >= 0 for value in values):
        raise ValueError("integer")
    if bridge < native:
        raise ValueError("clock")
    if not sent <= received <= sent + 2000:
        raise ValueError("deadline")
    remainder = max(0, amount - (bridge - native))
    return {"remaining": remainder, "remoteExpiry": received + max(0, remainder - (received - sent) - 100)}


def verify(path):
    raw = path.read_bytes()
    assert h(raw) == "968ea89860e86fc8493681f6a8edc472c99794fbf580275d9bde5a2efa29c39d"
    fixture = json.loads(raw)
    rows = fixture["vectors"]
    by_name = {row["name"]: row for row in rows}
    assert len(rows) == len(by_name) == 12
    checked = []
    for name in ("encoding-binding", "request-role-relay", "request-role-material", "request-other-encoding"):
        row = by_name[name]
        assert h(c(row["input"])) == row["sha256"]
        checked.append(name)
    encoding = by_name["encoding-binding"]["input"]
    request = by_name["request-role-relay"]["input"]
    assert request["encodingDigest"] == h(c(encoding))
    changed_encoding = {**encoding, "schema": "d" * 64}
    assert by_name["request-other-encoding"]["input"] == {**request, "encodingDigest": h(c(changed_encoding))}
    assert by_name["request-role-material"]["input"] == {**request, "role": "material-publisher"}
    assert len(c(request)) <= 4096
    assert len({by_name[name]["sha256"] for name in
                ("request-role-relay", "request-role-material", "request-other-encoding")}) == 3
    for name in ("source-full", "source-second-alias"):
        row = by_name[name]
        assert source(row["binding"], row["tag"]["native"]) == row["tag"]
        checked.append(name)
    full, alias = by_name["source-full"], by_name["source-second-alias"]
    assert full["tag"]["native"] == alias["tag"]["native"]
    assert full["tag"]["binding"] != alias["tag"]["binding"]
    assert full["tag"]["root"] != alias["tag"]["root"]
    row = by_name["nonce-challenge"]
    challenge = {"nonce": "05" * 32, "target": h(c(full["tag"])), "request": h(c(request))}
    assert row["value"] == challenge
    assert row["canonical"].encode() == c(challenge) and row["sha256"] == h(c(challenge))
    checked.append(row["name"])
    row = by_name["proof-exact-native-splice"]
    head_raw, delivery_raw = row["nativeHead"].encode(), row["delivery"].encode()
    head, delivery = json.loads(head_raw), json.loads(delivery_raw)
    assert h(head_raw) == row["nativeHeadSha256"] and h(delivery_raw) == row["deliverySha256"]
    assert delivery_raw.count(head_raw) == 1 and head_raw != c(head)
    assert delivery["payload"]["head"] == head
    assert delivery["requestBinding"] == delivery["payload"]["requestBinding"] == request
    assert delivery["payload"]["sourceTag"] == full["tag"]
    assert delivery["payload"]["challenge"] == head["challenge"] == challenge
    assert delivery["sequence"] == row["sequence"] == 1
    # Independent reconstruction replaces one canonical marker in the complete
    # outer value, rather than invoking the producer's nested splice helper.
    marker = "observer-independent-native-fragment"
    skeleton = copy.deepcopy(delivery)
    skeleton["payload"]["head"] = marker
    encoded = c(skeleton)
    assert encoded.count(c(marker)) == 1
    assert encoded.replace(c(marker), head_raw) == delivery_raw
    assert [len(head_raw), len(delivery_raw) - len(head_raw), len(delivery_raw)] == [
        row["nativeBytes"], row["allEnvelopeBytes"], row["totalBytes"],
    ]
    assert len(head_raw) <= 49152 and len(delivery_raw) - len(head_raw) <= 16384
    assert len(delivery_raw) <= 65536
    assert h(c(head["descriptor"])) == encoding["nativeDescriptor"]
    owner = head["ownerClock"]
    native_binding = {"protocol": "fixture.native/1", "hostScope": "fixture", "uid": 1000,
                      "ownerEpoch": "04" * 16, "bootId": "owner-boot", "clockDomain": "time:[123]",
                      "view": "full", "sourceContexts": [], "scopeContinuity": []}
    assert h(b"mesh-sync-native-binding\0" + f(c(native_binding))) == full["tag"]["native"][0]
    assert delivery["payload"]["bridgeClock"] == {
        "bootId": owner["bootId"], "timeNamespace": owner["clockDomain"].replace(
            "time:[", "time:").removesuffix("]"), "boottimeMs": 10015,
    }
    checked.append(row["name"])
    row = by_name["within-binding-moved-head"]
    assert row["requested"] == full["tag"] and row["unchangedChallenge"] == challenge
    assert source(full["binding"], row["actual"]["native"]) == row["actual"]
    assert row["actual"]["native"][0] == row["requested"]["native"][0]
    assert h(c(row["actual"])) != challenge["target"]
    checked.append(row["name"])
    for name in ("attenuate-15ms", "zero-native-remaining", "elapsed-remaining"):
        row = by_name[name]
        assert lease(row["input"]) == row["output"]
        checked.append(name)
    rejected = []
    for row in fixture["rejections"]:
        try:
            lease(row["input"])
        except ValueError as error:
            assert str(error) == row["reject"]
            rejected.append(row["name"])
        else:
            raise AssertionError(row["name"])
    assert len(rejected) == 4
    return {
        "result": "PASS", "fixtureSha256": h(raw), "positiveCases": checked, "rejections": rejected,
        "nativeRootValidityEstablished": False, "nativeOrRelayRuntimeExecuted": False,
        "nativeHeadBytes": len(head_raw), "envelopeBytes": len(delivery_raw) - len(head_raw),
        "totalBytes": len(delivery_raw),
        "framingCoverage": "JSON-fragment byte preservation only; fixture uses structural LF and no terminal transport LF.",
        "fixtureHeadStructuralLf": head_raw.count(b"\n"),
        "fixtureDeliveryStructuralLf": delivery_raw.count(b"\n"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    print(json.dumps(verify(parser.parse_args().fixtures), indent=2, sort_keys=True))
