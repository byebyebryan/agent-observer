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
