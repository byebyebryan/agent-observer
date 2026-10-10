# Focused collector cost follow-up

The [read-delivery pass](read-delivery-follow-up-plan.md) measured the existing
a11 collector while preserving its process and selection. Ten-minute windows
without added readers used about 55% of one core on Snap and 37% on Starship.
These are ordinary active hosts, not idle benchmarks. Collection helpers are
included; provider daemon and remote SSH server costs are excluded.

The [live profiling pass](evidence/2026-10-09-collector-cpu/REPORT.md) confirms the
main cause: `ObservationEngine.expire()` invokes runtime-only retention
reconciliation on every service loop. It rebuilds and repeatedly validates saved
identities even when no retirement deadline exists. The selector's 50 ms timeout
is a maximum idle wait, not a fixed iteration rate. The a11 retention change
`4f99e0d` introduced this path.

Consistent stack samples place about 95%/97% of captured Python execution inside
retention on Snap/Starship. Root/helper CPU is measured separately: Snap used
47–51% of one core in the collector and 10–12% in owned helpers; Starship used
36–38% and about 1%. A final unprofiled minute confirms the persistent cost.

Fresh cached studies use each collector's exact a11 package and interpreter
(Snap Python 3.12.8, Starship Python 3.14.7). With 128/354 saved rows and no
retirement deadlines, expiry still performs 768/2,124 identity validations per
call. The fixed-clock full scan costs 56.8/37.4 ms per call; direct trusted keys
in the isolated replica cost 0.69/0.88 ms. Skipping the scan costs less than
0.001 CPU seconds for 200 calls. The earlier Snap study used a different
interpreter. These counterfactuals establish avoidable work, not production
repair correctness or an exact live CPU floor.

This is a producer checkpoint, separate from the a13 reader selection. The
read-delivery pass changes no collector, cadence, provider settings or retention
semantics. Its [acceptance report](evidence/2026-10-09-read-delivery/REPORT.md)
records the complete measurement matrix and exclusions.

The [a14 repair report](evidence/2026-10-09-retention-cpu-repair/REPORT.md)
records completed C0–C5 source, artifact, native, sustained candidate/normal
CPU and scoped operational gates. Normal services select a14 on both hosts;
root/total CPU is 2.72/11.01% of one core on Snap and 1.12/2.02% on Starship. The implementation caches only a provider dirty flag
and its next eligible deadline; it reuses validated keys within changed
reconciliation instead of maintaining persistent full-roster indices.

## Execution gates

The user authorized the repair goal loop after live profiling. Keep this a
producer-only pass: API 2/wire 4/Service 2, provider policy, read CLI selection,
writer, Mesh bridge and downstream clients remain independently selected.

- C0: review mutation/expiry ownership and freeze the full-scan reference in
  test-only code. Admission still validates and owns copies of provider data.
- C1: mark retention reconciliation dirty on accepted receipts, source failure
  and lease expiry. Reuse each row's validated key within reconciliation and
  cache the next eligible retirement deadline. Unchanged ticks do no roster
  scan; current/saved protection still requires invalidation when receipts change.
  Compute the next deadline after ledger pruning, including missing-ledger
  candidates, so the optimization cannot postpone an existing omission.
- C2: prove old/new fixed-clock behavioral parity and quiet-tick cost, including
  mixed providers, history/runtime replacement, positive saved enrichment,
  context changes, failures, rejected samples and exact expiry boundaries.
- C3: freeze an immutable successor wheel. Independently verify installed bytes,
  regressions, native direct/cached/push comparisons and retention behavior on
  Snap and Starship before accepting the artifact.
- C4: measure at least ten minutes of ordinary candidate service costs on both
  hosts, separating root/helpers and reporting memory. Accept the repair only
  with a material CPU reduction and preserved observation behavior.
- C5: perform scoped Observer collector selection with rollback/reselection and
  normal-unit native/CPU checks. Preserve provider sessions and the separately
  selected reader/writer/bridge. Commit accepted checkpoints.

The cache is private optimization state, not a new public field or provider
evidence source. No fixed CPU floor is promised before live measurement.

## Required invariants

1. Maintain validated identity sets and retirement candidates at admission or
   replacement, and avoid roster scans when no candidate deadline can expire.
   Keep normal lease expiry cheap and preserve the original unsaved deadline.
2. Prove parity for current rows, positive saved identity, disappearing unsaved
   rows, repeated partial receipts, source failures, changed context, enrichment
   and history/runtime replacement. Omission remains observation-memory
   retirement; it supplies no parked classification or action permission.
3. Compare old/new pure-engine output using fixed-clock, mixed-provider rosters.
   Measure unprofiled CPU and allocations separately from profiler overhead.
4. Build an immutable collector candidate, run the independent native comparison
   on both hosts and repeat at least ten minutes of ordinary service costs.
   Decide selection only after source, artifact, native and operational gates.

Mesh bridge and fleet-reader CPU also increase with subscribers. Their recorded
costs warrant a separate Mesh investigation into repeated validation, copying
and per-reader SSH work. These observations do not authorize pooling, a broker,
new transport contracts or networking changes in Observer.

## Separate residual cost work

The retention repair removes the profiled root hotspot. Snap still spends
material CPU in owned collection helpers under active Claude/native-hint load.
The [residual profiling pass](evidence/2026-10-10-residual-collector-cpu/REPORT.md)
attributes the remaining Snap helper cost: hint-driven full Claude history scans
and duplicate activity/kind transcript decoding dominate; the hint listeners are
cheap. A fresh five-minute ordinary-workload window totals 6.91% of one core,
including at least 3.55% in Claude history workers/helpers. This does not replace
the preceding 11.01% ten-minute measurement or promise an idle floor. The proposed
first repair shares bounded transcript parsing, with behavioral parity and
independent installed/native/sustained-cost gates before collector selection.
Normalized metadata reuse was subsequently authorized through its separate
implementation and measurement gates.
The user subsequently authorized shared parsing and change-aware normalized
metadata reuse in the [Claude collection execution](claude-collection-cost-plan.md).
Its [acceptance report](evidence/2026-10-10-claude-collection-repair/REPORT.md)
records source, immutable/native, concurrent cost comparison and scoped selection
evidence. Normal services advance to a15 with unchanged API/cadence/hints.
The final normal-unit sustained acceptance remains part of that report.
It must preserve independent history/runtime clocks, accepted cadence/hints,
source faults and native classification. No cadence or native scope is relaxed
to make the retention repair look cheaper.

Mesh bridge/fleet subscriber costs remain in the separate Mesh thread. The
current a14 acceptance does not promise an idle floor, native event completeness,
provider outcomes beyond existing support or terminal/action authority.
