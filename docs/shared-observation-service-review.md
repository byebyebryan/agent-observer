# Shared observation service: deep review

Date: 2026-10-06. Verdict: proceed to a bounded Observer-only implementation
under the [execution gates](shared-observation-service-execution-plan.md).
The [design](shared-observation-service-plan.md) is viable after the resolutions
below. This is design, source, research and controlled-exercise acceptance;
there is no implemented or accepted shared service yet.

## Scope and evidence

This pass inspected the current collector, native adapters, sampled watch,
strict API v1 facade, Agent Plus host reader/cache and RLCD requirements. It
measured the independently accepted a2 CLI using ordinary passive reads on
Snap and Starship, profiled Snap reads and exercised fixtures, deterministic
delivery models and disposable local Unix sockets. Ordinary provider settings,
hooks, runtimes, sessions and downstream files were unchanged.

The [evidence report](evidence/2026-10-06-shared-service/REPORT.md) contains
reproducible scripts, bounded results, artifact identity and exclusions.
These reads are not another independent session census. Prior accepted native
predicates remain the baseline; service lifetime, cancellation and multi-reader
effects still require independent native proof.

## Resolved findings

| Priority | Finding | Resolution / acceptance gate |
| --- | --- | --- |
| Required | Every watch/client repeats collection; provider reads run sequentially | Shared producer, independent bounded provider jobs and one publisher; S1–S2 |
| Required | A cached, schema-valid document can still say current after its source expires | Explicit source confirmation/expiry clocks and conservative expired view projection; S0–S2 |
| Required | Native phase time is not last confirmation time | Keep event/evidence clocks unchanged; track successful reads separately |
| Required | Snapshot capture followed by registration can lose an update | Capture/register atomically; write outside publisher transaction; S1 |
| Required | Slow readers can block a synchronous watch writer | Nonblocking fair delivery, immutable in-flight frame, one pending view, gap/resync or disconnect; S1/S4 |
| Required | Per-reader bounds alone permit large aggregate retention | Global byte/connection limits and independent decoded-object/worker memory budgets; S1/S4 |
| Required | Whole-history collection is expensive at monitoring cadence | Separate runtime monitoring, inventory, saved metadata and workspace cadence without losing provenance; S3 |
| Required | Freshness can survive machine sleep if it uses active-only elapsed time | Suspend-aware expiry, scope generations and independent wake proof; S1/S5 |
| Required | User-service sandboxing can hide native endpoints or change identity | Preserve required home/config/PID/mount context; prove scoped unit hardening; S4/S5 |
| Required | Existing wire limits leave no guaranteed service-envelope allowance | Independently bounded service wire and reader; preserve observation wire 3 unchanged; S0 |
| Consumer gate | RLCD needs state episode timing; API v1 provides conversation activity/evidence clocks | Unknown episode age initially; later source/timing contract gate; separate bridge migration |
| Optional | Passive all-session native push is not established | Shared polling first; independently prove optional signals without resume/start |
| Optional | Notification events require correlation/loss semantics beyond sampled views | No completion/attention event stream in first service protocol |

No required issue remains a reason to mix Observer and frontend implementation.
The gates are concrete work still to execute, not current operational guarantees.

## Source audit and performance

`cli._snapshot` invokes full collection for every direct read and watch sample.
Each watch owns its own `SampledWatch`. `collection.collect` runs providers in
sequence before composing a combined snapshot. A slow Claude history worker or
Codex endpoint therefore delays the combined result, even if another source is
healthy. The current watch stdout loop has a write deadline, but it is synchronous
within that client's collection loop; copying it into a shared publisher would
block everyone.

The collectors combine runtime and saved-history work. Codex's profile performed
62 RPC requests for 52 rows, with saved inventory contributing about 0.89 seconds
in that profiled read. Claude's saved-history worker contributed about 0.65
seconds; physical executable inspection/hash checks contributed about 0.37
seconds across nine calls. These checks establish actual artifact/process context:
optimization cannot replace them with a provider release allowlist or discard
ownership/incarnation checks.

