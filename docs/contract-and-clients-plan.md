# Observation contract and first-party clients plan

Date: 2026-10-03. Status: captured design direction; interface details and
implementation gates remain provisional. The user requested this documentation
and a deep review, not implementation, provider changes or consumer deployment.
The [review record](contract-and-clients-review.md) records source validation.
The [implementation/execution plan](contract-and-clients-execution-plan.md)
defines unattended work packages and the independent Observer acceptance gate
before any downstream Agent Plus edits.

This plan governs the next contract/client work. The existing
[snapshot contract](snapshot-contract.md), [native evidence](evidence/2026-10-03-native-runtime/REPORT.md)
and [pilot handoff](execution-handoff.md) remain authoritative for what actually
works today. This document does not change schema v1 or accept new native behavior.

## Purpose and decisions

Agent Observer is a shared foundation for Agent Plus, the RLCD dashboard, a
possible ESP32-349 consumer and a possible Kitty session client. Its contract
must be useful without importing a frontend or adopting one frontend's runtime
ownership. Observer and frontend implementation passes will have separate
scope, checks and delivery records.

| Decision | Direction |
| --- | --- |
| Providers | Codex is primary, including use across machines. Claude Code is a required secondary provider, initially on the one work machine. OpenCode remains deferred and removed from migrated Agent Plus. |
| Provider independence | The mesh prevents exclusive coupling to one provider or host. Work/general grouping remains explicit presentation policy, even though Claude is currently used for work and Codex mostly elsewhere. |
| Observation | The host-local core owns discovery and monitoring only. It does not dispatch provider actions or own remote transport. |
| Clients | Provide a first-party read CLI and a lightweight first-party write CLI in this repository. The write client owns New/Resume implementation; no separate interaction service or public action SDK is required initially. |
| Networking | A separate optional networking component can live in the same repository. Design its seam now; implementation/extraction is a later gate. Reuse existing Host Mesh authority and routing. |
| Runtime state | Keep runtime presence separate from work phase. Working, blocked and waiting describe an available runtime context. Parked is a derived display state for proven absence of that context. |
| Attention order | Default client ordering is blocked, waiting, working; within each group use last conversation activity, newest first. Parked history is a separate discovery view. |
| Session age | Last conversation activity is the desired default. Creation, observation, state-change and file-modification times remain distinct. |
| Profiles | One configured store per provider per host is sufficient initially. Do not build profile selection or multi-profile meshing now; retain necessary source/configuration validation. |
| Project context | Enrich recorded cwd with local Git facts and configured logical workspace roots plus relative paths. Cross-host project grouping is explicit mesh/client configuration, not native session identity. |

Commands, field names, package splits, polling intervals and project-mapping
syntax below are proposals. Their semantics need conformance fixtures and, for
native facts/actions, exact-version and topology proof before release claims.

## Repository and dependency boundaries

| Owner | Responsibility |
| --- | --- |
| Observation core | Local provider adapters; saved/live inventory; native identity mappings; bounded titles/cwd; state, chronology, health, coverage and local project enrichment |
| Read CLI | Human-readable list/show/watch/doctor views and machine output through the public observation contract; provider-neutral filters and presentation defaults |
| Write CLI | Explicit local New Here and Resume requests; action-specific target/artifact/configuration checks; necessary native preparation/dispatch and structured entry/handoff results |
| Optional networking component | Host selection, authenticated transport association, bounded collection/dispatch, compatibility checks, partial fleet results and configured cross-host project grouping |
| Agent Plus and other clients | User intent, selections, presentation, terminal/window or device transport, viewer binding and operation permissions |
| Native providers | Conversation storage, native IDs, workers/jobs, execution and native runtime lifecycle |

The observation core imports neither client action code nor remote transport.
The write client may consume fresh observations and shared identity/model
utilities. It owns provider-specific action code internally. Frontends invoke
its versioned CLI/JSON boundary rather than copying that code. Networking invokes
the same host-local public interfaces; it does not interpret provider-private
files or invent another provider adapter.

Start with separately testable modules/entry points and optional dependencies
within one coordinated repository release. Separate distributions are a later
deployment decision. A read-only installation must not acquire mandatory SSH,
Tmux, terminal-launch or write-client dependencies. Local provider IPC belongs
to the core; cross-host transport does not. No new network daemon is needed to
establish these interfaces.

