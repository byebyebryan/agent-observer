# Discovery, monitoring and contract readiness review

The subsequent [API v1 execution](stable-api-execution.md) and
[a2 producer gate](evidence/2026-10-06-stable-api/REPORT.md) close R1-R8 within the
accepted scopes. This dated a11 review preserves the original findings and proof.
Use the [client handoff](api-v1-client-handoff.md) for current work.

Date: 2026-10-06. Reviewed source: `7e0cbbe`; installed producer: `0.2.0a11`,
frozen source `06af32dc9f28aa5d356d6da6c0235ccc1056dac2`, wheel SHA-256
`999d45171adfc4c4e62fe57b417614c0814de2a556693a6d23bb97b45a0a8b65`.
This is an Observer review and consumer handoff, with no producer/frontend
implementation, provider actions, configuration changes or artifact selection.

The subsequent user decision is to bind native support to required contracts,
with no daily provider version/hash registration. The
[provider compatibility plan](provider-contract-compatibility-plan.md) supersedes
the original image-requalification direction. Sampled failures below remain
valid evidence of the current a11 implementation's overly restrictive gates.

The model is suitable for a pinned prerelease consumer baseline. A stable
contract freeze is premature: current provider upgrades have reopened native
operation acceptance, watch retention has reproducible defects, and transport
limits and compatibility rules need closure. Earlier G1/G2 proofs remain valid
for their exact images and topologies; they do not accept the upgraded executables.

## How discovery works

The public CLI collects one owning host at a time. The caller supplies host
authority and provider selection. Core has no SSH, Host Mesh, Tmux or frontend
dependency. Logical identity is the complete host/provider/store namespace/native
kind/native ID tuple. The namespace hashes provider, exact configuration path,
selector kind and UID; runtime birth is separate. Equal titles, UUIDs on different
hosts, cwd and Git/project names never merge identities.

| Surface | Current source and join | Bound and failure behavior |
| --- | --- | --- |
| Codex runtime | Existing managed Unix endpoint; kernel peer, listener, process birth and exact image checks; loaded IDs followed by exact `thread/read` metadata | No daemon spawn. Default 512 loaded IDs, configurable internal bound up to 2,048. Loaded inventory is read before history. Unknown/missing runtime is explicit. |
| Codex saved rows | Managed `thread/list`, joining full native thread IDs while preserving distinct `sessionId`; accepted current-store SQLite/header fallback when the runtime path fails | At most 1,000 catalog rows; activity ordering before the 100-row history cap; loaded rows survive the history cap. Fallback is partial and excludes blank history placeholders. |
| Codex activity/outcome | Latest turn metadata with `itemsView=notLoaded`, no conversation items; exact image capabilities select accepted clocks and outcomes | Conversation start/completion and explicit terminal outcome stay separate from runtime. Missing metadata does not use native catalog recency or file mtime. |
| Claude runtime | Bounded direct session registry/job-store reads, exact UUID/job links, Linux PID domain, process birth and open executable image | Installed image gates private metadata; worker image separately gates phase predicates. No native roster command that can adopt/write jobs. Registry/job ambiguity and unsupported images remain explicit. |
| Claude saved rows | Source-only pinned SDK in an isolated read worker; exact UUID merge with live rows; native titles and recorded cwd | 2,048-file census; bounded transcript tails and aggregate scan budget; 100-row display cap after activity ordering. Saved coverage remains partial. Sidechains never turn the parent UUID into a child. |
| Project context | Local recorded cwd, bounded `.git`/gitfile/commondir reads, optional configured root and relative path | No Git command or network. Linked checkout/common repository context stay distinct. Only explicit project mappings establish project membership across hosts. Failures preserve the session row. |

Provider collection is sequential, and native samples are not atomic. Each
dimension retains its own clock/health. Host-wide `collectedAt` is the end of
collection, not a common provider event time. Unknown classification stays
visible; `list` hides positively classified children by default. `snapshot`
retains the full inventory, including children.
Claude currently projects proved top-level conversation activity as user and
runtime-only/ancestry-unproved rows as unknown; it does not promise positive
classification and exclusion of every Claude helper context.

## How monitoring works

Phase is `working`, `blocked`, `waiting` or `unknown`. Runtime is `running`,
`parked` or `unknown`. Worker, attachment and last outcome are independent.
Running does not imply working; a completed turn can leave a running context
waiting. Parked does not have a working phase. Saved-only presence or an absent
worker is insufficient to prove parked.

