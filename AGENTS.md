# Agent Observer development instructions

## Scope and authority

- The current user request sets scope. Read `README.md`, `docs/architecture.md`
  and `docs/roadmap.md` before implementation.
- The active development track is `docs/contract-and-clients-plan.md` and its
  review. Keep observation/core/read-client passes separate from frontend work.
  The proposed first-party New/Resume write client and optional networking
  component may share this repository, but are separate from passive core and
  have independent implementation/native gates. Design documentation alone
  does not accept proposed states/fields/commands or authorize deployment.
- `docs/contract-and-clients-execution-plan.md` defines the unattended sequence.
  G2 independently accepts the Observer artifact/read/write/native subset
  before any Agent Plus implementation; optional networking has its own gate.
  Producer defects found by a consumer reopen a separate Observer checkpoint,
  not a simultaneous producer/frontend edit cycle.
- The existing native-runtime migration pilot accepts only its documented
  exact-artifact subset; new versions, topologies and capabilities require
  independent proof. The schema-v1 command remains a prerelease contract.
- Continue preflight and spike work on Snap in `~/code/agent-observer`. Claude
  is available only there according to the user. Reinspect both providers on
  Snap; Starship evidence does not establish Snap versions or runtime behavior.
- RLCD and Agent Plus drive the initial requirements. WSNav is historical
  evidence and a possible future consumer; its integration is not a gate.
- Agent Plus meshes sessions across providers and hosts. Codex leads delivery;
  Claude Code remains a required second provider for the completed migration.
  Preserve provider-independent contracts and separate usage context from
  provider/host identity. See `docs/native-runtime-migration-plan.md` for the
  delivery boundaries and `docs/design-review.md` for pending proof decisions.
- OpenCode integration is deprecated and removed from Agent Plus at migration
  cutover. Do not add an OpenCode adapter or compatibility fallback to this work.
- Inspect actual installed versions and runtime topology. Existing projects,
  old spikes, and newer online docs are references, not current runtime proof.

## Observation invariants

- Preserve native provider workflows. Observation must not resume, start,
  interrupt, approve, deny, rename or delete a provider session.
- Preserve ordinary hooks, compatibility settings, processes and services.
  Use isolated, disposable configuration/endpoints for planned live proofs;
  establish isolation before anything that may auto-start a daemon.
- Keep saved history, logical session identity, worker identity and terminal
  attachment distinct. Worker/client exit alone does not establish session end.
- Treat hooks and process observations as evidence, not action authority.
- Retain bounded metadata and reason codes only. Never persist credentials,
  prompts, assistant responses, tool arguments/output, terminal captures or
  raw provider payloads in repository evidence.
- Keep identity ambiguity, unsupported capabilities, missed observations and
  stale state explicit. Do not guess from cwd, title, PID or file modification
  time, or label unavailable observations as idle.
- A liveness refresh must not make old work-state evidence appear fresh.
- Consumers retain action validation, runtime ownership and presentation policy.

## Validation and delivery

- Use the linked spike plan and report coverage per provider, version and
  topology. Standalone success does not establish daemon support.
- Distinguish static/schema, synthetic, controlled-server and native live
  evidence. Label pending or unsupported cases instead of promoting them.
- Run `./scripts/check` before committing or publishing documentation changes.
  Add appropriate runtime checks when code is introduced.
- Preserve unrelated changes in this and consumer repositories. Consumer
  migrations, installation and provider policy changes use their own scoped
  delivery gates and must not be inferred from passive source acceptance.
