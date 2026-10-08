# Codex daemon authority deep review

Date: 2026-10-08. Original source/design review with independent ordinary native
samples and targeted synthetic checks. The findings below describe the a16
baseline. The corrected a3 producer is now
[independently accepted](evidence/2026-10-08-codex-authority-acceptance/REPORT.md)
on Snap and Starship, with normal selection still a16.
The [reconciled plan](codex-daemon-authority-plan.md) defines the new target and
the [evidence report](evidence/2026-10-08-codex-authority-review/REPORT.md)
records the installed behavior at the original review.

R1–R9 and R11–R13 have source, strict/synthetic, packaged and scoped native
corrections as applicable. R10 now uses exact threadId and independently verifies
equal-ID fork targeting; distinct thread/tree-root TUI entry remains explicitly
unsupported until a native case is accepted. No old-wire/private-store fallback
or terminal-state authority was retained. The
[API 2 handoff](api-v2-client-handoff.md) records the accepted interface and next
delivery/Claude gates; this historical review does not expand their acceptance.

## Conclusion and review boundary

The existing Codex transport/collector does not use tmux or TUI attachment to
classify sessions. Endpoint ownership and incarnation checks already authenticate
the daemon. The drift is narrower runtime coverage, discarded saved-row status,
cache reconciliation assumptions and a public model shaped partly by terminal
and Claude-job concepts. The earlier API accepted those limitations as its
bounded contract; it did not implement full daemon-authoritative parked discovery.

This review traced the native read -> metadata -> collector -> projection ->
validator -> direct CLI/watch -> service collection/lease/merge -> cached
pull/push path. It also checked identity use in the write client, notification
separation, existing tests, evaluation oracle and current/historical documentation.
It is a primary-led source review; native comparisons use an independent stdlib
wire client, not another Observer collector. No delegated review is claimed.

## Drift and correction

| ID | Finding and evidence | Impact | Correction/checkpoint |
| --- | --- | --- | --- |
| R1 | `codex_snapshot.py` calls live projection only for loaded IDs; catalog and saved classification detail use `saved_thread_metadata`, which discards native status | Current saved records remain unknown even when the daemon positively reports `notLoaded`; native state outside the loaded set is ignored | One daemon-response classifier across catalog/detail; D2 |
| R2 | `collection.py` only supports parked for Claude, maps Codex presence only to running and hardcodes `loaded_threads` scope | Codex parked is impossible through the public adapter; complete loaded scope is narrower than target discovery | Explicit Codex parked predicate and corrected daemon scope/capabilities; D1-D2 |
| R3 | `_service_worker.py` excludes history during fast state work; `service_state.py` strips state from history-only rows and publishes runtime capability/coverage from the loaded-only receipt | A collector-only parked fix would still fail cached pull/push, or leave parked status on the slower wrong lease | Make daemon disposition part of state reconciliation and merge by fact/context/order; D3 |
| R4 | `contract.py` mandates worker/attachment, client binding and Claude job/history/session-kind fields for every provider | Core API exposes unsupported terminal concerns and provider-specific job scaffolding; cleanup is obstructed by old guards | Remove those fields from the common read model, with API 2/wire 4/service 2; D1/D3 |
| R5 | `codex_transport.py` omits `sourceKinds`; the native default is cli/vscode. Display protection is `selected_saved_ids | loaded_ids` | Other source origins are outside catalog discovery; daemon-running records outside loaded membership could be capped away | Explicit source scope and status-based running retention; D2 |
| R6 | `scripts/evaluate-observation` uses the same default source filter and accepts runtime/status/phase only for loaded IDs | The independent transport reference shares the implementation's semantic blind spot; it cannot accept the new parked/catalog-state contract | Correct the native oracle before producer repairs; D1 |
| R7 | Catalog scans are capped at 1,000 before activity clocks/order, while native default order is creation. Saved kind detail is performed after display capping | Old threads with recent work beyond the candidate bound cannot be recovered by frontend sorting; uncertainty is partly reported but the target recent-history guarantee is incomplete | Fully recover bounded candidates or expose explicit pagination/partial scope; prioritize running before parked limits; D2-D3 |
| R8 | Both known wait flags produce native `needs_input`/`multiple`, but public projection returns unknown phase with `questions_unproved` | A valid combined human-input state loses urgency and is mislabeled as unproved question support | Blocked with a bounded reason set; unknown flags stay conservative; D1-D2 |
| R9 | Strict validation checks parked/phase conflict but allows known working/blocked/waiting with unknown runtime | The public parser does not enforce the design's runtime/monitoring relationship | Known phase requires current running context; parked phase becomes explicitly not applicable; D1 |
| R10 | The writer invokes `codex resume --all nativeIds.sessionId`; OpenAI defines that field as the session-tree root and resumes an individual thread through `thread.id` | Potential wrong conversation targeting for forks with distinct IDs; current equal-ID ordinary cases do not establish it | Rename root metadata, retain exact thread identity and independently prove the TUI argument before accepting that write case; D1/D5 |
| R11 | Writer target validation collects a capped listing and hashes inventory/session-kind metadata into its guard | An exact saved target can age out or gain an irrelevant guard change; guards retain removed Claude/common fields | Separate native exact-reference validation and operation-relevant guards; D5 |
| R12 | Codex private SQLite/rollout fallback, public read facade exporting write validators, old provider acceptance gates and multiple historical status narratives complicate the new authority boundary | They are not current tmux-based state bugs, but add implementation/contracts to preserve when no compatibility is required | Remove fallback from the daemon-only path, separate read/write facade and clearly supersede old design gates; D0-D3 |
| R13 | The catalog request omits `useStateDbOnly`; current official documentation says the default scans logs to repair metadata | A read-shaped method is insufficient proof of strict observational passivity; repair side effects were not audited in this ordinary comparison | Require the database-only native query contract and independently prove its no-repair behavior, saved-record coverage and placeholder handling; D1/D4 |

