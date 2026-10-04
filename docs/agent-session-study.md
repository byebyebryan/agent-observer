# Coding-agent session-state data-source study

Date: 2026-10-02. Status: source/documentation study; live proof pending.
Execution plan: [agent-session-spike-plan.md](agent-session-spike-plan.md).

This study originated during RLCD planning and was moved into Agent Observer
on 2026-10-02. Earlier inspected versions and reference revisions below remain
dated evidence. The shared component's boundaries are in
[architecture.md](architecture.md).

Later [Snap preflight](evidence/2026-10-02-p1-snap/REPORT.md) and the
[runtime UX study](provider-runtime-ux-study.md) supersede the earlier provider
availability and command assumptions below. The
[migration plan](native-runtime-migration-plan.md) records the current product
direction; earlier inspected versions/checkouts remain dated reference evidence.

## Purpose and scope

Agent Observer is a shared host-side component for coding-agent discovery
and state observation. Its initial consumer targets are the RLCD dashboard
and Agent Plus. The RLCD needs a persistent session roster; the 349 already
handles interactive system information and notifications.

Data reliability comes before display implementation. Scope is Codex and
Claude Code on local hosts. OpenCode, calendar integration, quotas, remote
control, session actions, and firmware/UI changes are outside this proof.
Multi-host aggregation can follow a validated single-host data contract.

## Consumer priorities

The two active consumer projects are the RLCD dashboard and Agent Plus.
Their current discovery and monitoring needs drive Agent Observer's scope
and public interface; integrations remain pending.

The user reports that WSNav is not actively used or developed and may move
toward a simpler design. Retain its lifecycle work as a historical reference
and treat it as a possible future consumer. Its current private-tmux runtime
ownership and workstream model are not requirements for the shared component.
WSNav integration is not an acceptance gate for this spike. Implementation
language should follow the proof and active consumers, without assuming a
Rust library is required because WSNav uses Rust.

## Evidence and freshness

WSNav and Agent Plus are references for design and known failure modes.
Their local checkouts are not authorities on current provider behavior.
Provider docs can also describe capabilities newer than an installed binary;
the spike must establish the actual version, configuration, and topology.

The inspected checkouts were clean at these revisions:

| Repository | Inspected revision | Role |
| --- | --- | --- |
| `esp32-rlcd` | `a8e6384404008912824cc38d9dc3512c69948bab` | Working firmware/performance baseline before these notes |
| `wsnav` | `74662365b23ce331398d52b0680cd32d36a749d5` | Managed-runtime lifecycle and identity reference |
| `rofi-agent-plus` | `42ac16da09627988253bf12d635868bf25998fdf` | Inventory, process and tmux correlation reference |

The initial Starship inspection on 2026-10-02 established:

- `/usr/bin/codex` reports `codex-cli 0.160.0`.
- `codex features list` reports `hooks stable true` and
  `daemon_auto_start stable false`. Enabled hooks do not establish that an
  observer is configured or that any hook has been exercised.
- The live `~/.codex/config.toml` and chezmoi's
  `.chezmoitemplates/codex-portable-config.toml.tmpl` both set
  `features.daemon_auto_start = false`.
- Installed help exposes `codex agents` and `--no-daemon`. The latter
  explicitly runs without the shared server even when one exists.
  Configuration alone does not establish the live topology. Later Snap help
  probes found no `codex daemon start` or `codex daemon status` subcommand;
  general help output does not establish a daemon-management command.
- Generated schemas from the installed Codex binary expose runtime states
  `notLoaded`, `idle`, `systemError`, and `active`; active flags include
  `waitingOnApproval` and `waitingOnUserInput`. Schema presence is static
  capability evidence, not a successful observation of an ordinary session.
- `claude` was not on this shell's PATH. The Claude runtime version and its
  effective configuration on the actual working host remain preflight work.

