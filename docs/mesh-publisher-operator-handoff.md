# Agent-owned publisher and read operations

Accepted 2026-10-12, Observer a20 with Mesh a15 / SDK interface 1. API 2,
snapshot/watch 4, Service 2 and Mesh Read/Delivery 1 remain unchanged. The
[execution receipt](evidence/2026-10-11-mesh-publisher/REPORT.md) separates source,
installed, native, resource, publication and operational acceptance.

## Selected roles

| Role | Snap and Starship selection |
| --- | --- |
| Collector/local service | Observer a18, unchanged process/cadence/hints |
| Read CLI | Observer a20 / Mesh a15 |
| Resident Agent mesh bridge | Observer a20 / Mesh a15, Agent factory |
| Fixed SSH Agent bridge | Shared a15 launcher, lazy Agent a20 factory |
| Tmux publication | Independently selected Tmux a7 factory, preserved |
| Writer | Historical 0.4.0a16, unchanged |

The Agent read/publisher prefix is
`~/.local/share/agent-observer/0.5.0a20-8241cafc13dbfdfe-mesh-a15-publisher`.
Its archive binds the a20 wheel SHA256
`8241cafc13dbfdfe43da0b092dbce99328ee6cc0b0b74faa04b428dfa54a9b1a`,
Mesh a15 wheel SHA256
`42b25045f8f89afda61e56525f443a189dcc6769637aee5bcab959f096527f0f`,
manifests, `producer-lock.json` and exact artifact verifiers. Accepted wheels and
old prefixes remain immutable and available for rollback. Clean tracked-source
exports prevent stale build directories from reintroducing removed modules.

The shared managed launcher selects the Tmux-owned a15 runtime/dependencies and
both explicit lazy factories. Agent resolves from its independent a20 prefix;
Tmux resolves from its independent selected facade. Catalog authority stays lazy.
There are no config/wire module selectors or provider/TUI/attachment queries.
Changing an Agent prefix or shared launcher requires both domain read/proof/watch
checks and scoped rollback. Do not silently drop either selected factory during
a later Tmux/Mesh rollout. Omitted domains keep Mesh's declared reference path;
a selected factory failure never falls back.

## Cached reads and validation

```sh
agent-observer service list --host-scope snap
agent-observer mesh list --scope fleet
agent-observer mesh watch --human
agent-observer mesh assess --scope fleet --mode subscribe --timeout-ms 15000
/absolute/a20-prefix/bin/python -I -B scripts/check-mesh-fleet --hosts snap starship
/absolute/a20-prefix/bin/python -I -B scripts/check-mesh-owner --installed
```

`assess` is one bounded acquisition with no route writes or retained authority.
Its success can include only one ready host; inspect per-host delivery/evidence.
The fleet gate instead requires all declared hosts ready, a complete snapshot
and watch, remote proofs and owned cleanup. Host order follows the catalog;
identity is always the full host/provider/namespace/native reference.

Use [the native comparison workflow](observation-validation-workflow.md) and
`evaluate-mesh` to compare the installed public CLI against independent daemon
metadata. Another Observer read is not a native oracle. Ordinary samples prove
their time-bounded identities/states/activity; portable fixtures and controlled
source transitions do not establish exhaustive provider coverage.

Core/local service remain Mesh-free. `CachedAgentSource` only acquires cached
Service 2 status/watch, validates socket/peer/host/clock/order/receipts and owns
per-operation cleanup. `AgentProfile` owns pure native projection/eligibility.
Mesh owns copied envelopes, digests, original-receipt remaining leases, nonce
proof and delivery lifetime. Constructors open no socket; watch copies cannot
substitute for a new checked native read after nonce admission.

The source bounds concurrent channels at 32 and observed service incarnations
at 64; exhaustion explicitly fails and requires a new publisher. Native source
scope stays fixed within an incarnation. An unchanged queued watch revision
may precede another status emission without stalling initial delivery, while
older revisions, native receipt renewal/regression and retired publishers reject.

## Scoped verification and rollback

```sh
./scripts/agent-observer-mesh-operations --host snap --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/agent-observer-mesh.json --observer-selection /absolute/chezmoi/deployments/agent-observer.json
./scripts/mesh-selection-acceptance --host snap --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/agent-observer-mesh.json --observer-selection /absolute/chezmoi/deployments/agent-observer.json --baseline /absolute/captured-baseline.json
```

The first command is read-only and verifies exact artifacts, publisher role,
rendered controls, endpoint UID/PID/incarnation and cached local delivery. The
second is a separately authorized operational procedure: authenticate the
selected bridge before stopping it, restore the exact captured reader/launcher/
unit controls, prove prior cached reads, then reselect and verify. It uses scoped
targets and excludes chezmoi scripts. Collector/provider/writer/authority controls
and unrelated Tmux/UI drift remain protected. Never choose a dated baseline or
fresh source checkout implicitly.

Networking loss revokes current positives; successful reconnection admits a new
guard/binding. Push supplies complete leased state, not every native transition
or alert. WSS, occurrence/replay notifications, attachment/actions, frontend/
device acceptance, physical suspend and post-TUI-closure proof remain separate.
