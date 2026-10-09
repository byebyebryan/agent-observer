# Observer API 2

Date: 2026-10-08. Prerelease producer contract. The Codex a3 packaged/native gate
is [accepted on both hosts](evidence/2026-10-08-codex-authority-acceptance/REPORT.md).
The [a4 saved-evidence repair](evidence/2026-10-08-codex-evidence-repair/REPORT.md)
precedes the [a5 core completion](evidence/2026-10-08-codex-observation-completion/REPORT.md)
with the same API/wires. The [a6 successor](evidence/2026-10-08-codex-observation-gaps/REPORT.md)
removes redundant publication; normal read CLI/services select it after separate
installed/native and scoped operational acceptance. The following
[a8 Claude gate](evidence/2026-10-08-claude-observation/REPORT.md) preserves these
interfaces and adds passive Claude discovery/monitoring on Snap. The writer
remains independently selected at a16.
This document supersedes
[API 1](api-v1.md) for new read clients. No old-wire converter is supplied.

## Interfaces and ownership

The [ownership specification and source audit](observation-boundaries.md)
clarify core/model/adapter/engine, local service, mesh and read-client boundaries.
The implemented internal extraction preserves this contract. Native refresh hints,
read push and user-facing notification delivery are separate concerns; this
read API supplies no terminal/window matching or public attention-event stream.

| Interface | Version | Entry point |
| --- | --- | --- |
| Pure read API | 2 | `agent_observer.public`, `agent-observer api` |
| Snapshot / sampled watch | 4 / 4 | `snapshot`, `watch`, bundled JSON Schemas |
| Cached pull / push | service protocol 2 | `agent-observer service snapshot/watch/status` |
| Explicit local New / Resume | separate writer wire 2 | `agent-observer-write prepare/execute/enter` |

The pure read facade exports validators, selectors and schema descriptors only.
It does not import collecting or action modules. Collection authenticates an
existing provider endpoint or provider-owned session registration; it neither
starts a provider nor reads terminal attachment or tmux state. Codex history is
read through its daemon; Claude history projects bounded native transcript/SDK
metadata without retaining conversation contents. The service
owns collection helpers, leases and read fan-out. Clients own provider actions,
TUI lifetime, terminal placement and viewers. Networking is a separate component.

The implemented providers are Codex and Claude. Claude observation is accepted
on Snap through its independent native gate; new Claude write selection still
returns `unsupported_provider`.
Provider support binds required contracts, with versions/hashes as diagnostics
and executable/incarnation guards.

## Discovery and monitoring

Identity is the exact scoped tuple `hostScope/provider/namespace/nativeIdKind/nativeId`.
Codex `nativeIds.threadId` equals the identity's thread ID.
`nativeIds.sessionTreeRootId` is independent tree metadata and does not merge rows
or prove a child. Native classification gives `kind=user/child/unknown`; default
list hides only positively classified children. Unknown kinds remain visible.

Each row contains title, recorded cwd, workspace/project facts, creation time,
conversation activity and latest turn outcome. `hasSavedHistory` reports positive
saved identity independently of runtime state. `inventory` records saved-catalog
evidence or runtime-only membership; it does not classify lifecycle or grant action authority.
There are no common worker, terminal attachment, client binding or Claude-job fields.

| Positive current native status | Runtime | Phase | Blocked reasons |
| --- | --- | --- | --- |
| active, empty valid flags | running | working | empty |
| active, known wait flags | running | blocked | approval, question, or both |
| idle | running | waiting | empty |
| systemError | running | unknown | empty; finite native runtime error reason |
| notLoaded plus readable saved identity | parked | null | empty |
| missing/conflicting/stale/unsupported state | unknown | unknown | empty |

Runtime and phase are evidence records: value, source, health, observedAt,
reason and clock; stale records may keep lastKnownValue. Known phase requires
current running evidence from the same native sample. Parked requires positive
saved identity and phase null. A parked sample that expires becomes runtime
unknown and phase unknown, preserving its original clock and last-known parked
fact. Missing loaded membership and terminal exit never establish parked.
Unknown wait flags preserve known active runtime but leave phase unknown.

Conversation activity has its own native clock and health. Collection, rename,
Resume, enrichment and lease renewal never move it. Empty conversations have no
activity clock. Human age is computed when displayed; stale age uses lastKnownAt
and stays visibly stale. Read ordering is blocked, waiting, working, then
unknown/parked, with newest conversation activity within each group.

## Scope, bounds and failure

Each source declares namespace/config selector, authenticated runtime diagnostics,
capabilities, independent saved/runtime coverage, errors, limitations and nullable
`discovery` query metadata. Codex discovery declares database-only catalog mode,
all ten source kinds within the native non-archived catalog, 1000 catalog rows,
up to 512 loaded/runtime rows by default,
1000 parked-history rows, 64 pages, 2 MiB native message bound and whether parked
conversation clocks are collected. Exact writer preflight declares its one-row
query separately. Unavailable source placeholders may have discovery null.

Runtime coverage scope is `daemon_threads` for Codex. Catalog and complementary
loaded inventory are sampled independently. Every positively running candidate
is protected before parked-history limits. Bounds, unreadable summaries and
unknown status make coverage partial; healthy sibling facts remain current.
Database-only placeholders without a readable summary remain unresolved.
Direct reads with an unavailable daemon return no current rows and finite source
failure; they never fall back to a private store. Existing watch/service rows may
remain stale under bounded retention.

## Pull and push

Direct snapshots and sampled watch use the same projection as service workers.
The service's fast cycle also samples saved-thread daemon state. Its slower cycle
adds conversation clocks and workspace enrichment. A native status obtained by
metadata work is deliberately accepted under the short runtime lease and sample
ordering rules; metadata-only refresh cannot renew state.

A history sample that also contains current runtime evidence updates both
receipts before one published view. Their leases remain independent. View
revision counts publications, not native events; genuine coalescing still
requires gap/resync handling.

Cached snapshot and watch share one published view. [Protocol 2](service-protocol-v2.md) preserves service
identity, monotonic view revision, per-connection sequence, clock domain and
component leases. Heartbeats do not renew collection facts. Gaps, expiry and
incarnation changes preserve uncertainty and old clocks; clients reconnect and
request a resync rather than infer missed events. Push is sampled read fan-out,
not lossless native event replay or a notification-completion guarantee.

## Writer boundary and client migration

Writer preparation is passive and returns an explicit TTY handoff. `execute`
revalidates and still reports `prepared/effect=none`; only `enter` replaces the
foreground process with native Codex New/Resume. New identity is pending until
native discovery. Exact Resume uses uncapped `thread/read` and passes threadId,
never a catalog position, title, cwd guess or tree-root substitution. It guards
cwd/config, executable/settings and owning incarnation between preparation and
entry. Saved/live disposition changes alone do not invalidate exact identity.
The [saved-evidence repair](codex-evidence-repair-plan.md) additionally requires
an explicitly non-ephemeral summary and successful metadata-only stored-history
pagination before Resume preparation/revalidation. Empty history is allowed;
unproved persistence fails with `resume_saved_history_unproved`. Native path,
title, cwd and an activity clock do not substitute for this proof.
A distinct thread/tree-root TUI route returns `session_tree_entry_unproved`
until its native action target is independently accepted.

The [client handoff](api-v2-client-handoff.md) identifies the explicit installed
candidate and separate consumer/selection gates. Clients must rebuild against
wire 4/protocol 2, treat parked phase as null,
consume blockedReasons as a set, distinguish saved existence from running state,
and own attachment/action validation. Agent Plus implementation and managed
consumer selection are separate gates. Tmux Plus is unchanged.
