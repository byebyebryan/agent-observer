# Native runtime and session mesh migration plan

Date: 2026-10-02. Status: reviewed design and delivery plan; implementation and
native acceptance pending. [Architecture](architecture.md) defines ownership,
[roadmap](roadmap.md) tracks checkpoints, and the
[observation spike](agent-session-spike-plan.md) defines native source tests.

## Goal and accepted scope

Agent Plus provides session meshing across providers and hosts. Move provider
discovery and monitoring into Agent Observer so Agent Plus concentrates on
presentation, host routing, viewer association and validated actions. Providers
own execution and history; tmux carries individual native TUI clients. Agent
Observer remains passive and host-local.

Codex leads delivery because it is used most often and across machines. Claude
Code remains a required second provider, initially on the user's work machine.
Validate its distinct identity/lifecycle model before stabilizing the shared
contract. A useful Codex milestone can precede Claude completion; completion of
the migration includes both providers.

Temporary Agent Plus breakage is acceptable. A parallel legacy discovery stack
is not required. OpenCode integration is deprecated and is removed at the
migration cutover. Its standalone installation and saved history are separate
from this support decision.

The user's work/general distinction guides presentation. Provider, owning host
and usage context remain separate. Context views or tags are optional consumer
policy, not an Observer inference or a prerequisite for this migration.

## Evidence supporting the plan

The [runtime UX study](provider-runtime-ux-study.md) establishes installed
interfaces and current Agent Plus source behavior. The
[Snap preflight](evidence/2026-10-02-p1-snap/REPORT.md) proves only bounded empty
reads and selected static capabilities. Populated native sessions, managed
runtime identity, client bindings, transitions and recovery remain unproved.

During this planning pass, Snap package identities and executable hashes still
matched Codex 0.160.0 and Claude 2.1.287 from the preflight. Agent Plus remained
at `6d30f8c71a9e44ba1da19f4102292f6811df50d8` with a clean source checkout.
RLCD's Starship checkout remained at
`a8e6384404008912824cc38d9dc3512c69948bab`; its existing README change was read
and preserved. That README identifies Observer as a future consumer dependency;
agent host integration and the dashboard are not implemented.

These checks establish planning inputs, not installed Agent Plus parity,
current running-server versions or native-runtime acceptance. See the
[design review](design-review.md) for findings and validation limits.

## Runtime policy and individual TUI entry

| Provider | Target execution model | Target entry experience | Native proof required |
| --- | --- | --- | --- |
| Codex | Provider-managed shared runtime on the owning host | Individual native TUI connected to that runtime; manager browser remains optional | Managed endpoint discovery, exact thread/session mapping, ordinary entry, live attach versus history resume, switching and exit behavior |
| Claude Code | Provider supervisor and separate background-job workers | Individual native TUI attached to the selected job | Actual supervised job creation/transition, UUID/job mapping, attach/detach, ordinary entry preferences and worker recovery |

Enabling Claude Agent View permits management and observation candidates; bare
foreground entry does not by itself create a supervised session. Its proposed
foreground-compatible configuration is useful for comparison and transition,
but does not satisfy the supervised-runtime delivery gate.

Runtime configuration belongs to host/provider configuration work,
separate from Observer. Observation must not start a missing daemon, load or
resume a session, background work, or repair an opt-out. An absent endpoint or
unsupported namespace is a capability/health result.

The selected settings and ownership below were rechecked on Snap on 2026-10-02.
The table records the design-time baseline, not the later execution state.
Recheck ownership, overrides and launch flags on each rollout host.

| Configuration | Current Snap state | Planned change and delivery owner |
| --- | --- | --- |
| Codex `features.daemon_auto_start` in `~/.codex/config.toml` | `false`; chezmoi-managed | M2: enable after M0 proof through `.chezmoitemplates/codex-portable-config.toml.tmpl` and the existing `dot_codex/modify_private_config.toml` merge; scope rollout to the pilot before M4 |
| Claude `disableAgentView` in `~/.claude/settings.json` | `true`; not chezmoi-managed | M5: scoped change to `false` on the selected work host, preserving unrelated settings, hooks and plugins |
| Claude `defaultToAgentsView` and `leftArrowOpensAgents` UI preferences | Neither explicitly set in `~/.claude.json`; file not chezmoi-managed | M5: use proved native `/config` controls to set both to `false`, retaining individual entry and avoiding accidental backgrounding through Left |

