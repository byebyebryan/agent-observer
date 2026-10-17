# Observer review of the original A1 relay packet

Status: **native direction compatible; original standalone API packet needs
corrections**. This is the response to Mesh event `e-81f89ac7`, confined to its
named immutable revision. It grants no relay runtime or producer acceptance.

## Exact reviewed inputs

On Starship, immutable `git show` retrieval reproduced all four hashes:

| Input | Commit | SHA256 |
| --- | --- | --- |
| Mesh `docs/delta-sync-relay-api-proposal.md`, 13,744 bytes | `a7be9ae64ded5b88b1b1ecd2c61233ae58e7fbc6` | `05e5a9bef61d0235d6d82c326e630209dac610a122f581117bdb65beaa36183d` |
| RLCD A1 revision 2, `projects/agent-dashboard/docs/delta-sync-relay-addendum.md`, 6,186 bytes | `665f6caaed99740a755de9467c7ae53322f7e720` | `6eaa408376f91bb7c5e4276812927fd2bfce2445412fb02a211bea22a5e52aef` |
| Agreed cache-owned input contract, `docs/delta-sync-owned-input-api.md` | `0ca3b99c7413d2542ab48ff11e8e58fb82f73d93` | `7f7751ecd9df93277a3e7110ca72ebfda343d38fa629cd0212ec40b3a8f1d124` |
| Frozen G0 appendix | `ed771e5c8843dca718700c8b8b1d6804ae9134f0` | `a376bc848a78027d4fd723e8a2959dbbc4e00114da132d3a5d2733a6ebce2eb6` |

The [review evidence](evidence/2026-10-16-delta-sync-source/relay-original-review.json)
records the inspected Observer source hashes. The source implementation is the
existing `4030d50` checkpoint; this review changes no runtime code. Later relay
supplements are separate review inputs, not implicit changes to this packet.

## Native compatibility

The explicit relay role fits A1 revision 2: a trusted factory fixes the source,
native descriptor, full/active view and identity/clock configuration. The relay
has no profile callbacks, material cache, admission reuse or semantic facade.
Reader body/schema/domain, old-value, alias/token/cohort, root, receipt, clock,
nonce and request checks remain mandatory before authority publication.

The implemented Mesh-free source supports additive `open_session(inputs)` and
owned baseline/change/watch/head results. It requires only the public structural
reservation/ref protocol. The source closes its own operations, refs and leases;
it does not close the shared input owner, parent source or native service.
Parent close closes its sessions. Separately configured aliases retain separate
sessions, handles and accounting. These obligations agree with the first packet.

The current expanded-JSON scanner traverses the complete bounded grammar and
decodes only the bounded structural header and receipt map for material frames.
It preserves the original native binding, including provider/namespace context,
and leaves native body identity and support bytes opaque and unchanged. The
Reader must still validate their exact identity/context join. Local source guards
check socket inode/peer UID, host/boot/time namespace, owner incarnation,
challenge, cursor/order and original receipt watermarks. Structural acquisition
does not admit the opaque body, token, membership or root. A compact scanner
still needs its separately agreed codec and qualification.

`head_after_nonce` performs a live bounded native head request after challenge
validation. It can return the owner's actual moved tag; it does not collect,
export material or prove a requested old head. Original receipts and cohort
heads remain unchanged. Bridge attenuation needs only exact bounded key coverage,
strict nonnegative integers and the authenticated shared clock namespace:
`max(0, native_attenuation - (bridge_time - native_time))`. It requires no
provider classification or interpretation of receipt health. The Reader alone
derives authority from its independently admitted material and original support.

## Corrections required for exact API agreement

1. **Define the relay minting and consuming boundary.** The packet says a relay
   mints an `InputOwner` without a cache, but its only public minting signature is
   `OwnedSyncCache.input_owner()`. Its refs expose only `nbytes` and `close`;
   neither the native source nor a relay can use them as ordinary bytes. The
   proposed `SyncRelay` exposes only `aclose`, so there is no specified public
   operation that consumes a native ref, scans it and forwards it, or builds the
   fresh proof wrapper. Supply the separately bound relay owner factory/channel
   operations and byte consumer. They must retain raw/header/output credit
   through actual drain, bind source/descriptor/scanner/request/channel epochs,
   reject cache/relay/alias cross-use, and define who closes the minted owner.
   No profile or material cache may be introduced to obtain this capability.

2. **Use the complete agreed structural input protocol.** The implemented
   source calls `buffer_heap(nbytes)` before sealing and observes reservation
   `heap_bytes`/`encoded_bytes`. Those public members and the owner-close rule are
   absent from the original signature block. Reference the exact agreed
   `7f7751ec...` protocol for the common reservation/transfer rules, then declare
   the relay's distinct ownership/consumer binding explicitly. Session close
   closes only its own reservations/refs; the relay/channel owner closes its
   input owner. Header/ticket metadata retains separate credit after its data
   ref is consumed. Raw bytes and in-flight pins remain charged through awaited
   cancellation cleanup. Equal configuration alone cannot authorize alias reuse.

3. **Correct the batch transfer phase.** The original blanket statement that
   every supplied handle is consumed on any failure conflicts with the agreed
   common contract. Validate the tuple/container, element types and <=4 count
   before transfer; invalid shape leaves ownership with the caller/source
   session. A valid bounded tuple transfers all handles, including unvisited
   members if later sum-size, chain or admission checks fail. A foreign handle
   cannot release an unrelated owner/alias's storage. Closing a failed operation
   still awaits cleanup of all resources it actually owns.

4. **Fix the RequestBinding field-count statement.** The packet lists nine
   fields, ending with `role` and `encodingDigest`, then says the “first eight”
   preserve the existing aggregate shape. There are seven preceding fields.
   State the exact closed new-sync binding and its bounds without that claim;
   do not retroactively impose these candidate fields on legacy Delivery 1.
   Every echoed binding/challenge digest must cover the complete exact object.

Mesh's separately titled `delta-sync-relay-api-r2.md` supplies a candidate
distinct relay owner/channel API and fuller transfer rules. These corrections
are to the requested original bytes; they are not a request to resend or edit
that historical packet. The later packet and its supplements need their own
explicit same-byte decision with Mesh and RLCD. This review does not accept
them by substitution or duplicate a pending interface request.

## Arithmetic and acceptance boundary

The independent stdlib
[arithmetic replay](evidence/2026-10-16-delta-sync-source/verify_relay_attenuation.py)
imports neither producer. Python 3.14 and 3.11 produce identical results:
native `10000`, bridge `10015`, attenuation `500` gives `485`; Reader
sent/received `20000/20060`, margin `100`, gives expiry `20385`. Zero or exhausted
attenuation gives no positive lease. The replay also checks reversed clocks,
negative/boolean integers, duplicate/missing/extra keys and invalid Reader
timing. This is arithmetic evidence, not relay execution or native proof.

All original caps and deadlines stand: one shared 64 MiB heap/32 MiB encoded
budget, bounded intake/output/pins, native/proof frame limits, two-second proof
and a separate catch-up plus at most one fresh retry within the original
15-second acquisition deadline. Known movement/failure revokes host authority;
no late result or unavailable new material can preserve a stale target claim.

Exact relay API agreement and RLCD A1 acceptance remain pending. Compact codec,
dense Reader storage, producer CPU, aggregate resources/RSS, installed/native
transport and exact paired artifacts remain separate open gates. No Mesh/RLCD
edits, package allocation, artifact, installation, provider/service action or
rollout accompanies this review.