| Host / providers | Samples | Wall time per full read | Child CPU per read | Rows |
| --- | --- | --- | --- | --- |
| Snap / Codex | 3 | 1.28–1.33 s | 0.28–0.31 s | 52 |
| Snap / Claude | 3 | 1.14–1.24 s | 1.14–1.23 s | 31 |
| Snap / both | 2 | 2.36–2.38 s | 1.41–1.42 s | 83 |
| Starship / Codex | 3 | 1.73–1.85 s | 0.32–0.34 s | 96 |

These are separate-process passive CLI samples with uncontrolled OS caches and
ordinary active work, not service latency percentiles or idle/maximum-load
benchmarks. Snap's combined read exceeded the current two-second watch interval.
Continuous full scans at that observed rate would consume roughly 0.6 CPU-seconds
per second, before fan-out. The estimate is arithmetic from this small sample,
not an always-on measurement. Sharing removes duplicate scans; cadence separation
is also needed for an efficient continuously running service.

Composition has another bounded but costly path: duplicate detection repeatedly
validates identity against prior rows. Profiling recorded 2,756 `identity_key`
calls for 52 Codex rows and 992 for 31 Claude rows. Source inspection confirms
quadratic comparison growth. S3 should use an indexed full-identity lookup while
preserving duplicate rejection and semantic validation. Reusing verified artifact
inspection across samples is a separate optimization with actual image/context
invalidation tests, not a reason to remove required guards.

## Contract and freshness decisions

API v1 snapshot/watch 3 and write 1 remain unchanged. Strict validation rejects
extra service fields; API v1's pure facade also must remain usable without adapter
imports or a running daemon. Introduce a separate service protocol, proposed
version 1, with bounded schema, semantic validation, independent reader fixtures
and an explicit compatibility policy. The service's protocol version and runtime
package version are not provider version support lists.

Separate three clocks: original provider evidence/event time; source-read
confirmation/expiry time; service delivery/liveness time. Claude can confirm an
unchanged state whose native timestamp remains old. Codex sampled evidence can
change its sample clock without a semantic state change. Neither service heartbeat
nor a new subscriber manufactures conversation activity or a state episode.

The envelope must describe service incarnation, monotonic view/transport sequence,
configured host/source scope, source sample age/expiry, attempt result and scoped
recovery. Freeze names/enums only with S0 fixtures. A failed source does not make
the service dead; a responsive service does not make the source current. A new
cached read returns the same collected view, without generating a new collection
ID/time. New source results or expiry can publish a new reconciled view with
their actual constituent provenance.

Initially expire a whole provider sample conservatively. Preserve original clocks
and last-known values while clearing current runtime/phase claims and blocked
reason. Coverage no longer proves current absence; retained names/history remain
visibly stale via the source envelope. The later monitoring/history split needs
internal field-to-source generation/dependency tracking and independent freshness
policies. Reusing `compose_snapshot` with old provider pieces and a new assembly
timestamp alone is insufficient. Current capabilities must reflect usable sampled
predicates, rather than stale success being advertised as usable observation.

The initial service envelope embeds snapshot 3. Existing direct watch 3 retains
its current sampled grammar and implementation. Accepted new reads can publish
replacement service views even when phase values stay unchanged; their source
receipts establish confirmation. Pure service heartbeats renew nothing. This
avoids interpreting an unchanged heartbeat from `SampledWatch` as a source read
receipt, or dropping confirmation changes that its semantic diff ignores.

Expiry occurs on the scheduler even without source events, before serving a
snapshot and before choosing a pending outbound view. Clients also need bounded
transport silence and explicit age accounting; receiving another cached frame
cannot reset a source's age. Host-local elapsed clocks cannot be subtracted
across machines. Networking must carry conservative originating-source age and
account for forwarding/reconnect uncertainty under its own acceptance gate.

