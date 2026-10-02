# Agent Observer handoff to Snap

Date: 2026-10-02. Active checkpoint: P1 capability/topology preflight.

## Host decision and repository state

The user has chosen Snap as the execution host for continuing this project.
Claude is available only on Snap according to the user. Continue both providers'
preflight and subsequent isolated spike work there. This changes the work host;
it does not add multi-host aggregation or consumer migration to the scope.

SSH alias: `snap`. The repository checkout was verified at
`/home/bryan/code/agent-observer` (`~/code/agent-observer`), on host `80H1VV3`.
Before this handoff sync it was clean on `main`, tracking `origin/main`, at
bootstrap commit `52f7d872862e3b3311d5a5c0315cb10fcd328732`. The user explicitly
authorized recording context, committing, pushing, and syncing this checkout.
Repository sync is not a provider deployment or a native runtime test.

## Read first

- [Development instructions](../AGENTS.md).
- [Architecture boundaries](architecture.md).
- [Roadmap](roadmap.md).
- [Spike plan](agent-session-spike-plan.md).
- [Source study](agent-session-study.md).
- [Starship P1 report](evidence/2026-10-02-p1-starship/REPORT.md) and
  [capability evidence](evidence/2026-10-02-p1-starship/capabilities.json).

The study and spike plan originated in RLCD and moved into this repository on
2026-10-02. The bootstrap contains documentation and a check script. No provider
adapter, watcher, collector, consumer integration, or stable public API exists.

## Product boundary and decisions retained

Agent Observer owns host-local session discovery and bounded state evidence
for Codex and Claude Code. RLCD and Agent Plus drive initial requirements:
live state, saved-session inventory, exact identity, provenance and freshness.
Consumers retain presentation, actions, runtime ownership and action validation.

WSNav is historical evidence and an optional future consumer. Its private-tmux
ownership model and Rust implementation do not constrain this component.
OpenCode, multi-host aggregation, firmware/UI changes, session actions,
production hooks/services, provider policy changes and consumer migrations
remain deferred.

Snapshot, watch and capabilities over language-neutral JSON are proposals.
Implementation language, source choices, wire fields, reconciliation rules and
the need for a background collector remain open until proof supports them.
Prefer native state feeds where they prove adequate coverage, add hooks for
demonstrated gaps, and use process evidence to corroborate identity/liveness.
This remains a hypothesis rather than an accepted source decision.

## What the Starship slice established

| Area | Dated result | Evidence boundary |
| --- | --- | --- |
| Codex installation | `/usr/bin/codex` resolved to `/opt/openai-codex/bin/codex`; version 0.160.0 | Starship only; inspect Snap afresh |
| Effective selected features | Profile-free hooks enabled; daemon auto-start disabled | Current config, not each process's launch-time config |
| Runtime census | Five terminal-attached Codex processes; no owning daemon detected by inspected signatures | No native session IDs, session count or work state established |
| Ordinary hooks | One `Stop` entry; separate lifecycle profile not explicitly selected by observed processes | Configuration presence, not hook delivery |
| Temporary config | Disposable home/cwd selected `hooks=false` and `daemon_auto_start=false` | Config selection passed; daemon namespace isolation unproved |
| Static schema | Runtime states and approval/input waiting flags present | No native transition coverage |
| Preservation | Monitored config hashes and process birth identities unchanged | Bounded before/after comparison on Starship |
| Claude | No executable found in the bounded Starship search | Expected with the user's Snap-only clarification; no provider limitation established |

No native state/roster read, provider turn, hook installation, controlled-server
run, daemon launch, ordinary service/config mutation or consumer change occurred.
Temporary preflight directories were removed. Documentation and bounded JSON
checks passed. The report slice was completed; the overall P1 checkpoint was not.

## Learnings and unresolved questions

- Codex's installed schema exposes `notLoaded`, `idle`, `systemError`, `active`,
  and `waitingOnApproval`/`waitingOnUserInput`. These are promising primitives,
  not proof of reliable observation or cancellation coverage.
- Both thread `id` and `sessionId` exist. Establish their relationship and
  behavior across native new/clear/resume/fork operations before normalizing
  identity. Do not infer identity from cwd, title, PID or file modification time.
- Source kinds include CLI, VSCode, App Server and subagent sources. Establish
  an explicit inclusion policy from native-session evidence.
- `includeTurns=false` still permits a response containing `preview`. Filter
  received responses before retention; no unfiltered payload capture is safe.
- A separate metadata helper's `notLoaded` state cannot describe another
  runtime. App Server observation must reach the server owning the live session.
- Hook enablement, configured entries, and hook delivery are separate claims.
  Existing compatibility configuration must remain intact.
- Temporary config selection, controlled-server isolation and managed-daemon
  isolation require separate proof. A controlled App Server result cannot
  establish managed-daemon support.
- State evidence and presence evidence need separate timestamps. A live PID
  must not refresh old work-state evidence; silence or a missed connection must
  not become idle/settled. Saved history, logical sessions, workers and terminal
  attachments have separate identities and lifetimes.

## First task on Snap

Resume P1 with fresh read-only inspection for both providers. Do not carry
Starship's versions, schemas, config values or topology forward as Snap facts.

1. Inspect repo instructions/worktree and actual executable paths/versions.
   For Claude, establish version-specific command routing before diagnostics.
2. Inspect only known non-secret effective settings and their provenance,
   especially provider compatibility opt-outs and existing hook event coverage.
3. Establish actual foreground/daemon/supervisor topology using process birth
   identity and socket ownership. Stale PID/socket files are insufficient.
4. Check installed read-only interfaces and conditional identifiers. Establish
   whether reads start services, load/subscribe to sessions, or affect workers.
5. Establish disposable home/cwd/endpoint isolation before any live launch.
   Keep unsupported, unavailable and not-run rows explicit if isolation fails.
6. Write separate dated Snap evidence, with bounded metadata and reason codes
   only. Recheck monitored config hashes and ordinary runtime identities.

P1 exits with an evidence-backed capability matrix and minimum isolated
launch/read procedures, including explicit pending reasons for unavailable
rows. Then proceed to P2's smallest native source comparison, P3's waiting/
cancellation transitions, P4's identity/recovery cases, and P5's source/interface
decision. Follow the linked spike's coverage and timing requirements; do not
promote static, synthetic or controlled-server evidence to native acceptance.

## Execution and retention boundaries

Observation must not start, resume, interrupt, approve, deny, rename or delete
provider sessions. Deliberate disposable session creation is experiment setup,
separate from observer behavior. Do not install/update providers, bootstrap
services, enable Remote Control, stop ordinary daemons, change managed dotfiles
or bypass native hook trust to make the experiment work.

Keep credentials transient and outside Git/evidence. Never retain prompts,
assistant responses, tool arguments/output, terminal buffers or raw provider
payloads. Retain bounded identifiers, selected metadata, source/version/topology,
state/reason codes and timestamps. Ambiguous or missing identities remain unbound.
Clean up only experiment-owned processes/endpoints; preserve unrelated changes.

Run `./scripts/check` before committing/publishing documentation. Add focused
runtime validation when implementation arrives. This repository sync does not
authorize a new provider experiment, deployment or policy change; resume the
remaining checkpoint under the next task's scope.
