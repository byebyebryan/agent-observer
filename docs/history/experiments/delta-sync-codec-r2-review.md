# Observer acceptance of compact normalization revision 2

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **Observer accepts the exact R2 public-intent and raw-reference
completions below; no remaining owning contract conflict**. This answers Mesh
event `e-0ba504dc` under the existing G1 coordination. The coordinator's contract
reconciliation still precedes dependent shared implementation. This is neither
an Agent compact schema/encoding allocation nor runtime or resource acceptance.

## Exact input and agreement

Immutable retrieval on Starship verifies Mesh commit
`b9dd8c610ea4575c1f4441d9331cfaef5ac1f58c`,
`/home/bryan/code/mesh-plus/docs/delta-sync-codec-contract-r2.md`, 27,992 bytes,
SHA256 `0920bf9ea7c2e76695c2cfe21016636a5ae3ebeac60f59be44f0fac914d8f44d`.
Its committed review manifest is SHA256
`a3555b021414e45bac432190ebf9eff863763d8d4590f500df744beb887a0273`.
The [agreement evidence](../../evidence/2026-10-16-delta-sync-source/codec-r2-agreement.json)
binds those exact bytes, the new reference fixtures and the independent checker.

Mesh explicitly accepts the unchanged [Observer normalization decision](delta-sync-normalization-decision.md)
at `ffa302fba16f90d00c39229ae810547aeb850908`, SHA256
`35b1911388e75f4bc2a87087f23f07f7ca95346719933d7b37a5365d528734d6`.
That settles its signatures, AliasSpec/HeaderRef, streaming phases, before/
provisional/final aliases and compact single-writer decisions. The following
R2 completions fit the same Observer model without a counterproposal.

## Public handles and configured codec

Accept the additive `OwnedSyncCache(..., native_codec=None)` keyword: absent
codec keeps the strict expanded path. A configured codec and its immutable
spec/callback identities are captured locally; payloads cannot choose a codec,
profile, factory or fallback. Compact setup requires the exact configured
encoding/schema/native descriptor and explicit profile feature support.

Accept engine-minted `MembershipGroupIntent` with `cohort`, `record_ref`,
`old_mask`, `new_mask`. Its arrays use the existing metered readonly reference
and prepaid detached-materialization pattern. Property access and iterator next
reject after stage retirement; detached values grant no authority. AliasView
returns the same public reference family. The codec must explicitly prepay and
retain any detached normalized-DTO copy through engine adoption.

Baseline intents name each declared group with old mask zero; delta intents
name only explicit resolved group assertions, including equal-mask assertions.
Omitted groups inherit admitted before masks. Token-only implicit changes are
derived after the semantic callback rather than inventing callback group edits.
Compact callback `membership_expansion` remains exactly `()`; the generic engine
is the sole cell writer after independently validated tokens. Expanded behavior
and all four semantic callback signatures remain unchanged.

## Exact raw references and side selection

Accept the closed candidate reference grammar:

```text
RawRecordRef = [alias, birthGeneration]
RawGroupSide = [receiptIndex, alias, birthGeneration]
RawBaselineGroup = [afterSide, mask]
RawGroupChange = [beforeSide|null, expectedOldMask|null, afterSide|null, newMask]
receiptRefs = {before: [fullReceiptKey, ...], after: [fullReceiptKey, ...]}
fullReceiptKey = [provider, namespace, component]
```

The exact message binding restores owner epoch. Alias/birth must match the
chosen view's full five-part identity and birth; no bare alias or foreign epoch
is admitted. Alias is 1 through 2^64-1, birth generation 1 through proposed
generation, with bool rejected. A surviving identity keeps alias/birth. Distinct
A-to-B alias reuse needs separate removal/insertion groups; a duplicate logical
record operation cannot manufacture same-generation rebirth.

Each bounded receipt dictionary has at most 32 distinct full keys. Baseline
before is empty; before keys must exist before and after keys must exist in
candidate receipts. Candidate resolution uses receipt edits plus bounded before
keyed lookups. A dictionary can be a subset and confers no completeness, support,
reobservation or currentness. Index zero is valid; missing/null/bool/negative/
out-of-range indices and duplicate keys reject.

Every side is fixed by the typed schema position. Removals/expected-old refs
resolve before; new record/body/observation/support refs resolve after. Cohort
deletion resolves before and put/replacement support after. Original context,
negative and uncertainty values keep their exact expanded form; unavailable
identities do not receive invented live aliases. Receipt reorder/removal cannot
make an old ref use the after dictionary, or a new ref fall back to before.
Unlisted opaque values retain their exact logical form.

For a group change, before is null iff old mask is null; after is null iff new
mask is zero. Null-old to zero rejects. Two present sides must restore the same
full receipt key and full record ref even if their receipt indices differ.
Duplicate detection uses that resolved cohort/identity/birth key. Old masks
still require admitted before cells; new masks and references are provisional.
Every exact mask, token, original support, body/schema/join and root check remains
independent at admission. The native transaction ID covers original raw bytes,
including both dictionary arrays, through the agreed canonical ID formula.

## Bounded evidence and remaining gates

The stdlib [independent reference checker](../../evidence/2026-10-16-delta-sync-source/verify_codec_r2_refs.py)
imports neither producer nor Mesh's oracle. On Python 3.14.8 and 3.11.17 it
reproduces all six positive cases, both removal/insertion permutations and all
26 named rejection outcomes in the new fixture SHA256
`82f70805585aed2d7a70a2d10736de5650c9dad370b5cb811121fd47ad1761be`.
Outputs match across versions. It uses its own tuple-keyed toy definitions and
side dictionaries; upstream byte-for-byte replay is recorded separately.
Baseline checking explicitly supplies an empty before dictionary.

This proves toy sided-reference/mask syntax only. It does not test admitted
before masks, receipt existence/health, native schema, semantic support,
stage/ref retirement, rollback, roots, authority, performance or transport.
Existing R1 eight-state/permutation and joined full/active native fixtures remain
prior bounded evidence, with no new runtime claim from this reference review.

The actual Agent raw compact envelope/positions/schema/encoding and joined raw
restore vectors remain Observer-owned and unallocated. Those must preserve the
exact normalized eight tables/cohort/native/source roots under one complete
descriptor/generation. A descriptor change requires recomputed body IDs/tokens
and ordinary new-binding admission, not inherited old authority.

After coordinator reconciliation, shared staging still needs strict streaming
schema/domain admission, before-mask checks, omitted-mask token updates, compact
nonempty-patch rejection, atomic failure/cancel cleanup, codec/plan/iterator/
header revocation and GC-disabled held-error lifetime. All raw/DTO/overlay/
canonical/index/expanded-node/pin costs remain within the shared 64 MiB heap and
32 MiB encoded caps. Actual sparse visits, full/active capacity, dense/cold/
recovery CPU/bytes, RSS and installed populated IPC/fixed SSH pairing remain
open. A1 relay agreement is separate. No runtime/schema/package, sibling,
provider/service, selected tuple, consumer or rollout changes accompany this
contract review.
