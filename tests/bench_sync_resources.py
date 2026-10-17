"""Diagnostic ownership inventory; never a CPU, native or transport acceptance run.

This process uses synthetic inputs, disposable socketpairs and the production
queue/preflight code without starting a service or provider. Hooks retain scalar
metadata only. Their fixed scratch is heap charged. Optional integer-only buffer
inventories are written at a named checkpoint, then analysed after owner cleanup.
"""

import argparse
import hashlib
import json
import selectors
import socket
import struct
import sys
import uuid
from pathlib import Path

from bench_sync_producer import native_shaped_snapshot, sources

from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import AllocationAccount, _Lease
from agent_observer.sync_encoded import EncodedMap
from agent_observer.sync_encoded_budget import EncodedOwnership
from agent_observer.sync_state import OwnerSyncCache, _Operations, _Stage

SCRATCH = 262144
CELL = struct.Struct("!QQB")


class Observer:
    def __init__(self, owner, runtime, inventory_key, inventory_path):
        self.owner, self.runtime = owner, runtime
        self.inventory_key, self.inventory_path = inventory_key, inventory_path
        self.scratch = owner.account.reserve(SCRATCH, kind="external")
        self.active = None
        self.operation = "cold"
        self.finished = []
        self.fragments = []
        self.serials = {}
        self.pending_pins = ()
        self.busy = False
        self.heap_peak = self.encoded_peak = None
        self.checkpoints = {}
        self.inventory = None
        self.declined = []
        self.originals = []

    def hook(self, cls, name, invoke):
        original = getattr(cls, name)
        self.originals.append((cls, name, original))

        def call(instance, *args, **kwargs):
            return invoke(original, instance, args, kwargs)

        setattr(cls, name, call)

    def install(self):
        def allocation(original, account, args, kwargs):
            result = original(account, *args, **kwargs)
            if account is self.owner.account:
                self.sample("allocation")
            return result

        def resize(original, lease, args, kwargs):
            result = original(lease, *args, **kwargs)
            if lease._account is self.owner.account:
                self.sample("reservation")
            return result

        def canonical(original, ledger, args, kwargs):
            result = original(ledger, *args, **kwargs)
            if ledger is self.owner.encoded_ownership:
                self.sample("canonical")
            return result

        def publish(original, owner, args, kwargs):
            if owner is not self.owner:
                return original(owner, *args, **kwargs)
            slot, stage, generation = args
            self.active = slot.name, generation, stage
            self.finished, self.fragments = [], []
            self.serials = {}
            try:
                result = original(owner, *args, **kwargs)
                self.sample("committed-before-stage-close", checkpoint=True)
                return result
            finally:
                self.active = None
                self.finished.clear()
                self.fragments.clear()

        def mint(original, table, args, kwargs):
            result = original(table, *args, **kwargs)
            if table.account is self.owner.account:
                self.finished.append(result)
                count = self.serials.get(table.space, 0) + 1
                self.serials[table.space] = count
                self.sample(f"map:{table.space}:{count}", checkpoint=True)
            return result

        def fragments(original, operations, args, kwargs):
            result = original(operations, *args, **kwargs)
            if operations.stage.cache is self.owner:
                self.fragments.append(result)
                self.sample("operation-fragments", checkpoint=True)
            return result

        def credit(original, stage, args, kwargs):
            result = original(stage, *args, **kwargs)
            if stage.cache is self.owner:
                count = self.serials.get("credit", 0) + 1
                self.serials["credit"] = count
                self.sample(f"stage-credit:{count}", checkpoint=True)
            return result

        def reserve(original, owner, args, kwargs):
            try:
                return original(owner, *args, **kwargs)
            except ValueError as error:
                if owner is self.owner:
                    self.declined.append({"stage": None if self.active is None else self.active[:2],
                                          "operation": self.operation, "additionalBytes": args[0],
                                          "priorEncodedCounterBytes": self.runtime.sync_encoded_bytes(),
                                          "projectedEncodedCounterBytes": self.runtime.sync_encoded_bytes() + args[0],
                                          "reason": str(error)})
                    assert len(self.declined) <= 64
                    self.sample("encoded-request-declined", checkpoint=True)
                raise

        def pins(original, owner, args, kwargs):
            if owner is not self.owner:
                return original(owner, *args, **kwargs)
            self.pending_pins = args[0]
            return original(owner, *args, **kwargs)

        def queue(original, runtime, args, kwargs):
            try:
                return original(runtime, *args, **kwargs)
            finally:
                if runtime is self.runtime:
                    self.pending_pins = ()
                    self.sample("queued", checkpoint=True)

        self.hook(AllocationAccount, "_acquire", allocation)
        self.hook(_Lease, "resize", resize)
        self.hook(EncodedOwnership, "retain", canonical)
        self.hook(OwnerSyncCache, "_publish_staged", publish)
        self.hook(EncodedMap, "_mint_map", mint)
        self.hook(_Operations, "encoded_parts", fragments)
        self.hook(_Stage, "charge_encoded", credit)
        self.hook(OwnerSyncCache, "_reserve_encoded", reserve)
        self.hook(OwnerSyncCache, "pin_buffers", pins)
        self.hook(Runtime, "_queue_sync", queue)

    def restore(self):
        for cls, name, original in reversed(self.originals):
            setattr(cls, name, original)
        self.originals.clear()

    def summary(self, event):
        owner, runtime = self.owner, self.runtime
        outputs = {id(b): b for b in owner.retained_buffers()}
        pins = {id(b): b for peer in runtime.peers if peer.sync_view for b in peer.parts}
        pins.update((id(b), b) for b in self.pending_pins)
        shared = sum(len(b) for key, b in pins.items() if key in outputs)
        union = dict(outputs)
        union.update(pins)
        ledger = owner.encoded_ownership
        canonical_overlap = sum(len(b) for key, b in union.items()
                                if getattr(owner.account._held.get(key), "encoded_owner", None) is ledger)
        tuples = sum(sys.getsizeof(p.parts) for p in runtime.peers if p.sync_view and p.parts)
        physical = ledger.used + sum(map(len, union.values())) - canonical_overlap
        budget = physical + owner.encoded_staged + tuples
        enforced = runtime.sync_encoded_bytes()
        # Current frames are separate LF-terminated buffers. This comparison
        # also detects any unaccounted pin/canonical sharing in the real path.
        if not self.pending_pins:
            assert budget == enforced, (budget, enforced)
        assert budget <= 32 * 1024 * 1024
        assert owner.account._used <= owner.account.limit
        active = None if self.active is None else self.active[:2]
        roots = [[name, role, commit.generation, commit.tables["records"].count]
                 for name, slot in owner.views.items()
                 for role, commit in (("current", slot.current), ("predecessor", slot.previous))
                 if commit is not None]
        return {"event": event, "operation": self.operation, "stage": active,
                "heapUsedIncludingProbe": owner.account._used,
                "heapHighWaterIncludingProbe": owner.account._peak,
                "probeHeapReservation": SCRATCH,
                "canonicalUniqueBytes": ledger.used, "canonicalBuffers": ledger.count,
                "cacheOutputUniqueBytes": sum(map(len, outputs.values())),
                "pinUniqueBytes": sum(map(len, pins.values())), "outputPinOverlapBytes": shared,
                "canonicalOutputOrPinOverlapBytes": canonical_overlap,
                "retainedPayloadUniqueBytes": physical,
                "workspaceAndUncommittedOutputReservationBytes": owner.encoded_staged,
                "peerTupleBudgetBytes": tuples, "encodedBudgetBytes": budget,
                "runtimeEncodedCounterBytes": enforced,
                "serviceEncodedCounterBytes": runtime.encoded_bytes(),
                "roots": roots, "peers": len(runtime.peers)}

    def sample(self, event, *, checkpoint=False):
        if self.busy:
            return
        self.busy = True
        try:
            used = self.owner.account._used
            # Allocation hooks only materialize a summary on a high-water
            # candidate; named map/queue checkpoints are bounded per generation.
            if not checkpoint and self.heap_peak is not None:
                encoded = self.runtime.sync_encoded_bytes()
                if (used < self.heap_peak["heapUsedIncludingProbe"]
                        and self.encoded_peak is not None
                        and encoded <= self.encoded_peak["encodedBudgetBytes"]):
                    return
            value = self.summary(event)
            if self.heap_peak is None or (used, value["encodedBudgetBytes"]) >= (
                    self.heap_peak["heapUsedIncludingProbe"], self.heap_peak["encodedBudgetBytes"]):
                self.heap_peak = value
            if (self.encoded_peak is None
                    or value["encodedBudgetBytes"] > self.encoded_peak["encodedBudgetBytes"]
                    or checkpoint and value["encodedBudgetBytes"] == self.encoded_peak["encodedBudgetBytes"]):
                self.encoded_peak = value
            if checkpoint:
                prefix = self.operation if self.active is None else f"{self.active[0]}:{self.active[1]}"
                key = prefix + ":" + event
                value["key"] = key
                category_event = "stage-credit" if event.startswith("stage-credit:") else event
                category = ("query" if self.active is None else self.active[0]) + ":" + category_event
                assert len(self.checkpoints) < 128 or category in self.checkpoints
                prior = self.checkpoints.get(category)
                if prior is None or used > prior["heapUsedIncludingProbe"]:
                    self.checkpoints[category] = value
                if key == self.inventory_key and self.inventory is None:
                    self.inventory = dict(value)
                    self.write_inventory()
        finally:
            self.busy = False

    def write_inventory(self):
        # Integer identities/lengths only; no prompts, rows or native payloads.
        # The reader runs after owner close, so its sets never pin producer data.
        with self.inventory_path.open("wb", buffering=8192) as stream:
            def emit(role, value):
                stream.write(CELL.pack(id(value), len(value), role))

            for key in self.owner.account._held:
                held = self.owner.account._held[key]
                if getattr(held, "encoded_owner", None) is self.owner.encoded_ownership:
                    emit(0, held.value)
            for value in self.owner.retained_buffers():
                emit(1, value)
            for peer in self.runtime.peers:
                if peer.sync_view:
                    for value in peer.parts:
                        emit(2, value)
            for value in self.pending_pins:
                emit(2, value)
            if self.active is not None:
                stage = self.active[2]
                for table in stage.tables:
                    if table.base is not None:
                        for key, value in table.base.encoded_items():
                            emit(3, key)
                            emit(3, value)
                    for key, value, _expected, removed in table.entries.values():
                        emit(3, key)
                        if not removed:
                            emit(3, value)
                for parts in stage.encoded_claims:
                    for value in parts:
                        emit(3, value)
            for table in self.finished:
                for key, value in table.encoded_items():
                    emit(3, key)
                    emit(3, value)
            for parts in self.fragments:
                for value in parts:
                    emit(3, value)
            frame = sys._getframe()
            try:
                while frame is not None:
                    if frame.f_code.co_name == "_publish_staged":
                        # Last-row and framing bytes can remain in ordinary
                        # publication locals after their earlier scratch use.
                        # Record bytes only; never traverse a native row DTO.
                        for name in ("content_bytes", "old_body", "token_prefix", "header_parts", "transaction"):
                            value = frame.f_locals.get(name)
                            if type(value) is bytes:
                                emit(3, value)
                            elif type(value) in (tuple, list):
                                for item in value:
                                    if type(item) is bytes:
                                        emit(3, item)
                            elif type(value) is dict:
                                for item in value.values():
                                    if type(item) is bytes:
                                        emit(3, item)
                        break
                    frame = frame.f_back
            finally:
                frame = None
            for name, slot in self.owner.views.items():
                for role, commit in (("current", slot.current), ("predecessor", slot.previous)):
                    if commit is None:
                        continue
                    code = 4 + (2 if name == "active" else 0) + (role == "predecessor")
                    for table in (*commit.tables.values(), *commit.groups.values()):
                        for key, value in table.encoded_items():
                            emit(code, key)
                            emit(code, value)


