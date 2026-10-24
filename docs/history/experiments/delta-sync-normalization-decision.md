# Observer G1 normalization decision packet

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **concrete Observer proposal for same-byte Mesh agreement before shared
implementation**. This answers RLCD `e-fa6dd9db`. The absence of implemented
candidate classes is expected and is not an objection. No runtime, schema/ID,
cap, artifact, installed selection, relay role or sibling edit is authorized by
this document. Private Mesh storage work may proceed under the existing G1
authorization without waiting for this packet.

This single decision packet incorporates Mesh's original codec proposal SHA256
`4187fd9befabba300e2f8a36a653f4d2b564c1c0157cc9e35089cd09f47f9f56`
and its more precise revision-1 contract SHA256
`a67f11aee6c4b9f50048fbda55bdd4f82c6766ec69cd07abf31b749c3ba5b0b8`.
The exact signature/phase decisions below supersede ambiguous early wording.
Mesh agreement on these bytes is still required; this is not a unilateral ABI
freeze. Frozen G0 appendix `a376bc84…` and all old packaged bytes stay unchanged.

## Accepted signature candidates and explicit completions

Observer accepts the following revision-1 surface for the planned Agent codec:

```text
NativeCodec.spec: CodecSpec
CodecSpec(encoding_id, encoding_schema_digest, native_descriptor_digest,
          fields, alias_spec, required_profile_features)
AliasSpec(index: str, alias_path: tuple[str, ...], birth_path: tuple[str, ...])
SyncProfile.normalization_features: tuple[str, ...]

NativeCodec.open(raw: bytes, budget: BudgetRef) -> NativeInputPlan
NativeCodec.entries(plan, space, ctx: NormalizationContext)
    -> owned iterator[NormalizedEntry | MembershipGroup]
NativeCodec.operations(plan, space, ctx: NormalizationContext)
    -> owned iterator[NormalizedOperation | MembershipGroupChange]
NativeCodec.head(raw: bytes, budget: BudgetRef) -> NativeHeadTicket
NativeInputPlan.header: HeaderRef
NativeInputPlan.close() -> None
NativeHeadTicket.header: HeaderRef
NativeHeadTicket.close() -> None
HeaderRef.materialization_bytes: int
HeaderRef.materialize() -> dict

NormalizationContext.before, after_records: PublicStateRef
NormalizationContext.aliases.before, after: AliasView
NormalizationContext.binding, descriptor, budget, visits
NormalizationContext.pack(value: JsonValue) -> CanonicalValueRef
CanonicalValueRef.close() -> None
AliasView.get(alias: int) -> RecordRef | ABSENT
AliasView.resolve(alias: int, birth: FrozenValue) -> RecordRef

NormalizedEntry(space, key, value: CanonicalValueRef)
NormalizedOperation(space, op, key, expected_old_v, value: CanonicalValueRef?)
MembershipGroup(cohort, after_ref: RecordRef, mask: int)
MembershipGroupChange(cohort, before_ref: RecordRef?, expected_old_mask: int?,
                      after_ref: RecordRef?, new_mask: int)
PublicStageContext.compact_memberships: bool
PublicStageContext.membership_mask(cohort, record_ref, *, side: "before"|"after") -> int
PublicStageContext.membership_changes() -> owned iterator[MembershipGroupIntent]
MembershipGroupIntent(cohort, record_ref, old_mask: int, new_mask: int)
```

The two explicit type completions are AliasSpec's three fields and HeaderRef's
existing materialization pattern. For Agent, AliasSpec names `aliases`,
`("alias",)` and `("birth",)`; identity is the full record key. Fixed local
schema data owns every other reference path. HeaderRef is revocable, exposes
bounded structural header data only and retains no opaque body/observation
roster. Its detached materialization is prepaid using the advertised cost and
remains caller-owned/charged through actual retirement. Neither header access
nor an alias lookup grants admission or currentness. No public raw-byte export
or private graph access is added.

CodecSpec and the explicit feature tuple are immutable trusted configuration,
captured with codec/profile/callback identities and the applicable cache,
source/request/incarnation scope. Fields equal the descriptor's ordered fields.
The Agent compact feature remains the candidate `provisional-memberships/1`.
Missing support rejects compact setup. Encoding/schema IDs and actual schema
bytes remain unallocated pending joint review; wire data never chooses code.
A changed native descriptor requires its ordinary new binding/baseline path.

