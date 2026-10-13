# Offline timing design acceptance

2026-10-12. T0–T4 of the [authorized offline goal](../../timing-design-execution.md).
This pass completes timing research/design and a standalone prototype. It does
not implement a new public contract, native collector, notification source or
networking integration. API 2/read 4/Service 2/Mesh SDK 1 remains implemented.

## Outcome

The [draft specification](../../timing-contract-proposal.md) recommends explicit
native latest-turn identity/status/start/end/duration and a separate native
thread-update clock, preserving current conversation activity and phase/runtime
semantics. It defines nullable, stale/last-known, receipt attribution, ordering,
non-atomic join and clock rules. Observed-phase-series timing stays outside the
first public extension and has a separate optional native/client gate.

The [acceptance plan](../../timing-acceptance-plan.md) maps every offline case to
production core/schema/service, immutable native, Mesh, resources/operations
and consumer checkpoints. Proposed API 3/read-watch 5/Service 3 and a successor
Agent profile remain a reviewed following proposal, not deployed versions.

## Evidence and reproduction

- [Model](timing_model.py): stdlib-only normalized facts, fixed configured source
  contexts/order watermarks, bounded phase map, native-turn receipt selection
  and conservative derived timers. It performs no IO and imports no production
  Observer/provider/transport code. It is not packaged as runtime code.
- [Cases](test_timing_model.py): 54 offline tests covering scope, phase changes,
  same-phase turn changes, missing/empty/invalid/unproved clocks, distinct source
  leases, stale/failed ordering, source and observer replacement, omitted rows,
  non-atomic reads, collection delay, monotonic clocks and bounded capacity.
- [Runner](run-offline.py) and [receipt](results.json): all 54 pass; eight targeted
  broken variants are detected; nineteen bounded native metadata samples replay.
  SHA256 inputs bind the exact model, cases, runner and captured native receipt.

From the repository root:

```sh
rtk proxy python3 -B docs/evidence/2026-10-12-timing-design/run-offline.py
```

An optional `--receipt /absolute/new/path.json` writes exclusively to a new
file. Existing evidence is not overwritten. The runner temporarily replaces
in-memory modules for mutation checks, restores them, and starts no provider,
networking, service or native fixture. Mutation failures are expected detection
results, not ignored baseline errors.

The replay reuses the [previous native study](../2026-10-12-codex-timing/REPORT.md).
It derives deterministic monotonic-like offsets from captured wall timestamps.
This does not prove live BOOTTIME behavior or native phase-entry time. The earlier
ordinary Snap/Starship metadata reads and controlled real-App-Server/local-model
tests keep their exact provenance and partial scope. This goal performs **zero
provider reads/actions**, zero new inference and no additional native workload.

## Important cases and review findings

The captured approval turn illustrates the separate clocks:

| Captured observation | Native ongoing-turn elapsed | Observed phase span |
| --- | --- | --- |
| First blocked observation | 2990 ms | 0 ms |
| Repeated blocked observation | 4199 ms | 1209 ms |
| Approval answered / working | 4508 ms | 0 ms |

Native turn start stays `1791842909000` throughout. Native thread update remains
unchanged across the answer. Phase-series reset follows the newly observed
working phase; native turn elapsed includes the preceding block. These durations
are derived at the captured observations with seconds-based native precision,
not measurements of exact native phase entry.

The independent reread and fixture review reconciled these findings:

1. A newer failed/expired/in-progress/known-empty metadata observation must not
   revive an older completed turn or fill missing start/end fields from it.
   Select by source observation order, even when a newer authoritative response
   returns an older event timestamp; do not maximize event time.
2. Timing must bind to its actual selected component receipt. Healthy history
   can preserve its own native metadata after runtime expiry, but cannot keep a
   current working-turn/phase timer. Tied observations cannot choose a longer
   lease to promote current data.
3. Runtime and turn queries are non-atomic. Incompatible status/turn state, known
   ID disagreement and a start definitely after an earlier status suppress a
   joined timer while valid independent facts remain available. Compatible
   samples remain explicitly sampled rather than atomic.
4. Metadata-only new-turn knowledge cannot renew/start a phase anchor. Only a
   fresh admitted runtime observation can change the shared observed series.
   Carrier duplicates and client ticks are not engine observations.
5. A client disconnect does not imply the producer stopped observing. Fresh
   resync can recover its shared anchor. Source failure/expiry/missing partial
   rows/new context breaks that anchor; healthy positive siblings remain usable.
6. Late helper replies need source-generation/order fences. Source-wide batch
   fences bound storage without per-identity replay tombstones. Unknown/omitted
   phase rows remove optional ages and never assert parked.
7. Read completion may occur after the original lease. The model admits that
   receipt shape, then rejects a current timing claim; it does not extend expiry
   to read completion/arrival. Monotonic regression requires a new tracker.
8. Sampled phase span is not a lower bound: a hidden same-turn working/blocked/
   working cycle can leave an observed two-second series while the current
   actual working episode is only 0.1 seconds old.

The first identity fixture incorrectly sent two complete one-row rosters for
the same source, deliberately omitting the first identity. It was corrected to
send both ID kinds in one source roster; full identity scope now passes. The
stamp guard was also corrected to allow reads finishing after their deadline,
so expiry is represented as unavailable evidence rather than a malformed time.
These were offline fixture/model corrections, not provider behavior findings.

The eight detected variants break repeated-read anchors, expiry, turn-ID reset,
newest-receipt ordering, tied lease choice, turn-ID joins, failure ordering and
negative native clock deltas. They substantiate that the cases reject plausible
semantic regressions rather than only round-trip the model's chosen fields.

## Limits and unchanged ownership

The model is provisional and assumes already normalized/admitted provider facts.
It is not a full public shape/semantic validator or an implementation of the
new receipt binding. `lastUpdated` semantics come from the earlier native proof;
this pass does not implement its runtime projection. A nullable turn-ID case
proves model flexibility, not any additional provider's native capability.

Prototype bounds are fixed sources (maximum 32), maximum 1512 input rows and a
configurable live-map ceiling (default 512). Timing capacity can omit new optional
ages while retaining admitted series; it never edits the source discovery roster.
These are offline bounds, not new public capacity promises or runtime resource
measurements. Production frame growth must obey existing byte limits and report
capacity honestly; this proposal does not silently widen network budgets.

No new provider, transcript/event/notification capture, durable ledger, TUI/tmux
query or client edit is included. No native completeness, exact state age,
lossless transitions, cross-host clock accuracy, Mesh candidate performance,
managed rollout or physical dashboard acceptance follows from these results.
The external Mesh agent owns its separate networking/profile/candidate work.

Final project checks and the protected-source audit are recorded in
[verification](verification.json). Subsequent production integration follows
C0–C6 after reconciling the external Mesh pass, with independent native/consumer
gates and no converter or provider version pin.
