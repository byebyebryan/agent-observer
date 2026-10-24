# Working-set projection: P1 contract candidate

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-18. Owning implementation proposal under Bryan's explicit Luna goal
loop. This packet supplements the [product plan](working-set-projection-plan.md).
It needs exact Observer/Mesh/client agreement before dependent native schema,
runtime dispatch or packaged profile edits. The new pure policy helper is a
preparatory model, not a selected route or a completed producer gate.

The [cached P0 screen](../../evidence/2026-10-18-working-set/p0/README.md) finds a
small 72-hour body set on both hosts. It does not establish selection authority,
native parity, CPU, total wire, memory or fleet capacity. Dark delta-sync stays
off. No sync serializer, journal, tree, codec or controller is a dependency.

## Policy and configuration

One immutable policy per optional owner cache. The proposed canonical selector
is exactly the following closed object, with the configured integer substituted:

```json
{"version":1,"providers":["codex"],"kinds":["unknown","user"],"active":{"runtimeValues":["running"],"runtimeHealths":["current"]},"recent":{"field":"activity.at","windowMs":259200000,"boundary":"exclusive","unknown":"unresolved"}}
```

`windowMs` is an exact integer in 0..2,592,000,000 inclusive, default
259,200,000; booleans are rejected. Zero disables recency, including when its
activity evidence is missing. `selectorDigest` is `sha256:` followed by lowercase
SHA256 of existing Observer canonical UTF-8 JSON bytes. The selected window is
bound into every request, frame, profile source and reconnect incarnation.

Proposed service opt-in is `Runtime(..., working_set_window_ms=None)` by
default. `None` creates no working-set cache or route. CLI
`--working-set-window-hours [HOURS]` enables it: a bare flag means 72, explicit
integer 0..720 is converted exactly to milliseconds. A request must match the
startup selector; it cannot change or widen the owner policy. Existing active
and full endpoints retain their exact protocols, defaults and bodies. Changing
policy requires a new owner/service incarnation, never live reinterpretation.

Selection is strong three-valued `E AND (A OR R)`. Unknown kind remains eligible
under the existing policy; current child/system kind excludes. A is proved
current running, including waiting/blocked, independently of activity. A proved
current parked runtime, with the existing saved-identity dependency, proves A
false. Unknown runtime does not. R is current proved recent activity below.
Positive A or R survives an unknown sibling. A row is definitively outside only
when E is false or both alternatives are proved false. Otherwise selection is
unresolved. Recent never changes runtime, phase or action authority.

Proposed additional R=false case is a successful empty native turn response:
the same accepted input row has unavailable/null activity with reason
`no_conversation_activity` AND current/null latestTurn with reason
`no_native_turn`, exact current latestTurn FactSupport and the accepted sample
join. Preserve the unavailable activity DTO; an explicit private absence marker
records this evidence without manufacturing activity support. Skipped, failed,
malformed, unsupported, content-rejected and saved-store-missing results remain
unknown. An aggregate activitySupported flag never substitutes for this marker.
This domain interpretation is a P1 review item, not implemented by the current
stateless preparatory helper.

## Trusted source sample and conservative cutoff

The canonical worker already has this causal ordering:

1. Parent samples BOOTTIME `L=job.started` before worker spawn.
2. Worker finishes collection, then samples wall `W=snapshot.collectedAt`.
3. Parent parses the successful exact worker snapshot, then samples BOOTTIME U
   immediately before acceptance. All three integer captures are floored ms.
4. Only successful accepted input installs the private bracket, tied to the
   original worker `collectionId`, provider/namespace/context, serviceId, bootId
   and time namespace. Rejected, failed, late or unsupported custom workers
   install no clock authority. The bracket must be visible atomically with the
   accepted snapshot and its projection publication, not attached afterward.

The sample's original component may be history while its exact snapshot is
also promoted into the runtime receipt. Preserve this sample identity on both
receipts; do not infer job origin from a FactSupport component. Activity's exact
current support must match its receipt, and that receipt's original data
collectionId must match the bracket. Equal timestamps alone do not establish a
join. An old field carried across a gap does not inherit a new clock/support.

For published integer activity timestamp T, window Q and source owner now N:

```text
age = W - T
Dlo = L + Q - age - 1
Dhi = U + Q - age + 1
R = true     when N < Dlo
R = false    when N >= Dhi
R = unknown  otherwise
```

T must be current, nonnegative, source supported, and no later than W. L<=U<=N
and the exact service/boot/time-namespace/provider/namespace/context binding are
mandatory. Missing, future, stale, invalid or unproved evidence is unknown.
The +/-1 ms allowance handles flooring; activity's published integer value is
the product policy timestamp, not a claim of exact physical event timing. No
extra second is silently added to the requested window. Cutoff fields are exact
signed integers in -(2^53-1)..(2^53-1); a negative Dhi can prove already-old input
and is exported exactly. Out-of-range arithmetic makes the recent branch
unknown, never wrapped, rounded or represented by an ambiguous null. An
unavailable value/lastKnownAt does not prove recent.