Source pointers:

- [Codex metadata](../agent_observer/codex_metadata.py),
  [collector](../agent_observer/codex_snapshot.py),
  [transport](../agent_observer/codex_transport.py) and
  [private saved fallback](../agent_observer/codex_saved.py).
- [Projection](../agent_observer/collection.py),
  [public contract](../agent_observer/contract.py),
  [pure facade](../agent_observer/public.py),
  [reader](../agent_observer/read_client.py) and
  [sampled watch](../agent_observer/watch.py).
- [Service worker](../agent_observer/_service_worker.py),
  [state/merge](../agent_observer/service_state.py),
  [scheduler](../agent_observer/service_scheduler.py) and
  [runtime](../agent_observer/service_runtime.py).
- [Native evaluation](../scripts/evaluate-observation),
  [write client](../agent_observer/write_client.py) and
  [notification source](../agent_observer/notification_source.py).

R1/R2 are demonstrated by current ordinary saved-state reads. R3/R8/R9 have
targeted synthetic reproductions, not new native support proof. R5/R7 are
coverage/bound consequences of inspected code; the current complete broader
catalogs found no additional live records outside loaded lists. R10 is a
documented identity risk with no current unequal-ID native action case. R11 is
a code-path/bound risk, not a reproduced current ordinary Resume failure.
R4/R12 are intentional design cleanup, not claims that passive reads currently
launch providers or use tmux as state authority.
R13 is a documented side-effect risk, not an observed ordinary metadata write.
Both current hosts accept the database-only query shape, but that does not prove
the flag's semantics or historical coverage; isolated native proof remains open.

## Native contract research

