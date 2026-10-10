# Read-delivery follow-up acceptance

The [execution plan](../../read-delivery-follow-up-plan.md) preserves API 2,
snapshot/watch 4, Service 2 and Mesh Agent profile 1. R0–R4 are accepted: publication, sustained cost characterization, pure
consumer cache, timed human watches and reader-only operational selection. No provider settings, native sessions, collector or bridge process
have been changed by the source/package work.

## R0: published baseline

The [publication receipt](publication.json) accepts the exact archived a12/a4
GitHub prereleases, downloaded checksums and clean core/Mesh installation.
No accepted archive was rebuilt or overwritten. The fresh Mesh source gate
passes 116/169 oracles, 56 core tests and frozen lock/schema checks. That source
environment records installed metadata a3; the preceding
[immutable a4 native proof](../2026-10-09-mesh-integration/mesh-wheel-native.json)
retains its exact package bounds. New Mesh source development remains external.

## R2 and R3: cache and human watch

The [package/conformance receipt](package-and-conformance.json) accepts the
[a13 manifest](../../../artifacts/observer-0.5.0a13.json), wheel SHA
`646a067dcba3b1a37354c01b9aa91a247351adabbb352b19f732bd6f89cedbcc` and source
`4cb623376ce857dba10be90306ad0ef80f482429`. The optional-Mesh source profile
passes 425 tests with no skips. Four optional checks skip without Mesh installed.
Both installed prefixes independently pass 67 tests away from the checkout;
only tests, fixtures and static schemas are copied. The Snap profile includes
source-only Claude SDK 0.2.163; Starship is core-only. Provider version numbers
remain diagnostics, not support allowlists. Wheel byte, entrypoint, facade and
Mesh frozen-profile checks pass in the separate
[Snap](final-mesh-snap.json) and [Starship](final-mesh-starship.json) receipts.

Fourteen pure cache cases cover scope, UID/boot/time namespace, incarnation,
ordering, gaps/resync, warming/empty, component expiry, context revocation,
heartbeat nonrenewal, original activity age, terminal invalidation and reset.
Unknown runtime never becomes parked. Saved display context survives independent
runtime expiry; merged activity/outcome is conservatively stale when either
component expires because the wire lacks per-component provenance. This is a
consumer projection, not a new wire or provider predicate. See the
[cache/client guide](../../read-cache-client.md).

Controlled socket/timer tests prove quiet expiry, real-frame counting, pending
SDK read preservation and cleanup on cancellation/output failure. Installed
12-second local and fleet human watches on
[Snap](final-human-snap.json) and [Starship](final-human-starship.json) render
while active, exit 130 on Ctrl-C, close their owned process and print current-view
revocation. Actual watches do not force a source lease failure; controlled tests
supply that proof. Human output is drained in memory and never archived.
An intermediate unselected/unpublished wheel exposed a missing final notice on
async cancellation; the corrected immutable wheel and cancellation test replace
it. An initially undrained harness exercised bounded output failure rather than
normal cancellation. Neither rejected attempt establishes acceptance.

CI exposed six existing synthetic Claude tests assuming UID 1000. Their native
fixture now uses the runner UID; the public source-provenance invariant and
production wheel are unchanged. This correction is test-only.

## R4: independent native reads and reader selection

Installed direct/native comparisons pass on
[Snap](final-direct-snap.json) and [Starship](final-direct-starship.json).
Cached Mesh owner reconstruction, public reader ordering/age and native evidence
are compared independently in the
[Snap](final-native-snap.json) and [Starship](final-native-starship.json) reports.
Codex has 91 rows/three running sessions on Snap and 354 rows/six running sessions
on Starship. All comparable Codex facts agree. Claude has 37 direct rows/eight
running sessions on Snap, with the known setup-only UUID's unavailable cwd.
Its two excluded old background histories and partial registration assumption
retain the accepted limitations. Twenty-one older Starship Codex kinds remain
unknown. No legacy compatibility or post-TUI-close proof is added.

One cached Claude sample has an extra unknown UUID absent from both bracketing
native samples; a following cached read omits it. The native oracle does not
settle its prior runtime. This remains an explicitly unknown observation-memory
case within accepted partial coverage, not a running/parked assertion. Earlier
sampling rounds show an ordinary Starship turn transition; timing races remain
labelled rather than rewriting native clocks.

