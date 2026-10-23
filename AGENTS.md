# Agent Observer development instructions

## Scope and authority

- Current 0.7.0a9 source withdraws Observer writes and standalone active-only
  delivery; see docs/read-only-retirement.md. Shared projection semantics and
  working-set active membership remain. Earlier dated writer/active receipts
  below are historical, not current support requirements.

- The current user request sets scope. Read `README.md`, `docs/architecture.md`
  and `docs/roadmap.md` before implementation.
- Current consumers are read-only dashboards, diagnostics and agent utilities.
  Use `docs/utility-read-guide.md` for their public interface. Current Agent Plus
  independently opens native provider managers and has no Observer/Tmux runtime
  dependency. Native managers own conversation control. Claude native entry in
  Agent Plus does not imply Claude observation support here.
- `docs/observation-boundaries.md` defines the implemented observation boundary:
  model/passive adapters/reusable observation engine in core, service hosting
  and local read delivery, external meshing and attachment/action/alert clients.
  Native refresh hints do not grant runtime evidence or alert/action authority.
- `docs/api-v3-client-handoff.md` and
  `docs/evidence/2026-10-13-native-timing-rollout/REPORT.md` record the accepted
  a2/Mesh a16 collector/read/publisher selection on Snap and Starship: API 3,
  snapshot/watch 5, Service 3 and explicit Agent profile v2 through SDK 1.
  That dated selection is superseded by `docs/api-v4.md` and
  `docs/evidence/2026-10-13-system-classification/REPORT.md`: Observer 0.7.0a1 /
  Mesh a17, API 4, snapshot/watch 6, Service 4 and explicit Agent profile v3.
  The historical writer remains independent; a18 collection/a20 reads/Mesh a15
  are retained as a coordinated rollback tuple. The optional network component
  owns cached Service 4 acquisition and the lazy Agent factory; core/local
  service stay Mesh-free. Mesh owns copied envelopes/proofs/delivery. Preserve
  Tmux's independently selected factory, owner and controls. The later released
  a8/Mesh a24 working-set cohort and independent read/full/active/writer roles
  have their own receipts; effective host manifests determine current selection.
  Shared-launcher changes require both domain cached/proof/watch and paired
  collector/read/publisher rollback gates. Native timing does not provide exact
  phase entry or a receiving-device clock bridge.
- `docs/claude-retirement-plan.md` records the accepted a18 Claude retirement:
  Codex is the only implemented native provider, selected on Snap and Starship.
  Preserve provider-neutral core/read/Mesh interfaces;
  frozen wire provider vocabulary and synthetic data admission do not enable a
  native adapter. Claude collection, SDK/history, hints, service memo and
  Claude-specific notification/action tooling are removed. Ordinary Claude native sessions,
  history, settings, hooks and Agent View remain external and unchanged.
  Claude observation documents and released artifacts are historical evidence,
  not current support obligations. No compatibility collector is required.
  New providers require independent native/capability and contract review.
- The preceding Codex correction track is `docs/codex-daemon-authority-plan.md` and
  `docs/codex-daemon-authority-review.md`. Codex daemon queries own runtime
  classification; no TUI/tmux presence or attachment may decide running/parked
  or work phase. Clients own terminal lifetime/attachment. The original correction
  accepted Codex first; the later Claude gate is historical after retirement.
  Post-TUI-closure validation is deferred. Preserve provider-neutral
  interfaces, but do not retain compatibility converters, private saved-store
  fallback or terminal/job field scaffolding merely for the old contract.
  `docs/contract-and-clients-plan.md` records the preceding track. Keep
  observation/core/read-client passes separate from frontend work.
  The first-party New/Resume writer is retired in current source; native tools
  own entry and conversation control. Old writer artifacts and dated action
  proofs remain recovery/history inputs, with no current support obligation.
  Optional networking has its own implementation/native gates.
  Design documentation alone
  does not accept proposed states/fields/commands or authorize deployment.
- D0-D6 in `docs/codex-daemon-authority-plan.md` record the preceding correction
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
  exact-artifact bounds. The API 4/schema-v6/Service 4 command remains a prerelease contract.
- Validate native changes independently on affected hosts, using owned fixtures
  and the accepted observation-validation workflow. Claude native use remains
  external after retirement. Starship
  evidence does not establish Snap versions or runtime behavior.
- RLCD and reusable read utilities drive current requirements. The former
  Agent Plus consumer and WSNav are historical integration context, not gates.
- Codex is the only native observation adapter. The former required-second-
  provider condition is superseded by Claude retirement. Preserve pure
  provider-neutral contracts and separate usage context from host/home/session
  identity. Older native-runtime migration plans retain their dated boundary;
  they do not schedule a new Agent Plus migration or Claude adapter.
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
