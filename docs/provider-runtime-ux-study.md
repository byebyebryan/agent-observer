# Codex daemon and Claude Agent View workflow study

Date: 2026-10-02. Scope: normal terminal workflows and their impact on Agent
Plus. This is a documentation, installed-interface and consumer-source study;
it does not establish native UI acceptance or authorize a production migration.

Both providers offer native management that could improve discovery, but the
cost comes from changing the relationship between a conversation and its
terminal. Agent Plus can continue to provide cross-host selection and window
management while providers own execution. Its current process correlation and
fixed conversation-to-pane association would need to evolve.

The providers are not identical: Codex exposes a shared App Server runtime;
Claude's manager supervises separate background-session processes while direct
foreground sessions remain a distinct topology. Enabling Agent View does not
move every ordinary Claude conversation into that supervisor.

Foreground operation remains available in the inspected versions. No retirement
date for it was found in the reviewed sources. Continued compatibility is a
version-by-version obligation rather than a known countdown. Claude has a useful
intermediate option: enable its roster while retaining ordinary foreground
sessions and disabling the shortcut that backgrounds them.

## Evidence and limits

| Subject | Evidence inspected | What it establishes |
| --- | --- | --- |
| Codex on Snap | CLI 0.160.0; package `openai-codex-bin 0.160.0-1`; isolated help; bounded executable strings | Installed flags and entry points; UI labels are static evidence |
| Claude on Snap | CLI 2.1.287; package `claude-code 2.1.287-1`; isolated help; bounded embedded code inspection | Agent View gates, UI preference handling and a live-background resume route |
| Current settings | Selected user configuration and UI preference keys, read without printing other content | Codex `daemon_auto_start=false`; Claude `disableAgentView=true`; no explicit selected Claude UI preferences |
| Agent Plus source | Version 0.12.1, commit `6d30f8c71a9e44ba1da19f4102292f6811df50d8`; clean checkout at inspection | Current discovery, lifecycle and picker assumptions; installed fleet parity was not checked |
| Provider documentation | Official OpenAI and Claude pages retrieved on the study date | Documented behavior, subject to version and rollout differences |
| Earlier Snap preflight | [P1 report](evidence/2026-10-02-p1-snap/REPORT.md) and [capabilities](evidence/2026-10-02-p1-snap/capabilities.json) | Controlled empty Codex reads and isolated empty Claude roster behavior; populated sessions remain unproved |

The new native invocations were eleven version/help queries inside bubblewrap
with private home, temporary storage, PID and network namespaces. Ordinary
configuration, credentials and runtime endpoints were excluded. No prompt,
provider session, turn or native manager was intentionally started. The private
directory was removed afterward. Ordinary configuration was only read.

Bounded [study metadata](evidence/2026-10-02-runtime-ux/observations.json)
records binary identities and static offsets. No credentials, conversation
content, terminal captures, raw protocol payloads or embedded source fragments
are retained there. The preflight reports remain dated evidence; this study
does not advance P1 through its native-session gates.

## What Agent Plus currently manages

Providers already own conversation history and native IDs when their managers
are disabled. The suite supplies terminal persistence and makes those native
conversations discoverable and convenient to open:

| Object | Current owner and meaning |
| --- | --- |
| Saved conversation | Codex or Claude; can exist without a running process |
| Provider runtime | Ordinarily a foreground TUI in a tmux pane |
| Terminal persistence | Tmux Plus; survives closing a viewer or losing its SSH connection |
| Conversation selection | Agent Plus; selects a provider ID on its owning host |
| Viewer window | Tmux Plus and the managed terminal/window integration |

Agent Plus's `Active` means a matching provider process was observed, including
one waiting at its ordinary prompt. It does not mean a turn is working. `Open`
adds fresh viewer evidence on the viewing machine. Its launch-related `Waiting`
is not a native approval/input state. Close targets verified viewer windows and
leaves the tmux session and provider running. These definitions come from the
current [Agent Plus README](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/README.md).

That existing persistence matters: keeping work alive after closing a window is
already part of the tmux workflow. The native-manager benefit is more independent
runtime ownership and better observation, rather than window survival alone.

## Codex mode selection

The word off needs a precise definition:

