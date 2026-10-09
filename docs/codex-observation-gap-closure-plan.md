# Codex observation gap closure

Date: 2026-10-08. This follow-up closes actionable findings from the read-only
a5 review. The existing [ownership boundaries](observation-boundaries.md) and
[API 2](api-v2.md) remain authoritative. Codex is the sole live adapter;
Claude, mesh, attachment/actions, alerts, physical wake and post-TUI-closure
lifetime remain separate checkpoints.

## Execution and acceptance

| Checkpoint | Work | Acceptance |
| --- | --- | --- |
| G0: current validation | Reconcile the CLI validation workflow and record this sequence | Current daemon status, direct/cache/push and Codex-only scope are explicit; historical provider evidence stays labeled; repository checks pass |
| G1: atomic views | Accept a history sample and its runtime facts as one published engine view | One accepted sample advances one revision; both receipts preserve their independent leases; a healthy socket reader sees a contiguous next view; genuine coalescing still emits gap/resync |
| G2: helper retirement | Reproduce and instrument the intermittent transferred-anchor/deadline assertion; fix the demonstrated cause | Owned groups and descriptors retire on deadline/crash without signaling providers; bounded repeated controlled tests pass; any unresolved cause remains explicit |
| G3: metadata limits | Independently inspect missing native clocks and unknown kinds, including visible and recent rows | Distinguish absent native metadata from producer omission; no inferred conversation clocks, child guesses or private history compatibility path |
| G4: installed/native | Freeze and separately install a successor artifact on Snap and Starship | Installed direct/cache/push agree with independent owning-daemon identity/state/age; changed transport behavior is proved; ordinary provider configuration/incarnations remain unchanged |
| G5: scoped operations | Select the independently accepted read/service tuple and validate recovery and sustained readers | Only Observer read/service selection changes; writer/frontend/provider policy remain intact; a5 rollback/reselection and native comparison pass |
| G6: closeout | Review findings, receipts, contract/handoff and final patch; commit accepted checkpoints | Source/artifact/selected/native evidence is distinguished; remaining source limits and deferred features are stated; no push |

Run `./scripts/check` before each commit. Keep mutations and acceptance stages
sequential. Use owned fake sources for transport/helper failures and existing
authenticated Codex endpoints for ordinary native reads. No ordinary provider
action is necessary for these changes. Preserve Starship's separate checkout
history by delivering frozen artifacts and standalone harnesses.

Selecting a successor requires its independent artifact/native gate first.
Keep the selected a5 read/service tuple and a16 writer available for rollback.
If operational acceptance fails, restore a5; do not restart Codex, edit terminal
runtimes or change a frontend to make a producer check pass. Metadata limits
that originate in the provider are documented rather than filled by inference.

Push remains sampled current-view delivery. Removing redundant publication
does not establish native event replay, completion alerts or lossless delivery.
