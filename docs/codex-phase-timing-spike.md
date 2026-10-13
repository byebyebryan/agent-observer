# Codex turn time and observed phase time

2026-10-12. Research spike while the separately owned Mesh Plus loop finishes.
No runtime source, public API/schema, selected artifact, service or Mesh contract
is changed. The [timing contract review](codex-timing-contract-review.md) remains
a proposal. This spike narrows the clock semantics before implementation.

The following [offline goal report](evidence/2026-10-12-timing-design/REPORT.md)
hardens source/clock/lease/capacity handling and non-atomic turn/phase joins. The
[draft specification](timing-contract-proposal.md) recommends native turn/update
fields first and keeps observed-series timing as an optional later checkpoint.

## Native turn timing answers the primary question

Codex exposes the latest turn's native ID, `startedAt`, `completedAt`, status
and nullable `durationMs`. The current passive adapter already requests bounded
latest-turn metadata through `thread/turns/list`, with `limit: 1` and
`itemsView: notLoaded`; no conversation items are needed. Exposing these
already-read fields need not add another collector or transcript scan.

For an ongoing turn, elapsed turn time uses its native start, not the thread's
last update. In the [ordinary native samples](evidence/2026-10-12-codex-timing/REPORT.md):

| Host / sampled working thread | Time since native turn start | Time since native thread update |
| --- | --- | --- |
| Snap / `01a0fece-0176-7a33-abb3-e99fdb38417a` | 917.2 seconds | 1.2 seconds |
| Starship / `01a0a625-fddb-7a12-aaa6-0da3bd3fcc1e` | 1110.6 seconds | 14.6 seconds |

These are ages at the captured sample, not current assertions about either
session. They support the user's observation that an update clock can keep
moving during work. The exact Command Center column-to-field mapping has not
been independently instrumented; native clock meanings do not depend on it.

The controlled approval and question cases kept the same native turn ID and
start across working and blocked phases. Turn elapsed time therefore includes
the time spent blocked. It is useful even if Observer starts monitoring midway
through a turn or restarts, because a new authoritative read can recover it.
It does not mean uninterrupted working time, time since the latest approval was
answered, or the start of an entire multi-turn goal/task.

After a terminal turn, `completedAt` supplies time since that turn ended.
`durationMs`, when present, supplies native elapsed duration at finer precision
than subtracting the seconds-based start/end fields. A loaded idle session may
have no turn, and a resumed idle session may have a much older completed turn;
neither establishes when the current idle runtime began. Parked sessions also
have no useful running-phase timer.

Existing public `activity.at` already selects turn completion when present,
otherwise turn start, matching all 51 comparable ordinary samples. Keep that
meaning. Explicit latest-turn identity and boundary fields would make the
choice reliable for clients without inferring a clock type from diagnostic
reason codes or combining separately sampled status and metadata as atomic facts.

## What Observer can track itself

The [standalone prototype](evidence/2026-10-12-codex-timing/observed-phase-spike.py)
replays the nineteen captured native metadata samples and tests a separate
**observed phase streak**. Its [receipt](evidence/2026-10-12-codex-timing/observed-phase-spike.json)
records thirteen passing offline checks. It performs no provider reads/actions
and imports no production Observer code.

An observed streak starts when a current authoritative sample first shows a
phase. Repeated accepted samples of the same phase and turn retain that anchor.
A phase change or new turn ID resets it. Expiry, source failure, an unknown
phase, daemon replacement or a new Observer lifetime breaks the streak. Recovery
starts a new observed anchor; it cannot invent the missing earlier history.
Older receipts cannot rewind it. Changes between approval and question flags
alone do not prove that the normalized blocked phase ended.

This provides useful, explicitly observation-based age. It is not an exact
phase-entry timestamp or even a guaranteed lower bound on current phase age.
For example, polls see working at seconds 1 and 3 while the same turn briefly
blocks at second 2 and resumes at 2.9. The observed streak is two seconds old,
but the current working episode is only 0.1 seconds old. No polling frequency
or healthy lease can prove that such an intervening cycle did not happen.

Native `thread/status/changed` notifications contain no transition timestamp
in the inspected schema. They can reduce sampling delay, but the existing hint
listener deliberately emits refresh requests rather than authoritative facts.
`turn/started` and `turn/completed` contain turn metadata in the native schema;
the current listener does not select those methods. Adding them as optional
refresh hints could improve same-phase new-turn detection without transferring
authority to an unreplayed notification stream. Current-state push also does
not promise every transition, so a device cannot reconstruct a complete phase
timeline merely by watching snapshots.

## Boundary and eventual implementation

The passive provider adapter should expose native turn/update metadata with
independent health and unavailable-clock handling. If observational phase
tracking is wanted, the reusable core engine should own it, keyed by complete
session identity and source/Observer incarnation. The service hosts that engine;
clients joining later should see the shared observed anchor rather than each
starting an unrelated timer. Mesh delivers the original timing evidence and
leases. Clients choose labels, ordering and ticking. None of this requires
tmux, TUI matching, hooks or attachment data.

Use host monotonic/BOOTTIME clocks for observation ordering, streak duration
and lease expiry. Native event timestamps remain provider wall times; display
calculations need precision and clock-skew treatment. The offline replay uses
captured wall-time offsets only as a deterministic input clock, not as proof
of live monotonic behavior. Receipt races, component attribution, source gaps,
bounded ledger lifetime and cross-host delivery still need implementation and
native acceptance before a public tracking capability can be advertised.

The initial useful choices for a client are separately named clocks:

- Working or blocked: elapsed native ongoing turn, including blocked time.
- Waiting: time since the latest native turn ended, when known.
- Current phase: observed streak age, if the client accepts that approximation.
- General history/recency: last conversation activity, or a separately exposed
  native thread-update clock with its broader metadata effects.

Those are presentation choices, not one universal `stateSince` contract.
RLCD currently requires actual current-state entry time and displays unknown
ages otherwise. Native turn age and observed streak age would be explicit
refinements of that requirement; neither silently satisfies exact phase age.
The preferred producer addition remains explicit latest-turn boundaries first.
Decide whether clients also need observed streaks before freezing the successor
schema, then coordinate its separate Mesh profile adoption after the active
external loop finishes. No version or deployment is changed by this spike.
