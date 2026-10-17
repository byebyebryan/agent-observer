# Agent structural transport facade

Status: **G1 source implementation; relay/controller and installed qualification
remain separate**. This implements the Observer-owned structural/HeaderRef seam
of the accepted [R4 contract](delta-sync-relay-r4-review.md). Coordinator A1
closure is RLCD `818bdb7a8e2f5585386b012ca4b7ef3770b261aa`, addendum revision 3,
SHA256 `83a0963d9bf66185931a84a407623faab041df399a22c637998c97ebfe2a3bbe`.
It preserves the separately accepted owned-source/watch-close prerequisite.

## Explicit configuration and public surface

`agent_observer.sync_transport` imports no Mesh, provider adapter, service or
engine. Its supported surface is:

```text
AgentSyncTransportCodec(view, *, encoding_id, expected_host=None)
codec.encoding -> immutable integer-only JSON mapping
codec.header(raw: bytes, budget) -> NativeTransportTicket
codec.head(raw: bytes, budget) -> NativeTransportTicket
ticket.header -> HeaderRef
header.materialization_bytes -> int
header.materialize() -> dict
ticket.close() -> None
```

`view` explicitly selects `full` or `active`. The trusted caller supplies the
encoding ID; this module allocates no production encoding identifier or schema
and never guesses a codec from wire data. `encoding.schema` is the exact bundled
expanded-native schema digest; `encoding.nativeDescriptor` is the canonical
native descriptor digest for that view. `encoding` is a Mesh-free immutable
mapping with the R4 `id`, `schema`, `nativeDescriptor` fields. Configured codecs
are immutable. Generic transport captures its supported adapter/configuration
and callback identities through its own public interface.

Mesh confirmation `e-eab9a9d2` closes the pending Mapping/adapter compatibility
question for exact Observer `af2bc7bf9316bc0fb58c83ec8f560a83788467e4` and Mesh
runtime `ea25fcb07bac14162453b0f8626aa416db10edf3`. Mesh accepts the public
`Mapping` protocol, captures canonical encoding bytes and callback identities,
and binds `encodingDigest = SHA256(C(encoding))`. No Mesh-specific frozen wrapper
is required. Trusted composition passes the explicitly configured source,
`SyncDescriptor` and `native_codec`; the generic relay imports no Observer
modules or profile/semantic hooks. `open_session(inputs)` is synchronous and
structural. `fixture-expanded/1` remains a source-test identifier; this
confirmation allocates no production expanded/compact encoding ID and adds no
wire sniffing or fallback.

The [compatibility receipt](evidence/2026-10-16-delta-sync-source/transport-mapping-agreement.json)
pins the exact source/report inputs and records the counterpart confirmation.
Its reported controlled two-IPC/independent-Reader checks retain their original
source provenance and are not independently rerun or broadened by this receipt.
Later completion-transfer and compact-source/controller work keep their separate
coordination and implementation boundaries.

For an authenticated source the caller passes its exact configured host. The
existing `CachedAgentSyncSource.open_session(inputs)` remains the Mesh-free,
structural prepaid-source protocol; it does not choose cache versus relay role.
Its UID/socket/local boot/time checks and request/order/nonce/watch lifecycle
guards remain independent. The codec itself opens no sockets, reads no clocks,
selects no services and acquires no provider data.

Ticket/header constructors are not minting APIs. The codec returns independently
owned structural tickets, with no profile, material cache, semantic query,
admission memo, proof authority or raw-byte export.

## Structural checks and fresh-head boundary

`header` accepts one exact bounded native line, including its one terminal LF.
It reuses the lexical expanded scanner: complete strict UTF-8/integer-only JSON
grammar, depth/node limits, closed root/table registries and bounded decoded
native headers. Baseline projections contain all eight table names, with empty
arrays except bounded original receipts. Transaction projections contain all
eight empty operation arrays. Opaque material remains unadmitted and unexpanded.

`head` has its own 49,152-byte gate before scanning. It accepts only native head
or explicit control, rejects material before header validation/decoding and
never creates a material plan or visits bodies. Its closed head/control fields
retain descriptor/tag/challenge, owner clocks, original receipts/cohort heads,
native attenuation and explicit failure/control status. Native structural
binding/self-consistency checks do not turn the ticket into an admitted proof.
Fresh nonce acquisition, elapsed attenuation, request/channel/incarnation checks
and independent Reader material/proof admission remain with their R4 owners.

No opaque schema/domain/join/alias/expected-old/token/table/cohort/root check can
be skipped because scanning succeeded. Source tests include structurally valid
full/active material with independently recomputed roots but invalid Agent
aliases, and wrong native roots: tickets can be scanned, while the configured
independent Reader rejects both. This is synthetic boundary evidence, not an
implemented relay or actual populated transport gate.

## Ownership, copies and retirement