Codex running means a currently loaded managed context, not an OS worker or
all possible execution contexts. Claude running requires the exact registered
worker checks. The accepted Claude 2.1.289 parked predicate additionally requires
a unique terminal done/stopped idle job, valid terminal clock, complete stable
inventories, no pending work and positively absent matching workers.

Approval/question predicates are image-specific. Claude foreground question
labels and blank background readiness remain unproved. Codex `systemError`
does not invent a work phase or substitute for a turn outcome. Current viewer
binding, conversation-specific focus/close, native event replay and hook-based
monitoring remain unsupported/deferred.

`watch` is an on-demand collector loop that pushes sampled full snapshots over
newline-framed stdout. It suppresses collection IDs and refreshed sample clocks
when comparing semantic content. Initial snapshot, change, heartbeat, gap and
resync frames have stream UUIDs and increasing revisions. Polling is serial;
there is no lossless event guarantee or shared collection daemon. Each concurrent
client currently pays for its own polling/history reads. A consumer must retain
its last snapshot on heartbeat, track stream continuity and mark gaps explicitly.

## Fresh installed/native comparison

Two bracketed rounds used `scripts/evaluate-observation`, independently reading
native metadata without importing Observer. CLI collection times on Snap were
`2026-10-06T17:18:53.418Z` and `17:18:58.688Z`. Both installed environments match
the frozen a11 wheel and public schemas. The comparison tool's success exit
means it produced an evaluation, not that all comparisons passed.

| Host/provider | Public rows and independent runtime scope | Result |
| --- | --- | --- |
| Snap/Codex | 51 rows; 6 loaded, including 3 user contexts and 3 children; default list retains 48 | Identity, membership, cwd and all 51 activity clocks match in both rounds. Five loaded phases match; one known child has native `systemError` and conservatively unknown phase. No proved mismatch. |
| Starship/Codex | 96 rows; 8 loaded, including 2 user contexts and 6 children; default list retains 90 | Identity, membership, cwd, all 96 activity clocks and 8 loaded phases match in both rounds. No comparison issues. |
| Snap/Claude | 30 saved rows; reference sees 3 accepted-image live UUIDs | Discovery and titles/cwd/ages survive, but runtime/phase are unknown because the installed CLI is now unaccepted 2.1.291. Both rounds record 6 runtime/phase differences against the narrower accepted-image reference. One second-round activity difference is a sampling race. |

Snap therefore has a partial combined feed: Codex current, Claude saved partial
with runtime unavailable and `runtime_artifact_not_accepted`. Its default list
has 78 rows. This does not mean the Claude workers stopped.

A later independent registry/kernel check found the three 2.1.289 workers still
alive, plus a 2.1.291 interactive worker under the existing `c95a4e70-0081-4ee0-b6c9-3925f2baa8c3`
UUID. All four records match PID birth, ownership and PID domain. The duplicate
worker context has unresolved phase/identity implications; the comparison
script skips the unaccepted image and is not an exhaustive reference for it.
Do not promote its selected older worker's phase to a unique native truth.

The installed Codex CLI has also advanced to 0.160.1 on both hosts. The same
image is accepted as a managed peer, but has no CLI `entry` capability. Passive
`prepare` for zero-row New rejects Codex on both hosts and Claude on Snap with
`runtime_artifact_not_accepted`. No execute/enter or provider launch was attempted.
This newly observed drift does not establish the cause of the user's earlier
silent Agent Plus Resume failure.

Evidence: [Snap evaluation](evidence/2026-10-06-contract-review/native-snap.json),
[Starship evaluation](evidence/2026-10-06-contract-review/native-starship.json),
[current images and preflight](evidence/2026-10-06-contract-review/current-images-and-preflight.json),
[worker contexts](evidence/2026-10-06-contract-review/surviving-workers.json).

## Findings and required closure

P1 means a current operational block or a public stream that cannot be consumed
reliably. P2 means a reproducible resilience/semantic defect or a decision needed
before stable contract publication. Controlled findings are not claimed native
transitions in ordinary sessions.

### R1 — P1: provider upgrade acceptance is operationally fragile

`native_artifacts.py`, `claude_snapshot.collect_claude` and
`write_client.prepare` gate exact images. This is deliberate, but an ordinary
upgrade currently disables all Claude runtime reads even for surviving accepted
workers, and disables both providers' New/Resume preparation. Peer acceptance
does not accept the Codex CLI executable.

