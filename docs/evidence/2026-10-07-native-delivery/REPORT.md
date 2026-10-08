# Native-assisted Observer delivery

Date: 2026-10-07. Status: P0/P1 accepted; P2-P4 implemented with bounded
controlled/native proof. Separately installed a9 passes native latency/recovery/
lifetime subsets; P5's resource gate is not accepted. P6 hint rollout and its
30-minute managed soaks are withheld. P7 hands off selected a8 with explicit limits.
Execution follows the [next delivery plan](../../observer-next-delivery-plan.md).

## Baseline

Normal selection is a7 on both hosts. Six-target/artifact/live verification passed
independently on each. Ordinary Codex CLI is 0.160.1; both owning managed daemons
are 0.161.0. Snap Claude is 2.1.292. Versions and hashes are provenance only.
The [metadata comparison](baseline.json) brackets the installed cached CLI with
independent native reads, retaining separate runtime/history receipts.

Codex membership, identity, activity and proved runtime phases agree: 50 saved
rows / 2 loaded user conversations on Snap; 93 saved / 3 loaded user conversations
on Starship. Older unknown kind and unloaded runtime remain unknown. Snap Claude
proves four active user conversations. Its partial saved inventory includes two
Observer-only unknown rows and omits the previously identified setup-only entry.
Activity on the working conversation trails native history by the configured
120-second cadence; follow-up samples are reported separately, not normalized.
This is the latency problem native history wakeups must address.

No ordinary provider action occurred. Provider settings, frontend/external pin
hashes, command links and unit identities were captured privately before work.
Native action proofs will use masked disposable namespaces; borrowed
authentication/history and owned test processes must be removed before handoff.

## Checkpoints

P1 selects the independently accepted a8 on both hosts. The [operations receipt](a8-operations.json)
records exact artifact, profiles, unit/process identities, restart, rollback and
reselection. Rollback snapshots remain in the stated private persistent paths.
The helper now separately verifies the prior artifact, six-target render, exact
interpreter/arguments and PID birth. Prior publisher warming does not obstruct
ownership verification; the selected publisher must still pass readiness.
Both chezmoi source checks passed. P1-stage bookends retain provider settings and
frontend pins; closing configuration drift is reported separately below.
The [fresh direct comparison](a8-direct.json) keeps independent gaps/races explicit.

P2 adds the bounded epoch/component/reason pipe, owned helper cleanup, optional
private diagnostics, 1-second runtime / 10-second history hint cooldowns and
failure backoff that bursts cannot bypass. Controlled pipes prove obsolete epochs,
malformed/oversized messages, one pending bit, fair history, unchanged observation
receipts and publisher-death cleanup. No native hint candidate is selected.
P3 implements a long-lived passive initialized Codex peer on the existing owning
endpoint, whitelisting global start/status/name hints. P4 watches bounded Claude
registry/job/project directories, including open-file append, atomic replacement,
new directories and overflow/rearm. Unknown content is discarded. No frontend
change is part of this delivery.

## Frozen artifact and native subset

A9 is `0.4.0a9`, source `c2f3754353cb72cd9afc644d9aba1ab296987875`, wheel SHA256
`8165f9400fadaa50f5d95e95f578630492791a74f81ba417cd5f6faf89a36497`, installed
separately at `~/.local/share/agent-observer/0.4.0a9-8165f9400fadaa50` on both hosts.
The [manifest](../../../artifacts/observer-0.4.0a9.json) and
[artifact/reference receipt](a9-artifact-and-consumers.json) retain byte/profile/
entrypoint/schema validation, independent public consumer and capacity checks.
Snap uses source-only Claude SDK history; Starship uses core. API 1, snapshot/
watch 3, write 1 and separate prerelease service 1 are unchanged. Diagnostics are
bounded private operator JSON outside the public frame; no new fixture fields
or consumer decoder changes are required.

The [native receipt](a9-native.json) contains actions only in independently
verified disposable namespaces masking ordinary stores. Coherent private Codex
client/server contracts use the inspected cached 0.161.0 executable; ordinary
0.160.1 package entry and provider policy are unchanged. Claude is 2.1.292 on Snap
only. These versions/hashes identify the proof, never a compatibility allowlist.

