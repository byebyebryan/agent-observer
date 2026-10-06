# Claude stopped runtime acceptance

Date: 2026-10-05. Status: independent source and a11 packaged/native G2 accepted,
followed by scoped two-host pilot selection. This follows the
[execution plan](../../stopped-runtime-execution.md) and
[CLI/native validation workflow](../../observation-validation-workflow.md).
Observer producer acceptance precedes selection; frontend work is separate.

## Problem and native evidence

The user stopped `recap-2026-report` and `recap-2026-f2` through explicit native
Claude stop actions. Their retained jobs report stopped/idle and their workers
are absent, but selected a9 and candidate a10 left runtime unknown. Saved
history alone and disappearance of one process cannot establish inactivity.

The isolated [baseline](native-baseline.json) and final [a11 proof](native-a11.json)
use the installed Claude 2.1.289 image, SHA-256
`a186b99e4a9c88366cd49df2f7dad56c61fc306ef0140b19ee64b7c42a8d1348`.
Private user/mount/PID namespaces mask ordinary provider homes and provide
private temporary/runtime directories. Native job metadata and registry/process
births supply the independent reference; Observer never supplies expected facts.
Public installed read/write clients run outside the checkout, and owned PTYs
exercise native entry. Terminal content is drained and discarded.

Native stop after a completed turn exits its worker while retaining `done`.
Stop during a working turn instead retains `stopped`. Both cases with idle job
tempo and no live bound worker require parked runtime. The initial fixture
expected every stop to produce `stopped`; direct native inspection corrected
that expectation before accepting either case. A10 reproduces unknown in both;
a11 reports parked. Three held completed-stop samples preserve conversation age.
Viewer detach preserves its worker; subsequent native attach restarts the same
UUID with a different worker birth and returns to running. First-party saved
Resume returns an explicit new UUID, whose native TTY entry is accepted, while
the requested original remains parked.

## Accepted predicate and guards

Only the exact accepted current Claude artifact enables `parked_runtime`.
A unique exact-UUID retained `done` or `stopped` job must have idle tempo, valid
nonfuture terminal metadata and no pending/invalid in-flight counters. Complete
bounded job and registry inventories and a supported PID domain are required.
Every matching registry worker must be positively absent; live, unsupported or
ambiguous contexts prevent parked. Directory identities, inventory membership,
registry identities, candidate job state and worker absence are rechecked before
projection. Partial, capped, unavailable or changed evidence remains unknown.

Runtime absence is sampled evidence. Native terminal and conversation clocks
are not refreshed by that sample. Parked rows have phase unknown with
`runtime_parked`, because no running agent turn needs a work phase; completed
outcome remains a separate fact. Live presence overrides a terminal job.
The 212 source tests include duplicate, stale/resumed worker, changing UUID/job,
membership-race, invalid clock/counter and incomplete-inventory cases. Required
checks and scoped Ruff pass. No wire schema changes are needed.

## Immutable installed acceptance

The [manifest](../../../artifacts/observer-0.2.0a11.json) freezes `0.2.0a11`,
source `06af32dc9f28aa5d356d6da6c0235ccc1056dac2`, wheel SHA-256
`999d45171adfc4c4e62fe57b417614c0814de2a556693a6d23bb97b45a0a8b65`.
Both hosts install the same wheel at
`~/.local/share/agent-observer/0.2.0a11-999d45171adfc4c4`. Snap uses source-only
Claude SDK 0.2.163; Starship is core-only. Wheel/source bytes, installed bytes,
entrypoint interpreters, package versions and read/watch/write schemas 2/2/1
are verified independently of selection; see [package acceptance](package-acceptance.json).

Two ordinary [evaluation rounds](evaluations.json) compare the installed CLI
against independent stdlib native reads, with no provider actions. Snap has
51 Codex and 30 Claude rows, including six loaded Codex threads and three live
Claude workers. Starship has 96 Codex rows, including eight loaded threads.
All proved membership, runtime, activity, identity and metadata comparisons
match; default lists exclude three and six known Codex children respectively.
One Snap Codex child remains `systemError`, with unknown phase and a
`native_reference_unproved` finding rather than an invented phase. Saved history
and older TUI/helper coverage retain their existing finite limits.

The two [ordinary target rows](ordinary-targets.json) independently match stable
stopped/idle retained jobs and empty matching registries. Both report parked,
worker absent and unchanged conversation activity; the other three ordinary
Claude workers remain running. Snap's and Starship's public watch streams pass
four samples per reader with two readers using the frozen Plus environment's
Observer a3 validator, outside the checkout:
[Snap](watch-snap-a3.json), [Starship](watch-starship-a3.json).
This proves public compatibility, not graphical consumer acceptance.

## Scoped selection

After producer acceptance commit `a0e8282`, managed source commit `66fbdd3`
updates only the two Observer selectors, the exact pilot tuple and its operations
note. Starship's prior uncommitted migration work is preserved: the three exact
selector/tuple inputs receive the scoped patch, and its older operations history
receives the new checkpoint paragraph without replacement or a broad Git sync.
The candidate gate independently verifies producer, unchanged Plus and its
frozen a3 reader bytes/schemas before selection on both hosts.

Snap's full chezmoi status/diff still hits the pre-existing SSH Plus external
archive checksum mismatch; Starship's scoped diff is clean and its unrelated
Claude drift is preserved. A private source containing only the two canonical
Observer templates and machine mapping provides scoped diff, template rendering,
dry run and apply without evaluating externals or hooks. Only Observer's read
and write symlinks change; other-host selectors and consumer state stay intact.
Both normal commands now select a11, independently rechecked through the public
CLI and native reference. The recap rows remain parked, worker absent and age
unchanged; three ordinary Claude workers remain running. The
[selection receipt](selection.json) records exact targets and source state.

Rollback snapshots are armed at
`~/.local/share/agent-observer/rollback-20261005-stopped-live-HOST`; the established
managed rollback helper can restore the previous selectors/tuple only after its
current-source/link guards pass. Both previous and new artifacts remain installed.
No frontend implementation, cache migration, provider policy change, public push
or ordinary session restart accompanies this selection.

## Cleanup and remaining limits

The owned namespace is stopped and borrowed credentials/history are removed;
the [cleanup receipt](cleanup.json) and ordinary settings guards pass. Ordinary
provider configuration, hooks, native daemons and sessions receive no actions
from this checkpoint. Existing older artifacts remain installed for rollback.

Saved-only sessions without a terminal native job remain runtime unknown.
Failed jobs and unsupported/ambiguous worker contexts have no new parked proof.
Codex saved-only runtime absence remains unproved. Exhaustive legacy discovery,
current viewer binding, foreground Claude questions, blank background readiness,
native push/replay, optional networking, graphical behavior and physical
sleep/wake remain independent gates. No frontend implementation or public
release is included.
