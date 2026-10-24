# Codex timing and read-contract review

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-12. Research/validation checkpoint following the native-manager and
physical-dashboard direction. Codex is the only native provider. The current
API 2/read 4/Service 2/Mesh SDK 1 remains selected; this document proposes a
following timing checkpoint and changes no implemented wire or deployment.

The [post-Mesh reconciliation](post-mesh-timing-plan.md) supersedes the earlier
wait and temporary-Agent-Plus-launcher disposition below. Mesh's decision pass
is complete; native timing can proceed independently against SDK 1/IPC/SSH.
Agent Plus and its temporary desktop entry are parked, with Mod+A removed.

The following [turn/phase timing spike](codex-phase-timing-spike.md) validates
native turn elapsed time and a separate observed-phase-streak prototype. Public
implementation remains deferred while the externally owned Mesh loop finishes.

The following [offline goal pass](../delivery/timing-design-execution.md) settles a concrete
[draft layout and semantic rules](timing-contract-proposal.md), bounded model
and [implementation acceptance plan](../delivery/timing-acceptance-plan.md). It recommends
native latest-turn/update metadata first, with observational phase timing kept
outside that initial public extension. These supersede the open layout questions
below as design proposals, without implementing a new schema or deployment.

## Consumer scope

RLCD and ESP32-349 are the immediate read consumers. Native Codex Command Center
and Claude Agent View own interactive management. The temporary Agent Plus entry
is a host/provider launcher for Starship/Codex, Snap/Codex and Snap/Claude; it has
no Observer dependency. General attachment/window matching remains separate.

RLCD's existing study wants oldest current-state age within blocked, waiting and
working groups. That differs from Observer's conversation-activity ordering.
Its renderer supports unknown age, but an observation timestamp must not become
an exact phase-entry timestamp. Consumer presentation can select another named
clock; it must state what that clock means.

## Validated native facts

The [timing report](../../evidence/2026-10-12-codex-timing/REPORT.md) separates ordinary
managed-daemon reads on Snap/Starship from isolated native App Server transitions
with a deterministic local model source. No ordinary session, provider config,
normal service or deployment was changed. The native fixtures used no paid inference.

| Native clock | Observed meaning and limits |
| --- | --- |
| `updatedAt` | Native thread-update time. Advances during ordinary working turns and on tested completion/interruption. Also advances on a controlled cold load and paused-goal set/clear without a turn. Rename, one Git metadata patch and warm resume did not advance it in the controlled case. It is neither a universal conversation-event clock nor a phase-entry clock. |
| `recencyAt` | Provider recency-ordering clock. Equals latest turn start for the sampled saved rows; completion and tested goal changes leave it unchanged. This pattern is scoped evidence, not a universal formula. |
| Latest turn `startedAt` / `completedAt` | Explicit native turn boundaries. Started time includes subsequent blocking; completed time describes a terminal turn, including interruption. Neither describes every later phase episode. |
| `sectionEnteredAt` | Entry into an independently persisted user-visible section. Controlled section moves changed it while runtime stayed idle. Sections are user grouping, not normalized work phase. |
| Phase observation time | When Observer read current native status. Native status notifications have no transition timestamp in the inspected interface. |

In the controlled approval case, blocked-to-working changed status but left
`updatedAt` unchanged. Both native recency fields also advanced across reads for
five unsaved idle Starship children whose native turn metadata was unavailable.
Do not treat their returned timestamps as proved update/activity clocks. The
initial admission scope for new clocks should require positively saved native
metadata, leaving unproved runtime-only values unavailable without erasing their
independently known runtime/phase. A future reliable unsaved source needs its own
proof, not an arbitrary wall-clock threshold or title/age heuristic.

The current installed public `activity` matches the native latest-turn start or
completion clock in all 51 comparable ordinary samples. Its meaning is useful
and should remain intact. It does not expose the broader native update clock.

## Recommended next contract

