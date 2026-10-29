# Agent Observer

Quick fleet checks, session investigation and a persistent terminal dashboard
for Codex. Agent Observer reads session state, coverage and freshness
while native Codex continues to own conversations. Its public read interfaces
also support diagnostics, hardware dashboards and agent utilities.

[Project showcase](https://dev.byebyebryan.com/fleet-plus/projects/agent-observer/) ·
[CLI setup](docs/guides/sessions-cli.md) · [Dashboard setup](docs/guides/dashboard.md) ·
[Documentation](docs/README.md)

## Watch your agents

Requires Linux and Python 3.11+. Install the
[published reader pair](docs/guides/sessions-cli.md#prerequisites), then
[configure sources once](docs/guides/sessions-cli.md#configure-sources-once)
in your private `terminal.toml`. The reader uses existing working-set
publishers/bridges; their sockets differ from the collector's Service 4 socket.
If those endpoints are not hosted yet, follow the [working-set guide](docs/guides/working-set.md).

With sources configured, check setup and coverage:

```sh
agent-observer sessions sources --configured
agent-observer sessions sources
```

The first command validates configuration without connecting. The second reads
source health. Missing configuration or unavailable sources remain explicit.

| Workflow | Command |
| --- | --- |
| Quick overview, up to ten rows | `agent-observer` |
| All matching sessions and full IDs | `agent-observer sessions list` |
| Search admitted session metadata | `agent-observer sessions list --query renderer` |
| Inspect one exact session | `agent-observer sessions show FULL_THREAD_ID --host HOST --home HOME` |
| Keep the dashboard open | `agent-observer dashboard` |

The [dashboard](docs/guides/dashboard.md) needs the optional dashboard dependencies
and reuses the CLI configuration. It provides search, filters, source health and
details; press `?` for keys and `q` to quit. Use
`agent-observer sessions list --format json` for the versioned scripting interface.
Installing or opening a reader does not start providers, collectors or publishers,
control conversations, or add host routes.

## Diagnostics and reusable reads

| Need | Documentation |
| --- | --- |
| Inspect the local runtime | [First local read](docs/getting-started.md) |
| Share one collector's cached state | [Local Service 4](docs/guides/local-service.md) |
| Read active sessions and recent context across configured hosts | [Working-set](docs/guides/working-set.md) |
| Inspect a fuller cached inventory | [Full Mesh reads](docs/guides/full-mesh-reads.md) |
| Build a read-only utility | [Utility example](docs/guides/read-utilities.md) and [API reference](docs/reference/read-api.md) |

For an explicit native diagnostic read, use the
[local core installation and home-selection guide](docs/getting-started.md).
Commands such as `api` and `snapshot` remain separate from the configured cached
sessions CLI; direct reads query an existing daemon without starting one.

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

[0.7.0a14](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a14)
adds dashboard search over current cached repository roots, shared Git directories
and relative paths. The optional dashboard retains readable workspace details,
source health, filters and keyboard navigation from a13.
The finite sessions CLI and terminal JSON interface 1 remain compatible, along
with read-only API 4, snapshot/watch 6 and Service 4.
Working-set uses its own version-1 interfaces and paired Mesh a25 support.
Use [operations](docs/maintenance/operations.md) for release provenance and managed selections.
Installing source does not change deployed pins or accept a dashboard/device.

Current guides are organized in the [documentation index](docs/README.md).
