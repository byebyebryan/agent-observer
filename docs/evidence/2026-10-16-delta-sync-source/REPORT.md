# Snapshot/delta sync source checkpoint

This is unfinished G1 source evidence on Starship, beginning at Observer
`100637b`; later source checkpoints are recorded below.
Producer acceptance is **not granted**. There is no candidate wheel, package
selection, installed candidate, live service change or consumer acceptance.
G0's `ed771e5` / `a376bc84` appendix remains unchanged.

Implementation checkpoints are `82feed8` (native cache/local delivery),
`ca9d32d` (strict pure profile/read facade), `1be9f8e` (draft acquisition and
bounded header scanner) and `100637b` (owner allocation/removal work and matched
producer probe). These are isolated branch commits, not accepted releases.

The full source check passes 791 tests, without skips, plus Markdown/link/diff
checks. The focused Python 3.11 check passes 203 tests. Profile/read checks use
the in-progress Mesh source overlay; they do not certify a Mesh artifact or
freeze its pending codec/input APIs. Existing artifacts, normal services,
providers, Tmux, RLCD and 349 remain unchanged.

## Matched producer ABBA

[The probe](../../../tests/bench_sync_producer.py) uses a fixed native-shaped
Codex fixture and six accepted generations, with deterministic clocks and
incarnation. Every sample includes attempt diagnostics, common generation,
both sync views and full snapshot/projection/support/census oracle hashing.
Component timer overhead is included. The legacy process runs installed a7
with isolated Python; sync runs the source overlay. Both use Python 3.14 and
run serially under the existing shared CPU lock.

This measures producer generation only. It does not deliver a cold baseline or
measure IPC, publisher, SSH, Reader, facade, application or owned descendants.
Fixture construction and cold common/root construction are reported separately.
It is not installed candidate or end-to-end qualification.

| 2,000-row workload | Installed a7 median | Source median | Change | Result |
| --- | ---: | ---: | ---: | --- |
| Real N-row observation timestamps | 818.64 ms | 878.94 ms | +7.37% | Source producer target met for this input |
| Stable `lastUpdated.at` changes in all N rows, plus timestamps | 816.55 ms | 1,852.06 ms | +126.82% | Producer overhead gate failed |

Each median pools twelve samples from its two ABBA runs. All six generation
signatures match in every run of each workload. Transitive source hashes match
before/after each run and across the two source runs. Exact samples, components,
module hashes, counters and signatures are in [producer-abba.json](producer-abba.json).
Independent component medians are not additive.

The dense source workload has a 1,295.85 ms median sync stage, compared with
508.59 ms common generation and 46.63 ms oracle hashing. It retains correct
current/predecessor roots, with no cold rebuild or failed view. Its aggregate
heap-account peak is 65,972,597 bytes, below 64 MiB. Internal canonical buffers,
stages, journals and output pins also share the 32 MiB encoded limit.

The dense workload retires the optional change chain once per generation and
returns explicit baseline-required: six counted fallbacks per source run,
not successful incremental delivery. Packed baseline/recovery is unfinished.
No CPU saving may be inferred from omitted recovery work. Both source runs
close with zero accounted live allocations/objects and only the account base.

Example source invocation from the repository root, with the source overlay
and installed Python explicitly selected by the caller:

```sh
python -B tests/bench_sync_producer.py --rows 2000 --mode sync --workload timestamp
```

For the baseline, use installed a7's Python with `-I -B`, no source overlay and
`--mode legacy`. Repeat A/B/B/A serially under the shared advisory lock. The
source-overlay version metadata string does not identify an installed candidate.

## Subsequent token-buffer sharing

At `068f4b0`, the native owner shares each canonical membership-token buffer
between its global map and the corresponding cohort map. Keys, old-value
checks, nodes and commitment roots remain independent. The frozen-tree oracle,
exact replay and physical-sharing checks pass. The full source check passes
792 tests without skips; the focused Python 3.11 buffer/owner check passes 82.

