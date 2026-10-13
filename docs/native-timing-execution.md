# Native timing execution

2026-10-12. Execution of the approved [post-Mesh plan](post-mesh-timing-plan.md).
The selected a18 collector/a20 reader and Mesh a15 remain the baseline until
the following independent gates pass. Agent Plus and attachment stay parked.

## C0 decisions

The successor is Observer `0.6.0a1`, API 3, snapshot/watch 5 and Service 3.
These are breaking prerelease interfaces; there is no old-wire converter.
The independently selected historical writer is unaffected. Mesh's successor
Agent profile will use native wire 5 with SDK interface 1; Tmux's profile and
factory are unchanged. Its packaged schema/descriptor require a separate C4
review in Mesh before selection.

Adopt `lastUpdated`, `latestTurn` and `capabilities.timing` from the
[timing proposal](timing-contract-proposal.md). Turn IDs are opaque and nullable;
native boundaries have explicit millisecond units and precision. No observed
phase-series field is included. Existing activity/runtime/phase/outcome retain
their meanings. Codex timing requires a positively saved native identity.

Each native metadata response records wall time and BOOTTIME at observation.
Direct observations expose wall `observedAt` and a null receipt. Owned service
workers receive their original job start and component, and bind the normalized
record to that sample. The engine assigns the accepted provider incarnation's
context generation. A history job that refreshes runtime retains **history**
ownership for its timing: the same response does not acquire a longer/newer
lease through copying. The core remains independent of service boot identity;
Service 3 supplies boot/time-namespace and service identity.

Timing selection uses source observation order, including unavailable and known
empty observations. Replace the whole turn. Retained missing rows are stale;
they cannot borrow the newer component sample. Equal-order conflicts become
ambiguous; identical evidence keeps one original binding, conservatively using
the shorter deadline if distinct leases are possible. Never choose event-time
maximum or restore older completion when a newer observation fails/expires.

Current service timing must match its exact component/sample/context and lie
between sample start and emission, before lease expiry. Cache heartbeat and
unrelated component renewal cannot extend it. Stale records clear current
values and retain only previously admitted values and their original binding.
Malformed or unproved metadata is never converted to last-known evidence.

CLI timing labels describe native turn boundaries and thread update time.
Source-wall baselines advance with the matching BOOTTIME domain for local
cached timers. Contradictory sampled runtime/turn observations suppress a joined
ongoing timer; no phase-entry or lossless continuity is inferred. Remote clients
need Mesh's accepted clock/proof bridge; local device wall time is insufficient.

## Gate ledger

| Gate | Status |
| --- | --- |
| C0 schema/ownership decisions | Implemented strict API 3/wire 5/Service 3; [field specification](api-v3.md) |
| C1–C2 local core/service/read | Passed 395 local tests (24 optional Mesh tests excluded in the Mesh-free environment), 146 Markdown checks; 18 new production timing tests |
| C3 exact artifacts and independent two-host native proof | Pending |
| C4 successor Mesh Agent profile and fleet proof | Pending |
| C5 resource/managed rollback and selection | Pending |
| C6 read-consumer handoff | Pending |

The [acceptance matrix](timing-acceptance-plan.md) defines the required proof.
This ledger records progress, not deployment or native acceptance by declaration.

The old a15 Mesh-capable test environment correctly rejects the new source with
`mesh_sdk_incompatible`; its strict wire-4 profile is not silently expanded.
Full Mesh-capable checks resume under the separately accepted successor package.
The historical wire-4 schema bytes remain in frozen fixtures. Active native
validation scripts now require wire 5/Service 3; historical artifacts keep their
original script/source provenance.
