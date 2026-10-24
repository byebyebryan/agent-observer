# Observer and dashboard CPU reduction: execution plan

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Planning checkpoint: 2026-10-15. The [CPU investigation](../../evidence/2026-10-15-cpu/REPORT.md)
and source correction `62deb31` establish the starting point. This plan records
future delivery gates; it does not select artifacts, restart services or flash a
device. Start execution only from a fresh inventory of the affected repositories
and installed roles.

## Outcome and sequence

Deliver the measured Observer source corrections, adopt the already accepted
prepared read interface in RLCD, and measure complete application and fleet cost.
Then investigate the remaining dominant paths using the new baseline. Preserve
discovery, monitoring responsiveness, original evidence expiry and client policy.
There is no new absolute CPU or memory budget. Keep changes whose complete-path
benefit is repeatable and material relative to measurement noise and complexity;
report CPU seconds, percent of one core, steady/peak memory and remaining costs.

| Checkpoint | Owner | Result |
| --- | --- | --- |
| C0 | Observer/operations | Fresh role, source, device and rollback inventory |
| C1 | Observer | Immutable package of the existing CPU corrections |
| C2 | Observer/operations | Installed/native, cost, scoped role selection and rollback on both hosts |
| C3 | RLCD | Prepared-read application candidate against the frozen accepted producer |
| C4 | RLCD/Starship operations | Source sync, verified firmware flash and paired application/device acceptance |
| C5 | Both, with separate receipts | Complete cost comparison, publication and durable handoff |
| C6 | Mesh or Observer read component | Bounded residual-cost spikes, each with its own promotion decision |

The primary delivery batch is C0–C5. C6 is independently schedulable and does not
block that delivery. A producer defect found in C3/C4 reopens an Observer checkpoint;
freeze and validate the corrected producer before resuming client changes.

Delivery status, 2026-10-15: **C0–C5 accepted**. The
[producer/client ledger](../../evidence/2026-10-15-cpu-delivery/REPORT.md) records exact
selections, independent gates, Starship flash/rollback and measured cost; its
[completion audit](../../evidence/2026-10-15-cpu-delivery/completion-audit.json) maps the
requirements to evidence. The inputs and execution requirements below preserve
the original plan. C6 remains independently schedulable. The following
[a6/a22 owned-admission/selected-read checkpoint](../../evidence/2026-10-15-prepared-selection/REPORT.md)
accepts its independent producer source/package/native subset. It does not
select production roles or establish RLCD live CPU/device acceptance.

## Current inputs and authority

- Observer source on Snap is `62deb31`, one local commit beyond the previous
  published checkpoint. Its CPU changes pass 423 tests with Mesh a20 on Python
  3.11 and 3.14. They have synthetic cost and ordinary cached-source evidence,
  but no new immutable artifact or managed selection acceptance.
- Selected collectors remain core-only a3. Read CLI and Agent publication select
  Observer a4/Mesh a20. The writer and Tmux a7/profile-v1 factory retain independent
  selections. The [a20 role ledger](../../evidence/2026-10-14-mesh-a20/REPORT.md) supplies
  dated acceptance and rollback references.
- The [prepared read interface 1](../../prepared-agent-read-interface.md) and
  [RLCD handoff](rlcd-prepared-read-handoff.md) are accepted. API 4, snapshot/watch
  6, Service 4, explicit Agent profile v3 and SDK 1 stay the observation boundary.
- Starship's current RLCD source is `9cc159d`; its live bundle is
  `3a4b22b4556cb243`, built from `09dd027`, using Observer a1/Mesh a17. It already
  implements device wire 2 and failed-turn presentation. Snap's RLCD checkout is
  five commits behind its `origin/main` at this planning checkpoint.
- Mesh source checkouts differ from each other and from the accepted a20 source
  freeze. Resolve the selected wheel, schemas, lock and owner runtime from their
  accepted manifests; a clean checkout or branch named `main` is not proof of
  current selected SDK semantics. Keep Mesh a20 fixed for the first owner/client
  comparison. Do not adopt an older checkout or an unrelated private candidate.

