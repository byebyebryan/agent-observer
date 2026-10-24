# Additive owned native change completion

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **concrete owning proposal for Mesh agreement before shared ABI edits**.
This addresses Mesh `e-d62dc201`. Existing R4 and R2 agreements stay closed.
No new runtime method, return type, wire grammar, contract version, source
selection or artifact is implemented by this proposal. The companion source
correlation fix below preserves valid existing API shapes and is independent
of accepting the new return method. Mesh may continue its relay ownership and
output implementation against the accepted R4 interfaces.

## Confirmed seam and proposed surface

At Observer `d6346406a8125e75d79014fe84f37d483461f923`, the opt-in source's
`changes()` accumulates transaction refs, receives the native terminal control,
closes that control and returns only the transaction tuple. Thus a relay cannot
splice the exact completion bytes through its public source API. Reconstructing
native JSON, reaching into the source, treating EOF as completion or using a
watch heartbeat would conflict with the accepted relay role.

Add exactly this optional Python method and source-owned return type:

```text
SourceSession.changes_with_completion(
    base, *, target, max_transactions=4, max_bytes=8388608
) -> awaitable[OwnedChangeBatch[RefT] | SyncControl[RefT]]

OwnedChangeBatch.transactions: tuple[RefT, ...]
OwnedChangeBatch.completion: SyncControl[RefT]
OwnedChangeBatch.close() -> None
```

The source constructs the batch; no caller mint API is added. `transactions` is
the exact ordered tuple of zero through four single-consume byte-only refs.
`completion` is the original owned native control ticket, with its exact `.data`
ref and existing `.status`, `.reason`, `.tag`, `.cursor` and `.close()` surface.
It is always status `complete` on a successful batch. The original raw control
remains sealed under its configured input owner; neither the batch nor metadata
is a material admission token, proof or currentness grant.

The existing ordinary raw-byte API and `SourceSession.changes()` signatures,
return types and transaction-only success shape remain unchanged. The new method
uses the same existing native `changes` request and native frame schemas; it adds
no native operation, request selector, config field or source-name convention.
An R4 relay requiring exact native completion checks that this opt-in method is
callable during supported source setup and fails explicitly if unavailable. It
does not silently call legacy changes or synthesize a control.

## Exact completion correlation

No batch is returned until the entire bounded contiguous chain and its terminal
control have been read and checked. Successful completion requires:

1. Native status is exactly `complete`; heartbeat is not change completion.
2. Control `baseTag` and `targetTag` exactly equal the request's arrays.
3. The final contiguous transaction tag equals requested target; zero transactions
   are valid only when base equals target.
4. Control `tag` exactly equals requested target, and control cursor generation
   and root equal that target. Native structural validation binds cursor epoch to
   the control's original owner clock.
5. For a nonempty chain, every transaction base/result cursor has exact epoch and
   cursor continuity; the control cursor exactly equals the last result cursor.
   No same-tag control from another incarnation can terminate that chain.

At the pinned `d634640` input, the source checks base/target fields and final tag,
but its shared socket check does not explicitly require the terminal control's
own tag/cursor to name that target or retain cursor continuity for change
transactions. The companion correctness change tightens that common source
boundary for existing plain/owned changes. It fixes malformed completion
acceptance without changing any valid native request, reply or Python return.
For an empty chain, the source validates the original complete control's own
epoch/clock/cursor consistency; it invents no expected epoch from a digest.
The relay and independent Reader still bind source/request/incarnation and the
target's complete native/material/proof context through their own public checks.

Native `baseline_required`, gap, warming or error returns its existing owned
`SyncControl` subtype directly, with no successful batch or exposed transaction
prefix. The source closes any accumulated refs. Malformed completion, missing
completion, EOF, quota failure, timeout or cancellation rejects and retires every
ref/header/batch allocation from that operation. A syntactically successful but
uncorrelated control cannot be forwarded as success.

## Transfer and lifetime

The batch is one operation result. Its tuple, wrapper and lifecycle tracking are
prepaid separately before allocation and remain charged after request/parser
scratch retires. Existing input refs and the terminal ticket retain their own
physical buffer/header credit. Those bytes are neither copied nor re-sealed to
create the batch. Live batch tracking is bounded under the existing source
ownership policy and shared ledger; no unbounded returned-result history or new
capacity allowance is introduced.

