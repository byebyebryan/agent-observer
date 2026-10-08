# Shared service producer handoff

This is the selected a16/protocol-1 handoff. New consumer work uses the explicit
accepted a3 [API 2 handoff](api-v2-client-handoff.md) and
[protocol 2](service-protocol-v2.md). Normal selection remains a16 until its
own operational gate; this historical contract does not describe a3 source.

Date: 2026-10-08. Producer and client development remain separate. This handoff
adds explicit cached service access to the accepted [API v1 boundary](api-v1.md).
The service envelope is separately prerelease protocol 1; direct snapshot/watch 3
and write 1 remain unchanged. Read the [execution status](shared-observation-service-status.md)
and [evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md) for
case-by-case earlier acceptance. The [operational baseline](observer-operations-execution.md)
and [earlier evidence](evidence/2026-10-07-observer-operations/REPORT.md) record the
a7 baseline. The [latest delivery](evidence/2026-10-07-native-delivery/REPORT.md)
records the historical a15 selection and preserves earlier failed candidate gates.
The [daily-use repair report](evidence/2026-10-07-daily-use-gap/REPORT.md) records
current a16 selection, independently accepted producer repairs and scoped operations.

## Candidate and selection

The selected producer is `0.4.0a16`, source
`f143a1f6e46cc543b69a738e7da1dc913a0b8643`, wheel SHA256
`a9c13aee3d04144c00dbda80680761d9638fc761ec5cc04922c63ad41f338f23`.
Its [manifest](../artifacts/observer-0.4.0a16.json) verifies three entrypoints,
API 1's existing schemas and the separate service extension. It is installed at
`/home/bryan/.local/share/agent-observer/0.4.0a16-a9c13aee3d04144c` on Snap and
Starship. Snap includes the source-only Claude-history SDK; Starship uses core.
The exact wheel and manifest are retained on both hosts under
`/home/bryan/.local/share/agent-observer/artifacts/0.4.0a16-a9c13aee3d04144c`,
separate from the frozen installed prefix.
Provider support depends on required native predicates and actual process/image/
endpoint ownership, rather than native release allowlists.

Normal Observer read/write/service links now select a16, and the persistent
`agent-observer.service` user unit is enabled on both hosts. Agent Plus still
binds its previous artifact and wire 2; its private venv can shadow normal
commands. Use the explicit a16 prefix when validating or migrating a client.
No hook, networking component or frontend is selected by the Observer rollout.

A16 preserves passive native wakeups alongside periodic reconciliation. Snap runs
Codex and Claude at 30-second runtime / 120-second history cadences; Starship runs
Codex at 20/60 seconds. Both normal units use `--native-hints` with private
`%t/agent-observer/hints.json` diagnostics. The local endpoint is
`/run/user/1000/agent-observer/read.sock`. Hints request authoritative reads; they
do not supply session identity, phase or conversation clocks. Feed loss retains
periodic reconciliation and explicit unavailable/stale semantics.

The [a15 native/cost receipt](evidence/2026-10-07-native-delivery/a15-image-memo-and-host-cost.json)
accepts supported state, question, age, rename, reconnect and listener-lifetime
cases. Controlled matched host CPU overhead is +0.946 percentage points on
combined-provider Snap and +0.153 on Codex-only Starship. Sampled aggregate RSS
is 109.281/64.094 MiB, with added RSS 24.391/21.750 MiB. The user subsequently
relaxed the provisional 64 MiB target to a review threshold, without setting a
new cap. Earlier failed CPU/memory gates remain in the delivery report.

The [managed rollout receipt](evidence/2026-10-07-native-delivery/a15-managed-rollout.json)
records artifact/profile checks, restart, exact-publisher failure, rollback to a8,
reselection, normal-unit reader/resource soaks and independent native comparisons.
Persistent private rollback snapshots on both hosts are under
`~/.local/state/agent-observer/operations/2026-10-07-a15`; the a8 snapshot remains
available. The managed helper verifies prior and desired artifacts separately,
including exact unit contents, interpreter, arguments and PID birth. Its scoped
apply now preserves declared file modes under a private caller umask, and verified
rollback clears the owned unit's restart-rate failure before starting it.

The a16 gate repairs runtime-only Claude retention, saved Codex classification
and read/write diagnostics without decoder changes. Native retention controls
reproduce the a15 defect and accept a16. Independent direct and cache comparisons
match all nine ordinary active contexts and all 35 recent/active user kinds;
twenty-one older Starship kinds stay unproved. Separate three-minute candidate
reader checks pass on both hosts with zero gaps/errors. They do not replace the
historical a15 cost/lifetime/longer-reader receipts. A16's scoped managed gate
records exact selection, restart, publisher failure, a15 rollback/reselection
and current native comparisons. Its persistent rollback snapshots are
`~/.local/state/agent-observer/operations/2026-10-08-a16` on both hosts.

