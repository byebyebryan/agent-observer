# Your first local Observer read

This guide covers explicit native diagnostics. For the everyday cached fleet
overview, use the [sessions CLI](guides/sessions-cli.md); for persistent
monitoring, use the [dashboard](guides/dashboard.md).

Start on the machine where your Codex runtime lives. You need Linux, Python 3.11+
with `venv` and pip, and an existing authenticated Codex home with its native daemon
running through your normal native workflow. Observer reads that runtime; it does
not start a missing daemon.

## 1. Install the published core package

Create a dedicated environment in a directory you choose:

```sh
python3 -m venv observer-venv
. observer-venv/bin/activate
python -m pip install 'https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a12/agent_observer-0.7.0a12-py3-none-any.whl#sha256=1cfc8896950240448dc0485d0e12e05157855dc54b84713f9da5a916fcafef1d'
agent-observer api
```

The hash binds the download to the published a12 artifact. The core has no runtime
Python dependencies and requires no Mesh, Rofi or tmux installation. `api` reports
package interfaces without contacting a provider. Expect `apiVersion: 4` and
snapshot/watch schema versions `6`.

If your installation is managed by chezmoi or another owner, use its selected
environment instead of replacing it. This temporary environment can coexist with
that installation; creating it does not change managed commands or services.

## 2. Read your selected native home

Choose the logical host label and Codex home explicitly:

```sh
OBSERVER_HOST=workstation
OBSERVER_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
agent-observer list --host-scope "$OBSERVER_HOST" --provider codex \
  --codex-home "$OBSERVER_CODEX_HOME"
```

Replace `workstation` with your configured logical host identity, and select the
home that owns the conversations you want. A separate work home stays a separate
observation scope. `--host-scope` labels the source; it does not authenticate a
machine or configure a remote route.

The human table has these columns:

```text
HOST  PROVIDER  PHASE  RUNTIME  ACTIVITY_AGE  NATIVE_TURN  THREAD_UPDATE_AGE  ID  TITLE
```

This is an explicit direct read. `snapshot` returns the fuller public document;
`list` applies presentation filtering, hiding confirmed child/system rows by
default. Add `--include-children` or `--include-system` when that is your intent.

## 3. Understand what you see

| Field or result | Meaning |
| --- | --- |
| `PHASE` | Observed work state such as working, waiting or blocked, when qualified |
| `RUNTIME` | Native runtime disposition; running includes an idle/waiting daemon thread |
| `ACTIVITY_AGE` | Age of the observed conversation activity, not exact phase-entry time |
| `NATIVE_TURN` | Native latest-turn status/timing where supported |
| `unknown` or `saved/unknown` | Evidence is insufficient; it does not establish idle or parked |
| Header with no displayed rows | Inspect snapshot coverage before concluding that the source is completely empty |

For coverage and full identities, use the same explicit source:

```sh
agent-observer snapshot --host-scope "$OBSERVER_HOST" --provider codex \
  --codex-home "$OBSERVER_CODEX_HOME"
```

Inspect `sourceHealth`, `sources` and their saved/runtime coverage alongside the
session rows. An unavailable or partial source is different from a complete empty
inventory. Keep the original independently expiring evidence when building a utility.

If the expected conversations are missing, first check the selected home and its
existing native daemon. Do not use terminal/window presence as a substitute for
native runtime evidence. [API 4](reference/read-api.md) and [provider compatibility](reference/provider-compatibility.md)
explain the supported meanings and capability checks.

## 4. Reuse cached local observations

Multiple clients can read an explicitly hosted Service 4 cache instead of each
performing direct collection. Follow the [current local service guide](guides/local-service.md)
to use an existing endpoint or start your own foreground publisher on a private
socket. Client reads and watches do not start the service or a provider daemon.

## 5. Add remote delivery when needed

Mesh is optional. A working-set reader needs the paired Mesh a25 installation,
a configured source publisher and directional Host Mesh routes. Its active/recent
window must match the publisher's policy; the reviewed default is 72 hours.
Once those endpoints exist, use the [sessions CLI](guides/sessions-cli.md) for a
configured fleet overview or the [working-set guide](guides/working-set.md) for
bounded diagnostics. The [compatibility overview](https://dev.byebyebryan.com/fleet-plus/compatibility/)
describes independently selected roles. Adding `--host` to a read never provisions a peer.

Start a new utility with the [bounded public-read example](guides/read-utilities.md).
Native providers continue to own conversation control throughout these read paths.