def analyse(path):
    buffers = {}
    with path.open("rb") as stream:
        while raw := stream.read(CELL.size):
            identity, size, role = CELL.unpack(raw)
            before = buffers.get(identity, (size, 0))
            assert before[0] == size
            buffers[identity] = size, before[1] | (1 << role)
    names = ("canonical", "cacheOutput", "pins", "stageReachable",
             "fullCurrent", "fullPredecessor", "activeCurrent", "activePredecessor")
    totals = {name: sum(size for size, mask in buffers.values() if mask & (1 << bit))
              for bit, name in enumerate(names)}
    overlap = {f"{a}&{b}": sum(size for size, mask in buffers.values()
                              if mask & (1 << i) and mask & (1 << j))
               for i, a in enumerate(names) for j, b in enumerate(names) if i < j}
    unowned = sum(size for size, mask in buffers.values() if mask & 1 and not mask & 0b11111000)
    assert unowned == 0, unowned
    stage_only = sum(size for size, mask in buffers.values() if mask & 8 and not mask & 7)
    return {"uniqueImmutableBytes": sum(size for size, _mask in buffers.values()),
            "canonicalBytesWithoutRootOrStageReachability": unowned,
            "stageOnlyImmutableBytes": stage_only,
            "roleBytes": totals, "pairwiseOverlapBytes": overlap,
            "note": "Stage reachability includes borrowed base/candidate/operation/fragment bytes; do not add it to canonical bytes."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--workload", choices=("timestamp", "all-bodies"), default="all-bodies")
    parser.add_argument("--inventory-key")
    parser.add_argument("--inventory-path", type=Path, default=Path(".cache/ownership-inventory.bin"))
    args = parser.parse_args()
    probe_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    boot, value, wall = native_shaped_snapshot(args.rows)
    now = [15000]
    uuid.uuid4 = lambda: uuid.UUID(int=0xF000 + now[0])
    state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                         uid=1000, clock=lambda: now[0], boot_id=boot, clock_domain="time:[123]")
    state.wall_clock = lambda: wall + now[0]
    state.attempt("codex", "history")
    state.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
    runtime = Runtime(state, "/unused/diagnostic.sock", collect=False)
    owner = state._sync_owner()
    state.sync_reserver = runtime._sync_reserver
    observer = Observer(owner, runtime, args.inventory_key, args.inventory_path)
    observer.install()
    receivers, limitations = [], []
    hashes = None
    try:
        for view in ("full", "active"):
            owner.ensure(view)
        for view in ("full", "active"):
            observer.operation = "baseline-" + view
            try:
                data = owner.baseline(view)
            except ValueError as error:
                assert view == "full" and args.rows == 2000 and error.args == ("sync_frame_limit",)
                limitations.append("Expanded 2000-row full baseline rejected; full pins use heads, not delivered material.")
                data = owner.head(view, {"nonce": "d" * 32})
            for _peer in range(8):
                sender, receiver = socket.socketpair()
                receivers.append(receiver)
                peer = Peer(sender, state.clock(), family="sync-" + view, operation="watch", sync_view=view)
                runtime.peers.add(peer)
                runtime.selector.register(sender, selectors.EVENT_READ, ("peer", peer))
                runtime._queue_sync(peer, data)
        data = None
        hashes = sources()
        for _generation in range(6):
            now[0] += 10
            for row in value["sessions"]:
                row["runtime"]["observedAt"] += 1000
                if row["phase"] is not None:
                    row["phase"]["observedAt"] += 1000
                row["lastUpdated"]["observedAt"] += 1000
                if args.workload == "all-bodies":
                    row["lastUpdated"]["at"] += 1000
                for name in ("lastUpdated", "latestTurn"):
                    row[name]["receipt"].update(sampledBoottimeMs=now[0], observedBoottimeMs=now[0])
            state.attempt("codex", "history")
            state.accept("codex", "history", value, sampled_ms=now[0], ttl_ms=60000, runtime_ttl_ms=60000)
        observer.operation = "retained"
        observer.sample("retained", checkpoint=True)
        result = {"rows": args.rows, "workload": args.workload, "generations": 6,
                  "scope": "Instrumented synthetic owner/queue ownership only; no CPU/RSS, delivered IPC, native or installed acceptance.",
                  "sourceHashesStart": hashes, "sourceHashes": sources(),
                  "heapPeak": observer.heap_peak, "encodedPeak": observer.encoded_peak,
                  "checkpoints": observer.checkpoints, "inventoryCheckpoint": observer.inventory,
                  "ownerCounts": dict(owner.counts), "runtimeCounts": dict(runtime.counts),
                  "declinedEncodedRequests": observer.declined,
                  "limitations": limitations, "heapAccountBeforeClose": owner.account.snapshot(),
                  "failures": {name: slot.failed for name, slot in owner.views.items()}}
        result["probeSha256"] = probe_hash
    finally:
        observer.restore()
        for peer in list(runtime.peers):
            runtime._drop(peer)
        for receiver in receivers:
            receiver.close()
        runtime.selector.close()
        for memo in runtime.image_memos.values():
            memo.close()
        owner.close()
        observer.scratch.release()
    result["closedAccount"] = owner.account.snapshot()
    assert result["closedAccount"]["allocations"] == result["closedAccount"]["objects"] == 0
    assert hashes == result["sourceHashes"]
    assert probe_hash == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if observer.inventory is not None:
        result["inventory"] = analyse(args.inventory_path)
        result["inventorySha256"] = hashlib.sha256(args.inventory_path.read_bytes()).hexdigest()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
