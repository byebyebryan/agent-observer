# Session mesh design and roadmap review

This is the dated migration-planning review. The next independent contract/client
track is in [the new plan](contract-and-clients-plan.md) and
[review](contract-and-clients-review.md); those govern future component/client
ownership while this document retains its original evidence scope.

Date: 2026-10-02. Scope: planning, source and documentation validation.
This review covers the [architecture](architecture.md),
[migration plan](native-runtime-migration-plan.md),
[roadmap](roadmap.md) and alignment with the
[observation spike](agent-session-spike-plan.md). Native delivery acceptance
remains pending.

## Review outcome

The plan now expresses the user's product goal: Agent Plus meshes sessions
across providers and hosts, with provider-independent observation and separate
validated actions. Codex leads delivery; Claude remains required for the
completed migration and checks the shared abstraction. Work/general context
organization is independent of provider and host.

The roadmap separates P1-P5 source proof from M0-M6 runtime/Agent Plus delivery
and R1's RLCD consumer track. A first Codex milestone can precede Claude;
schema stabilization and completed Agent Plus acceptance require both models.
RLCD firmware acceptance does not block an Agent Plus milestone. Temporary
consumer breakage is accepted, and OpenCode is removed at cutover.

The next task is the bounded Codex native managed-runtime/client proof on Snap.
The documents do not authorize Observer to create work or promote empty/static
evidence to populated-runtime support. Implementation choices remain tied to
explicit proof decisions.

## Inputs checked

| Input | Inspection | Limit |
| --- | --- | --- |
| Observer checkout | Existing studies, spike, Snap/Starship evidence, architecture, roadmap and instructions | Existing uncommitted work preserved; documentation planning only |
| Snap provider installation | Codex package 0.160.0-1 and Claude package 2.1.287-1; executable hashes matched Snap evidence | Running-daemon versions/topology and populated native behavior not re-tested |
| Agent Plus source | Clean checkout at `6d30f8c71a9e44ba1da19f4102292f6811df50d8`, version 0.12.1; README, discovery, lifecycle, config and package metadata | Source inspection does not establish installed fleet parity or native acceptance |
| RLCD source on Starship | Checkout at `a8e6384404008912824cc38d9dc3512c69948bab`; README already modified and preserved | README declares Observer consumer intent; no agent host bridge/dashboard exists yet |
| Prior session-client research | Identity, validated attachment and recovery requirements retained | Terminal presentation feasibility is not managed-runtime acceptance; session rail remains separate |

The source check uses current checkouts rather than treating older reference
revisions as current implementation. RLCD input establishes planning fit only;
there is no existing dashboard protocol to validate or firmware change to test.

## Findings resolved in the design

| Finding | Evidence or conflict | Resolution |
| --- | --- | --- |
| Proof roadmap stopped before delivery | P1-P5 previously covered source selection without runtime/consumer sequencing | Added native, Observer, runtime/package, local Agent Plus, cross-host, Claude and release checkpoints with owners/dependencies |
| Codex priority could become exclusive coupling | Agent Plus README currently requires Codex in its core contract | Require Claude-only consumer operation; keep common schema generic and validate both native models before stabilization |
| Daemon enablement was too broad a proxy for adoption | Claude direct foreground entry remains distinct from supervised jobs; Codex auto-start flag is not actual topology | Separate managed-runtime/native entry proof from configuration and Observer reads |
| Launch options cannot establish current viewed identity | `fast_open_selection` validates a tmux launch option; README excludes native conversation switches | Make current binding an early feasibility gate; update or invalidate associations before session-specific viewer actions |
| Process, job and session lifetimes could be conflated | Current activity probes correlate processes; native workers/clients can have different lifetimes | Preserve logical/session/job/runtime/client distinctions and test viewer close, detach, TUI exit and native stop separately |
| Saved history could omit native live work | Codex history uses a CLI-only source filter and recency limit; live jobs may lack wrappers | Separate saved/live coverage and pagination; test old live sessions, manager-created sessions and missing wrappers |
| Batch Resume changes were implicit | Current batch opens existing tmux references and creates no provider process | Treat new attachment-client creation as an explicit action-contract change with frozen targets and separate native acceptance |
| New Here could change project/Git policy | Native Claude background dispatch can use provider-created worktrees | Preserve project-directory meaning; resolve supervised creation route and explicit worktree policy before acceptance |
| Passive command assumption was overstated | Isolated Claude roster calls initialized preferences; static trace includes housekeeping | Require populated path side-effect checks; source remains provisional and cannot repair settings/start runtime |
| Remote packaging requirements were missing | Current Agent Plus remote hosts need provider/terminal tools but not its source checkout | Install compatible Observer on each target host; invoke through existing host authority without embedded remote provider probes |
| OpenCode deprecation lacked removal detail | Provider probe, action map, ID validation, icon, aliases and package description remain in current source | Schedule full integration cleanup and cache/provider-set invalidation; preserve standalone tool/history; no imaginary runtime dependency removal |
| RLCD could accidentally become a UI migration gate | RLCD is still bring-up firmware with future consumer intent | Review its requirements at M1; give bridge/firmware an independent R1 track |
| Earlier documentation overstated command/proof status | Source study referred to daemon management; spike header said no live runs despite empty P1 evidence | Correct command claim, date earlier Starship observations and acknowledge bounded empty probes without upgrading native support |