The official [passive thread-read documentation](https://learn.chatgpt.com/docs/app-server#read-a-stored-thread-without-resuming)
states that summary reads return native runtime status without loading,
resuming or subscribing to the thread. The
[catalog documentation](https://learn.chatgpt.com/docs/app-server#list-threads-with-pagination--filters)
defines default interactive-only filtering and paginated saved records.
These support a daemon-owned status path without terminal correlation, subject
to native topology/passivity acceptance.

The same catalog documentation describes `useStateDbOnly=true` as avoiding
JSONL scanning/metadata repair. Both installed owning daemons returned a complete
database-only catalog with native status and tree-root IDs in the bounded probe.
This is query-shape evidence. It did not audit filesystem changes, prove that
every database record has resumable saved history or compare the two modes in
one stable isolated store. Those checks are required before the new contract
is accepted, rather than retaining default repair behavior for compatibility.

The [identity/resume documentation](https://learn.chatgpt.com/docs/app-server#start-or-resume-a-thread)
defines the tree-root role of `thread.sessionId` and the thread-id Resume target.
The installed TUI's passive `resume --help` calls its argument a session UUID/name;
that terminology does not prove the root-ID mapping for forked conversations.
Do not silently fix the write route based on documentation alone: an isolated
exact-thread TUI case is still its required independent action gate.

Native compatibility continues to bind to the required endpoint/metadata/CLI
contracts. Current version/hash diagnostics do not create a provider allowlist.
Historical 0.160.0 viewer-exit evidence remains historical and outside the user's
selected next acceptance scope.

## What already fits the ownership design

- Existing-only managed endpoint selection, peer UID/PID, store initialization,
  executable identity and incarnation rechecks. These authenticate observations;
  they do not infer session runtime from a TUI PID.
- Passive Codex metadata reads with no New/Resume, approval or daemon autostart.
  Provider workflows, ordinary hooks and terminal attachments remain intact.
- Separate scoped logical/native identity and daemon/runtime provenance. Public
  store identity already excludes daemon PID/birth from the logical reference.
- Running idle -> waiting and active -> working/single typed input waits.
  Current native runtime error -> running/unknown is appropriately conservative.
- Conversation-event age, latest outcome separation, bounded native titles,
  local Git/workspace enrichment and proved-child filtering.
- Hints as read wakeups, periodic reconciliation, owned Observer helper cleanup,
  bounded service leases/fan-out and explicit gaps/resync. Notifications are a
  separate event/client boundary, not a runtime-state writer.
- Provider-neutral host-local core and external host-mesh/terminal/device clients.

Preserve these properties through the rewrite. Removing unused field scaffolding
must not remove daemon ownership/security checks, per-fact health, bounds or
activity provenance.

## Acceptance changes required by the review

The current evaluator's loaded-only runtime oracle must change before a new
candidate can pass. For each exact native thread, compare status-driven runtime,
phase/reasons, identity/title, child classification and conversation clocks.
Bracket mutable reads and classify changes as sampling races rather than errors.
Do not use process-count agreement or an Observer service result as native proof.

The current ordinary sample accepts only the selected a16 running subset. Six
positive `notLoaded` detail reads demonstrate available evidence and the current
parked gap; they do not accept an unimplemented API 2 projection or a general
headless lifecycle. The next artifact must independently show parked through
direct CLI, sampled watch, cached pull and cached push, including expiry/recovery.

Required focused source cases include all-parked startup, zero-history blank
running threads, known/unknown/composite waits, native runtime error, explicit
notLoaded versus missing membership, catalog truncation, old running rows, row
identity conflicts, namespace/daemon change, fresh runtime with stale activity,
stale runtime with retained metadata and old-component/new-component races.

Required native cases include the ordinary Snap/Starship inventory, retained
saved records, active/idle/held approval/question under the managed runtime,
database-only catalog passivity/coverage, passive missing-daemon behavior and
bounded service recovery. Writer New/Resume
and distinct root/thread targets have their own action gate. Post-TUI-closure,
standalone parity, physical sleep/wake, Claude, notification installation and
frontend/device integration remain explicit follow-ups.

## Reconciliation outcome

The plan closes the authority/ownership design questions without requiring
terminal binding, preserved API 1 compatibility or Claude readiness first.
Source/API acceptance remains open at D1-D4. Installed normal commands remain
a16; this documentation pass changes neither their semantics nor selection.
