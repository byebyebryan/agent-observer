# Compact owner CPU diagnostic remains failed

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The compact serializer now sends already admitted row values directly to the
JSON encoder. Committed immutable objects use a shallow dictionary adapter;
ordinary packed lists/dictionaries and immutable array tuples need no temporary
freeze/thaw graph. The existing row construction envelope, encoded reservations,
canonical field order, native roots and raw transaction IDs remain unchanged.
No full roster, cross-row intern cache or relaxed admission is introduced.

The [byte-pinned receipt](../../evidence/2026-10-16-delta-sync-source/compact-owner-cpu.json)
records serial ABBA on the shared CPU advisory lock, using the unchanged installed
a7 Python for both sides. A runs import installed a7 in isolated mode; B runs
select the owning source overlay and explicit compact serialization. Each run
has six generations, real attempt diagnostics, both full/active publication and
the same complete snapshot/projection/support/census oracle. All signatures match;
all loaded source hashes stay stable within each run and between its repeated
sides. GC is enabled on both sides. These are synthetic source measurements,
not installed candidate or end-to-end acceptance.

| Rows | Old before/after median | Compact before | Compact after | After versus old |
| --- | ---: | ---: | ---: | ---: |
| 500 | 198.06/195.59 ms | 742.87 ms | 625.34 ms | +219.72% |
| 2000 | 805.97/801.92 ms | 2554.12 ms | 2238.85 ms | +179.19% |

Each before/after screen has its own serial old/new ABBA control runs. These
medians include oracle CPU. Exact component totals below sum across twelve
measured generations per side; the old owner excludes its separately recorded
oracle. New owner total is retained common generation plus all added sync work.
The oracle is also included separately in the overall measured totals.

| Rows | Old owner | New retained common | New sync | New combined owner | Old/new oracle |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 | 2214.209 ms | 1518.539 ms | 5799.579 ms | 7318.117 ms | 131.181/152.901 ms |
| 2000 | 9090.413 ms | 6435.286 ms | 19956.615 ms | 26391.901 ms | 502.597/553.464 ms |

The producer ceiling remains **FAIL**, including when the oracle is excluded.
The fixture has 3,510/14,010 full membership cells at 500/2,000 rows and only ten
active rows; it is not a fully dense nine-field roster. The 2,000-row source runs
record five baseline fallbacks each. No resulting baseline is delivered by this
probe, so these are neither successful recovery nor deliverable-target evidence.
Cold owner construction is reported separately; baseline/IPC/publisher/Reader/
facade/SSH, shared 32/64 MiB peaks, RSS, latency and installed acceptance are
excluded. No percentage here establishes a full-pipeline saving or promotion.

A separate instrumented 500-row profile attributes 7.856 of 12.358 seconds of
publication time to compact transaction serialization. Its three streaming
passes repeatedly adapt and encode changed rows; freeze/thaw alone has 3.220
seconds cumulative cost, overlapping other entries. Instrumented times are not
mixed into ABBA totals. Removing the redundant round trip lowers the observed
median at both scales but does not settle the remaining transaction passes,
alias/support lookups, or map staging costs. Those remain further work within
the original bounds; no cap/deadline changes are proposed.

Correctness checks run 62 existing export/source/codec/parser/structural transport
methods on both Python versions with GC disabled. Exact 100-row cold full/active
bytes, tags and membership counts match the prior committed export receipt.
Existing tests independently restore transaction tables/roots, verify raw IDs,
exercise Unicode, schema/expected-old failures and preallocation/rollback.
The final repository check is recorded in the receipt. Historical CPU failures,
source retirement acceptance and prior synthetic relay evidence retain their
original scope. No schema/encoding/version allocation, installed selection,
provider/service, sibling or rollout changes accompany this source checkpoint.

The first temporary profile helper was named `profile.py` and shadowed Python's
standard module. Renaming it fixed setup; that failed attempt is not a production
failure or an ABBA sample.