Public versions remain API 1, snapshot/watch 3, write 1 and separate prerelease
service 1. No new decoder fields are required. Runtime readiness after a new
context can precede fresh history: retain explicit stale `lastKnownAt` until an
accepted collection restores current activity. Reconnect cannot promote old
history. Native hooks, provider policy and frontend selections are unchanged by
this rollout. Historical a9–a14 candidate details are in the delivery report.

## Reproducible local entry

The normal selected unit supplies the default endpoint:

```sh
agent-observer service status --host-scope snap
agent-observer service list --host-scope snap
agent-observer service watch --host-scope snap --count 10
systemctl --user status agent-observer.service
```

For a separately owned candidate endpoint, start an explicit foreground publisher
and read it from another terminal:

```sh
candidate=/home/bryan/.local/share/agent-observer/0.4.0a16-a9c13aee3d04144c
"$candidate/bin/agent-observer-service" serve --host-scope snap \
  --provider codex --provider claude --runtime-interval 30 \
  --history-interval 120 --native-hints \
  --socket /run/user/1000/ao-candidate/read.sock
"$candidate/bin/agent-observer" service status --host-scope snap \
  --socket /run/user/1000/ao-candidate/read.sock
"$candidate/bin/agent-observer" service list --host-scope snap \
  --socket /run/user/1000/ao-candidate/read.sock
"$candidate/bin/agent-observer" service watch --host-scope snap \
  --socket /run/user/1000/ao-candidate/read.sock --count 10
```

On Starship use host scope `starship`, only `--provider codex`, and the packaged
20-second runtime/60-second history defaults. Stop the explicitly owned publisher
with Ctrl-C or SIGTERM. Clients never autostart it or fall back to direct reads.
The parent directory is canonical/private/owned; socket and lock are 0600.
See the [client guide](shared-observation-service-client.md) for selectors and
[protocol](service-protocol-v1.md) for exact framing, schemas and bounds.

## Consumer responsibilities

| Concern | Required handling |
| --- | --- |
| Decode | Validate the service envelope before passing its non-null embedded snapshot to API 1. Direct watch 3 cannot parse this envelope. |
| Scope | Retain expected host, UID, boot/time namespace, provider/store selectors and complete identity. A UI label or project grouping does not rewrite authority. |
| Stream | One `StreamGuard` per connection. Initial sequence is one; shared view revision, service UUID and connection sequence have different meanings. Restart/reconnect creates a new guard. |
| Freshness | Check source receipt expiry on delivery and while displaying cached data. Heartbeats only establish transport liveness. Failed/expired observations remain unknown/stale with original clocks. |
| Warm-up/loss | Null warm-up is pending discovery. Gap/resync replaces the entire view. EOF or silence invalidates current claims; there is no durable replay. |
| Discovery | Snapshot retains producer inventory. CLI list/watch are filtered client projections; prefer snapshot or unfiltered transport frames for producer inventory. List/watch exclude confirmed children by default and retain unproved kind. Never guess identity or child status from title, cwd or PID. |
| Age/order | Native conversation activity drives age; current display time drives its rendering. Missing/skewed ages remain explicit. Pure listing orders blocked, waiting, working, unknown, then activity/full identity. |
| Phase/outcome | Waiting, activity and terminal outcome remain independent. The producer clears a previous completion when newer native metadata says a turn is in progress. View changes and receipt counters are not completion events. |
| Actions | Use the separate write-1 prepare/execute/enter path and validate it on the owning host. Observation is no resume, stop, approval or focus authority. Native TTY entry stays client-owned. |
| Remote access | This is local IPC. Remote CLI validation runs on its owning host; a mesh/bridge needs separate transport-loss and conservative remote freshness handling. Local BOOTTIME cannot be directly compared across machines. |

The envelope exposes component leases rather than a per-field provenance map.
For a custom cached display, invalidate all current claims from a source at the
earliest expiry of its currently current/partial components, or obtain a new
producer-projected view. Ignore already-stale components when choosing that next
deadline. A newer runtime receipt cannot extend the lifetime of cached history
fields. The local transport validates at receipt; a UI must still handle expiry
and silence while holding that received view. Preserve last-known activity as
last-known, without restoring an older clock as current.

