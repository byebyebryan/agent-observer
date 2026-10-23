"""Shared legacy/sync IPC budgets and exact transaction delivery, no providers."""

import copy
import json
import selectors
import socket
import sys
import unittest
from unittest.mock import patch

from test_service_runtime import Running, scoped_snapshot

from agent_observer.sync_projection_schema import SELECTOR, SELECTOR_DIGEST
from agent_observer.contract import canonical
from agent_observer.service_contract import parse_frame
from agent_observer.service_runtime import MAX_SYNC_ENCODED_BYTES, Peer, Runtime
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import canonical as sync_canonical
from agent_observer.sync_native import parse_message


def request(operation, view="full", **fields):
    return {"syncProtocol": "agent-observer.active-sync" if view == "active" else "agent-observer.sync",
            "version": 1, "operation": operation, "hostScope": "fixture", **fields}


def seeded(*, working_set_window_ms=None):
    state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                         working_set_window_ms=working_set_window_ms)
    state.attempt("codex", "history")
    state.accept("codex", "history", scoped_snapshot(), sampled_ms=state.clock(),
                 ttl_ms=60000, runtime_ttl_ms=60000)
    return state


def read_sync_chain(reader, view="full"):
    """A bounded catch-up ends with a control, never an implicit EOF."""
    lines, transactions = [], []
    for _ in range(5):
        raw = reader.readline()
        value = parse_message(raw, view, "fixture")
        if value["kind"] == "control":
            return tuple(lines), transactions, value
        if value["kind"] != "transaction":
            raise AssertionError("unexpected sync catch-up message")
        lines.append(raw)
        transactions.append(value)
    raise AssertionError("sync catch-up exceeded four transactions without a control")


def assert_attempt_accepted_chain(test, baseline, transactions, control, title):
    """Check delivered semantics without consulting the owner's current roots."""
    test.assertEqual(len(transactions), 2)
    tag, cursor = baseline["tag"], baseline["cursor"]
    for transaction in transactions:
        test.assertEqual(transaction["kind"], "transaction")
        test.assertEqual(transaction["baseTag"], tag)
        test.assertEqual(transaction["baseCursor"], cursor)
        test.assertEqual(transaction["nativeBindingDigest"], tag[0])
        result = transaction["resultTag"]
        test.assertEqual(result[:2], [tag[0], tag[1] + 1])
        test.assertNotEqual(result[2], tag[2])
        test.assertEqual(transaction["resultCursor"], [cursor[0], *result[1:]])
        tag, cursor = result, transaction["resultCursor"]
    test.assertEqual(control["kind"], "control")
    test.assertEqual(control["status"], "complete")
    test.assertEqual(control["baseTag"], baseline["tag"])
    test.assertEqual(control["targetTag"], tag)
    test.assertEqual(control["tag"], tag)
    test.assertEqual(control["cursor"], cursor)

    attempt, accepted = (transaction["operations"] for transaction in transactions)
    # Attempt diagnostics cannot renew body fields, membership, coverage or seals.
    for space in ("records", "bodies", "observations", "memberships", "cohorts", "scopes"):
        test.assertEqual(attempt[space], [], space)
    receipts = {tuple(key): value for key, value in baseline["tables"]["receipts"]}
    history_key = next(key for key in receipts if key[-1] == "history")
    test.assertEqual(len(attempt["receipts"]), 1)
    operation = attempt["receipts"][0]
    test.assertEqual(operation[:2], ["put", list(history_key)])
    expected = copy.deepcopy(receipts[history_key])
    expected.update(attempts=expected["attempts"] + 1, inFlight=True)
    test.assertEqual(operation[3], expected)
    service = copy.deepcopy(dict(baseline["tables"]["metadata"])["service"])
    history = next(component for source in service["sources"] for component in source["components"]
                   if component["name"] == "history")
    history.update(attempts=history["attempts"] + 1, inFlight=True)
    test.assertEqual(len(attempt["metadata"]), 1)
    test.assertEqual(attempt["metadata"][0][:2], ["put", "service"])
    test.assertEqual(attempt["metadata"][0][3], service)

    updates = {tuple(operation[1]): operation[3] for operation in accepted["receipts"]
               if operation[0] == "put"}
    test.assertEqual(set(updates), set(receipts))
    for key, original in receipts.items():
        current = updates[key]
        test.assertEqual(current["accepted"], original["accepted"] + 1)
        test.assertEqual(current["attempts"], original["attempts"] + 1)
        test.assertFalse(current["inFlight"])
        test.assertGreaterEqual(current["sampledBoottimeMs"], original["sampledBoottimeMs"])
        test.assertGreaterEqual(current["expiresBoottimeMs"], original["expiresBoottimeMs"])
    test.assertTrue(any(operation[0] == "put" and operation[3]["title"] == title
                        for operation in accepted["bodies"]))
    test.assertTrue(accepted["records"])


