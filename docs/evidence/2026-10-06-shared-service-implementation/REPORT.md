# Shared-service implementation evidence

Date: 2026-10-06, continuing overnight on 2026-10-07 UTC. This is an Observer
producer pass. Source, controlled, installed and native gates remain separate.
Final A6 sustained resource checks are collecting. No downstream migration,
persistent normal unit/link, ordinary provider action, hook change or physical
suspend belongs to this batch.

## Exact candidate and source

`0.4.0a6`, source `c8c3992984e2dfb9aad3d6812ee936babd9bf999`, wheel SHA256
`3c2e5ae28d6e099f4fc8a9559832b813aa7a84286abaada3a815d1b0cf4b46e8`, installed
at `/home/bryan/.local/share/agent-observer/0.4.0a6-3c2e5ae28d6e099f` on both
hosts. The [manifest](../../../artifacts/observer-0.4.0a6.json) and artifact
receipts [Snap](artifact-a6-snap.json), [Starship](artifact-a6-starship.json)
verify wheel bytes, schemas and three entrypoints without invoking a provider
or selecting links. Snap includes source-only Claude SDK 0.2.163; Starship uses
core. This reproducibility dependency is separate from native provider support.

Native diagnostics: Codex managed 0.160.1 both hosts; Claude 2.1.291 Snap.
Releases/hashes identify inspected evidence, never compatibility allowlists.
API 1 snapshot/watch 3, write 1 and its pure facade remain unchanged. Service
wire 1 is a separate prerelease envelope, not a replacement direct watch parser.

| Commit | Accepted checkpoint |
| --- | --- |
| `93121fb` | Pure bounded service schema/codec/stream guard |
| `398e763` | Source leases, independent fair jobs, private IPC and bounded fan-out |
| `69715f5` | Existing-only owned workers, runtime/history split and identity indexing |
| `06c1200` | Explicit CLI/service, manifest-v2 extension and A1 packaging |
| `1e2f5fe` | Nested SDK group and unreaped-leader cleanup; A2 |
| `8580fa7` | Actual maximum-frame/retention checks and installed/native proof tools |
| `e39fbef` | Worker deadline survives publisher death; A3 |
| `016d3a3` | Operational/native checkpoint and independent Claude reference repair |
| `a9c98c4` | New in-progress turn clears previous completion, including expiry; A4 |
| `4448c75` | History-only age/workspace expiry and newer last-known activity; A5 |
| `767ed00` | Validator import formatting; frozen A5 source |
| `c8c3992` | Retained gap rows cannot renew negative turn evidence; exact A6 source |

Worker/helper repair tests use real subprocess deadline/crash cases; cleanup
never signals native provider groups. Direct SDK reads retain their separate
helper group. Outcome reconciliation cannot revive an older completion after
new-turn evidence expires. Activity similarly preserves newer stale evidence
instead of promoting an older history/runtime clock. A6 excludes gap-retained
rows from newly observed negative-outcome selection: a partial roster's new
receipt cannot renew an older retained turn-in-progress claim.

The A6 full check passed 278 tests, one optional JSON Schema skip, and 66 Markdown
files. [Independent JSON Schema](installed-reader-a6.json) validation passed
separately against an actual installed frame. Installed-origin state/scheduler
checks passed 14 tests on [Snap](installed-state-a6-snap.json) and
[Starship](installed-state-a6-starship.json), including mixed expiry and unloaded
history fields. Pure imports loaded no collectors, image inspectors or write client.

## Controlled runtime and resource bounds

Actual Unix sockets and owned fake sources exercise warming, atomic initial
capture, singleton/private endpoints, fragmented/incomplete/pipelined input,
absolute deadlines, EOF/reconnect, immutable partial writes and loss/resync.
State/scheduler tests cover source isolation, fair retry, hints during reads,
context generations, late-result rejection, partial retention, timer expiry and
wall-clock jumps. Healthy readers coexist with slow/no readers.

Installed maximum-frame checks passed [Snap](capacity-a6-snap.json) and
[Starship](capacity-a6-starship.json): a valid 4096-row, 8,388,292-byte snapshot
was decoded. Sixteen distinct pinned bodies exercised actual admission; nine
clients were dropped and encoded retention peaked at 58,711,884 bytes, below
64 MiB. Aggregate process RSS was about 129 MB including fixture construction.
This does not equate encoded retention with total memory or accept every
simultaneous two-provider/worker decoded heap at maximum size.

## Independent ordinary comparison

[evaluate-observation](../../../scripts/evaluate-observation) imports no Observer
module. Existing-only Codex metadata RPC and Claude registry/job/history references
bracket the installed service CLI. Other Observer projections are additional
regressions, not independent native proof. Receipts contain bounded metadata,
identities, clocks and predicates, never conversation or terminal content.

| A6 subset | Result |
| --- | --- |
| [Snap Codex](ordinary-a6-snap.json) | All 51 identities and supported fields matched; three loaded contexts including one child |
| [Starship Codex](ordinary-a6-starship.json) | All 96 identities and supported fields matched; eight loaded contexts including six children |
| [Snap Claude](ordinary-a6-snap.json) | All 30 conversation identities matched; three waiting workers and three positive parked jobs matched |

Saved/unloaded Codex runtime/phase and unproved title/kind stay explicit unknowns.
Snapshot retains confirmed children; list/watch suppress them by default.
Ordinary populations can change after these samples.