A new serial dense ABBA run measures 837.06 ms installed a7 versus 1,830.43 ms
source, **+118.67%**, so the producer gate still fails. All six signatures match
in every run, and both source runs use identical transitive source bytes.
Accounted aggregate heap peaks at 62,171,223 bytes, with zero live accounted
allocations/objects after close. This is an account measurement, not an RSS gate.
The six explicit baseline-required fallbacks persist in each source run; packed
recovery and end-to-end work are still unqualified. Exact results are preserved
in [dense-sharing-abba.json](dense-sharing-abba.json); the earlier table and data
remain the historical `100637b` checkpoint.

## Compact-layout feasibility

The subsequent [shared-ownership diagnostic](OWNERSHIP.md) records internal
canonical/output/stage/pin union and overlap at aggregate peaks, rejected
constructor reservations and exact additive CPU totals. Both encoded and heap
caps include canonical buffers. Its bounded source accounting evidence does
not settle the failed CPU or unfinished full-roster delivery gates.

The runtime's expanded baseline still needs 11,823,094 bytes at 2,000 rows,
exceeding the unchanged 8,404,992-byte frame cap. It is not a usable large-roster
wire format.

[packed_feasibility.py](packed_feasibility.py) tests a separate split-table layout:
record alias/identity/birth/body/order definitions first, stable bodies without
their repeated identity, alias-based observations and receipt-index membership
masks. The four small tables remain expanded. No body semantics or support
authority is inferred by packing.

| Full roster | Service 4 bytes | Proposed bytes | Increase |
| --- | ---: | ---: | ---: |
| 100 | 168,077 | 191,973 | 14.22% |
| 500 | 826,477 | 933,175 | 12.91% |
| 2,000 | 3,297,477 | 3,719,681 | 12.80% |

The ten-selected-row active view is 37,904 bytes in each fixture. Detached
reconstruction equals all eight logical tables; an independent full Patricia
rebuild reproduces NativeRoot. Four malformed structural cases per view reject
duplicate definitions, foreign body/observation aliases and inconsistent masks.
The owner closes to its fixed account base, with no live allocations/objects.
Exact results are in [packed-100.json](packed-100.json),
[packed-500.json](packed-500.json) and [packed-2000.json](packed-2000.json).

These are size/root feasibility checks using the current logical descriptor.
The layout is not emitted or accepted by the runtime, is not a frozen schema,
and has no budgeted admission/transport evidence. A changed final descriptor
will change dependent body IDs and field tokens. The detached oracle materializes
tables and is not a proposed sparse receiver implementation.

## Subsequent allocation-bookkeeping path

A bounded current profile attributes substantial cost to allocation bookkeeping
and staged persistent-map updates. The next source change uses direct lookups
in the same identity shards and avoids constructing JSON graph/ref/encoding
worklists when an allocation owns no JSON roots or canonical encodings. It
preserves the same eager capacity check, constructor credit transfer, payload,
metadata and allocation counters. Public reservation tests cover bufferless
credit transfer, metadata ownership and atomic rejection; existing map, dual-cap,
replay and delivery tests exercise branch allocations and reclamation.

One serial before/after source pair at 2,000 dense rows measures 1,846.74 ms
versus 1,764.64 ms per generation, a 4.45% reduction. The parent is `abd50bd`;
[accounting-pair.json](accounting-pair.json) records exact transitive input hashes,
all six samples and component timings on both sides. The signatures match;
both sides peak at 62,171,223 accounted bytes, retain valid roots, report six
baseline-required fallbacks and close with zero live allocations/objects.

This pair is exploratory optimization evidence, not repeated installed ABBA
or a passed producer gate. The matched dense ABBA above remains **FAIL**;
compact recovery and the other required workloads remain open. No omission of
delivery/recovery work is credited as a saving.

## Streaming profile admission

