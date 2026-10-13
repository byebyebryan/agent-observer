# Observation timing contract proposal

2026-10-12. T1–T3 of the [offline execution](timing-design-execution.md).
This is a reviewed producer design, not an implemented/exported contract.
API 2/read 4/Service 2/Mesh SDK 1 remains selected. The Mesh decision pass is now
complete; the [post-Mesh plan](post-mesh-timing-plan.md) specifies local timing
implementation first and separate successor-profile adoption. No current Mesh
upgrade or transport switch is required. The
[offline report](evidence/2026-10-12-timing-design/REPORT.md) records
the actual proof bounds; earlier [native timing evidence](evidence/2026-10-12-codex-timing/REPORT.md)
establishes Codex clocks on the sampled contexts.

## Decision

The first production timing checkpoint should expose **native latest-turn
metadata** and **last native thread update**, preserving existing conversation
activity, runtime, phase and outcome meanings. Keep observational phase timing
as an optional follow-up with its own consumer/native gate. The standalone
prototype validates its rules, but it does not solve exact current-state age.

Do not add an always-unknown phase-entry field, infer phase age from turn start
or `updatedAt`, or capture transcripts/events to reconstruct unavailable history.
Do not require a provider to support timing before its discovery/monitoring
adapter can be useful. Missing native IDs/boundaries remain nullable; unsupported
timing dimensions stay explicit. No Claude/OpenCode implementation is restored.

| Clock | Definition | Suitable use | Explicit limit |
| --- | --- | --- | --- |
| Existing `activity.at` | Latest native conversation boundary admitted by the adapter; Codex completion when present, otherwise start | Recent conversation ordering | Does not identify every phase entry or all native updates |
| Proposed `lastUpdated.at` | Provider-owned last update to the logical session/thread | Native update recency | Can include cold load and metadata changes; not conversation-only |
| Proposed latest-turn start | Provider-owned start of the latest observed turn | Elapsed ongoing turn | Includes blocking; not uninterrupted work or whole multi-turn task duration |
| Proposed latest-turn completion | Provider-owned end of the latest observed terminal turn | Time since that turn ended | Not resumed idle runtime entry or proof of task success |
| Proposed native turn duration | Provider-reported terminal duration, when available | Historical turn duration | Not guessed from rounded boundaries; ongoing duration may be unavailable |
| Experimental observed phase series | Elapsed source BOOTTIME since first observation in the current sampled series | Explicitly approximate phase display/order | Not exact phase age or a lower bound; missed intervening cycles are possible |

`recencyAt` and user `sectionEnteredAt` are excluded from the first extension.
Observed recency/section patterns do not establish native turn/phase predicates.

## Draft row layout

The following is the concrete schema target to review at production checkpoint
C0. It is not accepted input to today's strict wire-4 decoder. Each record is
always present in the proposed successor, using null/unavailable/unsupported
rather than omitted capability-dependent keys. This avoids implicit old-wire
compatibility. Record names may change at C0 only through an explicit decision.

```json
{
  "lastUpdated": {
    "at": 1791842910000,
    "timestampPrecisionMs": 1000,
    "observedAt": 1791842913508,
    "source": "codex_thread_metadata",
    "health": "current",
    "reason": "native_thread_update",
    "receipt": {
      "component": "runtime",
      "sampledBoottimeMs": 12500,
      "observedBoottimeMs": 12508,
      "contextGeneration": 0
    }
  },
  "latestTurn": {
    "value": {
      "id": "01a13228-fd1f-7233-8667-72452b072643",
      "status": "in_progress",
      "startedAt": 1791842909000,
      "completedAt": null,
      "durationMs": null,
      "timestampPrecisionMs": 1000
    },
    "observedAt": 1791842913508,
    "source": "codex_turn_metadata",
    "health": "current",
    "reason": "native_latest_turn",
    "receipt": {
      "component": "runtime",
      "sampledBoottimeMs": 12500,
      "observedBoottimeMs": 12508,
      "contextGeneration": 0
    }
  }
}
```

