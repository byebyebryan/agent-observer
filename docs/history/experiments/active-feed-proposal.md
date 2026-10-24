# Observer active-feed proposal

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Historical interface: withdrawn in source candidate 0.7.0a9. See the
[current retirement guide](../../read-only-retirement.md). Frozen definitions and
prior release receipts retain their original scope.

Status: Observer G0 planning confirmation, 2026-10-15 local / 2026-10-16 UTC.
This records the reconciled planning choices with RLCD and Mesh. It accepts no new contract,
reserves no package version, and authorizes no implementation, installation,
provider action or role selection. Names below are proposed interface names.

The coordinator's plan is
`esp32-rlcd/projects/agent-dashboard/docs/active-feed-plan.md`. Its private
`.cache/cpu-investigation/20261016T042557Z/FINDINGS.md` and `findings.json`
were inspected read-only. That dated additional reader received 9,798,780 bytes
in 60 seconds for 498 cached identities and ten selected bodies; composition
and admission used 57.5% of its Python CPU, visible projection 0.2%. These are
diagnostics, not a performance target or independent native completeness proof.
The cached Snap population in this later study does not replace the earlier
[a6 acceptance](../../evidence/2026-10-15-prepared-selection/REPORT.md), whose Snap
native gate was empty. No native reads were run for G0.

## Proposed source and API boundary

Host a pure Observer projection/cache in `ServiceState`, immediately after an
accepted reconciled engine generation and before local service IPC encoding.
The optional networking source then reads this projected service view before
Mesh's publisher IPC or fixed SSH transport. This avoids moving a full-roster
transfer and scan into every proof request at `CachedAgentSource`.

Proposed ownership and interfaces:

| Location | Proposed responsibility |
| --- | --- |
| `agent_observer.active_feed` | Mesh-free selector, projection state, strict projected-wire validation, membership decisions and pure expiry/reconciliation helpers |
| `ObservationEngine` / `ServiceState` | Supply the reconciled generation and exact supporting receipt bindings; host one configured selector/cache, including lease-expiry publications |
| `service_runtime` | Explicit opt-in projected request dispatch and bounded fan-out; share immutable encoded projected bodies across subscribers |
| Optional `mesh_source` / publisher factory | `CachedActiveAgentSource.snapshot()` and `watch()`, projected native admission, explicit source/selector/profile selection |
| Optional active Mesh profile/read facade | Pure codec/profile callbacks, supported prepared active read with current members, uncertainty, positive nonmembers and per-scope coverage |
| Mesh | Generic catalog, routing, negotiation, schema lock, proof, receipt conversion, order, delivery and resource cleanup |

Core, local service, validation and reconciliation import no Mesh modules.
The service hosts the projection; it does not gain external meshing ownership.
The existing full Service 4/API 4 inventory remains separately available.
Hosting this cache needs a later Observer service artifact/adoption gate; an
optional publisher update alone cannot enable it in an old collector.

Proposed public names/shapes, to freeze only after joint review:

```text
ActiveFeedProjector.accept(accepted_view, support, receipts) -> immutable generation
validate_active_frame(raw, *, expected_host, expected_selector) -> checked frame
CachedActiveAgentSource(host, socket, *, selector).snapshot() / .watch()
ActiveAgentProfile(*, selector)
PreparedActiveAgentWatch(request_id, *, host_ids, profile)
    .accept(admitted_mesh_response_or_raw_aggregate)
    .read(now_ms, reader_clock) -> ActiveAgentRead
    .disconnect()
```

`ActiveAgentRead` separates current member bodies, informational uncertainty,
current positive nonmembers, query-time scoped completeness and raw context.
Its positive/complete outputs contain only claims whose dependencies pass at
that read. Consumers may reconcile earlier context with these explicit results;
raw context is never a retirement result. The new facade's interface version 1
is distinct from existing prepared Agent read interface 2. It owns no I/O,
native observation, reconnect loop, timer, display cap or context-hiding policy.

