# Shared observation service and first-class pull/push

Date: 2026-10-06. Status: design/context capture for a research and validation
goal loop. This document authorizes no service implementation, installation,
provider subscription, hook change or downstream migration. Review findings and
the implementation/native gates will be recorded separately.

## Context and intended outcome

Observer is shared infrastructure for Agent Plus, the ESP32 RLCD dashboard,
possible other device dashboards and a possible Kitty session client. Codex is
the primary provider across hosts; Claude remains a required second provider
on Snap. Host/provider independence and separate core/frontend development
cycles remain requirements. OpenCode stays outside this program.

The [accepted API v1](api-v1.md) provides passive snapshot/read operations and
an on-demand sampled watch. Each watch currently collects its own snapshots.
The [experimental notification checkpoint](notification-client-contract.md)
adds bounded callback normalization and separate publication formatting, not
an all-session event receiver or shared monitoring service.

Agent Plus caches results to make discovery latency tolerable. A device bridge
will also need a continuous view and push transport. Giving each consumer its
own provider collection loop would repeat work, freshness handling and failure
recovery. The user therefore proposes first-class pull and push with a shared
host-side Observer runtime, covering monitoring and potentially discovery.

The desired outcome is one shared observed view per configured local service,
fast explicit snapshot access and bounded subscriptions. Adding consumers must
not multiply provider sampling. Local push should work even if every upstream
adapter still needs to pull. Neither service presence nor callback silence may
become a claim about native worker lifetime or phase.

## Ownership and topology

| Component | Responsibility |
| --- | --- |
| Pure core/public facade | Observation schemas, exact identity, semantic validation, state/freshness/coverage rules, filtering and ordering |
| Provider adapters | Existing-only native reads, bounded accepted metadata and independently proved source signals |
| Observer local service | Scheduling, shared collection/reconciliation, in-memory observed view, local snapshot/subscription delivery, health and bounded fan-out |
| First-party read client | Explicit direct or service access and diagnostic views; no provider action or remote route inference |
| First-party write client | Existing separately validated New/Resume/native entry; service observations do not authorize actions |
| Networking/Host Mesh | Authenticated owning-host transport, fleet composition, disconnected-host views and per-host stream recovery |
| Agent Plus/device bridge | Presentation, selection, viewer/device association and downstream transport |
| Notification client | Event publication/deduplication policy and originating-terminal/desktop routing |

The service is a runtime component of this repository and uses the same passive
core. It is not a provider runtime manager. Its lifetime must not start, resume,
hold, stop or approve provider work. Pure parsing and explicit direct collection
remain available without it. Native providers and terminal clients retain their
existing workflows.

Initial transport should be host-local and per user, with a private Unix socket
and an explicitly selected supervised user service. TCP, HTTP, device transport,
SSH route selection and cross-host aggregation are separate. Socket activation,
service startup and command names remain review decisions, not installed behavior.

## Pull and push model

Clients should have explicit access to:

1. The latest shared observed view, including its actual source/sample freshness.
2. An initial snapshot followed by changed views and health/gap/resync frames.
3. Direct collection for diagnosis and bounded refresh requests if the reviewed
   service protocol accepts them.

A service read does not imply a fresh provider scan. Sending a cached view must
not rewrite `collectedAt`, conversation activity or evidence clocks. A freshness
requirement must be honored, rejected or timed out explicitly; it cannot silently
bless old data. Client outage caches remain presentation/networking concerns.

State delivery can coalesce observations when only the newest view matters.
Reliable completion/attention events have different correlation and loss rules;
they must not be reconstructed from sampled phase changes. An event interface,
if later accepted, has its own versioned semantics and native source gates.

Discovery participates in the same view: newly discovered sessions, title and
history metadata changes, loaded/registered membership and accepted absence
predicates can produce updates. Saved-only absence remains unknown under API v1.
No callback or file deletion alone proves a session parked or removed.

## Hybrid sources and scheduling

Start from shared polling of already accepted reads. Introduce accepted source
signals incrementally: native notifications, metadata-only hook wakeups and
bounded local filesystem-change detection. Signals normally schedule a refresh;
file timestamps and callbacks do not become state, conversation age or final
success by themselves. Periodic reconciliation remains necessary.

Separate the latency/cost needs of active monitoring, loaded/registered inventory,
saved history and workspace enrichment. Avoid rescanning all saved history on
each state refresh. The current collectors may need internal extraction before
different cadences can be accepted; this is not a second discovery stack.

Scheduling must coalesce storms, retain periodic discovery through event silence,
bound retry/backoff and read deadlines, prevent overlap for each source and keep
one failed provider from delaying healthy delivery indefinitely. Subscriber
preferences do not grant unbounded polling frequency or a hook installation.
Measure actual cost and latency before selecting default intervals.

