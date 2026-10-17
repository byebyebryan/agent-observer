# Shared encoded ownership and additive CPU

This is unfinished Observer source evidence for the coordinator's encoded-cache
clarification. Producer acceptance remains **FAIL**. Runtime bytes are
`068f4b0fb34539d9afc7fea324e9b0153010ee8d`, also present at evidence checkpoint
`46f2c92`. No cap, frozen G0 document, native schema or selected artifact changed.

## What the caps count

The single 33,554,432-byte encoded budget includes retained canonical Ckey/Cvalue
buffers across both views, candidate staging, cached baseline/head/journal output,
all queued peer pins and encoding workspace. The same buffers are also heap
charged under the 67,108,864-byte owner allocation cap, together with nodes,
indexes, containers, accounting and temporary allocations. These are overlapping
caps. A physically shared buffer contributes once within each cap; equal copied
buffers contribute separately.

The enforced encoded counter is the unique canonical/output/pin union, plus
stage/output workspace reservation and peer tuple allowance. Operation fragments
that borrow canonical buffers do not create another encoded allocation. Copied
fragments and output constructors reserve additional bytes before construction.
The workspace reservation includes unused future constructor credit; it is not
all already allocated payload. This is an internal-cache budget, not an
output-only ledger.

## Diagnostic boundary

[bench_sync_resources.py](../../../tests/bench_sync_resources.py) uses the same
native-shaped fixture as the producer probe: six generations with all stable
`lastUpdated.at` values changing, full and ten-row active views, and sixteen
disposable socketpair peers (eight per view). It exercises production queue,
pin and reservation paths without starting a service or provider. Peers retain
their initial frames while the owner advances both views.

Instrumentation records scalar peaks and, at a chosen checkpoint, streams only
integer buffer identities, sizes and role bits. Offline union/intersection
analysis runs after owner cleanup. Its fixed 262,144-byte metadata/workspace
allowance is heap charged; map iterator frontiers used by the detailed inventory
are separately heap charged. These instrumented runs establish account and
ownership behavior only, not RSS, CPU, installed IPC, native or transport gates.

The full 2,000-row expanded baseline still exceeds the 8,404,992-byte frame cap.
That run pins full-view **heads only**, alongside active-view baseline frames.
It does not demonstrate delivery or recovery of the full roster. The 100/500-row
runs pin both material baselines. All runs have zero worker starts and end with
zero accounted live allocations/objects, at the fixed 29,548-byte account base.

Exact checkpoints, source/probe hashes, declined reservations and inventory
results are in [ownership.json](ownership.json). The probe SHA256 is
`856f7b5e2513c164e20eba241e8020919e7298e522bbb755f6295c7db7944496`.

## Aggregate peaks

All sizes below are bytes. Heap observations include the diagnostic allowance;
they are account measurements, not process RSS. Heap and encoded peaks can occur
at different points.

| Full rows / active rows | Observed heap peak | Encoded counter peak | Canonical at encoded peak | Cached output | Peer pins | Output/pin overlap | Stage/output reservation | Peer tuples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 / 10 | 7,935,151 | 3,349,722 | 1,180,109 | 524,970 | 685,159 | 0 | 958,588 | 896 |
| 500 / 10 | 26,550,512 | 15,034,134 | 5,436,513 | 2,169,772 | 3,046,761 | 0 | 4,380,192 | 896 |
| 2,000 / 10 | 62,526,683 | 22,339,989 | 21,404,017 | 103,120 | 85,290 | 0 | 746,666 | 896 |

At these encoded peaks the full current root is generation 12, full generation
13 is staging, and active current/predecessor roots are generations 12/11.
The owner evicted its own older full predecessor before staging, as permitted
by the bounded ownership contract. Both views retain current/predecessor roots
again after publication. The counter covers whichever roots are physically
retained; it does not assume a discarded full predecessor remains resident.

For example, immediately after the 500-row initial queues, cached output and
all sixteen pins refer to the same two buffers: each role totals 3,046,761 bytes,
and their overlap is 3,046,761 bytes. With canonical buffers of 3,732,022 bytes
and peer tuples of 896 bytes, the enforced total is **6,779,679 bytes**. The
frames are not charged sixteen times or twice for cache and pins. At the later
peak those initial pins survive cache eviction, so cache/pin overlap is zero
and both distinct output sets are charged.

## Detailed 2,000-row overlap

Two separate runs inventory the observed heap peak (`full:13:map:bodies:1`) and
encoded peak (`full:13:encoded-request-declined`). Their runtime and probe bytes
match. Both have the same 66,398 canonical buffers totaling 21,404,017 bytes.

