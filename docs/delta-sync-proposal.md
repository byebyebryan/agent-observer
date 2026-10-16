# Observer snapshot and delta synchronization proposal

Status: G0 closed and G1 implementation authorized, 2026-10-16. RLCD's shared
plan records acceptance of Mesh docs `ed771e5c8843dca718700c8b8b1d6804ae9134f0`
and the exact appendix/arithmetic review below. This document retains the proposal
and review reasoning; the accepted appendix and coordinator's final requirements
resolve its earlier open questions. No runtime/schema/artifact/installation or
service change was made during G0. G1 now proceeds on isolated branch
`observer-delta-sync-20261016` from `412e6ff`, preserving concurrent work.
Publication and normal service adoption retain their separate gates.

This responds to RLCD's `projects/agent-dashboard/docs/delta-sync-plan.md`.
Mesh owns the generic negotiated wire, result commitment, owned state cache,
proof, routing and delivery lifecycle. Observer owns authoritative change meaning,
the engine/service cache before IPC, domain admission and the pure read facade.
The [published a7 acceptance](evidence/2026-10-16-active-feed-publication/acceptance.json)
and [a7/a23 producer receipt](evidence/2026-10-16-active-feed/REPORT.md) remain the
baseline. Current full and active routes, Tmux, 349 and the writer stay intact.
Prior physical acceptance limits remain outside this planning pass.

## Recommended decisions

1. Add an explicitly negotiated sync family, with separate descriptors for full
   and fixed active inventory. Keep API 4, Service 4, active-feed 1 and all old
   Mesh profile/schema bytes unchanged. New protocol/profile IDs, package
   versions and lock checkpoint are unallocated. A proposed first sync-interface
   revision is independent of SDK 1 and preparation 1; it is not a claim that
   current interfaces already support incremental admission.
2. Use a complete baseline followed by atomic keyed transactions. Separate
   stable record content, per-field observation/support, source receipts and
   scope authority. A transport deletion is only removal from reconstructed
   state. It is never an implicit parked, excluded or presentation-retirement
   fact.
3. Compute normalization, field tokens, differences, encoded transactions and
   commitment updates once per owner generation and share them across local
   subscribers and Mesh publishers. An initial implementation may scan a native
   generation in O(N). Repeated head/proof calls must not invoke that scan.
4. Provide a fresh compact owner-head read after a proof nonce, plus bounded
   baseline/change acquisition. Mesh proves the exact independently admitted
   result and original receipts; a peer's digest alone supplies no authority.
5. Admit only changed bodies/facets and affected dependency indexes before an
   atomic commit. A new delta path must not call full `restore_native`, legacy
   frame validation, full snapshot export or whole-roster hashing internally.
6. Reconnect, missing base, gap, invalid transaction and retention overflow
   require explicit baseline recovery. No durable replay, occurrence-event
   journal, prior-identity reconciliation query or new presentation timeout.

The joint G0 closure accepts these choices as narrowed by the final appendix,
coordinator requirements and exact-byte review below. G1 freezes new schema/API
allocations and independently qualifies the implementation; existing contracts
are unchanged.

## Existing work and cost that must move

Source inspection of the current accepted implementation finds:

| Boundary | Current work | Proposed placement |
| --- | --- | --- |
| `ObservationEngine.publish` | Reconcile/validate a complete snapshot; build actual-value support and census | Preserve native semantics; produce indexed normalized state/diff once per publication |
| `ServiceState.publish` | Build the active projection once; cache serialized projected body | Commit full and active sync roots using the same engine result and original support |
| `ServiceState.frame` / `active_frame` | Expire, export and validate a complete native frame | Keep legacy route; new sync head/delta avoids this method |
| `Runtime._queue` / `_body` | Share encoded bodies by family/revision, but deliver complete bodies | Share encoded baseline/transactions; bound per-peer references to a base |
| `CachedAgentSource.snapshot` | Owned socket status read, full JSON decoding and strict frame admission | New owned baseline/change/head source; same authentication/lifetime requirements |
| Mesh `CachedPublisher.proof` | After nonce, call `native.snapshot`, copy/inspect/hash/validate complete frame | After nonce, query owner head, catch up bounded transactions, prove exact committed result |
| Current prepared guard/facade | Full generation preparation; active facade takes one full public snapshot per replacement | New incremental immutable indexes and public changed-key/current APIs; explicit full exports remain O(N) |

The [accepted producer study](evidence/2026-10-16-active-feed/producer-performance.json)
measured a7 full generation CPU near 40.82/197.43/831.03 ms and cached full
frame/encoding/parse CPU near 17.53/88.82/376.99 ms per read at 100/500/2,000
rows. Its active read cost was near 5.6 ms with ten selected rows. Those were
synthetic method-path measurements with different boundaries from actual
Runtime/transport; semantic hashing was excluded there. They motivate the
targets below but are not delta measurements or the final comparison harness.
No new runtime profiling is performed during G0.

## Native state representation

Working notation below describes semantics, not allocated field names.

Use two explicit binding layers. `NativeBinding` identifies the native contract
and schema digest, native host/UID scope, full-versus-active view and selector,
owner service incarnation, boot/time namespace, provider/namespace source
contexts and active scope continuity. `NativeRoot` commits that binding,
generation and all native table roots/cardinalities. The native owner is
Mesh-free and does not know a configured Mesh source alias or profile schema.
Record keys remain the full five-part identity. A title, native tree root,
presentation prefix or content digest cannot replace that key.

