# Observation ownership and contract boundaries

Date: 2026-10-08. This captures the user's clarified ownership direction after
the [a4 Codex acceptance](evidence/2026-10-08-codex-evidence-repair/REPORT.md).
The source audit below records the pre-extraction baseline. The
[completion loop](codex-observation-completion-plan.md) now accepts source
extraction/enforcement, installed/native proof and the separate read/service
operational gate. This ownership document alone does not accept new API fields,
event guarantees or adapters. [API 2](api-v2.md), read wire 4 and
service protocol 2 remain the accepted prerelease read contracts.

## Component ownership

Observer core owns host-local discovery and monitoring through a shared
provider-neutral model. Here, core includes the observation model, passive
provider adapters and a reusable observation engine. The pure public read
facade is a smaller part of core: importing it must perform no collection,
start no runtime and import no provider/action/alert implementation.

| Component | Owns | Inputs and outputs |
| --- | --- | --- |
| Observation model and pure read API | Exact session identity, runtime/phase semantics, metadata, activity clocks, uncertainty, validation and read selectors | Bounded validated observations; no native I/O |
| Passive provider adapters | Authoritative native queries, metadata projection, source capability proof and native-signal normalization | Existing provider endpoints to bounded samples and refresh hints |
| Observation engine | Sample ordering, reconciliation, retained uncertainty, freshness/expiry, refresh planning and the canonical local view | Samples, hints, explicit clock/config inputs to observations and collection work |
| Observer service | Host-local engine lifetime, helper execution, timers, IPC authentication, bounded pull/push delivery and shutdown | Hosts the engine and serves its view; owns only Observer processes |
| Network/mesh component | Authenticated host identity, routing, cross-host composition, reconnect and transport health | Consumes local read interfaces and preserves their origin/evidence |
| Read CLI | Explicit direct, service or supplied-input reads; validation, selection, ordering, age display and diagnostics | Uses core or a read endpoint; performs no provider action or alert delivery |
| Attachment/action layer | Context matching, viewer association, New/Resume/attach/focus intent, native action preflight and terminal lifetime | Exact Observer references plus independently established terminal/window evidence |
| Alert client | Attention policy, notification deduplication, formatting, desktop/device/terminal routing and delivery | Explicit evidence or read updates; owns user-facing publication |

These may live in one repository without sharing action authority. An
observation engine is a library boundary, not a new required daemon. The local
service is the long-running host for it; an explicit direct CLI invocation can
host a bounded read without starting that service. Cross-host networking is
optional and does not become a core dependency.

The service remains responsible for real runtime work, including timers,
helper isolation and backpressure. Calling it a wrapper means it does not
invent provider/session semantics or duplicate reconciliation policy.

## Provider-independent discovery and monitoring

The exact row reference is
`hostScope/provider/namespace/nativeIdKind/nativeId`. Native hierarchy IDs,
titles, cwd and project metadata do not substitute for that reference. Saved
existence, running disposition, phase, conversation age and source health are
separate facts. Observed running or parked state never authorizes an action.

- Discovery reports `running`, `parked` or `unknown`, with declared scope,
  bounds and coverage. Parked requires positive saved identity and the adapter's
  reviewed native lifecycle predicate. Absence from an ordinary list, terminal
  exit and an unavailable endpoint alone do not establish it. A scoped negative
  predicate must declare its registration/completeness assumptions and failure
  limits; exhaustive coverage requires independent completeness proof.
- A running session's phase is `working`, `blocked`, `waiting` or `unknown`.
  Parked has no applicable phase. Blocked reasons preserve approval/question
  evidence without approving or answering anything.
- Conversation activity comes from a native conversation event clock.
  Polling, receiving a push, Resume, title changes and lease renewal do not
  advance it. Missing and stale clocks stay explicit.
- An incomplete or failed read preserves independently proved sibling facts.
  Previously known facts may survive as bounded last-known evidence, not as
  current running/parked/phase assertions.
- Native child classification remains explicit. The canonical view retains
  children; the default read presentation hides confirmed children only.
  Unknown classification is preserved.

Codex's existing owning daemon is the
runtime authority: active is running, idle is running/waiting, and current
`notLoaded` plus positively readable saved identity is parked. Native error
and unsupported wait flags preserve the independently proved runtime fact
while leaving phase uncertain as required by API 2.

