"""Scalar-only failing callback-budget charge location; no production helper."""

import argparse
import asyncio
import fcntl
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "observer", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.mesh, args.observer = args.mesh.resolve(), args.observer.resolve()
    assert not args.output.exists()
    sys.path[:0] = [str(args.mesh / "src"), str(args.observer), str(args.observer / "tests")]
    from mesh_plus.sync.reconstruction import BudgetRef

    charge, events = BudgetRef.charge, []

    def observed(budget, amount):
        try:
            return charge(budget, amount)
        except BaseException:
            # Private scalar ledger inspection only; no frame/object history.
            events.append(dict(file=Path(sys._getframe(1).f_code.co_filename).name,
                               line=sys._getframe(1).f_lineno, amount=amount,
                               ledger=budget._ledger.inspect()))
            raise

    path = args.mesh / "docs/evidence/2026-10-17-reader-capacity/probe_reader_intake.py"
    spec = importlib.util.spec_from_file_location("reader_intake_probe", path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    args.rows, args.backend = 2000, "packed"
    with Path("/home/bryan/.cache/agent-active-feed-cpu.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with patch.object(BudgetRef, "charge", observed):
            asyncio.run(probe.run(args))
    report = json.loads(args.output.read_text())
    report["privateScalarChargeRefusals"] = events
    report["privateAuditExclusion"] = "Failing charge wrapper observes scalar location/amount/ledger only; no copied patch/graph, resource/RSS/CPU or semantic capability."
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(events))


if __name__ == "__main__":
    main()
