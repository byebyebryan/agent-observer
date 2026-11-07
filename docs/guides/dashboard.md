# Standalone dashboard

The published `0.7.0a18` prerelease smooths source arrivals and uses four
columns from 100 terminal columns in the standalone dashboard,
available through the optional `dashboard` extra. Bare `agent-observer` remains the quick overview;
`agent-observer dashboard` opens the persistent terminal application until you quit.

The current source preview adds a dashboard-only compact-row refinement for
32–99 columns. It is not included in the published a18 wheel; finite CLI layout
and output remain unchanged.

## Install the prerelease

Use Linux, Python 3.11+ and a separate environment. The qualified stack uses
Textual 8.2.8 and the unchanged Mesh a25 wheel:

```sh
python3 -m venv .venv
. .venv/bin/activate
curl --fail --location \
  https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a18/dashboard-requirements.txt \
  --output dashboard-requirements.txt
printf '%s  %s\n' 55091963b3457d9c0aa198b123b19f0f37909891be8e9127b8842d1dfd92cd46 dashboard-requirements.txt | sha256sum --check
python -m pip install -c dashboard-requirements.txt \
  'agent-observer[dashboard] @ https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a18/agent_observer-0.7.0a18-py3-none-any.whl#sha256=694b086e744319ec1fa07b42519e0aa268a32b4c51e5b7745cd1150cd26ba30d' \
  'mesh-plus @ https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a18/mesh_plus-0.1.0a25-py3-none-any.whl#sha256=0055e42162827744add4f817d3918cfc20471e5ec5a3cdf0840d254f76f5dc3a'
agent-observer dashboard --help
```

This installs only the reader. It does not select a managed package, start a
collector/publisher/provider, or change any other client. The dashboard extra
is optional; finite CLI and core/local service users need no Textual dependency.

## Configure and open