## Validation and ownership phases

Per-space iteration replaces the original undivided operation iterator. The
generic engine controls phases regardless of input property or operation order:

| Phase | Public data and checks |
| --- | --- |
| Owned intake | Reserve before receive/copy/parse; consume into a live input pin; no material authority |
| Plan open | Scan complete bounded JSON grammar, closed header and structural table/operation framing; bind exact configured encoding/descriptor; retain borrowed raw only under its input pin |
| Record definitions | Decode and validate record wire values one at a time; validate duplicate logical operations and old values; stage immutable record slots and before/after declared alias overlay |
| Remaining values | Resolve old references only before and new references only after; validate each complete closed wire value before yielding its prepaid generic-owned CanonicalValueRef; stage observations, scopes, receipts, metadata, cohort declarations and grouped masks |
| Semantic callback | Expose provisional public records/aliases/masks; validate Agent body/join/support/scope/order and derive final indexes/field tokens; no confirmed root or authority handle |
| Generic completion | Validate/freeze/charge patch, compare independent final aliases, expand masks using validated tokens, check every table/cohort/native/source root and transaction ID; candidate remains unconfirmed |
| Fresh proof | Separate head-only decode and unchanged independent proof/receipt/clock/request checks; publish only on success |

This streaming phase rule makes the early "strict schema before yielding"
wording precise. Open does not build a complete detached native DTO. Each wire
value must pass its structural schema before it is yielded, and every required
space/operation iterator must be exhausted and validated before a candidate can
survive. A late malformed value rejects the entire stage. Domain and cross-row
checks remain independent. No partially checked value, mask or root authorizes
a query. An implementation requiring a full parsed roster before iteration
conflicts with this packet and the accepted one-row callback boundary.

The engine may have only bounded current-value scratch per iterator. It closes
an iterator before switching spaces, then closes remaining iterators before
the plan; only then can borrowed input pins retire. Raw, parsed-value, header,
alias/group overlay, callback, index and canonical-buffer credits overlap for
their actual lifetimes. `pack` synchronously snapshots strict integer-only JSON
under the same ledger and returns a single-consume, scope-bound owned value.
Adoption transfers ownership without a copy, gap or validation memo. An
unconsumed value remains charged until explicit scope cleanup. Saved errors,
retired refs and partially consumed iterators cannot retain a graph after that
cleanup. All accesses after retirement reject, with GC disabled as well.

`head` validates only a closed bounded native head/control, at most 49,152 bytes,
using a separately owned header ticket. It never calls open, entries, operations
or pack, constructs a body plan, catches up or retires old material roots.
The complete proof cap remains 65,536 bytes and its whole operation remains
inside two seconds. Separate catch-up and one fresh retry retain the original
absolute 15-second budget. A control is recovery/transport data, not a proof.

## Before, provisional and final aliases

The before AliasView resolves exact admitted definitions, including removed
rows. The after AliasView is only the declared overlay after all record
retirements and additions have been validated, in an input-order-independent
batch. `after_records` exposes those provisional slots; it does not expose a
verified final root. Sparse work uses changed definitions and keyed collisions,
not a copy or scan of the complete alias index.

The semantic callback alone derives the final public `aliases` index. Generic
completion compares that patch with the declared overlay for all touched aliases
(all definitions at baseline). The overlay cannot commit itself. Missing,
extra, conflicting or duplicate definitions reject atomically.

RecordRef is exact `[fivePartIdentity,[ownerEpoch,creationGeneration]]`.
Removals and expected-old references resolve only before; live replacement
values resolve only after, with no fallback. A surviving identity keeps alias
and birth. Removing A and inserting distinct B under the same alias is valid
only with separate before-A and after-B refs/groups. Duplicate operations on
one logical record key reject; no same-transaction hidden rebirth is inferred.
An identity reintroduced after a committed absent generation gets the new birth.
Foreign context/view/epoch and stale birth reject. Context-only scope identities
remain full identities; no live alias is invented for an unavailable row.

## Provisional masks and validated tokens

Accept revision 1's exact masks and side rules. Agent field order is runtime,
phase, kind, savedIdentity, activity, outcome, workspace, lastUpdated, latestTurn.
Baseline masks are integers 1..511. Old null means exact absence, old 0 rejects;
old 1..511 is checked against admitted before cells. New 0 deletes and requires
null after_ref; new 1..511 requires an after ref. New null, booleans, negatives,
high bits, null-to-zero and duplicate resolved groups reject. Both refs, when
present, must have identical full identity and birth. Equal nonzero masks assert
a set; they confer no reobservation or renewal authority.

