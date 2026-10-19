"""Actual disposable native IPC -> public Mesh Reader -> domain facade.

Synthetic accepted inputs and collect=False are deliberate: this is component
integration, not independent provider, installed artifact or resource evidence.
"""

import asyncio
import copy
import os
import tempfile
import time
import unittest
from pathlib import Path
from uuid import UUID

from jsonschema import ValidationError
from mesh_plus.api import Bridge, Client, Endpoint, Reader, reconstructed, validate_response
from mesh_plus.transport import IPCServer, connect_ipc
from test_service_runtime import Running, scoped_snapshot

from agent_observer.contract import ContractError, canonical, identity_key
from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
from agent_observer.mesh_working_set_publisher import make_working_set_publisher
from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch
from agent_observer.service_state import ServiceState


class RecordingSource:
    """Delegate supported source methods, retaining bounded synthetic audits."""

    def __init__(self, source):
        self.source = source
        self.frames = {}
        self.snapshots = 0

    def record(self, frame):
        if len(self.frames) >= 64:
            raise AssertionError("bounded_source_audit_full")
        self.frames[canonical(frame)] = copy.deepcopy(frame)

    async def snapshot(self):
        self.snapshots += 1
        frame = await self.source.snapshot()
        self.record(frame)
        return frame

    async def watch(self):
        iterator = self.source.watch()
        try:
            async for publication in iterator:
                self.record(publication.frame)
                yield publication
        finally:
            await iterator.aclose()


def state_with_rows(*, window=60_000, count=3, recent_age=1000):
    state = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                         uid=os.geteuid(), working_set_window_ms=window)
    sample = scoped_snapshot()
    wall = int(time.time() * 1000)
    sample["collectedAt"] = wall
    sample["sources"][0]["capabilities"]["activity"] = True
    base = copy.deepcopy(sample["sessions"][0])
    sample["sessions"] = []
    for index in range(count):
        row = copy.deepcopy(base)
        identifier = str(UUID(int=9000 + index))
        row["identity"]["nativeId"] = identifier
        row["nativeIds"].update(threadId=identifier, sessionTreeRootId=identifier)
        if index:
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        row["activity"].update(at=wall - (recent_age if index == 1 else 4_000_000),
                               health="current", source="codex_rpc", reason="native_timestamp")
        sample["sessions"].append(row)
    lower = state.clock()
    state.attempt("codex", "runtime")
    accepted = state.accept("codex", "runtime", sample, sampled_ms=lower,
                            ttl_ms=120_000, accepted_boottime_ms=state.clock())
    if accepted is not True:
        raise AssertionError("synthetic_acceptance_required")
    return state, sample


def reader_clock():
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def reader_now():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