The selector syntax is provider-neutral, but the first supported descriptor is
fixed: Codex, `{user, unknown}`, running/current. Other combinations require
explicit review and fail as unsupported in the first pass. There is no phase,
title, activity-age, display-prefix or arbitrary callback predicate. This syntax
does not enable a retired/unimplemented native provider. Configure one active
selector per service in the first pass; reject another descriptor explicitly.
Canonical ordering and deduplication produce a selector digest. No subscriber
can cause native collection or create an unbounded selector cache.

Cache by service/projection incarnation, source context generation, owner view
revision and selector digest. Project each accepted generation once, including
failure/expiry generations. A fresh cached status operation after a proof
request emits a new checked header around the same immutable projected body;
it does not copy a previously received watch frame or re-run native reads.
Header emission, encoding and nonce work remain per operation. Public raw
projection/admission entry points remain strict; any internal reuse requires
an owned immutable generation, never a borrowed dictionary or digest alone.

The first implementation may scan the full admitted engine generation once.
Collection/history traversal and full-inventory publication remain separately
measured costs. Neither O(active) collection nor eliminated producer roster
work is claimed. Never nest the original full snapshot in a projected reply.

## Membership meaning

A member has an exact five-part identity (host, provider, namespace,
native-ID-kind, native-ID), positive current running evidence, and a selected
kind. Codex `idle` is running/waiting; active/blocked/capacity-error/system-error
threads remain running according to their admitted native runtime predicate.
Phase and outcome uncertainty do not remove membership. Known child/system
classification excludes a row only with valid classification support;
unknown kind is included in RLCD's selector.

Positive parked still requires the reviewed current saved-thread `notLoaded`
predicate. Loaded-list absence, client/process exit, age, saved-history presence
and an omitted projected row establish no parked fact. Retirement from this
selected feed also establishes no session deletion, end, acknowledgement or
action permission.

Each replacement has three identity entry variants plus one coverage authority
per covered provider/namespace. A native identity appears in at most one
identity variant. All subscribers of the selector receive the same replacement.

| Entry | Meaning and authority |
| --- | --- |
| Member | Full unchanged API 4 row body plus exact membership/field dependencies in projected metadata; positively selected under unexpired original evidence |
| Uncertain | Compact exact identity, bounded reason and prior membership binding; optionally a fresh native-unknown receipt, never a refreshed prior body |
| Nonmember | Compact exact identity, selected predicate that failed, positive parked or confirmed excluded-kind reason, original supporting receipts and decision order |
| Scope coverage | Selector-bound `complete`, `partial`, `warming`, `stale`, `unavailable` or `unsupported`, reason and supporting receipts; only fresh `complete` grants absence authority |

Uncertain/nonmember entries concern recent selected members, not every inactive
saved identity. Initial unknown historical inventory does not produce thousands
of uncertainty summaries. Unresolved potential members not individually covered
remain explicit through partial scope coverage. A new client cannot display an
identity/body that has never been observed; it can report that membership is
incomplete. No claim of exhaustive unknown-identity enumeration is made.

## Complete, partial and empty

Retain the existing `daemon_threads` coverage predicate. Current Codex source
sets complete only after loaded **and** saved census completion, no unresolved
runtime statuses, and successful bounded native processing. See
`codex_snapshot.py`'s final daemon coverage and `collection.py`'s runtime mapping.
Projection cannot upgrade partial native coverage. Source failure, retained
rows, view/byte limits, uncertain predicate support or dropped selected entries
prevent complete membership authority. Do not substitute loaded-only coverage.

This is conservative: large/incomplete saved inventories can leave the active
feed partial even when its displayed running rows are individually current.
A future narrower native completeness proof is a separate provider-contract
review, not a filtering optimization. The existing sampling race limits remain;
complete means the admitted bounded sampled census, not a transactional native
snapshot or event replay.

