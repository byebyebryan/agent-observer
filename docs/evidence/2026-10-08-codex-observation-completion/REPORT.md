# Codex observation completion acceptance

Date: 2026-10-08. Status: a5 source, separately installed artifact and native
observation gates are accepted on Snap and Starship. Normal read/service links
now select a5; restart/crash/reconnect, rollback/reselection and both 30-minute
managed-service checks pass. The normal writer retains a16 independently.
The [execution plan](../../codex-observation-completion-plan.md) and
[ownership specification](../../observation-boundaries.md) define the scope.

## Artifact and source boundary

The [manifest](../../../artifacts/observer-0.5.0a5.json) freezes source
`19c467bea38cd46a7a1aa4f538218ec8414d5548` and wheel SHA-256
`9e116932e007b0bfad7088059a9d6f82155e4c297ff2121598e4c09b06f5fa6b`.
Both hosts independently verify the core-only installation at
`/home/bryan/.local/share/agent-observer/0.5.0a5-9e116932e007b0bf`:
[Snap artifact](snap-artifact.json), [Starship artifact](starship-artifact.json).
Wheel, manifest and passive artifact verifier are retained in its `artifact/`
directory. No SDK or provider executable is bundled. Artifact verification
invokes no provider. API 2/read wire 4/service protocol 2 are unchanged.

`ObservationEngine` owns sample ordering, context changes, merge/retention and
expiry through explicit host/clock/profile inputs. `observation_scheduler` owns
refresh planning and hint coalescing; `observation_evidence` shares invalidation
and bounded retention with direct watch. The service supplies host resources,
helper lifecycle and transport envelopes. No provider classifier remains in
service state. One passive adapter dispatch supplies collection and feed helpers.
Unsupported provider selection fails before native/helper activity; the legacy
history-census diagnostic is removed. Transitive dependency checks isolate
read/core/service from actions and alerts and core from host I/O/native/service
implementations. All 379 tests pass (one skipped), with 89 documents checked;
scoped Ruff checks pass. These are static/controlled/real IPC checks, not native
provider fault injection.

The final full-suite run once failed the existing outer-worker helper-retirement
assertion within its one-second observation window. The exact test then passed
three sequential focused runs, and the full 379-test/doc check passed again.
No cleanup failure reproduced, no recent kernel OOM entry was found, and the
assertion/runtime were not relaxed. The one intermittent synthetic failure remains
an explicit test-reliability limit; sustained native service checks observed no
reader, publisher or resource-stability failure.

The separate writer's implementation and wire are unchanged. It is packaged
but does not become part of core; fixture initialization uses its previously
accepted explicit native-entry subset. This report adds no attachment/action
capability or new writer-selection gate.

## Independent ordinary comparison

Every direct/cached view has two bracketing native/CLI rounds. The independent
stdlib reference imports no Observer source and requests bounded metadata only.

| Host | Direct / owned cached publisher | Rows | Running | Known activity | Classification |
| --- | --- | --- | --- | --- | --- |
| Snap | [direct](snap-ordinary-direct.json), [cached](snap-ordinary-cached.json) | 89 | 2 | 52 | 51 user, 38 child |
| Starship | [direct](starship-ordinary-direct.json), [cached](starship-ordinary-cached.json) | 353 | 5 | 105 | 80 user, 252 child, 21 unknown |

All eight rounds agree on exact identity, daemon runtime/phase, saved identity,
tree-root metadata, known age/outcome and blocked reasons, with zero issues.
Read-client child filtering, urgency/activity ordering, human age, exact show
and doctor counts pass. Missing titles/clocks/outcomes and older unknown kinds
remain explicit; no terminal/process census supplies session authority.

The ordinary daemon is 0.162.0 on both hosts. Private TUI initialization copies
the installed 0.161.0 bytes. Those versions are proof provenance, not allowlists.
Ordinary CLI links and the owning daemon incarnation remain unchanged across
this native checkpoint.

## Isolated native observation

Codex-only private user/mount/PID/tmp namespaces mask ordinary provider paths.
Only Codex authentication is borrowed; Claude paths are masked without borrowing
its executable or credentials. Explicit fixture actions initialize private
contexts, hold input and interrupt/restart the private provider. Observation
itself performs no provider action. Terminal output is drained/discarded.

| Case | Snap | Starship | Accepted observation |
| --- | --- | --- | --- |
| Positive parked census | [read](snap-native-read.json) | [read](starship-native-read.json) | Independent direct/cached/pushed saved rows are parked from native notLoaded evidence; parked phase is null |
| Held work and input | [monitor](snap-native-monitor.json) | [monitor](starship-native-monitor.json) | Working, approval/question blocks and waiting agree across native/direct/cache/push; native conversation clocks survive refresh |
| Daemon outage/recovery | [recovery](snap-native-recovery.json) | [recovery](starship-native-recovery.json) | Absent daemon is not autostarted by reads; cached/pushed rows become unknown with original activity; explicit fixture action restores current evidence and a fresh subscriber view |

