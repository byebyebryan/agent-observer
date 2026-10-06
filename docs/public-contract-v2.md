# Public observation and read client contract v2

Version: 2; package candidate `0.2.0a9`, independently accepted subset recorded
in the [repair report](evidence/2026-10-05-evaluation-repair/REPORT.md). The `0.2.0a9`
producer is selected on Snap and Starship after its independent artifact gate;
Plus retains its schema-compatible `0.2.0a3` reader dependency. This is a semantic
cutover from the [v1 pilot](snapshot-contract.md), with no v1 option on the CLI.
Codex `0.160.1` daemon capability proof is separate from the `0.160.0` installed
CLI proof. Selection does not extend the accepted artifact bounds; new images
require independent proof. See the [repair execution](evaluation-repair-execution.md).

## Identity, states and source decisions

`identity` contains the caller-supplied host scope, provider, store namespace,
native ID kind and full native ID. The store namespace hashes provider, exact
canonical configuration path, selector kind and UID. OS namespace, boot, PID and
runtime birth no longer enter the logical reference. Moving a store or changing
its selector/UID changes that reference; no automatic alias or machine identity
claim is provided. `runtimeNamespace` and runtime incarnation metadata remain
separate action-context provenance. Native Codex thread/session IDs and Claude
session UUID/job short IDs remain distinct.

Phase is working, blocked, waiting or unknown. Approval waits map to blocked.
The proved Codex loaded idle state maps to waiting, with a sampled evidence
clock. Claude work/approval maps to working/blocked; completed background jobs
have a separate completed outcome. A completed background job with its current
verified worker maps to waiting within its exact image gate: an isolated native proof accepted a subsequent
prompt under the same UUID and completed it. Completion with a missing/unknown
worker does not establish readiness. The monitoring source checkpoint additionally
accepts Claude 2.1.289 foreground first-prompt/completed readiness and held
held background input as blocked/question. Foreground registry input labels are
shared with other dialogs and cannot establish the reason required by v2;
foreground questions remain unknown. Exact linked background job question
structure, working/blocked job state and current registry input wait accept
blocked/question. New predicates require that exact
worker image, independently of the installed CLI; surviving 2.1.287 workers keep
their previous limits. Current background completion requires explicit latest
terminal metadata and zero tasks, queued work and drainable monitors. Idle with
pending work or a blank background context remains unknown. Old terminal job
state cannot override current working/input-wait registry evidence.

Codex 0.160.1 explicit latest-turn completed/failed/interrupted metadata maps to
completed/failed/cancelled outcome, with its terminal clock. A new in-progress
turn clears the preceding outcome. Outcome does not settle runtime phase;
systemError remains unknown with `native_runtime_error`. Codex questions and
Claude failure/cancellation outcome predicates remain unproved. These source
changes await independent package acceptance and do not change selected a9.

Blank live background rows use `background_readiness_unproved`; native job
state `blocked`, whose meaning is not established by the held approval case,
uses `native_blocked_phase_unproved`. Neither native label alone authorizes a
waiting or blocked phase. Claude rows with current, exact-UUID non-sidechain
conversation-envelope activity are classified as user conversations. A child
transcript carrying its parent's UUID never classifies that parent as a child;
UUID-only runtime rows without conversation evidence remain unknown.

Runtime is running, parked or unknown. Current loaded Codex context or verified
Claude worker establishes running. Saved-only rows and worker absence remain
unknown: the sources do not prove absence of every relevant runtime context.
Parked is part of the vocabulary but is not enabled by these adapters yet.
Worker and attachment evidence are separate. Codex does not claim worker presence
from a loaded server thread; current client binding remains unsupported.
Runtime coverage explicitly names its scope: loaded_threads for Codex and
registered_workers for Claude. Complete coverage of those inventories does not
claim an exhaustive list of all provider execution contexts. In particular,
Codex work can survive viewer exit outside loaded-thread inventory; the current
collector leaves saved-only work unknown rather than claiming it stopped.

Activity uses metadata conversation events: Codex's latest turn completion,
or its start while incomplete, through `thread/turns/list` with `itemsView=notLoaded`
and a limit of one. No conversation items are requested. Native `recencyAt` only
advances on input and cannot represent assistant completion. Claude uses matching
top-level user/assistant message-envelope timestamps in a bounded transcript tail,
excluding sidechains, injected meta messages, renames and housekeeping. Prompt,
response and tool content is discarded inside the isolated read-only worker;
only the timestamp and provenance cross its output boundary. An empty conversation,
missing native timestamp, incomplete/changing record or exceeded bound remains
null with a reason. Creation, modification, collection and resume never substitute
for activity. These sources require the exact pinned provider artifacts.

Default ordering is phase attention
(blocked, waiting, working, unknown), then last conversation activity, newest
first, then full identity. Unknown activity stays unknown; `--order created` is
an explicit alternative. Native history creation metadata remains separate.

Activity ordering precedes saved-history display limits. Codex enumerates at most
1,000 saved rows, then selects the most recent 100 without dropping loaded rows.
Catalog/display limits have explicit partial coverage. Claude's existing 2,048-file
census bounds discovery, then reads at most 512 KiB per transcript and 64 MiB total
for activity before its 100-row display cap. Concurrent transcript appends no longer
invalidate the whole SDK catalog; a changed tail loses its own clock. Duplicate
native transcript identities remain ambiguous, and filesystem replacement still
invalidates the catalog. Activity is an ordering fact, never action authority.

