# Experimental notification source and client

Date: 2026-10-06. Separate S6 checkpoint; not part of stable API v1 or a hook
installation. Native/transport acceptance is recorded separately below.

The later [ownership clarification](observation-boundaries.md) distinguishes
provider refresh hints, Observer read push and user-facing alerts. This remains
an experimental source/client contract, outside API 2's accepted read surface.
Its suppression/disposition/formatting fields are client policy; future reusable
native-event evidence needs a separately reviewed boundary and native gate.

The [2026-10-09 state/event design](state-and-events-design.md) now settles that
future boundary, with [independent research proof](evidence/2026-10-09-state-and-events-design/REPORT.md)
and a separate implementation sequence. The ESP32-349 handoff is one client
request. This historical experimental wire remains policy-bearing and is not
the proposed pure event wire or a general consumer contract; no converter or
production event acceptance is implied.

## Source boundary

`notification_source` consumes an explicitly invoked provider callback and a
caller-supplied full Observer identity. Native UUID must match it exactly. An
optional validated public snapshot supplies exact kind/title; no private SQLite,
transcript, cwd/PID/title matching or provider executable is used for enrichment.
Absent enrichment uses a UUID title and unknown kind. Known children are
suppressed; unknown Codex classification retains the existing fail-open policy.
Event kind describes callback context: Claude's explicit child fields can suppress
a callback under the parent's UUID without changing the parent's Observer row.
Snapshot title/kind are supplied enrichment, not a freshness or authorship claim.
Codex's native name can settle after completion, leaving an initial UUID title.

Only bounded metadata crosses normalization: receipt UUID/time, complete identity,
finite source/signal/disposition/reason, kind/title, static body and correlation.
Prompts, responses, tool payloads, hook captions, transcript paths and raw callback
text are discarded. Receipt time never replaces conversation activity, phase or
runtime evidence. Caller-supplied identity/callbacks are not action permission.

Primary native references establish the following input semantics:

- [Codex notify](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications)
  supplies `agent-turn-complete`, thread/turn identifiers and content fields.
  The adapter keeps identifiers and a static completion body; `codex_exec` is
  suppressed. Missing/invalid turn IDs retain receipt-only correlation.
- [Claude hooks](https://code.claude.com/docs/en/hooks) distinguish Notification,
  Stop and SubagentStop. Notification permission/idle/elicitation signals map to
  static attention messages. Stop can be followed by parallel-hook continuation;
  it and UserPromptSubmit are wakeups only. `agent_id` proves a subagent;
  `agent_type` alone can describe a top-level custom agent. Prompt IDs correlate
  a user prompt, not unique permission/question/idle events. Background
  `agent_completed`/`agent_needs_input` depend on an open Agent View and currently
  have unproved target correlation here, so only wake. Hook delivery persists
  when native alert channels are disabled; that does not prove custom delivery.

Unknown notification types are ignored with a finite reason. A callback cannot
settle the parent or create a final-success claim. Unattached/background events,
missed hooks and unsupported source kinds have no synthetic completion fallback.
Sampled watch remains a different read interface without lossless replay.

## Explicit client

The module CLI is deliberately separate:

```sh
python -m agent_observer.notification_client schema
python -m agent_observer.notification_client normalize --identity FULL_REF_JSON --snapshot SNAPSHOT_JSON < CALLBACK_JSON
python -m agent_observer.notification_client render --format kitty < EVENT_JSON
python -m agent_observer.notification_client render --format claude-hook < EVENT_JSON
python -m agent_observer.notification_client stream --format json < EVENTS_JSONL
```

The experimental event wire is 1; its exported schema and semantic validator
reject extra fields/invalid identities/false correlations. Raw callbacks are
bounded to 1 MiB/100,000 nodes; normalized frames to 16 KiB/256 nodes. Errors are
finite and content-free. The ordinary read/write CLI neither imports this client
nor publishes notifications. Stable API 1 still declares only its read/write
schemas and pure facade; no public notification stability is implied.

These operator commands can exit 2 on invalid input. Do not wire them directly
into a controlling Claude Stop/tool hook: its adapter must return exit 0 and `{}`
on observation failure, without decision fields. The isolated capture helper
demonstrates that quiet failure boundary; it is not a production hook installer.

The stream client's 256-entry process-local LRU suppresses repeated normalized
receipts. Codex completion additionally uses full identity plus native turn ID;
repeated callbacks for that same turn coalesce. Only visible notification signals
consume a native dedupe key; ignored callbacks
cannot suppress a later visible completion. Claude prompt ID is correlation
only: distinct attention receipts survive even for the same prompt. Restart,
eviction and missing native IDs can produce duplicates. There is no durable
exactly-once journal, replay authority or desktop delivery acknowledgement.

## Kitty transport and ownership

[Kitty OSC 99](https://sw.kovidgoyal.net/kitty/desktop-notifications/) supports
separate base64 application name, title/body chunks and originating-window focus.
The explicit renderer produces Codex/Claude sender, native/fallback title, static
body, unfocused-only policy and native focus action. It emits no Ghostty fallback.
Kitty output can explicitly request `--tmux-passthrough`; this wraps doubled
escapes in tmux DCS. It does not select a pane or prove its passthrough setting.
Chunk IDs are shared and bounded; encoding prevents escape-sequence injection.
Claude-hook output contains only `terminalSequence`, with no decision/control
fields; ignored/wakeup events return `{}`.

Rendering to stdout is an explicit publication transport boundary. The caller
must establish the originating terminal/pane. No automatic TTY, Kitty window,
tmux pane or remote routing is inferred from daemon startup environment or a
session PID. A controlled sink/PTY proves formatting, not graphical sender,
focus/Open, duplicate native-alert policy or DMS/349 mirroring. Claude hook
terminalSequence requires an interactive UI path; detached daemon publication
and shared-daemon per-viewer routing are not accepted by this client.

Chezmoi retains ownership of normal helper/hook/settings selection. Normal Codex
external completion plus approval-only built-ins and Claude native Kitty policy
remain unchanged. Any replacement needs scoped configuration/artifact/native
duplicate tests, originating Kitty/tmux routing and graphical Open proof. 349
keeps consuming the desktop notification stream; it gains no provider lookups.

## Acceptance

The [a4 packaged/native checkpoint](evidence/2026-10-06-notifications/REPORT.md)
accepts the experimental subset independently of API v1 read/write acceptance.
Source tests cover privacy, exact identity/title/kind, fail-open unknown Codex,
child suppression, Stop continuation semantics, unsupported background targets,
correlation/restart/LRU limits, strict framing and Kitty fields. Native callback
capture proves Codex completion/turn IDs on both hosts, concurrent duplicate-title
mapping, Claude parallel Stop continuation, child suppression, permission and
idle signals with native alerts disabled. Actual Kitty/DMS/349 delivery, remote
and unattached origin routing, question callback coverage and background manager
target correlation remain separate limits. Normal wiring is unchanged.
