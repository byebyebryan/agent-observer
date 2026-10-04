# Native runtime migration execution status

Status date: 2026-10-03. Work began 2026-10-03 on Snap under the user's
authorization for the [reviewed migration plan](native-runtime-migration-plan.md).
This document tracks evidence and rollout gates; it does not mark a prerelease
artifact or source migration as shipped.

## Current checkpoint

The bounded native source slice now accepts selected Codex and Claude behavior
for the installed providers. The active Codex coordinator remains open for the
manual final handoff. Native proofs do not accept every state, identity or
consumer action. The [dated native report](evidence/2026-10-03-native-runtime/REPORT.md)
and its linked filtered metadata record the finite observations and limits.

Agent Observer `0.1.0a5` and Agent Plus `0.13.0a3` are installed on Snap and
Starship. All 13 Observer modules and 21 Plus Python/SVG files match their
source/wheel, and the four managed entry links per host are verified. Full gates
pass 127 Observer and 367 Plus tests. Exact wheel hashes, prefixes and SDK
dependency versions are recorded in the
[discovery/history acceptance report](evidence/2026-10-03-discovery-history/REPORT.md).
Sources are checkpointed in local commits; candidates remain unpublished. Previous prefixes, release
archives and external pins are preserved.

A subsequent [graphical callback audit](evidence/2026-10-03-discovery-history/rofi-callback-follow-up.json)
found one missed managed link: `.config/rofi/scripts/agent-plus` still selected
Plus `0.13.0a2`. The template and installed links now select `0.13.0a3` on both
hosts, and public discovery through that exact callback path passes. The
reported Codex `Run sleep 20` and Claude `Agent plus Claude entry accepted`
rows match owned top-level native validation conversations. Codex's native
origin is `vscode`; Claude's root transcript has `isSidechain=false`. Neither
example establishes a failed native subagent filter. Their saved history remains
available in that audit; it performed no provider action or history deletion.
The later [explicitly requested test cleanup](evidence/2026-10-03-discovery-history/test-session-cleanup.json)
removed two Codex and three Claude test conversations using exact creation
identities. Ordinary conversations and live sessions were preserved. Native
Codex delete removed its saved state; Claude rm removed the stopped jobs,
followed by selective removal of their exact UUID transcripts and session
environment directories. Discovery and production picker caches were refreshed
on both origins without errors or surviving target rows.

Installed public discovery from either origin returns both hosts without
errors: 47 Codex and 28 Claude conversations on Snap, 89 Codex on Starship after
the requested test cleanup.
Claude saved history reaches July 13 and retains native titles without a legacy
collector. Confirmed Codex children are filtered by Plus. Native saved Claude
Resume accepts both same-UUID continuation and a provider-created copy; work
survives viewer exit. Current-client binding and graphical acceptance remain
unsupported/pending. Earlier native artifacts and action evidence remain in
[the migration report](evidence/2026-10-03-native-runtime/REPORT.md), with dated
[provider-selection](evidence/2026-10-03-provider-selection/REPORT.md) and
[Claude-title](evidence/2026-10-03-claude-titles/REPORT.md) follow-ups.

Starship Claude is intentionally uninstalled. Both consumers now explicitly
request Codex only on Starship, while Snap retains Codex and Claude. Missing
or unavailable enabled providers still report errors. The initial
`0.13.0a1` discovery records preserve the earlier expected-absence error.

Bounded installed Agent Plus `0.13.0a1` actions passed for Codex Resume on Snap and
Starship and Claude New and Resume on Snap. The typed same-job Claude Resume
is recorded in [installed-action evidence](evidence/2026-10-03-native-runtime/agent-plus-claude-snap-resume.json).
Its native `/status` menu showed `waiting` later than the job's prior terminal
clock, so the consumer conservatively projected work as `unknown`/`ambiguous`
until Escape returned the exact job to `settled` with its original work clock.
No new user/assistant turn was sent. Cleanup stopped only the exact owned job
and wrapper; two ordinary foreground sessions were unchanged and the daemon was
not stopped. Installed Codex New also reached distinct unsaved native UUIDs on
both hosts: [Snap](evidence/2026-10-03-native-runtime/agent-plus-codex-snap-new.json)
and [Starship](evidence/2026-10-03-native-runtime/agent-plus-codex-starship-new.json).
The native actions were not repeated for the `0.13.0a2` provider-selection
follow-up; installed discovery and cache behavior were checked on both hosts.
GUI/focus acceptance is pending. Source commits do not establish a published
release or graphical acceptance.

## Accepted provider subset and limits

Codex 0.160.0 native proofs on Snap and Starship accept bounded saved/loaded
inventory, working/settled observations, a held approval and explicit denial,
new unsaved threads, exact saved-session resume, work that outlives its viewer,
and passive recovery after a disposable daemon restart. The installed
Observer candidate reads the managed runtime without starting it when absent.
These proofs do not establish the current TUI's selected conversation or
OS-worker presence. Session-specific focus and close actions remain disabled
for Codex rows; a terminal client is not a native conversation binding.

The installed lifecycle used the public Resume route for one exact native
Codex identity per host. In each case the attached owned client reached native
`/status` for that exact identity, observed settled work while the target was
loaded, and remained on the same daemon birth. Only owned generic wrappers were
closed, through the guarded public Tmux route. See the [Snap](evidence/2026-10-03-native-runtime/agent-plus-codex-snap-resume.json)
and [Starship](evidence/2026-10-03-native-runtime/agent-plus-codex-starship-resume.json)
records. The coordinator itself has no graphical-display connection: initial
terminal-request-only probes expired deferred wrappers and are excluded from
acceptance. Disposable Tmux attachment proves the routed command path, not GUI
visibility or focus.