A fresh complete scope plus an exhaustive selected member set permits removal
of prior selected identities absent from that scope's set. This says
`not_in_selected_census`, not `parked`. An empty set clears that covered scope
only while this completeness authority is valid. Another host/provider is
unaffected. History health, an empty array, a new projection timestamp or a
successfully admitted transport frame alone cannot authorize empty membership.

Under partial coverage, only present positive members and exact positive
nonmember facts decide membership. Other omissions remain unknown. Expired,
warming, stale and unavailable scopes never clear by absence. Healthy sibling
scopes retain their own independent authority.

## Bounded recent-member ledger

The service keeps one selector-wide ledger for identities it has positively
emitted as members. It is not subscriber history or a replay log. Each entry
holds identity, last positive decision order, the original membership receipt
bindings/deadlines, and at most one newer uncertainty/nonmember decision.
It retains no prompt, transcript, native payload, duplicate full row body or
inactive-history inventory.

Proposed hard ceilings are 4,096 tracked identities and 1 MiB canonical ledger
metadata, counting active, uncertainty and nonmember entries. Charge the UTF-8
canonical JSON encoding of the whole ledger object, including identities,
support references, decision watermarks and punctuation; do not count only its
identity keys. Selected full row bodies are separately charged to the whole
projected frame. Retain the existing 8 MiB + 16 KiB native frame ceiling and
16 KiB envelope ceiling; no raised transport limit is assumed. Crossing any
ceiling fails explicitly, without truncating membership. These are G0 review
bounds, not allocated release promises. Dormant identities never selected by
this feed consume no ledger space. Churn is a capacity case. Resident Python
memory and pinned slow-reader generations need separate bounded accounting.
Partition continuity by provider/namespace. If a scope cannot add its next
required entry within the shared ceilings, fail that scope without evicting
another scope's entries. Reserve bounded failure metadata for every configured
scope so reporting the capacity failure does not itself require ledger space.

An entry's unresolved-prior horizon is the original last positive membership
deadline, never last seen, current time plus TTL, projection generation or
subscriber reconnection time. Repeating an unknown/parked/excluded observation
cannot slide that horizon. A genuinely newer positive member has its own
original receipt/deadline. A positive nonmember fact is usable only during its
own supporting lease; retain its ordering watermark through any remaining old
positive horizon, without presenting an expired negative as current.

Prune an inactive ledger entry after that old positive horizon. Pruning only
means no old positive claim can still be current under its original lease.
It grants **no** parked/removal/complete-empty authority. Consumer-retained
last-known context may outlive that producer entry under the consumer's existing
policy; later partial omission cannot retire it. The consumer must never require
the producer to resend inactive history merely to preserve such local context.

Do not evict an entry to make a replacement appear complete. On either hard
limit, fail the affected projected scope explicitly with
`projection_tracking_capacity`, revoke its continuity/current authority and
require a fresh proved baseline for recovery. Existing consumer context becomes
uncertain within its original bounds; it is not a positive retirement. Full
inventory and healthy sibling scopes remain independent. Resetting a scope's
ledger changes its explicit projection continuity token bound to service
incarnation and selector; healthy scope tokens do not change. An old proof
cannot recover the earlier authority.
Recovery waits for capacity or an explicitly scoped reset, never native actions.

The wire is still a full filtered replacement: its ledger subset is complete
for that bounded producer state, not a delta requiring acknowledgements or an
unbounded sequence of tombstones. A missed negative may remain unknowable after
its lease/horizon. Reconnect under partial coverage therefore cannot promise
instant authoritative retirement of every consumer's retained context.

Preserve RLCD's existing post-expiry uncertain rows without imposing a new
time-to-hide. Positive-fact expiry, negative/completeness-evidence expiry, and
presentation-context lifetime are three separate decisions. Producer bookkeeping
is bounded by original horizons; presentation context is not required to expire
at that horizon. G0 explicitly accepts unresolved context after partial outages
or missed negatives. Exact eventual retirement through arbitrary partial outages
is not promised. An identity-reconciliation query and a new UI timeout are
deferred; neither is a prerequisite for this first feed.

