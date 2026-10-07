# Shared service: implementation goal-loop runbook

Date: 2026-10-06. Status: implementation/execution planning, not an active
implementation or rollout. Baseline is `f1a3881`, with a clean Observer checkout.
The [reviewed design](shared-observation-service-plan.md),
[deep review](shared-observation-service-review.md) and
[S0–S6 execution gates](shared-observation-service-execution-plan.md) remain
authoritative. This runbook makes those gates concrete for one large regular
goal loop, with commits as accepted checkpoints are completed.

## Intended batch outcome

Implement a host-local shared observation service and its explicit read client:
one producer schedule, cached snapshots, bounded push subscriptions, independent
provider failure handling and honest freshness. Preserve accepted API v1 direct
read/write semantics and the separate notification candidate.

Deliver a frozen installed candidate on Snap and Starship, an independently
validated reader, native comparisons and measured operational results. Codex
leads implementation and proof on both hosts; Claude is required on Snap before
claiming the complete producer subset. Reaching a Codex checkpoint is useful
progress, not acceptance of missing Claude work.

The default batch includes S0–S4 and every S5 case that can run unattended without
altering ordinary provider work. Long native-lifetime and resource checks belong
in this loop where the required isolated contexts are available. Actual physical
suspend needs a separate operator window and remains explicitly pending.
Normal links, persistent service selection, provider policy/hooks, Agent Plus,
networking and firmware remain outside this implementation batch.

## Concrete interface and implementation direction

Use these CLI boundaries as the S0 starting proposal. Final grammar must be
recorded and fixture-tested before S1; these commands do not exist yet:

| Proposed entry | Purpose |
| --- | --- |
| `agent-observer-service serve` | Explicit foreground local runtime with owning host, provider selection and private socket |
| `agent-observer service api` / `schema` | Pure service descriptor/schema export, with no provider or socket requirement |
| `agent-observer service status` | Service readiness, source attempts/leases, coverage and bounded operational diagnostics |
| `agent-observer service snapshot` | Cached service envelope with unchanged embedded snapshot 3 |
| `agent-observer service list` | Human discovery/age view using existing client filters/order on the same cached snapshot |
| `agent-observer service watch` | Initial view/status, replacement views, heartbeat and gap/resync envelopes |

Service reads require an expected host scope and selected socket. They validate
configured provider/store scope from the service descriptor; they do not choose
provider homes or scheduling. Default socket location can be a private directory
below the user's runtime directory, with explicit overrides for isolated proofs.
Existing `snapshot`, `list`, `show`, `watch`, `api` and write defaults remain
unchanged. The new service stream is not passed to the direct watch-3 parser.
There is no action, force-refresh, auto-start or stop endpoint in the first wire.
`service list` is a client projection, not another service request or collector.
Its diagnostic text retains source uncertainty; machine readers use the envelope.

Suggested module boundaries, adjusted only with a recorded reason:

| Responsibility | Proposed location |
| --- | --- |
| Pure service wire/schema/semantic validation | `service_contract.py`, bundled service schemas/fixtures |
| Separate pure service facade | `service_public.py`; do not add symbols to accepted `public.__all__` |
| Bounded socket read client | `service_client.py`, lazily reached by existing CLI's new service subcommand |
| Source receipts, dependency/expiry projection, reconciliation | `service_state.py` |
| Fair jobs, deadlines, dirty/context generations | `service_scheduler.py` |
| Owned provider collection process | `_service_worker.py`; trusted internal input, bounded public metadata output |
| Singleton, Unix IPC, publisher and lifecycle | `service_runtime.py`, `service_cli.py` |
| Existing native reads/projection | Existing adapters and `collection.py`, refactored internally rather than duplicated |

Start with validated single-provider snapshot-3 worker results. Reconcile them
through an explicit state layer; `compose_snapshot` accepts native inputs and
must not be called with cached public components or used to renew all clocks.
Add internal field/source receipts when splitting monitoring and history.
Keep the service implementation standard-library based; do not add a mandatory
async framework or expose adapter internals as a public client API.

## Commit-sized execution sequence

| Batch checkpoint | Work / proof | Commit boundary |
| --- | --- | --- |
| B0 / preflight | Recheck source, installed baselines, both hosts, required native capabilities and proof isolation tools; open a progress record | Recorded context and scope; no production selection |
| B1 / S0 | Service schema/descriptor, pure parser/facade, canonical and negative fixtures, independent reader | Contract candidate accepted synthetically; API v1 unchanged |
| B2 / S1 | Source receipts/expiry, scheduler, atomic publisher, controlled-source fan-out and resource accounting | Actual implementation passes race/failure/slow-reader tests |
| B3 / S2 | Existing-only reads in owned workers, per-provider publication, cold start and conservative expiry | Functional native-read candidate; no continuous full-history deployment |
| B4 / S3 Codex | Runtime/inventory/history separation, exact identity indexing and provenance; Snap/Starship comparisons | Codex monitoring candidate accepted within measured scope |
| B5 / S3 Claude | Registry/job/worker versus SDK history separation, context/age/title provenance and parked predicate parity | Required second-provider candidate; shared cadence/resource gate |
| B6 / S4 | Public CLI, packaging/verifier extension, fresh-prefix installs and private runtime/user-unit proofs | Installed artifact and independent read-client gate |
| B7 / S5 | Ordinary independent comparisons, isolated transitions/outages, restart/context recovery, slow readers and sustained/native-lifetime runs | Case-by-case producer acceptance with coverage limits |
| B8 / closure | Resolve producer findings, freeze/reverify final artifact, update handoff and remaining gates, clean owned proof resources | Reviewable final producer handoff; no downstream or normal selection |