Changing Claude's settings ownership is separate from the selected-key edits;
the plan does not assume an existing managed Claude template. Its supervised
creation/transition and attachment route still requires native proof: these
three settings alone do not move foreground work into the supervisor.

Execution update, 2026-10-03: the scoped Codex change is applied on Snap and
Starship. Snap Claude settings and the two UI preferences now use incremental
chezmoi overlays that preserve all unrelated fields; other hosts ignore these
Claude targets. Native evidence accepts empty `claude --bg` with closed stdin,
followed by exact short-ID attach, as Agent Plus New's supervised route. The
per-launch `worktree.bgIsolation="none"` setting preserves the selected cwd.
Ordinary default configuration unsets `CLAUDE_CONFIG_DIR`; explicit custom
roots retain it. These observations supersede the creation gate above for the
pinned subset; see the [execution status](execution-status.md) and
[native report](evidence/2026-10-03-native-runtime/REPORT.md).

Preserve New Here's project-directory meaning. Prove a native launch or
transition route that reaches the target runtime in the selected checkout.
Provider-created worktrees require an explicit creation policy; they must not
silently replace New Here or introduce implicit commit/push behavior. Keep
this route pending if the installed provider cannot supply the intended flow.

Viewer Close retains its current window-only meaning. Separately test client
detach, TUI exit and native stop/cancellation: they are different operations.
No promise that work survives every TUI exit follows from a persistent daemon.

## Observation and action integration

Observer supplies saved inventory and live observations independently, together
with exact identity scope, capability coverage, freshness and uncertainty. Agent
Plus joins those observations with Host Mesh authority and Tmux Plus viewer
evidence. Observer emits no terminal command, SSH route or operation handle.

The shared contract must work with a host that offers only Claude; Codex is not
a mandatory dependency of provider-neutral consumer startup. Missing providers
are reported independently. An unavailable provider must not invalidate healthy
observations from another provider or silently become an empty successful list.

Treat source coverage and presentation limits separately. A recent-history cap
must not hide older live work. Include native-manager-created user sessions only
after proving their source/identity mapping; do not inherit Agent Plus's current
CLI-only Codex filter as a universal roster rule. Relationships to worker or
subagent sessions remain explicit, with inclusion chosen by the consumer.

| Agent Plus operation | Planned behavior | Required evidence |
| --- | --- | --- |
| List/refresh | Read Observer on each selected host; combine results without starting provider work | Compatible schema, host authority, source coverage and freshness |
| Open existing viewer | Focus a viewer currently associated with the selected native conversation | Fresh conversation/client binding plus exact Tmux Plus reference and viewer validation |
| Open live session without a viewer | Create an attachment client through Tmux Plus for the existing native runtime/job | Fresh exact native target and proved attach semantics; attachment must not create replacement work |
| Resume saved history | Explicitly activate the selected saved conversation through the provider | Current history identity, known runtime disposition, namespace/cwd and native resume semantics |
| New Here | Create new work in the selected project and attach an individual TUI | Fresh host/provider/cwd validation and accepted native creation/worktree policy |
| Close viewer | Close only verified viewer windows for that selected session | Fresh association and exact window handles; no native stop, archive or deletion |
| Batch Resume | Eventually attach viewers to a frozen set of existing native sessions, including jobs without wrappers | Explicit preview/confirmation, current target identity, supported attachment and per-target validation |
| Batch Close | Close a frozen set of verified viewer windows | Exact fresh handles and current associations; ambiguity is an exclusion |

Current Batch Resume opens existing tmux references and creates no provider
process. Creating native TUI attachment clients expands that action contract,
even when no new job is started. Implement and accept it separately. A first
Codex milestone may retain wrapper-only batch eligibility as an explicit limit;
the completed cross-host viewer workflow must cover live sessions without an
existing wrapper.

Native conversation switching must remain usable. A launch-time tmux provider
option is historical association evidence, not proof of the current view. Prove
a supported source for the current binding, or invalidate that association and
show the limitation. Reject session-specific focus/close operations with stale
or ambiguous bindings. A fresh attachment may be offered only when its exact
native target and route are independently validated. Generic Tmux Plus window
management retains its own authority.

