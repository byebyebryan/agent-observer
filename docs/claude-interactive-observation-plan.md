# Claude interactive observation reconciliation

Date: 2026-10-08. Status: accepted design direction and registration assumption;
shared public contract fit is now [settled](claude-read-contract-review.md).
Implementation, artifact acceptance and rollout remain pending. This reconciles
the [a8 checkpoint](evidence/2026-10-08-claude-observation/REPORT.md) and subsequent
[native-source validation](evidence/2026-10-08-claude-interactive-source/REPORT.md)
with the user's accepted practical scope. It replaces the earlier requirement
for an exhaustive interactive census. It does not select a new artifact, wire,
provider configuration or consumer.

## Direction and current baseline

Observer is upstream of its clients. Core owns discovery and monitoring through
passive provider adapters and a reusable reconciliation engine. The service
hosts collection and local pull/push; networking composes host observations;
the read CLI consumes them. None queries client inventory, tmux-observer, tmux,
TUI attachment or windows to classify sessions. Context matching and actions
remain a separate client layer.

Codex continues querying its owning daemon unchanged. Claude's supported target
is ordinary interactive New and saved Resume, with or without Agent View.
Background jobs, supervised continuation and background attachment are outside
support. No legacy adapter, Observer session manager or terminal fallback is
required. Native process checks are permitted to authenticate provider-owned
UUID registrations; they are not generic process discovery or attachment.

The selected a8 adapter already authenticates native running registrations and
supported status, with saved metadata collected independently. Its parked
predicate applies only to bounded terminal retained jobs. Saved-only rows and
foreground `/exit` still report unknown. This plan changes that lifecycle policy
and removes background/attachment scaffolding; the new rule is not implemented.

Native evidence now establishes:

- Interactive registration, supported phase and exact saved Resume work with
  Agent View on and off in the tested flows, including observation without hooks.
- Normal `/exit` ends the incarnation, removes its registration and retains saved
  identity. A forced exit retains a stale record with its last status; native
  incarnation checks distinguish that dead worker from a current one.
- Resume after forced exit can leave stale and live registrations for the same
  UUID. Every matching record must be considered before asserting parked.
- A registration write failure can leave a usable session invisible even after
  the registry becomes readable again. The native JSON roster also misses it.
  An exhaustive interactive inventory is therefore not established.
- `claude agents --json` has initialization writes and is not an accepted passive
  source. Its availability is not required by this design.

The [native report](evidence/2026-10-08-claude-interactive-source/REPORT.md)
retains exact artifact/topology bounds. Source facts are established; the later
Observer implementation and normal Agent View opt-out still need their gates.

## Accepted assumption and lifecycle rule

Assume supported ordinary interactive sessions create and retain their native
UUID registration while running. Under that explicit assumption, a healthy
bounded provider-owned registry scan, native incarnation checks and positive
saved identity are enough to classify running or parked without client evidence.
This is a registered-interactive guarantee, not proof of every possible context.

| Native evidence | Target public result |
| --- | --- |
| Exact interactive UUID registration with authenticated current incarnation | Running; supported native status supplies phase |
| Positive saved UUID; healthy bounded registry scan; no matching live incarnation; no relevant unresolved or unsupported-context conflict | Parked; phase null, under the registration assumption |
| Old registration is definitively dead or its birth token no longer matches, with another authenticated live registration for the same UUID | Running; the old record cannot override the live incarnation |
| Multiple live registrations for one UUID | Running; preserve phase ambiguity if their work evidence conflicts |
| No positive live evidence, but a relevant record is malformed, torn, unreadable, foreign-domain or cannot be authenticated | Unknown runtime with a finite reason |
| Runtime scan failed, exceeded bounds, raced without resolution or expired | No current negative lifecycle assertion; retain bounded last-known evidence only |
| Saved identity is not positively established | No parked assertion; live runtime may still be reported independently |

Authenticate records using native UUID, source ownership, UID, PID domain, birth
token and configured executable locator. Ignore native terminal/tmux fields.
A numeric PID is insufficient. A confirmed birth mismatch proves the old
incarnation ended; it does not authenticate an unrelated replacement process.
Permission failures and unavailable process reads are not proof of death.

Normal exit, crash and forced kill are all supported target transitions.
Neither an exit event nor death of one worker proves that all contexts for its
UUID ended: check the current native registrations before parked. File existence
alone also fails because crash records can remain. A healthy empty registry can
classify positively saved UUIDs under the accepted assumption, including after
Observer restart. No remembered Observer run ledger or mandatory hook receipt
is needed.

### Accepted limitation: live registration missing

A live interactive session whose registration failed or disappeared may be
omitted from running discovery and reported as parked if its saved UUID exists.
This can persist after registry recovery and after Observer restart. The native
failure probe demonstrates this risk; stable repeated scans cannot eliminate it.
It is accepted for this scope, rather than a blocker requiring another session
manager or an exhaustive native source.

