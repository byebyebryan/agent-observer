# Sessions CLI

The `0.7.0a14` prerelease retains the sessions CLI described here. Installing a
reader does not change collector, publisher or other consumer selections.

Bare `agent-observer` opens the quick fleet overview. The explicit `sessions`
commands read the same configured working-set caches for overview,
listing and exact-session investigation. They never start a provider, control
a session, change host routes or fall back to a full inventory. Existing direct,
Service 4 and Mesh diagnostics remain available separately.

## Prerequisites

Use Linux and Python 3.11+ in an isolated environment. Install the published
Observer/Mesh pair with the qualified wheel hashes:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install \
  'https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/agent_observer-0.7.0a14-py3-none-any.whl#sha256=46a1158023023b60d9b839184a45f7b7eeb21b04dce67aad808fa8277522518f' \
  'https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/mesh_plus-0.1.0a25-py3-none-any.whl#sha256=0055e42162827744add4f817d3918cfc20471e5ec5a3cdf0840d254f76f5dc3a'
agent-observer sessions --help
```

From a checkout, `python -m pip install '.[mesh]'` installs the source reader
instead. Neither installation advances a deployed package pin. An already running
[working-set publisher/bridge](working-set.md) is required. If you own the
Codex home but have not hosted a publisher yet, use the complete
[first-source setup guide](source-setup.md). A cached local
bridge is distinct from the collector's Service 4 socket. Installing or opening
this CLI starts neither. No Textual/dashboard dependency is required.

## Configure sources once

The default file is `$XDG_CONFIG_HOME/agent-observer/terminal.toml`, or
`~/.config/agent-observer/terminal.toml`. Use `--config` to select another file.
It must be a private regular file owned by your user, without a symlink; use
mode 0600. No file, unknown selections and invalid configuration produce setup
errors instead of guessing a native home or adding routes.

For a local home manifest, inspect its pure route descriptions. The
[first-source guide](source-setup.md#resolve-one-existing-home-without-starting-it)
shows the minimal private `profiles.toml` and a private runtime root:

```sh
agent-observer profiles --config /absolute/path/profiles.toml --json
```

Copy the logical host, profile label/ID, full namespace, working-set Mesh source
and publisher/bridge socket from the selected route. This does not contact a
provider. Do not use the collector socket in the terminal source entry.

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
namespace = "sha256:<copy the full namespace from profiles>"
window_hours = 72
```

Replace every host/path/namespace placeholder with the existing source's values.
`home` is the consumer's selection name; `label` is its readable name. Neither
changes the native namespace. A source with the wrong namespace is blocked,
not relabeled. The reader window must match the publisher's fixed window.

There are at most eight configured sources. Each reserves 1,024 identity
outcomes and 4 MiB of admitted payload by default; optional `max_identities`
and `max_payload_mib` adjust reservations within the aggregate 8,192-identity/
32 MiB limit and the native per-source bound. A source over its allowance fails
visibly instead of silently truncating its inventory. These are admission safety
limits, not a guarantee of interactive large-fleet performance.

Check the resolved file without opening a connection:

```sh
agent-observer sessions sources --configured
```

## Quick checks and investigation

```sh
agent-observer
agent-observer sessions
agent-observer sessions list
agent-observer sessions list --host workstation --home default
agent-observer sessions list --membership active --phase working
agent-observer sessions list --query renderer --sort label
agent-observer sessions sources
agent-observer sessions show FULL_THREAD_ID --host workstation --home default
```

Bare `agent-observer`, `agent-observer sessions` and `sessions overview` show
the same overview. It has at most ten displayed rows, with a compact coverage
summary and separate membership/runtime/phase columns. Ordinary rows fit an
80-column terminal; narrower views use labeled session blocks. Long labels
wrap without losing text. Approximate activity ages use `~`; unknown or stale
facts retain their qualifications. Optional context appears in wider overviews.
Full IDs and context are available with `list` and `show`.

Interactive terminals use a cyan heading/navigation accent, bold session names,
quiet secondary metadata and colored state labels. Standard Unicode glyphs
mark `● working`, `○ waiting`, `! blocked` and `? unknown`; source coverage uses
`✓`, `!` or `×` alongside its text. No special font is required. Thin rules
separate headings from rows, with the same narrow-terminal layout.

`list` shows all matching
rows; counts and source health always describe the unfiltered selection as
well. Confirmed child/system kinds are hidden by default, unknown kinds remain
visible, and `--include-children`/`--include-system` enable diagnostic inclusion.
Exact show can inspect hidden kinds. Full thread ID plus host/home selects one
configured source; alternatively `show --ref JSON` takes the complete identity
with hostScope/provider/namespace/nativeIdKind/nativeId. Short IDs and names do
not select a session. Absence from this projection does not prove deletion or
absence from saved history.

