# Two-pass compact transaction serialization

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The compact serializer combines unsigned transaction hashing with final output
construction. A first bounded walk measures the canonical unsigned frame; the
second hashes those exact bytes while writing. Since `transactionId` sorts after
every unsigned header field, the final unsigned closing brace is hashed and
replaced in output with the ID field and transport LF. Raw transaction IDs and
canonical output remain unchanged. Inconsistent size or final fragments reject;
the temporary iterator, last fragment and digest retire on completion or failure.
No document or roster cache is added.

Existing output constructor, staged encoded credit and per-row scratch remain
in force. Output is reserved before the combined hash/write pass. This also
avoids a wasted hash walk when an optional journal cannot reserve construction
space; it does not make that target deliverable or establish recovery success.
Baseline and original head/control paths are unchanged.

The [receipt](../../evidence/2026-10-16-delta-sync-source/compact-owner-streamed-id.json)
records 18 deterministic full/active baseline, transaction and completion frames
from immutable `f3e3507` and the new source on both Python versions. Actual raw
files compare equal across all four runs; every transaction also matches the
independent raw-ID oracle. The sequence covers unchanged support masks, Unicode
body changes, membership removal and insertion. GC is disabled and the fixture
teardown checks native account retirement. These are synthetic oracle files
outside production ledgers, not memory or transport acceptance.

The 62 existing compact export/source/codec/parser/structural transport checks
pass on Python 3.14.8 and 3.11.17 with GC disabled. The full repository check is
recorded separately. The first 3.14 launch hit a directory-creation race in the
test harness before executing tests; its retry passes all 62. This setup error
is not a runtime fail-before claim.

## CPU remains failed

Each new screen uses serial installed-a7/source ABBA under the shared CPU lock,
six all-body generations per run, matching complete semantic signatures and
stable source hashes. Both full and active owner views publish. GC is enabled
for both sides. The prior source screen has its own old control; its original
[receipt](delta-sync-compact-owner-cpu.md) is preserved.

| Rows | Prior compact median | New compact median | New old control | New versus old |
| --- | ---: | ---: | ---: | ---: |
| 500 | 625.34 ms | 536.08 ms | 194.79 ms | +175.22% |
| 2000 | 2238.85 ms | 1938.75 ms | 795.79 ms | +143.63% |

These medians include the oracle. The receipt separately sums old owner CPU,
new retained common generation, all added sync CPU and old/new oracle CPU across
twelve measured generations per side. New owner total is retained common plus
sync, and the strict 25% owner ceiling still fails when the oracle is excluded.

The 2,000-row runs still have five baseline fallbacks each and deliver no ensuing
baseline. They are not successful recovery or deliverable-target evidence. This
fixture has 3,510/14,010 full membership cells, not a dense nine-field roster.
Cold construction, publisher, Reader/facade, actual IPC/SSH, recovery delivery,
aggregate 32/64 MiB peaks, RSS, latency and installed-candidate acceptance are
excluded. Failed construction and subsequent baseline/proof costs must be
included in the eventual full gates. The overall producer gate remains **FAIL**.

This partial source optimization changes no schema/encoding/version, generic API,
source request, original timestamp/support, proof or authority rule. The closed
consuming-ref finding and agreed controller contract remain separate. No normal
a7/a23 selection, provider/service, sibling or rollout action accompanies it.
Git attribution cleanup remains on HOLD while this work continues.
