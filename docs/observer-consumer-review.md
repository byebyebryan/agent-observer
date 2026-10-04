# Observer consumer fit review

This review retains the dated migration-pilot evidence below, including earlier
artifact tuples. The next contract/client track is in
[the plan](contract-and-clients-plan.md) and [review](contract-and-clients-review.md).
Use [the handoff](execution-handoff.md) for the latest pilot tuple; do not treat
the earlier candidate versions/test counts below as current installed state.

Status reviewed 2026-10-03 against the current Agent Observer, Agent Plus and
RLCD candidates, plus the finite native evidence in the
[runtime report](evidence/2026-10-03-native-runtime/REPORT.md). Bounded installed
native actions now pass for selected routes, but the v1 snapshot remains a
candidate contract. This review does not accept a published API, full consumer
migration, GUI/focus behavior or RLCD device integration.

## Shared boundary

| Fact | Agent Plus | RLCD projection | Current evidence boundary |
| --- | --- | --- | --- |
| Host, provider, namespace and full native identity | Mesh/cache identity and fresh action validation | Selection and deduplication key | Codex session identity and Claude job/session mapping are version-gated; keep the full tuple |
| Saved inventory and loaded/runtime inventory | History alongside active work | Do not mistake a history page for the live set | Tested per-provider subsets; completeness and source health remain explicit |
| Work state with its own evidence time | Work filters and action guards | Work symbol and age | `working`, `settled` and selected waits are accepted; unsupported states remain unknown |
| Worker/runtime presence with a separate clock | Explain runtime presence apart from state | Presence without refreshing work age | Claude worker presence is tested for selected cases; Codex OS-worker presence is unsupported |
| Current terminal-client binding | Gate focus and session-specific close | Usually not needed for passive display | Unsupported on both providers; a terminal attachment does not bind the selected conversation |
| Provider-specific health, coverage and errors | Preserve healthy Mesh/provider results | Mark partial feeds and bounded reconnect | Health and coverage stay per source; one failure must not erase healthy provider rows |
| Explicit native label and chronology | Picker label and history ordering | Bounded project/session label | Use explicit provider data only; do not infer identity or history age from cwd, title, PID or file times |

Neither consumer needs prompts, responses, tool arguments/output, credential
fields, raw events or terminal captures. A short displayed ID is never an
identity or an action target. Optional work/general grouping belongs to
presentation policy and remains separate from provider, host and namespace.

Unknown work must remain unknown; it cannot fall back to idle or settled. A
fresh worker-presence read cannot refresh an older work-state clock. Saved
history, logical sessions, workers and terminal clients retain separate
identities and lifetimes.

## Agent Plus candidate

Agent Plus `0.13.0a1` source consumes the Observer CLI through existing Host
Mesh routing. Its cache identity includes host, provider, namespace and full
native identity; cache v6 and preference v2 reject old tuples. Its 338 source
tests pass. The same candidate wheel is installed on Snap and Starship
(SHA-256 `a17884c5fd85792ddd88ff35defcdf2650aa635596d0f8df0cd46c5cfa3bcbdc`);
all 21 installed Python/SVG files match the wheel/source. The CLI, launcher and
Rofi script links were scoped-applied and verified with chezmoi on both hosts.
The candidate lives in a separate prefix and override tuple; the previous
owned release archive and external pins were left untouched. See the [Snap
artifact metadata](evidence/2026-10-03-native-runtime/agent-plus-installed-artifact.json)
and [Starship artifact metadata](evidence/2026-10-03-native-runtime/agent-plus-starship-installed-artifact.json).

Installed public discovery from either host origin returns both hosts
([Snap](evidence/2026-10-03-native-runtime/agent-plus-snap-installed-list.json),
[Starship](evidence/2026-10-03-native-runtime/agent-plus-starship-installed-list.json)).
Claude is intentionally uninstalled on Starship, and its unavailable source
does not hide healthy Snap Claude or Codex rows.

The bounded installed native subset is accepted for Codex Resume on Snap and
Starship, including distinct unsaved Codex New identities on both hosts, and
Claude New and Resume on Snap. The source worktree remains uncommitted, the
candidate is unpublished, and full consumer/release closure is pending.

Current candidate action routes are:

| Action | Candidate route | Current acceptance | Guard or remaining limit |
| --- | --- | --- | --- |
| Codex Resume | Validate and attach to the exact saved `sessionId` using `--all` | Installed native route accepted on Snap and Starship; `/status` reached the exact native identity on the same daemon birth with settled work while loaded ([Snap](evidence/2026-10-03-native-runtime/agent-plus-codex-snap-resume.json), [Starship](evidence/2026-10-03-native-runtime/agent-plus-codex-starship-resume.json)) | Thread/session distinction is preserved; do not use a display label |
| Claude Resume | Validate the exact live background-job short ID, then use native attach | Installed native route accepted on Snap ([evidence](evidence/2026-10-03-native-runtime/agent-plus-claude-snap-resume.json)); menu wait is conservatively unknown/ambiguous until menu exit restores settled work | Does not prove which conversation an already-open TUI currently shows |
| Codex New | Preserve the selected configuration namespace and cwd | Installed native route accepted on both hosts ([Snap](evidence/2026-10-03-native-runtime/agent-plus-codex-snap-new.json), [Starship](evidence/2026-10-03-native-runtime/agent-plus-codex-starship-new.json)); distinct unsaved UUID confirmed natively | No inference from another row or terminal group |
| Claude New | Create with `claude --bg`, then attach to the exact typed job ID | Installed native route accepted on Snap ([evidence](evidence/2026-10-03-native-runtime/agent-plus-claude-snap-new.json)) | Zero user/assistant records before the deliberate turn; work settled and worker survived viewer close; use explicit custom config root only when a custom namespace is selected |
| Focus or session-specific close | Disabled for both providers | Unsupported | Current-client conversation binding is unsupported |

