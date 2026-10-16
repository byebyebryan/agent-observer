"""Independent Agent rules, owned exports and fail-closed watch lifetimes."""

import asyncio
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REQUEST = "a" * 32


def supported():
    if not importlib.util.find_spec("mesh_plus"):
        return False
    from mesh_plus import api
    return getattr(api, "PREPARATION_INTERFACE_VERSION", None) == 1


def golden_frames():
    corpus = json.loads((ROOT / "tests/fixtures/mesh-v3/corpus.json").read_text())
    for case in corpus["cases"]:
        frame = copy.deepcopy(case["response"])
        frame["mesh"].update(operation="watch", requestId=REQUEST)
        yield case["case_id"], frame


def control(frame, kind, sequence):
    mesh = frame["mesh"]
    return {"protocol": frame["protocol"], "schemaVersion": 1, "mesh": {
        **{key: mesh[key] for key in ("meshProtocol", "requestId", "operation", "access")},
        "reader": {**copy.deepcopy(mesh["reader"]), "sequence": sequence}, "kind": kind,
    }}


@unittest.skipUnless(supported(), "optional prepared Mesh capability not installed")
class AgentPreparationTests(unittest.TestCase):
    def test_static_rules_have_independent_identity_receipt_and_eligibility_expectations(self):
        from mesh_plus.api import PreparationState

        from agent_observer.mesh_preparation import AgentPreparation

        identity = {"hostScope": "fixture", "provider": "codex", "namespace": "sha256:" + "a" * 64,
                    "nativeIdKind": "thread", "nativeId": "00000000-0000-4000-8000-000000000001"}
        source = "codex:" + identity["namespace"]
        for saved in (False, True):
            for health in ("current", "stale", "unknown"):
                for components in ((), ("history",), ("runtime",), ("history", "runtime")):
                    row = MappingProxyType({"identity": MappingProxyType(identity), "hasSavedHistory": saved,
                                            "runtime": MappingProxyType({"health": health})})
                    receipts = tuple(MappingProxyType({"sourceId": source, "component": c, "health": "partial"})
                                     for c in components)
                    state = PreparationState(MappingProxyType({}), (row,), MappingProxyType({}), "fixture", 100, receipts)
                    preparation = AgentPreparation()
                    rules = preparation.prepare_rules(state)
                    self.assertEqual(rules, preparation.prepare_rules(state))
                    self.assertEqual(len(rules), 1)
                    rule = rules[0]
                    self.assertEqual(rule.identity, tuple(identity.values()))
                    self.assertEqual(rule.required, frozenset((source, c) for c in components) or None)
                    self.assertIs(rule.eligible, saved or health == "current" and "runtime" in components)

    def test_full_v3_golden_raw_rows_and_multiple_expiry_boundaries_match_legacy(self):
        from mesh_plus.api import ReadGuard

        from agent_observer.mesh_profile import AgentProfile
        from agent_observer.mesh_read import PreparedAgentWatch

        for name, frame in golden_frames():
            with self.subTest(case=name):
                profile = AgentProfile()
                legacy = ReadGuard("agent", REQUEST, profile=profile)
                candidate = PreparedAgentWatch(REQUEST, profile=profile)
                legacy.accept(frame)
                candidate.accept(frame)
                self.assertEqual(candidate.snapshot(), frame)
                clock = frame["mesh"]["reader"]["clock"]
                boundaries = {frame["mesh"]["reader"]["encodedAtMs"]}
                boundaries.update(r["expiresAtMs"] for h in frame["mesh"]["hosts"]
                                  for r in h["receipts"] if r["expiresAtMs"] is not None)
                for now in sorted(boundaries):
                    read = candidate.read(now, clock)
                    self.assertEqual(read.sessions, legacy.current(now, clock))
                    self.assertEqual(read.context, frame["mesh"])
                candidate.disconnect()
                self.assertIsNone(candidate.read(max(boundaries), clock).context)
                self.assertEqual(candidate.read(max(boundaries), clock).sessions, [])

    def test_mutation_and_repeated_reads_cannot_modify_or_revalidate_admitted_facts(self):
        from agent_observer.mesh_profile import AgentCodec
        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-fleet"]
        original = copy.deepcopy(frame)
        watch = PreparedAgentWatch(REQUEST)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        frame["sessions"].clear()
        frame["mesh"]["hosts"].clear()
        exported = watch.read(now, clock)
        exported.sessions[0]["title"] = "changed"
        exported.context["hosts"].clear()
        watch.snapshot()["sessions"].clear()
        with patch.object(AgentCodec, "inspect_native", side_effect=AssertionError("read revalidation")):
            for _ in range(4):
                current = watch.read(now, clock)
                self.assertEqual(current.context, original["mesh"])
                self.assertEqual(current.sessions[0]["title"], original["sessions"][0]["title"])
        self.assertEqual(watch.snapshot(), original)

    def test_heartbeat_exports_nothing_and_gap_requires_resync(self):
        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        watch = PreparedAgentWatch(REQUEST)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        with patch.object(type(watch._guard), "snapshot", side_effect=AssertionError("heartbeat export")):
            watch.accept(control(frame, "heartbeat", 2))
            self.assertEqual(watch.read(now, clock).context, frame["mesh"])
        watch.accept(control(frame, "gap", 3))
        self.assertIsNone(watch.read(now, clock).context)
        self.assertFalse(watch.read(now, clock).sessions)
        resync = copy.deepcopy(frame)
        resync["mesh"].update(kind="resync")
        resync["mesh"]["reader"].update(sequence=4, revision=2)
        watch.accept(resync)
        self.assertTrue(watch.read(now, clock).sessions)

    def test_replacement_context_does_not_export_raw_records(self):
        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-fleet"]
        watch = PreparedAgentWatch(REQUEST)
        with patch.object(type(watch._guard), "snapshot", side_effect=AssertionError("raw export")):
            watch.accept(frame)
            now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
            self.assertEqual(watch.read(now, clock).context, frame["mesh"])

    def test_failed_admission_clock_capacity_and_changed_binding_revoke_context(self):
        from jsonschema import ValidationError
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_preparation import AgentPreparation
        from agent_observer.mesh_read import PreparedAgentWatch
        from agent_observer.public import ContractError

        frame = dict(golden_frames())["agent-local"]
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        for fault in ("shape", "scope", "clock", "capacity", "binding"):
            preparation = AgentPreparation()
            watch = PreparedAgentWatch(REQUEST, preparation=preparation)
            watch.accept(frame)
            bad = copy.deepcopy(frame)
            bad["mesh"]["reader"].update(sequence=2, revision=2)
            with self.subTest(fault=fault), self.assertRaises((ProtocolError, ContractError, ValidationError)):
                if fault == "clock":
                    watch.read(now - 1, clock)
                elif fault == "capacity":
                    with patch("mesh_plus.prepared._CAPACITY", 256):
                        watch.accept(bad)
                elif fault == "binding":
                    from dataclasses import replace
                    object.__setattr__(preparation, "descriptor", replace(preparation.descriptor, implementation_id="changed"))
                    watch.read(now, clock)
                else:
                    if fault == "shape":
                        bad["sessions"][0]["title"] = 123
                    else:
                        bad["mesh"]["requestId"] = "b" * 32
                    watch.accept(bad)
            self.assertIsNone(watch._context)
            if fault != "binding":
                self.assertIsNone(watch.snapshot())
                self.assertFalse(watch.read(now, clock).sessions)
            else:
                with self.assertRaises(ProtocolError):
                    watch.read(now, clock)

    def test_classification_selection_stays_external_and_future_activity_is_preserved(self):
        from mesh_plus.api import ReadGuard

        from agent_observer.mesh_profile import AgentProfile
        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        for row, kind in zip(frame["sessions"], ("user", "child", "system", "unknown"), strict=True):
            row["kind"] = kind
            row["activity"].update(at=4_000_000_000_000, source="fixture_activity", health="current", reason="observed")
        profile = AgentProfile()
        legacy = ReadGuard("agent", REQUEST, profile=profile)
        prepared = PreparedAgentWatch(REQUEST, profile=profile)
        legacy.accept(frame)
        prepared.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        self.assertEqual(prepared.read(now, clock).sessions, legacy.current(now, clock))
        self.assertEqual({r["kind"] for r in prepared.read(now, clock).sessions}, {"user", "child", "system", "unknown"})

    def test_compiler_cancellation_after_baseline_does_not_retain_context(self):
        from agent_observer.mesh_preparation import AgentPreparation
        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        class FailingPreparation:
            def __init__(self):
                self.owner = AgentPreparation()
                self.descriptor = self.owner.descriptor
                self.fail = False

            def prepare_rules(self, state):
                if self.fail:
                    raise asyncio.CancelledError()
                return self.owner.prepare_rules(state)

        preparation = FailingPreparation()
        watch = PreparedAgentWatch(REQUEST, preparation=preparation)
        watch.accept(frame)
        preparation.fail = True
        changed = copy.deepcopy(frame)
        changed["mesh"]["reader"].update(sequence=2, revision=2)
        with self.assertRaises(asyncio.CancelledError):
            watch.accept(changed)
        self.assertIsNone(watch.snapshot())
        self.assertIsNone(watch._context)


