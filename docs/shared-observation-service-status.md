# Shared service implementation status

Date: 2026-10-06. Regular implementation goal started from `dc92725`.
Follow the [batch runbook](shared-observation-service-batch-plan.md).
Normal provider sessions, hooks, selected Observer links and downstream clients
remain outside this loop. Physical suspend is a separate pending gate.

| Checkpoint | Status |
| --- | --- |
| B0 preflight/context | Clean source; Snap/Starship CLI/tool/SSH preflight available; native topology rechecked during installed proof |
| B1 service contract/reader | In progress |
| B2 scheduler/state/fan-out | Pending |
| B3 owned collection | Pending |
| B4 Codex cadence | Pending |
| B5 Claude cadence | Pending |
| B6 package/installed read client | Pending |
| B7 native/resource/lifetime | Pending |
| B8 final handoff/cleanup | Pending |

The existing pure API 1 and observation snapshot/watch 3, write 1 remain the
baseline. The new service protocol starts as a separately prerelease version 1.
Accepted checkpoints, candidate identity and proof ownership are recorded here
as execution advances. No service is selected or installed by this initial note.
