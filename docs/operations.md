# Releases and operation

This guide points to release and deployment authority. It does not select or
upgrade a host. First-time local setup is in [getting started](getting-started.md)
and [Service 4](local-service.md).

## Published interfaces

The [0.7.0a9 prerelease](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a9)
publishes the read-only core: API 4, snapshot/watch 6, Service 4 and version-1
working-set interfaces. The collector/working-set pair uses Mesh 0.1.0a25.
The [public-delivery closeout](https://github.com/byebyebryan/mesh-plus/blob/b306d44c329c6289781cc4db14f939ed2a4d20c2/docs/evidence/2026-10-23-public-delivery/README.md)
binds exact release assets, hashes, provenance and scoped managed delivery.

The [retirement checkpoint](read-only-retirement.md) records removal of writes
and standalone active-only paths. Frozen schemas, old release assets and dated
receipts retain their historical role without advertising current support.

## Managed selections

The deployment owner maintains
[agent-observer.json](https://github.com/byebyebryan/dotfiles/blob/main/deployments/agent-observer.json).
Collector, local read CLI, full publisher, working-set publisher, dashboard,
Tmux and SSH authority are independently selected roles. A newer source head
does not replace an installed wheel or accept a consumer migration.

The public-delivery receipt records Carbon working-set membership as partial
and unresolved. It does not prove complete-fleet membership. Consult a later
owning native/coverage receipt before upgrading that claim.

## Changes and recovery

Use reviewed owner operations and exact artifacts for the role being changed.
Inspect scoped managed diffs, retain paired rollback inputs and verify installed
bytes/readiness/recovery independently. Preserve unrelated native work and
directional routes. Package installation, service hosting, collector selection
and device adoption are separate steps.

[Historical delivery records](history/README.md#delivery) and
[dated evidence](evidence/) retain old tuple-specific commands and failures.
Use them for their recorded checkpoint rather than combining their commands
into a current installation recipe.
