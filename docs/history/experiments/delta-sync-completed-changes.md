# Owned native completion transfer

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **implemented opt-in source prerequisite, not relay/pipeline acceptance**.
This completes the agreed additive source seam in the
[owning review](delta-sync-completion-transfer-r1-review.md). Mesh accepted that
review and its sole native-control clarification at commit
`332e33ff27ee1dfa6c53faf970429c34fe08d46d`,
`docs/delta-sync-completion-transfer-r2.md`, SHA256
`c1aa8a8ad8e449b5b6d68fadc839e57377237d26ba9bb5a035f0571945484706`.
That supplement and unchanged R1 SHA256
`740dd8bc5b3c435612194c6451b5fb545d54bd0e3b8115f6934ff29a5686eff0`
are the common completion-transfer agreement. A1/R4 and compact R2 remain closed.

## Public source surface

`CachedAgentSyncSource.open_session(inputs)` remains synchronous. Its owned
session adds exactly:

```text
await session.changes_with_completion(
    base, *, target, max_transactions=4, max_bytes=8388608
) -> CompletedChanges | OwnedSyncControl

CompletedChanges.transactions: tuple[opaque single-consume ref, ...]
CompletedChanges.completion: original OwnedSyncControl
CompletedChanges.close() -> None
```

The source-private constructor returns a batch only after the whole original
chain and native terminal control pass existing status/base/target/tag/cursor/
epoch checks. Zero transactions require equal base/target. Explicit recovery
returns its original owned control after retiring the prefix. Missing, malformed
or mismatched completion exposes no successful prefix. Neither the batch nor
the control grants material, lease or proof authority.

The returned refs and completion ticket are the original sealed inputs. No
buffer is copied, re-sealed or synthesized for this result. `changes()` retains
its existing transaction-only tuple/control result and disposes its completion.
The plain-byte API, native request/frame schemas, encoding configuration and
normal routes are unchanged. Core/source imports no Mesh code.

## Ownership, bounds and retirement

Before constructing the returned tuple/wrapper, the source reserves a separate
4 KiB metadata lease in the caller's shared ledger; the input owner's own
reservation bookkeeping is additionally charged. Request, live framing/parser,
raw refs and completion headers keep their independent credit. Consuming all
data refs cannot release batch or completion-header metadata. Close drops the
batch's aliases, closes its remaining children and retires its own lease. It is
idempotent; both properties reject `sync_change_batch_closed` after retirement.
Borrowed children are not another ownership scope. The consumer closes the batch
after transferring/draining its output, whose own pins/copies stay independently
charged until physical retirement.

The live batch registry is bounded by the existing 64-item source policy and
the input owner's stricter aggregate slot/credit limits. Closed retained handles
do not accumulate registry history. Closing a batch preserves prior results and
siblings. Session/source retirement revokes its batches before awaited cleanup;
it never closes a shared input owner, sibling, native service or provider.

Cancellation after internal completion but before delivery closes the whole
unreturned result. Cancellation during stream cleanup revokes first, then waits
through repeated cancellation while live receive/request storage stays charged.
Saved closed-batch errors retain no strong source/session reference. Neither
close nor completion renews original receipts or acquisition/proof deadlines.

Material remains at most four transactions totaling 8 MiB. The separate original
Agent native control remains at most 16,384 bytes; the complete nested Mesh
control including envelope/LF must independently fit 65,536 bytes. All bytes,
containers, headers, parser/receive/copy/output/pin work count in the unchanged
shared 64 MiB heap / overlapping 32 MiB encoded limits and total CPU/wire gates.

## Source qualification and remaining work

The [source receipt](../../evidence/2026-10-16-delta-sync-source/completed-changes.json)
pins the exact implementation, immutable Mesh inputs and dual-version logs.
Fifteen new GC-disabled tests retain handles/errors and exercise full/active
zero/one/four exact original refs, actual synthetic ServiceState chains admitted
by an independent Mesh cache followed by fresh proof, separate metadata lifetime,
native-control/material limits, pre-construction reservation refusal, bounded
history, recovery/correlation, completed-await cancellation, cleanup held open,
immediate session retirement, sibling isolation and physical weak retirement.
The exact 8 MiB material case deliberately contains opaque invalid domain values;
it proves structural intake/quota behavior only. Fixture/server storage is
caller-owned outside the receiving ledger, so these are not aggregate RSS or
capacity measurements. Existing legacy-source tests remain unchanged.

Mesh relay consumption, whole-chain preflight and material-before-completion
output drains, its separately specified controller grammar, real compact native
serializer/journal/source dispatch, packed 2,000-row recovery, shared resources/
RSS, matched dense/cold/recovery CPU/bytes, populated native IPC/fixed SSH and an
independent immutable installed pair remain required. Earlier performance
failures remain failed. No identifiers, schema freeze, artifacts, installs,
normal role selections or rollout change at this source checkpoint.
