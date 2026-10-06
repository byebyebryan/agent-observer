"""Design exercises, not a service implementation or provider proof.

Run with the accepted a2 candidate's Python using -I -B. Only fixture metadata
and disposable local Unix sockets are used; no provider is contacted.
"""

from __future__ import annotations

import copy
import itertools
import json
import os
from pathlib import Path
import socket
import stat
import struct
import tempfile

from agent_observer import public
from agent_observer.contract import MAX_BYTES
from agent_observer.watch import SampledWatch


def main():
    checks = []

    def check(name, predicate):
        if not predicate:
            raise AssertionError(name)
        checks.append(name)

    fixtures = Path(__file__).resolve().parents[3] / "tests/fixtures/contract-v3"
    before = json.loads((fixtures / "snapshot.json").read_text())
    public.validate_snapshot(before)
    extended = copy.deepcopy(before)
    extended["serviceInstance"] = "fixture"
    try:
        public.validate_snapshot(extended)
    except public.ContractError:
        check("API1 rejects service fields inside snapshot3", True)
    else:
        raise AssertionError("service field was accepted")

    # Wire validation has no elapsed-time policy. An old valid document still
    # has current facts until the service explicitly projects expiry.
    check("old cached document still structurally current", before["sourceHealth"] == "current")
    watch = SampledWatch()
    first = watch.sample(before)[0]
    heartbeat = watch.sample(before)[0]
    check("same cached snapshot emits heartbeat", heartbeat["kind"] == "heartbeat")
    check("heartbeat contains no renewed snapshot", heartbeat["snapshot"] is None)
    check("cached collection clock remains original", watch.previous["collectedAt"] == before["collectedAt"])
    check("cached evidence clock remains original", watch.previous["sessions"][0]["phase"] == before["sessions"][0]["phase"])
    newer = copy.deepcopy(before)
    newer["collectionId"] = "00000000-0000-0000-0000-000000000099"
    newer["collectedAt"] += 1000
    for row in newer["sessions"]:
        for dimension in ("phase", "runtime", "worker"):
            if row[dimension]["clock"] == "sample":
                row[dimension]["observedAt"] += 1000
    check("unchanged new poll also emits heartbeat", watch.sample(newer)[0]["kind"] == "heartbeat")
    check("native phase time is not poll confirmation", watch.previous["sessions"][-2]["phase"]["observedAt"] == before["sessions"][-2]["phase"]["observedAt"])

    before["sessions"][0]["activity"] = {
        "at": 1700000010000, "source": "codex_turn_metadata",
        "health": "current", "reason": "native_conversation_event",
    }
    partial = copy.deepcopy(before)
    partial["sourceHealth"] = "partial"
    partial["sessions"] = partial["sessions"][3:]
    partial["sources"][0]["sourceHealth"] = "unavailable"
    for coverage in partial["sources"][0]["coverage"].values():
        coverage.update(status="unavailable", reason="source_failed")
    watch = SampledWatch()
    watch.sample(before)
    frames = watch.sample(partial)
    retained = public.select(frames[-1]["snapshot"], before["sessions"][0]["identity"])
    check("partial source produces gap and resync", [f["kind"] for f in frames] == ["gap", "resync"])
    check("missing blocked row becomes unknown", retained["phase"]["value"] == "unknown" and retained["blockedReason"] == "unknown")
    check("retention preserves original phase time", retained["phase"]["observedAt"] == before["sessions"][0]["phase"]["observedAt"])
    check("retention preserves stale activity separately", retained["activity"]["at"] is None and retained["activity"]["lastKnownAt"] == 1700000010000)
    watch.gap("collection_failed")
    check("post-gap view is resync", watch.sample(before)[0]["kind"] == "resync")
    check("watch restart changes epoch", SampledWatch().stream_id != first["streamId"])

    # Exhaustive tiny interleavings expose the subscribe race. A single
    # capture-and-register publisher transaction has only two update orders.
    lost = []
    for order in itertools.permutations("CRU"):
        if order.index("C") > order.index("R"):
            continue
        current, registered, delivered = 0, False, []
        for step in order:
            if step == "C":
                delivered.append(current)
            elif step == "R":
                registered = True
            else:
                current = 1
                if registered:
                    delivered.append(current)
        if delivered[-1] != current:
            lost.append("".join(order))
    check("naive subscribe has a concrete lost-update order", lost == ["CUR"])
    for order in ("SU", "US"):
        current, registered, delivered = 0, False, []
        for step in order:
            if step == "S":
                registered = True
                delivered.append(current)
            else:
                current = 1
                if registered:
                    delivered.append(current)
        check(f"atomic subscribe covers {order}", delivered[-1] == current)

    inflight = b'{"view":1}\n'
    pending, skipped = None, False
    sent_prefix = inflight[:4]
    for revision in (2, 3, 4):
        skipped |= pending is not None
        pending = revision
    check("pending coalesces while partial frame stays immutable", sent_prefix + inflight[4:] == inflight and pending == 4)
    check("skipped pending revisions require explicit recovery", skipped)

    # One worker per source; new hints during a read request one later read.
    dirty = {"codex": 1, "claude": 1}
    jobs = {provider: (generation, 1) for provider, generation in dirty.items()}
    for _ in range(1000):
        dirty["codex"] += 1
    check("hint storm does not create more running jobs", len(jobs) == 2)
    completed = {}
    completed["claude"] = jobs.pop("claude")
    check("healthy source can finish while other source is pending", "claude" in completed and "codex" in jobs)
    launched_generation, context_generation = jobs.pop("codex")
    check("hints during read require one follow-up", dirty["codex"] > launched_generation)
    check("changed context rejects a late result", context_generation != 2)

    # Fake suspend: elapsed freshness must include sleep; no physical wake is
    # exercised here. BOOTTIME is available on this Linux execution host.
    check("host offers suspend-aware clock", hasattr(__import__("time"), "CLOCK_BOOTTIME"))
    last_sample, ttl = 100, 10
    check("active-only clock would miss long suspend", 101 - last_sample < ttl)
    check("suspend-aware clock expires the same source", 161 - last_sample > ttl)

    # This is a bounds calculation, not a maximum-size schema conformance test.
    check("service envelope needs a distinct transport bound", MAX_BYTES + 16 * 1024 > MAX_BYTES)

    with tempfile.TemporaryDirectory(prefix="observer-design-ipc-") as directory:
        os.chmod(directory, 0o700)
        endpoint = Path(directory) / "read.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(endpoint))
            os.chmod(endpoint, 0o600)
            listener.listen(1)
            listener.settimeout(1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(1)
                client.connect(str(endpoint))
                connection, _ = listener.accept()
                with connection:
                    _pid, uid, _gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                    check("kernel peer UID matches configured local user", uid == os.geteuid())
                check("pathname socket and parent are private", stat.S_IMODE(endpoint.stat().st_mode) == 0o600 and stat.S_IMODE(Path(directory).stat().st_mode) == 0o700)
        endpoint.unlink()
    check("disposable IPC directory is cleaned", not Path(directory).exists())

    sender, receiver = socket.socketpair()
    try:
        receiver.settimeout(1)
        buffered, decoded = bytearray(), []
        for fragment in (b'{"n":', b'1}\n{"', b'n":2}\n'):
            sender.sendall(fragment)
            buffered.extend(receiver.recv(128))
            while b"\n" in buffered:
                line, _, rest = buffered.partition(b"\n")
                decoded.append(json.loads(line))
                buffered = bytearray(rest)
        check("fragmented stream decodes two complete frames", decoded == [{"n": 1}, {"n": 2}] and not buffered)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        sender.setblocking(False)
        total, blocked = 0, False
        while total < 2 * 1024 * 1024:
            try:
                total += sender.send(b"x" * 16384)
            except BlockingIOError:
                blocked = True
                break
        check("unread peer reaches nonblocking backpressure", blocked)
        healthy_sender, healthy_receiver = socket.socketpair()
        try:
            healthy_receiver.settimeout(1)
            healthy_sender.sendall(b"heartbeat\n")
            check("independent healthy socket remains usable", healthy_receiver.recv(64) == b"heartbeat\n")
        finally:
            healthy_sender.close()
            healthy_receiver.close()
    finally:
        sender.close()
        receiver.close()

    print(json.dumps({
        "host": "snap", "apiVersion": public.API_VERSION,
        "result": "pass", "checkCount": len(checks), "checks": checks,
        "scope": ["existing API/watch fixtures", "deterministic design models", "disposable Unix IPC"],
        "excluded": ["service implementation", "native provider subscriptions", "physical suspend", "maximum-size schema acceptance", "multi-client service performance", "downstream integration"],
    }, indent=2))


if __name__ == "__main__":
    main()