Close by replacing provider release/hash allowlists with required-contract
compatibility checks, independently for discovery, worker presence, phase/age,
parked and entry. Preserve executable/endpoint/worker provenance and actual
incarnation revalidation. The observed releases, surviving workers and duplicate
contexts are test points for the replacement, not new hardcoded allowed versions.
Routine contract-compatible upgrades must continue without Observer rebuild or
release registration. See the linked compatibility plan for native acceptance.

### R2 — P2: watch retention drops last-known conversation age

`watch._retain_missing` preserves old phase/runtime evidence clocks, but changes
`activity.at` to null when a row disappears from a partial inventory. Activity
has no last-known clock field, and validation forbids a nonnull activity timestamp
with stale health. The installed public watch reproduced an accepted timestamp
`1700000010000` becoming null after gap/resync. The existing test named
`test_watch_gap_retains_partial_missing_facts_and_original_age` does not assert
conversation age preservation.

Settle the representation before freeze: keep current versus last-known activity
explicit and preserve the original event timestamp without renewing it. A new
field/domain requires versioned conformance and consumer validation; do not
silently insert fields into strict v2. Client-only historical display caches are
possible, but they are separate from current public activity evidence.

### R3 — P2: fresh child exclusion can be undone by watch retention

The CLI applies `listing` before `SampledWatch.sample`. When a previously visible
unknown row becomes a known child under partial coverage, it is removed before
reconciliation. Watch then sees a missing ID and restores the old unknown row.
The installed CLI reproduced this exact controlled transition with the child
visible again after resync.

Reconcile the complete fresh identity/classification inventory before filtering;
an authoritative current exclusion must win over retention. Add repeated partial
refresh and recovery cases. The separate Plus cache has a similar ordering risk;
fixing Observer watch does not accept the frontend cache fix.

### R4 — P1: declared row bounds and consumable wire bounds disagree

The public schema allows 4,096 sessions, but `decode_document` defaults to
100,000 nodes. A valid 1,024-row snapshot is only about 1.5 MiB and passes shape
validation, yet installed `list --input` rejects it with `node_limit`. The
4096-row synthetic sample is about 5.3 MiB, also below the byte limit.

Retention also has no size/expiry policy. A prior 4,096-row snapshot plus one new
ID under partial coverage raises `contract_row_limit` after retention, although
both input shapes are valid. A separate installed public-CLI test supplied valid
512-row partial inventories with changing IDs: the second frame contained 1,024
rows and failed its own wire decoder's node limit. Retention grew to 4,096 rows;
the next poll exited 2 with `contract_row_limit`, rather than a recovery frame.
This is controlled churn, not a proved ordinary workload today.

Align producer, snapshot/watch decoder, schema, byte/node limits and retention
budget. Test maximum enabled loaded/history inventories, serialized round trips,
repeated churn and bounded overflow/gap recovery. Any eviction must be explicit
and cannot establish native deletion or parked state.

### R5 — P2: one Codex live-row fault discards healthy sibling evidence

`codex_snapshot.collect_codex` sets `runtime_rows_read` only after every loaded
read succeeds. A controlled two-ID roster with a valid first row and an
unsupported status on the second stales the first row, drops the second and
marks loaded coverage failed, despite a verified unchanged incarnation.

Isolate row-local unsupported metadata/read failures where exact identity and
runtime ownership are preserved. Keep a partial roster and healthy facts, with
finite diagnostics for unresolved rows. Identity mapping conflicts or incarnation
changes must retain their stronger invalidation behavior. Do not guess the failed
row's phase.

### R6 — P2: write-result validation lacks cross-object identity invariants

`write_contract.validate_result` accepts a fabricated ready/confirmed result
whose resulting identity differs from its handoff's Resume reference. Shape
validation and the existing effect checks pass. Dispatch revalidates its plan;
this finding does not prove an erroneous native dispatch.

Bind operation, status/effect, requested/resulting identity and handoff semantics
at the public validation boundary. Include legitimate Claude copied-identity
results and confirmed-effect/presentation-failure cases. Clients should not need
to invent provider-specific checks to interpret a validated result.

### R7 — P2: the independent reference omits unsupported worker contexts

`scripts/evaluate-observation` skips Claude registry records whose executable
hash is outside its reference table. It supplies no corresponding runtime-gap
reason. Known-image duplicate UUIDs can also overwrite rows in its UUID map.
The separate kernel check exposed a current 2.1.291 record omitted by this path.

Report records and ambiguity explicitly, assess the required native contracts
without dropping new releases, and compare absence only within proved complete
scopes. Add independent helper tests for changed images with unchanged contracts,
incompatible metadata and multiple live worker records.
The evaluator is an operator tool, not a consumer discovery adapter.

