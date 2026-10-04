# Contract and first-party clients review

Date: 2026-10-03. Scope: documentation, current source and contract/consumer fit.
The [plan](contract-and-clients-plan.md) captures the user's design discussion.
Independent subagents reviewed observation semantics, actions/networking and
consumer/project requirements. The primary owns decisions, documentation edits
and final validation. No provider session, runtime setting, installation or
frontend was changed by this review.

## Review status

The proposed boundaries are supported by current source inspection: passive
host-local observation, a first-party read client, a narrow write client and
optional networking can coexist in one repository. Detailed APIs and new native
facts/actions still require the plan's C1-C5 gates. C0 is complete: three
independent reviews and the primary's final review found no remaining
documentation/architecture blocker after the findings below were incorporated.
This accepts a design plan, not a stable API or new runtime capability.

The latest existing source baseline is Observer `0.1.0a5` at `ab5c314` and
Agent Plus `0.13.0a3` at `536851b`. These are local source revisions, not a new
published release or new live acceptance. The [handoff](execution-handoff.md)
records the installed pilot; earlier consumer-review tuples are dated evidence.

## Findings addressed in the plan

| Finding | Source evidence | Resolution / remaining implementation gate |
| --- | --- | --- |
| Parked cannot come from saved inventory alone | [Claude saved collection](../agent_observer/claude_snapshot.py) preserves unknown presence; [Codex collector](../agent_observer/codex_snapshot.py) keeps saved rows separate from loaded runtime inventory | Require current complete absence evidence for an accepted provider/store/topology scope. Never derive parked from a transcript, missing worker, partial roster or failed refresh. |
| Codex daemon-off saved discovery is not implemented | Codex saved RPCs run only after existing endpoint verification; [snapshot tests](../tests/test_codex_snapshot.py) return unavailable saved coverage when endpoint inspection fails | Investigate an existing-only passive saved source as a new proof gate; document unavailable coverage until then. Observation cannot start a daemon. |
| The proposed waiting meaning conflicts with current Plus labels | Agent Plus `rofi_agent_plus/observer_contract.py` maps `needs_input` to waiting and `settled` to idle | Explicit semantic/schema cutover, cache/projection migration and bounded mismatched-contract rejection; no silent v1 relabeling. |
| General question blocking and turn outcomes remain unaccepted | Accepted wait lists in [Codex](../agent_observer/codex_snapshot.py) and [Claude](../agent_observer/claude_snapshot.py) cover selected approvals only | Record general input/question and failure/interruption proofs as provider/topology gates. Unknown does not become waiting or working. |
| Runtime presence has different native meanings | [Current contract](snapshot-contract.md) distinguishes loaded Codex server thread and verified Claude OS worker; [model tests](../tests/test_observation_model.py) retain work independently of absent worker | Define runtime-context normalization and absence scope before a common parked predicate. Retained jobs and terminal attachment remain separate. |
| Conversation age is not established by current clocks | [Codex metadata](../agent_observer/codex_metadata.py) exposes native created/updated times; [Claude history](../agent_observer/claude_history.py) exposes creation/file times and truncates after creation-based ordering | Define accepted activity events, validate rename/housekeeping invariance and apply ordering before caps or provide recoverable pagination. Preserve evidence versus collection clocks; never present mtime/creation/poll time as activity. |
| Current logical namespace also contains runtime/OS context | Namespace functions in both snapshot collectors hash config path and OS namespace links | Validate storage-scope identity separately from runtime incarnation; preserve current v1 exact keys/guards until cutover. Deferred profiles do not remove provenance validation. |
| Aggregate partial health can hide healthy dimensions | [Claude tests](../tests/test_claude_snapshot.py) retain current live facts through independent history/partial-store failures; Codex invalidates live facts after a later saved-read failure; [RLCD example](../examples/rlcd_bridge.py) selects live rows using source-level current health | Specify shared-incarnation invalidation versus independent dimension failure. Preserve usable healthy facts under partial coverage; change consumers only in their own passes. |
| Default top-level filtering could omit legitimate history | Current saved Claude rows have unknown session classification | Exclude only confirmed children in default views. Unknown classifications remain visible and do not confer action authority. |
| New Here cannot simply extract row-dependent Plus New | Agent Plus `contract_lifecycle.py` New paths inherit a selected row and native source health | Add independent provider/artifact/config preflight and explicit owning-host cwd. Prove zero-row New; missing daemon may be started only by the explicit write action. |
| Prepared argv can outlive its validated context | Plus lifecycle prepares native commands, while backend launch preflight resolves executables separately; Claude observation hashes a fixed executable | Define execution-time handoff revalidation and bind the executable actually launched. A prepared result is not continuing action authority. |
| Machine JSON and native TTY entry need different I/O contracts | Existing snapshot CLI emits bounded JSON; native TUI attach/resume has interactive output and lifetime | Keep structured preparation/dispatch separate from native terminal execution; do not capture interactive entry with the snapshot runner. |
| Requested identity may differ from resulting identity | Plus `claude_actions.py` and backend correlate short job cue to actual public Observer session; saved resume can copy; Codex New can lack an ID before entry | Publish distinct requested/resulting identity and pending identity, with exact job/session mapping. Terminal failure after creation retains the provider effect. |
| Local/remote failure cannot prove no provider effect | Plus backend pins action route and avoids redispatch after uncertain launch; bounded runner kills launcher process group on timeout | Separate provider effect, transport certainty and viewer result. Prove launcher cleanup preserves managed workers. Missing remote marker and request IDs do not establish safe retry/idempotency. |
| Reader purity and cross-host project tests needed explicit gates | Current CLI only emits snapshots; Plus has a separate strict parser and RLCD projects stdin through its own reader | Add filesystem-free public-fixture reader checks, bounded polling, and explicit cross-host project-mapping cases. Public absolute-root output remains a C2 decision. |
| Push to consumers differs from native event coverage | Current Codex transport ignores unsolicited messages; official App Server reads do not subscribe; hook decisions/continuations can precede final native state | Define snapshot/watch contracts together. Initial polling may push sampled changes; native notifications/hooks remain separate proof gates and use snapshots for recovery. |

