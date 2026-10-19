# Codex catalog/detail tree metadata correction

This source correction separates exact thread identity from one observed
database-catalog/live-detail tree projection difference. It changes neither
the native wire nor Mesh, and does not select a service or qualify the whole
working-set producer.

## Observed behavior

A passive Starship check of Codex 0.163.0 found a loaded native subagent whose
database-only `thread/list` row reported its own ID as `sessionId`, while three
interleaved `thread/read(includeTurns=false)` results reported its live root.
Two complete catalog passes reproduced the self-root. The returned thread ID
and source parent metadata agreed, and the daemon incarnation stayed fixed.
The main-root and ordinary-thread controls matched across endpoints. Three
additional unloaded subagent controls also matched; this was not an exhaustive
subagent detail census or proof of an upstream implementation cause.

The [official app-server documentation](https://learn.chatgpt.com/docs/app-server)
distinguishes thread identity from current live session-tree root and describes
database-only listing as skipping metadata scan/repair. Current documentation
supports the distinction but is not source proof for the installed binary.

Previously the collector compared both `threadId` and `sessionId` as one identity
mapping. The independent native comparison tool made the same equality
assumption. A child catalog self-root therefore invalidated otherwise readable
runtime observations before the active/recent projection was involved.

## Narrow reconciliation rule

Matching thread and root IDs keep their existing behavior. A differing catalog
root is reconciled only when all of these hold:

- The validated thread identity matches exactly, including its owning scope.
- The catalog reports that thread's own ID as its root.
- Both catalog and detail explicitly classify a valid native subagent child.
- Current detail supplies a valid root and a supported live status: `idle`,
  `active`, or `systemError`. Existing work-state gates still apply independently.

The current detail root is retained as metadata. It is never inferred from cwd,
title or parent, replaced with the thread ID, or discarded to pass a comparison.
Unknown classification, malformed source/identity, non-self catalog root
disagreements, and mismatching unloaded or unsupported detail stay outside this
exception. The independent tool implements the rule without importing the
collector or its helper.

For loaded rows, catalog membership no longer overwrites the first validated
detail. The later detail read is compared with that first detail, so an actual
detail/detail tree change still invalidates the sample. If the later read fails,
the existing unavailable/partial handling applies without restoring the catalog
self-root or refreshing the original facts. A failed first detail may recover
from a successful later detail, while the original coverage error stays visible.
Saved identity still requires catalog membership and a successful detail read.

The writer's independent `session_tree_entry_unproved` guard is unchanged;
reconciliation must preserve a live child's non-self root. Namespace,
incarnation, wrong-thread, duplicate-inventory, source classification and work
authority checks remain in force.

## Validation and remaining gate

Focused collector, independent reference, qualifier and writer checks pass 90
methods on Python 3.14.8 and 3.11.17. New positive cases reproduce the previous
collector/reference rejection before the correction. Controls cover sibling
observations, runtime-only collection, saved-to-live races, failed first/later
reads, detail/detail conflict, wrong returned ID and malformed/unsupported data.

The full Python 3.14 repository check passes 1,151 tests with zero skips and 256
Markdown/link checks. A targeted passive read of the identified Starship child
passes both corrected rules while retaining its real non-self root, stable detail
bracket and exact thread ID. This is a native rule check, not installed-pair proof.

The earlier failed native qualification and installed package evidence retain
their original source bindings. A targeted native rule check cannot substitute
for an independent installed collector/Reader comparison on both hosts. That
qualification, package rebuild and any operational selection remain separate;
the [working-set checkpoint](working-set-producer-checkpoint.md) is not promoted
by this correction. No provider session action or metadata-repair scan is needed.
