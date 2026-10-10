# Local read cache and human watch

The read-delivery follow-up adds `service_public.ReadCache`, a pure consumer
utility for local Service 2 frames. It is not a collector, event stream,
notification client or Mesh cache. API 2, snapshot/watch 4 and Service 2 remain
unchanged; the helper's returned Python values are not a new wire protocol.

## Local consumer lifecycle

```python
from agent_observer.service_public import ReadCache

cache = ReadCache(host_scope=host, uid=uid, boot_id=boot_id,
                  clock_domain=time_namespace)

# Called with each local frame and the caller's CLOCK_BOOTTIME milliseconds.
cache.accept(frame, now_ms=boottime_ms)

# Also called on local timers, even if no new frame arrives.
view = cache.current(boottime_ms)
snapshot = view["snapshot"]
deadline = view["nextExpiryBoottimeMs"]

# EOF, transport/liveness failure, cancellation or selection change.
cache.invalidate()
# Reconnect establishes a new guard and baseline; no replay or auto-connect.
cache.reset()
```

Supply the actual local boot ID and time-namespace identity. Admission reuses
StreamGuard for host/UID/incarnation, sequence, gap/resync and schema checks;
future emission, reversed clocks and mismatched context are rejected. Invalid
and terminal streams revoke positives and require reset. Initial warming and
an admitted empty view are different. A gap remains invalid through status
until resync; reconnect starts a new baseline.

`current()` returns a qualified snapshot, health/reason, component statuses and
the next unexpired view deadline. Timers apply runtime/history/provider leases
independently. Heartbeat receipt fields never renew the cached view. Detected
component faults or context-generation changes revoke affected components
until a replacement view; generation regression rejects the stream. Detected
component faults or context-generation changes revoke the affected component
until a replacement view; generation regression rejects the stream. Expired
runtime becomes unknown and loses blocked reasons; it never becomes parked.
Saved metadata can remain under its independent history lease. Disappeared
unsaved rows omit observation memory without asserting session end.

The wire does not attribute merged activity/outcome to a single component.
If either component expires, the helper conservatively qualifies those facts
as stale, preserving the original conversation clock as `lastKnownAt`. It does
not choose another clock, advance age or infer provider-specific provenance.
Workspace remains available only under the history lease. Last-known titles,
identity and saved membership are display context, not fresh negative evidence.

`last_known` supplies an independent copy of the original admitted view and
receipts, without current authority. Neither `current()` nor caller mutation
rewrites it. Retain full identity for selection; filtering/order are external
presentation. Reset selection/baseline on policy changes. No helper differences
are native creation, completion, deletion or alert events.

## Human commands

```sh
agent-observer service watch --host-scope snap --human
agent-observer mesh watch --human
```

Human watch updates age every five seconds during quiet streams and applies
evidence expiry at local timer wakes (up to one second scheduling delay).
It displays warming, partial/stale coverage and end-of-stream revocation.
`--count` counts protocol frames, including control/warming, but not timer
renders. Local `--human` and `--json` are mutually exclusive. Existing default
service-watch JSON and its presentation filters remain unchanged.

Mesh human watch uses Mesh's ReadGuard/current selector and its reader-clock
receipts. It preserves one pending read while rendering timers; it does not
cancel/reconnect on each tick. Raw Mesh snapshot/watch frames remain lossless.
Timeout/EOF/error/output failure closes owned transport; reconnect is explicit.
Use the [Mesh guide](mesh-read-client.md) for remote scope and proof obligations.

Independent conformance is in `tests/test_read_cache.py`, local controlled ticks
in `tests/test_service_client.py`, and timer/count/cleanup in
`tests/test_human_watch.py`. Packaged/native/operational acceptance is a separate
gate in the [execution plan](read-delivery-follow-up-plan.md).
