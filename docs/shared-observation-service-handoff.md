# Shared service producer handoff

Date: 2026-10-07. Producer and client development remain separate. This handoff
adds explicit cached service access to the accepted [API v1 boundary](api-v1.md).
The service envelope is separately prerelease protocol 1; direct snapshot/watch 3
and write 1 remain unchanged. Read the [execution status](shared-observation-service-status.md)
and [evidence](evidence/2026-10-06-shared-service-implementation/REPORT.md) for
case-by-case earlier acceptance. The [operational baseline](observer-operations-execution.md)
and [current evidence](evidence/2026-10-07-observer-operations/REPORT.md) record a7
selection, workspace configuration, normal user-unit recovery and sustained checks.

## Candidate and selection

The repaired candidate is `0.4.0a7`, source
`8ca7a789899066cd6c2399f8c6fad60e06e869e7`, wheel SHA256
`09f41f33e6c22fe019e518af3deae067b58b42f571b84d6c45aebe706079865a`.
Its [manifest](../artifacts/observer-0.4.0a7.json) verifies three entrypoints,
API 1's existing schemas and the separate service extension. It is installed at
`/home/bryan/.local/share/agent-observer/0.4.0a7-09f41f33e6c22fe0` on Snap and
Starship. Snap includes the source-only Claude-history SDK; Starship uses core.
The exact wheel and manifest are retained on both hosts under
`/home/bryan/.local/share/agent-observer/artifacts/0.4.0a7-09f41f33e6c22fe0`,
separate from the frozen installed prefix.
Provider support depends on required native predicates and actual process/image/
endpoint ownership, rather than native release allowlists.

Normal Observer read/write/service links now select a7, and the persistent
`agent-observer.service` user unit is enabled on both hosts. Agent Plus still
binds its previous artifact and wire 2; its private venv can shadow normal
commands. Use the explicit a7 prefix when validating or migrating a client.
No hook, networking component or frontend is selected by the Observer rollout.

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
candidate=/home/bryan/.local/share/agent-observer/0.4.0a7-09f41f33e6c22fe0
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
| Workspace mapping | A7 accepts startup-only `--workspace-config` root/project mappings on history jobs, with independent Git validation and history leases. Restart only the Observer unit to reload. Explicit grouping does not merge native identities. |
| Claude coverage | SDK saved coverage is partial. One current setup-metadata-only candidate is omitted; foreground question predicates remain unproved. Background questions/approvals and positive parked predicates have native acceptance. |
| Claude foreground attach | The writer rejects a live foreground row with `unsupported_resume_route`; live attach requires a positively bound background job. Saved Resume is separately supported. Observation alone does not authorize terminal focus or attachment. |
| Native default entry | The current mixed Codex CLI/server pairing rejects a default feature mismatch in a fresh fixture. Entry proof disables `api_key_model_discovery` only in that private fixture; ordinary default startup is not accepted. Surface deferred TTY errors and never retry an uncertain write automatically. |
| Native UI exit | The disposable PTY `/exit` attempt did not establish command recognition. Viewer detach and explicit native stop/parked are separate accepted cases. |
| Resource/latency | Warm cache latency and publisher/owned-descendant CPU/RSS are measured per configuration. Native provider CPU and full-host idle overhead are not separately attributed. Monitoring/history can lag their configured cadence plus bounded read delay. |
| Selection/clients | Observer-only unit selection and restart/crash/rollback gates pass. Agent Plus migration, remote streams and device bridges retain independent delivery gates. |

The next Agent Plus pass should first bind this explicit installed a7 artifact
and exercise envelope/freshness/reconnect fixtures independently of UI work,
then validate installed local and remote reads against native evidence. Keep
write actions and terminal/focus behavior as separate client acceptance. Producer
findings reopen an Observer checkpoint; avoid simultaneous producer/frontend
repairs. RLCD and other clients use the same read boundary with their own bridge,
transport and presentation gates. OpenCode remains deprecated.
