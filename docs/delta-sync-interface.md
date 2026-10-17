# Native synchronization G1 interface draft

G0 is closed under the exact `ed771e5` / `a376bc84` appendix. This G1 draft
allocates native request families and records the current implementation shape.
It is not schema/runtime/artifact acceptance. Schema hashes remain unfrozen until
compact packing and the public confirmed-view seams are agreed with Mesh.

## Native contracts and source

The native protocols are `agent-observer.sync/1` for full inventory and
`agent-observer.active-sync/1` for the fixed active selector. Profile IDs are
`agent-observer.mesh-sync.v1` and `agent-observer.mesh-active-sync.v1`.
Mesh's separate delivery/commitment/interface are `mesh.state-sync/1`,
`mesh.patricia-sha256/1` and sync interface 1. Existing interfaces are unchanged.

New packaged schemas are `agent_observer/contracts/sync-request.schema.json`
and `agent_observer/contracts/sync-frame.schema.json`; the latter describes both
explicit native views. `agent_observer.sync_native.descriptor(view)` returns the
native-only descriptor: protocol, version, exact schema digest, commitment,
view, selector digest and eight-table registry. Its digest is SHA-256 of the
canonical descriptor bytes. The owner never includes a Mesh source alias or
profile schema in this descriptor/root.

`CachedAgentSyncSource(host, path, view="full"|"active")` owns cached local
acquisition, with async `baseline`, `changes`, `head_after_nonce`, owned
`watch(cursor)` and `aclose`. Baseline returns a ticket with exact bytes, native
tag and cursor. Tags are JSON arrays `[nativeBindingDigest,generation,root]`;
cursors are `[ownerEpoch,generation,root]`. Generation is a contiguous sync
publication counter per view, distinct from legacy service revision and channel
sequence. Source/watch close never shuts down the native owner service.

An explicit native attempt also commits its attempt/inFlight diagnostics through
a bounded receipt/service-metadata transaction. It reuses the existing row,
body, observation, membership, scope and order roots. Internal history-to-runtime
promotion is suppressed until the single reconciled acceptance commits; no
half-accepted component state is published. Thus one external attempt followed
by acceptance can produce two contiguous sync transactions.

Requests contain `syncProtocol`, `version:1`, `hostScope` and `operation`.
`changes` additionally carries `baseTag`, `targetTag`, `maxTransactions<=4`,
`maxBytes<=8 MiB`; `watch` carries `cursor`; `head` carries an opaque strict JSON
challenge capped at 4 KiB, depth 8 and 256 nodes. This challenge is echoed and
correlated, never interpreted as a selector or client predicate.

## Owner binding and logical tables

NativeBinding keys are protocol/version/schemaDigest, hostScope/uid, view and
selector, ownerEpoch, bootId, clockDomain, sourceContexts and scopeContinuity.
Each source context retains provider, namespace, configHome/configHomeKind,
contextGeneration and the complete original RuntimeInfo tuple or null, including
empty/unavailable scopes. Continuity is a bounded list of
`[provider,namespace,continuity]` for active scopes. Native time namespace must
match `time:[digits]` before export/admission.
An active warming baseline still binds each configured empty/unavailable scope
with initial continuity 1; it contains no selected body or completeness authority.

The following names are current G1 vocabulary, pending counterpart review:

| Space | Logical key | Value |
| --- | --- | --- |
| records | full five-part identity | birth, stable alias, body, order, scope |
| bodies | body digest | exact stable API 4 content |
| observations | identity/birth pair | fields (moved paths), nine supports |
| memberships | cohort/identity/birth/field | locally derived field token |
| receipts | provider/namespace/component | complete original component DTO plus serviceId/contextGeneration |
| cohorts | same stable receipt key | receipt key, seal `[generation,memberRoot,count]`, accepted/sample/expiry |
| scopes | typed provider/namespace/fact/identity key | coverage or one member/uncertain/nonmember fact |
| metadata | bounded metadata name | original snapshot/projection/service anchors and bounded arrays |

