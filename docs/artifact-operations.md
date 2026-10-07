# Candidate artifact operations

The current selected manifest is [Observer a7](../artifacts/observer-0.4.0a7.json).
It freezes the producer wheel independently of later operations/tooling/docs
commits. Normal read/write/service links and a user unit are selected on Snap
and Starship through the Observer-only chezmoi operations tuple. See the
[execution record](observer-operations-execution.md) and
[evidence](evidence/2026-10-07-observer-operations/REPORT.md) for source,
installed, native and operational acceptance. Provider compatibility follows
required contracts, not executable-release allowlists. Older manifests and
exact-image pilot receipts remain historical verification/rollback artifacts.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.4.0a7.json \
  --wheel /absolute/path/agent_observer-0.4.0a7-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.4.0a7.json \
  --wheel /absolute/path/agent_observer-0.4.0a7-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
```

The prefix's parent must already be canonical and owned by the operator. A new
prefix is never selected globally. Existing candidates must pass the same
byte/schema/profile checks or are rejected; no in-place repair occurs. Core
installation is offline from the supplied wheel. `--profile claude-history`
installs exactly SDK 0.2.163 from source (`--no-binary=claude-agent-sdk`), resolves
its Python dependencies and rejects a bundled native executable. Verification
never invokes providers, starts a daemon or registers hooks.

Measure an installed public read/watch stream independently of downstream clients:

```sh
candidate=/absolute/owned/parent/candidate
"$candidate/bin/python" -I -B scripts/check-read-watch \
  --prefix "$candidate" --host-scope snap \
  --provider codex --provider claude --samples 10 --readers 2 \
  --output /absolute/private/report.json
```

The installed interpreter supplies only public validation. Reports contain
aggregate counts/timing/resources; native payloads and titles remain in memory.
This is bounded sampled observation, not a lossless event feed or long-duration
performance guarantee. Use a Codex-only provider selection on Starship. Gaps,
partial sources and unsupported activity remain explicit.

Source CI checks are prepared in `.github/workflows/ci.yml`; no hosted result is
claimed before publication/push and an actual run. The [operational execution record](operational-execution-status.md)
tracks installed/native acceptance separately from tooling source checks.

`scripts/check-native-recovery` is a separate **write/native** proof, not a passive
read command. It requires an operator-established private namespace and masked
ordinary provider paths. It launches disposable contexts and stops only the
verified owned daemon. Do not run it against an ordinary provider home. See the
execution record for the exact isolation/proof matrix.
