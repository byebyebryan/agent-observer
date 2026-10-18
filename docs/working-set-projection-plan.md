# Generalized active and recent-session projection

Execution update, 2026-10-18: Bryan explicitly requested the Luna goal loop to
execute this plan. P0 cached workload sizing is recorded in the
[sanitized screen](evidence/2026-10-18-working-set/p0/README.md); the source-clock
and joint P1 contract gates remain open. Routine owning investigation and later
implementation after those gates need no repeated general approval. Deployment
and consumer/device adoption retain separate authorization. Earlier planning-only
statements below describe the c7f41ea checkpoint, not a new stop instruction.

Status: planning draft, 2026-10-17. Bryan requested a proper plan before
implementation and selected **3 days** as the everyday recent-history window.
This document proposes generalizing the existing active projector. It authorizes
no runtime/schema changes, identifier allocation, native probes, installation or
rollout. [Delta synchronization](delta-sync-dark-feature.md) remains deferred and
default-off. Its frozen branch, evidence and cleanup disposition are unchanged.

## Product behavior

The everyday inventory is the eligible active set plus eligible rows with
conversation activity in the last 72 hours. Active means the existing positively
proved running predicate, including working, blocked and waiting. An active row
is never excluded because its last conversation activity is old or unknown.
Recent means conversation activity age, not time since becoming inactive.

| Mode | Selection | Delivery |
| --- | --- | --- |
| Active only | Current active membership; recent window disabled | Existing active v1 remains supported |
| Everyday | Active union proved activity age less than 259,200,000 ms | Proposed generalized projection, complete replacements |
| Full history | Existing full inventory, including older/unknown-age rows | Explicit existing full read; no background full-history subscription implied |

A row appears once even when both reasons apply. Child/system exclusion and
unknown-kind treatment retain the current explicit policy. Rows that qualify
as recent may have parked **or unknown** runtime; their actual runtime DTO is
preserved. Recency supplies no running/parked assertion. A recent row with no
current runtime evidence must remain visibly uncertain about runtime.

The first version has one startup-configured recent window per owner, default
72 hours, alongside the existing active/full routes. Zero disables the recent
branch. Clients may narrow the advertised working set locally; widening beyond
the configured window needs an explicit full-history read or a separately
configured/reviewed policy. Do not add arbitrary per-request predicates,
unbounded per-client projection caches, automatic full-feed fallback or top-N
truncation in this pass. Full-history navigation/filtering/pagination beyond the
existing read is a separate product task if that occasional read is insufficient.

## Selection and uncertainty

Let E be current eligibility under the kind policy, A current positive active
membership, and R proved recent activity. Selection is `E AND (A OR R)`, evaluated
with true/false/unknown evidence rather than treating unknown as false.

| Evidence | Current selected membership | Interpretation |
| --- | --- | --- |
| A true, any activity age | Included | Active; preserve independently known/unknown fields |
| A false or unknown, R true | Included | Recent; preserve actual parked/unknown runtime |
| A false, R false | Outside this view | No provider deletion, session-end or global presentation-retirement claim |
| A unknown, R false/unknown; or A false, R unknown | Unresolved | Partial selection coverage and retained prior context |
| Current proved excluded kind | Outside this view | Exact kind decision under existing provenance rules |

Unknown activity, invalid/future timestamps or unproved clock mapping never
qualify the recent branch. Current active membership still qualifies the row.
An unresolved row is not silently placed in the recent body list and not
silently proved absent. The existing bounded uncertainty ledger covers prior
positives; it is not expanded into an unbounded inactive roster.

Membership has two fixed alternatives with separate original dependencies:
active depends on its current runtime/kind evidence; recent depends on its
current activity/kind evidence and the source-clock window. The facade evaluates
the union. Expiring activity cannot hide a still-active row; loss of active
support need not hide independently proved recent membership. Each displayed
field retains its own lease and original support. No generic expression language
or per-row historical receipt bank is introduced.