For the same full row identity, activity timestamp, policy and source clock
incarnation, a bounded owner ledger retains the established positive cutoff.
Heartbeat, proof, reconnect, unrelated observations and re-observation of the
same event cannot move positive Dlo later: use the minimum of retained Dlo and
candidate Dlo. Negative Dhi is the current sample's computed upper bound, never
clamped earlier using an old sample. This may enlarge conservative uncertainty;
it cannot manufacture a later positive or an early negative. A genuinely newer
event may establish a new cutoff. An older activity timestamp never replaces the
retained event key: that candidate makes R unknown and cannot supply either
cutoff or a current outside-window decision. Equal/newer supported timestamps
can restore comparison under the rules above. Keep at most one event key/ceiling
per tracked identity under the
existing 4,096/1 MiB bound, never an accumulating event history. Timers are only
for retained live boundaries, not all possible event keys.

Each accepted bracket also yields a wall-minus-BOOT interval. Disjoint
consecutive intervals, after the same flooring allowance, are a detected wall
discontinuity: invalidate R for unchanged events rather than resetting/extending
their cutoffs. A new supported event can establish a new pair. Boot, service,
time namespace or provider context changes retire old authority. Tiny/undetected
clock adjustments cannot extend an established monotonic cutoff. This contract
does not claim to reconstruct exact historical physical event time from wall
timestamps. Suspend advances BOOTTIME normally.

## Native DTO and exact admission responsibilities

Candidate literals, **unallocated and unfrozen**, are native protocol
`agent-observer.working-set` version1 and profile
`agent-observer.mesh-working-set.v1`, SDK1/frame_bytes8,404,992. Candidate paths
are `agent_observer/contracts/working-set-{request,frame}.schema.json` and Mesh
packaged `read-agent-working-set.profile.schema.json`. No existing ID, schema
digest or lock entry changes meaning. Schema bytes/digests follow later exact
freeze review; these names are not an allocated package/version.

The request is closed: `workingSetProtocol:1`, operation `status|snapshot|watch`,
`hostScope`, exact selector and selectorDigest. The frame retains Service4's
host/service/clock/source envelope but replaces serviceProtocol/snapshot with
workingSetProtocol/projection, adds `observationRevision`, and binds
`viewRevision` to the independent monotonic projection revision. Both revisions
are exact nonnegative integers. `sequence` remains stream-local strict order.

`projection` is null while warming or where the active protocol forbids a body;
otherwise it contains `scopes` and `sessions`. Sessions use byte-for-byte frozen
API4/schema6 row shape. They may be parked or runtime-unknown when R is true.
Reimplement row semantic validation as shared API4 semantics plus selected
membership checks; do not reuse active-only running/phase constraints on recent
rows. Native/owner fields retain original timestamps, health and FactSupports.

Each scope retains provider, namespace, contextGeneration, continuity and the
existing bounded coverage/uncertain/nonmember layout, with these additions:

- `clocks`: at most two current component bindings, keyed by exact component
  and accepted counter. Each contains original sampleId, originComponent,
  sampledBoottimeMs=L, wallMs=W and acceptedBoottimeMs=U. Service/boot/context are
  inherited from the enclosing exact frame/scope. Mirrored components may name
  the same immutable sample. The owner keeps the corresponding private source
  metadata; untrusted/native clients do not invent it.
- Members retain identity and all existing fieldSupports, plus `active` and
  `recent` alternatives. Active is null or the exact positive runtime/kind
  support set. Recent is null or the exact activity/kind support set, activityAt,
  component/accepted clock reference and cutoff bounds. Declared positive Dlo
  must be no later than the current sample's computed lower bound; Dhi must
  equal its computed upper bound. A conservative earlier Dlo needs no unbounded
  historical clock/support bank and cannot make a false positive/early negative.
  At least one alternative is proved true at frame emission. A null branch
  supplies no positive authority; it does not assert that branch false.
- A proved nonmember uses either existing excluded-kind evidence or new
  `outside_window` evidence: exact negative-active runtime/saved support plus
  negative-recent activity/clock/upper bound, zero-window policy or the exact
  supported `no_native_turn` absence above (with a distinct `no_activity` reason).
  Never emit
  old `parked` as sufficient exclusion from the generalized view. Context-only
  uncertainty carries no current positive or negative authority.
- Coverage is complete only with current exhaustive runtime AND saved census
  support over their exact identity union and a proved selection decision for
  every identity. Reuse the existing bounded projection_census: Codex's complete
  daemon_threads census already requires loaded+saved completeness and includes
  their union. Do not add a second history roster. Census completeness alone
  does not prove activity-read completeness. All decision dependencies remain
  current. Unknown age is partial; loaded-only census never establishes complete
  recent-history scope.
  Complete-empty remains a supported claim, not an inference from `sessions=[]`.