Claude's independently bounded reference found 32 candidates; SDK projected 31.
One command-only row has unknown activity/kind. Setup-only candidate
`e0cba9dd-b642-4730-af4b-beb3b7e9c16c` has exact-bound metadata but no conversation
and is omitted by the SDK. This is a saved-coverage limit, not a missed active/
conversation session. Two metadata companions resolved to conversation identity.
Reference bounds/ambiguity remain explicit; no legacy fallback was added.

## Installed lifecycle and isolated native proof

| A6 case | Evidence / scope |
| --- | --- |
| Entry, age, rename/housekeeping and saved/live Resume | [Snap](native-a6-snap.json), [Starship](native-a6-starship.json); Codex both, Claude Snap |
| Owned Codex outage/recovery | Same receipts; Snap independently proves healthy Claude waiting delivery during Codex failure |
| New turn while history retains an older completion | [Snap](outcome-a6-snap.json), [Starship](outcome-a6-starship.json); native in-progress clears completion, later native terminal restores it |
| Publisher SIGKILL/stale endpoint recovery | [Snap](lifecycle-a6-snap.json), [Starship](lifecycle-a6-starship.json); worker deadline, EOF, new UUID and fresh guard |
| Explicit transient user unit | [Snap](unit-a6-snap.json), [Starship](unit-a6-starship.json); native-visible stores, UID/time domain and stop/socket cleanup |

Native actions used verified private user/mount/PID namespaces with private tmp,
masked ordinary homes/images and disposable stores. Terminal/provider output
was discarded. Units used explicit candidates, Type=exec, NoNewPrivileges and
UMask=0077; no enable/linger operations occurred.

A6 [Claude monitoring](monitoring-a6-snap.json) proves held background questions
and permission prompts as blocked, positive native stop/worker absence as parked,
age preservation and explicit copied saved-Resume identity. Viewer detach
preserves the worker. PTY
`/exit` recognition remains unproved and is not accepted as stop evidence.

## Native retirement and proof correction

A6 paired completed-turn fixtures accepted native unload under continuous
20-second observation on [Snap](lifetime-a6-snap.json) and
[Starship](lifetime-a6-starship.json). Observed contexts unloaded around 61 seconds;
the otherwise quiet control's first probe followed observed unload plus a
30-second margin and also found it unloaded. Reads continued another minute.
Identical native bytes ran both stores.

This proves bounded passivity for the measured private completed-turn topology,
not exact control unload time, every topology or Claude idle retirement.
Installed predicates take precedence over assumed release/documentation durations.

The older empty-thread helper missed unload when the empty row disappeared.
Raw [A2 Snap](lifetime-a2-snap.json), [A2 Starship](lifetime-a2-starship.json),
[A3 Snap](lifetime-a3-empty-snap.json), [A3 Starship](lifetime-a3-empty-starship.json)
receipts reported pending/rejected even though final native observed and control
contexts were both unloaded. Their [classification correction](earlier-lifetime-classification.json)
preserves the original evidence. They do not prove that Observer prolonged native
lifetime. The fixed fixture settles a turn and independently confirms absent rows.

## Sustained measured configuration

Each run uses three independent healthy readers, a never-reading peer and 100
validated installed cached reads over 30 minutes. Readers share one producer
schedule; receipt counters/maxima report the actual workload. A6 final runs are
collecting; earlier artifacts below do not establish final A6 resource acceptance.

| Artifact / host | Runtime / history seconds | Read p95 ms | One-core CPU percent | Peak aggregate RSS MB | Peak FDs |
| --- | --- | --- | --- | --- | --- |
| [A3 Snap](soak-a3-snap.json) | 20 / 60 | 87.20 | 6.315 | 132.17 | 23 |
| [A3 Starship](soak-a3-starship.json) | 20 / 60 | 81.60 | 1.791 | 48.11 | 18 |
| [A3 tuned Snap](soak-a3-tuned-snap.json) | 30 / 120 | 85.09 | 3.884 | 130.92 | 24 |
| [A4 Snap](soak-a4-snap.json) | 30 / 120 | 84.32 | 3.795 | 131.00 | 32 |
| [A4 Starship](soak-a4-starship.json) | 20 / 60 | 80.04 | 1.784 | 48.18 | 19 |

Warm target is p95 <=250 ms; CPU tuning target is <=5 percent of one core.
Snap missed CPU at defaults and met it at explicit slower cadence. Monitoring/
history can lag their cadence plus bounded read delay. The 10-second deadline
yields default 60/180-second leases; tuned Snap uses 90/360 seconds. Only a
successful component read renews its lease; heartbeat/cached reads never do.

CPU includes publisher plus reaped owned children. Native provider, client,
reference and proof processes are excluded; an unreaped bookend job may slightly
undercount its final CPU. Ordinary work continued, so this is not separately
measured full-host idle overhead. RSS/FD peaks include owned descendants;
controlled maximum-frame memory is a separate workload.

## Remaining gates and closure

Physical suspend/wake remains pending an operator window; fake sleep-inclusive
expiry proves logic only. Foreground Claude questions, PTY `/exit` recognition,
all-topology retirement, full maximum simultaneous decoded heap and separate
native-provider/whole-host idle attribution remain unproved. Configured common
roots/project mapping exists for direct reads but lacks service selection.

Current push distributes views from scheduled pulls. Native/file/hook signals,
durable notification events, networking/remote streams, normal selection,
Agent Plus, RLCD and other clients/devices retain separate gates. The
[producer handoff](../../shared-observation-service-handoff.md) provides the exact
candidate quick-start and conservative expiry/reconnect obligations. Final owned
cleanup and preservation bookends follow the A6 sustained checks.
