# Complete host-local Codex observation

Date: 2026-10-08. Status: a5 Codex observation accepted and selected on both hosts.
The [ownership specification](observation-boundaries.md) defines the scope.
Core owns passive discovery/monitoring and reconciliation; the local service
hosts the engine, native feed helpers and read delivery. Codex is the only live
adapter. API 2/read wire 4/service protocol 2 stay unchanged.

## Checkpoints

| Checkpoint | Work | Acceptance | Status |
| --- | --- | --- | --- |
| C0: boundary | Review/commit the ownership document and this bounded sequence | Repository/doc checks pass; ordinary deployment remains unchanged | Complete: a18258e |
| C1: adapter authority | One passive adapter dispatch path for collection and feed helpers; reject unsupported legacy diagnostic/helper routes | Unsupported selection fails before native I/O/helper launch; read imports/actions/alerts/terminal boundaries enforced | Complete: 05b6a41 |
| C2: reusable engine | Extract sample reconciliation, retention, expiry and refresh planning; service owns envelopes/runtime; direct watch reuses shared evidence rules | Fake-clock partial/outage/incarnation/order/hint tests and existing wire/transport checks pass | Complete: 19c467b |
| C3: candidate/native | Freeze a successor wheel; separately install on both hosts; independently compare installed direct/cached/pushed discovery and monitoring | Exact identity/state/age/coverage agree; isolated state/recovery proofs pass; ordinary providers are preserved | Accepted: a5; see report |
| C4: operations | Review/render scoped managed read/service selection; restart/crash/reconnect/rollback/reselection; sustained normal-service reads/resource checks | Both hosts select the accepted Codex read/service tuple; recovery works; provider configuration/incarnations and separate writer/frontend selections are preserved | Complete: both-host recovery/rollback and 30-minute managed checks accepted |
| C5: closeout | Review docs/artifact/evidence; commit source, acceptance and operational checkpoints | Clear installed/selected/native status, bounded limitations and a clean intended patch; no push requested | Complete: closeout review/checks; commits retained locally |

## Scope and limits

Keep the observation engine provider-neutral through explicit inputs and passive
adapter descriptors. Do not build a plugin framework, mesh, terminal/window
matcher, attachment manager, new public event feed or user-facing alert client.
The existing separate writer/native action subset is outside this execution.
Selecting read/service commands does not require selecting a new writer.

Preserve ordinary provider workflows, settings, hooks and running sessions.
Use owned disposable namespaces/configuration/endpoints for any provider actions
needed to validate observation. Passive reads never restore an absent daemon.
Commit accepted checkpoints; leave remote publication for a separate request.
Starship has its own checkout history: deliver the frozen wheel and harnesses
without resetting or merging unrelated remote development.

No exact provider release allowlist, private-store compatibility fallback or
terminal evidence may determine runtime/phase. Known native metadata gaps remain
explicit. The catalog remains bounded/non-archived and push remains reconciled
sampling with gaps/resync. Post-TUI-closure lifetime and physical sleep/wake are
deferred; assume always-on hosts for this gate. Report resource usage/stability
without restoring the superseded strict 64 MiB threshold.

## Validation and rollout rules

Run `./scripts/check` before every source/document checkpoint. Label static,
controlled, real IPC and native evidence separately. Compare the installed CLI
with the independent native oracle on each owning host; another Observer view
is not a reference. Validate active and positively parked cases, monitoring
states, age, retention through partial/error reads and recovered current facts.

Keep the source/candidate/native gate before normal managed selection. Read the
managed repository instructions and preserve unrelated drift before changing
Observer-only selectors/unit metadata. Keep exact a16 rollback artifacts and
bookends. If operational checks fail, restore the prior observation selection;
do not repair failures by restarting ordinary Codex or editing consumers.

Evidence retains bounded metadata and reason codes only. No raw callback,
prompt, response, tool payload, credentials or terminal capture is retained.

## Execution record

- Preflight: Snap and Starship normal CLI/service still select a16. Snap's unit
  collects Codex/Claude; Starship collects Codex. Both user services are active.
- Source tree starts with only the preceding ownership documentation changes.
  All 367 tests pass (one skipped), with 87 Markdown documents checked.
- C0 committed the ownership/sequence with 367 tests passing and 88 documents
  checked. C1 consolidates live Codex dispatch, rejects unsupported private
  helpers before I/O and removes the old history-census option; 373 tests pass.
- C2 extracts `ObservationEngine`, `observation_scheduler` and shared evidence
  invalidation/retention into core. The service supplies host clocks and stream
  envelopes; direct watch shares conservative retention. Core tests use injected
  clocks/host identity with no OS/transport/native imports. All 379 tests pass
  (one skipped), including existing expiry, source order, incarnation, gap,
  history/runtime lease and native-hint controlled regressions. The successor
  package is a5; installed/native and normal rollout remain separate gates.
- C3 [acceptance](evidence/2026-10-08-codex-observation-completion/REPORT.md)
  independently verifies the frozen a5 installation on both hosts. Ordinary
  direct/cached views agree in all eight bracketing rounds (89/353 rows,
  2/5 running), and isolated parked, held-input and cached/pushed outage/recovery
  pass. All fixtures/auth/history are cleaned and ordinary bookends match exactly.
- C4 selects the Codex-only a5 read/service tuple while retaining a16 writer and
  frontend links. Both-host restart/crash/reconnect and a16 rollback/a5 reselection
  pass. Each ordinary managed unit completes 30 minutes with three healthy push
  readers, 100 cached CLI reads and an unread subscriber; no reader errors occur.
  The normal selected CLI/native comparison again agrees in eight rounds. Final
  bookends preserve provider configuration/hooks, workspace, writer/frontend links
  and ordinary daemon incarnation. Resource peaks and coalescing gaps are reported;
  no matched incremental CPU or lossless native-event guarantee is inferred.
- C5 reconciles current/historical API and handoff documentation, including the
  removed Codex private-store fallback and separate writer selection. The managed
  source check retains the unrelated preexisting Tmux archive-pin failure; scoped
  Observer operations checks pass. Concurrent Tmux Observer source changes are
  preserved. No provider or frontend migration and no push occur in this goal.
