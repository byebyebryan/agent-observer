"""Exercise refusal ownership without provider work or default-cap overclaims."""

import argparse
import gc
import hashlib
import json
import sys
import unittest
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--before", action="store_true")
args = parser.parse_args()
root = args.root.resolve()
sys.path[:0] = [str(root), str(root / "tests")]
gc.disable()
suite = unittest.defaultTestLoader.loadTestsFromName(
    "test_working_set_encoding_refusal.WorkingSetEncodingRefusalTest"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
loaded = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if filename is None:
        continue
    path = Path(filename).resolve()
    if path.is_relative_to(root) and path.suffix == ".py":
        loaded[name] = {
            "path": str(path.relative_to(root)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
args.output.write_text(json.dumps({
    "python": sys.version.split()[0], "gcEnabled": gc.isenabled(),
    "testsRun": result.testsRun, "failures": len(result.failures),
    "errors": len(result.errors), "skips": len(result.skipped),
    "expectedBeforeFailure": args.before, "loadedProjectModules": loaded,
    "scope": "test-only exact saturated reservation boundary/actual Runtime byte counter; no demonstrated default64MiB overrun, physical/RSS or producer acceptance",
}, indent=2, sort_keys=True) + "\n")
success = (len(result.failures) == 3 and not result.errors if args.before else result.wasSuccessful())
raise SystemExit(0 if result.testsRun == 3 and success and not result.skipped else 1)
