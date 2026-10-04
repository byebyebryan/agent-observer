# Candidate artifact operations

The accepted candidate manifest is `artifacts/observer-0.2.0a3.json`. It records
the frozen producer checkpoint and wheel independently of later operational
tooling/docs commits. It does not attest a host or authorize provider actions.

```sh
./scripts/candidate-artifact install \
  --manifest artifacts/observer-0.2.0a3.json \
  --wheel /absolute/path/agent_observer-0.2.0a3-py3-none-any.whl \
  --prefix /absolute/owned/parent/candidate
./scripts/candidate-artifact verify \
  --manifest artifacts/observer-0.2.0a3.json \
  --wheel /absolute/path/agent_observer-0.2.0a3-py3-none-any.whl \
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
