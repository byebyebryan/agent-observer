# Discovery, subagents and history after runtime cutover

Date: 2026-10-03. Status: the bounded follow-up is implemented and installed as
Observer `0.1.0a5` and Agent Plus `0.13.0a3`. See the
[acceptance report](evidence/2026-10-03-discovery-history/REPORT.md) for current
counts, artifacts, native same/copy Resume proofs and remaining gates. The
findings below preserve the initial `0.1.0a4`/`0.13.0a2` diagnosis.

## Decision

Keep existing conversation history. Neither enabling Codex's managed runtime
nor enabling Claude Agent View requires a clean conversation-history slate
for the inspected versions. Keep the new runtime/action boundary and avoid
restoring standalone discovery, old terminal associations or a second legacy
adapter. Discover history through the providers' current interfaces; entering
that history is a separate, validated consumer action.

Observer should retain explicit main/child classification where the provider
supplies it. Agent Plus should exclude positively identified child sessions
from its ordinary conversation picker. Missing classification stays unknown;
it must not hide older main conversations or be inferred from their titles,
cwd, PIDs or ID shape. A future child view is consumer policy.

## Installed and native findings

| Source | Current inventory | History finding | Subagent finding |
| --- | --- | --- | --- |
| Snap Codex 0.160.0 | 48 saved rows: 43 CLI, 5 VS Code; no loaded rows in the sampled daemon | Earliest provider creation time is 2026-05-19 UTC | Default saved listing excludes native child source kinds; loaded inventory has no consumer child filter |
| Starship Codex 0.160.0 | 90 rows: 67 CLI, 23 VS Code; 1 live, 89 saved | Earliest provider creation time is 2026-04-17 UTC | The live row explicitly reports a user thread; the other 89 project unknown thread classification |
| Snap Claude 2.1.287 | 2 active interactive sessions and 3 retained completed jobs | Saved coverage explicitly reports `not_observed`; the collector does not enumerate project transcripts | The 3 extra retained jobs are the earlier migration proof jobs, not confirmed child sessions |

These are finite observations, not continuous coverage. The two active Claude
names are supplied by their native user-named registry records. The current
Claude collector reads only the session registry and job state files, so it
cannot currently enumerate the nested transcript subagents. Its missing saved
rows are a source-coverage gap, not evidence of incompatible old conversations.

### Codex classification gap

A read-only database metadata sample selected one existing child UUID, then
`thread/read(includeTurns=false)` on the verified existing managed endpoint
confirmed the native API shape:

- `threadSource` is `subagent`.
- `source` is a structured `subAgent` value containing a `thread_spawn` record.
- A native parent thread ID is present.
- The thread remains `notLoaded`; it was not resumed.

At diagnosis Observer accepted only string source kinds and `threadSource=user`.
It therefore projects both child facts as `unknown`. Agent Plus accepts only
`user` and `unknown` and has no child exclusion. This establishes a real
classification defect and a path for loaded children to enter the picker;
the sampled current saved lists themselves contained only CLI/VS Code rows.
It does not establish that every suspicious displayed row was a child.

