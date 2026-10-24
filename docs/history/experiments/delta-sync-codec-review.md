# Observer G1 compact codec review

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **owning proposal; exact joint ABI agreement remains open**. This is a
review of Mesh `a7be9ae` and `docs/delta-sync-codec-proposal.md` SHA256
`4187fd9befabba300e2f8a36a653f4d2b564c1c0157cc9e35089cd09f47f9f56`.
It incorporates the coordinator's `e-91f27284` review without changing frozen G0
appendix `a376bc84…`. No compact schema, encoding identifier or runtime route is
accepted by this document. The [existing interface note](delta-sync-interface.md)
keeps prepaid intake and the separate A1 relay review open.

## Alias resolution and public references

Prefer the existing public `ctx.before.index("aliases").get(alias)` for admitted
old definitions. Define the proposed normalization `ctx.aliases.get(alias)` as
**candidate declared definitions only**, after all changed record definitions
have been staged. It is provisional data, not the profile's admitted final alias
index. `ctx.records` likewise names candidate record definitions. Before refs
never fall back to after, and after refs never fall back to a removed definition.
Both reference families are metered, revocable and callback-scoped.

The semantic profile remains the sole writer of its final `aliases` index.
Structural decoding declares a separately charged candidate catalogue; it must
not independently edit that same profile index. Generic code compares declared
aliases with the profile's independently admitted identity/birth/slot results
before committing either. Baseline builds definitions once; a sparse delta
applies only changed definitions and bounded keyed lookups, without enumerating
all admitted aliases.

| Material reference | Required resolution |
| --- | --- |
| Record/body/observation deletion and expected old membership | Admitted before definition and exact original birth |
| New body/observation/support put | Candidate after definition and exact candidate birth |
| Unchanged record reference | Exact same admitted identity/birth on both sides |
| Alias reused after removing a different identity | Separate before removal and after insertion; never reinterpret the old removal as the new row |

Generic normalized membership groups must carry full `[fivePartIdentity,birth]`
record refs after structural alias expansion. Different full refs stay distinct
even when their compact alias number is equal. Duplicates are checked on the
resolved logical group key `[cohort,identity,birth]`, not merely on the compact
alias. A reused alias may therefore require two distinct group edits.

The existing Agent profile permits removing identity A and inserting different
identity B with the same alias in one transaction. It rejects changing the birth
or alias of an identity that remains present. Duplicate remove/put operations
for the same logical record key remain invalid. Reintroducing the same identity
after a committed absent generation requires its new birth to equal the new
generation. Compact encoding must preserve these rules rather than create an
in-place rebirth operation.

A compact transaction also needs an explicit before/after basis for receipt
indices if it uses them. Deleting a cohort cannot resolve its old index through
a reordered candidate receipt list. The normalized cohort key remains its full
stable provider/namespace/component tuple. Exact raw reference shapes are still
a counterpart decision; no implicit fallback or order-dependent resolution is
acceptable.

## Masks and provisional callback input

Agent descriptor bit positions retain this exact nine-field order:
`runtime`, `phase`, `kind`, `savedIdentity`, `activity`, `outcome`, `workspace`,
`lastUpdated`, `latestTurn`. Its nonempty masks are integers 1 through 511;
booleans, negative values and unknown high bits reject. A baseline has no stored
zero-mask group and at most one group for each resolved cohort/record ref.

Proposed delta rules: `expected_old_mask=null` means exact group absence;
otherwise it is an integer 1 through 511 checked against **admitted before
cells**. A new mask is an integer 0 through 511; zero means deletion, never a
stored empty group. Null is not a new mask, and old zero is not a second absence
encoding. Reject absent-to-zero edits and duplicate resolved group edits,
including equal duplicates. An unchanged nonzero mask may assert the same set
while its validated field token changes. Each domain field still names its
single exact support ref; overlapping cohort assertions cannot authorize two
current supports for one Agent field.

