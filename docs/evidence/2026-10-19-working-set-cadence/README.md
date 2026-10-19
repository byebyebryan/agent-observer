# Working-set cadence source-cost evidence

This packet records a controlled, synthetic source-component comparison for the working-set path. It exercises the pinned a7 full-feed implementation against the b176 candidate working-set implementation in the exact tracked `read_matched.py` helper. The helper measures pure `ServiceState.attempt`/`accept` work and, for each configured read, complete local frame creation, canonical LF serialization, strict parsing, and row filtering.

This is SOURCE-only evidence. It does not measure SDK streams or Readers, network/IPC, native collection, an external parent parser, RSS/heap, deployed behavior, or production acceptance. `reads/generation` means sequential local reads in one helper process; 16 does not mean 16 simultaneous Readers. Serialized bytes are local frame bytes, not transmitted wire bytes. The candidate receives trusted synthetic accepted-BOOTTIME metadata directly, so its private source metadata is separate from the primary full-pipeline evidence. Results below are bounded to this fixture and do not establish a universal saving at every cadence or workload.

Each trial includes one untimed warmup and six measured generations with GC disabled. The table reports whole-six-generation trial totals, using the median of two ABBA trials per variant for each cell; it does not pool per-generation medians. Combined CPU is generation accept CPU plus measured local read CPU. Candidate-full was included only in the untimed validation preflight; measured candidate trials use candidate-working.

| Python | Rows | Reads / generation | a7 accept ms | Working-set accept ms | a7 read ms | Working-set read ms | a7 combined ms | Working-set combined ms | Combined CPU reduction | Local frame-byte reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3.14 | 100 | 0 | 135.167 | 106.298 | 0.000 | 0.000 | 135.167 | 106.298 | 21.36% | n/a |
| 3.14 | 100 | 1 | 129.190 | 106.510 | 79.901 | 6.823 | 209.091 | 113.333 | 45.80% | 95.53% |
| 3.14 | 100 | 16 | 130.473 | 107.445 | 1,292.330 | 105.049 | 1,422.803 | 212.494 | 85.07% | 95.53% |
| 3.14 | 500 | 0 | 636.542 | 511.889 | 0.000 | 0.000 | 636.542 | 511.889 | 19.58% | n/a |
| 3.14 | 500 | 1 | 633.108 | 514.510 | 404.110 | 11.239 | 1,037.218 | 525.749 | 49.31% | 98.52% |
| 3.14 | 500 | 16 | 641.632 | 516.433 | 6,509.549 | 170.818 | 7,151.181 | 687.252 | 90.39% | 98.52% |
| 3.14 | 2,000 | 0 | 2,590.412 | 2,075.496 | 0.000 | 0.000 | 2,590.412 | 2,075.496 | 19.88% | n/a |
| 3.14 | 2,000 | 1 | 2,565.477 | 2,120.197 | 1,635.234 | 42.975 | 4,200.711 | 2,163.172 | 48.50% | 98.48% |
| 3.14 | 2,000 | 16 | 2,534.735 | 2,062.513 | 25,936.345 | 673.899 | 28,471.080 | 2,736.412 | 90.39% | 98.48% |
| 3.14 | 100 | 4 | 132.310 | 108.599 | 327.828 | 26.888 | 460.138 | 135.487 | 70.56% | 95.53% |
| 3.11 | 100 | 0 | 147.894 | 125.138 | 0.000 | 0.000 | 147.894 | 125.138 | 15.39% | n/a |
| 3.11 | 100 | 1 | 149.291 | 125.384 | 78.732 | 6.104 | 228.023 | 131.488 | 42.34% | 95.53% |
| 3.11 | 100 | 16 | 150.248 | 124.525 | 1,256.750 | 91.721 | 1,406.998 | 216.246 | 84.63% | 95.53% |
| 3.11 | 500 | 0 | 733.110 | 604.405 | 0.000 | 0.000 | 733.110 | 604.405 | 17.56% | n/a |
| 3.11 | 500 | 1 | 739.088 | 602.614 | 391.669 | 9.959 | 1,130.757 | 612.573 | 45.83% | 98.52% |
| 3.11 | 500 | 16 | 735.849 | 608.361 | 6,264.125 | 152.081 | 6,999.975 | 760.442 | 89.14% | 98.52% |
| 3.11 | 2,000 | 0 | 3,088.338 | 2,548.435 | 0.000 | 0.000 | 3,088.338 | 2,548.435 | 17.48% | n/a |
| 3.11 | 2,000 | 1 | 3,101.993 | 2,440.618 | 1,609.382 | 39.704 | 4,711.375 | 2,480.322 | 47.35% | 98.48% |
| 3.11 | 2,000 | 16 | 3,022.202 | 2,501.461 | 26,188.011 | 627.050 | 29,210.213 | 3,128.511 | 89.29% | 98.48% |
| 3.11 | 100 | 4 | 150.497 | 124.730 | 315.079 | 23.420 | 465.576 | 148.151 | 68.18% | 95.53% |

The synthetic inputs contain 100, 500, or 2,000 full rows; working scopes contain 2, 4, or 20 IDs. The helper and independent saved-result review confirmed matching IDs and full, active, selected, and working digests, along with accepted-input source signatures. The exact full summary, including per-generation signatures and loaded-source hashes, remains at `/home/bryan/.cache/agent-observer-working-set-20261018/final-cadence-cost-b176/summary.json` (SHA256 `19d2751c67cfeaed5bdee382d7edefdf7185f7571e5a92225e996a21370582dd`).

The 80-trial matrix covered two Python versions, three row counts, read cadences 0/1/16, plus a 100-row cadence-4 lane per version. All 20 cells used the same ABBA order: `a7-full`, `candidate-working`, `candidate-working`, `a7-full`. The saved independent review passed all 355 artifact hashes, 87 raw result hashes, 80-trial arithmetic across 20 cells, and 1,320 loaded-module source references. It reviewed saved outputs only and did not rerun timing. Its first pass contained a reviewer assertion error that compared the scalar `workingScopeMembers` count with an ID list; the preserved diagnostic records that `workingScope.memberIds` is the ID list. The corrected review passed without a producer rerun.

An initial wrapper attempt was stopped by an inherited `RLIMIT_FSIZE` guard after the helper had written a valid JSON result. This was a controller-limit failure, not a helper or product failure. The initial controller and failure record are preserved alongside the final controller. The retry removed that inherited limit, retained bounded per-case timeout and output-size checks, then completed six untimed validations and the matrix.

The raw trial outputs remain in the private cache at `/home/bryan/.cache/agent-observer-working-set-20261018/final-cadence-cost-b176/trials`. The exact pointer and 355-file hash inventory are in `receipt.json` and `snapshots/original-artifact-manifest.json`; raw trial outputs are not duplicated in this repository packet. The seed remains private at the path recorded in the saved summary; its SHA256 is `92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9`. Snapshot hashes are listed in `SHA256SUMS`.