## Source clock, age boundary and quiet periods

This is the main contract addition. An age filter cannot use receiving-device
wall time, service emission time, file modification time or last-seen time as
conversation activity. Preserve the original native `activity.at` and exact
FactSupport. The existing row-age convention uses source-sampled clocks; the new
projection must provide a reviewed source wall/BOOTTIME anchor for that purpose.

Proposed algebra for a proved source anchor S and activity event T:

```text
age_at_S = S.wall_ms - T.activity_at
recent_until_boot = S.boottime_ms + window_ms - age_at_S
recent_now = 0 <= age_at_S AND owner_boottime_now < recent_until_boot
```

At equality the recent branch expires. Zero window selects no recent rows.
If remaining window time is nonpositive, the branch is false without emitting
an underflowed BOOTTIME deadline; future activity makes the branch unknown.
The anchor binds service/boot/time-namespace/source-context incarnation and the
original activity support. P0/P1 must establish whether the existing source
metadata supplies that exact pair; otherwise propose bounded native anchor
metadata and review it before schema freeze. A sample anchor measures elapsed
time; it does not refresh the event, provider observation or support lease.

For unchanged activity in one clock incarnation, heartbeats, reconnects, proof
calls, unrelated observations and cached reads cannot move an established cutoff
later. Repeated actual observations of the same timestamp retain that boundary;
a genuinely newer activity event can create a later one. Clock discontinuity,
future activity, boot/namespace change or an invalid anchor makes recency
unresolved until valid new evidence establishes it. Never extend a cutoff to
compensate silently for a wall-clock regression. BOOTTIME advancement includes
suspend; remote BOOTTIME values are never compared directly across hosts.

The service schedules the next relevant cutoff alongside existing lease timers.
When it fires, recompute the affected projection from owned reconciled state,
publish a replacement and schedule the next cutoff. No native collection or full
history read is triggered by that timer. Reads/proofs reuse the cached result.
Deadline bookkeeping must be bounded by retained selected records; no accumulating
timer tombstones, generic dependency graph or commitment tree is needed.

Time-only membership changes need a separate monotonic projection revision.
Keep the engine observation revision as provenance. Bind cache/watch ordering to
service/context incarnation, selector digest and projection revision, and retain
both revisions explicitly. The current projector ignores equal engine revisions;
the current service delivery also keys caches on that revision. Both seams need
reviewed changes so a cutoff update is delivered without inventing a new native
observation or renewing leases.

An old frame must not remain current recent membership after its deadline just
because the next replacement is delayed or disconnected. The prepared facade
must independently enforce the bound. Prefer using existing translated receipt
deadlines with exact original refs: for a required receipt with native expiry E
and translated reader expiry H, a native cutoff D can be conservatively bounded
by `H - max(0, E - D)`, while all original receipt checks remain mandatory.
Mesh must review that derivation and its attenuation/clock assumptions before
accepting it. If supported interfaces cannot enforce the source bound, that is
a specific contract blocker; do not invent receiver clock authority or access
private Mesh state. No new generic SDK capability is presumed.

## Coverage, removal and context

Reuse the active feed's exact identity, source incarnation, coverage, original
support and continuity model. Generalize the selection decision and its reason;
do not use the old `parked` nonmember reason for a recent row that simply aged
out. A new outside-window reason needs its own proved time boundary plus proof
that the active alternative does not apply. An unknown active alternative
prevents a definitive outside-window decision.

Complete coverage must prove the new predicate over the relevant native census,
including activity dependencies needed to classify non-active rows. Loaded-only
completeness cannot establish an exhaustive recent-history set. Missing history,
unknown ages, partial inventories or resource refusal make affected coverage
partial. Healthy sibling scope semantics and complete-empty support remain
explicit. No complete claim follows from an empty serialized array.