Writing means acting on the native provider, not modifying Observer's inventory.
Observer subsequently discovers the effects. Passive commands must never call
the write client implicitly, auto-start a missing daemon, repair configuration
or resume a session to improve discovery.

## Discovery and monitoring

Discovery lists retained logical sessions, including saved-only sessions and
sessions with current runtime context. Monitoring describes current work on
that context. Inventory membership, runtime presence, job retention and client
attachment remain independent facts with independent coverage.

| Proposed phase/display state | Meaning | Required evidence |
| --- | --- | --- |
| Working | A turn is progressing without a proved need for human intervention | Accepted current native work evidence |
| Blocked | The current turn requires human intervention, such as an approval or answer | Accepted native wait evidence plus bounded reason; a slow tool or ordinary internal pause is insufficient |
| Waiting | No turn is in progress; the runtime is ready for another prompt | Current runtime context and independently proved readiness; includes fresh blank sessions, not just completed turns |
| Parked | Retained session without current runtime context | Current authoritative, complete absence evidence for the applicable provider/store/topology |
| Unknown | Required evidence is missing, conflicting or unaccepted | Explicit health, source and finite reason, with original last-known facts retained when appropriate |

Parked is not a work phase or a claim that the task finished. Prefer the
contract's explicit runtime-presence fact underneath this display label. A
stopped worker, detached TUI, retained terminal job, old transcript or omission
from a partial roster does not alone establish parked. "Stopped" is better
reserved for an observed termination/outcome, not a generic history label.
A retained Claude terminal completion labeled `settled` also does not alone
establish readiness for another prompt; waiting requires its own readiness proof.

An available Codex runtime context currently means a loaded server thread;
Claude currently proves selected exact OS-worker contexts. Neither means an
attached terminal. Do not equate a loaded thread with a working OS process or
collapse these native models merely to produce a common label. Final absence
predicates need per-provider, topology-specific proof, including scope and
multiple native contexts even though multiple configuration profiles are deferred.

The target semantics are distinct from the current v1 wire values
`working`, `needs_input`, `settled`, `interrupted`, `error`, `unknown`.
Proposed blocked/waiting terminology must not silently replace v1 values.
Agent Plus currently projects `needs_input` as `waiting` and `settled` as `idle`;
its current waiting label therefore has a different meaning from this plan.
The consumer projection must migrate under the new contract/version, with
explicit mismatch rejection rather than relabeling existing cached values.
Failures/interruption belong in an independently evidenced turn outcome; they
must not become ordinary waiting or successful completion. Questions and
approvals retain finite reason codes; their contents never cross the boundary.

Urgency is presentation policy, not provider action authority. A shared pure
ordering helper/default may serve the read CLI and consumers. Unknown or stale
rows carry visible health rather than entering a known-phase bucket. A device
may choose another ordering without changing the observation contract.

## Session metadata, identity and chronology

The shared model needs host scope/provenance, provider, stable native session
reference, bounded native title, recorded cwd, inventory kind, session/child
classification, independent runtime/work facts and coverage/health. Runtime/job
IDs and incarnations remain separate from the logical session reference.

Current exact identity is the five-field v1 tuple in
[the snapshot contract](snapshot-contract.md). Preserve it for existing consumers
and action validation. Its namespace hashes configuration and OS namespaces, so
do not claim it is a durable storage identity across reboots, containers or
configuration-path aliases. Before defining persistent selections, validate a
storage-scope identity distinct from runtime provenance and define scope-change
behavior. Do not guess aliases or merge equal UUIDs across hosts/stores.
Deferring profile UX does not justify deleting the existing guards.

| Timestamp concept | Purpose | Source rule |
| --- | --- | --- |
| Created | Conversation creation | Explicit accepted provider metadata |
| Last conversation activity | Age and default within-group ordering | Accepted conversation activity source; missing remains null/unknown |
| Phase changed | Duration in working/blocked/waiting | Native transition time or explicitly labeled first-observed transition, never an invented exact change time |
| Evidence/source time | When the underlying native evidence was asserted, when available | Preserve the source's meaning and original clock; does not become a phase/activity clock |
| Collected/sampled | When Observer read a fact | Per-fact collection clock; does not refresh the underlying work/activity time |
| File modified | Diagnostic saved-file metadata only | Never substitutes for conversation activity or runtime presence |

