# CPU correction delivery: Observer checkpoint

This ledger records C0–C2 of the [execution plan](../../cpu-reduction-execution-plan.md).
Observer acceptance is complete. The independently gated RLCD C3–C5 delivery is
also accepted below; its implementation and device evidence remain in RLCD.
The [source study](../2026-10-15-cpu/REPORT.md) retains its original measurements.

## Immutable artifact

Source freeze: `6542b9204fb78ee64daeabed7c42910bfb2dbeb1`.
[Observer 0.7.0a5](../../../artifacts/observer-0.7.0a5.json) wheel SHA-256:
`25cd5663560c973b55fc322b9504e287f5a2a6706ef1c377100c6bf900752ee5`.
Both hosts install and select the read/local-client and optional publisher roles
under `~/.local/share/agent-observer/0.7.0a5-25cd5663560c973b-cpu`.
The archive retains both exact wheels, manifests, producer lock and verifiers.
Mesh remains the accepted a20 bytes, SHA-256
`e02306b2323ddd845fec2c1ee82dd25b429878edefcee4cf8ac2b552535fc200`.

The [wheel/source comparison](wheel-source.json) verifies the complete package
inventory and rejects retired/extra modules. Both installed prefixes pass exact
Observer/Mesh wheel, entrypoint, dependency, schema/lock and lazy factory checks.
Portable current Agent profile/network conformance passes with installed owner
bytes. API 4/read 6/Service 4/Agent v3/SDK 1/preparation 1 remain unchanged.
Core-only a3 collection and the historical writer remain independently selected.
The [producer CI receipt](producer-ci.json) separately records successful hosted
checks for source/documentation checkpoint `a0e2496`.

## Independent native and delivery acceptance

[Snap direct](snap-native-direct.json) compares 102 identities over two rounds;
[Starship direct](starship-native-direct.json) compares 390. Runtime, phase,
identity and activity checks match. Snap retains a working-thread update sampling
race and a new system helper's creation-time sampling race; older unsupported
title/kind/timing fields retain their explicit coverage limits.

Following selection, [Snap Mesh](snap-native-mesh.json) compares 101 identities and
[Starship Mesh](starship-native-mesh.json) compares 392. Native inventory changes
between checkpoints are preserved rather than normalized away. Runtime/phase and
membership match; cached working-thread `lastUpdated` values are 28/19 seconds
behind the contemporaneous native references. The independently expiring original
receipts remain valid. These are sampled cached timestamps, not exact current
native-update or phase-entry clocks. A Starship helper creation-time race remains.

Installed owner snapshot/proof/watch and owned fixed SSH pass on
[Snap](snap-publisher.json) and [Starship](starship-publisher.json), with zero native
channels after cleanup. Current Tmux a7 bytes/factory/profile remain independently
verified alongside Agent through both carriers:
[private Snap](snap-paired-private.json), [private Starship](starship-paired-private.json),
[selected Snap](snap-paired-selected.json), [selected Starship](starship-paired-selected.json).
Actual configured two-host fleet reads/watches pass from
[Snap](final-fleet.json) and [Starship](starship-final-fleet.json).

## Cost evidence

The [installed artifact comparison](artifact-cost.json) uses serial ABBA fresh
processes per roster, unchanged Mesh/dependencies and matching complete display
oracles. CPU reductions are:

| Rows per host, two hosts | Snapshot validation | Wire admission | Complete prepared consumer |
| --- | ---: | ---: | ---: |
| 50 | 24.33% | 55.70% | 11.97% |
| 250 | 28.28% | 55.25% | 14.67% |

The complete consumer includes four changed views and three human renders each.
Fixture creation/warm-up is excluded; this is not application/device acceptance.

Separate [Snap](snap-local-cost.json) and [Starship](starship-local-cost.json)
ordinary-host ABBA windows include a complete owned local cached publisher,
Bridge/IPC and prepared human read path. Each CPU window lasts 120 seconds after
ten seconds of warm-up. [Mean percent of one core](local-cost-summary.json):

| Host | Baseline publisher + reader | Candidate publisher + reader |
| --- | ---: | ---: |
| Snap | 1.91 + 2.47 = 4.38% | 1.42 + 2.13 = 3.55% |
| Starship | 8.26 + 8.00 = 16.26% | 5.07 + 6.25 = 11.32% |

