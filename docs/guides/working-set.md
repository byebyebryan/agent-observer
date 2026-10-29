# Working-set reads

Working-set is a bounded union of independently proved active membership and
recent conversation context. It covers the active use case while retaining
useful recent identities. Standalone active-only hosting is retired.

## Membership and coverage

The default recent window is 72 hours. The active branch remains independent:
an active identity is not excluded merely because its conversation clock is old
or unavailable. A recent-only member need not be active. Producer policy fixes
the window; a reader cannot reconfigure it by requesting a different value.

Member leases and scope-coverage leases expire independently. A valid empty
members array does not establish complete-empty coverage. Partial, stale,
unavailable, uncertain and admitted nonmember outcomes remain explicit. A
retained runtime label is not current active membership.

`coverage.reason` names one primary blocker. Source, census and support
blockers take precedence over row-level membership reasons. If several census
identities are unresolved, the reason comes from the lexicographically first
full identity; it does not enumerate every blocker. Reasons include
`census_support_unproved`, `census_identity_unprojected`,
`eligibility_support_unproved`, `active_support_unproved`, and native recency
reasons such as `clock_discontinuity` and `clock_bracket_overlap`.
`census_support_unproved` means the census support does not join a current
receipt; `census_identity_unprojected` means the census identity has no row for
the membership decision. For one row, unproved eligibility precedes unproved
active membership, which precedes a recent-branch reason when active membership
is known false. `membership_incomplete` is the fallback when no more specific
blocker is available.
## Clock changes and recovery

The owner advances `clockGeneration` when adjacent distinct accepted clock
brackets `I=[W-U-1, W-L+1]` do not overlap (all values are milliseconds; `W`
is the wall timestamp; `L` and `U` are the BOOTTIME sample and acceptance bounds).
The owner retains the lowest accepted interval endpoint internally and the
highest endpoint as `clockCeiling`. Both survive source-context changes within
the same collector incarnation. Mirrored samples and rejected inputs do not
advance them. The exported component clocks remain current bindings.

For activity timestamp `T`, recent window `H` and retained offset range
`[Omin, Omax]`, the possible expiry range is
`[T+H-Omax, T+H-Omin]`. Recent membership is proved only before the earliest
expiry and after every mapping places the event in the past. Outside-window
is proved only at or after the latest expiry. Crossing that range remains
unknown; `clock_discontinuity` can explain ambiguity spanning clock changes.
Quiet rows, including identities first seen after a change, can recover
without generating new activity. Quiet ticks reconsider the proof boundaries,
but expired source supports still require a new accepted native sample.

The positive cutoff for an unchanged timestamp cannot move later when clocks
move backward or polling refreshes support. A lower timestamp remains
`activity_timestamp_regression` unless a changed native latest-turn ID proves
a different turn: its current receipt must join the same accepted activity
sample, and its selected native start/completion time must equal `activity.at`.
Missing, stale or mismatched turn metadata grants no such exception. Active
membership remains independent of uncertain recency.

This policy uses the published integer `activity.at`, preserving its existing
timestamp semantics. The offset range covers accepted mappings during this
collector incarnation; it does not reconstruct unobserved clock excursions or
authenticate the physical age of timestamps saved before collection began.
Large corrections can leave a correspondingly large uncertainty interval.
Stable samples do not erase that evidence. Restarting the collector is not
proof of recovery from the incident.

Working-set v1 exports its existing exact current-sample bounds. Internal
negative decisions wait for the stronger retained-range proof; no reader
validation, wire schema or lease is weakened by this recovery policy.

For diagnosis before changing owner incarnation, preserve frame `serviceId`,
`bootId`, `clockDomain`, `sequence`, `viewRevision`, `observationRevision`,
`clockGeneration`, `clockCeiling`, and the current `projection.scopes[].clocks[]`
samples. The collector also retains the latest actual discontinuity and logs
its old/new accepted sample brackets, intervals, generation and acceptance
order as bounded metadata. These records establish a detector transition;
independent host evidence is needed to attribute it to NTP or another cause.

Zero current members can mean no identity qualifies while scope coverage is
still partial. Complete-empty requires complete current coverage and no
members, uncertain identities or known nonmembers.

## Bounded inspection

Requires the compatible optional Mesh pair, a running cached working-set
publisher/bridge and configured host routes. Installing a reader starts none
of these. If you own a Codex home and need to host the first source, follow the
[first-source setup guide](source-setup.md). With your configured logical host
ID:

```sh
agent-observer working-set list --host workstation --scope local
agent-observer working-set watch --host workstation --scope local --active --duration 30
```

The default source is `agent_working_set`. Select another configured home/source
with `--source`; use `--socket` for an explicit local bridge endpoint. Remote
host selection uses existing Host Mesh routes and never adds a peer or reverse
route. The ordinary window is 72 hours and must match the publisher.

List waits for a settled cached read; watch is bounded, defaults to 30 seconds
and is capped at 60. Human output includes identities, membership, runtime/phase
and coverage without conversation content. Closing the reader revokes its own
current view and stream. No provider or conversation action is taken.

## Build a consumer

Use `WorkingSetAgentProfile` with `PreparedWorkingSetAgentWatch` and the same
profile instance in the Mesh reader. Recompute membership and scope expiry on
quiet ticks. Revoke on gap, disconnect, cancellation or terminal failure;
require a new baseline before current positives return.

The [complete utility example](read-utilities.md) documents public factories,
clock contexts, setup budgets and cleanup. The [retirement guide](https://github.com/byebyebryan/agent-observer/blob/9c0636c7ac286d965a4c66452f26c47e1f4886b5/docs/read-only-retirement.md)
documents CLI details. Full inventories remain a separate
[diagnostic path](full-mesh-reads.md), never an automatic fallback.