Mesh computes an O(1) `SourceRoot` wrapper over `NativeRoot`/native cursor and
its exact configured authenticated host, source alias and profile/contract
descriptor. That descriptor binds the expected native contract/schema. Mesh's
request/proof envelope separately binds nonce, route, order and channel/reader
incarnation. The reader independently recomputes both layers against its
configured expectations; equal native bytes do not transfer source authority.

Two explicit publisher aliases may share one socket and immutable native
objects without the service constructing a per-alias roster root. Full and
active each have their own native root and share underlying objects where
valid, within aggregate budgets. Native transactions name native base/result
roots; Mesh transactions and admitted handles additionally bind the source
wrapper. Reusing content never reuses authority tokens across cache/profile/
callback/source instances. Exact wrapper framing is a Mesh G0 closure item.

`CommittedState` contains separately indexed tables:

| Table | Content and change unit |
| --- | --- |
| Record content | Exact identity and stable API 4 content facets, referenced by canonical digest/revision |
| Observation facets | Original per-field observation wall clocks, health/provenance, timing attribution and actual support bindings |
| Receipt map | Current original native receipt tuples, at most the existing 32 per host |
| Support cohorts | Validated field-content bindings actually reobserved under one exact current receipt |
| Scope authority | Full coverage/capabilities or active coverage, members, uncertain/nonmember decisions and continuity |
| Owner metadata | Publication/collection anchor, native source diagnostics, readiness and bounded reasons |

The native result commitment covers every table, its identity/cardinality and
`NativeBinding`; the source wrapper adds the exact Mesh binding. Session content
cannot be authenticated independently of the evidence and scope roots that grant its current meaning. Observation facets are domain
data, not generic Mesh policy. No original inactive roster is hidden inside an
active root. Full inventory includes all admitted kinds/dispositions and keeps
its original uncertainty semantics. Native support remains Codex-only; reserved
provider data does not enable a retired or new adapter.

### Stable content is not an unchanged API 4 row

The exact factorization must be frozen by Observer before schemas are drafted.
Use typed, whole-facet replacement, not arbitrary client JSON Patch paths.
The encoder/decoder must round-trip every field, optional key and null value.

- Keep identity/native IDs, title, cwd, inventory, saved identity, kind value,
  workspace, creation metadata and actual state/event values in content facets.
- Preserve `activity.at`, native outcome `observedAt`, thread update `at` and
  turn start/completion/duration as native event/content values. A generic
  rule deleting every property named `observedAt` is incorrect.
- Put runtime/phase source-sample `observedAt`, timing observation `observedAt`
  and timing receipt attribution in explicit observation facets. Health,
  reasons, current/last-known distinctions and field support must be represented
  losslessly and validated together with the relevant content. An unsupported
  native state or changed error reason is a real facet change.
- Cache canonical content/facet bytes and digests once per changed object at
  owner publication. Digest equality is an optimization only after schema,
  identity and original-evidence validation; it never renews a fact.

The public diagnostic export must reconstruct the same API 4 rows and old
full-generation `collectedAt` when requested for that generation. The new full
sync metadata therefore explicitly retains that anchor. Active sync retains the
adopted runtime-observation age anchor per row. Neither mode uses fresh emission
time, a receiving host/device wall clock, or an inferred wall/BOOTTIME bridge.
The [active interface](active-feed-interface.md) describes the existing anchor
boundary. These exports are explicit O(N) operations, not internal delta gates.

### Evidence renewal without silent rebinding

Original support still means exact service/provider/namespace/context/component,
accepted counter, sampled BOOTTIME and expiry. A newer receipt at the same key
does not validate an old field. Failed, retained or absent fields are not
reobserved merely because their containing source succeeds.

Preferred compact form: one named cohort per current native receipt key, with
an immutable indexed membership mapping `(identity, recordBirth, field)` to a
validated field-content token. `recordBirth` is the native owner epoch plus the
generation in which this current slot was inserted. Removing and reinserting the
same identity creates a new birth even if its body is equal. This protects cache
instance authority and does not invent a provider session lifecycle. Its versioned head names the exact support tuple and
membership root. A domain encoder may advance that head without retransmitting
the membership only when every referenced field/value was actually reobserved
and the exact binding set is unchanged. Sparse changes patch the binding set;
the pure codec checks each new binding against its admitted content/facet token.
Changing a title alone need not invalidate an unchanged runtime facet token.

This is a new explicit assertion of actual observation, not interpretation of
a receipt update as a wildcard. The existing transient support capture before
retention supplies the owner knowledge. A missing/retained field is removed
from the current cohort or explicitly bound to its original old support as
context. Old support that no longer matches the current receipt map remains
context-only. No historical receipt bank or per-ID current lease slot is added.
The exact cohort rules are an open joint G0 contract decision; until agreed,
per-record explicit support updates are correct but cannot be advertised as
constant-cost renewal.

