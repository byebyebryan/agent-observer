"""Replay focused source tests without provider/service actions."""

import argparse
import gc
import hashlib
import json
import sys
import unittest
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root))
    gc.disable()
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"), pattern="test_working_set_*.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    loaded = {}
    for name, module in tuple(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path is None:
            continue
        path = Path(path).resolve()
        if path.is_relative_to(root) and path.suffix == ".py":
            loaded[name] = {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    report = {
        "python": sys.version.split()[0],
        "gcEnabled": gc.isenabled(),
        "testsRun": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "loadedProjectModules": loaded,
        "scope": "synthetic component/local socket tests; no provider/native/installed/performance qualification",
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