Keep three separate lifetimes: positive row/field facts; negative/completeness
authority; consumer-retained presentation context. A proved window exclusion
can remove a row from this selected view without claiming it stopped or was
deleted. It establishes no new global context timeout. Omission, old ledger
pruning, capacity failure or a missed/expired negative under partial reconnect
cannot silently retire prior context. The UI must distinguish rows currently in
the requested window from older uncertainty/history context. Prior-ID queries
and exact eventual retirement across arbitrary partial outages remain outside
this pass.

## Reuse, compatibility and ownership

Generalize the existing projector, owned cache, source, pure profile/preparation
and facade. Keep complete replacement snapshots and SDK1 proof/delivery. Do not
depend on dark sync codecs, journals, Patricia trees, cohorts or delta controllers.
Core/local service remain Mesh-free. Native provider reads/classification,
collection cadence, actions/attachments and session lifecycle are unchanged.

| Owner | Planned responsibility |
| --- | --- |
| Observer engine/service | Preserve source samples/supports; one configured selection policy; cache, cutoff timer and projection ordering before IPC |
| Observer pure contract/profile/facade | Strict selector/clock/support admission, union membership, per-field currentness, coverage and lossless DTOs |
| Mesh | Reviewed additive profile/descriptor binding, unchanged proof/receipt translation and transport/cache ownership |
| RLCD/read clients | Requested-view policy, active/recent/uncertain presentation and explicit history navigation; independent adoption |

Bind the exact provider/kind/window policy into canonical selector bytes and its
digest. The configured source/profile must match it; no source-name magic,
silent fallback or unbound request-time age parameter. A policy change requires
a new projection incarnation/baseline and independent continuity; it cannot
reinterpret retained decisions from a different window.

The selected active v1 schema/selector/profile meaning and frozen API4 bodies
remain exact. Propose an additive native contract/profile revision for the
generalized selection and deadline metadata; literal IDs, versions and packaged
schema/lock changes remain unallocated until P1. Legacy active v1 is the
zero-window compatibility surface of the generalized implementation, with
unchanged wire bytes and semantics. Full Service4/profile v3 remain available.
Any later launcher change is explicit and independently paired with rollback.

## Resource and performance limits

Selection reduces serialized bodies and repeated consumer work. Native history
discovery and engine reconciliation may still examine the full bounded roster.
Do not claim those costs scale only with the working set without measuring them.
The existing active benchmark at 2,000 total/10 selected rows reports about
3.33 MB to 44 KB per read and 375 ms to 5.7 ms cached-read CPU, with added
generation cost. Its native collection/Mesh exclusions remain; it does not
predict the size or cost of a 3-day view.

Preserve existing published limits, including 4,096 tracked identities, 1 MiB
ledger, 8 MiB plus 16 KiB native frame, 32 receipts/host and shared service client/
encoding bounds. Count active and recent bodies, uncertainty/decisions, timers,
current/new caches, full/legacy-active coexistence, slow-reader pins and detached
copies. Reuse existing ownership/preallocation and fail explicitly under bounds.
An age window alone does not guarantee a small set. If all active bodies cannot
fit, fail affected coverage visibly; do not silently discard active rows. If the
recent set cannot fit, report the explicit capacity limit/partial scope; do not
claim a complete 72-hour window. A future top-N policy needs its own descriptor,
ordering and completeness definition before use.

Proposed performance gates to agree at P1, before optimizing or implementing:

- Zero-window behavior preserves legacy active membership, field health, order,
  support and coverage. Unchanged legacy frame/schema bytes stay exact.
- Matched owner-generation CPU increases at most 25% over accepted a7 for the
  same observations/configured views. Report retained legacy work plus new work
  and combined totals; no oracle/profiling time inside measured windows.
- At 500/2,000 total rows, when selected canonical body bytes are at most one
  quarter of full-body bytes, propose at least 30% lower combined producer/read
  cost and 50% lower total repeated delivery bytes than a full-feed consumer
  selecting the identical final rows at four reads per generation. Include
  selection/support/header overhead. Validate this target against the P0 cost
  model at P1 rather than copying delta-sync's unrealized targets. Report the
  100-row case and zero/one/four/sixteen-reader cadence separately; do not promise
  a saving at every cadence or compare different selected outputs.
