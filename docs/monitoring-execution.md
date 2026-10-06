# Monitoring execution checkpoint

Date: 2026-10-05. Status: complete within the accepted a10 candidate subset;
source and native acceptance are recorded separately. This regular goal loop follows the
[CLI/native validation workflow](observation-validation-workflow.md) after the
[evaluation repair](evaluation-repair-execution.md).

## Scope and sequence

1. Capture exact installed/runtime artifacts and preserve the selected a9
   baseline, ordinary provider stores, hooks and running sessions.
2. Prove current Claude 2.1.289 phase predicates in owned disposable namespaces.
   Compare direct metadata with independent native behavior. A supported roster
   CLI may be a disposable reference; its registry cleanup prevents assuming
   production passivity. Completion markers must not settle later work or live
   child/background work. First-prompt readiness differs from a question or
   approval during a turn. Hooks, if necessary, have a separate isolated proof
   and no automatic installation gate.
3. Project explicit latest Codex turn outcomes independently of current phase.
   Read metadata with items unloaded; a runtime error alone is not a failed turn.
4. Explain bounded Claude history exclusions, companion duplicates and unresolved
   candidates without inventing conversations or claiming complete history.
5. Freeze a new artifact; compare its installed public CLI outside the checkout
   with independent native evidence on Snap and Starship. Validate the unchanged
   strict v2 contract and frozen consumer reader before accepting the package.
   Commit accepted checkpoints and record unsupported cases honestly.

## Acceptance and boundaries

Native cases cover first prompt, held work, held approval/question, completed
turn, failed/cancelled outcome, concurrent child work and observation failure.
Static, synthetic, isolated native and ordinary native evidence are labeled
separately. Only independently established predicates enter exact-image gates.
Reports retain bounded identity/state/timing/reason metadata, never conversation
content, raw provider payloads, tool arguments/output or credentials.

No Agent Plus implementation, ordinary provider restart, older TUI cutover,
recent-cwd contract revision, broad networking, physical suspend or public release
belongs to this checkpoint. Candidate installation does not select production
entrypoints or install hooks. Ordinary sessions remain available throughout.

## Checkpoints

- M0: exact preflight and private namespace preparation accepted.
- M1: native predicate proof and source changes accepted within the
  [monitoring report](evidence/2026-10-05-monitoring/REPORT.md)'s exact-image bounds.
- M2: final immutable a10 package, outside-checkout CLI/native comparison on both
  hosts, unchanged strict v2/frozen-reader compatibility, isolated native entry
  and recovery, cleanup and review accepted. See the
  [package evidence](evidence/2026-10-05-monitoring/package-acceptance.json).
  Candidate installation leaves selected a9 and frontend sources unchanged.
