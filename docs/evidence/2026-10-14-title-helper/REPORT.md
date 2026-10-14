# Native title-helper classification correction

Observed 2026-10-13 PDT / 2026-10-14 UTC. This independent producer source
checkpoint starts from `e3d87bb`, preserving the prepared-read implementation.
It does not select a new installed artifact or change the RLCD consumer.

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