- Full-history-on-demand semantics remain exact; report its cold cost and added
  owner overhead separately. Cutoff timers, proof, copies, failure/recovery and
  slow peers are included in applicable CPU/resource totals.
- Qualify 100/500/2,000 total rows, varied active/recent ratios, 3-day bursts and
  dense supported body fields. Max-bound refusal is tested separately. Hold
  original freshness/deadline/transport limits and report RSS/plateau explicitly.

These are proposed gates, not achieved results or a reuse of dark-sync passes.
P0 must report actual row counts before finalizing a useful capacity target.

## Stages and exit criteria

| Stage | Work | Exit / authorization boundary |
| --- | --- | --- |
| P0 workload and source-clock review | On explicit later authorization, inspect existing cached public inventories on Snap/Starship; aggregate active counts, inactive age buckets at 24h/3d/7d, unknown ages/runtime/kinds, body bytes and sample-anchor availability | Sanitized counts/bytes and known limits; no prompts/content, provider actions, auto-start or new native daemon; confirm 3-day expected size and unsupported clock cases |
| P1 joint contract plan | Observer with Mesh/RLCD review exact selector, anchor/deadline, fixed union rules, time-only revisions, coverage/reconnect/overflow and profile bindings; choose finite window bounds and exact budgets | One concrete agreed packet and independent boundary/clock vectors; no runtime/schema/version allocation from this planning document alone |
| P2 pure projection/source implementation | After explicit implementation authorization, generalize behind opt-in policy; preserve v1; build bounded timer/cache and contract/profile/facade in owning repos | Synthetic functional/lifetime/limit checks and full old-contract regression gates; no installation/adoption |
| P3 immutable producer qualification | Paired exact source/artifacts, installed native parity, local IPC/fixed SSH, current/expiry/reconnect and controlled cost/resource matrices on both hosts | All agreed producer gates pass with exact provenance; failing gates stay explicit and stop promotion |
| P4 consumer adoption | RLCD/read-client view/history presentation, actual authenticated configured route, paired role rollback/reselection and independent device gates | Separately authorized deployment; physical checks remain distinct and may be deferred explicitly |

P0 is a small evidence pass, not a new large optimization campaign. If the
3-day set is usually large or source age cannot be proved cheaply, return that
finding before building a generalized contract. No automatic work loop, native
probe, peer implementation, package build or rollout is started by writing this
plan. The present task ends with the reviewable planning commit.

## Required vectors before schema freeze

Cover old-active-with-no-activity; old blocked/waiting; parked just inside/on/
outside 72 hours; zero window; active+recent dedup; recent with unknown runtime;
unknown/missing/future activity; kind exclusion and stale kind support; changed
activity versus unchanged/old refs; quiet cutoff and delayed watch frame;
heartbeat/proof/reconnect that cannot renew cutoff; wall regression, suspend,
boot/namespace/context changes; independent field expiry; partial and
complete-empty census; missed negative and retained context; changed policy;
overflow with all-active and burst-recent sets; shared-cache/pin/copy cleanup
with cancellation, retained errors and siblings. Validate equality against an
independently computed full-inventory filter, not another projection result.

Source basis: [active-feed interface](active-feed-interface.md),
[original projection plan](active-feed-proposal.md),
[accepted producer evidence](evidence/2026-10-16-active-feed/REPORT.md),
[API4](api-v4.md) and
[observation boundaries](observation-boundaries.md). The released a7 manifest
pins source `7807160384ba39b4d438c5c7f1b5f316c3608dcd`; historical objects remain
preserved after attribution cleanup. This planning branch starts at cleaned
`957e328e9215aa6a5b05bb1ac0e963877f06f028`; no released byte is changed.
