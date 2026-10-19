# Working-set qualification status

The active-plus-recent design is settled, with a default of 72 hours and an
explicit full-history path. Its Observer source candidate is implemented and
the reported clock, gap and refusal defects are corrected. It is ready for an
overall design/integration review. It is not yet an end-to-end usable or
producer-qualified feature.

The remaining work has two parts: stabilize metadata size/capacity on the
Observer side, and register the new profile/schemas on the Mesh side so the
ordinary public Reader can run it. Mesh registration is necessary, but is not
the only remaining gate. Independent native, inclusive resource, workload cost
and installed-pair validation follow. No further implementation or experiment
is being started for this checkpoint.

This audit applies to the opt-in candidate at source `bb7b8aa`, with resource
evidence committed at `610afaa` and the additional
[review checkpoint](evidence/2026-10-18-working-set/review-checkpoint/README.md). It keeps the
[execution plan](working-set-projection-plan.md) exit criteria intact. A source
test, a recorded review and an installed/native producer proof establish
different boundaries. The feature is not released or selected.

| Requirement | Current evidence | Status and remaining proof |
| --- | --- | --- |
| Everyday 72-hour workload is useful | [P0 cached samples](evidence/2026-10-18-working-set/p0/README.md): Starship 400 full rows / 12 selected estimate; Snap 102 / 4 | Sizing screen complete for those two samples. These published-field estimates are not selection-authority or native parity proof. |
| Exact union, clocks, uncertainty and coverage contract | Joint R1/R2 review and [R3 correction](working-set-contract-r3.md), preserved in the [contract record](evidence/2026-10-18-working-set/joint-contract/README.md) | Contract direction accepted. Source helper overflow/active-independence corrections are covered separately from producer qualification. |
| Canonical-worker clock authority installs only on accepted input | [Worker provenance correction](working-set-worker-provenance.md) and preserved independent review | Bounded source prerequisite clear. Mocked process/pipe tests do not establish a live provider clock bridge. |
| Nonterminal gaps cannot renew recency or reader time | [Client gap correction](working-set-client-gap.md) | Bounded policy prerequisite clear. Actual registered SDK guard, Reader proof, gap and resync still need execution. |
| Failed encoded staging cannot allocate an unadmitted replacement | [Encoding refusal correction](working-set-encoding-refusal.md) | Bounded source prerequisite clear, including a saturated test-only counter. This is not evidence of a default-limit or process-memory overrun. |
| Immutable window and lossless source/profile/facade path | [Native candidate](working-set-native-candidate.md) and [client candidate](working-set-client-candidate.md) | Implemented source candidates. Mesh a23 deliberately rejects the unregistered profile; no fake descriptor or fallback is permitted. |
| Public SDK registration and ordinary Reader admission | Exact prospective registration slice reviewed by Mesh; existing profile remains unsupported | Open. Needs additive profile/native/request schema and package copies, descriptor/validator and trusted-factory allowlists, append-only lock parity, real admission/preparation/Reader tests and isolated package parity. The Mesh owner remains review-only pending the scope decision. |
| Shared full/active/working-set encoded ownership | [Source resource matrix](evidence/2026-10-18-working-set/resource-source/README.md): 22 reports, 14 complete selections and eight explicit tracking refusals. Additional [slow-reader pressure](evidence/2026-10-18-working-set/resource-pressure/README.md): two fourteen-generation runs at the sixteen-client/default-budget limit | Recorded counter equations and stage admission reconcile; two oldest pinned readers naturally drop per run while healthy full/active/working-set readers survive. A dropped Peer temporarily retains encoded bytes inside `_room` after cache retirement without appearing in its counter. Both disappear by room return, but inclusive transient/physical accounting remains open; no cap-overrun or full memory pass is claimed. |
| Varied size, density and burst capacity | Same matrix: 100/500/2,000 full rows, three selection ratios, ordinary and long valid fields | Small 2,000-row selections complete. Larger selected unions refuse the tracking budget. They are capacity failures, not complete 72-hour views; no cap or estimate exception is accepted. |
| Matched owner and repeated-read cost | [a7/C6 source cost components](evidence/2026-10-18-working-set/performance-source/README.md) | Favorable bounded source comparison at four reads per generation. The original tuple remains a7/C6; no reattribution to later fixes. One/sixteen-read cadence, varied ratios, quiet timers, failures/recovery and applicable transport/copy work remain open. |
| Savings across selection density | [Current-source native byte screen](evidence/2026-10-18-working-set/wire-density-source/README.md): twelve cases per interpreter | At 500 rows, 25/50 selected save 86.65%/73.66% of native frame bytes; 100 selected occupies 20.88% of original row bytes but saves only 47.94%, below the 50% component target. All four larger 2,000-row unions refuse tracking. These are current native-component results, not the complete accepted-a7/SDK/transport byte gate. |
| Smaller receipt representation | [Support-density model](evidence/2026-10-18-working-set/support-density-model/README.md): whole eight-field receipt maps interned in a hypothetical per-scope table | Model only. For 500/100, exact round-trip arithmetic reduces the current 325,455-byte working frame to 179,184 bytes. No production packing, revised native schema or capacity pass is implemented. The refused 2,000/100 case supplies only a partial pre-failure scope; its full modeled capacity is unknown. |
| Heap/RSS and physical lifetime | GC-disabled source accounting and process RSS context in the resource matrix | Open. Encoded owner/cache/peer buffer accounting does not cover every Python DTO/container, fixture/oracle or transient allocation. No production RSS bound or plateau is established. |
| Independent populated native parity on both hosts | P2 synthetic/disposable IPC and worker tests; P0 public cached counts | Open. Another Observer result is not independent provider evidence. Current source tests do not prove an installed candidate against ordinary native sessions. |
| Exact immutable installed pair, IPC/fixed SSH and rollback | Legacy a7/a23 remains selected; working-set package/schema identifiers remain candidates | Open. No new pair is installed, no fixed-SSH working-set route is qualified and no normal-role change is inferred. |

The repository gate at `610afaa` passes 1,072 tests with zero skips, plus 228
Markdown/link/whitespace checks. That establishes repository regression and
documentation consistency, not all rows of this audit.

The checkpoint recommendation is to review the intended workload and one
bounded receipt-representation revision before investing in Mesh registration
against the current grammar. The model is promising enough to justify that
discussion, but does not justify changing limits or promising 2,000-row
capacity. Exact proposed grammar and lifetimes would need owning review before
implementation; current P1 semantics and original evidence remain intact.

Mesh's current assignment is review-only. Its required additive registration
work includes profile/native/request schema copies, descriptor/validator and
trusted-factory entries, lock/package parity and real public Reader tests.
That scope decision remains outstanding. No new generic SDK API has been
identified. Registration does not authorize installation or adoption.

P3 remains open until its actual producer exit criteria are proved. P4 consumer
adoption remains separately authorized. Preserve the selected a7/a23 and
independent full/Tmux/writer paths, original evidence, pinned objects and the
completed repository-cleanup disposition.
