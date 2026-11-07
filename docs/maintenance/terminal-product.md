# CLI and dashboard product contract

The [0.7.0a18 prerelease](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a18)
provides the finite sessions CLI and optional persistent dashboard. This page
records their current behavior, ownership and acceptance limits. Use the
[sessions guide](../guides/sessions-cli.md) and [dashboard guide](../guides/dashboard.md)
for installation, source configuration, commands and keys; use the
[roadmap](roadmap.md) for priorities and deferred work.

## Workflows and public interfaces

| Workflow | Contract |
| --- | --- |
| Quick check | Bare `agent-observer`, `sessions` and `sessions overview` share a finite overview with source health, shown/matching and unfiltered counts, and at most ten rows. |
| Investigate | `sessions list` returns all matching rows; `show` selects a full native ID in one host/home or an exact five-field JSON reference. Exact inspection bypasses display filters, including status, and hidden kinds, but cannot recover absent history. |
| Inspect delivery | `sessions sources` reports source health even without sessions. `sources --configured` validates configuration without connecting or importing Mesh. |
| Script | Finite `--format json` emits terminal interface 1; `sessions schema` prints its packaged schema without configuration or optional imports. Human text spacing is not a parser contract. |
| Keep watch | `dashboard` remains open until quit or terminal shutdown, over the same configured cached sources. It has no finite lifetime, JSON watch, `--format` or `--timeout` option. |

Terminal interface 1 is independent of API 4, snapshot/watch 6, Service 4 and
working-set v1. Its [packaged schema](../../agent_observer/contracts/terminal-v1.schema.json)
separates selection/filters, unfiltered totals, sources, members, uncertain
identities, known nonmembers and result/error. Additive fields are allowed;
incompatible output needs a new version. The utility example's diagnostic JSON
is not this contract. Existing direct/service/Mesh diagnostics remain separate;
diagnostic `working-set watch` retains its 60-second bound.

## State and presentation rules

Preserve exact `hostScope/provider/namespace/nativeIdKind/nativeId`, with the
configured source as provenance. Labels, paths, project keys and thread-tree
roots are metadata. Duplicate full-identity claims block every claimant rather
than choosing by arrival order. Native observation semantics remain in
[observation boundaries](../reference/observation.md).

- Membership, runtime and phase are independent. `active` needs an unexpired
  active branch; `recent` means recent membership is proved while active is not
  currently proved. A retained running value cannot establish active membership.
  Uncertain/nonmember outcomes come from the public facade, never local guesses.
- Runtime is running/parked/unknown; running phase is working/waiting/blocked/
  unknown. Native idle means running/waiting. Parked requires positive native
  evidence. Waiting alone does not mean a response is required. Expired facts
  become qualified unknown; last-known values remain explicitly noncurrent.
- Source health and unfiltered counts survive filtering, hidden kinds and empty
  results. `complete-empty` requires current admitted baselines, complete
  unexpired scopes and no members, uncertainty or known nonmembers across all
  watched sources. Zero matches, missing scopes and unavailable feeds cannot
  establish it. Only known nonmembers means zero qualifying members, not empty.
- Default presentation hides confirmed child/system kinds, retaining unknown
  kinds. Source/host/home/membership/runtime/phase/query/status selectors OR
  within a dimension and AND across dimensions. Finite `--status` uses the same
  qualified mapping as the dashboard, is applied before the overview cap and
  does not change in-app dashboard state. Nonmembers require explicit inclusion;
  exact inspection can still resolve them. Activity order is newest first across running and parked
  rows; unknown ages follow known timestamps and full identity breaks ties.
- Search is a case-insensitive literal substring over admitted name, project,
  reported cwd, host/home and full native ID; queries are 1–256 characters.
  Dashboard search also includes sanitized current repository root/commonDir/
  relativePath. Expired repository fields stop matching independently of other
  metadata. Existing finite CLI query results and default terminal JSON v1
  reports remain unchanged.
