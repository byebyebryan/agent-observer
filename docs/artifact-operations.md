# Candidate artifact operations

The current read/service manifest is [Observer a11](../artifacts/observer-0.5.0a11.json).
It freezes the producer wheel independently of later operations/tooling/docs
commits. Normal read/service links and a user unit select it on Snap and Starship
through the Observer-only chezmoi operations tuple. The writer independently
retains [a16](../artifacts/observer-0.4.0a16.json); read selection does not select
or accept a writer. See the
[retention acceptance report](evidence/2026-10-09-runtime-only-retention/REPORT.md)
and [client handoff](api-v2-client-handoff.md) for source, installed, native and
operational acceptance. Provider compatibility follows
required contracts, not executable-release allowlists. Older manifests and
exact-image pilot receipts remain historical verification/rollback artifacts.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.5.0a11.json \
  --wheel /absolute/path/agent_observer-0.5.0a11-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.5.0a11.json \
  --wheel /absolute/path/agent_observer-0.5.0a11-py3-none-any.whl \
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
profile alone does not establish native adapter acceptance. The current a11
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
