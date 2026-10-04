# Contract and clients implementation/execution plan

Date: 2026-10-03. Status: execution sequence prepared for an unattended run;
implementation has not started in this planning pass. This operationalizes
[the design](contract-and-clients-plan.md) and [review](contract-and-clients-review.md).
The current [v1 contract](snapshot-contract.md) and [pilot handoff](execution-handoff.md)
remain the baseline for accepted behavior and installed artifacts.

The user wants Observer development accepted independently before downstream
Agent Plus integration. The primary owns contract/native-source decisions,
review, artifact validation and milestone closure. Workers receive bounded
file ownership after interfaces are established; they do not migrate a consumer
to make an Observer checkpoint pass.

## Delivery priority and development boundary

The primary deliverable is an independently usable Observer candidate: public
observation/read/watch contracts, local project context and first-party
New/Resume client. Optional shared networking follows local acceptance. Agent
Plus integration is a subsequent pass against an accepted pinned artifact.

Codex leads implementation and native validation on Snap and Starship. Claude
remains required on Snap, and the common model must support a Claude-only host.
Do not install Claude on Starship to expand this run. RLCD/349 firmware, Kitty
product work and OpenCode are outside this implementation pass.

The initial milestone provides push to clients through sampled watch updates.
Native events or passive hook wakeups are independently proved improvements;
full native transition capture is not a prerequisite for the read client.
The write client remains narrow and preserves provider-managed execution with
individual native TUI entry.

## Ordered work packages

| Work package | Concrete work | Acceptance / dependency |
| --- | --- | --- |
| E0: baseline and checkpoint | Recheck Git states, installed provider artifacts, config/store selectors and existing candidate ownership; checkpoint the reviewed docs and establish an execution-status record | No unrelated edits absorbed. Exact host/provider/version/topology matrix and isolated-native procedure recorded before new proofs. |
| E1: model/source decisions | Resolve public identity/runtime/phase/outcome/clock semantics and conduct bounded source spikes for activity, parked/offline history, readiness/questions and event access | Each spike concludes with an accepted predicate/source or a finite unsupported reason. Existing v1 meaning is not silently changed. |
| E2: model, schemas and conformance | Implement provider-neutral model/strict bounded validation, adapt accepted native reads, publish snapshot/watch schemas and metadata-only fixtures; draft write schemas for E5 | Both providers fit; exact IDs/scopes and independent health/clocks preserved. Semantic changes use a new wire version. Unresolved write-only details do not gate G1. No frontend imports. |
| E3: Git/workspace context | Add local configured-root/path/Git enrichment with bounded inspection and cache; pure cross-host project-mapping fixtures | Non-Git/missing paths stay discoverable; linked worktrees and cwd retain provenance. Enrichment failure does not fail discovery. Depends on E1/E2 model. |
| E4: read CLI and sampled watch | Fixture/stdin reader, local list/show/doctor, human/JSON modes and an on-demand normalized watch stream | Pure public-fixture consumption, deterministic default ordering, unknowns/partial feeds and bounded polling/gaps. Read milestone G1 passes before write extraction. |
| E5: first-party write CLI | Complete write request/result/capability schemas and fixtures, independent New Here preflight, exact-ref Resume, bounded JSON effects/results and native TTY handoff | Zero-row New, actual executable/config/cwd validation, requested/resulting identity and no uncertain redispatch. Native local operation gates pass. |
| E6: independent Observer artifact | Build from the reviewed checkpoint, install in an isolated candidate prefix, exercise reference consumers outside source checkouts and record artifact/capability matrix | Observer gate G2 passes without Agent Plus implementation/deployment. Source, packaged and native results recorded separately. |
| E7: optional networking and event improvements | Extract thin generic Host Mesh composition around public local commands; separately test native events/hook signals if bounded source proof succeeds | Networking gate G3 is separate. No provider-private mesh adapters or ordinary hook/config deployment. Local acceptance does not depend on this package. |
| E8: Agent Plus consumer pass | Consume pinned Observer read/write contracts and shared networking if accepted; remove duplicate provider-specific behavior and update projection/cache semantics | Starts only after G2 and G3 if networking is selected. Own source/artifact/native checks; desktop UX acceptance remains distinct. |

E2/E3/E4 can have bounded parallel implementation only after the shared model is
frozen; final conformance belongs to the primary. E7 read-only networking can
proceed after G1 if write/event investigation is unavailable, but its acceptance
does not lower G2. The preferred order still closes the local Observer package
before networking/consumer changes. If G2 cannot close, continue independent
Observer work and record the remaining gate instead of starting Plus under a
weaker definition of success.

## E1 source decisions and bounded investigations

