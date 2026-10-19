# Current support-table density source screen

This is an untimed source-only comparison of the committed receipt-table
representation at Observer `a0d8bbf1f3892eab557ce46e0f841cb8d448ed47` against
the earlier source screen at `610afaac658903ddd6c466c793f9856b45e9f03e`.
It reuses the earlier density runner, fixture helper, seed recipe, and twelve
synthetic input cases unchanged. It does not qualify SDK delivery, provider
behavior, service installation, total heap/RSS, CPU, or deployment.

The candidate was exported with `git archive` from the pinned commit. Its tree
is `48fea754034846dc3a1b20e826264a963be685fb`; the deterministic archive SHA256
is `0fb5ebc8a3b89b6a869586606e87bb58c1b4ecea3524f9675dee36375220791a`. The
seed regenerated from that export is byte-identical to the previous screen:
`92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9`. The runner
and helper hashes remain `de93076d55ba10e1090cddf967cc2b60a15812ea43f1ca787a70840a92181573`
and `ccf91435e078fc5c1aadc5a1070e7e1973bdb06265351a8e1508b07c3644895b`; the
unchanged seed preparer is
`81166d1cd255a91aba729d8042f2c2d9ee38eb14bcaa4f5f92743edc42d1ac41`.
Each density report records all loaded source-module hashes and every case's
accepted input digest, row-byte counts, frame lengths, coverage reason, and
outcome. The diagnostic tracer SHA256 is
`a47cfcc04937309e9bf83b30fc30d54969e3020ef9eca5c7d24f41246977fcd2`; the
comparison script SHA256 is
`dc5c58700a99a049b972de3cce1037d03c25b8cdff389e21f208d8d94fe222d4`.

Both exact installed Python entrypoints ran the unchanged runner with GC
disabled. Each complete case asserts that strict parsed working-set DTOs equal
the independent filter of the full API4 frame. Refused cases remain explicit
`projection_tracking_capacity` outcomes; their small error frame is not counted
as a successful view.

| Rows / selected | Selected original row bytes / full row bytes | Python 3.14 working frame | Python 3.11 working frame | Outcome |
| --- | ---: | ---: | ---: | --- |
| 100 / 5 | 6,435 / 123,475 | 10,926 B | 10,926 B | Complete on both |
| 100 / 10 | 13,006 / 123,886 | 19,784 B | 19,784 B | Complete on both |
| 100 / 20 | 26,011 / 124,571 | 37,494 B | 37,494 B | Complete on both |
| 100 / 24 | 31,213 / 124,845 | 44,578 B | 44,578 B | Complete on both |
| 500 / 25 | 32,445 / 617,645 | 46,346 B | 46,346 B | Complete on both |
| 500 / 50 | 65,026 / 619,426 | 90,624 B | 90,624 B | Complete on both |
| 500 / 100 | 130,051 / 622,851 | 179,174 B | 179,174 B | Complete on both; 71.34% frame reduction |
| 500 / 120 | 156,061 / 624,221 | 214,594 B | 214,594 B | Complete; selected bytes are just over one quarter |
| 2,000 / 100 | 130,051 / 2,470,851 | 1,817 B refusal | 179,174 B | Python-specific tracking outcome |
| 2,000 / 200 | 260,101 / 2,477,701 | 1,817 B refusal | 1,817 B refusal | Tracking capacity |
| 2,000 / 400 | 520,201 / 2,491,401 | 1,817 B refusal | 1,817 B refusal | Tracking capacity |
| 2,000 / 480 | 624,241 / 2,496,881 | 1,817 B refusal | 1,817 B refusal | Tracking capacity |

All twelve input digests, original row-byte counts, and full native frame sizes
match the `610` screen. The compact table materially reduces complete working
frames. At 500 rows / 100 selected, the original selected rows are 20.88% of
the full row bytes and the working frame is 179,174 B versus a 625,195 B full
frame; this case meets the quarter-body and 50%-of-full-frame conditions. The
500 / 120 case is outside the quarter-body condition. The 2,000 / 100 case is
complete on Python 3.11 but refuses on Python 3.14, so the cross-interpreter
capacity result is not equal. The exact per-case comparisons are in
[`comparison.json`](comparison.json); the original `610` reports remain
unchanged and are only referenced as a baseline.

## Single refusal diagnostic

