# CLI/native evaluation repair execution

Date: 2026-10-05. Status: active regular goal loop, Observer only.
The user requested review/commit of the notification handoff, then resolution
of the [evaluation findings](evidence/2026-10-05-cli-native-evaluation/REPORT.md).
The reviewed [handoff](notification-handoff.md) is committed as `243bd89`.
Notification publication and frontend implementation have separate gates.

## Sequence and acceptance

| Checkpoint | Findings | Acceptance |
| --- | --- | --- |
| R0: records/preflight | E09 plus current host/artifact inventory | Preserve the unchanged a8 manifest, reconcile operator docs, inspect both hosts and establish disposable namespace ownership before any native launch. |
| R1: current Codex | E01, E02, E03, E06 | Independently prove exact current daemon read/state/clock capabilities and native action routes; separate artifact support from endpoint ownership. Preserve independently proved saved metadata through runtime failures, without a provider-spawning fallback. |
| R2: Claude semantics | E04, E05 | Held native background idle, tool wait, approval, completed readiness, child/helper identity and foreground cases. Map only independently proved facts; retain finite unsupported reasons where evidence is insufficient. |
| R3: context/topology | E07, E08 | Settle recorded versus recent working context with explicit provenance and schema compatibility. Diagnose the older TUI without guessing identity or adding an automatic standalone backend. Validate configured Git/root mappings separately. |
| R4: frozen producer | All findings | Tests/review/commits, exact source/wheel manifest, isolated package/native read/write/watch/recovery proofs, then installed CLI versus independent native references outside the checkout. Producer acceptance precedes any compatible scoped selection. |

Each finding receives a recorded fix or a justified bounded unsupported outcome.
An unsupported outcome is not evidence that the desired capability works.
General questions/outcomes, parked inference, attachment, push/replay, networking
and physical sleep/wake retain independent gates. One focused proof attempt may
establish a source limit; it does not justify cycling through legacy fallbacks.
Preserve notification event/correlation requirements while keeping sampled watch
distinct from lossless turn completion.

Ordinary reads may inspect existing native endpoints/files. Provider actions
run only in owned disposable configuration/store/workspace/endpoint namespaces,
with ordinary stores masked and exact process-birth cleanup. No coordinator
resume, ordinary provider restart, hook/config replacement, frontend edit,
physical suspend or release publication is part of this loop.

## Checkpoint log

- E09 closed: recovered the unchanged a8 manifest from prior acceptance scratch;
  the archived wheel hash and selected Snap package bytes, entrypoints, schemas
  and optional SDK profile pass `candidate-artifact verify`. Operator docs now
  identify a8 and its unsupported current-daemon limit. No rebuilt bytes or
  selected link change. Snap preflight reconfirms CLI `0.160.0`, daemon images
  `0.160.0`/`0.160.1`, and Claude `2.1.289`; native/Starship preflight continues.
- R1 source/native checkpoint: exact `0.160.1` read/work/approval/activity and
  `0.160.0` CLI direct Resume are proved on Snap; ordinary saved-store identity/
  clock evidence covers both hosts. Current source restores Codex discovery,
  separates image rejection from ownership errors, and retains independent
  saved metadata through live-source failure. Completion-only clocks remain
  gated per artifact/source. See the [report](evidence/2026-10-05-evaluation-repair/REPORT.md).
- R2 source/native checkpoint: held current Claude working/approval/completed
  readiness and child-storage cases are recorded. Ordinary conversations use
  explicit non-sidechain activity evidence for user classification. Blank
  background and native blocked-job meanings retain finite unsupported reasons;
  helper ancestry and foreground/questions remain independent gates.
- R3 context/topology checkpoint: recorded cwd semantics are explicit; disposable
  native Git/worktree/root mappings agree. The older Snap TUI remains outside
  accepted live binding, with discoverable history and an explicit limitation.
- R4 pending. Selected a8 still rejects current Codex; no source checkpoint
  by itself selects a package or accepts Starship actions/consumer behavior.

Record native evidence as bounded identity/state/time/count/version/reason
metadata only. Never retain authentication, prompts/responses, tool output,
terminal captures or raw native/hook payloads. Report source, packaged, native
and selected states separately, including remaining runnable acceptance steps.