class SyncServiceDeliveryTest(unittest.TestCase):
    def test_default_runtime_denies_both_sync_views_without_creating_owner(self):
        state = seeded()
        with Running(state=state) as server:
            self.assertFalse(server.runtime.experimental_sync)
            for view in ("full", "active"):
                for operation, fields in (("baseline", {}), ("head", {"challenge": {}})):
                    with self.subTest(view=view, operation=operation):
                        raw = sync_canonical(request(operation, view, **fields)) + b"\n"
                        with server.connect(raw) as peer:
                            self.assertEqual(peer.recv(1), b"")
                        self.assertIsNone(state._sync_cache)
            # The disabled experimental family leaves the existing routes usable.
            queries = (
                {"serviceProtocol": 4, "operation": "snapshot", "hostScope": "fixture"},
                {"activeFeedProtocol": 1, "operation": "snapshot", "hostScope": "fixture",
                 "selector": SELECTOR, "selectorDigest": SELECTOR_DIGEST},
            )
            for query in queries:
                with server.connect((canonical(query) + "\n").encode()) as peer:
                    with peer.makefile("rb") as reader:
                        reply = json.loads(reader.readline())
                if "activeFeedProtocol" in query:
                    self.assertEqual((reply["kind"], reply["reason"]), ("error", "active_feed_retired"))
                else:
                    self.assertIsNotNone(reply["snapshot"])
            self.assertIsNone(state._sync_cache)
            self.assertEqual(server.runtime.counts["workerStarts"], 0)

    def test_sync_gate_requires_exact_boolean_before_runtime_setup(self):
        state = seeded()
        for value in (None, 0, 1, "true"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "service_experimental_sync"):
                Runtime(state, "/unused/read.sock", collect=False, experimental_sync=value)
        self.assertIsNone(state._sync_cache)

    def runtime(self, state=None):
        result = Runtime(state or seeded(), "/unused/read.sock", collect=False, experimental_sync=True)
        self.addCleanup(result.selector.close)
        self.addCleanup(lambda: [result._drop(peer) for peer in list(result.peers)])
        self.addCleanup(lambda: [memo.close() for memo in result.image_memos.values()])
        return result

    def peer(self, runtime, *, view="full", write_started=0):
        sender, receiver = socket.socketpair()
        sender.setblocking(False)
        receiver.setblocking(False)
        self.addCleanup(receiver.close)
        result = Peer(sender, runtime.state.clock(), family="sync-" + view,
                      operation="watch", sync_view=view, write_started=write_started)
        runtime.peers.add(result)
        runtime.selector.register(sender, selectors.EVENT_READ, ("peer", result))
        return result, receiver

    def test_head_and_uninitialized_head_never_enter_legacy_or_publication(self):
        runtime = self.runtime()
        peer, _receiver = self.peer(runtime)
        with patch.object(runtime.state, "frame", side_effect=AssertionError("legacy frame")), patch.object(runtime.state, "expire", side_effect=AssertionError("expiry")), patch.object(
            runtime.state, "publish", side_effect=AssertionError("publication"),
        ):
            runtime._sync_request(peer, request("head", challenge={"nonce": "a" * 32}))
            self.assertEqual(json.loads(b"".join(peer.parts))["status"], "baseline_required")
            self.assertIsNone(runtime.state.sync_cursor("full"))
            self.assertEqual(runtime.state._sync_cache.counts["normalizations"], 0)
        runtime._drop(peer)
        baseline = runtime.state.sync_baseline("full")
        peer, _receiver = self.peer(runtime)
        counts = copy.deepcopy(runtime.state._sync_cache.counts)
        with patch.object(runtime.state, "frame", side_effect=AssertionError("legacy frame")), patch.object(runtime.state, "expire", side_effect=AssertionError("expiry")), patch.object(
            runtime.state, "publish", side_effect=AssertionError("publication"),
        ):
            runtime._sync_request(peer, request("head", challenge={"nonce": "b" * 32}))
        value = parse_message(b"".join(peer.parts), "full", "fixture")
        self.assertEqual(value["kind"], "head")
        self.assertEqual(value["challenge"], {"nonce": "b" * 32})
        self.assertEqual(runtime.state._sync_cache.counts["normalizations"], counts["normalizations"])
        self.assertNotEqual(b"".join(peer.parts), baseline)

    def test_baseline_bytes_are_shared_with_cache_and_legacy_body_stays_distinct(self):
        runtime = self.runtime()
        baseline = runtime.state.sync_baseline("full")
        first, _ = self.peer(runtime)
        second, _ = self.peer(runtime)
        runtime._sync_request(first, request("baseline"))
        before = runtime.encoded_bytes()
        runtime._sync_request(second, request("baseline"))
        self.assertIs(first.parts[0], baseline)
        self.assertIs(second.parts[0], baseline)
        self.assertLess(runtime.encoded_bytes() - before, 1024)
        legacy, _ = self.peer(runtime)
        legacy.sync_view, legacy.family = None, "service"
        runtime._queue(legacy, "view")
        self.assertEqual(len(parse_frame(b"".join(legacy.parts))["snapshot"]["sessions"]), 3)
        self.assertEqual(json.loads(baseline)["kind"], "baseline")
        self.assertLessEqual(runtime.sync_encoded_bytes(), MAX_SYNC_ENCODED_BYTES)
        self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)

    def test_shared_delivery_pins_keep_evicted_owner_bytes_heap_charged(self):
        runtime = self.runtime()
        baseline = runtime.state.sync_baseline("full")
        cache = runtime.state._sync_cache
        account = cache.account
        marker = id(baseline)
        self.assertEqual(account._held[marker].refs, 1)
        payload_bytes = account.snapshot()["byKind"]["value_bytes"]
        first, _ = self.peer(runtime)
        second, _ = self.peer(runtime)
        runtime._queue_sync(first, baseline)
        runtime._queue_sync(second, baseline)
        self.assertIs(first.parts[0], second.parts[0])
        self.assertEqual(account._held[marker].refs, 3)
        self.assertEqual(account.snapshot()["byKind"]["value_bytes"], payload_bytes)

        cache._clear_encoded(cache.views["full"])
        self.assertEqual(account._held[marker].refs, 2)
        self.assertEqual(account.snapshot()["byKind"]["value_bytes"], payload_bytes)
        runtime._drop(first)
        self.assertEqual(first.parts, ())
        self.assertIsNone(first.sync_pins)
        self.assertEqual(account._held[marker].refs, 1)
        self.assertEqual(account.snapshot()["byKind"]["value_bytes"], payload_bytes)
        runtime._drop(second)
        self.assertEqual(second.parts, ())
        self.assertIsNone(second.sync_pins)
        self.assertNotIn(marker, account._held)
        self.assertEqual(account.snapshot()["byKind"]["value_bytes"],
                         payload_bytes - sys.getsizeof(baseline))
        # Repeated teardown cannot release another owner's allocation.
        after = account.snapshot()["used"]
        runtime._drop(first)
        runtime._drop(second)
        self.assertEqual(account.snapshot()["used"], after)

    def test_control_and_head_buffers_release_heap_pins_after_write(self):
        runtime = self.runtime()
        runtime.state.sync_baseline("full")
        account = runtime.state._sync_cache.account
        for operation in ("watch", "head"):
            with self.subTest(operation=operation):
                peer, receiver = self.peer(runtime)
                peer.operation = operation
                line = (runtime.state.sync_head("full", {"nonce": "e" * 32})
                        if operation == "head" else
                        runtime.state.sync_control("full", "complete"))
                runtime._queue_sync(peer, line)
                self.assertIsNotNone(peer.sync_pins)
                self.assertIs(account._held[id(line)].value, line)
                runtime._write(peer)
                self.assertEqual(receiver.recv(65536), line)
                self.assertEqual(peer.parts, ())
                self.assertIsNone(peer.sync_pins)
                self.assertNotIn(id(line), account._held)
                self.assertEqual(peer in runtime.peers, operation == "watch")

    def test_owner_close_keeps_live_delivery_bytes_charged_until_peer_drop(self):
        runtime = self.runtime()
        baseline = runtime.state.sync_baseline("full")
        cache = runtime.state._sync_cache
        peer, _ = self.peer(runtime)
        runtime._queue_sync(peer, baseline)
        cache.close()
        self.assertIn(peer, runtime.peers)
        self.assertIs(peer.parts[0], baseline)
        self.assertEqual(cache.account._held[id(baseline)].refs, 1)
        runtime._drop(peer)
        self.assertNotIn(id(baseline), cache.account._held)

    def test_replacing_sync_frame_releases_only_previous_pin(self):
        runtime = self.runtime()
        first = runtime.state.sync_control("full", "complete", "first")
        second = runtime.state.sync_control("full", "complete", "second")
        account = runtime.state._sync_cache.account
        peer, _ = self.peer(runtime)
        runtime._queue_sync(peer, first)
        old_pin = peer.sync_pins
        runtime._queue_sync(peer, second)
        self.assertTrue(old_pin._released)
        self.assertNotIn(id(first), account._held)
        self.assertIs(account._held[id(second)].value, second)
        self.assertEqual(peer.parts, (second,))

    def test_heap_rejection_drops_sync_peer_and_releases_old_frame_only(self):
        runtime = self.runtime()
        old = runtime.state.sync_control("full", "complete", "old")
        new = runtime.state.sync_control("full", "complete", "new")
        account = runtime.state._sync_cache.account
        peer, _ = self.peer(runtime)
        runtime._queue_sync(peer, old)
        old_pin = peer.sync_pins
        legacy, _ = self.peer(runtime)
        legacy.sync_view, legacy.family = None, "service"
        runtime._queue(legacy, "view")
        legacy_parts = legacy.parts
        with patch.object(account, "_limit", account.snapshot()["used"]):
            runtime._queue_sync(peer, new)
        self.assertNotIn(peer, runtime.peers)
        self.assertEqual(peer.parts, ())
        self.assertIsNone(peer.sync_pins)
        self.assertTrue(old_pin._released)
        self.assertNotIn(id(old), account._held)
        self.assertNotIn(id(new), account._held)
        self.assertIn(legacy, runtime.peers)
        self.assertIs(legacy.parts, legacy_parts)
        self.assertTrue(parse_frame(b"".join(legacy.parts))["snapshot"])

    def test_encoded_rejection_precedes_heap_pin(self):
        runtime = self.runtime()
        baseline = runtime.state.sync_baseline("full")
        line = runtime.state.sync_control("full", "complete")
        cache = runtime.state._sync_cache
        self.assertIn(id(line), cache.query_buffers)
        self.assertIn(id(line), cache.account._held)
        peer, _ = self.peer(runtime)
        with patch.object(runtime, "_reserve_sync", return_value=False), patch.object(
            runtime.state, "sync_pin_buffers", side_effect=AssertionError("pin before preflight"),
        ) as pin:
            runtime._queue_sync(peer, line)
        pin.assert_not_called()
        self.assertNotIn(peer, runtime.peers)
        self.assertNotIn(id(line), cache.query_buffers)
        self.assertNotIn(id(line), cache.account._held)
        self.assertIs(cache.views["full"].baseline.data, baseline)
        self.assertIn(id(baseline), cache.account._held)

    def test_disappeared_peer_discards_query_output_without_heap_pin(self):
        runtime = self.runtime()
        peer, _ = self.peer(runtime)
        line = runtime.state.sync_control("full", "complete")
        cache = runtime.state._sync_cache

        def preflight(_reserve):
            runtime._drop(peer)
            return True

        with patch.object(runtime, "_reserve_sync", side_effect=preflight), patch.object(
            runtime.state, "sync_pin_buffers", side_effect=AssertionError("pin after peer dropped"),
        ) as pin:
            runtime._queue_sync(peer, line)
        pin.assert_not_called()
        self.assertNotIn(id(line), cache.query_buffers)
        self.assertNotIn(id(line), cache.account._held)

    def test_encoded_rejection_does_not_discard_baseline_owner(self):
        runtime = self.runtime()
        baseline = runtime.state.sync_baseline("full")
        cache = runtime.state._sync_cache
        peer, _ = self.peer(runtime)
        with patch.object(runtime, "_reserve_sync", return_value=False):
            runtime._queue_sync(peer, baseline)
        self.assertNotIn(peer, runtime.peers)
        self.assertIs(cache.views["full"].baseline.data, baseline)
        self.assertEqual(cache.account._held[id(baseline)].refs, 1)

    def test_internal_canonical_and_stage_storage_share_runtime_encoding_caps(self):
        runtime = self.runtime()
        with patch.object(runtime.state, "sync_owned_encoded_bytes", return_value=MAX_SYNC_ENCODED_BYTES):
            self.assertEqual(runtime.sync_encoded_bytes(), MAX_SYNC_ENCODED_BYTES)
            self.assertEqual(runtime.encoded_bytes(), MAX_SYNC_ENCODED_BYTES)
            self.assertFalse(runtime._sync_room(1))

    def test_watch_at_current_cursor_gets_liveness_only_then_exact_transaction(self):
        runtime = self.runtime()
        baseline = parse_message(runtime.state.sync_baseline("full"), "full", "fixture")
        original = tuple(runtime.state.sync_cursor("full"))
        peer, receiver = self.peer(runtime)
        runtime._sync_request(peer, request("watch", cursor=list(original)))
        self.assertEqual(json.loads(b"".join(peer.parts))["kind"], "control")
        runtime._write(peer)
        receiver.recv(65536)
        self.assertEqual(peer.sync_cursor, original)
        value = scoped_snapshot()
        value["sessions"][0]["title"] = "changed once"
        runtime.state.attempt("codex", "history")
        runtime.state.accept("codex", "history", value, sampled_ms=runtime.state.clock(),
                             ttl_ms=60000, runtime_ttl_ms=60000)
        runtime._sync_tick(peer, runtime.state.clock())
        documents = [json.loads(part) for part in peer.parts]
        self.assertEqual([part["kind"] for part in documents], ["transaction", "transaction", "control"])
        assert_attempt_accepted_chain(self, baseline, documents[:-1], documents[-1], "changed once")
        target = tuple(runtime.state.sync_cursor("full"))
        self.assertEqual(tuple(documents[-2]["resultCursor"]), target)
        retained = runtime.state.sync_changes("full", baseline["tag"], documents[-2]["resultTag"])
        for queued, cached in zip(peer.parts[:-1], retained[:-1], strict=True):
            self.assertIs(queued, cached)
        self.assertEqual(peer.sync_cursor, original)
        runtime._write(peer)
        self.assertEqual(peer.sync_cursor, target)
        self.assertIn(peer, runtime.peers)

    def test_slow_writer_keeps_exact_partial_bytes_then_closes_on_further_backlog(self):
        runtime = self.runtime()
        runtime.state.sync_baseline("full")
        original = tuple(runtime.state.sync_cursor("full"))
        peer, _receiver = self.peer(runtime)
        peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        peer.sync_cursor = original
        line = (canonical({"kind": "fixture-transaction", "padding": "x" * 300000}) + "\n").encode()
        next_cursor = (original[0], original[1] + 1, "a" * 64)
        runtime._queue_sync(peer, (line,), cursor=next_cursor)
        runtime._write(peer)
        self.assertTrue(peer.parts)
        self.assertEqual(peer.sync_cursor, original)
        with patch.object(runtime.state, "sync_cursor", return_value=[original[0], original[1] + 2, "b" * 64]):
            runtime._sync_tick(peer, runtime.state.clock())
        self.assertIs(peer.parts[0], line)
        with patch.object(runtime.state, "sync_cursor", return_value=[original[0], original[1] + 3, "c" * 64]):
            runtime._sync_tick(peer, runtime.state.clock())
        self.assertNotIn(peer, runtime.peers)

    def test_missing_watch_base_is_explicit_terminal_recovery(self):
        runtime = self.runtime()
        runtime.state.sync_baseline("full")
        peer, receiver = self.peer(runtime)
        bad = [runtime.state.service_id, 0, "f" * 64]
        runtime._sync_request(peer, request("watch", cursor=bad))
        control = parse_message(b"".join(peer.parts), "full", "fixture")
        self.assertEqual(control["status"], "baseline_required")
        runtime._write(peer)
        self.assertNotIn(peer, runtime.peers)
        self.assertTrue(receiver.recv(65536).endswith(b"\n"))
        self.assertEqual(receiver.recv(1), b"")

    def test_sync_retention_and_pins_share_real_32mib_budget(self):
        runtime = self.runtime()
        retained = tuple(b"x" * (7 * 1024 * 1024) for _ in range(2)) + tuple(
            b"j" * (1024 * 1024) for _ in range(8))
        first, _ = self.peer(runtime, write_started=1)
        second, _ = self.peer(runtime, write_started=2)
        healthy, _ = self.peer(runtime, write_started=3)
        first.parts = (b"a" * (8 * 1024 * 1024),)
        second.parts = (b"b" * (8 * 1024 * 1024),)
        healthy.parts = (retained[0],)
        with patch.object(runtime.state, "sync_retained_buffers", return_value=retained):
            self.assertGreater(runtime.sync_encoded_bytes(), MAX_SYNC_ENCODED_BYTES)
            self.assertTrue(runtime._sync_room(0))
            self.assertNotIn(first, runtime.peers)
            self.assertIn(second, runtime.peers)
            self.assertIn(healthy, runtime.peers)
            self.assertLessEqual(runtime.sync_encoded_bytes(), MAX_SYNC_ENCODED_BYTES)
            self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)

    def test_owner_reservation_preserves_global_64mib_budget_with_legacy_pins(self):
        runtime = self.runtime()
        legacy = []
        for number in range(6):
            peer, _ = self.peer(runtime, write_started=number + 1)
            peer.sync_view, peer.family = None, "service"
            body = bytes([number + 65]) * (8 * 1024 * 1024)
            runtime.bodies[number + 1] = body
            peer.body_revision, peer.parts = number + 1, (b"{", body, b"}\n")
            legacy.append(peer)
        retained = (b"x" * (7 * 1024 * 1024), b"y" * (7 * 1024 * 1024)) + tuple(
            b"j" * (1024 * 1024) for _ in range(8))
        self.assertTrue(runtime._reserve_sync(sum(map(len, retained))))
        with patch.object(runtime.state, "sync_retained_buffers", return_value=retained):
            self.assertNotIn(legacy[0], runtime.peers)
            self.assertTrue(all(peer in runtime.peers for peer in legacy[1:]))
            self.assertLessEqual(runtime.encoded_bytes(), runtime.encoded_limit)
            self.assertLessEqual(runtime.sync_encoded_bytes(), MAX_SYNC_ENCODED_BYTES)

    def test_bad_discriminants_fields_host_and_challenge_are_closed(self):
        valid = request("head", challenge={})
        cases = [
            {**valid, "serviceProtocol": 4}, {**valid, "activeFeedProtocol": 1},
            {**valid, "version": True}, {**valid, "syncProtocol": "other"},
            {**valid, "operation": "snapshot"}, {**valid, "extra": True},
            {**valid, "hostScope": "foreign"}, {**valid, "challenge": {"x": 1.5}},
            {**valid, "challenge": {"x": "x" * 4097}},
        ]
        with Running(state=seeded(), experimental_sync=True) as server:
            for value in cases:
                with self.subTest(value=value), server.connect((canonical(value) + "\n").encode()) as peer:
                    self.assertEqual(peer.recv(1), b"")
            with server.connect(b'{"serviceProtocol":4,"operation":"snapshot","hostScope":"fixture"}\n') as peer:
                with peer.makefile("rb") as reader:
                    self.assertIsNotNone(parse_frame(reader.readline())["snapshot"])

    def test_real_socket_baseline_watch_barrier_and_head_do_not_collect(self):
        state = seeded()
        with Running(state=state, experimental_sync=True) as server:
            with server.connect(sync_canonical(request("baseline")) + b"\n") as peer:
                with peer.makefile("rb") as reader:
                    baseline = parse_message(reader.readline(), "full", "fixture")
            value = scoped_snapshot()
            value["sessions"][0]["title"] = "between baseline and watch"
            state.attempt("codex", "history")
            state.accept("codex", "history", value, sampled_ms=state.clock(), ttl_ms=60000, runtime_ttl_ms=60000)
            with server.connect(sync_canonical(request("watch", cursor=baseline["cursor"])) + b"\n") as peer:
                with peer.makefile("rb") as reader:
                    lines, transactions, control = read_sync_chain(reader)
                    assert_attempt_accepted_chain(self, baseline, transactions, control,
                                                  "between baseline and watch")
            retained = state.sync_changes("full", baseline["tag"], transactions[-1]["resultTag"])
            self.assertEqual(lines, retained[:-1])
            with server.connect(sync_canonical(request("head", challenge={"nonce": "c" * 32})) + b"\n") as peer:
                with peer.makefile("rb") as reader:
                    head = parse_message(reader.readline(), "full", "fixture")
            self.assertEqual(head["tag"], transactions[-1]["resultTag"])
            self.assertEqual(server.runtime.counts["workerStarts"], 0)
        self.assertIsNone(state.sync_reserver)

    def test_total_sixteen_peers_are_shared_across_all_four_families(self):
        from agent_observer.working_set_contract import selector, selector_digest

        state = seeded(working_set_window_ms=0)
        state.sync_baseline("full")
        state.sync_baseline("active")
        queries = [
            {"serviceProtocol": 4, "operation": "watch", "hostScope": "fixture"},
            {"workingSetProtocol": 1, "operation": "watch", "hostScope": "fixture",
             "selector": selector(0), "selectorDigest": selector_digest(selector(0))},
            request("watch", cursor=list(state.sync_cursor("full"))),
            request("watch", "active", cursor=list(state.sync_cursor("active"))),
        ]
        with Running(state=state, experimental_sync=True) as server:
            clients = []
            try:
                for index in range(16):
                    peer = server.connect((canonical(queries[index % 4]) + "\n").encode())
                    reader = peer.makefile("rb")
                    self.assertTrue(reader.readline().endswith(b"\n"))
                    clients.append((peer, reader))
                self.assertEqual(len(server.runtime.peers), 16)
                with server.connect(b'{"serviceProtocol":4') as extra:
                    try:
                        reply = extra.recv(1)
                    except ConnectionResetError:
                        reply = b""
                    self.assertEqual(reply, b"")
                self.assertEqual(len(server.runtime.peers), 16)
            finally:
                for peer, reader in clients:
                    reader.close()
                    peer.close()
