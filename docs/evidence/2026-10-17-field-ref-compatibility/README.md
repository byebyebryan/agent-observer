# Compact field-reference compatibility

Independent focused compatibility passes for Observer runtime
`b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f` and Mesh runtime
`13f27e25c46e1fd3da664975e964104a56fd6dbf`. Observer is exported from evidence
`7e496b2b0555a76e7c381b1d5e6cada63f441c7b`; Mesh evidence is
`30e20118790ab83f526b2436d0739b7f531b4ed1`. No production source, public API,
schema/ID, package version, cap or selected artifact changes here.

The [qualifier](qualify_compatibility.py) independently runs 64 unchanged Observer
patch/profile/codec/read methods and 72 unchanged Mesh
reconstruction/compact/ordered/packed/workspace methods on each Python 3.14.8
and 3.11.17. All 136 methods per Python pass with cyclic GC disabled, no failures,
errors or skips. Each owning suite uses a separate fresh process to preserve
same-named fixture modules. Exact loaded project hashes match Git exports.
This is independent execution of owning tests, not independent test design.

The reviewed diff validates the complete record reference and birth before
borrowing an exact retired reference or AFTER alias owner. Unmatched references
keep the original owned path. Transient comparison bytes remain prepaid on
heap and encoded ledgers until their local references drop. Current record,
field token, native/index root and membership checks remain in place; expanded
admission and callback/DTO contracts stay unchanged. No public seam conflict is
identified within these tests.

## Saved Mesh evidence verified without replay

The qualifier verifies 262 current and 262 before Mesh inputs, 212 Observer
inputs, eight protected inputs, all 52 new Mesh artifacts and 56 prior Mesh
join artifacts. It also checks the original Observer patch/group/index receipt
pins, the declared before overlay and loaded hashes in saved reports. The
[receipt](receipt.json) separates these checks from our independent executions.

Mesh's saved twelve intake screens and extra scalar audit are **read/hash-checked
only**, without new capacity or audit execution. Their original provenance is
unchanged: eight 100/500-row cases complete baseline, two generations and fresh
heads; all four 2,000-row baselines refuse `sync_decoded_capacity` before proof
scratch, with six final Reader counters zero. Saved packed500 peaks are
28,527,235 / 28,742,075 bytes on Python 3.14 / 3.11. These are Mesh's accounted
high-water bounds, not new measurements or physical/RSS savings from this review.

The saved scalar audit has no failing `ledger.retain` call and does not identify
the final reservation's underlying allocator. Final zero bins/counters do not
justify reducing an allowance or raising a cap. Mesh's saved 407-test source
gate and before topology failures retain their original scope; neither is
rerun or reassigned here.

The original intake fixtures share one 32 MiB encoded / 64 MiB heap source/Reader
ledger, with native owner memory separate. Full-only 710 / 3,510 / 14,010 cells,
private nonce/native pin/proof carrier, extra prepaid scratch, synthetic Reader
time and an explicitly test-owned packed arena remain disclosed. No ordinary
authenticated Reader route, relay/controller intake, absolute 2s/15s timing,
inclusive physical/RSS, dense/full-active/slow-peer capacity, delivered 2k cold
recovery, populated native/fixed SSH or immutable installed pair is accepted.
CPU hard failures remain unchanged. No producer readiness, selection, sibling
edit or rollout follows; Git attribution cleanup remains **HOLD**.

Reproduce the focused tests and saved-artifact verification:

```text
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-17-field-ref-compatibility/qualify_compatibility.py --observer-repo /home/bryan/code/agent-observer-active-feed --mesh-repo /home/bryan/code/mesh-plus --python311 /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python --output .cache/new-field-ref-compatibility
```
