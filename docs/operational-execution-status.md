# Operational acceptance execution status

Date: 2026-10-04. Regular goal loop authorized with scoped checkpoint commits and
the conditional two-host pilot cutover in the [operational plan](overnight-operational-acceptance-plan.md).
The primary works directly. Ordinary providers/coordinator remain available;
public push/publication and desktop/suspend/reopen acceptance remain separate.

## O0 baseline

Plan checkpoint `c553267`. Observer producer source/wheel remains `222c5bf`,
`0.2.0a3`, SHA-256 `6aa793e6a0ba5ae37403f73999ea6e6d56bc8c21e5e4c7a10ac52cb946a45a3f`.
Plus source/wheel remains `90e5b4f`, `0.14.0a1`, SHA-256
`8ba19a0eba87944aec2848542fb3ddcb91f3ccc33790ba42565928e18daa497b`.
Native provider versions/hashes match the accepted artifacts. Actual Host Mesh
authority supplies Snap/Starship and the configured `starship` SSH route.
Old pilot links are still selected; no global write entry exists. No display
environment is available to the coordinator.

This is the O0 baseline. O4 below records the completed selection.

## O1 tooling

The accepted producer code/contract is unchanged. Repository-owned
`scripts/candidate-artifact` installs/verifies an exact local wheel with no
provider invocation or global link selection. Verification compares installed
wheel files byte-for-byte, entry interpreter ownership, all public schema versions
and the optional source-built SDK profile with no bundled executable. A failed
new install removes only its owned prefix; an existing prefix is verified and
never overwritten. `artifacts/observer-0.2.0a3.json` captures exact provenance.

`scripts/check-read-watch` measures bounded installed public watch streams under
isolated interpreters. It validates schemas, scoped snapshots, stream/revision
continuity and records aggregate timing/RSS/FD/coverage only. The tool invokes
no provider actions and never persists snapshots or conversation metadata.
Same-value native phase-clock updates are diagnostic counts, not presumed bugs:
ordinary activity may legitimately change evidence during a measurement.

Fresh core installation passes on both hosts; fresh source-built optional SDK
installation passes on Snap. Installed verification also accepts the existing
candidate prefixes with their distinct profiles. A shebang compatibility defect
in the new installer was corrected: owned `python`/`python3` venv aliases resolve
to the same interpreter and are both valid. No producer artifact change occurred.

157 source tests and 33 Markdown checks pass, with scoped Ruff/format passing.
Native ordinary single/concurrent watch reads each took about 20 seconds for
10 samples at a requested two-second interval. Snap's concurrent readers stayed
below 27 MiB RSS and five FDs; Starship stayed below 27 MiB and four FDs. These
are bounded windows including interpreter startup, not a long-duration stability
claim. Schema/revision checks pass and zero same-value native phase-clock updates
were observed. Partial saved-source coverage remains independent of aggregate
current health.

Evidence: [Snap fresh core](evidence/2026-10-04-operational/fresh-core-snap.json),
[Snap fresh SDK](evidence/2026-10-04-operational/fresh-claude-snap.json),
[Starship fresh core](evidence/2026-10-04-operational/fresh-core-starship.json),
[single read](evidence/2026-10-04-operational/read-single-snap.json),
[Snap concurrent](evidence/2026-10-04-operational/read-concurrent-snap.json) and
[Starship concurrent](evidence/2026-10-04-operational/read-concurrent-starship.json).
Operational tools/install/read checks are accepted; owned native gap/restart
recovery remains pending before full O1 closure and consumer entry acceptance.
Pilot selection has not started. Observer source/wheel remains frozen.

## Independent native recovery closure

`scripts/check-native-recovery` ran with the installed public read/write CLI in
private user/PID/mount namespaces on both hosts. It has no frontend imports.
The exact owned daemon executable path/PID/start ticks were checked before
stopping it. Offline observation stayed unavailable without starting a daemon;
old handoff execution rejected before native entry. A separate explicit native
entry established a fresh runtime, retained the original storage-scoped reference
and accepted exact Resume. Actual watch emitted gap/resync and retained missing
rows unknown through incomplete coverage. [Snap](evidence/2026-10-04-operational/native-recovery-snap.json)
and [Starship](evidence/2026-10-04-operational/native-recovery-starship.json) record
bounded results; provider/native output was never persisted.

The initial proof incorrectly assumed Codex supplied a native phase timestamp.
The accepted contract correctly labels each fresh RPC state read `clock=sample`;
that timestamp can advance while the phase stays waiting. The harness now checks
the actual clock kind and reports sampled evidence explicitly. No producer
defect or contract change was required. Claude native phase-clock stability is
checked separately by its own source-specific predicate.

O1 is accepted independently. Upcoming O2 may consume this unchanged artifact;
the old selected pilot remains intact. Private fixture namespaces are retained
only for owned consumer proofs and will be removed in final cleanup.

## O2 separate consumer acceptance

