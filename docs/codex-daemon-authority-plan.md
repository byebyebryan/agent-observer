# Codex daemon authority reconciliation

Date: 2026-10-08. Status: D1–D4 and the supported separate writer subset are
[accepted against 0.5.0a3](evidence/2026-10-08-codex-authority-acceptance/REPORT.md)
on Snap and Starship. Managed selection and Claude remain separate next gates.
This document governs the Observer reconciliation. The
[original review](codex-daemon-authority-review.md) and its
[baseline evidence](evidence/2026-10-08-codex-authority-review/REPORT.md)
retain the pre-correction findings.

The selected a16/API 1/wire 3 implementation remains the operational baseline.
Its documented loaded-thread and Claude parked predicates are historical
acceptance bounds, not the target for this checkpoint. Native actions were
restricted to isolated disposable namespaces; ordinary provider settings/hooks,
sessions, selected services and consumer repositories were preserved.

## Decisions and scope

- Codex is the sole acceptance target for this checkpoint, independently on
  Snap and Starship. Claude is the next provider checkpoint. Claude breakage
  does not block this work or justify retaining a weaker common contract.
- The common observation interface remains provider independent. Provider
  adapters establish their own native authority; they do not expose one
  provider's terminal/job model as mandatory fields for every provider.
- The Codex shared daemon owns execution and runtime lifecycle. Observer obtains
  running/parked state from the verified owning daemon, using passive reads.
- Clients own native New/Resume entry, TUI lifetime, tmux placement, attachment
  and viewer association. The normal workflow may keep TUIs alive to retain
  daemon contexts. Observer neither checks nor enforces that workflow.
- Post-TUI-closure lifetime experiments and headless-entry topology acceptance
  are deferred. Collection and projection must not branch on terminal presence;
  an available authoritative native state uses the same classifier.
- Breaking API/wire changes are authorized. Do not add old-wire converters,
  legacy collectors, terminal correlation or Claude compatibility shims.
- This pass reconciles design and records an implementation sequence. Provider
  actions, source implementation, managed selection and frontend migration
  retain separate acceptance gates.

## Ownership to enforce

| Owner | Owns | Boundary |
| --- | --- | --- |
| Codex daemon | Native conversation/thread metadata, execution, live session trees and runtime lifecycle | Its current thread status is the runtime authority within the selected managed namespace |
| Observer core | Passive native reads, exact identity, discovery, monitoring, activity, coverage, freshness and local project facts | No provider actions, terminal inspection or runtime upkeep |
| Observer service | Collection helpers, scheduling, leases, reconciliation and read-side pull/push fan-out | It owns only Observer processes; it does not own or keep alive provider sessions |
| First-party write client | Explicit local native New/Resume preflight and TTY handoff | Separate contract, imports and native action acceptance |
| Terminal/UI clients | User intent, TUI lifetime, tmux/Kitty attachment, viewer binding and presentation | Attachment facts never change Observer runtime/work facts |
| Host mesh/networking | Host authority, authenticated routing and composition | Outside host-local core; no networking prerequisite for Codex acceptance |

OS endpoint ownership, peer credentials, executable identity and process birth
checks remain necessary to authenticate the native observation context. They
do not classify a conversation as running or parked. Reading TUI PIDs, tmux
options, client counts, terminal captures or viewer-window state is outside the
Codex observation path.

## Runtime and monitoring semantics

The supported scope is the configured managed Codex namespace. This is not a
claim about execution in other standalone processes, stores or hosts. Runtime
state and conversation identity survive changes in how a client presents them.

| Current daemon status for the exact thread | Runtime | Phase | Meaning |
| --- | --- | --- | --- |
| `active`, empty valid flags | running | working | Native turn is progressing |
| `active`, known approval/question flags | running | blocked | Native turn needs human input; retain the bounded reason set |
| `idle` | running | waiting | Runtime exists and is ready for another prompt |
| `systemError` | running | unknown | Runtime exists, but the ordinary work phase is unavailable; preserve a finite native-error reason |
| `notLoaded`, with positive saved-thread identity | parked | not applicable | Saved thread has no context in the owning daemon |
| Missing, unsupported, conflicting or stale status | unknown | unknown | Preserve the appropriate health, reason and last-known facts |

Parked means unloaded, not deleted, successfully completed, attached or
resumable through every client route. It requires positive native status and
saved-thread identity; absence from a loaded list, a missing TUI or failed RPC
does not establish it. A saved thread may have no known conversation-activity
clock. A loaded blank thread may be running without a saved catalog entry.

Both known wait flags establish blocked with both reasons. Unknown/malformed
flags preserve running if `active` itself is valid, but leave phase unknown.
Native runtime errors and latest turn outcomes remain separate. Neither a
completion callback nor an old completed turn establishes current waiting.

Wire 4 represents phase as null when runtime is positively parked.
For running/unknown runtime it carries phase evidence, including explicit
unknown where needed. Expiring a parked runtime sample replaces null with
unknown phase and stale runtime evidence; it does not claim current absence.
Known working/blocked/waiting always requires current running evidence from
the same native context. Blocked has a nonempty, unique bounded reason set;
other phases and parked have no blocked reasons.