`membership_mask(..., side="before")` reads real admitted cells or a tag-bound
exact group index. After queries return provisional candidate bits, including
zero for absence; they cannot satisfy old-mask checks or grant authority.
Compact after-membership cell lookup rejects `sync_memberships_pending` during
the callback. Grouped intents use full resolved refs, never alias-only keys.
The Agent callback explicitly branches on the negotiated compact feature;
expanded mode keeps existing real-cell behavior.

The exact single-writer clarification is: **compact mode requires
`DomainIndexPatch.membership_expansion == ()`; reject nonempty expansion**.
The profile supplies ordinary validated field tokens/indexes. Generic code is
the sole cell expander from masks and those tokens. Expanded mode retains its
G0 data-only membership-expansion API. Compact input cannot also contain explicit
cell operations. This prevents an N-per-field public operation roster before
or after the callback while retaining exact logical cells and their real costs.

Changed tokens update their incident retained-mask cells even when a mask edit
is omitted. Equal tokens do no cell work. Every after bit needs its exact after
token; a removed token with a retained bit rejects. Null JSON field data hashes
as C(null); token=None removes a token and is distinct. Original support,
receipt/context/clock and actual reobservation checks remain the Agent profile's
responsibility. A mask, proof, receipt renewal or token change cannot slide old
evidence to a newer sample. Failures roll back aliases, masks, cells and indexes
together. All eight tables and grouped seals must equal explicit logical edits.

## Owned intake is already agreed

Accept the common cache-backed contract SHA256
`7f7751ecd9df93277a3e7110ca72ebfda343d38fa629cd0212ec40b3a8f1d124`
without additional signature changes:

```text
OwnedSyncCache.input_owner() -> InputOwner
InputOwner.buffer_heap(nbytes) -> int
InputOwner.reserve(heap_bytes, *, encoded_bytes=0) -> InputReservation
InputOwner.close() -> None                  # cache/owning Reader only
InputReservation.heap_bytes, encoded_bytes
InputReservation.resize(heap_bytes, *, encoded_bytes=0) -> None
InputReservation.seal(raw: bytes) -> OwnedInputRef
InputReservation.close() -> None
OwnedInputRef.nbytes
OwnedInputRef.close() -> None
```

Observer `4030d50` implements opt-in `open_session(inputs)` and owned baseline,
changes, watch and head/control intake through that structural API. It leaves
plain bytes strict and unchanged. Seal transfers exact buffer/control credit;
other request/header/tail/batch credit stays live. A source closes its own
refs/leases, never a shared InputOwner or native service. Source/session/request
retirement revokes its refs immediately and awaits whole-operation cleanup.

Cache admit_baseline, stage and confirm consume a supplied ref on success or
failure. A valid bounded stage_batch transfers all supplied refs, including
unreached members after a failure. Invalid container/type/count leaves caller
ownership; the first bounded shape check is before transfer. Head/proof inputs
obey the same pin lifetime; a native head still needs its exact independently
validated Mesh proof wrapper. No ref exports bytes, grants admission/currentness
or crosses a foreign cache/config/intake epoch. Unsealed receives and consuming
pins remain charged until their real cleanup even after revocation. The 64-slot
bound and 64 MiB heap/32 MiB encoded aggregate remain unchanged. A1 relay-owner
factories, forwarding and role/proof agreement remain a separate exact packet.

## Agreement and later gates

Reader decoded-density failure remains independent of native-owner fit and
expanded wire failure. Whole pages/slack, canonical cells, plans, DTOs, aliases,
masks, indexes, callbacks, outputs and paused/consuming pins share the original
budgets. Neither a packed arena nor this ABI removes Reader admission.

This packet returns specific signature/phase decisions for agreement now.
Joint codec arithmetic and actual joined Agent body/observation/support vectors,
strict raw schemas, atomic failure/lifetime/sparse-count tests, dense CPU and
inclusive resources/RSS, native IPC/fixed SSH and exact paired artifacts remain
required before runtime freeze/promotion. Arithmetic success or a prototype fit
cannot substitute for those gates. No new wire ID or package version is allocated.