The managed tuple now represents the reader and bridge selections independently.
Artifact/render and actual selection gates pass on both hosts. The
[operations receipt](operations-and-cleanup.json),
[Snap selection](selection-snap.json) and
[Starship selection](selection-starship.json) prove a13 selection, a12 rollback
and a13 reselection using only the read link and managed source tuples. A strict
missing-key template rejection was corrected and the full sequence repeated.
The independent [Snap](collector-gate-snap.json) and
[Starship](collector-gate-starship.json) collection gates remain accepted.
Protected provider/workspace/service/authority/external-pin hashes and publisher
PID/birth/restart counts agree with the preselection bookends. Starship's existing
Kitty source drift is preserved. No daemon reload or publisher restart occurs.
The normal writer remains a16 and collector a11. No new action capability,
frontend/device acceptance, provider-policy rollout or native occurrence replay
is implied.

## R1: operational costs

The ten-minute four-window matrix completes successfully on both hosts. It measures
baseline, one local reader, one fleet reader and two fleet readers after a
separate 30-second warmup. Ordinary provider activity and acceptance probes
continue; this is not an idle benchmark. Fleet phases run concurrently on both
hosts, yielding two/four total fleet subscribers. Managed collector helpers and
owned reader/SSH client trees are included. Provider daemons, remote SSH servers
and per-SSH remote bridge workers are explicitly excluded; no whole-fleet CPU
or network-byte claim is made.



| Host/workload | Collector CPU | Local bridge CPU | Owned reader CPU |
| --- | ---: | ---: | ---: |
| Snap baseline | 54.66% | 0.00% | — |
| Snap one local | 59.28% | 7.28% | 8.49% |
| Snap one fleet | 63.70% | 8.20% | 29.84% |
| Snap two fleet | 67.78% | 15.66% | 30.76% + 30.27% |
| Starship baseline | 36.73% | 0.00% | — |
| Starship one local | 39.98% | 4.28% | 4.65% |
| Starship one fleet | 42.36% | 4.38% | 12.57% |
| Starship two fleet | 45.07% | 9.34% | 12.43% + 12.37% |

Percentages refer to one logical CPU core. These are descriptive workload
observations, not isolated marginal-cost estimates. The exact
[Snap](sustained-snap.json) and [Starship](sustained-starship.json) windows retain
CPU seconds, sampled mean/peak/end RSS/PSS, process and FD counts. No RSS budget
is imposed. The measurement helper's recorded original hash is in
[the provenance receipt](measurement-script.json); its only later change before
commit clarifies root authentication in the docstring. All windows use the
existing a12 raw Mesh reader, a11 collector and a4 bridge. A13 human-watch steady
cost and remote SSH worker costs are not established by this matrix. Installed
human-watch acceptance is the separate bounded check above.

The steady collector cost is material for daily use even with zero subscribers.
Fleet subscribers add substantial local work, especially on Snap. All owned measurement reader roots are reaped and both managed Mesh bridges
return to eight root FDs. Remote SSH worker cleanup is not independently
authenticated. The next producer pass should investigate retention reconciliation first; Mesh validation,
serialization and independent fleet transport cost need their own external
checkpoint. This pass records those gaps and preserves existing publishers.

The [Snap](retention-snap.json) and [Starship](retention-starship.json) isolated
cached-data studies identify repeated retention scans as a strong collector
cost candidate. The tested engine bytes match installed a11/a12. The fixed-clock
counterfactual skips the scan only in an owned synthetic state; it is not a
producer repair or correctness proof. See the
[focused collector follow-up](../../collector-cost-follow-up.md).

Cold cached process startup is separately measured in three samples per mode on
[Snap](latency-snap.json) and [Starship](latency-starship.json): local Service
snapshot takes roughly 0.38–0.54 seconds, local Mesh 0.91–1.20 seconds and fleet
Mesh 1.60–2.57 seconds. These are descriptive timings on active hosts, including
validation and serialization, not a latency SLO or network bandwidth result.

Native notifications/events, shared brokers or pooling, physical suspend,
attachment/actions and downstream clients remain independent future gates.
