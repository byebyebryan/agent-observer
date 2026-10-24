# Deferred snapshot/delta-sync feature

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The 2026-10-20 [Mesh a24 dependency upgrade](../design/mesh-a24-complete-view-upgrade.md)
keeps this engine dark and also leaves a24's separate view-feed protocol
unselected. Observer uses ordinary complete selected-view delivery; installing
a package containing opt-in delta modules does not enable either route.

Disposition, 2026-10-17: Bryan directed wrapping this work as a gated, dark
feature and releasing its development hold on repository cleanup. Active G1
optimization and qualification stop at the preserved checkpoints below. Resume
requires a new explicit work request. Earlier continuation notices and scheduled
follow-ups do not override this disposition.

This is an unreleased implementation with bounded source evidence. Producer,
performance, native, installed-pair and consumer adoption gates remain failed
or open. Closed contracts and narrowly verified lifetime findings stay closed;
deferral does not turn them into whole-producer acceptance.

## Default-off service gate

`agent_observer.service_runtime.Runtime` defaults to
`experimental_sync=False`. Full and active sync requests close without a sync
response before creating an owner/cache or constructing sync material. Existing
Service 4 and active-feed 1 requests remain usable. The ordinary service CLI,
Mesh factories and selected launchers expose no sync enablement.

Disposable library experiments must explicitly construct
`Runtime(..., experimental_sync=True)`. Compact material additionally needs
`ServiceState(..., sync_serialization="compact")`, the explicit compact source
and matching transport/Reader codec. These choices enable an experiment; they
do not qualify it for use. Existing direct pure-library interfaces remain
available for replay. There is no automatic encoding sniff, fallback, service
start, package installation or route selection.

The guard has socket tests for both views, rejection before cache creation,
continued full/active legacy reads and exact-boolean option validation. Existing
sync delivery/source fixtures opt in explicitly. The final canonical check and
dual-Python focused results accompany the cleanup handoff. Historical test and
benchmark artifacts retain their original source tuples.

Observer a7 / Mesh a23 active roles, full a5/a20 diagnostics/read roles, Tmux,
349, the writer and native providers retain their independent selections.
There is no new artifact, encoding/schema allocation, freeze, install or rollout.

## Preserved results and failed gates

| Area | Last bounded result | Remaining gate |
| --- | --- | --- |
| Contracts and small synthetic pipeline | G0, A1, compact normalization/raw compatibility and controller agreements closed; actual disposable IPC/source/relay/independent Reader checks pass | Ordinary authenticated route, populated native/fixed SSH and immutable installed pair |
| Source lifetimes | Scoped consuming-ref, watch/cancellation, material and controller cleanup findings closed | Inclusive physical ownership/RSS and overlap at production scale |
| Reader capacity | Observer `b6ce8428` + Mesh `03a681f9`: 100/500-row baseline, two generations and fresh heads pass on default/private packed backends, both Pythons | All four 2,000-row baselines refuse `sync_decoded_capacity` before proof scratch under the unchanged 64 MiB cap |
| Owner CPU | Latest row-reuse screen: +165.5685% at 500 and +143.5020% at 2,000 versus the matched old owner, excluding the oracle | Hard FAIL against the maximum +25% increase |
| Recovery and broader scale | Five fallbacks per measured 2,000-row owner run; no ensuing recovery baseline delivered | Deliverable cold/recovery, dense nine-field/full+active/slow-peer and deadline qualification |

The [CPU evidence](delta-sync-compact-row-reuse.md),
[profile storage checkpoint](delta-sync-profile-patch-storage.md) and
[field-reference compatibility receipt](../../evidence/2026-10-17-field-ref-compatibility/README.md)
retain their exact scopes. Latest baseline-bucket evidence is Mesh
`d483351d302bdc090f62bcaa18029788b7ec75be`,
`docs/evidence/2026-10-17-baseline-buckets/README.md`, SHA-256
`ef1a1852e51e8ba8ae17583d94555a6b39d7989e9754e29e8dfa1d466e0ac990`.
RLCD independently records its source clearance at
`2242552cd2c3e0a456dbdb31d84447487568e37e`.

Observer's independent latest 64+76 focused methods per Python passed with GC
disabled; saved capacity/census/traces were hash-checked without replay in
`.cache/baseline-bucket-compatibility-20261017/review.json`, SHA-256
`e13b66e15df51fdc834633d47d69a2d70e18c105181db8c5dd5ffb6eb8e110c0`.
That cache-only result does not expand the committed capacity evidence.

Keep the overlapping 32 MiB encoded / 64 MiB heap limits and original 2-second
proof / 15-second catch-up bounds. Accounting reductions are not physical RAM
savings; near-limit refusal permits no estimate reduction or cap increase.
No unrun dense, RSS, native, transport, installed or physical gate is passed.

## Resume and repository handoff

The final Observer wrap commit contains this document and the default-off
guard, descending from evidence `51b0f27559b2b1553ffb60d04992ba90e639d873`.
Before that guard, the latest Observer implementation is
`b6ce8428b7f9d451bc9e99ca6f8e2943c656c23f`; latest reviewed Mesh runtime is
`03a681f95a609b20eaa20134f7241d3d14d441a6`. The next unimplemented generic
storage idea was packed-tree grafted-control ownership. It is excluded from
these results. Resume from exact frozen sources and supported public APIs;
deliverable 2,000-row capacity and the owner CPU failures come before expanded
qualification or release identifier allocation.

Observer owns branch `observer-delta-sync-20261016` in
`/home/bryan/code/agent-observer-active-feed`. Commit tracked work/evidence
before Git clearance. All prior source/evidence ancestors, including Mesh's
Observer pin `af2bc7bf9316bc0fb58c83ec8f560a83788467e4`, released tags/artifacts
and their exact bytes remain protected. Preserve the untracked `.cache` evidence
or its verified external archive before removing that worktree. Other Observer
worktrees and branches have separate owners.

The explicit final Git handoff identifies the wrap commit, verified external
Git bundle/cache archive, child/process and reminder state, and remaining
exceptions. That handoff releases this task's HOLD for existing cleanup scope
while preserving those recovery objects. It does not authorize deletion of
unrelated work, published history, artifacts or sibling data. Mesh and RLCD
provide their own clearances. No pending experiment or automatic continuation
is to restart this effort during cleanup.
