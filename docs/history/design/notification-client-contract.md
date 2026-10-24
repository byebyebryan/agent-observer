# Experimental notification source and client

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Current implementation, 2026-10-11: native intake and Kitty rendering support
Codex only after [Claude retirement](../providers/claude-retirement-plan.md). The experimental
wire remains version 1 and admits historical supplied data; that pure admission
is not a native adapter or transport capability. The removed `claude-hook` format
is unsupported. Normal native hooks/settings are outside this implementation.

This policy-bearing experiment is separate from [API 2](../contracts/api-v2.md), cached
[state push](state-push-design.md) and any future reusable occurrence-event API.
The [ownership boundary](../../observation-boundaries.md) distinguishes native refresh
hints, replacement read views and user-facing alerts. A pushed state view does
not promise every native transition or one completion notification per turn.
The ESP32-349 handoff remains one client's request, not a settled alert contract.

## Current source boundary

`notification_source.normalize` consumes explicitly supplied Codex callback
bytes and a caller-supplied complete Observer identity. The native thread ID
must match exactly. An optional validated public snapshot supplies title/kind
by the full reference; no provider lookup, private saved store, process, cwd,
terminal or window matching occurs. Missing enrichment leaves kind unknown and
uses a UUID title. Unknown kinds retain the experimental fail-open policy;
confirmed children and `codex_exec` callbacks are suppressed.

`agent-turn-complete` produces a static completion message and bounded thread/
turn correlation. Unsupported event types are ignored with a finite reason.
Prompts, responses, tool payloads, callback captions and transcript paths are
discarded in memory. Receipt time never replaces conversation activity, phase
or runtime evidence, and a callback supplies no action permission or final-
success guarantee. Snapshot enrichment does not establish current authorship.

Normalization rejects a retired native provider before decoding callback bytes.
Pure event validation and JSON forwarding retain frozen historical vocabulary;
Kitty rendering rejects providers other than Codex. The source/read service
never installs callback hooks or emits user-facing alerts on startup.

## Explicit experimental client

Use the accepted reader prefix's Python interpreter:

```sh
observer_python="$HOME/.local/share/agent-observer/0.5.0a18-06544d27ae62f590-mesh-a11-reader/bin/python"
"$observer_python" -m agent_observer.notification_client schema
"$observer_python" -m agent_observer.notification_client normalize --identity FULL_REF_JSON --snapshot SNAPSHOT_JSON < CALLBACK_JSON
"$observer_python" -m agent_observer.notification_client render --format json < EVENT_JSON
"$observer_python" -m agent_observer.notification_client render --format kitty < EVENT_JSON
"$observer_python" -m agent_observer.notification_client stream --format json < EVENTS_JSONL
```

The placeholders are explicit caller inputs, not provider discovery commands.
`render` and `stream` support `json` and `kitty`; `--tmux-passthrough` applies only
to Kitty and wraps doubled escapes in tmux DCS. It selects no pane and proves no
passthrough setting. Raw callbacks are bounded to 1 MiB/100,000 nodes; normalized
frames to 16 KiB/256 nodes. Invalid input/transport returns exit 2 with a finite,
content-free diagnostic. This is not a production hook installer.

The stream's 256-entry process-local LRU suppresses repeated receipt IDs. Codex
completion additionally deduplicates by full identity plus native turn ID.
Suppressed callbacks do not consume a later visible signal's deduplication key.
Restart, eviction and missing turn IDs can produce duplicates. There is no
durable journal, replay, exactly-once guarantee or desktop acknowledgement.

## Kitty and alert ownership

The renderer emits bounded base64 Kitty OSC 99 chunks with the Codex sender,
static body, supplied/fallback title, unfocused-only policy and native focus
action. Chunk identity is not a delivery acknowledgement. Rendering to stdout
is an explicit publication boundary: the caller must establish its originating
terminal/pane and remote route. No automatic TTY, Kitty window, tmux pane or
remote attachment is inferred from a daemon environment or session PID.

A controlled sink proves formatting, not graphical sender/focus/Open behavior,
duplicate native-alert policy or DMS/ESP32 delivery. Chezmoi owns ordinary
helper/hook/settings selection; this experiment supplies no replacement or
provider-policy acceptance. Device projections, alert policy, occurrence replay
and shared-daemon per-viewer routing retain independent implementation/native
and graphical gates.

## Historical evidence

The [a4 notification checkpoint](../../evidence/2026-10-06-notifications/REPORT.md)
retains its original Codex/Claude callback, privacy, correlation and controlled
transport bounds. Its Claude intake/rendering and removed operator commands do
not describe a18 support. The [pre-retirement guide](https://github.com/byebyebryan/agent-observer/blob/2fcacd1f7c85258b1fb857495978d61200315e52/docs/notification-client-contract.md)
preserves those original instructions. The following [state/event research](state-and-events-design.md)
and [execution proposal](../delivery/state-and-events-execution-plan.md) remain deferred.