These descriptive differences are 19.02% and 30.43% relative. Source activity and
system load are uncontrolled; Starship's two baseline combined costs vary from
19.25% to 13.28%. Frame/render/native-revision counts are recorded, including
startup/warm-up outside the CPU window. The workloads are not identical, so these
figures are not universal causal savings. Collector and remote SSH/server cost
are excluded. Memory/FD peaks and complete owned cleanup are reported separately
in each receipt. RLCD still uses its independent old application tuple here.

## Scoped selection and rollback

[Snap](snap-role-transitions.json) and [Starship](starship-role-transitions.json)
record reader-first selection, reader rollback/reselection, publisher selection,
actual running-old-publisher rollback and candidate reselection. Old and new
readers succeed against each running publisher. The old shared launcher also
passes paired factory SSH proof/watch checks on
[Snap](snap-old-paired.json) and [Starship](starship-old-paired.json).
Other observed units retain their identities/restart counts through these stages.

Scoped render/unit/artifact/live-peer selection checks pass on both hosts.
Dotfiles commit `5f138d2` publishes only the two Observer role-selection JSON files.
Nine unrelated local notification commits in Snap's managed checkout remain
unpublished by this pass; only the owned selection overlay is reconciled there.
Starship fast-forwards the scoped published selection. This pass writes no provider
configuration and changes no native session, collector, Tmux control, 349 or
dashboard selection. Starship's Codex configuration hash advances externally
during the concurrent notification work; its current bytes are preserved. Other
protected configuration hashes match, and only the expected Agent publisher unit
changes incarnation.
The full dotfiles checker passes, including its broader desktop matrix and
independent dashboard wiring. Scoped Observer acceptance is established by the
explicit artifact/render/live/rollback gates above.

## Independent RLCD C3–C5 acceptance

The [client receipt](https://github.com/byebyebryan/esp32-rlcd/blob/358d265/docs/evidence/2026-10-15-prepared-reads/REPORT.md)
records source `1e20604`, artifact/firmware freeze `19323e6` and published
acceptance `358d265`. Both hosts verify bundle `807eab96b48825ae`, selecting
the exact a5/a20 producer pair above with preparation/read interfaces 1. Five
installed optional-contract tests pass on both hosts, alongside 47 application
tests, packed-frame and ASan/UBSan motion checks. Hosted native/Debug/Release CI
passes for the source freeze. Observer remains frozen throughout this client pass.

Starship RLCD `94:a9:90:f3:43:74` has a verified private 16 MiB backup, unchanged
partition/bootloader prefix, application-only flash/readback and one clean boot.
The selected wire-2 application SHA-256 is
`0ecdc4cd7e3f87a664ad3554f865751106dc2e6601494494e21770319a1f4eca`.
Installed cached-feed capture confirms matching CRC/request/rows, silence expiry
and recovery. Fictional physical-device checks independently exercise failed
turn/retry and healthy-sibling behavior. Actual old firmware/managed bundle
rollback and candidate reselection both positively acknowledge real data.
Dotfiles `447aa18` selects only RLCD's owned bundle/dependency metadata. The final
service has one serial owner, zero restarts and healthy device diagnostics.

The matched 500-row controlled application pipeline averages 21.64% of one core
for old app/old dependencies, 18.43% for old app/new dependencies and 13.21% for
prepared app/new dependencies. Outputs match with zero late device replies and
complete cleanup. Client-only savings are 28.30%; combined savings are 38.96%.
Fixture publishers/Reader/application/serial supervision are included; providers,
real SSH and physical serial are excluded from those controlled CPU figures.

Separate ordinary 300-second Starship service windows use 20.99% before and
12.76% after, a descriptive 39.20% reduction. Native activity varies; controlled
attribution remains separate. Candidate mean/peak PSS are 47.41/47.44 MiB and RSS
68.51/68.51 MiB, with two processes and 19 FDs. Collector, resident publisher and
Snap's SSH-hosted source costs remain separately reported. A controlled extra
prepared reader adds 8.54 points of one core for the same fixture publisher pair;
remaining acquisition/admission and proof/carrier cost is material.

The [delivery summary](rlcd-delivery.json) and
[completion audit](completion-audit.json) identify the independent gates and
limits. Collector a3, Tmux, the historical writer and 349 retain their independent
selections/owners. Concurrent notification work advances Codex configuration and
foreign managed commits; this delivery performs no provider configuration writes
and preserves those changes. Manual panel/readability and actual host reboot are
not claimed. Hosted wheel releases and C6 Mesh/presentation studies remain
separate future work. C0–C5 are complete within these declared bounds.