There is an important lower bound: current native adapters stamp individual
runtime/phase and timing observations during each read. A generation can change
N observation timestamps while all state values and stable bodies stay equal.
Preserving exact values requires O(N) small facet changes in that case. Count
them as K=N; do not label the sample a one-record update. Compact timestamp
vectors may reduce bytes later, but cannot discard those values or hide their
decoding/validation cost. Unchanged-generation proof, receipt-only renewal with
unchanged facets, sparse actual updates and real native sampling are separate
benchmark cases.

## Owner generation and local IPC

The reusable engine remains Mesh-free. After accepting/reconciling a native
sample, one owner publication builds/reuses typed objects and field tokens,
updates identity/dependency indexes, compares with the preceding committed
state, updates the commitment and encodes one transaction. Full and active
projections share native normalization and support work. Where possible compare
while traversing the existing publish loop rather than adding independent full
scans. Charge all retained O(N) normalization, hashing, diff and cache work.

Publication is atomic: native source/order checks, complete census, projected
membership, all changed objects and capacity must pass before exposing a new
root. A failed transaction exposes no partly applied records. Scope-local
uncertainty/capacity failure can be a valid explicit domain result, preserving
healthy scopes; encoding/admission failure is not a successful partial commit.

Proposed owner source operations, with operation-owned bounded resources:

| Operation | Result and cost |
| --- | --- |
| `baseline()` | Bound complete state and cursor; O(N), cold/recovery or explicit export only |
| `watch(base)` / `changes(base)` | Complete transactions from an admitted base, or explicit `baseline_required`; O(K + changed bytes + commitment index work) |
| `head(challenge)` | Fresh live-owner reply after the caller's validated challenge, exact committed root/cursor and original receipts; O(P), P <= 32 |
| `close()` | Cancel/reap owned reads/watch resources; revoke acquired source authority |

These are proposed source contracts; Mesh chooses public SDK method names.
The local service owns canonical commitment production because doing it only in
the publisher would retain full native IPC acquisition on each proof. Its pure
implementation can live in Observer or an independently reviewed transport-free
utility; core must not import Mesh to compute a state root.

Head requests authenticate the current socket/peer UID, inode/service binding,
boot/time context and scope, then read an atomic cached root and receipt map.
They never call current full `frame()`/`active_frame()`, native collection or
whole-roster `expire()->publish()`. Expiry attenuates original leases at head
or reader time in O(P), without rewriting all stored bodies. Scheduler-driven
state/health changes still publish once. A live service with no usable evidence
may answer a fresh head but grants no current membership/completeness.

A baseline is tied atomically to the subsequent watch cursor. Deltas occurring
during baseline delivery are retained within the shared budget or produce an
explicit gap; they cannot disappear between two independently opened streams.
Several subscribers reuse the same transaction bytes and immutable state.
There is no per-subscriber native collection, diff, full hash or baseline copy.
After a nonce head captures H, the compact proof succeeds only if the reader
already owns H. If its admitted state is G != H, the moved head grants no new
authority and immediately revokes that host's current claims. Catch-up to the
captured H happens separately under the absolute 15-second acquisition budget,
followed by a new nonce proof. No body chain travels inside the two-second
proof attempt. Concurrent H+1 publication does not rewrite the captured head;
a second move after the single permitted moved-head retry requires explicit
baseline recovery/failure inside the absolute budget. Evicted H or exceeded
catch-up quota also requires explicit recovery. A publisher at G cannot prove
retained G when its live head says H. Informational/UI context survives under
the existing uncertainty rules.

## Generic commitment, proof and incremental admission seam

Mesh should specify canonical domain-separated commitments for indexed tables
and root composition. Prefer a persistent keyed Merkle index with O(log N)
changed paths, including identity, type, value length and node/cardinality rules.
Each receiver recomputes changed leaf/subtree commitments against its owned
base, then checks the resulting root. A plain replacement root claimed by a
peer, or an order-independent XOR accumulator, is insufficient.

Native transaction binding includes owner incarnation, native descriptor/selector,
base cursor/native root, next cursor/native result root and exact changed object/
support/scope sets. Mesh adds exact configured source/profile binding through
its source wrapper without rehashing native tables. Duplicate operations, conflicting identities, dangling references and
unexplained removal are rejected before atomic publication. No arbitrary
content-addressed object from another host/source/profile can become an owned
body just because its digest is equal. Old-process/object tokens cannot be
replayed into a different profile instance or incarnation.

Proposed pure Observer profile hooks:

| Hook | Responsibility |
| --- | --- |
| `admit_baseline` | Full structural/domain/capacity validation once; build immutable identity, field-token, scope and dependency indexes |
| `stage_delta(base, operations)` | Validate changed content/facets, binding references and affected cross-record invariants; return an unpublished transaction |
| `commit(transaction, verified_root)` | Atomically expose the new owned state after generic and domain checks succeed |
| `check_head(state, head)` | Check exact source/selector/incarnation/current receipt references and original evidence limits without full restoration |
| `export_full(state)` | Explicit detached complete API 4/native diagnostic reconstruction, cost O(N) |

Mesh owns the opaque state/transaction capabilities and mutation-safe callback
boundary. No application can manufacture an admitted token from a mutable dict
or exploit a reused descriptor callback. Domain callbacks see immutable base
indexes and changed values; rejected callbacks cannot mutate the committed base.
This seam replaces full `NativeState`/`prepare_rules` work on the negotiated path;
it cannot secretly adapt those SDK 1 callbacks by reconstructing all records.

