# Named Mesh probe on the committed source retirement fix

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The Mesh-owned named retirement probe,
`docs/evidence/2026-10-16-delta-sync/verify_completed_relay_retirement.py`,
at Mesh `835a43055bbb9f18d61c6a19ff1666f048640035` passes all eight
methods on Python 3.14.8 and 3.11.17 against committed Observer
`e3441d017b94ee27f4dfccb5f1f3f30612435adf`. Each run disables cyclic GC
before project imports, retains test errors through cleanup, and has no failures,
errors or skips. The [receipt](../../evidence/2026-10-16-delta-sync-source/source-retirement-owning-replay.json)
contains the exact source inventories, original reports, logs and loaded-module
verification. Mesh runtime remains `6fce5ed0e997d021e7532051fe985c3693962c3e`;
the later Mesh checkpoint has no changes under `src/`, `tests/`, `contracts/`
or `pyproject.toml`.

The named probe preserves the historical completion probe unchanged and inherits
seven methods. Its replacement material-drain method must have the same AST after
changing only the expected registered ref count from zero to five. All four
transaction refs and the exact completion ref remain registered while consuming
pins are live. The runner checks this equality before executing the tests; no
Observer-side adaptation is applied in this replay.

Mesh's before run on Observer `7213084` has seven passes and exactly the expected
ref-count failure on each Python version. That before result belongs to the
Mesh-owned receipt and is verified here without rerunning it. The earlier
[Observer final-pair replay](delta-sync-source-retirement.md), its unchanged
upstream failure, and its explicitly named one-assertion adaptation retain their
original evidence. The original and hardened five-case source regressions and
other owning component suites also retain their existing results; they are not
rerun or reassigned by this eight-method check.

These tests use actual expanded native IPC, the supported source and completion
batch, Mesh relay, ordinary independent Reader, exact native completion, held
writer drains, repeated cancellation, failed writes and sibling cleanup. Reader
and relay counters return to zero under the fixture assertions. Synthetic
ServiceState, trusted direct test control, private nonce setup and separate
fixture/oracle ledgers remain explicit limits. This is source lifecycle evidence,
not ordinary controller/carrier, compact lifecycle, shared 32/64 MiB peaks, CPU,
RSS, dense 2,000-row recovery, populated providers, fixed SSH or immutable
installed-pair acceptance. No runtime, API, schema/encoding identifier, package,
service/provider, sibling or selected-route changes accompany this receipt.

To reproduce, export the exact commits into fresh directories and run the
unchanged Mesh probe with fresh output and log paths:

```sh
rtk proxy /path/to/python -B /path/to/mesh-export/docs/evidence/2026-10-16-delta-sync/verify_completed_relay_retirement.py \
  --mesh /path/to/mesh-export --observer /path/to/observer-export \
  --output /path/to/fresh-result.json --log /path/to/fresh-unittest.log
```

Default mode requires all eight methods to pass. No old-pruning expectation flag
is used for the fixed source.
