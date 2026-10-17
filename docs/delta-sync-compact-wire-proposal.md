# Agent compact raw encoding candidate

This is the concrete Observer raw-schema/position packet requested by RLCD
`e-31a774b7`, after coordinator compact R2 closure `5bb452a4`. It completes the
Agent wire grammar left open by the accepted generic R2 contract. It is a
**candidate for exact compatibility review**, not an allocated encoding, schema
freeze, configured runtime codec or producer acceptance. No existing schema,
descriptor, default, route, package version or installed selection changes.

## Exact inputs and candidate bindings

The accepted Mesh input is commit `b9dd8c610ea4575c1f4441d9331cfaef5ac1f58c`,
`docs/delta-sync-codec-contract-r2.md`, SHA256
`0920bf9ea7c2e76695c2cfe21016636a5ae3ebeac60f59be44f0fac914d8f44d`.
Observer's exact completion review is
[delta-sync-codec-r2-review.md](delta-sync-codec-r2-review.md). The earlier
[normalization decision](delta-sync-normalization-decision.md) remains unchanged;
Mesh R2 explicitly accepts its signatures, streaming phases, AliasSpec,
HeaderRef and empty compact callback expansion. A1 R4 is already closed under
root `818bdb7a`; this packet does not reopen that approval.

| Item | Concrete candidate |
| --- | --- |
| Encoding ID | `agent-observer.compact/1` (proposed, unallocated) |
| Schema ID | `urn:agent-observer:sync-compact-frame:1` (proposed, unfrozen) |
| Raw schema | [sync-compact-frame.schema.json](../agent_observer/contracts/sync-compact-frame.schema.json) |
| Raw schema SHA256 | `cad76406eceab62bb5ba982f3472258b0f604d05dc890a865c7cd2acb43fb23e` |
| Raw schema bytes | 177,724; complete, self-contained Draft 2020-12 |
| Logical descriptor | Exact existing `sync_native.descriptor("full" or "active")` |
| Native protocols | Existing `agent-observer.sync/1`, `agent-observer.active-sync/1` |
| Mesh profiles | Existing proposed `agent-observer.mesh-sync.v1`, `agent-observer.mesh-active-sync.v1` |
| AliasSpec | `aliases`, `("alias",)`, `("birth",)` |
| Required feature | Exact `provisional-memberships/1` |

The encoding schema digest describes these raw bytes. NativeBinding.schemaDigest
and the logical descriptor continue to describe the existing logical eight-table
contract. The EncodingBinding is exactly R4's `{id,schema,nativeDescriptor}`:
candidate ID, candidate raw-schema digest and digest of the selected logical
descriptor. Full and active have distinct descriptor digests. No source alias or
profile schema enters the native root. The same logical state, descriptor and
generation must produce identical body IDs, field tokens, table roots, cohort
seals and native roots in expanded and compact forms. SourceRoot adds only the
existing configured source/profile wrapper.

## Complete message envelope

The schema contains closed baseline, transaction, head and control variants. No
client-selected predicate, request selector, code path, alias interpretation or
dictionary side is accepted from opaque JSON.

| Kind | Required keys |
| --- | --- |
| baseline | `kind, descriptor, nativeBinding, tag, cursor, receiptRefs, tables` |
| transaction | `kind, descriptor, nativeBindingDigest, transactionId, baseTag, resultTag, baseCursor, resultCursor, receiptRefs, operations` |
| head | Exact existing native head variant, unchanged |
| control | Exact existing native control variant including its original optional base/target tags, unchanged |

`tables` and `operations` contain all eight names, including empty arrays.
Records, bodies and observations retain the 4,096-row limit; receipts/cohorts
retain 32; logical memberships retain 36,864 and scopes/metadata 65,536. Raw
group arrays are also bounded. Transaction syntactic operation limits remain
twice the table limits; generic final capacity and duplicate checks still apply.
The frame limit stays 8,404,992 bytes, journal four generations/8 MiB, and the
existing shared 64 MiB heap / overlapping 32 MiB encoded budget is unchanged.
Schema validation does not establish any allocation, wire-size or delivery gate.

`receiptRefs` is exactly `{before:[fullReceiptKey...],after:[fullReceiptKey...]}`.
Each list has at most 32 distinct full `[provider,namespace,component]` keys.
Baseline `before` is exactly empty. Each key, even unused, must exist on its
declared side. Array order is arbitrary and message-local. Every typed index
uses only its fixed side; neither missing keys nor reordered dictionaries permit
fallback. The raw receipts table and all receipt operations retain full keys and
exact original receipt objects. Stage receipts before resolving other receipt
indices, after records; no receipt dictionary supplies authority or a historical
receipt bank.

