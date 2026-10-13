# Offline Observer timing execution

2026-10-12. Authorized goal: finish the timing design, recovery/race validation,
bounded standalone model and proposed contract/acceptance cases while the Mesh
Plus networking/performance loop runs independently.

## Work boundary

This pass owns only new timing research documents, sanitized evidence and an
offline model under `docs/evidence/2026-10-12-timing-design/`. It uses the earlier
[native timing receipts](evidence/2026-10-12-codex-timing/REPORT.md) and synthetic
cases. No provider queries, actions, hooks, new sessions or runtime workload are
needed. No production package, test suite, schema, validator, codec, publisher,
Mesh profile, selector, service or provider configuration is edited. Whole
project checks run once after the offline changes are complete.

The current API 2/read 4/Service 2/Mesh SDK 1 tuple remains implemented. A timing
successor is a design proposal until source/schema/artifact/native and scoped
operational gates accept it. Mesh owns its simultaneous work and profile/lock
decisions; this pass does not require that external loop to finish.

## Checkpoints

| Gate | Deliverable | Acceptance |
| --- | --- | --- |
| T0 | Evidence inventory, owned scope and protected-source baseline | Prior native/synthetic/ordinary bounds retained; no repeated provider work |
| T1 | Named clock semantics, receipt attribution and derived-age rules | Native turn/update/activity and observed-series clocks stay distinct |
| T2 | Bounded standalone timing model and recovery/race fixtures | Meaningful unknown/gap/restart/late/same-phase/lease/capacity cases pass |
| T3 | Provider-neutral timing proposal and producer acceptance matrix | Exact draft layout, future integration gates and client limits are reviewable |
| T4 | Independent reread, source-preservation audit and checks | Findings reconciled, evidence sanitized, production/networking work untouched |

The [draft timing specification](timing-contract-proposal.md) and
[offline report](evidence/2026-10-12-timing-design/REPORT.md) will record the
completed gates. Native seconds/milliseconds and independently sampled phase
and latest-turn metadata must remain explicit. A sampled observation series
never proves continuous native phase duration or a notification timeline.
