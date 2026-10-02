# P1 Starship read-only preflight

Date: 2026-10-02. Host: `starship`, current workspace host, UID 1000.
Inspection window: 22:22:21–22:39:06 UTC.
[Capability evidence](capabilities.json), [spike plan](../../agent-session-spike-plan.md),
and [roadmap](../../roadmap.md).

## Outcome and evidence boundary

The current-host read-only report is complete. P1 remains active: native
observation passivity and launch isolation still need proof, and Claude's
runtime on Snap has not been inspected. P2–P5 have not run. Source selection,
the public observation schema, implementation language, and collector design
remain provisional.

This report contains installed CLI/help evidence, generated static schema,
selected configuration metadata, a disposable configuration-selection probe,
and host process/socket observations. It contains no native work-state reads,
hook delivery, provider turns, controlled-server runs, or synthetic transition
tests. Configuration selection does not establish daemon endpoint isolation.

| Provider/topology | Installed capability evidence | Current host observation | Native state/transition coverage |
| --- | --- | --- | --- |
| Codex foreground, 0.160.0 | Version, help, selected features and schema inspected | Five terminal-attached Codex processes; logical IDs unbound | `not_run` |
| Codex daemon-backed, 0.160.0 | Server/daemon tooling and schema present | No owning daemon detected by inspected signatures | `not_run`; namespace isolation pending |
| Claude foreground | `unavailable`: no executable found in bounded search | No Claude process detected | `not_run` |
| Claude supervised | `unavailable`: no executable/version established | No supervisor detected | `not_run`; isolation pending |

No row establishes live waiting, cancellation, recovery, or daemon support.
An unavailable provider remains unavailable; process presence supplies no idle
or settled state. Other hosts were not inspected.

Follow-up target clarification: the user reports that Claude is available only
on Snap. Its absence on Starship is therefore expected and is not evidence of
unsupported Claude capabilities. Snap's version, settings, topology and native
interfaces remain unverified; the table retains the Starship inspection results.

## Installed capabilities and configuration

`/usr/bin/codex` resolves to `/opt/openai-codex/bin/codex` and reports
`codex-cli 0.160.0`. Profile-free `features list` reports `hooks stable true`
and `daemon_auto_start stable false`. The default user config and the canonical
chezmoi template contain those values. No additional system/project layer was
found in the selected checks. Current configuration is not a measurement of
each existing process's launch-time effective settings.

Installed help explicitly describes `--no-daemon` as avoiding the shared
background server even when it exists. The auto-start feature value alone is
not topology proof. `--remote` accepts explicit WebSocket and Unix endpoints;
`app-server --listen` accepts a custom Unix endpoint. `codex agents` is an
interactive shared-daemon browser; no machine-readable roster option was
established. Only its help was invoked.

The ordinary `~/.codex/hooks.json` contains one `Stop` event entry. A reference
`wsnav-observer.config.toml` profile contains one entry each for
`SessionStart`, `UserPromptSubmit`, `Stop`, and `SessionEnd`. None of the five
observed Codex processes carried an explicit profile selection or a
`CODEX_HOME` override.
These counts prove configuration presence only; hook command contents and
delivery were not captured or exercised.

A temporary `CODEX_HOME` and disposable working directory, containing only
`hooks=false` and `daemon_auto_start=false`, produced those two effective
values from `features list`, with exit code 0. The temporary directory was
removed. Stderr was present and discarded. This is a configuration-selection
probe, not a session launch or daemon isolation test.

An authentication file is present; no credential content was read. No OpenAI
API key was inherited by the inspection process. Authentication validity,
account access, and account-gated features were not tested.

Claude was absent from PATH and the targeted install locations recorded in
the JSON. Its user settings file remains present, but contains no
`disableAgentView` key or hook entries. The relevant inherited opt-out and
config-directory variables were unset. No managed/workspace settings were
found in the selected checks. This does not establish the effective opt-out
of a Claude installation on another host. No Claude command was executed.

## Static schema and identity gaps