The transaction ID is the existing domain-separated hash of canonical **raw**
message bytes excluding `transactionId`. Compact and expanded IDs can differ.
Expected-old value hashes always refer to the restored logical before value.
Native tag/cursor contiguity, binding, root, receipt and proof checks are unchanged.

## Fixed value positions

Array positions below are zero-based and fixed by the local schema. Only the
explicitly named positions are references. All nested API 4 objects keep their
complete original closed schemas, optional-key presence, nulls, integer bounds
and values. Native thread identity remains distinct from session-tree root ID.

| Space | Raw key | Raw value and restoration |
| --- | --- | --- |
| records | Full five-part identity | `[alias,birthGeneration,bodyHash,orderGroup]`; restore birth `[ownerEpoch,birthGeneration]`, order `[orderGroup,identity]`, scope `identity[1:3]` |
| bodies | Exact logical body hash | 18-position content tuple listed below; identity position is an AFTER RawRecordRef |
| observations | RawRecordRef | `[moved6,support9]`, positions below |
| receipts | Full receipt key | Exact existing receipt object |
| cohorts | Receipt index | `[seal,accepted,sampledBoottimeMs,expiresBoottimeMs]`; restore duplicate logical `receipt` from the resolved key |
| scopes coverage | `[provider,namespace,"coverage"]` | Exact original full or active coverage object; full original support tuples remain literal |
| scopes live member | `["members",RawRecordRef]` | Nine nullable receipt indices; restore full identity, scope key and named field map |
| scopes nonmember/uncertain | Original full scoped identity key | Exact original decision object including full identity and original support; no alias/ref substitution |
| metadata | Fixed literal metadata name | Exact closed service, snapshot header, projection header, scopeOrder or validationSources value |
| memberships | R2 group form | Sole generic mask expansion after validated tokens; no per-cell wire writer |

The full identity order is
`[hostScope,provider,namespace,nativeIdKind,nativeId]`. A RawRecordRef is
`[alias,birthGeneration]`, with positive non-boolean integers. Resolution requires
the exact selected epoch and birth, and birth cannot exceed the proposed
generation. Records are processed first regardless of JSON property order.
Surviving identity keeps birth/alias. Retirements and additions establish the
simultaneous provisional overlay; final semantic aliases must match it.

Body tuple positions 0 through 17 are:

```text
identity, nativeIds, title, kind, cwd, cwdSource, inventory, hasSavedHistory,
phase, runtime, outcome, blockedReasons, createdAt, activity, lastUpdated,
latestTurn, workspace, metadataIssues
```

Only position 0 changes to a RawRecordRef. For example, a present null optional
member inside lastUpdated remains a present null; an absent optional member
stays absent. Null phase remains null. Body hash verification is over the fully
restored stable API 4 content, never the compact tuple. Domain joining and each
field's support/value checks remain the profile's independent responsibility.

Moved positions are `runtime,phase,activity,outcome,lastUpdated,latestTurn`.
Runtime is `[health,observedAt]`; phase is null for an absent moved phase or
`[health,observedAt]`. Activity/outcome are health scalars. LastUpdated/latestTurn
are `[health,observedAt,timing]`; timing is null or
`[component,sampledBoottimeMs,observedBoottimeMs,contextGeneration]`. These are
literal original timing values, never reconstructed from a newer receipt.

Support positions, member-field positions and mask bits share the exact order:

```text
runtime, phase, kind, savedIdentity, activity, outcome, workspace,
lastUpdated, latestTurn
```

Observation support is null, an AFTER receipt index for a current cohort, or
literal `["context",originalFactSupport]`. Member fields are null or AFTER receipt
indices. Retained negative, uncertain and context support remains literal even
when a newer same-key receipt exists. No packing step slides its sample, expiry,
context generation, acceptance counter or source incarnation.

For nonmembership transaction operations, removes use BEFORE keys; puts use
AFTER keys and AFTER references in values. Bodies removed by hash have no alias
reference. Expected-old lookup for a put still uses the resolved logical key in
the admitted before state. Combined before/after group updates must resolve the
same full cohort, identity and birth. Alias reuse by distinct new identity uses
separate removal and insertion groups; old references cannot bind to the new row.

