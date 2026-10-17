# Observer patch and Mesh phase source join

Observer runtime `b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f` and Mesh runtime
`13876e6d723ad3ff5511c12e2900e7dc34f2c778` join through the existing public
profile/codec/source APIs. Mesh evidence is immutable
`2385712df2f0ea8ba0697facf01ae2543fb377d2`. No production source, public ABI,
contract, cap, schema, encoding ID, version or selected artifact changes here.

The bounded source check passes 93 methods on each Python 3.14.8 and 3.11.17,
with cyclic GC disabled: 64 unchanged Observer patch/profile/codec/read methods
and 29 unchanged Mesh compact methods. Module paths and hashes are checked
against the exact exports. This is independent execution of owning tests, not
independent test design or whole-producer acceptance.

The Mesh source diff retains original tracked key Atoms in each phase's
duplicate dictionary. The iterator closes and actual phase references clear
before phase credit retires; delta operation credit still lasts through finish
or rollback. Observer's grouped tokens, final keyed writes and old/new high-water
credit are unchanged. The joined tests find no public-interface conflict.
The earlier [Observer topology evidence](../2026-10-17-profile-patch/receipt.json)
and Mesh's phase evidence retain their separate proof and source boundaries.

## Shared source/Reader ledger screen

The [qualifier](qualify_join.py) exports both immutable commits, verifies all
212 Observer and 260 Mesh source/test/schema/script inputs and eight protected
inputs, checks 61 upstream artifacts, then uses the original Mesh intake probe
without edits. All twelve cases run serially under the shared advisory lock.
Actual compact native IPC, `open_session(cache.input_owner())`, admission and
fresh actual native heads use one original 32 MiB encoded / 64 MiB heap Reader
ledger. The native owner has its separate account.

| Rows/backend | Python 3.14.8 heap peak | Python 3.11.17 heap peak | Outcome |
| --- | ---: | ---: | --- |
| 100 default | 15,374,226 B | 15,423,290 B | Baseline, two generations and fresh heads pass |
| 100 private packed | 14,241,145 B | 14,290,209 B | Same |
| 500 default | 38,291,052 B | 38,522,516 B | Same |
| 500 private packed | 31,388,996 B | 31,620,460 B | Same |
| 2,000 default | 64,568,959 B | 65,324,247 B | Baseline admission refuses `sync_decoded_capacity` |
| 2,000 private packed | 66,496,563 B | 61,169,817 B | Baseline admission refuses `sync_decoded_capacity` |

All cases preserve the original limits, retain actual failed-operation errors
with GC disabled and finish with all six Reader counters zero. At 500 rows the
joined peak is 968,569 bytes below Observer `b6ce842` with the preceding Mesh
runtime on each backend and Python. These are accounted high-water bounds and
reserved allowances, not physical heap or RSS measurements. Later progress can
raise a failing case's peak; a changed failure peak is no capacity success.

The workload is full-only synthetic 710 / 3,510 / 14,010 membership cells at
100 / 500 / 2,000 rows. It is not dense nine-field, full plus active, slow-peer
or multi-source qualification. Confirmation uses the disclosed test nonce/native
pin/proof carrier, extra prepaid proof scratch and synthetic Reader clock. The
private packed arena is explicitly test-owned; no factory selects that backend.
All 2,000-row refusals precede proof scratch and confirm no large view.

The unchanged private scalar audit on packed 2,000/Python 3.14 reaches all
18,000 field-token writes and 6,004 final index writes. The prior generic
6,146,304-byte callback-patch charge succeeds on this pair. Separate narrow
wrappers observe no failing `BudgetRef.charge` or graph `retain`; a later heap
reservation of 1,050,528 bytes refuses with 8,288,826 committed and 58,199,661
reserved bytes (67,539,015 bytes including the request exceeds 67,108,864).
The captured immediate caller is the unchanged probe's reserve wrapper, so this
does not attribute the underlying allocation to a particular generic method.
All scalar bins and final counters return to zero. Instrumented runs are kept
separate; these cumulative charges and progress observations neither measure
physical storage nor justify reducing the remaining allowance.

## Provenance and limits

The [receipt](receipt.json) binds reports, logs, all loaded project modules,
the unchanged intake probe and upstream artifacts. No old negative baseline or
saved test report is rewritten. An initial harness selected Observer's
same-named compact module: its 74 tests passed, then the count assertion rejected
the run before any capacity case. Explicit-path Mesh loading corrected that
setup. A Python 3.11 launcher symlink was initially resolved past its environment,
so dependency import failed before tests; retaining the launcher path corrected
that setup. Logs remain separate. Completed Python 3.14 reports were verified
and reused without repeating those tests or capacity cases.

This join does not accept physical memory/RSS/plateau, matched CPU, absolute
2s/15s execution, relay/controller/authenticated selected routes, populated native
providers/fixed SSH, delivered 2,000-row cold recovery or immutable installed
pairs. The prior owner CPU increases remain hard failures; no timing from this
instrumented/resource work changes them. Earlier closed source/controller
findings stay closed. Package/schema/encoding allocation and producer readiness
remain open, selected a7/a23 and protected workflows stay unchanged, and Git
attribution cleanup remains **HOLD**.

Reproduce using the same dependency environments:

```text
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-17-profile-phase-join/qualify_join.py --observer-repo /home/bryan/code/agent-observer-active-feed --mesh-repo /home/bryan/code/mesh-plus --python311 /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python --output .cache/new-profile-phase-join
```