## Identity, metadata and chronology

Keep the scoped thread reference as the identity of a Codex row. Preserve the
existing host/provider/store separation and runtime incarnation as independent
provenance. A daemon upgrade/restart must not create a new logical conversation
identity or make previous state current again.

Codex `thread.id` selects an individual conversation. `thread.sessionId` is
the live session-tree root; it is separate metadata and can differ on a fork.
Name it `sessionTreeRootId` in the next Codex metadata projection. Never merge
rows or select a Resume target through equality of root IDs, titles, cwd or
processes. The write client must independently prove its native TUI target
argument for distinct thread/root IDs before claiming that action case.

Retain bounded native title, user/child/unknown classification, recorded cwd,
local Git/workspace context, creation time, last conversation activity and
latest turn outcome. Unknown classification stays visible; the normal read
view excludes only positively classified children. Broad catalog source kinds
and session-tree relationships do not independently prove child classification.
Validated native threadSource or a proved typed SubAgentSource variant supplies
classification; older unknown shapes stay unknown.

Age stays based on last conversation activity, with the native turn-completion
or in-progress turn-start clock. Polling, renaming, resuming, metadata enrichment
and lease renewal do not advance it. Retain original event clocks and explicit
stale last-known clocks. Missing clocks remain missing. The default read-client
order stays blocked, waiting, working, then unknown/history, with activity
newest first within each group; presentation remains a client policy.

## Collection and coverage correction

1. Verify the existing owning endpoint and exact configured store; never start
   a daemon or Resume a thread to make observation succeed.
2. Read the stored-thread catalog with explicit supported source kinds and
   bounded pagination. Require `useStateDbOnly=true` under a separately proved
   native contract: the documented default may scan logs and repair metadata.
   Read the loaded inventory as a complementary discovery source, including
   blank/runtime-only contexts. A database-only record without validated saved
   identity/readable native summary is unresolved, not automatically resumable.
3. Preserve current catalog runtime status. Obtain metadata-only detail for
   loaded/runtime candidates and unresolved identity/classification. Status
   from the owning daemon is authoritative regardless of catalog/list origin.
4. Apply one runtime/phase classifier to validated daemon responses. Explicit
   saved-only file/SQLite metadata cannot acquire runtime authority.
5. Keep per-thread read order and source incarnation. A later detail sample may
   reflect a native transition. Conflicts or changes whose ordering cannot be
   established require a bounded repeat/read or explicit uncertainty.
6. Read bounded conversation clocks and outcomes. Protect every positively
   running row before limiting parked history; protect by native status, not
   loaded-list membership or age.
7. Expose the selected namespace, source filters, pagination/row/byte limits,
   unresolved statuses and independently sampled coverage. Complete loaded-list
   coverage must not claim complete daemon-session discovery.

The corrected runtime scope is daemon threads in the declared managed namespace,
including discovered saved and runtime-only records. A bound that prevents a
full census makes coverage partial, while independently verified positive facts
remain current. Catalog truncation by creation order cannot claim a complete
recent-history view. Recover all candidates before activity ordering, or expose
explicit bounded/paginated coverage.

Remove the Codex private SQLite/rollout discovery fallback from the new
daemon-only producer path. Existing cached metadata may remain visible as stale
after failure. An unavailable daemon yields unavailable/unknown current facts;
it does not trigger a second live authority or provider startup. An offline
history browser would be a separately requested capability, not a compatibility
requirement here.

The database-only catalog selector is a provider RPC capability, not direct
Observer access to private databases. Accept its query semantics and coverage
independently, including database placeholders, missing summaries and older
records. Do not restore the default repair mode to recover omitted legacy data.

Capabilities describe validated native predicates and supported contract
semantics. Coverage and health describe a particular sample. An all-parked
inventory must not make working/blocked/waiting support disappear merely because
there were no running examples in that sample.

## Shared service and pull/push

Correct the service at the same producer checkpoint as direct collection.
Its fast state collection must sample daemon disposition for discovered saved
records as well as current running contexts. Its slower metadata work collects
parked-history activity and project enrichment. Prefer bulk catalog status plus
focused native detail over per-row full-history work on every fast cycle.

Scheduling component names do not grant or remove fact authority. Publish the
newest verified daemon runtime/phase sample for each exact thread under its
own lease and incarnation. A metadata-only sample cannot renew runtime state;
a native daemon status returned during metadata work is a runtime fact only if
the service deliberately accepts it under the runtime lease/order rules.
Avoid the current blanket rule that every history-component row loses state.

Direct snapshots, sampled watch, cached pull and cached push use the same
classifier and evidence rules. Failure, expiry, context change, resync and
retention produce uncertainty with original clocks. A complete healthy loaded
inventory does not turn unsampled saved records into parked. Remove stale
runtime-only membership on positively complete recovery, while retained saved
identity/history follows its own coverage and bounds.

