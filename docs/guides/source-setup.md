# Host the first working-set source

This guide starts from an existing owned Codex home and its already-running
native daemon. It hosts a foreground Service 4 collector and a cached Mesh
publisher, then uses the separately released a14 sessions CLI/dashboard. The
local trial paths are private and temporary. The local path changes no managed
service, Mesh authority, native daemon or home/XDG directory. The optional
remote path requires its source owner to review the shell startup mechanism
that supplies the wrapper to noninteractive SSH.
Use Linux, Python 3.11+ and `curl`.

Observer is read-only. It does not start Codex, control a conversation or
inspect transcript contents. The ordinary source window is fixed at 72 hours;
active membership remains independent of recent activity. Partial, stale,
unknown and unavailable results stay qualified. Zero displayed rows alone do
not prove a complete empty source. Observer writes, Claude observation and
standalone active-only hosting are retired; optional Mesh delta-sync and
complete-view feed paths remain unselected.

## Reuse before starting

If your current `terminal.toml` already selects a working-set source for this
host and home, check it with `agent-observer sessions sources` and reuse its
owner. Do not start another collector or bridge to replace that route. Check a
known custom Service 4 endpoint with its owning service command; the default
endpoint can be inspected with:

```sh
agent-observer service status --host-scope workstation
```

If a managed or otherwise owned endpoint already uses the intended host/home,
stop here and use its published source details. Starting the private trial below
is for an endpoint you own and have confirmed is not already running. The
sample does not discover custom service sockets or decide that a managed
endpoint is safe to duplicate.

Create one unique private trial directory and keep its printed path for each
terminal used below. It is only a path value; do not export it as an XDG or home
directory setting.

```sh
set -eu
umask 077
TRIAL=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/agent-observer-source.XXXXXX")
chmod 700 "$TRIAL"
printf 'Trial directory: %s\n' "$TRIAL"
```

## Install the producer pair

The source host uses the separately released Observer a11 working-set producer
and Mesh a25. Install them in their own environment; do not use the a14 reader
environment for collection. The wheel URLs and hashes below identify the
published bytes:

```sh
set -eu
python3 -m venv "$TRIAL/producer-venv"
. "$TRIAL/producer-venv/bin/activate"
python -m pip install \
  'agent-observer @ https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a11/agent_observer-0.7.0a11-py3-none-any.whl#sha256=f8956346ce169062b88940475a17b5f3e5b70e8ba5c2396c5c1844aab3bfe755' \
  'mesh-plus @ https://github.com/byebyebryan/mesh-plus/releases/download/v0.1.0a25/mesh_plus-0.1.0a25-py3-none-any.whl#sha256=0055e42162827744add4f817d3918cfc20471e5ec5a3cdf0840d254f76f5dc3a'
agent-observer-service --version
mesh-plus doctor --sdk
```

