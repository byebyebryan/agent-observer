# Optional Mesh state read client

Historical API 2 / wire 4 / Service 2 checkpoint. Current read-client work uses the
[API 3 handoff](api-v3-client-handoff.md); current role/profile adoption is recorded
in the [native timing receipt](evidence/2026-10-13-native-timing-rollout/REPORT.md).
The commands/artifacts below retain their original version bounds.

The current managed selection uses Codex-only Agent `0.5.0a20` readers and owned
Agent publication with Mesh `0.1.0a15` and the explicit Observer-owned profile.
The a18 collector, Tmux factory and historical writer remain independent.
The [publisher handoff](mesh-publisher-operator-handoff.md) records cached reads,
complete fleet gates and rollback; old a18/a11 reader and a16/a10 bridge artifacts
remain retained. The [retirement report](evidence/2026-10-11-claude-retirement/REPORT.md)
records exact artifacts, native/cached pull/push and scoped operational proof.
Frozen supplied-data provider vocabulary remains valid; no Claude native
collection is implemented. The SDK v1 acceptance and earlier selections below
retain their historical bounds.

The [accepted a12/a4 candidate](evidence/2026-10-09-mesh-integration/REPORT.md)
was selected on Snap and Starship. Both bridge units were enabled. Collection
then stayed a11 and the writer a16; the shared SSH Plus authority stayed a1.
The [a13 read-delivery pass](evidence/2026-10-09-read-delivery/REPORT.md)
then independently selected the reader without changing the a4 bridge or its a12 prefix.
The exact [a13 release](https://github.com/byebyebryan/agent-observer/releases/tag/v0.5.0a13)
adds timed human watch; raw envelopes remain unchanged.
These immutable wheels are archived locally on both hosts. The following read
delivery pass publishes [Observer a12](https://github.com/byebyebryan/agent-observer/releases/tag/v0.5.0a12)
and [Mesh a4](https://github.com/byebyebryan/mesh-plus/releases/tag/v0.1.0a4)
as GitHub prereleases with exact wheels and manifests. PyPI publication is not
implied; install the two downloaded wheels explicitly for Mesh commands.

The selected SDK v1 reader uses `mesh-plus>=0.1.0a11,<0.2` and an explicit
Observer-owned pure Agent profile. It uses the same profile through configured
readers, guards, validation, current selection and native reconstruction. The
Mesh reference publisher is retained independently; the accepted package/native
and operational gates are in the [execution status](mesh-sdk-v1-integration-status.md).
The original a12 dependency floor was a4. Install the
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
An explicit `--local-host` selects standalone local delivery even with the
default `fleet` scope. Omit it to resolve the actual fleet through the authority.

Python clients using the optional SDK supply
`agent_observer.mesh_profile.AgentProfile()` to `mesh_plus.api.configured_reader`,
`ReadGuard`, `validate_response`, `current_sessions` and `reconstructed`. Reuse
one profile consistently; import it only when networking is requested. The
Observer profile owns pure native validation, identity, projection and receipt
selection. SDK 1 owns compulsory generic admission, proof, expiry and cleanup.
Never treat `AgentCodec.validate_bridge` alone as a transport/proof validator.
Keep original clocks and component receipts; consumers own BOOTTIME timers,
presentation, reconnect and guard revocation. Publisher ownership source is
implemented in the private a19 candidate; normal bridge selection remains
independent pending its [execution gates](mesh-sdk-maintenance-adoption-plan.md).

The selected a20 client supplies `mesh assess --mode snapshot|subscribe` with
`--timeout-ms 1..60000` and the normal scope/source/socket/authority options.
It requires Mesh's `assess_configured` capability, supplied by the reviewed a15
input and released a13 diagnostics. The selected a20/a15 CLI offers this command;
retained a18/a11 rollback clients do not. For an accepted prefix:

```sh
/absolute/a20-prefix/bin/agent-observer mesh assess --scope local --local-host snap --mode snapshot --timeout-ms 5000
/absolute/a20-prefix/bin/agent-observer mesh assess --scope fleet --mode subscribe --timeout-ms 10000
./scripts/check-mesh-owner
```

Assessment includes catalog resolution in the acquisition budget, supplies the
pure owner profile and disables route writes. Its redacted JSON distinguishes
delivery acquisition, current/expired/nonpositive receipts and partial hosts.
Success means at least one delivery was acquired; inspect the per-host sample
before claiming complete coverage. Cleanup closes owned connections and revokes
watch authority before returning. This one sample neither retains authority nor
establishes native completeness. The conformance helper uses independent portable
profile/network cases; `--installed` prevents checkout imports. Native acquisition,
fixed SSH, resource and operational acceptance remain separate.

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
Coverage, delivery and view qualifications are printed before the rows. Ready
transport and partial native coverage do not establish an exhaustive census.

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

## Managed reader and bridge verification

The Agent-owned helper is `scripts/agent-observer-mesh-operations`. Supply all
configuration inputs explicitly:

```sh
./scripts/agent-observer-mesh-operations --host snap --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/agent-observer-mesh.json --observer-selection /absolute/chezmoi/deployments/agent-observer.json
```

This verifies the independently selected reader and resident bridge artifacts,
archived verifier hashes, UID/socket-peer and process-incarnation evidence,
rendered controls and independent collector selection. Each retained bridge
supplies its own archived dependency profile; it does not inherit the reader
profile. `--selection` supplies the candidate JSON; `--candidate` checks artifacts and
rendered targets without requiring live controls to match. No dated rollback
directory is chosen implicitly.
`scripts/mesh-selection-acceptance` additionally requires `--baseline` and the
same explicit source/selection inputs. It is a write/native acceptance procedure
with captured controls and owned restart/rollback guards, not an ordinary
read-only check. Shared Mesh CLI rollback is coordinated with the Tmux pair;
Agent collector and writer remain independently selected.

Mesh owns transport, authority, `doctor` and `probe`. Agent owns its reader and
bridge selection. Artifact checks, cached native delivery, sustained resources,
physical suspend and Agent Plus migration retain separate acceptance.
