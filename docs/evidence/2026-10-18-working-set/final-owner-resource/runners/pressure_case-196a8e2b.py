"""One bounded slow-reader pressure case using the real Runtime budget."""

# Imports intentionally follow gc.disable() so the measured child starts with
# collection disabled before importing the Observer/test fixture.
# ruff: noqa: E402

from __future__ import annotations

import gc

gc.disable()

import argparse
import copy
import hashlib
import json
import resource
import selectors
import socket
import sys
import weakref
from pathlib import Path
from types import MethodType
from uuid import UUID

# E402 is intentional: this isolated child disables GC before source imports;
# the driver supplies only the pinned worktree and its tests directory.
from test_service_state import provider_snapshot  # noqa: E402

from agent_observer.active_contract import StreamGuard as ActiveStreamGuard  # noqa: E402
from agent_observer.active_contract import parse_frame as parse_active_frame  # noqa: E402
from agent_observer.active_contract import validate_frame as validate_active_frame  # noqa: E402
from agent_observer.contract import (  # noqa: E402
    MAX_SNAPSHOT_BYTES,
    canonical,
    identity_key,
    store_namespace,
    validate_snapshot,
)
from agent_observer.service_contract import (  # noqa: E402
    StreamGuard as ServiceStreamGuard,
)
from agent_observer.service_contract import (  # noqa: E402
    parse_frame as parse_service_frame,
)
from agent_observer.service_contract import (  # noqa: E402
    validate_frame as validate_service_frame,
)
from agent_observer.service_runtime import Peer, Runtime  # noqa: E402
from agent_observer.service_state import ServiceState  # noqa: E402
from agent_observer.working_set_contract import (  # noqa: E402
    DEFAULT_WINDOW_MS,
    MAX_LEDGER_BYTES,
)
from agent_observer.working_set_contract import (  # noqa: E402
    MAX_FRAME_BYTES as WORKING_SET_FRAME_BYTES,
)
from agent_observer.working_set_contract import (  # noqa: E402
    StreamGuard as WorkingSetStreamGuard,
)
from agent_observer.working_set_contract import (  # noqa: E402
    parse_frame as parse_working_set_frame,
)
from agent_observer.working_set_contract import (  # noqa: E402
    validate_frame as validate_working_set_frame,
)

SOURCE_REVISION = "explicit_current_source_required"
RUNTIME_SOURCE_REVISION = "explicit_current_source_required"
BOOT_ID = "00000000-0000-0000-0000-000000000001"
ROWS = 2000
GENERATIONS = 14
SLOW_FULL_PEERS = 13
WINDOW_MS = DEFAULT_WINDOW_MS
WALL_FIRST_MS = 1_700_000_020_000
BOOT_FIRST_MS = 10_000
GENERATION_STEP_MS = 10_000
RECENT_AGE_MS = 60 * 60 * 1000
OLD_AGE_MS = 10 * 24 * 60 * 60 * 1000
ENCODED_LIMIT_BYTES = 64 * 1024 * 1024
CLIENT_LIMIT = 16
ACTIVE_COUNT = 10
RECENT_COUNT = 10


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", default=SOURCE_REVISION)
    parser.add_argument("--runtime-source-revision", default=RUNTIME_SOURCE_REVISION)
    parser.add_argument("--python-entrypoint", required=True)
    parser.add_argument("--driver", type=Path, required=True)
    return parser.parse_args()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_ids(values) -> str:
    return sha256("\n".join(sorted(values)).encode())