No durable view cache is proposed initially. Cold start reports warming/unavailable
until actual source results exist; it does not produce a complete empty inventory.
Bootstrap and later failures publish healthy provider data independently with
explicit incomplete scopes. Service restart creates a new incarnation; reconnect
starts from a current full view, without historical replay.

## Scheduling, delivery and resource decisions

Use a single publisher and independent Observer-owned subprocess jobs, one
in-flight read per provider. Existing blocking reads and SDK helpers then have a
bounded cancellation boundary. Killing a job must never kill a provider or its
ordinary runtime. A hint arriving during a read increments a dirty generation;
completion schedules at most one follow-up, subject to debounce/rate limits.
Periodic discovery and source-expiry deadlines cannot be starved by hint storms.
Captured context generations reject late results after configuration/runtime
replacement. Clock ordering alone does not establish context continuity.

The first service stream carries canonical full views, including confirmed
children; public read clients apply existing child/projection/order policy after
reconciliation. Avoid separate provider reads or an unbounded encoded filter
cache per subscriber. Capture/register subscriptions atomically. Keep socket
writes and encoding outside short publisher transactions, with view ownership
and global memory reservation established before allocating a new encoded view.

An in-flight partial frame is immutable. At most one newer pending view may be
replaced. If delivered view versions skip, send explicit loss/replacement semantics;
then resume from the newest full view. A blocked writer exceeding its deadline is
disconnected. A healthy client's write budget and provider collection deadlines
must remain independent. Service health/gap information belongs in the new
envelope; existing watch frames remain strict and cannot silently gain scoped
fields.

The proposed 16-client/64-MiB encoded-retention limits are aggregate limits.
Sixteen distinct near-8-MiB in-flight views would exceed that budget: admission
or eviction/disconnection must enforce it, including transient allocations.
Shared immutable bytes help, but decoded Python objects, provider subprocesses,
input buffers, schema walks and encoding CPU need independent bounds and measured
RSS. The 8-MiB observation limit is not a guaranteed 8-MiB service frame limit;
the proposed envelope allowance is 16 KiB and requires worst-case tests. Plus's
current 8-MiB host stdout cap cannot ingest arbitrary service envelopes unchanged.

## Primary research and native source boundaries

Codex's official [App Server documentation](https://learn.chatgpt.com/docs/app-server)
distinguishes metadata reads from loading/subscribing. `thread/read` does not
resume/load the thread or subscribe the caller. Its lifecycle documentation also
describes last-subscriber removal and later unloading. The existing Observer
transport ignores unsolicited messages. This supports a cautious design:
accepted reads first; do not use `thread/resume` to obtain an observation feed.
The documentation is research, not proof that the installed shared daemon exposes
an existing-only all-session subscription or has identical lifetime behavior.
Even periodic read-only calls need sustained native lifetime proof: the first
service gate must compare idle retirement with and without Observer sampling,
rather than infer lifetime passivity from a short successful read.

Claude's [hook reference](https://code.claude.com/docs/en/hooks) makes default
command hooks synchronous and documents limited Agent View background callback
delivery. Asynchronous command hooks avoid blocking the turn, but their configured
timeout is not enforced. A helper therefore needs its own hard bounds and neutral
failure, even if hook execution is asynchronous. Stop can be followed by continued
work, as the existing S6 proof established. Manager callback target correlation
and complete question/completion coverage remain unproved. Hooks initially serve
as refresh hints, not authorization or a complete native event stream.

