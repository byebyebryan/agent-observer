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