The staged context must publicly expose immutable keyed lookup, validated
field-content tokens, cohort membership and reverse dependency/scope indexes;
Observer must not inspect generic cache internals. The generic caller owns
root verification and invokes commit only after every domain check returns.
The domain transaction contains changed index nodes, changed prepared rules and
explicit removals, not a copied full owner record list. Proposed callback names
are illustrative; Mesh owns the final public signatures.

Changed keys update prepared rules and reverse dependency indexes. A receipt
head updates the cohort's usability without walking its entire membership just
to record that head. Queries evaluate exact support or visit genuinely affected
outputs. An expiration affecting N outputs costs O(N) when those N changes are
requested, with that cost charged. Unchanged cold-cache lookup does not call
consumer classifiers over every row or clone header arrays containing N refs.

Mesh's new fresh commit-proof path must be explicitly negotiated and reviewed;
lock 5's excluded/reserved digest-proof syntax remains unaccepted on old routes.
For each nonce: query the live local owner head after nonce admission, then
return only its source-wrapped root/native cursor, original receipts, source
clock and full request/proof binding inside the two-second proof budget. The
reader authorizes only an already owned, locally reconstructed native root with
the independently verified source wrapper. A moved head revokes that host's
current claims; perform bounded catch-up separately, then a fresh nonce proof,
all within the original 15-second acquisition deadline. No unproved candidate
field/completeness leaks into current output. A behind/stale proof cannot renew
a newer state or unrelated dependencies. Proofs retain original RTT,
margin, deadline, incarnation and source-liveness checks. Local or remote cache
body reuse is independent of the proof that its evidence is still usable.

## Domain lifecycle and public facade

Both sync descriptors preserve the three existing lifetimes: positive facts,
negative/completeness authority and external presentation context. Full sync
retains the complete admitted original roster and explicit unavailable/unknown
rows. Active sync retains only selected bodies, exact coverage and the existing
bounded recent-member exceptions. Complete-empty needs valid scope support even
when no record body exists. Partial omission never establishes parked.

Transport `remove(identity)` removes a key from this committed view. Retiring
prior presentation requires a separately current exact nonmember decision or
valid complete-scope absence authority. Positive expiry, pruning, missed negative,
overflow, source failure and reconnect are not such decisions. No new timeout
or eventual-retirement guarantee after arbitrary partial outages is introduced.
Per-field expiry remains independent: history loss may mask activity/workspace/
timing while valid runtime/kind still permits running membership. Native error
phase, idle/waiting, system/child exclusion and unknown kind retain a7 semantics.

The proposed public pure facade provides an opaque generation/cursor plus
changed current rows/facets, scope authority changes, exact current nonmembers
and uncertain context since an admitted cursor. It validates the reader clock,
delivery/incarnation and individual translated original deadlines before any
claim. Reader-current validation still precedes metadata inspection. The new
bounded header export contains roots/status, not an implicit full roster.

`current(now, clock, keys=...)` and incremental queries operate on owned indexes;
requesting all current rows still costs O(R) to return R detached bodies.
`snapshot()`/full diagnostic export is explicitly O(N). These costs are visible
in API documentation, counters and the benchmark. Accepting each delta must
not internally call public snapshot, inspect private Mesh storage, or fully
reconstruct/revalidate all rows. UI retention/sorting/display limits stay with
the consumer, including rows outside a 32-row display prefix.

## Bounded storage, loss and compatibility

Proposed initial limits for review:

| Resource | Proposed bound or behavior |
| --- | --- |
| Logical current view | Preserve existing native 4,096-record and 8,404,992-frame ceilings; factorization/support overhead counts, so some combinations fail earlier |
| Current receipt map/cohorts | Existing 32 receipts per host; at most one current cohort per key; no historical current-receipt bank |
| Field binding edges | At most 9 defined support fields per admitted record; scope-decision dependencies separately bounded |
| Active ledger | Preserve 4,096 identities and 1 MiB canonical whole-ledger accounting; scope-local explicit failure/continuity rules |
| Retained decoded roots | Current plus predecessor and one staged candidate; revocable tokens cannot pin older graphs |
| Encoded change journal | At most four generations and 8 MiB, inside the shared encoded budget; sampled state recovery only |
| Encoded sync retention/backlog | At most 32 MiB inside the existing shared 64 MiB service encoding budget, not 32 MiB per client; include baselines, transactions and pinned output |
| Owned decoded sync cache | Proposed 64 MiB aggregate per cache, including indexed current/retained objects, branch nodes, cohorts, staged transactions and queued updates; charge unique allocations at creation rather than scan N on each delta |
| Local subscribers | Existing maximum 16 clients; one pending transaction/base reference per slow peer, then explicit gap/resync or close |
| Old owned handles | Bounded cache tokens; retaining a token cannot pin unlimited old roots. Revoked/evicted base returns explicit baseline-required |
| Delta size | Existing frame ceiling; use explicit cached baseline replacement when a delta is not smaller, rather than an oversized chain |

