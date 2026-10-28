# CLI and dashboard product plan

Status: **CLI released in 0.7.0a12; TUI source preview implemented and checked within the scope below**. The
[roadmap](roadmap.md#current-milestone-cli-and-dashboard-qualification) establishes the product
direction. The user selected the CLI-first P1/P2 slice under luna-goal-loop.
The [sessions guide](../guides/sessions-cli.md) documents the CLI commands and
setup. Managed reader selection is separate from collector/publisher selection.
The reviewed dashboard plan is implemented as an unreleased source preview.
Textual 8.2.8 passes the current source and installed test boundaries. The short
realistic-fleet check and normal 30-minute resource checks pass. Extended
eight-hour soak and 8,192-outcome stress testing are optional future work,
not preview acceptance gates; large-fleet optimization is deferred. Focused native evidence is
bounded to the selected cases; human acceptance, publication and deployment
remain separate. The preview does not select a deployment.

## Inspected baseline

TUI planning uses maintained main
[`e14b403`](https://github.com/byebyebryan/agent-observer/commit/e14b403bc8d878dcc2dad5144b46a21ed084ae75),
after the a12 CLI release. Work is isolated on `plan/tui-20261026`; the canonical
checkout remains on `cpu-prepared-admission`, with all other worktrees retained.

| Existing surface | Finding and consequence |
| --- | --- |
| [`cli.py`](../../agent_observer/cli.py) | Top-level list/show/doctor/snapshot/watch are direct diagnostics and can query the provider. Preserve their behavior; introduce separate product commands. |
| [`working_set_cli.py`](../../agent_observer/working_set_cli.py) | One selected host/source, active-lease filtering, diagnostic rendering and a 60-second cap. Preserve this bounded diagnostic interface. |
| [`terminal/config.py`](../../agent_observer/terminal/config.py) and [`terminal/model.py`](../../agent_observer/terminal/model.py) | Shipped private source configuration, exact identity, safe labels, vocabulary, counts, filters and ordering. Reuse these semantics. |
| [`terminal/sources.py`](../../agent_observer/terminal/sources.py) | Finite fan-in keeps streams open until settlement/deadline, freezes the report and closes them. It has no persistent retry supervisor. Repeated finite reads are not the proposed TUI lifecycle. |
| [`utility_read.py`](../../agent_observer/utility_read.py) | Demonstrates admission, receiving clocks, quiet expiry and cleanup, but drops labels/activity/field leases from its summary. Its JSON and duration are not product contracts; it has no reconnect supervisor. |
| [`mesh_working_set_read.py`](../../agent_observer/mesh_working_set_read.py) | Public facade supplies full masked member records, uncertain identities, admitted nonmembers, scope coverage and member/field/scope deadlines. Use it as the product's selection authority. |
| [`home_profiles.py`](../../agent_observer/home_profiles.py) | Explicit private local manifest: required default, maximum two profiles, labels/namespaces/sockets/source IDs. This is not a fleet/home catalog. |
| Mesh a25 SDK 1 | Public `configured_reader` binds explicit local/configured hosts and source, with `report_routes=False`. Its host watch already retries channels and emits resyncs; avoid simultaneous SDK/product retry loops. |
| [Service 4](../guides/local-service.md) | Public `frames`/`ReadCache` supports independent full-cache diagnostics without Mesh. It is not an interchangeable working-set reader. |

The reinspection uses the installed Observer a12 CLI and exact Mesh a25 pair.
A bounded cached read on 2026-10-26 selected Starship Default and Snap
Default/Work: all three sources were complete, with 14 members, 14 admitted
names and 14 optional context labels. These counts are one transient sample,
not independent native validation, an exhaustive inventory or a metadata
availability guarantee. Carbon's four-source configuration is a useful second
layout case; the application must not hardcode either fleet arrangement.

No actual titles, paths, transcripts or raw frames are retained here.
Native `name` supplies bounded
titles, falling back to `Codex <thread ID>`; no prompt/preview access is needed.
Project/workspace metadata is optional and expires independently. Title/cwd
have no independent projection field lease: describe them as admitted display
metadata, not freshly sampled native state. Never inspect remote paths/Git.

## CLI baseline and proposed dashboard entry

| Command | Outcome |
| --- | --- |
| `agent-observer` | The usual quick check; opens the configured cached sessions overview. |
| `agent-observer sessions` | Default quick overview; equivalent to `sessions overview`: source health, unfiltered counts and at most ten readable rows, with remaining count. |
| `agent-observer sessions list` | All selected current members and uncertain identity stubs, with search/filters/order; no silent row limit. |
| `agent-observer sessions show ID --host HOST --home HOME` | Full native thread ID in exactly one configured host/home; no prefix/title matching. Host/home may be omitted only when one source is selected. |
| `agent-observer sessions show --ref JSON` | Exact five-field identity; mutually exclusive with positional ID. Exact selection bypasses kind/display filters, but cannot recover rows absent from this projection. |
| `agent-observer sessions sources` | Source delivery, coverage, reasons and expected/observed home binding, even with no sessions. |
| `agent-observer sessions sources --configured` | Pure configuration inspection without Mesh imports, connections or provider queries. |
| `agent-observer sessions schema` | Packaged terminal JSON output schema without configuration or optional imports. |
| `agent-observer dashboard` | Standalone persistent source-preview TUI until quit/terminal shutdown; no default duration limit. |

Bare `agent-observer` now opens the overview; all existing explicit
direct/service/mesh/profile commands and diagnostic `working-set watch` retain
their behavior. Product reads always use explicit
working-set caches. First milestone product reads require the optional Mesh
dependency, even for a local bridge. Core and local Service 4 diagnostics stay
usable without Mesh/Textual. Do not invent a Mesh-free working-set reader by
filtering a full inventory; a separate pure local facade is not a prerequisite.

Overview columns: `SESSION`, optional `CONTEXT` in wider terminals, `HOST/HOME`,
`MEMBER`, `RUNTIME`, `PHASE` and `ACTIVITY`. Full IDs remain in list/details.
Title is primary; optional admitted project key or
workspace/cwd basename is labeled context, never identity. Use `Codex <ID>`
when no useful name exists. Details expose full identity/name, optional path,
metadata issues, exact activity timestamp, independent fact health/reasons,
scope coverage and relevant clock/lease information. Escape terminal, bidi and
markup controls in metadata; never interpret it as commands or terminal links.
Interactive styling uses standard Unicode status glyphs, a thin header rule,
cyan navigation, green current work/complete coverage, amber uncertainty and
red unavailable sources. State words remain visible. `--icons auto|always|never`
controls ornaments separately from color, with plain pipe/basic-terminal fallbacks
and no special font or new runtime dependency.

For example, using invented labels:

```text
Agent Observer   7 sessions · 2 uncertain
Coverage: 1/3 sources complete; 1 partial/stale/warming; 1 unavailable/blocked
Sources: laptop/Default
server/Work: partial; coverage is incomplete; see sessions sources
server/Default: unavailable; connection lost; current facts revoked

SESSION              HOST/HOME        MEMBER     RUNTIME  PHASE    ACTIVITY
CLI planning         laptop/Default   active     running  working  ~2m
Renderer review      server/Work      active     running  waiting  ~8m
Release notes        laptop/Default   recent     parked   -        ~1h
Codex <native ID>    server/Work      uncertain  unknown  unknown  unknown
```

Source health precedes rows and survives filtering. Counts distinguish selected
members, uncertainty, known nonmembers, hidden kinds and displayed matches.
Narrow text wraps labels/secondary columns; piped text has no width truncation.

### Common semantics and defaults

- Membership is independent of native state. `active` requires an unexpired
  active branch lease. An otherwise admitted recent member displays `recent`:
  active is not currently proved, not proved false. Uncertain/nonmember outcomes
  come only from the facade. Stored `running` does not match an active filter.
- Runtime is running/parked/unknown. Running phase is working/waiting/blocked/
  unknown; parked has no applicable phase. Waiting does not imply a response is
  required. Show approval/question reasons only when admitted. Expired facts
  display `unknown (stale)`; last-known values are details, never current counts.
- Repeatable selectors: `--source`, `--host`, `--home`, `--membership`
  (active/recent/uncertain/nonmember), `--runtime`, `--phase`, `--query`. OR
  within a selector, AND across selectors. Uncertain rows cannot match positive
  runtime/phase filters. Default shows members and uncertain identities;
  nonmembers remain counted and explicitly inspectable.
- Default hides confirmed child/system kinds only; unknown kind stays visible.
  Add `--include-children`/`--include-system`. Search is case-insensitive literal
  substring over admitted name/project/path, host/home and full native ID, at
  most 256 characters. No regex, content search or persisted search history.
- Default flat list: active first, other members second, uncertainty last;
  within each class, current native activity descending, unknown activity last,
  full identity tuple as tie-breaker. Share `--sort activity|label|host` and
  `--group none|host-home` across CLI/TUI. Label sort uses casefolded label then
  identity; host sort uses host/home then the default activity order.
- Activity uses native `activity.at`. Relative wall-clock age is explicitly
  approximate; show clock-ahead/unknown qualifications and exact timestamp in
  details. Never use display age, thread update time, title changes, polling
  or transport liveness for membership/lease arithmetic. Preserve clock
  discontinuity; reconnect is not a repair for unchanged native activity.

`complete-empty` requires all selected sources to have current admitted
baselines, present complete unexpired scopes and no members, uncertainty or
known nonmembers. Filtering, hidden kinds, missing scopes, capacity limits and
empty configuration cannot establish it. With only admitted nonmembers, say
`0 qualifying members; N known nonmembers`. A filter result is `0 matches`,
with unfiltered counts and source health still visible.

### Scripting and exits

Use `--format text|json`, default text. Human spacing is not a scripting
contract. Piped text has no ANSI/cursor control or pager. Support
`--color auto|always|never`, `TERM=dumb` and nonempty `NO_COLOR`; `NO_COLOR`
takes precedence over always. Reuse the bounded stdout-write approach with
a five-second backpressure deadline.

JSON is one finite document: the published terminal output contract,
independent of API 4/working-set v1 and the utility's diagnostic JSON.
The packaged schema and fixtures define this envelope:

| Fields | Meaning |
| --- | --- |
| `interface: "agent-observer.terminal"`, `version: 1` | Additive fields allowed; incompatible change requires another version. |
| `generatedAt`, `selection`, `filters`, `totals` | Point-in-time generation, resolved explicit sources and separate unfiltered/displayed counts. Generation renews no evidence. |
| `sources[]` | Consumer source ID, host/home, Mesh source, expected/observed namespace, baseline/delivery, scope coverage, reasons, sample times and receiving-clock context. |
| `sessions[]` | Current member identity/provenance, selected display metadata, membership branches, independently qualified facts and activity. |
| `uncertain[]`, `nonmembers[]` | Explicit exact-identity outcomes and bounded reasons, not current session-state rows. |
| `result`, `error` | Complete/degraded/not-found and optional bounded code; no raw SSH/provider payload. |

Deadline exports carry receiving boot/time-namespace binding and no continuing
authority after read closure; the report is not a live lease transfer. No JSON
watch/event-replay contract is proposed. Diagnostics use stderr. Invalid
invocation may fail before a JSON envelope exists.

| Exit | Meaning |
| --- | --- |
| 0 | Finite read has complete current selected coverage, including zero matches; dashboard explicit quit returns 0 regardless of feed health. |
| 1 | Exact show target unavailable within fully observed selected projection; this does not prove deletion or absence from history. |
| 2 | Invalid arguments/configuration, empty source selection or missing dependency, with actionable stderr explanation. |
| 3 | Report has partial/stale/unavailable/unsupported coverage, blocked source, timeout or capacity failure, including all sources unavailable. Unresolved show uses this rather than not-found. |
| 130 / 143 | Interrupt / termination after owned cleanup and terminal restoration. |
| 141 | Closed output pipe, without traceback. Other output failures use exit 3. |

Finite reads wait for the first settled result from each source or a shared
ten-second total deadline (`--timeout` 1-60 seconds), then close all streams.
They do not print a final revoked line over the report. Preserve per-source
sample times: this is not an atomic fleet snapshot. Reconnect cannot extend
the finite deadline.

## Source/home configuration

Use a separate private consumer file at
`$XDG_CONFIG_HOME/agent-observer/terminal.toml` (fallback
`~/.config/agent-observer/terminal.toml`), overridden by `--config`. Missing
config produces setup guidance, not automatic home/host discovery.

```toml
version = 1
default_sources = ["workstation-default"]

[[sources]]
id = "workstation-default"
host = "workstation"
home = "default"
label = "Default"
mesh_source = "agent_working_set"
scope = "local"
socket = "/run/user/1000/mesh-plus-agent-working-set/read.sock"
namespace = "sha256:<replace with full namespace reported by profiles>"
window_hours = 72
```

Replace the namespace placeholder before use. Remote entries use `scope =
"hosts"`, with a host in the public Mesh catalog; the configured directional
route owns remote delivery. The socket field affects local selection only.
Do not parse/rewrite SSH or chezmoi files to discover remote homes. Remote
home labels/source IDs/namespaces are explicit configuration.

Reuse `profiles --config ... --json` or `load_home_profiles` for pure local route
inspection when preparing entries; do not change the producer manifest. The
existing Mesh codec binds host/source/window but not an expected home namespace,
as recorded in
[`test_home_profile_routes.py`](../../tests/test_home_profile_routes.py).
Require expected namespace and check every scope/identity before assigning a
home label. Mismatch blocks the source and revokes its rows. Do not relabel a
different home or reset namespace automatically on publisher restart.

Validate version, exact keys, bounded labels/IDs, namespace and absolute local
socket before I/O. Follow the profile loader's owner/private-regular-file/
no-symlink policy and 64 KiB limit. Require unique source IDs and host/home
pairs; reject duplicate host/Mesh-source routes. Limit to eight sources.
Select explicitly listed `default_sources` unless source/host/home selectors
choose other configured entries. Unknown selectors or zero selection fail.

Optional per-entry `max_identities` and `max_payload_mib` reserve client capacity
(defaults 1,024 and 4). Validate positive integers, the existing per-source
contract bound and aggregate limits before connecting. This is a visible client
capacity limit, not permission to request a smaller native inventory.

`--socket`/`--window-hours` overrides require exactly one selected source;
socket overrides require local scope. Window selection must match the fixed
publisher window and never reconfigures it. Do not use ambient `CODEX_HOME`
to redirect a cached source. Config contains no credentials/SSH commands and
is frozen during an invocation: no hot-added homes/hosts or automatic routes.

## Dashboard experience

`agent-observer dashboard` provides one persistent session list, source health
always visible, and details opened on demand. Bare `agent-observer` continues
to be the quick finite CLI. The implementation uses this reviewed default;
an always-visible split or host board is not part of the first TUI.

The first screen answers three questions: what is currently known, which
session matters, and which sources cannot be trusted right now. Keep technical
reasons in details instead of filling every row with diagnostics. Use the CLI's
state vocabulary, standard glyphs and restrained color; no special font,
flashing indicators, continuously animated spinner or clock seconds in the header.

An illustrative wide list uses invented labels and counts:

```text
◈ Agent Observer                                  9 members · 1 uncertain
Sources  laptop/Default complete   server/Work partial   server/Default retry 8s
Watching 3 sources   Find: —   Filters: default   Order: activity   Group: none
────────────────────────────────────────────────────────────────────────────
  SESSION                 HOST / HOME       MEMBER     RUNTIME / PHASE   AGE
> CLI planning            laptop / Default  active     running / working  ~2m
  Renderer review         server / Work     active     running / waiting  ~8m
  Release notes           laptop / Default  recent     parked              ~1h
  Codex <native ID>       server / Work     uncertain  unknown          unknown

4 matches · 6 hidden by kind/filter · coverage incomplete
↑↓ move   Enter details   / search   f filters   s sources   ? help   q quit
```

The application derives row limits and columns from available cells; this
sketch does not prescribe fixed spacing. `AGE` means approximate native activity
age, not lease age, delivery age or time since UI update. Counts and reasons
come from the shared model. With incomplete sources, totals describe observed
qualified outcomes rather than an exhaustive fleet size.

### Layout and details

- Default: use the full available list width. At least 80x24 gives single-line
  rows, prioritizing readable session names. At >=140 columns add a Repo
  column and separate runtime/phase columns; this threshold is independent
  of the split-details threshold below. Repo is the basename of the current
  cached Git working-tree root, not a project label or guessed cwd basename.
  A linked worktree keeps its own directory name. Current non-Git workspaces
  show none; missing or noncurrent workspace data stays explicit.
- Enter opens details. At 120x30 or wider it opens a side panel; below that it
  opens a full-screen detail view. Details stay closed initially at every width.
  Resize preserves whether details are open, their target and scroll position.
- With width >=60 and height >=16, but width <80 or height <24, use compact
  two-line rows, shorter source summaries and separate details/source views.
  With width <60 or height <16 show resize guidance, overall health and
  quit/help keys. Readers continue to expire evidence and recover independently.
- Header and footer stay present in list, details, source view and filter/help
  overlays. A long source ribbon collapses to a summary with `s sources`;
  incomplete/failed source counts remain visible, including with zero matches.
- Color follows the CLI: cyan navigation, green working/complete, cyan waiting,
  amber blocked/unknown/partial, red unavailable. Use literal state words,
  a `>` selection marker and a restrained theme-aware selection surface. Keep
  strong bold/reverse focus without color. Ordinary host/context text is quieter
  than the session name; section headings separate navigation from state.
  Icons follow `--icons auto|always|never`. Default ornaments require no Nerd Font.
- Use safe literal text, including Textual/Rich markup-like strings. Sanitize
  terminal/bidi controls using shared metadata rules; disable metadata markup,
  automatic links and terminal hyperlink/clipboard actions.

Details have a readable summary first: full name, host/home, membership,
runtime/phase with independent health, and qualified native activity time.
The workspace section puts the full reported working directory and current
cached repository root first, then relative repository path and independent
project context. Source health precedes the technical evidence. Sectioned
details retain the full shared Git directory, five-field identity, source ID, bounded reasons,
last-known values explicitly marked noncurrent, expected/observed namespace,
scope coverage and receiving-clock/deadline context. Show admitted path/project
metadata as optional context without filesystem/Git access. Details are not a
transcript, event log or native terminal. Repository data shares the existing
workspace lease and is carried only in the dashboard's internal projection;
the finite sessions CLI and terminal JSON v1 output/schema stay unchanged.
Reported cwd has no separate field lease and must not imply a fresh native cwd
sample. The dashboard does no Git or filesystem discovery.

The top bar identifies the view and totals; the toolbar emphasizes active
search/filter settings. A short contextual footer shows common actions, while
`?` groups the complete keyboard guide. These changes add no modes or keys.
Filter dimensions are clearly identified, and friendly source labels still
toggle exact configured source IDs.

The source view lists every watched source, including empty and blocked ones:
host/home, delivery, baseline, coverage, latest frame age, error explanation and
bounded original reason code, retry countdown or manual-correction requirement.
Frame age is delivery information and never proof of native fact freshness.

### Keys, focus and stable selection

| Key | Action |
| --- | --- |
| Up/Down or j/k; PageUp/PageDown; Home/End | Move through session rows; group headings are not selectable. |
| Enter / Escape | Open details / close the top panel or cancel an input edit. |
| Tab / Shift-Tab | Move focus within the open view; with split details, switch list/detail focus. |
| `/` | Edit literal search, 150 ms debounce; Escape restores the pre-edit query. |
| `f` | Edit source/host/home/membership/runtime/phase/kind display filters; show active filters and Reset. |
| `o` / `g` | Choose activity/label/host ordering or none/host-home grouping. |
| `s` | Open source status and select a source for inspection. |
| `r` | Retry the focused failed source; from a session, use its source. Healthy sources are left running. |
| Escape on the main list | Clear the pinned session selection. It does not silently reset filters. |
| `?` / `q` / Ctrl-C | Help / explicit quit / interrupt. |

Printable keys belong to a focused text input, including q/j/k. Dialog bindings
precede list bindings; details/source views scroll when focused. Ctrl-C remains
a global interrupt. The footer reflects the current focus. Mouse selection and
scrolling may work through standard widgets, but every task has a keyboard path.

Reuse CLI ordering: active first, recent next, uncertain last; current native
activity descending, unknown activity last, exact identity as tie-breaker.
Default hides confirmed child/system kinds, while unknown kind stays visible.
Default membership is members plus uncertainty; known nonmembers are counted
and explicitly inspectable. Search and filters retain CLI OR-within/AND-across
semantics. `/` edits one search term; applying it replaces the query term set,
while Escape restores the original terms. Search history is not persisted.

Selection is the exact five-field identity, with source ID as provenance.
Choose the first visible row once on initial population, then preserve selection
through inserts, reorders, grouping, paging and resize. Do not let widget cursor
indexes become action/selection authority.

If a filter hides the selection, show `selected session hidden by filters` and
keep its detail target. If it leaves the projection or the source is revoked,
keep only one pinned identity and sanitized label, marked `not currently
available`; discard current facts. Returning fresh evidence for that exact
identity can restore it. Choosing another row or clearing selection drops the
placeholder. Arrow navigation is an explicit choice of a visible row; a
background update never silently chooses a neighbor. Duplicate labels/native
IDs on different hosts/homes remain distinct. Conflicting claims for the same
full identity block all claimants, following the CLI model.

### Source selection and command behavior

Reuse private `terminal.toml` version 1 and the CLI source/host/home selectors.
Startup resolves an immutable watched set, ordinarily `default_sources`.
Repeatable filters, kind switches, sorting/grouping, one-source socket/window
overrides and color/icon settings follow the existing CLI rules. Do not add
fleet-specific defaults, configuration writes, automatic discovery or saved UI
preferences in the first TUI.

In-app source/host/home filters only narrow presentation within that watched
set. They do not unsubscribe healthy feeds, change the denominator for overall
coverage or add another configured source. Show `Watching N sources` separately
from the view filter. To watch a different set, restart with explicit selectors;
`r` retries the same selected binding and does not reload terminal.toml or adopt
a new namespace/topology.

Dashboard accepts `--connect-timeout` (default 15 seconds, range 1-60) for each
setup/baseline attempt. It has no finite lifetime or CLI `--timeout`, `--format`
or JSON watch option. `--help` is pure and works without optional imports.
Validate arguments/config/dependencies and terminal suitability before starting
readers or entering terminal mode. Require interactive stdin/stdout and a
cursor-capable terminal; reject pipes and TERM=dumb with guidance to
`sessions list`. `NO_COLOR` wins over `--color always`, removing foreground
and background colors while retaining necessary cursor controls and focus.

Explicit quit returns 0 even with unavailable sources. Setup/config/dependency
errors return 2; unrecoverable internal/output/cleanup failures return 3.
Ctrl-C returns 130, SIGTERM 143 and terminal hangup 129 after owned cleanup.
Source failure remains visible in the running app rather than terminating it.

## Persistent read lifecycle

Use a dedicated persistent supervisor over public cached facades. Do not spawn
the CLI repeatedly, parse rendered output, reread native history or invoke a
provider. The finite CLI's frozen report is not a continuing lease transfer.
No demonstrated gap requires a producer, transport or frozen-schema change.

One worker per configured host/Mesh-source pair owns a single attempt: profile,
configured reader, request ID, prepared guard, pending `anext` and receiving
clock binding. Guard calls are serialized. A source supervisor replaces that
attempt only after revocation and cleanup. Other sources continue independently.

```text
connecting -> warming -> observing (coverage may be complete, partial or stale)
     |           |          |
     +-----------+----------+-> revoked -> retry-wait -> connecting
                                  |
                                  +-> blocked until explicit retry
any state -> closed on shutdown
```

Lifecycle and evidence health are separate: a connected feed may be incomplete,
and a reconnecting feed is not a complete empty source. Reuse the CLI's strict
empty-state/counting rules. Never manufacture uncertain/nonmember outcomes
from client-side absence or expiry.

| Condition | Consumer response |
| --- | --- |
| Quiet stream / lease deadline | Schedule the next public receiving-clock expiry and call `read(now, clock)` when due. A shared lightweight CLOCK_BOOTTIME check, at most 100 ms apart, detects crossed deadlines/suspend without rebuilding every source. Expire member, field and scope authority independently. |
| EOF, transport failure, gap/resync, publisher/stream incarnation change | Publish revocation before considering replacement positives; close the attempt, then retry with a fresh baseline/proof. |
| Native field stale or clock/coverage uncertainty while delivery remains valid | Keep the feed observing with explicit stale/partial facts. Reconnecting must not pretend to repair unchanged native evidence. |
| Namespace/window/binding/contract/order/capacity failure; identity conflict | Revoke and block with an actionable reason. Explicit retry uses the same expected binding. |
| Catalog scope/revision change | Revoke and require explicit retry of the same configured source; do not silently adopt new authority or expand routes. |
| Temporary catalog/delivery unavailability | Revoke, retain the bounded reason and retry. |
| Shutdown/cancellation | Revoke, cancel pending work, disconnect guard and close only owned streams/children. |

The existing Mesh a25 SDK already retries channels (250 ms increasing to 30 s)
and emits resyncs. On the first observable failure/resync, close its iterator
and await owned cleanup before the product retries. This leaves one continuing
retry owner rather than nested supervisors. Keep `report_routes=False`, the
existing ten-second Agent proof cadence and the selected complete-view delivery.
UI expiry checks request no extra proofs/native samples and do not enable
view-feed, delta-sync or CPU research paths.

Product retries use 1, 2, 4, 8, 16, then 30 seconds, jittered to 80-100% of the
step. Reset after 60 seconds of stable admitted delivery. Permit four concurrent
setups and at most one new setup start per second, including manual retries.
The attempt timeout starts when a setup slot is granted, and covers reader
resolution through first settled baseline; queued sources remain visibly
connecting. Manual retry is throttled to one/second, never duplicates an active
attempt and never resets healthy peers. An attempt that has not finished
cleanup still owns its slot/resources and cannot be replaced. Cleanup failure
blocks that source; timeout/cancellation alone is not proof that its work ended.

Increment a source epoch on revocation. Admission, projection and UI handoff
carry that epoch; stale tasks/messages cannot restore an older positive.
Always require a new admitted baseline/proof before granting positives. Suspend
and a receiving-clock-domain change require revalidation before the first
resumed render; wall-clock changes alone never renew membership/activity.

Keep one logical admitted generation and one latest UI replacement/source,
plus a bounded candidate during replacement. Admit and order-check every wire
frame before presentation coalescing. Revocation advances the epoch and clears
pending positives; it is not an ordinary message that an older update can
replace. The UI reevaluates validity before rendering and after a scheduling
stall. Normal expiry revocation must reach the visible screen within 250 ms;
prioritize it over cosmetic repaint throttling. Time spent on a blocked event
loop is measured, not silently excluded from latency reports.

Use one coalesced dirty notification for the latest source slots, rather than
posting one framework message per incoming frame. Rebuilding the report must
not accumulate obsolete models or notifications behind a slow paint.

Compute the next expiry from the public member branch/membership and field
deadlines, complete-scope deadlines and all receiving receipt deadlines in the
facade context. Use only future receiving-clock values, never native-origin
support clocks or uncertain-stub horizons. The public facade still decides
membership and field masking at the boundary; the scheduler does not reproduce
domain arithmetic. Empty scopes and admitted negatives require deadlines too.

Evaluate/project on admitted state replacements, due expiry, or receiving-clock
revalidation. Admit unchanged heartbeats without repeating the whole projection.
Before any paint, check the source epoch and next deadline; if due, evaluate
the public facade first. Use one shared clock wake, not a full read per source
every UI tick. This schedules existing public semantics and changes no facade,
producer or transport contract.

Reuse model/config functions without changing finite JSON interface 1. The
current model uses per-source `capture_boottime_ms` and the finite reader
freezes it before closing streams: every TUI projection must instead receive a
fresh public-facade evaluation and capture clock. Rebuilding a report from an
old detached read at a later wall-clock time is insufficient.

### Output and shutdown ownership

An outer async runner owns the source supervisors and joins cleanup after
`App.run_async()` restores terminal mode. Textual workers may own UI-only work,
but not SDK streams or their final cleanup. Repeated cancellation must not
interrupt the owned join or create a second attempt while the first is closing.
Start cleanup on quit/signal immediately; let UI restoration proceed independently
and then inspect every worker/child result. A cleanup timeout fails acceptance
and exit status; it does not justify abandoning a still-live owned handle.

The stock Textual Linux output path is not sufficient proof of bounded output:
its 30-item writer queue blocks producers when full, and its close joins the
writer. Capping cosmetic repaints does not keep the event loop responsive to a
terminal that stops draining. The source preview uses a pinned Linux output
adapter through the documented `App(driver_class=...)`/Driver lifecycle boundary:

- Bound encoded pending output and each accepted write to 512 KiB. Preserve
  byte order; coalesce model updates before encoding, never discard arbitrary
  terminal diffs or partial escape sequences after encoding.
- Use owned output resources with nonblocking/deadline-aware draining; do not
  alter blocking flags on the inherited shared terminal file description.
- Two seconds without drain progress, capacity overflow, closed output or
  writer failure becomes a bounded output error and exit 3. Restore termios
  independently, revoke readers and join owned cleanup. No blocked queue put,
  unbounded writer join or unpublished private-field monkeypatch is acceptable.
- Verify Linux input, resize, color, signals and restoration through this
  adapter on the pinned framework. If a future change makes the public
  extension boundary fail the gate, revisit the framework before proceeding.

Visible-paint latency is measured on a draining terminal. A stopped output sink
cannot receive a revocation or alternate-screen reset: report the output failure
and terminal-flag restoration separately, and require a fresh valid model before
any resumed paint. Do not present this as successful screen restoration. Keep
stalls in the performance report, including their duration and failed threshold.

## Resource policy and acceptance targets

The following are acceptance targets, not measurements or guaranteed performance.
Confirm feasibility before polishing the UI. If a gate fails, report the owning
cost and revise the implementation/plan explicitly; do not weaken evidence or
silently enable another transport.

| Area | Proposed bound and proof |
| --- | --- |
| Sources/model | Reuse at most eight sources, 4,096 identities/source, aggregate 8,192 outcomes and 32 MiB encoded admitted payload. Reserve configured shares before I/O; defaults 1,024 identities/4 MiB per source. Include uncertainty/nonmembers/support, not only displayed rows. These are admission limits, not qualified fleet capacity, predecode or peak-RSS guarantees; account for SDK buffers/candidate copies separately. |
| Over capacity | Revoke/block the affected generation visibly. Do not truncate inventory silently, choose winners by admission order or report complete coverage. Other reserved sources remain usable. |
| UI work | At most four cosmetic repaints/second and one age-only update/second; unchanged heartbeats do not rebuild/repaint the table. Turn animations off. Materialize at most 200 list rows/page; filtering/counts span all accepted rows. Paging preserves exact selection. |
| Queues/history | One pending stream read/source and one latest UI replacement/source; bounded epoch/reason/retry state, no event history or disk session cache. Verify SDK/task/child cleanup rather than assuming it. |
| Output | At most 512 KiB pending encoded output; a full/stalled sink must not block the model/input loop. Fail after two seconds without drain progress and verify termios restoration plus bounded owned cleanup. |
| Normal quiet run | Three sources x 100 identities, 120x40, two-minute warmup then 30 minutes: client plus owned child CPU averages <=5% of one core provisionally; combined RSS <=192 MiB. Report existing producer cost separately. The user relaxed the original 2% target and deferred read-path optimization. |
| Optional extended run | Eight hours after warmup: RSS growth <=16 MiB; no growing task/FD/child counts or retained old generations. Include source failure/recovery. This is deferred testing, not a preview gate; reopen for a suspected leak or a concrete stronger uptime requirement. The completed normal resource runs and controlled recovery checks qualify the current preview scope. |
| Practical preview | Short 20-second installed-dashboard check of the actual configured cached fleet. Verify current projection, source health, matching/rendered counts, clean exit and terminal restoration. Reuse the existing controlled installed update, key/resize, expiry and disconnect/fresh-baseline recovery results; the real-fleet snapshot does not reproduce those transitions or establish sustained performance. Normal UI update p95 remains <=250 ms at the timing boundary recorded below. The former eight-source/8,192-session stress gate is deferred with optimization; it is not required for this preview. |
| Interaction | Resize/key-to-visible response p95 <=100 ms at normal load; measure real PTYs at 120x40, 80x24, 60x16 and 40x10 guidance. |
| Recovery | Warming/source UI within 500 ms independently of setup. Controlled available source baseline within five seconds of an attempt starting, plus at most 30 seconds backoff and the documented global start queue. Partial native coverage stays partial. |
| Outage/churn | 100 controlled disconnect/recovery cycles leave task/FD/child counts at steady state. One failed feed never stops healthy siblings; recovery requires a fresh baseline. The extended ten-minute outage is part of optional soak testing, not an additional preview gate. |
| Exit | Normal terminal mode restored within two seconds of quit/interrupt; all owned reader cleanup completes within five seconds. No publisher/provider or existing native session is stopped. |

State generation, guard evaluation, filtering/sort, framework rendering and
owned SSH work need separate timings so a slow path has an identifiable owner.
Record host/CPU/interpreter, terminal dimensions and exact package/dependency
bytes. A deterministic fixture quiet run establishes a reproducible CPU/RSS
baseline; a separate real cached-fleet run proves delivery behavior. Neither
is independent native classification evidence.

## T1 implementation checkpoint

The feature branch now has a persistent consumer in
[`terminal/watch.py`](../../agent_observer/terminal/watch.py) and the bounded
Linux driver in
[`terminal/dashboard_output.py`](../../agent_observer/terminal/dashboard_output.py).
These foundations now support the dashboard command and source-preview UI
described below. They are not a shipped TUI or an accepted installed/deployment
selection.

The reader uses the existing public admitted facade, a single lightweight clock
wake, exported receiving deadlines and fresh guards per recovered attempt.
Tests cover wrong namespace/capacity, quiet expiry, receiver clock changes,
identity conflicts, healthy siblings, no reproject on unchanged heartbeat,
and repeated cancellation during owned cleanup. Controlled wire-loss churn
closes only the owned fixture channels, then reconnects to a fresh baseline.
The normal source suite uses three cycles; qualification explicitly sets
`AO_DASHBOARD_CHURN_CYCLES=100`. This is a test-fixture control, not product policy.

The driver uses a fixed FIFO byte ring and a separate nonblocking file
description, retaining Textual's normal input/resize/termios implementation.
Nine focused PTY tests passed on Python 3.11/3.14, including inherited descriptor
flags, stalled/broken output, UTF-8 order, real two-second stall expiry and a
controlled wake-fd close/reuse race. Non-TTY or mismatched stderr is rejected
before raw mode. Future command preflight must diagnose this requirement too.

The first separate-process producer/consumer measurements failed the CPU gate
with three sources x100 identities: 5.38% of one core on Python 3.11.17 and
4.95% on Python 3.14.8, over 60 measured seconds after short warmup. Both kept
all 300 members complete, used about 46.4 MiB RSS and closed in about 6 ms.
These are early failure checkpoints, not the required 30-minute resource passes
or an optional extended-soak pass.
Profiling attributes most remaining work to existing schema/native admission
validation; the consumer is no longer projecting every clock tick. Do not skip
validation, change proof cadence, select a dark research path or silently raise
the acceptance target. The user subsequently authorized a provisional 5% CPU
target and deferred read-path optimization so the main UI can proceed. The
earlier measurements straddle that revised target: they are not a sustained
pass. Measure the complete dashboard at T3 and report any remaining miss.
The fixed-frame compiler experiment remains unadopted; no producer or SDK
change is part of this TUI implementation.

Use `scripts/check --require-working-set-mesh --require-dashboard` to require
both optional stacks; the dashboard gate locks the qualification framework to
Textual 8.2.8. The optional `dashboard` extra does not import Textual into the
finite CLI or core. `scripts/check-dashboard-resources` measures an explicit
cached consumer; `tests/dashboard_fixtures.py` supplies separate-process
invented sources without native provider calls. Record source/package bytes
and keep fixture producer CPU separate from consumer/owned-child CPU.

## T2 source-preview checkpoint

The branch now implements `agent-observer dashboard`, the shared CLI selectors,
full-list default, adaptive details, source view, search/filters, ordering and
grouping, stable identity selection, keyboard help and guidance layouts. The
outer runner starts revocation/cleanup on quit independently of framework
restoration. It shields its owned app/read joins from repeated cancellation;
output failure remains explicit even alongside another cleanup failure.

Controlled tests exercise fresh-projection fences on paint, age updates,
resize/resume and identity restoration, including an admitted replacement
whose display values stay unchanged. List rows retain their widgets, and
selection changes repaint only the affected rows. Long identity/evidence
fields wrap in details rather than losing their suffixes to list ellipses.

The frozen T5 checkpoint passed 1,285 source tests on each of Python 3.11.17
and 3.14.8, with strict paired Mesh and dashboard checks enabled. The source-preview wheel passed
all eight core/Mesh/dashboard/paired installation variants; the paired installs
each passed 85 dashboard tests without skips. Inherited clipboard and URL-opening
hooks are disabled, including search-input cut shortcuts. This unreleased wheel
retains a12 metadata and is distinct from the immutable published a12 artifact.

Actual installed-CLI PTY probes used three invented sources x100 identities,
100 navigation inputs paced over about 25 seconds, details/source/search, and
120x40/80x24/60x16/40x10 resize transitions. Key-to-visible p95 was 13-33 ms;
resize responses were 21-60 ms. The no-color probe emitted no foreground/background
SGR, printable q/j/k stayed in search, and explicit quit restored terminal flags.
Real cached-fleet checks displayed all three configured host/home sources.
Metadata-only independent native RPC comparisons matched three selected local
identities and their runtime/phase/activity evidence. These are bounded consumer
and selected native comparisons, not remote classification or user acceptance.

Fixed 30-minute measurements after two minutes of warmup retained all 300
outcomes and restored the terminal. The two frozen candidates have different
measurement boundaries:

| Candidate and measured boundary | Python 3.11 CPU | Python 3.14 CPU | Peak RSS |
| --- | --- | --- | --- |
| T5 dashboard with sampler/receipt work in the consumer | 5.14%, failed | 4.79%, passed | 63-66 MiB |
| T6 public CLI with an external sampler and no in-process probe | 5.16%, failed | 4.93%, passed | 64-67 MiB |

The T6 public CLI had no observed owned child births, kept every visible
coverage check complete, and passed explicit quit and OS SIGINT with terminal
reset and flags restored. External sampler CPU was reported separately and
never subtracted. The small Python 3.11 miss therefore remains present with
sampler work outside the consumer; it is not explained by the original
in-process measurement overhead. The limit remains 5%, and read-path optimization
remains deferred. The following expiry/shutdown corrections require fresh
qualification of their own artifact; these earlier receipts do not qualify it.

T5 also completed eight measured hours on Python 3.14: 4.93% CPU, about 70 MiB
peak RSS and 3.28 MiB growth. The ten-minute outage had one loss and one fresh
recovery, with both siblings continuously complete. Recovery occurred about
24 seconds after the listener returned, within the configured retry bound.
Terminal restoration and all owned cleanup passed. The original checker failed
the run because task minima changed from 75 to 76; the only census difference
was `async_generator_asend` changing from two to three. That failed receipt is
retained and is not retroactively accepted.

A separate controlled diagnostic reproduced a live pending-read count of
three, then two while a completed read awaited its owner's rearm, then three
again, with no unowned read tasks. The checker now retains raw counts and
compares persistent task counts separately from these read phases. It enforces
one live waiter of each known read layer per selected source at every sample;
extra waiters still fail. This correction and the frontend priority fix below
require fresh qualification of the corrected candidate.

The 8,192-outcome diagnostic did not retain complete coverage: sources timed out
or reported gaps. A reader-only probe reproduced the failures; one source with
1,024 outcomes established and retained a baseline. Independent fixture publisher
processes did not establish complete aggregate coverage either. These results do
not qualify capacity, even though the observed consumer RSS stayed below 768 MiB.
The literal Mesh `timeout`/`gap` reasons do not identify a single failing layer.
They are distinct from Observer's `baseline_timeout`, and observed frame sizes
were below the reserved limits. The configured consumer facade exposes no
setting for Mesh's internal I/O/handshake deadlines or queue policy. Raising the
dashboard connect timeout is not a demonstrated fix. The owning read/producer
boundary needs source-specific investigation before any later large-fleet
capacity claim. That stress qualification is now deferred by the user; this
preview does not select a different SDK, transport or inventory fallback.

Process suspend/resume review found that the inherited suspend path closed the
owned output pump permanently, while raw stop/continue recaptured already-raw
terminal flags. The driver correction retains one bounded FIFO across job-control
suspension, preserves the original flags and input/writer ownership, and handles
job-control callbacks on the event loop. The drain watchdog excludes intentional
job-control suspension; ordinary stalls still fail within the configured bound.
The driver drains the terminal reset before a job-control stop; a two-second
pre-stop drain failure exits with error 3 while leaving the process runnable.
PTY checks cover repeated job-control and raw stops, queued output, continued
rendering, signal-handler restoration and final terminal/thread/FD cleanup.
Process-pause evidence does not establish an actual machine sleep/wake cycle;
controlled receiving-clock tests cover the separate expiry-clock behavior.

On the corrected installed wheel, each interpreter passed 100 serialized
metadata-update samples at the three-source/300-outcome workload. First admitted
frame to visible PTY text p95 was 119 ms on Python 3.11 and 170 ms on 3.14.
This boundary starts after SDK and domain-guard admission and includes domain
read/model/render work; fixture acceptance to visible text p95 was 659-711 ms,
including publisher and delivery work. Both are retained rather than treating
the UI measurement as an end-to-end native-state latency guarantee.
Each process was stopped through job control for 27.5 seconds against 25-second
fixture leases. Degraded state was visible within 35 ms of continue, before any
fresh fixture writes; fresh evidence then restored all 300 outcomes and complete
baselines. Both exited normally with terminal flags restored and owned fixture
processes removed. Raw stop bypasses pre-stop drain and does not pause the active
output watchdog; it is separate from the supported job-control queue proof.

A subsequent 25-trial UI-only PTY probe revoked a source immediately after a
fresh cosmetic projection. T5 queued that revocation: p95 was 240 ms and the
maximum was 262 ms. That leaves insufficient margin for quiet-lease detection
under the explicit expiry bound. The corrected reader marks crossed receiving
deadlines independently of ordinary revisions; the UI cancels cosmetic timers
and paints revoked generations or due leases immediately. The deadline marker
remains latched if a not-yet-painted frame shortened a lease and the next read
has already replaced that deadline. Ordinary metadata changes remain throttled.

The real public-cache expiry probe exposed another frontend delay: the admitted
projection had withdrawn authority before the screen updated, while framework
timer dispatch and widget removal/remount pushed visible withdrawal past 250 ms.
The UI now hides revoked content and paints explicit uncertainty synchronously
before waiting for that framework work. A fresh fenced projection can update
source health immediately; content becomes visible again only after the final
projection fence. The pending view contains only fixed guidance/help, so a
background report replacement during unmount cannot introduce unfenced facts.
Input-only changes retain their current content rather than withdrawing authority.
The clock worker now wakes at an earlier known receiving deadline instead of
sleeping through it until the next 100 ms check. Its ordinary idle polling rate,
proof cadence and guard/native acquisition policy are unchanged. Focused tests
cover blocked teardown, concurrent pending-view updates and revocation during
the final age update. The corrected candidate's exact terminal and normal
30-minute resource results are recorded in the T9 checkpoint below.

Shutdown stops app update requests and timers synchronously before reader
revocation can wake the UI during teardown. The outer owner still joins the
notification/age tasks asynchronously. In-flight paints recheck the stop gate
after framework awaits, so they cannot resume against unmounted widgets.
Deterministic tests cover the stop-before-revoke order, pending-paint resumption,
the retained async join and an app factory without the optional synchronous hook.

`scripts/check-dashboard-resources` separates `diagnostic` from fixed `normal`,
`soak` and `capacity` resource profiles. Short/custom runs cannot become accepted
normal or soak qualification. The separate practical preview smoke does not
claim either sustained or large-fleet acceptance. Qualification binds exact
fixture roster/outcomes, 120x40 UI,
durations, runtime bytes, coverage and cleanup. The soak proof names the failed
source and requires advanced epochs, a fresh baseline and continuously healthy
siblings. Resource receipts explicitly exclude interaction/paint latency claims;
those need their own draining-terminal evidence. See the
[source-preview guide](../guides/dashboard.md) for setup and use.

## Resource and installed qualification baseline (T9)

This checkpoint records the measured baseline and its limits. The frozen product
candidate is source commit `d57233313f01983361b75fb0953662afa212c513`; its
wheel SHA256 is
`fd8ec13ee37470d1e31788df399057ba371eeaad67d412087993eb75995c55f0`. The
unreleased wheel retains a12 distribution metadata and is distinct from the
published a12 artifact. Strict Mesh/dashboard source checks passed 1,298 tests
on Python 3.11.17 and 3.14.8. Eight installed variants passed with 112 package-file
parity checks; paired dashboard installs passed 98 tests per runtime with zero
skips.

The fixed normal profile ran the installed `agent-observer dashboard` on a
draining 120x40 terminal with an external sampler: three sources x100 identities,
120 seconds of warmup and 1,800 measured seconds. CPU was 4.87764% and 4.73657% of
one core, peak RSS was 65.17 and 66.60 MiB, and there were no measurement
coverage misses. The external sampler was reported separately. The older T6
Python 3.11 result of 5.1597% remains failed; the candidate and measurement
windows differ, so the two results do not prove a speedup.

Other bounded installed checks passed on this candidate: ten quiet-expiry
trials per runtime had maxima of 84 and 189 ms against the 250 ms limit; 100
metadata updates had first-public-frame-to-screen p95 of 106 and 117 ms after
`guard.accept`, excluding SDK admission, while fixture-acceptance-to-screen
p95 was 631.268 and 569.446 ms including producer delivery. Five stuck-socket
startup trials per runtime displayed source health and quit/help in 165–196 ms,
including Python startup. Key p95 was 33.23/22.21 ms, resize was 20–54 ms across four
sizes, and 100 installed wire-churn cycles passed per runtime. The 27.5-second
job-control stop exceeded 25-second fixture leases: all facts were current at
stop and expired before continue, degraded state appeared in 33.634/33.452 ms
before fresh writes, then all 300 outcomes and complete baselines recovered.
This tests process job control, not physical machine sleep.

The optional T9 eight-hour soak was stopped after about 3.6 measured hours when
the user narrowed preview acceptance. The owner and test children exited, test
sockets were removed, and terminal flags/reset were restored. The receipt
retains its incomplete-duration and cancellation-related failures; this is not
an eight-hour pass or a substitute long-run qualification. The completed normal
resource runs and controlled recovery evidence supply the preview acceptance.
The original T5 task-minimum failure remains failed.
Historical eight-source/8192-outcome stress capacity is unmet and deferred:
both baseline and traced 8x1024 reader-only runs timed out before reaching
eight complete sources. Each had a sampled maximum of four complete sources/4,096
members and ended with three/3,072. Consumer CPU was 45.60–47.38 seconds per minute and
maximum event-loop lateness was 1.43–1.48 seconds. The consumer had no Textual
UI; traces show substantial cached source/publication work but do not prove the
exact timeout cause or establish dashboard capacity. Read-path optimization
remains deferred, with no SDK tuning, guard bypass, dark prepared branch or
hidden fallback. The user replaced that mandatory stress gate with a quick
check of the actual cached fleet, supplemented by existing controlled installed
update, interaction and source-recovery checks.
The replacement installed-dashboard smoke passed on Python 3.14.8: after twenty
seconds the public projection was current, with three complete sources,
16 members, zero uncertainty and all 16 rows materialized. Exit was zero,
terminal flags and reset were restored, and owned cleanup took 0.18 seconds.
Only aggregate metadata was retained. Existing installed update, key/resize,
expiry and 100-cycle source-loss/recovery checks supplement this snapshot;
those transitions were not reproduced in the real-fleet run. The stress failure
is retained as a limit, not a preview blocker or a successful capacity result.

Pre-push review also corrected tiny-terminal help: the `?` panel now replaces
resize guidance with a short keyboard summary and a matching footer. The
regression checks mounted help text rather than only the internal overlay flag,
and passes on source and a rebuilt, separately installed wheel. Review also
corrected manual-retry cooldowns after a receiving-clock change: timestamps from
the old clock no longer prevent retry, while facts remain revoked until a fresh
baseline is admitted. These corrections are checked separately from the frozen
resource/native measurements above.

The real cached fleet showed three complete sources and 15 members. Installed
public-CLI readings matched independent metadata-only native RPC samples taken
before and after them for three selected local working/waiting/parked cases.
All five identity fields and activity timestamps matched, and each cached
observation timestamp fell inside its native sample interval. Agreement at the
interval endpoints does not prove uninterrupted state, full remote coverage or
human acceptance. The preview is unreleased; no managed TUI selection or
deployment is claimed.

## Review findings and validation

The preimplementation review used the a12 source and exact Mesh a25 pair on
Linux/x86-64, with isolated Textual environments. Its findings below explain
the lifecycle/output design adopted by the source preview; they are historical
feasibility evidence, not a substitute for the current T9 qualification above.

| Finding | Evidence and resulting requirement |
| --- | --- |
| Fixed-rate full evaluation conflicts with the idle CPU target | On Ryzen 9 7900X / Python 3.11.17, 30 public-facade read samples for 100 synthetic identities averaged 15.57 ms CPU. Three such reads at 4 Hz project 18.68% of one core before proof/UI work. This is a microbenchmark projection, not measured fleet CPU. Schedule exported deadlines instead; the subsequently revised <=5% sustained target is still unproven. |
| Deadline scheduling can use existing public exports | Controlled admitted cached-service cases with 0, 1 and 100 members evaluated just before/at the exported receiving deadline, without consuming another frame. Positives and complete-empty coverage revoked at the boundary. The facade supplied uncertainty where appropriate. This proves boundary semantics, not a finished scheduler or its sustained cost. |
| Default NO_COLOR is insufficient for the stated contract | Textual 8.2.8 real PTYs emitted grayscale color commands under default NO_COLOR. Native ANSI construction plus NO_COLOR emitted no foreground/background color selections, with default resets/control sequences retained. Use this path and avoid the discouraged filter module. |
| Framework worker cancellation does not prove cleanup | A synthetic three-second finally block in a Textual worker was interrupted on shutdown on Python 3.11/3.14. An outer async owner completed it, while terminal restoration arrived at about 0.5 s from process start and process exit at about 3.6 s. This is a framework ownership probe, not qualification of Mesh cleanup. |
| Stock output backpressure can freeze progress and exit | In a real 80x24 PTY at four repaints/second, pausing output reads for 15 s filled the stock queue; only 30 update ticks ran and a quit scheduled at 13 s did not complete until output resumed. The bounded-output adapter is therefore a required feasibility gate, not optional polish. |

Headless input/literal-label/resize probes passed on Python 3.11.17 and 3.14.8
at 120x40, 80x24, 60x16 and 40x10. Ten real PTY cases distinguished the default
behavior from the required no-color and cleanup ownership paths. These
preimplementation checks validated assumptions; later source, installed and
resource evidence is recorded in the T9 checkpoint above. The realistic preview
check passes. Eight-hour stability and large-fleet stress testing are optional
future work.

## Implementation structure and dependencies

The source preview uses the optional extra `dashboard = ["textual>=8.2.8,<9"]`
and the exact Textual 8.2.8 qualification lock. [Published metadata](https://pypi.org/project/textual/8.2.8/)
includes Python 3.11/3.14; the current paired installed matrix is recorded in
the T9 checkpoint. Textual fits the existing asyncio reads and supplies resize/input/layout plus
[headless Pilot tests](https://textual.textualize.io/guide/testing/).
Earlier framework smoke probes passed on Python 3.11.17/3.14.8 with Textual
8.2.8 and Rich 15.0.0: input owns q/j/k, literal metadata remains literal, and
headless resize works at the four planned sizes. The source-preview package
matrix is qualified at the installed test boundary; release acceptance remains
separate.

Use the public [App ANSI-color option](https://textual.textualize.io/api/app/#textual.app.App)
with normalized NO_COLOR at construction for strict no-color output. On the
tested release, default NO_COLOR may emit grayscale RGB commands; native ANSI
mode plus NO_COLOR emits terminal-default color resets instead. Honor the CLI's
nonempty NO_COLOR precedence, including `--color always`; `--color never` uses
the same normalized path. Do not import `textual.filter` in product code: its
installed module explicitly discourages application use despite the API page.
Verify actual PTY SGR bytes, allowing default resets/bold/reverse/cursor controls
but no foreground/background colors. Framework
[worker cancellation](https://textual.textualize.io/guide/workers/#cancelling-workers)
does not replace explicit guard/SDK cleanup or source-specific error handling.

Curses would reduce third-party dependencies but require custom layout, focus
and terminal-test plumbing. Textual is the selected source-preview framework;
the realistic preview check and release acceptance still apply.
Rich remains a
transitive dashboard dependency, never a core/finite-CLI requirement. Install
`.[mesh,dashboard]`; lazy imports keep core-only and mesh-only behavior intact.
No syntax, dev-console, web-serving or remote UI feature is needed.

| Implemented ownership | Responsibility and acceptance boundary |
| --- | --- |
| `terminal/config.py`, `terminal/model.py` | Reuse bounded configuration and pure semantics; factor shared projection/filter functions only where needed. Finite CLI and JSON v1 regression proof remains required. |
| `terminal/sources.py` and `terminal/watch.py` | Share one-attempt admission/cleanup primitives while keeping finite fan-in/deadlines and persistent retry policy separate. The supervisor owns epochs, source state, expiry and bounded UI handoff. |
| `terminal/dashboard.py` and packaged stylesheet | Lazy Textual app, exact-identity selection, hidden/unavailable placeholders, grouping/pages, view/focus/keys, safe literal labels and bounded rendering. Views do not own or restart subscriptions and add no native classifier. |
| Dashboard output adapter/runner | Bound Linux terminal writes through the framework driver extension, retain native terminal/input behavior and keep source cleanup outside the widget worker lifetime. Bounded output and cleanup foundations are implemented; later resource gates remain. |
| `cli.py`, `pyproject.toml`, checks/CI | The dashboard dispatch, optional extra and stylesheet packaging use an explicit required-dashboard gate so skipped optional tests cannot qualify it. Diagnostics and wire schemas remain unchanged. |
| Tests, sessions guide and this plan | Controlled lifecycle/clock/selection cases, installed UI/package proof and public setup/use instructions. Update existing maintained topics rather than adding dated status pages. |

## Implementation sequence and review gates

This reviewed plan is implemented as a source preview. Failing qualification
measurements return to this contract rather than changing scope implicitly.
Publication and managed deployment remain separate later steps.

| Stage | Work and concrete exit |
| --- | --- |
| T0: design review | Complete; the selected full-list layout with on-demand details, source/view distinction, keys, Textual and budgets are specified above. |
| T1: feasibility and lifecycle foundation | Implemented and covered by source/installed checks. Current normal, quiet-expiry and cleanup evidence is summarized in T9; large-fleet stress capacity is deferred. |
| T2: usable TUI preview | Implemented as a source preview with list, health, details, search/filters, source view, stable selection, help, resize and guidance. Actual PTY and installed checks pass at their stated boundaries; user acceptance is pending. |
| T3: resilience and budgets | Preview scope checked: expiry, startup, interaction, job-control recovery, churn, normal 30-minute resource runs and the short realistic-fleet check pass. Extended eight-hour soak, eight-source/8192-outcome stress testing and read-path optimization are deferred. |
| T4: package and consumer qualification | Source and paired installed-wheel matrices pass. The public local/two-host recipe is documented; real cached-fleet and the focused independent native comparison pass at their recorded scope. No full remote/native coverage or human acceptance is inferred. |
| Later delivery | New immutable release and package/dependency provenance, retaining terminal JSON v1; independently reviewed TUI pin, managed rollout/recovery and Fleet presentation. No collector/publisher/hardware/Agent Plus/Tmux migration is inferred. |

Use unittest conventions and deterministic receiving clocks, controlled cached
servers and documented Textual Pilot APIs. Preserve meaningful installed CLI
checks while adding targeted tests for persistent behavior:

- Busy, quiet, waiting, blocked, parked and recent-with-unknown-runtime rows;
  independent membership/runtime/phase/activity health and stale facts.
- Complete empty, only nonmembers, uncertainty, partial census/clock recovery,
  wrong binding/window, zero filter matches and hidden child/system rows.
- Quiet member/field/scope expiry with no frames; gap/resync/EOF, publisher
  rotation, wrong order, source namespace change, catalog revision and restart.
- Healthy siblings during one failed source; bounded setup/retry concurrency;
  old epochs queued around revocation cannot restore positives.
- Exact selection with duplicate labels/IDs, reorder/filter/page/group changes,
  disappearance, source loss and return. Invalid duplicate identity claims block.
- Input focus owns q/j/k, search cancellation restores the old filter, details
  preserve target/scroll across resize and help remains discoverable.
- Wide/combining/long Unicode, literal markup, controls, NO_COLOR, explicit
  no-icons, light/dark terminals, unsupported terminal and terminal restoration.
- Shutdown during connect, baseline wait, proof wait, quiet sleep, retry wait,
  modal input and stalled output; no owned child/task/FD leak or provider action.
- Pause output draining through queue saturation, trigger quit/signal, inject
  writer failure and repeat cancellation during cleanup. Measure source expiry,
  event-loop responsiveness, queue bytes and terminal flags independently from
  screen-reset delivery. No private writer-thread patch or hidden abandoned task.

Package matrices cover core-only, mesh-only, dashboard-only and mesh/dashboard.
The dashboard-only install must explain missing Mesh before any I/O; ordinary
CLI/help/schema/config inspection must not import Textual. Verify wheel files
and optional dependencies outside the source checkout, including its stylesheet.

The public recipe uses an existing local working-set publisher/bridge, explicit
directional second-host delivery and a separately configured home, without
private chezmoi assumptions. Compare selected exact identities and independent
runtime/phase/activity evidence under the [validation workflow](validation.md).
Fixture/consumer agreement is not native proof. Preserve ordinary providers,
native sessions, hooks and all selected producer/other-consumer roles.

The implementation follows the command entry, full-list default with adaptive
on-demand details, keys, retry schedule and numeric budgets above. Textual
adoption remains conditional on the explicit feasibility gates.
Session content, alerts, native actions/terminal composition, Agent Plus
sidebar, WSNav revival and Tmux work remain outside this TUI.