Current field supports are `["cohort",cohortID]`; retained informational support
is `["context",originalFactSupport]` or null. Only a validated current membership
cell and explicit actual-reobservation assertion permit current head resolution.
Old context never follows a later head. A stable logical cohort ID does not
change when the immutable seal version advances. Positive ledger horizons and
presentation retention keep their accepted independent meanings.
Full coverage retains its exact original runtime-census and saved-receipt
support tuples. A later receipt under the same key cannot rebind an old complete
census to new evidence.

The original API 4 split/token table is in the accepted proposal. Full export
reconstructs its exact committed snapshot and array order; active export
reconstructs its exact committed projection. Neither diagnostic export grants
query-time currentness.

## Messages and acquisition

Every message has a closed `kind`. Initial logical baseline tables are arrays
of `[key,value]`; atomic operations are typed put/remove groups for all eight
spaces, with empty groups included. A put is `["put",key,expectedOldHashOrNull,
value]`; remove is `["remove",key,expectedOldHash]`. All hashes follow the G0
appendix; transaction IDs cover canonical bytes excluding transactionId.

Baseline carries descriptor/nativeBinding/tag/cursor/tables. Transaction carries
descriptor/nativeBindingDigest/transactionId/baseTag/resultTag/baseCursor/
resultCursor/operations. Head carries descriptor/nativeBindingDigest/tag,
challenge, ownerClock, originalReceipts, compact cohortHeads and attenuation.
OwnerClock contains bootId, clockDomain, boottimeMs, ownerEpoch, uid and hostScope.
It carries no roster or new evidence sample.

Head cohort entries omit the logical table's duplicate `receipt` field; the
cohort key is exactly that receipt key. Strict admission restores that one field
before comparing to the admitted logical head. The maximum 32-entry vector is
29,744 native bytes: receipt entry <=507 bytes and cohort entry <=297 bytes,
including commas. Fixed head bytes are 4,018. All are within the accepted caps;
this arithmetic/synthetic vector is not native performance acceptance.

Changes returns an exact bounded chain plus a terminal `complete` control whose
tag/cursor name the captured target. Missing base/target/quota returns explicit
baseline-required. Watch advances its cursor only after complete transaction
delivery; lost chains/backlog require baseline recovery. Complete/heartbeat
controls carry liveness only and never renew leases. A known moved head still
revokes that host, and catch-up remains outside the two-second proof attempt.

The owner retains current/predecessor decoded roots and one staged candidate,
at most four encoded change generations/8 MiB, and shared encoded full+active
buffers under 32 MiB inside the existing service 64 MiB budget. The runtime
counts unique buffers and pinned peer references, with total 16 local clients.
The pure indexed cache has the accepted shared 64 MiB decoded cap; these bounds
must pass real domain-shaped allocation/reclamation tests before promotion.
Map payloads, cache bookkeeping, owner binding/order containers, encoded buffers
and transaction encoding stages are charged. Canonical operation bytes reuse
the immutable map payloads; encoding does not first thaw changed bodies into a
second mutable roster. Independent replay tests rebuild all eight table roots
from the emitted transactions and compare detached full/active exports with the
same-generation fixture source; this is synthetic evidence, not native proof.

## Remaining G1 packing/query decisions

Logical roots are independent of compact wire packing. A pure, strictly checked
alias expansion may be required beyond membership masks to avoid repeating full
identities/births in every baseline table. The public profile normalizer/staging
seam must account for this before frame-schema freeze; there is no hidden full
restore or private Mesh-cache adapter.

