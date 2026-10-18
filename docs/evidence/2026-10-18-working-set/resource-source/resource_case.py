"""One synthetic ServiceState/runtime resource case in a fresh process.

This records encoded-byte accounting and process RSS only. It is not a CPU,
heap, provider, transport, Mesh, SDK, or production-service qualification.
"""

import gc

gc.disable()

import argparse
import copy
import hashlib
import json
import resource
import socket
import selectors
import sys
from pathlib import Path
from uuid import UUID

ROOT_ARGUMENT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT_ARGUMENT))
sys.path.insert(0, str(ROOT_ARGUMENT / "tests"))

from test_service_state import provider_snapshot

from agent_observer.active_contract import validate_frame as validate_active_frame
from agent_observer.contract import (
    MAX_SNAPSHOT_BYTES,
    canonical,
    identity_key,
    store_namespace,
    validate_snapshot,
)
from agent_observer.service_contract import validate_frame as validate_service_frame
from agent_observer.service_runtime import Peer, Runtime
from agent_observer.service_state import ServiceState
from agent_observer.working_set_contract import (
    DEFAULT_WINDOW_MS,
    MAX_FRAME_BYTES,
    MAX_LEDGER_BYTES,
    validate_frame as validate_working_set_frame,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--python-entrypoint", required=True)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument(
        "--mix", choices=("small", "quarter", "burst"), required=True
    )
    parser.add_argument("--fields", choices=("ordinary", "long-title-cwd"), required=True)
    return parser.parse_args()


ARGS = parse_args()
ROOT = ARGS.root.resolve()
if ROOT != ROOT_ARGUMENT:
    raise RuntimeError("resource_root_argument_mismatch")

from agent_observer.contract import canonical as _canonical

