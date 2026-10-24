# Exact Observer agreement on controller R2 plus completion R3

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **AGREED at the owning contract boundary**. The exact tuple is:

- Mesh `33cb57c98ca3062f139ea1fd0c68b15bd5abd8d6`,
  `docs/delta-sync-controller-proposal-r2.md`, 31,399 bytes, SHA256
  `89b24a9f3191bcded303d33c8b2ed973335b703811185abf1186848fbd562f48`.
- Mesh `5d8cb484f8eba9fb6ca8dce9421410434cedf37d`,
  `docs/delta-sync-controller-completion-r3.md`, 5,234 bytes, SHA256
  `42375477c46c097ede85b3bbbe5cda5f03a89823fdd7358e1078064a0c34e1c2`.

The R3 manifest is SHA256
`e545403d7fe9fd5c5bf0e2b5ec88771ee4d0d4693525b7f9ed0304ab5880d037`.
The [agreement receipt](../../evidence/2026-10-16-delta-sync-source/controller-agreement.json)
pins the actual immutable bytes and verified source references. This resolves
the sole clarification in the [earlier R2 review](delta-sync-controller-r2-review.md);
that historical review and its evidence remain unchanged.

R3 replaces only the R2 `changes` command row. `maxTransactions` is an exact
integer capacity in 1..4; the result is 0..capacity. Empty success requires exact
base==target and the original self-consistent correlated completion with the
expected tag, cursor, epoch and descriptor. Missing, partial, recovery or
mismatched controls cannot become empty success. `maxBytes` is an exact integer
in 1..8,388,608 bounding the sum of original transaction frames including LF.
The original Agent completion independently fits 16,384 bytes including LF;
the entire nested Mesh control independently fits 65,536 bytes including its
envelope and transport LF. Neither bound borrows unused bytes from another.
Every byte and ancillary container/parser/copy/pin/output operation still
belongs to the unchanged shared ledgers and CPU/wire totals. The native completion
drains after the material; a controller result never substitutes for it.

These provisions match the accepted [CompletedChanges contract](delta-sync-completed-changes.md)
and existing source request, chain and control bounds. They change no Observer
source API, native request grammar, receipt, support, identity, tag, root,
selector, context, original timestamp or admission/proof authority.

The other R2 findings remain compatible: terminal cleanup receipts have bounded
independent ownership within original deadlines; normal success still needs live
work; connection/request retirement revokes every result. Minted prepaid carriers
retain conservative first-userspace-read provenance across byte ranges and reject
unknown prebuffered provenance. The restrictive generic `not_after_ms` never
extends the original two-second head or absolute fifteen-second acquisition
bound. Carrier, source, shared owner and sibling lifetimes remain separate.
Independent Reader admission and fresh nonce proof remain mandatory.

The immutable R1/R2 documents, oracle programs and vectors were verified
byte-for-byte unchanged. The previous dual-Python R1 14/34 and R2 15/32 replay
retains its original scope; neither those oracles nor the prior Mesh composition
probes were rerun or reattributed. The required owning repository check passes
940 tests with zero skips and validates 195 Markdown files. Mesh has no
runtime/test/contract/package changes relative to
the already reviewed `6fce5ed` checkpoint in this tuple review.

No controller contract conflict remains for dependent G1 implementation under
the existing authorization; no further general, A1, normalization or retirement
approval is requested. This is not runtime/API freeze or carrier/parser/mint/
bootstrap/dispatcher/result/concurrency/deadline/resource/I/O qualification.
The separately closed consuming-ref source finding stays closed. The
[current owner CPU screen](delta-sync-compact-owner-cpu.md) stays failed;
aggregate 32/64 MiB peaks, RSS, dense and deliverable 2,000-row cold recovery,
populated native/fixed SSH and exact immutable installed-pair gates remain open.
No sibling edits, schema/encoding/version allocation, normal service/provider,
selected a7/a23 artifacts or rollout changes follow from this contract agreement.
