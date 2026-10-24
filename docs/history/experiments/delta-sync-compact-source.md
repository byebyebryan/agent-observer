# Explicit owned compact source

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

`agent_observer.sync_compact_source.CachedCompactAgentSyncSource` supplies one
explicitly configured compact full or active native endpoint. It inherits the
expanded source's `(host, path, view="full", timeout=15)` constructor and its
supported `open_session(inputs)`, `inspect()` and `aclose()` surface. Owned
sessions retain the existing baseline, exact `CompletedChanges`, fresh head,
watch and scoped close interfaces. Constructing this source does not configure
or start a service, choose a source name, allocate an encoding ID or install a
route. The [owner serializer](delta-sync-compact-export.md) must be independently
configured with `sync_serialization="compact"`.

The owned client captures a static parser function, retaining no bound parent
callback. Compact material uses the existing pure compact structural scanner
under the caller's receive, parser and header reservations. Bounded receipt
dictionaries are checked and discarded from the public logical header; body
values, reference joins, expected-old values, masks, tokens and roots remain
unadmitted. The original native frame is sealed once. The existing capture
limit also covers compact dictionary scratch in the encoded parser reservation.
Nonce head requests use the original expanded head scanner and frame bounds;
they do not enter a compact material scanner or load the body schema.

Ordinary unowned `baseline`, `head_after_nonce`, `changes` and `watch` methods on
this compact source reject `sync_source_input_owner` before I/O. The explicitly
selected compact route requires prepaid opaque input ownership. The ordinary
`CachedAgentSyncSource` still selects its strict expanded parser and byte APIs.
Neither route sniffs an encoding or falls back to the other representation.

Trusted relay composition selects this source together with
`CompactAgentSyncTransportCodec(view, encoding_id=..., expected_host=...)`.
Independent Reader composition selects `AgentCompactSyncCodec` with the same
configured encoding. Existing R2/R4 public callbacks and immutable native
descriptor/header conventions are unchanged. No CLI, controller dispatcher,
factory default, source-name policy, schema/encoding freeze or selected service
is added by this source checkpoint.

## Bounded verification

The [receipt](../../evidence/2026-10-16-delta-sync-source/compact-source.json) records the
exact source inputs, immutable Mesh counterpart and validation logs. Synthetic
`ServiceState` fixtures use the actual disposable native `Runtime` Unix request
dispatcher with collection disabled. Seven methods cover:

- Full and active baselines plus zero, one and four original transactions and
  the exact completion bytes returned by the dispatcher, including its fresh
  clock sample. Ordinary independent cache admission reaches the target root;
  changed material requires a new original head before proof confirmation and
  lossless public DTO equality.
- Expanded/compact route mismatches fail without fallback; ordinary compact
  byte methods fail before opening a socket; standalone source import brings
  in no Mesh, service, collection or provider module.
- A 200,000-character invalid opaque body is forwarded under the structural
  role without whole-body decoding or schema admission, then rejected by the
  independent Reader. The nonce path forbids compact scanner/schema work.
- Owned watch close revokes its delivered compact update and preserves a prior
  baseline ticket. GC stays disabled for IPC cases, held failures survive
  teardown, Reader counters return to zero and native owner scratch retires.

The proof carrier and nonce bootstrap are disclosed test scaffolding. Native
head bytes come through the actual source, but the tests use a private generic
native-byte pin and private Reader nonce setup. They do not qualify a relay,
authenticated controller, fixed SSH route or populated native provider. The
native owner, test oracle and Reader have separate ledgers; zero final counters
do not establish aggregate 32/64 MiB peaks, RSS, dense capacity or CPU savings.

The initial test draft compared separately generated completion controls; their
fresh owner clock samples correctly differed. The final test records the actual
dispatcher return and compares every sealed original frame with that return.
Initial diagnostics are preserved separately, with no producer defect inferred.

The independent [consuming-pin registry defect](delta-sync-source-pin-revocation.md)
is unchanged by parser selection. Its agreed public retirement query and scoped
source fix remain separate work. Original CPU failures, dense 2,000-row recovery,
aggregate resource, native/fixed-SSH and immutable installed-pair gates remain
open. Normal a7/a23, full/Tmux/349/writer and provider workflows are untouched.