The user's delivery direction is explicit: **sync RLCD work to Starship and flash
the hardware there**. The live Starship service binds
`/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_94:A9:90:F3:43:74-if00`.
Another serial device is present. The older Snap board identity is not the target.
Before any write, independently verify the selected board and its flash layout;
the service path alone is not a completed hardware identity check.

## C0 — refresh the baseline and preserve rollback

Capture clean/dirty Git state and exact source revisions in Observer, Mesh, RLCD
and the scoped managed selection files on each host. Preserve foreign commits
and edits. Reconcile Snap's older RLCD source with the accepted current base
before developing or syncing; do not copy a stale checkout over Starship.
Starship's Observer source checkout is also older than the installed a4 role
selection, so distinguish source synchronization from installed-byte verification.

Record selected entrypoints, wheel/bundle hashes, dependency origins, service
commands and PID births, shared-launcher factory bindings, source intervals and
current dashboard selection. Preserve a runnable old reader and publisher, the
current dashboard bundle and its matching wire-2 firmware, and exact scoped
selection/unit rollback files. Keep private backups outside Git.

Take an ordinary steady resource sample without profiling or tests. Account for
collector helpers, resident publishers, SSH-hosted publishers outside their unit
cgroups, reader processes and dashboard/serial workers separately. Record inventory
size, native view changes, proof/publication/read counts and bytes where measurable.
Report unobserved short-lived or SSH-server CPU; do not double-count overlapping
process and cgroup totals. Keep startup and steady windows distinct.

Exit: each comparison has an exact baseline and rollback target, and no historical
percentage is being treated as a current acceptance threshold.

## C1 — freeze and package the existing Observer correction

Keep this candidate scoped to the two reviewed changes: cheaper strict type
predicates and one bounded, scope-aware service wire admission. Standalone public
parsers and guards remain strict. Retain current CLI defaults and all native,
socket, stream ordering, concurrency and original-lease checks. New presentation
or Mesh reuse work belongs to C6, after the first delivery.

Allocate a new candidate package identity, build from a clean committed archive,
and compare every Python/schema payload against that archive. Archive the exact
wheel, manifest, Mesh a20 dependency bytes and producer lock. Verify isolated
imports, optional-Mesh separation, executable entrypoints and reported runtime
version. Reject mismatched or stale build output rather than overwriting an
accepted artifact identity.

Re-run relevant source gates if code changes; run installed current-profile and
network conformance against the new immutable prefix on both hosts. Test wire
framing/limits, forbidden fields, integer/boolean distinctions, scope, sequence,
gap/resync, expiry during silence, socket replacement and independent concurrent
watch/proof acquisitions. Source tests do not certify installed bytes.

Exit: one verified candidate usable by read/local-client and optional publisher
roles, with no wire migration. The collector remains independently selected a3.

## C2 — accept cost and select Observer roles

Before changing ordinary selections:

1. Compare the candidate public CLI/cache/Mesh results with independent daemon
   evidence on Snap and Starship using the
   [observation validation workflow](../../observation-validation-workflow.md).
   Compare exact identity, runtime/phase, activity/timing and source qualifications;
   retain accepted historical unknowns and sampling races explicitly.
2. Exercise candidate publisher snapshot, proof and watch through owned IPC and
   fixed SSH. Pair Agent checks with the currently selected Tmux factory because
   the shared launcher affects both domains. Include failure, cancellation,
   receipt regression and cleanup cases; never use another Observer read as the
   independent native reference.
3. Reproduce the controlled comparison at a small and a representative roster
   with fresh processes, unchanged SDK/cadence and output/authority oracles. Use
   serial ABBA/BAAB runs, separating instrumentation and allocation measurements
   from decision CPU. Extend coverage only for a new change, failure or unresolved
   concern; do not repeat the historical broad matrix mechanically.
