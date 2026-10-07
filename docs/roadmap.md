# Agent Observer roadmap

Date: 2026-10-06. This document records status and delivery dependencies.
The [architecture](architecture.md),
[migration plan](native-runtime-migration-plan.md),
[spike procedures](agent-session-spike-plan.md) and
[design review](design-review.md) define the associated scope and acceptance.

## Current track: contract and first-party clients

The reviewed design/research checkpoint is the
[shared observation service](shared-observation-service-plan.md): warm local
reads and bounded push for Plus/dashboard clients, with one collection loop.
The [review](shared-observation-service-review.md) records current cost,
source freshness, fan-out/recovery and consumer timing findings. The
[execution plan](shared-observation-service-execution-plan.md) sequences S0–S5
producer work before managed selection or separate client passes. No shared
service, hook selection or downstream migration is implemented by this checkpoint.
The [implementation-loop runbook](shared-observation-service-batch-plan.md) targets
a feature-complete installed producer candidate, both-provider native comparisons
and sustained recovery/resource proof, with physical wake and normal selection
remaining independent follow-ups.

The [API v1 contract](api-v1.md) is accepted within the independent
[a2 producer gate](evidence/2026-10-06-stable-api/REPORT.md): read snapshot/watch
wire 3 and write wire 1, strict pure consumer conformance and native Snap/Starship
cases. Required native contracts replace provider release/hash allowlists while
retaining executable/endpoint/birth and changed-action-context guards. Watch
age/classification/bounds, row isolation, write-result semantics and independent
reference coverage from the [review](discovery-monitoring-contract-review.md)
are repaired with explicit unsupported capabilities.

The [API v1 client handoff](api-v1-client-handoff.md) is the next consumer boundary.
A2 is installed separately; normal links remain a11/wire 2 and Plus retains its
old frozen reader. Client/cache migration and scoped selection have their own
gates. The separate notification source/client checkpoint follows stable read/write
acceptance; it cannot turn sampled watch into lossless native events. Older
exact-image records below remain historical proof.

The [contract/client plan](contract-and-clients-plan.md) and its
[review](contract-and-clients-review.md) govern the next development work. The
user has separated Observer work from frontend work: establish the host-local
model and public conformance boundary, then a local read CLI, a first-party
New/Resume write CLI and optional networking extraction. These can live in one
repository with independent interfaces, dependencies and validation gates.

The [implementation/execution plan](contract-and-clients-execution-plan.md)
maps this direction into E0-E8 packages and G1-G3 acceptance gates. Observer's
local public read/watch/write candidate must pass G2 independently, including
fresh-wheel/reference-client and enabled native routes, before Agent Plus E8
implementation begins. Networking and new push source proof have separate gates.
The [current execution record](contract-clients-execution-status.md) tracks the
regular goal loop independently from the earlier migration pilot.

The [operational resilience checkpoint](operational-resilience-execution-plan.md)
accepts `0.2.0a8` independently through G2 and selects it on Snap and Starship.
Fresh saved discovery through live failures, exact current/surviving Claude
image support, metadata companions, CLI age/diagnostics and native routes pass
within the [producer report](evidence/2026-10-05-operational-resilience/REPORT.md)'s
artifact/topology bounds. It builds on the prior
[discovery repair](evidence/2026-10-04-discovery-repair/REPORT.md).
Plus remains `0.14.0a1` with its frozen `0.2.0a3` reader. Wrapper association,
silent Resume, age presentation and graphical acceptance form its next separate
consumer checkpoint; networking remains deferred.

Routine Observer development follows the
[CLI/native comparison workflow](observation-validation-workflow.md), using
ordinary active sessions for inventory and isolated sessions for controlled
transitions. The 2026-10-05 check leaves Claude idle/background phase semantics,
transient Claude child classification and an older Codex TUI's runtime coverage
unresolved. These are separate producer investigations; the accepted artifact's
bounded capabilities are unchanged.