Baseline membership is `[[afterReceiptIndex,alias,birthGeneration],mask]`, mask
1..511. Change is `[beforeSide|null,oldMask|null,afterSide|null,newMask]` with each
side `[receiptIndex,alias,birthGeneration]`. Old null asserts exact absence;
old zero rejects. New zero deletes and requires null after side. New null rejects.
Duplicate resolved groups reject even when identical. Omitted/equal mask edits
still receive genuine changed field tokens. The compact callback returns
`membership_expansion == ()`; generic code alone derives cells after checking
the profile's tokens, then verifies all eight roots/seals atomically.

## Implementation boundary and next integration

[sync_compact_schema.py](../agent_observer/sync_compact_schema.py) reproduces the
new schema; [sync_compact_values.py](../agent_observer/sync_compact_values.py)
implements one-value pack/restore helpers and explicit sided lookup callbacks.
These helpers require complete per-value schema validation before restoration.
They borrow literal child objects for immediate synchronous serialization or
`ctx.pack`; the future caller must prepay current-value and overlay scratch.
They do not retain a detached roster, import Mesh, perform I/O or grant admission.

The agreed runtime plan will scan strict complete framing, retain borrowed raw
under its input pin, and expose bounded receipt dictionaries separately from the
public logical HeaderRef. Its structural header restores the existing logical
projection: bounded receipts plus empty opaque table/operation placeholders.
Dictionary metadata is not a public authority claim. Each complete raw value
must pass its local schema before yield; dynamic refs resolve against public
before/provisional contexts and immediately pass into generic-owned `ctx.pack`.
Late malformed values reject the entire candidate. There is no whole-DTO
restoration or private generic graph access.

This packet does **not** yet implement NativeInputPlan, the configured generic
NativeCodec, the compact profile branch, scanner extension, native streaming
export or source/factory dispatch. Existing expanded paths remain selected.
The intended native/source convention is explicit trusted encoding configuration,
expanded by default, with one selected sync serializer/journal per owner and all
peers sharing its existing caps. An encoding mismatch fails rather than guesses
from source names or bytes. This convention needs Mesh compatibility confirmation
before dependent integration; it grants no second journal or fallback path.
Head/control retain their exact logical bytes under that configured encoding and
head-only decode remains separate from material plan construction.

## Reproduction and bounded evidence

[compact-raw-vectors.json](evidence/2026-10-16-delta-sync-source/compact-raw-vectors.json)
contains eight full/active baseline states and ten transactions. Baselines cover
original running rows, observation-only refresh, value change, null-phase parked
rows and an active-empty negative decision. Eight transactions come from the
value-change and parked-transition ServiceState synthetic chains, including
their separate diagnostic generations. Two additional transactions derive valid
old-A/new-B same-alias states with new birth and deliberately distinct thread/tree
IDs; they are not native occurrence evidence. Eight schema-valid semantic/model
rejections cover before/after birth, combined rebirth, old mask, duplicate group,
expected-old hash, body ID and cohort seal.

The [generator](evidence/2026-10-16-delta-sync-source/make_compact_raw_vectors.py)
uses source helpers and a tiny **whole-map fixture model**. The independent
[stdlib verifier](evidence/2026-10-16-delta-sync-source/verify_compact_raw_vectors.py)
imports neither producer nor Mesh. It restores all logical tables and independently
recomputes body IDs, 144 field tokens, eight-table/cohort/native/source roots,
raw transaction IDs and the eight rejection outcomes. Its separate lossless
partition join also reproduces the fixture's seven selected baseline API 4 rows
and their field inputs; this is not independent API 4 semantic admission. It uses the existing
independent canonical/Patricia arithmetic helper. A toy profile-schema digest is
explicitly fixture-only. It checks prior model state survives failed operations;
this is not runtime rollback or a sparse implementation.

```text
python -B docs/evidence/2026-10-16-delta-sync-source/make_compact_raw_vectors.py
python -B docs/evidence/2026-10-16-delta-sync-source/verify_compact_raw_vectors.py \
  docs/evidence/2026-10-16-delta-sync-source/compact-raw-vectors.json
```

Python 3.14.8 and 3.11.17 produce identical fixture/verifier bytes. The
[review manifest](evidence/2026-10-16-delta-sync-source/compact-wire-review.json)
pins source inputs and check logs. Ten focused tests also cover complete schema
reproduction, warming full/active, unchanged head/control, malformed positions,
null/optional values, literal retained support and future-birth rejection.

Actual runtime expected-old/root/domain rollback, revocable plan/intent lifetime,
one-row preallocation, shared heap/encoded/pin/RSS peaks, full/active dense CPU,
deliverable 2,000-row cold/recovery bytes, populated local IPC/fixed SSH and the
exact immutable installed pair remain open. Previous CPU failures remain failures;
this packet supplies no CPU saving, wire-size or producer-readiness claim.
