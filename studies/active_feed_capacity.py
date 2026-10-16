#!/usr/bin/env python3
"""Installed bounded-capacity rejection, not a throughput claim."""

import argparse
import copy
import json
import uuid
from pathlib import Path


def run(args):
    import agent_observer
    from agent_observer.active_contract import MAX_IDENTITIES, MAX_LEDGER_BYTES
    from agent_observer.contract import MAX_SESSIONS, ContractError, validate_snapshot
    from agent_observer.service_state import ServiceState

    if "site-packages" not in agent_observer.__file__:
        raise AssertionError("installed_observer_required")
    full = json.loads(args.fixture.read_text())
    snapshot = full["snapshot"]
    snapshot["sources"] = snapshot["sources"][:1]
    row = next(row for row in snapshot["sessions"] if row["identity"]["provider"] == "codex")
    snapshot["sessions"] = []
    for number in range(5000):
        item = copy.deepcopy(row)
        identifier = str(uuid.UUID(int=number + 1))
        item["identity"]["nativeId"] = identifier
        item["nativeIds"]["threadId"] = item["nativeIds"]["sessionTreeRootId"] = identifier
        snapshot["sessions"].append(item)
    source = snapshot["sources"][0]
    state = ServiceState(host_scope=full["hostScope"], uid=full["uid"],
                         configs={"codex": (source["configHome"], source["configHomeKind"])},
                         clock=lambda: full["emittedBoottimeMs"])
    rejected = []
    for name, action in (
        ("native_snapshot", lambda: validate_snapshot(snapshot)),
        ("service_accept", lambda: state.accept("codex", "runtime", snapshot,
             sampled_ms=full["emittedBoottimeMs"], ttl_ms=60000)),
    ):
        try:
            action()
        except ContractError as error:
            rejected.append({"boundary": name, "reason": str(error)})
        else:
            raise AssertionError("capacity_input_not_rejected")
    if state.revision != 0 or state.snapshot is not None or state.active_projection is not None:
        raise AssertionError("rejected_input_created_authority")
    return {"status": "passed", "inputRows": 5000, "rejected": rejected,
            "fullSnapshotIdentityCeiling": MAX_SESSIONS, "projectedLedgerIdentityCeiling": MAX_IDENTITIES,
            "projectedLedgerCanonicalBytesCeiling": MAX_LEDGER_BYTES,
            "newAuthority": False, "module": agent_observer.__file__,
            "limits": ["5000 exceeds the frozen native 4096-row input ceiling; bounded rejection is expected",
                       "No claim of 5000-row native collection, throughput or full census completeness",
                       "Independent ledger count/byte overflow and recovery are covered by installed tests",
                       "Codex native catalog/loaded classification limits remain unchanged"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