The next Observer-only profile checkpoint removes its eagerly detached operation
list and changed-body/observation DTO dictionaries. It reads metadata, receipts
and cohorts first, then collects affected identities from public changed keys.
Each affected row is admitted under a public pre-copy reservation and its body,
observation, joined row and token-input DTOs retire before the next row. Compact
index writes, rules, tokens and affected keys are charged before retention.
The active baseline also uses its incrementally checked whole-ledger byte count
without reconstructing a second full ledger DTO merely to repeat that count.
The independent exact-byte fixture tests retain that oracle comparison.

Mesh independently checks body digests, one-to-one record/body linkage and
orphan removal before the callback. Changed record slots drive new body
admission; a no-op put of the same admitted body digest requires no body lookup,
copy or schema revalidation. Observation-only changes still use the admitted
compact rule without stable-body fallback. Original support/expiry, birth,
identity, order, orphan, scope and cross-record checks remain exercised.

New tests observe a detached-body lifetime peak of one in full and active
baseline admission, verify reservation precedes body copying, reject before a
copy when that reservation fails, and forbid body work for a no-op body put.
A rejection publishes no candidate. Mesh's bounded decoder memo may remain
charged until store close; close retires all allocations and reservations.

[profile-stream-capacity.json](profile-stream-capacity.json) records an unpaired
100/500-row source diagnostic using Observer `58c20b3`, Mesh `8b06de3` plus
the hash-pinned `cache.py` and `canonical.py` overlays, and its existing script.
All 79 Observer inputs match that commit. Of the 57 Mesh inputs, the two
overlays differ from the committed base: `src/mesh_plus/sync/cache.py` is
SHA256 `ffa71e5498193b73f4408e62672932f168a09e53659b3ee31e2620a2aaef3010`,
and `src/mesh_plus/sync/canonical.py` is SHA256
`3d481c03157934c479dcf6a501ee3a91638a5c3b0cad3d61b91b4a0ca57a507f`.
The unchanged JSON, SHA256
`461eb37c4a2a0514d7420eb77c2cf5bee68561e0613c4b09630a37d10083dbef`,
binds the complete input manifest; it is not a clean committed Mesh tuple.
The 500-row four-membership fixture still has a 2,125,267-byte native baseline
versus 683,333 legacy full bytes. Its accounted peak is 30,668,001 bytes, including
conservative callback charges and Mesh's new preallocation accounting. The
earlier 17.4 MB figure omitted not-yet-retained staging; these are different
accounting/source revisions and establish no memory or CPU regression ratio.
Both new diagnostic cases close with zero bytes/reservations. They are not
dense nine-field, RSS, installed, native IPC/SSH or producer acceptance.

This fixes callback roster materialization using the existing public changed-ref
and reservation APIs. Compact normalization/input ownership, aggregate capacity
and the failed producer CPU gate remain open. No shared codec ABI, schema, cap,
artifact, provider or normal service changes accompany it.

## GC-independent scratch and owner retirement

A GC-disabled investigation at `58c20b3` found that an encoded map could report
zero accounted allocations after its final root was dropped while its account
still remained physically reachable. Tree build/patch recursion is method-based;
the retained path was a per-call raw-bound visitor closure capturing a scratch
lease/account. Freeze, reuse, thaw and the fixed-schema compiler also created
self-referential local function cells that survived until cyclic collection.

The next source checkpoint breaks those cells in `finally` on success or
failure. A released lease drops its account and marker-tuple references. A
closed encoded ledger drops its callback and only its own configured account
link. Explicit owner-cache close also drops state/reserver backlinks, is
idempotent and rejects later sync queries rather than reopening outside the
closed ledger. Subsequent ordinary legacy acceptance remains independent.
This is internal owner-cache teardown; a client/source close still does not
stop the shared native service or invoke provider actions.

New tests disable cyclic GC and verify repeated JSON scratch stays bounded,
dropped compiled validators retire immediately, and encoded replay/rejection
releases old roots and the allocation account. They also verify immediate
physical retirement of an explicitly closed synthetic state/owner/account,
terminal sync reads and continued legacy acceptance. Existing delivery-pin tests
retain their independent charge until the final peer drop. The focused checks
pass 140 tests on Python 3.14 and 3.11 without skips.

