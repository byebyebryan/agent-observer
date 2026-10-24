# Timing implementation and acceptance plan

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-12. Companion to the [draft specification](../design/timing-contract-proposal.md)
and [offline execution](timing-design-execution.md). This plan does not authorize
an immediate networking/profile/deployment change. The completed Mesh performance
pass and its separate candidate retain their ownership and exact artifact bounds.

The [post-Mesh reconciliation](../design/post-mesh-timing-plan.md) updates the execution
ordering after the completed external decision: keep SDK 1/IPC/SSH, do not merge
or select private a21, implement local timing before successor Agent profile
adoption, and keep Agent Plus/attachment parked. Native/profile/operational
gates below remain separate and no timing version is implemented by this update.

The subsequent [execution ledger](native-timing-execution.md) and
[rollout receipt](../../evidence/2026-10-13-native-timing-rollout/REPORT.md) now accept
API 3/wire 5/Service 3, explicit Agent profile v2 over SDK 1, exact native proof,
managed selection and producer handoff. The proposal/offline language below
records the plan's earlier state; consumer/device work remains separate.

## Completed offline scope

The [offline report](../../evidence/2026-10-12-timing-design/REPORT.md) binds a standalone
normalized-metadata prototype, selected captured native replay and synthetic
cases. These establish design behavior, not a new public decoder, real process
lifecycle, live BOOTTIME behavior, managed daemon coverage or device acceptance.
Earlier ordinary/native clock receipts keep their independent topology bounds.

| Requirement | Offline acceptance | Still needed in production |
| --- | --- | --- |
| Native clock meanings | Earlier native metadata/goal/load/approval/question proofs; nineteen-sample replay | Current ordinary daemon comparisons against exact successor on both hosts |
| Stable turn vs changing phase | Same native start through working/blocked/working; separate observed-series reset | Packaged current-turn projection and held blocked cases |
| Activity preservation | Prior 51/51 comparable native/public samples; no source edit | Exact old/new semantic comparison, including latest completion/start and missing clocks |
| Identity and timing scope | Full host/provider/store/id-kind/native-ID keys; Observer/clock/source generations | Actual worker/service envelope and wrong-context admission |
| Lease ownership | Runtime/history metadata selection and independent expiry | Wire binding validation, original read-end stamps and idle cache expiry |
| Unknown/new-turn replacement | Known empty or newer in-progress/missing clock supersedes old terminal; no expired fallback | Engine merge/retention under real coupled component receipts |
| Read races | Idle/in-progress, working/terminal, different IDs and later native start suppress joined timers | Deterministic transport-controlled races and selected ordinary sampling |
| Source gap/restart | Failure, partial omission, unknown, expiry, new source generation and new observer | Real helper/source/service restart, recovery and receipt cleanup |
| Optional phase observations | Bounded source watermarks/live series; reader arrivals do not reset; no metadata-only renewal | Separate decision and exact implementation/native gate if exposed |
| Resource/capacity | Bounds and independent observation behavior in tiny offline fixtures | Normal/capacity CPU/RSS/frame-size and immutable runtime measurements |
| Mesh/client delivery | Required timestamp/lease/clock information described | Successor profile, both-host pull/push/proof/clock/fault acceptance and device policy |

## Following producer sequence

| Gate | Work | Exit evidence |
| --- | --- | --- |
| C0 — scope/schema review | Reconcile the completed Mesh candidate and this design; freeze names, nullable/last-known behavior, exact timing capabilities, receipt binding and version tuple | Reviewed strict schema/semantic examples and Mesh-owned profile/version agreement; no deployment |
| C1 — core projection | Native metadata normalization and observation stamps; whole latest-turn replacement, explicit origin component, stale last-known behavior | Meaningful adapter/engine/cache fixtures; preserved activity/runtime/phase/outcome; no new transcript scan/collector |
| C2 — public/service/read | New schemas, pure codecs/guards and CLI presentation; Service binding and timing-specific cache expiry | Old versions/extra fields rejected cleanly; local direct/cached pull/push agree; pure readers import no provider/action code |
| C3 — immutable native proof | Build clean exact bytes; independent installed public CLI vs native ordinary/owned sessions on Snap and Starship | Identity/phase/turn/update/activity comparisons, held working/blocked/terminal/missing/race/gap/recovery; sanitized bounded receipts |
| C4 — Mesh acceptance | Owner adoption of separately accepted successor Agent profile/descriptor with original leases and clock handling | Mixed-host pull/push/proof/resync/restart/stale/partial/sibling failure and cleanup; Tmux unchanged; no automatic old-wire converter |
| C5 — resources/operations | Compare exact accepted baseline/successor, frame growth and sustained cached consumers; scoped selector/unit/publisher change and rollback | Attribution, ordinary native/state preservation, exact selected bytes and managed rollback/reselection |
| C6 — consumer handoff | Export accepted schemas/examples/commands and supported clock semantics | Producer schemas/commands/clock-policy handoff delivered; RLCD/349 independently accept roster/clock/age policy, feed loss and physical rendering as separate consumer gates; attachment/actions stay external |