`close()` is idempotent. It closes all transaction refs and the completion ticket,
drops the tuple and ticket references, retires only that batch's tracking/metadata
credit and makes batch property reads reject `sync_change_batch_closed`. A
consumer can independently consume each ref once using its configured owner.
The completion's metadata lease survives consumption of its `.data` ref exactly
as current owned controls do, until ticket or batch close. Borrowing child
references does not mint another ownership scope or duplicate physical credit.
The consumer closes the batch after transferring/draining its owned outputs.

Cancellation or source retirement after the internal operation finished but
before delivery to its awaiting caller must close the entire unreturned batch,
including terminal raw ref and header. The existing scoped `_run` retirement
behavior must cover the new result as one closeable object. Source close revokes
its own sealed refs immediately before the first awaited cleanup; live receive,
parser, output or consuming pins keep their credit through actual unwind.
Late return cannot escape that revocation. Closing a batch/session never closes
the shared input owner, sibling sessions, native owner service or provider.

## Bounds and relay use

`max_transactions` and `max_bytes` keep their existing native meanings: they bound
the transaction material, not the separate terminal control. The latter remains
inside the unchanged 16,384-byte native control cap. Its complete physical bytes,
metadata, parser/copy/output staging, waiting and drain work count in the same
existing aggregate 64 MiB heap / overlapping 32 MiB encoded budgets and original
recovery CPU, byte and acquisition-deadline gates. This adds no quota exemption.

Relay use is conceptually: await the successful batch, independently check its
public structural transaction/header chain and exact terminal correlation,
consume/splice each exact native ref under the accepted output ownership rules,
drain transaction outputs, then drain the original completion control. The
success reply cannot precede the transaction drains. Any failure revokes and
cleans that acquisition without asserting successful completion or reusing old
authority. Fresh head proof remains separate; completion supplies no lease
renewal or material admission.

This is an additive **Python source completion-transfer** proposal. R4's closed
Python operations do not allocate an exact network operation-request grammar.
That Mesh-owned grammar and independent client compatibility must be specified
and reviewed separately before dependent transport/client integration. No field,
message spelling, encoding ID, descriptor or request digest is inferred here.

## Required owning checks after agreement

- Full/active exact native completion bytes transferred without synthesis;
  zero-, one- and four-transaction success, with material quotas unchanged.
- Legacy `changes()` still returns only transaction refs and retires completion.
- Strict status/base/target/tag/cursor/epoch checks; missing completion, malformed
  terminal, failure after a valid prefix and explicit recovery close the prefix.
- Batch/header/tuple pre-copy refusal; aggregate retained completion bytes and
  metadata remain charged, including after separate data consumption.
- Immediate own-scope close, paused I/O/cleanup, completed-await cancellation,
  retained consumed handles, late returns, sibling/shared-owner isolation and
  final zero live counters with cyclic GC disabled.
- Independent Mesh relay consumption through this public surface, with no
  private source inspection or native JSON reconstruction.

These are source/contract prerequisites. They do not establish aggregate physical
capacity/RSS, compact normalization/schema freeze, dense/cold/recovery performance,
populated IPC/fixed SSH, an installed immutable pair or producer readiness.

## Existing-source diagnostic and separate correction

The [controlled-socket diagnostic](../../evidence/2026-10-16-delta-sync-source/reproduce_completion_transfer.py)
reproduces four observations against immutable `d634640`, with cyclic GC disabled:
the exact native completion ref closes before legacy success is returned; a
control naming another target, one with a foreign owner cursor, and a heartbeat
can also be accepted as transaction-only success. It uses private **Observer
owning test instrumentation**, never a proposed Mesh access path. All data is
synthetic and the protected local endpoint is disposable; no provider or normal
service is invoked. Its old-source mode intentionally asserts these gaps and
must not be described as a fixed-source test or native proof.

The separate regression covers plain and owned callers, each wrong terminal
case plus a changed transaction cursor epoch. It keeps successful baseline and
sibling refs live, holds errors with cyclic GC disabled, and checks prefixes
retire without touching sibling authority or credit. A valid empty exact chain
retains the existing empty-tuple success shape. Legacy completion disposal is
preserved until the additive API has joint agreement. The
[review evidence](../../evidence/2026-10-16-delta-sync-source/changes-completion-review.json)
pins before/after source exports, results and remaining implementation gates.
