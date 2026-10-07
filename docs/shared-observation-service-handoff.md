# Shared service producer handoff

Date: 2026-10-06. Producer and client development remain separate. This handoff
adds explicit cached service access to the accepted [API v1 boundary](api-v1.md).
The service envelope is separately prerelease protocol 1; direct snapshot/watch 3
and write 1 remain unchanged. Read the [execution status](shared-observation-service-status.md)
and [evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md) for
case-by-case acceptance and final resource results.

## Candidate and selection

The repaired candidate is `0.4.0a6`, source
`c8c3992984e2dfb9aad3d6812ee936babd9bf999`, wheel SHA256
`3c2e5ae28d6e099f4fc8a9559832b813aa7a84286abaada3a815d1b0cf4b46e8`.
Its [manifest](../artifacts/observer-0.4.0a6.json) verifies three entrypoints,
API 1's existing schemas and the separate service extension. It is installed at
`/home/bryan/.local/share/agent-observer/0.4.0a6-3c2e5ae28d6e099f` on Snap and
Starship. Snap includes the source-only Claude-history SDK; Starship uses core.
The exact wheel and manifest are retained on both hosts under
`/home/bryan/.local/share/agent-observer/artifacts/0.4.0a6-3c2e5ae28d6e099f`,
separate from the frozen installed prefix.
Provider support depends on required native predicates and actual process/image/
endpoint ownership, rather than native release allowlists.

Normal Observer links still select a11. Agent Plus still binds its previous
artifact and wire 2. No persistent service, hook, networking component or frontend
has been selected by this producer batch. Use the full candidate path; the normal
`agent-observer` command does not supply these service subcommands yet.

## Reproducible local entry

Run the owning service explicitly, then read its socket from another terminal:

```sh
candidate=/home/bryan/.local/share/agent-observer/0.4.0a6-3c2e5ae28d6e099f
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
| Native signals/hooks | Shared views are pushed after scheduled pulls. Faster event-assisted monitoring, subscriptions and hooks need independent loss/identity/lifetime proof. |
| Notification events | No durable completion/attention publication here. Existing API v1 notification work is separate; source/view counters cannot substitute for native event correlation. |
| Workspace mapping | Service history performs default Git enrichment. Configured common roots/project mappings remain available to direct reads; the service has no workspace-config selection yet. Do not guess cross-host project identity. |
| Claude coverage | SDK saved coverage is partial. One current setup-metadata-only candidate is omitted; foreground question predicates remain unproved. Background questions/approvals and positive parked predicates have native acceptance. |
| Native UI exit | The disposable PTY `/exit` attempt did not establish command recognition. Viewer detach and explicit native stop/parked are separate accepted cases. |
| Resource/latency | Warm cache latency and publisher/owned-descendant CPU/RSS are measured per configuration. Native provider CPU and full-host idle overhead are not separately attributed. Monitoring/history can lag their configured cadence plus bounded read delay. |
| Selection/clients | Persistent user-unit selection, Agent Plus migration, remote streams and device bridges require their separate delivery gates. |

The next Agent Plus pass should first bind an explicit service-capable artifact
and exercise envelope/freshness/reconnect fixtures independently of UI work,
then validate installed local and remote reads against native evidence. Keep
write actions and terminal/focus behavior as separate client acceptance. Producer
findings reopen an Observer checkpoint; avoid simultaneous producer/frontend
repairs. RLCD and other clients use the same read boundary with their own bridge,
transport and presentation gates. OpenCode remains deprecated.