The user reports that both providers' daemon/internal session-management
features were deliberately disabled for Agent Plus compatibility. Preserve
that operating context. Codex's current setting was verified here; Claude's
exact opt-out and location were not established by the local checks. Current
Claude docs name `disableAgentView` and `CLAUDE_CODE_DISABLE_AGENT_VIEW`;
neither was present in the inspected local user settings or inherited shell
environment. Verify the opt-out on the actual working host during preflight.

Those opt-outs are a compatibility baseline, not an architectural requirement
for the RLCD feed. Standalone-only success will not establish daemon support.

## What the reference projects establish

### WSNav

Its [Codex hook parser](https://github.com/byebyebryan/wsnav/blob/74662365b23ce331398d52b0680cd32d36a749d5/src/provider/codex/hooks.rs)
accepts four lifecycle events: session start, prompt submission, response stop,
and session end. Its
[state transitions](https://github.com/byebyebryan/wsnav/blob/74662365b23ce331398d52b0680cd32d36a749d5/src/state/lifecycle.rs)
map those to a bound runtime, working, attention, and stopped.

Useful practices are bounded input and processing time, minimal retained
metadata, native session IDs, exact runtime generation/process identity,
and rejection of conflicting evidence. Its
[local observer](https://github.com/byebyebryan/wsnav/blob/74662365b23ce331398d52b0680cd32d36a749d5/src/app/local.rs)
checks a managed private-tmux runtime and direct provider-hook ancestry.
That authority model is specific to foreground runtimes; hooks from a
daemon worker may have different ancestry. This checkout has no Claude adapter.

The [App Server boundary study](https://github.com/byebyebryan/wsnav/blob/74662365b23ce331398d52b0680cd32d36a749d5/docs/evidence/studies/0003-codex-app-server-runtime-boundary.md)
distinguishes a short-lived metadata helper from the server owning a live
session. Its older live spikes are historical evidence, not acceptance of
Codex 0.160.0. Recheck hook ordering, terminal behavior and runtime ownership.

### Agent Plus

Its [process probe](https://github.com/byebyebryan/rofi-agent-plus/blob/42ac16da09627988253bf12d635868bf25998fdf/rofi_agent_plus/engine.py)
uses process arguments and open files to correlate sessions. Its
[backend](https://github.com/byebyebryan/rofi-agent-plus/blob/42ac16da09627988253bf12d635868bf25998fdf/rofi_agent_plus/contract_backend.py)
provides host/tmux association and explicit ambiguity handling. These are
useful identity and discovery patterns. A live process does not establish
that an agent is computing or waiting for a decision.

Current limitations relevant to this study:

- Codex discovery filters `sourceKinds` to `cli`; other interactive sources
  and some forks need an explicit inclusion policy.
- Shared Codex servers are excluded from process correlation. Rollout files
  may be held by a server rather than a terminal client.
- Launch-time tmux options do not track native conversation switching.
- The picker waiting marker represents a deferred launch, not agent input.
- Claude metadata parsing depends on private transcript layouts; the Codex
  request/response client discards unrelated notifications.

The pinned [README](https://github.com/byebyebryan/rofi-agent-plus/blob/42ac16da09627988253bf12d635868bf25998fdf/README.md)
explicitly places shared Codex servers, Claude's background agent view, and
native conversation switches outside its correlation contract. The RLCD feed
must evaluate those cases independently. Neither its private cache nor
WSNav's private database is a proposed integration API.

## Current provider interfaces

### Claude: evaluate the native roster first

Current [agent-view documentation](https://code.claude.com/docs/en/agent-view#list-sessions-as-json)
designates `claude agents --json` as an external state interface. It lists live
interactive sessions and background jobs; `--all` retains completed jobs.
Entries distinguish `kind`, `sessionId`, job `id`, process `status`
(`busy`, `waiting`, `idle`), and `waitingFor`. Background jobs additionally
have `state` (`working`, `blocked`, `done`, `failed`, `stopped`). Fields are
conditional. An absent process can coexist with a retained job. Private job
files are not the supported interface.

The documented supervisor can restart or retire workers without ending the
logical session. Opt-outs can disable agent view. Verify whether JSON listing
works under the actual opt-out, its coverage/version, and whether calling it
starts a supervisor. These are pending behavioral checks, not established
properties of the installed Claude runtime.

This changes the initial hook-first recommendation: evaluate the supported
roster before implementing a custom Claude lifecycle ledger.

### Codex: observe the runtime that owns the session

[App Server documentation](https://learn.chatgpt.com/docs/app-server)
provides stored-thread listing/reading, loaded-thread listing, runtime status,
and status-change notifications. `thread/read` does not load or subscribe to
the thread. A separate helper's `notLoaded` status cannot establish another
TUI's state. For daemon-backed sessions, investigate passive reads from the
owning server. Connectivity, authorization, observation side effects, and
coverage remain unproved.

Installed `codex agents --help` describes a browser for the shared local
server. This establishes a changed native topology to investigate; it does
not establish a machine-readable CLI roster. Do not invent a `--json` option
or resume a thread merely to observe it.

### Hooks and metadata are complementary candidates

[Codex hooks](https://learn.chatgpt.com/docs/hooks) include lifecycle,
permission and interruption events. A Stop hook may trigger continuation;
a permission request may be decided by another hook before a human prompt.
Prove final state and prompt resolution rather than translating each event
directly into a dashboard label. Current docs also require event-specific
passive output, including JSON for successful Stop hooks.

[Claude hooks](https://code.claude.com/docs/en/hooks) expose lifecycle and
permission events, plus `StopFailure` for API errors. Stop does not cover
user interruption. Prompt correlation fields depend on version, and
notifications have timing/coverage limitations. Neither provider's hooks
alone have proved complete waiting or cancellation coverage.

For metadata enrichment, [Claude's session SDK](https://code.claude.com/docs/en/agent-sdk/sessions)
offers session enumeration and exact metadata lookup. Codex's stored-thread
APIs serve a similar purpose. History, file modification times, and CPU usage
do not establish live turn state. A recent-history limit must not hide an
old session that is still running.

## Working design hypothesis

Prefer a supported native runtime snapshot where it accurately describes the
session being observed. Use passive hooks for proven gaps and prompt lifecycle
timing; use process evidence for identity/liveness reconciliation. Keep source
choice per provider and topology. The spike may reject this hypothesis.

Keep these concepts separate:

| Concept | Required distinction |
| --- | --- |
| Logical session | Host + provider + native session ID; a Claude job ID is a separate identifier |
| Runtime | Owning server/worker and its incarnation; a PID can change or be reused |
| Client attachment | Zero, one or multiple terminals can attach; detach is not session exit |
| Work state | Working, needs input, settled, interrupted, error, or unknown |
| Observation health | Current, stale, unavailable, ambiguous, or unsupported |

Foreground process exit and daemon worker exit require different handling.
Duplicate clients must not produce duplicate session rows. A response ending
does not prove task success or the absence of background work. An ordinary
idle prompt differs from a blocking question/approval. A fresh liveness check
must not make an old turn-state observation look fresh.

Retain only bounded identifiers, provider version/topology, project/title,
normalized state/reason codes, source and timestamps. Discard prompt text,
assistant messages, tool arguments/output, and raw provider payloads.
Unknown or conflicting evidence must remain visible as uncertainty.

## Questions the spike must answer

1. Which current native interfaces cover ordinary foreground and daemon
   sessions under the existing compatibility opt-outs?
2. Can observation remain passive, including when no daemon is running?
3. Can waiting for approval/input be entered and cleared promptly, including
   approval of a long-running command and denial of a request?
4. Can session identity survive conversation switches, client detach, worker
   restart, and collector restart without guessing from launch metadata?
5. What coverage requires hooks, and what remains unsupported on each version?

No daemon was started, stopped, or reconfigured for this study. No provider
turns, hook installations, or display changes were performed. The next
deliverable is a versioned coverage/result report from the linked spike plan.