## Requirements and delivery coverage

| Requirement | Planned coverage | Acceptance still pending |
| --- | --- | --- |
| Cross-provider/host mesh | Common identity/capability boundary, existing Host Mesh composition, M4/M5 | Native both-provider and multi-host cases |
| Individual TUI with provider-managed work | M0 workflow proof; M2/M5 host/runtime policy | Codex managed daemon and Claude supervised job/attach |
| Strong secondary provider | Early Claude model review, Claude-only host and M5 full integration | Populated Claude roster/lifecycle and single-host UX |
| Thin consumer with validated actions | Observer discovery; consumer action adapters; exact native and viewer checks | Current binding, attach/history/new and single/batch actions |
| Native navigation retained | Supported current binding or explicit invalidation; source-level ambiguity rules | A-to-B switching and delayed old evidence |
| Honest freshness/coverage | Separate state/presence clocks, epochs/revisions, pagination and explicit gaps | Mid-turn/wait recovery, partial rosters and source failure |
| Minimal safe retained evidence | Metadata allowlists, bounded errors, no prompts/tool content/raw payloads | Runtime receiver/hook failure behavior and overhead |
| Accepted breakage and narrow cutover | Direct native access, scoped settings/packages, one observation authority | Pilot and per-host source/installed/live checks |
| OpenCode removal | M3 cutover/M6 cleanup across probes, actions, caches, UI/assets/docs/tests | Implementation removal and obsolete-row rejection |
| RLCD reuse | M1 contract review and separate R1 host bridge | Bridge/device transport and physical acceptance |

## Validation performed

The delivery dependency comparison passed: both documents contain the same
eight M/R checkpoints and dependency edges, with no undefined or circular
dependencies. Codex M4 does not depend on Claude M5 completion; M6 requires
both M4 and M5; R1 does not gate Agent Plus closure. R1's stable boundary includes
the shared schema validation gate. Source references, native UX acceptance,
metadata retention and operation-specific action guards were reviewed against
the actual plan.

`./scripts/check` passed for 12 Markdown files, local links, whitespace, code
fences and Git diff checks. Agent Plus stayed clean; RLCD retained the same
pre-existing README modification after read-only inspection. Existing Observer
evidence and study changes were preserved.

No provider-native session, UI action, configuration change, hook installation,
service deployment or firmware test was executed by this planning validation.
Documentation and dependency checks do not establish a native coverage result.

## Configuration and execution continuity follow-up

A read-only recheck confirmed Codex `features.daemon_auto_start=false` and
Claude `disableAgentView=true`; neither selected Claude UI preference is
explicitly set. Chezmoi owns Codex's config through the existing merge/template,
but owns neither `~/.claude/settings.json` nor `~/.claude.json` on Snap. The plan
now distinguishes the managed Codex change at M2 from scoped Claude settings
and native UI preference changes at M5; ownership is rechecked on the work host.

The current terminal Codex process can remain the execution coordinator while
separate clients prove the new runtime. Process ancestry does not establish its
actual owning runtime or an in-place migration capability. The plan now
requires a durable metadata-only handoff and a validated exact-conversation
route before any final self-transition that exits this client. No restart is
required to begin implementation; any unavoidable manual step is documented
before reaching it. No ordinary provider settings or sessions were changed by
this follow-up.

## Remaining proof decisions

The following gates are deliberately unresolved, not hidden design assumptions:

- Managed Codex endpoint/namespace discovery and read passivity, including when
  absent and across runtime versions/incarnations.
- Exact native session/thread/job mapping and current client-to-conversation
  binding. An unavailable binding blocks affected viewer actions; independent
  inventory/metadata work can continue with explicit limits.
- Native detach, TUI exit and cancellation behavior, including manager returns
  and multiple clients.
- Claude populated-roster side effects, supervised New Here route, worktree
  policy, fullscreen copy/scroll and single-machine recovery.
- Source coverage, bounded history/live pagination and recovery from gaps;
  collector choice and measurable multi-consumer cost.
- Real host availability/routing, installed artifacts, ordinary hooks/plugins
  and sleep/wake acceptance on the selected rollout hosts.

These require isolated native tests or later consumer/host acceptance. Passing
documentation checks, schemas, synthetic fixtures or empty lists cannot close
them. Keep P1 active and report subsequent outcomes by provider/version/topology.
