# Prepared Agent reads and first-consumer follow-up

Date: 2026-10-13 local / 2026-10-14 UTC. Status: proposed execution plan following
the first real RLCD consumer review. This pass records the plan; implementation,
artifact publication, operational selection and RLCD adoption have not started.

## Outcome and current boundary

Certify Observer-owned static Agent rules for Mesh's prepared watch interface,
measure the complete read cost with realistic Agent inventories, and provide an
accepted optional read-client package and handoff. Repeated client renders should
reuse admitted evidence while checking its original expiry and delivery state.
The accepted observation meanings and native collector do not need a redesign.

The baseline is Observer **0.7.0a1 / API 4 / snapshot-watch 6 / Service 4**, with
Mesh **0.1.0a17 / Agent profile v3 / SDK 1**, selected on Snap and Starship. See
[API 4](api-v4.md) and the
[installed/native receipt](evidence/2026-10-13-system-classification/REPORT.md).
Core and local service remain Mesh-free. Codex's daemon owns running/parked and
phase; terminal inventory and attachment remain external. Claude stays retired.
Tmux's independent a7/profile v1 factory and the historical writer remain selected.

Mesh main `b3deb1fab10b3f247643274fa3dd956b0b2b5572` includes the qualified
**0.1.0a18** candidate, frozen from `37c3e01c36866b73734b6ec28d3b7686012c90c0`.
Its [prepared consumer interface 1](https://github.com/byebyebryan/mesh-plus/blob/b3deb1fab10b3f247643274fa3dd956b0b2b5572/docs/prepared-consumer-api.md)
and [changing-watch qualification](https://github.com/byebyebryan/mesh-plus/blob/b3deb1fab10b3f247643274fa3dd956b0b2b5572/docs/evidence/2026-10-14-watch/README.md)
already supply generic immutable admission and current-row expiry checks. They
are additive to SDK 1 and do not change the accepted wire, profile or lock.
That candidate is unreleased and unselected; its fixture compiler does not
certify Observer's Agent semantics. Reuse this seam instead of implementing a
second Mesh admission cache here.

## What the RLCD integration taught us

The accepted consumer uses one persistent fleet watch. Every one-second device
request calls `Fleet.sources()`, which invokes `ReadGuard.current()` and native
reconstruction over the full retained inventory. Only a small active subset is
displayed. Correct current-state admission is expensive enough to dominate that
read path; rendering and USB encoding were minor in the sampled profile.

Preliminary measurements from this conversation are planning evidence, not the
reproducible acceptance benchmark:

- A 124.4-second Starship cgroup sample attributed about **19.8% of one core** to
  the RLCD host bridge, **2.9%** to the Observer collector and **6.3%** to the
  resident local Agent publisher. All three retained their process incarnations
  and had zero automatic restarts. Remote SSH source/server cost was excluded;
  ordinary concurrent native work was not controlled.
- A bounded, cached offline replay used **484 raw rows / 8 selected rows**.
  With `cProfile` enabled, ten `sources()` calls averaged about **299 ms**, versus
  **3.1 ms** for projection and **0.03 ms** for wire encoding. Almost all measured
  time was in read admission/validation. Frozen original admission time isolated
  CPU; this replay did not establish real-time freshness or unprofiled latency.
- Mesh's independent changing-publication study found roughly **7–11%** consumer
  CPU savings at one read per publication, **39–40%** at four, and **66–68%** at
  sixteen in its representative Tmux cells. Its prepared allocation peaks were
  about **18–28% higher**. These are fixture consumer results, not Agent or RLCD
  pipeline results. Publication cadence and export cost must be measured here.

The integration also validated full session identity, system exclusion,
source-sampled conversation age, explicit partial/offline states and separation
of transport ACKs from source freshness. Those are preserved. RLCD's oldest-first
ordering within urgency bands, roster membership policy, 32-row wire capacity,
11 visible rows, serial recovery and alert behavior remain client decisions.

## Responsibility and sequencing

| Owner | Work in this plan |
| --- | --- |
| Mesh | Existing `PreparedReadGuard`, immutable generation ownership, generic full admission, proofs, clock/expiry checks and delivery barriers |
| Observer optional networking/read component | Explicit Agent preparation, pure source-context projection if needed, CLI integration, Agent conformance and installed/native acceptance |
| Observer core/local service | Preserve existing discovery, monitoring, receipt attribution and cached delivery; no new Mesh dependency |
| RLCD owner, after producer acceptance | Adopt the accepted optional interface in an immutable dashboard bundle; measure real device/application benefit and rollback separately |
| Mesh release owner | Publish exact accepted SDK bytes and independent release evidence; no new networking implementation is assumed |

Producer changes finish and receive independent acceptance before any RLCD source,
firmware, bundle or service change. A Mesh defect becomes a focused upstream
handoff; do not work around it by weakening Agent admission or editing both
repositories simultaneously. This plan does not authorize shared-launcher or
publisher changes just to install a new watch client.

## R0 — reconcile inputs and establish a reproducible baseline

Record exact source heads, candidate wheel hashes, Python/dependency versions,
installed roles, host topology and current process incarnations. Confirm the
Mesh candidate's preparation interface and explicit Agent v3 binding. Use clean
installed environments away from both checkouts; preserve the a1/a17 rollback.

Observe the ordinary read/publication ratio on both hosts with a bounded cached
watch, recording counts, row sizes and normalized timing only. Count native
replacement frames separately from heartbeats, gaps and render ticks. Do not
persist native payloads, prompts, tool output or private history in evidence.
Recreate representative inventory shapes with synthetic allowlisted metadata.

Use the same a18 SDK for legacy/prepared behavioral and cost comparisons to
isolate preparation's effect. Separately compare the deployed a17 legacy reader
with the complete proposed package; do not attribute unrelated SDK improvements
to Agent preparation. Account for startup, admission, current results, source
context/raw exports and teardown rather than timing a warmed lookup alone.

Exit: exact input manifest, workload/cadence summary, independent behavioral
oracle and benchmark specification. No new operational selection.

## R1 — settle the owner preparation and read-helper contract

Define an explicit immutable `StatePreparation` bound to the current Agent v3
descriptor and preparation interface 1, with an implementation/package identity.
It compiles one rule per admitted row, in the same full identity and order, from
immutable `PreparationState` facts alone. Match the existing `AgentProfile`
receipt and eligibility semantics exactly. Group receipt lookup once per source
where useful; do not add active-only or system filtering to transport admission.

The compiler must be deterministic and nonmutating. No wall time, environment,
live callback state, provider/collector access, networking or actions affect its
rules. Mesh continues to own original native/projected receipt expiry and proof
checks. Changed profile/compiler semantics require retirement and re-admission;
an implementation label is provenance, not an attestation of installed bytes.

Specify the minimum optional read-helper surface using concrete CLI and RLCD
needs. If a helper is justified, it should retain source metadata/reconstruction
once per admitted replacement and derive current facts through the guard. A raw
export is retained context, not fresh authority. Do not call `snapshot()` or
reconstruct all saved rows on every display tick and simply move the copy cost.
Review replacement, heartbeat, gap, expiry and reconnect behavior explicitly.
An explicit generation/export seam missing from Mesh is an upstream decision,
not permission to access private guard internals or invent an unchecked cache.

Keep display labels, source-to-device TTL policy, membership retirement, sorting,
alerts and transport ACKs outside the helper. No new observation fields or wire
version are proposed. Title provenance and exact phase age remain separate needs.
Prepared guards own watch generations only; polling keeps its current public APIs.

Exit: reviewed additive local Python interface, static-rule specification,
capability/dependency requirement and invalidation matrix. Legacy APIs retain
their mutable-input validation and later callback checks. Explicit prepared
requests fail closed if unsupported; they do not silently fall back.

## R2 — implement and certify Observer-owned preparation

Implement the compiler in the optional Mesh component and the R1 helper only if
it removes demonstrated duplicate consumer work. Add bounded reusable examples
and a comparison probe here, without modifying RLCD. Core/local service and the
dependency-free CLI/help path must still work without Mesh installed.

Compare prepared and legacy outputs against independent golden expectations,
including exact raw row/metadata preservation and full identity/order. Cover:

- Saved parked, running/waiting, working, blocked, runtime-only and unknown rows;
  confirmed child/system rows remain available for caller selection.
- Complete, partial, failed, missing and independently expiring history/runtime
  receipts; multiple namespaces and hosts, with healthy siblings preserved.
- Original activity and native timing fields, missing/future timing and unchanged
  native values with newly admitted receipts. Heartbeats do not renew evidence.
- Input/export mutation, wrong profile/preparation binding, compiler failure,
  changed code semantics, invalid clock and backwards BOOTTIME.
- Gaps, resync, EOF, terminal errors, framing/liveness failures, cancellation and
  reconnect with a fresh guard. Clear retained positives/context as specified;
  no preceding generation survives a failed preparation.
- Capacity rejection, replacement/export peaks, bounded generation retention and
  retirement after churn. Do not turn the serialized-body ceiling into an RSS claim.

Exit: `./scripts/check`, focused source and isolated-wheel tests pass with no
unexpected skips; preparation rules have independent Agent certification.
Generic Mesh tests are supporting evidence, not this owner gate.

## R3 — measure the full changing-watch path and decide adoption

Use serial randomized/ABBA comparisons in fresh processes, without profiling or
allocation tracing during decision CPU runs. Profile separately if a hot path
remains. Include empty/small and representative roughly 500-row inventories,
an enlarged inventory within reviewed native/frame bounds, one/two hosts,
8-ish active rows and **1/4/16 reads per replacement**. Also replay the actual
observed cadence. Change native state/metadata and envelope-only publications;
exercise normal expiry without resetting fixtures' leases to keep rows positive.

Report first admission, replacement, repeated reads, raw/source-context exports,
projection, teardown and complete watch-lifetime CPU/latency. Run allocation
measurements separately, recording steady and peak RSS/PSS where available,
traced allocation, FD/process counts and growth across at least 1,000 synthetic
replacements. Keep actual BOOTTIME freshness tests distinct from fixed-time
allocation tests. No strict process-memory budget is introduced.

Proposed improvement targets for the representative measured workload are at
least **50% less CPU in repeated reads** and **25% less CPU across the complete
watch consumer lifetime**, including changed-publication setup and exports.
These are acceptance targets, not forecasts of RLCD CPU or guarantees for the
single-read case. Publish every workload's result; no adverse case is hidden.
All behavioral/expiry gates must pass regardless of performance. If the normal
cadence does not meet the complete-lifetime target, retain legacy selection and
record the useful scope of the optional preparation instead of declaring the
daily-use problem solved.

Exit: fixed-input behavioral equality, complete cost/allocation report and an
explicit adopt/defer decision. Do not optimize the collector or publisher based
on consumer-only measurements. Their independent live costs remain reported.

## R4 — accept the immutable client artifact and native CLI path

After R2/R3 acceptance, integrate the chosen path into Observer's human Mesh
watch. Keep snapshot/list polling and raw machine envelopes lossless under their
existing contracts. Establish the explicit prepared selection and bounded error
behavior in R1; a tested legacy package remains the operational rollback.
Update the current read guide and API handoff with installed examples, dependency
requirements, ownership, expiry and reconnect obligations.

Build a distinct immutable Observer candidate with the exact accepted Mesh
input. Verify archived/downloaded hashes, clean core-only and optional installs,
Python 3.11 and actual host runtimes, supported imports and contract bytes.
Compare installed public CLI discovery/phase/activity/timing on Snap and Starship
against independent native daemon evidence using the
[validation workflow](observation-validation-workflow.md). Account for sampling
races and accepted partial/unknown native classifications explicitly.

Prove installed local IPC and actual fixed SSH replacement watches, ordinary
two-host fleet reads, healthy sibling behavior, expiry and owned cleanup. Use
isolated disposable services/endpoints for failure tests; ordinary provider
workflows and configuration remain untouched. Source/wheel/native/CI evidence
are separate, and another Observer output is not the native oracle.

Exit: immutable artifact manifest, native/delivery comparison and client handoff.
No RLCD or shared publisher selection is implied.

## R5 — scoped reader selection and downstream handoff

If operational selection is authorized for the execution loop, select only the
accepted Observer read-client prefix on Snap and Starship. Verify reader-only
rollback/reselection and process/FD cleanup while preserving collector, resident
publisher, Tmux, writer and provider configurations/incarnations. A watch consumer
optimization alone does not justify replacing the a1/a17 collector/publisher.
Any separately necessary shared-launcher change needs both domains' cached,
proof/watch and coordinated rollback gates before selection.

Measure matched bounded normal-workflow windows, with startup separate: no added
reader, one local human watch, one fleet watch and two simultaneous consumers.
Report one-core CPU, absolute memory, publication/render counts and authenticated
owned process trees; remote server/source costs are measured independently or
explicitly excluded. At least five minutes per steady window on each host;
changing ordinary workload limits causal before/after claims.

Hand RLCD its exact accepted package hashes, construction/current/export example,
invalidation matrix, cadence-dependent cost results and legacy rollback tuple.
Its agent owns bundle/service/device adoption and the application's matched CPU,
membership/feed-loss and serial recovery proof. Do not use a simulated adapter
or improved CLI to claim that the physical application's CPU issue is closed.

Exit: accepted producer/read-client delivery or an explicit selection deferral,
plus an actionable independent RLCD handoff. 349 can use the same local Python
interface when its own adoption work starts.

## R6 — distribution and wrap-up

Coordinate the exact accepted Mesh SDK release before publishing a consumer
dependency on it. Publish accepted immutable Observer wheel/manifests as a
separate release gate when authorized; verify fetched bytes and clean install.
Reuse accepted bytes rather than rebuilding under an existing artifact identity.
Record source push, hosted CI, release assets, installed read selection and RLCD
selection independently. Source commits or green CI do not establish hosted
wheel availability. An upstream release delay need not block local candidate
certification or the handoff.

Review each checkpoint, run the applicable checks and commit separately during
an authorized implementation loop. Summarize achieved targets, exclusions,
remaining collector/publisher costs and the next independently owned client step.
This planning change is not execution or publication authorization.

## Deferred work

No new daemon/broker, WSS rollout, notification occurrence normalization, exact
phase-entry age, remote wall-clock bridge, new provider, historical compatibility,
attachment/action layer or dashboard firmware/UI change. Physical suspend and
post-TUI-closure proof retain their accepted deferral. A concrete new semantic
need reopens contract review separately; this optimization does not require an
API 5 or Agent profile v4 by itself.
