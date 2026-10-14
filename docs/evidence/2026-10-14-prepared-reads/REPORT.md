# Prepared Agent read acceptance ledger

Execution authorized by the user on 2026-10-13 local / 2026-10-14 UTC under the
[R0–R6 plan](../../prepared-read-client-plan.md). This ledger distinguishes
source, artifact, native, operational and downstream gates.

## R0 — installed cadence

At baseline both endpoints selected Observer 0.7.0a1 / Mesh a17, Agent v3, API 4,
snapshot-watch 6 and Service 4. The private Mesh a18 wheel matches its accepted
SHA-256 `035f0a54a06581e702ad79cce93ecf56f3d5dcf8d28535b533c0098e97ae2098`.
Prepared interface 1 / SDK 1 and the exact Agent v3 descriptor are present.

Two bounded 60-second cached fleet observations used the installed
baseline, existing authority and no route writes. The clocks/windows differ;
they are cadence observations, not an AB performance comparison or an
independent native inventory census. No raw provider/observation payload is
retained. The [probe](../../../studies/prepared/cadence.py) records counts and
shape only and closes its owned iterator/guard.

| Origin | Replacement views | Native view changes Starship / Snap | Approximate 1 Hz reads per replacement | Connections after |
| --- | --- | --- | --- | --- |
| [Snap](snap-cadence.json) | 20 | 4 / 3 | 3.00 | 0 |
| [Starship](starship-cadence.json) | 17 | 3 / 2 | 3.53 | 0 |

The final sampled inventory was 97 Snap rows and 386 Starship rows. Replacement
views include warming/proof delivery updates; native revisions changed less
frequently. The benchmark must include all admitted replacements, not only
native changes, and include roughly three reads per replacement as the observed
device-consumer workload. Actual RLCD selection and physical CPU remain separate.

## R1 — additive owner interface

The [read interface specification](../../prepared-agent-read-interface.md)
binds static compilation to current AgentProfile semantics and provides a small
optional PreparedAgentWatch. It caches original header/source context once per
replacement, exports owned current rows through Mesh, and keeps raw exports
explicit. It adds no source health vocabulary or dashboard policy. The initial
CLI opt-in is `mesh watch --human --prepared`; existing calls remain independent.

## R2 — owner preparation certification

Source `dc4b4a1` implements the compiler and header/current-row helper; `7c0a3ff`
adds the explicit human CLI opt-in and freezes Observer **0.7.0a2** production
bytes. Python 3.11.10 and 3.14.8 both pass **410 tests, zero skips** with Mesh a18.
The nine focused preparation/CLI cases pass again from the isolated installed
wheel, including all seven frozen Agent v3 cases, exact expiry boundaries,
independent rule expectations, mutation, heartbeat/gap/resync, failed admission,
clock/capacity/binding errors, compiler cancellation and owned IPC/CLI cleanup.

## R3 — complete changing-watch cost and allocation

[96 fresh-process trials](cost/timing-cases.json) comprise two serial ABBA/BAAB
blocks per cell. Every trial imports the exact installed a2/a18 tuple, with one
unchanged measurement harness, workload and owner runtime hash set. Each lifetime
admits four changed publications; an untimed counted preflight requires four
full packaged-profile schema validations for both paths. Native cells change
title/phase/service ordering and remote payload digests; envelope cells change
reader ordering only. Original receipts and real BOOTTIME queries remain.

The [full summary](cost/timing-summary.json) reports every cell. At the observed
one-second / roughly three-read cadence:

| Shape/change | Total consumer CPU reduction | Repeated-read CPU reduction |
| --- | --- | --- |
| One host, 500 rows, native | 36.57% | 85.89% |
| Two hosts, 250 rows each, native | 36.18% | 86.55% |
| Two hosts, 250 rows each, envelope | 36.76% | 86.64% |
| One host, 1,000 rows, native | 35.89% | 85.61% |

This meets the proposed 25% complete-lifetime / 50% repeated-read targets.
Single-read cases save only about 10–11%, so ordinary defaults remain legacy and
prepared watch stays explicit. Sixteen-read cells save about 70–73% overall.
Timing includes admission/compilation, owned rows, source context and active
selection; excludes native acquisition, Reader/carrier I/O, serial and firmware.
These are Agent consumer results, not physical RLCD CPU savings. The earlier
[exploratory matrix](cost-exploratory/timing-summary.json) preceded frozen
installed input/harness qualification and is superseded for acceptance.

