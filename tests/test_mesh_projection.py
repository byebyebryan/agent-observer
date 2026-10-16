"""Selection preserves exact identity and uncertainty; it adds no native facts."""

import copy
import asyncio
import importlib.util
import json
import tempfile
import unittest
import uuid
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from agent_observer.contract import ContractError
from agent_observer.mesh_selection import AgentSelection, summarize


class AgentSelectionTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads((Path(__file__).parent / "fixtures/service-v4/view.json").read_text())["snapshot"]["sessions"][0]

    def test_explicit_running_filter_includes_unknown_kind_but_preserves_positive_exclusions(self):
        selection = AgentSelection(providers=frozenset({"codex"}), kinds=frozenset({"user", "unknown"}),
                                   runtime_values=frozenset({"running"}), runtime_healths=frozenset({"current"}))
        for kind, value, health, selected in (
            ("user", "running", "current", True),
            ("unknown", "running", "current", True),
            ("child", "running", "current", False),
            ("system", "running", "current", False),
            ("user", "parked", "current", False),
            ("user", "unknown", "current", False),
            ("user", "unknown", "unavailable", False),
        ):
            with self.subTest(kind=kind, value=value, health=health):
                row = copy.deepcopy(self.row)
                row["kind"] = kind
                row["runtime"].update(value=value, health=health)
                summary = summarize(row)
                self.assertIs(selection.matches(summary), selected)
                self.assertEqual((summary.kind, summary.runtime_value, summary.runtime_health), (kind, value, health))

    def test_full_identity_is_detached_and_default_selection_keeps_every_kind(self):
        original = copy.deepcopy(self.row["identity"])
        summary = summarize(self.row)
        self.row["identity"]["nativeId"] = "changed"
        self.assertEqual(summary.identity, tuple(original[k] for k in
                         ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")))
        with self.assertRaises(FrozenInstanceError):
            summary.kind = "child"
        self.assertTrue(AgentSelection().matches(summary))
        self.assertFalse(AgentSelection(providers=frozenset()).matches(summary))
        self.assertFalse(AgentSelection(providers=frozenset({"claude"})).matches(summary))

    def test_mutable_or_unsupported_filter_values_fail_explicitly(self):
        for name, value in (("providers", {"codex"}), ("kinds", frozenset({"guessed"})),
                            ("runtime_values", frozenset({"idle"})), ("runtime_healths", ("current",))):
            with self.subTest(name=name), self.assertRaisesRegex(ContractError, "agent_selection"):
                AgentSelection(**{name: value})


def selection_supported():
    if not importlib.util.find_spec("mesh_plus"):
        return False
    from mesh_plus import api
    return getattr(api, "SELECTION_INTERFACE_VERSION", None) == 1


@unittest.skipUnless(selection_supported(), "optional Mesh selection capability not installed")
class SelectedWatchTests(unittest.TestCase):
    def selection(self):
        return AgentSelection(providers=frozenset({"codex"}), kinds=frozenset({"user", "unknown"}),
                              runtime_values=frozenset({"running"}), runtime_healths=frozenset({"current"}))

    def test_incompatible_mesh_capability_and_mutable_selector_fail_before_use(self):
        from mesh_plus import api
        from mesh_plus.protocol import ProtocolError

        from agent_observer.mesh_read import PreparedAgentWatch

        with patch.object(api, "SELECTION_INTERFACE_VERSION", 2):
            with self.assertRaisesRegex(ProtocolError, "mesh_prepared_read_incompatible"):
                PreparedAgentWatch("a" * 32)
        with self.assertRaisesRegex(ProtocolError, "agent_selection"):
            PreparedAgentWatch("a" * 32, selection={"providers": ["codex"]})

    def test_golden_partial_hosts_and_each_expiry_match_independent_full_read(self):
        from mesh_plus.api import ReadGuard
        from test_mesh_preparation import REQUEST, golden_frames

        from agent_observer.mesh_profile import AgentProfile
        from agent_observer.mesh_read import PreparedAgentWatch

        selection = self.selection()
        for name, frame in golden_frames():
            with self.subTest(case=name):
                profile = AgentProfile()
                full = ReadGuard("agent", REQUEST, profile=profile)
                watch = PreparedAgentWatch(REQUEST, profile=profile, selection=selection)
                full.accept(frame)
                watch.accept(frame)
                clock = frame["mesh"]["reader"]["clock"]
                boundaries = {frame["mesh"]["reader"]["encodedAtMs"]}
                boundaries.update(r["expiresAtMs"] for h in frame["mesh"]["hosts"]
                                  for r in h["receipts"] if r["expiresAtMs"] is not None)
                for now in sorted(boundaries):
                    expected = full.current(now, clock)
                    result = watch.read(now, clock)
                    self.assertEqual(result.summaries, tuple(map(summarize, expected)))
                    self.assertEqual(result.sessions, [r for r in expected if selection.matches(summarize(r))])
                    self.assertEqual(result.context, frame["mesh"])
                self.assertEqual(watch.snapshot(), frame)

    def test_whole_roster_summaries_beyond_32_and_warm_reads_never_decode_rejected_bodies(self):
        from mesh_plus import prepared
        from mesh_plus.protocol import encode
        from test_mesh_preparation import REQUEST, control, golden_frames

        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        template = frame["sessions"][0]
        frame["sessions"] = []
        for index in range(85):
            row = copy.deepcopy(template)
            identity = str(uuid.UUID(int=index + 1))
            row["identity"]["nativeId"] = identity
            row["nativeIds"].update(threadId=identity, sessionTreeRootId=identity)
            row["hasSavedHistory"] = True
            row["kind"] = ("user", "unknown", "child", "system", "user")[index % 5]
            if index % 5 == 4:
                row["runtime"]["value"] = "parked"
                row["phase"] = None
                row["blockedReasons"] = []
            frame["sessions"].append(row)
        original = copy.deepcopy(frame)
        selection = self.selection()
        watch = PreparedAgentWatch(REQUEST, selection=selection)
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        result = watch.read(now, clock)
        self.assertEqual(len(result.summaries), 85)
        self.assertEqual(len(result.sessions), 34)
        self.assertEqual(sum(s.kind in {"child", "system"} or s.runtime_value == "parked"
                             for s in result.summaries), 51)
        rejected = {encode(row) for row in original["sessions"] if not selection.matches(summarize(row))}
        decode = prepared.decode_json
        def selected_only(payload, *args, **kwargs):
            self.assertNotIn(payload, rejected, "warm read decoded an unselected native body")
            return decode(payload, *args, **kwargs)
        frame["sessions"].clear()
        result.sessions[0]["title"] = "changed"
        result.context["hosts"].clear()
        with patch.object(prepared, "decode_json", side_effect=selected_only):
            current = watch.read(now, clock)
        self.assertEqual(current.summaries, tuple(map(summarize, original["sessions"])))
        self.assertEqual(current.sessions[0]["title"], original["sessions"][0]["title"])
        watch.accept(control(original, "heartbeat", 2))
        self.assertEqual(watch.read(now, clock).summaries, current.summaries)
        watch.accept(control(original, "gap", 3))
        retired = watch.read(now, clock)
        self.assertIsNone(retired.context)
        self.assertEqual((retired.sessions, retired.summaries), ([], ()))
        resync = copy.deepcopy(original)
        resync["mesh"]["kind"] = "resync"
        resync["mesh"]["reader"].update(sequence=4, revision=2)
        watch.accept(resync)
        self.assertEqual(len(watch.read(now, clock).summaries), 85)
        watch.disconnect()
        self.assertEqual(watch.read(now, clock).summaries, ())

    def test_selection_failure_revokes_retained_context_and_rows(self):
        from mesh_plus.protocol import ProtocolError
        from test_mesh_preparation import REQUEST, golden_frames

        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        watch = PreparedAgentWatch(REQUEST, selection=self.selection())
        watch.accept(frame)
        now, clock = frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"]
        with self.assertRaises(ProtocolError):
            watch.read(now, {**clock, "bootId": "foreign"})
        self.assertIsNone(watch.snapshot())
        self.assertIsNone(watch._context)

    def test_failed_outcome_and_retry_remain_lossless_selected_native_facts(self):
        from test_mesh_preparation import REQUEST, golden_frames

        from agent_observer.mesh_read import PreparedAgentWatch

        frame = dict(golden_frames())["agent-local"]
        row = frame["sessions"][0]
        row["phase"].update(value="unknown", health="unsupported", reason="native_runtime_error")
        row["blockedReasons"] = []
        row["outcome"].update(value="failed", health="current", observedAt=1700000020000,
                              source="codex_turn_metadata", clock="native", reason="latest_terminal_turn")
        watch = PreparedAgentWatch(REQUEST, selection=self.selection())
        for retry in (False, True):
            if retry:
                frame["mesh"]["reader"].update(sequence=2, revision=2)
                host = frame["mesh"]["hosts"][0]
                host["owner"]["metadata"]["sources"][0]["capabilities"]["timing"]["latestTurn"] = True
                row["latestTurn"].update(
                    value={"id": "retry", "status": "in_progress", "startedAt": 1700000020000,
                           "completedAt": None, "durationMs": None, "timestampPrecisionMs": 1000},
                    health="current", source="codex_rpc", observedAt=1700000020000, reason="native_latest_turn",
                    receipt={"component": "runtime", "sampledBoottimeMs": 100,
                             "observedBoottimeMs": 100, "contextGeneration": 1})
            watch.accept(frame)
            result = watch.read(frame["mesh"]["reader"]["encodedAtMs"], frame["mesh"]["reader"]["clock"])
            self.assertEqual(result.sessions, [row])
            self.assertEqual(result.sessions[0]["outcome"]["value"], "failed")


@unittest.skipUnless(selection_supported(), "optional Mesh selection capability not installed")
class OwnedSelectedDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_admission_from_real_reader_and_export_mutation_cleanup(self):
        from mesh_native_fixture import CachedPublisher
        from mesh_plus.api import AdmittedResponse, Bridge, configured_reader
        from mesh_plus.evidence import clock_domain
        from mesh_plus.transport import IPCServer, boottime_ms
        from test_mesh_preparation import REQUEST

        from agent_observer.mesh_read import PreparedAgentWatch

        publisher = CachedPublisher()
        profile = publisher.state_profile
        with tempfile.TemporaryDirectory(prefix="agent-owned-selection-") as directory:
            socket = Path(directory) / "read.sock"
            server = await IPCServer(socket, Bridge(publisher).serve).start()
            reader = await configured_reader("agent", source="agent", socket=socket,
                                             scope="local", local_host="fixture", profile=profile)
            watch = PreparedAgentWatch(REQUEST, profile=profile, selection=AgentSelection())
            stream = reader.watch_admitted(request_id=REQUEST, proof_interval=.1)
            try:
                for _ in range(10):
                    frame = await asyncio.wait_for(anext(stream), 2)
                    watch.accept(frame)
                    read = watch.read(boottime_ms(), clock_domain())
                    if read.sessions:
                        break
                self.assertIsInstance(frame, AdmittedResponse)
                original = frame.snapshot()
                original["sessions"].clear()
                self.assertEqual(watch.snapshot(), frame.snapshot())
                self.assertEqual(read.summaries, tuple(map(summarize, read.sessions)))
            finally:
                watch.disconnect()
                await stream.aclose()
                await server.close()
            self.assertEqual(reader.inspect()["activeConnections"], 0)
            self.assertEqual(publisher.watchers, 0)
            self.assertIsNone(watch.snapshot())