The draft pure profile uses Mesh's declared public ordered index. Full keys are
`[runtimeGroup,identity]`; active keys are `[0,identity]` under the existing
single configured scope contract. Only changed record/order entries edit this
index. A synthetic test reads it through the public staging index API and
compares native order across a running-to-parked transition in both views.
The draft pure `PreparedAgentSyncRead` facade uses Mesh's public confirmed view,
checks currentness before context, and offers keyed or changed-key reads. Full
ordered export is explicit. The profile declares an eighth ordered `scope_keys`
index whose values are null; only insertion/removal of an actual scope key edits
it. Existing public index iteration provides whole-scope exceptions and exact
active export without a new generic table iterator. Prefixes enumerate negative
or uncertain keys directly. Keyed/changed-key reads do not enumerate either
index. Synthetic tests cover exclusion beyond the first 32 identities, partial
reconnect uncertainty, expiry and exact full projection export.

## Qualification status

The expanded eight-table baseline is a development representation. A 2,000-row
native-shaped synthetic fixture needs 11,823,094 bytes, exceeding the unchanged
8,404,992-byte frame cap. Membership masks alone do not meet the cold byte gate.
A separate packing prototype carries each original API 4 row once with alias,
birth generation and nine receipt-index/null/context support references. With
the bounded small tables it needs 3,369,960 bytes versus the original 3,297,477
bytes, an increase of 2.20%. This proves size feasibility only; that representation
is not emitted, frozen or admitted by the current implementation.

Producer CPU and capacity remain open. The new opt-in sync service selects the
canonical-byte table backend. An independent frozen-tree reference produces the
same logical roots and full/active exports. Byte-only leaves return detached point parses; only the
native owner does an explicitly counted linear normalization/index pass. Reader
admission remains sparse. Per-row construction envelopes are derived from the
unchanged finite API 4 shape, and final identity/order retention is immutable.

The coordinator clarified that internal canonical key/value buffers count under
both the aggregate 32 MiB encoded cap and the 64 MiB heap cap, once per physical
buffer within each cap. The byte backend now uses an incremental identity ledger
for stage/map sharing; retained outputs, journal, temporary encoding and peer
pins share the encoded cap. Its sharded bookkeeping is itself heap-accounted.
Whole-cache admission, capacity, recovery and cleanup still need qualification;
an output-only ledger or a canonical-length estimate is insufficient.

The canonical-buffer ledger now shares the heap account's identity index rather
than retaining another per-buffer dictionary and claim object. Each held encoded
buffer adds 16 bytes of metadata, plus nonpooled reference counters. Equal copied
buffers are separate allocations; shared physical buffers are charged once.
Transaction construction borrows canonical key/value fragments, hashes the
unsigned message incrementally, and writes its final frame through a preallocated
buffer. Both constructor-copy allowance and retained outputs count under both
caps. It avoids `bytes.join`'s additional buffer array per fragment. A held
rejection traceback is cleared after deterministic stage cleanup, so it cannot
retain rejected fragments after their reservation retires.

An earlier source experiment removed repeated identity schema/regex checks
inside already-admitted owner loops. Public identity/snapshot admission remains
strict, and publication still validates its complete result. Six 2,000-row
common-generation samples measured a median 811 ms with installed a7 and 636 ms
with the source overlay. This is exploratory component evidence, not installed
candidate ABBA or a combined producer gate. Earlier one-generation owner-stage
numbers excluded the final dual-budget integration and are historical only.
The complete new owner generation must include common work, diagnostics and all
sync publication work and be compared with matched a7 before promotion.

A later six-generation source-only timestamp experiment enabled both native
sync views and included attempt diagnostics, common publication and all sync
work. It retained two views without recovery, with accounted heap peak 61.55 MB,
54.32 MB retained, 18.22 MB of internal canonical buffers and 6.45 MB of journals.
Its median was 964 ms per generation. The preceding installed-a7 sample was
811 ms; these exploratory, separate runs do not satisfy matched installed ABBA,
the 10% target, or end-to-end acceptance. These are historical revision results.