4. Measure complete publisher plus reader behavior, including Bridge/carrier work
   omitted by the source-only publisher probe. Ordinary-host windows must include
   warm-up exclusion and cadence/shape counts. If baseline/candidate native work
   differs, label the result descriptive or reproduce it under controlled inputs.

Select roles in stages: candidate read/local-client entrypoint first, then the
Agent publisher factory/resident role, with Snap before Starship. At each stage
check current local and two-host cached/proof/watch behavior and owned cleanup.
Exercise reader-only rollback and an **actually running old publisher** with
old/new readers, then reselect the candidate. A cached old response alone is not
publisher rollback proof. Recheck paired Tmux cached/proof/watch controls.

Preserve collector a3, provider processes/configuration, the writer, Tmux native
ownership, 349 and RLCD's old independent application tuple. Shared-launcher and
chezmoi changes use scoped render/diff/selection checks and isolated publication
when ordinary managed checkouts contain foreign drift.

Exit: immutable installed/native/performance and operational receipts, with the
producer frozen and a handoff identifying exact accepted bytes. No dashboard
performance claim is made here.

## C3 — adopt prepared reads in the RLCD client

This is a new client checkpoint in `esp32-rlcd`, starting from its current accepted
source, after C2. Follow the [prepared adoption handoff](rlcd-prepared-read-handoff.md).
Replace Fleet's legacy guard/current/full reconstruction path with
`PreparedAgentWatch` while retaining the configured Reader, explicit AgentProfile,
host scope and existing subscription/serial supervisor.

Use `read.sessions` for positive current rows and `read.context` only for retained
source metadata. Recreate the helper on reconnect. A gap revokes context/current
rows until valid resync; it does not by itself require a new guard. Terminal
error/EOF, framing failure, cancellation or worker/output failure disconnect and
close the owned stream as required by the contract.
Do not export/reconstruct the full roster each device tick, inspect private guard
state, fall back silently or treat a constructible DTO as an authority token.

Preserve wire 2, failed-turn precedence, titles/collisions, source-sampled ages,
urgency/order, 11 visible rows, 32-row transport prefix, whole-roster membership,
uncertain identity retention, exclusion and overflow. Client policy stays in RLCD.
Keep nonce/request-send device expiry distinct from Mesh and native evidence.

Compare complete Fleet/projection results over unchanged/changed views, partial
coverage, complete omission, system/child/parked reclassification beyond the USB
prefix, expired history/runtime, heartbeat, gap/resync, host loss, reconnect and
clock failure. Include caller mutation, healthy siblings, counts, failed turns,
serial absence/busy/recovery and supervisor cleanup. Existing C admission and
motion checks remain the regression gate.

Measure the old application/old dependencies, old application/new dependencies,
and prepared application/new dependencies where compatible. This separates tuple
upgrade cost from the client change. Use actual one-second device-request cadence
and observed publication cadence, with whole application admission/projection,
serial and supervision included. Compare exact outputs before timing; report
steady/peak memory separately. An unhelpful candidate gets a measured outcome,
not an assumed 36% application saving from the earlier consumer benchmark.

Exit: accepted client source and immutable host bundle with verified dependency
origins, wire-2 firmware pairing and an application cost result. Keep the previous
wire-2 application/firmware pair available for C4 rollback.

## C4 — sync, flash and accept the real device on Starship

Sync the reviewed committed RLCD revision to Starship, preserving unrelated work,
and verify source, bundle, dependency and firmware hashes there. Build the selected
`projects/agent-dashboard` app with the repository's documented ESP-IDF toolchain.
The read-path change needs no device-wire or layout redesign; hardware flashing
is the user's requested delivery step using that accepted wire-2 app.

Stop only `rlcd-agent-dashboard.service` for the required exclusive serial window,
verify release, and verify the target's stable identity/MAC, chip, flash size and
partition map. Preserve a verified private backup, current application image,
bundle and scoped service/selection files. Preserve the other device and the
independent 349 service. If identity or serial ownership is unresolved, defer the
hardware step and retain the completed source/package work.

