"""Locate refused generic reserve/atom-edge calls using scalar-only test hooks."""

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
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync.budget import AllocationLedger

    reserve, edge, events = AllocationLedger.reserve, AllocationLedger._retain_atom_edge, []

    def reserving(ledger, amount, *, encoded=0):
        try:
            return reserve(ledger, amount, encoded=encoded)
        except ProtocolError as error:
            if str(error) == "sync_decoded_capacity":
                events.append(dict(operation="reserve", amount=amount, encoded=encoded,
                                   file=Path(sys._getframe(1).f_code.co_filename).name,
                                   line=sys._getframe(1).f_lineno, ledger=ledger.inspect()))
            raise

    def retaining_edge(ledger, value):
        try:
            return edge(ledger, value)
        except ProtocolError as error:
            if str(error) == "sync_decoded_capacity":
                events.append(dict(operation="atom-edge", rootType=type(value).__name__,
                                   file=Path(sys._getframe(1).f_code.co_filename).name,
                                   line=sys._getframe(1).f_lineno, ledger=ledger.inspect()))
            raise

    path = args.mesh / "docs/evidence/2026-10-17-reader-capacity/probe_reader_intake.py"
    spec = importlib.util.spec_from_file_location("reader_intake_probe", path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    args.rows, args.backend = 2000, "packed"
    with Path("/home/bryan/.cache/agent-active-feed-cpu.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (patch.object(AllocationLedger, "reserve", reserving),
              patch.object(AllocationLedger, "_retain_atom_edge", retaining_edge)):
            asyncio.run(probe.run(args))
    report = json.loads(args.output.read_text())
    report["privateScalarLedgerRefusals"] = events
    report["privateAuditExclusion"] = "Scalar-only failure location/cost/type/ledger observations, no retained graphs or frames. Instrumented time excluded; no physical/RSS/CPU or authority claim."
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