| Case | Independent installed result |
| --- | --- |
| Codex Snap runtime / activity | Seven runtime samples p95 1.407 s; five history samples p95 1.422 s; three working/completed turns, exact new ID and rename age |
| Codex Starship runtime / activity | Runtime p95 1.135 s; history p95 1.093 s, same bounded workflow |
| Claude Snap runtime / activity | Runtime p95 0.801 s; history p95 9.443 s, three background turns, exact ID and rename age; Claude-only publisher |
| Foreground Claude question | Positive native question/registry predicate reaches cached blocked in 0.988 s at 30/120 cadence; three held samples; native prompt `/exit` recognized independently |
| Background Claude question | A9 direct-read regression retains three held blocked/question samples; this is not generic-dialog or full event latency proof |
| Unloaded saved Codex title | Snap 10.159 s / Starship 10.097 s from explicit isolated rename to cache; no load/resume, exact loaded sets and conversation ages unchanged |
| Owned feed death | Exact publisher helper killed; a new source reconnects and retains the conversation clock, both Codex hosts and Snap Claude |
| Native daemon death | Exact isolated owning daemon killed; runtime becomes unavailable/unknown in 0.943 s Snap / 0.859 s Starship; offline observation does not start it; explicit isolated New restores a new feed incarnation |
| Passive listener lifetime | Candidate feed held while the observed session and paired quiet control retire on both hosts; retirement does not establish general parked inference |
| Attached background `/exit` | Recognition remains unproved; retained native job done/idle, worker still present, public running/waiting and unchanged age |

Native-to-view time begins at the first independently observed qualifying native
fact and brackets it before/after the cached read. Samples are small controlled
coverage, not an all-transition guarantee. Source hints contain no conversation
ID, so latest-hint/component-sample differences are signed diagnostics and can
be negative; **event-arrival-to-view latency is not claimed**. No native input
question is answered. The terminal output is drained and never archived.

## Resource gate and withheld rollout

[Resource receipts](a9-resources.json) contain two sequential five-minute passive
ordinary-store runs per host, three independent healthy readers plus a slow
reader, and 100 cached CLI reads per run. Every healthy reader reports zero
errors. The harness completion status is separate from delivery acceptance.

| Host | Poll CPU / hints CPU, one core | Poll RSS / hints RSS, MiB | CPU delta / RSS delta | Hints read p95 |
| --- | --- | --- | --- | --- |
| Snap, 30/120 s | 4.13% / 6.30% | 124.9 / 167.2 | +2.17 points / +42.4 MiB | 98.6 ms |
| Starship, 20/60 s | 2.00% / 2.05% | 45.6 / 67.6 | +0.05 points / +22.0 MiB | 80.7 ms |

Snap's observed CPU delta exceeds the provisional one-point target. Ordinary
traffic differed and Claude history jobs rose from three to eight, so an
equivalent-workload causal comparison remains pending. Both hinted runs exceed
the provisional **aggregate** 64 MiB target; the Snap polling baseline already
exceeds it. Smaller incremental RSS does not clear an aggregate gate. One
suppressed-output profile identifies SDK import machinery as most of a history
scan's measured time; no unofficial SDK-loader workaround was added.

The [cost follow-up](../../native-hints-cost-follow-up.md) records the bounded
remaining producer pass. A9 is not selected. No hint flags are added to the
normal unit, and P6 restart/crash/rollback/30-minute hint-unit soak is not claimed.
The accepted a8 normal baseline stays active on both hosts. Its existing shared
service still pushes polling-derived current views; native hooks and ordinary
provider settings are not changed to make a candidate gate pass.

## Native workflow verdicts and client handoff

Ordinary cold Codex New/Resume still needs provider-management repair. Both
`/opt/openai-codex/bin/codex` files are owned by Arch `openai-codex-bin 0.160.1-1`;
the native cache owns the currently running 0.161.0 daemon. The managed chezmoi
portable template selects daemon auto-start and leaves the disputed feature
at native defaults. The prior independent matrix isolates `api_key_model_discovery`
default skew; this delivery again proves the coherent cached client/server pair
privately. The smallest proposed ordinary repair is package/client feature
coherence followed by isolated cold New/Resume reproof, then a separately scoped
provider rollout. Do not overwrite the package-owned binary, pin native releases
in Observer, change every session, or silently inject a feature override into
the observer/writer. Ordinary package updates and any necessary daemon/session
continuity belong to that separate delivery.

