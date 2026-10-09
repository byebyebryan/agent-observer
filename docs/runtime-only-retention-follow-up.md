# Disappeared runtime-only identity retention

Date: 2026-10-09. Status: scoped shared-core follow-up; no implementation or new
artifact accepted here. The [Claude wrap-up](claude-observation-wrap-up.md) remains
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

## Execution and acceptance

1. Review the concrete policy before implementation: original accepted runtime
   lease versus a separate finite retention window; source-read failure behavior;
   component merge, context replacement, watch parity and diagnostics. The
   original runtime lease is a candidate, not a settled new guarantee.
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
