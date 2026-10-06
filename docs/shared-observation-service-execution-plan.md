# Shared observation service execution plan

Date: 2026-10-06. Status: reviewed plan for a subsequent implementation goal.
Read the [design](shared-observation-service-plan.md),
[review](shared-observation-service-review.md) and
[evidence](evidence/2026-10-06-shared-service/REPORT.md) first.
This documentation checkpoint performs no service deployment or client migration.

## Sequence and ownership

Observer owns all S0–S5 producer work and acceptance. Keep Agent Plus, networking,
notification publication and firmware changes out of those checkpoints. Client
defects reopen a distinct producer checkpoint when evidence identifies an
Observer issue. Preserve the accepted a2 direct-read/write subset and a4 callback
candidate; new service packaging/selection has independent evidence.

| Stage | Deliverable | Exit gate |
| --- | --- | --- |
| S0 | Proposed service wire 1, pure codec/reader, schema and independent consumer fixtures | Strict bounded decoding, unchanged API v1 and explicit cached-state semantics |
| S1 | Shared scheduler/publisher/fan-out against controlled sources | Race-free initial view, independent sources, expiry, bounded delivery and recovery |
| S2 | Existing passive adapter collection in owned bounded workers | Same identity/predicates as direct CLI; no provider actions; source isolation |
| S3 | Efficient runtime/inventory/history/workspace cadence separation | Dependency/provenance correctness and measured CPU/latency budget |
| S4 | Packaged Unix service and explicit read-client backend | Private authority, clean lifecycle, independent installed-client acceptance |
| S5 | Native and operational acceptance on Snap/Starship | Ordinary and isolated comparisons, restart/outage/load/wake evidence |
| S6 | Optional scoped user-service selection | Separately authorized managed rollout/recovery after producer acceptance |
| Later | Native/file/hook signals, networking and consumer migrations | Independent contracts and native/consumer gates for each capability |

Commits should follow reviewable producer stages, not one large service/frontend
patch. Run `./scripts/check` before each commit, plus stage-specific tests. Commit
evidence separately when it materially clarifies source versus installed/native
acceptance. Do not publish or select a candidate solely because synthetic tests
or the design pass succeeded.

## S0: service contract and independent reader

Define a separate local-service protocol version and machine-readable descriptor.
Choose explicit service read/status/subscription commands without changing current
direct CLI defaults or `agent_observer.public.__all__`. Keep provider imports out
of the pure service reader. No action, resume, arbitrary config path, provider
interval preference, durable replay or force-refresh request in the first wire.

Specify service incarnation, configured host/store identity, view version and
transport sequence separately. Describe warming/ready service state independently
of source health. Source metadata must include actual accepted-read age/expiry,
last attempt result, context generation and affected coverage. State the scope
of elapsed clocks and the client's transport-silence policy. The first envelope
embeds unchanged snapshot 3; direct watch 3 retains its accepted grammar.
An accepted new read can publish a replacement view with unchanged phases.
Pure service heartbeats never renew a source confirmation.

Specify initial status/view ordering, heartbeat, source gap, delivery gap, resync,
disconnect and restart. Cached reads do not request a provider scan. Warm-up
does not establish complete empty inventory. No raw service envelope is sent to
an existing wire-3 parser. No source timestamp is renewed by serialization.

Enforce request size/depth/nodes, duplicate keys, invalid UTF-8, nonfinite values,
integer bounds, maximum envelope overhead and full frame bytes. Proposed initial
request/frame allowances are 16 KiB and observation maximum plus 16 KiB;
derive final values from worst-case fixtures. Keep finite content-free errors.
Start with one bounded request per connection, followed by its response or
subscription; reject pipelining and unused inbound traffic under explicit rules.
Test an independent reader without internal producer helpers, incompatible
versions, wrong host/store/UID scope and extra fields. Record service protocol
stability separately from accepted API v1.

## S1: controlled scheduler and delivery