Each accepted code checkpoint runs `./scripts/check`, affected conformance/runtime
tests and scoped review before commit. Native evidence may follow in its own
commit. A failed gate triggers a repair and appropriate rerun; it does not justify
skipping to frontend work. If native testing changes production bytes, rebuild
an immutable candidate and revalidate the affected installed/native subset.
Do not repair a frozen prefix in place or report an older wheel as proof of new
source. Final acceptance must identify the exact source and wheel tested.

## B0: preflight and continuation state

Fresh read-only planning preflight found Codex CLI `0.160.1` and Claude
`2.1.291` on Snap, Codex CLI `0.160.1` on Starship, reachable batch SSH and
`unshare`/`bwrap` executables on both hosts. These are diagnostics/tool presence,
not proof of native topology, usable isolation or contract support. Recheck at
loop start; inspect actual managed endpoints/images and Claude worker context.

Record a progress file with checkpoint status, source revision, candidate
prefix/hash, service socket/PID/birth, owning proof roots, tested cases and next
command. Keep raw payloads and credentials out of it. Use bounded metadata
receipts under a new implementation evidence directory. Before each native
launch/recovery proof, establish the private namespace and cleanup authority.
`scripts/native-isolation` uses user/mount/PID namespaces and masks ordinary
provider paths: that is an isolated native proof setup, not the proposed ordinary
service unit configuration.

Continue from the last accepted checkpoint after context compaction. Reinspect
Git and owned processes before resuming; do not recreate already completed
fixtures or erase unrelated work. Use an isolated worktree if unrelated changes
make the implementation checkout unsuitable. Commit intended paths only.

## B1–B3: essential implementation tests

Test the actual codec, scheduler, state layer and socket publisher, rather than
counting design-model assertions as implementation proof. Required cases include:

- Strict extra-field/version/identity/host rejection; fragmented, oversized,
  duplicate-key, nonfinite, incomplete and pipelined requests.
- Warming without complete empty inventory; initial capture/register races;
  independent provider completion and late changed-context result rejection.
- Unchanged values with a genuine new read receipt, pure heartbeat without
  renewal, timer expiry without incoming events and wall-clock jumps.
- Full-source expiry first, then mixed runtime/history/workspace generations;
  retained blocked facts become unknown, preserving original last-known clocks.
- Missing rows under partial coverage, cap/retention failure and two-provider
  aggregate row/byte limits. Admission/eviction cannot claim complete absence.
- Dirty signals during reads, debounce storms, fair periodic discovery, bounded
  backoff and hard worker deadlines without overlapping provider reads.
- Partial outbound frames, coalesced pending views, gap/resync, slow/no readers,
  healthy readers alongside them, connection admission and global memory limits.
- Singleton contention, foreign/symlink/replaced sockets, stale owned sockets,
  disconnect, forced owned-service exit and a new epoch after restart.

Prove cleanup targets only Observer-owned worker/helper descendants. No timeout
or service kill may signal an ordinary provider or current TUI. CPU/memory/FD
accounting must include subprocesses and encoding/decoded-state costs; sharing
bytes alone is not a memory proof.

## B4–B5: performance and freshness acceptance

Use these as tuning targets for the current ordinary workload, not published
guarantees or evidence already achieved:

| Measurement | Initial target / rule |
| --- | --- |
| Warm local snapshot | p95 at or below 250 ms over at least 100 validated reads; exclude bootstrap and report payload size |
| Adding read clients | Same scheduled provider jobs/RPC/history-worker counts; extra client delivery cost reported separately |
| Source change publication | Within the configured cadence plus bounded source-read/publisher delay; measure native reference timestamps |
| Ordinary idle CPU | Target at most 5 percent of one CPU on a sustained sample, including owned descendants; adjust explicitly with measured justification |
| RSS/FD/queue use | Enforced resource bounds and no sustained growth; report maxima for the actual and controlled maximum-size workloads |
| Saved discovery/activity lag | Explicit cadence, source receipt and expiry; no runtime refresh renewing history-derived fields |

Begin tuning with runtime monitoring around 2 seconds, inventory around
5 seconds, saved history around 60 seconds and workspace enrichment on cwd/root
changes plus a slower reconciliation. These apply only after the internal split,
not to the current full scan. Final intervals, hard deadlines, expiry budgets
and idle backoff are selected from measurements and recorded in the accepted
configuration. Unknown state cannot justify treating a source as idle.

