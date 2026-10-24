# Agent Observer

Read-only Codex session observation for dashboards, diagnostics and agent utilities.
Keep native Codex in charge of conversations; consume identities, runtime/activity
facts, coverage and independently expiring evidence through public read interfaces.

[Explore Agent Observer](https://dev.byebyebryan.com/fleet-plus/projects/agent-observer/) ·
[Documentation](docs/README.md) · [Build a utility](docs/utility-read-guide.md)

## What you can build

- A hardware or desktop dashboard showing useful conversations across machines.
- Bounded status and diagnostic tools using cached local or working-set reads.
- Read-only utilities that preserve unknown, partial, stale and unavailable states.

Codex is the only implemented native observation adapter. Claude monitoring is
[retired](docs/claude-retirement-plan.md). Agent Plus independently opens native
Codex/Claude TUIs; it has no Observer or Tmux runtime dependency.

## Current release

[**0.7.0a9**](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a9)
is the published read-only prerelease. It retires Observer writes and standalone
active-only delivery, retains full diagnostics and working-set reads, and adds
`agent-observer working-set list/watch` for bounded cached inspection.
See the [CLI and retirement guide](docs/read-only-retirement.md) and
[public delivery closeout](https://github.com/byebyebryan/mesh-plus/blob/b306d44c329c6289781cc4db14f939ed2a4d20c2/docs/evidence/2026-10-23-public-delivery/README.md).

The collector/working-set pair uses Observer a9 / Mesh a25. Dashboards, full
publishers, Tmux and SSH authority retain independently reviewed selections.
The [deployment owner](https://github.com/byebyebryan/dotfiles/blob/main/deployments/agent-observer.json)
records managed pins; a source or documentation update does not upgrade them.
Carbon's last delivery check reported partial working-set membership, not a
complete empty roster. Its cause remains unresolved in that closeout.

## Choose a read path

| Path | Use it for |
| --- | --- |
| Direct host snapshot | Explicit current inspection against the existing owning daemon |
| Local cached Service 4 | Multiple read-only clients of one independently running collector/service |
| Working-set through optional Mesh | Active membership plus recent context over configured local/fleet routes |
| Full diagnostic feed | Explicit fuller inventories and diagnostic consumers |

The core and local service import no Mesh. Optional Mesh delivers already
published state; it does not collect from a provider. A cached copy or heartbeat
never renews native evidence. Missing/expired membership does not establish idle,
parked or removed. See [API 4](docs/api-v4.md) and [observation boundaries](docs/observation-boundaries.md).

## Start from a checkout

Python 3.11+ is required. Install in a dedicated environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install .
agent-observer api
```

For an explicit read on the provider's host, with the existing Codex daemon:

```sh
agent-observer snapshot --host-scope workstation --provider codex
```

Replace `workstation` with your configured logical host identity. Observation
never starts a missing native daemon. Cached reads require an explicitly hosted
service; fleet/working-set reads also require the matching optional Mesh package,
publisher and configured directional routes. Follow the [read guides](docs/README.md).

## Develop and extend

```sh
python -m pip install '.[dev]'
./scripts/check
ruff check agent_observer tests scripts/check scripts/candidate-artifact
```

The source gate checks documentation and synthetic behavior without invoking
providers. CI separately checks core-only, legacy Mesh a23 and hash-pinned a24/a25
working-set pairs on Python 3.11 and 3.14. Paired checks require
`./scripts/check --require-working-set-mesh`; they cannot pass by skipping the pair.
Native observation, resource, managed deployment and physical dashboard acceptance
have their own evidence. See [validation](docs/observation-validation-workflow.md).

## Read further

- [Public read interfaces and examples](docs/README.md).
- [Architecture](docs/architecture.md), [roadmap](docs/roadmap.md) and [provider compatibility](docs/provider-contract-compatibility-plan.md).
- [Working-set checkpoint](docs/working-set-producer-checkpoint.md) and [RLCD consumer handoff](docs/rlcd-prepared-read-handoff.md).
- [Source checkout orientation](docs/source-orientation.md).
- [Historical README checkpoints](docs/readme-history.md), retaining earlier native,
  performance, writer and active-feed records in their dated scope.

Delta synchronization remains a [deferred dark feature](docs/delta-sync-dark-feature.md).
Ordinary delivery retains complete replacements; view-feed adoption remains
independent and unselected. Related [Codex Plus](https://github.com/byebyebryan/codex-plus),
[Agent Bookkeeper](https://github.com/byebyebryan/agent-bookkeeper) and
[Agent Historian](https://github.com/byebyebryan/agent-historian) have separate purposes.