The subsequent [independent evaluation](evidence/2026-10-05-cli-native-evaluation/REPORT.md)
reopens Observer work: both managed Codex peers now use the `0.160.1` release
image and the selected collector returns zero Codex rows. Current daemon
capability acceptance, discovery resilience and diagnostics lead the next
producer checkpoint, followed by held Claude phase/child and completion-only
clock cases. The report records context, topology and artifact-bookkeeping gaps
separately. No adapter or selection change was made during evaluation.

The subsequent [repair checkpoint](evaluation-repair-execution.md) accepts and
selects `0.2.0a9` on both hosts. Exact current-daemon capability proof, independent
saved discovery, actual-image diagnostics, completion-only clocks and Claude
conversation classification close the proved subset. Recorded context and older
TUI limits are settled explicitly. Installed CLI/native comparison, read/write,
concurrent watch, isolated recovery and frozen-reader compatibility precede
selection. The [report](evidence/2026-10-05-evaluation-repair/REPORT.md) records
all nine resolutions and remaining capabilities. No frontend implementation,
ordinary provider configuration/restart or public release accompanies it.

The [monitoring checkpoint](monitoring-execution.md) independently accepts the
`0.2.0a10` candidate on both hosts. Exact current-image Codex questions/outcomes,
Claude foreground readiness and typed background questions, and bounded history
diagnostics pass the [packaged/native gate](evidence/2026-10-05-monitoring/REPORT.md).
The strict v2 contract and frozen consumer reader remain compatible. Normal
entrypoints remained on a9 at that gate; candidate selection and frontend acceptance are separate.
Foreground Claude questions, older worker semantics, blank background readiness
and event-source installation remain explicit limits.

The subsequent [stopped-runtime checkpoint](stopped-runtime-execution.md)
independently accepts and selects `0.2.0a11` on Snap and Starship. Exact current
Claude retained done/stopped idle jobs with complete stable inventories and no
live bound worker report parked. Native detach/stop/attach/saved-Resume, ordinary
CLI/native comparisons and frozen-reader compatibility pass the
[producer gate](evidence/2026-10-05-stopped-runtime/REPORT.md) before the two
managed Observer entrypoints change. The two recap jobs now report parked with
their ages preserved; other ordinary workers remain running. Saved-only runtime
absence, failed/unsupported contexts and Codex parked inference retain their
limits. No frontend implementation or ordinary provider restart is included.

The initial G1/G2 pass accepted the independent `0.2.0a3` Observer candidate: public v2
read/watch, Git/workspace enrichment and separate New/Resume client. After that
closure, Plus `0.14.0a1` passed its own bounded source/package/native E8 gate
against the frozen producer artifact. G3 networking remains deferred. Both
candidates were selected as the provisional pilot on Snap and Starship; see the
[operational record](operational-execution-status.md) for independent installation,
bounded watch/recovery and real Tmux/SSH entry acceptance. The
[operational plan](overnight-operational-acceptance-plan.md) closed its unattended
O0-O5 work with all five managed entrypoints and private rollback snapshots.
Desktop/release/coordinator acceptance remains separate. The
[handoff](contract-clients-handoff.md) records the immutable package tuple and
remaining monitoring/networking work.

Checkpoint order is C0 capture/review, C1 model/source decisions, C2 schema and
fixtures, C3 read client, C4 write client, C5 optional networking, followed by
separate consumer migrations. C4 requires C2 and operation-specific proof;
read-only C5 does not require C4. A read-only/device consumer does not depend on
write-client delivery. The accepted candidate's exact fields and semantics are
in the [public v2 contract](public-contract-v2.md) and [write contract](write-client-contract.md).

C2 defines snapshots and a local watch stream together. C3 may initially push
sampled changes from polling; native notifications and passive hook wakeups have
separate source/passivity gates. Push to consumers does not imply lossless native
events or introduce cross-host networking into the core.

