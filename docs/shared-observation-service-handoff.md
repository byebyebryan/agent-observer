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

The catalog repair is separately installed `0.4.0a10`, source
`2cd1bbc693c5c4553e61c0f177d2fe2a0e739271`, wheel SHA256
`e57b3e947e731011ad1d470cb83740faf5057dc0a900458a759ed1d6688e2242`, prefix
`0.4.0a10-e57b3e947e731011` on both hosts. Its
[manifest](../artifacts/observer-0.4.0a10.json) and
[focused receipt](evidence/2026-10-07-native-delivery/a10-catalog-scope.json) bind
Claude watches to the project-level saved-history surface. Nested transcript
noise no longer requests catalog scans; primary activity/title still wakes reads.
Installed controlled comparison and one-turn native Claude regression pass.
Broader cost/operational acceptance remains pending; a10 is also unselected.

The SDK-initialization candidate is separately installed `0.4.0a11`, source
`28179263ea45d2315350aad0061f52d13bdefb33`, wheel SHA256
`80b3f82e577b566656b4b3752e0057f89aa46baa23c9fa7742d0d7b9128bb923`, prefix
`0.4.0a11-80b3f82e577b5666` on both hosts. Its
[manifest](../artifacts/observer-0.4.0a11.json) and
[installed/native receipt](evidence/2026-10-07-native-delivery/a11-sdk-and-native.json)
bind a reviewed, guarded SDK metadata-only initialization and unchanged public
schemas. Real copied-history and synthetic companion/omitted-kind projections
match a10 exactly. The helper remains isolated, audited and deadline bounded;
SDK files/parsers are not patched. The SDK lock is an Observer dependency.

Three-turn event-to-view runtime p95 is 1.431 s on Snap Codex, 1.233 s on Starship
Codex and 0.703 s on Snap Claude; history p95 is 2.299, 1.982 and 10.164 s.
These are small controlled exact-ID samples, not native transition-time or
lossless event guarantees. Foreground Claude question/exit and both-host paired
retirement pass. Ordinary CLI/native comparisons retain known partial saved
Claude coverage and unknown older Codex kinds. A11 remains unselected: the
original aggregate-memory gate is unmet, and P6's managed restart/crash/rollback/
30-minute acceptance is pending. Clients should keep the explicit selected a8
endpoint unless intentionally evaluating an unselected candidate.

The later a12/a13 runtime/scheduling repairs are separately installed and
unselected. The [a13 receipt](evidence/2026-10-07-native-delivery/a13-debounce-and-host-cost.json)
passes correlated native latency, foreground Claude question/exit and both-host
listener retirement, but its matched two-provider Snap workload measures +2.330
CPU percentage points and 109.289 MiB sampled aggregate RSS. Both original
resource gates fail. A14 adds bounded metadata scheduling fingerprints to the
owned Claude helper; its separately installed native subset passes, and its
held background question reaches cached blocked state in 0.789 seconds. Its
[combined cost receipt](evidence/2026-10-07-native-delivery/a14-filter-and-host-cost.json)
still misses the original gates: +2.086 CPU points and 131.402 MiB sampled
aggregate RSS. These repairs do not change API 1 or the
service envelope and do not select native hints for ordinary use. Refer to the
[cost follow-up](native-hints-cost-follow-up.md) before evaluating an unselected
candidate; selected a8 remains the client handoff endpoint.

A15 adds a private descriptor-anchored executable-image memo, with fresh native
endpoint/process guards and no retained session state. Its separately installed
tuple is `0.4.0a15` / source `193a929605b7dca0a03f57d4c672e3da439db5fd` /
wheel `b359730d6a5435484513247ef9048cf109173a456fec5ef0ada16e6d6e2659d9`;
the prefix on both hosts is
`/home/bryan/.local/share/agent-observer/0.4.0a15-b359730d6a543548`.
Public versions and profiles remain unchanged. Its controlled Snap combined and
Starship Codex workloads pass the one-point incremental CPU gate at +0.946/+0.153
points, with zero healthy reader errors or gaps. Aggregate RSS still fails the
original 64 MiB limit: 109.281/64.094 MiB. Added RSS is 24.391/21.750 MiB, recorded
without redefining the gate. No normal hint selection follows from these tests;
the selected a8 endpoint and downstream deployment boundaries remain current.
The [a15 receipt](evidence/2026-10-07-native-delivery/a15-image-memo-and-host-cost.json)
also records ordinary cached/native comparisons, unloaded rename and isolated
daemon replacement with unchanged conversation age. Runtime readiness after a
new context can precede fresh history: retain explicit stale `lastKnownAt` until
an accepted collection restores current activity. Reconnect is not permission
to promote old history. The initial failed immediate-age test is retained, and
the strengthened fresh-history proof passes on both hosts. All owned native
stores/authentication and ordinary proof publishers are removed.

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
| Native signals/hooks | Selected a8 pushes shared views after scheduled pulls. A9 passes bounded native wakeup/recovery cases; a10 additionally removes nested-history noise with focused Claude proof. Cost acceptance and the 30-minute hint-unit rollout soak remain pending. No action-based subscription or hook replacement is used. |
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
