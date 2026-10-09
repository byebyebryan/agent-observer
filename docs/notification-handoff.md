# Agent notification client request

The user clarified on 2026-10-09 that this ESP32-349 handoff is **requirements
input from one client, not a settled Observer contract**. Other clients may need
different event evidence, child policies, formatting or transports. The reviewed
[state/event design](state-and-events-design.md) separates reusable native facts
from these requested alert behaviors; its
[execution gates](state-and-events-execution-plan.md) leave production and
client delivery independently pending. Nothing in this note installs hooks or
selects an alert client.

The subsequent [experimental source/client contract](notification-client-contract.md)
and [a4 native report](evidence/2026-10-06-notifications/REPORT.md) implement the
bounded source/formatting checkpoint. Normal hook selection, originating terminal
routing, graphical Open and 349 physical mirroring remain separate. The original
request and managed ownership below are retained.

Date: 2026-10-05. Status: user-requested follow-up for later implementation;
this note does not implement or select a new notification client.

## Requested behavior

For the requested desktop/349 client, standardize notifications from Codex and
Claude Code:

| Field | Content |
| --- | --- |
| Sender / application name | `Codex` or `Claude`, rather than `kitty` |
| Title | The current session name/title |
| Message | A short state message, such as `Turn complete`, `Waiting for input`, or `Permission needed` |

The user cares most about sender and session title. Start with static state
messages; response summaries are optional future work. Keep top-level
notifications and suppress child/subagent completions. Unknown Codex child
classification currently fails open in that client; do not silently change its
migration policy. Shared core events preserve child and unknown evidence instead
of applying this suppression.

Kitty is the only supported terminal for this requested alert client. Ghostty is deprecated;
no OSC 777 fallback, compatibility layer, or Ghostty action bridge is required.
Preserve unfocused-only delivery and Kitty's native Open/focus behavior,
including the originating pane when running under tmux.

## Ownership

Reusable provider event handling can live in the Agent Observer repository.
Core owns passive event normalization; the local service hosts sources, bounded
intake and read publication. Desktop publication, notification policy and
formatting belong in a separate client. Merely reading Observer must not emit
notifications or perform provider actions. The implementation gate is separate
from this client's requested sender/title/Open behavior.

ESP32-349 remains downstream: its `notification-panel` mirrors desktop
notifications from all applications, displays cards and handles device
interactions. It should not acquire its own Codex/Claude hook logic, session
title lookup, or duplicate provider-state implementation. Improved desktop
notifications should reach it through the existing desktop notification path.

Chezmoi owns installed provider settings and helper/hook wiring. Update managed
sources, apply narrowly and verify source/installed/live behavior separately.
Do not install hooks or replace the current notification path solely because
this design has been recorded.

## Current configuration cleanup

The ESP32 discussion separately authorizes only these managed cleanup changes:

- Claude: set `.claude.json`'s exact key `preferredNotifChannel` to `kitty`,
  preserving other local preferences and hooks.
- Codex: retain `notify = ["/home/bryan/.local/bin/codex-notify"]`; make the
  existing helper Kitty-only and remove its OSC 777 fallback.
- Retain `tui.notifications = ["approval-requested"]` and
  `tui.notification_method = "osc9"`. Completion notifications already use
  the helper; enabling built-in completions as well would duplicate them.

Canonical sources are in `/home/bryan/.local/share/chezmoi`:
`modify_private_dot_claude.json`,
`dot_local/bin/executable_codex-notify`, and
`.chezmoitemplates/codex-portable-config.toml.tmpl`.
`scripts/check-codex-notify` validates the helper without desktop side effects.
This cleanup does not implement the requested sender/session-title format.

## Handoff review

Reviewed on 2026-10-05 against the managed source and the primary references
below. The managed Codex helper is already Kitty-only, leaves the application
name unset, and uses `Codex` as its title. The managed Claude template sets
`preferredNotifChannel` to `kitty`; the Codex template retains the external
completion helper and approval-only built-in notifications. These are source
checks, not proof of installed settings or desktop delivery on either host.

The documented hook fields and OSC 99 application metadata support the proposed
investigation. They do not establish current native event coverage, display-name
precedence, duplicate handling or tmux/desktop Open acceptance. Keep those gates
in the separate notification-client pass. The cleanup authorization above is
context from the originating discussion, not an instruction for an Observer
repair loop to apply managed configuration changes.

## Findings to retain for implementation

- Observer's [v2 watch contract](public-contract-v2.md#sampled-watch) emits
  sampled state updates, gaps and resynchronization. It does not promise
  lossless native turn-completion events. Native notifications and hook
  wakeups need their own source/correlation proof; do not reconstruct every
  completion by diffing snapshots. See the
  [source-event plan](contract-and-clients-plan.md#push-monitoring-and-source-events).
- Claude's `Notification` hook suits existing attention/idle/permission
  notifications. Its optional `title` is the alert caption, not the session
  name. The shared design enriches from Observer's exact-reference cache,
  preserving unavailable titles explicitly. Earlier private transcript findings
  below are source-investigation context, not a request for clients to perform
  their own provider lookups. A `Stop` hook is not required just to supply a title.
- `Stop` provides immediate response-end evidence and `last_assistant_message`,
  but other parallel Stop hooks can continue work. Snap has review/loop Stop
  hooks. Do not equate one Stop callback with successful task completion or
  let a child Stop settle the parent.
- Claude transcript metadata inspected locally includes `custom-title`,
  `ai-title` and `agent-name`. This is internal storage, not a guaranteed title
  API. Prove current native display-name precedence and use bounded reads with
  an exact-ID fallback; never identify a session from title, cwd or PID.
- Claude's hook JSON output field `terminalSequence` can send supported OSC
  sequences through its interactive terminal writer. It is an output transport,
  not a session-title field or event source. Native notifications still need
  an explicit duplicate policy if custom hook notifications replace them.
- Kitty OSC 99's base64 `f` metadata supplies the application name independently
  of title/body. The inspected Kitty backend retains its native default action
  and originating-terminal association when a custom app name is supplied.
  Sanitize and bound metadata; preserve control-character and tmux guards.
- The current Codex helper reads `threads.source` from local `state_*.sqlite`
  read-only to suppress children. Verify the owning runtime's actual configured
  SQLite location and native ID mapping before migration; do not assume that
  every store lives directly under `CODEX_HOME`.
- DMS displays `appName`. ESP32's Open bridge validates raw app name, summary
  and body against the live DMS notification. Preserve those raw fields and
  test that custom `Codex`/`Claude` sender labels retain Open. Review terminal
  body classification, which currently recognizes terminal application names.

## Separate implementation and acceptance pass

Resolve event coverage and notification-client integration with the current
Observer work before selecting a source. Use exact provider/host/namespace/session
identity; retain source gaps and uncertainty. Keep prompts, responses and raw
hook payloads out of Observer's metadata contract and repository evidence.

Validate both providers with concurrent sessions, renamed/missing titles,
child completions, permission/input waits, Stop continuation, reconnect/restart,
duplicate delivery and bounded failure behavior. Then prove Kitty focus policy,
tmux pane routing and desktop Open independently from source/synthetic tests.
ESP32 desktop mirroring and physical Open remain a separate downstream check.

## Primary references

- [Claude hook reference](https://code.claude.com/docs/en/hooks)
- [Claude terminal notifications](https://code.claude.com/docs/en/hooks#emit-terminal-notifications)
- [Codex notification settings](https://learn.chatgpt.com/docs/config-file/config-advanced#notify-vs-tuinotifications)
- [Kitty desktop notification protocol](https://sw.kovidgoyal.net/kitty/desktop-notifications/)