- Reported title/cwd have no independent field lease and imply no fresh native
  sample. Optional repository/project metadata uses workspace support; linked
  worktrees remain distinct. Human finite CLI and dashboard workspace labels
  prefer an admitted, current leased repository/worktree root and otherwise use
  reported cwd; expiry falls back to cwd. This does not add repository fields to
  finite CLI search or default JSON. No filesystem/Git discovery, branch/dirty
  queries, content search or persisted search history is performed.
- Activity uses native `activity.at`. Approximate display age is not evidence
  renewal, membership arithmetic or phase-entry time. Polls, title changes and
  transport heartbeats do not advance it; reconnect does not repair native
  clock uncertainty.

The dashboard initially shows the full list with details closed. The current
source preview has a dashboard-only row refinement, not included in the
published a18 wheel. At 100 columns and wider it keeps the full four-cell
Status / age, Session, Profile and Workspace table. At 32–99 columns each entry
uses exactly two lines: a selection/pin marker, qualified status, truncated
title and full activity age on the first line, then profile and workspace on
the second. Age labels can grow on their row while the title start and age
right edge stay fixed. Below 32 columns or 12 rows it shows resize guidance
with live source health and help/quit. Height reduces chrome and page capacity
but does not compact a wide table.
Enter opens split details at 120x30 or larger, otherwise a separate view.
Source health remains visible with its denominator in the main view, panels and
filtered states. Detail paths, source evidence and filter choices wrap and
scroll; selection remains visible on resize. The
[dashboard guide](../guides/dashboard.md#read-and-navigate) owns the key
reference and layout explanation.

List updates remain independent per source. Current visible rows stay on screen
while an empty sibling warms or adds its baseline; changed or expired facts are
reconciled or withdrawn before the dashboard waits for widget work.

Selection follows the exact identity through reorder, filtering, paging and
resize. A hidden selection stays pinned. If evidence disappears or its source
is revoked, retain only its identity and sanitized label, marked unavailable;
discard old facts. Fresh evidence for that identity can restore it. Background
updates never select a neighbor. Search input owns printable q/j/k; Escape
restores the pre-edit query. Search edits debounce at 150 ms. Clearing selection
on the main list does not reset filters.

Metadata remains literal: escape terminal/bidi controls and disable markup,
automatic links, clipboard and URL actions. Color and standard glyphs supplement
state words; no special font is required. Nonempty `NO_COLOR` overrides color
settings. Piped finite text has no color/control sequences, pager or truncation.

## Configuration and role ownership

The private version-1 consumer file is
`$XDG_CONFIG_HOME/agent-observer/terminal.toml`, falling back to
`~/.config/agent-observer/terminal.toml`; `--config` selects another file.
Validate before I/O: owner-private readable regular file, no final symlink,
64 KiB maximum, exact keys, bounded IDs/labels, namespace and absolute socket.
Require unique source IDs, host/home pairs and host/Mesh-source routes.

Resolve `default_sources` unless explicit source/host/home selectors choose
other configured entries. Unknown selectors or zero selection fail. Check every
scope and identity against the expected host/provider/namespace before assigning
a home label. A mismatch blocks and revokes; a publisher restart cannot silently
adopt another home. Single-source socket/window overrides are diagnostic only;
socket override requires local scope and the window must match the publisher.
Ambient `CODEX_HOME` never redirects a cached source.

Configuration is frozen during the invocation. Dashboard in-app source/host/home
filters change presentation, retaining the watched set and coverage denominator.
Retry uses the same binding without reloading config or adopting a new namespace.
Restart with explicit selectors/configuration to change the watched set. There
is no automatic host/home discovery, route creation or configuration writing.

Product reads require the public working-set facade and optional Mesh dependency,
even for a local bridge; published recipes pair the reader with Mesh a25.
Core and Service 4 diagnostics import neither Mesh nor Textual. The dashboard
extra is optional; its qualified framework is Textual 8.2.8. Published dependency constraints are linked from
[operations](operations.md#cli-and-dashboard-reader-release).

The independent CLI/dashboard reader selection does not advance collectors,
working-set/full publishers, hardware dashboards, Agent Plus or Tmux. Readers
never start providers/services, control conversations, send alerts or fall back
to a full inventory. Existing directional Mesh authority owns remote access.

## Read lifecycle

Finite reads wait for each source's first settled result or a shared ten-second
deadline (`--timeout` 1–60), then freeze per-source capture clocks and close all
streams. Recheck expiry while waiting for slower sources. Report generation and
cleanup renew nothing; exported deadlines are not a continuing lease transfer.
A finite fleet report is not an atomic snapshot.

The persistent supervisor owns one attempt per source: profile, configured
reader, request ID, guard, pending read and receiving-clock binding. Views own
no streams. Keep `report_routes=False` and the existing proof cadence. On the
first failure/gap/resync, revoke current positives, retire that attempt and join
owned cleanup before retry; healthy siblings continue independently. Avoid
simultaneous SDK and product retry supervisors.

Retries use 1, 2, 4, 8, 16, then 30 seconds, jittered to 80–100%; reset after
60 seconds of stable admitted delivery. Permit four concurrent setups and at
most one new start per second, including manual retries. Attempt timeout starts
after start scheduling and covers setup through settled baseline: default
15 seconds, `--connect-timeout` 1–60. Binding/namespace/contract/identity/capacity
faults block for inspection/manual retry. Retry never repairs a native source.

Increment a source epoch on revocation and require a fresh admitted baseline
before restoring positives. Keep one coalesced dirty notification and the latest
state per source; stale tasks/projections cannot restore older authority. Recheck
the projection before paint and after scheduling stalls or resume. Revalidate a
changed receiving clock/domain; wall time alone renews nothing.

Schedule quiet expiry from public receiving member/branch/field, scope and
receipt deadlines, without reproducing producer arithmetic or issuing extra
native samples. Unchanged heartbeats do not rebuild the report. Crossed leases
and revoked epochs bypass cosmetic throttling; visible withdrawal must occur
within 250 ms on a draining terminal, including event-loop delays.

The [sessions guide](../guides/sessions-cli.md#pipes-json-and-exits) owns finite
exit meanings. Dashboard quit returns 0 regardless of source health; setup errors
return 2, internal/output/cleanup failure 3, hangup 129, interrupt 130 and
termination 143, after owned cleanup. Feed failures remain visible in the app.

## Output, cleanup and resource budgets

Validate interactive stdin/stdout/stderr on the same cursor-capable Linux
terminal before reads or raw mode; reject pipes and `TERM=dumb` with finite-CLI
guidance. The outer runner owns reads and joins cleanup independently of the
framework's widget lifetime. Repeated cancellation cannot interrupt owned joins.
Timeout is failure evidence, never permission to abandon a live owned handle.

The bounded Linux driver uses the framework extension point and preserves
input/resize/job-control/termios ownership. Preserve encoded FIFO byte order and
inherited descriptor flags; coalesce models before encoding, not terminal diffs
after encoding. On output failure, revoke reads and restore terminal flags
independently of screen-reset delivery. A stopped sink cannot receive a reset
or visible revocation; record that distinction explicitly.

| Boundary | Budget and required proof |
| --- | --- |
| Admission | At most eight sources, 4,096 outcomes/source, 8,192 total and 32 MiB encoded admitted payload. Defaults reserve 1,024 identities/4 MiB per source before I/O. Capacity faults block the affected source, never silently truncate. These are safety bounds, not fleet capacity or peak-RSS guarantees. |
| UI/state | At most four cosmetic paints/second, one age update/second and 200 materialized list rows/page. A replacement may prepare one hidden page alongside the current page; paint generations do not accumulate. Filtering/counts span all admitted outcomes. One pending read/source; bounded latest state, no event history or session disk cache. |
| Output | At most 512 KiB pending encoded output and per accepted write; fail after two seconds without drain progress. No blocked event-loop queue put or unbounded writer join. |
| Normal resource profile | Three sources x100 identities, draining 120x40 terminal, two-minute warmup and 30 measured minutes. Client plus owned children <=5% of one core and <=192 MiB RSS; report producer/sampler cost separately. |
| Interaction | Normal key/resize-to-visible p95 <=100 ms; admitted-update-to-visible p95 <=250 ms at its recorded boundary. Exercise 120x30 and 120x16 full tables, 80x24 and 60x16 compact rows, 40x12 and 32x12 compact rows in the source refinement, and guidance below 32 columns or 12 rows. Pixel-to-column fit depends on the emulator/font and remains a human visual check. |
| Recovery | Source/warming UI within 500 ms; controlled available baseline within five seconds of an attempt, plus start queue/backoff. Fresh baseline and healthy siblings required. Verify quiet expiry, receiving-clock changes, job control and 100 controlled disconnect/recovery cycles without resource growth. |
| Shutdown | Terminal flags restored within two seconds and all owned cleanup joined within five. Preserve unrelated native sessions, services and processes. Measure delivered screen reset separately. |
| Practical preview | Twenty-second installed-dashboard check over the actual configured cached fleet: current projection/counts/source health, clean quit and terminal restoration. Supplement with controlled update/input/expiry/recovery checks. This is not sustained-performance or native-accuracy proof. |

Source checks require both optional stacks with
`./scripts/check --require-working-set-mesh --require-dashboard`. Package matrices
cover core-only, Mesh-only, dashboard-only and paired installs on Python 3.11
and 3.14. Core/help/schema/config inspection stays lazy; a dashboard-only install
must explain missing Mesh before I/O. Check packaged code, schema and stylesheet
outside the source tree. Use owned cached fixtures and metadata-only native
comparisons under [validation](validation.md), preserving ordinary providers.

## Qualification and limits

The a18 [manifest](../../artifacts/observer-0.7.0a18.json) and public
[provenance](https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a18/provenance.json)
bind runtime source, wheel, dependency stack, exact-head CI and source/installed
checks. Managed rollout targets Snap and Starship; Carbon is offline and pending;
[operations](operations.md) separates managed selections from publication.
Reader delivery does not close separate producer incidents or establish human,
full native/remote, resource or physical-device acceptance.

Sustained resource/native evidence retains its original source-preview boundary:
source `d57233313f01983361b75fb0953662afa212c513`, wheel SHA256
`fd8ec13ee37470d1e31788df399057ba371eeaad67d412087993eb75995c55f0`
with unreleased a12 metadata. Its fixed normal profile measured 4.88%/4.74%
of one core and 65.17/66.60 MiB peak RSS on Python 3.11/3.14. Later a13/a14/a15/a16/a17/a18
reader and package/delivery checks do not claim new sustained runs.
Selected local native comparisons cover only their exact identities/intervals;
agreement with another Observer command is cached-consumer evidence.

The [frozen qualification record](https://github.com/byebyebryan/agent-observer/blob/7dbcd611f7b0ecfbebf7b2e8053963fb25915999/docs/maintenance/terminal-product.md#resource-and-installed-qualification-baseline-t9)
retains detailed measurements, artifact bounds and earlier failures. Prior CPU
and task-minimum failures remain failed; the optional eight-hour soak stopped
after about 3.6 measured hours and remains incomplete. Eight-source/8,192-outcome
reader-only stress runs never reached complete coverage and do not establish
usable dashboard capacity or an exact timeout cause. The user deferred extended
soak, stress qualification and read-path optimization in favor of the practical
preview. Reopen conditions belong to the [roadmap](roadmap.md#deferred-work-and-reopen-conditions).

Completed planning, feasibility and implementation checkpoints remain
[in Git](https://github.com/byebyebryan/agent-observer/blob/7dbcd611f7b0ecfbebf7b2e8053963fb25915999/docs/maintenance/terminal-product.md),
not as additional maintained contracts or current deployment instructions.

## Read-only session board

The a18 reader prioritizes status and activity in human terminal output,
with exact favorites and optional remembered ordering in the dashboard. The
[reviewed plan](https://github.com/byebyebryan/agent-observer/blob/ef623e80b7f419518df844acc9a80477289cce00/docs/maintenance/terminal-product.md#proposed-refinement-a-read-only-session-board)
records the design research. Native Codex owns conversation selection, drafts,
prompts, approvals and lifecycle. Native switching and its spike stay deferred.

### User-facing rows

Finite human CLI output keeps the shared width modes: at 100 columns and wider
it uses the four-cell table; 60–99 columns use two-line rows with a shared
left/right boundary; 32–59 columns use four-line cards; and below 32 columns it
uses stacked text with bounded wrapping. A non-TTY finite CLI has no known
width and keeps its natural full-field layout.

The dashboard keeps the four-cell table at 100 columns and wider. In the
current unpublished source preview, 32–99 columns use exactly two lines per
entry. The first line shows selection and pin markers, then the qualified
status, bold truncated title and complete right-aligned activity age. The
second uses a six-cell indent, then a profile field sized to at most 12 cells
and a left-aligned workspace. The workspace starts at the same column for every
row in that list pane. This context line is italic and remains normal weight
when selected, with the existing readable colors. With icons enabled, compact
rows show only the status shape: `●` Working, `○` Ready, `!` Blocked, `-`
Inactive, `?` Unknown,
`~` Stale and `×` Unavailable. `--icons never` shows the full qualified status
in that same geometry. The compact footer includes the selected row's full
status when it fits, and `?` lists the symbol meanings.

Compact ordinary ages reserve at least four cells on each row; qualified ages
such as Clock ahead, Unknown or Unavailable get the width they need on that
row. Their title truncates to fit while its left edge and the age's right edge
remain fixed. Human dashboard row captions omit only the literal home id
`default` (for example, `starship/default` becomes `starship`). Non-default
profile names remain visible; details and selectors keep the full identity.
Workspace uses the current cached repository root or reported directory as
before. Below 32 columns, the dashboard shows a minimum-size guide. Section and
group headings and row lines count against the dashboard page budget; exact
selection stays visible on resize. Breakpoints describe terminal cells, not a
fixed pixel size; physical fit depends on the terminal emulator and font.

Finite `sessions show` leads with title, qualified Status and activity age,
Profile, Workspace and full native ID. A diagnostics divider precedes raw
membership/runtime/phase, the complete identity, source and scope health,
reasons, paths, field leases and receiving-clock evidence. Uncertain and known
nonmember targets carry their membership qualification and never receive an
invented Working or Inactive status. Missing targets retain the honest lookup
outcome and selected-source health.

Status is a presentation summary of qualified facts, with no new producer state:

| Required current evidence | Status |
| --- | --- |
| Running runtime and working phase | Working |
| Running runtime and waiting phase | Ready |
| Running runtime and blocked phase | Blocked |
| Positively observed parked runtime | Inactive |
| A required runtime/phase fact is stale or unavailable | Stale or Unavailable |
| Unknown, unsupported, ambiguous or missing required evidence | Unknown |

Runtime qualifies phase; an old waiting phase cannot make a parked or unknown
runtime Ready. Active/recent membership does not establish work state. Source
coverage remains visible independently, including partial coverage with valid
positive row facts. Raw membership/runtime/phase and reasons remain available
in details and terminal JSON v1. Existing filters retain their fact-level
semantics. Activity order uses current native conversation activity descending,
without active/recent membership or running/parked priority. Unknown ages follow
known timestamps; full identity breaks ties. Host order uses the same recency
order within each host/profile. Explicit groups and favorite order still apply.

### Dashboard status filter

The dashboard opens its filter panel with Status. Choices use the qualified
status table above, including Unknown, Stale and Unavailable; membership or last-known facts
cannot make a row match Working, Ready or Blocked.

Choices OR within Status and AND with the existing query, source, host, profile,
membership, runtime, phase and kind filters. All statuses are initially enabled;
none means no matching rows. In the Status panel, `a` clears all when all are
selected and selects all from a partial/empty choice. Space/Enter toggles the
focused status. Reset restores all statuses and the ordinary defaults.
Current cached updates and quiet expiry recompute status matches.
Favorites bypass no filter, and a hidden selection retains its exact identity.
Unfiltered counts and watched source health remain visible with zero matches.

Dashboard status remains presentation state for that run and never enters
backend read filters. It adds no configuration field, saved-view field or
producer fact. Finite sessions CLI separately accepts repeatable, case-
insensitive `--status` values; they OR with each other and AND with other
selectors. Exact `show` bypasses them. Terminal JSON v1 adds `filters.status`
only when the user supplies the option, with canonical lowercase values; the
default JSON shape and per-row fields remain unchanged. The packaged schema
bytes do not change.

### Activity and context colors

Last active is approximate time since native conversation activity, never time
spent in the displayed status. It retains its own freshness and qualifications
independently of runtime/phase; a display tick renews no evidence. Unknown ages
stay qualified. Numeric ages use compact units without a prefix and remain
approximate activity ages. A logarithmic
truecolor fade runs from `#ffe49a` to `#819fc7` over the first 24 hours, then
holds the older-activity shade. Light dashboard themes use `#6c4b00` to
`#31527a`. The dashboard updates color on the existing age tick, including when
the formatted age is unchanged, without adding timers. Unknown, stale,
unavailable and clock-ahead ages use a neutral shade, never the newest-activity
color.

Profile is a user-facing caption for the configured home, displayed with its
host to distinguish identical profile names. Configuration keys, selectors
such as `--home`, exact namespaces and the saved `host-home` group value do not
change. A five-family blue/violet/magenta palette hashes the exact host for its family;
the exact home selects a fixed shade within that family. Host and home have
separate spans. Family and shade identity stay consistent across row order,
filters and selection. The dashboard uses a fixed softer 50% palette variant;
the finite CLI keeps its current palette, so the exact colors differ between
those views. Finite palette colors may repeat.

Workspace labels omit `repo`/`dir` prefixes: the dashboard
shows the current cached repository/worktree name, otherwise compact reported
cwd, otherwise `unknown`. Reported `/home/<user>` prefixes display as `~`
without consulting the viewing machine; full paths remain in details and JSON.
The finite CLI uses its existing cwd metadata.
Full repository/directory labels
remain in details; no-color rows retain the workspace name/path.
Dashboard workspace colors distinguish repo (`#a8d1bd` dark / `#315449` light),
directory (`#dac19d` / `#624d30`) and unknown (`#bbc2ca` / `#464f5a`). For a
directory label, the parent prefix through the last visible slash is neutral
(`#b3bdc9` dark / `#404b59` light), and the final visible component keeps the
directory color. The finite CLI retains its repo (`#55d7af` / `#005d49`),
directory (`#f0b56f` / `#804500`) and unknown (`#a9b2bb` / `#4b535e`) colors.
An expired repository falls back to reported cwd and uses directory styling.
There is no filesystem or Git discovery. Full paths remain in details, cwd has
no independent freshness lease and linked working-tree roots remain distinct.

Colors supplement text: status keeps its green/cyan/amber/red semantics, the
selected-row surface and marker stay neutral, and `?` shows a concise palette
and workspace-type legend. Explicit labels remain readable without color or
when a Rich terminal reduces truecolor to its finite palette. Piped output
retains plain labels and no ANSI sequences.
Light dashboard status colors use darker shades on selected rows. The finite
CLI honors an explicit white-background `COLORFGBG` hint ending in `7`/`15`;
otherwise its palette defaults to dark. It performs no terminal query.

The finite overview retains its ten-row bound; human `list` retains full native
IDs as secondary evidence. Piped text preserves full names and IDs without
color or truncation. JSON v1 fields and query/filter behavior remain compatible;
activity/host row order follows the recency rule above in text and JSON. Pins
and saved-view state use version 1.

### Favorites and ordering

A favorite references all five exact identity fields, independently of retained
inspection selection. With list focus, `p` pins/unpins the visible selected row
without changing selection. `P` opens Pins, where `p` removes the focused
reference even when its row is absent or hidden. Search input owns printable
`p`/`P`; Enter still opens Observer details.

Matching pins appear first in first-pinned order, with an ASCII `*` marker and
Pinned heading. Other sessions retain activity/label/host ordering and optional
host/home grouping within that remaining region. Each row appears once. Without
matching pins the existing layout remains. Section/group headings count against
the page budget; pins scroll with the list rather than reserving screen space.
Existing order/group menus preview changes, accept with Enter/Space, and restore
the original choice on Escape. Only accepted changes save.

Favorites bypass no filter, hidden kind, watched-source selection, exact-identity
admission or source-health policy. Missing favorites retain references only:
they create no synthetic session rows, member counts or native facts. Returning
exact identities regain their pin position; a same-name replacement does not.
`Pinned N in view / M saved` is separate from source and membership counts.
The Pins panel says `not in this view` without diagnosing why. Labels come only
from this invocation's admitted metadata; full identity remains inspectable.

### Optional local view state

`$XDG_STATE_HOME/agent-observer/dashboard-view.json`, falling back to
`~/.local/state/agent-observer/dashboard-view.json`, remembers version 1, ordered
exact pins and accepted sort/group values. Limits are 32 unique pins and 64 KiB;
reaching a bound refuses the edit without evicting another pin. Persist no labels,
paths, source definitions/sockets, observed facts, filters, query history,
selected row or scroll position. This is local presentation state, not a source
configuration or session cache.

Explicit startup `--sort`/`--group` wins over saved values, then defaults. Startup
overrides alone never save. A subsequent deliberate in-app edit saves the current
complete view. Filter Reset retains favorites/order/group. Dashboard-only
`--no-saved-view` skips all state-file I/O and keeps edits in memory. Finite CLI,
help, schema and configuration inspection never access this state.

Startup creates nothing. The state root must already exist and be owned by the
user without group/other write permission. New application directories use 0700;
existing owned application directories retain safe permissions without group/other
write access. Only deliberate saves create state. Reject symlinks, unsafe destinations, nonprivate
files, corrupt/unsupported/unreadable state and strict-schema violations while
preserving existing bytes. A visible warning disables persistence for that run.
Failed saves retain the in-memory choice and say it was not saved.

All filesystem work runs in an owned isolated helper, outside projection,
paint and lease processing. Startup load has a 250 ms operation deadline;
saves have one second. One save runs at a time with one pending latest snapshot.
Shutdown allows at most two seconds to drain before terminating the helper,
then joins owned cleanup independently of terminal restoration. Actual cleanup
budget misses are failures, not permission to abandon a live child. Atomic
0600 staging/replacement preserves the prior target on pre-replacement failure.
A forced kill during staging can leave a private temporary file; no cleanup
sweep removes another dashboard's staging files. Controlled timeout checks do
not guarantee interruption of arbitrary kernel-blocked filesystem calls.

Independent dashboards use last-successful-save-wins over complete views,
without merge, live reload or cross-machine synchronization. No general settings
framework, multiple boards, aliases, manual row movement, additional sort engine,
persistent filters or notifications is introduced.

Source/installed checks and controlled terminal previews qualify only the
reader's recorded scope. Ordinary use beside an independently opened Codex
TUI remains the human usefulness decision. The deferred resource, stress, soak,
native and managed boundaries above remain unchanged.