The final command checks the installed Mesh SDK. Installation selects no
collector, publisher, bridge or route. For the released a14 reader pair and
optional dashboard dependencies, use the hash-pinned commands in the
[sessions CLI prerequisites](sessions-cli.md#prerequisites) and
[dashboard install guide](dashboard.md#install-the-prerelease). Keep the reader
in a separate environment.

## Resolve one existing home without starting it

Use the exact Codex home already owned by the running daemon and the logical
host name you intend to publish. The configured home spelling participates in
identity; do not substitute a similarly named directory or a different symlink
alias. These shell variables are local to this shell and are passed explicitly
to Observer; they do not rebind `HOME`, `CODEX_HOME` or any XDG setting.

```sh
set -eu
OBSERVER_HOST=workstation
OBSERVER_CODEX_HOME=/home/you/.codex
mkdir -m 700 "$TRIAL/runtime"
test -d "$OBSERVER_CODEX_HOME"
```

Create the minimal private home manifest. Replace both example values; the
selected path must be the existing owned Codex home, not a new or inferred one.

```sh
set -eu
cat > "$TRIAL/profiles.toml" <<TOML
version = 1
host = "$OBSERVER_HOST"

[profiles.default]
label = "Default"
codex_home = "$OBSERVER_CODEX_HOME"
TOML
chmod 600 "$TRIAL/profiles.toml"
```

Resolve it with the producer package. This is a pure local route calculation:
it does not connect to the daemon, create sockets, inspect native state or
start a collector. Passing a private runtime root keeps the derived sockets
under this trial rather than at managed/default service paths.

```sh
set -eu
agent-observer profiles \
  --config "$TRIAL/profiles.toml" \
  --runtime-dir "$TRIAL/runtime" \
  --json > "$TRIAL/profiles.json"
python -m json.tool "$TRIAL/profiles.json"
OBSERVER_HOST=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["host"])' "$TRIAL/profiles.json")
OBSERVER_PROFILE_ID=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["id"])' "$TRIAL/profiles.json")
OBSERVER_CODEX_HOME=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["codexHome"])' "$TRIAL/profiles.json")
OBSERVER_NAMESPACE=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["namespace"])' "$TRIAL/profiles.json")
OBSERVER_COLLECTOR_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["collector"]["socket"])' "$TRIAL/profiles.json")
OBSERVER_MESH_SOURCE=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["mesh"]["source"])' "$TRIAL/profiles.json")
OBSERVER_MESH_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["mesh"]["socket"])' "$TRIAL/profiles.json")
```

For profile `default`, the output identifies:

| Output field | Meaning |
| --- | --- |
| `host` / `codexHome` | The exact logical host and configured home spelling |
| `namespace` | The complete local Codex identity namespace; copy it without editing |
| `collector.socket` | Observer Service 4 input socket, read by the working-set factory |
| `mesh.source` | `agent_working_set` for the default profile |
| `mesh.socket` | Local Mesh bridge output socket, read by local Mesh/Observer clients |

The namespace is derived from provider, configured home, explicit selector and
effective UID. The host label is not included. A second profile gets a distinct
namespace only when it selects a distinct configured Codex home; changing a
profile ID or label alone does not change identity. Neither `profiles` nor this
guide offers a standalone active-only mode.

## Keep the launcher and source descriptor owner-private

The maintained
[version-bound launcher](../../examples/mesh_plus_agent_working_set.py) composes
Mesh's a25 static `publisher_factories` hook with the Observer a11
`make_working_set_publisher` factory. It is intentionally tied to that installed
pair; the Observer module used by it is not a general stable public API. Review
the small file before placing it in service. The companion
[source descriptor example](../../examples/mesh-sources.toml.example) shows its
version-1 shape.

Copy the Python launcher into a private directory as
`mesh_plus_agent_working_set.py`; its sidecar must be named
`mesh-sources.toml` beside that file. Create a separate shell entrypoint named
`mesh-plus` in the same directory, as shown below. Do not replace the Mesh
environment's installed `mesh-plus` executable or edit
`~/.config/mesh-plus/sources.toml`. The wrapper binds only the selected
`agent_working_set` source for `bridge` and `serve` when `--config` is omitted.
It keeps an explicit `--config` unchanged, accepts fully spelled `--source` and
`--config` forms (including `--flag=value`), rejects ambiguous/duplicate target
bindings, and leaves Mesh authority commands and unrelated Mesh commands/source
IDs on ordinary Mesh dispatch. A bad or mismatched selected descriptor fails
before Mesh can choose a reference adapter.

```sh
set -eu
SETUP_EXAMPLE_REVISION=d3e4df66902fd97b17aef6239261473fb1c4e91a
LAUNCH_DIR="$TRIAL/mesh-plus-observer"
if [ -e "$LAUNCH_DIR" ]; then
  printf 'Refusing to reuse existing launcher directory: %s\n' "$LAUNCH_DIR" >&2
  exit 1
fi
mkdir -m 700 "$LAUNCH_DIR"
curl --fail --location \
  "https://raw.githubusercontent.com/byebyebryan/agent-observer/$SETUP_EXAMPLE_REVISION/examples/mesh_plus_agent_working_set.py" \
  --output "$LAUNCH_DIR/mesh_plus_agent_working_set.py"
chmod 700 "$LAUNCH_DIR/mesh_plus_agent_working_set.py"
cat > "$LAUNCH_DIR/mesh-sources.toml" <<TOML
version = 1
host = "$OBSERVER_HOST"

[sources.agent_working_set]
domain = "agent"
socket = "$OBSERVER_COLLECTOR_SOCKET"
TOML
chmod 600 "$LAUNCH_DIR/mesh-sources.toml"
cat > "$LAUNCH_DIR/mesh-plus" <<SH
#!/bin/sh
exec "$TRIAL/producer-venv/bin/python" -I -B "$LAUNCH_DIR/mesh_plus_agent_working_set.py" "\$@"
SH
chmod 700 "$LAUNCH_DIR/mesh-plus"
```

Use the immutable example revision published with this guide in
`SETUP_EXAMPLE_REVISION`; do not substitute a moving branch name. The downloaded
file is a small reviewed helper, not a wheel or a source installation.

That descriptor's `socket` is the collector input from `profiles`, not the Mesh
output socket. The wrapper reads this separate owner-private file only when the
exact Observer source is selected and no explicit config was supplied. It does
not modify Mesh's default configuration or any environment variable. The
directory and file must remain owned by the publishing user; Mesh validates the
descriptor as an owner-private regular file without following a file symlink.
The private `mesh-plus` command is a small shell entrypoint to the maintained
Python launcher. It fixes the producer interpreter and opts out of CWD, user
site and `PYTHONPATH` imports; it does not replace the venv's installed Mesh
command.

## Start only the endpoints you own

Terminal A: after confirming no managed/owned Service 4 endpoint already
publishes this same host and home, start the a11 collector on the resolved
private socket. It reads the existing Codex daemon and stays in the foreground.
The explicit `--codex-home` prevents fallback to a guessed home. The
`--working-set-window-hours 72` selection enables active plus recent membership;
it is not active-only hosting. Native hints remain unselected. In a fresh
terminal, set `TRIAL` to the exact printed path and activate the producer env.

```sh
set -eu
TRIAL=/absolute/path/printed/above
. "$TRIAL/producer-venv/bin/activate"
OBSERVER_HOST=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["host"])' "$TRIAL/profiles.json")
OBSERVER_CODEX_HOME=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["codexHome"])' "$TRIAL/profiles.json")
OBSERVER_COLLECTOR_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["collector"]["socket"])' "$TRIAL/profiles.json")
cd "$TRIAL"
agent-observer-service serve \
  --host-scope "$OBSERVER_HOST" \
  --provider codex \
  --codex-home "$OBSERVER_CODEX_HOME" \
  --working-set-window-hours 72 \
  --socket "$OBSERVER_COLLECTOR_SOCKET"
```

Terminal B: in another shell with the **producer** environment activated, start
the local cached Mesh bridge at the separately resolved output socket. It reads
the collector socket from the sidecar descriptor. This local `serve` process
owns only the Mesh output socket; it is not another collector. Set `TRIAL` to
the same printed path and activate the same producer env in this shell. Mesh
does not create the output socket's parent directory, so create that private
parent from the resolved socket path before starting it.

```sh
set -eu
TRIAL=/absolute/path/printed/above
. "$TRIAL/producer-venv/bin/activate"
OBSERVER_MESH_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["mesh"]["socket"])' "$TRIAL/profiles.json")
cd "$TRIAL"
mkdir -m 700 "$(dirname "$OBSERVER_MESH_SOCKET")"
LAUNCH_DIR="$TRIAL/mesh-plus-observer"
"$LAUNCH_DIR/mesh-plus" serve \
  --source agent_working_set \
  --socket "$OBSERVER_MESH_SOCKET"
```

Check that the foreground process starts without error, then use another
producer shell to read its local Mesh output:

```sh
set -eu
TRIAL=/absolute/path/printed/above
. "$TRIAL/producer-venv/bin/activate"
OBSERVER_HOST=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["host"])' "$TRIAL/profiles.json")
OBSERVER_MESH_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["mesh"]["socket"])' "$TRIAL/profiles.json")
cd "$TRIAL"
observer_read_status=0
agent-observer working-set list \
  --host "$OBSERVER_HOST" --source agent_working_set --scope local \
  --socket "$OBSERVER_MESH_SOCKET" --window-hours 72 || observer_read_status=$?
printf 'Cached diagnostic exit status: %s\n' "$observer_read_status"
```

The sockets have distinct roles: Service 4 is the collector input; `mesh serve`
creates the local Mesh IPC output; SSH later starts a remote Mesh bridge over
stdio and has no remote socket pathname. A reachable output socket or a
publisher heartbeat does not extend native leases or establish complete
coverage. If the read is warming, unavailable, stale or partial, preserve that
state and check the owner process, exact host/home/source binding and baseline.
Do not translate zero rows into complete-empty; inspect source health, coverage,
uncertain identities and known nonmembers.

## Open the released a14 CLI and dashboard

Use a separate a14 reader environment. Create one private terminal source
binding from the exact route output. Copy the full `namespace`, set `socket` to
`mesh.socket` (the Mesh output, never the collector input), and retain the
72-hour publisher window.

The code below creates and activates one `reader-venv` under the local trial.
Inside that active environment, run only the pip installation commands from
the linked guides: use the [sessions CLI prerequisites](sessions-cli.md#prerequisites)
for CLI-only use, or the [dashboard install guide](dashboard.md#install-the-prerelease)
for the a14 CLI plus its constrained optional dashboard stack. The dashboard
install includes the same reader pair. Do not run either guide's `.venv`
creation/activation lines, create a second reader environment, or run both pip
install alternatives.

```sh
set -eu
TRIAL=/absolute/path/printed/above
python3 -m venv "$TRIAL/reader-venv"
. "$TRIAL/reader-venv/bin/activate"
cd "$TRIAL"
OBSERVER_HOST=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["host"])' "$TRIAL/profiles.json")
OBSERVER_PROFILE_ID=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["id"])' "$TRIAL/profiles.json")
OBSERVER_NAMESPACE=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["namespace"])' "$TRIAL/profiles.json")
OBSERVER_MESH_SOCKET=$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"][0]["mesh"]["socket"])' "$TRIAL/profiles.json")
```

After that installation, create the source binding:

```sh
set -eu
cat > "$TRIAL/terminal.toml" <<TOML
version = 1
default_sources = ["workstation-default"]

[[sources]]
id = "workstation-default"
host = "$OBSERVER_HOST"
home = "$OBSERVER_PROFILE_ID"
label = "Default"
mesh_source = "agent_working_set"
scope = "local"
socket = "$OBSERVER_MESH_SOCKET"
namespace = "$OBSERVER_NAMESPACE"
window_hours = 72
TOML
chmod 600 "$TRIAL/terminal.toml"
```

In the **reader** environment, check the config without connecting, then check
live source health before opening a view:

```sh
set -eu
TRIAL=/absolute/path/printed/above
. "$TRIAL/reader-venv/bin/activate"
agent-observer sessions sources --config "$TRIAL/terminal.toml" --configured
agent-observer sessions sources --config "$TRIAL/terminal.toml" || [ "$?" -eq 3 ]
agent-observer sessions --config "$TRIAL/terminal.toml" || [ "$?" -eq 3 ]
agent-observer dashboard --config "$TRIAL/terminal.toml" || [ "$?" -eq 130 ]
```

The bare command is the quick overview. The dashboard needs an interactive
Linux terminal and the optional Textual stack from the dashboard install guide;
press `q` or Ctrl-C to leave. The reader never starts either producer process.
It keeps source health and partial coverage visible even when filters show no
rows. Only complete current coverage with no members, uncertain identities or
known nonmembers qualifies as complete-empty.
The finite reader's exit 3 reports degraded coverage, so the conditionals keep
that valid result from aborting these strict-mode setup shells. Exit 2 still
stops on invalid configuration; dashboard exit 130 is an intentional interrupt.

## Add one explicitly directional remote source

Do this only after the local source works. The remote source owner must own the
source Codex home and use their own UID, runtime root and exact home spelling.
The reader cannot derive a remote namespace from its own profile, UID or a
label.

### Prepare the source host

Run the common source setup on the **source host**, not in the reader's trial.
The source owner repeats [Reuse before starting](#reuse-before-starting),
[Install the producer pair](#install-the-producer-pair), [Resolve one existing
home](#resolve-one-existing-home-without-starting-it), and [Keep the launcher
and source descriptor owner-private](#keep-the-launcher-and-source-descriptor-owner-private)
there. Those sections are the canonical a11/Mesh a25 install, minimal
`profiles.toml`, pure route calculation and immutable helper/sidecar/wrapper
recipe. Substitute that host's logical host and existing Codex home. Use the
source host's own printed private `TRIAL` path throughout; do not reuse the
reader's trial, UID or profile output.

First check the source host's existing default and every known custom Service 4
endpoint using the common reuse step. If one already serves this host/home, use
its owner-published endpoints and do not start another collector. Set
`OBSERVER_COLLECTOR_SOCKET` to the exact owner-published Service 4 socket before
creating the sidecar. Otherwise, start only Terminal A from [Start only the
endpoints you own](#start-only-the-endpoints-you-own) on the source host. The
remote bridge uses SSH stdio on demand; Terminal B's persistent local Mesh
`serve` is not required for the remote route.

The common profile step resolves source identity and candidate socket paths from
the source host's own `profiles.json`. Send the reader owner these exact values;
use an existing publisher's actual Mesh output socket when reusing one:

```sh
set -eu
printf 'source_host=%s\nprofile_id=%s\nnamespace=%s\nmesh_source=%s\nmesh_socket=%s\n' \
  "$OBSERVER_HOST" "$OBSERVER_PROFILE_ID" "$OBSERVER_NAMESPACE" \
  "$OBSERVER_MESH_SOURCE" "$OBSERVER_MESH_SOCKET"
```

The namespace is source-owner identity. Do not calculate it on the reader. The
`socket` field on a remote `scope = "hosts"` entry is required by the reader's
config schema but is not used for the connection; use the remote publisher's
output socket, or the source profile's resolved Mesh socket as a descriptive
value for an on-demand stdio bridge.

### Expose and verify the source command to SSH

The common launcher recipe creates the owner-private command at
`$TRIAL/mesh-plus-observer/mesh-plus` on the source host. Its wrapper uses the
absolute producer Python with `-I -B`, so remote execution stays on a11 when the
reader uses a14 and CWD/`PYTHONPATH` cannot shadow installed packages. The
adjacent owner-private sidecar supplies the collector input because the fixed
SSH argv carries no `--config`; it does not replace Mesh's default config.

The source account must configure its **noninteractive SSH command PATH**;
exporting PATH only in the current terminal is insufficient. Replace the path
below with the exact source-host `TRIAL/mesh-plus-observer` directory created by
the common launcher step. For zsh, add an owner-reviewed line to `~/.zshenv`:

```sh
export PATH="/absolute/source-trial/mesh-plus-observer:$PATH"
```

For Bash, put the equivalent line in `~/.bashrc` before any interactive-only
guard or early return. Do not overwrite startup files or an existing
`mesh-plus` command. Use the source owner's approved SSH environment mechanism
if those files are managed or unsuitable; the private path must precede the
stock Mesh command. The wrapper binds only the allowlisted
`agent_working_set` source for `bridge`/`serve` with no explicit `--config`;
authority and unrelated commands/sources keep ordinary Mesh dispatch. Fully
spelled flags are required. An explicit `--config` remains authoritative and a
bad selected descriptor fails closed.

If a Mesh launcher is already independently managed, have its owner compose
this source factory without replacing other role selections. The private PATH
entry is for an explicitly owned source setup, not a managed-role upgrade.

Before the reader adds a route, verify the same noninteractive source command
environment that SSH will use. Replace `SOURCE` and the launch directory with
the exact authority destination and source-host paths. `command -v` must resolve
to that private entrypoint, and `doctor` must accept the adjacent private
sidecar:

```sh
set -eu
SOURCE=owner@source-host
SOURCE_LAUNCH_DIR=/absolute/source-trial/mesh-plus-observer
REMOTE_MESH_PLUS=$(ssh "$SOURCE" 'command -v mesh-plus')
printf '%s\n' "$REMOTE_MESH_PLUS"
test "$REMOTE_MESH_PLUS" = "$SOURCE_LAUNCH_DIR/mesh-plus"
ssh "$SOURCE" 'mesh-plus doctor --config /absolute/source-trial/mesh-plus-observer/mesh-sources.toml --source agent_working_set'
```

If the source owner wants a separate local smoke test, repeat Terminal B and
its local `working-set list` check on the source host with that host's own
`TRIAL`. Terminal B creates the resolved Mesh output parent as private 0700;
the persistent local `serve` is optional and is not part of the remote stdio
path. For a temporary source trial, wait until the reader has closed its remote
connection, then stop only an optional `serve` and collector started for this
trial. Deactivate the source trial environment in each active source-host
terminal before removing only the source owner's printed private `TRIAL`.
Keep the trial directory while it hosts a source that is still in use.
When retiring a temporary remote trial, remove only the shell PATH line added
for that trial after its readers and owner processes have closed.

### Confirm the reader's outgoing route and add its source

Host Mesh authority and outgoing route selection remain an explicit prerequisite
owned outside Observer. If the reader lacks a route, use the [Mesh host-routing
guide](https://github.com/byebyebryan/mesh-plus/blob/f0e06120c41279daf6e2055270919f8e93bed102/docs/guides/host-routing.md)
and its [Host Mesh v1 contract](https://github.com/byebyebryan/rofi-ssh-plus/blob/main/docs/reference/host-mesh-v1.md)
with the authority owner; this guide does not change that configuration. On the
reader host, inspect the already selected authority:

```sh
mesh-plus mesh list --json
```

Confirm that the reader endpoint has one configured outgoing route to the
exact source host. A route in one direction does not imply a reverse route. The
remote endpoint's authority is separate; unless its owner inspects that
endpoint, reverse reachability remains unknown. This guide adds no route, peer,
forwarding rule or reverse permission. Do not use DNS, known-host entries or a
successful incoming connection as route discovery.

Append one source to the reader's private `terminal.toml`, retaining the local
default source. Replace the values below with the exact host, profile ID,
namespace and Mesh socket supplied by the source owner. The host must match the
reader authority destination; the home field is a consumer-facing profile ID,
not a namespace. `socket` names the remote Mesh output but is not used for
`scope = "hosts"`. The remote request invokes the fixed
`mesh-plus bridge --source agent_working_set --stdio` command and has no remote
output socket path:

```sh
set -eu
REMOTE_HOST=source-host
REMOTE_HOME=default
REMOTE_NAMESPACE='exact namespace printed by the source owner'
REMOTE_MESH_SOCKET='/exact mesh output socket supplied by the source owner'
cat >> "$TRIAL/terminal.toml" <<TOML
[[sources]]
id = "source-host-default"
host = "$REMOTE_HOST"
home = "$REMOTE_HOME"
label = "Source host default"
mesh_source = "agent_working_set"
scope = "hosts"
socket = "$REMOTE_MESH_SOCKET"
namespace = "$REMOTE_NAMESPACE"
window_hours = 72
TOML
```

The source namespace must come from the source host's resolved profile output;
it cannot be derived from the reader's profile manifest. Keep the existing
`default_sources` list unless you intend to make this remote source a default.
Verify config identity and the live route before combining the view:

```sh
set -eu
agent-observer sessions sources --config "$TRIAL/terminal.toml" --configured
agent-observer sessions sources --config "$TRIAL/terminal.toml" --source source-host-default || [ "$?" -eq 3 ]
agent-observer sessions list --config "$TRIAL/terminal.toml" --source source-host-default || [ "$?" -eq 3 ]
agent-observer dashboard --config "$TRIAL/terminal.toml" \
  --source workstation-default --source source-host-default || [ "$?" -eq 130 ]
```

Mesh's fixed stdio argv carries no ad-hoc config path. The source-host wrapper
uses its adjacent private descriptor only for this allowlisted source when
`--config` is absent; an explicit config remains authoritative. The source owner
keeps the descriptor private and verifies the exact SSH command before the
reader uses the route.

## Stop and clean up the foreground trial

Close CLI reads and quit the dashboard first. Then press Ctrl-C in terminal B
to stop the Mesh `serve` process, and wait for it to exit and remove only its
own output socket. Finally press Ctrl-C in terminal A to stop the Observer
collector. Its owned socket is removed on exit; its lock file can remain until
the private trial directory is removed. Do not remove a socket or lock while an
owner process is still running, and do not stop a managed service.

After every owned process has exited, deactivate the trial environment in each
terminal where it is active and leave the trial directory before removing it:

```sh
deactivate
cd /
```

Remove only the unique local trial directory created above:

```sh
rm -rf -- "$TRIAL"
```

This removes the private venvs, config files, wrapper and any owned residual
lock in that directory. It does not touch the Codex home/daemon, installed
managed packages, Mesh authority or another process's runtime path.