Saved Claude Resume and positively bound background attach remain the accepted
writer routes. No provider-supported exact arbitrary live-foreground attach route
has been established; retain `unsupported_resume_route`. Foreground prompt exit
is recognized, while attached-background command recognition is unresolved and
cannot mean worker stop. Explicit native stop with a complete absent-worker/
terminal-job predicate remains the supported parked route. Generic dialogs,
Codex unloaded/parked inference, unknown older child kind, Claude setup-only
history and current terminal binding keep their explicit limits. No legacy
reconstruction or heuristic ID/title/cwd/PID binding is added.

The [fresh selected CLI comparison](final-a8-comparison.json) agrees on all 50
Codex saved rows / two active conversations on Snap and 93 / three on Starship,
including proved state and age. Claude's three current Snap workers agree; its
saved comparison retains the known setup-only omission and one extra unknown
row. This is partial saved coverage, not a full native catalog guarantee.

The [current producer handoff](../../shared-observation-service-handoff.md)
binds exact selected a8, the default local socket, independent source leases,
disconnect/reconnect behavior, child filters, age/order and separate writer
authority. SSH fresh-sequence reconnect passes against selected a8. Agent Plus
still uses its previous wire-2 reader and receives no implementation/selection
change here. A separate consumer pass can use a8 polling now; it does not need
to wait for or repair a9's cost gate through frontend work.

## Cleanup, preservation and source delivery

[Closing receipts](cleanup-and-preservation.json) verify all five owned native
namespaces stopped and their stores, borrowed authentication and history removed.
Owned candidate services/readers have exited. Both selected a8 units pass final
artifact/six-target/ownership/readiness verification; rollback snapshots remain
private at `~/.local/state/agent-observer/operations/2026-10-07-a8` on each host.
Ordinary Codex daemon PID/birth matches the initial incarnation on both hosts.
Claude settings, chezmoi external pins and Agent Plus links match their initial
hashes/targets. No frontend/provider/hook deployment accompanies this work.

Ordinary `.codex/config.toml` hashes changed on both hosts during the loop.
Captured metadata cannot attribute that drift; whole-file preservation is not
claimed. Daemon auto-start remains enabled. No ordinary config write is part of
the Observer delivery or the isolated proof actions; the drift is retained and
not overwritten to make bookends appear equal. Ordinary Claude inventory changed
from four to three active conversations during the loop, and the final
comparison reflects that current native evidence.

Canonical Observer source commits are local. Immutable a8/a9 artifacts and the
six scoped Observer managed targets are delivered to both hosts. Starship's
checkout and unrelated dirty chezmoi migration state are retained; installed
artifact acceptance does not claim that its Observer checkout was synchronized.
No source push, public package release or hosted CI result is claimed.

## Follow-up: unnecessary nested history wakeups

Source review found a concrete additional cost: a9 watches nested project/session/
subagent directories, although the authoritative saved-history census reads only
project-level transcripts. Child transcript writes therefore request full scans
without changing the primary catalog. The repair scopes directory watches and
history events to the same surface as discovery, retaining periodic reconciliation,
overflow/root replacement recovery and direct job-state/registry wakeups.

This is frozen separately as `0.4.0a10`, source
`2cd1bbc693c5c4553e61c0f177d2fe2a0e739271`, wheel SHA256
`e57b3e947e731011ad1d470cb83740faf5057dc0a900458a759ed1d6688e2242`, installed
at `~/.local/share/agent-observer/0.4.0a10-e57b3e947e731011` on both hosts.
The [manifest](../../../artifacts/observer-0.4.0a10.json) and
[repair receipt](a10-catalog-scope.json) distinguish installed controlled and
native evidence. Both artifact profiles pass byte/schema/entrypoint verification.

Identical controlled synthetic filesystem activity produces two extra history
reads for a9 and zero for a10 after 100 nested transcript writes; a primary
append reaches a10's cached native-format activity clock in 1.064 seconds.
This is installed filesystem integration, not native workflow proof. A separate
disposable native Claude run accepts New, working/waiting, conversation activity,
rename-age preservation and owned-helper reconnect at 30/120 cadence: three
runtime samples p95 0.796 s and three history samples p95 1.981 s. One turn is
focused regression coverage, not a replacement for a9's broader native matrix.
Codex adapter/feed and shared scheduler/runtime production bytes are unchanged
and explicitly compared in the receipt; no additional Codex native claim is made.