An untimed tracer captured the precise 2,000 / 100 selected acceptance on both
interpreters. It records scalar locals only. On Python 3.14, the rejected member
would take tracking charge to 1,049,055 B against the unchanged 1,048,576 B
limit, a 479 B excess. The attempted plan comprised current charge 1,011,562 B,
compact member 535 B, ledger delta 591 B, prior support-table preflight 36,027 B,
and incremental preflight 340 B. At that point there were 2,000 event guards,
91 candidate ledger entries (53,947 B), one retained support map, and 505 prior
support references. Old-ledger charge was 258 B.

The guard charge is interpreter-specific because `_guard_entry_charge` uses
`sys.getsizeof`: Python 3.14 reports 906,938 B total guard charge (650,000 B
entries + 256,512 B prepaid dictionary table + 426 B shared prefix), while
Python 3.11 reports 890,962 B (634,000 + 256,512 + 450). Both retain the same
2,000 exact identities and the same table reserve. Python 3.14 therefore has
15,976 B more charged guard storage; the refused next member crosses the fixed
tracking cap. Python 3.11 completes with 100 candidate entries, 59,257 B
candidate-ledger charge, and 1,035,863 B combined tracking charge.

This is an observed implementation-specific storage cost: the membership rule
is unchanged, but completion differs at this cap boundary. It is not grounds to
round or lower any charge. The next
source question belongs to a separately reviewed representation slice: whether
the guard can retain only each native ID while the exact four-field identity
prefix remains owned and checked once per context. Any such change must preserve
full identity matching and anti-regression semantics, demonstrate its actual
object topology, and rerun this same pair without reducing the 1 MiB limit.

## Reproduction

Use a private cache directory and a fresh output name; the scripts intentionally
refuse to overwrite prior reports. The seed and report bodies contain synthetic
fixture data only; repository reports store scalar lengths, hashes, and reason
codes.

```sh
TABLE_DENSITY_CACHE=/home/bryan/.cache/agent-observer-working-set-20261018/table-density
rtk mkdir -p "$TABLE_DENSITY_CACHE/source"
rtk git archive --format=tar a0d8bbf1f3892eab557ce46e0f841cb8d448ed47 | rtk tar -xf - -C "$TABLE_DENSITY_CACHE/source"
rtk /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-18-working-set/performance-source/prepare_seed.py "$TABLE_DENSITY_CACHE/source" "$TABLE_DENSITY_CACHE/seed.json"
```

Run the unchanged 12-case runner once per exact interpreter:

```sh
rtk /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-18-working-set/wire-density-source/run_wire_density.py --root "$TABLE_DENSITY_CACHE/source" --seed "$TABLE_DENSITY_CACHE/seed.json" --fixture-helper docs/evidence/2026-10-18-working-set/performance-source/read_matched.py --source-revision a0d8bbf1f3892eab557ce46e0f841cb8d448ed47 --output "$TABLE_DENSITY_CACHE/wire-314.json"
rtk /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python -B docs/evidence/2026-10-18-working-set/wire-density-source/run_wire_density.py --root "$TABLE_DENSITY_CACHE/source" --seed "$TABLE_DENSITY_CACHE/seed.json" --fixture-helper docs/evidence/2026-10-18-working-set/performance-source/read_matched.py --source-revision a0d8bbf1f3892eab557ce46e0f841cb8d448ed47 --output "$TABLE_DENSITY_CACHE/wire-311.json"
```

The checked-in `wire-314.json` and `wire-311.json` were produced by those exact
calls with the output path redirected into this evidence directory. The separate
[`diagnose_tracking_refusal.py`](diagnose_tracking_refusal.py) tracer and
[`compare_density.py`](compare_density.py) comparison script reproduce the
scalar diagnostic and cross-version/baseline analysis. No source, cap, fixture,
or original report was modified for this screen.

The current reports are pinned by
`wire-314.json` SHA256
`0223b84d1827cb268df1de56a2e37a08aaaf4d6fc3aefcd4a54663afd93c7bfc`,
`wire-311.json` SHA256
`99862516bf2e14d31efddfc6976a54fcb5b12dc5370d994c69aebf8a700e58ff`, and
`comparison.json` SHA256
`c29c3aa20cb5e4ee7a52c6b63b87c340540b18f410a7c079c0b2035938ef565e`.