Decoded nodes, indexes, retained branches and callback/consumer exports must
also be measured and bounded; canonical bytes are not an RSS bound. The proposed
64 MiB decoded budget needs joint ratification and concrete accounting of Python
overhead. Existing engine working memory and detached caller exports are
separate from this cache cap and remain inside aggregate RSS measurements. Count unique retained
objects once, plus each peer's pending envelope and references. Do not duplicate
unchanged full and active tables per subscriber or silently evict healthy
clients to maintain an unaccounted compatibility cache.

Reject wrong base/result, conflicting duplicate, out-of-order operation, unknown
identity/body/facet reference, schema/selector/profile mismatch and old owner
epoch. Exact retransmission may be recognized only under a bounded request/
transaction token, without executing effects twice. A gap, restart, clock-context
change, evicted base or failed validation revokes affected authority and requires
a proved baseline. A malformed peer cannot publish a partial result or force
native collection. Receipt watermarks and their bounded incarnation history
retain existing safeguards. Reclamation/cancellation closes owned sockets,
tasks, transactions and proof waiters; late work cannot republish retired state.

Old clients/publishers remain on their old fixed profiles and routes. New mode
requires matching owner sync source, Mesh negotiated descriptor and pure facade.
An explicit full baseline is recovery within sync mode, not silent fallback to
the older full source/profile. Trusted factory/source mapping remains explicit.
No migration or deployment configuration is changed by G0. Later service,
publisher, reader and consumer adoption requires paired rollback of the exact
qualified tuple, while preserving independent full diagnostics/Tmux/writer.

## Acceptance matrix and numeric targets for review

Targets are proposals derived from current cost inspection, not measured delta
results. Use exact future installed artifacts and a7/a23 replacement baselines
for the SAME full inventory; repeat with the SAME active inventory. Do not reuse
full-versus-active percentage savings as evidence for synchronization.

Freeze a representative matrix before timing: 100/500/2,000 records, 1/4/16
local subscribers, one and four reads per generation, initial/empty baselines,
unchanged generation,
receipt-only renewal, real N-row observation-stamp renewal, one changed record,
about 1% changed, all changed, sparse removals beyond a display prefix and
gap/reconnect/slow-reader recovery. Native collection cadence/bounds stay equal.
The primary value case is one subscriber and four reads per generation; report
one-read amortization separately. Four/sixteen subscribers exercise sharing,
resource bounds and capacity with total/per-subscriber work stated. A baseline
that misses existing deadlines is a capacity limit, not an equal-work CPU
comparison. No full Cartesian product is required.

| Gate | Proposed numeric target |
| --- | --- |
| Structural work | Zero whole-view restore/validation/hash/export calls on unchanged head/proof or a true sparse transaction; count K body/facet/binding changes, P receipts and D expired outputs explicitly |
| Unchanged local head | At most 2 ms median service+source CPU and 8 KiB application bytes at 100/500/2,000 rows; 2,000-row cost at most 2x 100-row cost with equal P |
| Full unchanged / sparse steady path | At 500 and 2,000 records, at least 70% lower incremental synchronization CPU; at least 90% fewer cohort-only application bytes and 75% fewer sparse-body bytes at each local-service/Mesh boundary, excluding cold baseline |
| Full same-output end to end | At least 50% lower measured CPU at 500/2,000 for four reads per generation, including generation/diff/hash/cache, local IPC, publisher, proof/admission/facade/application; any measurement exclusions explicit |
| Native generation overhead | Target additional diff/cache/commit CPU <=10% above a7, hard promotion ceiling <=25%; report any target miss and include all work in end-to-end totals; native collection is not slowed |
| Small active view | No total CPU regression over 10% or 5 ms per generation, whichever budget is larger; separately report incremental-path saving and unavoidable owner work |
| All-change / cold / recovery | No more than 25% CPU or bytes regression against replacement at each scale, respecting unchanged deadlines; prefer an explicitly cached baseline when smaller |
| Latency | Sparse commit visibility p95 no worse than matched baseline + 10 ms; no new native check cadence or deadline relaxation; report baseline/resync separately |
| Memory | At 2,000 rows, aggregate retained RSS no more than 1.5x matched baseline plus 16 MiB, with canonical/index/root counts and steady reclamation plateau; hard byte/client caps exercised |
| Correctness / cleanup | Exact full-row/field/support/coverage/identity and retirement-decision signatures; zero accepted partial/conflicting states; zero leaked owned tasks/processes/FDs/sockets after success/failure |

The head byte budget must include nonce reply, receipts and binding, not just a
digest. The 8 KiB performance target applies to the current native case with
at most four receipts; the complete 32-receipt protocol head has a separately
proposed 64 KiB hard ceiling, detailed below. No receipt is omitted to meet a target.
All-change/baseline comparisons include any expanded normalized metadata.
Small-input percentage noise and the added a7 generation cost must be reported
as absolute CPU too. A failing target triggers a review decision, not an
unannounced weaker test or premature artifact acceptance.

Run serial ABBA under the shared CPU lock, with exact original wall/BOOTTIME
field and support values, roster/cardinality/coverage and application output
held equal. Include canonical/hash comparison in measured workloads. Report its
cost separately as well; an independent whole-view oracle is not a free hidden
setup phase. Instrumented allocations are separate from uninstrumented CPU;
keep excluded/timeout samples visible. Report application bytes, IPC/SSH wire
bytes, encrypted endpoint CPU where measured, full-export frequency, latency,
unique retained generations/objects and cleanup. Synthetic remote-proof policy
over IPC is not SSH crypto. Percentages from different boundaries are not added.

