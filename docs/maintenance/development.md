# Development

Use maintained `main` and Python 3.11+. Inspect `git status --short --branch`
and `git worktree list`; preserve research worktrees and unrelated edits.

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
| `docs/guides/` / `docs/reference/` | Current workflows and interface references |
| `tests/fixtures/` / `artifacts/` | Executable fixture inputs and artifact provenance |

## Independent qualification

Source tests do not establish native classification, installed bytes, managed
recovery or physical dashboard behavior. Follow the
[native validation workflow](validation.md) for affected
hosts/homes. Use isolated owned resources and independent native evidence;
preserve ordinary providers, sessions, hooks and services.

## Documentation maintenance

Keep only `README.md` and `getting-started.md` at the docs root. Use lowercase
kebab-case filenames in one shallow topic folder: `guides/` for workflows,
`reference/` for current interfaces, and `maintenance/` for development/operations.
Media belongs in `assets/`. Mesh's hash-locked `contract-freeze.md` is the sole
root exception; its original bytes remain normative input.

Update or consolidate the existing guide instead of adding a dated plan,
handoff or status page. Delete superseded notes; Git retains earlier revisions.
Do not add forwarding pages or copy old reports into the current docs tree.
Keep executable test data beside tests, not under docs. Record necessary release
provenance with an immutable Git/release link in the operations guide.

Run `scripts/check-docs` and the canonical source gate before committing. The
docs check enforces this layout and checks local links/heading fragments.
Package, native, managed, consumer and physical acceptance remain separate.
