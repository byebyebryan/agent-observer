# Candidate artifact operations

The current collector manifest is [Observer a15](../artifacts/observer-0.5.0a15.json).
The read CLI independently selects [a17](../artifacts/observer-0.5.0a17.json)
with [Mesh a11](../artifacts/mesh-0.1.0a11.json). Separate a16/a10 bridges and the
shared Mesh CLI retain their selection. The
[SDK integration report](evidence/2026-10-11-mesh-sdk-integration/REPORT.md) records
exact installation, native delivery and reader-only rollback acceptance.
It freezes the producer wheel independently of later operations/tooling/docs
commits. The normal service link and user unit select a15 on Snap and Starship
through the Observer-only chezmoi operations tuple. The writer independently
retains [a16](../artifacts/observer-0.4.0a16.json); read selection does not select
or accept a writer. See the
[Claude collection acceptance report](evidence/2026-10-10-claude-collection-repair/REPORT.md)
and [client handoff](api-v2-client-handoff.md) for source, installed, native and
operational acceptance. Provider compatibility follows
required contracts, not executable-release allowlists. Older manifests and
exact-image pilot receipts remain historical verification/rollback artifacts.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.5.0a15.json \
  --wheel /absolute/path/agent_observer-0.5.0a15-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.5.0a15.json \
  --wheel /absolute/path/agent_observer-0.5.0a15-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
```

The prefix's parent must already be canonical and owned by the operator. A new
prefix is never selected globally. Existing candidates must pass the same
byte/schema/profile checks or are rejected; no in-place repair occurs. Core
installation is offline from the supplied wheel. Starship selects Codex with
`--profile core`; Snap selects Codex and interactive Claude with
`--profile claude-history`. That option
installs exactly SDK 0.2.163 from source (`--no-binary=claude-agent-sdk`), resolves
its Python dependencies and rejects a bundled native executable; installing that
profile alone does not establish native adapter acceptance. The current a15
report independently accepts its installed native subset. Verification
never invokes providers, starts a daemon or registers hooks.

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
performance guarantee. Use Codex on both hosts and Claude only on Snap. Gaps,
partial sources and unsupported activity remain explicit.

Source CI checks are prepared in `.github/workflows/ci.yml`; no hosted result is
claimed before publication/push and an actual run. The [operational execution record](operational-execution-status.md)
tracks installed/native acceptance separately from tooling source checks.

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
require `--previous-tuple /absolute/private/previous.json`. A snapshot uses a new
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