Keep work state, runtime presence, provider attachment, local window presence,
observation health and deferred-launch status separate in the UI. Agent Plus's
current Active/Open/Waiting vocabulary needs a deliberate mapping review. An
approval wait must not reuse the pending-launch marker, and an unavailable
observation must not appear idle/inactive. Changing the picker layout or adding
a persistent session rail is separate presentation work.

## Delivery checkpoints and dependencies

All delivery checkpoints below are planned. Existing P1-P5 observation proof
remains version/topology-specific. Runtime configuration and consumer actions
are exercised by separate, deliberate operator/test actions, never by the
observer adapter.

| Checkpoint | Work and owner | Dependencies | Exit |
| --- | --- | --- | --- |
| M0: native workflow proof | Observer spike and isolated native TUI procedures, Codex first; early Claude identity/lifecycle comparison | Relevant P1 isolation/passivity gates | Codex managed topology, exact identities and attachment behavior proved; Claude model differences recorded; remaining coverage explicit |
| M1: Codex Observer implementation | Observer source adapters, saved/live reconciliation and provisional JSON | Codex P2-P4 evidence and source decision | Passive supported reads, explicit incomplete/unknown states, version/schema handling, recovery and measured overhead; RLCD/Agent Plus requirement review |
| M2: host runtime and package pilot | Managed Codex configuration plus Observer installation on Snap | M0/M1 | Native individual entry, actual owning runtime, hooks/plugins and exact installed artifacts accepted; direct native access documented |
| M3: Codex Agent Plus migration | Agent Plus Observation backend, state presentation, provider action adapters and viewer bindings | M1 contract; M2 before ordinary-runtime acceptance | Codex discovery and single actions accepted locally; malformed/stale inputs reject; temporary limits documented; OpenCode support removed at cutover |
| M4: Codex across machines | Observer host installation, existing Host Mesh transport and Tmux Plus attachment workflows | M3; preflight each target host | Two-host identity/routing, SSH loss, unavailable hosts, sleep/wake, jobs without wrappers and accepted batch semantics; source/installed/live evidence per host |
| M5: Claude mesh completion | Claude P1-P5 proof, Observer adapter, single-host runtime policy and Agent Plus actions | Early M0 model review; consumer boundary from M1/M3 | Supervised native UX, state/recovery, context-independent identity and actions accepted; shared contract validated for both providers; Claude-only host case accepted |
| M6: Agent Plus release closure | Agent Plus deployment bookkeeping, contract stabilization and obsolete-code cleanup | M4/M5 | Both-provider Agent Plus acceptance recorded; compatible artifacts/schema, legacy discovery removal and maintenance procedure documented |
| R1: RLCD host bridge | RLCD selection/prioritization and device transport using Observer | Proved M1 observations and common contract review; M5 for stable schema | Live roster/health/waiting and bridge recovery accepted; firmware/physical evidence recorded separately in RLCD |

M5 can progress alongside M4 when its dependencies are ready. R1 contract
fixtures and bridge design can start at M1; stable integration follows shared
contract validation. Firmware layout/transport work belongs to RLCD, and RLCD
physical acceptance is a separate delivery record that does not gate Agent Plus.
WSNav and a new Observer network control plane are not gates for either consumer.

The critical Codex path is native proof, Observer, runtime/package pilot, Agent
Plus local integration, then cross-host acceptance. Contract fixtures and UI
mapping may be developed before the runtime pilot; do not promote that synthetic
success to native acceptance. Target-host inventory is re-established at M2/M4:
Snap and Starship are known references, not proof of an exhaustive fleet list.

## Execution continuity and handoff

The current Codex session can coordinate implementation, scoped installation
and separate disposable native trials while it remains available. Configuration
changes are tested through fresh clients in the proved namespace; restarting
the executing session is not a prerequisite for this work. Establish isolation
before a test entry point can start a runtime, and keep test operator actions
separate from Observer reads.

Do not assume a configuration edit reloads the current session or moves its
active conversation into another runtime. Read-only process ancestry on Snap
confirmed a terminal Codex ancestor, but did not establish its owning runtime
or an in-place migration capability. Existing ordinary sessions, including the
execution coordinator, continue until a deliberate, proved transition or normal
completion.

If moving this conversation requires exiting its client, prepare a durable
metadata-only handoff before that exit: implementation and check status,
outstanding gates, exact saved conversation identity and owning host/namespace,
the validated reopen/attach route, and recovery instructions. Never exit the
coordinator while it is executing the cutover or resume its conversation into
another writable runtime concurrently. Use the proved provider route after
the old owner has quiesced. If the agent cannot reopen its own exited client,
the user performs that final reopen and continues from the handoff.