| Invocation or setting | Meaning in the installed interface | Implication |
| --- | --- | --- |
| `daemon_auto_start=false` | Disables automatic startup; does not stop a running daemon | A compatibility preference, not proof of an embedded runtime |
| `codex --no-daemon` | Explicitly bypasses the shared background server even when it exists | The stronger standalone selection for a future compatibility adapter |
| Daemon auto-start enabled | Allows ordinary startup to use the shared runtime | Actual connection, fallback and package behavior require native proof |
| `codex agents` | Browses sessions on a shared App Server | Installed validation messages require a shared server |
| `codex --remote <endpoint>` | Connects a TUI to an explicitly selected App Server | An explicit client/server topology; not proof of managed-daemon parity |

Installed help and strings establish that `--no-daemon` cannot be combined with
`--remote` or `codex agents`. They also contain embedded-mode fallback messages.
Therefore configuration alone cannot establish what runtime a particular TUI
uses. These are interface/static findings, not a tested fallback sequence.

There is no installed `codex daemon start` or `codex daemon status` subcommand:
their isolated help probes returned parser errors. `codex daemon --help`
displayed the general CLI help, which is not evidence of such a command.
Do not copy Claude's daemon commands into a Codex procedure.

The official [CLI reference](https://learn.chatgpt.com/docs/developer-commands)
describes regular interactive startup and explicit App Server connections.
Connecting a client to a server does not itself mean launching a session list
as the default UI.

## Codex everyday workflow changes

| User operation | Standalone workflow | Shared-runtime workflow and Agent Plus impact |
| --- | --- | --- |
| Start from a project | Open the normal TUI in the terminal | A native TUI can be the client of the shared runtime; entry need not become a dashboard |
| Select a saved conversation | Agent Plus creates or opens the appropriate wrapper; `codex resume <UUID>` is its current launch command | The command still exists; whether it attaches to the exact existing live thread needs proof |
| Find other running work | Use Agent Plus's cross-host process-backed list | `codex agents` adds a provider-local command center; its relationship to standalone sessions needs proof |
| Change conversations inside a terminal | `/new` and `/resume` already make the launched ID stale for Agent Plus | Native management makes such switching more useful, increasing pressure to track the viewed conversation dynamically |
| Close a viewer or lose SSH | tmux retains the TUI | tmux can retain the client; server execution has its own lifetime as well |
| Exit the TUI or change the selected thread | The foreground runtime and view are closely coupled | Treat client departure, turn cancellation, thread unloading and saved history as separate events |
| Copy and scroll | Depends on the renderer and terminal settings | Daemon selection alone does not establish a renderer change |
| Create a worktree task | A separate workflow choice | Installed command-center labels include New worktree; do not equate enabling the daemon with forcing all sessions into worktrees |
| Import another provider's setup | A local TUI can expose `/import` | Official documentation excludes `/import` while connected to the local daemon or a remote server |

The conversation commands and import restriction are documented in the
[CLI reference](https://learn.chatgpt.com/docs/developer-commands). Command-center
labels in 0.160.0 include All, Needs you, New, Resume, Rename, Archive, Filter,
Group and task details. Labels establish shipped UI vocabulary, not successful
interaction or keyboard acceptance.

Codex's [App Server API](https://learn.chatgpt.com/docs/app-server) distinguishes
stored threads, loaded threads and runtime status. It exposes status-change
notifications. Unsubscribing the last client can eventually unload an inactive
thread; a persistent server is not a promise that every thread stays resident
forever. A separate metadata helper cannot establish another server's live
state. The correct runtime owner and observation/subscription behavior must be
proved before adoption.

## Claude mode selection

Claude has three useful configurations to compare, rather than a single binary
choice:

| Configuration | Normal entry | Native roster | Background session use |
| --- | --- | --- | --- |
| Agent View disabled | Ordinary foreground conversation | `agents --json` is blocked | Manager and on-demand supervisor are disabled |
| Agent View enabled with foreground preferences | Ordinary foreground conversation | Available as an observation candidate | Explicit use remains possible; it is not required for each conversation |
| Agent View enabled and actively used | `claude agents`, `--bg`, or an enabled default-view preference | Available | Provider hosts jobs independently of their viewers |

The disabling switch covers the manager, background launch and on-demand
supervisor, as documented in [environment variables](https://code.claude.com/docs/en/env-vars)
and confirmed by the installed gate. It is broader than hiding a screen.

The installed 2.1.287 preference code independently handles
`defaultToAgentsView` and `leftArrowOpensAgents`. Its local fallbacks are false
for default entry and true for the Left shortcut. The arrow dispatch checks
the preference separately. Feature availability and existing sessions'
launch-time preferences were not established by those defaults.

On Snap, neither preference nor `tui` was explicitly present in the selected
global UI preferences. They were also absent from the selected user settings.
With Agent View currently disabled, these absent keys do not establish an
enabled-mode UX or the effective renderer.

A proposed intermediate configuration is:

| Control | Proposed value | Purpose |
| --- | --- | --- |
| User setting `disableAgentView` | false | Permit the native JSON roster and explicit manager use |
| `/config` preference `defaultToAgentsView` | false | Keep bare `claude` opening a regular conversation |
| `/config` preference `leftArrowOpensAgents` | false | Avoid backgrounding through an empty-prompt Left press |

The latter two are UI preferences in the installed code; use the native
`/config` controls rather than assuming they belong in `settings.json`.
These are proposed settings, not changes made by this study. Explicit `/bg`
and native switching would still need handling or a documented boundary.

## Claude everyday workflow changes

| User operation | Agent View off | Enabled with foreground use | Native background use |
| --- | --- | --- | --- |
| Open Claude | Ordinary TUI | Ordinary TUI with default-view preference off | Open the manager or dispatch a job explicitly |
| Navigate from an empty prompt | No Agent View transition | Can preserve this with the Left preference off | Attach/detach is part of the native navigation model |
| Leave a conversation | Exit its foreground TUI; tmux handles viewer persistence | Same foreground model until a native transition | `/exit` detaches; `/stop` stops the background session |
| Fork work | `/fork` retains the forked-subagent meaning | `/fork` changes meaning when Agent View is enabled | Creates a separate background conversation; `/subtask` is the side-worker command |
| Review and copy | Existing renderer choice | Enabling the manager does not itself force fullscreen for direct sessions | Attached background sessions render fullscreen |
| Reopen a running job | Manager access is disabled | Resume can route into native attachment on supported versions | Attach a provider-owned job rather than create its work process in tmux |

The `/fork`, `/subtask`, `/background`, `/exit` and `/stop` distinctions are
documented in [commands](https://code.claude.com/docs/en/commands). They are a
real workflow difference even when default entry and the Left shortcut are
kept unchanged. Background session management is also distinct from subagents,
teams and background shell commands; [the parallel-work overview](https://code.claude.com/docs/en/agents)
separates those concepts.

[Fullscreen documentation](https://code.claude.com/docs/en/fullscreen) states
that attached background sessions use the alternate screen. Native terminal
scrollback and tmux copy mode therefore do not contain the full conversation.
Claude supplies transcript search, in-app scrolling and a transcript-to-scrollback
operation. Mouse capture and clipboard forwarding require acceptance in the
actual Kitty/tmux/SSH combination; documentation about smoother rendering does
not establish measured flicker or copy behavior on this fleet.

### Resume can already become attach

Claude's [session documentation](https://code.claude.com/docs/en/sessions)
dates automatic attachment of a running background conversation to 2.1.285.
At a terminal, ordinary `claude --resume <session>` can open that live job;
redirected I/O, configuration/output/limit flags and disabled Agent View can
prevent this route. `--continue` has different handling. Native `/resume` can
also move the current conversation into the background before attaching another.

Snap has 2.1.287. Its executable contains a live-background resume path that
invokes attach, corroborating the documented route without exercising it.
Agent Plus currently launches exactly `claude --resume <UUID>` in a deferred
tmux wrapper, without extra configuration flags. **Inference:** its command
may already open a running native job when enabled, so a mandatory replacement
of every Claude Resume command is not established. Native acceptance is still
required, especially after detaching into the manager inside that same pane.

### Runtime and repository behavior

The [Agent View guide](https://code.claude.com/docs/en/agent-view) documents one
worker process per background session under a supervisor. An unattached settled
worker may be retired after about an hour; the job remains resumable. Its JSON
roster includes live interactive sessions as well as background jobs, whereas
the interactive manager lists background sessions. Backgrounding an existing
conversation can hand work to a fresh process; some in-flight work requires
confirmation or restart. These are documented cases, not native proofs here.

New background dispatches can enter their own worktrees before edits; backgrounding
an existing foreground session keeps its checkout. The guide also describes
commit/push instructions for provider-created worktrees, subject to the user's
git instructions. This changes where work lands and how results are delivered,
not merely how sessions are listed. Inspect that policy before selecting native
background dispatch as the meaning of Agent Plus New.
See the [Agent View guide](https://code.claude.com/docs/en/agent-view).

[Worktree documentation](https://code.claude.com/docs/en/worktrees) describes
transcript movement with the working directory and worktree retention/cleanup.
Agent Plus must accept changing native cwd and stale or removed worktree paths
without treating either as a new conversation or guessing a replacement path.

## Concrete impact on Agent Plus

The following are source-based implications, not reproduced native failures.

| Surface | Current implementation | Required consideration for native management |
| --- | --- | --- |
| Codex inventory | Short-lived `app-server --stdio`; `thread/list` restricted to `sourceKinds=["cli"]` | Retain saved history; prove source coverage for native-manager-created threads and read live state from the owning server |
| Claude inventory | Parses project transcripts/history; excludes `sdk-cli` entries | Add native roster observations; preserve inactive history; prove native job/transcript coverage and deduplicate by explicit IDs |
| Activity | Reads same-user processes, launch args and open file/task-directory handles | Replace assumptions that one process identifies one conversation; retain ambiguous or unavailable observations explicitly |
| Codex process selection | Explicitly excludes App Servers with non-stdio listen endpoints | Shared runtime threads may lack the evidence this probe needs; enabling the daemon cannot be treated as an observation upgrade by itself |
| Pane association | Exact tmux provider option first, otherwise provider process ancestry | A server or supervised worker need not descend from the viewing pane; join a validated client attachment to the conversation separately |
| Resume one row | Focus a verified wrapper, otherwise create a deferred native UUID resume wrapper | Choose focus, live attach or history resume using current topology; prove Claude's automatic route and Codex's live-thread behavior |
| Close one row | Close verified viewer windows, leaving provider/tmux alive | Keep this meaning; do not map Close to a native stop or deletion command |
| New here | Fresh target-host/cwd/tool validation, then bare `codex` or `claude` | Native default-view preferences could open a manager; background dispatch could change cwd/worktree policy; retain an explicit creation meaning |
| Batch Resume | Opens existing tmux references; never creates providers | Jobs without wrappers are currently outside this batch; creating attachment clients would be a separate change to its contract |
| Batch Close and Open | Require activity plus fresh viewer evidence and stricter operation handles | Preserve viewer validation while separating worker liveness from whether a window is open |
| In-terminal switching | Does not update the managed launch identity | Track the currently viewed native ID or invalidate the association before actions |
| Remote hosts | Uses Host Mesh routing and host-local provider tools | Discover the runtime on its owning host; version/config-root differences must not silently change action semantics |

These mechanisms were inspected in
[engine.py](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/rofi_agent_plus/engine.py),
[contract_backend.py](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/rofi_agent_plus/contract_backend.py),
[claude_probe.py](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/rofi_agent_plus/claude_probe.py)
and [contract_lifecycle.py](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/rofi_agent_plus/contract_lifecycle.py).

### Failure sequences to test

1. Open conversation A through Agent Plus, then switch to B natively in the
   same pane. The original provider option and viewer identity still describe
   A. Exact launch-option validation alone cannot prove which conversation is
   now on screen; Resume or Close can target the wrong association.
2. Background a Claude conversation. Its runtime can move away from the pane
   ancestry that Agent Plus uses. A surviving job may still need input after
   its worker exits, so absence of a matched process cannot establish that the
   job ended or that observation is healthy.
3. Resume a native Claude job through the existing wrapper. The resume may
   attach correctly, but `/exit` can return to the provider manager in that
   pane. A subsequent selection could display another conversation while the
   wrapper still carries the original UUID.
4. Start several Codex threads in one server. The current probe excludes that
   server, and one client's handles are not a complete server roster. A fresh
   metadata helper can list saved sessions without establishing live work.
5. Change the viewing machine. A live native job can have no tmux wrapper to
   open. Existing batch Resume excludes that case; a native attachment client
   must be created only through a separately authorized action path.

## Sustainability of keeping both managers disabled

There is present-day evidence for keeping foreground workflows: Codex ships
`--no-daemon`, and Claude still exposes ordinary interactive startup and a
documented Agent View disabling switch. Neither reviewed interface establishes
a planned removal date. Claude Agent View is still described as a research
preview in the [parallel-work overview](https://code.claude.com/docs/en/agents).

The maintenance burden is already visible in Agent Plus source:

- Codex identity depends on open rollout handles and source classification.
- Claude identity needs launch arguments, transcript handles, and a task-directory
  fallback when fresh TUIs close their transcript between writes.
- Local and remote activity probes carry parallel implementations of those rules.
- A fixed tmux option cannot follow native conversation switching, even with
  both managers disabled.

**Inference:** new persistence formats, worker reuse, native navigation and
default routing can increase repair work even if foreground mode stays
supported. There is no basis here for estimating a number of months or claiming
foreground operation is about to stop working.

Adopting native management trades some of that heuristic maintenance for API,
capability, runtime-discovery and reconnect maintenance. It also adds shared
runtime failure and update cases. Supported native interfaces are promising
sources, but enabling a manager alone does not remove the integration work.

## Adoption choices

| Direction | Everyday experience | Agent Plus work | Assessment |
| --- | --- | --- | --- |
| Continue current foreground model | Familiar window/tmux workflow | Maintain correlation, enforce actual Codex topology and document native-switch limits | Viable near term; continuing maintenance obligation |
| Enable Claude roster while retaining foreground use | Small visible change if entry and Left preferences are preserved; `/fork` still changes | Prove roster passivity and identity, then add observations without changing actions | Best first experiment |
| Adopt native runtimes while retaining separate Agent Plus viewers | Native work can outlive clients; background Claude attachment uses fullscreen | Topology-aware observation, exact attachment identity, resume/attach handling and revised batch eligibility | Promising long-term direction; larger migration |
| Replace the picker with a dedicated session client | Persistent session list beside the provider view | Additional presentation, switching, recovery and ownership work | Separate product choice; not required by this study |

The earlier [Agent Plus session-client study](https://github.com/byebyebryan/rofi-agent-plus/blob/6d30f8c71a9e44ba1da19f4102292f6811df50d8/docs/agent-plus-session-client-exploration.md)
keeps Kitty conditional and records a validate-before-detach requirement.
Those presentation results do not establish daemon compatibility. Native
management does not require adopting a new terminal client at the same time.

## Recommended proof and migration order

First establish the enabled-mode UX and native identity in isolated disposable
sessions. Then improve observation. Change Agent Plus actions only after those
observations and the action route are independently accepted. Providers retain
runtime ownership; Agent Observer reports metadata/state; Agent Plus retains
host routing, action validation and viewer policy.

| Proof | Acceptance question | Current status |
| --- | --- | --- |
| Codex standalone against an existing disposable daemon | Does `--no-daemon` isolate the TUI, and what does startup-disabled mode actually select? | Interface/static evidence only |
| Codex normal shared TUI and `codex agents` | Is normal entry familiar; which navigation exits/detaches/interrupts; does resuming reach the same live thread? | Native UI not run |
| Codex identity and API observation | Map saved/logical IDs, loaded threads and clients; prove passive reads/notifications, approval/input state and disconnect lifetime | Schema/empty reads only |
| Claude enabled foreground use | Preserve direct entry and Left behavior; verify `/fork` semantics, roster identity and no observation-triggered work | Preferences/static and empty roster only |
| Claude background and existing Resume wrapper | Prove 2.1.287 resume-to-attach, native detachment, job UUID mapping and the effect on tmux/viewer association | Documented/static route only |
| Viewer and terminal behavior | Test real Kitty/tmux copy, scroll, mouse, approvals, cancellation and reconnect; Close must preserve work | Native managed-session acceptance pending |
| Job recovery and cwd | Worker retirement/restart, manager restart, sleep/SSH gaps, worktree movement and missing history | Native proof pending |
| Agent Plus integration | Unattended jobs, multiple clients, native switches, Active/Open counts and exact single/batch action targets | Source implications only |
| Ordinary integrations | Verify hooks/plugins and launch configuration reach the intended runtime, including shared Claude-Mem behavior | Not tested by isolated help or empty proofs |

No fleet-wide flag flip follows from this study. The first comparison should
be Claude's foreground-compatible roster path and Codex's explicit standalone
versus actual shared-runtime behavior. A future decision to adopt native
management should preserve the normal provider UI while making Agent Plus's
conversation, runtime and viewer identities explicit.
