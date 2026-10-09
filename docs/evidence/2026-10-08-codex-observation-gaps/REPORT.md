# Codex observation gap closure

Date: 2026-10-08. Source gap repairs and the separately installed a6
artifact/native gate are accepted; managed operational selection is pending. The
[execution plan](../../codex-observation-gap-closure-plan.md) keeps those gates
separate from consumers, actions, Claude and provider policy. API 2, read wire 4
and service protocol 2 are unchanged.

## Atomic publication

One accepted history sample previously published twice while refreshing history
and runtime receipts. Core revision and real-socket reader regressions reproduce
the extra revision and healthy-reader gap on the prior implementation. Acceptance
now updates both receipts before one publication. Separate leases, rejection
ordering, expiry/last-known clocks and genuine coalescing gap/resync are preserved.
The full source gate passes 383 tests (one skip). This changes read delivery
churn, not native source authority or lossless-event guarantees.

## Helper retirement

The [baseline repetition](helper-retirement.json) reproduces three errors in
20 runs: one `FileNotFoundError` and two `ProcessLookupError` events between
checking `/proc/PID/stat` existence and reading it. No live-helper assertion fails
in these runs. The test now uses the existing single-read retirement probe,
which treats those exact exit errors as retirement while rejecting live states
and propagating permission failures. Its one-second observation window and
descriptor-closure check are unchanged. Corrected repetition has zero failures
in 60 runs; the helper/image suites and full source check pass.

The earlier a5 boolean assertion failure was not reproduced. These results fix
the demonstrated probe races; they do not establish the cause of every historical
failure or a new provider/process lifetime capability. Production helper cleanup
is unchanged.

## Missing native metadata

The standalone stdlib reference imports no Observer implementation. It queries
existing authenticated owning-daemon endpoints, excludes turn items and persists
only bounded metadata/counts. It performs no provider actions.

| Host | Native rows | Missing activity clocks | Native turn proof | Unknown kinds |
| --- | --- | --- | --- | --- |
| Snap | 89 | 37, all parked children | All 37 have no native turn record | 0 |
| Starship | 353 | 248, all parked children | All 248 have no native turn record | 21, all non-running and created more than seven days earlier |

See [Snap](snap-metadata.json) and [Starship](starship-metadata.json). No visible
user/unknown row has a missing activity clock in these samples. The 21 unknown
kinds have absent or unsupported native classification metadata: 16 VS Code and
two CLI origins lack `threadSource`; three VS Code origins have another shape.
Origin alone cannot distinguish a user thread from a child, so those rows remain
visible with kind unknown. No private history fallback, guessed age or legacy
classification is introduced. These are dated native limits, not universal
claims about future inventories.

## Installed artifact and native comparison

The [a6 manifest](../../../artifacts/observer-0.5.0a6.json) freezes source
`826befa8a7f544d4239126e9f84a539a86bd7125` and wheel SHA-256
`9240493982e041c8b8b98d59864c65a69b158bbd0c9fe63b8f9949becc5b84e7`.
Both hosts independently verify the core installation at
`/home/bryan/.local/share/agent-observer/0.5.0a6-9240493982e041c8`:
[Snap artifact](snap-artifact.json), [Starship artifact](starship-artifact.json).
The immutable archive retains the wheel, manifest and passive verifier. No SDK
or provider executable is bundled. Normal read/service selection still uses a5.

| Host | Direct / owned cached / pushed view | Rows | Running | Result |
| --- | --- | --- | --- | --- |
| Snap | [direct](snap-candidate-direct.json), [cached](snap-candidate-cached.json), [push](snap-candidate-push.json) | 89 | 2 | Exact identities, runtime/phase, saved identity, known clocks/outcomes and classification agree |
| Starship | [direct](starship-candidate-direct.json), [cached](starship-candidate-cached.json), [push](starship-candidate-push.json) | 354 | 6 | Exact identities, runtime/phase, saved identity, known clocks/outcomes and classification agree |

Each direct/cached mode has two bracketing native rounds; the pushed initial
view is separately bracketed. All ten comparisons have zero issues. Child
filtering, urgency/activity ordering, human age, exact show and doctor counts
pass. Starship gains a new user thread during this pass; the complete scoped
native inventory and the installed CLI both include it.

Both candidate publishers complete three minutes with three independent healthy
readers, 100 cached CLI reads and an unread subscriber:
[Snap](snap-candidate-soak.json), [Starship](starship-candidate-soak.json).
Healthy readers receive 24/30 frames and 8/18 views, respectively, with zero
coalescing gaps and zero reader errors. Runtime/history receipts remain current.
This is a focused successor check, not a replacement thirty-minute resource or
matched incremental provider-cost proof. Genuine coalescing and gap/resync remain
part of the contract and controlled regression coverage.

[Snap bookends](snap-before.json) match [after candidate](snap-after-candidate.json)
exactly. [Starship before](starship-before.json) and
[after candidate](starship-after-candidate.json) match all provider configuration,
workspace, selected links and normal Observer unit/incarnation fields. Its ordinary
daemon changes PID/birth during the broader pass with the same diagnostic image
and release. All candidate native comparisons already bind the new daemon;
the initial daemon is not claimed preserved. No harness performs provider actions,
and this naturally occurring change is not promoted into controlled recovery proof.
Starship's checkout history is untouched.

A fresh Starship epoch also brackets [direct](starship-reconciled-direct.json),
[cached](starship-reconciled-cached.json) and [pushed](starship-reconciled-push.json)
views with zero issues. Its [before](starship-reconciled-before.json) and
[after](starship-reconciled-after.json) preservation bookends match exactly,
including the new ordinary daemon. An additional
[two-minute reader check](starship-reconciled-soak.json) passes. All owned
candidate publishers exit and remove their sockets. An attempted late cached
probe against the already-finished first candidate was unavailable by design;
the fresh owned publisher supplies the accepted new-epoch comparisons.

## Remaining gates

Perform the separate scoped read/service upgrade, recovery, a5 rollback/reselection
and sustained readers. Retain ordinary providers, workspace and writer/frontend
selections. The a5
[completion report](../2026-10-08-codex-observation-completion/REPORT.md) retains
its historical exact-artifact evidence and thirty-minute acceptance bounds.