| Question | Preferred outcome | Result if proof is unavailable |
| --- | --- | --- |
| Stable logical identity | Storage-scoped native reference separate from OS/runtime incarnation, with explicit source/store selector and fresh action context | Retain an exact scoped reference and document its durability limit. Do not invent aliases, drop provenance or merge equal UUIDs across hosts/stores. |
| Conversation activity | Accepted native conversation-event time; rename, inspection, maintenance and liveness do not advance it; ordering occurs before history caps | Nullable unsupported activity. Creation-based ordering may be explicitly selected/labeled, never represented as conversation age. |
| Runtime context and parked | Accepted per-provider presence/absence predicates with complete relevant scope; retained job/history/attachment facts separate | Saved-only presence remains unknown. Missing source or worker cannot become parked. |
| Codex saved discovery without daemon | Existing-only passive saved metadata source with proved identity, coherent read behavior and bounded coverage | Unavailable saved coverage while daemon absent. No spawn/standalone compatibility backend just to list sessions. |
| Waiting and blocked | Accepted readiness for available context, selected approval reasons, then isolated question/input cases | Existing accepted work/approval subset remains usable; unproved questions/readiness/outcomes remain unknown or unsupported. |
| Native events/hooks | Passive event access or metadata-only local wakeup with exact session/turn correlation and preserved provider lifetime | Poll-and-diff watch. Native event, replay and reliable completion capabilities remain unsupported. |

Use one focused source comparison and isolated proof attempt per unresolved
capability before documenting its bounded outcome and moving to independent
work. Revisit when new evidence or implementation changes the question, rather
than cycling through speculative legacy fallbacks. Optional dimensions can be
unsupported in a usable release; a claimed fact or enabled action still needs
the proof it relies on. Codex priority does not permit fabricating Claude equivalence.

Proposed model, schema and entry-point names are settled at E1/E2. A schema-v2
cutover is expected for the changed identity/state meanings; keep the currently
installed v1 tuple pinned while developing the separate candidate. No dual
discovery stack is required. Define finite unknown/mismatch behavior before
switching consumer artifacts.

## Implementation ownership and dependency shape

The following are responsibility boundaries, not fixed filenames:

| Responsibility | Implementation surface | Ownership constraint |
| --- | --- | --- |
| Public contract/model | Model, validation, schemas, canonical fixtures and semantic/version documentation | Primary sets semantics; one owner edits each shared module/schema. |
| Provider observation | Existing Codex/Claude collectors and metadata adapters | Primary owns source/passivity decisions and native acceptance; workers may implement a bounded accepted mapping. |
| Project context | New local enrichment/configuration helper and focused filesystem/Git fixtures | Worker may own this module/tests once the public shape is fixed. No network or provider actions. |
| Read/watch client | New pure reader/projection/ordering, human CLI and sampled watch runner/tests | Consume public contracts, not private provider payloads. Observe only; no write/mesh dependency. |
| Write client | New first-party CLI, provider entry/preparation internals, result validation and handoff tests | Internal action code stays separate from core imports. No Tmux/frontend implementation dependency. |
| Networking | Optional generic Host Mesh contract/transport wrapper and tests | Import no Plus coupled backend; invoke installed local interfaces. |

Workers are told they share the codebase, preserve other edits and own only
their assigned surfaces. Dependency edits are sequential; independent modules
may run in parallel. The primary reviews integration after each bounded change
and keeps the active execution-status/checkpoint record current.

The read client must parse/filter/order/project public fixtures without provider
homes, filesystem inspection, actions or transport. A separate collecting path
feeds the same public boundary. Git inspection operates on unique bounded local
contexts, not an unbounded subprocess chain per session.

Watch must distinguish semantic changes from new collection IDs/timestamps.
Repeated unchanged polls do not create new conversation activity or phase
transitions. Define minimum interval from measured cost, one refresh at a time,
bounded timeout/cancellation, stream epochs/revisions, heartbeat/sample metadata,
gap/resync and slow-consumer overflow. Missing rows in partial/capped inventory
do not become deletion or parked. Last-known evidence retains original clocks.

## Observer acceptance gates

### G1: observation/read milestone

- Versioned model, snapshot/watch schema and canonical valid/invalid/partial/gap
  fixtures cover both providers and precise unknown/capability semantics.
- State/outcome, runtime, store/native identity, evidence time, sample time and
  activity remain independent. Known child filtering preserves unknown rows.
- Local enrichment and public-fixture read/list/show/doctor/watch pass without
  importing write, remote transport or consumer implementations.
- Core/read installation keeps its passive dependency boundary. New reads are
  supported only after appropriate isolated source proof; existing accepted
  subset is reused with its explicit artifact/topology limits.
- Repository checks and independent review pass. G1 is a useful completed
  deliverable even while write/network work continues; it does not open E8.

### G2: independently usable local Observer package

G1 plus the first-party write client and a fresh packaged acceptance pass:

- New Here accepts provider plus absolute owning-host cwd without an existing
  row. Dispatch validates/chdirs locally, preserves native trust handling and
  binds the actual executable/configuration/artifact.
- Resume validates exact current host/store/native identity and the appropriate
  live attach or saved-history route. Codex thread/session IDs remain distinct;
  Claude job short ID and session UUID remain distinct, including copied results.
- JSON results separate requested/resulting identity, pending identity, confirmed
  versus uncertain provider effects and presentation failure. Native TTY output
  uses a separate contract. Delayed/changed handoffs are revalidated at execution.
