# Shared service implementation status

Date: 2026-10-06. Regular implementation goal started from `dc92725`.
Follow the [batch runbook](shared-observation-service-batch-plan.md).
Normal provider sessions, hooks, selected Observer links and downstream clients
remain outside this loop. Physical suspend is a separate pending gate.

| Checkpoint | Status |
| --- | --- |
| B0 preflight/context | Clean source; Snap/Starship CLI/tool/SSH preflight available; native topology rechecked during installed proof |
| B1 service contract/reader | Pure bounded protocol/schema committed; transport client follows in B6 |
| B2 scheduler/state/fan-out | Controlled sockets, leases, independent jobs and fragmented loss/resync implemented; native/resource gates remain B7 |
| B3 owned collection | Bounded single-provider worker implemented; source-native runtime samples passed, installed proof follows |
| B4 Codex cadence | Runtime skips saved catalog; Snap source sample 160 ms / 3 loaded rows; history 904 ms / 51 rows |
| B5 Claude cadence | Runtime skips SDK history; Snap source sample 375 ms / 6 registry rows; source interpreter has no SDK, installed history proof follows |
| B6 package/installed read client | Explicit CLI and manifest-v2 extension implemented; candidate installation/native checks pending |
| B7 native/resource/lifetime | Pending |
| B8 final handoff/cleanup | Pending |

The existing pure API 1 and observation snapshot/watch 3, write 1 remain the
baseline. The new service protocol starts as a separately prerelease version 1.
Accepted checkpoints, candidate identity and proof ownership are recorded here
as execution advances. No service is selected or installed by this initial note.

## Owned-worker repair checkpoint

Review found that the nested Claude SDK metadata helper started its own session,
so an outer service deadline could miss it. Service collection now keeps that
helper in its verified owned group. Direct history collection retains its
separate helper group. The supervisor also keeps an exited leader unreaped until
owned group cleanup; a leader crash cannot orphan its helper. Actual subprocess
tests exercise both deadline and crash cases. A fresh a2 candidate follows this
repair; a1 evidence is retained separately.
