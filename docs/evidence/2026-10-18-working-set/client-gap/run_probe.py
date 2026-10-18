"""Replay nonterminal facade watermarks without SDK registration or fake guards."""

import argparse
import gc
import hashlib
import json
import sys
import unittest
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
parser.add_argument("mesh_src", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--before", action="store_true")
args = parser.parse_args()
root, mesh = args.root.resolve(), args.mesh_src.resolve()
sys.path[:0] = [str(root), str(root / "tests"), str(mesh)]
gc.disable()
name = "test_mesh_working_set_read.WorkingSetGapPolicyTest"
if args.before:
    methods = (
        "test_gap_cannot_reauthorize_expired_row_with_regressed_native_clock",
        "test_no_generation_read_keeps_scope_continuity_without_row_history",
        "test_reader_time_cannot_regress_during_or_after_gap",
    )
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name + "." + method)
                               for method in methods)
else:
    suite = unittest.defaultTestLoader.loadTestsFromName(name)
result = unittest.TextTestRunner(verbosity=2).run(suite)
loaded = {}
for module_name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if filename is None:
        continue
    path = Path(filename).resolve()
    for label, directory in (("observer", root), ("mesh", mesh)):
        if path.suffix == ".py" and path.is_relative_to(directory):
            loaded[module_name] = {
                "repo": label, "path": str(path.relative_to(directory)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            break
args.output.write_text(json.dumps({
    "python": sys.version.split()[0], "gcEnabled": gc.isenabled(),
    "testsRun": result.testsRun, "failures": len(result.failures),
    "errors": len(result.errors), "skips": len(result.skipped),
    "expectedBeforeFailure": args.before, "loadedProjectModules": loaded,
    "scope": "native-admitted synthetic frames/direct translated headers; pure Observer policy only, no SDK guard/proof/transport/provider acceptance",
}, sort_keys=True, indent=2) + "\n")
success = (result.testsRun == 3 and len(result.failures) == 4 and not result.errors
           if args.before else result.testsRun == 5 and result.wasSuccessful())
raise SystemExit(0 if success and not result.skipped else 1)
