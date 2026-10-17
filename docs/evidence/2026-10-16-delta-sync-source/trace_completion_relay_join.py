"""Test-only KeyError location capture; no producer code modification."""
import json
import runpy
import sys
from pathlib import Path


def trace(frame, event, arg):
    if frame.f_code.co_filename.endswith("/mesh_plus/sync/relay.py") and frame.f_code.co_name == "_changes":
        if event == "exception" and type(arg[1]) is KeyError:
            sys.stderr.write(json.dumps({"diagnostic": "KeyError", "path": frame.f_code.co_filename,
                                         "line": frame.f_lineno, "key": str(arg[1])}) + "\n")
        return trace
    return None


sys.settrace(trace)
runpy.run_path(str(Path(__file__).with_name("verify_completion_relay_join.py")), run_name="__main__")
