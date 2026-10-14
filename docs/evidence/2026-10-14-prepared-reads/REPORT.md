# Prepared Agent read acceptance ledger

Execution authorized by the user on 2026-10-13 local / 2026-10-14 UTC under the
[R0–R6 plan](../../prepared-read-client-plan.md). This ledger distinguishes
source, artifact, native, operational and downstream gates.

## R0 — installed cadence

Both endpoints still select Observer 0.7.0a1 / Mesh a17, Agent v3, API 4,
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
This is an installed candidate, not yet the ordinary read selection.

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

## Remaining gates

R5 reader-only selection/rollback, bounded operational resource windows and the
independent RLCD handoff; R6 exact source/CI/release distribution evidence.
Source, immutable candidate and native acceptance do not select a dashboard or
publish the currently unreleased Mesh input.
