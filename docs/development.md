# Development

Use maintained `main`; [source orientation](source-orientation.md) explains
research worktrees and immutable artifact provenance. Python 3.11+ is required.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
./scripts/check
```

The source gate checks Markdown/local links, whitespace and synthetic behavior
without invoking providers. Use Ruff from the declared dev extra for lint:

```sh
ruff check agent_observer tests scripts/check scripts/candidate-artifact
```

## Optional paired networking

The core must remain importable without Mesh. Install the reviewed compatible
Mesh package separately for network checks, then require the pair explicitly:

```sh
./scripts/check --require-working-set-mesh
```

CI checks core-only and separately pinned compatibility pairs on Python 3.11
and 3.14. A skipped optional pair is not a paired pass. See
[operations](operations.md) for release sources and independently selected roles.

## Repository map

| Path | Contains |
| --- | --- |
| `agent_observer/` | Pure facades, passive adapters, engine, CLI, local service and optional networking |
| `agent_observer/contracts/` | Packaged schemas; current versions are reported by the CLI |
| `examples/` | Consumer examples using public interfaces |
| `tests/` | Synthetic contracts, dependency, lifecycle and regression checks |
| `scripts/` | Source, package, isolated native and operations gates |
| `docs/` | Maintained guides and references |
| `docs/history/` | Dated plans, old interfaces, investigations and experiments |
| `docs/evidence/` / `artifacts/` | Immutable acceptance inputs and artifact records |

## Independent qualification

Source tests do not establish native classification, installed bytes, managed
recovery or physical dashboard behavior. Follow the
[native validation workflow](observation-validation-workflow.md) for affected
hosts/homes. Use isolated owned resources and independent native evidence;
preserve ordinary providers, sessions, hooks and services.

## Documentation maintenance

Keep one current guide per topic and link it from [the index](README.md).
Current instructions must use the current protocol/provider scope. Put completed
plans and dated investigations under history, with their original acceptance
limits. Preserve evidence bytes and frozen contract inputs.

When a historical page moves, update ordinary links and retain a forwarding page
where immutable receipts or external clients need its old path. Forwarding pages
are compatibility links, not a place for new guidance. Check local paths and
heading fragments, and avoid copying host rollout ledgers into the README.
