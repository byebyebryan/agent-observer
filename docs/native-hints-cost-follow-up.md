# Native hints: remaining producer cost gate

Date: 2026-10-07. The [delivery report](evidence/2026-10-07-native-delivery/REPORT.md)
records separately installed a9; normal Snap/Starship units select a8 polling.
This follow-up does not authorize provider-policy changes or frontend work.

The [subsequent a10 repair](evidence/2026-10-07-native-delivery/a10-catalog-scope.json)
removes unnecessary scans from nested transcript traffic. Identical installed
synthetic activity causes two extra history reads in a9 and zero in a10; primary
append and a focused native Claude workflow still pass. A10 is separately
installed on both hosts, without a repeated cost/operational gate or selection.
The remaining sequence below still applies; the a9 CPU/RSS numbers are not
silently reassigned to a10. Original targets remain pending explicit clarification.

## Evidence and decision

Controlled native wakeups improve runtime and conversation-age latency without
loading a saved session to observe it. Source loss/reconnect, daemon incarnation
changes, foreground questions and paired passive-listener retirement pass within
the recorded topologies. API 1, snapshot/watch 3, write 1 and service protocol 1
remain unchanged. These cases do not clear the resource gate.

Two sequential five-minute ordinary-store runs per host compare polling with
hints at the same configured cadences and reader count. Snap measured 4.13 versus
6.30 percent of one core, with peak aggregate RSS 124.9 versus 167.2 MiB. Starship
measured 2.00 versus 2.05 percent, with RSS 45.6 versus 67.6 MiB. Actual ordinary
traffic differed; Snap performed three versus eight Claude history jobs. The
observed CPU delta is not an equivalent-workload causal estimate. Both hinted
runs exceed the plan's provisional **aggregate** 64 MiB RSS target; the Snap
polling baseline already exceeds it. Incremental RSS was 42.4/22.0 MiB, which
must not silently replace that aggregate target. Harness `status=accepted` means
the measurement completed, not that this delivery gate passed.

One suppressed-output cProfile scan spent 0.946 of 1.114 seconds in SDK imports,
loading client/MCP/model machinery before read-only history projection. This is
a useful lead, not proof that bypassing SDK initialization is safe. The separate
[binding review](sdk-metadata-loading-review.md) now bounds that private SDK
dependency, preserves the immutable audit guard and requires equivalence/native
proof. Its separately installed a11 candidate returns identical projections on
31 real copied rows, reducing that sample's CPU from 0.833 to 0.184 seconds.
Synthetic companion/omitted-kind cases also agree. Raw history was never archived;
copied stores were removed. This is a dependency initialization repair, not a
new public API or provider-version compatibility filter.

The [a11 installed/native receipt](evidence/2026-10-07-native-delivery/a11-sdk-and-native.json)
adds three-turn independent event clocks, both-host Codex passive-listener
retirement and foreground Claude question/exit regressions. Event receipt is
measured separately from native-first-observation and provider transition time.
The [matched resource receipt](evidence/2026-10-07-native-delivery/a11-resources.json)
shows a11 saved-metadata CPU delta within one point, but real Claude turns add
2.311 points and miss that gate. Real Starship Codex turns add 0.766 points.
Aggregate RSS also exceeds 64 MiB. Source, artifact and native subsets therefore
do not authorize hint selection. The normal a8 units remain selected while the
CPU repair and explicit budget decision are completed. ChezmoI's optional hint
flags default off; a8 rejects enabling them.

A focused runtime profile spends 0.384 of 0.388 seconds in executable inspection,
including separately hashing the installed CLI and the same resident image.
A12 shares the existing provider/full-descriptor-signature cache only within one
collection. Opens, ownership, process birth, signature bookends and replacement/
mutation rejection remain mandatory. There is no persisted/cross-request image
cache or cached session state. Distinct surviving images are still independently
hashed. Its 317 source tests, public conformance and separately installed
ordinary Claude comparison pass. The [a12 native cost receipt](evidence/2026-10-07-native-delivery/a12-runtime-cost.json)
measures three scripted turns in each fresh polling/hint store: 1.270 versus
2.703 percent of one core, an incremental 1.433 points. Hinted peak aggregate
RSS is 87.840 MiB, versus 65.340 MiB polling. The CPU gap shrinks but still misses
one point; aggregate memory also misses 64 MiB. Native stores/authentication are
removed, and a8 remains selected. This is measured workload evidence, not a
universal worst-case bound.

