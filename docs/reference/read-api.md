# Read API

The current prerelease full-read tuple is **API 4 / snapshot-watch 6 / Service 4**.
Optional full Mesh delivery uses explicit Agent profile v3 through SDK 1.
Working-set has separate version-1 read/member-lease/scope-lease interfaces.
Codex is the only native adapter. [Observation semantics](observation.md) defines
identity, runtime, activity, uncertainty and clocks.

## Inspect the installed contract

```sh
agent-observer api
agent-observer service api
agent-observer schema --help
```

These inspect metadata without provider collection. Packaged
[schemas](../../agent_observer/contracts/) define exact wire fields; public pure
facades are [`public.py`](../../agent_observer/public.py) and
[`service_public.py`](../../agent_observer/service_public.py).

## Classification and selection

`kind` is user, child, system or unknown. Native child signals retain their
precedence. Supported `threadSource=system` and `threadSource=thread_title` tags
classify internal helpers; ephemeral persistence alone does not. Inconsistent,
malformed or unsupported classification stays unknown with a bounded issue.

Raw snapshots preserve every admitted identity. Normal list/human views hide
confirmed child/system rows; unknown kinds stay visible. Diagnostic inclusion
and exact `select`/`show` retain access. Classification never determines runtime,
phase, saved existence or activity. Daemon idle remains running/waiting; parked
requires the positive native predicate described by observation semantics.

## Time and cached reads

Conversation activity is native evidence, distinct from observation and transport
time. Runtime/phase facts and source components have independent leases. Native
boottimes are host-scoped; Mesh expiry belongs to the receiving clock domain.
Hints, polling, copied frames and heartbeats renew no native fact.

Use [local Service 4](../guides/local-service.md),
[working-set](../guides/working-set.md) or
[full Mesh reads](../guides/full-mesh-reads.md). Optional
[prepared reads](prepared-reads.md) add local helpers, not a new wire contract.
Clients recompute expiry during silence and revoke current views at gaps,
disconnects and incarnation changes.

## Compatibility and retired interfaces

Select API 4/read 6/Service 4 and Agent v3 together. Older full profiles reject
this tuple; there is no automatic conversion or downgrade. Mesh SDK/Read/Delivery
versions and Tmux's native contracts remain independently versioned.

Observer writes, Claude observation and standalone active-only hosting are
removed. Old native active requests receive `active_feed_retired`; old Mesh
active-profile identifiers are rejected before binding/dispatch without aliasing
to working-set. Working-set retains its independent active and recent branches.
Native provider managers own conversation entry/control.

[Operations](../maintenance/operations.md) identifies public artifacts and
independent managed roles. A source update does not upgrade installed readers.