The action findings are requirements for extraction, not proof that the new write
CLI exists. The source inspection identified executable/handoff and row-dependent
New limitations; resolving the documentation does not fix those code paths.

## Acceptance matrix for later implementation

| Area | Meaningful cases | Evidence gate |
| --- | --- | --- |
| Passive dependency boundary | Core/read functions work without write/SSH/Tmux dependencies; passive entry never imports or dispatches write behavior or auto-starts a provider | Import/install checks and bounded fixture tests; native side-effect proof for new reads |
| Phase semantics | Blank live session waiting without completed-turn claim; approval/question blocked only after acceptance; tools/internal waits working; present unknown stays unknown | Contract fixtures plus isolated native transitions per provider/artifact/topology |
| Parked/coverage | Saved-only unknown; partial or unavailable roster unknown; complete scoped runtime absence parked; viewer exit during working does not park; retained job/outcome preserved | Scoped absence fixtures and native lifetime/coverage proof |
| Chronology | Repeated polling, rename, Git inspection and maintenance do not refresh activity; old session with a new turn survives history cap; phase-change time may be unknown; skew/equal/null timestamps explicit | Source-semantics proof and ordering/pagination fixtures |
| Identity | Same UUID on different hosts/stores stays separate; verified same storage identity survives runtime restart/rebinding; action context refreshes; path aliases are not guessed | Contract fixtures and isolated native rebinding tests |
| Partial facts | Healthy provider survives another failure; healthy live/history dimension survives unrelated failure; shared identity failure invalidates affected facts | Fault-injection/conformance fixtures; native gaps where needed |
| Git/workspace | Nested cwd, linked worktree with `.git` file, non-Git and missing directory, detached/unborn branch, overlapping roots, symlink policy, bounded cost and no network/hooks/status scan | Disposable local filesystem/Git fixtures; no provider action needed |
| Cross-host projects | Explicitly mapped different physical roots join project context; unmapped same-named repositories/clones/worktrees stay ungrouped; grouping preserves session keys and checkout context | Pure mapping fixtures; no network or native provider needed |
| Read CLI | Public-fixture parsing/filtering/ordering/projection without provider homes/filesystem/actions/transport; human/JSON preserve identity/unknown/coverage; unknown children visible; polling cost/minimum interval, no overlap and timeout/cancel/gaps explicit | CLI/public-schema conformance corpus reused in separate consumer checks; snapshot sampling is not an event stream proof |
| Push monitoring | Initial snapshot/event races, duplicate/late events, slow consumers/overflow, sink downtime, restart/resync, metadata-only hook delivery and parent/child correlation; observer disconnect does not alter provider lifetime | Watch/gap fixtures; isolated native event-subscription/hook passivity proof per artifact/topology; no lossless/replay claim from polling |
| Write contract | Rejected, known no-effect failure, prepared identity pending, confirmed native creation/copy, trust required, uncertain effect and viewer failure after creation | JSON fixtures and execution-boundary tests |
| New/Resume | Zero-row New, owning-host cwd validation, actual executable/config validation, live attach versus saved UUID resume, actual copied session identity | Isolated native action proof, preserving existing empty Claude BG/closed-stdin route |
| Handoff/supervision | Delayed/changed preparation rejected; execution revalidates; timeout cleans owned launcher without killing provider work; created session retained after UI failure | Launcher fixtures plus isolated native worker-lifetime tests |
| Networking | Per-host provenance and schema checks, partial feeds/cache age, read fallback, no uncertain write redispatch, remote cwd validation | Controlled transport tests; native SSH-loss/sleep/recovery accepted separately |
| Consumer delivery | Plus uses public read/write contracts; RLCD needs no write dependency; each retains UI/device and viewer guards | Separate consumer source, installed and UI/device acceptance |