Correctness must cover receipt-only changes without positive renewal, independent
history/runtime expiry, retained old field under a newer same-key receipt,
kind/error/activity/outcome changes, complete-empty expiry, partial/missed-negative
uncertainty, namespace/context/continuity changes, owner restart, malformed
base/result/duplicate updates, callback/export mutation, cancellation and
backpressure. Initial baseline and applied-delta results must agree with an
independent full-state oracle at every committed generation. Ordinary native
comparisons, exact installed IPC/fixed SSH and old full/Tmux compatibility are
separate producer gates; live fleet/device acceptance remains with RLCD.

## Proposed resolution of the coordinator's initial review

These details narrow the preceding recommendations and await Mesh's matching
public API/specification plus RLCD ratification. They are not implementation.

**Value case.** Apply the 50% total CPU target at 500/2,000 full records and four
reads per generation to unchanged generations, actual same-set cohort renewal,
one/1% content changes AND production-shaped N-row timestamp refresh with stable
content. Require at least 50% total application-byte reduction in that last
case at each local-service and Mesh boundary, counting complete baseline and
all observation/support changes over at least six generations. The 90% cohort-
only and 75% sparse-body byte targets are separate. The <=25% all-change
allowance is for all stable bodies actually changing, not a loophole
for receipt/timestamp refresh. One-read and subscriber scaling cases still
report end-to-end costs and the regression/resource limits, without asserting
that four-read amortization applies to them. Preserve actual timestamps in both
arms. If these value targets fail, return the measured case to G0 review.

**Exact typed split.** Proposed content is the complete API 4 row with only
these paths moved into a lossless per-row observation object:

```text
runtime.health, runtime.observedAt
phase.health, phase.observedAt              (only when phase is non-null)
activity.health, outcome.health
lastUpdated.health, lastUpdated.observedAt, lastUpdated.receipt
latestTurn.health, latestTurn.observedAt, latestTurn.receipt
```

Every other field and optional key stays in content, including outcome event
time, last-known values and reasons. No coalesced batch timestamp substitutes
for the moved per-row values. Domain validation checks the joined changed row
and support, while caching its validated content/field tokens. Changes to error
reason, current/unknown values or last-known representation remain real content
changes. Changes to moved paths are real observation changes.

A cohort membership entry can use an admitted record key plus a 9-bit field
mask; the receiver computes and caches the referenced field-content tokens.
Its sealed membership root commits each identity/birth/field and its exact token,
not just a row count or mask. Tokens need not be repeated as 64-character wire
strings for every cell. Runtime tokens include runtime value/source/reason/clock;
phase tokens also include blocked reasons; activity/outcome/timing tokens include
their actual event/content values; kind/saved-identity/workspace tokens include
the corresponding identity-dependent content. Observer must freeze this token
extraction table and vectors with the schema. Altering only a title cannot
validate or invalidate unrelated runtime support.

The exact token input proposal is the following. Every token is domain-separated
and includes full identity, current record birth and the field name, followed
by the canonical typed value below. Preserve optional-key absence separately
from present null. These tokens bind content, while all original observation
fields and exact support still live in the other committed spaces.

| Field | Canonical value committed by its field-content token |
| --- | --- |
| runtime | Entire runtime object except the moved health/observedAt paths |
| phase | Phase object except moved health/observedAt, plus complete blockedReasons; null remains null |
| kind | Exact kind value |
| savedIdentity | Exact inventory and hasSavedHistory pair |
| activity | Complete activity object except moved health |
| outcome | Complete outcome object except moved health, including native outcome observedAt |
| workspace | Complete workspace value plus cwd and cwdSource |
| lastUpdated | Complete lastUpdated object except moved health/observedAt/receipt |
| latestTurn | Complete latestTurn object except moved health/observedAt/receipt |

A token can bind an explicit unknown/negative value when the native adapter
actually observed it; existence of a token alone grants no positive state.
Cohort validation checks exact observation health, chosen component and original
support separately. No field inherits authority merely because it shares a
body or content digest with a supported field. Schema/domain constraints still
apply to the reconstructed changed row.

**Order and commit granularity.** Full rows retain the engine's exact order:
`(runtime.value != "running", full five-part identity)`. Maintain a committed
ordered index with that key, so a runtime disposition/identity change updates
only its affected slot. Do not assign shifting integer positions to every row.
Active export retains original bounded source/scope order, then identity order
within each scope, matching the owner projection. Commit the bounded scope
order explicitly; membership/decision lists use their existing identity order.
The export and independent oracle compare those arrays in order. Other bounded
owner arrays retain their original order in metadata, rather than being silently
canonicalized for a convenient digest.

Each native transaction and proof confirmation is atomic per host/native source
view; it is not a cross-host transaction. Mesh's aggregate view fixes ordered
host selection/catalog/route and exact per-host confirmed tags. A host move or
failure revokes that host's authority; other confirmed hosts keep only their
own original leases. Reader aggregate readiness and detached output must expose
those per-host states without publishing a candidate host as confirmed. Full
and active views are separately configured contracts, not an implicit atomic
pair. Exact generic aggregate handle semantics remain Mesh-owned.