Linux [Unix socket documentation](https://man7.org/linux/man-pages/man7/unix.7.html)
supports pathname permissions and kernel peer credentials for connected streams.
Use a 0700 parent, 0600 socket and expected UID. Abstract sockets do not provide
the same pathname permission boundary. Credentials establish the local peer,
not provider event truth or host-name attestation. A stream handles large views
through bounded framing, partial-read/write handling and deadlines; small
datagrams are not an 8-MiB-view transport.

Linux [inotify documentation](https://man7.org/linux/man-pages/man7/inotify.7.html)
documents event coalescing, queue overflow and directory watch races. Signals
cannot count native episodes. Overflow, replacement or invalidated watches must
cause explicit reconciliation and rearming; absence of events is not freshness.
Avoid an initial recursive transcript watcher. Any optional watcher should use
bounded configured metadata roots and retain periodic reconciliation.

Linux [clock documentation](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)
distinguishes active-only monotonic time from suspend-inclusive `CLOCK_BOOTTIME`.
Use the latter for freshness expiry on the supported Linux hosts. Wall-clock
jumps cannot extend a source lease; native wall timestamps stay diagnostic/native
evidence. A fake-clock exercise checks the rule, not physical suspend behavior.

Python's [selectors documentation](https://docs.python.org/3/library/selectors.html)
provides a standard-library readiness loop for nonblocking local IPC. This is
the recommended initial transport implementation; it does not itself provide
fairness, bounded buffers or worker cancellation.

Installed systemd 262 manuals for
[socket](https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html),
[service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
and [execution](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
were inspected locally. Socket units default to broad modes unless overridden;
`Accept=yes` creates per-connection service instances, defeating the shared
collector. `MaxConnections` is not an `Accept=no` fan-out limit. Defer activation
and enforce actual client limits in the service. Kernel peer PID with an activated
listener also cannot simply be assumed to equal the daemon's PID.

For a later user unit, start with explicit artifact selection, `Type=exec`, scoped
runtime-directory permissions and bounded restart behavior. `PrivateTmp` can hide
Codex's ordinary endpoint; `ProtectHome` can hide stores/runtime prefixes;
`ProcSubset=pid` hides required boot metadata. New PID/user/mount contexts can
break Claude worker evidence. Preserve the default-versus-explicit config selector:
forcing `CLAUDE_CONFIG_DIR` to the ordinary default path changes store identity.
Hardening and watchdog settings need capability proof; provider outage is not a
reason to restart an otherwise responsive service repeatedly.

## Consumer fit and remaining product boundaries

Agent Plus currently invokes one Observer snapshot per selected local/SSH host,
with host-authority checks and a capped response. It already avoids provider
fallbacks. A warm service reduces owning-host provider-scan latency; remote SSH
startup still costs time. Continuous remote subscriptions require a separately
validated networking/mesh component. Host route selection, offline view policy,
picker selection and terminal/action validation stay in Plus/its networking
layer. API v1 migration and service access are separate frontend checkpoints.

The RLCD dashboard currently uses a synthetic fixture workload, not a live
Observer/device transport. Its checkout's `projects/agent-dashboard/docs/ui-ordering.md`
requires oldest state first within blocked/waiting/working groups, including
distinct same-phase episodes and unknown timing after gaps. API v1 conversation
activity is a different datum. The existing `examples/rlcd_bridge.py` consumes
historical host schema 1, uses another ordering and caps input at 512 KiB; it is
a provisional projection, not an API v1/service client. Its replacement needs
its own input contract, explicit unknown episode ages, device admission/transport
and physical gates. Push supplies updates but does not supply missing state-entry
evidence.

Notifications also remain separate. State coalescing can omit an entire transient
blocked phase; sampled waiting does not prove a unique completion. Keep the
accepted callback normalizer/publication client independent until native event
correlation, loss, deduplication and origin routing are accepted. The shared
service initially has no notification publication or action endpoint.

## Review closure

The repository now has a captured design, explicit resolved choices, measured
cost motivation and a staged implementation plan. Required implementation proof
remains: service schema/independent parser, scheduler/fan-out under failures,
efficient split-source provenance, packaged artifact, same-user IPC/context,
ordinary/isolated native lifetime comparisons, sustained multi-client load,
service restart/source replacement and actual suspend recovery. Optional native
signals, managed selection, remote networking, frontend/device integration and
native state-episode timing remain separately gated. No provider release pinning
or legacy OpenCode path is added.
