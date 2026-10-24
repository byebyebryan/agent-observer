# Local Service 4 read cache

`agent_observer.service_public.ReadCache` is a pure local consumer helper for
the current Service 4 frames (API 4, embedded snapshot 6). It performs no native
collection, starts no service and imports no Mesh. The caller owns transport,
timers and shutdown. Cached service setup is in [Service 4](local-service.md).

## Lifecycle

Construct the cache with the expected host scope, UID, boot ID and local
time-namespace clock domain. Admit validated local frames with the caller's
`CLOCK_BOOTTIME` milliseconds. Call `current(now_ms)` on quiet ticks as well as
after frames so independent evidence leases expire without new delivery.

Preserve warming, partial, stale and unavailable results. A heartbeat is
transport liveness and cannot renew source evidence. On disconnect or terminal
failure, revoke the cache and close its owned iterator. A new stream needs its
own validated baseline; retained rows alone grant no current facts.

The [complete utility example](utility-read-guide.md) shows exact imports,
frame acquisition, clock context, budgets, cache admission and cleanup. Prefer
that runnable example to copying a partial lifecycle snippet.

## CLI clients

```sh
agent-observer service list --host-scope workstation
agent-observer service watch --host-scope workstation --human
```

Replace `workstation` with the configured logical host identity and pass the
explicit service socket when using a nondefault endpoint. Cached commands start
no provider/collector and take no conversation action.

The [earlier Service 2 guide](history/design/read-cache-client-before-20261024.md)
retains its old helper introduction and version bounds.
