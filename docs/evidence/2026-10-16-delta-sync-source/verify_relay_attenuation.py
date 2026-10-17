"""Independent arithmetic replay of the original A1 packet; no producer imports."""

import json


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError("integer")
    return value


def attenuate(native, bridge, pairs, expected):
    native, bridge = integer(native), integer(bridge)
    if bridge < native:
        raise ValueError("clock")
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = max(0, integer(value) - (bridge - native))
    if set(result) != set(expected):
        raise ValueError("coverage")
    return result


def expiry(sent, received, remaining, margin):
    sent, received = integer(sent), integer(received)
    remaining, margin = integer(remaining), integer(margin)
    if not 100 <= margin <= 2000 or not sent <= received <= sent + 2000:
        raise ValueError("deadline")
    return received + max(0, remaining - (received - sent) - margin)


def main():
    positive = []
    for native, bridge, value, expected in (
        (10000, 10015, 500, 485),
        (10000, 10015, 0, 0),
        (10000, 10015, 15, 0),
        (10000, 10015, 10, 0),
        (10000, 10000, 500, 500),
    ):
        actual = attenuate(native, bridge, [("receipt", value)], ["receipt"])
        assert actual == {"receipt": expected}
        positive.append([native, bridge, value, expected])
    bridge = attenuate(10000, 10015, [("receipt", 500)], ["receipt"])
    assert expiry(20000, 20060, bridge["receipt"], 100) == 20385
    assert expiry(20000, 20060, 0, 100) == 20060
    rejected = []
    cases = (
        ("bridge-before-native", lambda: attenuate(10, 9, [("r", 5)], ["r"])),
        ("negative-native", lambda: attenuate(-1, 10, [("r", 5)], ["r"])),
        ("boolean-native", lambda: attenuate(True, 10, [("r", 5)], ["r"])),
        ("boolean-bridge", lambda: attenuate(0, True, [("r", 5)], ["r"])),
        ("negative-attenuation", lambda: attenuate(0, 0, [("r", -1)], ["r"])),
        ("boolean-attenuation", lambda: attenuate(0, 0, [("r", True)], ["r"])),
        ("duplicate-key", lambda: attenuate(0, 0, [("r", 1), ("r", 1)], ["r"])),
        ("missing-key", lambda: attenuate(0, 0, [], ["r"])),
        ("extra-key", lambda: attenuate(0, 0, [("r", 1), ("s", 1)], ["r"])),
        ("reader-clock-reversed", lambda: expiry(20, 19, 500, 100)),
        ("reader-proof-late", lambda: expiry(0, 2001, 500, 100)),
        ("reader-margin-short", lambda: expiry(0, 1, 500, 99)),
        ("reader-margin-long", lambda: expiry(0, 1, 500, 2001)),
        ("reader-boolean", lambda: expiry(0, 1, True, 100)),
    )
    for name, operation in cases:
        try:
            operation()
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    print(json.dumps({
        "status": "PASS",
        "attenuationCases": positive,
        "remoteExpiry": 20385,
        "zeroRemainingExpiry": 20060,
        "rejected": rejected,
        "scope": "Independent arithmetic only; no schema/native/relay admission.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
