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
The owner advances `clockGeneration` when adjacent distinct accepted clock
brackets `I=[W-U-1, W-L+1]` do not overlap (all values are milliseconds; `W`
is the wall timestamp; `L` and `U` are the BOOTTIME sample and acceptance bounds).
`clock_discontinuity` means
an event guard remains unresolved across that epoch until a newer native
activity timestamp is observed. The exported component clocks show current
bindings, not incident history.

Later overlapping brackets or a complete
current native census do not clear an event guard for unchanged `activity.at`:
a quiet parked row can remain unresolved. This affects the recent branch; a row
with proved eligibility and current active support can still qualify through
the active branch. Polling and lease renewal do not advance native activity,
and restarting or manufacturing activity is not a recovery procedure.

For diagnosis before changing owner incarnation, preserve frame `serviceId`,
`bootId`, `clockDomain`, `sequence`, `viewRevision`, `observationRevision`,
`clockGeneration`, `clockCeiling`, and the current `projection.scopes[].clocks[]`
samples.

Zero current members can mean no identity qualifies while scope coverage is
still partial. Complete-empty requires complete current coverage and no
members, uncertain identities or known nonmembers.

## Bounded inspection

Requires the compatible optional Mesh pair, a running cached working-set
publisher/bridge and configured host routes. Installing a reader starts none
of these. With your configured logical host ID:

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
