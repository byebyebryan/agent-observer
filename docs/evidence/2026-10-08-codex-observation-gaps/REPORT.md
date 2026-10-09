# Codex observation gap closure

Date: 2026-10-08. Source gap repairs are accepted; a6 artifact/native and
managed operational gates are pending. The
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

## Remaining gates

Freeze/install a6 and compare direct/cache/push with independent native samples
on both hosts. Then perform the separate scoped read/service upgrade, recovery,
a5 rollback/reselection and sustained readers. Retain ordinary providers,
workspace, writer/frontend selections and Starship checkout history. The a5
[completion report](../2026-10-08-codex-observation-completion/REPORT.md) retains
its historical exact-artifact evidence and thirty-minute acceptance bounds.
