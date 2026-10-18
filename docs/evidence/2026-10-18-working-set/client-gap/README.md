# Nonterminal client gap evidence

This packet accompanies the [owning correction](../../../working-set-client-gap.md).
It preserves the upstream diagnostic rather than rewriting a prior result as a
new producer gate.

- `upstream-review.json`, `upstream-probe_gap_policy.py` and
  `upstream-gap-{314,311}.json` are byte-identical copies of Mesh's cache-only
  review of Observer `c6a238f`. The original diagnostic reports positive renewal
  after a gap; its direct translated headers are not Reader proofs.
- `before-{314,311}.{json,log}` run the first three final owning methods against
  immutable Observer `c4db120` plus only the final test-file overlay. Four failed
  checks across three methods are expected; these are semantic failures, with
  no missing API or fixture error.
- `after-{314,311}.{json,log}` run all five final owning methods against the
  final source input inventory. GC is disabled and loaded project modules are
  hashed. The exact snapshot export and reader-time checks remain domain policy
  tests; there is no fabricated descriptor or injected private SDK guard.

The two before logs retain unittest's original trailing space on a subtest
progress line. The local `.gitattributes` permits that exact raw-output detail
only for those two named files; all other diff/whitespace checks stay enabled.

Reproduction uses Python 3.14.8 or 3.11.17 and a separate immutable source export:

```sh
python -B run_probe.py OBSERVER_EXPORT MESH_SRC RESULT.json --before
python -B run_probe.py OBSERVER_EXPORT MESH_SRC RESULT.json
```

Use `git archive c4db120` for the before export and copy only
`tests/test_mesh_working_set_read.py` from the final correction into that export.
The immutable Mesh source is evidence commit
`d483351d302bdc090f62bcaa18029788b7ec75be` (runtime `03a681f9`, SDK1/a23),
whose public descriptor registry intentionally rejects this candidate profile.
No Mesh source is changed by this packet.

The accompanying receipt binds final source and output bytes. The combined
working-set regression/canonical gate includes the separately documented
encoding-refusal correction in the same final source inventory. It does not
reattribute the original P2, cost or worker-provenance results to that inventory.
SDK registration, actual working-set Reader/transport, inclusive resources/RSS,
native and immutable installed-pair qualification remain open. Normal roles,
services, providers and dark delta state remain unchanged.
