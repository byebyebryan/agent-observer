# Claude interactive observation reconciliation

Date: 2026-10-08. Status: proposed execution plan, requested after the
[a8 Claude checkpoint](evidence/2026-10-08-claude-observation/REPORT.md).
This document accepts the ownership and interactive-only target, not a new
runtime predicate, artifact, public wire or provider configuration rollout.

## Direction and baseline

Observer is the upstream read authority for consumers. Provider-native evidence
is its source of truth. Core owns discovery and monitoring through passive
adapters; service hosts collection and local pull/push; networking composes host
observations; the CLI reads them. None queries client inventory, tmux-observer,
tmux, TUI attachment, terminal processes or windows to classify sessions.
Clients separately match Observer references to contexts and perform actions.

Codex continues using its owning daemon unchanged. Claude's target is ordinary
interactive sessions, including native New and saved Resume. Background jobs,
supervised continuation and background attachment are outside supported runtime
scope. Agent View is a candidate for disabling, subject to native proof below.
There is no legacy adapter, session manager or client-inventory fallback.

The accepted a8 adapter already reads Claude-owned files without terminal
matching. It authenticates running UUID registrations, maps supported status
to work phase and reads saved metadata independently. It only proves parked
for a bounded terminal-job predicate. Saved-only rows and foreground exit stay
unknown. The remaining change is native interactive lifecycle authority and
scope cleanup, not moving a current terminal classifier into core.

Current audit leads, not mode-off acceptance:

- Installed source appears to write interactive registration files independently
  of the Agent View flag, and to update UUID/status and remove records on exit.
  Registration writes can fail without necessarily aborting the native session.
- `claude agents --json` is gated by Agent View and its isolated a8 probe made
  preferences/job-store writes. It is not an accepted passive source or a saved
  interactive catalog. Direct provider-owned metadata remains the first candidate.
- Public session rows have no attachment fields, but `SessionObservation` and
  Claude's private samples still carry unused attachment scaffolding. Remove it.
- The required read contract and source coverage still include job-store
  predicates. Replace that dependency with the independently proved interactive
  contract; do not copy background lifecycle into the new target.

