# Candidate artifact operations

The current collector/read manifest is [Observer a18](../artifacts/observer-0.5.0a18.json).
Codex-only collector and a18/[Mesh a11](../artifacts/mesh-0.1.0a11.json) reader
prefixes are independently accepted on Snap and Starship. Separate a16/a10
bridges, the shared Mesh CLI and historical writer retain their selections.
The [retirement report](evidence/2026-10-11-claude-retirement/REPORT.md) distinguishes
source, exact immutable artifacts, native and scoped operational gates. The
[client handoff](api-v2-client-handoff.md) supplies current commands. Native
compatibility binds required contracts, not release-number allowlists.
Archived manifests and their own verifiers keep historical/rollback scope.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.5.0a18.json \
  --wheel /absolute/path/agent_observer-0.5.0a18-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.5.0a18.json \
  --wheel /absolute/path/agent_observer-0.5.0a18-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
```

The prefix's parent must already be canonical and owned by the operator. A new
prefix is never selected globally. Existing candidates must pass the same
byte/schema/profile checks or are rejected; no in-place repair occurs. Core
installation is offline from the supplied wheel. Both hosts select Codex with
`--profile core`; the retired `claude-history` install profile is rejected.
Verification rejects installed Claude SDK/native modules or bundled executables,
checks exact package bytes/schemas and never invokes a provider, starts a daemon
or registers hooks. The separate optional reader installs the accepted Mesh
wheel/dependencies explicitly and uses the archived Mesh verifier. Retained
bridge artifacts keep their own historical dependency profiles; their archived
verifiers are not rewritten or used to enable Claude collection.

The installer supplies an isolated prefix; managed selection additionally needs
an immutable `artifact/` archive. Copy the exact wheel, the manifest under the
canonical name `manifest.json`, and `scripts/candidate-artifact` into that private
same-user directory. Bind the verifier's checksum and path in the managed tuple.
A missing canonical manifest fails upgrade preflight before any unit is stopped;
the versioned repository manifest filename alone does not satisfy that layout.

Measure an installed public read/watch stream independently of downstream clients:

```sh
candidate=/absolute/owned/parent/candidate
"$candidate/bin/python" -I -B scripts/check-read-watch \
  --prefix "$candidate" --host-scope snap \
  --provider codex --samples 10 --readers 2 \
  --output /absolute/private/report.json
```

The installed interpreter supplies only public validation. Reports contain
aggregate counts/timing/resources; native payloads and titles remain in memory.
This is bounded sampled observation, not a lossless event feed or long-duration
performance guarantee. Use Codex on both hosts. Gaps,
partial sources and unsupported activity remain explicit.

Source CI in `.github/workflows/ci.yml` passes hosted core/optional-Mesh jobs
on main and the original a18 source tag. The exact a18 wheel/manifest are
published as a GitHub prerelease and freshly downloaded/verified on both hosts.
Later operator/documentation commits retain separate source provenance. The current
[operational cleanup report](evidence/2026-10-11-ops-cleanup/REPORT.md) distinguishes
installed/native acceptance, collection/subscriber costs and publication.
The earlier [operational execution record](operational-execution-status.md)
retains its historical pilot scope.

`scripts/check-native-recovery` is a separate **write/native** proof, not a passive
read command. It requires an operator-established private namespace and masked
ordinary provider paths. It launches disposable contexts and stops only the
verified owned daemon. Do not run it against an ordinary provider home. See the
execution record for the exact isolation/proof matrix.

## Managed selection tooling

The current host selection is configuration-owned in
[dotfiles deployments/agent-observer.json](https://github.com/byebyebryan/dotfiles/blob/main/deployments/agent-observer.json).
Collector, reader and writer prefixes are independent; use the selection rather
than inferring one from another. The reader and bridge retain independently
verified immutable archives; reader selection does not require a matching bridge
package version. Source checkout identity is separate from
installed runtime identity. Use a checkout of this repository at the reviewed
operations-tooling commit on each host; no Snap development path is required.

```sh
./scripts/agent-observer-operations verify --host snap --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/agent-observer.json
./scripts/agent-observer-operations apply --host snap --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/agent-observer.json
```

`verify` is passive; `apply` defaults to a dry run. Live selection requires
`--apply --snapshot /absolute/private/new-backup`, and upgrades additionally
require `--previous-tuple /absolute/private/previous.json`. Retired provider
profiles are accepted only as explicit authenticated prior/rollback metadata,
never a new desired collector selection. A snapshot uses a new
owned 0700 directory beneath an existing canonical parent. Six targets are in
scope: read/write/service links, workspace JSON, user unit and enablement link.
The projection excludes unrelated externals. It never changes frontend selection,
provider settings, hooks, native sessions or lingering.

Installed wheel/profile/manifest/verifier checks precede selection. Existing
controls must match the previous render; executable, argv, UID and PID birth
must match before stopping the owned unit. Missing canonical artifact archives,
changed workspace/unit bytes, foreign prefixes and changed incarnations reject
before stop. `rollback --snapshot ...` verifies all selected controls, restores
only captured targets and restarts the verified prior publisher. Source remains
on the candidate. Reselection reuses the snapshot only after exact restoration;
review drift and explicitly reselect before any broader configuration apply.

The synthetic operations self-test covers ownership, arguments, process birth,
permissions, foreign prefixes, restore/reselection and unrelated externals.
It does not establish live deployment, native delivery, physical suspend or
UI acceptance. Cached `service list/status/watch` reads never start a collector;
direct reads perform collection. Authorized unit recovery creates a new service
incarnation, and clients must discard previous authority and honor warming,
partial, stale and gap states.