A same-set renewal is admitted only when: the owner asserts actual reobservation
of that exact sealed set after retention is excluded; service/context/component
match; accepted/sample/expiry are valid and nonregressing; the head's sealed set
matches the receiver's already validated immutable membership/content-token
root; and all changed observations/bindings/receipts are in the same atomic
result commitment. A subset observation explicitly removes/reattributes missing
cells before renewing its new set. Old cells remain informational with their
original refs and cannot inherit the renewed head. Neither a new receipt key nor
a matching digest alone meets this predicate.

**Mesh-free commitment.** Proposed normative algorithm owner is Mesh, with
independent stdlib-only Observer implementation and shared immutable vectors.
Use SHA-256 over the agreed canonical JSON byte encoding with explicit domain
tags and length framing. Keys hash canonical typed original keys. A compressed
binary Patricia tree commits leaf key/value bytes and branch prefix/split plus
child hashes; canonical shape depends on keys, not insertion order. Reject an
observed key-hash collision with different original keys. It has at most about
2N nodes per table, rather than allocating 256 nodes per key. The native result
root commits all table roots/cardinalities, native contract/schema, owner/selector/
clock binding and generation. The O(1) Mesh source wrapper commits that root plus
exact configured host/source/profile binding; it is not part of native owner
configuration. Only changed paths are recomputed; sorted full-table rebuilds
are not the sparse receiver path. Mesh must supply empty/singleton, insertion-
order, replace/delete, cohort/receipt-only, context mismatch and invalid-root
vectors before dependent schemas/code. This avoids a Mesh import in core and
an unrelated third package. Exact framing/Patricia rules still need Mesh approval.

**Commit versus fresh head.** Committed original health, counters, source support,
per-row wall/BOOTTIME observations, coverage and generation collection/publication
metadata are root-covered state. A head adds only nonce/challenge, acquisition
clock and monotonically attenuated remaining/effective usability. It cannot
replace accepted/sample/expiry or turn an originally unavailable fact current.
Zero remaining lease means no current authority even if a committed object
remains available as context. An actual failed observation or context change
produces a new committed result; mere time passage need not hash all bodies.

`export_committed()` reconstructs the exact committed API 4 snapshot, including
collection ID, `collectedAt`, host/source/capability/coverage metadata, errors,
limitations and all row fields. Active export reconstructs its exact committed
active DTO and original runtime-observation age anchors. Full versus active
identity/scope meanings remain distinct. These are explicit diagnostic exports;
they do not grant query-time currentness. Current query output applies the
existing domain expiry/uncertainty rules before exposing any positive claim.
Transport sequence, challenge, acquisition/emission time and proof remaining
are new per-delivery envelope fields, not a fabricated old Service 4 emission.
A legacy Service 4 response still comes from its original endpoint; the new
sync reader does not synthesize a fresh legacy envelope around stale evidence.

**Hard budgets.** The 64 MiB decoded sync-cache cap is aggregate across shared
full/active roots, persistent index/cohort nodes, staging and pinned generations
inside one owner service. An overlapping immutable object is charged once.
Independent publisher/reader processes each enforce the same per-cache cap;
the benchmark counts their aggregate RSS too. Allocation accounting includes
Python node/container overhead at object creation and reference reclamation;
a whole-cache `getsizeof` walk on every transaction is not accepted. Existing
engine working state and detached application exports are measured separately,
not hidden inside a canonical-byte estimate.

The 32 MiB encoded budget is also aggregate across full/active and all peers,
inside the unchanged 64 MiB total service encoding budget. Only current plus
predecessor decoded roots and one staged candidate are retained; the encoded journal is at most four generations/8 MiB. The first
exhausted generation/byte cap wins. Cache handles are revocable lookup tokens, not owning
references that can pin an unbounded old object graph. A consumer requiring an
expired token gets baseline-required and affected authority is revoked.

Compact proof contains no body catch-up: its two-second deadline includes the
fresh head and independent root/receipt/request checks only. A moved head
revokes that host's current claims. Separate catch-up is at most four atomic
transactions and 8 MiB changed data, with at most one moved-head retry, inside
the absolute unchanged 15-second acquisition budget. Then obtain a new nonce
proof. Exceeded quota, evicted target or a further move requires explicit sync
baseline recovery/failure inside that budget; retained old results are not
proved instead. At most one pending target/proof waiter per operation and
existing connection/subscriber caps apply. Baseline recovery is counted and
cannot loop indefinitely during an update storm.

Proposed complete head hard cap is 65,536 bytes, separately from unchanged legacy
control/envelope limits. Budget <=8 KiB fixed binding/challenge/table-root/clock
data, <=768 bytes per original receipt and <=384 bytes per cohort head, with
at most 32 of each: <=45,056 bytes before reserved head slack. Config-home paths,
record keys/cell lists and scope bodies are not copied into the head; their
committed roots bind them. Enforce every entry cap and the complete byte cap,
including exact support and both endpoint clocks; if a legitimate reviewed
representation exceeds it, reject explicitly or revise G0, never truncate.
The two/four-receipt native performance case retains its 8 KiB target. Include
a full 32-receipt/cohort boundary vector, not just an estimate, at G1 freeze.

## G0 resolution checklist retained for implementation