The before/after weak-reference reproduction distinguishes physical retirement
from zero ledger counts: the old encoded account and closed owner graph survived
without collection; the corrected cases retire without calling `gc.collect()`
after the measured operations. This is bounded synthetic lifetime evidence,
not installed RSS/plateau, native, transport or producer acceptance. The
packing, aggregate resource and failed CPU gates remain open.

## Paused acquisition lifetime

The next owning source change moves complete strict frame parsing and socket,
operation, receipt and order checks into a per-frame coroutine. It returns only
raw bytes and bounded ticket/control fields. That coroutine retires its full
parsed graph and receive/conversion locals before the async generator pauses;
the generator keeps only actual unread framing bytes and bounded stream state.
Framing now copies the complete line once without intermediate partitioned
line/rest buffers. Failed change batches clear their partial byte list, and
unwound parser failures retire saved traceback references. The existing plain
byte methods and full validation behavior remain unchanged.

New controlled Unix-socket tests disable cyclic GC and check that parsed frames
and received tickets retire while a subscription remains open and paused. A
completed I/O task can retain its return until its event-loop callback retires;
the checks allow that loop turn without collecting. A saved partial-chain
failure retains neither its old parsed frame nor a partial batch. An invalid
opaque operation still fails strict parsing rather than gaining admission from
its structural header. The 20 source and 16 header tests pass on Python 3.14
and 3.11, without skips.

