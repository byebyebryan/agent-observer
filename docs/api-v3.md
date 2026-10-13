# Observation API 3 / wire 5 / Service 3

The `0.6.0a1` source candidate adds native timing to the passive provider-neutral
read interface. Operational selections remain a18 collection and a20/Mesh a15
until the [execution gates](native-timing-execution.md) accept exact replacements.
API 3 is a breaking prerelease extension, with no old-wire conversion. The
independent historical writer and Tmux profile are unaffected.

## Timing fields

Every row contains `lastUpdated` and `latestTurn`. Each has `health`, bounded
diagnostic `source`/`reason`, original source-wall `observedAt`, and `receipt`.
`capabilities.timing` declares the two independently supported dimensions.
Unsupported timing does not disable discovery or monitoring.

`lastUpdated.at` is the provider's thread-update timestamp in Unix milliseconds.
For Codex it can advance during work, cold loading and metadata operations. It
is neither conversation activity nor phase entry. `timestampPrecisionMs` is
1000 for Codex's native second-resolution clock, null when the clock is missing.

`latestTurn.value` is null for known-empty or unavailable metadata; inspect
`health` to distinguish them. A current non-null value contains opaque nullable
`id`, normalized `status` (`in_progress`, `completed`, `failed`, `cancelled`,
`unknown`), nullable Unix-millisecond `startedAt`/`completedAt`, independent
nullable native `durationMs`, and boundary `timestampPrecisionMs`. Duration can
differ from rounded end minus start. In-progress turns cannot contain an end or
duration. Missing clocks are never filled from another turn. Codex interruption
normalizes to cancelled. IDs are scoped by the complete session reference.

`activity.at` retains its previous completion-else-start meaning and remains the
default ordering clock. Runtime/phase/outcome meanings are unchanged. Native
turn elapsed time includes blocked time; it does not measure uninterrupted work.
Turn completion does not establish when an idle runtime was resumed.

Codex timing initially requires a positively saved native identity. Unproved
runtime-only clocks remain unsupported without last-known values. No transcript
payload is admitted. Malformed timing clears only its own dimension.

## Receipts and stale metadata

Direct snapshots have `receipt:null`; they make no cached lease claim. Service
3 requires a receipt for every current timing record:

```json
{"component":"runtime","sampledBoottimeMs":100,"observedBoottimeMs":120,"contextGeneration":1}
```

The enclosing service supplies host/store, service ID, boot ID and time namespace.
Current timing must match the source generation and exact component sample;
its observation falls between sample start and emission, before expiry. Original
job start consumes collection time. A history job retains history ownership even
when it also refreshes runtime. An unrelated lease or heartbeat never renews it.

The engine selects observation order (sample start, then source observation
BOOTTIME), replacing a whole turn including known-empty, unavailable and unknown
metadata. It does not maximize event time or restore old completion after a newer
sample expires. Equal-order conflicting metadata becomes ambiguous. Identical
metadata uses its original binding, choosing the shorter lease for distinct tied
origins. Missing rows retained across partial coverage remain stale under the
original sample; no new receipt is attributed to them.

Stale records clear `at`/precision or `value`. Previously admitted metadata may
remain as `lastKnownAt` plus `lastKnownTimestampPrecisionMs`, or `lastKnownValue`,
with original provenance and receipt. Unavailable/unproved input never becomes
last-known. Old unmatched bindings cannot borrow a current sample's lease.

## Read clients and clocks

`agent-observer api` and `schema --kind snapshot|watch` export API 3/wire 5.
`agent-observer service api` and `service schema --kind request|frame` export
Service 3. The pure facade remains `agent_observer.public`; local leased caching
uses `agent_observer.service_public.ReadCache`. The cached local CLI is
`agent-observer service list|watch --socket PATH --host-scope HOST`.

Human output distinguishes `ACTIVITY_AGE`, `NATIVE_TURN` and
`THREAD_UPDATE_AGE`. A terminal turn can show its native duration. An ongoing
turn timer requires current running and working/blocked evidence plus current
in-progress metadata; contradictory non-atomic samples suppress it. Status
responses do not expose a correlated turn ID, so compatible samples do not prove
an atomic join or lossless continuity.

`public.age_ms` calculates source-wall age at the metadata observation. A negative
delta remains unknown, preserving the native value. `public.ongoing_turn_age_ms`
also applies the sampled runtime/turn guard. Optional `now_boottime_ms` advances
only already-admitted local service data in its matching clock domain; expire
the frame through ReadCache first. Direct output uses the source baseline.
Local cached human watch advances with BOOTTIME, independently of wall-clock
ticks and carrier frames. It revokes current display on disconnect/expiry.

Remote clients must use Mesh's accepted source clock/proof accounting. Passing
device BOOTTIME or subtracting a remote event time from device wall time is not
valid. Exact blocked/current-phase age remains unavailable; the first extension
contains no observed-phase series. Clients independently accept age labels,
ordering, feeds and physical rendering.

Mesh's wire-4 profile cannot admit this extension. A separately reviewed Agent
profile and exact package gate follow local/native acceptance; SDK 1 and IPC/SSH
remain the intended networking boundary. See the [timing matrix](timing-acceptance-plan.md).
