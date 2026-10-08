# Shared service implementation status

Historical B0–B8 candidate record: 2026-10-06, with overnight evidence collected
on 2026-10-07 UTC. The [2026-10-07 operational baseline](observer-operations-execution.md)
selected a7 and a persistent Observer-only user unit on both hosts, added
startup workspace configuration and accepted normal-unit restart/crash/rollback.
The [latest delivery](evidence/2026-10-07-native-delivery/REPORT.md) now selects a8
on both hosts. Separately installed a9 implements passive native runtime/history
wakeups; latency/recovery/lifetime subsets pass, but its provisional resource
gate is not accepted. Normal units retain polling without hints. The
[cost follow-up](native-hints-cost-follow-up.md) and current handoff supersede
earlier selection statements below; earlier resource results remain historical.
The separately installed a10 repair scopes Claude hints to the authoritative
history catalog and passes installed noise/primary-append and focused native
regression checks. It also remains unselected with cost/operational gates pending.
The regular goal loop began at `dc92725`; the [batch runbook](shared-observation-service-batch-plan.md)
defines B0–B8. Producer work and client development remain separate.

| Checkpoint | Status |
| --- | --- |
| B0 preflight/context | Snap/Starship topology and isolation rechecked; ordinary sessions retained |
| B1 contract | Separate pure service wire/schema/guard 1; API v1 unchanged |
| B2 scheduler/state/fan-out | Actual controlled sockets, leases, independent jobs, bounded delivery and gap/resync accepted |
| B3 owned collection | Bounded existing-only workers; nested SDK cleanup and independent deadline survive publisher death |
| B4 Codex | Runtime/history split; ordinary and disposable native comparisons on both hosts |
| B5 Claude | Runtime/SDK-history split; ordinary comparisons and disposable blocked/parked proofs on Snap |
| B6 installed client | A6 byte/schema/entrypoint verification on both hosts; pure imports, installed state tests and transient user units accepted |
| B7 operational/native | A6 native entry/age/resume/outage/recovery/outcome/retirement, Claude blocked/parked and 30-minute multi-reader/resource subset accepted |
| B8 closure | Final artifact reverified; proof processes/sockets/native fixtures cleaned; closing preservation checks and producer handoff complete |

## Frozen candidate

`0.4.0a6`, source `c8c3992984e2dfb9aad3d6812ee936babd9bf999`, wheel SHA256
`3c2e5ae28d6e099f4fc8a9559832b813aa7a84286abaada3a815d1b0cf4b46e8`,
installed at `/home/bryan/.local/share/agent-observer/0.4.0a6-3c2e5ae28d6e099f`
on both hosts. Snap uses the source-only Claude-history profile; Starship uses
core. The [manifest](../artifacts/observer-0.4.0a6.json) and
[implementation evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md)
identify exact installed acceptance. API 1 snapshot/watch 3 and write 1 remain
unchanged; service protocol 1 is separately prerelease.

At the earlier B8 closure, normal Observer links still selected a11. Agent Plus retains its previous artifact
and wire 2. That B8 batch selected no persistent service, provider policy, hook, network
bridge or frontend. The later operational gate selects only Observer. The [producer handoff](shared-observation-service-handoff.md)
gives current a8 commands and client obligations.

## Repairs accepted during validation

- A2 keeps the nested Claude SDK helper in its verified collection-worker group
  and retains an exited leader until owned group cleanup. Direct SDK reads still
  own their separate helper group.
- A3 gives the worker its own hard deadline so a publisher SIGKILL cannot leave
  its collection helper running indefinitely. Installed forced-exit/recovery
  checks passed independently on both hosts.
- A4 clears an older terminal outcome when a newer sample explicitly reports a
  turn in progress, including after that negative sample expires. A genuinely
  later terminal sample can restore the outcome.
- A5 binds unloaded age/workspace to history rather than a healthy runtime
  roster. Newer last-known activity is preserved when its lease expires instead
  of reviving an older clock as current. Pure validation now checks coverage,
  workspace and metadata lease dependencies.

The A6 source check passed 278 tests with one optional JSON Schema skip, plus
66 Markdown files. Independent JSON Schema validation of an actual installed
frame passed separately. Installed state/scheduler tests passed on both hosts.

## Measured operating boundary

The packaged default is runtime 20/history 60 seconds, with a 10-second worker
deadline. Snap's two-provider runs exceeded the initial five-percent CPU target
at that cadence. The final A6 Snap run at runtime 30/history 120 seconds measured
83.45-ms warm-read p95 and 3.80 percent of one core; Starship at 20/60 measured
76.15 ms and 1.79 percent. All three healthy readers per host had zero errors.
Peak aggregate RSS/FDs were 131.19 MB/24 on Snap and 48.04 MB/14 on Starship.
These are explicit measured configurations, not real-time monitoring or whole-host
idle CPU guarantees. Native provider/client/reference CPU is outside the measured
publisher/owned-descendant scope.

Current push distributes snapshots obtained through scheduled native reads.
Native/file/hook signals, durable notification events, physical suspend/wake
and downstream rollout retain separate gates. A7 closes configured service
project mapping and normal Observer selection after independent proof.
Claude saved history is partial. The
[remaining-gap investigation](evidence/2026-10-07-gap-investigation/REPORT.md)
accepts foreground questions in the separate a8 candidate, recognizes foreground
prompt `/exit`, proves private passive native hints/lifetime and SSH reconnect,
and explains the Codex default feature skew. A8 also preserves configured polling
intervals above five minutes. That checkpoint kept normal units on a7; the latest
delivery selects a8. Background
`/exit`, live foreground attach, physical wake and notification publication keep
their explicit limits. See the handoff before selecting or extending a candidate.

## Retained gap-row repair

A partial inventory may retain an older row for identity continuity. Its new
component receipt must not make that retained row's old in-progress evidence a
new observation. A6 excludes retained rows from the latest negative-outcome
guard, allowing genuinely later terminal evidence to remain known. Both runtime/
history component orders have a regression check. A6 is frozen and installed
separately. A5 receipts remain exact earlier-artifact evidence.