Schema validation alone is insufficient: strict native admission checks exact
identity/body membership bijection, unique scope/clock/support sets, policy
digest, all clock/sample/support joins, cutoff arithmetic and ceilings, current
branch validity, field support, coverage dependencies and resource bounds. A
frozen frame cannot prove future owner comparisons; producer ceiling continuity
also requires service/revision continuity tests and independent vectors.

Mesh decomposition remains `owner.metadata=projection minus sessions`,
`owner.service=frame minus projection`, `records=sessions`. Restore is the exact
inverse. A null projection exports no positive current receipt/body authority.
Native clocks stay source BOOTTIME; no receiver wall-clock comparison occurs.

## Mesh and prepared facade: proposed supported path

Keep the existing `(host, source, native_socket)->adapter` factory API. A
trusted explicit working-set factory constructor captures the expected selector
and profile, checks them on every response, and exports only the existing
snapshot/proof/subscribe capabilities. Full/Tmux/active dispatch stays explicit;
no source-name magic, sniffing or full-feed fallback. The pure owner stays
Mesh-free. Mesh owns the additive schema/descriptor allowlist and lock change.

The prepared facade admits each replacement once and calls public snapshot()
once to retain its detached rows. Every claim calls `current(now,clock)` before
public `context()`, including complete-empty scopes. Generic static record rules
are conservative support bookkeeping; they do not implement the OR of evolving
active/recent alternatives or the new age bound. The domain facade independently
evaluates both exact alternatives and each displayed field at read time from
the admitted replacement and translated receipt metadata. Raw snapshot export
remains informational, never a currentness claim.

For native original receipt expiry E, Mesh-translated reader expiry H, and a
native **positive** cutoff Dlo, proposed reader upper cutoff is:

```text
H - max(0, E - Dlo)
```

All original receipt/context/accepted checks remain required, and all required
translated supports must be current. This clamps to E and can only attenuate
positive authority. Mesh must confirm the public translation assumptions.
**Do not use this attenuated upper cutoff to prove that Dhi has passed.** Early
expiry cannot establish a negative time fact. Readers use an explicit freshly
admitted native outside-window decision for definitive removal; after positive
expiry alone they return unresolved retained context. This avoids a new clock
bridge or SDK seam for lower-bound time authority.

The original service schedules both relevant conservative boundaries. On Dlo,
publish recent membership loss/uncertainty unless A remains true. On Dhi,
publish a supported outside-window decision only if A is proved false and its
other dependencies remain live. No collection or full-history query is caused
by either timer. Recompute from reconciled owner state, not copied wire DTOs.

Each material or metadata change increments projection revision. An actual
engine observation records its engine observationRevision; quiet expiry retains
that value. No-op reads/proofs/heartbeats neither increment revision nor renew
support. Watch/cache keys and pending/skipped bookkeeping use the new family
and projection revision, including equal engine revisions. Reconnect needs a
new baseline and exact policy/incarnation; partial reconnect cannot retire old
presentation context merely by omission.

## Limits, cost gates and review questions

Keep 4,096 tracked identities, 1 MiB combined scope/clock/decision ledger,
8 MiB body +16 KiB envelope, 32 Mesh receipts/host and current service shared
client/encoding bounds. Include all simultaneous legacy/full/working-set caches,
cutoff/event-key state, current/new generations, delayed-reader pins and copies.
Capacity refusal breaks affected coverage/continuity explicitly; no top-N or
active-row truncation. Scope and clock metadata also consume the frame bound.

Proposed CPU/byte gates in the product plan remain proposed: <=25% additional
matched owner CPU, and at 4 reads/generation with <=quarter selected body bytes,
>=30% lower combined producer/read CPU and >=50% lower total delivery bytes.
Measure 0/1/4/16 reads,100/500/2000 rows, active/recent bursts and dense fields;
full on-demand/cutoffs/recovery/slow peers and RSS stay explicit. P0's two small
sets justify testing these targets, not asserting them. No optimization campaign
or cap exception follows if they fail.

Exact review requests before dependent implementation:

1. Mesh: confirm public positive cutoff attenuation, raw-context facade union,
   exact source factory binding and proposed additive SDK1 profile decomposition.
   Name any concrete unsupported public seam; no generic API change is presumed.
2. RLCD: confirm active/recent/uncertain/context distinctions, explicit full
   history access, conservative boundary gap and removal-only-on-proved-negative.
3. Both: review independent floor/interval/receipt vectors and original coverage,
   cutoff/reconnect/resource gates before finalizing native schema/identifiers.

The preparatory pure helper currently covers floor boundaries, broad brackets,
unknown/future input, exact original sample/support joins, mirrored history,
service/boot/context changes, zero/default/max windows and all 27 union cases.
Stateful ceiling/timer, native semantic/schema, Mesh and producer qualification
remain future work, not implied by those unit tests.
