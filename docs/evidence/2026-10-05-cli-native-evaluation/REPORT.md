# Installed CLI versus independent native evidence

Date: 2026-10-05. Status: evaluation completed; current Codex discovery fails.
This executes the [evaluation plan](../../cli-native-evaluation-plan.md) and
[workflow](../../observation-validation-workflow.md). No producer adapter,
provider policy, selected artifact or frontend was changed.

## Method and exact scope

The standalone [reference probe](../../../scripts/evaluate-observation) imports
only the Python standard library. It reads the existing Codex Unix WebSocket
endpoint and direct Claude registry/job/transcript metadata. It does not import
Observer collectors, projections or validation helpers. Each installed snapshot
is bracketed by native samples; only stable fields are compared. State and
activity changes between the brackets are recorded as races.

The selected CLI on both hosts is Observer `0.2.0a8`, prefix
`/home/bryan/.local/share/agent-observer/0.2.0a8-8bbbff345b58c051`, wheel SHA-256
`8bbbff345b58c0517e2ca69bc9caa2157d01c59c82c087af7b06dc17c4d90a8c`.
Its [earlier acceptance](../2026-10-05-operational-resilience/REPORT.md) is bounded
to Codex runtime `0.160.0`. Installed Codex executable bytes on both hosts still
match `12eb3e81…`, that accepted artifact.

Both running daemon peers now use the `0.160.1` release path and exact image
SHA-256 `f34a4d2301892ae96c90097786bfe5dc269f187b6f69faf42a7b357b8c081e35`.
The probe verifies the existing owned endpoint, peer UID, image and process
birth, then requires that explicit study-only digest. Version evidence is the
release path and image digest; no native entrypoint was invoked for version
discovery. This pin does not register the image in Observer or accept its
action/state capabilities. The cause of the daemon update was not established.

Claude on Snap remains installed `2.1.289` / `a186b99e…`; three independently
verified workers retain `2.1.287` images and one uses `2.1.289`. The independent
reference binds each UUID to native registry PID/domain/starttime, rechecks
birth after image inspection, and uses the matching job record where available.
Observer's optional SDK is `0.2.163`. Claude is not evaluated on Starship.

Final snapshot samples are 2026-10-05 21:07:53–21:07:58 UTC. Counts below are
samples of native inventories, not a permanent roster. See the bounded
[Snap comparisons](snap.json), [Starship comparisons](starship.json) and
[supplementary checks](supplementary.json). No raw native payloads, conversation
bodies, tool output, credentials or terminal captures are retained.

## Results

| Host/provider | Independent native inventory | Installed Observer | Result |
| --- | --- | --- | --- |
| Snap/Codex | 49 saved-or-loaded records; 4 loaded, comprising 3 user threads and 1 child | 0 rows | All 49 stable identities missing within this native scope |
| Starship/Codex | 92 saved-or-loaded records; 4 loaded, comprising 2 user threads and 2 children | 0 rows | All 92 stable identities missing within this native scope |
| Snap/Claude | 28 conversation identities and 4 verified registered workers | 28 persistent rows and 4 running rows | Stable membership and presence agree; two work phases remain unproved |

The native Codex user threads are `esp32-349`, `agent-observer` and `esp32-rlcd`
on Snap, and `fluid-2.5d` and `pd-lab-next` on Starship. Native user/child markers
are read directly. The source failure prevents current installed-CLI Codex
classification, phase, age and project checks from being exercised.

Claude's 25 independently available explicit titles and all 28 recorded cwd
values agree. Three titles lack an independently proved explicit-title value
within the reference's typed metadata scan, so those title checks remain unproved.
Each final round matches 27 stable activity clocks; the actively changing
`embeddings-bf` clock is a race between the native brackets. The completed
`recap-2026-f2` (`bbe9d846…`) maps to waiting and the interactive
`embeddings-bf` worker maps to working. The two older recap workers remain unknown.

Installed `list`, human age rendering, attention/activity ordering,
`include-children`, exact-reference `show` and doctor count checks pass against
the same captured public snapshot. All four running Claude references return
the expected row. Child-filter results in this pass have zero confirmed child
rows to filter; the Codex failure makes that ordinary end-to-end check vacuous.
They do not accept new native child detection.

Four distinct Snap cwd contexts agree with independent read-only Git metadata
checks, including two repositories and two non-repositories. Optional configured
root/project mappings are not selected or tested here. The saved-history
reference scans a 2 MiB transcript tail plus a bounded head, independently of
Observer's 512 KiB tail and SDK catalog. It reads about 50 MiB per sample and
retains only metadata. Metadata-only or unproved transcript files remain scan
notes; they do not erase a separately proved conversation with the same UUID.

The installed sampled watch passes five-frame schema/revision checks over about
nine seconds: one snapshot, two changes and two heartbeats. Snap provider rows
remain partial while Codex is unavailable. This accepts framing for the sampled
run, not completeness, failure-transition recovery or lossless native events.

## Gaps and issues

