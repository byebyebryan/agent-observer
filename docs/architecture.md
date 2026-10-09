# Agent Observer architecture boundaries

The [observation ownership clarification](observation-boundaries.md) defines
the implemented boundary: core contains the model, passive adapters and reusable
observation engine; the service hosts it and provides local IPC. Provider refresh
signals, pushed read updates and user-facing alerts have separate ownership.
Meshing and terminal/window matching remain external. The
[a5 completion report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
records source/artifact/native acceptance without changing API 2. Normal read
CLI/service selection now uses [a8 Claude observation](evidence/2026-10-08-claude-observation/REPORT.md)
after independent artifact/native and scoped operational acceptance. History
and runtime receipts from one sample publish one view with independent leases.
The independently selected writer remains a16.

The next [Claude interactive reconciliation](claude-interactive-observation-plan.md)
keeps Observer upstream of all clients. Under the user's accepted native-registration
assumption, healthy provider-owned scans and authenticated incarnation checks
classify positively saved interactive UUIDs with no live context as parked,
including after normal exit or crash. Missing live registration can cause false
parked classification, so coverage remains partial with that explicit limitation.
Client inventory and attachment are outside observation. Background runtime
support is excluded; implementation and Agent View opt-out retain separate gates.
This design does not change the accepted a8 artifact or wires.

The [2026-10-08 Codex daemon authority reconciliation](codex-daemon-authority-plan.md)
governs the accepted producer correction. It supersedes earlier loaded-only
discovery, terminal/job field scaffolding, compatibility obligations and the
requirement to complete Claude proof before this common-contract checkpoint.
Codex owns execution and native runtime disposition; Observer core/service own
passive reads, evidence, reconciliation and fan-out; clients own native entry,
TUI lifetime and terminal attachment. The observation path has no TUI/tmux state
authority. Claude's independent observation gate accepts provider-owned native
registration/status metadata and a bounded terminal-job parked predicate on
Snap, without terminal matching. Saved-only lifecycle remains unknown and
post-TUI-closure Codex acceptance is deferred.
The [review](codex-daemon-authority-review.md) led to API 2/read wire 4/service 2
with clean rejection of the old wire. The following
[saved-evidence repair](codex-evidence-repair-plan.md) accepts the a4 successor
through [packaged/native acceptance](evidence/2026-10-08-codex-evidence-repair/REPORT.md)
on both hosts. It precedes the a5 core/operational checkpoint; historical reports
below retain their original bounds. See the [API 2 client handoff](api-v2-client-handoff.md).
Future terminal discovery/attachment can consume tmux-observer through clients;
it is not an Observer core implementation or acceptance dependency.

The [shared observation service proposal](shared-observation-service-plan.md)
adds a separately reviewed local runtime for collection, pull and push fan-out.
Its [review](shared-observation-service-review.md) and
[execution gates](shared-observation-service-execution-plan.md) retain the pure
API v1 facade and a separately versioned local service envelope.
It preserves pure core, provider ownership and external networking boundaries;
The [service implementation](shared-observation-service-status.md) now supplies
shared leased samples, bounded Unix fan-out and an explicit cached read client.
Native lifetime and operational acceptance are recorded per case; normal
selection, networking, hooks and downstream migrations remain separate gates.

The [2026-10-06 provider compatibility policy](provider-contract-compatibility-plan.md)
governs future native support: required contracts and observed capabilities
determine compatibility. Release versions and hashes record provenance and
incarnation changes; routine provider upgrades do not require allowlist entries.
The [API v1 contract](api-v1.md) and [a2 acceptance](evidence/2026-10-06-stable-api/REPORT.md)
implement this policy. The version-gated pilot description below is historical;
the [historical service handoff](shared-observation-service-handoff.md) records a16
selection with passive native hints and periodic reconciliation. Consumer
migration retains a separate delivery gate.

The [contract and clients plan](contract-and-clients-plan.md), captured
2026-10-03, defines the next development track: a passive host-local core,
first-party read/write clients and optional networking in the same repository.
It takes precedence for future extraction/ownership; the sections below record
the current migration-pilot boundary. No proposed terminology changes schema v1.
See the [new review](contract-and-clients-review.md) for source gaps and gates.

Date: 2026-10-02. Status: accepted ownership and product direction; source,
source coverage remains version/topology gated. Python and the host-local JSON
[contract candidate](snapshot-contract.md) are selected from native evidence;
release stability and ordinary runtime/consumer acceptance remain pending.
The [migration plan](native-runtime-migration-plan.md) defines delivery and
acceptance; the [roadmap](roadmap.md) records current status.

## Purpose and product boundaries

Agent Observer provides reusable host-side provider discovery and observation
for Agent Plus and RLCD. Agent Plus meshes sessions across providers and hosts;
RLCD needs a reliable live roster. Provider independence is an architectural
requirement. Codex leads delivery because it is used most frequently and across
machines. Claude Code remains a required second provider, initially on the
user's single work machine.

The target is provider-managed execution with individual native TUI entry.
Codex's shared server and Claude's supervised background jobs have different
models. Their adapters preserve those differences behind common observations
and explicit capabilities. Native behavior must be proved before choosing a
source or claiming a supported topology.

OpenCode support in Agent Plus is deprecated and removed at migration cutover.
Its observation/action adapters are outside this migration. WSNav supplies
historical evidence and may be a future consumer; its runtime model, language
and integration are not gates.

## Ownership

| Owner | Responsibility |
| --- | --- |
| Native provider | Conversation history and IDs, work execution, jobs/workers, native runtime lifecycle and native UI semantics |
| Agent Observer | Provider observation adapters, saved/live inventory, exact identity mappings, bounded metadata, work/presence evidence, capabilities, freshness and reconciliation |
| Agent Plus | Cross-host/provider composition, picker presentation, optional context organization, host routing, viewer association, provider action adapters and action validation |
| SSH Plus / Tmux Plus | Host authority/routes and public terminal/window lifecycle with exact references and viewer handles |
| Managed host configuration | Provider runtime policy, compatible artifact installation/pins, hooks/plugins and per-host rollout |
| RLCD host bridge | Session selection/prioritization, dashboard representation and device transport |

Observer observations are evidence, not permission or an operation handle.
Observer cannot start, resume, background, interrupt, approve, deny, rename,
archive or delete provider sessions. Consumer actions remain separate from the
observation interface and revalidate their exact targets.

The reuse boundary is host-local JSON. Agent Plus reaches the owning host using
existing Host Mesh routing, validates its Observer result, and composes the mesh.
Observer neither chooses SSH routes nor introduces a network control plane.
Tmux retains terminal clients; it is not the source of provider job ownership.

## Identity and session meshing

Separate logical conversations, saved history, retained jobs, runtime workers
and client attachments. A conversation can have no running worker; a retained
job can survive worker retirement; one conversation can have several clients.
Client or worker exit alone cannot establish logical-session end.

Scope native identity to its owning host, provider and applicable configuration
or runtime namespace. Preserve distinct native IDs, job IDs and runtime
incarnations until their mapping is proved. Codex thread and session IDs must
not be collapsed from schema names alone. Claude short job IDs must not replace
conversation UUIDs. Different namespaces can require separate records even on
the same machine.

Host Mesh owns logical host authority and routing. The consumer validates
returned machine/source provenance against its selected host; a display hostname
is not sufficient identity. Native ID equality on different hosts is not a
cross-host conversation link. Cwd, title, launch arguments, PID and file mtime
cannot resolve ambiguous identity by themselves.

Provider-specific reads and actions belong in separate adapter boundaries.
Shared consumer logic works with normalized observations and capabilities;
adding a future provider should not require interpreting its private runtime
data throughout the UI or rebuilding the host mesh. A host offering only Claude
must work without a Codex dependency in generic startup or routing.

The user currently uses Claude exclusively for work and Codex mostly for other
activity, with occasional work use. Preserve those context distinctions in
presentation. Any context grouping is explicit consumer policy, independent of
provider/host identity and native source interpretation. Context tagging and a
persistent session rail are optional later presentation work.

## Observation contract proposal

The following are semantic requirements, not a stable wire schema or implemented
CLI. Consumers may prototype against clearly labeled bounded fixtures. Choose
exact fields and representation from native proof.

| Information | Required distinction |
| --- | --- |
| Envelope | Schema version, collection identity/revision, host/source provenance and per-provider/namespace coverage/errors |
| Saved inventory | Logical/native IDs, bounded native title/cwd metadata, available history and pagination; independent of live work |
| Native job/runtime | Optional retained job ID, owning endpoint/namespace, actual provider/runtime version, topology and incarnation |
| Current observations | Work state/reason, runtime presence, job retention and attachment evidence, each independently unknown when unproved |
| Freshness | State and presence observation times, source provenance, observation health and recovery/gap information |
| Capabilities | Supported/pending/unsupported versions, topologies, observation dimensions and known side effects; separate from action permission |

Bound native title metadata and use an ID-based display fallback. Do not derive
previews from prompts or parse conversation content for a name. Retain neither
credentials, prompt/response text, tool arguments/output, terminal captures nor
raw provider payloads. Filter source payloads in memory before emitting,
logging or persisting allowlisted metadata. Bound input sizes and diagnostics;
oversized or malformed responses produce explicit failed/incomplete coverage.

Saved inventory may be paginated or display-limited. Live coverage must remain
explicit and independent: old live sessions cannot disappear because history
was capped. A partial or failed roster cannot prove that missing rows are
inactive or deleted. Keep uncertainty per provider/namespace so one failure
does not erase healthy observations elsewhere.

Candidate work states are working, needs input, settled, interrupted, error and
unknown. Settled does not establish task success. Keep bounded native state and
reason codes when normalization loses useful distinctions. Runtime presence,
job retention, client attachment and local viewer-window presence are separate
dimensions. Native approval/input waits are distinct from deferred TUI launch.

## Freshness ordering and recovery

A liveness refresh updates presence evidence, not the age of previous work
state. Do not expire a long running turn merely because hooks are silent. After
an observation gap, recover from an authoritative source or expose uncertainty;
absence of events does not establish settled/idle.

Define collection epochs/revisions and per-source ordering at P5. Reject late
callbacks from a previous identity binding or runtime incarnation. Do not use
wall-clock timestamps to order unrelated hosts or invent a total provider event
order. Watch reconnect must report a gap and resynchronize; when the source
cannot reconstruct a state, it remains unknown until new authoritative evidence.

Worker/PID reuse, daemon restart and client churn require fresh incarnation and
binding checks. Retained metadata may remain visible with its original age and
health. It cannot authorize an action merely because a new process is alive.

## Observation operations and process lifetime

| Proposed operation | Purpose |
| --- | --- |
| Snapshot | Return saved/live observations, provenance, coverage and freshness |
| Watch | Initial snapshot plus changes, with explicit revisions, gaps and recovery |
| Capabilities | Report version/topology/source support and bounded limitation reasons |

Start with the smallest passive host-local implementation that serves consumer
needs. Snapshot is the initial candidate; watch or a shared collector follows
measured source behavior, latency and concurrent-consumer cost. No background
service is required solely to share code. A collector's lifetime is separate
from a provider's daemon and must not turn Observer into its runtime owner.

An absent runtime produces unavailable/capability evidence. Observer must not
invoke an entry point that auto-starts a provider daemon, loads/resumes work or
changes settings to make discovery succeed. Subscription/disconnect effects,
including loaded-thread or worker lifetime, are part of passivity proof.
Claude's CLI roster has observed initialization/housekeeping writes in isolated
empty cases; its populated ordinary path is not yet accepted as passive.

Native state feeds are the first source candidates: Codex reads from the actual
owning server and Claude's documented roster where it meets the invariants.
A separate metadata helper cannot prove another runtime's live status. Hooks
are added only for demonstrated coverage gaps, with bounded event-specific
passive output and failure behavior. Process evidence supports reconciliation;
it does not confer action authority or solve an ambiguous native mapping.

## Consumer actions and viewer bindings

Agent Plus selects among focus of an existing viewer, attachment to existing
native work, explicit history resume and creation of new work. Its provider
action adapters use proved native routes; Tmux Plus creates/opens the terminal
client under current Host Mesh authority. Observer supplies observations, not
launch commands. Creation/worktree policy belongs to consumer/provider setup.

Revalidate logical host authority, provider namespace, selected native identity,
current runtime disposition and the applicable Tmux/viewer reference before an
action. Observation capabilities do not imply permission or safe support for
every action. Schema mismatch, stale scope, missing evidence or ambiguity must
produce a bounded rejection or exclusion.

Require evidence relevant to the selected operation. Missing work-state coverage
alone does not prohibit a window-only action whose current conversation binding
and exact viewer handle are independently verified. An unknown current binding
still prevents session-specific focus/close. Keep these guards distinct from
the presentation of monitoring uncertainty.

A tmux option records launch association. After native new/resume/fork or a
return to the provider manager, it may no longer describe the current view.
Prove a current client/conversation binding or invalidate it. Preserve native
navigation; do not call an old launch marker a current binding. Session-specific
focus/close needs that binding plus exact terminal/window validation. Generic
terminal management retains the separate Tmux Plus authority.

Viewer Close keeps its window-only meaning. Native detach, TUI exit, cancellation
and native Stop must be tested separately. Batch attachment to live jobs without
wrappers is a separate action-contract change with frozen previews and exact
per-target revalidation; it never silently activates saved history or new jobs.

## Contract decisions and delivery scope

Codex leads the complete native-runtime/Observer/Agent Plus integration. Check
Claude's job/session/client distinctions early. A Codex milestone may proceed
with Claude explicitly pending; stabilize the shared contract only after native
evidence demonstrates both providers' identity/lifecycle models. The completed
Agent Plus migration includes both-provider acceptance and cross-host Codex
acceptance. RLCD reviews the common observation requirements before contract
stabilization and has an independent bridge/firmware delivery track.

Source choices, implementation language, exact schema/ordering, limits, polling
intervals and collector deployment follow P1-P5 evidence and measurements.
Foreground results are comparative/transition evidence; full foreground feature
parity is not a prerequisite for the managed-runtime target. Keep unsupported
topologies explicit, without silently restoring the retired discovery stack.

Production runtime changes, hook installation, packaging, consumer migration and
deployment are later delivery checkpoints in the migration plan. This design
pass does not execute them. OpenCode adapters, WSNav integration, transcript
archives/search and a new Observer network control plane remain outside scope.
