# Observer review of the A1 R2 and R3 relay tuple

Status: **source/role/clock/lifecycle direction compatible; one exact public
header-access completion remains**. This answers Mesh event `e-0ce299ca` under
the existing owning review. Joint API agreement and the coordinator's A1 record
still precede dependent relay implementation. No producer acceptance is given.

## Exact inputs

Immutable retrieval on Starship verified:

| Input | Commit | SHA256 |
| --- | --- | --- |
| Mesh `docs/delta-sync-relay-api-r2.md`, 27,392 bytes | `e68b26417035b9dd78b1a50c1f228120926bac52` | `8616bfba7c05dcf8982e431309bcd0bdf354c91bc023fdf0fcf85dcbe4c7abdd` |
| Mesh `docs/delta-sync-relay-lifecycle-r3.md`, 12,316 bytes | `50b6e686ecb45ca91f4f694d7d0fd76c679fbff1` | `eb5c217c544bbe10766c7c0f32d574294412c6f6230c7ad6b95a2a57483c0c9f` |
| R2 stdlib oracle | `e68b26417035b9dd78b1a50c1f228120926bac52` | `defeb1d4c67b811a3fefc3f3586759d8005fd758cbe19bf110bbdca2469defcf` |
| R2 arithmetic fixtures, 12,690 bytes | `e68b26417035b9dd78b1a50c1f228120926bac52` | `968ea89860e86fc8493681f6a8edc472c99794fbf580275d9bde5a2efa29c39d` |
| R2 review manifest | `e68b26417035b9dd78b1a50c1f228120926bac52` | `92035073d95392fd31d53d72118b5eb82855baae3182234917710fd94157a6ee` |

R3 is an explicitly identified second input. It replaces R2's channel-wide
acquisition signatures and adds bridge bootstrap; it is not an implicit edit
to the requested R2 bytes. R2 alone leaves those lifetime questions open. This
review reads the complete stated R2+R3 candidate without asking Mesh to rewrite
or resend its historical R2 packet.

The role reference remains RLCD A1 revision 2, `665f6caa`, SHA256
`6eaa408376f91bb7c5e4276812927fd2bfce2445412fb02a211bea22a5e52aef`.
Frozen G0 remains `a376bc848a78027d4fd723e8a2959dbbc4e00114da132d3a5d2733a6ebce2eb6`;
the agreed common input contract remains
`7f7751ecd9df93277a3e7110ca72ebfda343d38fa629cd0212ec40b3a8f1d124`.
The [original packet review](delta-sync-relay-review.md) remains historical.
The [new evidence](evidence/2026-10-16-delta-sync-source/relay-r2-review.json)
records exact input/source hashes and arithmetic outputs.

## Compatible ownership and source shape

The explicit trusted factory, shared ledger and distinct relay input types
address the original minting/consuming-boundary gap. Acquisition methods acquire,
structurally inspect and send results; no public raw export is needed. The relay
has no profile callbacks, material cache, semantic query or admission-reuse
capability. Existing material publishers keep independent G0 admission. Reader
material/domain, old-token, root, receipt, clock, nonce and request validation
remains complete.

The type parameter `AcquisitionInputs[RefT]` fits the implemented Mesh-free
source. Source code needs only `buffer_heap`, reservation credit/resize/seal/
close and ref `nbytes`/close. `seal` supplies the concrete opaque ref type;
baseline/control tickets and watch/change/head results do not infer its role.
The owned resync result remains a control variant. Plain-byte acquisition stays
strict and unchanged. No production RelayInputOwner or new transport codec is
implemented or qualified by this review.

Valid bounded tuples transfer all refs; malformed shape/count/type rejects
before transfer. Independent raw versus header/ticket credit remains charged
through actual retirement. Output pins/copies stay charged through drain.
Retirement forbids new receive/resize/seal/consume and late output; unsealed
buffers and consuming pins retain credit through awaited cleanup. A source
session closes its own refs/leases, not the shared owner, sibling or service.

R3's acquisition capsule fits source operation-scoped cancellation and returned
ref ownership. A capsule can cancel/await its own tasks and close its returned
tickets without closing an unrelated watch or shared source session. No mandatory
child-scope source API is needed. Actual relay capsule/watch/output isolation
still needs implementation tests. The existing 20 controlled Observer source
tests cover the narrower tracking, late-result, cancellation and sibling boundary.

The separate common-cache `InputOwner.close()` publication gap reproduced at
Mesh `32090d6` remains an implementation issue. R2's distinct byte-only relay
owner does not import semantic-cache authority or qualify that implementation.
Neither a shared protocol nor these choices grants resource acceptance.