### R8 — P2: stable compatibility policy is still incomplete

Strict unknown-field rejection works and all five exported schemas match the
bundled schemas. Plus's a3 reader schemas are identical to a11. However,
`history.sdkVersion` allows only `0.2.163`, so a history SDK upgrade couples a
provider implementation detail to the public accepted domain. The policy also
needs explicit coverage for Python imports, diagnostic outputs and write errors.

Before publication, distinguish wire versions, producer package versions and
native contract profiles. Resolve SDK-version extensibility with a
versioned change if needed. Define which CLI JSON surfaces and pure Python
symbols are supported, which diagnostics/human formats may evolve, the treatment
of newly encountered finite reason codes, and the required reader/cache transition
for incompatible changes. Do not add a second legacy collection stack.

Also settle capability scope: the currently unaccepted Claude source still
advertises working/blocked/waiting and running, although runtime is null and
runtime coverage unavailable. Per-row health prevents false facts, but clients
need an explicit distinction between an adapter's potential capability and one
accepted for the current image/context. See
[the diagnostic sample](evidence/2026-10-06-contract-review/capability-diagnostics.json).

Controlled evidence: [installed CLI cases](evidence/2026-10-06-contract-review/public-cli-reproductions.json),
[installed library cases](evidence/2026-10-06-contract-review/controlled-reproductions.json),
[row-local fault](evidence/2026-10-06-contract-review/row-fault.json),
[watch churn](evidence/2026-10-06-contract-review/watch-churn.json).

## What can be held stable now

Use the existing a11 wire-v2/read and wire-v1/write artifact as a pinned
prerelease boundary. Keep full logical identity, passive local collection,
separate runtime/phase/outcome/health, real conversation activity, explicit
coverage scopes and provider-independent New/Resume unchanged in the next pass.
No redesign of the core/network/client split is needed.

Do not announce stable release compatibility yet. R2/R4/R6/R8 need representation
and conformance decisions; R1/R7 need current native/validation acceptance; R3/R5
need resilience closure. Unsupported optional capabilities may stay unsupported
with clear reasons: foreground questions, exhaustive saved-only parked inference,
current viewer binding, native push/replay, networking and physical sleep/wake.
They do not require speculative compatibility implementations.

## Observer-only follow-up and client handoff

1. Formalize required native contracts and replace release/hash allowlist support
   selectors. Repair independent reference coverage and validate compatibility
   across current CLI/peer/worker contexts without daily release registration.
2. Repair watch age/classification/retention and serialized bounds; preserve
   healthy row evidence through row-local faults. Settle any required new wire
   version before changing strict schemas.
3. Complete write-result semantic validation and compatibility documentation;
   review pure reference consumers, maximum-size fixtures and failure cases.
4. Build and independently accept a new Observer artifact on Snap/Starship under
   G2, including contract-based native read/write/recovery and cleanup. Selection
   is a separate scoped gate. No Plus edit is used to make this producer pass.
5. A separate Plus agent consumes the accepted pinned interface. It can develop
   fixture-based presentation/cache/error handling against a11 now; repaired
   watch/native actions and rollout wait for the relevant renewed Observer gate.

The client instructions are in the adjacent Agent Plus checkout at
`../rofi-agent-plus/docs/observer-client-handoff.md` (relative to this repo root).
Producer defects discovered there return to an Observer checkpoint. Existing
Host Mesh and Tmux composition stay client-owned; OpenCode remains removed.

## Validation and limits

The unchanged source passes `./scripts/check`: 212 tests and the documentation
gate. Independent Draft 2020-12 validation checks five installed/bundled schemas
and seven canonical fixtures with `jsonschema 4.26.0`. All five a11/a3-reader
schemas match. Both installed a11 wheel environments pass byte/entry/schema
verification. A three-sample installed Snap watch yielded snapshot plus two
heartbeats at roughly two-second spacing, with a partial Claude feed. This is
bounded current read evidence, not renewed Claude monitoring acceptance or a
long-duration/multiple-consumer performance guarantee.

No ordinary session was started, resumed, stopped or changed. No native New/Resume,
held input, restart, suspend or graphical proof was run in this review. Native
fixtures from earlier reports retain their original acceptance bounds. Metadata
only is retained here; public-fixture/control tests do not accept new native
provider semantics.

[The check record](evidence/2026-10-06-contract-review/checks.json) also records
the documentation-only Plus handoff gate: 312 tests and its complete local check
passed, with no frontend implementation or native consumer acceptance.
