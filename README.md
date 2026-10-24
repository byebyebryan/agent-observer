# Agent Observer

Read-only Codex session state for dashboards, diagnostics and agent utilities.
Observe exact identities, runtime/activity, coverage and freshness while native
Codex continues to own conversations.

[Project showcase](https://dev.byebyebryan.com/fleet-plus/projects/agent-observer/) ·
[Get started](docs/getting-started.md) · [Documentation](docs/README.md)

## Start locally

Requires Linux, Python 3.11+ and an existing native Codex runtime. From a checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
agent-observer api
agent-observer snapshot --host-scope workstation --provider codex
```

Replace `workstation` with your logical host identity. An explicit direct read
queries the existing daemon; it never starts a missing daemon or controls a
conversation. The [first-read guide](docs/getting-started.md) includes a pinned
published-package installation, home selection and output explanation.

## Choose an interface

| Need | Documentation |
| --- | --- |
| Inspect the local runtime | [First local read](docs/getting-started.md) |
| Share one collector's cached state | [Local Service 4](docs/guides/local-service.md) |
| Read active sessions and recent context across configured hosts | [Working-set](docs/guides/working-set.md) |
| Inspect a fuller cached inventory | [Full Mesh reads](docs/guides/full-mesh-reads.md) |
| Build a read-only utility | [Utility example](docs/guides/read-utilities.md) and [API reference](docs/reference/read-api.md) |

Core and local service have no Mesh dependency. Optional Mesh carries published
facts over explicitly configured directional routes. A heartbeat or cached copy
cannot make expired native facts current. Unknown and partial coverage remain
visible; missing membership does not prove idle, parked or removed.

Codex is the only native observation adapter. Observer writes, Claude monitoring
and standalone active-only hosting are retired. Agent Plus independently opens
native Codex/Claude TUIs and has no Observer runtime dependency.

## Develop

```sh
python -m pip install '.[dev]'
./scripts/check
```

See [development](docs/maintenance/development.md) for the paired Mesh gate, repository map
and independent native/package checks. Current architecture and future work are
in [architecture](docs/reference/architecture.md) and [roadmap](docs/maintenance/roadmap.md).

## Releases and operation

[0.7.0a10](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a10)
is the published read-only prerelease: API 4, snapshot/watch 6 and Service 4.
Working-set uses its own version-1 interfaces and paired Mesh a25 support.
Use [operations](docs/maintenance/operations.md) for release provenance and managed selections.
Installing source does not change deployed pins or accept a dashboard/device.

Current guides are organized in the [documentation index](docs/README.md).
