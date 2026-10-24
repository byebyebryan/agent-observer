# Actual source completion: immutable join recheck

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **bounded synthetic source/relay/Reader join PASS**. This is not
producer readiness or a route, physical resource, native-provider or installed
artifact acceptance.

Mesh `be6470edab0ae7d67063fd08b61a8019c2093e35` removes the unsupported
`completion_header["nativeBindingDigest"]` lookup. The exact typed terminal tag
continues to bind the requested native target; descriptor, chain, cursor,
epoch, metadata and completion checks remain. Its
`171f21c60697d2671d1db602f991435379819306` report is independently hash checked:
`completion-g1-review.json`, SHA256
`17b87a121c2c590a2b4c60e4b8f65f4bfdd54ba3b2a92a1a0a3216cc90dd4509`.
All 187 captured Mesh inputs and eight protected inputs match its runtime export.
No Mesh file is edited here.

The [original failed join](delta-sync-completion-join.md) remains valid for
Observer `2f697d4` / Mesh `b57c2176`. Its unchanged
[six-case harness](../../evidence/2026-10-16-delta-sync-source/verify_completion_relay_join.py)
now passes on both Python 3.14.8 and 3.11.17 against the corrected Mesh export,
separately paired with immutable Observer
`2f697d468eb3b0cb895276fd07cb746acbd23d37` and current
`fc7579bd2e3e6b020b4e66958e8e425e60889b93`. These are four independent runs,
six cases each, with cyclic GC disabled and final five relay counters zero.
The older Mesh report's missing-source-method statement is bound to its older
Observer `3a751916` input; Observer implemented the agreed `CompletedChanges`
method in `2f697d4`. No second implementation or new interface agreement is needed.

## Actual native source through two disposable IPC paths

Each case constructs a test-owned synthetic ServiceState and protected native
Unix endpoint. The actual `CachedAgentSyncSource.open_session` implementation
receives original transactions and the native terminal control. The generic
relay forwards them over a second Unix endpoint after whole-batch preflight.
The receiving oracle checks delivery sequence, exact original native fragments
and one original terminal control after all zero/one/four material deliveries,
for both full and active views. No fixture CompletedChanges, native JSON
synthesis, tuple fallback or private source access is used.

The separate
[Reader join](../../evidence/2026-10-16-delta-sync-source/verify_completion_relay_reader_join.py)
adds ordinary independent `OwnedSyncCache` admission and original native proofs
to the current `fc7579b` / `be6470e` pair. It verifies all six cases on both
Python versions with cyclic GC disabled. Full fixtures contain three identities;
active fixtures select two. Each case:

1. Forwards an original baseline, independently admits it, and rejects current
   access before confirmation.
2. Acquires a fresh native nonce head through public source/relay operations,
   verifies its exact original fragment, confirms it independently and compares
   the lossless native DTO with the fixture owner.
3. Applies zero, one or four native transactions through the actual completed
   source result. The terminal binds the exact original base/target/tag/cursor.
4. Independently stages every transaction, checks that changed material remains
   unconfirmed, then requests another distinct nonce and confirms the final
   exact native tag and DTO.

The same immutable 15-second acquisition capsule covers baseline, catch-up and
both fresh heads; no retry resets it. Each head retains its two-second bound.
The sole private receiving operation is the already-disclosed test nonce setup
`cache._proof_request`; the relay receives no Reader profile or admission hook.
Actual native head/proof bytes come from the public source/relay operations.
Closing the test-owned native cache is fixture cleanup. Both Reader's six and
relay's five ledger counters return to zero; output is fully consumed and native
handlers finish. Zero counters are bounded logical cleanup evidence.

```sh
rtk proxy /path/to/python -B docs/evidence/2026-10-16-delta-sync-source/verify_completion_relay_reader_join.py \
  --mesh /absolute/immutable/mesh-be6470e \
  --observer /absolute/immutable/observer-fc7579b \
  --output /absolute/new-reader-report.json
```

Both harnesses refuse to overwrite reports. Exact source/test/schema inventories,
loaded inputs, raw report and log hashes, interpreter commands and qualification
results are in the [receipt](../../evidence/2026-10-16-delta-sync-source/completion-relay-recheck.json).
The original failure evidence retains its exact old tuple and is not reattributed.

## Remaining gates

A later [immutable deadline/intake recheck](delta-sync-relay-deadline-recheck.md)
records the exact `f32218b` correction, independent old/new relay regressions and
the same actual-source/Reader probes on that newer pair. It leaves the following
broader gaps separate and preserves this original `be6470e` evidence.

The [consuming-pin registry defect](delta-sync-source-pin-revocation.md) remains
open. These sequential success cases do not call inspect during a consuming pin,
hold cleanup across session close or prove the proposed public status-query fix.
They do not close any wider cancellation, live pin or physical accounting gate.
The earlier source watch-close and Mesh owner/material-retirement fixes remain
separate, narrowly closed findings.

The native fixture, sockets, queues, decoder/oracle and Reader versus relay
ledgers are separate test allocations; this does not establish aggregate 32/64
MiB limits, physical reclamation/RSS or an installed transport. The trusted test
controller composes request/descriptor/encoding bindings directly; network hello
and operation-dispatch grammar remain unqualified. Source encoding is expanded;
this does not qualify compact source dispatch, dense nine-field data, packed
2,000-row recovery, slow peers, expired head write attempts, total CPU, populated
native service/fixed SSH or the immutable installed pair. All original bounds,
failed performance gates and selected a7/a23/normal workflows remain unchanged.
