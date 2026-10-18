"""Explicit candidate startup flag and pure schema/interface commands."""

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agent_observer import service_cli
from agent_observer.working_set_contract import interface, schema_document

ROOT = Path(__file__).resolve().parent.parent


class WorkingSetCliTest(unittest.TestCase):
    def test_startup_flag_is_absent_or_one_exact_fixed_window(self):
        for options, expected in (
            ([], None),
            (["--working-set-window-hours"], 259200000),
            (["--working-set-window-hours", "0"], 0),
            (["--working-set-window-hours", "720"], 2592000000),
        ):
            state = Mock()
            with (
                patch(
                    "agent_observer.service_state.ServiceState", return_value=state
                ) as constructor,
                patch("agent_observer.service_runtime.Runtime") as runtime,
                patch.object(service_cli.signal, "signal"),
            ):
                code = service_cli.serve(
                    ["serve", "--host-scope", "fixture", "--provider", "codex", *options]
                )
            self.assertEqual(code, 0)
            runtime.return_value.run.assert_called_once()
            if expected is None:
                self.assertNotIn("working_set_window_ms", constructor.call_args.kwargs)
            else:
                self.assertEqual(constructor.call_args.kwargs["working_set_window_ms"], expected)

    def test_invalid_startup_window_rejects_before_adapter_or_service_setup(self):
        for value in ("-1", "721", "72.5", "true"):
            with (
                patch("agent_observer.adapters.select_adapters") as select,
                patch("agent_observer.service_state.ServiceState") as state,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as error:
                    service_cli.serve(
                        [
                            "serve",
                            "--host-scope",
                            "fixture",
                            "--provider",
                            "codex",
                            "--working-set-window-hours",
                            value,
                        ]
                    )
            self.assertEqual(error.exception.code, 2)
            select.assert_not_called()
            state.assert_not_called()

    def test_interface_and_schema_are_explicit_pure_candidates(self):
        for args, expected in (
            (["working-set-api"], interface()),
            (["working-set-api", "--window-hours", "0"], interface(0)),
            (["working-set-schema", "--kind", "request"], schema_document("request")),
            (["working-set-schema", "--kind", "frame"], schema_document("frame")),
        ):
            output = io.StringIO()
            with (
                patch(
                    "agent_observer.adapters.select_adapters",
                    side_effect=AssertionError("provider setup"),
                ),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(service_cli.main(args), 0)
            self.assertEqual(json.loads(output.getvalue()), expected)
        code = """
import builtins,socket,subprocess,sys
original=builtins.__import__
blocked=('mesh_plus','agent_observer.adapters','agent_observer.provider',
         'agent_observer.collection','agent_observer.service_runtime','agent_observer.service_state')
def guarded(name,*args,**kwargs):
    if name in blocked or name.startswith('mesh_plus.'):
        raise AssertionError(name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('socket'))
subprocess.Popen=lambda *a,**k: (_ for _ in ()).throw(AssertionError('process'))
from agent_observer.service_cli import main
assert main(['working-set-api'])==0
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
