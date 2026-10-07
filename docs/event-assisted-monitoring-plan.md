# Event-assisted monitoring implementation gate

Date: 2026-10-07. Status: reviewed investigation proposal, not production event
wiring or a new public API. The [native investigation](evidence/2026-10-07-gap-investigation/REPORT.md)
proves useful passive Codex global start/status hints and Claude registry wakeups
within disposable contexts. The selected service still pushes scheduled reads.

The [next-delivery execution plan](observer-next-delivery-plan.md) defines ordered
checkpoints, provisional latency/cost targets, operational upgrade/rollback work
and the separate native workflow/client branches. This document supplies the
provider-source boundary for that plan.

## Ownership and algorithm

Keep one host-local publisher and provider-owned hint sources. The pure core and
read codecs remain free of hooks, native sockets, filesystem watchers or actions.
A hint invalidates scheduling assumptions; it does not supply a session identity,
phase, completion, activity clock or action authority. Collectors still obtain
and validate authoritative metadata using the existing contracts.

1. The publisher optionally owns a Codex initialized passive native peer and a
   Claude metadata-directory watcher. Resolve and validate endpoint UID/process/
   incarnation before connecting. Never resume, load or subscribe via a session
   action to obtain monitoring. Drop unknown methods and content immediately.
2. Coalesce bounded hints by provider/store/component. Queue at most one pending
   runtime and one pending history wakeup per source. Minimum collection gaps,
   debounce and a job budget prevent native event storms from creating overlapping
   jobs or unbounded scans. Runtime and history retain independent scheduling.
3. Hint-triggered reads obey existing process isolation, timeout, source-generation
   and native ownership checks. Publish only accepted projections; component
   receipt clocks advance only when that component accepts a fresh read.
4. Retain periodic full reconciliation. Watch overflow, disconnect, incarnation
   change, source directory replacement and missed/new-directory watches request
   a bounded full reconciliation and rearm. Feed loss is explicit diagnostics;
   it does not renew leases or invalidate a still-current receipt early without
   contrary evidence. Expiry and unsupported metadata remain conservative.
5. Stop only owned listeners/watchers with the publisher. Native provider workers
   retain their existing lifecycle. No autostart or control fallback is introduced.

Codex start/status events are useful runtime hints in current native proof. No
global lossless turn completion stream was accepted. Match only finite native
method/metadata contracts, not version/hash registration. Claude directory events
must cover atomic file replacement and subtree creation; event paths/names/mtime
are wakeup locators, never identities or conversation clocks. Transcript changes
may request a separately budgeted history read to reduce conversation-age lag.
Hooks are optional future hints with their own ownership, duplicate and loss
gates; they are not required to start this passive implementation.

## Acceptance before selection

| Gate | Required independent proof |
| --- | --- |
| Scheduling | Controlled bursts, concurrent providers, saturated jobs, successful slow intervals, retry backoff and no overlapping work; memory and job-count bounds. |
| Native usefulness | Exact session/state/age comparisons for New, work, held waits, completion, title and saved-history change; report which global events are absent. Prove both Codex hosts and Claude on Snap. |
| Loss/recovery | Listener disconnect/reconnect, daemon incarnation change, watcher overflow/directory replacement, lost hint and periodic reconciliation; preserve source generations and old clocks. |
| Passivity/lifetime | Passive method allowlist, loaded-set bookends and paired quiet-control retirement with the long-lived peer. No ordinary settings/hooks/services change. |
| Cost/latency | Warm client latency plus event-to-accepted-observation delay, runtime/history job counts and owned process CPU/RSS/FDs versus the same polling baseline. Native/whole-host CPU claims need separate attribution. |
| Contract/client | API 1 remains snapshot/watch 3 and write 1. Service protocol 1 remains a separate prerelease envelope. Reference consumers test expiry, resync and transport loss before a frontend migration. |
| Delivery | Frozen source/wheel/native acceptance before an Observer-only managed rollout; no simultaneous Agent Plus or dashboard repair. |

Bounded push improves monitoring and discovery latency while preserving scheduled
reconciliation. Notification delivery remains its own experimental client because
snapshot/status changes cannot establish every completion, originating terminal
or durable event replay.