Keep one in-flight job per provider. Bound history work slices so they cannot
starve monitoring; record any native operation that cannot meet that bound.
Reuse existing predicate/projection functions. Codex title/activity/child changes
and Claude custom-title/history companion/sidechain cases must retain provenance.
An executable cache is optional and requires invalidation proof; never optimize
by dropping physical image, process birth or endpoint-ownership guards.

If a target is missed, diagnose and optimize before ordinary always-on acceptance.
A deliberately slower bounded candidate can be a documented intermediate result,
but its measured tradeoff cannot be described as the target being met.

## B6: packaging and explicit installed client

Reserve a new service candidate series, provisionally `0.4.0a1`, with API 1,
snapshot/watch 3, write 1 and a separately prerelease service protocol 1. Package
version and provider version remain unrelated to contract support.

Extend `scripts/candidate-artifact` and its tests: it currently accepts exactly
two entrypoints and a fixed core schema map. A versioned manifest extension must
verify the service executable, service schemas/descriptor and ordinary installed
bytes while continuing to verify existing manifests unchanged. Keep service
versions outside API v1's existing `schemas` map; adding `service` there would
break the current descriptor equality check. Verification invokes no provider.

Install fresh immutable prefixes using Snap's source-only Claude-history profile
and Starship's core profile. Run installed commands outside the checkout with
an independent service reader and current API v1 reader. Check import purity,
schema versions, peer UID, expected host/store scope, errors and old direct/write
regressions. CLI readers do not silently fall back to direct collection.

First run the service explicitly in the foreground. Test an owned, uniquely named
temporary user unit if feasible, preserving native-visible home/config selectors,
mount/PID context and boot metadata. Do not enable a persistent normal unit, move
normal read/write links, change login lingering or restart ordinary providers.
Test and clean only the recorded service socket/process/unit. The current coding
session does not need a restart for this producer work.

## B7: native comparison, failure and sustained proof

Compare installed service output with independent native evidence using
[the CLI validation workflow](observation-validation-workflow.md). Direct Observer
parity is an additional regression check, not the independent reference.
Record exact identity/title/kind/runtime/phase/activity and coverage comparisons
on Snap Codex/Claude and Starship Codex. Bracket changing rows with sample times.

Use ordinary sessions for passive inventory and state comparisons. Put controlled
work, held input, TUI exit, provider restart, executable/context replacement and
cleanup into verified disposable contexts. Scope helper changes to the needed
service/lifetime scenarios; do not indiscriminately run all write proofs.
Retest write behavior only where adapter/refactoring changes affect its guards
or preparation/entry paths, using isolated owned sessions.

Run a bounded multi-reader soak, initially 30 minutes per required host/provider
combination, with healthy and slow readers plus recorded source-job/CPU/RSS/FD
counts. Host runs may overlap where independent; retain progress every minute
rather than one long blocking wait. Test source outage and Observer restart on
owned contexts while healthy source delivery continues.

For idle-retirement passivity, use comparable isolated observed and unobserved
contexts. Probe the control only at necessary comparison points; continuous
reference polling would contaminate the control. Observe for the installed native
retirement window plus a margin, not an assumed provider-version duration. Prove
reads do not subscribe or hold an otherwise retiring context. If the native
predicate/window is unavailable, mark this exact gate pending and continue other
independent work; do not infer lifetime passivity from matching phase snapshots.

Use fake-clock recovery for deterministic suspend logic. Do not suspend either
ordinary host unattended: it would disrupt active work or the executing loop.
Actual physical wake remains a named follow-up with no claim of operational
suspend acceptance.

## Completion, recovery and exclusions

Maintain separate source, packaged, controlled and native status for every gate.
Core implementation is complete only when B1–B6 deliver the planned features and
required installed checks. B7 acceptance is reported case by case; any required
native failure remains an unresolved producer issue, not a successful broad gate.
Finish all feasible repairs and tests before the B8 handoff. External unavailable
proof conditions do not erase accepted independent work or authorize guesses.

At closure, clean owned proof runtimes/helpers/sockets/units, verify ordinary
provider workflows were not changed, commit final evidence and report exact Git,
artifact and acceptance status. Include a small reproducible quick-start using
the accepted candidate, a client-facing service contract and a gap matrix.
Leave the previously selected artifacts available and normal selection unchanged.

Follow-on work stays separate: managed service selection, Agent Plus migration,
remote mesh streaming, RLCD/API v1 bridge and physical device acceptance, hooks/
native signals, notification event delivery and native state-episode timing.
No OpenCode, provider version allowlist, legacy discovery stack or action service
is added to this loop.

## Proposed goal text for starting the loop

Implement the reviewed shared host-local Observer service and explicit read
client through S0–S4, preserving API v1 and native workflows. Commit accepted
checkpoints. Build, install and independently validate an immutable candidate on
Snap and Starship; prove Codex on both and Claude on Snap through passive ordinary
comparisons and scoped disposable native tests. Complete the feasible S5 failure,
recovery, multi-reader/resource and native-lifetime matrix, repair producer defects,
and record exact accepted/pending cases with reproducible handoff. Preserve normal
artifact selection, hooks/settings and ordinary provider sessions; do not edit
downstream clients or initiate physical host suspend.
