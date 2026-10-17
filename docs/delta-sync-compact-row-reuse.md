# Bounded compact serializer row reuse

The owner compact serializer reuses one record slot within the current row,
matched by exact side and full identity. It clears that memo at every row
boundary and before releasing scratch. Its container adds 256 bytes of prepaid
heap credit; the decoded slot remains in the existing row envelope. No roster
cache or cross-generation lookup is added.

Membership-mask changes now read the after observation from the exact canonical
bytes retained by the committed edit. Removal has no after observation. The
before value still comes from the original before table, and the uncached path
remains for edits without retained bytes. This changes neither support meaning
nor the generic single-writer membership expansion rule.

The [receipt](evidence/2026-10-17-compact-row-reuse/receipt.json) binds the parent
`af3ec00` (production source `f7f7a55`), two-file overlay, immutable Mesh
`a482abb`/evidence `f667588`, and all captured outputs. On each Python 3.14.8 and
3.11.17, 64 compact export/source/parser/transport/codec checks pass with GC
disabled and no skips. Two new tests check row/side isolation and prevent an
after-map reread for changed observation insertion/removal. An initial new test
omitted creation of the initial sync baseline; that test setup was corrected.

Four deterministic captures compare 18 original full/active baseline,
transaction and completion frames byte-for-byte against the prior source on
both Python versions. Every transaction independently matches the raw-ID
oracle. They include Unicode changes, unchanged masks and membership
removal/insertion. These synthetic files are outside production ledgers.

A separately instrumented 500-row publication profile records 30,696 to 18,456
serializer map-entry reads. Instrumented serialization time is 2.962 to 2.481
seconds across the measured calls. These profiler timings are diagnostic and
are excluded from the matched CPU screens.

## CPU ceiling remains failed

Fresh serial installed-a7/source ABBA screens use six all-body generations per
run under the shared CPU advisory lock. Both sides have GC enabled. All semantic
signatures match and final source hashes are stable. The receipt sums exact
owner-only components over twelve generations per side, excluding the separately
reported semantic oracle:

| Rows | Old owner | New retained common | Added sync | New owner total | Increase |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 | 2,310.133 ms | 1,534.832 ms | 4,600.153 ms | 6,134.985 ms | +165.57% |
| 2000 | 9,230.158 ms | 6,406.722 ms | 16,068.900 ms | 22,475.622 ms | +143.50% |

Both strict 25% owner ceilings **FAIL**. Each 2,000-row source run still falls
back five times and delivers no ensuing recovery baseline. This fixture has
3,510/14,010 full membership cells and ten active rows, not a dense nine-field
roster. Prior screens retain their own timing and source provenance; these runs
do not establish a whole-pipeline saving.

An earlier 500-row draft screen belongs to the initial overlay. A 2,000-row
draft was invalidated by a source edit during measurement; its hash guard
failed, and its partial logs remain separate from the final frozen screens.

Cold construction, delivered recovery, publisher/Reader/facade cost, actual
IPC/SSH, aggregate 32/64 MiB peaks, RSS, latency, dense capacity and immutable
installed-pair acceptance remain open. Mesh's independently reported stamped
header-copy lifetime finding is also open; these checks do not cover that edge.
The controller agreement and Observer consuming-ref closure remain separate
closed prerequisites.

No schema/encoding/version allocation, shared API, original timestamp/support,
proof or authority change accompanies this source optimization. Normal a7/a23
selection, providers/services, Tmux/349/writer and sibling repositories are
unchanged. Git attribution cleanup remains on HOLD.