WALL_MS = 1_700_000_020_000
BOOT_ID = "00000000-0000-0000-0000-000000000001"
CLOCK_DOMAIN = "time:[123]"
RECENT_AGE_MS = 60 * 60 * 1000
OLD_AGE_MS = 10 * 24 * 60 * 60 * 1000
WINDOW_MS = DEFAULT_WINDOW_MS
ENCODED_LIMIT = 64 * 1024 * 1024
FAMILIES = (("full", "service"), ("active", "active"), ("working_set", "working_set"))
PEERS_PER_FAMILY = 5
GROUPS = {
    "full": ((0, 1), (2, 3), (4,)),
    "active": ((0, 1), (4,), (2, 3)),
    "working_set": ((4,), (0, 1), (2, 3)),
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def current_rss_kib():
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def process_highwater_kib():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def id_digest(values):
    return sha256("\n".join(sorted(values)).encode())


def build_layout(rows, mix):
    if mix == "small":
        each = max(1, rows // 200)
        active_only, recent_only, overlap = each, each, 0
    elif mix == "quarter":
        active_only, recent_only, overlap = rows // 10, rows // 10, rows // 20
    else:
        active_only, recent_only, overlap = 0, rows, 0
    active_ids = set()
    recent_ids = set()
    roles = []
    for index in range(active_only):
        roles.append("active_only")
    for index in range(recent_only):
        role = "recent_only"
        if active_only == 0 and mix == "burst":
            role = "recent_only"
        roles.append(role)
    for index in range(overlap):
        roles.append("overlap")
    # Spread the three groups through a deterministic, non-prefix order so the
    # row identity list does not encode the branch result.
    if mix == "small":
        assignments = ["active_only"] * active_only + ["recent_only"] * recent_only
    elif mix == "quarter":
        assignments = (
            ["active_only"] * active_only
            + ["recent_only"] * recent_only
            + ["overlap"] * overlap
        )
    else:
        assignments = ["recent_only"] * rows
    result = ["old"] * rows
    positions = list(range(rows))
    order = sorted(positions, key=lambda item: ((item * 7919) % max(1, rows), item))
    for index, role in zip(order, assignments):
        result[index] = role
        native_id = str(UUID(int=1000 + index))
        if role in {"active_only", "overlap"}:
            active_ids.add(native_id)
        if role in {"recent_only", "overlap"}:
            recent_ids.add(native_id)
    return result, active_ids, recent_ids, active_ids | recent_ids


def make_seed(rows, mix, fields):
    value = provider_snapshot("codex")
    value["host"]["uid"] = 1000
    namespace = store_namespace("codex", "/fixture/codex", "explicit", 1000)
    value["sources"][0]["namespace"] = namespace
    value["sources"][0]["configHome"] = "/fixture/codex"
    value["sources"][0]["configHomeKind"] = "explicit"
    value["sources"][0]["capabilities"]["runtime"] = ["running", "parked"]
    value["sources"][0]["capabilities"]["activity"] = True
    template = copy.deepcopy(value["sessions"][0])
    value["sessions"] = []
    roles, active_ids, recent_ids, expected_ids = build_layout(rows, mix)
    input_ids = set()
    for index, role in enumerate(roles):
        row = copy.deepcopy(template)
        native_id = str(UUID(int=1000 + index))
        input_ids.add(native_id)
        row["identity"]["namespace"] = namespace
        row["identity"]["nativeId"] = native_id
        row["nativeIds"].update(threadId=native_id, sessionTreeRootId=native_id)
        row["runtime"]["value"] = "running" if role in {"active_only", "overlap"} else "parked"
        if row["runtime"]["value"] == "parked":
            row["phase"], row["blockedReasons"] = None, []
        age = RECENT_AGE_MS if role in {"recent_only", "overlap"} else OLD_AGE_MS
        row["activity"].update(
            at=WALL_MS - age,
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        if fields == "long-title-cwd":
            row["title"] = "t" * 256
            row["cwd"] = "/" + "c" * 1023
        value["sessions"].append(row)
    if input_ids != {str(UUID(int=1000 + i)) for i in range(rows)}:
        raise RuntimeError("synthetic_identity_layout")
    validate_snapshot(value)
    input_bytes = len(canonical(value).encode())
    if input_bytes > MAX_SNAPSHOT_BYTES:
        raise RuntimeError("synthetic_input_exceeds_native_snapshot_limit")
    return value, roles, active_ids, recent_ids, expected_ids, input_bytes


def add_peer(runtime, now, family_label, runtime_family, slot, sockets, labels):
    sender, receiver = socket.socketpair()
    sender.setblocking(False)
    receiver.setblocking(False)
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
    label = f"{family_label}-{slot}"
    peer = Peer(sender, now, operation="watch", family=runtime_family)
    runtime.peers.add(peer)
    runtime.selector.register(sender, selectors.EVENT_READ, ("resource_peer", peer))
    sockets[label] = receiver
    labels[id(peer)] = label
    return peer, {
        "label": label,
        "requestedSendBufferBytes": 1024,
        "actualSendBufferBytes": sender.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
        "actualReceiveBufferBytes": receiver.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
    }


def _role_entries(runtime, state, labels):
    entries = []
    owners = (
        ("owner.active", state.active_projector._encoded),
        ("owner.working_set", state.working_set_projector._encoded),
    )
    for role, value in owners:
        if value is not None:
            entries.append((role, value))
    for revision, value in runtime.bodies.items():
        if isinstance(revision, tuple):
            role = f"cache.{revision[0]}:{revision[1]}"
        else:
            role = f"cache.full:{revision}"
        entries.append((role, value))
    for peer in runtime.peers:
        label = labels.get(id(peer), "unlabeled")
        for index, value in enumerate(peer.parts):
            role = f"peer.{label}.part{index}"
            if index == 1 and peer.body_revision is not None:
                body = runtime.bodies.get(peer.body_revision)
                if body is None or value is not body:
                    raise RuntimeError("pinned_peer_body_alias_mismatch")
                role = f"peer.{label}.body_alias"
            entries.append((role, value))
    return entries


def buffer_inventory(runtime, state, labels):
    entries = _role_entries(runtime, state, labels)
    unique = {}
    roles = {}
    for role, value in entries:
        item = unique.setdefault(id(value), {"length": len(value), "roles": []})
        item["roles"].append(role)
        prefix = role.split(".", 1)[0]
        aggregate = roles.setdefault(prefix, {"references": 0, "referenceBytes": 0})
        aggregate["references"] += 1
        aggregate["referenceBytes"] += len(value)
    unique_role_bytes = {}
    for item in unique.values():
        prefixes = sorted({role.split(".", 1)[0] for role in item["roles"]})
        for prefix in prefixes:
            unique_role_bytes[prefix] = unique_role_bytes.get(prefix, 0) + item["length"]
    unique_buffer_bytes = sum(item["length"] for item in unique.values())
    role_byte_sum = sum(unique_role_bytes.values())
    peer_body_alias_entries = [
        (role, value) for role, value in entries if role.endswith(".body_alias")
    ]
    owner_values = {
        id(value): value
        for value in state.working_set_retained_buffers()
    }
    peer_bytes = sum(
        len(value)
        for peer in runtime.peers
        if peer.sync_view is None
        for index, value in enumerate(peer.parts)
        if not (index == 1 and peer.body_revision is not None)
    )
    manual_charge = (
        runtime.sync_encoded_bytes()
        + sum(map(len, owner_values.values()))
        + sum(map(len, runtime.bodies.values()))
        + peer_bytes
    )
    actual_charge = runtime.encoded_bytes()
    return {
        "runtimeEncodedBytes": actual_charge,
        "manualChargedBytes": manual_charge,
        "counterMatchesRoleCharge": actual_charge == manual_charge,
        "limitBytes": runtime.encoded_limit,
        "withinLimit": actual_charge <= runtime.encoded_limit,
        "bufferReferenceCount": len(entries),
        "uniqueBufferObjectCount": len(unique),
        "uniqueBufferBytes": unique_buffer_bytes,
        "uniqueBufferBytesByRole": dict(sorted(unique_role_bytes.items())),
        "roleByteSum": role_byte_sum,
        "roleOverlapBytes": role_byte_sum - unique_buffer_bytes,
        "peerBodyAliasReferenceCount": len(peer_body_alias_entries),
        "peerBodyAliasReferenceBytes": sum(len(value) for _role, value in peer_body_alias_entries),
        "uniqueBufferBytesWithinConservativeCharge": unique_buffer_bytes <= actual_charge,
        "pinnedPeerBodyAliasesMatchCache": True,
        "roleReferences": {key: value for key, value in sorted(roles.items())},
        "rssCurrentKiB": current_rss_kib(),
        "processRssHighWaterKiB": process_highwater_kib(),
    }


def cache_keys(runtime):
    return {str(key) for key in runtime.bodies}


def live_peer_labels(runtime, labels):
    return {labels[id(peer)] for peer in runtime.peers if id(peer) in labels}


def current_generation_result(
    state, generation, input_bytes, input_digest, active_ids, expected_ids
):
    sequence = generation + 1
    full = validate_service_frame(state.frame("status", sequence))
    active = validate_active_frame(state.active_frame("status", sequence))
    working = validate_working_set_frame(state.working_set_frame("status", sequence))
    full_rows = full["snapshot"]["sessions"]
    active_rows = active["projection"]["sessions"]
    full_ids = {row["identity"]["nativeId"] for row in full_rows}
    active_actual = {row["identity"]["nativeId"] for row in active_rows}
    if full["state"] != "ready" or len(full_rows) != ARGS.rows:
        raise RuntimeError("legacy_full_route_mismatch")
    if active_actual != active_ids:
        raise RuntimeError("legacy_active_route_mismatch")
    if len(full_ids) != ARGS.rows:
        raise RuntimeError("legacy_full_identity_mismatch")

    projector = state.working_set_projector
    projection = working["projection"]
    reason = None
    coverage = None
    actual_ids = set()
    bodies_equal = None
    exact_membership = None
    capacity_outcome = None
    working_set_dto_digest = (
        sha256(canonical(projection["sessions"]).encode())
        if projection is not None
        else None
    )
    if working["kind"] == "error":
        reason = working["reason"]
        if reason != "projection_encoding_capacity" or projection is not None:
            raise RuntimeError("unclassified_working_set_error")
        capacity_outcome = "stage_reservation_refused"
    elif projection is not None:
        scope = projection["scopes"][0]
        coverage = scope["coverage"]["status"]
        reason = scope["coverage"]["reason"]
        actual_ids = {row["identity"]["nativeId"] for row in projection["sessions"]}
        if coverage == "complete":
            expected_rows = sorted(
                (row for row in full_rows if row["identity"]["nativeId"] in expected_ids),
                key=lambda row: identity_key(row["identity"]),
            )
            actual_rows = projection["sessions"]
            exact_membership = actual_ids == expected_ids
            bodies_equal = actual_rows == expected_rows
            if not exact_membership or not bodies_equal:
                raise RuntimeError("complete_working_set_mismatch")
        elif reason in {
            "projection_tracking_capacity",
            "projection_frame_capacity",
            "recency_tracking_capacity",
        }:
            capacity_outcome = reason
            if not actual_ids.issubset(expected_ids):
                raise RuntimeError("capacity_output_not_subset_of_expected")
        else:
            raise RuntimeError("unexplained_incomplete_working_set")
    else:
        raise RuntimeError("working_set_material_missing_without_explicit_error")

    missing_active = active_actual - actual_ids
    active_missing_digest = id_digest(missing_active) if missing_active else None
    if capacity_outcome is None and missing_active:
        raise RuntimeError("working_set_lost_active_member")
    return {
        "generation": generation,
        "inputSnapshotBytes": input_bytes,
        "inputSnapshotSha256": input_digest,
        "serviceRevision": state.revision,
        "workingSetViewRevision": state.working_set_revision,
        "workingSetKind": working["kind"],
        "workingSetErrorReason": working["reason"] if working["kind"] == "error" else None,
        "coverageStatus": coverage,
        "coverageReason": reason,
        "capacityOutcome": capacity_outcome,
        "expectedActiveCount": len(active_ids),
        "actualActiveCount": len(active_actual),
        "workingSetMissingActiveCount": len(missing_active),
        "workingSetMissingActiveIdentityDigest": active_missing_digest,
        "activeIdentityDigest": id_digest(active_actual),
        "expectedWorkingSetCount": len(expected_ids),
        "actualWorkingSetCount": len(actual_ids),
        "expectedWorkingSetIdentityDigest": id_digest(expected_ids),
        "actualWorkingSetIdentityDigest": id_digest(actual_ids),
        "exactMembershipWhenComplete": exact_membership,
        "originalFullDtoEqualityWhenComplete": bodies_equal,
        "fullRows": len(full_rows),
        "fullIdentityDigest": id_digest(full_ids),
        "fullDtoDigest": sha256(canonical(full_rows).encode()),
        "activeDtoDigest": sha256(canonical(active_rows).encode()),
        "workingSetDtoDigest": working_set_dto_digest,
        "providerRuntimeHealth": state.receipts["codex"]["runtime"].health,
        "providerRuntimeAccepted": state.receipts["codex"]["runtime"].accepted,
        "workingSetBlocked": projector._capacity_blocked,
        "processRssHighWaterKiB": process_highwater_kib(),
        "rssCurrentKiB": current_rss_kib(),
    }


def source_hashes(root):
    files = {}
    for name, module in tuple(sys.modules.items()):
        path_value = getattr(module, "__file__", None)
        if not path_value:
            continue
        path = Path(path_value).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if relative.parts[0] not in {"agent_observer", "tests"} or path.suffix != ".py":
            continue
        files[str(relative)] = sha256(path.read_bytes())
    script_path = Path(__file__).resolve()
    files["resource-source/resource_case.py"] = sha256(script_path.read_bytes())
    fixture_path = root / "tests/fixtures/service-v4/view.json"
    files["tests/fixtures/service-v4/view.json"] = sha256(fixture_path.read_bytes())
    snapshot_schema = root / "agent_observer/contracts/snapshot.schema.json"
    files["agent_observer/contracts/snapshot.schema.json"] = sha256(snapshot_schema.read_bytes())
    return dict(sorted(files.items()))


def main():
    seed, roles, active_ids, recent_ids, expected_ids, input_bytes = make_seed(
        ARGS.rows, ARGS.mix, ARGS.fields
    )
    input_digest = sha256(canonical(seed).encode())
    now = [10_001]
    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=1000,
        clock=lambda: now[0],
        boot_id=BOOT_ID,
        clock_domain=CLOCK_DOMAIN,
        working_set_window_ms=WINDOW_MS,
    )
    runtime = Runtime(state, "/unused/resource-source.sock", collect=False)
    if runtime.encoded_limit != ENCODED_LIMIT or runtime.max_clients != 16:
        raise RuntimeError("runtime_default_limits_changed")
    state.working_set_reserver = runtime._reserve_working_set
    reservation_calls = []
    original_reserve = runtime._reserve_working_set
    generation_for_reserve = [None]
    sockets, labels, peer_details = {}, {}, []
    peers_by_family = {}
    generations = []
    counter_points = []
    delivery_events = []
    failures = []
    max_encoded_bytes = 0

    def record_point(label, generation):
        nonlocal max_encoded_bytes
        inventory = buffer_inventory(runtime, state, labels)
        max_encoded_bytes = max(max_encoded_bytes, inventory["runtimeEncodedBytes"])
        if (not inventory["withinLimit"] or not inventory["counterMatchesRoleCharge"]
                or not inventory["uniqueBufferBytesWithinConservativeCharge"]
                or not inventory["pinnedPeerBodyAliasesMatchCache"]):
            failures.append(f"{label}:encoded_counter_invariant")
        counter_points.append({"label": label, "generation": generation, **inventory})
        return inventory

    def record_reservation(additional_bytes):
        before = runtime.encoded_bytes()
        before_peers = live_peer_labels(runtime, labels)
        before_cache = cache_keys(runtime)
        result = original_reserve(additional_bytes)
        after = runtime.encoded_bytes()
        after_peers = live_peer_labels(runtime, labels)
        after_cache = cache_keys(runtime)
        counter_after_room = record_point("reservation_after_room", generation_for_reserve[0])
        row = {
            "generation": generation_for_reserve[0],
            "currentBytesBefore": before,
            "worstCaseAdditionalBytes": additional_bytes,
            "requestedCurrentPlusAdditionalBytes": before + additional_bytes,
            "admitted": result,
            "currentBytesAfterRoom": after,
            "admittedCurrentPlusAdditionalBytes": after + additional_bytes if result else None,
            "limitBytes": runtime.encoded_limit,
            "admittedReservationFitsLimit": bool(result and after + additional_bytes <= runtime.encoded_limit),
            "droppedPeerLabels": sorted(before_peers - after_peers),
            "evictedCacheKeys": sorted(before_cache - after_cache),
            "counterAfterRoom": counter_after_room,
        }
        if result and after + additional_bytes > runtime.encoded_limit:
            raise RuntimeError("runtime_reserve_admitted_over_limit")
        if after > runtime.encoded_limit:
            raise RuntimeError("runtime_counter_over_limit_after_reservation")
        reservation_calls.append(row)
        if row["droppedPeerLabels"] or row["evictedCacheKeys"]:
            delivery_events.append({
                "operation": "reserve",
                "generation": generation_for_reserve[0],
                "droppedPeerLabels": row["droppedPeerLabels"],
                "evictedCacheKeys": row["evictedCacheKeys"],
            })
        return result

    state.working_set_reserver = record_reservation
    for display_family, runtime_family in FAMILIES:
        family_peers = []
        for slot in range(PEERS_PER_FAMILY):
            peer, detail = add_peer(
                runtime, now[0], display_family, runtime_family, slot,
                sockets, labels,
            )
            family_peers.append(peer)
            peer_details.append(detail)
        peers_by_family[display_family] = family_peers
    if len(runtime.peers) > runtime.max_clients:
        raise RuntimeError("resource_peer_count_over_runtime_cap")
    peer_count_highwater = len(runtime.peers)

    template = copy.deepcopy(seed["sessions"][0])
    seed["sessions"] = []
    source_activity_timestamp = WALL_MS - RECENT_AGE_MS
    expected_active_count = len(active_ids)
    expected_recent_count = len(recent_ids)
    record_point("startup", None)
    for generation in range(3):
        now[0] = 10_001 + generation
        generation_for_reserve[0] = generation
        sample = copy.deepcopy(seed)
        sample["collectionId"] = str(UUID(int=200 + generation))
        sample["collectedAt"] = WALL_MS + generation
        rows = []
        for index, role in enumerate(roles):
            row = copy.deepcopy(template)
            native_id = str(UUID(int=1000 + index))
            row["identity"]["namespace"] = store_namespace(
                "codex", "/fixture/codex", "explicit", 1000
            )
            row["identity"]["nativeId"] = native_id
            row["nativeIds"].update(threadId=native_id, sessionTreeRootId=native_id)
            row["runtime"]["value"] = "running" if role in {"active_only", "overlap"} else "parked"
            if row["runtime"]["value"] == "parked":
                row["phase"], row["blockedReasons"] = None, []
            age = RECENT_AGE_MS if role in {"recent_only", "overlap"} else OLD_AGE_MS
            row["activity"].update(
                at=WALL_MS - age,
                health="current",
                source="codex_rpc",
                reason="native_timestamp",
            )
            if ARGS.fields == "long-title-cwd":
                row["title"] = "t" * 256
                row["cwd"] = "/" + "c" * 1023
            rows.append(row)
        sample["sessions"] = rows
        validate_snapshot(sample)
        sample_bytes = canonical(sample).encode()
        generation_input_bytes = len(sample_bytes)
        generation_input_digest = sha256(sample_bytes)
        del sample_bytes
        if generation_input_bytes > MAX_SNAPSHOT_BYTES:
            raise RuntimeError("native_snapshot_limit_exceeded")
        state.attempt("codex", "runtime")
        if not state.accept(
            "codex",
            "runtime",
            sample,
            sampled_ms=10_000 + generation,
            ttl_ms=100_000,
            accepted_boottime_ms=now[0],
        ):
            raise RuntimeError("synthetic_source_accept_rejected")
        del sample, rows
        result = current_generation_result(
            state,
            generation,
            generation_input_bytes,
            generation_input_digest,
            active_ids,
            expected_ids,
        )
        if result["providerRuntimeHealth"] != "current":
            raise RuntimeError("synthetic_provider_health_changed")
        if result["coverageStatus"] == "complete" and result["capacityOutcome"] is None:
            if result["actualWorkingSetCount"] != len(expected_ids):
                raise RuntimeError("complete_expected_union_mismatch")
        generations.append(result)
        record_point("accepted_generation", generation)

        family_results = {}
        for family, runtime_family in FAMILIES:
            group = GROUPS[family][generation]
            family_peers = peers_by_family[family]
            selected_peers = [family_peers[slot] for slot in group]
            queued = []
            for slot, peer in zip(group, selected_peers):
                before_peers = live_peer_labels(runtime, labels)
                before_cache = cache_keys(runtime)
                if peer in runtime.peers:
                    runtime._queue(peer, "view")
                queued.append(peer)
                peer_count_highwater = max(peer_count_highwater, len(runtime.peers))
                record_point(f"{family}_queue_peer_{slot}", generation)
                after_peers = live_peer_labels(runtime, labels)
                after_cache = cache_keys(runtime)
                dropped = sorted(before_peers - after_peers)
                evicted = sorted(before_cache - after_cache)
                if dropped or evicted:
                    delivery_events.append({
                        "operation": "queue",
                        "family": family,
                        "generation": generation,
                        "peerSlot": slot,
                        "droppedPeerLabels": dropped,
                        "evictedCacheKeys": evicted,
                    })
            live_queued = [peer for peer in queued if peer in runtime.peers and peer.body_revision is not None]
            same_generation = False
            if len(live_queued) >= 2:
                left, right = live_queued[0], live_queued[1]
                same_generation = (
                    left in runtime.peers
                    and right in runtime.peers
                    and left.body_revision is not None
                    and left.body_revision == right.body_revision
                    and len(left.parts) > 1
                    and len(right.parts) > 1
                    and left.parts[1] is right.parts[1]
                )
                if not same_generation:
                    failures.append(f"{family}-generation-{generation}:body_not_shared")
            write_peer = queued[0]
            write_label = labels.get(id(write_peer), "dropped")
            write_before = len(write_peer.parts)
            before_peers = live_peer_labels(runtime, labels)
            before_cache = cache_keys(runtime)
            if write_peer in runtime.peers and write_peer.parts:
                runtime._write(write_peer)
            peer_count_highwater = max(peer_count_highwater, len(runtime.peers))
            record_point(f"{family}_write_peer_{group[0]}", generation)
            after_peers = live_peer_labels(runtime, labels)
            after_cache = cache_keys(runtime)
            dropped = sorted(before_peers - after_peers)
            evicted = sorted(before_cache - after_cache)
            if dropped or evicted:
                delivery_events.append({
                    "operation": "write",
                    "family": family,
                    "generation": generation,
                    "peerSlot": group[0],
                    "droppedPeerLabels": dropped,
                    "evictedCacheKeys": evicted,
                })
            write_pending = write_peer in runtime.peers and bool(write_peer.parts)
            family_results[family] = {
                "queuedPeerCount": len(live_queued),
                "sharedSameGenerationBody": same_generation if len(live_queued) >= 2 else None,
                "slowPeerLabel": write_label,
                "slowPeerWriteAttempted": write_before > 0,
                "slowPeerStillHasFragments": write_pending,
                "slowPeerBodyRevisionPinned": write_peer.body_revision is not None
                if write_peer in runtime.peers else False,
            }
        if len(runtime.peers) > runtime.max_clients:
            raise RuntimeError("runtime_peer_cap_exceeded")
        record_point("queued_and_written_generation", generation)
        previous_material = []
        if generation > 0:
            for family_peers in peers_by_family.values():
                for peer in family_peers:
                    if peer in runtime.peers and peer.body_revision is not None:
                        key = peer.body_revision
                        previous_material.append({
                            "peer": labels[id(peer)],
                            "bodyRevision": str(key),
                            "bodyRetained": key in runtime.bodies,
                        })
                        if key not in runtime.bodies:
                            failures.append("pinned_body_missing_from_runtime_cache")
        generations[-1]["deliveryFamilies"] = family_results
        generations[-1]["pinnedPeerBodiesAfterQueue"] = previous_material
        generations[-1]["runtimePeerCount"] = len(runtime.peers)
        generations[-1]["runtimeDroppedConnectionCount"] = runtime.counts["droppedConnections"]
        if state.receipts["codex"]["runtime"].accepted != generation + 1:
            raise RuntimeError("provider_acceptance_counter_mismatch")

    for family, _runtime_family in FAMILIES:
        shared_generations = sum(
            item["deliveryFamilies"][family]["sharedSameGenerationBody"] is True
            for item in generations
        )
        if shared_generations < 2:
            failures.append(f"{family}:insufficient_shared_generation_observations")

    for row in reservation_calls:
        if not row["admitted"] and row["currentBytesAfterRoom"] > row["limitBytes"]:
            failures.append("refused_reservation_left_counter_over_limit")
    # On complete generations the selected DTO digest is compared to the
    # current full inventory subset; capacity outcomes are reported explicitly.
    outcomes = [
        "complete" if item["capacityOutcome"] is None and item["coverageStatus"] == "complete"
        else "bounded_refusal"
        for item in generations
    ]

    final_inventory = buffer_inventory(runtime, state, labels)
    admitted_reservation_totals = [
        row["admittedCurrentPlusAdditionalBytes"]
        for row in reservation_calls
        if row["admittedCurrentPlusAdditionalBytes"] is not None
    ]
    owner_before_cleanup = [
        {"role": "active_owner", "bytes": len(state.active_projector._encoded)}
        if state.active_projector._encoded is not None else None,
        {"role": "working_set_owner", "bytes": len(state.working_set_projector._encoded)}
        if state.working_set_projector._encoded is not None else None,
    ]
    owner_before_cleanup = [item for item in owner_before_cleanup if item is not None]
    all_peers = [peer for family_peers in peers_by_family.values() for peer in family_peers]
    for peer in all_peers:
        if peer in runtime.peers:
            runtime._drop(peer)
        peer.parts = ()
        peer.body_revision = None
    receiver_socket_count = len(sockets)
    for receiver in sockets.values():
        receiver.close()
    receiver_sockets_closed = all(receiver.fileno() == -1 for receiver in sockets.values())
    sockets.clear()
    runtime.bodies.clear()
    runtime.latest.clear()
    for family_peers in peers_by_family.values():
        family_peers.clear()
    peers_by_family.clear()
    state.working_set_reserver = None
    runtime.selector.close()
    owner_after_cleanup = [
        {"role": "active_owner", "bytes": len(state.active_projector._encoded)}
        if state.active_projector._encoded is not None else None,
        {"role": "working_set_owner", "bytes": len(state.working_set_projector._encoded)}
        if state.working_set_projector._encoded is not None else None,
    ]
    owner_after_cleanup = [item for item in owner_after_cleanup if item is not None]
    peer_fragments_after_cleanup = sum(len(peer.parts) for peer in all_peers)
    peer_body_pins_after_cleanup = sum(peer.body_revision is not None for peer in all_peers)
    peer_sockets_closed = all(peer.sock.fileno() == -1 for peer in all_peers)
    final_encoded_after_cleanup = runtime.encoded_bytes()
    post_cleanup_inventory = record_point("cleanup_after_cache_clear", None)
    if final_encoded_after_cleanup != post_cleanup_inventory["runtimeEncodedBytes"]:
        failures.append("cleanup_counter_changed_during_inventory")
    if len(runtime.peers) or runtime.bodies or runtime.latest:
        failures.append("runtime_delivery_references_survive_cleanup")
    if any(peer.parts or peer.body_revision is not None for peer in all_peers):
        failures.append("peer_material_references_survive_cleanup")
    selected_peers.clear()
    queued.clear()
    all_peers.clear()
    labels.clear()
    peer = None
    write_peer = None
    left = right = None

    source_file_hashes = source_hashes(ROOT)
    if "tests/test_service_state.py" not in source_file_hashes:
        raise RuntimeError("provider_snapshot_fixture_not_pinned")
    if "agent_observer/working_set_feed.py" not in source_file_hashes:
        raise RuntimeError("working_set_projector_source_not_pinned")
    if "agent_observer/working_set_clocks.py" not in source_file_hashes:
        raise RuntimeError("working_set_clock_source_not_pinned")
    if any(name == "mesh_plus" or name.startswith("mesh_plus.") for name in sys.modules):
        raise RuntimeError("mesh_imported_in_source_resource_case")
    if final_encoded_after_cleanup > runtime.encoded_limit:
        failures.append("cleanup_owner_counter_over_limit")

    data = {
        "schema": "working-set-resource-source-case-v1",
        "sourceRevision": ARGS.source_revision,
        "root": str(ROOT),
        "pythonVersion": sys.version.split()[0],
        "pythonEntrypoint": ARGS.python_entrypoint,
        "pythonExecutableDiagnostic": sys.executable,
        "gcEnabled": gc.isenabled(),
        "case": {
            "rows": ARGS.rows,
            "mix": ARGS.mix,
            "fields": ARGS.fields,
            "windowMs": WINDOW_MS,
            "activeCount": expected_active_count,
            "recentCount": expected_recent_count,
            "expectedUnionCount": len(expected_ids),
            "expectedActiveIdentityDigest": id_digest(active_ids),
            "expectedRecentIdentityDigest": id_digest(recent_ids),
            "expectedUnionIdentityDigest": id_digest(expected_ids),
            "activityAtMs": source_activity_timestamp,
            "recentActivityAtMs": WALL_MS - RECENT_AGE_MS,
            "oldActivityAtMs": WALL_MS - OLD_AGE_MS,
            "eventTimestampFixedAcrossGenerations": True,
            "wallMsFirst": WALL_MS,
            "wallIncrementPerGenerationMs": 1,
            "sampledBoottimeMsFirst": 10_000,
            "acceptedBoottimeMsFirst": 10_001,
            "boottimeBracketWidthMs": 1,
            "freshCollectionIds": [str(UUID(int=200 + index)) for index in range(3)],
            "longTitleChars": 256 if ARGS.fields == "long-title-cwd" else None,
            "longCwdChars": 1024 if ARGS.fields == "long-title-cwd" else None,
            "initialNativeSnapshotBytes": input_bytes,
            "maximumNativeSnapshotBytes": MAX_SNAPSHOT_BYTES,
            "initialInputSha256": input_digest,
        },
        "runtime": {
            "collect": False,
            "workersStarted": runtime.counts["workerStarts"],
            "encodedLimitBytes": runtime.encoded_limit,
            "encodedLimitChanged": False,
            "maxClients": runtime.max_clients,
            "runtimePeerCountAtPeak": peer_count_highwater,
            "socketpairPeerCount": len(peer_details),
            "socketBufferSettings": peer_details,
            "worstCaseStageReservationBytes": MAX_FRAME_BYTES + 2 * MAX_LEDGER_BYTES,
            "workingSetLedgerLimitBytes": MAX_LEDGER_BYTES,
            "workingSetFrameLimitBytes": MAX_FRAME_BYTES,
        },
        "sourceFilesSha256": source_file_hashes,
        "meshImports": [name for name in sys.modules if name == "mesh_plus" or name.startswith("mesh_plus.")],
        "reservations": reservation_calls,
        "deliveryResourceEvents": delivery_events,
        "observedCacheEvictionCount": sum(
            len(event["evictedCacheKeys"]) for event in delivery_events
        ),
        "observedRuntimePeerDropCount": sum(
            len(event["droppedPeerLabels"]) for event in delivery_events
        ),
        "generations": generations,
        "counterPoints": counter_points,
        "finalInventoryBeforeCleanup": final_inventory,
        "cleanup": {
            "peersClosed": len(peer_details),
            "receiverSocketsClosed": receiver_socket_count,
            "receiverSocketsAllClosed": receiver_sockets_closed,
            "runtimePeersAfterCleanup": len(runtime.peers),
            "peerSocketsClosed": peer_sockets_closed,
            "peerFragmentPartsRetainedAfterCleanup": peer_fragments_after_cleanup,
            "peerBodyPinsRetainedAfterCleanup": peer_body_pins_after_cleanup,
            "cacheReferencesCleared": True,
            "runtimeBodiesAfterCleanup": len(runtime.bodies),
            "runtimeLatestAfterCleanup": len(runtime.latest),
            "workingSetReserverRemoved": state.working_set_reserver is None,
            "selectorClosed": True,
            "ownerBuffersRetainedAfterCleanup": owner_after_cleanup,
            "runtimeEncodedBytesAfterCleanup": final_encoded_after_cleanup,
            "gcDisabledOwnerZeroClaim": False,
            "rssCurrentKiB": current_rss_kib(),
            "processRssHighWaterKiB": process_highwater_kib(),
        },
        "encodedCounterHighWaterBytes": max_encoded_bytes,
        "admittedReservationHighWaterBytes": max(admitted_reservation_totals, default=0),
        "requestedCurrentPlusReservationHighWaterBytes": max(
            (row["requestedCurrentPlusAdditionalBytes"] for row in reservation_calls),
            default=0,
        ),
        "refusedReservationCount": sum(not row["admitted"] for row in reservation_calls),
        "allAdmittedReservationsWithinDefaultLimit": all(
            row["admittedReservationFitsLimit"]
            for row in reservation_calls
            if row["admitted"]
        ),
        "allActualCountersWithinDefaultLimit": max_encoded_bytes <= ENCODED_LIMIT
        and all(point["withinLimit"] for point in counter_points),
        "allCountersMatchConservativeRoleCharge": all(
            point["counterMatchesRoleCharge"]
            and point["uniqueBufferBytesWithinConservativeCharge"]
            and point["pinnedPeerBodyAliasesMatchCache"]
            for point in counter_points
        ),
        "outcomes": outcomes,
        "caseStatus": "complete" if all(outcome == "complete" for outcome in outcomes)
        else "explicit_bounded_refusal",
        "failures": failures,
        "rssScope": "process current/high-water includes imports, fixture, oracle, state, peers and caches; not a production RSS or heap bound",
        "scope": "synthetic accepted ServiceState plus actual Runtime reservation/queue/write and socketpairs; no provider, service process, Mesh, SDK, network, CPU, delta or production operation",
    }
    if not data["allActualCountersWithinDefaultLimit"]:
        data["failures"].append("actual_encoded_counter_exceeded_default_limit")
    if not data["allCountersMatchConservativeRoleCharge"]:
        data["failures"].append("runtime_counter_role_inventory_mismatch")
    if failures:
        data["caseStatus"] = "unexpected_failure"
    ARGS.output.parent.mkdir(parents=True, exist_ok=True)
    ARGS.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    if failures:
        raise SystemExit("resource_case_failures:" + ",".join(failures))
    print(json.dumps({
        "case": data["case"],
        "caseStatus": data["caseStatus"],
        "outcomes": outcomes,
        "encodedCounterHighWaterBytes": max_encoded_bytes,
        "sourceRevision": ARGS.source_revision,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