Codex's native `updatedAt` is currently exposed, but its conversation-activity
semantics still need validation against rename, metadata updates, reading and
runtime/client churn. Claude exposes SDK creation and file-modification times;
the latter is not the requested conversation clock. Current live work clocks
are not automatically phase-change or conversation-activity clocks.
In particular, current Claude `work.observedAt` carries native status/terminal
evidence time, while Codex work uses its observation clock. Preserve these v1
semantics; a new model must explicitly separate evidence time from collection
time rather than reinterpret the same field silently.
Validate a bounded metadata-only activity source, or report the field unsupported.
Do not silently fall back to creation, mtime or observation time under the same
label. A client may explicitly select a different, labeled ordering.
Define which native user/assistant/turn events advance conversation activity
before selecting a source; housekeeping, rename, Git inspection and liveness
polls must not advance it. History collection must apply the accepted ordering
before any display cap, or expose pagination/coverage sufficient to recover
old sessions with recent activity. Frontend sorting cannot repair an earlier
creation-based truncation.

Cross-host timestamps are useful approximate display chronology, not a causal
event order. Retain host provenance and source clocks; define handling of missing,
future/skewed and equal timestamps. Neither timestamps nor urgency grant an
action target. Phase-first ordering must not be mistaken for a global event log.

Confirmed child/subagent classification belongs in the common facts. The read
CLI and Agent Plus default views exclude only confirmed children. Unknown
classification remains visible and labeled unknown; an explicit include-children
filter supports inspection. Observation classification alone does not grant
action authority. Do not guess child status from a name, cwd or runtime PID.

Health is fact/dimension-specific as well as source-level. A saved scan failure
must not erase independently current live evidence when its shared scope remains
validated. Conversely, failed shared identity/incarnation validation invalidates
affected facts. Specify this distinction explicitly; an aggregate partial health
label alone must not cause clients to hide all current facts from that provider.

## Local Git and workspace enrichment

Perform bounded read-only enrichment on the host that owns the cwd. Preserve
the provider-recorded path separately from a resolved inspection path. For a
saved conversation, this describes the checkout as inspected now; it is not
historical evidence of the branch/project at the time of the turn.

Candidate metadata:

- Logical workspace-root ID and cwd relative to its configured host-local root.
- Detected Git checkout root and cwd relative to that checkout.
- Local repository/common-directory linkage sufficient to recognize linked
  worktrees; optional bounded branch with explicit detached/unborn handling.
- Inspection source/time/health and finite non-repository, missing-path,
  permission, timeout or unsupported reasons.

