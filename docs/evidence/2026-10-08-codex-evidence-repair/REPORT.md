# Codex saved-evidence repair acceptance

Date: 2026-10-08. Status: the two reproduced producer/writer gaps are closed
for the separately installed `0.5.0a4` candidate on Snap and Starship. This is
Observer-only acceptance. Normal CLI links and managed user services remain
on a16; Claude, frontend migration and terminal integration are separate gates.

## Artifact and contract

The [manifest](../../../artifacts/observer-0.5.0a4.json) freezes source
`03286334bc086033b06e899da187f948777b56e0` and wheel SHA-256
`28f5ad02a0312b3632b3cedbff0d079ad465a84fd062fb8efb6274902af4699f`.
The explicit prefix on both hosts is
`/home/bryan/.local/share/agent-observer/0.5.0a4-28f5ad02a0312b36`.
[Snap](snap-artifact.json) and [Starship](starship-artifact.json) verify all wheel
bytes, entrypoints and schemas with the core-only profile, no SDK/bundled provider
executable and zero provider invocations. Acceptance-harness refinements after
the freeze do not change packaged modules or this wheel.
The exact wheel and manifest are retained in each prefix's `artifact/` directory.

API 2, snapshot/watch wire 4, service protocol/frame/request 2 and independent
writer wire 2 are unchanged. No provider version/hash allowlist was introduced.
The observed daemon is 0.162.0 on both hosts; the isolated TUI copies the installed
0.161.0 bytes. These are provenance for the recorded native cases, not support
policy. The [repair plan](../../codex-evidence-repair-plan.md) records the scope.

## Repairs and controlled checks

Catalog membership and a successful exact summary read now supply separate
evidence. Page failure, malformed pagination, cursor cycles, collection deadline
and summary-read budgets cannot leave an unverified current parked fact.
Individually proved running/parked siblings survive; incomplete saved evidence
is exposed as partial. Native running does not require saved history.

The exact writer now requires an explicitly non-ephemeral summary plus a
successful bounded metadata-only stored-history read. Unproved persistence
returns `resume_saved_history_unproved` during preparation and revalidation,
before native entry. It never lists a capped discovery view or reads native
private files. Successful empty history and unavailable activity clocks remain
distinct from failed history reads.

Controlled regressions cover those faults, missing/malformed/ephemeral writer
evidence, no-entry rejection, partial watch retention and recovery. Real local
service sockets prove cached pull/push parity through partial discovery and
recovery; retained parked state becomes unknown with the original last-known
state/activity clock. Existing incarnation/identity/expiry/order tests still
pass. The final `scripts/check` passes 367 tests (one skipped), 86 Markdown files
and repository checks; scoped Ruff validation also passes. These are controlled
checks, not native pagination fault injection.

## Independent ordinary CLI comparison

Each view below has two bracketing native/CLI rounds. The reference uses its own
stdlib transport, imports no Observer code and queries only metadata. All rounds
have current sources, complete declared runtime/saved coverage and zero issues.

| Host | Direct / isolated cached publisher | Rows | Running | Known activity | Classification |
| --- | --- | --- | --- | --- | --- |
| Snap | [direct](snap-ordinary-direct.json), [cached](snap-ordinary-cached.json) | 89 | 2 | 52 | 51 user, 38 child |
| Starship | [direct](starship-ordinary-direct.json), [cached](starship-ordinary-cached.json) | 353 | 5 | 105 | 80 user, 252 child, 21 unknown |

Both views match exact identities, daemon runtime/phase, saved identity,
tree-root metadata, blocked reasons and known conversation clocks/outcomes.
The read client also passes child filtering, activity/urgency ordering, human
age, exact show and doctor count checks. Missing native titles/clocks/outcomes
and the 21 older Starship unknown kinds remain unproved, rather than inferred.
The active ordinary rows are Snap's agent-observer/tmux-plus and Starship's
fluid-2.5d/pd-lab-next/raster90/devlog/sleep. Phase may change between rounds;
these are daemon contexts, with no terminal/process census used as authority.

## Focused isolated native proof

| Case | Snap | Starship | Accepted behavior |
| --- | --- | --- | --- |
| Blank then initialized history | [saved evidence](snap-native-saved.json) | [saved evidence](starship-native-saved.json) | Blank idle remains running without saved history; Resume rejects before entry and preserves native inventory; after one completed turn, exact native Resume enters and preserves the native activity clock |
| State and pull/push | [monitor](snap-native-monitor.json) | [monitor](starship-native-monitor.json) | Independent direct/cached/pushed identity/state/age parity, positive parked rows, held approval/question and waiting after explicit private interruption |
| Supported fork target | [fork](snap-native-fork.json) | [fork](starship-native-fork.json) | Exact fork thread receives a new native turn and parent turn stays unchanged; observed thread/root IDs are equal |

The [initial persistence spike](snap-persistence-spike.json) establishes that
`ephemeral=false` and a nonnull native path do not prove a materialized blank
context. It reads the private file only as an explicitly isolated operator
negative control; production observation never does so. The official
[app-server documentation](https://learn.chatgpt.com/docs/app-server) describes
summary reads and metadata-only stored-turn pagination; native proof remains
separately required.

An attempted empty-log fixture did not establish a native empty-history case:
turn metadata remained readable after trimming the private log, including after
a forced private daemon restart. A graceful private stop also exceeded the
probe's bound. Original private bytes were restored and those namespaces were
cleaned. The final native harness uses native workflows without private-store
edits. Positive empty-response semantics have controlled coverage only; this
report does not claim native empty-saved TTY acceptance.

An early held-state run also reported a bracketing `createdAt` sampling race.
The final harness retries every field within 20 seconds and accepts only zero
comparison issues; it does not waive races or weaken native expectations.
Final Snap approval/question parity takes one/two attempts respectively.

## Preservation and remaining gates

Before/after receipts verify ordinary provider configuration hashes, selected
links, Observer unit/service identity and owning native daemon incarnation:
[Snap before](snap-before.json), [Snap after](snap-after.json),
[Starship before](starship-before.json), [Starship after](starship-after.json).
The [cleanup receipt](cleanup.json) records termination of all disposable
namespaces and removal of borrowed authentication/history. Repository evidence
contains bounded metadata/reasons only, with no raw payloads or terminal output.

Normal rollout still needs its separate restart/crash/reconnect/rollback gate.
Distinct thread/tree-root TUI entry remains `session_tree_entry_unproved`.
Claude remains explicitly unsupported in this Codex-only candidate. Post-TUI
closure lifetime, physical wake, long managed-unit resource acceptance,
notifications and downstream GUI/device acceptance are outside this pass.
Future terminal discovery/attachment belongs to tmux-observer and its clients;
no terminal authority or compatibility layer was added here.
