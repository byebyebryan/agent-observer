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
| B6 package/installed read client | A3 installed and byte/schema/entrypoint verified independently on Snap and Starship; explicit CLI and transient user-unit acceptance passed |
| B7 native/resource/lifetime | A3 ordinary/native entry/age/resume/Codex recovery, Claude blocked/parked, forced publisher recovery and maximum-frame measurements passed; sustained/retirement checks running |
| B8 final handoff/cleanup | Pending |

The existing pure API 1 and observation snapshot/watch 3, write 1 remain the
baseline. The new service protocol starts as a separately prerelease version 1.
Accepted checkpoints, candidate identity and proof ownership are recorded here
as execution advances. Candidates are installed separately; no normal service or
Observer link has been selected.

## Owned-worker repair checkpoint

Review found that the nested Claude SDK metadata helper started its own session,
so an outer service deadline could miss it. Service collection now keeps that
helper in its verified owned group. Direct history collection retains its
separate helper group. The supervisor also keeps an exited leader unreaped until
owned group cleanup; a leader crash cannot orphan its helper. Actual subprocess
tests exercise both deadline and crash cases. A fresh a2 candidate follows this
repair; a1 evidence is retained separately.

A3 (`e39fbef`) also adds an independent hard worker deadline. A publisher SIGKILL
cannot leave the owned metadata worker/helper group running indefinitely. The
actual installed forced-exit/restart proof passed on both hosts.

## Installed checkpoint

Final candidate so far: `0.4.0a3`, source `e39fbef02455dd791d9b57dea7679862763340db`,
wheel SHA256 `e90edba4ceaf0609cfac0b382053165c544497305a1256b92233e1de5827fbfa`,
prefix `/home/bryan/.local/share/agent-observer/0.4.0a3-e90edba4ceaf0609` on both
hosts. Snap uses the Claude-history profile; Starship uses core.

See the [implementation evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md)
for scoped acceptance. Cached reads met the initial latency target. The first
30-minute Snap run exceeded the 5-percent CPU tuning target; an explicit
30-second runtime/120-second history configuration is under sustained retest.
The default remains 20/60 seconds. Physical suspend and the native retirement
predicate remain unaccepted while their respective gates are pending.

## Outcome reconciliation repair

Review found that an older history completion could override a newer runtime
sample explicitly reporting a turn in progress; the reverse sampling order had
the same problem. The latest explicit new-turn evidence now clears the older
outcome, including after its lease expires. Only a subsequently sampled terminal
outcome restores a completed/failed/cancelled value. API 1 and service schemas
are unchanged. A4 will freeze and independently validate this producer repair.
