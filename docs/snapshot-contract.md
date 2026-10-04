# Host-local snapshot contract candidate, version 1

This is the current installable candidate, `agent-observer 0.1.0a5`. It is
supported only for the exact provider artifacts and topologies listed below.
The migration may revise this prerelease contract; consumers reject unknown
schema versions instead of falling back to historical discovery heuristics.

## Command and transport

`agent-observer snapshot --host-scope snap` emits one bounded JSON document
and one trailing newline. Repeat `--provider codex` or `--provider claude` to
select sources. Explicit `--codex-home` and `--claude-home` select existing
configuration roots; environment defaults preserve native provider settings.

The command reads existing local metadata. It does not invoke provider CLIs,
start daemons, repair endpoints, resume sessions, or watch terminal content.
There are no provider action commands. A valid document can report unavailable
sources with exit status zero; process/parse failure is a different transport
failure. Consumers bound output and enforce their own timeout.

Host Mesh supplies `--host-scope` and owns local/SSH routing. The echoed
`host.authority` is caller-selected provenance, not machine attestation.
`nativeHostname` is descriptive. Observer provides no cross-host control plane.

## Document and identity

The envelope contains `schemaVersion: 1`, a UUID `collectionId`, Unix
milliseconds `collectedAt`, `host`, independent `sources`, `sessions`, finite
`errors` and `limitations`, `sourceHealth`, and bounded `durationMs`.
Each source retains its own collection clock, namespace, configuration root,
runtime fingerprint, coverage, source health and finite failure reasons.
An unavailable provider does not invalidate healthy facts from another.

Every row has the exact logical key:

| Field | Meaning |
| --- | --- |
| `identity.hostScope` | Caller-selected Host Mesh host ID |
| `identity.provider` | `codex` or `claude` |
| `identity.namespace` | Configuration and OS namespace fingerprint |
| `identity.nativeIdKind` | Codex `thread`, Claude `session` |
| `identity.nativeId` | Native UUID |

Keep all five fields in deduplication, persisted selections and action
revalidation. A runtime PID, viewer, title, cwd or job short ID cannot replace
this key. Duplicate exact keys remain visible with ambiguous unknown facts.
Codex `nativeIds.threadId` and `nativeIds.sessionId` are distinct protocol
fields. Claude `nativeIds.sessionId` and optional eight-digit hexadecimal
`nativeIds.jobId` identify different objects.

Only bounded native metadata is projected. No prompts, assistant text, tool
arguments/output, terminal captures, credentials, provider environment, or raw
payloads cross this boundary. Native explicit titles and cwd are presentation
metadata and never identity or join evidence. Claude projects a bounded native
registry/job name only when `nameSource` is explicitly `user`. Names with absent,
automatic, derived or other unproved provenance retain the native-ID fallback;
job names can otherwise originate from task text. Saved history additionally
accepts the official SDK's explicit bounded `custom_title`, without attributing
its author. SDK summaries and first prompts are never projected. A rename never refreshes
the work-state clock or changes session identity.

## Independent facts and clocks

Rows expose `work`, `presence`, and `attachment` separately. Each fact has
`value`, `observedAt`, `source`, `health`, and finite `reason`; invalidation may
retain `lastKnownValue`. `observedAt` is Unix milliseconds or null.

| Dimension | Values |
| --- | --- |
| Work | `working`, `needs_input`, `settled`, `interrupted`, `error`, `unknown` |
| Presence | `present`, `absent`, `unknown` |
| Attachment | `attached`, `detached`, `unknown` |
| Health | `current`, `stale`, `unavailable`, `unsupported`, `ambiguous` |

Known facts require an explicit source and clock. A liveness refresh does not
renew work-state evidence. Unavailable, unproved or conflicting evidence is
unknown, never idle. Worker/client exit does not establish logical session end.

`presenceKind: server_thread_loaded` means Codex loaded inventory membership;
it does not prove an OS worker or attached TUI. Claude `presenceKind: os_worker`
requires exact PID birth, PID domain and accepted executable identity. Retained
jobs remain separate from workers and historical interactive registry entries.

## Accepted native coverage

| Provider artifact | Native topology and accepted evidence |
| --- | --- |
| Codex 0.160.0, Linux x86_64 musl, SHA-256 `12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad` | Existing native managed Unix endpoint; saved/loaded inventories; exact read without turns; working, settled and approval wait; viewer exit with work continuation; exact saved resume; outage without Observer auto-start; new daemon birth with the same saved session |
| Claude Code 2.1.287, Linux x86_64, SHA-256 `3920489a5109cff5786a1a392c25277408ff22bc796d5edb9c16a60e5a1718f0` | Direct private session registry/job files; verified workers; background working, terminal completion and approval wait; native short-ID attach; worker survives viewer exit and completes work; retained terminal job survives explicit disposable worker exit |

