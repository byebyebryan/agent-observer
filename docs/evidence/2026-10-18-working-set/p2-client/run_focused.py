"""Focused native/client candidate checks; no provider or installed SDK action."""

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
    parser.add_argument("mesh", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, mesh = args.root.resolve(), args.mesh.resolve()
    sys.path[:0] = [str(root), str(mesh)]
    gc.disable()
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), "test*working_set*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    loaded = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        for label, base in (("observer", root), ("mesh", mesh)):
            if path.is_relative_to(base) and path.suffix == ".py":
                loaded[name] = {
                    "repo": label, "path": str(path.relative_to(base)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                break
    args.output.write_text(json.dumps({
        "python": sys.version.split()[0], "gcEnabled": gc.isenabled(),
        "testsRun": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": len(result.skipped),
        "loadedProjectModules": loaded,
        "scope": "synthetic native/CLI/local socket/domain policy; current SDK rejects candidate profile; no actual working-set Reader, native provider, installed or cost acceptance",
    }, indent=2, sort_keys=True) + "\n")
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
