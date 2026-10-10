"""Read-client boundary and optional SDK admission/cleanup checks."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer import mesh_cli
from agent_observer.read_client import human_snapshots, ordered_snapshots

ROOT = Path(__file__).resolve().parents[1]


class MeshClientTest(unittest.TestCase):
    def test_descriptors_and_help_without_network_provider_or_optional_imports(self):
        result = subprocess.run([sys.executable, "-I", "-c", """
import sys
sys.path.insert(0, sys.argv[1])
from agent_observer.cli import main
assert main(['mesh', 'api']) == 0
assert not any(name.startswith('mesh_plus') for name in sys.modules)
assert not any(name in sys.modules for name in (
 'agent_observer.collection', 'agent_observer.service_runtime',
 'agent_observer.write_client', 'agent_observer.codex_snapshot',
 'agent_observer.claude_snapshot'))
""", str(ROOT)], check=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout), mesh_cli.interface())

    def test_missing_optional_dependency_fails_explicitly(self):
        result = subprocess.run([sys.executable, "-I", "-c", """
import sys
sys.path.insert(0, sys.argv[1])
class Block:
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith('mesh_plus'): raise ImportError('private path')
sys.meta_path.insert(0, Block())
from agent_observer.cli import main
raise SystemExit(main(['mesh', 'snapshot', '--local-host', 'fixture']))
""", str(ROOT)], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(json.loads(result.stderr)["error"], "mesh_dependency_unavailable")
        self.assertNotIn(b"private path", result.stderr)

    def test_invalid_selection_or_raw_filters_fail_before_optional_reads(self):
        for args in (["snapshot", "--hosts", "snap"],
                     ["snapshot", "--scope", "hosts", "--hosts", "snap", "snap"],
                     ["watch", "--count", "0"], ["watch", "--provider", "codex"]):
            with self.subTest(args=args), patch("agent_observer.mesh_cli.run") as run:
                with self.assertRaises(SystemExit), patch("sys.stderr"):
                    mesh_cli.main(args)
                run.assert_not_called()

    def test_cross_host_urgency_age_and_child_filter_are_presentation_only(self):
        first = json.loads((ROOT / "tests/fixtures/contract-v4/snapshot.json").read_text())
        second = copy.deepcopy(first)
        second["host"]["authority"] = "other"
        for row in second["sessions"]:
            row["identity"]["hostScope"] = "other"
        first["sessions"][0]["kind"] = "child"
        before = copy.deepcopy([first, second])
        rows = ordered_snapshots([first, second])
        self.assertEqual(rows[0]["identity"]["hostScope"], "other")
        self.assertEqual(rows[0]["phase"]["value"], "blocked")
        display = human_snapshots([first, second], now_ms=1700000030000)
        self.assertIn("AGE", display)
        self.assertIn("unknown", display)
        self.assertEqual([first, second], before)

    def test_gap_and_heartbeat_do_not_claim_current_rows(self):
        self.assertIn("revoked", mesh_cli.human_view({"mesh": {"kind": "gap"}}, [], reconstruct=None))
        self.assertIn("unchanged", mesh_cli.human_view({"mesh": {"kind": "heartbeat"}}, [], reconstruct=None))


@unittest.skipUnless(importlib.util.find_spec("mesh_plus"), "optional Mesh SDK not installed")
class OptionalMeshSDKTest(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, *, watch=False, wrong_request=False, fail_output=False):
        from mesh_plus.protocol import ProtocolError
        from mesh_plus.reader import Endpoint, Reader

        args = mesh_cli.parser().parse_args(["watch" if watch else "snapshot", "--local-host", "fixture"])
        args.count = 1
        sdk = Reader("agent", [Endpoint("fixture", True, None, None)], local_host="fixture")
        closed, outputs, policies = [], [], []

        class FakeReader:
            async def execute(self, request):
                try:
                    frame = sdk.compose(sdk.endpoints, {"fixture": (sdk.unavailable(sdk.endpoints[0]), [])},
                                        "0" * 32 if wrong_request else request["requestId"], request["operation"])
                    yield frame
                    raise AssertionError("consumer should close after count")
                finally:
                    closed.append(True)

        async def configured(*args, **kwargs):
            policies.append(kwargs)
            return FakeReader()

        def output(frame):
            outputs.append(frame)
            if fail_output:
                raise OSError("output closed")

        with patch("mesh_plus.configured_read.configured_reader", configured):
            if wrong_request or fail_output:
                with self.assertRaises(ProtocolError if wrong_request else OSError):
                    await mesh_cli.run(args, output=output)
            else:
                self.assertEqual(await mesh_cli.run(args, output=output), 1)
        self.assertEqual(closed, [True])
        self.assertFalse(policies[0]["report_routes"])
        self.assertEqual(len(outputs), 0 if wrong_request else 1)

    async def test_snapshot_validates_identity_and_closes_owned_stream(self):
        await self.exercise()
        await self.exercise(wrong_request=True)

    async def test_watch_count_invalid_binding_and_output_failure_close_stream(self):
        await self.exercise(watch=True)
        await self.exercise(watch=True, wrong_request=True)
        await self.exercise(watch=True, fail_output=True)