No new test suite is added in this documentation pass. These cases define
appropriate future checks; current synthetic tests establish only their existing
coverage, not proposed commands or native capabilities.

## Open decisions

The plan deliberately leaves exact durable storage identity, accepted activity
source/events, per-provider runtime-absence predicates, root/symlink mapping
rules, schema version/evolution details, read/write entry-point names and
execution-time handoff mechanism for C1/C2/C4. They are bounded decisions with
acceptance cases, not reasons to introduce a provider manager, networking daemon,
operation journal, profile UX or legacy discovery stack.
Whether configured absolute-root paths are public fields also belongs to C2;
they remain necessary host-local configuration regardless of wire projection.

The user's new priority is core/contract/client work independently of frontends.
The earlier M/R pilot's graphical, native recovery, artifact publication and
coordinator-reopen gates remain open in the handoff. Schema/source validation
cannot close them, and this documentation work requires no current-session restart.

## Validation record

The subsequent push-monitoring discussion added a primary source/documentation
review of current transport behavior and official Codex/Claude interfaces, and
explicit watch/source-event requirements. This follow-up is not new native proof
or a claim that the three earlier reviewers tested a streaming implementation.

Initial inspection found a clean Observer worktree at `main`, two local commits
ahead of `origin/main`. All review workers were read-only. Only documentation
and development guidance are edited by the primary; changes are uncommitted.

- Contract review: current/proposed phase and clock meanings, parked predicates,
  durable identity, classification, recency caps and independent fact health.
  Final revised-text review found no unresolved documentation blocker.
- Action/network review: actual executable/context, zero-row New, native entry,
  copied/pending identity, JSON/TTY separation, effect uncertainty, retries and
  provider ownership. Final revised-text review found no unresolved blocker.
- Consumer/project review: public-fixture reader purity, explicit cross-host
  mappings, local Git/root scope, polling budgets and separately gated consumer
  delivery. No architecture blocker; its requested acceptance additions are
  incorporated in the plan and matrix.
- Primary review: conversation decisions captured; C0-C5 dependencies have no
  cycle, networking/write delivery do not gate a read-only consumer, current v1
  semantics remain explicit, and dated pilot records have navigation notices.
- `./scripts/check`: passed 127 existing tests and checks for 24 Markdown files,
  local links, whitespace, fences and staged/unstaged Git whitespace. Tests are
  synthetic/controlled and do not prove the proposed native capabilities.
- Agent Plus and chezmoi worktrees remain clean at their existing local-ahead
  revisions. No consumer files, installed artifacts or provider settings changed.

Next execution is C1's bounded model/source decisions, followed by C2 public
schema/fixtures. Native proof, implementation, installation and consumer
acceptance are separate work; no published release or restart is implied here.