Repeat source/host/home/membership/runtime/phase/query selectors to OR values
within one selector; different selectors are ANDed. Search is literal and
case-insensitive over admitted metadata, never conversation content. Source
selection and membership filters do not restart or reconfigure a publisher.
Activity ordering puts active members first, then other members, then uncertain
identities, using current native conversation activity and exact identity ties.
Use `--sort activity|label|host` and `--group none|host-home` for presentation.

Runtime, phase and membership are separate. `waiting` does not mean a response
is required. `recent` means the recent branch is proved while active is not
currently proved. Expired state becomes qualified unknown, never idle. Activity
ages are approximate against display wall time; receiving BOOTTIME leases own
validity. Source health, uncertainty, nonmembers and clock discontinuity remain
visible even if filters match no rows.

## More hosts and homes

Add another explicit source entry with a unique ID and host/home pair. For a
second local home, use that profile's distinct Mesh source, socket and namespace.
For another configured host, use `scope = "hosts"` and its exact catalog host
ID, Mesh source and expected namespace. The local socket field does not override
remote routing. Obtain remote route/home descriptions from that host's owner;
do not calculate its namespace from a local UID or guess it from a home label.

Include the desired IDs in `default_sources`, or select them explicitly using
`--source`, `--host` or `--home`. Remote reads use the existing directional Mesh
authority and noninteractive route. No reverse route or home discovery is added.
Test with `sessions sources` first: a failed source stays separate from healthy
ones and cannot turn a zero-row report into complete empty.

For a local/two-host check, use one known local entry and one known remote entry,
then add the remote second home as a third entry if configured. Compare each
entry with the existing diagnostic `working-set list` using the same exact
host/source/window. This verifies cached consumer agreement, not independent
native classification. Do not start another collector to make a reader pass.

## Pipes, JSON and exits

`--format json` emits one versioned `agent-observer.terminal` version-1 report.
It is distinct from the utility example's diagnostic JSON and all native wire
versions. Reports separate source health, current members, uncertain identities,
known nonmembers, requested filters and counts. Exported times describe a
point-in-time observation; closing the command ends live authority. Output is
not event replay and is not an atomic cross-host snapshot.

```sh
agent-observer sessions list --format json
agent-observer sessions schema
agent-observer sessions list --color never
agent-observer sessions --color never --icons never
agent-observer sessions sources --timeout 5
```

Human output is not a parser contract. Piped text has no terminal control/color,
pager or width truncation. Nonempty `NO_COLOR` overrides color settings.
`--icons auto|always|never` controls decorative glyphs independently of color.
Auto enables them only on an interactive terminal whose output encoding
supports them; `TERM=dumb` uses the plain fallback. Pipes omit decorative glyphs
even with `--icons always`. `--icons never` uses plain status words and separators.
Every colored/icon state retains its text label; color alone conveys no state.
The finite read budget is ten seconds by default (`--timeout` 1-60), including
setup. Reads recheck expiry while waiting for slower feeds. Invocation/output
errors go to stderr; source failures and degraded results are in the report.

Each source records its final `captureBoottimeMs` before read cleanup. Source
facts and deadlines refer to that capture in the exported receiving clock,
while `generatedAt` describes output generation. Time spent closing a stream
cannot make old facts current at a newer clock reading.

`sessions schema` prints the packaged terminal output schema without loading
configuration or Mesh. It does not change the native `schema` command.

Single-source `--socket` and `--window-hours` overrides are explicit diagnostics;
socket override requires local scope. They cannot change a host/home binding or
reconfigure the publisher's fixed window.

| Exit | Meaning |
| --- | --- |
| 0 | Complete current selected coverage, including a valid zero-match result |
| 1 | Exact show target unavailable in a fully observed working-set projection |
| 2 | Invalid invocation/configuration, no selected sources or missing dependency |
| 3 | Degraded, unavailable, blocked, timed-out or over-capacity result |
| 130 / 143 | Interrupt / termination after owned read cleanup |
| 141 | Closed output pipe, without traceback |

`complete-empty` requires complete current coverage and no members, uncertainty
or known nonmembers across every selected source. Filtered zero matches, expired
coverage, warming and missing baselines do not satisfy that condition.

The persistent dashboard is available with the optional `dashboard` extra in a14;
see the [dashboard guide](dashboard.md) for setup and use and the
[terminal product contract](../maintenance/terminal-product.md) for its acceptance
limits. Managed reader installation, native acceptance and hardware/Fleet
presentation are separate.