| ID / priority | Finding and evidence | Required follow-up |
| --- | --- | --- |
| E01 / P0 | Codex daemon image/version drift removes discovery on both hosts. The selected `0.2.0a8` collector expects the old release image; independently verified `0.160.1` peers return inventories, while the public source rejects them. | Independently prove and register the current daemon artifact per capability. Re-run installed inventory/state/action gates appropriate to each capability; do not add a blanket version bypass. |
| E02 / P1 | Codex saved discovery is coupled to live endpoint/artifact acceptance. This failure removes saved history as well as monitoring: 49 and 92 records disappear. | Establish whether saved discovery can remain available through an independently accepted metadata source or read capability. Keep unsupported live state explicit. Avoid a second legacy discovery stack. |
| E03 / P1 | Diagnostics misidentify this version difference as `runtime_peer_identity_mismatch`. Doctor reports runtime version unavailable and generic observation failure, although the owning peer/image is inspectable. | Separate unsupported executable/version from ownership/incarnation failure and expose bounded actual-runtime evidence. A matching installed CLI version is insufficient daemon preflight. |
| E04 / P1 | Two live Claude BG recap workers have registry `idle` plus job `working`, tempo `blocked`; phase stays unknown. Early samples also capture the third recap job's native `state=blocked` with busy/idle registry changes; `native_blocked_phase_unproved` makes that phase unsupported until the job later becomes done. | Use isolated native cases to establish blank/background idle, blocked job, held approval, internal/tool waiting and completed readiness as distinct predicates. Do not map a tempo or job label directly to human urgency. |
| E05 / P1 | Claude public `kind` is unknown for every persistent row. Native subagent files have `isSidechain=true` and agent IDs scoped under parent conversations, but these are not runtime UUID bindings. A transient UUID-only registry row appears during an early comparison; it is gone later. A subsequent 50-second monitor captures no new transient worker. | Establish native top-level/child and helper-runtime identity correlation in a held controlled case. Prove filtering without hiding legitimate unknown sessions. No false-positive child is confirmed by this pass. |
| E06 / P2 | Older Codex clocks are over-restricted by the current predicate: 13 of 48 saved Snap rows and 5 of 90 saved Starship rows have explicit completion timestamps but null start timestamps. `codex_activity` rejects that shape. Both payloads explicitly exclude conversation items. | Prove completion-only timestamps as conversation activity for the accepted runtime, then accept them without creation/mtime fallback. Current `0.160.1` observations alone do not change the old artifact's support. |
| E07 / P2 | Three Claude histories have recent conversation cwd in a worktree/subdirectory while the public recorded cwd remains the original repository root. That agrees with the current SDK/head-based recorded-cwd contract. | Decide whether to add separately evidenced current/recent working context, preserving original cwd and provenance. Validate worktree/project grouping and Resume/New Here implications. This is a context limitation, not a cwd projection regression. |
| E08 / P2 | An older Snap Codex TUI process predates the managed daemon and remains outside a proved current thread binding. The native scopes here cover loaded threads/registered workers, not every terminal or executing context. | Diagnose that process's topology and report unsupported/unobserved context explicitly. Do not count it as a missing daemon session or infer identity from launch argv/cwd. Full standalone parity is not an automatic migration requirement. |
| E09 / P2 | The accepted `0.2.0a8` manifest exists in private acceptance scratch but is absent from tracked `artifacts/`; manifests currently end at `0.2.0a7`. Public-contract status still calls `0.2.0a7` selected and artifact-operation examples identify `0.2.0a3`. | Checkpoint the unchanged accepted manifest and reconcile current operational documentation without changing native support or rebuilding production bytes. The prior exact wheel/acceptance evidence is present; the reusable repository entry is missing. |

Returning exit zero or an empty top-level `errors` array does not prove healthy
discovery. In this pass provider-specific errors and coverage correctly carry
the failure, and overall Snap health is partial. Consumers and evaluation tools
must inspect those fields; this behavior is not treated as a new wire defect.

## Remaining capability and evaluation gaps

- Saved-only or worker-absent sessions have unknown runtime/phase; exhaustive
  absence and parked inference remain unsupported. Claude saved scan coverage
  remains partial even when the source is freshly read.
- General questions, foreground Claude readiness, failure/interruption outcomes
  and arbitrary new provider artifacts/topologies retain independent proof gates.
- Current viewer/thread binding and attachment are unsupported. Window focus,
  session-specific close, Agent Plus silent Resume/age presentation and graphical
  acceptance remain separate consumer work.
- Native push/hooks, event replay, multi-host networking and long-duration
  sleep/wake/reconnect recovery are not accepted by this sampled pass. Configured
  project/root mapping is also unrun in this ordinary configuration.
- The current `0.160.1` native New/Resume/approval/recovery gates and held Claude
  child/helper/idle/blocked cases were not run. Earlier controlled acceptance
  remains bounded to its original artifacts; no new test session was created.
- The reference is bounded, not an exhaustive alternative collector. Its
  before/after checks cannot exclude an intervening ABA transition, and completed
  transient contexts without retained authoritative metadata remain unresolved.

The reference comparison's five synthetic regression checks cover missing rows,
sampling races, public-only unknowns, cwd semantics and rejection of action/content
requests. These are evaluation-tool checks, not native transition proof.
The full repository suite passes 182 tests; scoped Ruff passes.

## Next Observer checkpoint

Prioritize E01–E03 together: independently evaluate current Codex daemon
capabilities, restore compatible discovery and describe exact version failures.
Then address E04–E05 through held Claude cases and E06 through native clock
proof. E07 requires a contract/context decision; E08 is a bounded topology
diagnostic; E09 is artifact/documentation bookkeeping. Accept the repaired
producer independently before resuming the downstream client pass.