The full resource comparison and 30-minute operational soaks are **not rerun**
or accepted for a10. Removing unnecessary reads is a demonstrated source repair,
not proof the original CPU/RSS targets now pass. Selected a8 stays unchanged.
The additional sixth native namespace is stopped and borrowed credentials/history
removed; both synthetic publisher processes and their owned history store are
also removed. The current memory-budget clarification is pending; the original
aggregate target remains in force and no hint-unit rollout occurs.

## Follow-up: SDK initialization and correlated event clocks

A11 is frozen from `28179263ea45d2315350aad0061f52d13bdefb33`, wheel SHA256
`80b3f82e577b566656b4b3752e0057f89aa46baa23c9fa7742d0d7b9128bb923`,
installed separately on both hosts at
`~/.local/share/agent-observer/0.4.0a11-80b3f82e577b5666`.
Its [manifest](../../../artifacts/observer-0.4.0a11.json) and
[installed/native evidence](a11-sdk-and-native.json) bind SDK metadata-only
initialization under the [reviewed boundary](../../sdk-metadata-loading-review.md).
The existing SDK implementation, immutable audit guard, one-request helper,
deadline, output cap and census stay intact. SDK dependency coupling is explicit;
provider support remains contract based.

Full and narrow loading return exactly the same 31 allowlisted rows from 34
privately copied real history files, with stable copy bookends. The sample uses
0.833 versus 0.184 CPU-seconds. Synthetic duplicate-companion and SDK-omitted
meta-only cases also agree. Copied histories are removed, and neither prompts nor
raw payloads are archived. Source checks pass 316 tests with one optional skip
and 75 Markdown files; installed profile/bytes/entrypoints and pure schema/CLI
consumer checks pass. API 1, snapshot/watch 3, write 1 and service 1 are unchanged.

Three-turn native cases retain stable exact-ID native brackets, require each
new activity clock to differ from the prior turn and separately correlate event
receipt to the cached view. Runtime event p95 is 1.431 s for Snap Codex, 1.233 s
for Starship Codex and 0.703 s for Snap Claude; history p95 is 2.299, 1.982 and
10.164 s. Each provider has six correlated runtime and four history samples.
Codex uses exact-ID status/name events. Claude binds file events through
subsequent independent exact-ID metadata. These are receiver clocks, not exact
provider transition times or lossless delivery claims. The original signed
latest-hint/sample diagnostic remains distinct. Foreground Claude question/exit
passes with three held samples and a 1.115 s cached question delay. Paired Codex
retirement passes on both hosts with held native feeds and an extra initialized
peer, observed unload at 61.448/60.787 s and a subsequent quiet-control probe.

Ordinary a11 direct CLI/native comparisons agree on Snap's 50 Codex saved IDs /
two active conversations and Starship's 93 / four. Snap Claude has three current
workers and 31 projected saved rows; setup-only omission, unknown older kinds and
other unproved dimensions remain explicit. The failed initial Claude test
assumed an empty background job already had proved waiting state; that harness
precondition was removed without changing producer predicates. All three native
fixtures, control stores and borrowed authentication are removed.

The [matched resource evidence](a11-resources.json) distinguishes saved-metadata,
real native-turn and ordinary-traffic measurements. Five minutes per mode with
31 identical synthetic histories, three healthy readers, one slow reader and
100 cached CLI reads gives a10 incremental CPU +0.090 points quiet / +1.373 active,
and a11 -0.004 / +0.513. The active workload appends seven primary records and
700 nested records; all actions and reader errors are checked. Idle collection
counts match after startup. A11 observed RSS is 87.3 MiB quiet / 82.2 active,
with incremental RSS 42.5 / 37.6 MiB. Every synthetic history subtree is removed.

