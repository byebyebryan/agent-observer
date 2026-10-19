# Working-set cadence source cost

This report qualifies a narrow, synthetic source component at a7 7807160384ba39b4d438c5c7f1b5f316c3608dcd and current Observer b176ac06b39daeead4be0a33ff9d781304091fe0. It calls the exact tracked read_matched.py helper from the current export, with a7 full feed as baseline and current working projection as candidate.

The measured work is ServiceState.attempt plus ServiceState.accept per generation and, for each requested sequential read, complete local native-frame creation, canonical LF serialization, strict parser admission, and selected-row filtering. Each trial has one untimed warmup plus six measured generations; collection and equality assertions outside CPU windows remain in the helper. GC is disabled. Whole-trial CPU and local serialized-byte totals are reported as the median of two six-generation ABBA trials per lane.
Each cell is bounded to this synthetic population. Positive CPU reductions in these sampled cells do not establish a universal saving at every cadence, population, or production workload. Candidate-full was exercised only in the untimed validation preflight; the measured candidate lane is candidate-working.

| Python | Rows | Reads / generation | A7 accept ms | Candidate accept ms | A7 read ms | Candidate read ms | A7 combined ms | Candidate combined ms | Combined CPU reduction | Local frame-byte reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| py314 | 100 | 0 | 135.167 | 106.298 | 0.000 | 0.000 | 135.167 | 106.298 | 21.36% | n/a (zero measured reads) |
| py314 | 100 | 1 | 129.190 | 106.510 | 79.901 | 6.823 | 209.091 | 113.333 | 45.80% | 95.53% |
| py314 | 100 | 16 | 130.473 | 107.445 | 1292.330 | 105.049 | 1422.803 | 212.494 | 85.07% | 95.53% |
| py314 | 500 | 0 | 636.542 | 511.889 | 0.000 | 0.000 | 636.542 | 511.889 | 19.58% | n/a (zero measured reads) |
| py314 | 500 | 1 | 633.108 | 514.510 | 404.110 | 11.239 | 1037.218 | 525.749 | 49.31% | 98.52% |
| py314 | 500 | 16 | 641.632 | 516.433 | 6509.549 | 170.818 | 7151.181 | 687.252 | 90.39% | 98.52% |
| py314 | 2000 | 0 | 2590.412 | 2075.496 | 0.000 | 0.000 | 2590.412 | 2075.496 | 19.88% | n/a (zero measured reads) |
| py314 | 2000 | 1 | 2565.477 | 2120.197 | 1635.234 | 42.975 | 4200.711 | 2163.172 | 48.50% | 98.48% |
| py314 | 2000 | 16 | 2534.735 | 2062.513 | 25936.345 | 673.899 | 28471.080 | 2736.412 | 90.39% | 98.48% |
| py314 | 100 | 4 | 132.310 | 108.599 | 327.828 | 26.888 | 460.138 | 135.487 | 70.56% | 95.53% |
| py311 | 100 | 0 | 147.894 | 125.138 | 0.000 | 0.000 | 147.894 | 125.138 | 15.39% | n/a (zero measured reads) |
| py311 | 100 | 1 | 149.291 | 125.384 | 78.732 | 6.104 | 228.023 | 131.488 | 42.34% | 95.53% |
| py311 | 100 | 16 | 150.248 | 124.525 | 1256.750 | 91.721 | 1406.998 | 216.246 | 84.63% | 95.53% |
| py311 | 500 | 0 | 733.110 | 604.405 | 0.000 | 0.000 | 733.110 | 604.405 | 17.56% | n/a (zero measured reads) |
| py311 | 500 | 1 | 739.088 | 602.614 | 391.669 | 9.959 | 1130.757 | 612.573 | 45.83% | 98.52% |
| py311 | 500 | 16 | 735.849 | 608.361 | 6264.125 | 152.081 | 6999.975 | 760.442 | 89.14% | 98.52% |
| py311 | 2000 | 0 | 3088.338 | 2548.435 | 0.000 | 0.000 | 3088.338 | 2548.435 | 17.48% | n/a (zero measured reads) |
| py311 | 2000 | 1 | 3101.993 | 2440.618 | 1609.382 | 39.704 | 4711.375 | 2480.322 | 47.35% | 98.48% |
| py311 | 2000 | 16 | 3022.202 | 2501.461 | 26188.011 | 627.050 | 29210.213 | 3128.511 | 89.29% | 98.48% |
| py311 | 100 | 4 | 150.497 | 124.730 | 315.079 | 23.420 | 465.576 | 148.151 | 68.18% | 95.53% |

## Fixture parity and source identity

Candidate export manifest c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877 binds 2223 tracked files to b176; all exported file bytes matched the Git tree. The a7 package export matched 63 Git blobs. The candidate export also contained 94 pre-existing cache extras (a7 had 0); these were excluded from tracked comparisons, left unchanged, and runs set PYTHONDONTWRITEBYTECODE=1. The helper SHA256 is ccf91435e078fc5c1aadc5a1070e7e1973bdb06265351a8e1508b07c3644895b and seed SHA256 is 92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9. Every measured trial preserves seven canonical accepted-input digests; the summary records the aggregate and each generation signature. The helper asserts selected identity membership and DTO equality on every measured generation/read; the analyzer independently checks current working-scope member IDs against the deterministic fixture IDs.

The input is synthetic. At 100/500/2,000 full rows the fixture has 1/2/10 running rows and an equal number of recent parked rows; the rest are old parked rows. A working scope therefore contains 2/4/20 synthetic IDs. Full, active, selected, and working-selection digests matched across both Python versions and both ABBA lanes. GC remained disabled in every result.

The current candidate receives a trusted synthetic accepted BOOTTIME directly. This source component does not qualify worker provenance or reproduce primary full-pipeline metadata. It does not measure canonical native collection, parent parsing, SDK streams, actual Readers or concurrent reads, sockets, SSH, Mesh proof/delivery, physical transmission, RSS/heap, installed runtime, provider behavior, or production acceptance. Cadence 16 means sixteen sequential local reads per generation in one helper process; it is not sixteen simultaneous Readers. Serialized bytes are local encoded frames including LF, not delivered wire bytes.

## Timing and artifact bounds

The 80 fresh-process matrix trials completed in 351.453s under the exclusive shared lock, with a 180s maximum per case and 900s matrix budget. The initial wrapper attempt01 is preserved in the artifact manifest; the helper wrote a valid result, but the wrapper was terminated by the controller inherited RLIMIT_FSIZE guard after the result write. The retry removed that faulty guard, retained the per-case timeout/post-run size checks, and passed six untimed 100-row checks before the matrix.

All 80 measured raw result JSON files are SHA256-listed in artifact-manifest.json, along with validation outputs, per-trial invocations/logs, controller inputs, progress, and status. Full per-cell raw trial values, digests, identities, input signatures, serialized bytes, and exact loaded-module source hashes are in summary.json.
