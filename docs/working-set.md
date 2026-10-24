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

The [complete utility example](utility-read-guide.md) documents public factories,
clock contexts, setup budgets and cleanup. The [retirement guide](read-only-retirement.md)
documents CLI details. Full inventories remain a separate
[diagnostic path](mesh-read-client.md), never an automatic fallback.

The [producer checkpoint](history/delivery/working-set-producer-checkpoint.md)
and [history index](history/README.md) preserve exact qualification and cost
limits. They do not expand acceptance to a different host, home or consumer.