Git supports checkout-root and common-directory inspection; linked worktrees
have distinct checkout paths while sharing repository data. Use
[Git's documented interfaces](https://git-scm.com/docs/git-rev-parse) rather than
assuming `.git` is a directory. [Worktree documentation](https://git-scm.com/docs/git-worktree)
describes the distinction. Git facts are enrichment, never native session
identity or a prerequisite for listing non-Git sessions.

For example, configured logical root `code` may map to `/home/bryan/code` on
one host and another absolute root on another. An inspected session could report
repository path `agent-observer` and within-repository cwd `agent_observer`.
Matching those paths becomes an explicit grouping rule only when the configured
root mappings declare that relationship. A root label or repository basename
alone cannot establish a global project.

Root configuration belongs to local enrichment; shared project mappings belong
to networking/client configuration. Define component-aware containment,
overlapping-root precedence and symlink handling before implementation. A linked
worktree outside the configured root must not be silently assigned an unrelated
project. Preserve facts and use an explicit mapping when automatic grouping is
unproved. Non-Git projects can use configured paths without pretending to be repos.

The configured absolute root is required local configuration; whether that
additional path belongs in public output is a C2 decision. Most consumers can
use the logical root ID and relative paths. Explicit cross-host mappings may
join project context while checkout/worktree context and all native session
keys remain separate. Unmapped same-named repositories, clones and worktrees
must not acquire an automatic project link.

Cache by bounded local inspection context, not once per session row without a
budget. Do not recursively scan the host, run Git hooks, fetch, modify repositories
or collect full status/diffs. Git/environment overrides must not redirect an
inspection away from the selected cwd. Remote URL normalization is deferred;
if later added, remove credentials and treat it as a hint requiring an explicit
grouping policy, not automatic cross-host session merging.

## Read client and public contract

Today `agent-observer snapshot` is the machine-readable host-local producer.
Human list/show/watch/doctor operations do not yet exist. Entry-point names are
provisional; they must preserve an independently usable observation command.

The reference read client must use the public normalized model and documented
validation boundary, not provider-private collector functions. CLI output and
schema/conformance fixtures must let consumers in other languages integrate
without importing Python implementation internals. Include bounded errors,
null/unknown values, partial sources, duplicates and unsupported versions.
Parsing, filtering, ordering and projection must run on those fixtures without
provider homes, filesystem inspection, action modules or transport. The public
corpus supports separate Agent Plus/RLCD conformance checks; updating their
implementations remains in their own consumer passes.

Initial watch may poll snapshots. It must disclose polling semantics, gaps,
interval and sample age; it cannot promise every transition or reliable
turn-completion notifications. A reconnect/restart needs resynchronization and
last-known facts retain their original clocks. A true event interface requires
separate sequence/deduplication/coverage proof. No collector service is required
solely to make multiple clients use the same code.
Measure polling latency/cost and define a minimum supported interval, bounded
timeouts, cancellation behavior and no overlapping refreshes per watch. Multiple
consumers must not force unbounded reads or require an always-on collector.

Publish a schema and canonical metadata-only fixtures before calling the next
contract stable. Define additive-field tolerance and unknown-enum handling for
each supported version. Changes to identity, state meaning or existing required
fields require an explicit schema/version cutover and consumer pin update.
Prefer a bounded breaking prerelease migration to a second legacy discovery
stack. Fixtures are conformance evidence, not native provider proof.

## Push monitoring and source events

Push has two separate boundaries: provider-to-Observer evidence and
Observer-to-client updates. The core is currently snapshot/pull only. A passive
host-local watch interface should expose normalized updates to read clients
without requiring every provider to supply a native event stream. An initial
poll-and-diff backend can push observed changes; it remains sampled state, not
a complete native transition history.

Define the watch contract at C2 alongside snapshots: initial snapshot, scoped
revisions/incarnations, updates, health/gaps and explicit resynchronization.
Define snapshot/event race handling, duplicate/late delivery and bounded slow
consumer behavior. Collector revisions order this stream only; they are not a
native event clock or cross-host total order. Consumers can learn source/timing
capabilities without depending on whether polling, native events or hooks drive
the adapter. Reliable turn-completion notifications require separate event proof.

Prefer accepted native events where available, optional local hooks or metadata
file-change signals for demonstrated gaps, and periodic snapshots for coverage
and reconciliation. A file-change signal triggers inspection; mtime does not
become session phase or conversation activity. An unproved hook should wake an
authoritative refresh, not directly assign a final state.

Codex's [official App Server documentation](https://learn.chatgpt.com/docs/app-server)
describes status/turn notifications, but `thread/read` does not subscribe. A
passive observer connection's event coverage and subscription/lifetime effects
on the pinned managed runtime remain unproved. Do not resume/load threads merely
to obtain notifications. The current transport ignores unsolicited messages
while waiting for RPC responses; it is not a native event receiver.

For Claude, candidate [hooks](https://code.claude.com/docs/en/hooks) can signal
prompt submission, permission requests and Stop. Notification hooks have delay
and coverage limits; Stop may be followed by another hook's continuation.
[Codex hooks](https://learn.chatgpt.com/docs/hooks) likewise allow permission
decisions and Stop continuation. None of these candidates establishes a proved
all-session event source for our installed topologies. Native source comparison
and isolated hook output/delivery tests remain necessary.

If hooks add accepted coverage, a tiny host-local emitter sends only allowlisted
provider/store/session identity, event kind, optional native turn ID and timing
metadata to a bounded local sink. Exact identity/provenance must be validated;
subagent completion must never settle the parent turn. Keep prompts, responses,
tool inputs/output and raw hook payloads out of this path. Emitters preserve
other hooks and return event-specific neutral output: no permission decision,
context injection, continuation or stop. Delivery failure must not stall work.

Hook receivers and native watchers belong to passive observation. The write
client remains uninvolved. Watch can initially run on demand; a local shared
collector/sink is optional if fan-out or receiving hooks without an active
client justifies it. Sink downtime, queue overflow, reconnect and daemon restart
produce gaps and a fresh snapshot, never inferred idle. Hooks cannot reconstruct
unobserved earlier events, and no replay guarantee is implied.

Optional networking forwards the owning host's watch stream and preserves its
scope, revisions and gaps. Hooks never need to contact remote clients directly.
This keeps local push independent of cross-host networking and frontend work.
Hook installation is a separate managed/native gate, not an automatic effect
of installing or invoking the read client.

## Write client: narrow scope, explicit effects

The first-party write client is a consumer of observation, not a new Observer
action API. Initial operations are conceptual `new(provider, owningHostCwd)` and
`resume(exactSessionRef)`. A name such as `agent-session` is illustrative only.
Approval/denial, interrupt/stop, rename/delete, batch operations and terminal
focus/close are outside the initial write-client scope.

New Here works from a provider and explicit owning-host cwd with zero discovered
sessions. A stopped/missing daemon does not make a supported explicit native
launch impossible; action preflight must be independent of live inventory while
still proving provider artifact/configuration and action capability. Observation
itself must never start the runtime. Validate/chdir on the owning host immediately
before dispatch, with no fallback to home, implicit mkdir, worktree creation or
automatic trust acceptance. Provider trust prompts remain visible native UI.

Resume distinguishes an existing live context from saved-history activation.
Revalidate the full host/store/native reference with evidence appropriate to
that action; unsupported monitoring alone does not categorically prohibit an
independently validated saved resume. Codex preserves its explicit thread and
saved-session ID mapping. Claude live background attach uses an exact validated
short job ID; saved Resume uses the full conversation UUID and can create a copy.
Ordinary foreground Claude entry has no proved background-attach route.

Preserve the accepted Claude supervised route: closed-stdin empty `--bg`
creation/preparation, exact typed attach cue, default config context with
`CLAUDE_CONFIG_DIR` unset versus explicit root, and the per-launch overlay that
disables background worktree isolation. Codex New may only prepare native TUI
entry, with no UUID until the native client creates the conversation. Do not
invent a common provider lifecycle or require an initial prompt.

The structured result must retain separate requested and resulting identity,
permitted native entry/handoff, effect stage and finite outcome/reason. Exact
fields/enum names need fixtures covering at least:

- Rejected before dispatch, and known failure with no provider effect.
- Prepared entry, with session identity explicitly pending where necessary.
- Confirmed native effect and resulting identity/job when actually proved.
- Possible dispatch/effect with unknown outcome; never report this as safely retryable.
- Successful provider preparation followed by terminal/viewer failure; retain
  the provider effect and any known identity instead of creating another session.

Returned argv is not continuing authorization. Bind dispatch to the actual
executable, supported artifact, configuration and current target; do not validate
one binary then execute another through PATH. Prepared handoffs need an
execution-time revalidation mechanism, such as write-client execution inside
the terminal. Bound handoff age/scope and reject stale or changed preparation;
the exact mechanism is a design gate, not an implemented token scheme.

Machine-readable preparation/dispatch results must not share stdout with native
interactive TUI output. A write-client execution mode inside a terminal needs
an explicit native TTY handoff contract, separate from bounded JSON mode.
Interactive attach/resume must not run through the snapshot capture runner.

Caller/transport failure after possible dispatch cannot trigger an automatic
repeat of New/Resume. The write client owns provider effect classification;
networking owns transport certainty; frontend viewer recovery is independent.
Automatic job deletion/stop after presentation failure is not implied cleanup.
Bounded launcher cleanup must prove it does not kill an already-created native
worker/supervisor; a timeout is not authority to clean up provider-owned work.
Operation permission and user intent stay with the caller; shared technical
validation does not grant unattended action authority.

## Optional networking component

Networking consumes existing Host Mesh host authority and supplies remote
execution around the same local read/write interfaces. The current
`--host-scope` is caller-supplied provenance, not attestation; native hostname
is descriptive. Validate returned provenance
against the selected authenticated route using the existing Host Mesh contract.
Core neither enumerates hosts nor authenticates SSH endpoints.
Route-associated validation does not provide independent machine attestation;
Host Mesh supplies configured logical hosts, route identity and SSH policy.

Define separate transport failure, producer/source failure, contract mismatch
and stale-cache results. Bound concurrency, output, deadlines and per-host cache
retention. An unreachable host stays unavailable; its sessions do not become
parked or disappear from retained display solely because a refresh failed.
Healthy host/provider observations survive another source's failure.

Read retries/fallback may follow existing route authority. Writes pin one
validated route and have no automatic redispatch after any possible effect.
Any retry after an explicit, proved pre-action rejection needs a documented
operation-specific rule; it must not reuse read fallback behavior.
Absence of a remote completion/launch marker does not prove no write occurred.
Remote loss, suspend/resume and route changes need separate acceptance; schema
fixtures do not establish those native behaviors.

No operation journal or idempotency service is required for this first pass.
A request ID may support correlation but does not guarantee provider duplicate
prevention. Recovery begins with reporting retained effects and fresh observation.

The component may also compose explicit cross-host project mappings. It never
merges equal UUIDs into one conversation, copies history or adopts provider
lifecycle ownership. The read CLI/core acceptance gate does not require this
component, an always-on service, or a frontend migration.

## Current implementation gaps and delivery

| Gap | Current source/evidence | Required decision or proof |
| --- | --- | --- |
| Parked | Codex saved-only and Claude saved-only rows report unknown presence; incomplete observations cannot prove absence | Per-provider absence predicates and complete scoped coverage; keep unknown until accepted |
| Daemon-off discovery | Codex saved discovery currently needs an existing managed endpoint | Investigate an existing-only passive saved source, or explicitly declare unavailable history; no auto-start/fallback launch |
| General blocked input | Only selected approval waits are native accepted | Isolated question/input proof for each intended topology, or explicit unsupported capability |
| Conversation age | Native Codex updated time and Claude creation/file times do not prove the shared desired clock | Validate activity semantics or publish unsupported/null without false fallback |
| Durable session reference | v1 namespace includes OS context | Storage/runtime scope separation, namespace-change/alias tests and explicit schema cutover |
| Formal conformance/read CLI | Snapshot producer exists; strict consumer validation is substantially in Agent Plus/RLCD | Public schema, canonical fixtures, reusable provider-neutral validation and human read client |
| New/Resume write client | Provider actions currently live in Agent Plus and New inherits a selected row | Independent preflight, empty-inventory New, structured effects and execution-time validation |
| Networking | Agent Plus currently composes through Host Mesh | Optional extraction behind local contracts; separate read/write transport rules and validation |

| Checkpoint | Dependencies | Exit and scope |
| --- | --- | --- |
| C0: capture/review | Current checkouts and conversation | This plan, independent source/consumer review, resolved documentation findings and repository checks; no runtime claims |
| C1: model/source decisions | C0 | Presence/phase/absence semantics, durable identity, conversation clock and Git/root rules; exact capabilities and open proofs recorded |
| C2: public contract | C1 | Versioned snapshot/watch schema, metadata-only success/failure/gap fixtures, conformance boundary, evolution rules and both-provider consumer fit |
| C3: read client | C2 | Local list/show/doctor and watch stream, initially sampled polling; partial/unknown states, age and child filters validated; no action/network dependency |
| C4: write client | C2; action-specific native proofs | New/Resume JSON/entry contract, zero-row New, exact local guards, resulting identity/effect uncertainty and native handoff acceptance |
| C5: optional networking | C2/C3; C4 for writes | Existing Host Mesh composition, bounded partial feeds and separate read/write dispatch semantics; cross-host native recovery is separately accepted |
| Consumer passes | Compatible contract/client releases | Agent Plus, RLCD and future clients migrate independently, each with its own UI/device/installed acceptance |

The preferred execution order is C1/C2, local read client, write client, then
optional networking extraction. Read-only networking can proceed without C4;
RLCD does not depend on write/network implementation. Consumers remain pinned
to compatible artifacts until their own migrations; no core task also edits a
frontend or deploys provider policy merely to close its gate.

C1/C2 can explicitly publish unsupported/null optional dimensions; the local
read client need not wait for every activity, parked or general-question proof.
Agree on semantics and capability reporting first, then accept additional native
facts independently. Unsupported results are not substitutes for proving a
dimension that a particular consumer/action actually requires.

Native proofs use isolated disposable configurations/endpoints and preserve
ordinary hooks, sessions and services. Repeat source/installed/native validation
only for newly introduced behavior. The pilot's outstanding GUI, recovery,
release and coordinator-reopen gates remain in the existing handoff; this
contract pass neither closes them nor requires restarting the current session.
