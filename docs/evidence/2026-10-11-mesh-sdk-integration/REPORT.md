# Mesh SDK v1 integration evidence

Execution date: 2026-10-11. This report advances the reviewed M0–M5 plan without
changing API 2, snapshot/watch 4, Service 2 or Mesh Read/Delivery 1. Acceptance is
reported per gate; source success is not installed or native acceptance.

## Source and owned delivery

The explicit Agent profile uses released Mesh `0.1.0a11`, wheel SHA-256
`9d3c2446b2391ab2271236804b4dfc03dfa5d29f2766d72b3d12086848b36359`.
The isolated Python 3.11 environment contains that wheel and no Tmux Observer.
The core remains optional-Mesh-free. CI provisions a checksummed chezmoi binary
and runs separate core and pinned-Mesh jobs; a local clean-tool-path check passes.
Hosted CI remains pending publication and an actual result.

Owner tests specify Codex-only, Claude-only and combined native frames,
distinct provider-store namespaces, empty/warming snapshots, exact identity,
clock/receipt reconstruction and nonmutation. Multiple configurations are tested
as separate native views, respecting Service 2's one source per provider.
Callbacks run with reference/collector/action imports blocked.

Owned IPC tests cover positive raw pull, human list/watch, explicit-profile
propagation, independent provider expiry, original receipts, disconnection,
cancellation and closed reader/publisher resources. Aggregate admission rejects
duplicate rows, incompatible native version, wrong native host, missing receipt
and extended receipt. An IPC endpoint classified as remote supplies a nonce proof;
forging its lease cannot borrow the healthy local sibling's receipts. This last
test is synthetic remote proof, not SSH transport acceptance.

The released SDK's ten independent boundary tests also pass outside the checkout
with reference-native imports blocked. They supplement owner tests for checked
hello/binding, nonce/digest/clock/receipt faults, packaged frozen views, empty
requirements, deadlines, repeated cancellation, gap/restart/resync and catalog
replacement. These are Mesh-owned tests, not copied into Observer or made a
required sibling-checkout dependency.

New artifact admission requires the reviewed profile and frozen lock checksum,
an unambiguous canonical manifest, exact wheel hash, SDK 1 descriptor and installed
wheel bytes. Version is diagnostic, not an admission allowlist. The archived
verifiers for prior artifacts remain unchanged. The operations gate independently
verifies reader and bridge artifacts while requiring the same delivery contract;
it no longer requires identical package versions.

## Following gates

Immutable a17 installation, native comparisons, real SSH delivery, matched cost
measurements and scoped reader selection remain pending. Ordinary providers,
collector a15, writer 0.4.0a16, separate a16/a10 bridge and shared global Mesh CLI
have not been changed by the source gate.
