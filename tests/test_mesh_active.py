"""Optional projected profile, cached acquisition and public prepared facade."""

import asyncio
import contextlib
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_active_contract import support

from agent_observer.active_contract import SELECTOR, SELECTOR_DIGEST, validate_frame
from agent_observer.contract import ContractError, canonical

REQUEST = "a" * 32


def supported():
    if not importlib.util.find_spec("mesh_plus"):
        return False
    try:
        from mesh_plus.api import descriptor
        descriptor("agent", profile_id="agent-observer.mesh-active.v1")
        return True
    except (ImportError, ValueError):
        return False


def native_frame(*, empty=False, optional_history=False):
    from mesh_native_fixture import native_frame as full_native

    value = full_native()
    row = value.pop("snapshot")["sessions"][0]
    value.pop("serviceProtocol")
    value["sources"] = value["sources"][:1]
    value.update(activeFeedProtocol=1, selector=copy.deepcopy(SELECTOR), selectorDigest=SELECTOR_DIGEST)
    history = next(c for c in value["sources"][0]["components"] if c["name"] == "history")
    history["expiresBoottimeMs"] = value["emittedBoottimeMs"] + 5000
    runtime = support(value)
    fields = dict.fromkeys((
        "runtime", "phase", "kind", "savedIdentity", "activity", "outcome", "workspace",
        "lastUpdated", "latestTurn",
    ))
    fields.update(runtime=copy.deepcopy(runtime), phase=copy.deepcopy(runtime), kind=copy.deepcopy(runtime))
    scope = {
        "provider": "codex", "namespace": value["sources"][0]["namespace"],
        "contextGeneration": 1, "continuity": 1,
        "coverage": {"status": "complete", "reason": "complete_native_census", "supports": [runtime]},
        "members": [] if empty else [{"identity": copy.deepcopy(row["identity"]), "fieldSupports": fields}],
        "uncertain": [], "nonmembers": [],
    }
    if optional_history:
        row["activity"].update(at=1700000010000, source="codex_rpc", health="current", reason="native_activity")
        fields["activity"] = support(value, "history")
        scope["coverage"]["supports"].append(support(value, "history"))
    value["projection"] = {"scopes": [scope], "sessions": [] if empty else [row]}
    return validate_frame(value)


def aggregate(native=None, *, admitted=False, profile=None):
    from mesh_plus.api import Endpoint, Reader
    from mesh_plus.transport import boottime_ms

    from agent_observer.mesh_active_profile import ActiveAgentProfile

    native = native_frame() if native is None else native
    profile = ActiveAgentProfile() if profile is None else profile
    state = profile.bind("fixture", "agent").inspect_native(native)
    receipts = []
    now = boottime_ms()
    for original in state.receipts:
        current = original["health"] in {"current", "partial"}
        receipts.append({
            **{k: v for k, v in original.items() if k != "expiry"},
            "remainingMs": max(0, original["expiry"] - now) if current else 0,
            "expiresAtMs": original["expiry"] if current else None,
        })
    host = {
        "hostId": "fixture", "local": True,
        "delivery": {"path": "ipc", "status": "ready", "epoch": 1,
                     "routeToken": None, "error": None, "proof": None},
        "viewState": "warming" if state.owner["metadata"] is None else "current" if any(
            r["health"] in {"current", "partial"} for r in receipts
        ) else "historical",
        "owner": state.owner, "receipts": receipts,
    }
    endpoint = Endpoint("fixture", True, None, None, profile.bind("fixture", "agent"))
    reader = Reader("agent", [endpoint], local_host="fixture", profile=profile)
    compose = reader.compose_admitted if admitted else reader.compose
    return compose(reader.endpoints, {"fixture": (host, list(state.records))}, REQUEST, "watch")


def control(frame, kind, sequence):
    mesh = frame["mesh"]
    return {"protocol": frame["protocol"], "schemaVersion": 1, "mesh": {
        **{key: mesh[key] for key in ("meshProtocol", "requestId", "operation", "access")},
        "reader": {**copy.deepcopy(mesh["reader"]), "sequence": sequence}, "kind": kind,
    }}


