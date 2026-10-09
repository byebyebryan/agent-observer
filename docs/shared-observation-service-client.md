# Explicit local service client

This guide records the historical protocol-1/a16 workflow. New source and the
selected a6 read/service artifact use [API 2 client commands](api-v2-client-handoff.md)
and [service protocol 2](service-protocol-v2.md), with Codex as the sole native
adapter. Normal read/service selection now uses protocol 2; the examples below
retain their historical protocol-1 artifact bounds.

The service is a separate prerelease protocol 1 carrying unchanged API 1
snapshot 3. Direct `snapshot/list/show/watch` and the pure `public` facade retain
their existing contracts. Clients never autostart a publisher or fall back to
direct collection. The [managed operational baseline](observer-operations-execution.md)
selects a7 and enables its user unit on Snap and Starship.

The selected unit is available through `agent-observer service list --host-scope snap`
and `agent-observer service watch --host-scope snap`. Use host scope `starship` on
Starship. For a separately owned candidate endpoint, start a foreground publisher
with its full installed prefix:

```sh
PREFIX=/absolute/candidate/prefix
"$PREFIX/bin/agent-observer-service" serve --host-scope snap \
  --provider codex --provider claude --runtime-interval 30 \
  --history-interval 120 --socket /run/user/1000/ao-proof/read.sock
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

Starting with the operational a7 candidate, `serve --workspace-config /path/to/workspace.json`
uses the same root/project mapping model as direct reads. The file must be a
regular JSON file of at most 128 KiB. It is validated and copied at startup before
opening the endpoint or collecting providers; file changes require an Observer
restart. A missing option retains default Git enrichment with no configured roots
or project mappings. For example:

```json
{
  "roots": [{"key": "code", "path": "/home/bryan/code"}],
  "projects": [{"rootKey": "code", "relativePath": "agent-observer", "projectKey": "agent-observer"}]
}
```

Only history jobs carry this configuration and enrich workspace metadata.
Workspace expires with its history lease even while runtime monitoring remains
healthy. A project key groups explicit workspace mappings; it does not merge
session identities, attest another host or grant action authority. Installed/native
acceptance and normal selection are tracked in
[the operational execution](observer-operations-execution.md).

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
never renew it. Retry uses bounded backoff. The measured Snap configuration is
runtime 30/history 120 seconds, with
90/360-second leases; Starship uses the packaged 20/60 seconds and 60/180-second
leases. Snap's slower cadence reduces measured publisher/owned-worker CPU below
the initial five-percent target. Monitoring and saved discovery can lag their
respective cadence plus bounded read delay. Faster intervals are explicit server
configuration and require separate resource measurements.

Watch heartbeats occur every 10 seconds. The client defaults to a 15-second
transport deadline and rejects current leases that expire during delivery. A
custom consumer must also stop presenting current claims when its local lease
expires or delivery becomes silent. With no public per-field receipt map,
conservatively invalidate that source's current claims at the earliest expiry
among its currently current/partial components, or receive a newly projected view;
ignore already-stale components when computing the next deadline. In particular,
a runtime receipt cannot renew cached history fields. A service heartbeat is only
transport liveness. Native conversation activity and last-known clocks are preserved.
Use current display time to calculate age; do not mutate collection/evidence
clocks when drawing a cached view.

This interface grants no frontend, notification or provider action authority.
The normal Observer unit/link selection has its own operational acceptance. See the [implementation status](shared-observation-service-status.md)
for the exact accepted artifact and operational gaps.
