# P1 Snap capability and bounded empty-state evidence

Date: 2026-10-02. Host: `snap` (`80H1VV3`), UID 1000.
Main preservation window: 23:05:28–23:27:32 UTC.
[Machine-readable capability evidence](capabilities.json), [spike plan](../../agent-session-spike-plan.md),
[roadmap](../../roadmap.md), and the dated
[Starship report](../2026-10-02-p1-starship/REPORT.md).

## Outcome and evidence boundary

This completes a bounded Snap P1 slice, not P1 as a whole. It establishes the
installed Codex and Claude versions and selected opt-outs, Codex static schema,
an empty-store controlled Codex App Server read, and Claude Agent View behavior
inside a disposable namespace. Loaded native sessions, active work, workers,
transitions, identity and recovery remain unproved. The source, public contract,
implementation language, and collector design remain provisional.

Evidence labels used here are `static_schema`, `embedded-static`,
`controlled-empty`, `isolated-native-empty`, and `not_run`. No credentials,
conversation content, hook commands, response bodies, terminal captures, or raw
provider payloads were retained. A passing empty-state probe does not establish
behavior for ordinary sessions or managed runtimes.

| Provider and topology | Installed version | Evidence and result | Remaining coverage |
| --- | --- | --- | --- |
| Codex foreground | 0.160.0 | Installed CLI/config and host process census passed | Native roster, work state, hook delivery: `not_run` |
| Codex custom App Server | 0.160.0 | `controlled-empty`: initialize, empty lists, missing-ID read, reconnect passed | Loaded session/worker and native UI comparison: `not_run` |
| Codex managed daemon | 0.160.0 | Unit inspected; no managed-daemon proof | Namespace, start/lifetime, reads: `not_run` |
| Claude ordinary foreground | 2.1.287 | Current user opt-out established; ordinary roster call: `not_run` | Ordinary session/worker state: `not_run` |
| Claude isolated CLI namespace | 2.1.287 | `isolated-native-empty`: enabled empty roster and both opt-outs passed | Populated roster, job/worker state and transitions: `not_run` |
| Claude supervised worker | 2.1.287 | `embedded-static` dispatch/root trace only | Native supervisor and worker state: `not_run` |

Process counts below are not logical session counts. No row establishes that
an unavailable or unobserved session is idle or complete.

## Installed versions and selected configuration

Snap has `openai-codex-bin 0.160.0-1`: `/usr/bin/codex` resolves to
`/opt/openai-codex/bin/codex`, and the CLI reports `codex-cli 0.160.0`.
`claude-code 2.1.287-1` provides `/usr/bin/claude`, a POSIX shell wrapper that
sets `DISABLE_UPDATES=1` and `DISABLE_INSTALLATION_CHECKS=1`, then execs
`/opt/claude-code/bin/claude` with the original arguments; the CLI reports
`2.1.287`. These package and running-binary identities were checked during the
bounded census.

Profile-free `codex features list` exited 0 and reported `hooks=true` and
`daemon_auto_start=false` from `/home/bryan/.codex/config.toml`. The observer
checkout has no `.codex/config.toml`; the relevant shell `CODEX_HOME` and
`CODEX_PROFILE` overrides were unset. This does not establish every existing
process's launch-time settings. The Codex root `hooks` key is present with no
direct root event entries, and legacy `notify` is configured. The ordinary
`~/.codex/hooks.json` file is absent. Cached hook state has 10 reference keys:
five user hooks-file references and five Claude-Mem plugin references. Plugin
source loading and delivery were not inspected. These are configuration
presence counts only; hook delivery was `not_run`.

The ordinary Claude user settings at `/home/bryan/.claude/settings.json` set
`disableAgentView=true`; `CLAUDE_CONFIG_DIR` and
`CLAUDE_CODE_DISABLE_AGENT_VIEW` were unset in the inspection shell. The
bounded settings check found no observer-project or managed settings file.
The user `PreToolUse` hook event count is 1; command contents and delivery were
not inspected. The wrapper's update/install-check variables are separate from
this user Agent View opt-out. Ordinary user settings and global Claude
preferences remained unchanged during the isolated probes.

## Codex static schema and controlled server