## Original receipts and clocks

Every membership decision names its original source/component, accepted counter,
sample and expiry, plus service/source context and projection incarnation.
Receipt binding is mandatory even for a zero-member complete scope.
Decision precedence follows the engine's admitted evidence ordering and
original supporting samples. A larger projection revision or encoding time
alone cannot make an older negative override a newer positive native fact.

| Claim | Required original support |
| --- | --- |
| Running membership | Current runtime predicate and identity support; any component actually used for selected-kind classification |
| Positive parked nonmember | Current runtime observation containing the reviewed saved-thread `notLoaded` predicate and its positive saved identity support |
| Excluded-kind nonmember | Component(s) that supplied the positive native child/system classification; no runtime inference from kind |
| Native unknown | Fresh receipt for that unknown observation, if one exists; otherwise only failure/absence reason and the old membership binding as last-known context |
| Complete scope / absence | Original runtime census receipt plus any additional dependency required to prove exhaustive selector classification, all fresh |
| Activity, phase, outcome, timing, workspace | Their existing independently expiring evidence/component rules; no new projection clock |

Runtime failure/attempt/emission metadata does not renew a native receipt.
Uncertainty is not a positive runtime assertion. Preserve original activity,
latest-turn, thread-update and timing receipt fields; no projection time becomes
conversation age or phase entry.

### Chosen dependency provenance

Choose transient engine support metadata, not inference from the frozen row
and not a blanket assumption that the latest receipt owns every field. A support
reference is `(provider, namespace, contextGeneration, component, accepted,
sampledBoottimeMs, expiresBoottimeMs)`, bound to the service incarnation. Capture
it when that component accepts the actual sample. Runtime facts use the engine's
runtime receipt, including a history sample explicitly accepted into runtime;
timing fields keep their existing original runtime/history attribution.
For body expiry, runtime/phase use their original runtime support, workspace its
original history support, and existing explicit timing bindings stay exact.
Capture transient actual activity/outcome support at acceptance too, and carry
the support of the value chosen by their existing reconciliation rules. Never
construct a dependency set from only components still live at publication: a
stale/missing actual producing dependency makes its value last-known. Retention
does not rebind activity/outcome to a newer unrelated receipt. Title/identity
context grants no freshness. This avoids claiming a new public per-field map
for the unchanged full contract while defining the new projected wrapper exactly.

For each directly observed input identity, track runtime, kind, positive
saved-identity, activity and outcome support separately. Reconciliation copies
the support of the value actually chosen: runtime kind when chosen, history kind only
when the existing unknown-kind fallback chooses history. An unresolved kind
may remain explicitly `unknown`; that is selected by the fixed first descriptor
without claiming positive user/child/system classification. A known kind without
valid support is uncertainty, not a fabricated current unknown or exclusion.

Retention preserves old references unchanged. Merging `hasSavedHistory`, receipt
renewal for another row, newer projection revision, cache emission and failure
must not rebind retained kind/runtime/identity to a new sample. A current decision
reference must equal the current component's accepted/sample/expiry/context
tuple and have current/partial health. Otherwise it is only last-known support.
An accepted fresh sample may of course establish the same kind again. A raw full
frame lacking this support cannot alone create a current negative decision.
These support maps are internal bounded metadata; do not change API 4 row bytes.
The native/translated receipt map still contains only current configured
source/components, never a historical receipt bank per identity. Preserve Mesh's
32-receipt per-host bounds. Older support references in ledger context do not
add receipt-map entries or recover authority after an exact-match failure.

For a parked negative, require the runtime sample's own positive parked and
saved-identity support; a saved flag merged from old history cannot fill a
missing native parked predicate. For a kind negative, require the exact chosen
positive child/system support. Do not add a dependency on an unrelated healthy
component as a substitute. Failure or unavailable support yields uncertainty.