The semantic callback needs a public metered iterator of changed normalized
groups, with full cohort/ref and before/after masks, and the proposed
`ctx.membership_mask(cohort,record_ref)` for candidate masks (zero when absent).
These are unadmitted assertions. They can check that an observation's claimed
support has a matching candidate bit, but cannot establish currentness, a valid
token, an accepted receipt or complete/removal authority. Body/schema/join,
original support, scope, birth and clock checks remain independent.

Keep the four semantic callback signatures and the G0 data-only patch contract.
The exact public changed-group type and relationship between
`DomainIndexPatch.membership_expansion` and generic mask expansion still need
joint specification. Generic code must independently check completeness and
exact correspondence of every derived cell, old value and validated token;
merely trusting a callback-supplied root or accepting a partial expansion is
insufficient. The expanded raw route remains strict and unchanged.

## Equivalent logical transaction and atomicity

After bounded structural definitions and nonmembership operations, expose only
provisional public data to the semantic callback. It validates actual Agent
content and produces charged immutable index/token/derived-operation data.
Generic code checks and applies that patch, then verifies all table/grouped
cohort/native/source commitments before publication or proof confirmation.

For each affected full record ref and cohort, compare before and candidate
masks. Removed bits delete their exact old cells. Added bits insert the newly
admitted field token. Retained bits with a changed validated token replace that
cell even when the wire mask was omitted or unchanged. Other bits are untouched.
An omitted mask means the existing logical set, not implicit deletion or renewal.
This produces the same explicit logical membership operations and all eight
normalized tables as the unpacked transaction. Same logical cohort IDs keep
unchanged member keys stable; only immutable seal versions/roots/counts advance.

Changed tokens visit only their incident bounded cohorts and keyed cells.
Receipt-only updates produce zero member edits. Count body/facet/schema/token,
reference, catalogue, callback, expansion and map work separately and in the
combined total. No hidden member iterator, roster restore or all-alias scan is
permitted for a sparse change.

Any malformed definition/mask, old-value mismatch, domain error, capacity error,
wrong root, cancellation or retired reference discards the whole candidate,
including declared aliases, final profile indexes, tokens and derived cells.
Prior roots stay immutable. No failed candidate or provisional mask can support
a proof, a selected row or a completeness/removal claim.

## Required exact vectors and resource qualification

Joint G1 inputs must cover, in full and active views:

- Baseline packed versus explicit eight-table equality, exact API 4 join and
  independent table/cohort/native/source roots, including empty coverage.
- Same alias removed from A and inserted for B in one transaction, old/new birth
  confusion, foreign epoch, colliding declarations and retained-identity rebirth
  rejection; receipt-index reorder/removal cannot rebind old support.
- Mask absence, zero deletion, null/type/boolean/high-bit rejection, duplicate
  resolved groups and conflicting per-field support; wrong old masks fail even
  if candidate masks/tokens would otherwise be self-consistent.
- One changed field with an unchanged or omitted mask versus explicit cell
  replacement, membership add/delete/subset, receipt-only zero-cell edits,
  exact original support and failed/expired/context-only evidence.
- Failure after structural catalogue staging and after semantic patch creation;
  atomic rollback, revocation and cleanup under rejection/repeated cancellation.
- At 100/500/2000 rows, exact sparse key/path/classification/iterator counts;
  5000 remains a separately labeled capacity case.

All plan/iterator/catalogue/ref/control containers, raw/parsed input, scratch,
callback materialization, masks, expanded nodes, current/predecessor/candidate,
journals and I/O pins count under the existing shared 32 MiB encoded and 64 MiB
heap caps as applicable. Physical sharing is counted once within each cap;
copies are additional allocations. Intake credit is prepaid and transfers
without a gap; closing a plan cannot uncharge storage retained elsewhere.
Saved failures cannot pin retired buffers or authority. Public refs must fail
after retirement, including during partial iteration.

The reported 32,934,920-byte 500-row draft peak and separate 29,567,161-byte
key-reuse screen are unpaired source diagnostics, not full/dense aggregate
memory or CPU acceptance. A1 role agreement, prepaid acquisition, exact compact
schema/codec agreement, paired installed/native transport and all existing
performance/resource gates remain separate and open. No cap, service, selected
artifact, provider or consumer change follows from this review.