1. Mesh's canonical keyed commitment and incremental SDK transaction/handle
   ownership: agree exact tables, subtree validation, scope binding, revocation
   and token lifetime before writing native schemas.
2. Ratify cohort membership plus exact support-head renewal, or explicitly
   accept O(N) support updates as a first pass. Preserve real per-row timestamps
   in either choice; they can make a generation genuinely metadata-dense.
3. Freeze Observer's typed content/observation factorization and lossless API 4
   export, including native outcome times, last-known variants and both age
   anchors. No inferred observation time or fabricated phase-entry clock.
4. Agree local baseline/watch barrier and compact head-after-nonce interface,
   original receipt root versus query-time expiry attenuation, and changed-root
   catch-up ordering. The current full snapshot callback is insufficient.
5. Ratify current/predecessor/staged decoded roots, four-generation/8 MiB encoded
   journal inside 32 MiB aggregate, the 64 MiB decoded-state bound, separate
   catch-up work and when explicit baseline replacement wins. These are resource
   choices, not an event replay guarantee.
6. Ratify numeric CPU/bytes/latency/memory targets and the exact matched harness,
   particularly small active views and real all-row observation renewal. G0
   currently has no new measurements or accepted performance claims.

## Current agreement and remaining closure inputs

Observer accepts the coordinator's final G0 reconciliation in the shared plan,
including the separated proof/catch-up budgets, moved-head host revocation,
current/predecessor decoded-root policy, encoded journal and final numerical
gates recorded above. These supersede this draft's initial tighter regression
proposals and earlier proof-with-catch-up sketch; they are explicit pre-measurement
review choices, not results. Observer accepts Mesh's parallel source/cache/reader/
view split and immutable `PublicStageContext` / frozen `DomainIndexPatch` callback
shape. Profile instance/callback/cache ownership and per-host atomic confirmation
remain required; no legacy full restore adapter implements the incremental path.

The exact native lossless split, nine field-token inputs, birth-bound cohorts,
full/active export order and native/source two-root split are now concrete
Observer proposals. Remaining joint inputs are Mesh's exact native/table/message
framing and canonical Patricia/root vectors, final public context/index-patch/
handle signatures, and counterpart agreement on those domain inputs. The G0
contract appendix must be readable and agreed before native/runtime/schema work;
a statement of directional agreement alone does not release that gate.

## Exact appendix arithmetic review

The Mesh appendix became readable on Starship at
`/home/bryan/code/mesh-plus/docs/delta-sync-contract-appendix.md` while Mesh was
still revising it. Observer captured separate exact revisions; no mutable-path
acceptance is claimed. The latest reviewed capture is 28,802 bytes, SHA-256
`a376bc848a78027d4fd723e8a2959dbbc4e00114da132d3a5d2733a6ebce2eb6`.
Its capture, independent stdlib-only `reproduce_vectors.py` and
`vector-results.json` are under this checkout's
`.cache/delta-sync-g0/a376bc848a78027d4fd723e8a2959dbbc4e00114da132d3a5d2733a6ebce2eb6/`.
Script SHA-256 is
`67a29dabb4abff4d945d257edf4d1be30e87b7b804817323a77da79041c47d54`;
result SHA-256 is
`2e3efc5fa5cafe4ff4064300f8bb0d34af46115fc55e8ce6fd572a296e495792`.

All 20 documented hash vectors match independently, including the non-byte-
aligned branch and birth-bound cohort roots. The canonical Unicode/escape fixture
matches; 720 six-key insertion permutations agree; strict canonical/duplicate-key
rejection checks pass. This is documentation arithmetic, not an incremental
runtime implementation or schema/native/performance acceptance. Exact joined-row,
field-token, cohort-renewal, transaction and maximum-head gates remain at G1 freeze.

The reviewed staged/index/head/source-wrapper/aggregate shape is suitable. The
latest revision resolves the stable logical cohort ID versus immutable seal
version: a one-cell change updates affected membership paths and the head,
without rekeying unchanged members. Current support resolves a validated cell
and the exact seal/head of its admitted state; only explicit actual reobservation
permits a new head to authorize that current set. Retained context preserves its
original exact refs and cannot follow a new seal/head. G1 must demonstrate
changed-key/visit counts, including no hidden N-cell observation-ref rewrite.

This exact revision explicitly defines provider/namespace context binding even
for empty/unavailable scopes, the existing identity field names
`hostScope`/`nativeIdKind`, and bounded idempotent source/watch/publisher/reader/
stream cleanup. Source close never stops the shared native owner; externally
owned clients can serve two aliases with independent authority and watch
lifetimes. Staged/index/head/source-wrapper/aggregate callbacks and capability
ownership fit the domain requirements. Observer confirms G0 contract/arithmetic
acceptance of the exact appendix hash above with no remaining conflict. Later
changed bytes require a separately identified review. Mesh identified intended-
final docs commit `ed771e5c8843dca718700c8b8b1d6804ae9134f0`; Observer verified
its committed appendix is byte-for-byte equal to the capture above. Both owners'
same-byte confirmation is complete. RLCD has now explicitly closed G0 in the
shared plan, releasing implementation under the existing authorization.

Changes to accepted semantics require an identified amendment and joint review.
G0 closure releases G1 implementation on the isolated Observer branch. No runtime,
package, native, performance or deployment readiness is claimed by this document.