def current_rss_kib():
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def rss_highwater_kib():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def make_seed():
    value = provider_snapshot("codex")
    value["host"]["uid"] = 1000
    namespace = store_namespace("codex", "/fixture/codex", "explicit", 1000)
    value["sources"][0]["namespace"] = namespace
    value["sources"][0]["configHome"] = "/fixture/codex"
    value["sources"][0]["configHomeKind"] = "explicit"
    value["sources"][0]["capabilities"]["runtime"] = ["running", "parked"]
    value["sources"][0]["capabilities"]["activity"] = True
    template = copy.deepcopy(value["sessions"][0])
    roles = ["old"] * ROWS
    order = sorted(range(ROWS), key=lambda index: ((index * 7919) % ROWS, index))
    active_ids = set()
    recent_ids = set()
    for index in order[:ACTIVE_COUNT]:
        roles[index] = "active_only"
        active_ids.add(str(UUID(int=1000 + index)))
    for index in order[ACTIVE_COUNT:ACTIVE_COUNT + RECENT_COUNT]:
        roles[index] = "recent_only"
        recent_ids.add(str(UUID(int=1000 + index)))

    value["sessions"] = []
    for index, role in enumerate(roles):
        row = copy.deepcopy(template)
        native_id = str(UUID(int=1000 + index))
        row["identity"]["namespace"] = namespace
        row["identity"]["nativeId"] = native_id
        row["nativeIds"].update(threadId=native_id, sessionTreeRootId=native_id)
        row["runtime"]["value"] = "running" if role == "active_only" else "parked"
        if role != "active_only":
            row["phase"], row["blockedReasons"] = None, []
        age = RECENT_AGE_MS if role == "recent_only" else OLD_AGE_MS
        row["activity"].update(
            at=WALL_FIRST_MS - age,
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        row["title"] = "t" * 256
        row["cwd"] = "/" + "c" * 1023
        value["sessions"].append(row)

    value["collectionId"] = str(UUID(int=200))
    value["collectedAt"] = WALL_FIRST_MS
    validate_snapshot(value)
    seed_bytes = canonical(value).encode()
    if len(seed_bytes) > MAX_SNAPSHOT_BYTES:
        raise RuntimeError("pressure_input_exceeds_snapshot_limit")
    return value, roles, active_ids, recent_ids, active_ids | recent_ids, len(seed_bytes), sha256(seed_bytes)


def generation_sample(seed, generation):
    sample = copy.deepcopy(seed)
    # Give each cached full DTO body distinct bytes while preserving the same
    # row membership, activity timestamps, validity and fixed encoded lengths.
    sample["sessions"][0]["title"] = f"{generation:02d}" + "t" * 254
    sampled = BOOT_FIRST_MS + GENERATION_STEP_MS * generation
    accepted = sampled + 1
    sample["collectionId"] = str(UUID(int=200 + generation))
    sample["collectedAt"] = WALL_FIRST_MS + GENERATION_STEP_MS * generation
    validate_snapshot(sample)
    encoded = canonical(sample).encode()
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise RuntimeError("pressure_generation_exceeds_snapshot_limit")
    metadata = {
        "generation": generation,
        "sampleId": sample["collectionId"],
        "wallMs": sample["collectedAt"],
        "sampledBoottimeMs": sampled,
        "acceptedBoottimeMs": accepted,
        "inputSnapshotBytes": len(encoded),
        "inputSnapshotSha256": sha256(encoded),
        "activityAtMs": WALL_FIRST_MS - RECENT_AGE_MS,
    }
    return sample, metadata


def revision_key(value):
    return str(value)


def cache_keys(runtime):
    return sorted(revision_key(key) for key in runtime.bodies)


def peer_label(peer, labels):
    return labels.get(id(peer), "unlabeled")


def peer_cursor(peer):
    if not peer.parts:
        return 0
    return sum(len(part) for part in peer.parts[:peer.part]) + peer.offset


def buffer_inventory(runtime, state, labels):
    entries = []
    for role, value in (
        ("owner.active", state.active_projector._encoded),
        ("owner.working_set", state.working_set_projector._encoded),
    ):
        if value is not None:
            entries.append((role, value))
    for key, body in runtime.bodies.items():
        family = key[0] if isinstance(key, tuple) else "full"
        entries.append((f"cache.{family}:{revision_key(key)}", body))

    aliases = []
    alias_valid = True
    peer_bytes = 0
    for peer in runtime.peers:
        label = peer_label(peer, labels)
        for index, value in enumerate(peer.parts):
            role = f"peer.{label}.part{index}"
            if peer.body_revision is not None and index == 1:
                cached = runtime.bodies.get(peer.body_revision)
                matches = cached is value
                alias_valid = alias_valid and matches
                aliases.append({
                    "peer": label,
                    "revision": revision_key(peer.body_revision),
                    "bytes": len(value),
                    "matchesCacheObject": matches,
                })
                role = f"peer.{label}.body_alias"
            else:
                peer_bytes += len(value)
            entries.append((role, value))

    unique = {}
    references = {}
    for role, value in entries:
        item = unique.setdefault(id(value), {"bytes": len(value), "roles": []})
        item["roles"].append(role)
        group = role.split(".", 1)[0]
        aggregate = references.setdefault(group, {"references": 0, "referenceBytes": 0})
        aggregate["references"] += 1
        aggregate["referenceBytes"] += len(value)

    unique_role_bytes = {}
    unique_records = []
    for item in unique.values():
        roles_for_object = sorted(item["roles"])
        groups = sorted({role.split(".", 1)[0] for role in roles_for_object})
        for group in groups:
            unique_role_bytes[group] = unique_role_bytes.get(group, 0) + item["bytes"]
        unique_records.append({"bytes": item["bytes"], "roles": roles_for_object})
    unique_records.sort(key=lambda item: item["roles"])
    unique_bytes = sum(item["bytes"] for item in unique.values())
    owner_values = {id(value): value for value in state.working_set_retained_buffers()}
    manual_charge = (
        runtime.sync_encoded_bytes()
        + sum(map(len, owner_values.values()))
        + sum(map(len, runtime.bodies.values()))
        + peer_bytes
    )
    actual_charge = runtime.encoded_bytes()
    cache = [
        {"revision": revision_key(key), "bytes": len(value)}
        for key, value in sorted(runtime.bodies.items(), key=lambda pair: revision_key(pair[0]))
    ]
    latest = {
        family: revision_key(key)
        for family, key in sorted(runtime.latest.items())
    }
    pins = [
        {
            "peer": peer_label(peer, labels),
            "family": peer.family,
            "revision": revision_key(peer.body_revision),
            "writeStartedMs": peer.write_started,
            "bodyBytes": len(runtime.bodies[peer.body_revision]),
            "bodyAliasMatchesCache": (
                len(peer.parts) > 1
                and peer.parts[1] is runtime.bodies.get(peer.body_revision)
            ),
            "pendingBytes": sum(len(part) for part in peer.parts) - peer_cursor(peer),
        }
        for peer in runtime.peers
        if peer.body_revision is not None
    ]
    pins.sort(key=lambda item: item["peer"])
    aliases.sort(key=lambda item: (item["peer"], item["revision"]))
    return {
        "runtimeEncodedBytes": actual_charge,
        "manualChargeBytes": manual_charge,
        "counterMatchesManualCharge": actual_charge == manual_charge,
        "encodedLimitBytes": runtime.encoded_limit,
        "withinEncodedLimit": actual_charge <= runtime.encoded_limit,
        "peerCount": len(runtime.peers),
        "uniqueBufferObjectCount": len(unique_records),
        "uniqueBufferBytes": unique_bytes,
        "uniqueBufferBytesByRole": dict(sorted(unique_role_bytes.items())),
        "roleOverlapBytes": sum(unique_role_bytes.values()) - unique_bytes,
        "uniqueBytesWithinRuntimeCharge": unique_bytes <= actual_charge,
        "roleReferences": {key: value for key, value in sorted(references.items())},
        "uniqueBuffers": unique_records,
        "bodyCache": cache,
        "latestCacheKeys": latest,
        "peerBodyAliases": aliases,
        "peerPins": pins,
        "allPeerAliasesMatchCache": alias_valid,
        "syncEncodedBytes": runtime.sync_encoded_bytes(),
    }


def source_hashes(root, driver_path):
    files = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if relative.parts[0] not in {"agent_observer", "tests"} or path.suffix != ".py":
            continue
        files[str(relative)] = sha256(path.read_bytes())
    for label, path in (
        ("resource-pressure/pressure_case.py", Path(__file__).resolve()),
        ("resource-pressure/run_pressure.py", driver_path.resolve()),
        ("tests/fixtures/service-v4/view.json", root / "tests/fixtures/service-v4/view.json"),
        ("agent_observer/contracts/snapshot.schema.json", root / "agent_observer/contracts/snapshot.schema.json"),
    ):
        files[label] = sha256(path.read_bytes())
    return dict(sorted(files.items()))


def route_summary(frame, family, expected_ids, active_ids, full_rows):
    if family == "full":
        rows = frame["snapshot"]["sessions"]
        selected_ids = {row["identity"]["nativeId"] for row in rows}
        expected = {row["identity"]["nativeId"] for row in full_rows}
        if selected_ids != expected or len(rows) != ROWS:
            raise RuntimeError("full_route_membership")
        return {
            "rowCount": len(rows),
            "identitySha256": digest_ids(selected_ids),
            "dtoSha256": sha256(canonical(rows).encode()),
            "bodySha256": sha256(canonical(frame["snapshot"]).encode()),
        }
    if family == "active":
        rows = frame["projection"]["sessions"]
        selected_ids = {row["identity"]["nativeId"] for row in rows}
        expected = sorted(
            (row for row in full_rows if row["identity"]["nativeId"] in active_ids),
            key=lambda row: identity_key(row["identity"]),
        )
        if rows != expected:
            raise RuntimeError("active_route_dto_mismatch")
        return {
            "rowCount": len(rows),
            "identitySha256": digest_ids(selected_ids),
            "dtoSha256": sha256(canonical(rows).encode()),
            "bodySha256": sha256(canonical(frame["projection"]).encode()),
        }
    projection = frame["projection"]
    if projection is None or len(projection["scopes"]) != 1:
        raise RuntimeError("working_set_projection_missing")
    scope = projection["scopes"][0]
    if scope["coverage"]["status"] != "complete":
        raise RuntimeError("working_set_scope_not_complete")
    rows = projection["sessions"]
    selected_ids = {row["identity"]["nativeId"] for row in rows}
    expected = sorted(
        (row for row in full_rows if row["identity"]["nativeId"] in expected_ids),
        key=lambda row: identity_key(row["identity"]),
    )
    if selected_ids != expected_ids or rows != expected:
        raise RuntimeError("working_set_route_dto_mismatch")
    return {
        "rowCount": len(rows),
        "identitySha256": digest_ids(selected_ids),
        "dtoSha256": sha256(canonical(rows).encode()),
        "bodySha256": sha256(canonical(projection).encode()),
        "coverageStatus": scope["coverage"]["status"],
        "coverageReason": scope["coverage"]["reason"],
    }


def socket_pair(runtime, now_ms, label, family, *, slow):
    sender, receiver = socket.socketpair()
    sender.setblocking(False)
    receiver.setblocking(False)
    requested = 4096 if slow else 1024 * 1024
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, requested)
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, requested)
    peer = Peer(sender, now_ms, operation="watch", family=family)
    runtime.peers.add(peer)
    runtime.selector.register(sender, selectors.EVENT_READ, ("pressure_peer", peer))
    return peer, receiver, {
        "label": label,
        "family": family,
        "slow": slow,
        "requestedSocketBufferBytes": requested,
        "actualSendBufferBytes": sender.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
        "actualReceiveBufferBytes": receiver.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
    }


