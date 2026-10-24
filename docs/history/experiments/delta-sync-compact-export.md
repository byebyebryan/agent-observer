# Compact native owner serialization checkpoint

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

This candidate implements the Mesh-free native serializer after the accepted
[compact wire compatibility](delta-sync-compact-wire-proposal.md) and the
[streaming Reader codec](delta-sync-compact-codec.md). The raw schema, fixed
positions, logical descriptor, native roots and token algebra retain the exact
`c161090` bytes. No schema or encoding identifier is allocated or frozen here.

`ServiceState(..., sync_serialization="compact")` explicitly selects compact
baseline and journal serialization for its shared full/active sync owner.
The default remains `"expanded"`. The selection is captured when the owner is
created; there is one serializer, one bounded journal and one cached baseline
per view. There is no expanded fallback or format detection. The compact option
requires the encoded table backend so internal canonical buffers count under
both existing caps. `OwnerSyncCache(..., backend="encoded",
serialization="compact")` is the corresponding owning constructor.

No normal service launcher, CLI flag, wire request or installed source route is
changed. The existing plain/owned cached source still expects its explicitly
configured expanded acquisition grammar. Candidate source dispatch and joined
compact IPC/SSH qualification remain following work. A trusted independent Reader
can explicitly configure `AgentCompactSyncCodec` with its own fixture encoding ID
to admit these bytes; the constructor option is not an encoding allocation.

## Encoding and sparse changes

The exporter reads committed canonical key/value buffers, decodes one logical
value, applies the reviewed one-value transform and writes its compact encoding.
It never builds an expanded frame, a detached roster, or a per-cell membership
document. Its bounded before/after receipt dictionaries use full receipt keys.
All record references use keyed logical identity/birth lookups; there is no alias
scan or inferred before/after fallback.

Baseline masks group the owner's exact observation support references. The
normalizer creates those references and membership cells together. Transaction
masks visit only changed observation keys and their before/after observations.
Unchanged masks are omitted, including body-token changes; the independent Reader
derives the new field tokens and expands masks after domain admission. Retired
and new births use their separate sided references. Receipt-only renewal carries
no member edits. Expected-old hashes remain hashes of the original logical cells.

The serializer's point lookups and bounded receipt scans are separate from the
owner normalizer's retained roster/index/field work. The latter still contributes
to the failed total CPU gate. A 100-row test forbids body/record/membership scans
only during transaction serialization; it makes no O(K) claim about total owner
publication.

Canonical raw transaction IDs include the exact message-local receipt dictionary.
Counting, hashing and writing use repeatable streaming walks under the same
scratch reservation. Baseline uses counting and writing walks. Head and control
serialization is unchanged: nonce heads never enter the material exporter, and
native completion controls retain their original 16,384-byte bound.

## Ownership and limits

The shared account prepays dictionary containers, one-row decode/copy scratch,
point lookups, encoder strings/chunks/UTF-8 overlap and two output buffers before
construction. Encoder workspace counts in both the 64 MiB heap and 32 MiB encoded
limits, alongside existing internal canonical cells, stage, journal and pins.
Suspended prior-row values remain covered by a two-row high-water allowance.
Iterators close before scratch retirement; temporary reference callbacks are
detached with cyclic GC disabled. No per-roster encoded fragment list is retained.

Output exceeding the unchanged frame or journal bounds is rejected. Optional
journal capacity refusal keeps the new material head and reports
`baseline_required`; it never emits another encoding. Cold baseline refusal
leaves the committed head unchanged and refunds its construction scratch.
The native encoded budget continues to include slow-peer pins through the
existing owner/runtime accounting; this checkpoint does not requalify those
aggregate peaks.

## Bounded evidence

Ten new tests exercise actual owner output: full/active baseline restoration
against separately constructed expanded owners; warming scopes; receipts,
token-only body changes, row insertion/removal and all table roots; canonical raw
IDs; unchanged head/control bytes; actual compact Reader staging and fresh proof
confirmation; malformed expected-old/root rollback; serializer-only scan counts;
preallocation/frame refusal and explicit optional-journal recovery. Tests disable
cyclic GC, retain errors and check deterministic final accounting. The Reader
uses immutable Mesh `05ad6fc8db1725afd6aac19435af83e4c0eb46eb`; its existing
test-owned proof challenge setup is disclosed. These tests use no normal native
provider or selected service.

The [cold export probe](../../evidence/2026-10-16-delta-sync-source/probe_compact_owner_export.py)
uses fixed synthetic Service 4 fixtures at 100/500/2,000 identities. Full compact
frames are 142,313 / 687,515 / 2,739,021 bytes; corresponding legacy full frames
in this exact fixture are 168,077 / 826,477 / 3,297,477 bytes. The active view
selects ten identities and is 19,545 bytes at each scale. Those fixture rows
contain 710 / 3,510 / 14,010 full membership cells, not nine current fields on
every identity. Full and active cold native outputs fit together in this source
screen; no predecessor, overlapping new stage, slow peer, relay or Reader was
present. The independent large-DOM oracle runs after the recorded owner account
peak and is explicitly outside aggregate memory evidence.

The [byte-bound manifest](../../evidence/2026-10-16-delta-sync-source/compact-export.json)
records exact source inputs, both interpreter gates and cold output/account
screens. Previous matched producer CPU failures remain failures. This checkpoint
does not establish dense nine-field CPU or capacity, deliverable 2,000-row
recovery, whole pipeline physical lifetime/RSS, populated IPC/fixed SSH,
installed paired artifacts, native provider correctness, producer readiness or
consumer adoption. The separate [consuming-pin revocation gap](delta-sync-source-pin-revocation.md)
also remains open pending its one public Mesh status-query agreement.