The unchanged installed Plus wheel passed actual installed Host Mesh/Tmux CLIs,
real configured SSH transport and native deferred entry. Owned namespace wrappers
and a PTY/user-scope adapter supplied isolation and terminal presentation; no
Tmux responses/provider results were fabricated. Codex New/exact Resume passed
on Snap and Starship; Claude New/live/saved Resume passed on Snap. Every case
required one public prepare/execute pair. Saved Resume retained private history
after stopping the owned namespace and clearing only its runtime registries.
Claude native phase evidence retained its clock. A real read-only SSH disconnect
and reconnect preserved the remote namespace; native uncertainty after a possible
write remains controlled coverage. Consumer evidence/tooling is committed in
Plus `a2dcf65`, with 312 tests and its full source gate passing. Bootstrap/CI
requires supplied exact Observer wheel bytes; hosted CI/publication is pending.

This closes the real Tmux/SSH path, not graphical placement/focus, ordinary trust
dialogs or current-client binding. Existing controlled expired-plan/failure/no
redispatch cases remain labeled separately. No Observer producer code changed.

## O3 managed preparation and O4 provisional selection

Chezmoi `ac0f420` records the exact unpublished pilot manifest, candidate/live
gates, five coordinated selectors, host exclusion and guarded rollback tooling.
Targeted render checks pass for Snap/Starship and preserved Carbon/unknown-host
branches. New-tool lint, legacy gate self-tests, strict identity cases and a
rollback round trip/replaced-selector rejection pass. The broad chezmoi source
gate remains blocked by an unrelated external SSH Plus archive checksum mismatch.
Its expected `0ecbd01e…` and supplied `37a8202b…` hashes are not changed here.

Even scoped chezmoi apply evaluates that unrelated archive. The reviewed helper
uses an owned source projection containing only the five byte-identical managed
templates and machine map. It invokes chezmoi for those exact links with no
externals, removal list or deployment scripts. Both reviewed dry runs and applies
passed. The selected tuple is now Observer `0.2.0a3-6aa793e6a0ba5ae3` and Plus
`0.14.0a1-8ba19a0eba87944a` on **Snap and Starship**. All five links, including
`~/.local/bin/agent-observer-write` and the separately pinned Rofi script link,
match their immutable prefixes. Old prefixes remain installed.

Selected-live gates pass on both hosts through normal configured routes with
private cache/UI state: cache v7, full store-scoped identities, zero provider-stage
errors and headless peer/page/action callbacks. Snap's gate additionally covered
actual generic Tmux lifecycle on both advertised hosts with exact-reference
cleanup and SSH usage-history preservation. The first live check exposed a gate
resolver assumption about the released extension directory; the explicit pilot
mode now validates the manifest's exact wheel prefix. No package defect or
artifact change was required.

Evidence: [Snap candidate](evidence/2026-10-04-operational/pilot-candidate-snap.json),
[Starship candidate](evidence/2026-10-04-operational/pilot-candidate-starship.json),
[managed preflight](evidence/2026-10-04-operational/managed-preflight.json),
[Snap live](evidence/2026-10-04-operational/pilot-live-snap.json) and
[Starship live](evidence/2026-10-04-operational/pilot-live-starship.json).
Selected [Snap](evidence/2026-10-04-operational/selected-cli-launcher-snap.json)
and [Starship](evidence/2026-10-04-operational/selected-cli-launcher-starship.json)
read/write schema and launcher checks also pass. The launch-owned Rofi adapter
verifies the actual initial frame, native Rofi arguments and matching sibling CLI;
it supplies no graphical appearance/focus evidence.

## O5 cleanup, rollback and remaining gates

Both exact owned namespace incarnations stopped and both private provider stores,
borrowed auth copies, terminal ledgers and private native histories were removed.
No ordinary saved provider sessions were created or deleted. Ordinary provider
auth/config/settings/Claude preference hashes match each host's pre-run baseline.
The [cleanup report](evidence/2026-10-04-operational/native-cleanup.json) and
preservation checks for [Snap](evidence/2026-10-04-operational/ordinary-preservation-snap.json)
and [Starship](evidence/2026-10-04-operational/ordinary-preservation-starship.json)
record only counts/booleans and paths, never provider values.
The coordinator remains available and was never restarted. Starship's existing
uncommitted managed migration work is preserved; only scoped selector/gate files
were copied from the committed Snap managed checkpoint. Nothing was pushed.

Private rollback snapshots are armed at
`~/.local/share/agent-observer/rollback-20261004-snap` and
`~/.local/share/agent-observer/rollback-20261004-starship` on their respective hosts.
The managed `docs/agent-observer-pilot-operations.md` explains the rollback command
and guards. Default rollback restores selectors/managed sources; optional consumer
state restoration rejects later user changes. It never restores provider stores,
auth/settings or stops native work. Tests used private consumer state, so ordinary
cache/UI state remains available for its normal v7 migration on next launch.

Morning checks remain: open the normal picker, inspect names/pages/order, use
New/Resume locally and across hosts, and verify terminal placement/focus and
native trust handling. Physical suspend and deliberate coordinator reopen remain
manual. Public push/release, supplied hosted-CI artifact input and the unrelated
external archive maintenance remain open. Monitoring expansion stays an independent
Observer batch: last conversation activity, parked/offline predicates, broader
input/questions, foreground Claude readiness, native events and optional networking.