def drain_healthy_peer(runtime, peer, receiver, *, capture_frame):
    expected_wire = hashlib.sha256()
    for part in peer.parts:
        expected_wire.update(part)
    received_wire = hashlib.sha256()
    raw = bytearray() if capture_frame else None
    total = 0
    calls = 0
    for _ in range(4096):
        if not peer.parts:
            break
        runtime._write(peer)
        calls += 1
        progress = False
        while True:
            try:
                data = receiver.recv(65536)
            except BlockingIOError:
                break
            if not data:
                raise RuntimeError("healthy_reader_closed")
            progress = True
            total += len(data)
            received_wire.update(data)
            if raw is not None:
                raw.extend(data)
        if not progress and peer.parts:
            raise RuntimeError("healthy_reader_stalled")
    if peer.parts:
        raise RuntimeError("healthy_frame_write_incomplete")
    return {
        "wireBytes": total,
        "writeCalls": calls,
        "wireDigestMatchesQueuedParts": received_wire.digest() == expected_wire.digest(),
        "frameBytes": bytes(raw) if raw is not None else None,
    }


def main():
    args = parse_args()
    root = args.root.resolve()
    driver_path = args.driver.resolve()
    if (len(args.source_revision) != 40
            or any(c not in "0123456789abcdef" for c in args.source_revision)
            or args.runtime_source_revision != args.source_revision):
        raise RuntimeError("explicit_whole_commit_pin_required")

    seed, roles, active_ids, recent_ids, expected_ids, seed_bytes, seed_digest = make_seed()
    now = [BOOT_FIRST_MS + 1]
    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=1000,
        clock=lambda: now[0],
        boot_id=BOOT_ID,
        clock_domain="time:[123]",
        working_set_window_ms=WINDOW_MS,
    )
    runtime = Runtime(state, "/unused/resource-pressure.sock", collect=False)
    if runtime.encoded_limit != ENCODED_LIMIT_BYTES or runtime.max_clients != CLIENT_LIMIT:
        raise RuntimeError("runtime_default_budget_changed")

    labels = {}
    receivers = {}
    peer_records = {}
    sender_sockets = {}
    peer_settings = []
    for index in range(SLOW_FULL_PEERS):
        label = f"full_slow_{index:02d}"
        peer, receiver, settings = socket_pair(
            runtime, now[0], label, "service", slow=True
        )
        labels[id(peer)] = label
        peer_records[label] = weakref.ref(peer)
        sender_sockets[label] = peer.sock
        receivers[label] = receiver
        peer_settings.append(settings)
    for label, family in (
        ("full_reader", "service"),
        ("active_reader", "active"),
        ("working_set_reader", "working_set"),
    ):
        peer, receiver, settings = socket_pair(
            runtime, now[0], label, family, slow=False
        )
        labels[id(peer)] = label
        peer_records[label] = peer
        sender_sockets[label] = peer.sock
        receivers[label] = receiver
        peer_settings.append(settings)
    if len(runtime.peers) != CLIENT_LIMIT:
        raise RuntimeError("pressure_topology_not_at_default_client_cap")

    failures = []
    events = []
    room_events = []
    drop_events = []
    reservation_events = []
    generations = []
    all_inventories = []
    context = {"operation": "setup", "generation": None, "family": None, "peer": None}
    room_depth = [0]
    peer_count_highwater = len(runtime.peers)
    max_encoded_bytes = 0
    original_room = runtime._room
    original_drop = runtime._drop
    original_reserve = runtime._reserve_working_set

    def record_inventory(label):
        nonlocal max_encoded_bytes
        value = buffer_inventory(runtime, state, labels)
        max_encoded_bytes = max(max_encoded_bytes, value["runtimeEncodedBytes"])
        if not value["counterMatchesManualCharge"]:
            failures.append(f"{label}:runtime_counter_mismatch")
        if not value["withinEncodedLimit"]:
            failures.append(f"{label}:encoded_limit_exceeded")
        if not value["uniqueBytesWithinRuntimeCharge"]:
            failures.append(f"{label}:unique_buffers_exceed_runtime_charge")
        if not value["allPeerAliasesMatchCache"]:
            failures.append(f"{label}:peer_body_alias_mismatch")
        if value["peerCount"] > runtime.max_clients:
            failures.append(f"{label}:client_limit_exceeded")
        all_inventories.append({"label": label, **value})
        return value

    def get_peer(label):
        peer = peer_records[label]
        return peer() if isinstance(peer, weakref.ReferenceType) else peer

    def traced_drop(self, peer):
        if peer not in self.peers:
            return original_drop(peer)
        before = record_inventory(f"drop_before:{peer_label(peer, labels)}")
        candidates = [item for item in self.peers if item.parts]
        oldest = min(candidates, key=lambda item: item.write_started) if candidates else None
        label = peer_label(peer, labels)
        body_revision = peer.body_revision
        body = runtime.bodies.get(body_revision) if body_revision is not None else None
        body_bytes = len(body) if body is not None else 0
        body_digest = sha256(body) if body is not None else None
        peer_part_bytes = sum(len(part) for part in peer.parts)
        peer_body_alias_matches = (
            len(peer.parts) > 1
            and body is not None
            and peer.parts[1] is body
        )
        peer_write_started = peer.write_started
        candidate_count = len(candidates)
        victim_was_oldest = oldest is peer
        original_drop(peer)
        after_drop = record_inventory(f"drop_after_runtime:{label}")
        if peer.parts or peer.body_revision is not None:
            failures.append("dropped_peer_retains_encoded_body")
        drop_events.append({
            "peer": label,
            "family": peer.family,
            "causeOperation": dict(context),
            "insideRuntimeRoom": room_depth[0] > 0,
            "writeStartedMs": peer_write_started,
            "wasOldestWriteStartedCandidate": victim_was_oldest,
            "candidateCountBeforeDrop": candidate_count,
            "bodyRevision": revision_key(body_revision) if body_revision is not None else None,
            "bodyBytes": body_bytes,
            "bodySha256": body_digest,
            "peerBodyAliasMatchesCachedBody": peer_body_alias_matches,
            "peerPartBytesBeforeDrop": peer_part_bytes,
            "peerPartsRetainedBySourceDrop": bool(peer.parts),
            "peerBodyRevisionRetainedBySourceDrop": peer.body_revision is not None,
            "before": before,
            "afterRuntimeDropBeforeRoomPrune": after_drop,
        })

    def traced_room(self, reserve, *, protected=None):
        before = record_inventory(f"room_before:{context['operation']}:{context['generation']}")
        cache_before = set(cache_keys(self))
        peer_labels_before = {peer_label(peer, labels) for peer in self.peers}
        drops_before = len(drop_events)
        room_depth[0] += 1
        succeeded = False
        error_name = None
        try:
            result = original_room(reserve, protected=protected)
            succeeded = True
            return result
        except BaseException as error:
            error_name = type(error).__name__
            raise
        finally:
            room_depth[0] -= 1
            after = record_inventory(f"room_after:{context['operation']}:{context['generation']}")
            cache_after = set(cache_keys(self))
            peer_labels_after = {peer_label(peer, labels) for peer in self.peers}
            retired = sorted(cache_before - cache_after)
            dropped = sorted(peer_labels_before - peer_labels_after)
            room_drop_events = drop_events[drops_before:]
            for dropped_event in room_drop_events:
                dropped_peer = get_peer(dropped_event["peer"])
                dropped_event["peerObjectAliveAfterRoomReturn"] = dropped_peer is not None
                dropped_event["peerPartBytesAfterRoomReturn"] = (
                    sum(len(part) for part in dropped_peer.parts)
                    if dropped_peer is not None else 0
                )
                dropped_event["bodyRevisionAfterRoomReturn"] = (
                    revision_key(dropped_peer.body_revision)
                    if dropped_peer is not None and dropped_peer.body_revision is not None
                    else None
                )
                del dropped_peer
            event = {
                "operationContext": dict(context),
                "reserveBytes": reserve,
                "protectedRevision": revision_key(protected) if protected is not None else None,
                "encodedBeforeBytes": before["runtimeEncodedBytes"],
                "requestedCurrentPlusReserveBytes": before["runtimeEncodedBytes"] + reserve,
                "requestExceedsDefaultLimitBeforeRoom": before["runtimeEncodedBytes"] + reserve > self.encoded_limit,
                "limitBytes": self.encoded_limit,
                "succeeded": succeeded,
                "errorType": error_name,
                "encodedAfterBytes": after["runtimeEncodedBytes"],
                "requestFitsAfterRoom": succeeded and after["runtimeEncodedBytes"] + reserve <= self.encoded_limit,
                "droppedPeerLabels": dropped,
                "retiredCacheRevisions": retired,
                "dropEventCount": len(drop_events) - drops_before,
                "before": before,
                "after": after,
            }
            room_events.append(event)
            if succeeded and after["runtimeEncodedBytes"] + reserve > self.encoded_limit:
                failures.append("runtime_room_returned_without_reservation_space")

    def traced_reserve(additional_bytes):
        before = record_inventory(f"reservation_before:{context['generation']}")
        cache_before = set(cache_keys(runtime))
        peers_before = {peer_label(peer, labels) for peer in runtime.peers}
        result = original_reserve(additional_bytes)
        after = record_inventory(f"reservation_after:{context['generation']}")
        event = {
            "operationContext": dict(context),
            "additionalBytes": additional_bytes,
            "currentPlusAdditionalBeforeBytes": before["runtimeEncodedBytes"] + additional_bytes,
            "limitBytes": runtime.encoded_limit,
            "admitted": result,
            "currentAfterBytes": after["runtimeEncodedBytes"],
            "currentPlusAdditionalAfterBytes": after["runtimeEncodedBytes"] + additional_bytes,
            "fitsAfterRoom": bool(result and after["runtimeEncodedBytes"] + additional_bytes <= runtime.encoded_limit),
            "droppedPeerLabels": sorted(peers_before - {peer_label(peer, labels) for peer in runtime.peers}),
            "retiredCacheRevisions": sorted(set(cache_before) - set(cache_keys(runtime))),
            "before": before,
            "after": after,
        }
        reservation_events.append(event)
        if additional_bytes != WORKING_SET_FRAME_BYTES + 2 * MAX_LEDGER_BYTES:
            failures.append("working_set_reservation_size_changed")
        if not result or not event["fitsAfterRoom"]:
            failures.append(f"working_set_reservation_refused:{context['generation']}")
        return result

    runtime._drop = MethodType(traced_drop, runtime)
    runtime._room = MethodType(traced_room, runtime)
    state.working_set_reserver = traced_reserve
    record_inventory("startup")

    def set_context(operation, generation, family=None, peer=None):
        context.update({
            "operation": operation,
            "generation": generation,
            "family": family,
            "peer": peer,
        })

    def traced_operation(operation, generation, family, peer, callback):
        before = record_inventory(f"{operation}_before:{family}:{generation}")
        caches_before = set(cache_keys(runtime))
        peers_before = {peer_label(item, labels) for item in runtime.peers}
        drop_start = len(drop_events)
        previous = dict(context)
        set_context(operation, generation, family, peer)
        result = callback()
        after = record_inventory(f"{operation}_after:{family}:{generation}")
        event = {
            "operation": operation,
            "generation": generation,
            "family": family,
            "peer": peer,
            "droppedPeerLabels": sorted(peers_before - {peer_label(item, labels) for item in runtime.peers}),
            "retiredCacheRevisions": sorted(caches_before - set(cache_keys(runtime))),
            "dropEventCount": len(drop_events) - drop_start,
            "before": before,
            "after": after,
        }
        events.append(event)
        context.clear()
        context.update(previous)
        return result

    def queue(peer, generation, family, label):
        def run():
            runtime._queue(peer, "view")
            return peer in runtime.peers
        return traced_operation("queue", generation, family, label, run)

    def write_healthy(peer, receiver, generation, family, label, *, capture_frame):
        def run():
            output = drain_healthy_peer(
                runtime, peer, receiver, capture_frame=capture_frame
            )
            frame_data = output.pop("frameBytes")
            parsed = None
            if frame_data is not None:
                if family == "service":
                    parsed = parse_service_frame(
                        frame_data, expected_host="fixture", expected_uid=1000
                    )
                elif family == "active":
                    parsed = parse_active_frame(
                        frame_data, expected_host="fixture", expected_uid=1000
                    )
                elif family == "working_set":
                    parsed = parse_working_set_frame(
                        frame_data,
                        expected_host="fixture",
                        expected_uid=1000,
                        expected_window_ms=WINDOW_MS,
                    )
            output["frameBytes"] = frame_data
            output["parsedFrame"] = parsed
            return output

        output = traced_operation("write", generation, family, label, run)
        return output

    full_stream_guard = ServiceStreamGuard(expected_host="fixture", expected_uid=1000)
    active_stream_guard = ActiveStreamGuard(expected_host="fixture", expected_uid=1000)
    working_set_stream_guard = WorkingSetStreamGuard(
        expected_host="fixture", expected_uid=1000, expected_window_ms=WINDOW_MS
    )
    deliveries = []
    for generation in range(GENERATIONS):
        sample, sample_meta = generation_sample(seed, generation)
        now[0] = sample_meta["acceptedBoottimeMs"]
        set_context("accept", generation)
        state.attempt("codex", "runtime")
        accepted = state.accept(
            "codex",
            "runtime",
            sample,
            sampled_ms=sample_meta["sampledBoottimeMs"],
            ttl_ms=1_000_000,
            accepted_boottime_ms=sample_meta["acceptedBoottimeMs"],
        )
        if not accepted:
            failures.append(f"provider_sample_rejected:{generation}")
        del sample
        now[0] += 1000

        sequence = generation + 1
        full = validate_service_frame(state.frame("view", sequence))
        active = validate_active_frame(state.active_frame("view", sequence))
        working = validate_working_set_frame(state.working_set_frame("view", sequence))
        if full["state"] != "ready" or active["state"] != "ready" or working["state"] != "ready":
            failures.append(f"route_not_ready:{generation}")
        full_rows = full["snapshot"]["sessions"]
        if len(full_rows) != ROWS:
            failures.append(f"full_rows_mismatch:{generation}")
        full_semantics = route_summary(full, "full", expected_ids, active_ids, full_rows)
        active_semantics = route_summary(active, "active", expected_ids, active_ids, full_rows)
        working_semantics = route_summary(working, "working_set", expected_ids, active_ids, full_rows)
        if active_semantics["rowCount"] != ACTIVE_COUNT or working_semantics["rowCount"] != ACTIVE_COUNT + RECENT_COUNT:
            failures.append(f"small_union_count_mismatch:{generation}")

        full_reader = peer_records["full_reader"]
        if not queue(full_reader, generation, "service", "full_reader"):
            failures.append(f"healthy_full_peer_dropped_on_queue:{generation}")
        full_wire = write_healthy(
            full_reader,
            receivers["full_reader"],
            generation,
            "service",
            "full_reader",
            capture_frame=True,
        )
        delivered_full = full_wire["parsedFrame"]
        full_reader_dto_matches = (
            delivered_full is not None
            and delivered_full["snapshot"] == full["snapshot"]
            and delivered_full["viewRevision"] == full["viewRevision"]
            and delivered_full["sequence"] == sequence
        )
        if delivered_full is None:
            failures.append(f"healthy_full_frame_not_parsed:{generation}")
        else:
            full_stream_guard.accept(delivered_full)
        if not full_reader_dto_matches:
            failures.append(f"healthy_full_dto_mismatch:{generation}")
        full_body = runtime.bodies.get(full_reader.frame_revision)
        full_body_digest_matches = (
            full_body is not None and sha256(full_body) == full_semantics["bodySha256"]
        )
        if (
            not full_wire["wireDigestMatchesQueuedParts"]
            or not full_body_digest_matches
            or not full_reader_dto_matches
        ):
            failures.append(f"healthy_full_wire_mismatch:{generation}")
        if full_reader not in runtime.peers:
            failures.append(f"healthy_full_peer_unavailable:{generation}")
        full_wire.pop("frameBytes")
        full_wire.pop("parsedFrame")
        del delivered_full

        slow_label = f"full_slow_{generation:02d}" if generation < SLOW_FULL_PEERS else None
        slow_result = None
        if slow_label is not None:
            slow_peer = get_peer(slow_label)
            if slow_peer is None:
                failures.append(f"slow_full_peer_object_missing:{generation}")
                continue
            if not queue(slow_peer, generation, "service", slow_label):
                failures.append(f"slow_full_peer_dropped_during_queue:{generation}")
            body_revision = slow_peer.body_revision
            body = runtime.bodies.get(body_revision) if body_revision is not None else None
            expected_shared = (
                body is not None
                and slow_peer.parts[1] is body
                and sha256(body) == full_semantics["bodySha256"]
                and slow_peer.frame_revision == full["viewRevision"]
            )
            if not expected_shared:
                failures.append(f"slow_full_body_not_current_shared_dto:{generation}")
            before_cursor = peer_cursor(slow_peer)
            before_inventory = record_inventory(f"slow_write_before:{generation}")
            runtime._write(slow_peer)
            after_cursor = peer_cursor(slow_peer)
            after_inventory = record_inventory(f"slow_write_after:{generation}")
            receiver = receivers[slow_label]
            try:
                unread = receiver.recv(1, socket.MSG_PEEK)
            except BlockingIOError:
                unread = b""
            sent = after_cursor - before_cursor
            total_frame_bytes = sum(len(part) for part in slow_peer.parts)
            slow_result = {
                "peer": slow_label,
                "bodyRevision": revision_key(body_revision),
                "bodyBytes": len(body) if body is not None else 0,
                "bodySha256": sha256(body) if body is not None else None,
                "bodyMatchesFullDtoDigest": expected_shared,
                "firstWriteBytes": sent,
                "queuedFrameBytes": total_frame_bytes,
                "writeRemainsPartial": bool(slow_peer.parts and after_cursor < total_frame_bytes),
                "receiverHasUnreadBytes": bool(unread),
                "bodyStillPinned": slow_peer in runtime.peers and slow_peer.body_revision is not None,
                "before": before_inventory,
                "after": after_inventory,
            }
            if (
                sent <= 0
                or not slow_result["writeRemainsPartial"]
                or not slow_result["receiverHasUnreadBytes"]
                or not slow_result["bodyStillPinned"]
            ):
                failures.append(f"slow_reader_not_partially_pinned:{generation}")

        sibling_results = {}
        for label, family, direct in (
            ("active_reader", "active", active),
            ("working_set_reader", "working_set", working),
        ):
            peer = peer_records[label]
            if not queue(peer, generation, family, label):
                failures.append(f"healthy_sibling_dropped_on_queue:{label}:{generation}")
            delivery = write_healthy(
                peer,
                receivers[label],
                generation,
                family,
                label,
                capture_frame=True,
            )
            delivered = delivery["parsedFrame"]
            if delivered is None:
                failures.append(f"healthy_sibling_frame_not_parsed:{label}:{generation}")
                delivered_semantics = None
            else:
                delivered_semantics = route_summary(
                    delivered, family, expected_ids, active_ids, full_rows
                )
                if delivered["projection"] != direct["projection"]:
                    failures.append(f"healthy_sibling_dto_mismatch:{label}:{generation}")
                if family == "active":
                    active_stream_guard.accept(delivered)
                else:
                    working_set_stream_guard.accept(delivered)
            if peer not in runtime.peers or peer.parts:
                failures.append(f"healthy_sibling_not_current:{label}:{generation}")
            sibling_results[label] = {
                "wireBytes": delivery["wireBytes"],
                "writeCalls": delivery["writeCalls"],
                "wireDigestMatchesQueuedParts": delivery["wireDigestMatchesQueuedParts"],
                "dtoSha256": delivered_semantics["dtoSha256"] if delivered_semantics else None,
                "rowCount": delivered_semantics["rowCount"] if delivered_semantics else None,
                "streamGuardAccepted": delivered is not None,
                "peerRemainedLive": peer in runtime.peers,
            }
            if not delivery["wireDigestMatchesQueuedParts"]:
                failures.append(f"healthy_sibling_wire_mismatch:{label}:{generation}")
            del delivery, delivered, delivered_semantics

        if state.receipts["codex"]["runtime"].health != "current":
            failures.append(f"provider_health_not_current:{generation}")
        if state.receipts["codex"]["runtime"].accepted != generation + 1:
            failures.append(f"provider_accept_counter_mismatch:{generation}")
        if state.working_set_projector._capacity_blocked:
            failures.append(f"working_set_capacity_blocked:{generation}")
        generation_result = {
            **sample_meta,
            "providerRuntimeHealth": state.receipts["codex"]["runtime"].health,
            "providerRuntimeAccepted": state.receipts["codex"]["runtime"].accepted,
            "serviceObservationRevision": state.revision,
            "workingSetViewRevision": state.working_set_revision,
            "full": full_semantics,
            "active": active_semantics,
            "workingSet": working_semantics,
            "fullHealthyReader": {
                "wireBytes": full_wire["wireBytes"],
                "writeCalls": full_wire["writeCalls"],
                "wireDigestMatchesQueuedParts": full_wire["wireDigestMatchesQueuedParts"],
                "bodySha256": sha256(full_body) if full_body is not None else None,
                "bodyMatchesFullDtoDigest": full_body_digest_matches,
                "dtoMatchesDirectFrame": full_reader_dto_matches,
                "streamGuardAccepted": True,
                "peerRemainedLive": full_reader in runtime.peers,
            },
            "slowReader": slow_result,
            "healthySiblingReaders": sibling_results,
            "runtimePeerCount": len(runtime.peers),
            "runtimeDroppedConnectionCount": runtime.counts["droppedConnections"],
            "inventory": record_inventory(f"generation_end:{generation}"),
            "instrumentedProcessRssKiB": current_rss_kib(),
        }
        generations.append(generation_result)
        deliveries.append({
            "generation": generation,
            "slowPeerLabel": slow_label,
            "slowPeerQueuedAndPartiallyWritten": slow_result is not None and slow_result["bodyStillPinned"],
            "siblingPeersHealthy": all(row["peerRemainedLive"] for row in sibling_results.values()),
        })
        all_inventories.append({
            "label": f"generation_semantics:{generation}",
            **generation_result["inventory"],
        })
        if slow_result is not None:
            del slow_peer

    # Let time advance only through generation samples; no wall-clock sleep or
    # arbitrary peer timestamps are used to make a full peer the oldest.
    final_live_counts = {
        family: sum(peer.family == family for peer in runtime.peers)
        for family in ("service", "active", "working_set")
    }
    final_inventory = record_inventory("before_cleanup")
    final_owner_buffers = [
        {"role": "active", "bytes": len(state.active_projector._encoded)}
        if state.active_projector._encoded is not None else None,
        {"role": "working_set", "bytes": len(state.working_set_projector._encoded)}
        if state.working_set_projector._encoded is not None else None,
    ]
    final_owner_buffers = [item for item in final_owner_buffers if item is not None]

    pressure_reservations = [
        row for row in reservation_events
        if row["currentPlusAdditionalBeforeBytes"] > runtime.encoded_limit
    ]
    natural_drops = [row for row in drop_events if row["insideRuntimeRoom"]]
    dropped_labels = sorted({row["peer"] for row in natural_drops})
    if not pressure_reservations:
        failures.append("default_budget_pressure_not_reached")
    if not natural_drops:
        failures.append("runtime_room_did_not_drop_slow_peer")
    if any(row["family"] != "service" or not row["peer"].startswith("full_slow_") for row in natural_drops):
        failures.append("runtime_room_dropped_healthy_sibling")
    if any(not row["wasOldestWriteStartedCandidate"] for row in natural_drops):
        failures.append("runtime_room_victim_not_oldest_write_started")
    if any(row["bodyBytes"] <= 0 or row["bodyRevision"] is None for row in natural_drops):
        failures.append("runtime_room_drop_lacked_pinned_body")
    if any(not row["fitsAfterRoom"] for row in reservation_events):
        failures.append("working_set_reservation_failed_to_fit")
    if len(generations) < 13 or sum(item["slowPeerQueuedAndPartiallyWritten"] for item in deliveries) < 13:
        failures.append("insufficient_slow_full_generation_bodies")
    slow_body_digests = [
        item["slowReader"]["bodySha256"]
        for item in generations
        if item["slowReader"] is not None
    ]
    if len(set(slow_body_digests)) != len(slow_body_digests):
        failures.append("slow_full_generation_bodies_not_content_distinct")
    if final_live_counts["active"] != 1 or final_live_counts["working_set"] != 1:
        failures.append("healthy_sibling_peer_lost")
    if final_live_counts["service"] < 1:
        failures.append("full_peer_family_unavailable")

    source_file_hashes = source_hashes(root, driver_path)
    if "agent_observer/service_runtime.py" not in source_file_hashes:
        failures.append("runtime_source_not_pinned")
    if "agent_observer/working_set_feed.py" not in source_file_hashes:
        failures.append("working_set_source_not_pinned")
    if "agent_observer/working_set_clocks.py" not in source_file_hashes:
        failures.append("working_set_clock_source_not_pinned")
    if "tests/test_service_state.py" not in source_file_hashes:
        failures.append("fixture_source_not_pinned")
    mesh_imports = [
        name for name in sys.modules
        if name == "mesh_plus" or name.startswith("mesh_plus.")
    ]
    if mesh_imports:
        failures.append("mesh_imported")
    if runtime.counts["workerStarts"] != 0:
        failures.append("worker_started")
    if runtime.encoded_limit != ENCODED_LIMIT_BYTES or runtime.max_clients != CLIENT_LIMIT:
        failures.append("runtime_default_limits_mutated")

    # Stop tracing before teardown; the report above describes natural drops
    # only. Runtime-owned encoded accounting is then cleared normally.
    # Release local references to frame/body DTOs too; the live ServiceState
    # owner buffers are reported separately and intentionally remain retained.
    del seed, full_rows, full, active, working, direct, full_body, body
    runtime._drop = original_drop
    runtime._room = original_room
    state.working_set_reserver = None
    receivers_closed = True
    sender_sockets_closed = True
    for peer in list(runtime.peers):
        runtime._drop(peer)
        peer.parts = ()
        peer.body_revision = None
    for peer_entry in peer_records.values():
        peer = peer_entry() if isinstance(peer_entry, weakref.ReferenceType) else peer_entry
        if peer is not None:
            if peer.sock.fileno() != -1:
                sender_sockets_closed = False
            peer.parts = ()
            peer.body_revision = None
    sender_sockets_closed = sender_sockets_closed and all(
        sock.fileno() == -1 for sock in sender_sockets.values()
    )
    for receiver in receivers.values():
        receiver.close()
    receivers_closed = all(receiver.fileno() == -1 for receiver in receivers.values())
    runtime.bodies.clear()
    runtime.latest.clear()
    runtime.selector.close()
    cleanup_encoded = runtime.encoded_bytes()
    cleanup_owner_expected = sum(item["bytes"] for item in final_owner_buffers)
    if cleanup_encoded != cleanup_owner_expected:
        failures.append("cleanup_counter_not_owner_only")
    if runtime.peers or runtime.bodies or runtime.latest:
        failures.append("runtime_delivery_buffers_survive_cleanup")

    data = {
        "schema": "working-set-resource-pressure-case-v1",
        "sourceRevision": args.source_revision,
        "runtimeSourceRevision": args.runtime_source_revision,
        "root": str(root),
        "pythonVersion": sys.version.split()[0],
        "pythonEntrypoint": args.python_entrypoint,
        "pythonExecutableDiagnostic": sys.executable,
        "gcEnabled": gc.isenabled(),
        "case": {
            "rows": ROWS,
            "fields": "long-title-cwd",
            "titleChars": 256,
            "cwdChars": 1024,
            "windowMs": WINDOW_MS,
            "activeCount": len(active_ids),
            "recentCount": len(recent_ids),
            "expectedUnionCount": len(expected_ids),
            "activeIdentitySha256": digest_ids(active_ids),
            "recentIdentitySha256": digest_ids(recent_ids),
            "expectedUnionIdentitySha256": digest_ids(expected_ids),
            "activityTimestampFixedAcrossGenerations": True,
            "wallFirstMs": WALL_FIRST_MS,
            "wallStepMs": GENERATION_STEP_MS,
            "bootSampleFirstMs": BOOT_FIRST_MS,
            "acceptedBootFirstMs": BOOT_FIRST_MS + 1,
            "bootSampleStepMs": GENERATION_STEP_MS,
            "generationCount": GENERATIONS,
            "initialInputBytes": seed_bytes,
            "initialInputSha256": seed_digest,
            "maxSnapshotBytes": MAX_SNAPSHOT_BYTES,
        },
        "topology": {
            "slowFullPeerCount": SLOW_FULL_PEERS,
            "healthyFullPeerCount": 1,
            "healthyActivePeerCount": 1,
            "healthyWorkingSetPeerCount": 1,
            "peerCountAtStart": CLIENT_LIMIT,
            "peerCountAtPeak": peer_count_highwater,
            "defaultMaxClients": runtime.max_clients,
            "socketBufferSettings": peer_settings,
            "slowReaderReceiverBytesConsumed": 0,
        },
        "runtime": {
            "collect": runtime.collect,
            "workersStarted": 0,
            "encodedLimitBytes": runtime.encoded_limit,
            "encodedLimitChanged": False,
            "worstCaseStageReservationBytes": WORKING_SET_FRAME_BYTES + 2 * MAX_LEDGER_BYTES,
            "workingSetFrameLimitBytes": WORKING_SET_FRAME_BYTES,
            "workingSetLedgerLimitBytes": MAX_LEDGER_BYTES,
        },
        "sourceFilesSha256": source_file_hashes,
        "meshImports": mesh_imports,
        "generations": generations,
        "reservationEvents": reservation_events,
        "roomEvents": room_events,
        "dropEvents": drop_events,
        "operationEvents": events,
        "deliveries": deliveries,
        "counterInventories": all_inventories,
        "pressure": {
            "aboveLimitReservationCount": len(pressure_reservations),
            "firstAboveLimitReservation": pressure_reservations[0] if pressure_reservations else None,
            "naturalRuntimeRoomDropCount": len(natural_drops),
            "naturalDroppedPeerLabels": dropped_labels,
            "allDropsWereOldestPinnedSlowFullPeers": bool(natural_drops) and all(
                row["family"] == "service"
                and row["peer"].startswith("full_slow_")
                and row["wasOldestWriteStartedCandidate"]
                and row["bodyBytes"] > 0
                for row in natural_drops
            ),
            "healthyRoutePeersAtEnd": final_live_counts,
            "finalInventoryBeforeCleanup": final_inventory,
            "actualCounterHighWaterBytes": max_encoded_bytes,
            "maxReservationCurrentPlusAdditionalBytes": max(
                (row["currentPlusAdditionalBeforeBytes"] for row in reservation_events),
                default=0,
            ),
            "cacheRetirementCount": sum(len(row["retiredCacheRevisions"]) for row in room_events)
            + sum(len(row["retiredCacheRevisions"]) for row in events)
            + sum(len(row["retiredCacheRevisions"]) for row in reservation_events),
        },
        "cleanup": {
            "allSenderSocketsClosed": sender_sockets_closed,
            "receiverSocketCount": len(receivers),
            "allReceiverSocketsClosed": receivers_closed,
            "runtimePeersAfterCleanup": len(runtime.peers),
            "runtimeBodiesAfterCleanup": len(runtime.bodies),
            "runtimeLatestAfterCleanup": len(runtime.latest),
            "workingSetReservationRemoved": state.working_set_reserver is None,
            "selectorClosed": True,
            "ownerBuffersRetainedByLiveState": final_owner_buffers,
            "runtimeEncodedBytesAfterCleanup": cleanup_encoded,
            "gcDisabledOwnerZeroClaim": False,
            "rssCurrentKiB": current_rss_kib(),
            "processRssHighWaterKiB": rss_highwater_kib(),
            "rssScope": "process includes imports, state DTOs, fixture/oracle objects, caches, sockets and transient parsing; not a Python heap or production bound",
        },
        "caseStatus": "pressure_complete" if not failures else "unexpected_failure",
        "failures": failures,
        "scope": "synthetic ServiceState acceptance plus actual default Runtime reserve/room/queue/write/drop on local socketpairs; no provider, service process, SDK, Mesh, network, CPU or RSS acceptance",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    if failures:
        raise SystemExit("pressure_case_failures:" + ",".join(failures))
    print(json.dumps({
        "caseStatus": data["caseStatus"],
        "generationCount": len(generations),
        "runtimeRoomDrops": len(natural_drops),
        "droppedPeers": dropped_labels,
        "actualCounterHighWaterBytes": max_encoded_bytes,
        "maxReservationCurrentPlusAdditionalBytes": data["pressure"]["maxReservationCurrentPlusAdditionalBytes"],
        "sourceRevision": args.source_revision,
        "runtimeSourceRevision": args.runtime_source_revision,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