Python consumers can use the pure `service_public` codec/guard or the bounded
`service_client.frames` local transport. The transport validates socket/peer
ownership and local clock scope and imports no collectors. CLI consumers use
newline envelopes from the explicit service commands. Filters/order are consumer
policy after producer validation. Coverage describes the observed native feed;
it does not make a CLI-filtered row set a complete producer inventory. Use
`service snapshot`, `service_client.frames`, or CLI watch with
`--include-children` when inventory completeness is required.

## Remaining capabilities and rollout gates

| Case | Boundary |
| --- | --- |
| Physical suspend/wake | Pending operator window. Fake BOOTTIME expiry tests establish logic only. |
| Native signals/hooks | Selected a16 preserves bounded passive Codex global-event and Claude filesystem wakeups with periodic authoritative reconciliation. Earlier native latency/lifetime cases retain their a15 bounds; a16 ordinary and retention cases are independently checked. This is sampled state delivery, with no action-based subscription or hook replacement. |
| Notification events | No durable completion/attention publication here. Existing API v1 notification work is separate; source/view counters cannot substitute for native event correlation. |
| Workspace mapping | Startup-only `--workspace-config` root/project mappings already load in both managed services. A16 independently checks Git/root parity. Direct reads need the explicit flag. Restart only the Observer unit to reload. Grouping does not merge native identities. |
| Saved Codex kind/lifecycle | A16 optionally reads bounded `thread/read(includeTurns=false)` detail for unknown saved kind. All recent/active roots match native user kind; 21 older Starship kinds remain unknown. Failed/budgeted detail stays explicit. Saved runtime remains unknown across unproved topologies; human output shows `saved/unknown`. |
| Claude coverage | SDK saved coverage stays partial; the omitted setup-only candidate has zero conversation records. A16 prevents history from indefinitely retaining runtime-only identities; actual saved evidence and incomplete runtime rosters retain conservative gap behavior. A8 accepts verified interactive/no-job exact input waits as blocked/question. Generic dialogs remain unknown. Background questions/approvals and positive parked predicates retain native acceptance. |
| Claude foreground attach | The writer rejects a live foreground row with `unsupported_resume_route`; live attach requires a positively bound background job. Saved Resume is separately supported. Observation alone does not authorize terminal focus or attachment. |
| Native default entry | Both-host private matrices isolate mixed Codex client/server feature defaults; matched pairs enter with defaults. Ordinary provider repair/reproof remains a separate delivery. Surface deferred TTY errors and never retry an uncertain write automatically. |
| Missing historical cwd | Writer preparation reports `cwd_unavailable` or `config_home_unavailable` before dispatch. Two recent Starship contexts have missing cwd. No path substitution/relocation route is accepted. |
| Native UI exit | Foreground prompt `/exit` is independently recognized and removes its registration. Attached-background recognition remains unproved and its worker stays live. Viewer detach and explicit native stop/parked remain separate cases. |
| Resource/latency | A15 controlled event-receipt-to-view runtime p95 is 1.346 s Snap Codex / 1.724 s Starship Codex / 0.997 s Snap Claude; history p95 is 2.226 / 2.037 / 9.218 s. These finite samples do not establish provider-transition time or lossless events. Matched CPU overhead passes; RSS is reviewed without a hard cap. Feed loss falls back to configured polling plus bounded reads. See the native and managed receipts for actual workload, resource and timing limits. |
| Selection/clients | A16 managed selection/restart/crash/a15-rollback/reselection and both-host normal-unit checks are recorded separately. Earlier SSH disconnect/reconnect proof retains its a8 artifact bound; pure connection-epoch/expiry conformance is unchanged. Networking/bridge, Agent Plus and device migrations retain separate delivery gates. |

Tmux Plus development currently blocks Agent Plus implementation. Its next
separate pass should first bind the exact selected a16 artifact
and exercise envelope/freshness/reconnect fixtures independently of UI work,
then validate installed local and remote reads against native evidence. Keep
write actions and terminal/focus behavior as separate client acceptance. Producer
findings reopen an Observer checkpoint; avoid simultaneous producer/frontend
repairs. RLCD and other clients use the same read boundary with their own bridge,
transport and presentation gates. OpenCode remains deprecated.

Before a client pass, read the [event-assisted monitoring plan](event-assisted-monitoring-plan.md)
and [daily-use verdict](evidence/2026-10-07-daily-use-gap/REPORT.md). Native
hints improve supported monitoring latency, but cached conversation ages can
still lag native activity. Current receipt health is not a promise of the latest
message, and feed silence or reconnect never makes stale history current. Client
acceptance must compare the installed public interface with independent native
evidence and preserve the producer's unsupported/partial classifications.
