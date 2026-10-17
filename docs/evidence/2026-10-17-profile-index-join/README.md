# Observer patch and Mesh index workspace join

This checkpoint joins immutable Observer runtime
`b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f` and Mesh runtime
`231a631337bb8c4d5feb7cd7d7c8193ef29b5ffc`, from Mesh evidence
`103f3b3056d5f88d4e72e6556e7af6e8ff2e7aed`. No production source, shared API,
schema/encoding ID, package version, cap or selected artifact changes here.

Each Python 3.14.8 and 3.11.17 passes 64 unchanged Observer
patch/profile/codec/read methods and 68 unchanged Mesh
reconstruction/compact/ordered/packed/workspace methods. The 132 methods per
Python run in separate fresh Observer/Mesh interpreters to avoid cross-repository
fixture-module collisions, with cyclic GC disabled throughout. This is
independent execution of owning tests, not independent test design. Every loaded
project file matches its exact immutable source.

The Mesh diff retires compact index/rule duplicate and bulk containers at their
actual phase boundaries after constructor/validator cleanup and sanitized
failures. Caller patch/DTO credit remains held through finish or rollback.
Per-record field-list credit stays separate, and exact duplicate fields reject
before append. The existing public profile/source/codec seam fits this pair;
there is no API or authority relaxation. Expanded-route prepayment stays on its
original route. Mesh's independent topology/negative evidence retains its own
source scope and is not reassigned to Observer's patch.

## Original shared-ledger intake probe

The [runner](qualify_join.py) exports both commits, verifies 212 Observer and
262 Mesh source/test/schema/script inputs plus eight protected inputs, and checks
the four immutable upstream packets. It executes the original Mesh intake probe
without changes, serially under the shared advisory lock. The disposable compact
native Runtime/source IPC and Reader share the original 32 MiB encoded / 64 MiB
heap ledger. Native owner memory has its separate account.

| Rows/backend | Python 3.14.8 heap peak | Python 3.11.17 heap peak | Outcome |
| --- | ---: | ---: | --- |
| 100 default | 14,906,203 B | 14,951,363 B | Baseline, two generations and fresh native heads pass |
| 100 private packed | 13,713,787 B | 13,759,731 B | Same |
| 500 default | 35,932,113 B | 36,146,873 B | Same |
| 500 private packed | 28,714,434 B | 28,929,978 B | Same |
| 2,000 default | 67,108,005 B | 67,108,591 B | Baseline admission refuses `sync_decoded_capacity` |
| 2,000 private packed | 67,108,500 B | 67,108,813 B | Same |

Compared with the [prior exact group join](../2026-10-17-profile-group-join/README.md),
500-row default peaks are 1,553,176 / 1,553,960 bytes lower on Python 3.14 / 3.11;
packed peaks are 1,868,799 bytes lower on both. These are accounted high-water
bounds, not physical heap/RSS or matched CPU savings. The 2,000-row cases reach
later refusals near the cap; their higher peaks do not establish capacity or
usable headroom. All four refuse before proof scratch, confirm no large view
and deliver no recovery.

Every case retains actual failure objects with GC disabled and finishes with
six Reader ledger counters zero. Encoded high-water bounds stay below 33,554,432
bytes. Full-only synthetic fixtures have 710 / 3,510 / 14,010 native membership
cells at 100 / 500 / 2,000 rows. This is not dense nine-field, full plus active,
multi-source or slow-peer coverage. No extra private scalar audit or instrumented
timing is claimed by this checkpoint.

## Acceptance boundary

The [receipt](receipt.json) binds all reports/logs, loaded source hashes, upstream
artifacts and the unchanged prior joined receipt/artifacts. Utilities are reused
only at their exact committed bytes. This run has no harness setup failures or
source changes. Earlier before/after topology and capacity failures remain tied
to their original tuples.

The probe discloses a test nonce/native pin/proof carrier, extra prepaid proof
scratch and synthetic Reader time. The private packed arena is explicitly
test-owned; no factory enables it. Neither ordinary authenticated Reader routes,
relay/controller intake, absolute 2s/15s deadlines, inclusive physical 32/64 MiB
memory/RSS/plateau, dense 2,000-row capacity/delivered cold recovery, populated
native providers/fixed SSH nor immutable installed-pair acceptance is established.
The owner CPU hard failures remain unchanged. There is no producer readiness,
artifact/ID/schema freeze, selection, sibling edit or rollout. Git attribution
cleanup remains **HOLD**.

Reproduce using the same dependency environments:

```text
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-17-profile-index-join/qualify_join.py --observer-repo /home/bryan/code/agent-observer-active-feed --mesh-repo /home/bryan/code/mesh-plus --python311 /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python --output .cache/new-profile-index-join
```