| Physical role / reservation | Heap-peak checkpoint | Encoded-peak checkpoint |
| --- | ---: | ---: |
| Unique canonical buffers | 21,404,017 | 21,404,017 |
| Unique cached output | 103,120 | 103,120 |
| Unique peer pins | 85,290 | 85,290 |
| Canonical/output/pin cross-role overlap | 0 | 0 |
| Unique retained canonical/output/pin union | 21,592,427 | 21,592,427 |
| Stage-reachable immutable bytes | 21,306,807 | 21,844,316 |
| Stage/canonical overlap, already charged above | 21,306,568 | 21,306,568 |
| Additional distinct stage immutable bytes | 239 | 537,748 |
| Physical immutable union including stage | 21,592,666 | 22,130,175 |
| Stage/output reservation including those distinct bytes | 85,180 | 746,666 |
| Unused stage/output credit | 84,941 | 208,918 |
| Peer tuple allowance | 896 | 896 |
| Enforced encoded counter | **21,678,503** | **22,339,989** |

Stage-reachable bytes include the borrowed full base, candidate maps, operation
claims and fragments. Adding that entire role to canonical bytes would double
count 21,306,568 bytes. At the encoded peak, the distinct 537,748 stage bytes
plus unused 208,918-byte credit equal the 746,666-byte reservation. Thus the
physical union plus unused credit plus peer tuples equals the enforced counter.

Within the canonical union, full current owns 14,509,023 bytes; active current
owns 96,499 and active predecessor 96,501, sharing 95,551 bytes. Their active
union is 97,449 bytes. There is no full/active buffer overlap in this fixture.
The remaining 6,797,545 canonical bytes are newly staged outside those retained
roots. No canonical byte lacks root or stage reachability. The full predecessor
is absent at these staging checkpoints because it was evicted before staging.

After the final publication, all four full/active current/predecessor roots are
retained (generations 13/12), with no stage: canonical bytes total 20,850,165,
cached output 100,734 and pins 85,290, with no output/pin overlap. Including the
896-byte tuple allowance, their shared encoded counter is 21,037,085 bytes.

The detailed inventory's charged traversal raises the complete heap-account
high-water mark to 62,658,003 bytes in the heap-inventory run and 62,576,908 in
the encoded-inventory run. The observed source allocation peak before that
inventory work is 62,526,683, including the fixed diagnostic allowance. None of
these figures substitutes for a later installed heap/RSS gate.

At generation 13 the expanded transaction constructor requests an additional
16,470,530 bytes (two times its 8,235,265-byte frame). The current encoded
counter is 22,339,989; the prospective total is **38,810,519**, above 33,554,432.
The request is refused **before buffer allocation** with `sync_encoding_limit`.
This prospective rejected total is not retained memory. Six such refusals cause
six explicit baseline-required fallbacks. Current roots remain valid, with no
failed view or cold rebuild, but packed recovery remains unfinished.

Existing tests separately check physical sharing, equal independent copies,
evicted output still pinned, final pin release, the aggregate encoded limit and
the enclosing service limit. The source check passes 792 tests without skips,
plus Ruff, Markdown, links and Git diff checks.

## Additive CPU boundaries

The uninstrumented serial dense ABBA at `068f4b0` remains the CPU evidence;
resource-probe timings are not used. [dense-sharing-abba.json](dense-sharing-abba.json)
contains twelve generation samples per side. These matched batch totals include
attempt diagnostics, retained common work, both sync views and oracle hashing.
Cold construction, baseline/recovery delivery and downstream transport are
excluded. Missing recovery work is not a saving.

| Measured component | CPU milliseconds, twelve-sample sum |
| --- | ---: |
| Old owner common work | 9,484.498129 |
| Old oracle | 543.007580 |
| **Old owner total including oracle** | **10,027.505709** |
| New retained common work | 6,169.390853 |
| New oracle | 560.881960 |
| **New retained legacy work including oracle** | **6,730.272813** |
| **Added new sync work** | **14,897.415415** |
| **Combined new owner total including oracle** | **21,627.688228** |

The new total is exactly 6,730.272813 + 14,897.415415 ms. Compared with the old
10,027.505709 ms, aggregate total CPU increases **115.68%**. The separate pooled
median comparison is 837.06 ms old versus 1,830.43 ms new, **+118.67%**. Independent
component medians must not be added. Both statistics exceed the 25% overhead
ceiling: the producer CPU gate remains **FAIL**, despite exact signatures.

The shared-byte accounting clarification is reflected in this diagnostic;
compact transport, dense CPU, immutable artifacts and installed/native gates
remain open. No rollout or adoption is claimed.
