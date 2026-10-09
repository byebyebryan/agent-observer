# Disappeared runtime-only identity retention

Date: 2026-10-09. Status: authorized shared-core implementation checkpoint;
native artifact and operational gates remain pending. The [Claude wrap-up](claude-observation-wrap-up.md) remains
complete within its declared scope. API 2/wire 4/service 2 and selected a9 stay
unchanged. This work is independent of frontend implementation and provider policy.

## Problem and current evidence

`observation_evidence.retain_missing` retains missing rows as stale unknown when
the new source coverage is partial. The engine calls it for incomplete runtime
samples and a9 Claude deliberately never declares exhaustive runtime coverage.
Consequently a disappeared, unsaved identity can remain in the cached view
indefinitely, bounded only by existing row/byte limits. A direct read omits it.

The [ordinary review](evidence/2026-10-09-claude-wrap-up/REPORT.md) and original
[retention receipt](evidence/2026-10-08-claude-interactive-observer/selected-retention-limit.json)
observe UUID `4359adf3-32f1-49fb-ab95-cc780bfe68de`: cached stale unknown,
`hasSavedHistory=false`, original clocks and `retained_after_gap`, with no current
matching native registration/root transcript and no direct row. It does not
inflate active counts or establish parked. The practical defect is stale picker
clutter and differing direct/cache membership.

Do not fix this by claiming complete Claude coverage, guessing that a process
ended, restoring background compatibility, deleting native history or restarting
the service to hide the symptom. Observed identity retention is distinct from
native lifecycle authority.

## Boundary and required behavior

Core owns provider-neutral retention; adapters still own native evidence.
Service hosts the engine and direct sampled watch shares evidence helpers.
Consumers apply presentation policy without becoming a second native classifier.

- Retained disappeared unsaved identities need a finite retention bound. Eviction
  omits stale observation memory; it never asserts parked, ended or deleted.
- Time in retention must not renew on each incomplete read, metadata enrichment,
  heartbeat or reader connection. Preserve original evidence clocks.
- Never evict a row that is positively observed in the current accepted native
  sample because it has no saved history or an unsupported phase.
- Preserve saved identities and history/age across runtime faults. An SDK failure
  must not turn a saved conversation into an expired unsaved identity.
- Reappearance uses exact scoped identity and accepted sample order; it restores
  current evidence independently of any expired retention entry.
- Keep registry faults, partial coverage and the registration assumption honest.
  Retention policy cannot prove exhaustive native absence.
- Bound bookkeeping by existing row/byte limits and clock/context lifetime.
  Use injected host-local monotonic clocks, never conversation age or cross-host
  wall time. Direct watch and service delivery must declare their retention bounds.

## Accepted retention policy

The service binds each unsaved observation to its original runtime receipt lease,
using the injected host-local BOOTTIME clock. At the configured cadence the bound
is 90 seconds on Snap and 60 seconds on Starship, from the last positively
accepted native sample start. Repeated incomplete reads do not extend it. History
leases, enrichment, heartbeats, readers and delivery do not extend it either.
Receipt renewal does not renew missing-row evidence.

Sampled direct watch uses a fixed 60-second host-local BOOTTIME bound. The CLI
captures sample start before collection; slow collection cannot start the bound
at delivery. Expiry is applied at the next sample; a collection gap already
invalidates the view until resync. Single direct reads keep no prior identity
memory and need no retention policy.

Current accepted native rows remain protected, including unsaved rows with an
unknown phase. Positive saved proof from either component protects the identity
through SDK/runtime faults and preserves the original conversation clock. When
an unprotected deadline expires, both component caches drop the unsaved row so
an older history sample cannot resurrect it. Exact fresh reappearance supplies
new evidence. Deadline bookkeeping follows the bounded current component rows
and is not restored across collector/stream incarnations.

This is finite observation-memory eviction, never proof of parked, ended or
deleted. Full pushed views reflect the removal; it needs no additional native
event or alert. API 2/wire 4/service 2 remain unchanged. Additive bounded
limitation codes describe runtime-lease retention and the direct-watch bound;
they introduce no fields, enums or action capabilities.

The first frozen a10 native probe passed normal exit but rejected forced-kill
acceptance: the Claude adapter kept returning an unsaved dead registration as a
new unknown candidate. Renewing that candidate defeated disappearance retention.
The a11 successor also omits this provider metadata residue when a healthy native
bracket/guard and every matching interactive incarnation prove absence, with no
positive saved identity or relevant unresolved/background conflict. It does not
delete native files or assert logical session end. Saved records, live matching
incarnations and uncertain/faulted scans remain protected. This admission repair
belongs to the passive Claude adapter; service/core retain no Claude predicate.

## Execution and acceptance

1. R0 policy review is complete above: original runtime lease for service,
   fixed direct-watch bound, exact saved/current protection and no sliding
   deadlines. Source, artifact/native and operational proof remain separate.
2. Implement in `observation_engine.py`, `observation_evidence.py` and sampled
   watch as needed, with no provider-specific branch in the service/read client.
   Prove deadlines do not slide, current rows survive, reappearance works and
   saved metadata is not lost. Include runtime/history merge and delayed SDK cases.
3. Validate unchanged descriptors/schemas and pure consumer conformance. If a
   concrete public meaning or field must change, use its own versioned gate;
   do not silently extend wire 4 or infer that private cleanup requires a bump.
4. Freeze a successor artifact and independently prove isolated unsaved
   interactive New/normal exit and forced exit through direct/cache/push, along
   with source faults/recovery, reappearance and saved Resume age preservation.
   Reuse existing source facts within their bounds; do not rerun background
   lifecycle compatibility or ordinary session actions.
5. Compare the installed successor with ordinary native Claude on Snap and Codex
   on both hosts. Check exact membership, runtime/phase, user history age and child
   filtering. Only after producer acceptance perform its separate scoped
   read/service selection, recovery/rollback and consumer handoff.

Completion requires disappeared unsaved identities to retire by the accepted
bound without false lifecycle claims, active/saved loss or refreshed stale age.
Do not remove the accepted invisible-registration limitation or couple this
producer checkpoint to frontend work.