Claude saved Resume creates a new UUID and initially hydrates the copied history
in memory. Its `resumeSessionId` already names the new UUID, so it supplies no
safe origin relation for activity inheritance. Until native transcript metadata
appears, that new row's activity remains unknown (`conversation_metadata_not_persisted`).
The first new prompt materializes the copied store and advances its activity.
The requested and resulting identities remain explicit in the write result.

Claude native job `state=blocked` is recognized as an observation-only unsupported
phase (`native_blocked_phase_unproved`), with public job state unknown. It does not
become urgency blocked or waiting without a separate semantic proof. A healthy
target can still attach through an exact verified retained job/worker link.

Each evidence object retains value, health, reason, source, original observedAt
and whether that clock is native or sampled. Collection/liveness time cannot
renew conversation age. Incomplete sources retain healthy current dimensions;
a failed history dimension does not erase verified live facts. Unknown child
classification remains visible; confirmed children are filtered by the list
client by default.

## Schemas and validation

Bundled snapshot/watch JSON Schemas use Draft 2020-12. Export them with
`agent-observer schema --kind snapshot` or `--kind watch`. The dependency-free
Python reader validates the vocabulary used by those schemas, rejects duplicate
keys, controls, nonfinite numbers, oversized/deep documents and unknown fields,
and enforces semantic identity/provenance/evidence invariants. These additional
semantic checks remain required beyond generic JSON Schema validation.

Snapshots contain at most two provider sources and 4096 sessions. Inputs are
bounded to 8 MiB. Errors are finite codes, never provider payloads. Canonical
metadata-only fixtures in `tests/fixtures/contract-v2` cover both providers,
partial feeds and a watch gap. Fixtures and controlled tests do not constitute
new native proof.

## Local read commands

```sh
agent-observer snapshot --host-scope snap
agent-observer list --host-scope snap
agent-observer doctor --host-scope snap
agent-observer list --input snapshot.json --json
agent-observer show --input snapshot.json --ref '{"hostScope":"snap","provider":"codex","namespace":"sha256:FULL_DIGEST","nativeIdKind":"thread","nativeId":"FULL_UUID"}' --json
agent-observer watch --host-scope snap --interval 2
```

`snapshot` emits the complete public JSON model. `list --json` emits the same
model with ordered/filtered rows; human list output labels unavailable activity
as unknown. `show` requires the complete exact JSON reference. `doctor --json`
returns host, source health/coverage/capabilities and session count.
`doctor --history-census` performs a separately timestamped bounded Claude SDK
scan and reports candidate files/UUIDs, returned/projected/omitted/unresolved
UUIDs, companion duplicates and display counts. SDK omission does not prove
invalid history. Coverage stays partial; limits or unsafe stores remain errors.
This optional diagnostic is outside the snapshot schema and requires live scope.
`--input FILE` (or `-` for stdin) parses only a public snapshot and never imports
collectors, inspects provider homes, enriches paths or performs actions.

## Project context

`cwd` is the provider's recorded context, with `cwdSource` identifying its source.
For live Claude rows the registry wins; saved Claude rows retain the SDK's
recorded context. A later message's cwd can differ, but is not promoted to the
session's launch/resume context. Codex RPC context and the fallback's explicit
session header are independently compared; stale catalog cwd is not substituted.
Workspace enrichment describes that selected recorded context. It does not
claim the latest tool cwd or establish action authority. A separate recent
context field would require a versioned contract and native Resume proof.

Local collection inspects bounded Git directory/gitfile and commondir metadata,
without invoking Git, hooks, status, fetch or network operations. Linked worktrees
retain distinct checkout roots and a shared Git common directory. Inspection is
cached for 15 seconds and limited to 256 unique contexts and 64 ancestors.
The two-second enrichment budget is a soft filesystem scheduling budget, not a
hard guarantee for a stalled filesystem. Failed enrichment preserves discovery.

Optional `--workspace-config FILE` supplies local roots and explicit mappings:

```json
{"roots":[{"key":"code","path":"/home/bryan/code"}],"projects":[{"rootKey":"code","relativePath":"agent-observer","projectKey":"agent-observer"}]}
```

The snapshot exports the selected absolute root, logical root key, relative path
and Git context. Only explicit project mappings establish cross-host project
membership; matching names, remote URLs or worktree common directories do not
merge native sessions. The fixture reader does no filesystem enrichment.

## Sampled watch

Watch emits newline-framed JSON: initial snapshot, semantic changes, heartbeats,
gaps and full resynchronization snapshots. Every invocation has a fresh stream
UUID and monotonically increasing revisions. Collection UUID/time and sampled
evidence-clock refreshes alone do not create semantic changes. Each poll completes
before another begins. Minimum interval is one second; the observed local passive
collection took approximately one second in this checkpoint, with provider
timeouts independently bounded. Default interval is two seconds.

Partial/capped inventories retain missing last-known rows as stale, preserving
their original evidence clocks. They cannot imply deletion or parked state.
Source failure emits a gap and resynchronization; collector exceptions emit a
gap until a successful sample. `--count` bounds an invocation for development.
SIGINT exits without provider cleanup/actions. A blocked stdout consumer times
out after five seconds; reconnect starts a new stream and full snapshot. No
buffered replay or lossless native event capture is promised. Native notification
and hook wakeups have separate passivity/correlation gates and are deferred.
