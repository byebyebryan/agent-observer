# Codex observation completion acceptance

Date: 2026-10-08. Status: a5 source, separately installed artifact and native
observation gates are accepted on Snap and Starship. Managed rollout is the
following checkpoint; this report initially leaves normal a16 selection intact.
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
implementations. All 379 tests pass (one skipped), with 88 documents checked;
scoped Ruff checks pass. These are static/controlled/real IPC checks, not native
provider fault injection.

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

## Operational checkpoint and remaining boundaries

Observer-only normal read/service selection, restart/crash/reconnect,
rollback/reselection and sustained normal-unit checks follow this native gate.
The independent writer and frontend selections remain preserved at rollout.

Catalog discovery remains bounded and non-archived. Missing native metadata and
classification remain unknown; sampled push has explicit gaps/resync and no
lossless replay/completion guarantee. Hosts are assumed always on for this gate.
Physical wake and post-TUI-closure lifetime remain deferred. Claude, mesh,
terminal/window matching, attachment/actions, user-facing alerts and downstream
GUI/device acceptance remain independent tracks.
