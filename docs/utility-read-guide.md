# Bounded current-state utility example

Date: 2026-10-23. This guide describes the developer-only
[`current_summary.py`](../examples/current_summary.py) example. Its JSON is a
content-free diagnostic projection, not a new wire format, API, daemon or
deployment contract. It does not query a provider or take action.

## Interpreter prerequisites

Run the example with an interpreter that can import this Agent Observer
checkout or an installed Agent Observer package. Mesh mode also requires the
matching Mesh Plus SDK 1 installation with the Observer working-set profile
registered; local Service 4 mode does not import Mesh. Running a script from
`examples/` does not put the repository root on `sys.path`. From a checkout,
make that path explicit:

```sh
OBSERVER_ROOT=/path/to/agent-observer
OBSERVER_PYTHON=/path/to/venv/bin/python
PYTHONPATH="$OBSERVER_ROOT" "$OBSERVER_PYTHON" \
  "$OBSERVER_ROOT/examples/current_summary.py" local --host-scope starship \
  --socket /absolute/path/to/service4.sock --duration 5
```

Use the same interpreter for Mesh and its SDK. With an installed package,
select the environment where both distributions are installed and pass the
example's absolute checkout path.

## Explicit invocations

The local Service 4 watch requires both the host scope and absolute socket path:

```sh
OBSERVER_ROOT=/path/to/agent-observer
OBSERVER_PYTHON=/path/to/venv/bin/python
PYTHONPATH="$OBSERVER_ROOT" "$OBSERVER_PYTHON" \
  "$OBSERVER_ROOT/examples/current_summary.py" local \
  --host-scope starship \
  --socket /absolute/path/to/the-service4.sock \
  --duration 5
```

The managed default publisher source is `agent_working_set`. On the selected
host, `--scope local` binds the supplied `--host` as the local identity and uses
the explicit local Mesh publisher/bridge socket:

```sh
OBSERVER_ROOT=/path/to/agent-observer
OBSERVER_PYTHON=/path/to/venv/bin/python
PYTHONPATH="$OBSERVER_ROOT" "$OBSERVER_PYTHON" \
  "$OBSERVER_ROOT/examples/current_summary.py" mesh \
  --host snap \
  --source agent_working_set \
  --scope local \
  --socket /absolute/path/to/the-local-mesh-publisher-bridge.sock \
  --window-hours 72 \
  --duration 5
```

The Mesh socket is the local publisher/bridge endpoint used when the selected
host is local; it is not a reader endpoint. For `--scope hosts`, the host must
exist in the configured Mesh/SSH Plus authority, and remote hosts use that
configured route. No source, socket, host or route fallback occurs. The Mesh
working-set window is an integer from 0 through 720 hours; zero selects only
the active branch, and the default is 72 hours.
The chosen window must match the configured publisher's fixed window; changing
this argument does not reconfigure a producer and a mismatch must fail.

Duration defaults to five seconds and is capped at 60 seconds. The local budget
starts immediately before the first Service 4 read. Public `frames` requires a
minimum one-second timeout, so setup/read may consume that transport budget for
subsecond requests; a 100 ms wake and iterator-close overhead can extend total
runtime further. A validated baseline-backed watch closes normally at its
budget. If a transport timeout ends it first, only the public
`service_transport_timeout` at or after that budget is treated as normal
completion. Reaching the budget without a validated baseline, or any earlier or
other transport error, revokes. Mesh duration includes `configured_reader`
setup and the watch; its final SDK cleanup can add close overhead. Quiet wakeups
are at most 100 ms apart and recompute expiry without renewing any lease. Output
summaries are capped at one per second, plus the final revoked/closed line.

## Interfaces and ownership

The local route uses public `agent_observer.service_client.frames` and
`agent_observer.service_public.ReadCache`. The socket client validates Service
4 frames, and the cache applies local `CLOCK_BOOTTIME` expiry in the caller's
boot and time-namespace context. It imports no Mesh module and starts no
service. The summary includes only exact identity, runtime/phase value and
health, source coverage, component freshness, transport state and clock
context. It omits titles, workspace paths and all provider/session content.

The Mesh route uses public `mesh_plus.api.configured_reader` and its admitted
working-set watch. A single `WorkingSetAgentProfile` instance is passed to both
the configured reader and `PreparedWorkingSetAgentWatch`. The prepared facade
returns current members, uncertain identities, admitted nonmembers and
per-scope coverage; a quiet tick calls its public `read(now, clock)` path so
membership and scope leases expire without another frame. A pending SDK
`anext` task stays alive across quiet ticks. On disconnect, stream failure,
cancellation, gap/resync or bounded completion, the invocation disconnects the
prepared guard and closes its own stream. There is no reconnect supervisor in
this example. A fresh invocation uses a new request and obtains a new baseline.

The compatible interface tuple is API 4 / snapshot 6 / Service 4, Mesh SDK
interface 1, and working-set read, member-lease and scope-lease interfaces 1.
The utility displays the receiving Mesh `CLOCK_BOOTTIME` and Mesh clock domain;
the local route displays the local `CLOCK_BOOTTIME`, boot ID and Linux time
namespace. Mesh translated expiry values belong to that receiving clock, not a
remote host's raw boottime.

## Reading the output

Each JSON line is a new diagnostic summary. The local route reports source
coverage (`complete`, `partial`, `unavailable` or `unsupported`) separately
from the current/partial/stale/unavailable read health. It labels
`complete-empty` only when it has a non-null validated snapshot, no sessions,
complete saved and runtime coverage for every source, and all relevant
component leases remain current. Warming and unavailable reads have no current
session rows. A quiet tick can downgrade a previously current view as a lease
expires.

The Mesh route retains each scope's coverage state and reports members,
uncertain rows and native nonmembers separately. `complete-empty` requires at
least one present scope and complete current coverage, with no members,
nonmembers or uncertainty. An empty member array alone says nothing about
coverage. Warming context, partial/stale scopes and unavailable delivery remain
visible. Final lines are `closed` or `revoked`, contain no current identities,
and identify an endpoint or stream failure when one occurred.

The watch is not event replay. It makes no guarantee that changes which began
and ended between observations will appear. Heartbeats, copied frames and the
example's presentation ticks do not renew source facts; no lease is renewed by
polling. The local cache and prepared Mesh facade recompute expiry against their
respective local receiving clocks.

## Separate full-read diagnostic path

This example reads the selected working-set projection in Mesh mode. The
existing full-read CLI is a distinct diagnostic path for full API 4 snapshots
and watches, not an implicit fallback for this utility. See the
[API 4 handoff](api-v4.md) and [Mesh read-client guide](mesh-read-client.md),
including the ordinary `agent-observer service list --host-scope HOST` and
`agent-observer mesh list` commands.

Current ownership and freshness rules live in
[architecture boundaries](architecture.md),
[observation boundaries](observation-boundaries.md),
[working-set guide](working-set.md), and
[operations](operations.md). Earlier
candidate status and rollout statements in dated checkpoints are historical
evidence; consult each receipt's date and selected tuple before treating it as
current runtime evidence.