The next focused a13 repair implements the scheduler's already declared 500 ms
settling window. Previously the first hint dispatched immediately; a hint during
an active collection also lost that window. Anchor the delay to the first
unconsumed hint so continued traffic cannot postpone work indefinitely. Periodic
reads can still run earlier, one-second runtime/ten-second history minimum gaps
remain, and failure backoff and provider fairness stay in force. Deterministic
clock tests cover both bursts and late hints during an active job. The CPU and
latency targets are unchanged; a new frozen native measurement is required.

## Focused Claude scheduling filter

A14 is a separate proposed repair following a13's measured CPU miss. The owned
Claude feed may read bounded registry/job metadata solely to decide whether to
request a full collection. It reuses the adapter's pure field parsers; it never
calls the adapter's process/image or observation functions and publishes no
metadata facts. The publisher still accepts only complete authoritative worker
results with the existing scope/generation/lease checks.

Keep only bounded in-memory SHA256 fingerprints, not raw payloads or session
state caches. Ignore noncontributing detail/heartbeat fields and nonzero pending
count churn. Busy/shell are one scheduling class because both project to working;
retain attention changes, identity, user title/cwd, job state/tempo, pending versus
zero work, question presence and terminal clocks. Registry clocks remain part of
the fingerprint for unavailable, mismatched or failed/stopped linked-job
contexts, where the clock relation can change an ambiguity predicate. Changed
or unfamiliar kinds/waits and malformed metadata always wake reconciliation.
These are wakeup predicates, never support or action authority.

Open exact owned watched-directory descriptors and no-follow/nonblocking files;
require regular owned/nonwritable bounded files with stable descriptor/path
bookends. Limit each input to 128 KiB, depth 16 and 8192 decoded nodes. Read a
unique runtime file once per inotify chunk, with at most 64 fingerprint reads;
excess files force a conservative wakeup. Failed/deleted reads forget the old
digest so recovery cannot be hidden. Bound fingerprints to 4096 entries; overflow,
watch loss and runtime rearm clear them. Transcript files continue to produce
history wakeups without being read by this filter. Periodic reconciliation and
all runtime/history timing/resource gates remain unchanged.

Controlled tests must cover unchanged metadata, identity/attention/title/cwd and
terminal changes, unsupported shapes, failed-clock relations, read recovery,
oversized files, FIFO/symlink rejection, overflow and bounds. Freeze separately
and repeat matched single/mixed-provider native cost plus working/waiting,
foreground/background questions, activity/rename, reconnect and listener lifetime
before accepting the filter. No normal hint-unit selection follows from source
acceptance or the a13 results.

The [a14 installed/native receipt](evidence/2026-10-07-native-delivery/a14-filter-and-host-cost.json)
passes these focused state, question, activity, rename, reconnect and lifetime
checks, including a held background question reaching cached blocked state in
0.789 seconds. The matched Snap publisher still adds **2.086 CPU percentage
points** and samples 131.402 MiB aggregate RSS (47.824 MiB incremental).
Claude runtime collection counts fall, while both providers still require extra
history jobs. All private stores/authentication are removed. A14 remains
unselected; the original CPU and aggregate-memory gates are not accepted.

## Memory decision and host scope

The pending budget question distinguishes two implementation directions. Neither
choice has been accepted by elapsed time or by a suggested-answer default.