Native notifications and passive hooks are wakeups for authoritative reads.
They do not write runtime/phase facts into the cache, impersonate current daemon
state or grant action permission. Consumer notification routing, including tmux
or Kitty delivery, remains separate. Push is an observation stream with bounded
gaps/resync, not native event replay or lossless completion delivery.

## Clean breaking contract

Use API 2 and snapshot/watch wire 4 for this incompatible producer correction.
Update the strict pure parser, bundled schemas, conformance fixtures, descriptor,
CLI, sampled watch and artifact tooling together. Use service protocol 2 for the
new embedded view and lease/component contract. Reject old wire/cache input;
do not translate it or silently relabel accepted API 1 facts.

Remove terminal `attachment`, worker presence and `clientBinding` from the
common read model. Remove mandatory Claude `jobId`, `job`, SDK `history` and
interactive/background `sessionKind` fields from Codex/common rows. Provider
native IDs remain typed metadata; future Claude support supplies its own
adapter without making retained-job semantics universal. Source ownership,
state provenance, coverage, identity, activity, outcome and project facts remain.

Keep observation and the first-party write client separately versioned.
The next pure observation facade does not export write validators/commands.
Write extraction, changed guard semantics and exact-thread TUI entry require
their own schema/native checkpoint before a new writer is accepted. Remove
old inventory/session-kind fields from its guards rather than emitting null
compatibility placeholders. A saved Resume target must not be rejected merely
because it aged out of a discovery display cap; validate the exact requested
reference through the native provider contract.

Do not advertise Claude as accepted by the new candidate. Default to Codex and
reject an explicitly requested unimplemented Claude adapter with a finite
unsupported-provider result. Keep historical evidence as historical evidence.
Claude follows after the Codex read/service gate and does not require copying
Codex's process or daemon topology. Networking, Agent Plus, Tmux Plus and device
firmware are independent consumers, not producer implementation dependencies.

## Implementation and acceptance sequence

D0–D4 are complete for the explicit a3 Codex candidate. The supported D5 writer
subset accepts initialized saved/live Resume, repeated TTY entry and equal-ID
fork targeting, with exact native identity and age checks. A native unequal
thread/tree-root case was not obtained and remains explicitly guarded; blank
runtime-only Resume is unaccepted. D5 normal selection/restart/rollback and D6
Claude are not completed by source or isolated artifact acceptance. The
[API 2 client handoff](api-v2-client-handoff.md) keeps consumer implementation
and rollout separate.

| Checkpoint | Work | Required exit |
| --- | --- | --- |
| D0: reconcile | Capture this design, review source/contract/service/oracle drift and record current ordinary evidence | Reviewed plan, bounded native/synthetic evidence and documentation checks; no native support claims added |
| D1: oracle and wire | Correct independent native reference first; freeze API 2/wire 4/service 2 schemas, phase/reason/identity semantics and valid/invalid fixtures; specify database-only catalog semantics | Old-wire rejection, no action/terminal imports in passive paths, known-phase/runtime constraints and exact-ID distinctions enforced; native catalog passivity/coverage procedure ready |
| D2: Codex producer | Preserve daemon catalog/detail state; implement parked; explicit source selection; protected running inventory; remove private saved-store fallback | Synthetic/controlled cases cover positive states, missing/unknown status, mixed flags, transitions, partial catalogs, bounds, row isolation and incarnation changes |
| D3: service and read CLI | Replace loaded-only state scope; field leases/order; cache merge/retention; direct/watch/cache parity; rebuild list/show/doctor and public tooling | Current parked survives cached pull/push, all-parked startup works, expiry/recovery stays unknown where appropriate, age/order and child filtering remain correct |
| D4: independent Codex acceptance | Freeze/install an isolated candidate; compare public CLI and service to independent native reads on both hosts | Running/parked identity/state/activity parity; isolated held approval/question/waiting cases; database-only catalog and daemon-unavailable passivity; finite watch/recovery and resource checks |
| D5: delivery and write handoff | Review candidate and, when selected, perform Observer-only rollout; accept the separate Codex write client with exact-reference/fork cases | Exact artifact/rollback receipt and independent write route proof; no provider policy change or frontend edits inferred |
| D6: Claude next | Review Claude authority and native workflow, then adapt to the new common interface | Independent Claude discovery/monitoring/native action gates; no inherited daemon or background-job assumptions |

At D4, ordinary attached TUIs supply the active workload. There is no observation
assertion about which pane holds each thread, and no required TUI-close/kill
experiment. Prove parked from current positive daemon responses for retained
saved records. Tests of a daemon-owned active record outside the loaded list are
useful classifier/oracle fixtures, but are labeled synthetic/controlled rather
than accepted post-TUI-closure behavior.

Preserve ordinary sessions, hooks and settings. Use disposable namespaces and
exact cleanup ownership for native cases requiring New/Resume, approval or
failure. Provider versions/hashes are diagnostics, provenance and incarnation
guards; acceptance binds to required contracts, not daily release allowlists.