The installed 0.160.0 schema generator ran in a private home, SQLite home,
working directory and output directory, with no credentials copied. It exited
0 (`static_schema`). The selected schema includes `ThreadReadParams` with
required `threadId`, `ThreadListParams`, `ThreadLoadedListParams`,
`ThreadLoadedListResponse` with required `data`, `ThreadReadResponse` with
required `thread`, `ThreadStatusChangedNotification` with required `status`
and `threadId`, and `InitializeParams` with required `clientInfo`. Static
status values include `notLoaded`, `idle`, `systemError`, and `active`; active
flags include `waitingOnApproval` and `waitingOnUserInput`. The schema also
contains fields such as `preview` and `turns`; a future receiver must filter
bounded metadata before retaining or emitting provider responses. Schema
presence says nothing about live identity or state semantics.

Both `Thread.id` and `Thread.sessionId` are required in the generated schema;
their relationship across native switches remains unproved. Source kinds
include CLI, VSCode, App Server, exec and subagent variants. The roster's
inclusion policy is still open. Loaded-list pagination fields are present;
the empty-store probe did not exercise multiple pages.

The credential-free plain App Server used isolated Codex and SQLite homes, a
private working directory and a custom Unix endpoint. No ordinary-server
connection or session/turn creation call occurred. Three startup-only attempts
stopped before protocol handshake because the ownership check compared the
requested path lexically. The requested endpoint is a symlink to a hashed path
under `/tmp/codex-daemon-UID`; resolving that alias allowed the fourth attempt
to prove the server-owned file descriptor matched the kernel socket inode. The
socket mode was `0600`.
On this version, the resolved filename is the SHA-256 of the requested endpoint
path string: `/tmp/codex-daemon-<uid>/<sha256>`. Its persistent lock is the same
path with `.lock` appended. This observed custom-listener mapping does not prove
the managed daemon's isolation or lifetime.

The successful `controlled-empty` sequence initialized, read
`thread/loaded/list` and `thread/list` as empty, attempted `thread/read` for a
missing ID (error `-32600`), disconnected, then reconnected and observed the
loaded list still empty. Both connections completed handshakes and the server
incarnation survived disconnect/reconnect. No session files were present. All
experiment processes exited; run-owned symlinks, sockets and exact lock files
were removed, and the shared parent directory was preserved. The failed
startup-only attempts are instrumentation failures before handshake, not
provider failures. This proves transport and empty-store reads only.

## Claude Agent View static trace and isolated CLI probes

Installed help (exit 0) exposes `claude agents --json`. The bounded
`embedded-static` trace of the installed 2.1.287 binary shows the JSON route
checking `CLAUDE_CODE_DISABLE_AGENT_VIEW` and `settings.disableAgentView`
before calling the JSON renderer. With Agent View enabled, the renderer scans
process records and background-job state, and connects to the selected
supervisor control socket; the inspected JSON route contains no explicit
supervisor start/ensure call. A failed connect returns through the inspected
client path. This is static code evidence, not proof about all startup paths.
Settings/feature initialization occurs before the opt-out check. That
initializer was not fully traced; the native probes below suppressed
nonessential traffic and used an isolated network namespace.

The selected config root is `CLAUDE_CONFIG_DIR` when set before process start,
otherwise normalized `$HOME/.claude`. The traced session-record, job fallback,
and daemon-roster paths are under that root. The control socket is derived from
the absolute root under `/tmp/cc-daemon-<uid>/`. The preferences fallback also
uses the selected config root or home. An injected storage handle used by the
job scan was not fully traced. The installed binary identity and bounded
dispatch/root offsets are recorded in `capabilities.json`; no code fragments
are retained.

The process-record scan has a fire-and-forget stale-record cleanup branch.
Consequently, the roster command is not strictly filesystem-read-only. This
housekeeping is distinct from deleting a provider logical session or changing
its work state; neither effect was established by the static trace.

Five CLI queries ran in bubblewrap with private home and `/tmp`, PID and network
namespaces, ordinary home/runtime excluded, and `/usr` plus the provider
installation read-only. No credentials were copied; nonessential traffic was
disabled. The namespace setup check saw only PIDs 1 and 2 and could not see the
ordinary settings.

