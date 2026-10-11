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

## Immutable package

[Observer a17](../../../artifacts/observer-0.5.0a17.json) comes from source
`3650e5e6c8bf8d9715801e8e9817860d22d8fefc`, wheel SHA-256
`06eebb2d87a32829ed1c3b658a2a8e13426bf38bd8de5c58336890e6cd5ef14d`.
A checkout build retained an obsolete file from its build cache; that uninstalled
wheel was discarded. The accepted wheel was rebuilt from a clean Git archive.
Its complete package file set and bytes equal the committed source, including
unchanged public schemas. The isolated reader prefixes on both hosts include
released Mesh a11 and private immutable artifact archives.

[Package receipts](packages.json) verify exact installed Observer/Mesh bytes,
SDK 1, the Agent descriptor, entry points, `pip check` and zero provider or
collector imports/invocations during artifact verification. Snap independently
installs the existing Claude-history Python SDK profile without a bundled native
executable; Starship uses core. All 466 checks pass with the pinned Mesh wheel on
Python 3.14 with no skips. Python 3.11 passes with only two unrelated sealed-memfd
skips. A frozen owner delivery view also passes the selected a10 reference;
native reconstruction and effective counts agree at original time and component
expiry: 5 combined rows, 2 Claude rows, then zero. Independent owner assertions
specify these counts.

## Native and mixed-artifact delivery

[Bounded comparisons](native-comparisons.json) bracket installed direct and
local cached reads with independent existing Codex daemon queries and Snap Claude
interactive/history evidence. There are two rounds per path and host. No
providers or normal collectors are restarted. Exact identity/store scope,
membership, running/parked classification, work phase and proved activity clocks
agree. Snap observes 91 Codex rows (3 running) and 37 Claude rows (3 running);
Starship observes 384 Codex rows (6 running). Native raw child rows are preserved;
normal lists hide 38 Snap and 254 Starship children. Age, ordering and full identity
read checks pass.

The oracle reports one older non-conversation Claude history's cwd differently:
UUID `e0cba9dd-b642-4730-af4b-beb3b7e9c16c` is parked with unknown kind and absent
conversation activity; Observer retains unknown cwd instead of promoting setup
metadata. This UUID's narrower historical evidence is already recorded in the
preceding collection checkpoint. Two Starship creation timestamps change between
bracketing native samples and are reported as sampling races, not exact matches.
Legacy unknown kinds/activity, old unsupported Claude histories and the accepted
interactive-registration coverage assumption remain explicit.

Fleet snapshot reads deliver all 512 raw rows with complete transport and an
after-nonce proof for the SSH host. Replacement watch passes in both directions:
Snap receives 30 frames (27 complete), Starship 30 (28 complete), over roughly
18 seconds each. The separate standalone local watches receive 19/17 frames.
An explicit `local_host` bypasses catalog scope in SDK 1; fleet proofs omit it
and assert both host deliveries. Every ready owner reconstructs as valid Service 2; current
selection leaves caller frames unchanged. Streams close with zero active owned
connections and disconnect revokes positives. This is current ordinary-host SSH
delivery, separately from synthetic owner fault tests. Delivery completeness
does not upgrade Claude's partial native coverage.

[Delivery receipts](delivery.json) also record a guarded termination of one owned
SSH subprocess, not a resident bridge or provider. The Reader reports unavailable
remote delivery without granting its rows through the healthy local sibling,
reconnects and fully resynchronizes, then closes all owned connections. The
successful procedure leaves Reader in sole charge of client cleanup. An earlier
probe that concurrently called `Client.close` while Reader owned it recovered but
triggered a Python 3.14 asyncio subprocess callback warning; it is not the accepted
transport-failure procedure. No such warning occurs in the owned SSH-exit proof.

## Matched ordinary-host cost

[Cost receipts](cost.json) use 30-second windows after 5-second warm-up, with
local one, fleet one and fleet two readers, first selected a16/a10 then candidate
a17/a11. Each tree includes its owned local SSH child; remote SSH server costs
are excluded. These are short, active-host samples, not idle or long-soak claims.

Snap reader CPU is 4.7% of one core locally, 12.9% for one fleet reader and
9.4–10.3% each with two fleet readers; baseline is 5.2%, 12.1% and 8.8–8.9%.
Starship is 4.7%, 9.8% and 7.7% each versus 3.9%, 9.3% and 6.6%.
The SDK path adds roughly 0.5–1.5 core percentage points in fleet samples.
Mean fleet-tree PSS remains about 30–31 MiB, local PSS 22–27 MiB; process/FD
counts stay bounded and the owned connection checks retire cleanly. There is no
new collection loop or large memory increase. This accepts the migration's
bounded cost, not a low-CPU promise for every reader on a large busy roster.

Three pull samples per path give candidate local latency 371–380 ms on Snap and
597–620 ms on Starship; fleet 1232–1298 ms and 892–920 ms. Baseline local is
355–423/548–568 ms and fleet 1140–1192/844–860 ms. SDK validation adds a small
measured cost in exchange for its independent native/receipt checks. Further
generic reader validation/publication optimization belongs to Mesh's separate
maintenance track and must preserve admission and original source leases.

## Operational selection and handoff

[Selection receipts](selection.json) accept a17/a11 readers serially on Snap and
Starship. Each host's normal CLI reads the complete two-host 512-row view after
selection, after rollback to a16, and after reselection to a17. Only the managed
Agent reader link changes. Candidate rendering, both immutable artifact gates,
exact captured controls and the selected bridge's UID/arguments/interpreter/birth
guard precede mutation. Rollback restores only the captured reader link; neither
unit is stopped. The successful [procedure](reader-selection-proof.py) retains
these explicit inputs and guards.

Collector a15 and bridge a16/a10 retain their exact process incarnations. The
writer, workspace/unit controls, provider settings and shared global Mesh CLI
remain byte-identical. Starship's pre-existing Kitty/Niri source edits are
unchanged. The canonical two-file selection is committed as dotfiles `50685bc`
and reconciled on Starship without writing unrelated worktree files. Private
captured rollback inputs remain in each host's
`~/.local/state/agent-observer-sdk-v1-20261011-<host>/baseline.json`.

The [current Mesh guide](../../mesh-read-client.md) and
[API 2 client handoff](../../api-v2-client-handoff.md) describe the selected tuple
and explicit-profile obligations. Ordinary provider workflows/settings and all
public wire versions are preserved; no session restart was needed. This pass is
committed locally. Hosted CI and an a17 GitHub release have not been published
or accepted yet. Local immutable archives on both hosts are the artifact authority.

M0–M5 are complete within the stated observation, short-cost and native bounds.
Publisher extraction, Mesh generic maintenance, event products and downstream
consumer/GUI migration remain independently scheduled work.
