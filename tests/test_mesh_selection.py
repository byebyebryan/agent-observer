"""Real owned process checks; no normal services or rollback targets are touched."""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class MeshSelectionTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "scripts/mesh-selection-acceptance"
        loader = importlib.machinery.SourceFileLoader("mesh_selection_gate", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.module = importlib.util.module_from_spec(spec)
        loader.exec_module(self.module)

    def test_separate_reader_bridge_authentication_and_foreign_arguments(self):
        with tempfile.TemporaryDirectory(prefix="observer-mesh-unit-") as name:
            home = Path(name)
            relative = ".local/share/agent-observer/bridge"
            prefix = home / relative / "bin"
            prefix.mkdir(parents=True)
            (prefix / "python").symlink_to(sys.executable)
            entry = prefix / "mesh-plus"
            entry.write_text("import time\ntime.sleep(30)\n")
            value = {"readerPrefix": ".local/share/agent-observer/reader",
                     "bridgeSelection": {"readerPrefix": relative},
                     "unit": "fixture.service", "source": "agent", "socket": "fixture/read.sock"}
            endpoint = Path(f"/run/user/{os.getuid()}") / value["socket"]
            child = subprocess.Popen([str(prefix / "python"), str(entry), "serve", "--source", "agent",
                                      "--socket", str(endpoint)])
            try:
                deadline = time.monotonic() + 2
                while os.fsencode(entry) not in Path(f"/proc/{child.pid}/cmdline").read_bytes():
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
                with patch.object(self.module, "run", return_value=str(child.pid).encode()) as run:
                    identity = self.module.bridge_identity(value, home)
                    self.module.same_bridge(value, home, identity)
                    for changed in (
                        {**value, "bridgeSelection": {"readerPrefix": value["readerPrefix"]}},
                        {**value, "source": "foreign"}, {**value, "socket": "foreign/read.sock"},
                    ):
                        with self.assertRaisesRegex(ValueError, "^selection_foreign_unit$"):
                            self.module.bridge_identity(changed, home)
                    with self.assertRaisesRegex(ValueError, "^selection_unit_changed$"):
                        self.module.same_bridge(value, home, {**identity, "startTicks": "different"})
                    run.assert_called_with(["systemctl", "--user", "show", value["unit"], "-p", "MainPID", "--value"])
                    self.assertNotIn("stop", str(run.call_args_list))
                unified = {**value, "readerPrefix": relative}
                del unified["bridgeSelection"]
                with patch.object(self.module, "run", return_value=str(child.pid).encode()):
                    self.assertEqual(self.module.bridge_identity(unified, home), identity)
                with patch.object(self.module, "run", side_effect=[str(child.pid).encode(), b"1"]):
                    with self.assertRaisesRegex(ValueError, "^selection_unit_changed$"):
                        self.module.bridge_identity(value, home)
            finally:
                child.terminate()
                child.wait(timeout=5)

    def test_invalid_prefix_and_inactive_unit_reject_before_mutation(self):
        value = {"readerPrefix": ".local/share/agent-observer/reader", "unit": "fixture.service"}
        for prefix in ("/tmp/foreign", ".local/share/agent-observer/../foreign"):
            with self.subTest(prefix=prefix), patch.object(self.module, "run") as run:
                with self.assertRaisesRegex(ValueError, "^selection_bridge_prefix$"):
                    self.module.bridge_identity({**value, "bridgeSelection": {"readerPrefix": prefix}}, Path("/tmp"))
                run.assert_not_called()
        with patch.object(self.module, "run", return_value=b"0"):
            with self.assertRaisesRegex(ValueError, "^selection_unit_inactive$"):
                self.module.bridge_identity(value, Path("/tmp"))
