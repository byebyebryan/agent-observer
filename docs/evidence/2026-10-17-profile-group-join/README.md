# Observer patch and Mesh group ownership join

This checkpoint joins immutable Observer runtime
`b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f` with Mesh runtime
`4301339515e84f2edb63c88a886380bcde56c621`, from Mesh evidence
`aa4a7fd7b265c18ac6c45144e2462f0b0b5e2024`. No production source, public API,
schema, encoding ID, package version, cap or selected artifact changes here.

All 99 unchanged focused methods pass on each Python 3.14.8 and 3.11.17 with
cyclic GC disabled: 64 Observer patch/profile/codec/read methods and 35 Mesh
compact methods. This independently executes owning tests rather than adding
independent test design. Exact loaded source paths and hashes match the exports.

The Mesh diff validates exact sided identity/birth before sharing the admitted
alias record-ref Atom. A bounded stage owner pools cohort Atoms. Canonical group
markers have explicit heap and encoded-buffer ownership, and ordered aliases
drop before their marker owners. Fixed group metadata still lasts through
finish or rollback. The current owning tests find no public-interface conflict;
Mesh's separate topology/negative evidence retains its own source boundary.

## Unchanged shared-ledger intake probe

The [runner](qualify_join.py) uses byte-pinned utilities from the
[previous join](../2026-10-17-profile-phase-join/README.md), exports both commits,
verifies 212 Observer and 260 Mesh inputs plus eight protected inputs, and checks
88 upstream artifacts. It executes the original Mesh intake probe unchanged.
The twelve screens run serially under the shared advisory lock, with actual
compact native IPC and `open_session(cache.input_owner())` on one original
32 MiB encoded / 64 MiB heap source/Reader ledger. Native owner memory has its
separate account.

| Rows/backend | Python 3.14.8 heap peak | Python 3.11.17 heap peak | Outcome |
| --- | ---: | ---: | --- |
| 100 default | 15,216,435 B | 15,262,379 B | Baseline, two generations and fresh native heads pass |
| 100 private packed | 14,083,354 B | 14,129,298 B | Same |
| 500 default | 37,485,289 B | 37,700,833 B | Same |
| 500 private packed | 30,583,233 B | 30,798,777 B | Same |
| 2,000 default | 61,330,663 B | 62,021,983 B | Baseline admission refuses `sync_decoded_capacity` |
| 2,000 private packed | 67,108,368 B | 67,108,357 B | Same |

The 500-row peak is 805,763 bytes lower on Python 3.14 and 821,683 lower on
Python 3.11 than the prior exact `b6ce842`/`13876e6` join, for both backends.
These are accounted ledger high-water bounds, not physical heap/RSS or CPU
savings. Later progress can increase a failing case's peak. Both packed 2,000
cases reach within hundreds of accounted bytes of the heap cap and still refuse;
this is no capacity or usable-headroom acceptance.

All four 2,000-row cases refuse before proof scratch, confirm no large view and
deliver no recovery. Every case retains actual failure objects with GC disabled
and finishes with six Reader ledger counters zero. Encoded peaks remain below
33,554,432 bytes. The source-only full workload has 710 / 3,510 / 14,010 native
membership cells at 100 / 500 / 2,000 rows; it is not dense nine-field coverage.
No additional private scalar audit or instrumented timing is claimed here.

## Acceptance boundary

The [receipt](receipt.json) binds all reports/logs, source inventories, loaded
modules, unchanged upstream artifacts and the prior joined receipt. The earlier
negative baselines, prior topology measurements and source failures stay exact.
This run has no harness setup failures or source modifications.

The probe uses disclosed test nonce/native pin/proof carrier, extra prepaid
proof scratch, synthetic Reader time and an explicitly test-owned packed arena.
No factory enables the private backend. Neither ordinary authenticated Reader
routes nor relay/controller intake, absolute 2s/15s deadlines, inclusive physical
32/64 MiB memory/RSS/plateau, full plus active/slow peers, dense 2,000-row capacity,
delivered cold recovery, populated native providers/fixed SSH or immutable
installed-pair acceptance is established. The original owner CPU hard failures
are unchanged; there is no producer readiness, artifact/ID/schema freeze,
selection, sibling edit or rollout. Git attribution cleanup remains **HOLD**.

Reproduce using the same dependency environments:

```text
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-17-profile-group-join/qualify_join.py --observer-repo /home/bryan/code/agent-observer-active-feed --mesh-repo /home/bryan/code/mesh-plus --python311 /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python --output .cache/new-profile-group-join
```
