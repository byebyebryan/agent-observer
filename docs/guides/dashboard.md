# Standalone dashboard

The dashboard is a **source preview under qualification**. The published
`0.7.0a12` release contains the finite sessions CLI, not this dashboard. Bare
`agent-observer` remains the quick overview; `agent-observer dashboard` opens
the persistent terminal application until you quit.

## Install the source preview

Use Linux, Python 3.11+ and a separate environment in a checkout containing the
dashboard changes. The initial qualification uses Textual 8.2.8 and Mesh a25:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c tests/fixtures/dashboard-requirements.txt \
  '.[mesh,dashboard]' \
  'https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a12/mesh_plus-0.1.0a25-py3-none-any.whl#sha256=0055e42162827744add4f817d3918cfc20471e5ec5a3cdf0840d254f76f5dc3a'
agent-observer dashboard --help
```

This installs only the reader preview. It does not select a managed package,
start a collector/publisher/provider, or change any other client.

## Configure and open

Reuse the private version-1 `terminal.toml` from the
[sessions guide](sessions-cli.md#configure-sources-once). It describes existing
working-set Mesh bridges, distinct from collector Service 4 sockets. The file
must be owned by your user, regular, without a symlink, and mode 0600. Check it
without connecting, then inspect the actual source health:

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

In-app source/host/home filters narrow presentation only. `Watching N sources`
still describes the immutable startup watched set, and source failures continue
to affect overall coverage. Restart with different selectors to watch a
different set. No preferences or search history are written.

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

The [terminal product plan](../maintenance/terminal-product.md) tracks source,
installed-wheel, controlled-failure, resource and native comparisons separately.
The current provisional resource target is 5% of one core and 192 MiB for three
sources x100 identities after warmup. Read-path optimization is deferred. Short
reader measurements are not complete-dashboard or eight-hour acceptance.
Neither synthetic fixtures nor agreement with another Observer command prove
native classification. Human terminal acceptance and managed rollout remain
separate from this preview.
