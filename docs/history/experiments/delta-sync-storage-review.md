# Observer dense storage and compact-mask review

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **no domain objection to a constrained private prototype; representation,
compact ABI and producer acceptance remain open**. This answers Mesh
`e-207afd0d` within G1. No runtime, schema, cap, installed selection or sibling
file changes accompany this review. Frozen G0 commitments remain unchanged.

## Exact evidence and conclusion

Reviewed Mesh runtime `95c406f22f6857076da0253f98a3542488239e08` and diagnostic
commit `4121cbb87547ed54853f909a06971033fe034008` on Starship. The latter's
`docs/evidence/2026-10-16-delta-sync/DENSITY-REVIEW.md` is SHA256
`a1687e05db50e4a371d400318a10885887377f6436b1d37b23c8909e2ae674e3`.
The recorded normalized-density JSON is SHA256
`94eb0e389080a5eb5d37d4864714200085d47d0113d370670a3ac4c1ea221372`.
Its 58 runtime/script hashes match the respective committed inputs. The
259-core/31-Observer source-gate JSON is SHA256
`a840d59edd524e8779df9da6f6e4f7b857bf24ea0c667b381eb68e5ca2e2f278`;
its log hashes were checked, without rerunning those gates or the benchmark.
The [owning evidence record](../../evidence/2026-10-16-delta-sync-source/density-source-review.json)
binds this review and the Observer sources inspected.

| Records in each structural view | Retained after first | Retained after both | Accounted heap peak |
| --- | ---: | ---: | ---: |
| 100 | 2,548,579 | 5,087,774 | 6,558,965 |
| 500 | 12,596,396 | 25,183,396 | 31,940,541 |
| 2,000 | first stage rejected | second not attempted | 63,897,393 |

This is a distinct decoded-storage blocker before frame/proof intake. Wire
packing alone cannot qualify it. The 2,000-row peak leaves 3,211,471 bytes under
64 MiB, but that is peak headroom, not rejection-time available credit. The
record omits the rejected reservation's requested size; this review does not
independently reproduce its refusal arithmetic. Future resource qualification
should capture that request and available credit before any failed allocation.
All recorded final retained/reserved/encoded/pending counters are zero.

The fixtures use minimal bodies, nine fields, no declared domain indexes and
two independently described generic views. Their caller-owned normalized DTOs
and full oracle are outside the cache ledger. They are neither Agent full/active
capacity nor total process memory. No savings ratio, RSS plateau, native proof,
transport, installed artifact or combined CPU pass follows from these numbers.

## Compact membership callback boundary

Agree with avoiding a roster of per-field public operation/ref objects for
compact masks. Baseline grouped declarations may require O(N) normalization;
the callback should see public grouped intents and bounded point mask queries,
not an invented final cell table. After validated field-token/index output,
the generic engine must independently produce every logical membership cell,
check exact old masks/values and verify global/grouped/native/source roots.
Logical cell cardinality and all actual expansion work still count.

The candidate revision-1 codec contract, SHA256
`a67f11aee6c4b9f50048fbda55bdd4f82c6766ec69cd07abf31b749c3ba5b0b8`,
fits that direction. One exact writer rule needs to be explicit before shared
implementation: **compact mode requires an empty
`DomainIndexPatch.membership_expansion`; reject a nonempty value**. Generic
mask expansion plus the independently validated `field_tokens` patch is the
single cell writer. Expanded mode retains its existing G0 patch/operation API.
This is a proposed clarification, not same-byte acceptance of revision 1.

The current Agent callback's `_field` and `_removed` inspect actual candidate
membership cells. It must explicitly advertise and implement the reviewed
compact feature before using provisional masks instead. No feature discovery,
pretend after cells, inferred currentness or silent profile substitution is
acceptable. Preserve before-only old mask/token validation, separate alias
before/after resolution and exact identity/birth refs. A mask, renewed receipt
or changed token cannot substitute for original support or domain validation.
The existing [codec review](delta-sync-codec-review.md) and joined native-vector
gate remain open; this density review does not settle them or the A1 role.

## Private arena ownership requirements

An internal node arena can preserve the public ABI. Observer has no domain
objection to a prototype meeting these constraints:

- Count ownership per live node edge and external root/stage/view/I/O pin.
  Page occupancy must not act as a reason to retain dead nodes' children or
  payload references. Clear a dead slot's outgoing edges/payloads and retire
  their exact ownership even if another live node keeps the page allocated.
- Charge whole allocated pages, slack, free-slot maps, refcounts, generation
  tags, root registries and temporary rollback work before allocation. Canonical
  key/value and encoded payload buffers remain in both the existing 32 MiB
  encoded aggregate and 64 MiB heap aggregate. Encoded-pool capacity stays
  charged while allocated; separate metadata pages still consume heap credit.
  Physical sharing counts once per cap; copied buffers add another charge.
- A reused slot/page cannot satisfy an old handle. Bind handles to arena/scope
  and slot incarnation, reject stale/ABA access and define counter exhaustion.
  Do not reuse a node while any valid root, public reference or output pin owns
  it. Revocation cannot refund storage still retained by an in-flight consumer.
- Preserve immutable prior roots and their canonical values, tokens and child
  edges. Factored membership lookup cannot consult the newest token bank to
  reconstruct an older root's value. No restored row or shared node transfers
  source/profile/request/currentness authority between independent caches.
- Keep cleanup deterministic with cyclic GC disabled, including partial page
  construction, callback/root/capacity failure and saved errors. Retirement of
  predecessor material stays outside the two-second native/bridge nonce path.
  Meter cleanup CPU, including failed staging and subsequent bounded recovery.

The design must identify the actual owner for each page, live edge, canonical
buffer and pin. A page may retain unused capacity until it empties, but its full
charge remains live; dead descendant graphs must not. No reduced accounting
allowance, raised cap or silent baseline discard turns this into acceptance.

## Required qualification before promotion

Compare the new backend against independent G0 canonical/Patricia/root vectors,
full explicit eight-table results and strict Agent full/active joined fixtures.
Exercise mask insert/remove/subset/token-only changes, alias reuse, old birth,
bad old value, callback/root failure and atomic rollback. Logical point reads,
detached values, committed order and metered enumeration must remain identical.

With GC disabled, retain current and predecessor roots, an overlapping stage
and slow-peer pins across eviction; retire dead nodes on partly live pages;
reuse freed slots and reject stale handles. Fail every new page/edge/payload
reservation before allocation and verify prior roots, revocation and zero-live
cleanup. Include paused input, header/DTO/callback, output and consuming pins in
the same full+active/all-peer budgets and actual RSS/plateau measurements.

At 100/500/2000, demonstrate actual sparse key/branch/rehash/classification and
iterator counts: one changed existing field cell edits its global/grouped leaf
and cohort head without rekeying or scanning unrelated members; receipt-only
renewal does zero member edits. Count all domain body/facet/reference work and
private storage/normalizer/cleanup CPU in the same totals. Cold, all-body and
failed-frame/recovery work must meet the original numeric gates. The existing
dense producer CPU failure and 2,000-row frame/recovery failure remain explicit.

No candidate qualification is established until codec, role, storage, aggregate
resources, exact paired artifacts and installed/native transport gates close.