class RegisteredWorkingSetTests(unittest.IsolatedAsyncioTestCase):
    def check_reference_admission(self, snapshot, profile, codec):
        """Independent public routes reject schema-coercible and bad refs."""
        host = snapshot["mesh"]["hosts"][0]
        native = reconstructed(snapshot, host, profile=profile)
        scope = native["projection"]["scopes"][0]
        fields = scope["members"][0]["fieldSupports"]
        field = next(name for name, ref in fields.items() if ref is not None)
        ref = fields[field]
        for bad_ref in (float(ref), False, len(scope["supportTable"])):
            with self.subTest(reference_type=type(bad_ref).__name__, reference=bad_ref):
                malformed = copy.deepcopy(native)
                malformed["projection"]["scopes"][0]["members"][0]["fieldSupports"][field] = bad_ref
                with self.assertRaises(ContractError):
                    codec.inspect_native(malformed)
                bridge = {"hostId": "fixture", "sourceId": "working", "ownerFrame": malformed}
                with self.assertRaises(ContractError):
                    codec.admit_bridge(bridge)
                response = copy.deepcopy(snapshot)
                metadata = response["mesh"]["hosts"][0]["owner"]["metadata"]
                metadata["scopes"][0]["members"][0]["fieldSupports"][field] = bad_ref
                with self.assertRaises((ContractError, ValidationError)):
                    validate_response(response, profile=profile)
        self.assertEqual(canonical(reconstructed(snapshot, host, profile=profile)), canonical(native))

    async def pipeline(self, *, remote, count, window):
        state, sample = state_with_rows(window=window, count=count)
        full_rows = state.frame("status", 1)["snapshot"]["sessions"]
        expected = [row for row in full_rows if row["kind"] in {"unknown", "user"} and (
            row["runtime"]["value"] == "running" or (
                window > 0 and row["activity"]["at"] is not None
                and 0 <= sample["collectedAt"] - row["activity"]["at"] < window
            )
        )]
        profile = WorkingSetAgentProfile(window)
        with Running(state=state) as native, tempfile.TemporaryDirectory() as directory:
            publisher = make_working_set_publisher("fixture", "working", native.path, window_ms=window)
            capture = RecordingSource(publisher.native)
            publisher.native = capture
            mesh_path = Path(directory) / "mesh.sock"
            server = await IPCServer(mesh_path, Bridge(publisher).serve).start()
            codec = profile.bind("fixture", "working")

            async def connect():
                return await Client.connect(await connect_ipc(mesh_path), host="fixture", source="working",
                                            profile=profile.descriptor.profile_id, codec=codec.validate_bridge)

            revision = "sha256:" + "b" * 64

            async def catalog_check():
                return revision

            reader = Reader("agent", [Endpoint("fixture", not remote, revision if remote else None,
                                               connect, codec)], local_host="reader" if remote else "fixture",
                            profile=profile, catalog_revision=revision if remote else None,
                            catalog_check=catalog_check if remote else None)
            stream = reader.watch_admitted(request_id="d" * 32, proof_interval=.1)
            facade = PreparedWorkingSetAgentWatch("d" * 32, profile=profile, window_ms=window)
            nonces = set()
            try:
                for _ in range(40):
                    facade.accept(await asyncio.wait_for(anext(stream), 3))
                    result = facade.read(reader_now(), reader_clock())
                    snapshot = facade.snapshot()
                    if snapshot is None or result.context is None:
                        continue
                    host = snapshot["mesh"]["hosts"][0]
                    if host["delivery"]["status"] != "ready":
                        continue
                    self.assertEqual(result.members, expected)
                    self.assertEqual([identity_key(row["identity"]) for row in result.members],
                                     [identity_key(row["identity"]) for row in expected])
                    self.assertEqual(result.scopes[0]["coverage"]["status"], "complete")
                    restored = reconstructed(snapshot, host, profile=profile)
                    self.assertIn(canonical(restored), capture.frames)
                    self.assertEqual(restored, capture.frames[canonical(restored)])
                    if count and window:
                        self.check_reference_admission(snapshot, profile, codec)
                        self.assertEqual(facade.read(reader_now(), reader_clock()).members, expected)
                    if remote:
                        self.assertIsNotNone(host["delivery"]["proof"])
                        nonces.add(host["delivery"]["proof"]["nonce"])
                        if len(nonces) < 2:
                            continue
                        self.assertGreaterEqual(capture.snapshots, 2)
                    break
                else:
                    self.fail("ordinary_reader_never_reached_complete_fresh_view")
                snapshot["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"].clear()
                self.assertTrue(facade.snapshot()["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"])
                facade.disconnect()
                self.assertIsNone(facade.read(reader_now(), reader_clock()).context)
            finally:
                facade.disconnect()
                await stream.aclose()
                await server.close()
                capture.frames.clear()
            self.assertEqual(reader.inspect()["activeConnections"], 0)
            self.assertEqual(publisher.native.source._active, 0)
            self.assertEqual(publisher.native.source._pending_reads, 0)

    async def test_local_complete_selected_empty_and_zero_window(self):
        for count, window in ((3, 60_000), (0, 60_000), (3, 0)):
            with self.subTest(count=count, window=window):
                await self.pipeline(remote=False, count=count, window=window)

    async def test_remote_proof_selected_empty_and_zero_window(self):
        for count, window in ((3, 60_000), (0, 60_000), (3, 0)):
            with self.subTest(count=count, window=window):
                await self.pipeline(remote=True, count=count, window=window)