For complete scope authority, require the original runtime receipt's complete
`daemon_threads` census, its exact native census identity set, and a decidable
selected/nonselected result for every identity in that census. Use reconciled
values with their support above. The dependency set is the runtime census
receipt plus the union of exact kind/saved-identity component supports actually
used to decide those identities. In the current two-component model this union
has at most runtime and history per source. Every dependency must be valid and
unexpired. Retained history outside the complete current census is not silently
promoted into current native membership; the full inventory can still retain it.
Any missing support, unresolved runtime, census/view/byte limit or lost selected
entry makes coverage partial. The internal census set is not serialized as an
inactive identity list. This is the G0 contract choice; G1 proves its implementation.

### Query-time metadata authority

Adopt Mesh's metadata seam: `NativeState.records` contains only selected API 4
bodies. Typed coverage, uncertain/nonmember facts and member support references
live in projected owner metadata. Reconstruct the complete projected DTO for
native round-trip/digest admission. Do not insert scope records into Agent
sessions. This supersedes the initial suggestion to use generic scope records.

The new Observer active-read facade first calls public
`PreparedReadGuard.current(now_ms, clock)` to validate clock/generation, then
`context()` for the admitted header, even with zero selected bodies. A missing
generation/header grants no authority. At every read it checks
each metadata claim's exact support against that host's public translated
`receipts`: accepted counter, original owner binding, current/partial health,
non-null `expiresAtMs > now_ms`, ready delivery, exact selector and current
service/source/per-scope continuity. All required dependencies must pass; the
effective deadline is their minimum. Use Mesh's translated expiry, never remote
absolute time subtraction. Absence of a dependency grants no authority.

Thus a complete-empty claim expires when its runtime/classification dependency
expires even if history, transport or retained headers stay healthy. Exported
context is informational, never query-time completeness authority. Gap,
disconnect or clock/epoch mismatch invalidates the facade before reconciliation.
Negative expiry does not reverse an already valid retirement or revive an older
positive. On each accepted replacement the facade calls public
`PreparedReadGuard.snapshot()` once and privately retains only those admitted
selected bodies and their support metadata as owned immutable context. It never
reads private guard state. Generic `current()` can conservatively reject a whole
body because one field dependency expired; the facade still has the admitted
body and evaluates/masks each field against its original dependency independently.
It exports detached results, never its owned cache. A valid runtime/kind may
still grant membership while expired activity/workspace becomes last-known.
Missing/unproved support never becomes current. Clear the cache's authority on
gap/disconnect/changed incarnation; consumer presentation context stays separate.
Generic whole-body ineligibility is not identity-retirement authority.
Mesh's reviewed G0 proposal confirms this supported public header/receipt seam;
no new generic expiry API is needed. New profile/schema acceptance is separate.

## Wire, profile and proof proposal

Use a distinct opt-in `agent-observer.active-feed` native contract version 1,
with a separate projected local request/frame schema (proposed discriminant
`activeFeedProtocol: 1`). Dispatch it explicitly on the protected local service
socket alongside the unchanged Service 4 request family. Old services reject
it; the caller reports bounded unsupported capability. Do not label a filtered
array as snapshot schema 6 or add selection fields to frozen Service 4 frames.

Propose distinct Mesh profile `agent-observer.mesh-active.v1`, explicitly
configured with the exact selector descriptor/digest and native contract digest.
The domain remains Agent; transport source/route must distinguish this selection
from full inventory. Do not change `agent-observer.mesh-candidate.v3` bytes or
default resolution. For the fixed selector, accept Mesh's proposal to use
explicit hello source/profile negotiation rather than add a generic projected
Delivery capability. Retain SDK 1, state product, Mesh Read 1 and Delivery 1
subject to the new profile addendum/schema-lock review. Existing Observer
API 4/read 6/Service 4, full Agent v3, prepared
read interface 2, Tmux and ordinary CLI defaults retain their meanings.
The new active facade has its own initial interface descriptor. No Mesh SDK,
global API or package-version bump is assumed merely from these proposed names.