Detected source faults still prevent negative assertions. A recovered directory
does not retrospectively prove that every surviving session registered. Report
the registration assumption and partial coverage consistently; never advertise
an exhaustive census. Keep the induced failure as a documented limitation test,
distinct from tests requiring unknown for faults the adapter actually detects.
Hooks may later improve corroboration and refresh latency, with their own gate;
they are not required for this implementation or cold-start discovery.

### Unsupported background contexts

Removing background support must not silently classify known excluded work as
parked. Use a bounded minimal provider-native conflict guard for noninteractive
registrations and processless continuation evidence. Without a positive live
interactive incarnation, an affected saved UUID stays unknown/unsupported
rather than parked. A positive interactive incarnation still proves running;
keep phase uncertain when mixed work evidence cannot be attributed safely.
If malformed or unbound conflict evidence prevents a safe negative assertion,
invalidate the affected negative scope explicitly.

The guard does not project background phase, reconstruct job lifecycle or
provide attachment. Remove the full job projection and terminal-job parked
predicate from the new adapter. Retained ordinary job data is neither deleted
nor stopped during migration. Historical terminal job metadata alone is not a
live conflict; guard current or unresolved potentially live work only.
Saved user conversations remain discoverable;
saved existence does not imply that their historical runtime route is supported.
Prove the minimal guard before accepting the candidate; do not hide a full
background compatibility implementation inside it.

## Monitoring, age and freshness

Keep working, blocked, waiting and unknown phase, with typed approval/question
reasons where proved. Unsupported dialogs preserve running with unknown phase.
Incarnation liveness and filesystem hints cannot renew old work-state evidence.
Conversation age follows native conversation activity; Resume, registration,
rename, collection and delivery do not advance it.

Negative lifecycle evidence has the short runtime lease, separate from saved
catalog/title/activity leases. Runtime-only refresh must update lifecycle for
known saved UUIDs without rerunning the whole history SDK scan. A cold start
obtains positive saved identities and native runtime evidence afresh; no prior
Observer state or client is required. History failure does not erase positive
live evidence, and an expired negative sample cannot remain current parked.
Never restore an older parked sample over a newer running one or renew a stale
conversation clock through runtime recovery.

The adapter owns the Claude predicate and a bounded private registration-scan
sample. The engine owns provider-neutral ordering, reconciliation and leases.
The service hosts these operations; neither service nor read client contains a
second Claude classifier. Direct pull, cached pull and push use the same rule.
Define how bounded known saved identities reach an adapter runtime refresh and
how scoped negative evidence crosses back before implementing that interface;
do not move the native predicate into engine code or pass raw native payloads.

## Contract changes and implementation ownership

Preserve shared identity, running/parked/unknown, work phase, activity clocks and
uncertainty. Add no public PID, worker, terminal, attachment or job fields.
Replace the private Claude read profile with required interactive registration,
incarnation, status, saved-identity and scoped negative-lifecycle contracts.
Versions/hashes remain provenance and incarnation guards, not support allowlists.

The [read-contract alignment](claude-read-contract-review.md) accepts API 2,
snapshot/watch wire 4 and service protocol 2: Claude keeps
`scope=provider_sessions`, reports runtime
coverage as partial, and declares finite reasons/limitations for the interactive
scope, registration assumption and unsupported background runtime. Partial
coverage does not invalidate independently established row facts. Scan health
and readiness for the scoped parked predicate are separate from all-context
coverage; do not require `coverage=complete` to classify an otherwise qualified
saved UUID.

The public part of I1 is settled: shared semantics and diagnostic codes fit the
unchanged strict validators/descriptors, including the installed a8 reader.
No automatic API 3 / wire 5 / protocol 3 bump is needed for private cleanup.
Read-client source work can begin independently against the settled interface.
I1's native oracle and bounded private sample interface remain unfinished.
If implementation demonstrates a required new public field/enum or incompatible
shared meaning, reopen a concrete versioned contract gate rather than silently
extending wire 4 or adding a converter. The installed a8 behavior remains the
baseline until a successor's separate artifact/native acceptance.

| Area | Responsibility |
| --- | --- |
| `claude_metadata.py`, `native_contracts.py` | Healthy bounded native scans; exact incarnation authentication; status predicates and minimal unsupported-context guard; remove background projection and version-based support declarations |
| `claude_snapshot.py`, `claude_projection.py`, `claude_saved_identity.py`, `claude_history.py` | Exact saved/live join; parked under the declared assumption; independent history/age failures; honest coverage and finite reasons |
| `observation_model.py` | Remove unused private attachment fields and serialization; preserve presence/work independence |
| `observation_engine.py`, `observation_evidence.py`, adapter profiles | Bounded private scan evidence, runtime-only negative refresh, ordering, expiry and cold start; no Claude predicate in service/read clients |
| Public descriptors, validators, CLI/service clients | Settled API 2/wire 4/service 2 scope/limitations; consistent direct/cache/push conformance without new public fields |
| `claude_hints.py`, service helpers | Native signals remain refresh hints, with periodic reconciliation and expiry |
| Independent evaluation/native scripts | Independent oracle first; scoped lifecycle expectations and explicit accepted limitation cases |

