# Final SDK watch-copy CPU evidence

This packet records the V3.6 matched full-versus-working-set watch-copy CPU
screen on the pinned Observer/Mesh pair. It is a bounded source measurement of
the synthetic workload described below, not producer, installed, or deployed
acceptance.

The experimental unit is one fresh three-generation process trial. For each
Python/row-count cell, the result is the median of the two complete three-
generation totals per variant. The calculation does not pool the six individual
generation samples. Reductions below are `100 × (1 − working/full)` from those
two medians.

| Python | Rows | Full median (ms) | Working-set median (ms) | CPU reduction |
| --- | ---: | ---: | ---: | ---: |
| 3.14.8 | 500 | 2,139.1867285 | 350.5710600 | 83.6119468% |
| 3.14.8 | 2,000 | 9,308.6259350 | 1,306.4681130 | 85.9649735% |
| 3.11.17 | 500 | 2,257.0082380 | 397.9470150 | 82.3683845% |
| 3.11.17 | 2,000 | 9,955.0192650 | 1,508.6068130 | 84.8457670% |

Each cell used four fresh processes in full, working, working, full order. The
16 trials contain 48 accepted generations and four detached local facade copies
per generation. Those copies are local reads, not four SDK deliveries. Selected
row counts were 4 at 500 inputs and 20 at 2,000 inputs. Each trial's outputs
matched its independently constructed expected DTOs and IDs; primary cross-run
checks found no membership/ID mismatch. The ABBA manifest records all 16
trial report hashes; the reconciliation records the whole-trial totals.

The timed work begins at synthetic accepted generation creation and includes
Observer native IPC, public Mesh watch/proof acquisition, and the four facade
copies. The fixture, imports and constructors, native provider collection,
collector parent parsing, independent oracle, hash comparisons, and post-close audit are
outside the interval. Each process used `collect=False`, cyclic GC disabled,
and the shared CPU lock. This exercises the public local watch/proof pipeline
over trusted same-host IPC; it does not collect from a provider or prove SSH,
authentication, or installed-service behavior.

Public completed-sender and validated-receiver JSON-line counters include
teardown. They matched in 11 of 16 trials; that equality is diagnostic only.
These counters are not physical wire bytes or proof that a peer parsed every
byte. The run did not evaluate an RSS, Python-heap, global-memory, native
provider, installed-runtime, authenticated transport, or deployed-consumer
acceptance gate. No wire-savings conclusion follows from these CPU results.

## Provenance and preserved history

Observer `b176ac06b39daeead4be0a33ff9d781304091fe0` and Mesh
`c06b33e058339d9d1d89ecf6844044867d816c58` were the exact source pair. The
Observer export had 2,223 verified files; its archive SHA-256 is
`a1785e81f1f998a134cf23f283eb638f398b681395ab71a4c69948f26e78c47e` and its
manifest SHA-256 is
`c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877`. The
primary check verified 920 loaded module references and all 16 runner copies.
The exact Python entrypoints and source pins are in the [ABBA
manifest](summaries/abba-manifest.json).

The [primary CPU reconciliation](summaries/primary-cpu-reconciliation.json),
ABBA manifest, 16 exact trial sidecars, and exact controller and trial-runner
bytes are included. The 16 large row-shaped trial reports are not copied; their
hashes remain in the ABBA manifest. The included runner snapshots use the
recorded private source paths. Reproducing the run requires those original
source exports, Mesh checkout, interpreter paths, and a separate fresh output
directory. The preserved controller writes beneath its own directory, so copy
both runner files to an untracked private directory before using its `--run-id`
command; do not launch it from this evidence packet. This packet was not rerun
during packaging.

V3.5 remains a separate failed measurement. Its [README](history/v3.5/README-v3.5.md)
and [first-trial failure record](history/v3.5/failure-after-py314-500-00.json)
are preserved byte-for-byte.
The [preserved-artifact pointers](history/v3.5/preserved-artifact-pointers.json)
identify the original row-shaped V3.5 report and counter-classifier test by
their original private paths and hashes; those files were not copied or
changed. V3.5 counter-equality/teardown observations and earlier harness
failures are not rewritten or promoted by this V3.6 result.

The [receipt](receipt.json) records the source, trial, and copied-artifact
hashes. [SHA256SUMS](SHA256SUMS) covers this README, the receipt, and every
included artifact; it does not hash itself.
