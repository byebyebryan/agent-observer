# Observer API 2

Date: 2026-10-08. Prerelease producer contract. Source implementation is complete;
final packaged native acceptance is tracked in the
[reconciliation plan](codex-daemon-authority-plan.md). This document supersedes
[API 1](api-v1.md) for new clients. Installed normal selection remains a16 until
a separate operational gate. No old-wire converter is supplied.

## Interfaces and ownership

| Interface | Version | Entry point |
| --- | --- | --- |
| Pure read API | 2 | `agent_observer.public`, `agent-observer api` |
| Snapshot / sampled watch | 4 / 4 | `snapshot`, `watch`, bundled JSON Schemas |
| Cached pull / push | service protocol 2 | `agent-observer service snapshot/watch/status` |
| Explicit local New / Resume | separate writer wire 2 | `agent-observer-write prepare/execute/enter` |

The pure read facade exports validators, selectors and schema descriptors only.
It does not import collecting or action modules. Collection authenticates an
existing provider endpoint; it neither starts a provider nor reads terminal
attachment, tmux state, private saved databases or rollout logs. The service
owns collection helpers, leases and read fan-out. Clients own provider actions,
TUI lifetime, terminal placement and viewers. Networking is a separate component.

The implemented provider is Codex. Explicit Claude collection or write selection
returns `unsupported_provider`; reserved Claude identity/schema fixtures do not
establish a native adapter. Claude gets a separate reconciliation checkpoint.
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
saved identity independently of runtime state. `inventory` records whether the
current row comes from a live or saved disposition; it is not action authority.
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
all ten source kinds, 1000 catalog rows, up to 512 loaded/runtime rows by default,
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

Cached snapshot and watch share one published view. Protocol 2 preserves service
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
A distinct thread/tree-root TUI route returns `session_tree_entry_unproved`
until its native action target is independently accepted.

Clients must rebuild against wire 4/protocol 2, treat parked phase as null,
consume blockedReasons as a set, distinguish saved existence from running state,
and own attachment/action validation. Agent Plus implementation and managed
consumer selection are separate gates. Tmux Plus is unchanged.