@unittest.skipUnless(supported(), "optional prepared Mesh capability not installed")
class PreparedDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_prepared_cli_and_output_failure_close_owned_delivery(self):
        from mesh_native_fixture import CachedPublisher
        from mesh_plus.api import Bridge
        from mesh_plus.transport import IPCServer

        from agent_observer import mesh_cli

        publisher = CachedPublisher()
        with tempfile.TemporaryDirectory(prefix="agent-prepared-cli-") as directory:
            socket = Path(directory) / "read.sock"
            server = await IPCServer(socket, Bridge(publisher).serve).start()
            args = mesh_cli.parser().parse_args(["watch", "--human", "--prepared", "--count", "2",
                                                "--local-host", "fixture", "--socket", str(socket)])
            outputs = []
            try:
                self.assertEqual(await mesh_cli.run(args, human_output=outputs.append), 0)
                self.assertTrue(any("AGE" in output for output in outputs))
                self.assertIn("revoked", outputs[-1])
                def fail(_value):
                    raise OSError("owned_output_failed")
                with self.assertRaisesRegex(OSError, "owned_output_failed"):
                    await mesh_cli.run(args, human_output=fail)
            finally:
                await server.close()
            self.assertEqual(publisher.watchers, 0)

    async def test_owned_ipc_replacement_and_disconnect_preserve_native_raw_context(self):
        from mesh_native_fixture import CachedPublisher
        from mesh_plus.api import Bridge, configured_reader
        from mesh_plus.transport import IPCServer, boottime_ms

        from agent_observer.mesh_read import PreparedAgentWatch

        publisher = CachedPublisher()
        with tempfile.TemporaryDirectory(prefix="agent-prepared-ipc-") as directory:
            socket = Path(directory) / "read.sock"
            server = await IPCServer(socket, Bridge(publisher).serve).start()
            reader = await configured_reader("agent", source="agent", socket=socket,
                                             scope="local", local_host="fixture", profile=publisher.state_profile)
            watch = PreparedAgentWatch(REQUEST, profile=publisher.state_profile)
            stream = reader.watch(request_id=REQUEST, proof_interval=.1)
            try:
                for _ in range(10):
                    frame = await asyncio.wait_for(anext(stream), 2)
                    watch.accept(frame)
                    if watch.read(boottime_ms(), frame["mesh"]["reader"]["clock"]).sessions:
                        break
                self.assertEqual(watch.snapshot()["sessions"], publisher.frame["snapshot"]["sessions"])
                publisher.frame["snapshot"]["sessions"][0]["title"] = "replacement"
                publisher.frame["viewRevision"] += 1
                publisher.changes.put_nowait(True)
                for _ in range(10):
                    frame = await asyncio.wait_for(anext(stream), 2)
                    watch.accept(frame)
                    read = watch.read(boottime_ms(), frame["mesh"]["reader"]["clock"])
                    if read.sessions and read.sessions[0]["title"] == "replacement":
                        break
                self.assertEqual(read.sessions[0]["title"], "replacement")
            finally:
                watch.disconnect()
                await stream.aclose()
                await server.close()
            self.assertIsNone(watch.snapshot())
            self.assertEqual(reader.inspect()["activeConnections"], 0)
            self.assertEqual(publisher.watchers, 0)
