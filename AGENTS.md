# Agent Observer development instructions

## Scope and authority

- The current user request sets scope. Read `README.md`, `docs/architecture.md`
  and `docs/roadmap.md` before implementation.
- `docs/observation-boundaries.md` defines the next boundary-hardening pass:
  model/passive adapters/reusable observation engine in core, service hosting
  and local read delivery, external meshing and attachment/action/alert clients.
  Native refresh hints do not grant runtime evidence or alert/action authority.
- `docs/claude-observation-execution.md` and its
  `docs/evidence/2026-10-08-claude-observation/REPORT.md` accept the following
  Claude observation checkpoint on Snap. Stable authenticated provider registration
  and status metadata supply running/phase; terminal retained jobs have a bounded
  positive parked predicate. Saved-only absence and foreground exit remain
  unknown. The earlier Codex-only correction below is historical scope, not a
  prohibition on this independently accepted passive adapter. Claude actions,
  attachment and generic background lifetime remain separate gates.
- The active correction track is `docs/codex-daemon-authority-plan.md` and
  `docs/codex-daemon-authority-review.md`. Codex daemon queries own runtime
  classification; no TUI/tmux presence or attachment may decide running/parked
  or work phase. Clients own terminal lifetime/attachment. Codex-only acceptance
  leads this breaking correction; Claude support is deferred to the next gate
  and may break. Post-TUI-closure validation is deferred. Preserve provider-neutral
  interfaces, but do not retain compatibility converters, private saved-store
  fallback or terminal/job field scaffolding merely for the old contract.
  `docs/contract-and-clients-plan.md` records the preceding track. Keep
  observation/core/read-client passes separate from frontend work.
  The proposed first-party New/Resume write client and optional networking
  component may share this repository, but are separate from passive core and
  have independent implementation/native gates. Design documentation alone
  does not accept proposed states/fields/commands or authorize deployment.
- D0-D6 in `docs/codex-daemon-authority-plan.md` define the next correction
  sequence. Its D4 gate independently accepts the Codex read/service artifact;
  write/native delivery and Claude have separate following gates. The preceding
  `docs/contract-and-clients-execution-plan.md` records the earlier sequence.
  Its G2 independently accepted the Observer artifact/read/write/native subset
  before any Agent Plus implementation; optional networking has its own gate.
  Producer defects found by a consumer reopen a separate Observer checkpoint,
  not a simultaneous producer/frontend edit cycle.
- Provider support follows the required protocol/metadata/CLI contracts and
  observed capabilities, not provider version or executable-hash allowlists.
  Follow `docs/provider-contract-compatibility-plan.md`. Versions/hashes remain
  diagnostics, native-test provenance and executable/incarnation-change guards.
  Routine upgrades preserving required contracts do not require release
  registration; changed contract semantics, topologies or new capabilities need
  focused independent proof. Existing pilot evidence retains its historical
  exact-artifact bounds. The API 2/schema-v4 command remains a prerelease contract.
- Continue preflight and spike work on Snap in `~/code/agent-observer` and
  independently validate Codex on Starship. Claude is available only on Snap
  according to the user; reinspect it at its next provider checkpoint. Starship
  evidence does not establish Snap versions or runtime behavior.
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
- A current saved-thread `notLoaded` daemon response is the Codex parked
  predicate; missing loaded membership or unavailable reads are not. `idle` is
  running/waiting. Codex thread ID is the row/action identity; its session-tree
  root ID is separate metadata. Prove distinct-ID native entry independently.
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

- Follow `docs/observation-validation-workflow.md`: compare the installed public
  CLI with independent native evidence from ordinary active sessions or isolated
  test sessions. Report exact identity/state/age comparisons, coverage limits
  and unresolved classifications; another Observer result is not independent
  native proof. Keep producer acceptance separate from frontend validation.
- Use the linked spike plan and report coverage per provider, version and
  topology. Standalone success does not establish daemon support.
- Distinguish static/schema, synthetic, controlled-server and native live
  evidence. Label pending or unsupported cases instead of promoting them.
- Run `./scripts/check` before committing or publishing documentation changes.
  Add appropriate runtime checks when code is introduced.
- Preserve unrelated changes in this and consumer repositories. Consumer
  migrations, installation and provider policy changes use their own scoped
  delivery gates and must not be inferred from passive source acceptance.
