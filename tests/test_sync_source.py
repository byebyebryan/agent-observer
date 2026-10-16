"""Owned sync socket/subscription lifetime; no native provider invocation."""

import asyncio
import contextlib
import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from agent_observer.contract import ContractError, store_namespace
from agent_observer.mesh_source import MAX_INCARNATIONS, boottime_ms
from agent_observer.sync_commitment import canonical, native_binding_digest
from agent_observer.sync_native import TABLES, descriptor, validate_message
from agent_observer.sync_source import (
    BaselineTicket,
    CachedAgentSyncSource,
    ResyncRequired,
    SourceWatch,
    SyncControl,
    _History,
)


def message_fixture(kind="baseline", *, view="full", generation=1, epoch=None):
    """Outer acquisition fixture only; it is not an admitted domain/root state."""
    selected = descriptor(view)
    epoch = epoch or "00000000-0000-0000-0000-000000000007"
    namespace = store_namespace("codex", "/fixture/codex", "explicit", os.geteuid())
    context = {"provider": "codex", "namespace": namespace, "configHome": "/fixture/codex",
               "configHomeKind": "explicit", "contextGeneration": 1, "runtimeContext": None}
    binding = {**{key: selected[key] for key in ("protocol", "version", "schemaDigest", "view")},
               "ownerEpoch": epoch, "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
               "clockDomain": os.readlink("/proc/self/ns/time"), "uid": os.geteuid(), "hostScope": "fixture",
               "selector": None, "sourceContexts": [context], "scopeContinuity": []}
    if view == "active":
        from agent_observer.active_contract import SELECTOR

        binding.update(selector=copy.deepcopy(SELECTOR), scopeContinuity=[["codex", namespace, 1]])
    digest = native_binding_digest(binding)
    tag = [digest, generation, f"{generation:064x}"]
    cursor = [epoch, *tag[1:]]
    now = boottime_ms() - 10
    clock = {key: binding[key] for key in ("bootId", "clockDomain", "ownerEpoch", "uid", "hostScope")}
    clock["boottimeMs"] = now
    receipts = [[["codex", namespace, component], {
        "name": component, "attempts": 1, "accepted": 1, "sampledBoottimeMs": now - 100,
        "expiresBoottimeMs": now + 60000, "health": "current", "lastResult": "accepted",
        "inFlight": False, "serviceId": epoch, "contextGeneration": 1,
    }] for component in ("runtime", "history")]
    if kind == "baseline":
        value = {"kind": kind, "descriptor": selected, "nativeBinding": binding, "tag": tag,
                 "cursor": cursor, "tables": {space: [] for space in TABLES}}
        value["tables"]["receipts"] = receipts
    elif kind == "head":
        value = {"kind": kind, "descriptor": selected, "nativeBindingDigest": digest, "tag": tag,
                 "challenge": {"nonce": "a" * 32}, "ownerClock": clock,
                 "originalReceipts": receipts, "cohortHeads": [],
                 "attenuation": [[key, receipt["expiresBoottimeMs"] - now] for key, receipt in receipts]}
    elif kind == "transaction":
        base = [digest, generation - 1, f"{generation - 1:064x}"]
        value = {"kind": kind, "descriptor": selected, "nativeBindingDigest": digest,
                 "transactionId": "d" * 64, "baseTag": base, "resultTag": tag,
                 "baseCursor": [epoch, *base[1:]], "resultCursor": cursor,
                 "operations": {space: [] for space in TABLES}}
    else:
        value = {"kind": "control", "descriptor": selected, "status": "complete", "reason": "sync_complete",
                 "tag": tag, "cursor": cursor, "ownerClock": clock}
    return validate_message(value, view, expected_host="fixture")


def wire(value):
    return canonical(value) + b"\n"


class SubscriptionOwnershipTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        class Source(CachedAgentSyncSource):
            def __init__(self):
                super().__init__("fixture", "/unused/read.sock")
                self.open_streams = 0
                self.ready, self.release = asyncio.Event(), asyncio.Event()

            async def _frames(self, request, **_kwargs):
                self.open_streams += 1
                try:
                    yield b"first\n"
                    self.ready.set()
                    await self.release.wait()
                    yield b"second\n"
                finally:
                    self.open_streams -= 1

            def subscription(self):
                result = SourceWatch(self, b"request\n")
                self._watches.add(result)
                return result

        self.source = Source()

    async def asyncTearDown(self):
        await self.source.aclose()
        self.assertEqual(self.source.open_streams, 0)
        self.assertEqual(self.source.inspect()["activeTasks"], 0)
        self.assertEqual(self.source.inspect()["activeWatches"], 0)

    async def test_closing_one_subscription_preserves_source_and_sibling(self):
        first, second = self.source.subscription(), self.source.subscription()
        self.assertEqual(await anext(first), b"first\n")
        self.assertEqual(await anext(second), b"first\n")
        await first.aclose()
        self.assertFalse(self.source.inspect()["closed"])
        self.assertEqual(self.source.open_streams, 1)
        self.source.release.set()
        self.assertEqual(await anext(second), b"second\n")
        await second.aclose()

    async def test_async_context_releases_subscription_on_exception(self):
        with self.assertRaisesRegex(RuntimeError, "fixture_failure"):
            async with self.source.subscription() as watch:
                await anext(watch)
                raise RuntimeError("fixture_failure")
        self.assertEqual(self.source.open_streams, 0)
        self.assertFalse(self.source.inspect()["closed"])

    async def test_source_close_cancels_only_owned_pending_work(self):
        watch = self.source.subscription()
        await anext(watch)
        waiting = asyncio.create_task(anext(watch))
        await self.source.ready.wait()
        unrelated = asyncio.create_task(asyncio.sleep(10))
        try:
            await self.source.aclose()
            with self.assertRaises(asyncio.CancelledError):
                await waiting
            self.assertFalse(unrelated.done())
            self.assertTrue(self.source.inspect()["closed"])
            await self.source.aclose()
        finally:
            unrelated.cancel()
            await asyncio.gather(unrelated, return_exceptions=True)

    async def test_concurrent_next_is_explicit_and_cancellation_reaps_watch(self):
        watch = self.source.subscription()
        await anext(watch)
        waiting = asyncio.create_task(anext(watch))
        await self.source.ready.wait()
        with self.assertRaisesRegex(ContractError, "sync_watch_busy"):
            await anext(watch)
        waiting.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiting
        self.assertEqual(self.source.open_streams, 0)

    async def test_invalid_client_configuration_is_rejected_before_io(self):
        for options in ({"view": "other"}, {"timeout": True}, {"timeout": 0}):
            with self.subTest(options=options), self.assertRaises(ContractError):
                CachedAgentSyncSource("fixture", "/unused/read.sock", **options)

    async def test_repeated_close_cancellation_still_reaps_owned_subscription(self):
        cleanup_started, release_cleanup = asyncio.Event(), asyncio.Event()

        async def frames(_request, **_kwargs):
            self.source.open_streams += 1
            try:
                yield b"first\n"
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await release_cleanup.wait()
                self.source.open_streams -= 1

        self.source._frames = frames
        watch = self.source.subscription()
        await anext(watch)
        waiting = asyncio.create_task(anext(watch))
        await asyncio.sleep(0)
        closing = asyncio.create_task(self.source.aclose())
        await cleanup_started.wait()
        closing.cancel()
        await asyncio.sleep(0)
        closing.cancel()
        release_cleanup.set()
        with self.assertRaises(asyncio.CancelledError):
            await closing
        with self.assertRaises(asyncio.CancelledError):
            await waiting
        await self.source.aclose()
        self.assertEqual(self.source.open_streams, 0)


