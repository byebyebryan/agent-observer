# Snap residual collector CPU

The remaining cost is primarily repeated Claude catalogue processing. Transcript
writes wake the history scheduler, which starts a new full metadata scan rather
than refreshing only the changed session. Activity and session-kind classification
decode substantially overlapping transcript tails in separate passes.

This investigation changes no collector implementation, artifact selection,
provider policy or cadence. The selected a14 collector remains accepted. The
following repair is proposed, not implemented or operationally accepted.

## Normal-unit CPU attribution

The preceding ten-minute [a14 normal-unit window](../2026-10-09-retention-cpu-repair/normal-cpu-snap.json)
measured 11.01% of one logical core: 2.72% publisher and 8.29% owned helpers.
A fresh unprofiled five-minute window measured **6.91%** under the current ordinary
workload. This is workload variation, not an idle floor or another repair.

The [owned-counter receipt](owned-cpu-snap.json) reads the explicit systemd unit's
cgroup CPU counter for the total, and UID/incarnation-checked process counters
every 50 ms for role attribution. Only the normal unit is measured; no readers,
provider work or profiler are added during this window. Provider processes,
Mesh, the sampler and unrelated workloads are outside that cgroup.

| Work in the 300.012-second window | Percent of one core |
| --- | ---: |
| Publisher | 1.770% |
| Claude history workers and nested metadata helpers | at least 3.546% |
| Other identified Claude collection workers | at least 0.350% |
| Identified Codex collection workers | at least 0.450% |
| Two native-hint listeners together | 0.090% |
| Unattributed collector and unobserved short-process CPU | about 0.703% |
| Whole owned unit | **6.909%** |

The kernel total includes exited helpers. Per-role attribution uses observed own
ticks and is a lower bound: 2.0286 of 15.4186 helper CPU seconds were not attributed
to a captured process tail. One short collector's provider also remained unknown.
The sampler does not read worker request pipes, environments or native payloads.
Claude history is identified by its exact metadata child, not by session labels
or generic process discovery. Other Claude/Codex workers are identified only when
their owned file descriptors expose the corresponding configured store. The
listeners' provider identities are corroborated by the later native-hint stacks;
the counter receipt retains the original unknown label for the non-inotify helper.

The window captured 18 Claude history-worker/metadata-helper pairs and ten other
Claude collectors. Claude admitted 31 history hint batches and four runtime hint
batches, with zero feed losses, rejections or restarts. Codex admitted no new
hint batches. These counters count coalesced port wakeups, not every native write.
Only 37 Claude logical saved identities are involved, with three running contexts
in the later native comparison. A small number of active sessions therefore
causes repeated processing of the broader saved catalogue.

## Scheduling and collection paths

[Claude file hints](../../../agent_observer/claude_hints.py) request history
reconciliation for writes to project-level `.jsonl` transcripts. The
[scheduler](../../../agent_observer/observation_scheduler.py) keeps one dirty bit,
a 500 ms settling window and a ten-second minimum history start gap. Consequently,
the configured 120-second history interval is the periodic fallback, not a limit
on hint-driven scans. Hints already coalesce; the listeners themselves are cheap.

Every [Claude collection](../../../agent_observer/claude_snapshot.py), including
runtime-only collection, calls `saved_ids()` across the bounded catalogue before
authenticating native registrations. History collection also starts the isolated
[metadata worker](../../../agent_observer/_claude_history_worker.py). That worker
uses the SDK metadata API and separately calls `transcript_activity()` and
`transcript_kind()` for each returned session. The first parses a bounded tail;
the second parses a bounded head and another bounded tail. Unchanged transcripts
are decoded again on every refresh. It does not read the whole saved store.

## Installed controlled measurements

The [component study](claude-components.json) uses the selected a14 package and
Snap Python 3.12.8, with the normal descriptor-anchored image memo. It performs
read-only collections in a separate process; it is not normal-unit CPU evidence.
Native file changes and same-process import amortization limit exact comparison
with short-lived normal workers.

| Warm installed read | Own CPU seconds | Metadata child CPU seconds |
| --- | ---: | ---: |
| Runtime, first warm sample | 0.0628 | 0 |
| Runtime, second warm sample | 0.0698 | 0 |
| History, first sample | 0.0695 | 0.4902 |
| History, second sample | 0.0708 | 0.4948 |

Warm positive saved-identity scanning costs approximately 0.05–0.056 CPU seconds;
native registration authentication costs approximately 0.003 seconds and public
snapshot composition approximately 0.010 seconds. The separate
[positive-identity study](claude-saved-identity-profile.json) confirms three
unprofiled scans at 0.055–0.058 CPU seconds. Its instrumented scan decodes 1,885
bounded JSON records for 37 positive UUIDs. That is secondary to history cost.