The native turn/update values illustrate the captured approval-answer sample;
receipt numbers are synthetic examples, not captured BOOTTIME measurements.
All native timestamps normalize to Unix milliseconds without inventing finer
precision. Native IDs are opaque bounded text scoped by the complete session
reference. They are not global IDs, row positions, titles, session-tree roots
or Observer-generated episode counters. A provider without a native turn ID
may supply explicit boundaries with `id: null`.

Latest-turn statuses are `in_progress`, `completed`, `failed`, `cancelled` and
`unknown`. Codex `interrupted` normalizes to cancelled. In-progress metadata must
not contain a completion/duration. Terminal status may have unavailable clocks;
it never fills missing clocks from the preceding turn. Duration is a separate
native measurement: seconds-based boundaries may differ from `durationMs`.
Known empty turn history uses current health and `value: null`; missing/failed
reads have unavailable/stale health. Unsupported providers use unsupported
health. Diagnostics remain bounded open reason/source codes, not client branches.

`lastUpdated` uses `at: null` for unavailable current evidence. On invalidation,
preserve original source, observation time and receipt, clear current values
and expose optional `lastKnownAt`/`lastKnownTimestampPrecisionMs` or
`latestTurn.lastKnownValue`. These are visibly historical; they never supply a
current timer or an older-turn fallback. Do not retain unproved raw values in
last-known fields. No previous known record means no last-known member.

Add `capabilities.timing` with `lastUpdated` and `latestTurn` booleans. These
describe supported evidence dimensions, not guaranteed clocks on every row,
complete inventory, runtime/action permission or exact phase age. The first
Codex admission requires positively saved native metadata. Runtime-only clocks
remain unavailable until an independent native source gate proves them. Their
known runtime/phase is unaffected. If timing alone is malformed, invalidate that
dimension while preserving independently admitted identity/runtime/phase facts.

## Receipt ownership, freshness and selection

In direct snapshots `receipt` is null: the adapter supplies current native
metadata and its original `observedAt`, without a cached service-lease claim.
Cached Service 3 views require a non-null receipt for admitted current timing.
It binds exactly to the row's provider/namespace, source context generation,
selected runtime/history component and that receipt's original sample start.
The observation BOOTTIME lies after sample start; a read finishing after expiry
cannot provide current timing under that lease. Boot/time-namespace identity
comes from the service envelope. No native timestamp is a BOOTTIME value.

The adapter reports when the bounded metadata response was observed; the worker
returns the observation stamps and the engine attributes them to the actual
accepted receipt. Neither the service emission time nor consumer arrival time
substitutes for this clock. Native start/end/update times remain separate.
The service validator must check the receipt binding, clock range and matching
sample even after metadata is merged from another component. Read caches expire
each selected timing record under its actual component, rather than guessing
that both leases renewed it. Metadata-only work cannot renew phase/runtime.

Historical last-known bindings can refer to an earlier, replaced receipt; that
preserves provenance only. A current value must bind to the current accepted
receipt. An old unmatched binding cannot borrow a new sample's healthy lease.

Select the newest admitted source observation, not the greatest native event
timestamp. Replace latest-turn metadata as one unit: new IDs, unknown clocks,
known-empty history and new in-progress status supersede older summaries.
An expired/failed newer sample never promotes an older terminal turn to current.
Equal-order conflicting reads are ambiguous. Identical metadata attributed to
two leases cannot silently choose the longer deadline; establish a unique
origin or use the conservative earlier one. Receipt ties and ordering must be
proved through the existing engine's coupled history/runtime publication path.

Stale values and ordering watermarks remain subject to canonical row/byte
retention bounds. No permanent event/turn ledger is required. Positive fresh
native reads recover after restart; old receipt scope cannot survive a new
Observer/boot/time namespace or provider incarnation as current evidence.

## Derived timers and non-atomic reads

The native turn summary is a fact about the latest turn at its metadata read.
It does not become an atomic assertion about a separately read work phase.
Runtime may be working while turn metadata is terminal, or runtime may be idle
while a newer metadata read sees in-progress work. Keep both independently
valid dimensions and suppress a misleading joined timer until reconciliation.

