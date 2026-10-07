# Explicit local service client

The service is a separate prerelease protocol 1 carrying unchanged API 1
snapshot 3. Direct `snapshot/list/show/watch` and the pure `public` facade retain
their existing contracts. No service is automatically started or selected.

Start the candidate in the foreground with its full installed prefix:

```sh
PREFIX=/absolute/candidate/prefix
"$PREFIX/bin/agent-observer-service" serve --host-scope snap \
  --provider codex --provider claude --socket /run/user/1000/ao-proof/read.sock
"$PREFIX/bin/agent-observer" service status --host-scope snap \
  --socket /run/user/1000/ao-proof/read.sock
"$PREFIX/bin/agent-observer" service list --host-scope snap \
  --socket /run/user/1000/ao-proof/read.sock
"$PREFIX/bin/agent-observer" service watch --host-scope snap \
  --socket /run/user/1000/ao-proof/read.sock --count 10
```

Use only `--provider codex` on Starship. The socket's parent must be a canonical,
owned private directory (0700); the service creates that immediate directory if
absent. The socket and singleton lock are 0600. The default endpoint is
`$XDG_RUNTIME_DIR/agent-observer/read.sock`. Stop the explicitly owned service
with SIGTERM or Ctrl-C. This does not stop provider sessions.

Service configuration chooses the owning host/store once. Default Codex home is
`CODEX_HOME` or `~/.codex` with its explicit store selector. Default Claude home
is `CLAUDE_CONFIG_DIR` or `~/.claude`; the default and explicit Claude selectors
remain distinct. Subscribers cannot relabel the host, choose stores, change
collection intervals, trigger a refresh or request an action.

`service api` and `service schema --kind request|frame` work without a service.
`status` and `snapshot` emit one service envelope. `list` displays ordered rows;
its `--json` form retains the envelope and filters its embedded snapshot.
`watch` emits newline-framed service envelopes. List/watch exclude confirmed
children by default; `--include-children`, `--provider` and `--order` apply client
presentation policy. Snapshot retains the entire producer inventory.

Read the [service protocol](service-protocol-v1.md) before implementing a client.
Use `service_public.parse_frame` and one `StreamGuard` per connection. The separate
`service_client.frames` transport additionally checks endpoint/peer ownership,
local boot/time namespace and source lease validity on receipt. It imports no
provider adapters and performs no direct fallback. Frames have bounded size and
an absolute receive deadline, including fragmented or trickled input.

Do not pass an envelope to the existing snapshot/watch parser. Validate its
service scope/incarnation/sequence/lease first, then consume `frame['snapshot']`
when present. Warm-up has a null snapshot, not complete empty discovery. Delivery
loss produces `gap` followed by a full `resync`; reconnect starts a new guard.
No durable replay or native event continuity is promised.

The candidate defaults to runtime polling every 20 seconds and saved history
(including workspace enrichment) every 60 seconds, with a 10-second collection
deadline. Runtime/history lease lengths are independently derived as the larger
of three intervals and the timeout plus two intervals plus one second. Failed
reads invalidate their component immediately; heartbeats and cached requests
never renew it. Retry uses bounded backoff. Faster intervals are explicit server
configuration and require separate resource measurements.

Watch heartbeats occur every 10 seconds. The client defaults to a 15-second
transport deadline and rejects current leases that expire during delivery. A
custom consumer must also stop presenting current claims when its local lease
expires or delivery becomes silent; a service heartbeat is only transport
liveness. Native conversation activity and last-known clocks are preserved.
Use current display time to calculate age; do not mutate collection/evidence
clocks when drawing a cached view.

No normal unit, link, frontend, notification publisher or provider policy is
selected by this interface. See the [implementation status](shared-observation-service-status.md)
for the exact accepted artifact and operational gaps.