Implement one publisher with bounded per-provider jobs, dirty generations,
periodic deadlines, source expiry and fair retry/backoff. Use injected sources
and clocks for deterministic verification. One source timeout must not delay
another source's ready update or change its evidence health.

Exercise hints before/during/after reads, storms, overlapping request attempts,
changed context, late success, failure recovery, lost signals, callback silence,
empty partial feeds and bounded retained rows. Expiry should produce unknown/stale
facts and an update without any native event. Prove monotonic/BOOTTIME clock
choice with fake wall jumps and sleep-inclusive time advances. Expiration and
context generation are distinct guards.

Register/capture initial views atomically. Encode/write outside the transaction.
Use one immutable in-flight frame and one pending latest view per client; skipped
views get explicit loss/resync semantics. Do not replace a partly sent frame.
Bound request/write time and fair bytes per event-loop pass. Verify fragmented
frames, malformed/oversized/incomplete requests, EOF, reconnect and clients that
never read. Exercise slow and healthy readers together using the actual fan-out.

Proposed limits are 16 connections and 64 MiB global encoded retention. Reserve
before allocation; share immutable bytes; enforce the global limit even if every
client pins a different large frame. Measure and bound decoded-object, worker,
encoding and file-descriptor use separately. Maximum-size tests must exercise
the real schema/parser, not just arithmetic from the design study.

## S2: bounded shared accepted collection

Call existing adapters through Observer-owned subprocess workers with bounded
stdout, sanitized finite errors and hard wall deadlines. Kill/reap only owned
workers and owned helper descendants. Establish ownership before group cleanup;
do not signal the native daemon or its sessions. Publish providers independently
and use configured scope rather than subscriber labels to compose data.

Initially a full provider sample is one freshness unit. Reconcile by the full
identity and preserve confirmed child classification before client projection.
Expire current claims conservatively while preserving original last-known
evidence; do not infer removal, parked or waiting from a failed inventory.
Reject late results if provider store/runtime context generation changed.

Compare service output to the direct installed CLI and independent native
evidence. A comparison to another Observer view detects divergence but does not
establish native correctness. This stage is a functional candidate, not permission
to run full-history collection at the current two-second watch cadence overnight.

## S3: efficient monitoring with provenance

Extract provider runtime monitoring/inventory and saved metadata phases without
creating duplicate adapters or weakening predicates. Keep one scheduled producer
per provider; cheap monitoring can run between slower history work, subject to
deadlines and bounded priority. Define maximum history work slices so saved
discovery cannot indefinitely block phase observations. Event hints may advance
an eligible read but never grant unlimited frequency.

Track internal field dependencies and sample/context generations. Runtime-only
refreshes cannot freshen saved coverage, titles/activity/workspace from an old
source, or invalidate historical event clocks merely for being old. Prove saved
history lag, new unsaved sessions, renamed metadata, child classification changes,
mixed fresh/stale components, activity ordering and source-specific absence.

Replace quadratic duplicate detection with indexed exact identity without changing
rejection rules. Any cross-sample executable-validation cache must revalidate
file/process/config/runtime context and reject replaced/deleted images. Retain
actual hashes/ownership/birth checks; support stays predicate-based.

Measure process CPU, wall latency, RPC/worker counts, RSS and time to observe
changes on an ordinary idle and active workload. Adding clients must not multiply
source reads. Choose and document monitoring/inventory/history intervals and
expiry policies from those measurements. Acceptance needs a written resource
budget and achieved results; current short CLI measurements do not supply a
production interval or latency promise.

## S4: packaged local service and client

Package a new candidate without changing accepted normal links. First launch
manually with explicit prefix, owning host, default/explicit provider selectors
and runtime path. Use a private per-user directory and pathname socket with
expected peer UID, a singleton lock and safe inode-aware cleanup. Refuse live,
foreign, symlinked or replaced endpoints; one failed bind must not unlink another
service's socket. No client-selected stores or host relabeling.