Real native cost uses fresh, masked namespaces per mode and identical scheduled
three-turn stimuli. Snap Claude adds **2.311 CPU percentage points**, still above
the original one-point gate, with 87.3 MiB hinted RSS and 42.3 MiB incremental RSS.
Starship Codex adds 0.766 points, with 65.3 MiB hinted RSS and 21.8 MiB incremental
RSS. These are small finite workloads, not universal performance bounds. The
native cases own one live session, and Claude additionally has 31 synthetic
saved rows; real model timing can differ. Both modes' positive working/completion/
new-activity predicates are independently checked. All native stores/auth are
removed after each mode.

Ordinary five-minute hinted runs measure Snap CPU 8.18 percent / RSS 129.1 MiB
and Starship 2.77 percent / 67.5 MiB. They have no same-traffic polling pair and
cannot establish an incremental CPU estimate. All six healthy readers report
zero errors/gaps. Separate 180-second owned process/FD/inotify windows show bounded
helper counts and stable 18 Claude directory watches; per-role maxima are not
simultaneous sums. There are no persisted FD paths or raw process arguments.

P5 remains open for **CPU and aggregate memory**, so P6 stays withheld. The local
chezmoi flag support is committed as `7c15b3e`, defaults off and renders unchanged
a8 unit bytes. Invalid boolean modes and unsupported a8 hint flags reject before
selection; explicit true binds exact flags/private diagnostics to the artifact.
No normal unit, provider policy, hook or frontend changes in this follow-up.
The pending memory-budget choice does not waive the CPU gate. A further separately
frozen a12 repair shares installed/resident image digests within one collection
only, preserving ownership/signature/birth bookends; its native cost gate is still
being measured and is not reassigned the a11 results.

## A12 runtime digest-sharing acceptance subset

Source `8ffd8e6`, wheel `4bc275dd69fdc11bed1eb81d2883e505e972be963d7cb2c2556a7e63666d0a5f`,
and both separately installed prefixes verify; 317 source tests and pure public
API conformance pass. Two independent ordinary Claude comparisons retain the
31 projected/32 native saved rows, three live workers, matching known phase and
conversation clocks and explicit setup-only/unknown history coverage. The
[a12 resource receipt](a12-runtime-cost.json) records matched scripted native
turns, three healthy readers and 100 cached reads per mode, no reader gaps or
errors, and complete removal of private stores/authentication. CPU overhead is
1.433 percentage points and hinted aggregate RSS is 87.840 MiB. Both original
resource gates remain unmet, so selection stays a8 and P6 remains withheld.
A13's subsequent anchored debounce is a separately tested producer repair;
it has no native acceptance yet.

## A13 debounce and combined host acceptance subset

Source `521fb7a`, wheel `bf611f5ec99f1991257295a9dad964880b44f81d6f9261f5b633e43e5132d1d0`,
and both installed profiles verify. Its 320 source tests and pure public API
conformance pass. The [bounded receipt](a13-debounce-and-host-cost.json) includes
three-turn independent event clocks on both Codex hosts and Snap Claude,
foreground question/exit and paired passive-listener retirement on both hosts.
All focused latency cases pass the unchanged runtime/history targets. The
500 ms anchored debounce preserves periodic cadence, backoff and fairness.

Matched five-minute Claude-only cost improves to +1.156 CPU percentage points,
still above one; Starship Codex measures +0.685. The separate two-provider Snap
case uses three scheduled native turns per provider, one publisher, three healthy
readers and 100 cached reads per mode. It measures 2.323 versus 4.653 percent of
one core: +2.330 points. Hinted sampled aggregate RSS is 109.289 MiB and polling
67.043 MiB. No reader gaps/errors occur. This combined result independently
fails the host gate; separate-provider results cannot substitute for it. All a13
namespaces, borrowed authentication/history and paired control stores are removed.
Normal a8 selection remains unchanged. A14's subsequent scheduling fingerprint
repair is separately frozen; its native/resource acceptance remains pending.

## A14 scheduling-filter acceptance subset

Source `724b418`, wheel `283e1d1be5011814269e0d4e7e529c7d0f4bd9f90a56108a30bdc0939bb6394f`,
and both installed profiles verify. Its 327 source tests and pure public API
conformance pass. The [bounded receipt](a14-filter-and-host-cost.json) records
three-turn state/activity, unchanged-age rename and reconnect checks on both
Codex hosts and Snap Claude. Independent event-receipt runtime/history p95 is
1.866/2.335 seconds for Snap Codex, 1.795/2.563 for Starship Codex and
1.136/9.900 for Snap Claude. These are exact-ID event receipt measurements,
separate from native-first-observation and provider transition time.