The current fixed-schema optimization compiles complete SESSION/SNAPSHOT shape
checks once. The dynamic shape interpreter remains unchanged and all public
cross-field semantic and complete-publication checks still run. Differential
tests cover 4,662 nested malformed values plus typed equality, required/closed
fields, Unicode and schema-capture behavior on Python 3.11 and 3.14. The first
matched synthetic producer run includes six real timestamp generations,
attempt diagnostics, both sync views and the full semantic oracle. It measured
832 ms per generation with installed a7 versus 881 ms with source sync enabled,
an increase of 5.9%, with identical snapshot/projection/support/census signatures.
This is one source comparison, not repeated installed candidate acceptance.

A serial source ABBA repetition at 2,000 rows measured a combined median 825 ms
for installed a7 and 884 ms for the source overlay, an increase of 7.05%. Both
source runs used identical transitive source bytes, and all six generation
signatures matched across the four runs. This supports the producer target for
that synthetic input. It does not qualify an installed candidate, IPC, Mesh,
consumer CPU, cold/recovery or the other required workloads.

A split-table packing feasibility check keeps record definitions first, carries
each stable body without its repeated identity, and refers to observations and
membership masks by the admitted row alias. At 500/2,000 rows it uses
933,175/3,719,681 bytes, 12.91%/12.80% above Service 4. Both fit the unchanged
frame cap. Detached reconstruction exactly matches all eight logical tables;
an independent full Patricia rebuild matches NativeRoot. Duplicate definitions,
foreign body/observation aliases and inconsistent masks are rejected. The active
ten-row view uses 37,904 bytes. These are exploratory layout checks using the
current logical descriptor, not a frozen new schema or a budgeted wire codec.
Changing the eventual descriptor also changes dependent body IDs and tokens.

Dense body changes now retain the admitted current/predecessor roots rather
than rebuilding them when an optional encoded change frame cannot fit. The
chain is retired and callers receive explicit baseline-required. A 2,000-row
source fixture retained both views with a 66.90 MB heap peak, no cold rebuild
and one counted baseline fallback. CPU and packed baseline recovery remain
open; this does not turn the expanded over-limit baseline into deliverable data.

Head/control construction and queued peer output have separate shared heap
leases. Evicting owner cache output keeps the exact bytes charged until its
last delivery pin retires. Unqueued temporary results have a bounded 16-entry
FIFO and transfer to delivery pins without a copy. Rejection, completed write
and peer drop release their respective resources. Synthetic head probes at
100/2,000 rows measured 0.192/0.188 ms owner CPU and 0.878/0.884 ms including
header parsing, with 2,186/2,189 bytes. These code probes contain no IPC or
installed/native acceptance. Expanded packing and the full gates remain open.

## Acquisition budget seam still open

The draft `CachedAgentSyncSource` is not yet an aggregate-budget implementation.
Its strict full parser still allocates the whole decoded input. A subsequent
lifetime fix retires that document before a watch pauses, keeps only bounded
ticket/control fields and clears partial batches on failure. Unconsumed framing
bytes and intentional raw batch outputs remain retained. Byte and node caps
alone cannot bound Python heap: 1.1 million empty
arrays occupy about 3.3 MB of JSON but more than 64 MiB in list storage alone.
No source, installed-package or native acceptance is claimed for this path.

The standalone pure `sync_acquisition.parse_header` prerequisite scans the
expanded JSON grammar with bounded scratch and constructs only the structural
envelope and original receipts. Opaque body/operation trees are not decoded;
domain, entry, duplicate opaque-key, commitment and proof admission remain
mandatory at the Mesh boundary. Its closeable header ticket retains its decoded
reservation and grants no currentness or admission authority. It has no Mesh,
provider or service import. The opt-in source implementation below now uses it.

