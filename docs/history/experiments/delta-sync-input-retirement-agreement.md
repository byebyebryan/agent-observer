# Owning agreement: explicit input retirement query

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Observer accepts the exact Mesh proposal at
`d8d7a6233f625ba352c3451396770a61b28635c7`,
`docs/delta-sync-ref-retirement-proposal.md`, 6,067 bytes, SHA256
`298efa4af40a23651702ac85862d817a045e9b7e781daf363bc43e1300aaf018`.
This selects one public G1 seam for the
[reproduced consuming-pin registry defect](delta-sync-source-pin-revocation.md).
It supersedes the earlier per-ref property preference; no competing property,
new child-scope API, `nbytes` fallback or general approval is required.

```text
InputOwner.ref_is_retired(ref: OwnedInputRef) -> bool
RelayInputOwner.ref_is_retired(ref: RelayInputRef) -> bool
```

The minting owner identity and exact ref role/type bind the query. Available and
actively consuming **unrevoked** refs return exact `False`; the source retains
their scoped revokers. Logical close/revocation, completed consumption or minting
owner retirement returns exact `True`, even when a revoked pin still holds fully
charged physical bytes. Same-owner retired refs remain queryable after owner
close. Foreign-owner/replacement/sibling/role/raw/malformed handles reject
`ProtocolError("sync_input_owner")` without closing or refunding anything.

The query performs bounded O(1) storage-lifetime checks, allocating no history
or reservation and invoking no parser, codec, profile or domain callback. It
grants no raw bytes, admission, proof, lease, publication or free-capacity claim.
It never reclaims material or revives authority. The absence of a same-owner
storage record is terminal; there is no unbounded bank of consumed handles.
Existing `nbytes` and all ordinary reserve/seal/consume/close rules remain strict.
No wire descriptor, native root, support, receipt, encoding, deadline or cap is
changed by this addition.

## Native source adoption through the supported method

The source will require callable `inputs.ref_is_retired` at `open_session`,
before its source-state reservation or I/O. Unsupported/noncallable owners reject
`ContractError("sync_source_input_owner")`; older source-owner evidence retains
its original exact tuple. Ordinary byte APIs and selected normal roles remain
unchanged. This is an explicit opt-in pairing requirement, not capability guessing.

The session captures that public callback. Pruning checks exact `bool`, removes
only `True`, and preserves `False` consuming refs until its own scoped close can
revoke them. Non-bool/foreign errors fail affected intake, preserve shared owner
and siblings, and cannot refund physical storage or a separate header/batch lease.
Terminal cleanup drops the captured callback after its own I/O and children
retire. There is no read of generic private buffers/records or a substitute ref.

This choice fits the current source responsibilities: one bounded live registry,
immediate own-scope revocation before awaited cleanup, preserved original raw
input/header/container credit, and explicit foreign/sibling isolation. It avoids
using temporary `nbytes` unavailability as evidence that a consuming ref is safe
to forget. The proposal's exact wrong-owner error also permits strict setup and
failure handling without a new semantic or publication capability.

## Acceptance boundary and following checks

This is exact contract agreement only. The [review receipt](../../evidence/2026-10-16-delta-sync-source/input-retirement-agreement.json)
pins the proposal and current owning source. Neither this commit nor the
[sequential actual completion join](delta-sync-completion-join-recheck.md)
implements or accepts the fix. Mesh must first provide a committed public query;
Observer can then make dependent source changes under the existing G1 task.

Required evidence remains the proposal's state/error matrix; available,
consuming, revoked, consumed, owner-closed and replacement refs; unchanged
publication/callback/counter state; source inspection and automatic receive with
held pins; 70 retained terminal handles; watch/batch/source close and repeated
cancellation; independent aliases and shared-ledger siblings; logical revocation
before cleanup with physical credit held until unwind; and deterministic GC-off
retirement with errors retained. The existing five-case failing overlay must
be rerun unchanged before and after the actual source fix. Joined actual-source
relay/Reader and codec gates must use the final committed pair.

All 32/64 MiB budgets, two-/15-second deadlines, dense/cold/recovery CPU and byte
gates, native/installed paired acceptance and rollout boundaries remain. No
producer readiness, runtime implementation, schema/version allocation or normal
service/provider/route change is asserted by agreeing this seam.