Prove cold start, warming/partial status, normal shutdown, forced service exit,
stale endpoint recovery, service restart epoch, disconnected reads and no silent
direct fallback. Reconnect cannot reuse stream sequence/previous source freshness.
Persist no observation journal initially. Record actual service-read latency,
warm view size, CPU/RSS and bounded diagnostic output through an independent
installed reader. Verify Python parsing remains usable when the service is absent.

Test the optional systemd user unit as a separately selected artifact: explicit
prefix, preserved home/config selectors, ordinary native endpoint visibility,
boot/PID domain, runtime permissions and bounded restart policy. Start without
socket activation or login-lingering changes. Hardening only follows proved
required capabilities; a unit directive alone is not acceptance.

## S5: independent native/operational gate

Follow [the observation validation workflow](observation-validation-workflow.md).
Use independent native identity/inventory/state/activity evidence from ordinary
active sessions when safe; use isolated disposable contexts for new transition
or failure proofs. Inspection does not authorize native resume/start/stop. Snap
must prove Codex and Claude; Starship proves Codex independently. Record required
capabilities and actual runtime diagnostics without making releases allowlists.

| Case | Required result |
| --- | --- |
| Ordinary active/saved/parked subset | Exact identity, phase/runtime separation, age/title and coverage comparisons with explicit unknowns |
| Two readers, then several including a slow reader | One producer schedule; healthy delivery remains timely; global memory/FD bounds hold |
| Controlled turn / blocked input / settled state | Same accepted predicates; no state-episode clock or completion inferred from sampled changes |
| Source timeout/unavailable with other provider healthy | Scoped failure/expiry, healthy rows and updates retained |
| Provider executable/runtime/store replacement | Changed context invalidates old jobs/cache; no release-list rejection |
| TUI exit, reader exit, Observer restart/kill | Provider work/lifetime unchanged; new Observer epoch and explicit recovery |
| Sustained polling through native idle retirement | Reads do not subscribe, hold an otherwise retiring context or change its unload policy |
| Ordinary provider restart and service outage | Reconcile exact context; no empty complete inventory or invented parked state |
| Sustained operation | Recorded CPU/RSS/read counts/latency under idle and active workloads, not one short sample |
| Actual suspend/wake | Expired facts are invalidated before serving; healthy sources recover independently |

Separate synthetic, controlled-server, isolated native, ordinary native and
physical wake evidence in receipts. Physical suspend may require a later operator
window; it remains explicitly pending, not substituted by the fake-clock exercise.
Retain only allowlisted metadata/reasons, never prompts/tool outputs/raw callback
or terminal captures. Clean every isolated context and verify provider/session
lifetime independently afterward.

## S6 and independent follow-on tracks

Only after the producer artifact and required native/operational subset are
accepted, propose or perform a scoped managed selection within current user
authorization. Preserve direct diagnosis and previous candidate recovery. Unit
selection does not imply provider configuration, notification hooks or frontend
rollout. Report actual selected links/unit/state separately from source commits.

Optional signal work follows a separate pass: existing-only Codex subscriptions
with lifetime proof; bounded metadata-root inotify with overflow/rearm proof;
neutral bounded hook emitters and Claude callback correlation. Shared polling
is accepted independently, so unsupported native push never blocks basic fan-out.
An event publication wire would need its own correlation/loss/deduplication gate.

Then hand off API v1 plus accepted service access to Agent Plus in another task.
Keep host mesh/authentication/offline cache and action validation there or in
separate networking. Existing SSH and 8-MiB limits require explicit new-protocol
handling; a warm local view does not prove remote streaming.

The RLCD bridge migration is another consumer task: wire-3/service input,
urgency/admission, unknown state-episode ages, device framing/transport, reconnect,
firmware and physical readability. Native state entry/same-phase episode timing
is an optional producer capability with an independently versioned contract.
Neither the service view version nor conversation activity is its substitute.