Working/blocked/waiting phases and Git/workspace context are accepted within the
candidate's source-specific bounds. Parked is accepted only for the bounded
exact-image Claude terminal-job predicate; other absence remains unknown.
Last-conversation activity is accepted for bounded native metadata; missing
older Codex clocks and unpersisted copied Claude histories stay explicitly
unknown. Creation is a separately labeled ordering option.
Multi-profile UX remains deferred. The reviewed managed cutover selects v2 on
Snap and Starship and retains the old artifacts for rollback. The gaps and acceptance cases are in the public contract and
execution record.

The M/R records below describe the existing migration pilot and its remaining
acceptance gates. They do not authorize combined core/frontend work in this
next track or make networking a prerequisite for the host-local contract.

## Product and provider priorities

Agent Plus meshes sessions across providers and hosts. Agent Observer owns its
provider discovery/monitoring boundary; Agent Plus retains UI, host composition,
viewer association and validated actions. Providers own work; tmux carries
individual native TUI clients.

Codex is primary and leads the first complete integration and validation across
machines. Claude Code is secondary, with strong support on the user's single
work machine. Priority changes delivery order, not support quality or the
provider-neutral architecture. Check Claude's native model before stabilizing
the shared contract; the completed migration includes both providers.

The user's work/general distinction is consumer presentation policy, separate
from provider and host identity. Context views/tags and a persistent session
rail are optional later UI work. OpenCode support in Agent Plus is deprecated
and removed at migration cutover. Temporary Agent Plus breakage is acceptable;
a parallel legacy discovery implementation is not a migration requirement.

## Observation proof status

P1-P5 are evaluated per provider, version, namespace and topology. A completed
Codex checkpoint does not assert Claude support. Source decisions and a
provisional Codex interface can precede completion of Claude proof; shared
contract stabilization requires both models' native evidence and consumer fit.

| Checkpoint | Status | Exit |
| --- | --- | --- |
| B0: bootstrap | Complete | Separate repository, migrated study/plan, ownership boundaries and documentation check |
| P1: capability/topology preflight | Exact installed artifacts and native runtime subsets proved on Snap and Starship | Exact target versions/topologies, isolation/passivity procedure and capability coverage with gaps explicit |
| P2: minimal source comparison | Native Codex endpoint and passive Claude files selected; mutable Claude roster CLI rejected | Bounded study adapters compared with populated native work on the intended topology |
| P3: transition proof | Working, settled and approval subset accepted for both; other transitions unsupported | Working/settled, approvals/denials, blocking input, cancellation and observation failure outcomes |
| P4: identity/recovery proof | Codex exact resume/new/lifetime/recovery accepted; Claude worker/client lifetime accepted; current-client binding unsupported | Native switches, concurrent sessions, gaps/restarts, job/worker/client lifetime and exact mappings |
| P5: source/interface decision | Python/JSON candidate selected and consumer fit reviewed; release gates pending | Per-provider source choices and explicit gaps; schema/ordering/lifetime/overhead proposal reviewed against both consumers |

The [Snap report](evidence/2026-10-02-p1-snap/REPORT.md) and
[capabilities](evidence/2026-10-02-p1-snap/capabilities.json) establish installed
Codex 0.160.0 and Claude 2.1.287, selected settings/static interfaces, controlled
Codex empty reads and isolated Claude empty-roster/opt-out behavior. The
[runtime UX study](provider-runtime-ux-study.md) adds installed entry/navigation
interfaces and Agent Plus source implications. Later [native runtime evidence](evidence/2026-10-03-native-runtime/REPORT.md)
supersedes those empty-state limits for the accepted subset. Client binding and
additional transition semantics remain unsupported rather than inferred.

The [Starship preflight](evidence/2026-10-02-p1-starship/REPORT.md) is dated
Starship evidence; it does not establish Snap or current fleet behavior. A
custom App Server is not managed-daemon proof. Foreground comparisons remain
useful, but full standalone parity is not required for the migration target.

## Delivery checkpoints

The unattended execution loop has installed Observer and Agent Plus candidates
on Snap and Starship and accepted bounded native action routes; see
[execution status](execution-status.md). This is a prerelease pilot. Desktop
acceptance, full recovery/batch coverage and published release closure remain
separate gates. Detailed exits, implementation areas and acceptance cases remain in the
migration plan.

