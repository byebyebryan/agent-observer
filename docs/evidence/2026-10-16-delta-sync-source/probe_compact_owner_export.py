"""Synthetic owner baseline bytes only; no Reader/IPC/RSS/CPU acceptance.

Run serially per size with source/tests on PYTHONPATH. Large JSON parsing below
is an independent fixture oracle after the recorded producer account peak; it
is not part of the native serializer or aggregate memory qualification.
"""

import argparse
import gc
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from bench_sync_producer import native_shaped_snapshot

from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    gc.disable()
    boot, value, wall = native_shaped_snapshot(args.rows)
    with patch("agent_observer.service_state.uuid.uuid4") as minted:
        import uuid

        minted.return_value = uuid.UUID(int=61440)
        owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                             uid=1000, clock=lambda: 15000, boot_id=boot, clock_domain="time:[123]",
                             sync_serialization="compact")
    owner.wall_clock = lambda: wall
    owner.collection_id = lambda: str(uuid.UUID(int=61440))
    owner.attempt("codex", "history")
    owner.accept("codex", "history", value, sampled_ms=15000, ttl_ms=60000, runtime_ttl_ms=60000)
    result = {"scope": "synthetic owner cold full+active only; no Reader/transport/CPU/RSS/recovery acceptance",
              "rows": args.rows, "gcDisabled": not gc.isenabled(), "views": {}}
    cache = None
    try:
        for view in ("full", "active"):
            legacy = canonical(owner.frame("view", 1) if view == "full" else owner.active_frame("view", 1)) + b"\n"
            raw = owner.sync_baseline(view)
            cache = owner._sync_cache
            account = cache.account.snapshot()
            encoded = {"internal": cache.encoded_ownership.used,
                       "outputs": sum(map(len, cache.retained_buffers())), "staged": cache.encoded_staged}
            # Native output is completely built before this separate DOM oracle.
            message = json.loads(raw)
            selected = len(message["tables"]["records"])
            bits = sum(mask.bit_count() for _group, mask in message["tables"]["memberships"])
            assert bits == cache.views[view].current.tables["memberships"].count
            assert message["tag"] == list(owner.sync_current_tag(view))
            result["views"][view] = {
                "selected": selected, "legacyBytes": len(legacy), "compactBytes": len(raw),
                "ratio": len(raw) / len(legacy), "sha256": hashlib.sha256(raw).hexdigest(),
                "tag": message["tag"], "membershipCells": bits,
                "membershipGroups": len(message["tables"]["memberships"]),
                "receiptCount": len(message["tables"]["receipts"]),
                "ownerAccount": account, "ownerEncoded": encoded,
            }
            del message, legacy, raw
    finally:
        if cache is not None:
            cache.close()
            closed = cache.account.snapshot()
            result["closedAccount"] = closed
            assert closed["used"] == closed["base"] and not cache.encoded_staged
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"rows": args.rows, "views": {
        view: {key: data[key] for key in ("selected", "legacyBytes", "compactBytes", "ratio", "membershipCells")}
        for view, data in result["views"].items()}}))


if __name__ == "__main__":
    main()