This removes avoidable retention; it is not a prepaid intake implementation or
an aggregate memory/CPU acceptance result. Mutable pending bytes, actual batch
outputs, decoder scratch, tickets and all I/O/stage pins still need the agreed
public ownership lifetime. The exact Mesh session/relay API review and its
remaining scoped-retirement/metadata-credit question are recorded in the
[interface note](../../delta-sync-interface.md#acquisition-budget-seam-still-open).
No role, schema, cap, artifact or installed service changes accompany this fix.

## Changed-token read probe

A subsequent owner-only change skips reading/decoding an old membership token
when changed body content already requires deriving its new token. The final
membership edit still independently compares the old value, and grouped/global
roots retain their ordinary checks. Unchanged-body/new-support lookup is kept.

One serial 2,000-row dense source pair at parent `02c78a4` measured total owner
CPU of 1,743.59 versus 1,720.13 ms per generation (1.35% lower in this pair).
Common-work medians also varied, so this is not evidence of a repeatable saving
or a new ABBA gate. [token-read-pair.json](token-read-pair.json) preserves each
sample and exact transitive source hashes. All six signatures match; both runs
have six baseline-required fallbacks, no failed roots, and zero live allocations
and objects after close. Accounted peaks are 62,171,223 and 62,130,231 bytes.
This bounded optimization leaves the failed combined producer CPU gate and all
packed recovery/intake/installed/native acceptance work open.

## Exact Mesh source compatibility

A later independent compatibility check pairs Observer `38e2b64` with an export
of Mesh `e15764b56a42847d0d72258bd7ca533ef4c39236`. The live Mesh worktree had
concurrent owned-input changes; those bytes were excluded. All 58 exported
package/pyproject files match the manifest in Mesh's qualification JSON SHA256
`9d27e728a0e2d80e6cf8d04fdccac3d0a115a436681ff378db419c01ac6c75be`
before and after the checks.

The strict profile, facade, cached source and structural-header suites pass
79 tests with zero skips on each of Python 3.14 and 3.11. Exact inputs and logs
are in [mesh-e15764b-compatibility.json](mesh-e15764b-compatibility.json).
This is source compatibility, not an installed paired artifact, sync IPC/SSH,
resource/CPU or native acceptance. It neither accepts concurrent public intake
work nor resolves the compact codec/alias/mask or A1 relay review. The reported
expanded-wire byte and 2,000-row frame-limit failures remain open.

## Native nonce material-retirement audit

Mesh's later `70fb22d787908aa672bfd1557e885bb9006df774` checkpoint moves
predecessor retirement out of generic confirmation. Its committed
`proof-retirement-source.json` matches the announced SHA256
`0a75c5b70be3848881bfe351ff2e721d2d428813ea95d46607627e256d612909`;
all 58 exported package/pyproject files match that report's manifest. Newer live
Mesh drafts are excluded from this review.

The analogous Observer native audit found no material-root retirement in the
nonce path. `OwnerSyncCache._head` reads only current receipt/cohort tables and
the original clock/tag; it never calls `ensure`, normalization, publication or
expiry. Cold requests return bounded baseline-required. Query-output FIFO
eviction releases byte-output leases. Runtime reservation/drop paths inspect
bounded output/peer collections and release byte pins, leaving owner material
roots alone. Predecessor/material retirement remains in publication, recovery
and explicit owner teardown, outside the nonce operation.

A new regression check observes material-lease releases without retaining those
leases or roots itself. With cyclic GC disabled, both native backends retain
full/active current and predecessor roots across repeated head reads, FIFO
output replacement and output-capacity rejection. No material lease retires;
root identities remain unchanged. This guards the cleanup boundary and leaves
all ordinary receipt/clock/token/root checks intact. No runtime fix was needed.

This is static and controlled source-test evidence, not actual native two-ms
head CPU, installed IPC/SSH, whole-proof latency, RSS or producer acceptance.
All existing failed/open performance, packing, resource and ABI gates remain.

## Remaining work

- Qualify the implemented public owned-input transfer and complete the compact codec ABI with Mesh,
  including provisional alias declarations versus the profile's independently
  derived final alias index, mask assertions and resource ownership.
- Implement packed baseline/change emission and strict budgeted normalization.
  The opt-in source ownership tests are not aggregate memory/RSS or paired
  transport acceptance.
- Resolve the failed dense producer overhead case and qualify cold/all-body/
  forced recovery. A timestamp pass does not settle those gates.
- Run the remaining exact native, immutable artifact, installed paired IPC/SSH,
  end-to-end CPU/bytes/latency, resource/capacity, compatibility and cleanup gates.
  Empty sources or code probes cannot substitute for populated native parity.

No installation, version allocation, rollout or provider operation is authorized
by this source checkpoint.

## Opt-in prepaid source intake

The source now implements `CachedAgentSyncSource.open_session(inputs)` using
only the public structural API agreed against Mesh `0ca3b99`. The exact
source-contract document remains SHA256
`7f7751ecd9df93277a3e7110ca72ebfda343d38fa629cd0212ec40b3a8f1d124`.
The implementation has no Mesh import. Existing plain-byte methods keep full
strict parsing and their return types; owned methods structurally scan native
headers and return opaque single-consume refs or closeable header tickets.
Sealing still grants no schema/domain/root/currentness authority.

All receive/growth/copy, unread-tail, parser/header, request/batch and completed
callback credit is prepaid through the configured InputOwner. The source keeps
header leases independent of consumed data refs, and its state, request and
temporary encoding allowances count inside the existing 64 MiB heap / 32 MiB
encoded caps. The [interface note](../../delta-sync-interface.md#acquisition-budget-seam-still-open)
records the actual allowances and cleanup boundary. These are conservative
accounting reservations, not observed RSS or a capacity/performance pass.

Twenty new controlled protected-socket tests exercise baseline, head/control,
four-item and partial batches, coalesced paused-watch tails, source/watch/parent
cleanup, foreign and consumed refs, independent full/active cache handles on a
shared ledger, allocation refusal, malformed/duplicate headers and deferred
opaque duplicate rejection. Real ServiceState full/active fixture baselines
reach independently validated, still-unconfirmed receiver candidates. A
fabricated structural baseline still rejects at the receiver. No source-only
ticket can publish a view.

Additional regressions hold outer-operation storage after inner I/O has ended,
repeat cancellation during cleanup, and keep a saved timeout while cyclic GC
is disabled. Close waits before refunding; a lost late result retires only its
operation scope, preserving older tickets. Watch failure traces do not retain
decoded request or receive frames after their leases close. Closing a session
leaves the shared cache-minted InputOwner and sibling source/session usable;
the remaining owner-base charge is intentional until cache teardown.

Exact source manifests and verification commands/results are recorded in
[owned-source-compatibility.json](owned-source-compatibility.json). This is an
Observer source checkpoint only. It does not adapt Mesh's acquisition controller,
provide A1 relay authority/byte export, freeze the compact codec, or qualify
aggregate intake+material peaks, RSS, installed/native/SSH proof delivery,
immutable artifacts or the failed dense combined CPU gate. Expanded full 2,000
baseline/recovery remains undeliverable under the fixed frame limit; the
historical ownership probes and their limited head-only case remain separate.

## Historical counterpart fixture failure reconciliation

Mesh's earlier `protocol-metadata-source.gate2.log` records a real `ABSENT`
NameError during a mixed-source run. The owning `58c20b3` commit already added
that import; no new runtime or fixture edit was necessary. The historical Mesh
report remains failed, rather than acquiring retrospective acceptance.

Against stable Observer `4030d50`, all 31 profile tests now pass with zero skips
on each immutable Mesh export `8b06de35e49dd4da5f61f80e350c338b11aa8e3f`
and `0ca3b99c7413d2542ab48ff11e8e58fb82f73d93`. Before/after source hashes
match. [fixture-reconciliation.json](fixture-reconciliation.json) records the
exact fixture, failure-log hash, source inputs and fresh results. These checks
reconcile that fixture issue only; all producer readiness limitations above
remain in force.

## Normalized dense storage counterpart review

The [Observer storage review](../../delta-sync-storage-review.md) checks Mesh
runtime `95c406f` plus diagnostic `4121cbb` and the normalized-density JSON
SHA256 `94eb0e389080a5eb5d37d4864714200085d47d0113d370670a3ac4c1ea221372`.
All 58 source/script hashes match the pinned commits; this is a static evidence
review, with no benchmark or source-gate rerun. The nine-field minimal-body
fixture rejects its first 2,000-row normalized stage at a 63,897,393-byte
accounted heap peak, before input frames/proofs. It exposes a decoded-storage
blocker independent of expanded native wire size. These generic independent
views omit Agent indexes, caller DTO/oracle memory, source and transport; they
do not establish domain capacity, total RSS or a savings comparison.

Observer has no domain objection to a private arena prototype preserving
per-node live-edge ownership, exact roots and public logical lookup, with all
pages/slack/controls/payloads/pins prepaid under the existing caps. The review
requires dead slots to release child graphs on partly live pages, stale-handle
rejection, immutable old token values, GC-disabled cleanup and combined
current/predecessor/stage/slow-pin qualification. It agrees with grouped compact
callback intents while proposing an explicit single-writer rule for compact
membership expansion. Exact compact ABI/domain vectors, A1 role and storage
implementation/acceptance remain open. [density-source-review.json](density-source-review.json)
records checked hashes, reported counters and evidence limits.

## Concrete normalization agreement proposal

RLCD's exact density review is committed at `0aa5f5b`, SHA256
`8dac4913e166eaa8ffed30bf604a4777bf6712ed1eaab0155a4190a0d16f7b18`.
It confirms that native-owner fit cannot establish Reader fit and releases
independent private Mesh storage work while shared normalization is reviewed.
The [single Observer decision packet](../../delta-sync-normalization-decision.md),
SHA256 `35b1911388e75f4bc2a87087f23f07f7ca95346719933d7b37a5365d528734d6`,
accepts the proposed revision-1 per-space codec surface, separate before and
declared-after aliases, independently derived final aliases and provisional
mask/validated-token flow. It explicitly completes the HeaderRef/AliasSpec
surface, phases strict streaming validation without a full DTO roster, and
requires an empty compact `membership_expansion` patch so generic expansion is
the single cell writer. The already agreed common input API covers reserve,
seal, consume and batch/head cleanup. Its source implementation stays `4030d50`.
Mesh same-byte agreement is pending; no absent candidate class is treated as a
failure and no dependent normalization implementation has started.

[verify_codec_arithmetic.py](verify_codec_arithmetic.py) independently uses
stdlib JSON/hash functions and a bit-string Patricia oracle, importing neither
producer. It reproduces eight positive cases, all eight table roots/native
roots, 11 record/group permutations and four distinct optional-value tokens
from Mesh's pinned toy fixtures on Python 3.14 and 3.11. Its exact changed-cell
counts are 0, 1, 1, 2, 1, 1, 0 and 4. Separately replaying Mesh's own pinned
stdlib script reproduces its eight positive/37 rejection fixture bytes on both
versions; that replay is not an independent implementation of the rejections.

[joined_codec_vectors.py](joined_codec_vectors.py) independently extracts
literal native moved paths/nine token inputs and hashes them, then compares
public native split/join/admission/token helpers. Its
[retained synthetic vectors](joined-codec-vectors.json) are byte-identical on
both Python versions: eight full/active cases, 72 tokens and four partition
rejections. Running versus parked/null phase is explicit. Observation-only
clock/receipt refresh changes no body/token; a real lastUpdated value change
changes exactly that token. These are native-shaped fixtures, not provider,
new compact schema/runtime, support-authority or transport acceptance.
[normalization-decision-evidence.json](normalization-decision-evidence.json)
binds exact inputs, hashes, coverage and remaining agreement/gates.

The implemented public intake/source/header/profile/facade suites also pass
99 tests with zero skips on each Python version against an immutable export
of Mesh `32090d69c0603955613421d100386b3809e0ab90`, including its later input
control prepayment and terminal callback retirement fixes. All 88 exported
inputs and the previously captured 153 Observer source/test inputs match
before/after. This independently checks the existing cache-backed API; it does
not execute or accept proposed codec classes or supply installed/native proof.

## Continued dense producer CPU investigation

A fresh serialized 500-row dense cProfile screen still places substantial time
in immutable map construction and allocation/encoded-ledger work. Profiled
times include instrumentation overhead and are not compared with unprofiled
performance results. A five-point shard-lookup inlining trial kept its exact
hash function, accounting and input semantics; 69 commitment/encoded-budget
checks passed before the experiment.

Four serial 2,000-row trials ran before/after/after/before under the shared CPU
lock, six generations each. Pooled per-generation medians were 1,719.56 and
1,710.13 ms, a 0.55% difference with mixed trial results. This does not establish
a repeatable saving, and the micro-optimization was reverted. The
[retained trial patch](dense-shard-inline.patch) and
[exact results/manifests](dense-shard-inline.json) preserve the candidate for
inspection; no runtime change from that trial is selected.

| Trial side (12 generation samples) | Retained legacy plus oracle ms | Added sync ms | Combined new owner ms |
| --- | ---: | ---: | ---: |
| Before micro-optimization | 7,180.476 | 13,106.634 | 20,287.110 |
| After micro-optimization | 7,179.981 | 13,060.097 | 20,240.078 |

Both sides are sync-enabled source: this is not a new comparison with the old
installed owner and cannot qualify the 25% ceiling. All snapshot/projection/
support/census signatures agree; native delivered wire/root parity is outside
this timing probe. Each trial retains six baseline-required fallbacks rather
than delivered recovery. Close leaves zero live allocations/objects/leases,
with only the account's fixed base charge. The earlier matched producer CPU
gate stays failed, and Reader density, 2,000-row packed recovery, aggregate
resources/RSS, A1, native/installed and immutable paired artifacts stay open.
