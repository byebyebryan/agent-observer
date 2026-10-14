# Native title-helper classification correction

Observed 2026-10-13 PDT / 2026-10-14 UTC. This independent producer source
checkpoint starts from `e3d87bb`, preserving the prepared-read implementation.
The initial source proof precedes the packaged collector acceptance below;
RLCD consumer acceptance belongs to its independent device pass.

## Trigger and cause

The RLCD showed extra codex-plus rows on Starship and Snap. Fresh owning-daemon
metadata reads on both hosts found a distinct unnamed, idle, ephemeral helper
with `threadSource=thread_title` and cwd pointing at codex-plus. The ordinary
Snap codex-plus conversation had its own persistent user identity.

Codex 0.162.1's [title-generation implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/tui/src/app/thread_title.rs)
creates a temporary thread with `ThreadSource::Feature("thread_title")`.
Observer recognized only literal `system`, leaving these native helpers unknown.
The RLCD retained their positive loaded/idle facts and used cwd as the fallback
label. The duplicate-looking labels therefore represented distinct native
identities rather than a host alias or row-identity collision.

## Correction and checks

- Explicitly map the known `thread_title` native helper tag to existing
  `kind=system`; retain literal `system` and all wire/profile versions.
- Preserve child precedence, malformed/unproved classifications and unknown
  feature tags. Ephemeral user threads remain user threads.
- All 411 source tests pass, including the native-tag/ephemeral matrix,
  malformed feature values, child precedence and retained-row reclassification.
- Passive ordinary native comparison reads six loaded Starship rows and five
  loaded Snap rows from the unchanged owning Codex 0.162.1 daemons. Exactly one
  title helper per host changes from installed `unknown` to candidate `system`.
  Other normalized metadata remains equal, excluding independently sampled
  BOOTTIME read timestamps. No provider action or model turn is invoked.

## Delivery boundary

The proof compares the currently installed a2 package with the candidate metadata
module in an isolated checkout. It is source/native classification acceptance,
not a packaged producer or managed service rollout. Installed artifacts remain
immutable, and the ongoing prepared-read handoff on Snap remains untouched.
Package the correction and accept/select its collector separately; the existing
RLCD system exclusion then removes the helper identities from rows and counts.
No dashboard label blacklist, project deduplication, thread archive or firmware
flash is needed for this correction.

## Packaged producer and managed acceptance

The correction is now independently installed and selected for collection on
Snap and Starship as [Observer 0.7.0a3](../../../artifacts/observer-0.7.0a3.json).
Its wheel is `b2df912102505295e57ffc0d1685fa393815330e3a9121aa6471411306e19f70`,
built from source freeze `2356323d032fbf06169bdc342d8a04590c16a411` in a clean
Git archive, not the development build cache. Both hosts retain wheel, manifest
and verifier bytes under
`~/.local/share/agent-observer/0.7.0a3-b2df912102505295-title-helper/artifact/`.
The collector environment is core-only; API 4/read 6/Service 4 stay unchanged.

Exact installed-byte, entrypoint and schema verification passes on both hosts.
The installed classification/metadata/service-contract subset passes 30 tests
with one expected optional-Mesh skip. The full source gate passes 411 tests
using the independently accepted a2/a18 environment, without skips.

The independent stdlib native evaluator recognizes the source-confirmed helper
tag. Direct packaged comparisons report zero mismatches across 385 Starship
and 98 Snap identities. These later inventories have five/four running rows;
the two earlier native title helpers have already disappeared from their owning
daemons. Their absence in this later sample is not a claim about filtering.
The earlier passive helper comparisons and installed fixtures establish the tag
correction without creating a provider thread or invoking a model.

After selection, cached Service 4/native comparisons agree on identity, kind,
runtime, phase, activity and outcome. Snap has zero reported differences.
Starship's currently active dashboard conversation has one `lastUpdated`
difference: cached `1791966767000` versus native `1791966779000`. The cache
preserves its original runtime receipt and sampled BOOTTIME; the later native
update is a twelve-second sampling lag, not refreshed timing authority. This
receipt does not claim simultaneous cached/native timing equality.

Both unchanged a1/a17 publisher environments pass the installed cached Agent v3
IPC and owned localhost-SSH gate against the selected collector. On each host,
scoped candidate render/dry-run, six-target selection, rollback to the prior
collector, and reselection pass. The read CLI remains a2/a18, publishers remain
a1/a17, and protected reader/writer/launcher/configuration bytes plus publisher,
Tmux, RLCD and 349 service identities/restart counts remain equal. Native endpoint
selection and Codex configuration remain equal; no provider action is performed.

Operator receipts are summarized in [acceptance](acceptance.json). Native metadata
and operation snapshots remain private local evidence; no raw provider payload
is committed. Hosted wheels remain a separate distribution checkpoint. This
accepts the producer correction before the independent RLCD failure/wire pass.

Source through `e399dd0` is published and its [hosted checks](https://github.com/byebyebryan/agent-observer/actions/runs/38536245587)
pass. Scoped dotfiles publication `7afbe06` selects only the collector correction,
preserving the prepared reader/publisher fields. Both ordinary source checkouts
retain independent foreign commits; owned collector fields are reconciled without
resetting those trees or publishing unrelated changes.
