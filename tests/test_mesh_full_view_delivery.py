"""Selected Observer publishers use ordinary complete-view Mesh delivery."""

import asyncio
import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from mesh_test_support import require_working_set_sdk

from agent_observer.contract import canonical


def forbidden(*_args, **_kwargs):
    raise AssertionError("opt-in Mesh delta route selected")


class SelectedFullViewDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_cached_publisher_bridge_reader_full_views_proofs_expiry_reconnect(self):
        """The installed a24 SDK does not select its feed or sync entrypoints."""
        require_working_set_sdk()

        from mesh_plus import api, view_feed
        from mesh_plus import sync as mesh_sync
        from mesh_plus.transport import IPCServer, connect_ipc
        from test_service_runtime import Running
        from test_working_set_registered_sdk import RecordingSource, reader_now, state_with_rows

        from agent_observer.mesh_active_profile import ACTIVE_PROFILE_ID
        from agent_observer.mesh_publisher import FULL_PROFILE_ID, make_publisher
        from agent_observer.mesh_working_set_publisher import make_working_set_publisher
        from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

        disabled = (
            patch.object(view_feed.ViewFeedBridge, "__init__", side_effect=forbidden),
            patch.object(view_feed.ViewFeedClient, "connect", side_effect=forbidden),
            patch.object(view_feed, "configured_reader", side_effect=forbidden),
            patch.object(mesh_sync, "create_sync_relay", side_effect=forbidden),
            patch.object(mesh_sync, "serve_sync_relay", side_effect=forbidden),
            patch.object(mesh_sync.SyncRelay, "__init__", side_effect=forbidden),
        )
        with disabled[0], disabled[1], disabled[2], disabled[3], disabled[4], disabled[5]:
            state, sample = state_with_rows(window=60_000, count=3)
            window = 60_000
            with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
                self.assertFalse(native.runtime.collect)
                self.assertFalse(native.runtime.experimental_sync)
                unused = str(Path(directory) / "unused.sock")
                full = make_publisher("fixture", "agent", unused)
                active = make_publisher("fixture", "agent", unused, profile_id=ACTIVE_PROFILE_ID)
                working = make_working_set_publisher(
                    "fixture", "working", native.path, window_ms=window
                )

                for publisher in (full, active, working):
                    self.assertIs(type(publisher), api.CachedPublisher)
                    self.assertIs(type(api.Bridge(publisher)), api.Bridge)
                self.assertEqual(full.profile, FULL_PROFILE_ID)
                self.assertEqual(active.profile, ACTIVE_PROFILE_ID)

                profile = working.state_profile
                capture = RecordingSource(working.native)
                working.native = capture
                mesh_path = Path(directory) / "mesh.sock"
                server = await IPCServer(mesh_path, api.Bridge(working).serve).start()
                reader = None
                watch = None
                stream = None
                reconnected = None
                reconnect_stream = None
                try:
                    codec = profile.bind("fixture", "working")
                    revision = "sha256:" + "d" * 64

                    async def connect():
                        return await api.Client.connect(
                            await connect_ipc(mesh_path), host="fixture", source="working",
                            profile=working.profile, codec=codec.validate_bridge,
                        )

                    async def catalog_check():
                        return revision

                    reader = api.Reader(
                        "agent",
                        [api.Endpoint("fixture", False, revision, connect, codec)],
                        local_host="reader",
                        profile=profile,
                        catalog_revision=revision,
                        catalog_check=catalog_check,
                    )
                    request_id = "a" * 32
                    watch = PreparedWorkingSetAgentWatch(
                        request_id, profile=profile, window_ms=window
                    )
                    stream = reader.watch_admitted(request_id=request_id, proof_interval=0.1)

                    async def next_full_view(*, prior_nonce=None, title=None):
                        async with asyncio.timeout(5):
                            while True:
                                watch.accept(await anext(stream))
                                response = watch.snapshot()
                                if response is None:
                                    continue
                                host = response["mesh"]["hosts"][0]
                                if host["delivery"]["status"] != "ready" or host["owner"] is None:
                                    continue
                                proof = host["delivery"]["proof"]
                                if proof is None or proof["nonce"] == prior_nonce:
                                    continue
                                frame = api.reconstructed(response, host, profile=profile)
                                rows = frame["projection"]["sessions"]
                                if title is not None and not any(row["title"] == title for row in rows):
                                    continue
                                key = canonical(frame)
                                self.assertIn(key, capture.frames)
                                self.assertEqual(frame, capture.frames[key])
                                return response, frame, proof["nonce"]

                    try:
                        first, first_frame, first_nonce = await next_full_view()
                        self.assertEqual(len(watch.read(
                            reader_now(), first["mesh"]["reader"]["clock"]
                        ).members), 2)
                        unchanged, unchanged_frame, unchanged_nonce = await next_full_view(
                            prior_nonce=first_nonce
                        )
                        self.assertNotEqual(first_nonce, unchanged_nonce)
                        self.assertEqual(unchanged_frame["viewRevision"], first_frame["viewRevision"])
                        self.assertEqual(unchanged_frame["projection"], first_frame["projection"])

                        changed_sample = copy.deepcopy(sample)
                        changed_sample["collectionId"] = str(UUID(int=7654321))
                        changed_sample["collectedAt"] = int(time.time() * 1000)
                        changed_sample["sessions"][0]["title"] = "complete view changed"
                        sampled = state.clock()
                        state.attempt("codex", "runtime")
                        self.assertTrue(state.accept(
                            "codex", "runtime", changed_sample, sampled_ms=sampled,
                            ttl_ms=120_000, accepted_boottime_ms=sampled,
                        ))
                        updated, updated_frame, updated_nonce = await next_full_view(
                            prior_nonce=unchanged_nonce, title="complete view changed"
                        )
                        self.assertNotEqual(updated_nonce, unchanged_nonce)
                        self.assertGreater(updated_frame["viewRevision"], first_frame["viewRevision"])
                        self.assertEqual(updated_frame["projection"]["sessions"][0]["title"],
                                         "complete view changed")

                        receipts = updated["mesh"]["hosts"][0]["receipts"]
                        expiries = [receipt["expiresAtMs"] for receipt in receipts
                                    if type(receipt["expiresAtMs"]) is int]
                        self.assertTrue(expiries)
                        expired = watch.read(max(expiries) + 1,
                                             updated["mesh"]["reader"]["clock"])
                        self.assertEqual(expired.members, [])
                        self.assertEqual(expired.nonmembers, [])
                        self.assertNotEqual(expired.scopes[0]["coverage"]["status"], "complete")
                    finally:
                        if watch is not None:
                            watch.disconnect()
                        if stream is not None:
                            await stream.aclose()
                        watch = stream = None

                    await asyncio.sleep(0.05)
                    self.assertEqual(reader.inspect()["activeConnections"], 0)
                    self.assertEqual(capture.source._active, 0)
                    self.assertEqual(capture.source._pending_reads, 0)

                    reconnect_id = "b" * 32
                    reconnected = PreparedWorkingSetAgentWatch(
                        reconnect_id, profile=profile, window_ms=window
                    )
                    reconnect_stream = reader.watch_admitted(
                        request_id=reconnect_id, proof_interval=0.1
                    )
                    try:
                        response, frame, _nonce = await next_reconnected_view(
                            self, api, reconnect_stream, reconnected, profile, capture,
                            expected_revision=updated_frame["viewRevision"],
                        )
                        self.assertEqual(response["mesh"]["hosts"][0]["delivery"]["status"], "ready")
                        self.assertEqual(frame["projection"]["sessions"][0]["title"],
                                         "complete view changed")
                    finally:
                        if reconnected is not None:
                            reconnected.disconnect()
                        if reconnect_stream is not None:
                            await reconnect_stream.aclose()
                        reconnected = reconnect_stream = None

                    await asyncio.sleep(0.05)
                    self.assertEqual(reader.inspect()["activeConnections"], 0)
                    self.assertEqual(capture.source._active, 0)
                    self.assertEqual(capture.source._pending_reads, 0)
                finally:
                    if watch is not None:
                        watch.disconnect()
                    if stream is not None:
                        await stream.aclose()
                    if reconnected is not None:
                        reconnected.disconnect()
                    if reconnect_stream is not None:
                        await reconnect_stream.aclose()
                    await server.close()


async def next_reconnected_view(test, api, stream, watch, profile, capture, *, expected_revision):
    async with asyncio.timeout(5):
        while True:
            watch.accept(await anext(stream))
            response = watch.snapshot()
            if response is None:
                continue
            host = response["mesh"]["hosts"][0]
            if host["delivery"]["status"] != "ready" or host["owner"] is None:
                continue
            proof = host["delivery"]["proof"]
            if proof is None:
                continue
            frame = api.reconstructed(response, host, profile=profile)
            if frame["viewRevision"] < expected_revision:
                continue
            key = canonical(frame)
            test.assertIn(key, capture.frames)
            test.assertEqual(frame, capture.frames[key])
            return response, frame, proof["nonce"]