Bind exact selector/version, native/profile/schema digest, host/provider/namespace
scope, service and projection incarnation, source context, owner generation,
record variants, completeness and original receipts into the owner payload
digest and configured source/profile. Bind delivery to the actual request,
catalog authority and source, not just a matching digest or roster cardinality.
Reject mismatched selectors, namespaces, epochs, profiles and late proofs.

Retain fresh correlated full projected replies for changed candidates and the
existing nonce/whole-RTT/safety-margin rules. Source `snapshot()` gets a fresh
cached service reply after request admission. This proposal adds no digest-only
proof, watch-body substitution, new nonce semantics, delta protocol or replay.
Heartbeat, repeated identical payload, suspend, silence and copied headers never
renew evidence. Clock mismatch, gap, disconnect or incarnation change revokes
the affected authority and requires the ordinary proved replacement baseline.

There is no implicit full-roster fallback. An operator can deliberately select
the retained full-feed Observer/Mesh/client tuple for rollback. G4 must cover
the later required collector/service selection as well as publisher/read roles.

## Consumer lifecycle examples

| Input after prior member A | Required interpretation |
| --- | --- |
| A idle/waiting, blocked or capacity error with current running predicate | A remains a member; render phase/outcome independently |
| A current positive parked, or positively excluded kind | Remove exact A using the newer nonmember decision; do not claim session end |
| A native unknown/failed detail, or A omitted from partial scope | No current running claim; retain bounded uncertain prior context, no parked assertion |
| Complete, unexpired selected set excludes A | Retire A from selected membership for that scope, including A outside the display prefix |
| Complete empty | Clear covered selected membership while completeness remains authoritative |
| Empty partial/warming/unavailable | Clear nothing by absence; show the affected coverage uncertainty |
| A's ledger entry expires or overflows | No positive removal; enforce original claim expiry and continuity failure separately |
| First partial baseline, no prior context | Admit its positive members and report partial membership; invent no missing identities |
| Reconnect partial baseline, prior A retained locally | Revoke old current authority; new positives may restore A, exact negatives may retire A, omission leaves bounded uncertain context |
| New owner/projection epoch or stale old proof | Reject old authority, require proved replacement; no restoration from cached prior bytes |
| Same native ID on another host/provider/namespace | Separate exact identity and scope; one scope's failure cannot remove its sibling |

Reconcile the whole projected membership before sorting/display/USB32 limits.
The facade distinguishes current claims, last-known context, coverage status
and positive retirement facts. It does not impose a retention duration,
sorting, host badges, token format, retry UI or device cadence. A consumer's
future context timeout is a presentation decision, never a native parked fact.

## Independent acceptance gates after G0

1. **Contract agreement.** RLCD reconciles this proposal and Mesh's normative
   review, including limits, dependency provenance, partial reconnect, empty
   scope expiry, selector negotiation and explicit rollback. G0 completion is
   agreement on the plan, not runtime acceptance.
2. **Observer source.** In a separately authorized G1, implement only agreed
   Observer seams. Verify pure/Mesh-free imports, strict raw validation,
   immutable cache ownership, one projection per generation, bounded selector,
   ledger and slow-subscriber memory, and unchanged full inventory semantics.
   Prove the lifecycle matrix including provenance failures, expiry, eviction,
   churn overflow, prefix exclusion, namespace collision and stale epoch races.
3. **Exact packages.** Allocate fresh versions only then; freeze wheel hashes,
   native/profile schemas and supported APIs. Qualify the exact accepted Mesh
   wheel independently in Observer; Mesh independently qualifies its producer.
   Source tests and a peer's acceptance do not accept an owner artifact.
