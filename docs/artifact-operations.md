# Candidate artifact operations

The current read/service manifest is [Observer a5](../artifacts/observer-0.5.0a5.json).
It freezes the producer wheel independently of later operations/tooling/docs
commits. Normal read/service links and a user unit select it on Snap and Starship
through the Observer-only chezmoi operations tuple. The writer independently
retains [a16](../artifacts/observer-0.4.0a16.json); read selection does not select
or accept a writer. See the
[completion report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
and [client handoff](api-v2-client-handoff.md) for source, installed, native and
operational acceptance. Provider compatibility follows
required contracts, not executable-release allowlists. Older manifests and
exact-image pilot receipts remain historical verification/rollback artifacts.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.5.0a5.json \
  --wheel /absolute/path/agent_observer-0.5.0a5-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.5.0a5.json \
  --wheel /absolute/path/agent_observer-0.5.0a5-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
```

The prefix's parent must already be canonical and owned by the operator. A new
prefix is never selected globally. Existing candidates must pass the same
byte/schema/profile checks or are rejected; no in-place repair occurs. Core
installation is offline from the supplied wheel. Codex is the sole live adapter;
use `--profile core`. The historical `--profile claude-history` option
installs exactly SDK 0.2.163 from source (`--no-binary=claude-agent-sdk`), resolves
its Python dependencies and rejects a bundled native executable; installing that
profile does not accept or enable a current Claude adapter. Verification
never invokes providers, starts a daemon or registers hooks.

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
performance guarantee. Use Codex-only selection on both hosts in this checkpoint. Gaps,
partial sources and unsupported activity remain explicit.

Source CI checks are prepared in `.github/workflows/ci.yml`; no hosted result is
claimed before publication/push and an actual run. The [operational execution record](operational-execution-status.md)
tracks installed/native acceptance separately from tooling source checks.

`scripts/check-native-recovery` is a separate **write/native** proof, not a passive
read command. It requires an operator-established private namespace and masked
ordinary provider paths. It launches disposable contexts and stops only the
verified owned daemon. Do not run it against an ordinary provider home. See the
execution record for the exact isolation/proof matrix.