An ongoing-turn timer requires current, same-session/source-generation/clock
evidence, active working/blocked phase and in-progress latest-turn metadata.
Known turn-ID disagreement or a turn beginning definitely after the status
observation makes that association unavailable. Compatible samples can support
**latest observed ongoing turn elapsed**, with sampling limitations; they do
not prove uninterrupted work or every native transition. Do not add another
provider RPC just to manufacture atomicity in this design pass.

Calculate native clock age at the source metadata observation from its wall
clock and native event time. Subsequent ticks use elapsed time in the same
BOOTTIME domain. A negative native/source clock delta stays unknown, without
clamping or rewriting the native timestamp. Precision remains visible. A source
wall-clock change before the baseline can affect inferred elapsed time; native
absolute timestamps are not a guarantee of continuous physical duration.
Where available, terminal native `durationMs` remains the separate measure.

Cross-host clients must use reviewed Mesh source-age/transit/freshness accounting
before advancing the source baseline in a local clock domain. Subtracting a
remote event timestamp from an unrelated device clock is not accepted clock
proof. This pass specifies the required information and does not implement or
change Mesh's clock/proof policy. A clock model cannot grant runtime authority.

## Experimental phase tracking

The [offline model](evidence/2026-10-12-timing-design/timing_model.py) tracks only
positive normalized running-phase observations. It has a fixed configured
source set, source generations/order watermarks and a bounded live-row map.
Global source watermarks reject delayed batches without an unbounded per-row
tombstone ledger. Existing tracked rows survive timer-capacity pressure; new
untracked rows simply have unknown optional age. This drops no discovery rows.

Each first observation starts an Observer-scoped series. Repeat observations
of the same phase/known turn keep the anchor; phase change, known turn change
or loss/recovery of turn identity starts a new observed series. Blocked reason
changes alone are not proof that the normalized blocked phase ended. Metadata
selection, heartbeats, reader ticks and incoming clients cannot mutate this
tracker: only accepted runtime observations do. A coupled history read may do
so once through its actual runtime evidence, with that short lease.

Source failure, expiry, missing rows in partial or complete observations,
unknown phase, parked status and registered provider-generation changes break
the affected series. Missing observations never imply parked. Positive partial
siblings can continue. New Observer/boot/time namespace needs a new tracker;
clock regression invalidates the tracker rather than extending old spans.
No source-gap persistence claims or durable recovery ledger are proposed.

An external client's disconnect/gap is different from a source observation
gap. The continuously observing producer may retain its anchor. After a fresh
accepted resync/proof, a returning client can use that same anchor. A client
cannot invent continuity from its own cached old view or reset the shared
producer merely because it joined later.

Series IDs distinguish Observer observations, not native work episodes. The
prototype's `firstObservedAt` and BOOTTIME span are not exact phase entry or a
guaranteed lower bound: a same-turn working/blocked/working cycle can occur
between polls. Push and un-timestamped hints do not remove that uncertainty.
This record is deliberately absent from the first proposed wire extension.

## Client implications and following gates

RLCD's current ordering asks for oldest actual current-state age. It must keep
that age unknown where native evidence cannot establish it. Turn-age ordering,
time-since-completion or observed-series ordering would be explicit client
policy refinements. State counts/urgency still work without a known age. Device
transport/rendering and Agent Plus/native launchers are separate workstreams.

The [acceptance matrix](timing-acceptance-plan.md) separates offline proof from
production implementation, immutable artifacts, ordinary/native comparison,
resources, local/fleet delivery and client/physical acceptance. The contemplated
successor is API 3/read-watch 5/Service 3, subject to C0 schema/version review.
Mesh needs an independently reviewed successor Agent descriptor/schema/profile;
generic SDK 1 may remain compatible. Preserve the Tmux profile and owner's
simultaneous work. No old-wire converter, provider-version pin or automatic
deployment is introduced by these documents.