The proposal anticipates API 3, snapshot/watch 5 and Service 3; C0 decides their
actual required scope. Mesh's generic SDK can remain 1 when signatures and
guarantees remain compatible, but its strict current Agent profile cannot read
the proposed new native fields. A Mesh-owned successor profile is required.
Do not renumber Tmux or the independently selected historical writer solely for
read timing. Provider versions/hashes record diagnostics/provenance, not support
allowlists. New required native contracts need their own focused proof.

## Mandatory implementation cases

1. Positively saved current working/blocked/idle/parked metadata; empty latest
   history and missing native boundaries; unknown native status and invalid
   timestamps/precision/duration. Invalid timing must not erase valid phase.
2. Native thread-update changes during work, completion, cold load and metadata
   changes. Verify that these never rewrite conversation activity or become
   phase entry. Runtime-only unproved values stay unavailable, not last-known.
3. Distinct native turn ID and session-tree ID; nullable turn ID for an explicitly
   capable future adapter; same-phase new turn and same-turn blocked recovery.
   Normalize interruption without claiming successful completion.
4. Non-atomic detail/turn reads: newer turn start after earlier status, observed
   turn IDs disagreeing, idle/in-progress, working/terminal, and compatible
   samples with no claim of lossless continuity. Reconcile without TUI matching.
5. Each field's runtime/history receipt independently expires. A current native
   timing field survives unrelated component expiry where its actual receipt
   stays valid, but current-turn display stops when phase/runtime expires.
6. Newer in-progress/known-empty/unknown/failed metadata and later expiration
   cannot restore older completion, fill a new start from an old turn or choose
   the largest event timestamp as if that were observation order.
7. Coupled history/runtime acceptance publishes once, with real origin binding;
   duplicate carrier frames cannot mutate core tracking. Concurrent equal-start
   reads need a proven tie rule, never a longer-lease/current promotion shortcut.
8. Provider incarnation, Observer restart, boot/time namespace changes, late
   old-helper replies, source failures and partial rosters. New clients/reconnect
   can recover fresh native times; stale anchors are never replayed as facts.
9. Clock units/precision and delayed collection. Read time consumes the original
   lease. Known source-clock anomalies keep native values intact while derived
   age becomes unknown. Remote source-age advancement uses Mesh's accepted proof.
10. Byte/row/capacity pressure: no hidden transcript payload, no discovery row
    dropped only because optional timing cannot be tracked, no unbounded timing
    history/tombstone store. Report CPU/RSS/validation cost without assuming the
    standalone prototype predicts runtime performance.

## Optional observation-series checkpoint

The first public extension excludes this record. If a concrete client accepts
observed-series age, review a separate C0 addendum rather than silently naming
it `stateSince`. Prove first positive observation, repeated reads, native turn
identity appearance/loss/change, normalized blocked reasons, source gaps,
partial healthy siblings, capacity, source-order fences, client reconnect and
copy ownership. A missed same-turn phase cycle remains an accepted sampling
limit; neither callback receipt time nor current-state push makes it exact.

The core owns the bounded series state; the service hosts it. Any proposed
series identifier binds Observer/source/clock scope and is explicitly not a
native episode ID. Durable persistence, event replay, notifications and higher
poll frequency are excluded unless separately requested and proved.
