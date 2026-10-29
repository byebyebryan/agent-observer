# Current local service: Service 4

Agent Observer a9 supplies **Service 4**, carrying **API 4 / snapshot 6**. The service
hosts read-only Codex observations on a local Unix socket. It has no Mesh dependency.
Begin with [your first local read](../getting-started.md) for package installation and
selection of an existing Codex home/runtime.

## Check the installed interface

```sh
agent-observer service api
```

This is a metadata-only command. It should report `serviceProtocol: 4`,
`observationApiVersion: 4` and `embeddedSnapshotVersion: 6`. Old protocol-1/2/3
guides describe historical artifacts and are not current setup instructions.

## Use an existing service

If your deployment already hosts Observer, use that endpoint. Its default is
`$XDG_RUNTIME_DIR/agent-observer/read.sock`, with `/run/user/<uid>` as the runtime
root fallback. Supply the source's exact configured host scope:

```sh
agent-observer service status --host-scope workstation
agent-observer service list --host-scope workstation
```

Replace `workstation` with the publisher's logical host identity. The client does
not select a different native home or relabel the publisher. For a different socket,
pass `--socket /absolute/path/read.sock` to each client command.

## Host your own foreground cache

If you need a new publisher, choose its home and private endpoint explicitly.
Do not launch a second collector merely to read an existing managed service.
The following starts a separately owned foreground Observer service; it reads
the existing native daemon and does not start that daemon.

In terminal A, activate the environment from the getting-started guide:

```sh
OBSERVER_HOST=workstation
OBSERVER_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
OBSERVER_DEMO_DIR=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/observer-demo.XXXXXX")
OBSERVER_SOCKET="$OBSERVER_DEMO_DIR/read.sock"
printf 'Observer socket: %s\n' "$OBSERVER_SOCKET"
agent-observer-service serve --host-scope "$OBSERVER_HOST" \
  --provider codex --codex-home "$OBSERVER_CODEX_HOME" \
  --socket "$OBSERVER_SOCKET"
```

Keep it in the foreground. `mktemp -d` gives this example a unique private parent;
the service uses a 0600 socket and its own singleton lock. Only Codex is accepted
by the current native service. Native hints and experimental delivery remain
unselected by this command.

In terminal B, activate the same package environment and copy the exact socket
path printed by terminal A. Set the host to the same value:

```sh
OBSERVER_HOST=workstation
OBSERVER_SOCKET=/absolute/path/printed/by/terminal-A/read.sock
agent-observer service status --host-scope "$OBSERVER_HOST" --socket "$OBSERVER_SOCKET"
agent-observer service list --host-scope "$OBSERVER_HOST" --socket "$OBSERVER_SOCKET"
agent-observer service snapshot --host-scope "$OBSERVER_HOST" --socket "$OBSERVER_SOCKET"
```

The example uses default runtime/history intervals of 20/60 seconds. Collection
and service availability have separate evidence; a reachable socket is not proof
that native collection is complete or current.

## Read and watch the cache

| Command/result | Meaning |
| --- | --- |
| `status` | Service state, source/component evidence and a cached snapshot when available |
| `list` | Human rows from one cached snapshot, with normal child/system filtering |
| `snapshot` | Full Service 4 envelope, including source/component receipts |
| `watch --human` | Human view with local expiry handling between received frames |
| `warming` with null snapshot | The source has not supplied a usable baseline; it is not complete-empty |
| Partial/stale/unavailable evidence | Preserve that limitation instead of inferring idle, removal or an empty roster |

For a finite watch, count five received frames:

```sh
agent-observer service watch --host-scope "$OBSERVER_HOST" \
  --socket "$OBSERVER_SOCKET" --human --count 5
```

`--count` counts frames, not seconds or native transitions. Use Ctrl-C to stop
your client sooner. Stopping a read/watch does not stop the publisher or provider.
For filtered JSON rows, `service list --json` preserves the service envelope;
`service snapshot` preserves the full cached snapshot.

## Stop only the publisher you started

Use Ctrl-C in terminal A. After that foreground process has exited, its socket is
removed but its private lock file can remain. For this unique demo directory only:

```sh
rm -- "$OBSERVER_SOCKET.lock"
rmdir "$OBSERVER_DEMO_DIR"
```

Do not remove the lock while a publisher still owns it, remove a managed endpoint,
or stop an unrelated service. Native conversations and their owning daemon continue.

## Utilities and optional networking

Local utilities use `service_client.frames` and `service_public.ReadCache` through
the [bounded public-read example](read-utilities.md). Clients preserve the
publisher identity, boot/time-domain binding and independent receipt expiry;
heartbeats and cached delivery never renew native facts.

Working-set cache creation is explicit through `--working-set-window-hours 72` on
an intentionally configured publisher. It is not required for the ordinary local
Service 4 recipe above. Mesh publication and remote routing have their own setup
and role selections; see [first-source setup](source-setup.md) for the complete
a11 producer-to-a14 reader path and [working-set reads](working-set.md) for
membership semantics.
