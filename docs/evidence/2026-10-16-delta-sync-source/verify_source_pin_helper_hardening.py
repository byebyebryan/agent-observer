"""Reproduce the open source gap and reject a swallowed pin-body error."""

import argparse
import gc
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def load_overlay(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SourceRefRevocationTest


def run_cases(cases):
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(cases))
    final = [
        [cache.ledger.used, cache.ledger.reserved, cache.ledger.encoded,
         cache.ledger.encoded_reserved, cache.ledger.pending_units]
        for case in cases for cache in case.caches
    ]
    return {
        "tests": result.testsRun,
        "failures": [test._testMethodName for test, _ in result.failures],
        "errors": [test._testMethodName for test, _ in result.errors],
        "skips": len(result.skipped),
        "failureDetails": [text for _, text in result.failures],
        "finalCounters": final,
        "heldErrors": sum(len(case.errors) for case in cases),
        "cyclicGcDisabled": not gc.isenabled(),
    }


def interior_error_case(cls):
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync.inputs import InputOwner

    case = cls("test_scope_close_revokes_head_without_inspection")
    original = InputOwner.reserve
    injected = 0

    def reserve(owner, heap_bytes, *, encoded_bytes=0):
        nonlocal injected
        if owner is getattr(case, "inputs", None) and heap_bytes == 1 and encoded_bytes == 0:
            injected += 1
            raise ProtocolError("sync_input_retired")
        return original(owner, heap_bytes, encoded_bytes=encoded_bytes)

    with patch.object(InputOwner, "reserve", new=reserve):
        result = run_cases([case])
    result["injectedInteriorErrors"] = injected
    return result


def clean(result):
    return (not result["errors"] and not result["skips"] and result["cyclicGcDisabled"]
            and all(values == [0] * 5 for values in result["finalCounters"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observer", "mesh", "before", "after", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    sys.path[:0] = [str(args.observer), str(args.observer / "tests"), str(args.mesh / "src")]
    before = load_overlay("before_source_pin_overlay", args.before)
    after = load_overlay("after_source_pin_overlay", args.after)
    expected_gaps = {
        "test_public_inspect_preserves_head_pin_for_scope_close",
        "test_receive_pruning_preserves_another_head_pin_for_scope_close",
        "test_inspection_does_not_abort_a_healthy_pin",
    }
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        results = {}
        for name, cls in (("before", before), ("after", after)):
            normal = run_cases(list(unittest.defaultTestLoader.loadTestsFromTestCase(cls)))
            injected = interior_error_case(cls)
            results[name] = {"originalFiveCases": normal, "interiorErrorInjection": injected}
        before_fault = results["before"]["interiorErrorInjection"]
        after_fault = results["after"]["interiorErrorInjection"]
        verified = all(
            clean(phase["originalFiveCases"]) and phase["originalFiveCases"]["tests"] == 5
            and set(phase["originalFiveCases"]["failures"]) == expected_gaps
            and clean(phase["interiorErrorInjection"])
            and phase["interiorErrorInjection"]["injectedInteriorErrors"] == 1
            for phase in results.values()
        ) and not before_fault["failures"] and len(after_fault["failures"]) == 1 and (
            "pin body did not finish before pin-exit rejection" in after_fault["failureDetails"][0]
        )
        report = {
            "result": "HARDENING_VERIFIED_OPEN_GAP_REPRODUCED" if verified else "UNEXPECTED_RESULT",
            "python": sys.version.split()[0],
            "sourceFixAccepted": False,
            "scope": "Synthetic UNIX source fixture; private input_bytes pin and injected public reserve error; no resource or producer acceptance",
            "phases": results,
            "loadedModules": [
                {"module": name, "owner": owner, "path": str(path.relative_to(root)),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for name, module in sorted(sys.modules.items())
                if (filename := getattr(module, "__file__", None))
                for path in (Path(filename).resolve(),)
                for owner, root in (("observer", args.observer.resolve()),
                                    ("mesh", args.mesh.resolve()))
                if path.is_relative_to(root) and path.is_file()
            ],
        }
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"result": report["result"], "python": report["python"]}))
        return 0 if verified else 1
    finally:
        if was_enabled:
            gc.enable()


if __name__ == "__main__":
    raise SystemExit(main())