The [cleanup receipt](cleanup-native.json) verifies both namespaces stopped,
borrowed authentication/history removed and acceptance publishers stopped.
Ordinary preservation bookends are exactly equal on each host:
[Snap before](snap-before.json), [Snap after native](snap-after-native.json),
[Starship before](starship-before.json), [Starship after native](starship-after-native.json).
They cover provider configuration hashes, selected Observer/writer/frontend
links, the normal unit/service identity and the owning Codex daemon identity.

## Observer-only operational checkpoint

The managed operations tuple selects a5/API 2/read wire 4/service protocol 2
with Codex as the sole provider on both hosts. Runtime/history reconciliation
remains 30/120 seconds on Snap and 20/60 on Starship, with passive native hints.
The immutable archive supplies the checksum-bound artifact verifier, preserving
Starship's unrelated Observer checkout history. The normal writer stays at a16
through its independent `writerPrefix`. Provider policy and frontend selection
are outside the operation.

Scoped operations self-tests, candidate byte verification, six-target rendering,
unit syntax and upgrade dry runs pass. The full chezmoi check fails earlier at
`Rofi Tmux Plus archive pin drifted`; the unchanged baseline script reproduces
the same assertion before the Observer section. No Tmux Plus or Agent Plus
source/selection was changed to bypass it. Initial live applies also found a
missing rollback parent and stopped before any publisher change. Creating the
owned private parent resolved that operational prerequisite; the guide now
documents it.

| Case | Snap | Starship | Result |
| --- | --- | --- | --- |
| Restore a16 and reselect a5 | [rollback](snap-rollback.json), [reselection](snap-reselected.json) | [rollback](starship-rollback.json), [reselection](starship-reselected.json) | Six prior targets restored exactly; old active unit/read link confirmed; candidate reselection accepted |
| Restart and forced publisher failure | [recovery](snap-managed-recovery.json) | [recovery](starship-managed-recovery.json) | Old watches end; new PID/service incarnation recovers; fresh watch starts at sequence 1 with a view |
| Normal selected CLI/native comparison | [direct](snap-selected-direct.json), [cached](snap-selected-cached.json) | [direct](starship-selected-direct.json), [cached](starship-selected-cached.json) | Two bracketing rounds per host/mode, zero issues, 89/353 rows and all 2/5 running contexts agree |

The selected read client also passes filtering, attention/activity ordering,
human age, exact-reference show and doctor-count checks. Restart recovery takes
0.90/1.53 seconds; forced publisher recovery takes 6.19/6.63 seconds, including
the unit's restart delay. These actions touch only the owned Observer publisher.

[Snap rollout bookend](snap-after-rollout.json) and
[Starship rollout bookend](starship-after-rollout.json) preserve the original
provider configuration/hooks, workspace mapping, writer/frontend links and
ordinary owning Codex daemon incarnation. Read/service links and unit bytes are
the intentional changes. The final bookends follow sustained acceptance and
match each publisher's measured service incarnation. Installed bytes and exact
live unit arguments also pass [Snap verification](snap-live-verified.json) and
[Starship verification](starship-live-verified.json).

The [Snap sustained receipt](snap-managed-soak.json) and
[Starship sustained receipt](starship-managed-soak.json) cover 30 minutes of the
ordinary managed unit, three independent push readers, 100 process-based cached
CLI reads and an unread subscriber. Each publisher retains its PID/incarnation;
all reader sequences and leases remain valid, with zero reader errors.

| Measurement | Snap | Starship |
| --- | --- | --- |
| Duration | 1800.094 s | 1800.167 s |
| Cached CLI read p95, including process startup | 95.1 ms | 154.6 ms |
| Publisher cgroup CPU, percent of one core | 0.980% | 2.814% |
| Peak sampled aggregate RSS | 66.8 MiB | 75.4 MiB |
| Cgroup memory peak | 36.5 MiB | 45.2 MiB |
| Peak aggregate descriptors / owned processes | 23 / 3 | 23 / 3 |
| Frames per healthy reader / reader errors | 252 / 0 | 302 / 0 |
| Coalescing gaps per reader | 15 | 32 |

RSS sums shared pages across processes and differs from cgroup memory. These are
absolute workload measurements, not a matched incremental provider-cost proof
or a reinstatement of the superseded strict 64 MiB limit. Resource peaks stay
bounded throughout the run. The service explicitly emits `delivery_coalesced`
gaps when multiple revisions precede delivery, followed by a full resync. Healthy
readers therefore also need the contract's gap/resync handling; this is sampled
current-view delivery, not a lossless native event stream.

## Remaining boundaries

Catalog discovery remains bounded and non-archived. Missing native metadata and
classification remain unknown; sampled push has explicit gaps/resync and no
lossless replay/completion guarantee. Hosts are assumed always on for this gate.
Physical wake and post-TUI-closure lifetime remain deferred. Claude, mesh,
terminal/window matching, attachment/actions, user-facing alerts and downstream
GUI/device acceptance remain independent tracks.
