# Completion-transfer r1 owning review

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **method/result/lifetime shape aligns; explicit native-limit wording
clarification sent to Mesh before exact joint freeze**. This responds to the
existing completion-transfer review reported in Mesh `e-f9959a4a`. It creates no
new general approval gate and does not reopen A1/R4/R2.

## Exact candidate and source context

Reviewed on Starship: Mesh evidence commit
`0b942c25fd3c74e16f11398170f28efac2f13138`,
`docs/delta-sync-completion-transfer-r1.md`, 6,105 bytes, SHA256
`740dd8bc5b3c435612194c6451b5fb545d54bd0e3b8115f6934ff29a5686eff0`.
The document is in that evidence commit, **not** runtime commit
`ea25fcb07bac14162453b0f8626aa416db10edf3`. Its retrieval is therefore:

```text
rtk proxy git -C /home/bryan/code/mesh-plus show 0b942c25fd3c74e16f11398170f28efac2f13138:docs/delta-sync-completion-transfer-r1.md
```

Observer's [original concrete proposal](delta-sync-changes-completion-proposal.md)
is commit `8f54fd0c3d743ac410776a70c6b01ef2f9620a90`, proposal SHA256
`32ff86a3a1e4f65d3b070dc57206da6b8bdc2c79c4ca5b40f8cdc38a471f93f1`.
Its same checkpoint independently fixes existing source completion correlation;
that source fix does not implement or freeze the additive return API.

## Agreed implementation direction

The proposed optional method and closeable result match the owning proposal.
Observer accepts the public result name `CompletedChanges` instead of its earlier
proposed `OwnedChangeBatch`; no duplicate alias or compatibility type is needed.

```text
SourceSession.changes_with_completion(
    base, *, target, max_transactions=4, max_bytes=8388608
) -> awaitable[CompletedChanges[RefT] | SyncControl[RefT]]

CompletedChanges.transactions: tuple[RefT, ...]
CompletedChanges.completion: SyncControl[RefT]
CompletedChanges.close() -> None
```

The constructors stay source-private. A successful result owns the exact ordered
transaction refs and original complete-control ref/ticket, with independently
prepaid batch/container and control/header metadata. It opens no second source
session, copies/reseals no buffer and grants no material/proof authority. Existing
`changes()` keeps its signature and transaction-only tuple/control result.

The existing source's strict correlation fix binds complete status, request
base/target, the control's own target tag, the nonempty chain's final cursor and
every intermediate cursor epoch. A zero chain is valid only for exact equal
base/target and the native control's original self-consistent clock/cursor;
the independent Reader still binds its complete target material/incarnation.
Explicit failure returns its owned control without a successful prefix or batch.
The generic relay independently checks all supplied raw headers and terminal
metadata before output, drains transactions before the original completion,
and retains all relevant pin/copy/metadata credit through actual retirement.

The result closes as one scoped operation, including cancellation after internal
completion but before delivery. Public properties reject after retirement.
Consumed data does not retire still-live metadata. Session/source close must
revoke owned refs before awaited cleanup while active storage retains credit;
siblings, shared input owner and native owner/provider are untouched. Bounded
tracking, retained handles/failures, no-GC cleanup, pre-copy refusal and exact
zero/one/four transaction cases remain required implementation tests.

The relay explicitly requires the new method; it cannot fall back to legacy
changes, infer completion from EOF/watch or synthesize native JSON. The network
operation-request grammar remains separately owned by Mesh and unallocated by
these Python names. Producer coordination of this additive source seam occurs
inside the already authorized G1; no new general coordinator approval is needed.

## One concrete bound clarification

R1 states a separate native completion upper bound of 65,536 bytes. That is the
generic **outer Mesh control** bound. The existing Agent native control bound is
16,384 bytes in `sync_native.MAX_CONTROL_BYTES`, retained in native validation
and both material-header/head-only acquisition paths. All existing native family
limits continue to apply; the outer limit cannot replace a stricter codec limit.

Requested exact wording:

> Native completion remains within its codec's existing native control cap
> (Agent: 16,384 bytes). The complete nested Mesh control, including envelope and
> LF, also remains at most 65,536 bytes. Both limits and all shared charges apply.

This does not report a runtime cap bypass: the current Agent facade already
rejects oversized native controls. It makes the two required limits explicit in
the candidate packet. There is no request to raise a cap, change a role, add a
quota exemption or reopen R4. Transaction material remains at most four refs and
8 MiB, with the separate native control fully charged in the same 64/32 MiB
budgets and original total wire/CPU/deadline gates.

The [pure bound probe](../../evidence/2026-10-16-delta-sync-source/probe_completion_control_bounds.py)
checks both full/active and header/head facade paths: a syntactically valid
16,384-byte padded native control succeeds; 16,385 and 65,536 bytes reject.
Its twelve cases are lexical native-bound evidence, not a real relay, native
provider, material admission or aggregate resource measurement.

## Review boundary and next work

The [review manifest](../../evidence/2026-10-16-delta-sync-source/completion-transfer-r1-review.json)
pins exact inputs, probe outputs and checks. No new method, return class,
generic interface, schema/encoding ID, source selection or installed artifact is
implemented by this review. Existing strict source fixes and closed agreements
retain their own exact provenance. The initial attempt to read the candidate
from the runtime commit failed because it belongs to the evidence commit; that
location error is not attributed as a source or test failure.

After this existing counterpart coordination is settled, the owning source will
implement the accepted return shape and qualify its metadata/control/container
lifetimes. Generic relay/controller consumption, exact compact encoding/native
export, full shared physical resources/RSS, dense/cold/recovery CPU/bytes,
populated IPC/fixed SSH and independent immutable installed pair remain separate
required gates. The upstream scaffold's reported 305 core and four Reader cases
are not rerun or promoted by this review.
