# Standalone dashboard

The `0.7.0a14` prerelease adds repository-path search to the standalone dashboard,
available through the optional `dashboard` extra. Bare `agent-observer` remains the quick overview;
`agent-observer dashboard` opens the persistent terminal application until you quit.

## Install the prerelease

Use Linux, Python 3.11+ and a separate environment. The qualified stack uses
Textual 8.2.8 and the unchanged Mesh a25 wheel:

```sh
python3 -m venv .venv
. .venv/bin/activate
curl --fail --location \
  https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/dashboard-requirements.txt \
  --output dashboard-requirements.txt
printf '%s  %s\n' 55091963b3457d9c0aa198b123b19f0f37909891be8e9127b8842d1dfd92cd46 dashboard-requirements.txt | sha256sum --check
python -m pip install -c dashboard-requirements.txt \
  'agent-observer[dashboard] @ https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/agent_observer-0.7.0a14-py3-none-any.whl#sha256=46a1158023023b60d9b839184a45f7b7eeb21b04dce67aad808fa8277522518f' \
  'mesh-plus @ https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/mesh_plus-0.1.0a25-py3-none-any.whl#sha256=0055e42162827744add4f817d3918cfc20471e5ec5a3cdf0840d254f76f5dc3a'
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
| `s` | Inspect every watched source |
| `r` | Retry the focused failed source with the same configured binding |
| `?` | Keyboard help |
| `q` / Ctrl-C | Quit / interrupt |

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

At 120x30 or larger, details open alongside the list; below that they use the
content area. At least 80x24 shows single-line rows, 60x16 uses compact rows,
and smaller terminals show resize guidance with overall health and quit/help.
Opening/closing panels does not restart subscriptions.

The list gives session names priority. A Repo column and separate runtime/phase
columns appear at 140 columns; narrower full layouts keep runtime/phase together.
Repo names come from current cached Git working-tree roots, including each linked
worktree's own directory name. Project labels are separate context. Details show
the full reported working directory and repository root near the top, with the
shared Git directory in the diagnostic section. A current workspace with no
repository says none reported; missing or expired metadata stays explicit.
The dashboard uses cached metadata without inspecting paths or running Git.
Working-directory metadata is a reported path, not a fresh native cwd sample.
Details group the session summary, workspace and source health before exact
identity, reason and deadline evidence lower down. Use the contextual footer for
common actions and `?` for the full keyboard guide.

In-app source/host/home filters narrow presentation only. `Sources N`
still describes the immutable startup watched set, and source failures continue
to affect overall coverage. Restart with different selectors to watch a
different set. The released a14 dashboard writes no preferences or search history.

## Source candidate: favorites and saved view

The maintained source also provides a small session board. This section does
not describe additions to the published a14 wheel or change managed selections.

Its main rows show **Status · Last active · Session · Profile · Workspace**.
Working, Ready and Blocked summarize current running runtime with the matching
phase; positively parked sessions show Inactive. Unknown, stale and unavailable
evidence stay explicit. Last active measures conversation activity, not duration
in that status. Source health remains above the list, and raw facts/reasons
remain in details.

Session titles receive the most flexible width. Profile shows host/profile;
Workspace shows a known current repo/worktree name or compact reported cwd.
Narrow rows and the split-details list keep status, activity age and title on
the first line, with profile/workspace below. Full paths and exact identity
remain inspectable. The [presentation contract](../maintenance/terminal-product.md#user-facing-rows)
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
summarizes current evidence and links the frozen qualification record. The a14
reader has source/installed checks and short actual-fleet terminal checks;
sustained resource and selected native measurements retain their earlier exact
artifact bounds. No new sustained run is claimed for the a13/a14 UI/search work.

The user accepted the practical preview and deferred large-fleet stress,
read-path optimization and the extended eight-hour soak. Earlier failures and
the cancelled partial soak remain failed/incomplete. Admission caps are not
usable fleet capacity. Cached-consumer agreement does not prove native accuracy;
human/physical acceptance and managed delivery remain separate gates.
