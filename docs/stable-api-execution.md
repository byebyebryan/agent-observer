# First stable API execution

Date: 2026-10-06. Status: active regular goal loop, authorized by the user.
This executes the [contract review](discovery-monitoring-contract-review.md)
and [provider compatibility policy](provider-contract-compatibility-plan.md).
Commit independently reviewed checkpoints; do not combine Observer repairs with
Agent Plus implementation or change ordinary provider sessions/settings/hooks.

## Sequence and acceptance

| Checkpoint | Deliverable | Acceptance |
| --- | --- | --- |
| S0: execution capture | This sequence and the existing eight review findings | Clean baseline; explicit scope and independent gates |
| S1: public correctness | Write-result identity invariants, stale conversation age, child reconciliation, row/byte/node bounds and bounded watch retention | Regression cases from the installed-a11 review; maximum serialized round trips, repeated partial churn and recovery; no provider actions |
| S2: native contract compatibility | Capability profiles independent of provider version/hash; executable provenance/incarnation guards, row fault isolation and independent-reference coverage | Compatible image changes/additive native fields, incompatible required fields, unknown states and duplicate workers; current native reads remain a separate gate |
| S3: first stable API candidate | Public JSON/Python/CLI scope, compatibility/error policy, title meaning and capability semantics; schemas and pure consumer fixtures | Strict versioned validation, negative semantics, independent reader and public CLI conformance; no provider-release enums |
| S4: packaged/native acceptance | Immutable Observer candidate and metadata-only evidence on Snap/Starship | Installed CLI versus independent native IDs/titles/state/age; isolated affected New/Resume/parked/phase/recovery cases; passivity and owned cleanup |
| S5: client handoffs | Accepted interface/artifact, limits and migration notes for Plus and read-only consumers | Documentation/conformance gates; no frontend implementation or rollout |
| S6: notification checkpoint | Separate normalized source/client and notification contract, with publication separate from passive observation | Identity/kind/title reuse, event correlation/deduplication/gaps, continuation and partial evidence, synthetic transport and isolated native proofs; explicit unattached/remote/focus limitations |

Public correctness can precede the larger compatibility refactor when it has no
native dependency. S4 accepts the combined candidate before S5 relies on its
native behavior. S6 is independent of stable read/write acceptance and cannot
retroactively turn sampled watch into a lossless event feed.

The first stable API label is separate from wire and package versions. Stale age
and SDK-version representation require a prerelease observation-wire cutover:
do not silently extend strict wire v2. The write wire remains v1 when corrections
only enforce its already intended semantic invariants. Select the observation
wire version explicitly in the implementation and conformance corpus; retain
historical a11 evidence without rewriting it as new acceptance.

## Native and downstream boundaries

Use ordinary sessions only for passive, independently timestamped comparisons.
Native writes, runtime recovery and hook proofs use disposable owned contexts
whose isolation is established first. No runtime startup is a compatibility
probe. Versions/hashes identify test provenance and changed action context,
never the ongoing provider support list.

Managed entrypoint selection and notification hook installation retain separate
scoped artifact/native gates. Notification GUI focus/Open and ESP32 physical
acceptance require their own evidence; a controlled sink is not desktop proof.
Keep desktop sender/title changes out of the read/write contract acceptance.

## Progress

- S0: clean Observer baseline `7b69894`; no implementation accepted yet.
- S1: write-result cross-object identity, operation/effect/pending and route
  invariants repaired; copied Claude identities and confirmed-effect/no-viewer
  cases remain valid. Source check passes 214 tests. Watch repairs remain pending;
  no new packaged/native acceptance is claimed by this validator-only change.
- S1 source candidate additionally uses observation wire v3 (`0.3.0a1`): stale
  age provenance, reconcile-before-filter, row/byte/node alignment and bounded
  retention/gap recovery. SDK diagnostic text no longer has a release enum.
  The [v3 contract](public-contract-v3.md) records the explicit consumer cutover.
  Full source check passes 220 tests, including 4,096-row snapshot/watch round
  trips, repeated maximum-row churn and serialized-byte eviction. Candidate
  packaging/selection remains pending.
- S2-S6: pending. Update this record at reviewed checkpoints with concrete
  source, packaged and native results and any remaining capabilities.