Reuse the private version-1 `terminal.toml` from the
[sessions guide](sessions-cli.md#configure-sources-once). If a working-set source
is not hosted yet, use the [first-source setup guide](source-setup.md) before
opening the dashboard. The file describes existing working-set Mesh bridges,
distinct from collector Service 4 sockets. It must be an owner-private regular
file without a symlink, with mode 0600. Check it without connecting, then
inspect the actual source health:

```sh
agent-observer sessions sources --configured
agent-observer sessions sources
agent-observer dashboard
```

Use an interactive Linux terminal with stdin, stdout and stderr attached to
the same terminal and a cursor-capable `TERM`. For pipes, use
`agent-observer sessions list --format json` instead. The dashboard has no
JSON output, finite lifetime, `--format` or `--timeout` option.

Startup selection and presentation options follow the CLI:

```sh
agent-observer dashboard --source workstation-default
agent-observer dashboard --host server --home work --connect-timeout 15
agent-observer dashboard --query renderer --sort label --group host-home
agent-observer dashboard --color never --icons never
```

`--connect-timeout` bounds each setup/baseline attempt, from 1 to 60 seconds;
the default is 15. It does not limit application lifetime. `NO_COLOR` overrides
`--color always`. Standard icons need no special font; words and selection
markers remain usable without color or icons.

For two hosts and a second home, follow
[more hosts and homes](sessions-cli.md#more-hosts-and-homes): add one local
source and the remote host's existing default/second-home bindings, then select
their IDs or include them in `default_sources`. Obtain full namespaces and
Mesh source names from each owner; a home label cannot establish identity.
The dashboard uses existing directional Mesh routes and never discovers or
creates another route. Verify each source with `sessions sources` before
opening the combined view. A failed source stays visible independently.

## Read and navigate

The initial screen is the full list. Source health remains visible with empty
results, filters and open panels. Membership (`active`, `recent`, `uncertain`,
`nonmember`), runtime and phase are separate facts. Activity ages refer to
qualified native activity, not delivery heartbeats. Partial/stale/unavailable
sources cannot establish a complete empty fleet.

| Key | Action |
| --- | --- |
| Up/Down or j/k | Select a visible session |
| PageUp/PageDown, Home/End | Move through the list and its bounded pages |
| Enter | Open the exact selected session's details |
| Escape | Close the current panel/cancel an input edit; on the main list, clear selection |
| Tab / Shift-Tab | Move focus within the current view |
| `/` | Edit literal search; Escape restores the pre-edit query |
| `f` | Edit display filters and kind inclusion; Reset restores defaults |
| `o` / `g` | Choose ordering / grouping |
| `p` / `P` | Pin the selected exact session / manage favorites |
| `s` | Inspect every watched source |
| `r` | Retry the focused failed source with the same configured binding |
| `?` | Keyboard help |
| `q` / Ctrl-C | Quit / interrupt |

The dashboard opens `f` with **Status**: Working,
Ready, Blocked, Inactive, Unknown, Stale and Unavailable, matching the row
labels. Multiple statuses match with OR and combine with the
other filters using AND. All are selected by default; `a` toggles all/none while
Status is open. For one status, press `a` to clear all, then Space/Enter on that
status. Selecting none shows no rows. `r` restores all statuses and the other
default filters. Existing Source, Host, Profile, Member, Runtime, Phase and Kind
dimensions remain available.
Status choices are display filters for this run, with source health and exact
selection retained. See the [status-filter contract](../maintenance/terminal-product.md#dashboard-status-filter).

Search is a case-insensitive literal substring over the session name, project
context, reported working directory, host/home and full native ID. It also
searches the current cached repository root, shared Git directory and path
relative to that repository. Expired or unavailable repository metadata does
not match. Search remains a display filter; it does not inspect the filesystem
or merge linked worktrees.

While a text input is focused, printable keys including `q`, `j` and `k` enter
text. Ctrl-C remains global. Details show qualified facts first and retain full
identity, source, namespace, bounded reasons and deadline context as evidence.
Last-known values are explicitly noncurrent. Labels, paths and markup-like
metadata are literal text; the view does not open paths, links or transcripts.

Selection follows all five identity fields through updates, ordering, filters
and resize. A hidden selection stays pinned. If evidence leaves the projection,
only its identity and sanitized label remain, marked unavailable; old runtime
facts are discarded. A background update does not choose a neighboring row.

The dashboard chooses list rows by terminal columns,
independent of height: 100 columns and wider use the four-cell table; 32–99
columns use two-line rows. Their first line has the selection/pin marker,
qualified status, truncated title and complete activity age. The second line
keeps profile and workspace together. Below 32 columns or 12 rows, the app
shows resize guidance with live source health and help/quit. Height changes
chrome and page capacity without switching a wide terminal to compact rows, so
120x16 keeps the full table. The source ribbon
retains the source denominator and explicit health, including partial, stale
and unavailable states. Narrow footers use short key labels; `?` retains the
full meanings. Details, source evidence and filter choices wrap and scroll in
the content area, without horizontal list scrolling. Opening/closing panels
does not restart subscriptions.

List updates are staged: visible current rows remain while another
empty source warms or adds its baseline. Health and the watched-source
denominator update as each source changes. Changed or expired row facts are
refreshed or withdrawn before the dashboard waits for widget work.

These breakpoints refer to terminal columns and rows. Their fit in a particular
pixel-sized window depends on its emulator and font and remains a human visual
check. At 120x30 or larger, details open alongside the list; below that they use
the content area.

The list gives status, activity and session names priority, with profile and
workspace context. Repo names come from current cached Git working-tree roots,
including each linked worktree's own name. Details retain full reported paths,
repository roots and separate project labels. Missing/expired metadata stays
explicit; the dashboard does not inspect paths or run Git.
Working-directory metadata is a reported path, not a fresh native cwd sample.
Details group the session summary, workspace and source health before exact
identity, reason and deadline evidence lower down. Use the contextual footer for
common actions and `?` for the full keyboard guide.

In-app source/host/home filters narrow presentation only. `Sources N`
still describes the immutable startup watched set, and source failures continue
to affect overall coverage. Restart with different selectors to watch a
different set. Search history and display filters are never saved.

## Favorites and saved view

The a18 reader provides exact favorites and optional remembered ordering.

Human finite CLI rows use four cells: **Status / age · Session · Profile ·
Workspace**. Dashboard rows use four columns at 100 columns and wider. In the
current source preview, 32–99 column dashboard rows use two lines: selection and
pin markers, status, title and age on line one; profile and workspace on line
two. The context line uses a six-cell indent and a profile field sized to at most
12 cells; the left-aligned workspace starts at the same column for every row in
that list pane. It is italic and remains normal weight when selected, with the
existing host, home and workspace-type cues. Titles are bold at every width.
Dashboard identity and workspace colors use a fixed, softer 50% palette; the
finite CLI keeps its current palette. The published a18 wheel retains its
previous compact breakpoints until a later release.

Icons-on compact rows show only a status shape: `●` Working, `○` Ready, `!`
Blocked, `-` Inactive, `?` Unknown, `~` Stale and `×` Unavailable. `--icons
never` keeps the same two-line geometry and shows full status words. The compact
footer shows the selected row's full status when it fits; `?` includes the
symbol key. Ordinary activity ages reserve four cells per row. Longer age
qualifiers keep their full width on that row, shortening its title while the
title start and age right edge stay fixed. Ages use compact units such as `8s`
or `5m`, without a prefix; they remain approximate. Working, Ready and Blocked
summarize current running runtime with the matching phase; positively parked
sessions show Inactive. Unknown, stale and unavailable evidence stay explicit.
Last active measures conversation activity, not duration in that status.
Source health remains above the list, and raw facts/reasons remain in details.

Long TUI cells ellipsize while details retain full values. Workspace shows the current
cached root's name or a compact reported directory path, without `repo`/`dir`
prefixes. Reported `/home/<user>` paths display as `~` (for example,
`~/code/widget`); full reported paths remain in details and JSON. An expired
repository falls back to the reported directory, and
missing metadata is `unknown`. Full paths and exact identity remain inspectable.

The palette keeps selection background and marker neutral while
preserving status colors. Current activity age fades from newer to older over
24 hours; unknown, stale, unavailable and future ages stay neutral. Profile hue
identifies a stable host family and its bounded shade follows the exact home.
Repo, directory and unknown workspaces use distinct type colors. Light themes
use darker variants. For directory labels, the parent path through the last
visible slash is neutral and the final visible component uses the directory
color. `?` includes a short palette/type legend. No-color rows keep the workspace
name/path; details identify the repository and directory. The
[presentation contract](../maintenance/terminal-product.md#user-facing-rows)
defines status qualification and metadata limits.

- `p` with list focus pins/unpins the visible selected session; its exact
  selection follows it after movement. Matching favorites appear first in
  first-pinned order, marked `*`. The remaining rows keep normal ordering/grouping.
- `P` opens Pins. Select a reference and press `p` to remove it even when it is
  absent or hidden. `not in this view` makes no claim about native state.
- Order/group menus preview choices; Enter/Space accepts, Escape restores the
  previous value. Text input continues to own printable `p` and `P`.

Pin counts distinguish references in the current view from saved references;
favorites bypass no source selection, filter, kind or identity check. A missing
favorite creates no session row or native fact. Full exact identity, rather than
name or path, controls whether a returning row matches.

Optional local view state remembers only ordered exact pin identities and
accepted sort/group values (32 pins, 64 KiB maximum). Its path is
`$XDG_STATE_HOME/agent-observer/dashboard-view.json`, falling back to
`~/.local/state/agent-observer/dashboard-view.json`. The state root must already
exist; startup creates nothing. Labels, paths, queries, filters, selected rows,
source definitions and observations are never saved.

Explicit startup `--sort`/`--group` wins over saved choices without saving by
itself. Later deliberate edits save the current complete view. Use
`agent-observer dashboard --no-saved-view` for session-only edits and no state-file
I/O, including fixtures/previews. Independent dashboards use the last successful
save without merge or live reload. Invalid, unsupported or unsafe state is
preserved with a visible session-only warning; failed saves retain the current
in-memory choice and report it unsaved. See the
[local-state contract](../maintenance/terminal-product.md#optional-local-view-state)
for permissions, operation deadlines and interrupted-save limits.

## Recovery and exits

Quiet expiry removes positive authority without needing another frame. Feed
failure revokes that source's current facts before retry. Automatic retries use
1, 2, 4, 8, 16, then 30 seconds with bounded jitter; recovered feeds require a
fresh admitted baseline. Binding, namespace, contract, identity or capacity
faults stay blocked for inspection/manual retry. Retry does not reload config,
repair a native source, or adopt a changed namespace.

Explicit quit returns 0 even with failed sources. Setup/config/dependency errors
return 2; internal, output or cleanup failure returns 3. Ctrl-C returns 130,
SIGTERM 143 and terminal hangup 129 after owned cleanup. Stalled output fails
after two seconds without drain progress. Restored terminal flags and delivered
screen reset are separate outcomes when a terminal has stopped draining.

## Qualification boundary

The [terminal product contract](../maintenance/terminal-product.md#qualification-and-limits)
summarizes current evidence and links the frozen qualification record. The a18
reader has source/installed checks and short actual-fleet terminal checks;
sustained resource and selected native measurements retain their earlier exact
artifact bounds. No new sustained run is claimed for the a13/a14/a15/a16/a17/a18 reader work.

The user accepted the practical preview and deferred large-fleet stress,
read-path optimization and the extended eight-hour soak. Earlier failures and
the cancelled partial soak remain failed/incomplete. Admission caps are not
usable fleet capacity. Cached-consumer agreement does not prove native accuracy;
human/physical acceptance and managed delivery remain separate gates.