An explicit owned-input adapter is requested from Mesh: reservation precedes
socket/framing copies, sealing transfers that reservation to an opaque ref,
and input remains charged through decoder/stage consumption or deterministic
close. Baseline, change batches, watch frames and head/control payloads need that
same lifetime rule. Existing plain-byte source methods remain a separate ABI;
a bytes subclass cannot preserve ownership across ordinary copies. This public
common cache-backed handoff is now agreed at the source-contract boundary
below; its Observer source implementation is a controlled source checkpoint.
Aggregate qualification and compact normalization remain open.
No private cache access or uncharged transfer substitutes for that work.

The agreed additive ownership shape used by the Observer source is:

```text
OwnedSyncCache.input_owner() -> InputOwner
InputOwner.buffer_heap(nbytes) -> heap_bytes
InputOwner.close() -> None                 # cache/owning Reader only
InputOwner.reserve(heap_bytes, *, encoded_bytes) -> InputReservation
InputReservation.heap_bytes: int
InputReservation.encoded_bytes: int
InputReservation.resize(heap_bytes, *, encoded_bytes) -> None
InputReservation.seal(exact_immutable_bytes) -> OwnedInputRef
InputReservation.close() -> None
OwnedInputRef.nbytes: int
OwnedInputRef.close() -> None
```

Sealing transfers only the exact raw buffer/bookkeeping credit without copying;
other framing/header/container credit remains on its original lease. Framing
includes mutable receive storage, immutable conversion, overlapping chunks and decoder scratch;
it cannot release credit when a bare byte return crosses the source boundary.
The explicit owned-source variant carries refs in baseline tickets,
transaction tuples, watch values and nonce/control results. Public cache batch
and confirmation inputs need corresponding additive ref support. Existing bytes
methods retain their signatures. Failed admission, cancellation and close must
retire refs deterministically, including saved-failure tracebacks.

Input refs confer byte ownership only. The cache binds them to its exact
source/descriptor/callback/request configuration and intake epoch; foreign,
retired or consumed refs reject. First-version aliases use separate handles
and charges; physical backing-store sharing across aliases is not a public
capability. Every receiving admission and proof grants independent authority.

Mesh's earlier A1 session/relay packet at `a7be9ae`, SHA256
`05e5a9bef61d0235d6d82c326e630209dac610a122f581117bdb65beaa36183d`,
has a separate [original-packet review](delta-sync-relay-review.md): native
compatibility holds, while its standalone relay API needs corrections. Its
lifecycle question is addressed for the
cache-backed intake by Mesh `0ca3b99`, `docs/delta-sync-owned-input-api.md`,
SHA256 `7f7751ecd9df93277a3e7110ca72ebfda343d38fa629cd0212ec40b3a8f1d124`.
Observer accepts that exact common public signature/state contract for its
opt-in source implementation; this is not API/schema freeze, A1 relay approval
or implementation/resource acceptance.

A source session immediately revokes its own sealed refs when close starts,
then cancels and awaits its I/O. Receive/header reservations close only after
their physical storage retires. It never closes the shared cache-minted
InputOwner or parent source/service. Its ref registry can remain bounded by the public 64-item
ownership limit, preserving revokers for consuming refs and pruning only refs
known logically revoked rather than inspecting private state. The current
[`nbytes`-based implementation has a reproduced consuming-pin gap](delta-sync-source-pin-revocation.md);
the [exact public owner-bound query](delta-sync-input-retirement-agreement.md)
is agreed before dependent implementation of its fix.
`nbytes` rejection alone is insufficient evidence of terminal retirement. Independent
header/ticket leases keep metadata charged after its data ref is consumed.
Reserve/resize/seal reject after intake retirement; unsealed buffers and
consuming pins stay charged until their actual cleanup. Repeated close is safe.