Foreground Claude question/exit passes. The separately held background question
reaches a cached `blocked/question` view 0.789 seconds after independent native
detection and remains bracketed across three samples without answering it. This
case makes no event-arrival latency claim. Paired Codex retirement with a held
passive peer passes on both hosts: observed unload at 76.080/61.718 seconds,
with the quiet control absent at its first delayed probe. The control establishes
absence after unload plus a margin, not an exact matching retirement time.

The matched two-provider Snap cost pair retains three scheduled native turns per
provider, three healthy readers, one slow reader and 100 cached reads in each
five-minute mode. Polling uses 2.338 percent of one core and hinted collection
4.425 percent: **+2.086 percentage points**, still above one. Claude's measured
runtime jobs fall to 15 versus polling's ten after startup; history jobs are
nine versus two. Codex performs 16 runtime/eight history jobs versus ten/two.
The fingerprint filter reduces redundant runtime wakeups but cannot eliminate
required history refreshes. Sampled aggregate RSS is 83.578/131.402 MiB,
an incremental 47.824 MiB. Both original resource gates remain unmet. RSS samples
are not hard maxima, and different runs' brief peaks must not be compared as
proof of a regression. All healthy readers report zero errors/gaps.

All eight a14 native namespaces, their paired controls, borrowed authentication
and native history stores are removed; physical store absence was independently
checked. Both normal a8 unit PIDs, links and managed selection remain unchanged.
Snap's late configuration bookend matches. Starship's formerly present Claude
settings file is absent at the final bookend, an unattributed ordinary-state
change; the proof performed no ordinary provider action or restore. It is not
reported as unchanged preservation. P5 and P6 remain open, and the memory-budget
question remains unanswered.

The final [ordinary selected-CLI comparison](a14-closing-selected-baseline.json)
uses two independent native brackets per provider/host. Selected a8 reports
50 saved/two loaded Codex identities on Snap, 93/two on Starship and 31 projected/
32 independently enumerated Claude rows with three active workers on Snap.
Known active identity, work state and conversation age agree. The same one
unresolved Claude saved-only membership candidate recorded in a11/a12 remains
omitted by the SDK projection and explicitly reported; 30 Claude activity clocks
are independently established. Older Codex saved rows retain unproved kind and
inactive-runtime classifications. Attention/activity ordering, human age,
child-filter options and exact-reference lookup pass. These are selected direct
CLI checks, not new cache-cadence or hint-unit acceptance.

A subsequent [private anchored-image spike](anchored-image-spike.json) isolates
the next cost lead without modifying installed bytes. It is research, not a
production memo or host resource gate. Its ownership/transfer/failure requirements
and alternative history-collector concerns are captured in the cost follow-up.

## A15 anchored-image memo and host acceptance subset

The [bounded a15 receipt](a15-image-memo-and-host-cost.json) retains artifact,
interface, native, resource, ordinary comparison, cleanup and preservation
evidence. Failed proof attempts remain separately identified.

Source `193a929605b7dca0a03f57d4c672e3da439db5fd`, wheel
`b359730d6a5435484513247ef9048cf109173a456fec5ef0ada16e6d6e2659d9`,
and both separately installed profiles verify. The private memo retains at most
32 read-only executable descriptors per provider plus validated file signatures
and diagnostic digests. It retains no session state. Exact worker ownership,
generation/context acceptance, failed transfer fallback, descriptor cleanup and
SDK isolation are tested; current process/endpoint/UID/birth and image-signature
guards remain mandatory. All 337 source tests and independent public conformance
pass. API 1, snapshot/watch 3, write 1 and service 1 remain unchanged.

Three-turn native state/activity, unchanged-age rename and source reconnect pass
for both Codex hosts and Snap Claude. Independent exact-ID event-receipt runtime/
history p95 is 1.346/2.226 seconds for Snap Codex, 1.724/2.037 for Starship Codex
and 0.997/9.218 for Snap Claude. These clocks are separate from independent
native-first-observation and provider transition time. Foreground question/exit
passes; the held background question reaches cached `blocked/question` state
0.790 seconds after independent detection and agrees across three held samples.
Paired passive-listener lifetime passes on both Codex hosts. The quiet control's
first delayed probe establishes absence, not an exact matching retirement time;
the Snap lifetime publisher uses 20/60-second cadence rather than normal 30/120.