Codex documents [resuming an interactive session by ID](https://learn.chatgpt.com/docs/developer-commands).
That supports a candidate continuity route, not proof of live daemon attachment
or in-place promotion. Native authentication or visual/focus acceptance may
need user participation when the available tools cannot complete them; routine
file edits, configuration deployment and separate terminal trials remain agent
execution work. Record any required manual step with the exact point, reason
and validated procedure before reaching it.

## Migration and recovery procedure

Before each host cutover, record the provider binaries, actual running runtime
version, relevant settings, configuration namespace and endpoint ownership.
Install the proved Observer artifact and verify its schema/capabilities. Runtime
changes are scoped to the intended host/provider and new launches; active
ordinary sessions are not automatically converted or terminated.

Define a bounded breakage window at the pilot/cutover. Verify direct native
launch/attach access first, then change scoped runtime settings and switch the
Agent Plus backend. The backend uses one discovery authority; consumers do not
silently fall back to the retired process/transcript implementation. Old cached
rows are invalidated through an explicit schema/provider-set migration, without
deleting provider history.

Observer is needed on target hosts once discovery moves there. Agent Plus's
current remote-tool-only deployment is insufficient for the new boundary.
Existing SSH routing invokes the host-local executable and validates its result;
source code is not injected into remote probes. Reuse an existing daemon without
creating an Observer-owned provider server. Choose a watcher/collector only if
measurements justify it, and measure concurrent consumers' connection/load cost.

If a cutover fails, keep direct native access available and record which
integration is unavailable. Restore a previous consumer/configuration artifact
only after checking its compatibility with the current runtime and live work.
Do not stop the provider daemon or replay session activation to make a rollback
look successful. Restoring a flag alone cannot establish standalone topology.

## Source ownership for later implementation

| Repository | Responsibility and starting areas |
| --- | --- |
| Agent Observer | Provider adapters, metadata allowlists, identity/reconciliation, JSON boundary, coverage fixtures and native evidence; implementation layout/language chosen at P5 |
| Agent Plus | Replace provider probes in `contract_backend.py`, `engine.py`, `codex.py` and `claude_probe.py`; adapt `wire.py`/`cache.py`; revise `contract_lifecycle.py`, `contract_viewers.py`, `viewer_state.py`, `batch.py` and `rofi.py` |
| SSH Plus / Tmux Plus | Preserve public host/terminal contracts; change them only if exact native client binding or attachment delivery requires a separately reviewed extension |
| Host configuration / managed dotfiles | Codex managed runtime settings, scoped Claude settings/preferences under verified ownership, compatible Observer/consumer pins and per-host installation; hooks/plugins verified separately for each provider |
| RLCD | Host bridge selection/prioritization and device transport using Observer; firmware remains in that repository |

OpenCode removal in Agent Plus includes `opencode_probe.py`, local/remote probe
branches, action mappings, wire/cache provider validation, search aliases/icons,
package metadata, fixtures/tests and current documentation. Current Agent Plus
configuration only has `max_sessions` and `refresh_seconds`, and its package has
no runtime dependencies; remove provider-specific items where they actually
exist. Preserve generic contracts and unrelated provider history.

## Acceptance and review matrix

Record `passed`, `failed`, `unsupported`, `unavailable` or `not_run` per provider,
version, host, namespace and topology, with the evidence type attached. Required
supported-mode gates must pass before declaring that mode accepted; an explicit
limitation is honest coverage, not a passed requirement. Source normalization may
be tested synthetically; live identity and actions require native trials.

| Gate | Required evidence | Delivery boundary |
| --- | --- | --- |
| Passive observation | Missing-runtime read does not start it; populated reads do not activate work, change settings or alter native session behavior; disconnect/subscription effects measured | M0/M1 and each new provider/source |
| Exact identity | Same cwd/title, differing hosts/namespaces, native new/resume/fork and old delayed events preserve correct logical bindings | M0/M1/M4/M5 |
| Work and waiting | Working/settled, approval and denial, blocking input, cancellation and errors, with separate state/presence freshness | P3 and M1/M5 |
| Runtime/client lifetime | Viewer close, native detach, TUI exit, worker retirement/restart and daemon restart have distinct observed outcomes | M0/M3/M5 |
| Native TUI experience | Individual entry, streaming, input/paste, mouse, scroll/copy, focus and approval interaction work in the real terminal/tmux setup; cross-host clipboard/reconnect tested separately | M0 feasibility; M3/M4 Codex; M5 Claude |
| Current viewer binding | A pane switched from A to B updates or invalidates its association before actions for A | M0 feasibility; M3/M5 acceptance |
| Recovery and coverage | Mid-turn/wait restart, missed observations, pagination/partial lists and old live sessions outside history cap produce correct recovery or explicit uncertainty | M1/M4/M5 |
| Provider independence | Claude-only host and absent provider fixtures use the same generic consumer boundary; shared contract represents both native models | M1 synthetic; M5 native |
| Cross-host actions | Host revision, namespace/runtime incarnation and exact target are refreshed before action; SSH/sleep gaps cannot focus/close/create on another target | M4 |
| Batch attachment | Frozen preview and per-target revalidation; creation of clients for existing work introduces no new job or additional target | M4/M5 after action contract change |
| Ordinary integration | Scoped settings, native startup, hooks/plugins and installed source hashes checked for each provider/host | M2/M4/M5 |
| Execution continuity | Coordinator preserved during rollout; any final self-transition has a metadata-only handoff and validated exact-conversation reopen route | M2/M4 and any coordinator transition |
| OpenCode removal | No provider probe/action/UI path remains; old rows are visibly unsupported or invalidated and cannot be reinterpreted | M3/M6 |
| RLCD consumer fit | Common observations support live roster, waiting/health and recovery without provider-private parsing | M1 contract review; R1 bridge acceptance |

The spike's one-second snapshot, five-second health and two-second wait-clear
targets remain measurement targets. Hook handoff, if needed, targets 100 ms.
Choose intervals, size limits, memory/CPU budgets and watcher lifetime from the
source measurements; record failures or unresolved timing instead of promising
unmeasured service levels. Evidence remains bounded metadata/reason codes, with
no prompts, responses, tool content, terminal captures or raw provider payloads.

For Claude background attachment, accept fullscreen scroll/copy using its native
controls in the actual work-machine terminal. Tmux scrollback is not assumed to
contain the full conversation. Keep real UI acceptance separate from source,
schema and transport checks.

## Decisions required from proof

| Decision | Default direction | Resolution gate |
| --- | --- | --- |
| Owning-runtime discovery | Exact existing native endpoint and namespace; no Observer auto-start | M0/P1 |
| Snapshot/watch/collector | Start with the smallest passive host-local read; add watch only for proved coverage/latency or reuse needs | P2/P5 and M1 measurements |
| Client-to-conversation binding | Supported native client evidence; otherwise association becomes unknown | M0, before session-specific viewer acceptance |
| Stored versus native IDs | Preserve separate IDs and exact mapping evidence | P4/M0 |
| Claude New Here | Provider-supported supervised flow preserving selected checkout; worktrees explicit | M0 comparison/M5 |
| Shared schema and language | Provider-independent metadata JSON with version/coverage; use the language justified by the proof | P5/M1; stabilization after Claude validation |
| Active/Open/waiting UI | Separate runtime presence, work, window and launch state; preserve useful current navigation | M3/M5 |
| Batch Resume expansion | Attach viewers to existing work after explicit frozen preview; no new jobs | M4/M5 |

## Next bounded work packet

Prepare a Codex managed-runtime/native-TUI proof on Snap. Recheck the installed
binary and existing endpoints; establish private configuration, workspace and
runtime isolation before any auto-start-capable entry. Use separate operator
creation/attachment and observer read paths. Any authenticated setup needs its
own isolation check; the prior network-isolated empty fixture cannot prove it.

Prove the owning endpoint, logical/thread IDs, one native conversation and its
client, and the outcomes of viewer close versus client detach/exit. Test a
native conversation switch early because viewer binding can determine whether
the planned action path is viable. Capture only allowlisted metadata and
coverage reasons, then verify ordinary configuration/runtime preservation and
exact cleanup.

If native isolation or the current binding source cannot be established, record
the specific unavailable capability and revise that action/source choice.
Continue metadata/contract work that does not depend on it. Add a bounded
Claude supervised identity/lifecycle comparison before treating the model as
shared. This planning pass does not execute those proofs or change ordinary
runtime configuration.
