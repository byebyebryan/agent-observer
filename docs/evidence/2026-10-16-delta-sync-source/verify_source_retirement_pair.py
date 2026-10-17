"""Run final source lifetime components and unchanged owning Mesh relay cases."""

import argparse
import gc
import hashlib
import importlib
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

MODULES = (
    "test_sync_source_retirement", "test_sync_compact_source", "test_sync_compact_export",
    "test_sync_completed_changes", "test_mesh_sync_codec", "test_sync_compact_plan",
    "test_sync_compact", "test_sync_compact_transport", "test_mesh_sync_profile",
    "test_mesh_sync_read", "test_sync_owned_source", "test_sync_source",
    "test_sync_transport", "test_sync_acquisition",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observer", "mesh", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    observer, mesh = args.observer.resolve(), args.mesh.resolve()
    sys.path[:0] = [str(observer), str(observer / "tests"), str(mesh / "src")]
    path = mesh / "docs/evidence/2026-10-16-delta-sync/verify_completed_relay.py"
    original = path.read_text()
    old = 'self.assertEqual(session.inspect()["ownedRefs"], 0)  # consuming-ref pruning exercised, batch still owns children'
    new = 'self.assertEqual(session.inspect()["ownedRefs"], 5)  # four transactions plus completion stay revocable while pinned'
    assert original.count(old) == 1
    adapted = original.replace(old, new)
    probe = ModuleType("owner_adapted_mesh_completed_relay")
    probe.__file__ = str(path)
    exec(compile(adapted, "<Observer one-assertion Mesh retirement adaptation>", "exec"), probe.__dict__)
    sync = importlib.import_module("mesh_plus.sync")
    transport = importlib.import_module("mesh_plus.transport")
    wire = importlib.import_module("mesh_plus.sync.canonical")
    probe.ENV = SimpleNamespace(
        Source=importlib.import_module("agent_observer.sync_source").CachedAgentSyncSource,
        Profile=importlib.import_module("agent_observer.mesh_sync_profile").AgentSyncProfile,
        Codec=importlib.import_module("agent_observer.sync_transport").AgentSyncTransportCodec,
        seeded=importlib.import_module("test_sync_service_delivery").seeded,
        snapshot=importlib.import_module("test_service_runtime").scoped_snapshot,
        Ledger=importlib.import_module("mesh_plus.sync.budget").AllocationLedger,
        ProtocolError=importlib.import_module("mesh_plus.protocol").ProtocolError,
        relay=sync.create_sync_relay, Cache=sync.OwnedSyncCache, Budgets=sync.SyncBudgets,
        binding=sync.source_binding, Line=transport.LineChannel, now=transport.boottime_ms,
        canonical=wire.canonical, decode=wire.decode,
    )
    gc.disable()
    owning = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in MODULES)
    seam = unittest.defaultTestLoader.loadTestsFromTestCase(probe.CompletedRelayTests)
    assert owning.countTestCases() == 212 and seam.countTestCases() == 8
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite((owning, seam)))
    assert not gc.isenabled()
    loaded = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename or Path(filename).suffix != ".py":
            continue
        path = Path(filename).resolve()
        for label, root in (("observer", observer), ("mesh", mesh)):
            if path.is_relative_to(root):
                loaded.append({"owner": label, "path": str(path.relative_to(root)),
                               "module": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {"python": sys.version.split()[0], "tests": result.testsRun,
              "owningComponents": 212, "unchangedMeshSeamMethods": 8,
              "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
              "cyclicGcDisabled": True, "sourceFixProducerAcceptance": False,
              "upstreamProbeSha256": hashlib.sha256(original.encode()).hexdigest(),
              "adaptedProbeSha256": hashlib.sha256(adapted.encode()).hexdigest(),
              "testOnlyAdaptation": {"old": old, "new": new, "changedAssertions": 1},
              "loadedInputs": loaded, "meshCases": probe.OUTCOMES,
              "scope": "Synthetic native IPC/source/relay/ordinary Reader plus isolated pin lifecycle; no controller, aggregate resource, CPU, populated native, installed pair or rollout acceptance"}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
