# Focused collector cost follow-up

The [read-delivery pass](read-delivery-follow-up-plan.md) measured the existing
a11 collector while preserving its process and selection. Ten-minute windows
without added readers used about 55% of one core on Snap and 37% on Starship.
These are ordinary active hosts, not idle benchmarks. Collection helpers are
included; provider daemon and remote SSH server costs are excluded.

An isolated cached-data study identifies a strong candidate cause:
`ObservationEngine.expire()` invokes runtime-only retention reconciliation on
every service loop, roughly every 50 ms. The reconciliation repeatedly validates
and canonicalizes all saved identities even when no retirement deadline exists.
With the actual cached rosters, 200 calls consumed 3.53 CPU seconds for Snap's
129 rows and 5.08 seconds for Starship's 354 rows. Skipping the scan in the
isolated fixed-clock study reduced this to less than 0.001 seconds. The study
does not establish repair correctness or exclusive attribution of live CPU.

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