The caller supplies the same aggregate `reserve(amount, encoded=0)` budget and
owns the raw input pin. The facade prepays its ticket/control before construction
and keeps parser scratch charged until private callback/error frames unwind.
It retains only the bounded projection, never raw bytes or opaque material.
Ticket close drops that projection before refunding its independent header lease.

The header advertises a conservative heap bound for a complete detached copy
and copying scratch. The caller must reserve that bound before materializing
and keep the separate copy credit until the dictionary and all retained children
retire. Extra encoded serialization/copies require their own encoded/heap credit.
For example, with an already borrowed input and a live same-ledger budget:

```python
ticket = codec.header(raw, budget)
copy_credit = document = None
try:
    copy_credit = budget.reserve(ticket.header.materialization_bytes)
    document = ticket.header.materialize()
    # Inspect only bounded structural fields while the detached copy is charged.
finally:
    document = None  # Also retire any retained child aliases/error frames.
    if copy_credit is not None:
        copy_credit.close()
    ticket.close()
```

Closing a ticket revokes new header/property access immediately. Reentrant or
concurrent close during a materialization keeps the physical header lease live
through copy unwind and prevents late successful return. A caller-retained copy
continues under its own credit after ticket close. Retained header handles use
weak ticket references and cannot retain closed metadata/budgets. A failed scan
clears unwound decoder/validation frames before deferred credits are released,
including held errors with cyclic GC disabled.

Raw input and downstream output pins remain owned by their source/relay until
actual retirement/drain, independent of this ticket's close. No source session,
watch or ticket closes a shared input owner, sibling, parent service or provider.
All caller and facade allocations remain inside the unchanged shared 64 MiB
heap and 32 MiB encoded caps; the budget argument is not another allowance.

## Explicit compact structural facade

`agent_observer.sync_compact_acquisition.CompactAgentSyncTransportCodec` provides
the same constructor, immutable encoding, header/head and ticket surface for the
[candidate compact wire grammar](delta-sync-compact-wire-proposal.md). It is
unselected and does not allocate or freeze the proposed encoding ID/schema.
The trusted caller still supplies `encoding_id` and view explicitly. Its encoding
schema digest is the exact bundled compact raw-schema digest; its logical native
descriptor digest is unchanged. The expanded facade/defaults remain strict.

This scanner admits only bounded structural headers. Material messages require
their exact extra `receiptRefs` root field. Each before/after dictionary is at
most 32 distinct full receipt keys; a baseline before dictionary is empty.
Dictionary syntax and full key types are checked, then the dictionaries retire
without entering the exported logical header. The Reader's normalization plan
must independently retain/check its own dictionaries against admitted before and
provisional after state. A structurally valid missing receipt, stale alias/birth,
wrong mask or corrupt opaque body supplies no authority and remains a required
Reader rejection. No plan, profile or semantic cache is available to this facade.

The dictionary has a 40 KiB raw header capacity bound, including two maximal
32-key lists with fully escaped component strings. It remains inside the existing
384 KiB captured-header, 64 MiB heap and message limits. Complete byte-framing,
strict lexical JSON and closed root/table checks use the same scanner as the
expanded facade. Material bodies remain opaque. Wrong explicit encoding shape
fails; no name/byte sniffing or fallback is added. Head/control use the original
separate head-only scanner and unchanged bytes, with no compact dictionary or
material-plan construction on the nonce path.

The compact path reuses the existing prepaid ticket/control, detached-copy,
immediate revocation and deferred physical header-credit retirement rules above.
Source tests compare all eight candidate baseline/ten transaction headers with
their logical projection, isolate head-only decoding, reject malformed/bounded
dictionaries before expensive decode, refuse unpaid construction, keep siblings
usable, and retire failed scanner frames with cyclic GC disabled. These are
structural source tests, not complete raw-schema/domain admission or proof of
aggregate physical allocation. The
[compact scanner evidence](evidence/2026-10-16-delta-sync-source/compact-transport.json)
pins this separate component checkpoint and its exact source dependencies.

The native serializer, cached-source encoding configuration, streaming semantic
NativeCodec/profile branch and actual generic relay/controller wiring remain
separate G1 work. Existing A1/R2 contract closure authorizes that work; this
component does not reopen their approval or establish runtime/installed acceptance.

## Qualification boundary

The source [evidence record](evidence/2026-10-16-delta-sync-source/transport-facade.json)
pins code/tests, exact A1 inputs, Python checks and the counterpart source used.
It covers pure import/role, full/active headers, bounded copying, strict framing,
head isolation, preallocation rejection, late/reentrant/concurrent close,
error-frame retirement, GC-disabled held headers and independent raw rejection.
It does not establish the generic relay/controller, actual relay-owned input
types/output drains, fresh network proof/capsules, full intake/output memory,
RSS, dense/cold/recovery CPU/bytes, native IPC/fixed SSH or an installed pair.
Those remain required before adoption. Normal a7/a23/full/Tmux/349/writer/provider
selections and all rollout/physical gates remain unchanged.