Flash the verified RLCD app on **Starship**, preserving the reviewed partition
layout and unrelated flash regions. Verify application readback, boot and a
bounded complete runtime capture. Restore any temporary port ACL exactly.
Deploy the verified host bundle through scoped managed configuration and restore
exactly one serial owner. No provider or Observer restart is implied by this
dashboard step.

Check real cached feed/ACK request, checksum and row agreement, source expiry,
silence/offline clearing, recovery and healthy sibling behavior. Preserve current
failed-turn/attention behavior. Device ACK proves device admission, not fresh
native state. Measure complete live application CPU separately after startup and
flash/capture work ends; record device render, heap and stack diagnostics.

Exercise rollback to the retained matching bundle/firmware, verify recovery, then
reselect the candidate. If firmware bytes are identical, record their equality
and exercise the application rollback without inventing a second firmware change.
Automated boot/readback/feed evidence does not establish visible panel readability;
keep that separately reported. A host reboot remains outside this pass.

Exit: Starship source/bundle/firmware agree, live feed is healthy, scoped rollback
passes, and unrelated service identities/configuration remain preserved.

## C5 — measure the result and close delivery

Take matched steady baseline/candidate whole-application windows on Starship and
endpoint-specific publisher/collector windows on both hosts. Use the same reader
count and cadence, count changed/unchanged publications and device requests, and
include one controlled additional-reader case for fan-out cost. Preserve baseline
and candidate bounds; do not compare a 60-second startup-inclusive profile with a
five-minute warmed service as a causal result. Ordinary source activity remains
uncontrolled; mismatched workloads retain a descriptive label and require a
controlled reproduction before attributing savings to a specific change.

Record CPU by owner, startup/steady and memory/capacity results, parity/expiry
checks, native coverage, all scoped rollout/rollback targets, and outstanding
limits. Commit producer and client work separately; publish reviewed source and
artifact metadata as separate receipts. Update the client handoff and roadmap
from the installed result. Keep working-tree state, artifacts, managed selection,
hosted publication and hardware acceptance distinct.

Exit: the normal Starship dashboard uses the accepted prepared client, both hosts
have independently accepted Observer roles, and a measured remaining-cost list
replaces expectations. Further optimization starts from this baseline.

## C6 — bounded residual-cost studies

Two opportunities remain, with separate ownership and no assumed promotion:

- **Mesh native-body reuse.** Reproduce full-roster composition and repeated
  admission on unchanged native bodies at actual proof cadence. Prototype reuse
  only for exact privately owned immutable bytes bound to the current profile,
  publisher/incarnation and receipt context. Independently check every new proof,
  nonce, envelope, ordering, clock, ownership and original lease. Revision, title,
  PID or digest equality alone cannot grant current authority. Mutation, renewed
  receipts, same-revision body changes, rollback, partial hosts, gap/resync and
  reconnect must retain full rejection/revocation behavior. Accept only after
  whole-pipeline CPU, allocation/capacity, Agent and selected Tmux conformance.
- **Observer presentation/header work.** Keep arbitrary-input public formatters
  strict. Spike a private prepared CLI formatting path with exact ordering/filter/
  age/output and caller-ownership parity, avoiding repeated snapshot validation
  after successful admission. The current helper exports all rows once to obtain
  its header; an owned header-only SDK seam would need explicit Mesh review and
  capability acceptance. Do not read SDK private storage or copy an untrusted
  caller header as a substitute for admitted owned state. A CLI-only saving is
  not a dashboard saving.

Begin each with a narrow realistic unchanged/changed fixture and a measured
hypothesis. Stop a non-material prototype after that screen. A successful spike
gets its own artifact/operational plan; C6 does not reopen C0–C5 automatically or
authorize a networking rewrite, transport switch, delta contract, shared reader
daemon, slower monitoring, discovery truncation, new provider, alert or action.