Claude Code 2.1.287 accepts direct bounded metadata reads for the tested job
and worker subset. In the corrected ordinary background-job proof, stdin was
closed and the job had no initial prompt; its transcript had no user or
assistant records before exact job attachment. Native work moved from
`working` to `settled` and stayed settled after the attachment viewer closed;
only the exact owned job was stopped. The
[pilot metadata](evidence/2026-10-03-native-runtime/claude-snap-native-pilot.json)
retains counts and projections, not prompt or response text. Installed Agent
Plus New passed this supervised `claude --bg` route and exact typed attach. A
separate [installed New record](evidence/2026-10-03-native-runtime/agent-plus-claude-snap-new.json)
records zero user/assistant records after attachment and before the deliberate
turn, six `working` and nineteen
`settled` public samples, and a present worker after viewer close. The installed
typed Resume of that same job is now accepted; its evidence preserves the
conservative `unknown`/`ambiguous` guard when the native status menu waits with
a clock later than the terminal work clock. The original settled clock returns
after menu exit. The isolated stage-10 acceptance remains separate evidence.

Agent View alone does not give a bare Claude TUI supervised lifetime: the
provider worker ended when that viewer closed. Agent Plus New therefore uses
the proved supervised creation route, `claude --bg`, followed by attachment to
the exact typed job ID. A custom `CLAUDE_CONFIG_DIR` is passed explicitly when
using a custom namespace; the ordinary shell default is unset. This route's
source behavior is established and its bounded installed New path is accepted.
The `claude agents --json` roster is not accepted as an assured passive source
because its path can adopt orphans and write job records.

Across both providers, unknown work remains unknown; it is never presented as
idle or settled by fallback. Work evidence and runtime/worker presence use
separate meanings and clocks. History chronology is shown only where an
explicit provider time supports it. Provider health and coverage are independent
so one unavailable source does not erase healthy rows from another.

The current-client binding boundary remains unsupported for both providers.
Focus and session-specific close groups stay disabled; generic terminal
management is a separate action. A displayed short ID or historical Tmux label
is not an action target. Hook callbacks are not accepted as capture evidence:
trusted configuration references were preserved, but callback execution is
unproved. The inspected host did not have `~/.codex/hooks.json`, `swbctl`, or
`~/.claude-mem`; do not claim hook capture or delivery.

## Consumer and rollout status

| Checkpoint | Current status | Remaining gate |
| --- | --- | --- |
| M0: native workflow | Bounded Codex and Claude subsets accepted | Unsupported input, cancellation, error/interruption, binding and recovery cases stay explicit |
| M1: Observer | `0.1.0a5` installed on both hosts; all 13 modules match source; 127 tests/gates pass; passive Claude history and native child classification accepted | Contract stabilization and published release decision |
| M2: Codex pilot | Ordinary native proofs and installed Resume pass on Snap and Starship | GUI/focus remains unavailable; current-client binding stays unsupported |
| M3: Agent Plus | `0.13.0a3` installed on both hosts; 367 tests/gates pass; managed links and discovery verified; installed saved-Claude same/copy Resume accepted; earlier Codex actions retained | Graphical picker/terminal/focus acceptance and published release remain pending |
| M4: Codex hosts | Installed routed New/Resume reaches exact native identity and loaded work on both hosts | GUI/focus and sleep/wake/SSH-loss recovery remain pending; current-client binding unsupported |
| M5: Claude | Installed supervised New and exact-job Resume plus isolated stage 10 accepted | GUI/focus remains unaccepted; bare-TUI route excluded |
| M6: closure | Candidate artifact, source checks, cleanup and [handoff](execution-handoff.md) recorded | Manual GUI/reopen and published release bookkeeping |
| R1: RLCD | Installed schema-1 input projected live with both providers in a partial feed; 14 focused bridge tests pass | Firmware, transport and physical-device acceptance remain pending |

The [RLCD projection metadata](evidence/2026-10-03-native-runtime/rlcd-native-input-projection.json)
records schema-1 input with two providers visible, a partial feed, preserved
work clocks and filtered private fields. This remains a candidate, not a stable
public API or device release. The installed projection and focused bridge
tests do not establish firmware, transport or physical-display behavior.

## Next gates and continuity

The [discovery/history acceptance](evidence/2026-10-03-discovery-history/REPORT.md)
closes the child-classification, passive saved-Claude inventory and validated
history Resume slices. Neither provider needed existing history wiped. The
remaining gates below are not promoted by the bounded installed proofs.

1. Keep native GUI/focus acceptance pending. The active coordinator has no
   graphical-display connection; preserve it and record/manual-test its reopen
   route last.
2. Review the source and candidate artifact bookkeeping before published
   release closure; the independent installed prefixes are a verified pilot.
3. Keep current-client binding unsupported on both providers. Do not enable
   focus or session-specific close groups from terminal attachment alone.
4. Preserve partial-provider semantics and the `unknown` work state through the
   installed consumer path. Keep hook delivery unproved unless a separate
   finite callback check establishes it without changing ordinary hooks.
5. Keep RLCD firmware, transport and physical-device acceptance separate from
   Observer and Agent Plus checks.

The active coordinator session is
`01a0fece-0176-7a33-abb3-e99fdb38417a`. Keep it alive. Before closing it, record
and manually verify its exact reopen route. The prepared
[execution handoff](execution-handoff.md) records the full identity and command;
reopening it is the last step, not an unattended prerequisite.
