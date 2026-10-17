# Completion relay join: first concrete failure

Status: **FAIL / actual joined completion remains unqualified**.

This status belongs to the exact historical pair below. The later
[immutable recheck](delta-sync-completion-join-recheck.md) records the corrected
Mesh source with actual Observer completion and independent Reader coverage;
it preserves the original failure and its narrower remaining gates.

This independently joins immutable Observer
`2f697d468eb3b0cb895276fd07cb746acbd23d37` with immutable Mesh
`b57c2176d60a8593fa2f85d7322655384a3227b6` on Starship. Observer's
[implemented additive source](delta-sync-completed-changes.md) already supplies
the agreed `changes_with_completion`/`CompletedChanges` surface. Mesh's source
checkpoint statement that the method is absent predates that owning handoff;
it does not require another source implementation or interface agreement.

## Exact first mismatch

The actual Agent native control and supported `AgentSyncTransportCodec` header
contain `kind`, `descriptor`, `status`, `reason`, `tag`, `cursor`, `ownerClock`,
and, for this change completion, `baseTag`/`targetTag`. They contain no
`nativeBindingDigest` field. That field belongs to transaction/head frames. The
closed control schema in `agent_observer.sync_native.FRAME` is unchanged.

Mesh `src/mesh_plus/sync/relay.py:729` reads:

```python
completion_header["nativeBindingDigest"] == target.binding
```

All six full/active zero-, one- and four-transaction joins fail at this lookup.
The generic boundary reports `sync_admission_rejected`; a separate test-only
exception tracer identifies `KeyError('nativeBindingDigest')` at that exact line
in every case. No producer code is patched for tracing. The completion's tag
already carries its native binding digest; the generic owner must check that
supported tag/binding against the requested target while preserving all existing
descriptor/tag/cursor/epoch/metadata mismatch rejection. Adding or synthesizing
a native control field would alter the closed owner contract and original bytes.

One concrete correction request was sent to Mesh. No Observer runtime or sibling
source changes are made here. This identifies the first failed check; it does
not establish that all later joined checks pass after correction.

## Reproduction and bounded results

The [probe](evidence/2026-10-16-delta-sync-source/verify_completion_relay_join.py)
uses actual Observer source/session/structural codec APIs and generic Mesh relay
APIs, with two disposable protected Unix IPC paths. Its native fixture is a
synthetic ServiceState. A trusted test controller supplies the agreed configured
descriptor, encoding and request binding directly; this does not qualify the
network hello/operation dispatcher. No private source state, native JSON wrapper
or legacy completion fallback is used. The sole private owner operation is
closing the test-owned native cache during fixture cleanup.

```sh
rtk proxy /path/to/python -B docs/evidence/2026-10-16-delta-sync-source/verify_completion_relay_join.py \
  --mesh /absolute/immutable/mesh-b57c217 \
  --observer /absolute/immutable/observer-2f697d4 \
  --output /absolute/new-report.json
```

Against the pinned pair this command intentionally exits 1: six joined errors,
zero skips on each Python 3.14.8 and 3.11.17. It keeps failures through cleanup
with cyclic GC disabled, uses the original acquisition deadlines and refuses to
overwrite its report. Source acquisition returns the expected one/two/five
original frames including completion. Relay setup succeeds, but no material or
completion delivery is emitted. All five relay heap/encoded/pending counters
return to zero. That is bounded logical cleanup evidence, not a memory/RSS gate.

The adjacent
[diagnostic launcher](evidence/2026-10-16-delta-sync-source/trace_completion_relay_join.py)
runs the same probe with test-only KeyError location tracing. The
[receipt](evidence/2026-10-16-delta-sync-source/completion-relay-join.json)
pins both immutable source inventories, loaded inputs, harness bytes and logs.
Both Mesh fixture suites independently pass 27 cases with cyclic GC disabled,
including zero final counters. Those fixtures accept a control shape that does
not expose this actual Agent mismatch. Passing fixture/source suites do not
turn the failing join into acceptance.

The fixture/server/oracle and native owner's separate allocations are outside
the receiving relay ledger. Independent Reader/fresh proof is not reached in
this failing completion probe. No populated provider/native service, installed
package, fixed SSH, aggregate resources/RSS, dense/cold/recovery CPU/bytes or
paired acceptance is established. The earlier source-only acceptance scopes,
closed agreements, schema/encoding candidate status, failed performance results
and protected a7/a23/normal roles remain unchanged. After the owning correction,
the actual source/relay/Reader, cancellation and drain cases must be rerun against
new exact immutable bytes.