| Decision | Consequence before selection |
| --- | --- |
| Keep 64 MiB aggregate RSS | Review a different collection/helper architecture. Current isolated Claude hints already exceed the limit, and the ordinary Snap polling baseline also exceeds it. Do not inline the guarded SDK into the publisher or discard process/deadline isolation as an incidental memory optimization. |
| Set 64 MiB incremental RSS | Retain absolute RSS alongside polling-to-hints overhead and prove the revised limit on matched native workloads. This is an explicit new budget, not acceptance under the original target. CPU, latency, cleanup and rollout gates still apply. |

The one-point CPU target applies to the configured host publisher and its owned
live/reaped descendants. Separate successful Codex and Claude cases cannot clear
Snap's combined-provider gate. The private `native-mixed-hint-cost-case` therefore
uses both providers in one isolated publisher, 31 synthetic saved Claude rows,
three scheduled native turns per provider, three healthy readers plus one slow
reader and 100 cached reads per mode. Both modes use fresh owned stores and the
same scripted population/schedule. Native durations may differ; record the
observed workload rather than claim deterministic native events or a universal
worst-case limit. Outer cleanup must remove both providers' borrowed auth/history
even on a failed case. This proof introduces no public command or frontend work.

## Next bounded producer pass

### Reviewed next cost boundary after a14

A private read-only spike against the installed a14 Claude runtime collector
compares five warmed samples per mode. Baseline mean process CPU is 0.393 seconds;
reusing a previously hashed image with an open descriptor anchor is 0.00128
seconds. The three image anchors are closed afterward. Exact bounded identity,
known work/presence, wait reason and activity projections agree across samples.
The [spike receipt](evidence/2026-10-07-native-delivery/anchored-image-spike.json)
records this research separately from installed-artifact acceptance. It patches
only the private proof process; it implements no production cache, worker
transport, failure protocol or history changes. It has no causal host-budget
claim and does not establish adversarial safety.

The demonstrated remaining lead is repeated image hashing across independent
collection jobs. Prefer reviewing a bounded **descriptor-anchored digest memo**
before splitting history from runtime or extending runtime hint delays. The
memo would retain only an open image descriptor, its full validated file
signature and diagnostic digest. It must never retain session state, provider
payloads, transcript metadata or work evidence. No provider/hash allowlist is
introduced. Cache use cannot skip current executable-path/UID/process-birth,
regular-file/mode/size or before/after descriptor checks. The still-open anchor
prevents inode reuse from equating a different image with an old digest; changed
signature, unsafe ownership/mode, missing anchor or unknown input forces a fresh
inspection or explicit failure. An on-disk signature/digest cache without these
anchors is outside this proposal.

Existing owned workers are short-lived, so a production implementation needs a
separately reviewed private descriptor-transfer protocol. Keep hashing/native
I/O out of the publisher's IPC loop. Transfer only positively owned read-only
image descriptors and bounded signature/digest records between the publisher
and its exact spawned collection worker. Bound entries to 32 per provider,
messages and inherited/received descriptors; close all rejected, evicted,
failed-worker and shutdown descriptors. Never transfer these descriptors into
the guarded SDK helper. Only a successful validated current-generation worker
may return memo entries; timeout, malformed/truncated transfer, wrong scope,
changed incarnation or publisher replacement must not preserve unverified
entries. Misses retain the current hard collection deadline and hashing limits.
Public snapshots, service frames, component leases and native observation clocks
remain unchanged. This is an implementation proposal, not an accepted protocol.

The concrete private transfer uses one unnamed Unix sequenced-packet socket
pair per positively spawned, isolated collection worker. Only that child's
socket descriptor is inherited; the existing bounded stdin request carries its
descriptor number. The publisher sends one initial packet and the worker sends
one return packet. Each has an exact protocol/provider/records shape, at most
16 KiB and 32 read-only image descriptors via `SCM_RIGHTS`. A record carries only
the full file signature and digest; version diagnostics are reconstructed from
that digest. Received descriptors are close-on-exec, regular owned/nonwritable
images within the existing size bound, with a matching full descriptor signature
and read-only access. Reject mismatched counts, duplicate signatures, unexpected
ancillary records, truncation and malformed shapes, closing every received FD.

