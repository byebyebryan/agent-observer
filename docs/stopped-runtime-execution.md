# Stopped runtime checkpoint

Date: 2026-10-05. Status: in progress. This Observer-only regular goal loop
follows the [validation workflow](observation-validation-workflow.md) after the
[monitoring checkpoint](monitoring-execution.md).

The user explicitly stopped two exact Claude jobs. Independent native reads
confirmed stopped/idle retained jobs and exited workers, while both installed
a9 and candidate a10 returned unknown runtime. Correct that producer gap using
the existing v2 `parked` vocabulary; work phase and conversation outcome remain
separate. Saved history alone and worker disappearance alone do not prove parked.

## Sequence and acceptance

1. Preserve ordinary provider settings, stores, hooks and runtime processes.
   Establish a disposable user/mount/PID namespace with masked provider paths.
   Prove current-image native stop, viewer detach and native restart/resume
   independently of Observer. Confirm the native stopped job's identity, terminal
   clock and absence of a bound live worker before accepting a predicate.
2. Project parked only from a unique, stable, exact-UUID stopped/idle or done/idle retained job
   under the accepted image and complete relevant inventories. Recheck inventory
   membership, identity and candidate state after worker checks. Live, unsupported,
   ambiguous, partial, changing or unavailable evidence prevents parked.
   Add meaningful regression cases for stale stops, resumed/duplicate workers,
   duplicate jobs, missing clocks, capped reads and collection races.
3. Freeze a11; validate its installed public read/write clients outside checkout,
   controlled stop/resume, ordinary native comparisons on Snap and Starship,
   strict v2 and frozen-reader compatibility. Keep clocks and identities intact.
4. After independent producer acceptance, select only the verified Observer
   read/write entrypoints through scoped managed configuration on the pilot hosts.
   Recheck the two stopped ordinary sessions and other healthy active workers.
   Retain the accepted older artifacts for rollback and commit scoped checkpoints.

No frontend implementation, provider policy change, ordinary provider restart,
hook installation, OpenCode work or public release belongs to this pass.
Only owned isolated sessions receive further native actions. Repository evidence
contains bounded metadata and reason codes, never native payloads or conversation
content. Run `./scripts/check` before each source/docs commit and finish namespace
cleanup before declaring acceptance complete.

The independent baseline additionally established that native stop after a
completed turn retires its worker while preserving `state=done`. Both that case
and active-turn stop (`state=stopped`) require inactive runtime reporting; a
completed outcome remains independent of whether its worker is running.
