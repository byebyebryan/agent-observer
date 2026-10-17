"""Deterministic synthetic native frames for exact cross-source comparison.

Files are a separate fixture oracle, not aggregate memory/performance evidence.
"""

import argparse
import copy
import gc
import hashlib
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observer", "mesh", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    observer, mesh = args.observer.resolve(), args.mesh.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [str(observer), str(observer / "tests"), str(mesh / "src")]
    gc.disable()
    from compact_vectors_support import raw_transaction_id
    from test_sync_compact_export import SyncCompactExportTest

    case = SyncCompactExportTest()
    case.setUp()
    frames = []

    def capture(raw, view, step):
        value = json.loads(raw)
        if value["kind"] == "transaction":
            assert value["transactionId"] == raw_transaction_id(value)
        filename = f"{len(frames):02d}-{view}-{step}-{value['kind']}.raw"
        (args.output_dir / filename).write_bytes(raw)
        frames.append({"file": filename, "bytes": len(raw), "kind": value["kind"],
                       "sha256": hashlib.sha256(raw).hexdigest()})

    try:
        for view in ("full", "active"):
            owner = case.owner()
            capture(owner.sync_baseline(view), view, 0)
            for step in range(4):
                value = case.fixture(3 if step < 2 else 2 if step == 2 else 4)
                if step in {1, 3}:
                    value["sessions"][0]["title"] = "new Ω title"
                base = owner.sync_current_tag(view)
                case.now += 10
                owner.accept("codex", "runtime", copy.deepcopy(value), sampled_ms=case.now, ttl_ms=10000)
                for raw in owner.sync_changes(view, base, owner.sync_current_tag(view)):
                    capture(raw, view, step + 1)
    finally:
        case.tearDown()
    assert not gc.isenabled() and len(frames) == 18
    loaded = {}
    for module in tuple(sys.modules.values()):
        if getattr(module, "__name__", None) == "__main__":
            continue  # The exact probe is pinned separately from imported modules.
        filename = getattr(module, "__file__", None)
        if not filename or Path(filename).suffix != ".py":
            continue
        path = Path(filename).resolve()
        # A Mesh export may be nested in Observer's .cache. Assign its actual
        # owner first and exactly once, rather than creating Observer aliases.
        for label, root in (("mesh", mesh), ("observer", observer)):
            if path.is_relative_to(root):
                loaded[label + "/" + str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
                break
    report = {"python": sys.version.split()[0], "frames": frames, "loadedInputs": loaded,
              "gcDisabled": True, "scope": "synthetic owner baseline/transactions/controls only; no transport or resource/CPU acceptance"}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"python": report["python"], "frames": len(frames)}))


if __name__ == "__main__":
    main()