The matched five-minute combined-provider Snap case retains 31 synthetic saved
Claude rows, three scheduled native turns per provider, three healthy readers,
one slow reader and 100 cached reads per mode. Polling/hints use 1.049/1.995
percent of one core: **+0.946 percentage points**, now within the one-point CPU
gate. Starship's matched Codex case measures 0.423/0.576 percent: **+0.153 points**.
All scheduled native turns independently establish working, completion and new
activity, and all healthy readers have zero errors/gaps. Snap's margin is only
0.054 points; these finite native workloads do not establish a universal bound.

Sampled aggregate RSS still fails the original 64 MiB limit: Snap polling/hints
84.891/109.281 MiB, Starship 42.344/64.094 MiB. Incremental RSS is 24.391/21.750
MiB. Starship exceeds the total target by 98,304 bytes; Snap's polling baseline
already exceeds it. Sampling every 200 ms can miss brief peaks and is not a hard
maximum. The CPU checkpoint is accepted for these controlled cases; memory is
not. The unanswered incremental-versus-aggregate budget question is not approval,
and P6 hint selection plus normal-unit 30-minute soaks remain withheld.

Supplemental ordinary cached CLI comparisons use two independent native brackets
per provider/host. Codex reports all 50 saved/two loaded identities on Snap and
97/six on Starship with matching known states and age. Claude projects 31 of 32
native candidates and all three running workers with matching known phases.
One initial active conversation clock is 11.196 seconds behind the native clock;
four later samples agree. This observes convergence without measuring its exact
duration. The previously documented setup-only saved candidate remains absent,
and partial coverage stays explicit. Recorded and latest conversation cwd can
differ; older unloaded Codex kind/runtime remain unproved. These ordinary-store
checks supplement controlled proof rather than replacing its latency/resource
gate, and do not establish complete history classification.

Both additional five-minute owned publishers over ordinary stores complete with
three healthy readers, one slow reader and 100 cached reads. All readers have
zero errors/gaps; cached-read p95 is 88.581 ms on Snap and 83.495 ms on Starship.
Owned CPU is 3.823/1.342 percent and sampled aggregate RSS 113.508/67.277 MiB.
These runs have no matched same-traffic polling pair, and cannot establish
incremental CPU, hard resource maxima or long-term process/FD/watch stability.
Their publishers and private sockets are gone; normal units were not restarted.

Fresh both-host Codex recovery fixtures additionally prove unloaded saved rename
in 9.817/9.801 seconds, unchanged conversation age and unchanged loaded sets.
Daemon loss reaches unavailable runtime in 0.941/0.860 seconds; seven seconds
of offline observation starts no daemon. Only explicit isolated native New
starts a replacement, and the owning feed follows its new incarnation.

The first Snap recovery attempt failed an immediate activity assertion after
runtime readiness. It had not recorded the failing clock, so that attempt is
not accepted. Review identified the missing distinction between runtime and
history readiness after context replacement. The strengthened proof requires
truthful stale `lastKnownAt` followed by independently bracketed fresh history
within 15 seconds. A fresh Snap fixture reproduces stale history with its
correct unchanged clock, then restores current history in 3.421 seconds after
runtime readiness. Starship's strengthened fixture has a current initial clock
and accepted fresh history in 0.606 seconds. The producer artifact is unchanged;
the harness correction does not renew old evidence or weaken freshness checks.

All eight Snap and six Starship a15 namespaces, including the failed attempt and
paired controls, are stopped. Their actual `native-<host>` directories containing
borrowed authentication/history are physically absent. This pass's configuration
hashes, normal links, managed pins and enabled/active a8 unit PIDs match its own
starting bookends on both hosts. Earlier unattributed whole-loop drift remains
documented and was not restored. The native branch's entry/attach/parked/dialog
limits above remain current. The selected a8 client handoff is updated; P5's
aggregate memory gate and P6 remain open pending the explicit budget decision.
