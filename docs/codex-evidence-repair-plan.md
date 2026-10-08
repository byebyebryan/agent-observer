# Codex saved-evidence repair pass

Date: 2026-10-08. Status: R1-R4 accepted against the
[a4 candidate](evidence/2026-10-08-codex-evidence-repair/REPORT.md), within its
recorded native and controlled coverage. Scope: Observer-only producer/read/service correction and a
separately accepted exact Resume preflight. The normal selected a16 installation,
Claude, frontend work and terminal attachment remain separate gates. Future
terminal discovery/attachment should consume tmux-observer rather than add a
second terminal observer here.

## Reproduced gaps

1. Catalog membership set saved identity before a summary read. A later page
   error skipped validation and preserved an unverified current parked row.
   This was reproduced with controlled transport failure, invalid pagination
   and cursor-cycle fixtures, not the ordinary native sample.
2. Exact writer lookup treated every readable summary as saved. Blank
   runtime-only Resume was documented as unaccepted but not explicitly guarded.
   A passive prepare could therefore select the native Resume route without
   proved persistence. No native action was performed in that reproduction.

## Execution and acceptance

| Checkpoint | Work | Acceptance |
| --- | --- | --- |
| R1: producer | Separate catalog membership from successful exact summary reads; preserve native running independently of saved history; expose incomplete saved evidence | Aborted pages, malformed responses, cursor cycles, summary failures/budgets and identity/incarnation failures cannot promote unverified parked rows; proved siblings survive |
| R2: writer | Prove exact stored-history readability before New/Resume route selection; reject unproved Resume before entry and during revalidation | No discovery-list cap, private-file lookup or implicit New fallback; empty saved history does not require an activity clock; ephemeral or unmaterialized contexts are rejected |
| R3: read/service | Exercise partial discovery, retention, expiry and recovery | Direct and sampled watch remain truthful; cached pull/push carry the same view; retained parked evidence becomes unknown with its original last-known clock |
| R4: artifact/native | Freeze a successor wheel, install it separately on Snap/Starship and compare public commands with independent daemon reads | Exact ordinary identities/status/activity match; isolated blank rejection and supported saved/live TTY Resume pass; borrowed authentication/history are cleaned; normal selection remains unchanged |

R1, R2 and R4 are separate reviewable commits. Run `scripts/check` before each
commit and the appropriate focused runtime checks after relevant changes.
API 2/read wire 4/service 2/write wire 2 remain unchanged unless an actual shape
change is necessary. Versions and executable hashes are diagnostic provenance,
not provider capability allowlists.

## Native persistence decision

The official [app-server contract](https://learn.chatgpt.com/docs/app-server)
documents summary reads and metadata-only stored turn pagination. The installed
schema describes `path` as unstable and `ephemeral` as disk-materialization
intent. A fresh isolated Snap probe found a blank non-ephemeral context with a
nonnull native path but no saved catalog record or materialized history. Its
metadata-only turn read failed. After one native turn, stored-history pagination
succeeded and catalog membership was present. These are focused native samples,
not a promise about all future storage modes.

Exact writer proof therefore requires an explicitly non-ephemeral native summary
and a successful bounded `thread/turns/list` response with `itemsView=notLoaded`.
Empty `data` is valid positive readability; missing activity clocks do not mean
unsaved. Missing/unsupported/failed history reads stay unproved and cause
`resume_saved_history_unproved`. The core never reads the native path/file for
this proof. A proved saved identity does not automatically accept every native
entry route: distinct thread/tree-root TUI targeting remains independently
guarded.

## Delivery boundary

Native actions use fresh operator-owned private configuration/endpoints and
user/mount/PID namespaces. The pass does not restart ordinary providers, select
normal CLI links/services, edit clients or infer runtime from TUI/tmux state.
Controlled faults remain labeled controlled; ordinary/native success cannot
promote them to a native fault-injection proof. Normal rollout follows only a
separate restart/crash/reconnect/rollback checkpoint.
