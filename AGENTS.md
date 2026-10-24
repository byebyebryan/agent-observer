# Agent Observer development instructions

Read `README.md`, `docs/README.md`, `docs/reference/architecture.md` and `docs/maintenance/roadmap.md`.
The user request sets scope. Current main is Codex-only, read-only observation:
API 4, snapshot/watch 6, Service 4 and independent working-set v1 interfaces.
Observer writes, Claude observation and standalone active-only hosting are retired.
Working-set retains active membership and recent context; full diagnostics remain.

## Authority and invariants

- Follow `docs/reference/observation.md`. Keep pure reads, passive adapters,
  reusable engine, service hosting, optional Mesh delivery and consumer policy
  distinct. Core/local service import no Mesh or action/alert implementation.
- Native Codex daemon queries own runtime classification. Idle is running/waiting;
  parked requires the reviewed positive saved-thread `notLoaded` predicate.
  Missing membership, TUI/tmux/window/PID/path signals do not establish runtime.
- Preserve exact host/provider/namespace/native identity. Thread-tree roots and
  terminal attachment are separate metadata. A worker/client exit proves no
  session end. Activity clocks do not advance on polling or transport liveness.
- Keep unknown, partial, unsupported, stale and unavailable explicit. A cached
  heartbeat renews no native fact. Recompute expiry during silence and revoke
  current positives on gaps, disconnects and incarnation changes.
- Observe without starting/resuming/interrupting/renaming/deleting sessions or
  changing provider settings, hooks, services or ordinary processes. Native
  probes require isolated owned endpoints/resources and independent evidence.
- Retain bounded metadata/reasons only: no credentials, prompts, responses,
  tool contents, terminal captures or raw provider payloads in evidence.

## Compatibility and ownership

Provider compatibility follows capabilities/contracts, not version allowlists;
see `docs/reference/provider-compatibility.md`. Claude wire vocabulary and
synthetic fixtures do not enable an adapter. New providers need independent
native/contract review. OpenCode integration remains removed.

Agent Plus independently opens native Codex/Claude managers and has no Observer
or Tmux runtime dependency. Read-only utilities and hardware dashboards drive
current requirements. Consumers retain presentation, alert/action validation,
terminal lifetime and their own acceptance. Tmux retains independent pins,
factory and supported generic actions. Preserve directional host authority.

Delta-sync is deferred and dark; optional view-feed/prepared adoption requires
its own gate and does not select a deployment. No cleanup may revive retired
paths or infer new capabilities from historical plans.

## Validation and documentation

Use the workspace RTK wrapper. Run `./scripts/check` before committing docs;
paired work requires `--require-working-set-mesh` with the reviewed SDK, not a
skipped optional check. See `docs/maintenance/development.md` and the independent native
workflow in `docs/maintenance/validation.md`.

Preserve unrelated work, research branches, immutable release assets, frozen
schemas and contract inputs. Source, package, installed role, native,
consumer and physical acceptance are separate. Managed selections belong to
owner manifests, not source HEAD. Do not deploy as a side effect of docs work.

Only README/getting-started belong at the docs root. Use lowercase kebab-case
names and shallow guides/reference/maintenance folders. Keep one maintained
page per topic; cut obsolete plans, status notes and receipts instead of adding
archives or forwarding pages. Git retains previous records. Fixture inputs
belong beside tests. Run `scripts/check-docs` and the source gate before commit.