Make a small explicit timing extension before finalizing a device feed that
needs these clocks. Keep the existing identity/runtime/phase/activity/outcome
meanings. The proposed new data is:

- `lastUpdated`: a timestamp evidence record for native session/thread updates,
  using `at`, source, health, reason and stale last-known context consistently
  with existing clock records. Initial Codex admission is saved-native metadata.
  Label it as last native update, including observed metadata effects.
- `latestTurn`: bounded metadata for the latest provider turn, with native turn
  ID, normalized status, nullable start/completion times and source/health
  provenance. The ID is scoped by the complete session reference. This lets a
  consumer name turn elapsed time or time since a turn ended without guessing
  which event the general activity clock represents.

These names/layouts are a concrete proposal, not implemented exports. Freeze
their exact schema, capability and receipt attribution in the next producer
checkpoint. Missing clocks remain null/unavailable; invalid new timing metadata
must not destroy independent runtime evidence. Preserve original native clocks
through cached reads, source faults, retention, reconnect and Mesh delivery.
Prove history-only and runtime-only expiry rather than letting transport,
heartbeat or unrelated liveness renew a clock.

Do not add an always-unknown `phaseSince` field as if it solved native timing.
Do not use `updatedAt`, turn start, custom section entry or a receipt timestamp
as a generic phase-entry clock. An observation-based duration is a separate,
explicitly labeled proposal with gap/episode semantics; it is not accepted by
this research or by the existing RLCD state-age design. Native recency ordering
can remain a provider diagnostic unless a concrete consumer requires it.

## Version and Mesh impact

The installed v4 validator rejects a proposed extra timing field with
`invalid_contract_fields`. Optional new fields would still be rejected by old
strict readers. A public extension therefore needs a successor contract rather
than unversioned fields or a silent reinterpretation of `activity`.

The proposed sequence is API 3 with snapshot/watch 5 and a successor Service 3
binding the new embedded snapshot. Commands and transport envelopes need no
extra operation merely to expose clocks. Confirm exact version scope when the
schema is frozen; do not bump unrelated action interfaces or provider versions.

Mesh a15's Agent descriptor binds native version 4, its packaged strict Agent
schema digest and profile v1. A new Observer wire requires an independently
reviewed successor Agent profile/schema/descriptor in Mesh, followed by owner
adoption. The generic SDK callback interface can stay SDK 1 if its signatures
and guarantees remain compatible; that does not make the current a15 descriptor
accept v5. Mesh owns its version/lock decision. Preserve Tmux's separately
selected schema, factory and native acceptance. No old-wire converter is required.

## Execution gates

1. Freeze the required timing fields, nullable/unsupported behavior, receipt
   attribution and public version tuple. Keep true phase age explicitly outside
   the guarantee. Resolve the companion Mesh profile contract before packaging.
2. Implement passive metadata projection, merge/expiry, public schemas/codecs,
   supplied fixtures and CLI diagnostics. Use already-read native fields where
   possible; do not add transcript/event capture or another collector.
3. Prove saved and runtime-only admission, metadata-only changes, turn identity,
   clock units, late/racing metadata, source loss and independent expiry. Check
   that phase and original conversation activity are not reinterpreted.
4. Independently accept exact installed artifacts, ordinary direct/cached native
   comparisons on both hosts and local/fleet pull/push. Measure the added
   validation/copy cost and prove cleanup and conservative mismatched versions.
5. Adopt read/service/publisher roles through their scoped operational gate,
   preserving shared Agent/Tmux factories and captured rollback. Then hand the
   accepted tuple to the RLCD consumer for device-feed/native/physical acceptance.

The other agent's existing Observer work remains independently owned. This
review edits no runtime or existing handoff. The Agent Plus temporary launcher
can proceed now; RLCD may prepare its host adapter, bounded device feed and
unknown-age handling against the accepted contract while the timing producer
checkpoint is settled. A consumer defect reopens an Observer checkpoint rather
than coupling producer and device implementation in one pass.
