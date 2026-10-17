"""Controlled local-socket source seam diagnostic, not native/relay acceptance.

Reproduces existing behavior at d634640: successful changes hides its exact
completion ref, and malformed completion tag/epoch can pass the source boundary.
This intentionally asserts the observed defects. It is not a future API test.
Private Observer instrumentation is owning diagnostic code, never a proposed
Mesh access path or admission shortcut.
"""

import argparse
import copy
import gc
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--source-root", type=Path, default=ROOT,
                    help="exact immutable old Observer export; current fixed source should reject these cases")
SOURCE_ROOT = PARSER.parse_args().source_root.resolve()
sys.path[:0] = [str(SOURCE_ROOT), str(SOURCE_ROOT / "tests")]

from test_sync_owned_source import OwnedSourceTest  # noqa: E402
from test_sync_source import message_fixture, wire  # noqa: E402

from agent_observer import sync_owned_source  # noqa: E402
from agent_observer.sync_owned_source import OwnedSyncControl  # noqa: E402

RESULTS = []


class CompletionReview(OwnedSourceTest):
    async def inspect_case(self, kind):
        terminal = message_fixture("control", generation=3 if kind == "wrong-target" else 2)
        if kind == "foreign-epoch":
            terminal["cursor"][0] = terminal["ownerClock"]["ownerEpoch"] = "00000000-0000-0000-0000-000000000008"
        if kind == "heartbeat":
            terminal["status"] = "heartbeat"
        terminal.update(baseTag=copy.deepcopy(self.baseline["tag"]),
                        targetTag=copy.deepcopy(self.transaction["resultTag"]))
        await self.responses([self.transaction, terminal])
        captured, original = [], sync_owned_source._OwnedClient._read_frame

        async def observe(client, *args, **kwargs):
            packet = await original(client, *args, **kwargs)
            if isinstance(packet, OwnedSyncControl):
                captured.append((packet.data, packet.tag, packet.cursor))
            return packet

        with patch.object(sync_owned_source._OwnedClient, "_read_frame", observe):
            returned = await self.session.changes(self.baseline["tag"], target=self.transaction["resultTag"])
        self.assertEqual(len(returned), 1)
        self.assertEqual(len(captured), 1)
        ref, tag, cursor = captured[0]
        with self.assertRaisesRegex(ValueError, "sync_input_retired"):
            _ = ref.nbytes
        encoded = sum(value.nbytes for value in returned)
        self.assertEqual(self.cache.ledger.encoded_reserved, encoded)
        self.assertEqual(self.session.inspect()["ownedTickets"], 0)
        RESULTS.append({
            "case": kind, "sourceReturnedSuccess": True,
            "returnedTransactions": len(returned), "completionWasObservedOwned": True,
            "completionRawSha256": hashlib.sha256(wire(terminal)).hexdigest(),
            "completionBytes": len(wire(terminal)), "completionRefRetiredBeforeReturn": True,
            "completionTagMatchedTarget": tag == tuple(self.transaction["resultTag"]),
            "completionStatusWasComplete": terminal["status"] == "complete",
            "completionCursorMatchedLastResult": cursor == tuple(self.transaction["resultCursor"]),
            "retainedEncodedBytes": encoded, "retainedTicketCount": 0,
        })
        for value in returned:
            value.close()
        self.assertEqual(self.session.inspect()["ownedRefs"], 0)

    async def test_exact_completion_hidden(self):
        await self.inspect_case("exact-completion")

    async def test_wrong_target_accepted(self):
        await self.inspect_case("wrong-target")

    async def test_foreign_epoch_accepted(self):
        await self.inspect_case("foreign-epoch")

    async def test_heartbeat_accepted(self):
        await self.inspect_case("heartbeat")


def main():
    enabled = gc.isenabled()
    gc.disable()
    try:
        log = io.StringIO()
        tests = unittest.TestSuite(CompletionReview(name) for name in (
            "test_exact_completion_hidden", "test_wrong_target_accepted", "test_foreign_epoch_accepted",
            "test_heartbeat_accepted"))
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(tests)
        if not result.wasSuccessful() or result.skipped:
            print(log.getvalue(), file=sys.stderr)
            return 1
        print(json.dumps({"status": "EXISTING SOURCE GAPS REPRODUCED; NOT ACCEPTANCE",
                          "python": sys.version.split()[0], "cases": RESULTS,
                          "sourceRoot": str(SOURCE_ROOT),
                          "tests": result.testsRun, "skips": len(result.skipped), "gcEnabledDuringRun": False,
                          "scope": "synthetic protected local Unix socket; exact source result/ref disposal only; no generic relay/native provider/resource/performance/installed gate"},
                         sort_keys=True, indent=2))
        return 0
    finally:
        if enabled:
            gc.enable()


if __name__ == "__main__":
    raise SystemExit(main())
