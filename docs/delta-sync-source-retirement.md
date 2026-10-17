# Scoped source retirement through the public owner query

The source implements the [exact agreed owner-bound query](delta-sync-input-retirement-agreement.md)
against Mesh runtime `6fce5ed0e997d021e7532051fe985c3693962c3e`. Before reserving
session state or starting I/O, `open_session(inputs)` requires callable
`ref_is_retired`, `reserve` and `buffer_heap`. Missing or noncallable capability
rejects `sync_source_input_owner`. Both ordinary cache and separate relay input
owners supply this supported seam; no generic private storage is read by the
source and there is no `nbytes` fallback.

The session captures the query once. Pruning accepts exact `bool`, removes only
`True` and retains available or consuming `False` refs for scoped revocation.
Non-bool results fail the affected inspection/intake with
`sync_source_input_owner`; errors never prove terminal state. Source close still
revokes its own refs before awaiting cleanup, keeps unsealed receive storage
charged until cleanup, and preserves shared owners and sibling sessions. The
captured callback is dropped after its own child/I/O cleanup. Ordinary byte
acquisition and the expanded source default remain unchanged.

`CompletedChanges.close()` explicitly closes and untracks its own transaction
children and completion packet. It does not query unrelated registry entries
during cleanup. This keeps terminal cleanup independent of an unsupported or
malformed query result, and releases the separate batch/header credit only after
the corresponding aliases retire. Successful consume and explicit logical close
remain distinct from physical pin retirement in Mesh; this source change never
refunds a generic pin or grants publication authority.

## Bounded final-pair checks

The [receipt](evidence/2026-10-16-delta-sync-source/source-retirement.json) pins the
source, immutable Mesh runtime, probes and logs. The original `90b4292` evidence
and [hardened overlay](evidence/2026-10-16-delta-sync-source/test_source_ref_revocation.py)
retain their separate provenance. The same hardened five cases on the new Mesh
runtime fail three source cases before this change, with two control passes;
all five pass afterward on Python 3.14.8 and 3.11.17. The overlay's end-of-pin-body
assertion ensures an earlier shared-owner or sibling error cannot satisfy the
expected pin-exit retirement rejection.

Normal source tests include those five cases plus capability preflight,
non-bool query failures and shared-owner/sibling survival, captured callback
retirement, and explicit batch cleanup without unrelated queries. A real public
relay factory mints a separate `RelayInputRef` for the actual source session.
Inspection and automatic receive retain that consuming ref; session close then
revokes it while its raw bytes remain charged, and pin exit rejects. This pin
test uses the disclosed private generic pin helper and a test-owned output sink;
it does not establish late-output, controller, native-provider or aggregate
capacity behavior.

The final-pair replay also runs the Mesh eight-method actual completion
composition probe, alongside the owning expanded/compact component checks.
The unchanged upstream probe has one stale assertion expecting zero registered
refs during a held four-transaction drain, deliberately exercising the old bug.
It fails on both versions because the fixed source correctly retains five
revokers. Those failed logs are preserved. The Observer-owned replay changes
only that assertion to require all four transaction refs plus the completion
ref, records both source hashes and exact replacement text, and leaves every
other assertion unchanged. The Mesh checkout is untouched.

The probe's synthetic ServiceState, two disposable Unix sockets, ordinary
independent Reader, exact native completion, invalid terminal bounds, held real
writer drains, repeated cancellation, failed writes and sibling cleanup retain
the upstream probe's limits. The source fix changes no native field or typed tag.

GC remains disabled throughout the focused replay and saved errors survive
cleanup. Final Reader/relay counters are zero; native owner scratch retires.
Separate fixture/oracle ledgers and final zero counters do not establish shared
32/64 MiB peaks, RSS or CPU savings. Original dense CPU, cold bytes, deliverable
2,000-row recovery, populated native/fixed-SSH, controller and immutable installed
pair gates remain open. No a7/a23 selection, service/provider, sibling, version,
encoding/schema allocation or rollout changes here.
