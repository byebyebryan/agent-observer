# Claude native session title follow-up

Date: 2026-10-03. The user confirmed that Agent Plus displayed
`Claude <UUID>` instead of the native Claude name on Snap.

## Cause and selected metadata

The previous Observer collector always generated a UUID-based Claude title.
This deliberately excluded job names with unproved/task-derived provenance,
but also discarded native user-assigned registry names.

The installed Claude Code 2.1.287 executable was rechecked against SHA-256
`3920489a5109cff5786a1a392c25277408ff22bc796d5edb9c16a60e5a1718f0`.
Static inspection established the native registry writer's `nameSource`
classification and the job writer's user/automatic name distinction. Both
ordinary interactive registry records on Snap have a nonempty name explicitly
marked `user`. Names and raw metadata were inspected in memory only.

Observer now projects a sanitized, bounded name only when `nameSource` is
`user`. A registry name takes precedence over a job name. A job name supplies
the title only for the exact session/job link without a conflicting identity.
Absent, automatic, derived and unproved sources retain the native-ID fallback.
No transcript, prompt preview, job intent/detail, terminal label or cwd supplies
a session title or an identity join.

Title-only updates do not invalidate stable identity/work observations. The
second bounded file read refreshes the title while preserving the work clock.
The public snapshot shape is unchanged; Agent Plus already uses its title field.

## Installation and validation

Observer `0.1.0a4` is installed on Snap and Starship from wheel SHA-256
`d5e65f10eb1bc61e288c5970d822bf713684e03a0029599ad269e90a4912dc03`.
Its independent prefix is
`~/.local/share/agent-observer/0.1.0a4-d5e65f10eb1bc61e`.
All 11 installed modules match the wheel on both hosts and source on Snap.
The Observer managed link was scoped-applied and verified on both hosts;
Agent Plus remains `0.13.0a2`. Provider runtime configuration was not changed.

Source validation passed all 111 tests, documentation/link checks and Ruff
lint/format checks. Added cases cover explicit names, unsafe/unproved name
provenance, sanitization/bounds, retained job names, exact conflicting links,
registry precedence and rename races without work-clock renewal.

The source live read preserved the same five Claude UUIDs. Fresh installed
Agent Plus refreshes from both Snap and Starship returned no errors and matched
both user-assigned names to their exact UUIDs. Rendered picker protocol rows
include both escaped native names. The other three retained jobs remain
UUID-labeled: they lack a verified user-assigned name. The
[filtered installation/refresh record](installed-refresh.json) contains counts,
checks and artifact metadata, without native names or payloads.

These are native metadata, installed discovery/cache and rendered protocol
checks. No provider session was started, resumed, renamed or restarted. Native
action and graphical/focus acceptance were not repeated; their earlier proof
limits remain in the [execution status](../../execution-status.md).
The candidates remain unpublished and source remains uncommitted.