The separate [deployed-tuple comparison](deployed-comparison.json) runs eight
fresh trials, ABBA/BAAB, at two hosts / 500 rows / three reads per replacement.
The old installed a1/a17 legacy path versus the complete a2/a18 prepared path
saves **35.82% total and 86.25% repeated-read CPU**. Both retain four full schema
admissions and the same independently expected active-row oracle. Its temporary
driver changes only import availability and diagnostic hashing for the older
package; [reproduction](../../../studies/prepared/compare_deployed.py) preserves
the frozen decision harness and records hashes. This complete-tuple result is
separate from the same-a18 isolation matrix; savings are not attributed solely
to Agent preparation. The packaged study driver
[reproduces](deployed-reproduction.json) the same harness/workload/oracle hashes
in a second eight-trial run, saving 36.44% total and 86.58% repeated-read CPU.

Separate allocation runs cover 1,000 replacements at 16 total rows and 32
replacements at 500 total rows. Inputs are prebuilt and excluded from tracing;
process RSS includes them. Fixed admitted-time queries isolate allocation and
do not prove real-time freshness.

| Traced allocation | Legacy | Prepared |
| --- | --- | --- |
| [500-row](memory-legacy-inventory.json) / [prepared](memory-prepared-inventory.json) final retained | 1,130,774 B | 775,981 B |
| 500-row peak | 2,693,702 B | 3,624,618 B |
| [1,000-replacement](memory-legacy-churn.json) / [prepared](memory-prepared-churn.json) final retained | 82,133 B | 116,113 B |
| 1,000-replacement peak | 346,430 B | 350,113 B |

Prepared retained allocation at the 1,000-replacement checkpoints is 113,291 B
at 251, 114,279 B at 501 and 116,113 B at 1,000. This bounded sample shows a
plateau rather than retained generations accumulating at inventory size. It is
not unlimited-churn or maximum-frame RSS proof. Prepared temporary peak is about
35% higher in the 500-row sample. Post-disconnect residuals remain in the reports;
they are not attributed to a leak or cache without further evidence. No strict
memory budget or memory-saving guarantee is imposed.

## R4 — immutable package and installed/native acceptance

The accepted Observer wheel SHA-256 is
`d4a37999bcf5652d877572230746d9d0c3c306362b4c174b29cd642414f5768d`,
from `7c0a3ff53e288e4c7a7210f5ce8daa94d3be5626`. The
[source comparison](wheel-source.json) checks every packaged Python/schema file
against an isolated committed tree and finds zero retired Claude files. A draft
wheel `005218b75d26bea87d0ed6aeebb484eb4485547e652f2f030abefde2e92f7b60`
was rejected before installation: the development checkout's ignored build
cache had included removed Claude files. The isolated rebuild avoids touching
that inherited cache. Only the distinct reviewed hash is accepted/archived.

The [installed conformance](installed-conformance.json) passes seven profile and
ten network cases. [Snap](snap-artifact.json) and [Starship](starship-artifact.json)
independently verify exact installed Observer/Mesh wheel bytes, unchanged locked
schemas/profile and pure import boundaries. Prefix on both hosts:
`~/.local/share/agent-observer/0.7.0a2-d4a37999bcf5652d-mesh-a18-prepared`.
This was the installed candidate at R4; R5 independently selects only its read CLI.

[Snap direct/native](snap-native-direct.json) matches 97 identities, all runtime
and phase checks, including three active sessions, in both rounds with no issues
or context differences. [Starship direct/native](starship-native-direct.json)
matches 383 identities, including three active sessions, likewise. Existing
unproved historical name/kind/activity/timing cases remain explicitly counted.
No provider actions or controlled native sessions are used by these comparisons.

The [Snap cached comparison](snap-native.json) preserves original sampling:
one continuously working thread's update timestamp is 34 seconds behind the
instantaneous native read in the first round, then reported as a sampling race.
The cached sample predates both native reads and its original runtime/history
receipts are still current. Direct reads match. This is documented acquisition
latency, not a claim that cached update time equals latest daemon time.

Ordinary installed [Snap](snap-installed-watch.json) and
[Starship](starship-installed-watch.json) fleet watches compare complete raw
exports and every current row with legacy over 40-second windows. Both local IPC
and remote fixed-SSH nonce proofs are present, with 15/13 replacement frames,
zero connections after cleanup and zero current/raw state after disconnect.
The current human CLI also renders the sampled Snap view and revokes on exit.
Collector/publisher and RLCD incarnations remain unchanged.

## R5 — reader-only selection and operational resource bounds

[Snap](snap-reader-selection.json) and [Starship](starship-reader-selection.json)
select the accepted a2/a18 prefix for `.local/bin/agent-observer` only. Each
reverts to a1/a17, checks the public CLI and cached service, then reselects a2/a18.
Protected files, configurations, collector/publisher/Tmux/writer controls and
process incarnations remain equal. There are zero service restarts or provider
actions. Ordinary CLI defaults remain legacy; preparation is explicitly requested.
The [selection probe](../../../studies/prepared/select_reader.py) uses owned
symlink replacement and restores only that target on failure.