The official [Codex App Server documentation](https://learn.chatgpt.com/docs/app-server)
separates stored `thread/list`, in-memory `thread/loaded/list`, passive
`thread/read` and explicit `thread/resume`. Omitted `sourceKinds` defaults to
CLI and VS Code. Source kind describes origin; switching runtime topology
does not by itself require generating a new conversation identity. Preserve
the separately returned thread and saved-session IDs in the consumer contract.

### Claude passive history feasibility

The filesystem inventory found 34 root conversation JSONL files across 11
project directories and 182 nested subagent transcripts. No session-index
JSON files were present. These filename counts alone do not prove resumability.

Anthropic's [session-browser cookbook](https://platform.claude.com/cookbook/claude-agent-sdk-05-building-a-session-browser)
documents `list_sessions()` as a metadata-only filesystem read without an
agent launch or API call. The inspected official implementation enumerates
root UUID transcript files, excludes first-record sidechains and does not
descend into subagent directories for the history list.

A temporary probe loaded the unmodified official metadata modules at commit
`9c69ce7aced5cdf2aa1ac86fe62e877b4962de8b`. It bypassed the SDK package entry
module and exercised only global `list_sessions()`. An isolated Python
environment supplied `anyio`; the full SDK distribution and its bundled CLI
were not installed. Therefore this proves the metadata function on current
native files, not the production SDK packaging or consumer integration.

The probe returned 31 unique top-level conversation IDs, including both active
registry UUIDs. All 31 had cwd and explicit transcript creation time; history
extends to 2026-07-13 UTC. It opened 34 root transcripts and zero subagent
transcripts, taking 9 ms in this finite sample. Python audit guards prohibited
writes, subprocess creation and network operations during listing. Only
filtered counts and source hashes are retained in
[probe metadata](evidence/2026-10-03-discovery-history/passive-history-probe.json).

Integration must project only allowlisted native metadata. SDK `summary` and
`first_prompt` can contain conversation content and must never reach the
snapshot, logs or repository evidence. `custom_title` combines custom and
AI-generated native titles; it does not independently establish user naming
provenance. Preserve established registry/job names and retain a conservative
fallback where title provenance is insufficient. SDK `last_modified` comes
from file mtime and must not become a native work clock or identity signal.
The SDK silently skips some unreadable or metadata-only files; a successful
call alone cannot justify complete saved coverage. Its dependency and bundled
CLI footprint must be evaluated before selecting a production package.

### Claude history entry differs from job attachment

The official [Agent View documentation](https://code.claude.com/docs/en/agent-view)
keeps saved conversations available through native resume. On versions since
2.1.257, `--resume` with a full UUID plus `--bg` can continue the same UUID or
create a copy when in-place continuation is unavailable. Bare resume, names,
paths and `--continue` with background mode always copy. These are documented
semantics; this pass did not resume an ordinary saved conversation to prove
its outcome on 2.1.287.

At diagnosis Agent Plus supported exact retained-job attachment, not generic saved
Claude history entry. A history row therefore cannot borrow that action route
or invent a short job ID from its UUID. Observer must not resume/register old
conversations just to make them visible. The consumer must establish the
resulting job/conversation mapping after an explicit user Resume, including
the possible copied identity.

## Bounded implementation pass

1. Preserve native Codex child classification in Observer, with finite source
   enums and optional validated lineage metadata. Extend the consumer validator
   and exclude confirmed children in Agent Plus presentation, including loaded
   children. Unknown old main sessions remain visible. Verify native child
   shapes and controlled loaded-child cases without spawning production work.
2. Add Claude saved inventory through a pinned supported metadata interface if
   its packaging remains reasonable. Keep saved coverage and partial errors
   independent of the live registry/jobs. Join exact UUIDs in the same namespace
   only; never synthesize live state from transcript history. Root conversation
   listing must continue to exclude nested transcripts and sidechains.
3. Add a separate Agent Plus saved-Claude Resume action. Use the full UUID and
   revalidate host, namespace and existing activity before launch. Prove exact
   continuation and copy fallback with disposable conversations before enabling
   the route. Existing supervised jobs keep their exact attachment route.
4. Verify source, installed artifacts and managed links on Snap and Starship,
   with Codex on both and Claude on Snap. Reopen the picker for a coordinated
   candidate update; provider-session restart is not a requirement for discovery
   metadata changes. Keep graphical and current-client binding gates separate.

Do not add legacy terminal discovery, an automatic history migration, a
parallel daemon-off adapter or transcript compatibility variants. If the
supported Claude metadata integration proves too costly, keep its history
preserved and natively resumable while exposing limited picker history
coverage. That would be an explicit UI limitation, not a history deletion or
mandatory provider clean slate.