`coverage` reports completeness per source/dimension. History display limits do
not cap Codex loaded inventory. Claude optionally enumerates top-level saved
conversations through `claude-agent-sdk 0.2.163`'s global `list_sessions()` API.
It uses an isolated bounded read helper with the exact configuration root,
without invoking Claude. Healthy saved coverage remains
`{complete:false,reason:"metadata_scan"}` because the SDK can exclude entries
without reporting why. Source errors use finite `history_*` reason codes;
consumers keep these warnings separate from live-source failures.
Interrupted/error and general input/worker/sandbox
wait semantics remain unaccepted; candidate collectors return unknown for them.

Both providers currently report client binding/attachment unsupported.
Source connectivity and launch-time Tmux options do not identify the conversation
currently displayed after native navigation. Consumers may offer independently
validated fresh native attachment routes, but must reject session-specific
focus/close based solely on an old wrapper label. Consumers retain all action,
permission, runtime ownership and presentation policy.

## Evidence and delivery gates

The native study is [the runtime report](evidence/2026-10-03-native-runtime/REPORT.md).
Unit and controlled-server tests verify the contract's failure behavior; they
do not establish native acceptance. Packaged installation, ordinary hooks,
cross-host routing, migrated consumer UI and the current coordinator's final
reopen have separate gates in [execution status](execution-status.md).

Codex rows optionally include `nativeHistoryTimes` with nullable Unix-millisecond
`createdAt` and `updatedAt`, projected only from the accepted native protocol's
explicit integer Unix-second fields. Missing or invalid values remain null with
`native_history_time_unavailable`; they never come from file times or presence.
Consumers may order history using explicit `updatedAt`, independently of work
and presence clocks. Version `0.1.0a2` added this bounded metadata to the initial
`0.1.0a1` installed pilot without changing schema version 1.

Claude sources in `0.1.0a3` expose `configHomeKind: default | explicit`. The
default selector means the host default `.claude` root with `CLAUDE_CONFIG_DIR`
unset; an explicit selector means that variable or a non-default root. The
selector joins the namespace hash. This distinguishes native preference-file
locations even when the registry directory is identical. Consumers preserve
default entry with `env -u CLAUDE_CONFIG_DIR`, and set the exact root for explicit
entry. Missing mode remains unknown and cannot authorize attachment or creation.
This is configured source context, not a claim about a terminal's current session.

## Discovery and saved history in 0.1.0a5

Codex `sourceKind` includes `subagent` and `threadKind` includes `child`.
Explicit `threadSource=subagent` or validated native `source.subAgent`
metadata establishes a child. Conflicting user/child evidence stays unknown
with `thread_classification_conflict`; malformed child evidence stays unknown
with `thread_classification_unavailable`. Nested source payloads and parent
IDs are not exported. Observer retains children for consumers that need them;
Agent Plus excludes confirmed children and rejects child or ambiguous actions.

Claude saved-only rows have `inventory=saved`, `sessionKind=unknown`, exact
session UUID, null job identity and `cwdSource=claude_history`. Work and presence
remain unknown with null clocks and `reason=unobserved`; attachment remains
unsupported. An old transcript does not establish an absent or idle worker.
Optional `history` has exactly `source=claude_sdk`, `sdkVersion=0.2.163`, nullable
integer Unix-millisecond `createdAt`, and nullable `fileModifiedAt`. The latter
is file metadata and cannot refresh work, presence or consumer recency.

Exact same-namespace UUID matches merge saved metadata into live rows while
preserving live identities, state, clocks and cwd. A saved native title replaces
only the UUID fallback. Agent Plus orders saved-only rows by explicit SDK
`createdAt`, while live rows retain their independent work clocks.

Consumers may offer a distinct saved Resume action after fresh validation.
Agent Plus invokes `claude --resume FULL_UUID --bg` once with closed stdin;
the native attach cue identifies the actual short job and a fresh public
Observer row identifies the actual session. A provider-created copy attaches
using its resulting UUID. Transport ambiguity, identity mismatch or a later
viewer failure never dispatches another provider resume. Ordinary foreground
sessions require native navigation and keep their attachment unsupported.