The [official Agent View documentation](https://code.claude.com/docs/en/agent-view#turn-off-agent-view)
describes the opt-out and distinction between ordinary interactive sessions and
supervised background sessions. Documentation and static call sites do not
establish installed mode-off registration or monitoring behavior.

## Required evidence and predicates

Private process checks authenticate exact provider-owned registrations. They
use native UUID, UID, PID domain, birth token, executable locator and stable
record reads. They are not generic process discovery, terminal matching or
public attachment handles. Ignore native tmux/terminal fields entirely.

| Native evidence | Proposed public result |
| --- | --- |
| Exact interactive UUID registration with authenticated current incarnation | Running; phase from supported native status evidence |
| Positive saved UUID plus a validated exhaustive native interactive census proving no live context for that UUID, with no unresolved noninteractive conflict | Parked; phase null |
| One bound incarnation ended, but another context or census completeness is unresolved | Unknown runtime; ending one worker does not end the logical session |
| Missing/malformed PID, denied process read, foreign PID domain, torn record, conflicting UUID or unsupported native kind | Unknown for affected identity or scope, with a finite reason |
| Runtime read failed, exceeded bounds or expired | No current negative lifecycle assertion; retain bounded last-known evidence only |

The parked predicate is a conjunction of positive saved identity and a proved
native absence contract. A readable directory, an empty list, PID-file removal,
an invalid old PID or `/exit` alone is insufficient. PID reuse proves the old
incarnation ended; it must never authenticate the replacement process.

The native gate must establish when registration is created relative to session
availability, how UUID switches/resumes are committed, whether every supported
interactive context registers, and what failed writes mean. Include a controlled
unwritable-registry case: if a session can remain usable but invisible, that
topology cannot advertise exhaustive runtime coverage or generic parked truth.
Stable bracketing reads bound races; they do not create an atomic inventory.
Startup, UUID changes, duplicate contexts and unresolved reads remain explicit.

If the installed native contract cannot establish completeness without client
inventory, keep parked unsupported for that scope and report the precise gap.
Investigate another passive provider source before accepting a narrower predicate.
Do not implement optimistic absence or a hidden client/process scan to pass the
gate. Optional hooks may corroborate exact lifecycle events and trigger refresh;
they are not the first implementation, an exhaustive inventory, or a way to
classify unseen saved history after restart.

### Unsupported background contexts

Dropping background support must not turn excluded live work into parked rows.
Prove a bounded provider-native conflict guard for noninteractive registrations
and processless continuation evidence. It only prevents false interactive
classification; it does not project background phase, lifecycle or attachment.
Conflicting saved UUIDs remain unknown/unsupported. If a conflicting record has
no usable UUID, declare the resulting census limitation rather than assuming
the rest of the catalog is safely parked.

Existing retained job data is not deleted or stopped during observation. Remove
the full job projection and terminal-job parked predicate once the narrower
guard is proved. If the guard requires the existing full job classifier, return
that design issue at the source gate instead of preserving it as compatibility.
Saved user conversations remain discoverable regardless of their historical
entry route; saved existence never proves an interactive runtime.

### Monitoring, age and freshness

Keep `working`, `blocked`, `waiting` and unknown phase, with separately proved
approval/question reasons. Unsupported dialogs retain running with unknown
phase. A process liveness check or filesystem hint cannot renew old work-state
evidence. Conversation activity remains a native conversation clock; entry,
Resume, registration updates, title changes and collection do not advance age.

Parked assertions use the runtime census lease, independently of saved catalog
metadata. Runtime refresh must update lifecycle for known saved UUIDs even when
the slower history scan has not run. A failed/expired census invalidates its
negative assertions. A service restart reconstructs state from native sources;
it needs neither prior Observer receipts nor an attached client. History failure
does not erase positive live evidence; missing positive saved identity prevents
parked. Recovery must not restore an older parked sample over a newer running
sample or refresh stale activity by implication.

## Contract and implementation changes

Preserve shared identity, runtime, phase, activity and uncertainty semantics.
Do not add PID, worker, terminal or background-job fields to session rows.
Replace the private Claude read profile with an interactive registration/census
contract, separating live presence, phase, saved metadata and negative lifecycle
capabilities. Required contracts select support; provider versions/hashes remain
diagnostics and incarnation guards.

Propose explicit `interactive_sessions` runtime coverage for Claude. Current
wire 4 only permits `daemon_threads` and `provider_sessions`, so this is a strict
schema change. At the contract gate, review API 3 / snapshot-watch wire 5 /
service protocol 3 together, including scope validation and lease semantics.
Do not silently extend wire 4 or ship a converter. Codex predicates remain
unchanged; both-host Codex reads must pass the new envelope conformance gate.
The independently selected writer and its wire are outside this change.

| Area | Responsibility |
| --- | --- |
| `claude_metadata.py`, `native_contracts.py` | Bounded authenticated interactive census, native work-state predicates, minimal unsupported-context guard; remove background projection and stale version-gated declarations |
| `claude_snapshot.py`, `claude_projection.py`, `claude_saved_identity.py`, `claude_history.py` | Exact saved/live identity join, lifecycle evidence for saved UUIDs, independent metadata failure/age handling and explicit scope |
| `observation_model.py` | Remove unused attachment dimension and private serialization; preserve work/presence independence |
| `observation_engine.py`, `observation_evidence.py`, adapter profiles | Reconcile leased native census evidence with saved identities, including runtime-only refresh and cold start; no Claude classifier in service/read clients |
| Public schemas, validators, descriptors and read/service clients | Explicit scope and version rejection; one classification across direct pull, cached pull and pushed views |
| `claude_hints.py`, service helpers | Native filesystem signals remain refresh hints; periodic reconciliation and expiry remain authoritative |
| Independent evaluation/native scripts | Implement expected predicates independently before producer changes; explicit private Agent View on/off fixtures |

Keep evidence production in the adapter and provider-neutral reconciliation in
the engine. If whole-census evidence must cross the adapter/engine boundary,
define a bounded private sample contract instead of passing raw provider data
or introducing a service-side Claude classifier.

## Execution gates

| Gate | Work | Acceptance |
| --- | --- | --- |
| I0: independent native source proof | Reinspect Snap; isolated Agent View on/off; registration/status/UUID/exit/completeness and background-conflict probes | Required interactive predicates and failure scope recorded independently; no ordinary provider settings or sessions changed |
| I1: oracle and read contract | Update `scripts/evaluate-observation` independently; review explicit coverage, private census sample and versioned public descriptors | Oracle imports no Observer collector; strict conformance fixtures distinguish healthy empty census from unavailable/incomplete source |
| I2: producer implementation | Simplify adapter/model, implement lifecycle/lease reconciliation, update CLI/service delivery | Meaningful source tests and `./scripts/check` pass; no attachment or client-inventory dependency; Codex semantics preserved |
| I3: immutable artifact/native proof | Install an explicit candidate; ordinary Snap Claude and both-host Codex comparisons; isolated transitions and failures via direct/cache/push | Exact identities, runtime, phase and age agree within bracketed sampling limits; cold-start parked proof succeeds within declared scope |
| I4: Observer operational selection | Scoped read/service selection after artifact acceptance; restart/failure/reconnect/rollback/reselection | Installed bytes and normal endpoints independently verified; writer remains separately selected |
| I5: provider policy and handoff | Decide Agent View opt-out from I0/I3 evidence; prepare managed Snap settings separately, then validate fresh launches | Provider configuration gate has explicit launch-mode evidence; no forced restart of ordinary sessions; clients receive the accepted read contract |

If I0 cannot prove exhaustive negative lifecycle, continue accepting independent
running/phase/catalog improvements, but do not describe I3 as complete interactive
discovery. Record the parked blocker and required provider capability. A long
execution loop may investigate it autonomously within isolated fixtures; the
plan does not authorize weakening its predicate.

Mode-off selection is based on registration, waiting/working, held approval and
question, saved Resume, exact UUID and child classification proof. Native roster
CLI availability is not a requirement. A settings edit only changes fresh
launches; pre-existing workers may retain their earlier mode. Validate mixed
incarnations by contract, not by assuming a global mode from settings. Agent View
on can remain if off removes required evidence. Neither option introduces
background-session support or terminal observation.

## Validation matrix and completion

- Native isolated lifecycle: startup, New, exact saved Resume, waiting, working,
  approval, question, normal `/exit`, abnormal process exit, same-process UUID
  switch, duplicate UUID contexts and observer/service restart while parked.
- Faults: native registration write failure, missing/unreadable/torn/oversized
  census records, denied process reads, PID reuse/birth mismatch, foreign domain,
  unknown kind/status, history failure, source expiry and recovery. Synthetic
  cases cover hazardous process/identity variants without altering ordinary work.
- Unsupported background conflict: registered background worker and processless
  continuation cannot become interactive running or parked. Retained historical
  metadata does not grant a supported background capability.
- Metadata: exact titles/UUIDs, native child filtering, positive saved identity,
  activity unchanged by Resume/rename/heartbeat, separate saved coverage limits.
- Delivery: compare installed direct reads, cached pull and pushed full/resync
  views with independent native evidence; validate lease expiry, collection
  races, delayed history, runtime-only refresh and cold-start reconstruction.
- Regression: ordinary Claude sessions on Snap and Codex on Snap/Starship, plus
  dependency checks proving observation can run with all client inventories and
  attachment services absent. Provider-native process authentication still works.

Record versions and topology as provenance, bounded UUID/state/time comparisons,
finite reasons and coverage limits. Preserve ordinary settings/hooks/processes;
isolate before launching native tests and clean up only owned fixtures. Retain
no prompts, responses, credentials, tool payloads, raw native records or terminal
captures in repository evidence. Another Observer result is not a native oracle.

Completion means clients can obtain the supported interactive catalog, current
running/parked disposition and supported work phase from Observer alone, with
honest scope/freshness, including after Observer restart. Background work,
attachment/actions, networking, notifications and frontend migration retain
their separate gates. Historical a8 evidence remains valid within its original
scope and is not rewritten as acceptance of this plan.