Publisher send/receive must be nonblocking and never hash an image. Receive the
return only after the exact worker has exited and its owned helper group has
been stopped. Install returned entries only after the snapshot passes the
existing schema/store/scope/generation checks and a known runtime context is
unchanged; otherwise discard them. A failed optional transfer clears the memo,
without changing an independently valid observation result. Child receive/send
remain bounded by the outer collection deadline. The memo evicts least recently
used entries at its fixed limit; changed signature or failed anchor checks close
the old entry and perform a fresh inspection. All channels, queued descriptor
rights and anchors close on rejection, failed spawn, worker failure/timeout and
publisher shutdown. The SDK subprocess keeps `close_fds=True` and receives none
of these descriptors. This protocol remains private; it is not a new consumer
capability or a change to service protocol 1.

Before a source checkpoint, independently exercise same-image reuse, mutation,
replacement and surviving old workers, read-only descriptor validation, UID/mode
changes, cache bounds/eviction, truncated or inconsistent transfer, worker and
publisher death, and generation/incarnation reset. Review exceptional cleanup
as carefully as the hot path. Then freeze a new candidate and repeat public
conformance, independent native state/age/title/questions/reconnect/lifetime
and matched combined Snap plus Starship cost. The spike's CPU reduction must
not be substituted for those host measurements. Retained descriptors add a
bounded FD cost and do not solve the unanswered aggregate-memory decision.

A history-only collector is an alternative architectural branch, not an
incidental `include_runtime=False` change. Current history workers also establish
live title/cwd, workspace association, identity ambiguity, new-turn outcome and
runtime context. Dropping these reads requires a separate merge/freshness design
and independent equivalence proof. Reusing runtime facts from a full history job
also requires explicit component receipt and pending-hint coverage rules; a
history refresh cannot casually renew old runtime or conversation evidence.

### Acceptance sequence

1. **Establish equivalent measurements.** Use owned isolated native stores and
   identical scripted activity, history population and readers. Compare quiet
   startup/steady state separately from active runtime/history workloads. Include
   per-process CPU/RSS, live and reaped descendants, total authoritative reads,
   FD/process/inotify watch counts and hard collection deadlines. Ordinary-store
   acceptance supplements this controlled comparison rather than replacing it.
2. **Reduce demonstrated cost.** Profile runtime and history jobs independently.
   First consider supported metadata-only SDK entry or a bounded reusable
   read-only metadata worker, retaining audit guard, deadline, incarnation,
   output limits and publisher-death cleanup. Compare that complexity with an
   explicit larger aggregate budget. Do not add transcript caches, legacy
   reconstruction or unofficial SDK-loading shims without a separate design and
   evidence. Provider versions remain diagnostics; the reproducible SDK lock is
   an Observer dependency, not a provider compatibility allowlist.
3. **Settle the budget explicitly.** Preserve the original one-point incremental
   CPU and 64 MiB aggregate RSS results. Any revised budget is a visible design
   decision with absolute and incremental values, not retroactive acceptance.
   If the original budget is retained, meet it with a separately frozen candidate.
4. **Reaccept the candidate.** Run schema/reference consumers, controlled burst/
   loss/backoff/fairness, independent native ID/state/activity/title comparisons,
   foreground/background Claude and Codex on both hosts, saved unloaded rename,
   paired lifetime and periodic fallback. Measure correlated event arrival
   separately; source-level latest-hint/sample differences do not prove it.
5. **Complete P6.** Only after the gate passes, add the exact managed hint flags,
   verify old/new tuples, apply Snap then Starship, and exercise restart/crash/
   rollback/reselection plus a 30-minute multi-reader soak per host. Refresh
   preservation bookends and remove all owned native stores/authentication.

No frontend migration is needed to investigate this cost. Agent Plus and other
clients can independently consume selected a8's accepted read/write boundaries
and explicit cached service. Native entry repair, graphical focus, remote/device
transport, durable notifications and physical suspend/wake keep their own gates.