The [independent Claude gate](evidence/2026-10-08-claude-observation/REPORT.md)
accepts passive observation on Snap. Exact provider registrations authenticated
by native PID domain, process birth, source ownership and executable locator
supply running and current status evidence. These authenticate provider-native
records and do not inspect terminal attachment. Terminal retained jobs require
positive lifecycle, no pending work and saved existence before parked. General
saved-only absence remains unknown. The native roster CLI has initialization
writes and is not invoked by observation.

The next [interactive-only Claude plan](claude-interactive-observation-plan.md)
uses the user's accepted native-registration assumption: a healthy bounded scan
with no matching live incarnation or relevant unresolved conflict can classify
positively saved UUIDs as parked. Normal exit and crash are supported targets.
A live missing registration can instead produce false parked, even after source
recovery; declare partial coverage and that limitation. The implementation removes
unused private attachment/job scaffolding and reconstructs state after Observer
restart without a run ledger or client inventory. Provider-owned registration
incarnation checks are permitted; generic process/terminal discovery is not.
Contract review, artifact selection and Agent View opt-out retain separate gates.

Future adapters must prove equivalent evidence for the shared semantics.
They need not copy Codex's protocol, process layout or daemon topology. Missing
capabilities remain unknown/unsupported with declared limits. An adapter must
not fill a missing native predicate by inspecting a TUI, tmux session or window.
Provider release numbers remain diagnostics, not support allowlists.

Endpoint authentication can inspect the owning provider daemon's UID/PID,
executable and incarnation. This authenticates the source; it does not inspect
terminal attachment or infer session activity from a foreground process.

## Three meanings of notifications

### Provider signals that trigger observation

Native daemon notifications and any separately accepted passive hook source
belong to the provider-adapter boundary. They are normalized into bounded
refresh hints, with source context and feed health supplied by the owning
adapter/host. The engine owns coalescing, refresh planning and reconciliation;
the service hosts listeners/helpers and executes the requested reads.

Current Codex signals are wakeups for authoritative queries. A signal alone
cannot create a runtime/phase fact, renew a lease, advance conversation age or
prove saved existence. Losing a listener cannot prove that sessions stopped.
Periodic reconciliation remains required when signals are absent, duplicated
or lost. Hooks are optional sources with their own proof/installation gate;
core reads do not install them or modify ordinary provider settings.

### Observer push updates

Push carries the same reconciled view as cached pull. The engine owns which
facts are current and how the view changes; the service owns stream envelopes,
subscriber isolation, queue limits, heartbeats and resync delivery. A heartbeat
is transport liveness, not fresh provider evidence. Direct reads have the same
projection/semantics but may represent a different sampling instant.

Current push is sampled/reconciled read delivery. It does not promise every
native transition, durable replay or a completion notification for every turn.
A dashboard can use it to track current state; an alert client must separately
account for sampling gaps and supported event evidence.

### User-facing alerts

Desktop, Kitty and device notifications belong to a separate client. Suppression,
focus policy, delivery deduplication, static message text, pane/window selection
and Open actions are client policy. Observation reads and service startup emit
no user-facing alerts.

Core may normalize bounded native event evidence for reuse, but a public
attention/completion event API needs a separate contract/native gate. The
existing [experimental notification source/client](notification-client-contract.md)
does not establish such an API 2 event stream. Its policy-bearing `notify`,
`wake` and `ignore` dispositions are not new core state semantics.

## Network and attachment boundaries

Meshing consumes the local read interface; it does not query providers or run
its own provider classifier. It preserves complete references, source scope,
provider incarnation, evidence clocks, coverage and uncertainty. Network loss
adds transport uncertainty; it cannot label a remote session parked or make
old evidence current. Local revision/lease clock domains remain host-local;
the mesh must not compare raw boottime values across hosts.

`hostScope` is supplied scope, not host authentication. The network component
binds it to the authenticated route. Project grouping across hosts is separate
from logical session identity. Meshing can initially stay in existing clients;
this pass does not require a new network runtime or public mesh schema.

Context matching is deliberately outside observation. A separate layer may
combine an exact session reference with tmux-observer, niri or other window
evidence and report matched, unmatched or ambiguous context independently.
No mapping changes Observer's runtime, phase or evidence freshness. Being
unmatched does not make a running session parked; being attached does not make
an unknown native session running.

