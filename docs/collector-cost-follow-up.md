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

## Proposed next gate

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