class SyncSourceOrderingTest(unittest.TestCase):
    def setUp(self):
        self.source = CachedAgentSyncSource("fixture", "/unused/read.sock")
        self.head = message_fixture("head")

    def test_exact_receipt_watermarks_and_failed_admission_are_atomic(self):
        history = _History()
        self.source._admit(self.head, history=history)
        previous = copy.deepcopy((self.source._receipts, history))
        bad = copy.deepcopy(self.head)
        bad["originalReceipts"][0][1]["expiresBoottimeMs"] += 1
        with self.assertRaisesRegex(ContractError, "sync_receipt_renewal"):
            self.source._admit(bad, history=history)
        self.assertEqual((self.source._receipts, history), previous)
        bad = copy.deepcopy(self.head)
        bad["originalReceipts"][0][1].update(accepted=2, sampledBoottimeMs=0)
        with self.assertRaisesRegex(ContractError, "sync_receipt_clock_regression"):
            self.source._admit(bad, history=history)
        self.assertEqual((self.source._receipts, history), previous)

    def test_serial_generation_and_receipt_regressions_fail(self):
        history = _History()
        newer = copy.deepcopy(self.head)
        newer["tag"][1] += 1
        newer["originalReceipts"][0][1]["accepted"] += 1
        self.source._admit(newer, history=history)
        with self.assertRaisesRegex(ContractError, "sync_acquisition_superseded"):
            self.source._admit(self.head, history=history)
        older = copy.deepcopy(self.head)
        older["tag"][1] = newer["tag"][1]
        with self.assertRaisesRegex(ContractError, "sync_receipt_regression"):
            self.source._admit(older, history=history)

    def test_future_original_sample_never_becomes_an_acquired_receipt(self):
        bad = copy.deepcopy(self.head)
        bad["originalReceipts"][0][1]["sampledBoottimeMs"] = boottime_ms() + 10000
        with self.assertRaisesRegex(ContractError, "sync_receipt_future"):
            self.source._admit(bad)
        self.assertIsNone(self.source._service)

    def test_retired_owner_never_reappears_and_history_is_bounded(self):
        self.source._admit(self.head)
        for _ in range(MAX_INCARNATIONS - 1):
            replacement = copy.deepcopy(self.head)
            replacement["ownerClock"]["ownerEpoch"] = str(uuid.uuid4())
            self.source._admit(replacement)
        with self.assertRaisesRegex(ContractError, "sync_publisher_retired"):
            self.source._admit(self.head)
        replacement["ownerClock"]["ownerEpoch"] = str(uuid.uuid4())
        with self.assertRaisesRegex(ContractError, "sync_incarnation_capacity"):
            self.source._admit(replacement)


class SyncSourceAcquisitionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="observer-sync-source-")
        self.path = Path(self.directory.name) / "read.sock"
        self.source = CachedAgentSyncSource("fixture", self.path, timeout=1)
        self.baseline = message_fixture()
        self.transaction = message_fixture("transaction", generation=2)
        self.handlers, self.requests = set(), []
        self.mode = "normal"
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.updates = asyncio.Queue()

        async def handler(reader, writer):
            task = asyncio.current_task()
            self.handlers.add(task)
            try:
                request = json.loads(await reader.readline())
                self.requests.append(request)
                self.entered.set()
                if self.mode == "wait":
                    await self.release.wait()
                operation = request["operation"]
                if operation == "baseline":
                    response = copy.deepcopy(self.baseline)
                    if self.mode == "wrong_uid":
                        response["nativeBinding"]["uid"] += 1
                        response["nativeBinding"]["sourceContexts"].clear()
                        response["tables"]["receipts"].clear()
                        response["tag"][0] = native_binding_digest(response["nativeBinding"])
                    writer.write(wire(response))
                elif operation == "head":
                    response = message_fixture("head")
                    response["originalReceipts"] = copy.deepcopy(self.baseline["tables"]["receipts"])
                    response["challenge"] = request["challenge"] if self.mode != "wrong_challenge" else {}
                    now = response["ownerClock"]["boottimeMs"]
                    response["attenuation"] = [[key, max(0, receipt["expiresBoottimeMs"] - now)]
                                               for key, receipt in response["originalReceipts"]]
                    writer.write(wire(response))
                elif operation == "changes":
                    response = copy.deepcopy(self.transaction)
                    if self.mode == "wrong_chain":
                        response["baseTag"][2] = response["baseCursor"][2] = "f" * 64
                    writer.write(wire(response))
                    if self.mode != "missing_terminal":
                        complete = message_fixture("control", generation=2)
                        complete.update(baseTag=request["baseTag"], targetTag=request["targetTag"])
                        if self.mode == "required":
                            complete.update(status="baseline_required", reason="sync_missing_base")
                        writer.write(wire(complete))
                else:
                    writer.write(wire(message_fixture("control")))
                    await writer.drain()
                    update = await self.updates.get()
                    writer.write(wire(update))
                await writer.drain()
                if operation == "watch":
                    await reader.read()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                self.handlers.discard(task)

        self.handler = handler
        self.server = await asyncio.start_unix_server(handler, path=self.path)
        self.path.chmod(0o600)

    async def asyncTearDown(self):
        await self.source.aclose()
        self.server.close()
        for task in list(self.handlers):
            task.cancel()
        await asyncio.gather(*self.handlers, return_exceptions=True)
        await self.server.wait_closed()
        self.assertEqual(self.source.inspect()["activeSockets"], 0)
        self.assertEqual(self.source.inspect()["activeTasks"], 0)

    async def test_watch_capacity_rejection_and_close_release_slots_without_io(self):
        watches = [self.source.watch(self.baseline["cursor"]) for _ in range(16)]
        with self.assertRaisesRegex(ContractError, "sync_acquisition_capacity"):
            self.source.watch(self.baseline["cursor"])
        self.assertEqual(self.source.inspect()["activeSockets"], 0)
        self.assertEqual(self.requests, [])
        await watches[0].aclose()
        replacement = self.source.watch(self.baseline["cursor"])
        await self.source.aclose()
        self.assertEqual(self.source.inspect()["activeWatches"], 0)
        with self.assertRaises(StopAsyncIteration):
            await anext(replacement)
        self.assertEqual(self.source.inspect()["activeWatches"], 0)
        self.directory.cleanup()

    async def test_all_four_operations_preserve_exact_bytes_and_own_cleanup(self):
        with patch("agent_observer.service_contract.parse_frame", side_effect=AssertionError("legacy parse")), patch(
            "agent_observer.active_contract.parse_frame", side_effect=AssertionError("legacy active parse"),
        ):
            ticket = await self.source.baseline()
            self.assertIsInstance(ticket, BaselineTicket)
            self.assertEqual(ticket.data, wire(self.baseline))
            self.assertEqual(ticket.tag, tuple(self.baseline["tag"]))
            reply = await self.source.head_after_nonce({"nonce": "b" * 32})
            self.assertEqual(json.loads(reply)["challenge"], {"nonce": "b" * 32})
            changes = await self.source.changes(ticket.tag, target=self.transaction["resultTag"])
            self.assertEqual(changes, (wire(self.transaction),))
            async with self.source.watch(ticket.cursor) as watch:
                self.assertIsInstance(await anext(watch), SyncControl)
                self.updates.put_nowait(self.transaction)
                self.assertEqual(await anext(watch), wire(self.transaction))
        self.assertEqual([value["operation"] for value in self.requests], ["baseline", "head", "changes", "watch"])
        self.assertTrue(all(value["syncProtocol"] == "agent-observer.sync" for value in self.requests))
        self.assertEqual(self.source.inspect()["activeSockets"], 0)

    async def test_partial_or_wrong_chain_never_returns_a_partial_result(self):
        for mode in ("wrong_chain", "missing_terminal"):
            self.mode = mode
            with self.subTest(mode=mode), self.assertRaises(ContractError):
                await self.source.changes(self.baseline["tag"], target=self.transaction["resultTag"])
            self.assertEqual(self.source.inspect()["activeSockets"], 0)
        self.mode = "required"
        result = await self.source.changes(self.baseline["tag"], target=self.transaction["resultTag"])
        self.assertIsInstance(result, ResyncRequired)
        self.assertEqual(result.status, "baseline_required")

    async def test_wrong_uid_and_challenge_are_rejected_before_admission(self):
        self.mode = "wrong_uid"
        with self.assertRaisesRegex(ContractError, "sync_clock_context"):
            await self.source.baseline()
        self.assertIsNone(self.source._service)
        self.mode = "wrong_challenge"
        with self.assertRaisesRegex(ContractError, "sync_challenge_binding"):
            await self.source.head_after_nonce({"nonce": "b" * 32})
        self.assertIsNone(self.source._service)

    async def test_source_close_reaps_blocked_real_socket_read(self):
        self.mode = "wait"
        task = asyncio.create_task(self.source.baseline())
        await self.entered.wait()
        await self.source.aclose()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.release.set()
        self.assertEqual(self.source.inspect()["activeSockets"], 0)

    async def test_reply_from_replaced_socket_inode_is_rejected(self):
        self.mode = "wait"
        task = asyncio.create_task(self.source.baseline())
        await self.entered.wait()
        previous = self.server
        previous.close()
        self.path.unlink(missing_ok=True)
        self.server = await asyncio.start_unix_server(self.handler, path=self.path)
        self.path.chmod(0o600)
        self.release.set()
        with self.assertRaisesRegex(ContractError, "service_socket_changed"):
            await task
        await previous.wait_closed()
        self.assertIsNone(self.source._service)


class RealServiceSyncSourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_full_active_clients_barrier_changes_and_independent_close(self):
        from test_service_runtime import Running, scoped_snapshot
        from test_sync_service_delivery import assert_attempt_accepted_chain, seeded

        state = seeded()
        with Running(state=state) as server:
            full = CachedAgentSyncSource("fixture", server.path)
            active = CachedAgentSyncSource("fixture", server.path, view="active")
            try:
                ticket = await full.baseline()
                active_ticket = await active.baseline()
                self.assertEqual(json.loads(ticket.data)["descriptor"]["view"], "full")
                self.assertEqual(json.loads(active_ticket.data)["descriptor"]["view"], "active")
                normalizations = state._sync_cache.counts["normalizations"]
                for source in (full, active):
                    reply = await source.head_after_nonce({"nonce": "c" * 32})
                    self.assertEqual(json.loads(reply)["kind"], "head")
                self.assertEqual(state._sync_cache.counts["normalizations"], normalizations)
                async with full.watch(ticket.cursor) as watch:
                    self.assertIsInstance(await anext(watch), SyncControl)
                    value = scoped_snapshot()
                    value["sessions"][0]["title"] = "one new native generation"
                    state.attempt("codex", "history")
                    state.accept("codex", "history", value, sampled_ms=state.clock(),
                                 ttl_ms=60000, runtime_ttl_ms=60000)
                    lines, transactions = [], []
                    for _ in range(5):
                        item = await asyncio.wait_for(anext(watch), 3)
                        if isinstance(item, SyncControl):
                            control = json.loads(item.data)
                            break
                        lines.append(item)
                        transactions.append(json.loads(item))
                    else:
                        self.fail("sync watch exceeded four transactions without a control")
                    assert_attempt_accepted_chain(self, json.loads(ticket.data), transactions, control,
                                                  "one new native generation")
                    chain = await full.changes(ticket.tag, target=transactions[-1]["resultTag"])
                    self.assertEqual(chain, tuple(lines))
                await full.aclose()
                self.assertTrue(full.inspect()["closed"])
                reply = await active.head_after_nonce({"nonce": "d" * 32})
                self.assertEqual(json.loads(reply)["kind"], "head")
                self.assertEqual(server.runtime.counts["workerStarts"], 0)
            finally:
                await full.aclose()
                await active.aclose()
            self.assertEqual(full.inspect()["activeSockets"], 0)
            self.assertEqual(active.inspect()["activeSockets"], 0)