The installed generator was run with a disposable home/cwd and no credentials
copied into that home. Its stable schema was extracted in two passes; generated
files were removed. Both invocations exited 0. Stderr was discarded.
Installed help and the matching release's
[CLI routing](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/cli/src/main.rs#L1328)
established the protocol-generation branch before execution. Release source is
a reference, not an attestation of the installed binary.

The generated schema exposes `notLoaded`, `idle`, `systemError`, and `active`,
with `waitingOnApproval` and `waitingOnUserInput` active flags.
`ThreadReadParams` contains `threadId` and optional `includeTurns`.
Loaded-thread listing is paginated (`cursor`, `limit`, `nextCursor`);
status-change notifications contain `threadId` and `status`.

The thread schema includes both `id` and `sessionId`; their relationship and
stability across native switches remain unproved. Source kinds include `cli`,
`vscode`, `appServer`, `exec`, subagent kinds, and `unknown`. Inclusion policy
must follow native-session evidence rather than importing a CLI-only filter.
`preview` and `turns` occur in responses and must be discarded at the receiver
boundary; selecting `includeTurns=false` does not make an unfiltered response
safe to retain.

Current [App Server documentation](https://learn.chatgpt.com/docs/app-server)
describes `thread/read` as avoiding load/subscription and loaded-thread listing
as server-local. Those semantics are still native proof targets for 0.160.0.
A metadata helper's state cannot describe another runtime's live work.

## Runtime and preservation evidence

Five Codex executable processes had terminal descriptors and distinct process
birth identities. Their running executable hashes matched the installed binary
when checked. The inspection did not bind any native conversation UUID or
derive a session count, work state, or completion state from those processes.

The daemon and updater PID records refer to absent PIDs. An updater socket
exists on disk but has no matching entry in the kernel Unix-socket table.
No owning app-server/managed-daemon process was detected. No provider-named
unit files were found in the inspected user-unit directories; the service
manager was not queried. The JSON records visibility limits, including two
unreadable same-user executable links whose status names were `systemd` and
`(sd-pam)`. This is a bounded census, not a claim about all possible launchers.

The monitored config, hook, settings, and PID-file hashes were identical
between 22:26:06 and 22:38:09 UTC. Ordinary executable process identities and
boot identity were unchanged; no daemon socket appeared in either snapshot.
Profile/template hashes were collected later and are not part of that
comparison. Session/server launches, ordinary configuration mutations,
service actions, and native roster reads performed by this preflight: zero.

## Procedures for the next experiments

These are preparation procedures with explicit gates. They have not been run
as native experiments. Operator-created disposable sessions are test setup;
the observer itself must never create, resume, approve, or interrupt sessions.

### Codex foreground

1. Create a private temporary directory containing an empty working directory
   and explicit Codex home. Review applicable system/project layers and use a
   minimal config; keep ordinary hooks and configuration intact. Repeat the
   selected-feature probe and record the new process/config baseline.
2. Establish transient authentication outside repository evidence if a native
   turn is required. Do not copy ordinary history, hook commands, or profiles.
3. An operator launches a new native TUI with explicit `--no-daemon`, the
   disposable home/cwd, and native trust/configuration flows. Do not supply an
   ordinary session ID. Verify terminal attachment and process birth identity.
4. Before adding a study hook, establish event-specific passive output on this
   version, a bounded handoff and failure behavior that cannot alter or stall
   provider work. Retain only allowlisted IDs, event/reason codes and times.
   Hook ancestry is supporting evidence, not action authority.
5. Compare native visible states against captured evidence under the spike
   cases. Recover unknown state explicitly after gaps; keep state and presence
   timestamps separate. Clean up only run-owned processes/files and compare
   the monitored ordinary baseline again.

### Codex controlled App Server

1. Prepare a separate private home/cwd and explicit new `unix://PATH` endpoint
   inside the run directory. Establish endpoint ownership, applicable config
   layers, and credential handling before launch. Avoid the default endpoint.
2. A future operator-run experiment launches plain `app-server` at that
   endpoint, without managed-daemon mode. Attach a disposable native TUI using
   the installed explicit remote endpoint form; verify it reaches that server.
3. The observer uses only initialization and candidate reads such as
   `thread/loaded/list` and `thread/read` with `includeTurns=false`, on the
   owning server. Follow pagination. Filter received data in memory before any
   output, with bounded buffers/timeouts and no raw response or terminal logs.
4. Prove that connection/read/disconnection does not load or subscribe to a
   thread or affect worker lifetime. The observer must not call start, resume,
   fork, turn-start, unsubscribe, or session-control methods. Compare native
   UI state and loaded/runtime evidence before and after reads.
5. Apply the spike's transition/identity cases and cleanup comparisons. Label
   every result `controlled-server`; it cannot establish managed-daemon support.

### Codex managed daemon

No launch/read procedure is accepted yet. There is no detected owning runtime
to inspect here, and custom controlled-server transport does not prove managed
namespace/package/updater isolation. Establish the version-specific namespace,
startup and authorization path before any daemon start/proxy operation. If it
cannot be isolated, keep this row pending. Do not bootstrap, stop, update, or
reconfigure the ordinary daemon environment.

### Claude

Inspect the executable, version and effective opt-out on Snap first; its role
as the sole Claude host is user-reported and has not been verified remotely.
Verify installed command routing before diagnostics. Current
[agent-view documentation](https://code.claude.com/docs/en/agent-view)
describes `agents --json`, a separate supervisor instance under
`CLAUDE_CONFIG_DIR`, and opt-outs through `disableAgentView` or its environment
variable. Opening agent view starts its supervisor. These are documentation
candidates, not installed capability or passivity proof. Confirm namespace
isolation and read side effects before invoking a roster or live experiment.
Keep job IDs, conversation UUIDs, worker lifetimes and client attachments separate.

## Next gate

Close P1's remaining native passivity/isolation prerequisites, inspect the
Claude runtime on Snap, and then begin the smallest P2 comparison on safely
available topologies. Keep unavailable/not-run rows explicit. Production
hooks, consumer integration, provider policy changes and deployment remain
outside this evidence slice.
