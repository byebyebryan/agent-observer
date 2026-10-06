# Separate notification source/client checkpoint

Date: 2026-10-06. Status: accepted experimental metadata/source/formatting subset;
normal hook selection and desktop routing/delivery remain separate. API v1
read/write acceptance is independently recorded in the [a2 report](../2026-10-06-stable-api/REPORT.md).

## Artifact and consumer boundary

- Package/source: `0.3.0a4` / `196226300658ab07760aff1cc396df26c908d12f`.
- Wheel SHA256: `68f656483b8a7e23b366e4ad870367cf689a67c464f12920b62d23983c61afc3`.
- Immutable prefix on Snap/Starship:
  `/home/bryan/.local/share/agent-observer/0.3.0a4-68f656483b8a7e23`.
- Experimental module CLI: `python -m agent_observer.notification_client`;
  event schema 1. Stable API 1 remains snapshot/watch 3 and write 1.

Both profiles verify exact installed wheel bytes/entrypoints/API/schema. A byte
comparison proves all 30 existing producer files other than the package version
are identical to a2; only the two separate notification modules are added.
Independent jsonschema/CLI consumers pass both notification conformance and the
unchanged read/write public corpus, including the 4,096-row inventory. Source
checks pass 239 tests; the new files also pass scoped Ruff lint/format checks.
Wheels are archived on both hosts. No normal entrypoint changes.

The source normalizes bounded callback metadata, exact caller-supplied identity,
public snapshot title/kind and static bodies. It never reads private stores for
notification enrichment or emits desktop output during ordinary observation.
The explicit renderer/stream client handles publication formatting separately.
[The contract](../../notification-client-contract.md) records bounds and policy.

## Independent native callback proof

The same private user/mount/PID isolation and ordinary-path masking precedes
native startup. Only disposable configuration enables capture hooks/notify;
Codex built-in notifications and Claude native alert delivery are disabled there.
The callback sink preserves normalized metadata plus bounded hook flags. It
returns `{}` to Claude and no control fields. All PTY output is discarded.
The tested images are Codex 0.160.1 on both hosts and Claude 2.1.291 on Snap;
the isolation receipts record actual executable hashes. These identify this
proof, not provider support allowlists.

| Scope | Native result |
| --- | --- |
| Codex Snap and Starship | Native completion callback's thread/turn IDs match exact public identity and independently read latest-turn ID |
| Codex Snap and Starship | Two concurrent sessions with identical explicitly renamed native titles keep separate identities, titles and native turn keys |
| Claude Snap | A parallel Stop hook deliberately continues the same prompt once; two Stop callbacks share its prompt ID and both remain wakeups |
| Claude Snap | An actual SubagentStop with native child field is suppressed without changing the parent Observer row |
| Claude Snap | Held approval emits one permission Notification under the exact UUID/title; the tool is not executed and no approval is supplied |
| Claude Snap | Idle Notification arrives while native alert delivery is disabled; callback receipt does not prove a terminal publication route |

The attention receipt predates the idle callback and correctly records no idle
signal at that point. The later dedicated idle receipt independently reads the
exact native job as `done`/`idle` and the public row as `waiting`. Journal checks
also confirm the two Stop callbacks share one native prompt ID and the identical
Codex titles belong to distinct session UUIDs.

The first concurrent harness incorrectly required a turn catalog before a blank
context had a turn; rename was isolated from that read. A subsequent native
callback retained its then-current UUID title while Codex populated its native
name afterward. This is a real metadata timing difference, not a projection
failure. Both concurrent proof targets were explicitly named to validate stable
mapping and duplicate-title behavior. The API/handoff now clarifies asynchronous
native naming; an already captured notification is not retroactively retitled.

Native callback UUIDs can fall outside the sampled public inventory. Such Codex
receipts preserve unknown classification and the required fail-open policy;
this is not exhaustive child exclusion. Known public children and explicit
Claude child callbacks are suppressed. No transcript or hook caption is used to
invent a missing title or relationship.

## Controlled formatting and duplicate behavior

Pure tests and the separate schema reader validate sender Codex/Claude, exact
public/fallback title, static body, base64 OSC 99 title/body chunks, unfocused
policy and native focus action. Explicit Kitty tmux DCS wrapping is validated
synthetically. Claude output contains only terminalSequence; wake/ignored events
return `{}`. Duplicate suppression binds Codex native turn plus full identity;
Claude prompt IDs only correlate, so repeated attention within one prompt is not
silently lost. Receipt replay, bounded LRU eviction and restart are covered.
Final review found that an ignored codex_exec receipt could consume a visible
completion key in a3.
The failing regression now passes in a4: only notify dispositions consume native
dedupe keys; ignored callbacks use their receipt keys. A4 repeats packaged and
native checks independently; a3 is not selected.

These are controlled output checks, not Kitty/DMS GUI delivery, tmux pane
routing or desktop acknowledgement. The client has no automatic daemon-to-TTY
lookup, persistent exactly-once journal or lossless source replay. Both owned
namespaces and their borrowed auth/history are removed; cleanup receipts are
retained. Normal provider settings/hooks and a11 selected Observer links remain
unchanged, as does the Plus artifact.

## Remaining gates

Background manager completion/input callbacks have no accepted exact-target
correlation here and only wake; Agent View-dependent callbacks are not a general
unattached daemon feed. Native elicitation/question callback coverage, exhaustive
Codex child classification, shared/remote daemon originating-terminal routing,
normal duplicate-alert replacement, graphical sender/focus/Open and 349 physical
mirroring remain separate. Do not reconstruct lossless completions from watch.

The next notification rollout needs a concrete owned origin transport, scoped
chezmoi helper/settings plan, native duplicate policy and real Kitty/tmux GUI
proof before selecting it. 349 continues to mirror desktop notifications without
provider lookups. Read/write clients can migrate independently against accepted
a2; this experimental notification checkpoint does not require their integration.

All repository evidence is bounded metadata. Raw callbacks, prompts, assistant
responses, tool payloads, credentials and terminal captures are not retained.
