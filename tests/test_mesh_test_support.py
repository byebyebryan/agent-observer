"""Optional SDK absence skips tests; broken supported integrations must fail."""

import io
import runpy
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from mesh_test_support import WORKING_SET_PROFILE, require_working_set_sdk


class SDKError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class MeshTestSupportTests(unittest.TestCase):
    def sdk(self, descriptor):
        api = ModuleType("mesh_plus.api")
        api.descriptor = descriptor
        protocol = ModuleType("mesh_plus.protocol")
        protocol.ProtocolError = SDKError
        return patch.dict(sys.modules, {"mesh_plus.api": api, "mesh_plus.protocol": protocol})

    def test_missing_optional_sdk_skips(self):
        with patch("mesh_test_support.importlib.util.find_spec", return_value=None):
            with self.assertRaisesRegex(unittest.SkipTest, "not installed"):
                require_working_set_sdk()

    def test_registered_profile_runs(self):
        def descriptor(kind, *, profile_id):
            self.assertEqual((kind, profile_id), ("agent", WORKING_SET_PROFILE))
            return object()

        with self.sdk(descriptor), patch("mesh_test_support.importlib.util.find_spec", return_value=object()):
            self.assertIs(require_working_set_sdk(), True)

    def test_only_missing_profile_skips(self):
        for code in ("profile_descriptor", "broken_schema"):
            def descriptor(_kind, *, profile_id, code=code):
                raise SDKError(code)

            with self.subTest(code=code), self.sdk(descriptor), patch(
                "mesh_test_support.importlib.util.find_spec", return_value=object()
            ):
                expected = unittest.SkipTest if code == "profile_descriptor" else SDKError
                with self.assertRaises(expected):
                    require_working_set_sdk()

    def test_unexpected_descriptor_failure_is_not_skipped(self):
        def descriptor(_kind, *, profile_id):
            raise RuntimeError("broken_descriptor")

        with self.sdk(descriptor), patch("mesh_test_support.importlib.util.find_spec", return_value=object()):
            with self.assertRaisesRegex(RuntimeError, "broken_descriptor"):
                require_working_set_sdk()

    def test_required_pair_cannot_succeed_by_skipping(self):
        module = ModuleType("agent_observer.mesh_working_set_profile")

        def missing_profile():
            raise ValueError("profile_descriptor")

        module.WorkingSetAgentProfile = missing_profile
        check = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "check"))
        stderr = io.StringIO()
        with patch.dict(sys.modules, {module.__name__: module}), patch("sys.stderr", stderr):
            self.assertEqual(check["main"](["--require-working-set-mesh"]), 1)
        self.assertIn("needs a compatible SDK", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
