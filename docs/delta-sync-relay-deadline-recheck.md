# Independent relay deadline and intake recheck

Mesh runtime `f32218bffab8860d374964721e35384f66a86269` passes this bounded
Observer review of the deadline/intake source prerequisite. It is not full
relay, producer, resource, native-provider or installed-pair acceptance.

The owning evidence at `028d90b63fed69bb1e095d8da44e2cce73a7e9a5` is pinned by
`relay-deadline-review.json`, SHA256
`bf0e529d9ad6b58cb22ebef3a7703254c2485390a04b45cf98638b3f941541e2`.
Its report `docs/delta-sync-relay-deadline-g1.md` is SHA256
`0be8dcb7b13e7a3c1a9cf12a6ff538402b2f51268ad8c056f0f66eb8a0c21df2`.
All 13 reported artifacts, 187 Mesh inputs and eight protected inputs are
independently checked against the exact immutable Git objects/export. Mesh's
earlier documentation-only failed link check is preserved; `cdb8cd0` repairs that
prose without changing runtime/tests/scripts. No sibling file is edited here.

## Exact correction and before/after

The public head operation now captures one absolute bound at entry: the earlier
of its original acquisition deadline and entry plus two seconds. That same bound
covers challenge preparation, native source await, scanner/header copying,
output-lock waits and each write/drain. Returning from the source cannot start
another two-second window. A synchronous scanner overrun rejects before later
copy/output; exactly at the bound rejects as well.

Before any write attempt, expiry retires the acquisition and preserves a separate
blocked watch. After an attempted write, failure starts affected-channel cleanup
and keeps physical output/input pins charged through cleanup and repeated cancel.
The code does not promise that previously queued bytes disappear at the deadline;
it prevents starting another fragment after its bound fails. Reader proof RTT,
incarnation, tag/root and original receipt checks remain independent.

Failed changes intake now starts affected-channel/session cleanup even if the
source allocated internal results and then raised before returning a batch.
The operation worker unwinds before awaiting that initiated cleanup, avoiding a
wait on itself. Malformed returned shapes are not treated as transferred batch
ownership, and shared owners/sibling channels are preserved. No public signature,
wire shape, scope authority, deadline or capacity is changed.

This review exports exact old Mesh `171f21c` and overlays only the final
`tests/test_sync_relay.py` from `f32218b`. Both Python 3.14.8 and 3.11.17 execute
33 methods with **seven expected failed checks**, zero errors/skips. That is a
successful defect reproduction, not a passing old runtime. The identical final
test file against `f32218b` passes 33/33 on both versions, cyclic GC disabled,
saved failures and final five counters zero. Covered expiry/lock cases show no
write attempt after pre-write expiry; partial-write and independent-watch cases
retain their specific fixture bounds.

## Actual completed-source compatibility

The unchanged [completion forwarding harness](evidence/2026-10-16-delta-sync-source/verify_completion_relay_join.py)
and [independent Reader harness](evidence/2026-10-16-delta-sync-source/verify_completion_relay_reader_join.py)
are rerun against immutable Observer
`fc7579bd2e3e6b020b4e66958e8e425e60889b93` and Mesh `f32218b`.
Each harness passes six full/active zero/one/four-transaction cases on both Python
versions, with actual `CompletedChanges`, exact original fragments/terminal and
two disposable Unix IPC paths. Reader cases independently admit/stage, obtain two
distinct fresh native nonce proofs under one acquisition capsule, and restore the
exact final native DTO. Full fixtures contain three identities and active selects
two. Reader's six and relay's five final ledger counters return to zero.

The actual source's 39 focused completion/owned-source cases also pass on both
versions with GC disabled. Observer's canonical check passes 924 tests/zero skips
against this exact Mesh runtime. These results supersede the older source-missing
statement for its old `3a751916` input; the implementation exists since `2f697d4`.
No fixture shim, native completion synthesis or legacy fallback is used.

Exact commands, reports, loaded inputs, log hashes and immutable inventories are
in the [receipt](evidence/2026-10-16-delta-sync-source/relay-deadline-recheck.json).
The receiver nonce setup and native-cache fixture cleanup remain the explicitly
disclosed private test scaffolding; production source/relay uses supported APIs.

## Still open

The [consuming-pin registry defect](delta-sync-source-pin-revocation.md) is not
fixed by these deadline checks. Its exact public retirement query is
[agreed](delta-sync-input-retirement-agreement.md), but its committed Mesh
implementation and dependent source adoption/held-pin qualification remain open.
These sequential actual-source successes do not establish actual-source overlapped
watch/pin cancellation or general physical lifetime.

The expired-deadline edge is qualified by controlled generic source/scanner/output
fixtures, while actual-source IPC cases here are timely successes. This review
does not establish populated provider/native service behavior, controller grammar,
compact source dispatch, aggregate 32/64 MiB with full+active/current+predecessor/
stage/slow-peer pins, RSS, dense nine-field CPU/cold/recovery bytes, packed
2,000-row delivery, fixed SSH or immutable installed artifacts. Fixture/oracle,
native, relay and Reader allocations are separate test ownership domains. Original
failed performance gates and selected a7/a23/normal workflows remain unchanged.
