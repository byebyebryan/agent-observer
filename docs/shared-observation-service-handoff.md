# Shared service producer handoff

Date: 2026-10-07. Producer and client development remain separate. This handoff
adds explicit cached service access to the accepted [API v1 boundary](api-v1.md).
The service envelope is separately prerelease protocol 1; direct snapshot/watch 3
and write 1 remain unchanged. Read the [execution status](shared-observation-service-status.md)
and [evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md) for
case-by-case earlier acceptance. The [operational baseline](observer-operations-execution.md)
and [earlier evidence](evidence/2026-10-07-observer-operations/REPORT.md) record the
a7 baseline. The [latest delivery](evidence/2026-10-07-native-delivery/REPORT.md)
selects a8 on both hosts and records the unselected a9 hint candidate and cost gate.

## Candidate and selection

The selected producer is `0.4.0a8`, source
`3c71f216a716a36f2403f7c71fa5935c41c9917f`, wheel SHA256
`a8370b0f96d2669ff3bbf290ff01b9387cd7dfdacdf263c9f3baffbaf2343926`.
Its [manifest](../artifacts/observer-0.4.0a8.json) verifies three entrypoints,
API 1's existing schemas and the separate service extension. It is installed at
`/home/bryan/.local/share/agent-observer/0.4.0a8-a8370b0f96d2669f` on Snap and
Starship. Snap includes the source-only Claude-history SDK; Starship uses core.
The exact wheel and manifest are retained on both hosts under
`/home/bryan/.local/share/agent-observer/artifacts/0.4.0a8-a8370b0f96d2669f`,
separate from the frozen installed prefix.
Provider support depends on required native predicates and actual process/image/
endpoint ownership, rather than native release allowlists.

Normal Observer read/write/service links now select a8, and the persistent
`agent-observer.service` user unit is enabled on both hosts. Agent Plus still
binds its previous artifact and wire 2; its private venv can shadow normal
commands. Use the explicit a8 prefix when validating or migrating a client.
No hook, networking component or frontend is selected by the Observer rollout.

A8 repairs foreground Claude question detection and slow polling schedules.
The old-to-new managed helper verifies prior and desired artifacts separately;
restart, rollback and reselection passed on both hosts. Persistent private
rollback snapshots are under `~/.local/state/agent-observer/operations/2026-10-07-a8`.

The separate hint candidate is `0.4.0a9`, source
`c2f3754353cb72cd9afc644d9aba1ab296987875`, wheel SHA256
`8165f9400fadaa50f5d95e95f578630492791a74f81ba417cd5f6faf89a36497`.
Its [manifest](../artifacts/observer-0.4.0a9.json), archive and installed prefix
`0.4.0a9-8165f9400fadaa50` exist on both hosts under the same roots as a8.
It adds opt-in `--native-hints` and optional private `--hint-diagnostics` alongside
periodic reconciliation. API/wire/service versions and public fixtures remain
unchanged. Native latency, helper recovery and paired retirement cases pass,
but the provisional resource gate is not accepted. Do not treat its installation
as normal selection or enable its hints in the managed unit. The
[cost follow-up](native-hints-cost-follow-up.md) defines the remaining producer work.

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
candidate=/home/bryan/.local/share/agent-observer/0.4.0a8-a8370b0f96d2669f
"$candidate/bin/agent-observer-service" serve --host-scope snap \
  --provider codex --provider claude --runtime-interval 30 \
  --history-interval 120 --socket /run/user/1000/ao-candidate/read.sock
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
| Native signals/hooks | Selected a8 pushes shared views after scheduled pulls. Separate a9 native start/status/name and Claude registry/job/history wakeups pass bounded latency/recovery cases, with controlled overflow/rearm/burst/backoff checks. Cost acceptance and the 30-minute hint-unit rollout soak remain pending. No action-based subscription or hook replacement is used. |
| Notification events | No durable completion/attention publication here. Existing API v1 notification work is separate; source/view counters cannot substitute for native event correlation. |
| Workspace mapping | A7 accepts startup-only `--workspace-config` root/project mappings on history jobs, with independent Git validation and history leases. Restart only the Observer unit to reload. Explicit grouping does not merge native identities. |
| Claude coverage | SDK saved coverage stays partial; the omitted setup-only candidate has zero conversation records. A8 accepts verified interactive/no-job exact input waits as blocked/question. Generic dialogs remain unknown. Background questions/approvals and positive parked predicates retain native acceptance. |
| Claude foreground attach | The writer rejects a live foreground row with `unsupported_resume_route`; live attach requires a positively bound background job. Saved Resume is separately supported. Observation alone does not authorize terminal focus or attachment. |
| Native default entry | Both-host private matrices isolate mixed Codex client/server feature defaults; matched pairs enter with defaults. Ordinary provider repair/reproof remains a separate delivery. Surface deferred TTY errors and never retry an uncertain write automatically. |
| Native UI exit | Foreground prompt `/exit` is independently recognized and removes its registration. Attached-background recognition remains unproved and its worker stays live. Viewer detach and explicit native stop/parked remain separate cases. |
| Resource/latency | Selected polling can lag 30/120 seconds on Snap and 20/60 on Starship plus bounded reads. A9 controlled native-to-view runtime p95 is 0.8–1.4 seconds; activity p95 is at most 9.5 seconds and saved unloaded rename about 10.2 seconds. Exact event-arrival latency is not claimed. Snap observed CPU delta +2.17 points needs equivalent-workload proof; aggregate RSS 167.2 MiB Snap / 67.6 MiB Starship exceeds the provisional 64 MiB target. |
| Selection/clients | A8 upgrade/restart/rollback/reselection passes. SSH disconnect/reconnect with fresh connection sequence passes against selected a8; networking/bridge, Agent Plus and device migrations retain separate delivery gates. |

The next Agent Plus pass should first bind the exact selected a8 artifact
and exercise envelope/freshness/reconnect fixtures independently of UI work,
then validate installed local and remote reads against native evidence. Keep
write actions and terminal/focus behavior as separate client acceptance. Producer
findings reopen an Observer checkpoint; avoid simultaneous producer/frontend
repairs. RLCD and other clients use the same read boundary with their own bridge,
transport and presentation gates. OpenCode remains deprecated.

Before a client pass, read the [event-assisted monitoring plan](event-assisted-monitoring-plan.md)
and [latest delivery verdict](evidence/2026-10-07-native-delivery/REPORT.md). Cached
Claude conversation ages can lag the configured history cadence; current receipt
health is not a promise of the latest native message. A8's question repair is
available through the selected producer. A client can migrate now against this
polling baseline; a9 hint acceptance is a later producer checkpoint and must not
be closed through a simultaneous frontend repair.