Codex's current transport ignores unsolicited messages and the accepted reads
do not establish a passive subscription. Native subscription lifetime effects
need focused proof. Claude Stop continuation and Agent View-dependent background
notifications likewise do not establish a complete monitoring feed. Existing
S6 callback proof remains its own bounded subset.

## Delivery and recovery invariants

- Initial subscription must capture a consistent view and establish subsequent
  delivery without dropping the change between those two operations.
- Preserve full identity, source scope, child classification and per-dimension
  freshness. Filter only after reconciliation; unknown remains visible.
- Bound subscribers, frame bytes, input, queue memory, retention, CPU and file
  descriptors. A slow subscriber cannot block provider reads or other clients.
- Distinguish intentional state coalescing from observation/delivery loss. Loss
  produces explicit gaps and a replacement view, not an inferred phase.
- Reconnect or service restart begins a new stream epoch and a fresh initial
  view. No durable journal, exactly-once delivery or native replay is promised.
- Service heartbeats establish only service/transport liveness. Source failure,
  long-running turns and absent callback traffic retain their actual evidence.
- In-memory last-known data is not automatically current after sleep, provider
  restart, configuration change or a new executable/process incarnation.
- Revalidate source context for collection and preserve provider-specific
  capability predicates; supported release lists must not return.

## Local service safety and lifecycle

Socket authority must include ownership/permissions and kernel peer identity,
not pathname alone. Validate the configured user, owning host scope and exact
provider-store selection; client-provided labels cannot relabel shared data.
Prevent arbitrary filesystem/configuration access through read requests.

Hook senders need bounded local delivery and event-specific neutral failure.
UID equality does not attest provider event truth. Treat unproved local signals
as refresh hints and never as action permission. Retain allowlisted metadata;
never journal prompts, responses, tool content, credentials or raw callbacks.

Normal hooks/settings/services remain unchanged during design and research.
Runtime selection, managed service installation and hook registration have
separate scoped rollout gates. Observer shutdown must affect only Observer-owned
processes and IPC, leaving native providers, workers and clients intact.

## Consumer effects

Agent Plus can open from a warm owning-host view and maintain updates through
its networking layer. Cross-host reconnect, host authority, offline caches and
picker selection still belong to that layer/client. Push does not prove current
terminal-to-conversation binding or make stale observations safe action plans.

A dashboard bridge subscribes to normalized observations and projects the latest
view into its device protocol. It owns display throttling, frame sizing, transport
and device reconnect; it should not own provider polling or classification.
Fixture/host-input acceptance does not establish physical device acceptance.

The notification client can reuse accepted source identity/context, but state
updates and publishable native events remain distinct. Kitty/tmux origin routing,
duplicate native-alert replacement and desktop/349 delivery stay separate gates.

## API v1 compatibility

Preserve existing API v1 direct reads, pure public symbols and snapshot/watch 3,
write 1. The proposed local service protocol is independently versioned and
must describe transport, request bounds, cached-view freshness and recovery.
Reusing existing documents does not make those new service semantics stable.

Do not quietly add fields, request commands or event promises to existing strict
documents/descriptors. If review establishes a need to change an accepted wire
or public meaning, use its explicit version/major policy. Begin with full views
rather than patch deltas unless measured size/cost justifies a separate format.

## Review and validation sequence

| Pass | Questions and evidence |
| --- | --- |
| R0: capture | Preserve user motivation, current accepted boundaries and design-only scope |
| R1: contract/source review | Can watch 3 represent shared cached state, expiry, subscriber epochs and scoped recovery without silently changing API v1? |
| R2: primary research | Provider event/subscription semantics; hook lifetime and neutral delivery; Unix IPC, notification queues and user-service lifecycle |
| R3: bounded measurements | Existing snapshot/watch cost per source/host and consumer collection behavior; label passive samples rather than new service acceptance |
| R4: controlled validation | Initial-view/update race, coalescing versus loss, slow readers, restart, source outage, stale clocks and API/schema conformance |
| R5: deep review closure | Findings, revised choices, explicit unsupported cases, implementation work packages and independent native/artifact/consumer gates |

Research can inspect current files/interfaces and make bounded passive reads.
Any new native subscription, provider launch or callback registration requires
an independently isolated proof plan; documentation or synthetic exercises do
not establish passivity. This loop implements no service or downstream client.

## Implementation direction after review

Provisional order: contract/controlled scheduler and fan-out; shared accepted
collection; independent packaged/native service proof; optional source signals;
then separate client migrations and managed selection. A passive shared-polling
service is a useful milestone without an all-provider native event feed.
Review will refine this order and the actual acceptance matrix.
