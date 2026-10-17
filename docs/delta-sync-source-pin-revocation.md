# Source registry and consuming-pin revocation

Status: **current-source gap reproduced; exact owner-bound public query agreed;
no consuming-pin fix or acceptance claimed**.

Mesh's `be6470edab0ae7d67063fd08b61a8019c2093e35` diagnostic also reproduces
against the current Observer runtime `2f697d468eb3b0cb895276fd07cb746acbd23d37`,
using immutable Mesh `b57c2176d60a8593fa2f85d7322655384a3227b6`.
The finding is independent of the
[completion control-header mismatch](delta-sync-completion-join.md). The additive
source completion method already exists; this does not reopen its agreement.

## Reproduced source defect

`OwnedSourceSession._prune_refs()` currently removes a ref when public `nbytes`
raises `sync_input_retired`. The generic owner uses that same rejection while a
ref is actively consuming and its physical raw pin is still live. Public
`inspect()` calls the pruning method, as does automatic receive/seal preparation.
Removing the source's revoker at that point means its later scoped close can
miss that consuming ref.

On both Python 3.14.8 and 3.11.17, the unchanged upstream diagnostic produces
byte-identical bounded results:

| Case | Source registration during pin | Source close / pin exit |
| --- | --- | --- |
| No inspection | Retained | Rejects `sync_input_retired` |
| Public inspection during pin | Incorrectly changes 1 to 0 | Pin exit incorrectly succeeds |

The original 1,753 encoded bytes remain charged during either pin. All five
final ledger counters return to zero. This is a missed source-scope logical
revocation, not an observed uncharged allocation, cap overrun, material authority
or actual late relay output. Closing the source session still preserves the
shared input owner before the generic consuming operation finishes. A generic
admission may separately invalidate its own cache on revoked pin exit.

## Why existing nbytes cannot be a retirement test

The present public ref surface does not distinguish an unavailable consuming
ref from a terminal consumed/closed ref. Both reject `nbytes` with the same code.
Inspection cannot close every rejected ref: that would abort healthy pins.
Keeping every unavailable ref forever cannot satisfy the bounded live-only
registry requirement when callers retain many terminal handles. Private generic
record inspection or a source wrapper replacing the exact ref type is excluded.

The already accepted R4 lifetime rule says that `nbytes` rejection alone does
not prove a consuming pin's physical retirement. Source tracking needs explicit
public evidence of logical revocation, independent of physical pin credit.

## Agreed minimal public shape

Observer accepts Mesh `d8d7a6233f625ba352c3451396770a61b28635c7`,
proposal SHA256 `298efa4af40a23651702ac85862d817a045e9b7e781daf363bc43e1300aaf018`,
through this [exact owning agreement](delta-sync-input-retirement-agreement.md):

```text
InputOwner.ref_is_retired(ref: OwnedInputRef) -> bool
RelayInputOwner.ref_is_retired(ref: RelayInputRef) -> bool
```

For an exact same-owner ref the status is monotonic. It is false for an available unconsumed ref
and for an actively consuming, unrevoked ref. It becomes true after logical
`close`, completed consumption, or owner-epoch retirement. A logically revoked
pin can still hold fully charged physical storage; true never means that its
bytes may be refunded. This read-only query grants no bytes, material, scope,
ledger or proof capability. Existing `nbytes`, close, consume, exact ref types,
caps and sibling semantics remain unchanged. No child-scope API is proposed.

The source will prune only an exact true result and retain false pins for
scoped close. The new unselected adapter must reject an absent/noncallable query
before source allocation and reject non-bool results during intake, preserving
shared owners and siblings. It never falls back to `nbytes`. Same-owner closed
refs remain queryable; foreign/role/replacement/raw handles reject without
closing anything. This owner-bound choice supersedes the earlier per-ref
property preference retained in `90b4292`; it is not another wire/root/lease,
A1 or general rollout permission change. Dependent runtime edits follow Mesh's
committed supported method, which is not claimed by this agreement.

## Regression and next qualification

The [unchanged upstream diagnostic](evidence/2026-10-16-delta-sync-source/probe_source_inflight_prune.py.txt)
and [owning regression overlay](evidence/2026-10-16-delta-sync-source/test_source_ref_revocation.py)
use disposable native Unix fixtures with synthetic frames. The only private
generic helper is the disclosed test-only `input_bytes` pin. Source state is
not patched. The five overlay cases require inspection and automatic receive
pruning to retain revokers, inspection to leave a healthy pin usable, and 70
caller-retained terminal heads to leave no live history. Against current source,
three cases fail and the no-inspection/terminal-history controls pass on both
Python versions, with cyclic GC disabled, held errors and final counters zero.
The [receipt](evidence/2026-10-16-delta-sync-source/source-pin-revocation.json)
pins exact before inputs, harnesses and outputs. These expected failures are
not an implementation pass.

After the agreed public query is available, implement the source fix through
that supported seam, rerun these identical regressions, and qualify cache/relay
refs, receive, watch, batch and session cancellation with consuming pins held.
The current source revocation prerequisite remains open. No native provider,
normal service, sibling source, artifact, installed role, cap/deadline, source
encoding, A1/R4/R2 acceptance or broader producer gate changes here.