- Controlled failure tests cover malformed requests, stale/conflicting targets,
  changed cwd/config/binary, trust-required, timeout/overflow, failed post-action
  observation and no repeat after possible dispatch. Owned launcher cleanup does
  not claim ownership of provider jobs or stop created work after viewer failure.
- Isolated native proofs cover the enabled Codex New/Resume routes on Snap and
  Starship and Claude New/live attach/saved Resume on Snap. Copied/retained job
  cases have explicit evidence or bounded outcome/capability limits. Extraction
  correctness is newly checked even when native provider behavior has prior proof.
- Build a reviewed candidate wheel and install outside source checkouts. Run
  public read/watch/write consumers from an unrelated directory with checkout
  import paths removed. Prove no dependency on Plus, RLCD or SSH/Tmux frontend
  packages and no hidden source-tree execution.
- Record source revision, wheel hash/version, schema/client versions, dependency
  profile, supported native operation matrix, remaining capabilities and cleanup
  metadata. Existing pilot links/providers/histories remain intact during this gate.

G2 is the hard boundary before downstream implementation. Passing only source
tests, or using Agent Plus itself as the sole reference consumer, cannot close it.

### G3: optional networking acceptance

Networking consumes existing Host Mesh authority and calls installed local
interfaces. Test configured host/route association, schema mismatch, provider/host
outage, bounded deadlines/late responses, retained partial feeds, watch gaps and
owning-host cwd validation. Read fallback stops on reached domain failures;
writes pin a route and do not redispatch after an uncertain effect. Missing
remote markers do not establish a safe retry. No machine-attestation or provider
idempotency guarantee is introduced.

Pure project-mapping fixtures show explicitly related different physical roots
joining project context while native keys and checkout contexts stay distinct.
Unmapped same-named repos/clones/worktrees stay ungrouped. Native SSH-loss and
physical suspend acceptance remain separate from controlled transport checks.

If Plus will consume this component, its accepted artifact/API is pinned before
E8. If networking remains deferred, local G2 stands independently and Plus may
retain its existing external Host Mesh composition without a second provider
discovery/action implementation.

## Later Agent Plus pass

Read its own development instructions and current Git state at E8 entry.
Consume the accepted pinned public artifact from G2 (and G3 if selected); do
not reopen Observer design decisions from inside frontend implementation.
An observed producer defect is recorded and fixed in a new Observer checkpoint,
validated there, then consumed by Plus. No simultaneous producer/frontend edit
is used to make their tests agree.

Migrate the new waiting/blocked meaning, full reference/version/cache handling,
project/age fields and New/Resume invocation. Remove duplicate provider-private
action logic while keeping picker presentation, permissions, terminal/window
lifecycle and current-viewer binding guards. Existing native focus/close limits
stay explicit. Cross-provider and cross-host behavior remains part of Plus
acceptance, not a prerequisite for Observer's source/artifact gate.

Run the consumer checks, conformance corpus, packaging and installed/native
routes separately. Any pilot cutover selects a compatible Observer/Plus tuple
together, with artifact/config ownership rechecked and prior tuple retained.
Switching managed links/configuration is a distinct final rollout checkpoint;
it is not automatic because source integration passed. The execution record
distinguishes built, installed candidate, selected pilot and published states.

## Unattended operation and handoff

The unattended run can implement, test, review, make scoped local checkpoint
commits, build/install isolated candidates and run owned disposable native/PTY
proofs. Record progress after each accepted checkpoint so compaction or a source
gap does not restart completed work. Use the existing provider policy; preserve
ordinary hooks, sessions, services and the current coordinator.

Before any native launch, establish isolated config/store/workspace/endpoint and
exact cleanup ownership. If isolation cannot be established for a case, mark it
pending and continue independent work. Store only bounded metadata/reasons in
repo evidence. Do not create test conversations in ordinary stores, resume the
coordinator in parallel or perform its final reopen during unattended execution.

Native event/hook improvements get their own passivity proof and opt-in managed
installation gate; ordinary hook registration is not changed to make watch work.
Full graphical picker/focus/terminal appearance, interactive UX, coordinator
reopen and physical sleep/wake remain later manual/native acceptance. Lack of a
display does not prevent the host-local or packaged gates from completing.

After each milestone, record actual checks, unsupported cases, exact source/
artifact/native provenance, remaining work and the next runnable step in a
dedicated execution-status document. Final handoff distinguishes G1, G2, G3 and
E8 completion, including any built candidate not yet selected. Public release
publication and broad fleet rollout have their own gates. No fixed completion
time or complete native push guarantee is promised.

## Planning validation

Read-only subagent reviews checked contract/source ordering and write/network/
artifact acceptance against the current implementation. Their final draft
reviews found no blocker after clarifying that write-only schema/handoff details
do not gate G1. The primary incorporated
their recommendations: bounded source outcomes, pure fixture readers, semantic
watch diffs, separate read/write gates and independent packaged acceptance before
Plus. E0-E8/G1-G3 dependencies are acyclic; native events/networking do not gate
local observation/read delivery. `./scripts/check` passed 127 existing tests and
checks for 25 Markdown files, links, whitespace and fences. This is a reviewed
planning checkpoint, not implementation or new native acceptance.
