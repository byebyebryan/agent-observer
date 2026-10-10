# Agent Observer

Shared host-side discovery and state observation for Codex and Claude Code
sessions. Agent Observer gives consumers a consistent view of session identity,
runtime state, and observation freshness while preserving native workflows.

The initial consumer projects are
[ESP32 RLCD](https://github.com/byebyebryan/esp32-rlcd) and
[Agent Plus](https://github.com/byebyebryan/rofi-agent-plus).
[WSNav](https://github.com/byebyebryan/wsnav) contributes historical lifecycle
work and may become a consumer later; it is currently inactive and may be
simplified.

## Status

The a12 [Mesh read client](docs/mesh-read-client.md) and Mesh a4 bridge are
[accepted and selected](docs/evidence/2026-10-09-mesh-integration/REPORT.md)
on Snap and Starship. Local/fleet cached pull and push, native comparisons,
bridge restart and scoped rollback/reselection pass. Networking stays in Mesh
Plus; core and the host-local collection service remain independent.

The observation checkpoint is [a11 finite runtime-only retention](docs/evidence/2026-10-09-runtime-only-retention/REPORT.md).
Normal collection/services remain a11; the read CLI independently selects a12.
Codex is accepted on both hosts; Claude interactive discovery
and monitoring are accepted on Snap. The reusable core owns reconciliation and
evidence, passive adapters own native reads, and the service owns helper lifetime
and cached pull/push. The normal writer remains a16 independently.

[API 2](docs/api-v2.md), snapshot/watch wire 4 and service protocol 2 are unchanged.
The [client handoff](docs/api-v2-client-handoff.md) supplies direct/cached commands,
consumer obligations and current limits. Read-client development can proceed
independently. Frontend migration, actions/attachment, networking and user-facing
alerts remain separate.
The [Claude wrap-up](docs/claude-observation-wrap-up.md) closes the interactive
observation pass and records independent follow-ups.

The active [state-push design](docs/state-push-design.md) and
[review/validation](docs/evidence/2026-10-09-state-push-refinement/REPORT.md)
refine existing complete-view discovery/monitoring delivery. Initial views,
source expiry and reconnect/gap/resync establish current state without a new
event protocol. [Following work](docs/state-push-execution-plan.md) covers optional
read-cache ergonomics and conformance. The preceding
[native occurrence-event research](docs/state-and-events-design.md) is retained,
but notification normalization, hooks, event replay and Kitty/D-Bus integration
are deferred. The 349 handoff is one client's request; device projections and
alert policy remain external. Networking is in the separate mesh-plus thread.

Codex queries its owning daemon for running/parked independently of TUI/tmux.
Claude authenticates provider-owned interactive registrations and status.
Healthy bounded scans with positive saved identity and no live matching
incarnation or relevant unresolved conflict report parked under the accepted
native-registration assumption. Normal exit, forced kill, exact Resume, same-process
UUID changes, duplicate live contexts and Observer cold start have native proof.
Agent View on/off both pass; ordinary provider settings remain unchanged.

A live Claude session with failed/missing registration can be missed or falsely
parked; runtime coverage remains partial with explicit limitations. Background
runtime and attachment are unsupported; native job metadata only vetoes unsafe
negatives. Two old stopped recap background histories remain unknown and are
outside the user's forward interactive workflow. The
setup-only SDK omission now has a saved row, while its cwd, kind and conversation
age remain unavailable. Generic dialogs, excluded nested child history and
Claude turn outcomes remain unproved.

Installed native comparisons match all six ordinary Claude running contexts,
35 saved UUIDs and 33 known conversation clocks on Snap within the documented
metadata gap. All 89 Snap and 354 Starship Codex rows agree. Direct reads,
cached pulls and pushed views pass independently. Age follows native conversation
activity; leases, source faults, ambiguity and gaps remain explicit.
The [shared-core retention pass](docs/runtime-only-retention-follow-up.md)
retires disappeared unsaved rows at their original runtime lease: 90 seconds on
Snap and 60 on Starship; sampled direct watch uses 60 seconds and applies expiry
at the next sample. Repeated partial reads do not extend retention. Current rows
and positive saved history survive, with original conversation age. Retirement
omits observation memory and establishes no native lifecycle or action authority.

The preceding [a9 interactive checkpoint](docs/evidence/2026-10-08-claude-interactive-observer/REPORT.md),
[a8 Claude checkpoint](docs/evidence/2026-10-08-claude-observation/REPORT.md)
and [a6 Codex gap closure](docs/evidence/2026-10-08-codex-observation-gaps/REPORT.md)
retain their historical artifact bounds. Twenty-one older Starship kinds are an
accepted forward-looking limit. Physical sleep/wake and Codex post-TUI-closure
lifetime remain deferred. No ordinary session restart is required for observation.

## Previous checkpoints

The [shared observation service design](docs/shared-observation-service-plan.md)
captures first-class pull/push and one local collector for multiple clients.
The [deep review](docs/shared-observation-service-review.md) includes passive
Snap/Starship cost measurements and controlled delivery/freshness exercises.
The [execution plan](docs/shared-observation-service-execution-plan.md) keeps
implementation, native service proof and downstream migrations separate.
The shared service and explicit cached read client are now implemented as a
separate prerelease candidate. Read the [client guide](docs/shared-observation-service-client.md)
and [implementation status](docs/shared-observation-service-status.md) for exact
acceptance. The [producer handoff](docs/shared-observation-service-handoff.md)
records the explicit candidate, client obligations and separate rollout gates.
The [large implementation-loop plan](docs/shared-observation-service-batch-plan.md)
sets the current checkpoints and unattended producer validation.

The [operational baseline pass](docs/observer-operations-execution.md) adds
startup-only service workspace configuration and independently gates an
Observer-only managed CLI/user-service rollout. Its
[operational evidence](docs/evidence/2026-10-07-observer-operations/REPORT.md) compares
the installed selected and service-capable candidates against native metadata;
that pass selected a7 read/write/service commands, and the Observer user unit
was enabled on Snap and Starship. At that a7 gate, restart/crash/rollback/
reselection and both 30-minute normal-unit reader/resource checks passed. The report records
remaining native entry, foreground attach and physical wake limits.

The [native delivery](docs/evidence/2026-10-07-native-delivery/REPORT.md) selected
`0.4.0a15` on Snap and Starship with passive native wakeups and periodic
reconciliation. Snap supports Codex/Claude; Starship supports Codex. The
[a15 receipt](docs/evidence/2026-10-07-native-delivery/a15-image-memo-and-host-cost.json)
records supported state, question, age, rename, reconnect and listener-lifetime
proof. Matched incremental CPU meets the one-point target (+0.946/+0.153 points).
The user relaxed the 64 MiB aggregate RSS target to a review threshold; absolute
and added RSS remain reported, with idle/collection PSS and stability measurements
in the [managed rollout receipt](docs/evidence/2026-10-07-native-delivery/a15-managed-rollout.json).
That separate operational gate records both-host restart/crash/rollback/reselection
and normal-unit reader/resource checks. Earlier failed candidates retain their
original evidence in the delivery report. Physical suspend/wake, provider entry
repair, notifications and downstream migrations remain separate.

The [daily-use repair pass](docs/evidence/2026-10-07-daily-use-gap/REPORT.md)
selected `0.4.0a16` on both hosts with the same API and hint/reconciliation
boundary. It repairs Claude runtime-only retention, classifies current saved
Codex roots from passive detail and improves human age/runtime and missing-cwd
diagnostics. Independent direct/cache comparisons match all nine ordinary active
contexts. Saved lifecycle remains unknown where native evidence cannot establish
parked. Tmux Plus development and Agent Plus migration remain separate.

The [API v1 contract](docs/api-v1.md) is independently accepted against
`0.3.0a2`, observation snapshot/watch wire 3 and write wire 1. The
[packaged/native report](docs/evidence/2026-10-06-stable-api/REPORT.md) records
independent CLI/native comparisons on Snap/Starship, isolated New/Resume,
blocked/parked/recovery cases, bounded watch and strict consumer conformance.
Required native contracts replace daily provider release/hash allowlists;
actual executable identity and changed-context action guards remain enforced.

The immutable a2 candidate is installed separately on both hosts. At the
following daily-use checkpoint Observer links selected a16/wire 3. It is the retained
rollback artifact; the current read/service selection uses API 2. Agent Plus
still uses its separate frozen reader and requires its own migration. Use the
[API 2 client handoff](docs/api-v2-client-handoff.md) for new read clients;
frontend and notification rollout have independent gates. No ordinary provider
restart is needed for passive observation.

The [earlier discovery/monitoring review](docs/discovery-monitoring-contract-review.md)
records eight producer findings; the stable API execution closes their scoped
source/package/native gates. Older exact-artifact reports below retain their
original bounds and do not define daily provider support.

The [stopped-runtime checkpoint](docs/evidence/2026-10-05-stopped-runtime/REPORT.md)
accepts and selects `0.2.0a11` on Snap and Starship. Exact-image Claude retained
done/stopped idle jobs report parked when complete stable inventories prove no
live bound worker. At that acceptance both ordinary recap sessions reported parked
with their conversation ages preserved. Installed native stop/resume, independent
ordinary CLI comparisons and the frozen reader's watch/schema checks passed.
That selection changed only managed Observer read/write entrypoints; no frontend
work or session restart accompanied it. Saved-only absence and unsupported
contexts remain unknown.

The [monitoring checkpoint](docs/evidence/2026-10-05-monitoring/REPORT.md)
independently accepts the `0.2.0a10` candidate on Snap and Starship. It adds
exact-image Codex question waits and explicit turn outcomes, proved current
Claude readiness and background question predicates, and an optional bounded
Claude history census. Installed CLI/native comparisons, isolated New/Resume,
held input, recovery and the frozen consumer reader pass within the recorded
artifact bounds. That gate installed the candidate separately while ordinary
entrypoints remained on `0.2.0a9`; a11 includes those accepted predicates.
Frontend work and production selection have separate gates.

The [evaluation repair pass](docs/evidence/2026-10-05-evaluation-repair/REPORT.md)
independently accepted and selected `agent-observer 0.2.0a9` before this update.
It supports the exact current Codex `0.160.1` managed image separately from the
installed `0.160.0` CLI, preserves independently proved saved metadata through
runtime failures, and accepts current completion-only activity clocks. Ordinary
Claude conversations classify from explicit non-sidechain evidence. CLI age,
ordering, actual runtime diagnostics and finite unsupported phase reasons are
validated against independent native references. Installed New/Resume, held
approval, partial discovery and watch/recovery pass within exact artifact bounds.
Agent Plus remains `0.14.0a1` with its frozen `0.2.0a3` reader dependency; its
reported silent Resume and graphical acceptance require a separate consumer pass.
No provider configuration change or session restart is required by this update.

The preceding [CLI/native evaluation](docs/evidence/2026-10-05-cli-native-evaluation/REPORT.md)
found nine producer gaps. The [repair execution](docs/evaluation-repair-execution.md)
records a fix or bounded unsupported outcome for each before compatible selection.
Blank Claude background contexts, untyped blocked jobs, ephemeral helper ancestry,
foreground questions, older worker predicates and older Codex TUI binding remain
explicit limits. Recorded cwd and project/worktree context are preserved with provenance.
Further frontend acceptance remains a separate development checkpoint.

The initial regular contract/client execution loop independently accepted
`agent-observer 0.2.0a3`: the [public v2 observation/read contract](docs/public-contract-v2.md), including
strict schemas, list/show/doctor, local Git/workspace enrichment and sampled
watch. The [execution record](docs/contract-clients-execution-status.md) separates
source checks from [independent packaged/native acceptance](docs/evidence/2026-10-04-contract-clients/REPORT.md).
The separate [write client](docs/write-client-contract.md) supports validated
New/Resume and native TTY entry. That v2 provisional pilot was selected on
Snap and Starship after independent operational acceptance and real Tmux/SSH
consumer proofs; see the [operational record](docs/operational-execution-status.md).
Agent Plus subsequently passed its own bounded public-contract/native-entry
consumer gate against that unchanged Observer artifact. The [current handoff](docs/contract-clients-handoff.md)
records the selected producer, compatible consumer and remaining acceptance gates.

The [contract and first-party clients track](docs/contract-and-clients-plan.md) provides
a passive host-local core, read and New/Resume write clients, and an optional
separate networking component in this repository. Contract/core work and
frontend migrations have independent gates. The [design review](docs/contract-and-clients-review.md)
distinguishes this direction from the preceding pilot below. The public v2
contract was selected at the earlier pilot gate; API v1 wire 3 now supersedes it on those hosts; other consumers migrate separately.

The preceding pilot was `agent-observer 0.1.0a5`, written in Python
with no runtime dependencies. Its host-local JSON
[contract candidate](docs/snapshot-contract.md) separates logical identity,
work, presence, attachment, source health and coverage.

Native isolated proofs on Snap accept Codex 0.160.0 managed-runtime inventories,
working/settled/approval observations, exact saved resume, work after viewer
exit and daemon recovery. Claude Code 2.1.287 accepts direct metadata discovery,
verified workers, background work/completion/approval and work after viewer
exit. General input, interrupted/error transitions and current conversation
binding remain explicitly unsupported. Observer and Agent Plus candidates are
installed on Snap and Starship; ordinary runtime and bounded routed native
action pilots are accepted. Graphical UI, sleep/wake and published release
acceptance remain separate gates.

The [native report](docs/evidence/2026-10-03-native-runtime/REPORT.md),
[execution status](docs/execution-status.md) and
[roadmap](docs/roadmap.md) distinguish those gates from source and fixture tests.
The [reviewed migration plan](docs/native-runtime-migration-plan.md) defines
rollout. The [execution handoff](docs/execution-handoff.md) records the current
coordinator's final deliberate reopen route and remaining checks.

The historical Claude pilot uses the optional pinned `claude-history` extra. It
builds `claude-agent-sdk==0.2.163` from its official source distribution with
`--no-binary=claude-agent-sdk` to avoid the wheel's bundled Claude executable.
The SDK and its Python dependencies belong in Observer's own environment;
Codex-only hosts need no SDK. Observer projects explicit saved titles, UUIDs,
cwd and creation metadata through a bounded passive helper. It does not export
SDK summaries or conversation contents.

The retained a16 [API v1 candidate](docs/api-v1.md) keeps its historical
JSON/CLI and pure Python surface. Current a11 read clients use
[API 2](docs/api-v2.md). `agent-observer api` reports the invoked artifact's versions.

## Command candidate

```sh
python -m pip install .
agent-observer snapshot --host-scope snap
agent-observer snapshot --host-scope starship --provider codex
```

Run Observer on the selected host. `--host-scope` is supplied by the consumer's
Host Mesh authority. It does not authenticate a host. Provider configuration
roots can be supplied explicitly. The Codex collector reads the existing
owning daemon without private saved-store fallback. It never starts a missing
daemon or invokes a provider action. See the [API 2 handoff](docs/api-v2-client-handoff.md)
for direct and cached commands against the accepted candidate and normal service.

## Scope

The [observation ownership specification](docs/observation-boundaries.md)
defines core/model/adapter/engine, local service, optional mesh and read-client
boundaries. The reusable core and passive adapter hardening are implemented.
Terminal/window matching, attachment/actions and user-facing alert delivery
have separate client ownership.

Agent Observer owns provider discovery, bounded metadata, runtime observations,
source/version capability handling, and reconciliation of stale or conflicting
evidence. Its interface should work across consumer languages.

Agent Plus uses these observations to mesh sessions across providers and hosts.
Provider independence is an architectural requirement. Codex's delivery priority
reflects usage frequency; the completed migration includes strong support for
both Codex and Claude Code.

Saved conversations, logical sessions, runtime workers, and attached terminal
clients have separate identities and lifetimes. Session inventory is separate
from live work state; observation health is separate from both. Unsupported
or ambiguous evidence remains explicit.

Consumers own their presentation and actions. RLCD owns dashboard selection
and device transport; Agent Plus owns picker, host routing and terminal actions.
WSNav's current private-tmux and workstream model does not constrain this
component. Resume, launch, focus, approval, interruption and session deletion
are outside the initial observation API.

The v2 candidate extracts reusable New/Resume behavior into a first-party write
client rather than adding actions to observation. The read client consumes the
same public model as other consumers. Optional networking wraps local interfaces
and reuses existing Host Mesh routing; it is not required by the core/read gate.

Codex is the primary provider: it leads the first complete implementation and
validation across the user's machines. Claude Code is the secondary provider,
with strong support targeted at the user's single work machine. Priority sets
delivery order; both providers require passive observation, exact identity,
reliable recovery and explicit capability limits.

The user's current workflows naturally separate Claude Code for work from
Codex for mostly other activity, with occasional work use. Work context is a
consumer organization concern, separate from provider and host identity.

The historical proof covers Codex and Claude Code, including foreground and
daemon/supervisor topologies where they can be isolated. Scoped policy changes
apply to fresh launches; existing ordinary sessions remain intact. Codex and Claude Code are the only
providers in the Agent Plus migration. OpenCode integration in Agent Plus is
removed from the migrated candidate; an OpenCode adapter is
outside this migration. Observer multi-host aggregation remains deferred;
Agent Plus uses existing host routing to compose host-local observations.

## Starting points

- [Implementation/execution plan](docs/contract-and-clients-execution-plan.md):
  unattended work packages, independent Observer read/write/artifact acceptance
  and a later separately validated Agent Plus integration pass.
- [Contract and clients plan](docs/contract-and-clients-plan.md): captured
  decisions, phase/age/project semantics, core/read/write/network boundaries
  and independently scoped implementation gates.
- [Contract and clients review](docs/contract-and-clients-review.md): current
  source gaps, independent findings, acceptance cases and documentation validation.
- [Native runtime migration plan](docs/native-runtime-migration-plan.md):
  accepted product direction, native TUI/action design, implementation ownership,
  delivery dependencies, rollout and acceptance gates.
- [Design review](docs/design-review.md): source/evidence checks, resolved
  planning issues, coverage and remaining proof decisions.
- [Provider runtime and UX study](docs/provider-runtime-ux-study.md): Codex
  daemon and Claude Agent View mode comparisons, everyday workflow changes,
  Agent Plus impact and migration proof requirements.
- [Session-state source study](docs/agent-session-study.md): origins, inspected
  revisions, current interface candidates, evidence boundaries and open questions.
- [Spike plan](docs/agent-session-spike-plan.md): capability preflight, source
  comparison, native transition proof, identity/recovery checks and decision gates.
- [Architecture boundaries](docs/architecture.md): shared responsibilities and
  proposed snapshot/watch/capability interfaces.
- [Consumer fit review](docs/observer-consumer-review.md): Agent Plus routing and
  action boundaries, RLCD model fit and partial-feed handling still to resolve.
- [Roadmap](docs/roadmap.md): checkpoint status and the next bounded task.

The study and spike plan originated in the RLCD repository on 2026-10-02 and
now live here. Their earlier provider observations are dated evidence;
preflight must establish the actual installed versions and topology.

Agent Observer focuses on current session observations. Related projects
[Agent Bookkeeper](https://github.com/byebyebryan/agent-bookkeeper) and
[Agent Historian](https://github.com/byebyebryan/agent-historian) cover historical
evidence and cross-session continuity.

## Development

The current [validation workflow](docs/observation-validation-workflow.md)
compares the installed CLI with independent native evidence from ordinary active
sessions and isolated test sessions. It checks identity, phase, age and coverage
before a separate frontend pass; fresh feeds alone do not prove completeness.

From a clone, run:

```sh
./scripts/check
```

The check requires Python 3.11 or newer and Git. It checks repository Markdown
links, whitespace, code fences and Git whitespace errors. It does not invoke
providers, install hooks or start services. It also runs the observation invariant, collector and controlled transport tests. These are
synthetic/controlled checks; native runtime acceptance is recorded separately in evidence.

See [AGENTS.md](AGENTS.md) for development boundaries. The project uses the
[MIT license](LICENSE).