The launcher used `bwrap --unshare-all --die-with-parent --new-session`,
read-only binds for `/usr` and `/opt/claude-code`, a private home bind and
tmpfs `/tmp`, private `/proc` and `/dev`, and an empty `/etc`. The child
environment contained only launch essentials and explicit test configuration,
including `CLAUDE_CONFIG_DIR` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`.
The original home, runtime sockets and authentication files were not mounted.
Results:

| Scenario | Result |
| --- | --- |
| Enabled `agents --json` with an empty config root | Exit 0; empty JSON array; zero records |
| User-settings opt-out | Exit 1; disabled marker observed |
| Environment opt-out | Exit 1; disabled marker observed |

The first settings and environment opt-out attempts returned exit 1 with
non-JSON output that a narrow classifier did not recognize. Only those two
cases were repeated with a corrected classifier; both confirmed the disabled
reason. They are not provider failures. Each of the three final calls created
`.claude.json` and a backup in its private config root, including the blocked
calls. Thus even the opt-out roster path is not filesystem-read-only. No
ordinary roster was queried. No child provider process or control socket was
observed after the calls; 20 ms process sampling cannot rule out a shorter-lived
child. The empty result proves no populated roster or supervised-worker
semantics.

## Host topology and preservation

The baseline at 23:05:28 UTC and final census at 23:27:32 UTC each recorded
four terminal-attached Codex processes, two terminal-attached Claude
processes, and four Codex code-mode helpers. Native identities were unbound;
these process counts must not be read as session counts or work states. The
same-UID bounded census found no provider-namespace-named socket rows in either
snapshot. That does not rule out every possible launcher or endpoint.

The existing user `codex-app-server.service` is a plain App Server unit, not a
managed-daemon acceptance result. It is unmanaged by chezmoi and unowned by
pacman, and remained `inactive/dead/disabled` with `MainPID=0`. Across the
baseline and final census, ordinary provider/helper process birth identities,
selected configuration hashes and boot identity were unchanged; no ordinary
identities were added or removed. The global Claude preference hash has a
separate baseline at 23:20:16 UTC and was rechecked after the namespace probes;
it was unchanged. The selected file hashes, process birth identities and binary
comparisons are retained in `capabilities.json`. All
run-owned endpoint artifacts were cleaned. This is a bounded preservation
comparison, not proof about uninspected system policy or every launch path.

## Remaining P1 gates and next bounded procedures

Still `not_run`: native Codex foreground passive observation and hook delivery;
Codex reads against a loaded native session/worker with native UI comparison;
managed-daemon namespace/lifetime; populated Claude roster and worker/job
state; native transition, identity and recovery cases; and ordinary supervisor
interaction. Authentication and account-gated behavior were not tested. No
observer-created session or turn was used.

For a next Codex read proof, keep `CODEX_HOME`, `CODEX_SQLITE_HOME`, cwd and the
custom endpoint private. Resolve the requested Unix path before ownership
checks, confirm the hash mapping and that neither the resolved socket nor its
lock preexists, prove the owned file descriptor and kernel inode, and remove
only the run-owned socket, symlink and exact lock entries. Use a minimal
disposable config with `hooks=false` and `daemon_auto_start=false`, and launch
plain `codex app-server --listen unix://<absolute-run-socket>`. The Unix
transport requires a WebSocket handshake. Limit observer calls to initialization
and the proven read candidates; filter responses in memory. Compare a separate,
operator-created disposable native session only if that is needed and safely
available; never use an ordinary session. A custom-server result remains
separate from managed-daemon support.

For a next Claude proof, preserve the bubblewrap boundary: private home/config
root and `/tmp`, PID/network namespaces, ordinary home/runtime absent, and
read-only provider installation. Set the config root before process launch;
verify ordinary settings/runtime are absent before `claude agents --json`,
and compare only files and processes inside the disposable namespace. The
network-isolated fixture cannot establish authenticated native turns; any
later setup needing network/authentication requires a new isolation check.
A populated worker/job fixture would be a separate test. If it cannot be isolated, leave
it `not_run` or `unavailable` rather than querying ordinary rosters. Once the
remaining topology and passive-read gates are closed or explicitly unavailable,
proceed to P2's minimal source comparison. P1 remains active meanwhile.

## References

Current [Codex App Server documentation](https://learn.chatgpt.com/docs/app-server),
[Codex environment-variable documentation](https://learn.chatgpt.com/docs/config-file/environment-variables),
and [Claude Agent View documentation](https://code.claude.com/docs/en/agent-view)
are references only; installed probes above establish the Snap evidence.