@unittest.skipUnless(supported(), "optional active Mesh profile not installed")
class ActiveMeshProfileTest(unittest.TestCase):
    def test_codec_roundtrip_combined_admission_and_strict_raw_boundaries(self):
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_active_profile import ActiveAgentProfile

        profile = ActiveAgentProfile()
        codec = profile.bind("fixture", "agent")
        frame = native_frame()
        payload = {"hostId": "fixture", "sourceId": "agent", "ownerFrame": frame}
        with patch("agent_observer.mesh_active_profile.validate_frame", wraps=validate_frame) as validate:
            state = codec.admit_bridge(payload)
            self.assertEqual(validate.call_count, 1)
        self.assertEqual(profile.restore_native(state.owner, state.records), frame)
        self.assertEqual(state.owner["protocol"], "agent-observer.active-feed")
        self.assertNotIn("sessions", state.owner["metadata"])
        for boundary in (codec.inspect_native, lambda f: codec.validate_bridge({**payload, "ownerFrame": f})):
            bad = copy.deepcopy(frame)
            bad["projection"]["sessions"][0]["title"] = 1
            with self.assertRaises(ContractError):
                boundary(bad)
        with self.assertRaisesRegex(ProtocolError, "bridge_source_binding"):
            codec.admit_bridge({**payload, "sourceId": "other"})
        frame["clockDomain"] = "time:1"
        with self.assertRaisesRegex(ProtocolError, "owner_clock_domain"):
            codec.inspect_native(frame)

    def test_warming_never_translates_native_receipts_into_positives(self):
        from agent_observer.mesh_active_profile import ActiveAgentProfile
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        native = {**native_frame(), "kind": "status", "state": "warming", "projection": None}
        profile = ActiveAgentProfile()
        state = profile.bind("fixture", "agent").inspect_native(native)
        self.assertTrue(state.receipts)
        self.assertFalse(any(r["health"] in {"current", "partial"} for r in state.receipts))
        self.assertEqual(profile.restore_native(state.owner, state.records), native)
        frame = aggregate(native, profile=profile)
        watch = PreparedActiveAgentWatch(REQUEST, profile=profile)
        watch.accept(frame)
        result = watch.read(frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"])
        self.assertFalse(result.members)
        self.assertFalse(result.scopes)

    def test_raw_same_key_newer_accepted_cannot_bind_original_claims(self):
        from agent_observer.mesh_active_profile import ActiveAgentProfile
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        native = native_frame()
        native["sources"][0]["components"][0].update(accepted=2, attempts=2)
        with self.assertRaisesRegex(ContractError, "active_support_mismatch"):
            ActiveAgentProfile().bind("fixture", "agent").inspect_native(native)
        frame = aggregate()
        source = frame["mesh"]["hosts"][0]["owner"]["service"]["sources"][0]
        source["components"][0].update(accepted=2, attempts=2)
        watch = PreparedActiveAgentWatch(REQUEST)
        with self.assertRaises(ContractError):
            watch.accept(frame)
        self.assertIsNone(watch.snapshot())

    def test_factory_selects_only_explicit_full_or_active_without_acquisition(self):
        from functools import partial

        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_active_profile import ACTIVE_PROFILE_ID
        from agent_observer.mesh_active_source import CachedActiveAgentSource
        from agent_observer.mesh_publisher import FULL_PROFILE_ID, make_publisher
        from agent_observer.mesh_source import CachedAgentSource

        full = make_publisher("fixture", "agent", "/not-opened/read.sock")
        active = partial(make_publisher, profile_id=ACTIVE_PROFILE_ID)("fixture", "agent", "/not-opened/read.sock")
        self.assertIs(type(full.native), CachedAgentSource)
        self.assertEqual(full.profile, FULL_PROFILE_ID)
        self.assertIs(type(active.native), CachedActiveAgentSource)
        self.assertEqual(active.profile, ACTIVE_PROFILE_ID)
        self.assertEqual(active.native._active, 0)
        with self.assertRaisesRegex(ProtocolError, "profile_descriptor"):
            make_publisher("fixture", "agent", "/not-opened/read.sock", profile_id="unsupported")


@unittest.skipUnless(supported(), "optional active Mesh profile not installed")
class ActivePreparedReadTest(unittest.TestCase):
    def test_optional_field_expiry_does_not_retire_supported_membership(self):
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        native = native_frame(optional_history=True)
        frame = aggregate(native)
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        clock = frame["mesh"]["reader"]["clock"]
        now = frame["mesh"]["reader"]["encodedAtMs"]
        self.assertEqual(len(watch.read(now, clock).members), 1)
        deadline = support(native, "history")["expiresBoottimeMs"]
        # Generic whole-body preparation expires at the conservative union.
        self.assertEqual(watch._guard.current(deadline, clock), [])
        read = watch.read(deadline, clock)
        self.assertEqual(len(read.sessions), 1)
        self.assertIs(read.sessions, read.members)
        self.assertEqual(read.members[0]["runtime"]["value"], "running")
        self.assertIsNone(read.members[0]["activity"]["at"])
        self.assertEqual(read.members[0]["activity"]["lastKnownAt"], 1700000010000)
        self.assertEqual(read.scopes[0]["coverage"]["status"], "stale")
        self.assertEqual(watch.read(support(native)["expiresBoottimeMs"], clock).members, [])

    def test_complete_empty_expires_even_with_other_receipts_and_retained_header(self):
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        native = native_frame(empty=True)
        runtime = native["sources"][0]["components"][0]
        runtime["expiresBoottimeMs"] = native["emittedBoottimeMs"] + 1000
        native["projection"]["scopes"][0]["coverage"]["supports"] = [support(native)]
        frame = aggregate(native)
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        self.assertEqual(watch.read(now, clock).scopes[0]["coverage"]["status"], "complete")
        read = watch.read(runtime["expiresBoottimeMs"], clock)
        self.assertEqual(read.scopes[0]["coverage"]["status"], "stale")
        self.assertEqual(read.members, [])
        self.assertEqual(read.context["hosts"][0]["owner"]["metadata"]["scopes"][0]["coverage"]["status"], "complete")

    def test_negative_expiry_and_uncertainty_do_not_invent_retirement(self):
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        native = native_frame()
        scope = native["projection"]["scopes"][0]
        row = native["projection"]["sessions"].pop()
        scope["members"].clear()
        scope["coverage"].update(status="partial", supports=[])
        scope["nonmembers"].append({
            "identity": row["identity"], "reason": "parked", "value": "parked",
            "supports": [support(native)], "horizonBoottimeMs": support(native)["expiresBoottimeMs"] + 10000,
        })
        frame = aggregate(native)
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        self.assertEqual(len(watch.read(now, clock).nonmembers), 1)
        self.assertEqual(watch.read(support(native)["expiresBoottimeMs"], clock).nonmembers, [])
        scope["nonmembers"].clear()
        scope["uncertain"].append({
            "identity": row["identity"], "reason": "native_unknown",
            "priorSupport": support(native), "support": None,
            "horizonBoottimeMs": support(native)["expiresBoottimeMs"],
        })
        frame = aggregate(native)
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        read = watch.read(frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"])
        self.assertEqual(len(read.uncertain), 1)
        self.assertEqual(read.nonmembers, [])

    def test_owned_admission_snapshot_once_and_detached_exports(self):
        from mesh_plus.api import PreparedReadGuard

        from agent_observer.mesh_active_profile import ActiveAgentProfile
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        profile = ActiveAgentProfile()
        frame = aggregate(admitted=True, profile=profile)
        watch = PreparedActiveAgentWatch(REQUEST, profile=profile)
        original = PreparedReadGuard.snapshot
        with patch.object(PreparedReadGuard, "snapshot", autospec=True, side_effect=original) as export:
            watch.accept(frame)
            self.assertEqual(export.call_count, 1)
            snapshot = watch.snapshot()
            now, clock = snapshot["mesh"]["reader"]["encodedAtMs"], snapshot["mesh"]["reader"]["clock"]
            for _ in range(3):
                read = watch.read(now, clock)
                read.members[0]["title"] = "mutated"
                read.context["hosts"].clear()
                read.scopes[0]["coverage"]["status"] = "complete"
            self.assertEqual(export.call_count, 1)
        snapshot["sessions"].clear()
        self.assertEqual(len(watch.snapshot()["sessions"]), 1)
        self.assertNotEqual(watch.read(now, clock).members[0]["title"], "mutated")

    def test_public_read_order_heartbeat_gap_disconnect_and_clock_regression(self):
        from mesh_plus.api import PreparedReadGuard
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        frame = aggregate()
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        events = []
        current, context = PreparedReadGuard.current, PreparedReadGuard.context
        with patch.object(PreparedReadGuard, "current", autospec=True,
                          side_effect=lambda guard, *args: (events.append("current"), current(guard, *args))[1]), patch.object(
            PreparedReadGuard, "context", autospec=True,
            side_effect=lambda guard: (events.append("context"), context(guard))[1],
        ):
            watch.read(now, clock)
        self.assertEqual(events, ["current", "context"])
        with patch.object(PreparedReadGuard, "snapshot", side_effect=AssertionError("heartbeat export")):
            watch.accept(control(frame, "heartbeat", 2))
        watch.accept(control(frame, "gap", 3))
        self.assertIsNone(watch.read(now, clock).context)
        self.assertIsNone(watch.snapshot())
        resync = copy.deepcopy(frame)
        resync["mesh"].update(kind="resync")
        resync["mesh"]["reader"].update(sequence=4, revision=2)
        watch.accept(resync)
        self.assertTrue(watch.read(now + 10, clock).members)
        with self.assertRaisesRegex(ProtocolError, "active_reader_clock_regression"):
            watch.read(now + 9, clock)
        self.assertIsNone(watch.snapshot())
        watch.disconnect()
        self.assertEqual(watch.read(now, clock).members, [])

    def test_stale_translated_headers_never_grant_complete_or_positive_members(self):
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        frame = aggregate()
        host = frame["mesh"]["hosts"][0]
        host["viewState"] = "historical"
        for receipt in host["receipts"]:
            receipt.update(health="stale", expiresAtMs=None, remainingMs=0)
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        read = watch.read(frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"])
        self.assertFalse(read.members)
        self.assertEqual(read.scopes[0]["coverage"]["status"], "stale")

    def test_scope_continuity_regression_fails_closed(self):
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        frame = aggregate()
        frame["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]["continuity"] = 2
        watch = PreparedActiveAgentWatch(REQUEST)
        watch.accept(frame)
        bad = copy.deepcopy(frame)
        bad["mesh"]["reader"].update(sequence=2, revision=2)
        bad["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]["continuity"] = 1
        with self.assertRaisesRegex(ProtocolError, "active_scope_continuity"):
            watch.accept(bad)
        self.assertIsNone(watch.snapshot())


@unittest.skipUnless(supported(), "optional active Mesh profile not installed")
class ActiveCachedSourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_projected_ipc_watch_and_fresh_nonce_remote_proof_use_public_sdk(self):
        from mesh_plus.api import (
            Bridge,
            CachedPublication,
            CachedPublisher,
            Client,
            Endpoint,
            Reader,
            configured_reader,
            reconstructed,
        )
        from mesh_plus.protocol import ProtocolError
        from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc

        from agent_observer.mesh_active_profile import ActiveAgentProfile
        from agent_observer.mesh_active_read import PreparedActiveAgentWatch

        class Native:
            def __init__(self):
                self.frame = native_frame()
                self.reads, self.watchers = 0, 0
                self.changes = asyncio.Event()

            async def snapshot(self):
                self.reads += 1
                return copy.deepcopy(self.frame)

            async def watch(self):
                self.watchers += 1
                try:
                    yield CachedPublication(copy.deepcopy(self.frame), self.frame["serviceId"],
                                            {"viewRevision": self.frame["viewRevision"]})
                    await self.changes.wait()
                finally:
                    self.watchers -= 1

        native = Native()
        profile = ActiveAgentProfile()
        publisher = CachedPublisher("agent", "fixture", "agent", native, profile=profile)
        with tempfile.TemporaryDirectory(prefix="observer-active-mesh-") as directory:
            path = Path(directory) / "publisher.sock"
            server = await IPCServer(path, Bridge(publisher).serve).start()
            local = await configured_reader("agent", source="agent", socket=path, scope="local",
                                            local_host="fixture", profile=profile)
            watch = PreparedActiveAgentWatch(REQUEST, profile=profile)
            stream = local.watch_admitted(request_id=REQUEST, proof_interval=.1)
            try:
                async with asyncio.timeout(3):
                    async for response in stream:
                        watch.accept(response)
                        snapshot = watch.snapshot()
                        if snapshot is not None:
                            read = watch.read(boottime_ms(), snapshot["mesh"]["reader"]["clock"])
                            if read.members:
                                break
                self.assertEqual(len(read.members), 1)
                self.assertEqual(watch.snapshot()["sessions"], native.frame["projection"]["sessions"])
            finally:
                watch.disconnect()
                await stream.aclose()

            async def connect():
                return await Client.connect(await connect_ipc(path), host="fixture", source="agent",
                                            profile=publisher.profile, codec=publisher.validate)

            remote = Reader("agent", [Endpoint("fixture", False, "sha256:" + "a" * 64,
                                               connect, profile.bind("fixture", "agent"))],
                            local_host="local", catalog_revision="sha256:" + "b" * 64,
                            profile=profile)
            before = native.reads
            try:
                response = await remote.snapshot()
                host = response["mesh"]["hosts"][0]
                self.assertEqual(host["delivery"]["status"], "ready")
                self.assertIsNotNone(host["delivery"]["proof"])
                self.assertGreater(native.reads, before)
                self.assertEqual(reconstructed(response, host, profile=profile), native.frame)
                before = native.reads
                with self.assertRaises(ProtocolError):
                    await publisher.proof({"nonce": "invalid"})
                self.assertEqual(native.reads, before)
            finally:
                await server.close()
            self.assertEqual(local.inspect()["activeConnections"], 0)
            self.assertEqual(remote.inspect()["activeConnections"], 0)
            self.assertEqual(native.watchers, 0)

    async def test_cached_source_uses_fixed_wire_and_owned_watch_cleanup(self):
        from agent_observer.mesh_active_source import CachedActiveAgentSource

        frame = native_frame()
        requests, tasks = [], set()

        async def handler(reader, writer):
            task = asyncio.current_task()
            tasks.add(task)
            try:
                request = json.loads(await reader.readline())
                requests.append(request)
                reply = {**frame, "kind": "status" if request["operation"] == "status" else "view"}
                writer.write((canonical(reply) + "\n").encode())
                await writer.drain()
                await reader.read()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                tasks.discard(task)

        with tempfile.TemporaryDirectory(prefix="observer-active-cached-") as directory:
            path = Path(directory) / "read.sock"
            server = await asyncio.start_unix_server(handler, path=path)
            path.chmod(0o600)
            source = CachedActiveAgentSource("fixture", path)
            try:
                result = await source.snapshot()
                self.assertEqual(result["projection"], frame["projection"])
                self.assertEqual(source._active, 0)
                stream = source.watch()
                publication = await anext(stream)
                self.assertEqual(publication.epoch, frame["serviceId"])
                self.assertEqual(publication.barrier, {"viewRevision": frame["viewRevision"]})
                await stream.aclose()
                self.assertEqual(source._active, 0)
                self.assertEqual([r["operation"] for r in requests], ["status", "watch"])
                for request in requests:
                    self.assertEqual(request["activeFeedProtocol"], 1)
                    self.assertEqual(request["selector"], SELECTOR)
                    self.assertEqual(request["selectorDigest"], SELECTOR_DIGEST)
                    self.assertNotIn("serviceProtocol", request)
            finally:
                server.close()
                await server.wait_closed()
                for task in list(tasks):
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
