# Codex timing validation

2026-10-12. Native research and contract review only. The
[review and execution gates](../../codex-timing-contract-review.md) propose a
following producer checkpoint. API 2/read 4/Service 2/Mesh SDK 1 and selected
collector/read/publisher roles are unchanged. No client integration or physical
acceptance is claimed.

## Inputs and bounds

Both ordinary owning daemons report Codex 0.162.1, binary SHA256
`628e35487d888a28f0427fc37501da529dd3d81fcbad7a2c3421c1e8670d92e1`.
Version/hash record provenance, not support allowlists. The native binary's
experimental generated schema supplies clock descriptions, nullable fields,
status variants and request method names. See [inputs](inputs.json).

The existing standalone evaluation client authenticates the normal Unix endpoint,
UID, daemon image and incarnation before metadata-only native reads. It imports
no Observer collector and invokes no provider action. The installed public CLI
is a20; service collection stays a18. Three expanded rounds read at most sixteen
selected rows per host, with loaded and a few recent parked identities. This is
a selected sample, not an exhaustive inventory or transition census.

The controlled source is the same real Codex binary in a disposable private
`CODEX_HOME` and workspace, hosted as a separate stdio App Server. A local HTTP
Responses stub supplies deterministic synthetic tool/message output. The native
runtime produces actual status, approval/question requests and stored turn
metadata. The model backend is synthetic; these cases do not establish normal
daemon transition coverage, TUI behavior or real-model outcomes. Ordinary reads
provide separate managed-daemon clock evidence on each host.

Two controlled transition runs used twelve local Responses requests in total,
zero paid/remote model requests and only task-owned fixture threads. Additional
metadata-only checks started zero turns. Each owned server/model listener was
retired. Normal provider configuration hashes and daemon incarnations were
unchanged across each ordinary sample. No normal service, hook, writer, frontend,
provider setting or deployment was changed.

## Ordinary native/public comparisons

| Host | Expanded rounds | Rows per round | Saved rows | Unsaved rows | Public/native activity matches |
| --- | --- | --- | --- | --- | --- |
| Snap | 3 | 9 | 9 | 0 | 27/27 comparable |
| Starship | 3 | 13 | 8 | 5 | 24/24 comparable; fifteen unsaved samples unproved |

See [Snap](snap-passive.json) and [Starship](starship-passive.json). Ordinary
activity changes altered counts from earlier reads; the disposable native
fixture is in another namespace and does not appear in these samples.

All comparable installed `activity.at` values equal the latest native turn end
when present, otherwise its start. Native `updatedAt` can advance during an
ongoing working turn while its turn start and native `recencyAt` remain fixed.
For sampled saved rows, `recencyAt` equals turn start, including after completion.
These patterns do not define a universal recency formula.

Five idle unsaved Starship children have no proved native turn metadata. Their
native `createdAt`, `updatedAt` and `recencyAt` advance with later reads. This
extends the known unsaved-creation-clock limit to admission of native update
clocks: do not publish these values as proved history/activity timestamps. Their
runtime/phase remain independently known and children remain canonical data.

## Controlled transitions

The [expanded native receipt](controlled-native.json) includes nineteen bounded
metadata samples and twelve native status notifications. No notification in
this inspected shape supplies a native phase-transition timestamp.

| Case | Result |
| --- | --- |
| Empty loaded thread | Idle status, no latest turn; returned thread clocks alone do not establish a useful state age |
| Held generation and repeated reads | Active status and stable native turn start; repeated reads do not advance the saved working clock |
| Normal completion | Idle status; completed timestamp and updated timestamp advance, recency remains turn start |
| Quiet saved read | No update-clock renewal |
| Rename / one Git metadata patch / warm resume | No updated/recency advancement in this fixture |
| Held approval | Native `waitingOnApproval`; updated timestamp advances when tool request is recorded |
| Approval answered | Status becomes active without wait flags while `updatedAt` remains unchanged: direct counterexample to a general phase-entry clock |
| Held question and answer | Native `waitingOnUserInput`; same turn spans working, blocked and terminal states |
| Interrupt | Native idle plus interrupted terminal turn and completion time; does not establish successful task completion |

The first transition run omitted recency/section fields. The second used a fresh
private namespace and expanded capture; the first receipt remains under the
private study root. Native metadata-only checks use the expanded fixture.

## Metadata-only and cold-load controls

The [corrected metadata receipt](metadata-native.json) proves:

- Cold loading the saved fixture changes `notLoaded` to idle and advances
  `updatedAt`, while the prior turn-recency clock remains fixed.
- Setting a paused goal and clearing it advance `updatedAt` while status stays
  idle and no turn starts. This disqualifies unconditioned conversion into
  conversation activity, even though several other metadata operations did not
  advance it.
- Creating, assigning, renaming and removing user sections leaves runtime idle.
  Section moves change `sectionEnteredAt`; section rename does not reset it;
  removal clears it. It is group-entry timing, not work-phase timing.

An initial section call used the wrong RPC prefix and was rejected. The
generated ClientRequest declares `threadSection/create`, `threadSection/update`
and `threadSection/delete`, alongside `thread/section/move`. The corrected
method names passed. The initial failed attempt remains private evidence, not
an unsupported-provider claim.

[Official resume guidance](https://learn.chatgpt.com/docs/app-server#start-or-resume-a-thread)
says resume alone does not advance the thread timestamp. Warm resume matched
that statement; the controlled cold-load path advanced it. This receipt does
not establish the precise internal append responsible or every resume topology.
Regardless of that cause, paused-goal metadata is an independent counterexample
to a conversation-only timestamp. The
[official list interface](https://learn.chatgpt.com/docs/app-server#list-threads-with-pagination--filters)
also exposes distinct update and recency sort keys.

## Contract decision and exclusions

Keep current conversation activity semantics. A separately named native thread
update clock and explicit latest-turn boundaries would give read consumers
useful options without claiming exact phase duration. Runtime-only native clocks
need conservative admission. True native phase-entry time remains unproved.

The installed v4 validator accepts the supplied baseline fixture and rejects
an extra proposed timing record with `invalid_contract_fields`. Service 2 embeds
wire 4; Mesh a15 binds that version and a strict packaged Agent schema digest.
A timing extension requires a reviewed successor Observer/Service/Agent profile
tuple. Generic Mesh SDK 1 signatures need not change solely for extra native
fields, but the current descriptor cannot admit them. The exact schema and
version sequence remain proposal/implementation work, not accepted exports.

Repository receipts contain bounded identity/status/timestamp/provenance fields,
never conversation content, raw provider payloads, tool arguments/output,
terminal captures or credentials. Harness hashes and schema digest bind the
private study inputs. Producer checks, artifact/native/operational delivery,
resource acceptance, physical dashboard validation and future attachment work
remain separate gates.

## Following offline phase-tracking spike

The [turn/phase study](../../codex-phase-timing-spike.md) reuses these native
receipts without running another provider fixture. The
[standalone prototype](observed-phase-spike.py) and
[receipt](observed-phase-spike.json) record thirteen passing offline checks and
nineteen replayed samples. Stable native turn start survives blocking; the
prototype's separate observed-phase anchor resets on observed changes, new
turns, source gaps and new incarnations. A deliberately missed same-turn
working/blocked/working cycle disproves an exact or lower-bound phase-age claim.
The replay adds no provider reads/actions and changes no public/runtime contract.
