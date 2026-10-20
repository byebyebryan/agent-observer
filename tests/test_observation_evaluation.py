"""Reference-comparison decisions; no provider runtime or payload fixtures."""

import copy
import importlib.machinery
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    "independent_observation_evaluation",
    str(Path(__file__).parent.parent / "scripts/evaluate-observation"),
)
spec = importlib.util.spec_from_loader(loader.name, loader)
evaluation = importlib.util.module_from_spec(spec)
loader.exec_module(evaluation)

SID = "01234567-0123-4567-89ab-0123456789ab"


class ObservationEvaluationTest(unittest.TestCase):
    def child_client(self, *, loaded, catalog_root=SID, detail_root=None, status="idle", detail_fields=None):
        root = "21234567-0123-4567-89ab-0123456789ab"
        source = {"subAgent": {"thread_spawn": {"parent_thread_id": root}}}
        class Client:
            pid, start, artifact = 123, "456", {}
            def pages(self, method):
                return ([SID] if loaded else []) if method == "thread/loaded/list" else [
                    {"id": SID, "sessionId": catalog_root, "source": source,
                     "threadSource": "subagent", "status": {"type": "idle"}}
                ]
            def call(self, method, params):
                if method == "thread/read":
                    return {"thread": {
                        "id": SID, "sessionId": detail_root or root, "source": source,
                        "threadSource": "subagent", "status": {"type": status},
                        **(detail_fields or {}),
                    }}
                return {"data": []}
        return Client()

    def test_current_child_reference_uses_detail_root_not_catalog_placeholder(self):
        for loaded in (True, False):
            with self.subTest(loaded=loaded), patch.object(evaluation, "birth", return_value=("456", "S", 1)):
                result = evaluation.codex_reference(self.child_client(loaded=loaded))
                row = result["rows"][SID]
                self.assertEqual(row["sessionTreeRootId"], "21234567-0123-4567-89ab-0123456789ab")
                self.assertEqual(row["kind"], "child")
                self.assertEqual(row["runtime"], "running")
                self.assertTrue(row["hasSavedHistory"])

    def test_reference_does_not_accept_other_tree_disagreements(self):
        for loaded in (True, False):
            for fields in ({"catalog_root": "11234567-0123-4567-89ab-0123456789ab"},
                           {"status": "notLoaded"}, {"status": "futureState"},
                           {"detail_fields": {"id": "11234567-0123-4567-89ab-0123456789ab"}},
                           {"detail_fields": {"sessionId": "malformed"}},
                           {"detail_fields": {"threadSource": "user"}},
                           {"detail_fields": {"source": {"subAgent": {"thread_spawn": {
                               "parent_thread_id": "malformed",
                           }}}}}):
                with self.subTest(loaded=loaded, **fields), patch.object(evaluation, "birth", return_value=("456", "S", 1)):
                    with self.assertRaisesRegex(ValueError, "native_detail_identity_conflict"):
                        evaluation.codex_reference(self.child_client(loaded=loaded, **fields))

    def test_catalog_status_cannot_supply_readable_saved_identity(self):
        for status, expected in (("idle", "running"), ("notLoaded", "unknown")):
            with self.subTest(status=status):
                class Client:
                    pid, start, artifact = 123, "456", {}
                    def pages(self, method, status=status):
                        return [] if method == "thread/loaded/list" else [
                            {"id": SID, "sessionId": SID, "source": "vscode",
                             "threadSource": "user", "status": {"type": status}}
                        ]
                    def call(self, method, params):
                        if method == "thread/read":
                            raise ValueError("native_read_failed")
                        return {"data": []}
                with patch.object(evaluation, "birth", return_value=("456", "S", 1)):
                    row = evaluation.codex_reference(Client())["rows"][SID]
                self.assertEqual(row["runtime"], expected)
                self.assertFalse(row["hasSavedHistory"])

    def test_saved_native_reference_reads_metadata_only_and_checks_identity(self):
        class Client:
            pid, start, artifact = 123, "456", {}
            def __init__(self):
                self.calls = []
                self.returned_id = SID
            def pages(self, method):
                self.calls.append((method, {}))
                return [] if method == "thread/loaded/list" else [{"id": SID, "sessionId": SID, "source": "vscode"}]
            def call(self, method, params):
                self.calls.append((method, params))
                if method == "thread/read":
                    return {"thread": {"id": self.returned_id, "sessionId": SID, "source": "vscode", "threadSource": "user"}}
                return {"data": []}
        client = Client()
        with patch.object(evaluation, "birth", return_value=("456", "S", 1)):
            result = evaluation.codex_reference(client)
            self.assertEqual(result["rows"][SID]["kind"], "user")
            self.assertEqual(result["rows"][SID]["runtime"], "unknown")
            self.assertEqual(result["loaded"], result["loadedAfter"])
            self.assertIn(("thread/read", {"threadId": SID, "includeTurns": False}), client.calls)
            client.returned_id = "11234567-0123-4567-89ab-0123456789ab"
            with self.assertRaisesRegex(ValueError, "native_detail_identity_conflict"):
                evaluation.codex_reference(client)

    def scoped_snapshot(self, codex_home=None):
        sources, sessions = [], []
        for provider, suffix, native_kind in (("codex", ".codex", "thread"), ("claude", ".claude", "session")):
            home = str(
                codex_home if provider == "codex" and codex_home is not None
                else Path.home() / suffix
            )
            selector = "explicit"
            namespace = "sha256:" + evaluation.hashlib.sha256(json.dumps(
                [provider, home, selector, os.getuid()], separators=(",", ":")
            ).encode()).hexdigest()
            sources.append({"provider": provider, "configHome": home,
                            "configHomeKind": selector, "namespace": namespace})
            sessions.append({"identity": {"provider": provider, "hostScope": "fixture",
                                          "namespace": namespace, "nativeIdKind": native_kind,
                                          "nativeId": SID}})
        return {"host": {"authority": "fixture", "nativeHostname": evaluation.socket.gethostname(),
                         "uid": os.getuid()}, "sources": sources, "sessions": sessions}

    def test_single_provider_native_reference_validates_all_cached_frame_scopes(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider):
                result = evaluation.identity_scope(self.scoped_snapshot(), "fixture", [provider])
                self.assertTrue(result["hostProvenance"])
                self.assertTrue(result["storeScopes"])
                self.assertTrue(result["fullRowReferences"])
                self.assertEqual(result["rowsChecked"], 2)
                self.assertEqual(result["providersChecked"], ["claude", "codex"])
                self.assertEqual(result["nativeReferenceProviders"], [provider])

    def test_codex_home_override_is_the_exact_identity_scope(self):
        selected_home = Path("/fixture/codex-work")
        snapshot = self.scoped_snapshot(codex_home=selected_home)
        self.assertTrue(
            evaluation.identity_scope(
                snapshot, "fixture", ["codex"], codex_home=selected_home
            )["storeScopes"]
        )
        self.assertFalse(
            evaluation.identity_scope(snapshot, "fixture", ["codex"])["storeScopes"]
        )

    def test_evaluator_parser_keeps_default_and_accepts_explicit_codex_home(self):
        parser = evaluation.build_parser()
        base = ["--host-scope", "fixture", "--provider", "codex"]
        self.assertEqual(
            parser.parse_args(base).codex_home,
            Path.home() / ".codex",
        )
        selected_home = Path("/fixture/codex-work")
        self.assertEqual(
            parser.parse_args([*base, "--codex-home", str(selected_home)]).codex_home,
            selected_home,
        )

    def test_main_uses_selected_home_for_native_rpc_and_direct_cli_scope(self):
        selected_home = Path("/fixture/codex-work")
        constructed = []
        invocations = []
        sample = {
            "collectedAt": 1,
            "sourceHealth": "current",
            "errors": [],
            "sources": [],
            "sessions": [],
        }

        class Native:
            def __init__(self, home, reference_sha256=None):
                constructed.append((home, reference_sha256))

            def close(self):
                pass

        def cli_call(_cli, argv, _input=None):
            invocations.append(list(argv))
            return b"agent-observer fixture\n" if argv == ["--version"] else json.dumps(sample).encode()

        native_result = {
            "sampleAt": 1,
            "rows": {},
            "runtime": {},
        }
        stdout = io.StringIO()
        with patch.object(evaluation, "NativeRPC", Native), \
             patch.object(evaluation, "cli_call", side_effect=cli_call), \
             patch.object(evaluation, "codex_reference", return_value=native_result), \
             patch.object(evaluation, "compare", return_value={}), \
             patch.object(evaluation, "identity_scope", return_value={}), \
             patch.object(evaluation, "read_client_checks", return_value={}), \
             patch.dict(os.environ, {"CODEX_HOME": "/fixture/ambient-home"}), \
             patch("sys.stdout", stdout):
            evaluation.main([
                "--host-scope", "fixture", "--provider", "codex",
                "--codex-home", str(selected_home), "--rounds", "1",
            ])

        self.assertEqual(constructed, [(selected_home, None)])
        snapshot_call = next(argv for argv in invocations if argv and argv[0] == "snapshot")
        self.assertEqual(snapshot_call[-2:], ["--codex-home", str(selected_home)])
        self.assertEqual(invocations[-1], ["--version"])

    def test_uncompared_provider_scope_is_not_implicitly_trusted(self):
        baseline = self.scoped_snapshot()
        cases = [
            lambda v: v["sessions"][1]["identity"].update(namespace="sha256:" + "f" * 64),
            lambda v: v["sessions"][1]["identity"].update(hostScope="foreign"),
            lambda v: v["sources"][1].update(configHome="/tmp/another-store"),
            lambda v: v["sources"].append(copy.deepcopy(v["sources"][1])),
            lambda v: v["sources"].append({"provider": "unsupported"}),
            lambda v: v["sessions"].append(copy.deepcopy(v["sessions"][1])),
            lambda v: v["sources"].pop(),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                value = copy.deepcopy(baseline)
                mutate(value)
                result = evaluation.identity_scope(value, "fixture", ["codex"])
                self.assertFalse(result["storeScopes"] and result["fullRowReferences"])

    def native(self, **fields):
        row = {"title": "Native title", "cwd": "/tmp/project", "runtime": "running", "phase": "working", "activity": 100, "kind": "user", "sessionTreeRootId": SID, "blockedReasons": [], "createdAt": 50, "hasSavedHistory": True, "lastUpdated": None, "latestTurn": None}
        return {"rows": {SID: {**row, **fields}}}

    def public(self, **fields):
        row = {"identity": {"provider": "codex", "nativeId": SID}, "title": "Native title", "cwd": "/tmp/project", "runtime": {"value": "running"}, "phase": {"value": "working"}, "activity": {"at": 100}, "kind": "user", "nativeIds": {"sessionTreeRootId": SID}, "blockedReasons": [], "createdAt": 50, "hasSavedHistory": True, "outcome": {"value": "unknown", "observedAt": None}, "lastUpdated": {"at": None}, "latestTurn": {"value": None}}
        return {"sessions": [{**row, **fields}]}

    def test_runtime_only_missing_clock_is_unknown_and_remains_unproved(self):
        native = self.native(hasSavedHistory=False, activity=None, createdAt=None)
        public = self.public(hasSavedHistory=False, activity={"at": None}, createdAt=500)
        result = evaluation.compare(native, public, native, "codex")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["checks"]["activity_unproved"], 1)
        self.assertEqual(result["checks"]["createdAt_unproved"], 1)
        invented = self.public(hasSavedHistory=False, activity={"at": 500})
        result = evaluation.compare(native, invented, native, "codex")
        self.assertTrue(any(i["field"] == "activity" for i in result["issues"]))

    def test_stable_missing_row_and_native_active_inventory_are_retained(self):
        result = evaluation.compare(self.native(), {"sessions": []}, self.native(), "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "membership", "result": "missing_cli_row"}])
        self.assertEqual(result["nativeActive"][0]["id"], SID)

    def test_changed_native_phase_is_a_race_not_a_projection_mismatch(self):
        result = evaluation.compare(self.native(), self.public(), self.native(phase="waiting"), "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "phase", "result": "sampling_race"}])
        result = evaluation.compare(self.native(phase="waiting"), self.public(), self.native(phase="waiting"), "codex")
        self.assertEqual(result["issues"][0]["result"], "mismatch")

    def test_positive_parked_compares_null_phase_without_loaded_membership(self):
        native = self.native(runtime="parked", phase=None)
        public = self.public(runtime={"value": "parked"}, phase=None)
        result = evaluation.compare(native, public, native, "codex")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["checks"]["runtime"], 1)
        self.assertEqual(result["checks"]["phase"], 1)

    def test_public_only_row_is_unproved_without_double_counting_a_race(self):
        result = evaluation.compare({"rows": {}}, self.public(), {"rows": {}}, "codex")
        self.assertEqual(result["issues"], [{"id": SID, "field": "membership", "result": "cli_only_unproved", "runtime": "running"}])

    def test_inactive_unknown_phase_and_recent_cwd_are_distinct_semantics(self):
        native = self.native(runtime=None, phase=None, latestConversationCwd="/tmp/project/worktree")
        public = self.public(runtime={"value": "unknown"}, phase={"value": "unknown"})
        result = evaluation.compare(native, public, native, "codex")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["contextDifferences"][0]["recordedCwd"], "/tmp/project")

    def test_reference_never_dispatches_session_or_content_operations(self):
        client = evaluation.NativeRPC.__new__(evaluation.NativeRPC)
        for method, params in (("thread/resume", {}), ("thread/start", {}), ("thread/read", {"includeTurns": True}), ("thread/turns/list", {"itemsView": "loaded"})):
            with self.subTest(method=method), self.assertRaises(ValueError):
                client.call(method, params)