## Execution gates

| Gate | Work | Acceptance |
| --- | --- | --- |
| I0: native source and scope | Existing on/off, hookless, normal exit, crash, Resume and registration-failure receipts; retain remaining duplicate/switch/background cases for candidate proof | Positive source facts established; exhaustive guarantee disproved; narrower registration assumption accepted by the user; no artifact/policy selection |
| I1: independent oracle and contract | Public read alignment accepted; finish independent `scripts/evaluate-observation` changes and bounded private saved-identity/scan sample interface before producer changes | Oracle imports no Observer collector; fixtures distinguish healthy scoped absence, dead/live duplicate records, detected faults and accepted invisible-runtime limitation |
| I2: producer implementation | Simplify adapter/model; implement scoped lifecycle and leased reconciliation; update read CLI/service delivery | Meaningful source checks and `./scripts/check` pass; no client/attachment dependency; Codex unchanged |
| I3: immutable artifact/native proof | Explicit candidate; ordinary Snap Claude and both-host Codex comparisons; isolated transitions/faults through direct/cache/push | Exact identity/state/age agree within bracketing limits; normal/crash parked and cold start pass within declared scope; accepted limitations remain visible |
| I4: Observer operational selection | Scoped read/service selection after I3; restart/failure/reconnect/rollback/reselection | Installed bytes and normal endpoints verified independently; writer remains separately selected |
| I5: provider policy and handoff | Prefer Agent View off for the interactive-only workflow if I3 preserves required evidence; prepare managed Snap settings separately and validate fresh launches | Separate configuration gate; no forced restart of ordinary sessions; clients receive the accepted artifact/contract and registration limitation |

Remaining I1 oracle/private work is the next checkpoint. Reuse native I0 facts
rather than repeating the entire spike for every daily provider update. Additional cases
establish the candidate's bounded behavior; they are not an attempt to prove
away the already demonstrated missing-registration limitation. If a required
normal-workflow predicate fails, report that specific capability gap and revise
it before selection.

Native isolation does not establish source/native success for every planned
case. Same-process UUID switches, simultaneous duplicate live contexts and the
minimal background-conflict guard remain unproved. Use isolated native cases
where safe; hazardous PID/domain/read variants may use synthetic fixtures with
that coverage stated. Unresolved predicates remain explicit at I3 rather than
being inferred from a passing schema or another Observer view.

Agent View opt-out changes fresh launches; older workers can retain their prior
mode. Validate mixed incarnations by required native contracts. On may remain
if off removes required evidence in a new context. Neither mode grants background
support, passive roster-CLI use or terminal observation.

## Validation and completion

- Lifecycle: startup/New, exact saved Resume, waiting/working, held approval and
  question, normal `/exit`, crash/forced kill, stale-plus-live duplicate UUIDs,
  conflicting live phases, same-process UUID switch and Observer restart parked.
  Validate the candidate in isolated Agent View on/off launches before selecting
  a mode-off policy; earlier native-only receipts do not accept the new artifact.
- Detected faults: unreadable/torn/oversized registry, denied process reads,
  PID reuse/birth mismatch, foreign domain, unknown kind/status, source bounds,
  sampling races, lease expiry and recovery. No detected uncertainty becomes
  parked; healthy positive sibling facts remain usable.
- Accepted limitation: failed/lost native registration with a live saved UUID,
  including readable-source recovery and cold start. Record the possible false
  parked result explicitly, without claiming the adapter can detect hidden loss.
- Unsupported-context guard: registered background work and processless pending
  continuation cannot become supported interactive running or parked. Prove the
  guard's bounds without retaining full job lifecycle compatibility.
- Metadata: exact UUID/title, child filtering, positive saved identity, existing
  SDK omissions, and conversation activity unchanged by Resume/rename/heartbeat.
- Delivery: installed direct/cache/push compared with independent native evidence;
  runtime-only refresh with delayed history, independent expiry, cold-start
  reconstruction and retained-fact ordering. Push remains sampled delivery.
- Regression: ordinary Claude on Snap and Codex on Snap/Starship; observation
  succeeds with client inventories and attachment services absent. Preserve
  ordinary settings/hooks/processes; isolate and clean up only owned fixtures.

Record bounded UUID/state/time comparisons, finite reasons, provenance and limits.
Keep prompts, responses, credentials, tool payloads, raw provider records and
terminal captures out of repository evidence. Another Observer result is not
an independent native oracle.

Completion means Observer alone supplies the supported interactive catalog,
running/parked disposition and work phase with honest scope/freshness, including
after its own restart, under the accepted registration assumption. Missing live
registration, saved SDK coverage gaps and unsupported status variants remain
declared limits. Background support, attachment/actions, networking, public
notification events and frontend migration retain independent gates. Historical
a8 receipts are not retroactively promoted to acceptance of this successor.