## Native identity, scanner, proof and lifetime

The structural scanner can traverse bounded complete JSON while retaining only
bounded header/receipt data, without an opaque body/operation roster. Native
host/UID/socket, owner/boot/time namespace, descriptor/view, complete original
provider/namespace context and tag/cursor continuity remain exact. No scope or
body identity is inferred from an alias or transport health. Reader checks
every deferred native/domain value, support, token, table, cohort and root.

Fresh head follows the exact Reader challenge. Within-binding movement returns
the actual fresh tag; binding/incarnation/context replacement reports change/
failure. The native/source two-root formula stays unchanged. Bridge clock uses
the same authenticated boot/time scope, with only `time:[digits]` to
`time:digits` conversion. Exact bounded attenuation coverage and strict integers
give `max(0, native_remaining - elapsed)` without provider-health or support
interpretation. Reader whole RTT/margin and original receipts still bound
authority. A native head control/failure cannot become a proof.

R3 separates channel/watch lifetime from cold/warm/recovery acquisition lifetime.
Each capsule has one immutable local deadline; the Reader retains its original
absolute 15-second end-to-end bound. Setup/watch startup do not create serial
extra acquisition budgets. Each proof keeps its two-second bound. Stop/catch-up/
baseline fallback and at most one fresh proof retry retain the same logical
acquisition deadline. Proof performs no full export, body stage or predecessor
retirement. Known movement/failure revokes affected Reader authority.

Factory-minted immutable bridge ID, authenticated hello nonce, exact offer and
complete nine-field request binding resolve R2's bridge bootstrap gap. Reconnect
changes channel epoch; a new factory changes bridge ID. Native owner epoch is
independent. Hello/setup grants no material or lease authority; reconnect transfers
no admission capability to a new binding.

## Exact completion still required

R2 names `NativeTransportTicket.header: HeaderRef` and describes revocation, but
does not specify public methods for reading the header or charging a detached
copy. The source's existing `AcquisitionHeader.document` is a borrowed owning
projection; it is not an implicitly interchangeable generic HeaderRef API.
The relay must not need a private field or an uncharged full header copy.

Use the same concrete public completion already proposed in the
[normalization decision](delta-sync-normalization-decision.md):

```text
NativeTransportTicket.header: HeaderRef
HeaderRef.materialization_bytes: int
HeaderRef.materialize() -> dict
NativeTransportTicket.close() -> None
```

Both header methods reject after ticket retirement. The advertised cost covers
sufficient prepaid credit for the bounded structural copy before allocation.
The caller retains that independent credit until its copy retires; closing the
ticket does not refund a surviving detached copy. The ticket keeps its own
header lease, no opaque raw payload, body/operation roster or authority. The
dictionary contains only the agreed kind-specific structural projection;
head/control status remains explicit. This is an API completion for agreement,
not an implemented facade or admission bypass.

Explicit Mesh agreement to this completion with the exact R2+R3 tuple remains
needed before unconditional Observer API signoff. No new role amendment, scope
API, schema identifier or resource allowance is requested.

## Arithmetic evidence and remaining gates

The independent stdlib
[verifier](evidence/2026-10-16-delta-sync-source/verify_relay_r2_vectors.py)
imports neither producer. On Python 3.14.8 and 3.11.17 it checks all 12 positive
fixture cases and four rejections with identical outputs. It recomputes encoding/
request/native-binding/source/challenge hashes, two-alias wrappers, moved tags,
nested raw-fragment preservation, sizes and attenuation/whole-RTT expiry. Its
one-marker reconstruction of the complete delivery differs from Mesh's nested
splice helper. Upstream replay also matches the retained fixture byte-for-byte
on both versions; that replay is separate from the independent checker.

The toy native fragment is 1,121 bytes, nested envelope 1,896 and total 3,017.
It contains structural line feeds and no terminal transport LF. This proves
JSON-fragment preservation and formulas, not strict native newline-delimited
framing or LineChannel acceptance. Runtime framing gates need actual valid
single-line native frames, escaped newlines, delimiter removal/addition,
chunking, controls and all nested caps. Fixture descriptors/native roots remain
unadmitted toy inputs.

Scanner/facade and capsule/ref tests, malformed/domain-invalid Reader rejection,
clock/context/replay/movement, inclusive intake/output/pin memory, GC-disabled
held-error cleanup, dense CPU, cold/packed recovery, actual IPC/fixed SSH and
installed paired artifacts remain open. All 64 MiB heap/32 MiB encoded, frame/
client/journal and deadline bounds stay unchanged. No package allocation,
normal service/provider action, Mesh/RLCD edit or rollout accompanies this review.