The implemented opt-in source methods are `open_session(inputs)`, then session
`baseline`, `changes`, `changes_with_completion`, `watch`, `head_after_nonce` and `aclose`. They return
closeable owned tickets/controls or opaque input refs; their structural claims
are unadmitted. The plain-byte methods retain full strict parsing and their
existing types. Observer uses structural protocols without importing Mesh.
No relay byte-export capability or admission memo is supplied by this cache API.
The additive [completion-transfer result](delta-sync-completed-changes.md) owns
the exact original terminal control alongside its bounded transaction tuple;
legacy `changes()` retains its transaction-only success result. Its independently
prepaid container/header credit survives data consumption and retires with the
result. This source prerequisite does not accept relay/controller integration.
The later [immutable completion join](delta-sync-completion-join-recheck.md)
separately exercises actual source/relay forwarding and fresh independent Reader
confirmation on small synthetic full/active fixtures; wider gates remain open.

`agent_observer.sync_owned_source` prepays a 512 KiB session/control allowance,
768 KiB per active operation or watch for bounded requests/batches/callback
scratch, and separate receive/parser/header leases. These are charges within
the normal shared caps. It reserves receive growth before `recv`/resize,
immutable conversion and coexisting tail copies; capacity/slack and a 64 KiB
completed-callback allowance stay charged through retirement. The operation
lease retains request bytes plus that callback allowance. Structural parsing
adds 1,835,008 encoded bytes of conservative temporary credit; bounded decoded
headers retain independent leases until ticket close. These conservative
credits are not measured physical RSS or a substitute for aggregate gates.

Each operation has a fresh ownership scope, distinct from retained native
receipt/order history. A timeout after a completed receive revokes that
operation's otherwise lost result without revoking prior tickets. Whole API
operations are cancelled and awaited through cleanup, including outer request
and batch storage after inner I/O tasks complete. Watch close revokes its refs,
drops unread coalesced tails and clears decoded request frames before refunds.
Caller challenge/tuple preflight bounds allocation before the unchanged strict
request validator; it supplies no admission or proof authority.

Controlled protected-socket tests cover real full/active baselines reaching
independent receiver admission as unconfirmed candidates, full/active aliases
on one ledger, four-item batches, paused partial batches and coalesced watches,
foreign/consumed handles, header versus opaque duplicate rejection, quotas,
disconnect, repeated cancellation, saved failure traces and scope retirement
with cyclic GC disabled. This is source/test compatibility with exact Mesh
`0ca3b99`, not installed pairing or complete proof/IPC/SSH/resource acceptance.
Mesh's acquisition controller is not adapted by this Observer checkpoint.

Aggregate intake qualification must include each physically unique live buffer
and container: receive chunk, mutable pending bytes, immutable conversion and
any framing overlap; strict DTO or structural scan scratch/header; accumulated
change batch; paused watch and outstanding baseline/head/control/ticket refs;
output/stage/decoder pins and alias copies. A transfer can drop credit only
after physical retirement or gap-free handoff under the same ledger. Cancels,
rejections, saved exception traces and retired source/session/request paths must
leave no usable handle or uncharged retained input. The existing source-only
heap figures do not establish these peaks or the matched total CPU gate.

Changed-body admission validates the joined API 4 row once and computes its nine
tokens. Observation-only admission uses a compact cached semantic rule and
performs no stable-body lookup, join, validation or token hashing. Differential
facet fixtures compare that rule with the full row validator. These source
checks do not establish installed/native acceptance or satisfy the remaining
controlled CPU, cold/recovery, IPC/SSH and capacity gates. Candidate packaging
and independent installed/native qualification remain pending.

The explicit [compact native serializer](delta-sync-compact-export.md) writes the
agreed candidate baseline and sparse transaction representation directly from
committed tables. Its default, logical roots, nonce head and completion bytes
are unchanged. Source dispatch, identifiers/freeze, aggregate capacity, recovery,
total CPU and native/installed pair acceptance remain separate.

The [source checkpoint report](evidence/2026-10-16-delta-sync-source/REPORT.md)
pins the current implementation and matched ABBA samples. At `100637b`, real
N-row timestamps meet the source producer target (+7.37%), while changing a
stable field in every row fails it (+126.82%). This failed gate and the unfinished
packed recovery path prevent producer readiness.