4. **Native/transport.** Later, compare full and projected installed public
   paths with independent native metadata on the same endpoint/incarnation.
   Prove running idle/blocked/error, positive parked/classification transitions,
   partial/unknown and complete-empty where genuinely available. Report each
   host/provider/topology separately. Populated Starship, cached populated Snap,
   empty native Snap and controlled fixtures remain distinct evidence levels;
   never manufacture a populated gate or infer completeness from agreement.
   Test local service IPC and projected Mesh IPC/fixed SSH with original proofs,
   independent receipt expiry, restart/gap/reconnect and complete cleanup.
5. **Controlled cost.** Hold active members/decisions and update cadence fixed;
   vary dormant inventory at 100/500/2,000 while checking row and byte limits.
   Compare full semantic results before any cap and
   final consumer wire. Measure collector, projection/cache, publisher, catalog,
   transport and RLCD separately: absolute CPU, bytes, memory, latency, late
   replies and cleanup in serial matched ABBA windows without a profiler.
   Require projected consumer bytes/work to track active plus bounded recent
   churn/uncertainty, not untouched inactive inventory. Explain residual producer
   O(inventory) work and metadata changes; promise no numeric saving in advance.
   Measure consumer-retained uncertain-context cardinality separately: this wire
   does not bound its lifetime/size or promise O(active) client work when such
   context accumulates. Keep it fixed across matched comparisons.
   Full snapshot limit is 4,096 rows and just under 8 MiB per host snapshot.
   A 5,000-row single-host full fixture is therefore a capacity/partial case,
   not an accepted normal-scale benchmark. Use supported scales or independently
   verify a multi-host 5,000 aggregate and every enclosing Mesh capacity first.
6. **Separate adoption.** RLCD G2/G4 follow both producer acceptances. Preserve
   its one-second cadence, uncertainty/presentation and explicit full diagnostics.
   Later scoped rollout proves compatible old/new collector/service, publisher,
   Mesh and consumer tuples, protected Tmux/349/writer roles and device receipts.
   This planning pass changes none of those selections.

## G0 planning agreement and following contract freeze

Observer explicitly confirms these planning choices, with no remaining G0
semantic discrepancy against Mesh's updated proposal and RLCD's coordinator
positions. The established threads received the proposal; Mesh's current
`docs/active-feed-g0-proposal.md` was independently read, including its public
body-context/expiry seam. The coordinator relayed Mesh's explicit confirmation.

- Fixed first selector and owner-hosted pure cache before IPC, new opt-in
  native/profile route, unchanged full inventory and full projected nonce replies.
- Public `snapshot()` once per replacement, then `current()` first and `context()`
  on every read; exact original support and translated receipt expiry govern
  each claim, including empty scope authority. No private guard access.
- Mandatory transient actual-value support, exact-match-or-context-only rules,
  complete native census/dependency union, and no historical receipt bank.
- 4,096 identities/1 MiB whole-ledger planning ceilings, separate body/frame
  accounting, per-scope failure/reset continuity and no sibling eviction.
  Implementation must still prove serialized/resident capacity and recovery.
- Existing post-expiry uncertain presentation, accepted unresolved context after
  partial outages, and deferred identity-reconciliation/UI-timeout proposals.
- SDK 1/state/Read 1/Delivery 1 target, subject to a separate new-profile
  addendum/schema-lock checkpoint; no silent fallback or changed frozen v3 bytes.

Literal new schema/profile identifiers and interface names above remain review
names, not reserved allocations or normative contract bytes. Strict schemas,
addenda, exact dependency fixtures, artifacts and independent runtime/native
acceptance still require the following gates and explicit G1 instruction.
No implementation or rollout is opened by this G0 confirmation.

G0 validation: `./scripts/check` passes 434 synthetic tests with 43 expected
optional-dependency skips in the Mesh-free environment, plus 163 Markdown/link/fence
checks. No runtime implementation, package installation, native observation,
provider/session action or production change was performed for this proposal.