The initial cold component read costs 0.82 CPU seconds, including installed-image
and native-image authentication. Subsequent memo-guarded checks are cheap. Do not
attribute that cold cost to every normal refresh or propose weakening image guards.

The [metadata profile](claude-history-profile.json) captures normalized counters
only. It finds 39 candidate files, 37 UUIDs and 36 SDK-projected rows; the known
setup-only SDK omission remains explicit. Activity decodes 9,268 records / 17.50 MB
and kind classification 9,820 records / 18.58 MB: **about 34.4 MiB** of overlapping
bounded record data per catalogue refresh. These byte counters count JSON decoder
inputs, not unique file bytes or full-store reads.

In the instrumented 0.594-second run, activity and kind together account for
0.526 inclusive seconds, approximately 88%. Their counts and source paths establish
duplicate work. These timings include cProfile/counting overhead and are not a
production CPU partition. SDK list metadata costs about 0.018 seconds, census
about 0.007, and metadata module binding about 0.038. Fresh subprocess startup,
SDK imports and duplicate-directory census are smaller targets than transcript
decoding in this workload.

## Live stacks and observation bookend

[Consistent py-spy sampling](live-profile-summary.json) attaches only to the
authenticated normal collector and its owned children: 120 seconds, 79 Hz,
GIL-holding threads, 237 captured samples and one read error. Short-lived workers
can escape subprocess discovery; the counts cannot partition OS CPU.

Of 24 captured metadata-helper samples, 11 include activity scanning and 12 kind
scanning. Of 120 publisher samples, 104 include worker completion, 88 public-shape
validation, and 67 complete-view publication; inclusive counts overlap. Eleven
include retention reconciliation during changed work. The previous constant
retention hotspot is gone; receipt validation/publication now dominate captured
publisher execution. Twenty-three Claude collector samples include saved-identity
scanning. These independent live paths agree with the isolated studies.

The [installed identity receipt](installed-identity.json) authenticates the same
publisher PID/birth and both hint incarnations after profiling. Installed engine,
Claude scan/hint helpers, scheduler and service hashes match this checkout.
The normal unit retains MainPID 2367213, birth 65491117 and zero restarts.

Two independent [installed CLI/native comparisons](native-comparison-snap.json)
after profiling check all 128 rows: 91 Codex and 37 Claude. All three running Codex
contexts and all three running Claude contexts agree on runtime and phase. Codex
has zero comparison issues. Claude retains the accepted setup-only cwd omission
for `e0cba9dd-b642-4730-af4b-beb3b7e9c16c`; current coverage remains partial and
background/registration assumptions remain unchanged. Cached views can lag native
activity; this is an observation bookend, not a new lifecycle or delivery gate.

## Proposed repair sequence

1. Start with one bounded transcript read/parse shared by activity and kind.
   Preserve their independent results, byte budgets, malformed/duplicate-key
   handling, sidechain and local-command exclusions, identity checks, incomplete
   records and file-change guards. Keep main/child classification and age identical
   for stable inputs. Prove old/new parity with frozen helpers and adversarial
   fixtures; measure unprofiled decode/CPU reduction before building a candidate.
2. Re-measure with the accepted cadences and native hints. The first change should
   remove much duplicate tail decoding, but this investigation does not promise a
   normal-unit CPU floor. Leave the broader positive-identity scan secondary.
3. If whole-catalogue refreshes still dominate, independently design a bounded
   memo of normalized saved metadata for unchanged transcript incarnations. Such
   a memo needs fresh directory/file ownership, identity and change checks, clear
   invalidation on faults/replacement/removal, and native proof. File stamps may
   invalidate a memo; they must not become conversation age, runtime authority or
   renewed work evidence. Never keep raw transcripts or tool contents in the memo.
   This is a separate complexity decision, not required for the first repair.
4. Freeze any successor artifact and independently validate native direct/cached/
   pushed observations, faults, identity/kind/age and retention. Measure at least
   ten unprofiled normal-workload minutes on both hosts and report publisher/helper
   CPU separately. Scoped collector rollout follows artifact acceptance, retaining
   independent reader, writer, Mesh and provider-policy selections and rollback.

Slower polling, disabling hints, deleting history, changing provider workflows,
persistent SDK workers and networking changes are not needed to test the first
repair. Publisher validation is a following measured target if it becomes material
after eliminating duplicate Claude parsing; no validation bypass is proposed.