Generic terminal management remains distinct from a provider-session action.
The Claude `agents --json` roster is not the accepted passive source: its path
can adopt orphan records and write job state. The current Observer candidate
uses bounded direct metadata for the tested Claude cases.

The ordinary shell `CLAUDE_CONFIG_DIR` default is unset. The custom config-root
case is supplied explicitly to the new-job route; it must be set before Claude
starts so session, job and supervisor files stay in that namespace. Agent View
alone with a bare TUI failed the worker-lifetime proof; it is not the New route.

## Codex and Claude evidence

The same Agent Observer `0.1.0a3` wheel is installed on Snap and Starship. Its
SHA-256 is
`dd60b4754fc7be1b75f8378423edb062c91fc0db09dc79ad2e796afe003047a5`; the final
artifact record verifies the managed command and all 11 installed modules.
The artifact and per-host proof records are linked from the
[native runtime report](evidence/2026-10-03-native-runtime/REPORT.md).

Codex's accepted native subset includes exact saved/loaded inventory,
working/settled observations, an approval wait and explicit denial, a distinct
unsaved new thread, exact saved resume, work continuing after viewer exit, and
passive recovery through a new daemon birth. Ordinary proofs passed on Snap and
Starship. Terminal-current-session binding remains unsupported on both hosts,
and Codex worker presence remains unsupported. Native history chronology is
available only when backed by an explicit provider timestamp.

Claude's accepted subset includes bounded direct metadata for supervised jobs,
exact job/session identity, short-ID attach, selected work transitions, and a
worker continuing after the attachment viewer closes. The corrected
[Snap pilot metadata](evidence/2026-10-03-native-runtime/claude-snap-native-pilot.json)
records an empty disposable transcript before attach, a `working` to `settled`
transition, survival after viewer close, and stopping only the exact owned job.
The installed New route passed with closed stdin and no initial prompt; public
sampling showed six `working` and nineteen `settled` samples, and viewer close
preserved the worker and settled clock. The installed typed Resume route also
passed. While native `/status` showed `waiting` later than the job's prior
terminal clock, work was conservatively `unknown`/`ambiguous`; after Escape
exited the menu, the exact job returned to `settled` with its original work
clock. No new user/assistant turn was sent, and cleanup stopped only the owned
wrapper and job while preserving both ordinary foreground sessions and the
daemon. See the [Resume metadata](evidence/2026-10-03-native-runtime/agent-plus-claude-snap-resume.json).
The isolated stage-10 case is distinct. Agent View enabled on a bare TUI did
not preserve worker lifetime after viewer close, so that route is excluded from
Agent Plus New. GUI/focus remains unaccepted: the
current coordinator has no graphical-display connection, and disposable Tmux
attachment proves a route but not visual UI acceptance.

Hook configuration references were preserved, but callback execution is not
proved. The inspected host lacked `~/.codex/hooks.json`, `swbctl` and
`~/.claude-mem`; no hook capture or delivery claim belongs in this review.

## RLCD projection

The standalone bridge projected installed Observer schema-1 input into a live
candidate feed with both providers visible. The retained
[projection metadata](evidence/2026-10-03-native-runtime/rlcd-native-input-projection.json)
records a partial feed, 52 rows, six visible rows and two live-visible rows;
private fields were filtered and original work clocks kept. The feed preserves
full identity, separates saved from live inventory, separates work freshness
from runtime presence, and carries provider health and coverage. Fourteen
focused bridge tests pass after the live-priority correction. This is not a
firmware protocol or a device release. Firmware integration, transport and
physical-display acceptance remain pending.

The renderer must not make an incomplete empty feed look exhaustive or let one
unavailable provider hide healthy rows from another. Displaying `0 WAIT` or
`NO LIVE SESSIONS` requires the bridge/header to carry completeness and health;
unknown work is not a waiting or settled state. RLCD owns presentation and
device transport once a separate bridge is implemented.

## Remaining consumer gates

1. Complete installed Codex New headless proofs on both hosts; keep that route
   pending until the primary retains both host records.
2. Complete the primary-owned final Observer source check and evidence/cleanup
   audit. The expected 106-test total remains pending until that check passes.
3. Keep GUI/focus acceptance pending. The coordinator currently has no display
   connection; manual UI and reopen validation are still needed.
4. Keep Codex current-client binding unsupported and focus/session-close groups
   disabled until a native source proves the selected conversation identity.
5. Keep RLCD firmware, transport and physical-display acceptance separate from
   Observer schema, installed projection and synthetic bridge checks.

No consumer integration changes provider policy, creates observer sessions,
captures hook output or authorizes an action without a fresh exact identity
check.
