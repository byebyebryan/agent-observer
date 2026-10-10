# Optional Mesh state read client

The [accepted a12/a4 candidate](evidence/2026-10-09-mesh-integration/REPORT.md)
is selected on Snap and Starship. Both bridge units are enabled. Collection
services stay a11 and the writer stays a16; the shared SSH Plus authority stays a1.
These immutable candidate wheels are archived locally on both hosts, not released
publicly by this pass.

Observer a12 adds a read-only client of `mesh-plus>=0.1.0a4,<0.2`. Install the
optional `mesh` extra or explicitly install the reviewed Mesh wheel into the
client environment. Core and local service remain dependency-free. Normal
direct/service commands and `mesh api`/help work without Mesh installed.

```sh
agent-observer mesh api
agent-observer mesh snapshot --scope local
agent-observer mesh list
agent-observer mesh list --scope hosts --hosts starship snap --provider codex
agent-observer mesh watch --count 5
agent-observer mesh watch --human
```

Reads are cached. No collection request, provider action, route-health report,
notification or attachment lookup occurs. The default authority is the existing
`rofi-ssh-plus mesh list --json`; `--authority mesh` selects Mesh's facade.
Configured remote bridges are fixed-source SSH stdio connections. The default
local source selector is `agent` and socket is
`$XDG_RUNTIME_DIR/mesh-plus-agent/read.sock` (fallback `/run/user/<uid>/...`).
`--source`/`--socket` override this selection. `--local-host snap --scope local`
explicitly bypasses catalog lookup for local diagnosis.

`snapshot` and ordinary `watch` print lossless validated
`agent-observer.mesh-candidate.v1` frames as JSON/NDJSON. They include native
children, complete per-host owner metadata and original evidence clocks.
Filtering or reordering these frames breaks their exact native reconstruction
and remote-proof binding. `mesh api` describes this separate mode;
API 2/wire 4/service 2 are unchanged.

`list` and `watch --human` are presentation views. They use Mesh's current-row
selector, hide confirmed children by default, retain unknown classification and
show age from original conversation activity. Shared urgency/activity sorting
works across hosts: blocked, waiting, working, then unknown/inapplicable; most
recent within each group. `--include-children`, repeated `--provider` and
`--order created` apply only here. Filters supply no negative native evidence.
Coverage, delivery and view qualifications are printed before the rows. A ready
transport with partial Claude coverage does not mean an exhaustive census.

Push is replacement state, with explicit warming, per-host failure, gap and
resync. Heartbeats do not renew source evidence. The per-request ReadGuard
validates every watch frame; invalid frames, EOF, cancellation and output failure
close the owned stream and revoke cached positives. `--count` limits all frames,
including control/warming frames; a first pending frame is not a complete roster.
There is no replay/event feed or implicit polling fallback. Watch stdout has a
bounded five-second backpressure deadline. Reconnect starts a new read/guard.

Missing dependencies or admission errors yield bounded codes, without private
configuration/payload diagnostics. Unavailable snapshots return 1; partial
snapshots remain usable with explicit per-host outcomes. Terminal base errors
end the read. See the [integration plan](mesh-integration-plan.md) for independent
source, immutable package, native and operational gates. Downstream consumers,
devices, provider policy and fleet broker services remain separate work.