New/Resume/attach/focus live beyond this boundary. The existing separate writer
has its own accepted native-entry subset; it is not part of passive core.
Distinct thread/tree-root TUI entry remains unproved. Neither this boundary nor
an observed running row promises provider lifetime after TUI closure. The user
has deferred that acceptance while assuming ordinary TUI contexts remain alive.

## Pre-hardening source audit

This is an ownership audit, not a new native-state mismatch. a4's recorded
Codex acceptance remains bounded by its existing report.

| Finding | Current evidence | Hardening needed |
| --- | --- | --- |
| Public read facade is isolated | `public.py` and `service_public.py` expose validators/read helpers; existing import tests reject collection/action imports | Extend enforcement to alert clients and terminal/network layers, including transitive dependencies |
| Read semantics span service modules | `service_state.py` contains sample acceptance, retention, merge and expiry as well as clock defaults/service frames; `service_scheduler.py` owns refresh planning | Extract reusable observation decisions from service hosting/envelopes with injected clocks and explicit inputs |
| Direct CLI hosts collection | `cli._snapshot` calls `collection.collect`; direct watch uses `SampledWatch`, while service reconciliation uses `ServiceState` | Preserve explicit direct reads; share reconciliation rules without promising identical observations at different times |
| Provider dispatch remains distributed | `collection.py`, `_service_worker.py` and `_hint_worker.py` dispatch separately; private workers retain Claude branches although public a4 selection rejects Claude; `cli.py` retains a separate Claude history-census diagnostic path | Introduce a small adapter dispatch boundary and fail unsupported selection before any provider/helper activity, including optional diagnostics; retain no private legacy route solely for compatibility |
| Native hints have the right authority | `codex_hints.py` projects metadata to refresh components; `service_hints.py` validates helper epochs; scheduler coalesces hints | Keep parsing in adapters, lifecycle in the service and refresh decisions in the engine; ensure hint/feed loss never renews facts |
| Experimental normalization includes alert policy | `notification_source.normalize` includes child/noninteractive suppression, disposition, title and static body; `notification_client.py` renders Kitty/tmux output | Keep the experimental client isolated; separate native event facts from alert policy at its own future event/client gate |

The observation path currently contains no session-to-tmux/niri matcher and
does not import the separate writer or notification client. Remaining source
seams do not authorize adding those features to core.

## Focused execution and acceptance

Source implementation now uses `ObservationEngine`, `observation_scheduler`
and `observation_evidence`; service state is the host/envelope wrapper. One
passive adapter dispatch serves direct collection and owned helpers. Unsupported
private routes are rejected, and the history-census diagnostic option is removed.
Dependency tests enforce the read/action/alert boundary and core's independence
from host I/O/service/native implementations. The
[a5 completion report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
accepts the installed/native and separate managed operational gates on both
hosts. The steps below retain the original acceptance sequence.

1. Lock this ownership specification and add meaningful dependency/authority
   checks. Exercise transitive imports, rejection before unsupported provider
   invocation, and read/service independence from actions and alerts.
2. Consolidate passive adapter dispatch and its capability/source descriptors.
   Codex remains the only implemented selection; no plugin framework or Claude
   reimplementation is required to establish the seam.
3. Extract a reusable observation engine for sample ordering, failure retention,
   freshness and refresh planning. Move decisions incrementally with fake-clock
   and partial/outage/incarnation/hint-burst tests. Preserve API 2 semantics and
   current bounds; do not introduce a second provider state machine in service.
4. Route direct sampled watch and service hosting through those shared decisions.
   Keep service IPC/fan-out and CLI presentation separate. Verify cached pull
   and push consume one engine view, including gaps, expiry and resync.
5. Build an explicit candidate and compare its installed CLI against independent
   native evidence on Snap and Starship. Compare exact identity, running/parked,
   phase, age and coverage; verify no provider action, alert or terminal query
   occurs and preserve ordinary configuration/services/processes.

Run `./scripts/check` before publishing changes. Distinguish static/dependency,
controlled fake-adapter/clock, real service transport and native acceptance.
The pass is complete when the reusable core owns observation semantics and
adding a provider needs no new classifier in service, mesh or read clients.
This does not require a second live provider for the Codex-only checkpoint.

No API version bump is required for internal extraction that preserves the
accepted wire and semantics. A change in guarantees or public fields requires
its own explicit contract review. Managed rollout, new public native-event
feeds, network implementation, Claude and attachment/action client development
retain independent following gates.