Both installed [Snap](snap-operations.json) and
[Starship](starship-operations.json) operations gates pass against the exact
reader and independent bridge/collector selections. Candidate render gates are
[separate](snap-selection-candidate.json) on [both hosts](starship-selection-candidate.json).
The managed pin commit [7dce74d](https://github.com/byebyebryan/dotfiles/commit/7dce74d)
changes only reader fields in two chezmoi deployment files; bridgeSelection,
collector and writer pins remain independent. An isolated current-source tree
supplies render/publish checks. Both ordinary chezmoi checkouts have independent
foreign commits, and Starship also has unrelated dirty changes; these are
preserved rather than reset or merged. [Starship's scoped update](starship-managed-source.json)
records the two managed-file before/after hashes. Full chezmoi checks pass.

The installed [resource probe](../../../studies/prepared/resources.py) records
four matched shapes on each host: no added reader, one local prepared watch,
one fleet prepared watch and two fleet prepared watches. Each steady window is
at least five minutes; a ten-second startup interval is excluded. Owned CLI/SSH
descendant birth, CPU, RSS and FD samples accompany unit cgroup CPU/memory.
All service incarnations/restart counts remain stable. All owned readers and
observed descendants are gone afterward on both hosts.

| Host / prepared reader window | Reader CPU, percent of one core | Peak summed reader-tree RSS | Collector CPU | Resident Agent publisher CPU |
| --- | --- | --- | --- | --- |
| Snap / local | 3.20% | 36.6 MB | 2.06% | 2.90% |
| Snap / fleet | 15.17% | 63.5 MB | 1.45% | 1.75% |
| Snap / two fleet readers | 15.78% + 15.80% | 64.0 + 71.5 MB | 1.94% | 3.64% |
| Starship / local | 7.54% | 50.3 MB | 4.45% | 14.99% |
| Starship / fleet | 12.20% | 78.1 MB | 3.93% | 11.80% |
| Starship / two fleet readers | 12.12% + 12.17% | 62.9 + 62.0 MB | 5.75% | 19.31% |

See [summary](resources-summary.json) and full
[Snap](snap-resources.json) / [Starship](starship-resources.json) receipts. CPU
for a reader uses only the authenticated stable PID tree observed throughout
its sampled interval; remote SSH server/source processes are explicitly excluded.
RSS sums per-process resident pages and may count shared pages more than once;
it is not PSS. These are descriptive ordinary-workload windows, not causal AB
CPU comparisons. No-added-reader retains existing readers/RLCD; publication and
render frame counts are not captured in these resource windows, and R0's
separate cadence sample cannot establish their exact publication rate.

Whole fleet watches still use **12–16% of one core per reader**. The consumer
benchmark does not include Reader/carrier/per-publication pipeline work or
human presentation, and does not identify which remaining layer dominates.
The unchanged RLCD application uses **19.35–21.70%** in these windows. Its bundle
has not adopted this helper. A separate complete-pipeline profile and the
client's matched adoption measurement remain useful next steps; this receipt
does not claim the daily application's CPU issue is solved.

The [RLCD handoff](../../rlcd-prepared-read-handoff.md) supplies exact wheel
hashes, construction/current/context/export semantics, retirement/reconnect
obligations, full identity/expiry policy, cost limits and independent bundle,
service, serial/device and rollback gates. No consumer source or device changes
are included here.

## R6 — distribution and wrap-up

Source through `6331382f388de2d255e562b18e1bcd0199fd8e4e` is pushed. Its
[hosted CI](https://github.com/byebyebryan/agent-observer/actions/runs/38521162852)
passes, recorded separately in [source-ci.json](source-ci.json). Reader CI uses
the accepted Mesh a18 freeze; publisher CI retains its independent a17 input.
Core-only and exact optional installed checks have their own R2/R4 evidence.
The final dependency-free `./scripts/check` passes 410 discovered tests with
32 expected optional-Mesh skips plus 155 Markdown checks; the independently
installed Mesh a18 source runs above have zero skips.

Both accepted wheels, manifests and archived verifier inputs exist in each
host's immutable selected-prefix `artifact/` directory. Exact installed byte
verification passes independently on each host. Mesh **v0.1.0a18 has no hosted
release** at this checkpoint; the Observer a2 wheel is likewise not published.
Do not rebuild or replace these hashes under the accepted identity. The
independent release owner must publish/verify the exact Mesh input before a
hosted Observer consumer release is advertised. As the plan permits, that
distribution delay does not block local candidate acceptance or the handoff.

Observer's scoped implementation/acceptance loop is complete. The observation
contract stays **API 4 / read 6 / Service 4 / Agent profile v3 / SDK 1**; the
additive local preparation/read interface is **1**. Independently pending work
is hosted wheel distribution, RLCD adoption/application CPU proof, and profiling
remaining whole-pipeline watch costs. Existing native timing/history, physical
suspend and post-TUI-closure deferrals retain their bounds. No new provider,
attachment/action or rich notification contract is implied.
