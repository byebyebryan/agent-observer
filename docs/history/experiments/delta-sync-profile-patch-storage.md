# Pure Agent patch storage and capacity

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The pure `AgentSyncProfile` patch builder groups field writes by exact record
reference and coalesces repeated index updates into one final slot. Public
`DomainIndexPatch` keys, values and DTO types are unchanged. No Mesh, native
serializer, shared ABI, descriptor/schema/ID, version or normal selection is
changed. The [receipt](../../evidence/2026-10-17-profile-patch/receipt.json) binds the
source overlay against `b8e25ca`, immutable Mesh `f0924e`/runtime `d013d2a`,
before/final tests, graph census and actual-source capacity reports.

## Storage and ownership

Nine field writes for one record share one reference graph and one immutable
logical marker. Markers preserve the exact list/integer/string key structure;
unsupported bool/dictionary/null keys reject. Public patch data stays plain
JSON. This replaces retained canonical bytes in token, index and affected-row
registries. The public callback budget has no encoded-charge argument, so it
cannot correctly account retained canonical markers under the encoded cap.
The new builder retains no such encoded buffers and requires no generic API
extension. Bounded canonical comparison elsewhere stays unchanged.

An index slot keeps its first key and final value. Its heap reservation grows
only when the union of live old/new graphs reaches a new high-water. Old/new
values remain covered while the caller still holds both; no credit is refunded
early. Fixed per-slot storage covers marker/entry/counter/dictionary growth.
Each record group prepays its shared reference/marker and bounded map storage;
each field prepays old/new slotted DTO/token overlap. Result construction
prepays write/remove DTOs and list/tuple overlap. A fixed-size token pointer
list avoids an unknown-length flattening constructor. These callback charges
remain live through generic completion or rollback/error unwind.

Five tests cover final-write semantics, full reference/birth separation, shared
reference identity, repeated counters, replacement overlap, refusal before
mutation, marker types/no encoded buffers and graph/preallocation bounds at
100/500/2,000 records. Exact before-source overlays reproduce six failed checks
across four storage methods, with the refusal control passing. Final profile,
codec, read and patch suites pass all 64 methods on Python 3.14.8 and 3.11.17,
GC disabled, zero failures/errors/skips.

The separate synthetic internal-patch census emits identical canonical write/
token semantic digests before and after at all three scales on both Python
versions. It is not native admission or an inclusive physical-heap/RSS proof.
At 2,000 records on Python 3.14.8, unique reachable builder/result storage is
8,309,965 to 8,144,354 bytes, while prepaid charge is 41,542,434 to 21,132,788
bytes. Token marker slots fall from 18,000 to 2,000. The small actual graph
reduction and larger reservation reduction are separate measurements; no 49%
RAM saving is claimed. Python 3.11's corresponding graphs are 8,310,077 to
8,192,466 bytes, charges 42,966,434 to 21,756,804.

## Actual source plus Reader screens

The unchanged Mesh compact intake probe runs twelve final serial cases under
the shared CPU lock with exact before/after input inventories. Source intake
and Reader material/staging use the same original 32 MiB encoded / 64 MiB heap
ledger; the native service has its separate owner account. The private packed
arena is explicitly fixture-owned. These are full-only 710/3,510/14,010-cell
fixtures, not dense nine-field or simultaneous full/active qualification.

| Rows/backend | Python 3.14.8 ledger heap peak | Python 3.11.17 peak | Outcome on both |
| --- | ---: | ---: | --- |
| 100/default | 15,571,195 B | 15,620,259 B | Baseline + two generations + fresh actual heads |
| 100/packed | 14,438,114 B | 14,487,178 B | Same |
| 500/default | 39,259,621 B | 39,491,085 B | Same |
| 500/packed | 32,357,565 B | 32,589,029 B | Same |
| 2000/default | 67,107,930 B | 67,105,438 B | `sync_decoded_capacity` at baseline admission |
| 2000/packed | 64,276,598 B | 65,031,886 B | Same refusal |

All final six Reader counters are zero with real errors retained and GC disabled.
These are ledger bounds, not measured process heap/RSS. The smaller cases
confirm actual owner roots after original native proofs; they construct no
detached full-roster DTO oracle. The 2,000-row cases create no confirmed current
view and do not reserve the later 4 MiB fixture proof scratch.

The final scalar packed/2,000 audit reaches all 18,000 field writes and the
complete callback patch, then encounters the next generic staging charge.
Its exact counts and refusal remain in the receipt. This identifies the next
boundary; it does not justify reducing Mesh charges. Generic normalization,
phase/group/alias and index ownership remain Mesh-owned. **2,000-row capacity
remains FAIL.** No caps are raised or accounting exception introduced.

Earlier prototypes and a counter-overlap test expectation error remain separate
diagnostics. The earlier canonical-marker prototype snapshot was restored
byte-for-byte against its captured input hashes after preparing the typed-marker
variant; final runs use a separate frozen export. Drafts are excluded from final
claims. The five-test before overlay and both census outputs retain their exact
source pins.

The probe discloses private nonce/native pin/proof carrier, prepaid proof scratch,
synthetic clocks, disposable collection-disabled Runtime and separate fixture/
oracle/native storage. Absolute 15 s acquisition/2 s proof, inclusive process
heap/RSS, dense capacity, delivered cold/recovery, relay/controller/authenticated
selected route, populated native/fixed SSH and immutable installed pairs remain
open. No CPU measurement is rerun: the existing owner hard failures and recovery
fallbacks remain unchanged. Prior source/controller closures stay closed; no
provider/service, sibling, artifact or rollout action occurs. Git attribution
cleanup remains on HOLD.