| Checkpoint | Dependencies | Exit focus |
| --- | --- | --- |
| M0: native workflow proof | Relevant P1 gates | Codex managed entry, owning runtime, exact IDs and client binding; early Claude model comparison |
| M1: Codex Observer | Codex P2-P4/source decision | Passive saved/live discovery, provisional JSON, recovery, coverage, limits and measured cost |
| M2: runtime/package pilot | M0/M1 | Scoped Snap managed Codex configuration, native individual entry, installed Observer and hooks/plugins acceptance |
| M3: Codex Agent Plus | M1; M2 for ordinary runtime trials | Observer-backed discovery/UI and validated single actions; OpenCode removed at cutover |
| M4: Codex across machines | M3; preflight each target | Correct host routing/identity, reconnect/sleep/restart, jobs without wrappers and accepted batch attachment |
| M5: Claude mesh completion | Early M0 model review, Claude P1-P5 and M1/M3 boundary | Single-machine supervised UX/actions, Claude-only host case and both-provider contract validation |
| M6: Agent Plus release closure | M4/M5 | Both-provider migration acceptance, schema/artifact bookkeeping, legacy removal and maintenance procedure |
| R1: RLCD host bridge | Proved M1 observations and common contract review; M5 for stable schema | Live roster/health/waiting consumed through Observer; bridge recovery and device transport accepted in RLCD |

The primary path is M0 → M1 → M2 → M3 → M4. M5 can proceed alongside M4,
and M6 closes the Agent Plus migration after both are accepted. R1 can develop
against the provisional boundary from M1 with explicit version/coverage limits;
its stable integration follows contract stabilization. RLCD firmware/physical
acceptance is a separate track and does not block an Agent Plus milestone.

Observer installation is required on each selected target host. Existing Host
Mesh transport supplies cross-host composition; Observer multi-host aggregation
and a new network control plane are outside this program. Re-establish the
target host list at rollout; Snap/Starship references are not an exhaustive
fleet inventory. Claude's initial target is its one work machine. WSNav remains
an optional future consumer.

The migration plan records the [selected configuration changes](native-runtime-migration-plan.md#runtime-policy-and-individual-tui-entry)
and [execution continuity procedure](native-runtime-migration-plan.md#execution-continuity-and-handoff).
Keep the executing Codex session available while building and testing separate
clients. A final move of that conversation may require a deliberate reopen;
prepare its exact identity, validated route and handoff before any such exit.

## Remaining acceptance and release work

Use a graphical desktop to check the managed picker, individual TUI launches,
selection preservation and focus behavior. The unattended coordinator has no
display connection; disposable attached clients prove native entry routes but
do not establish those visual outcomes. The exact coordinator reopen procedure
is recorded in the [execution handoff](execution-handoff.md) and remains last.

Keep current-client conversation binding unsupported. Native rows cannot gain
focus, session-specific close or batch authority from historical Tmux options.
Cross-host sleep/wake and transport-loss recovery still need their native cases;
controlled failure tests do not establish physical suspend behavior.

The same candidate wheels and scoped managed links are installed on both hosts.
The old owned extension archive and published external pins remain available;
the independent candidate override is not a published release tuple. Review and
publish source/artifact bookkeeping after desktop acceptance and contract
stabilization. Hook capture remains unproved: preserved historical trusted
references do not establish live callback execution.

The RLCD bridge candidate consumes public schema 1 and has synthetic and
installed-native-input projection evidence. Firmware transport, bridge recovery
and physical display acceptance remain in the separate RLCD track. Preserve
the existing user changes in that repository.

## Planning review outcome

The [review](design-review.md) separates documentation/source validation from
runtime acceptance and records the resolved design gaps. The migration plan
guided the bounded execution pilot. Existing-only Codex endpoint discovery,
explicit native ID mapping, passive Claude metadata and supervised empty Claude
creation now have native evidence for the pinned versions. Current viewer
binding and additional transition/recovery cases remain unsupported or pending.
