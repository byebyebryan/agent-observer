# Observation API 4

The current full-read tuple is API 4, snapshot/watch 6 and Service 4. Optional
Mesh delivery binds the explicit Agent profile v3 through SDK 1. Working-set
has separate version-1 interfaces. Codex is the only native adapter and all
interfaces remain prerelease. See [architecture](architecture.md) for semantics
and [operations](operations.md) for release/role selection.

Current schemas are packaged under [`agent_observer/contracts/`](../agent_observer/contracts/).
Public pure reads are exposed by [`public.py`](../agent_observer/public.py)
and [`service_public.py`](../agent_observer/service_public.py). Use
`agent-observer api`, `agent-observer schema --help` and
`agent-observer service api` to inspect the installed contract independently
of source documentation. CLI examples begin in [getting started](getting-started.md).

API 4 introduced system classification without changing the inherited identity,
runtime, activity, component freshness or clock rules. Its original
[a1 acceptance](evidence/2026-10-13-system-classification/REPORT.md) retains its
exact historical package and host scope.

## Classification and selection

`kind` is `user`, `child`, `system` or `unknown`. Codex's supported
`threadSource=system` and `threadSource=thread_title` tags classify internal client
helpers. Codex uses `thread_title` for its built-in temporary title generator.
Other feature tags remain unknown until their ownership is established. This is an
optional client-supplied analytics classification, not an OS process type.
The [title-helper correction](evidence/2026-10-14-title-helper/REPORT.md) records
the source/native proof and its separate installed rollout boundary.
Ephemeral persistence alone does not classify a system thread. Valid native
child signals retain their existing precedence; inconsistent, malformed or
unsupported classification stays unknown with a bounded metadata issue.

Raw snapshots preserve every admitted row, including system identities.
`listing` and human/direct/cached/Mesh list and watch views hide confirmed
system rows by default. `include_system=True` and CLI `--include-system` make
those rows visible. Exact identity `select` and `show` preserve diagnostic access.
Unknown classifications remain visible. Filtering happens after reconciliation,
so a retained unknown identity positively classified as system stops appearing.

An optional [prepared watch helper](prepared-agent-read-interface.md) is additive
local Python read support. It retains this same wire/profile, delegates current
expiry to Mesh and keeps source context separate from authority. Its
[package/native/operational gates](evidence/2026-10-14-prepared-reads/REPORT.md)
are independent of the a1 producer acceptance. Preparation does not add phase
entry timestamps, alter activity/order or certify a device integration.

Classification never determines runtime, phase, history presence or activity.
Daemon idle remains running/waiting, and parked still requires its reviewed
positive native predicate. All [API 3 timing semantics](history/contracts/api-v3.md) remain.

## Compatibility

This is a breaking prerelease enum extension. API 3/wire 5/Service 3 and Agent
profile v2 do not accept the new tuple. No converter or automatic downgrade is
provided. Mesh SDK 1, Read 1, Delivery 1, Tmux v1 remain independent. Observer writes are retired. Immutable producer/read/publisher packages, native
metadata comparisons and both-host cached IPC/SSH proofs gate adoption.

## Read-client handoff

The [API 3 handoff](history/contracts/api-v3-client-handoff.md) retains the timing, identity,
component freshness and ownership rules. Select API 4/read 6/Service 4 and the
explicit Agent v3 profile together; old clients must reject the new tuple.

```sh
agent-observer api
agent-observer service list --host-scope starship
agent-observer service list --host-scope starship --include-system
agent-observer mesh list
agent-observer mesh list --include-system
```

Raw snapshots include system rows, so downstream applications must apply their
own reviewed selection policy. The RLCD excludes confirmed child/system and
positively parked rows from membership, counts, overflow and retained context;
it retains running rows of unknown kind. Classification alone never proves
runtime disposition.
