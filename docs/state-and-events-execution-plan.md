# Local native event implementation and acceptance plan

Date: 2026-10-09. Follows the reviewed
[state/event design](state-and-events-design.md) and
[research evidence](evidence/2026-10-09-state-and-events-design/REPORT.md).
This plan is ready for a subsequent implementation goal. The current research
request authorizes study scripts/docs only, not these production changes or
ordinary hook selection. Keep accepted state/read behavior usable throughout.

**Deferred:** the following E0–E5 packages retain future implementation gates.
The subsequent user decision prioritizes the
[state-only design and plan](state-push-execution-plan.md), without native event
normalization, callback installation, replay or Kitty/D-Bus work. These packages
are not dependencies of existing discovery/monitoring push or read clients.

## E0 — freeze the independent event contract

Export event record wire 1 and local event protocol 1 in their own schema/facade
namespace; do not reuse the experimental policy-bearing notification schema.
Freeze request/frame shapes, event meanings, exact metadata provenance, cursor
scope, nullable fields, bounds, finite errors and pure-client guard behavior.
Keep API 2/read wire 4/Service 2 unchanged. Select explicit read/intake endpoint
paths inside the owned service runtime directory; intake is not a public read
operation. Specify live/retained/after starts and immutable replay IDs.

Acceptance: strict schema and semantic conformance, malformed/duplicate-key/
scope/epoch tests, import isolation from providers/actions/hosting/alerts,
receipt-versus-correlation checks and an independent client conformance example.
Publish a small event client handoff before downstream event implementation.

## E1 — passive sources and neutral emitter

Implement allowlisted pure normalization separate from current experimental
alert dispositions and formatting. Codex notify and Claude PermissionRequest,
Notification/Stop/SubagentStop retain their distinct meanings and actor scope.
Prove capability selection: documented but untested source meanings must remain
unsupported, not enabled by a broad callback-name match.

Provide a small same-user, bounded emitter for explicitly selected callbacks.
It binds configured host/provider/store scope, strips content before intake,
does no title/native query, and returns neutral hook output on every failure.
Set finite parse/write/connect deadlines; no autostart, control fields, journal,
terminal output or provider settings installer. Hooks remain optional for state.

Acceptance: source semantics, malformed/oversized inputs, actor/root separation,
exact scope mapping, metadata-only/no-log privacy, unavailable endpoint and
slow/saturated intake all preserve provider control flow. Prove emitted bytes
and latency independently; do not count a source test as desktop delivery.
Add dependency checks that event emission cannot enter action/attachment code.

## E2 — service-owned intake and local event delivery

Host callback intake and source health in the existing local service. Reuse
owned passive listeners where appropriate; no provider work per event reader.
Enrich only from existing exact-reference cache with explicit health/revision;
missing or late titles cannot stall ingress or rewrite published events.

Implement bounded in-memory replay, epoch/sequence cursors, loss floor, atomic
replay/live barrier, source status and independent subscriber bounds. Start with
256 records/1 MiB/five-minute retention and a 16 KiB record ceiling; report and
validate these operational choices. State and event streams have separate
queues/envelopes/failure domains in one service process.

Acceptance: controlled concurrent producer/reader tests for admission ordering,
replay/live race, empty expired ring, future/old/wrong-scope cursor, restart,
duplicate correlation, byte/count/age overflow, hidden-filter checkpoint and
blocked control delivery. Inject input/helper faults independently of state;
accepted snapshot/watch remain responsive and do not renew evidence falsely.
Measure aggregate memory/CPU/latency with slow readers and saturated intake.
Keep detectable input loss distinct from delivery loss and unknown native loss.

## E3 — read-only event inspector

Add explicit CLI status/live/replay inspection using the pure facade and local
read transport. Show source capabilities, epoch/cursors, actor, scope, unknown
metadata and loss visibly. Offer JSON output and client-side filters that retain
scanned progress. No Kitty/desktop output, hook installation, provider actions,
TUI matching, mesh or implicit fallback/autostart.

Acceptance: CLI parser/exit semantics, disconnected/warming/disabled source,
bounded replay and sparse-filter progress. A CLI reader must add no provider
queries/helpers beyond the selected service sources. Current direct/cache state
commands continue to pass their independent comparison workflow.

## E4 — immutable producer and native acceptance

Package an explicit candidate only after source/conformance checks. Repeat native
isolation before launch and compare installed candidate output to independent
provider facts, never another Observer result. Capture artifact/hash/version
provenance as diagnostics, not compatibility allowlists.

Codex on **Snap and Starship**: concurrent interactive roots, native thread/turn
mapping, passive stream scope, exact callback correlation, known/unknown child
classification, missing/renamed title, source loss and restart/replay. Keep failure/
interruption/headless cases unsupported unless separately proved. No thread
resume/load by the observer to obtain detailed events.

Claude on **Snap**: held PermissionRequest and delayed Notification, same-prompt
Stop continuation, child actor under parent UUID, missing title, native alerts
on/off and Agent View on/off where configuration affects accepted scope. Prove
idle/elicitation only if included as supported capabilities; no background job
compatibility. Never approve the held test tool. Test neutral emitter failure
alongside ordinary parallel hooks in isolated configuration.

Acceptance: exact event/source/cursor meaning plus independent state comparisons,
source faults do not settle parents or change phase/age, no raw content evidence,
bounded read latency/resource behavior, and exact owned cleanup. This accepts
the producer/read candidate only; GUI actions and physical devices remain separate.

## E5 — scoped Observer operations

Only after separate rollout authorization: select the immutable read/service
candidate, inspect source/managed/installed/live tuple, test restart/crash/
rollback/reselection and ordinary native/CLI state plus event status. Event
source installation needs explicit managed hook/notify selection in chezmoi,
with preservation of unrelated hooks and native control/duplicate behavior.
Do not alter native alert policy just to accept the local event producer.

A service with disabled/unselected callbacks is valid: existing state works,
event coverage is explicitly unavailable/partial, and it emits no desktop alerts.
Document whether newly selected hooks require new provider processes; do not
assume old sessions acquire changed callback configuration automatically.

## Independent client and networking gates

After E0/E4, client work can use the frozen event interface without joining the
producer dev cycle. Producer defects reopen an Observer checkpoint, rather than
causing simultaneous frontend changes.

The 349 request can drive a later alert-client pass: sender/title/static messages,
chosen child/unknown policy, native-versus-custom duplicate selection, Kitty
unfocused delivery, originating terminal/pane and desktop/physical Open. Its
historical preferences do not constrain other clients' event consumption.

mesh-plus consumes accepted local state and optional event envelopes in its own
repo, with authenticated routing, original source clocks/epochs and loss. No
network code or physical suspend/wake proof is an Observer event gate here.

Each gate records static/synthetic, controlled transport, immutable native and
operational evidence separately. Commit only reviewed scoped changes after
`./scripts/check`; do not infer deployment or sibling-repo edits from a source
or design checkpoint.
